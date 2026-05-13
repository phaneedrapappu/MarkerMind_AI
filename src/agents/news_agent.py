"""
News Agent - Fetches and analyses financial news for tracked stocks.
Uses free RSS feeds (RSS from Google Finance / Moneycontrol / Economic Times)
so no paid API key is required.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus

import feedparser
import requests

from .base_agent import BaseAgent
from ..database.db_manager import DatabaseManager

logger = logging.getLogger("MarketMindAI.NewsAgent")

# ── RSS feed templates ─────────────────────────────────────────────────────────
GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search?q={query}+stock+india&hl=en-IN&gl=IN&ceid=IN:en"
)
ET_MARKETS_RSS = "https://economictimes.indiatimes.com/markets/rss.cms"
MONEYCONTROL_RSS = "https://www.moneycontrol.com/rssfeeds/marketsnews.xml"

SENTIMENT_KEYWORDS = {
    "POSITIVE": [
        "rally", "surge", "gain", "bull", "profit", "growth", "strong", "beat",
        "upgrade", "buy", "outperform", "positive", "record high", "breakout",
    ],
    "NEGATIVE": [
        "fall", "drop", "crash", "bear", "loss", "weak", "miss", "downgrade",
        "sell", "underperform", "negative", "record low", "breakdown", "dip",
    ],
}


def _simple_sentiment(text: str) -> str:
    text_lower = text.lower()
    pos = sum(1 for kw in SENTIMENT_KEYWORDS["POSITIVE"] if kw in text_lower)
    neg = sum(1 for kw in SENTIMENT_KEYWORDS["NEGATIVE"] if kw in text_lower)
    if pos > neg:
        return "POSITIVE"
    if neg > pos:
        return "NEGATIVE"
    return "NEUTRAL"


class NewsAgent(BaseAgent):
    """
    Fetches recent financial news for each tracked stock and the general
    Indian market via RSS feeds.  Persists results to the database.
    """

    def __init__(self, config: Dict[str, Any], db_manager: DatabaseManager):
        super().__init__("NewsAgent", config)
        self.db = db_manager
        self.stocks: List[str] = config.get("stocks", [])
        self.max_articles_per_stock: int = config.get("max_articles_per_stock", 5)
        self.lookback_hours: int = config.get("lookback_hours", 24)

    def initialize(self) -> bool:
        try:
            logger.info("Initialising News Agent")
            # Verify feedparser is importable
            _ = feedparser.__version__
            logger.info("News Agent ready – using RSS feeds (no API key required)")
            return True
        except Exception as exc:
            logger.error(f"News Agent init failed: {exc}")
            return False

    # ── Public interface ───────────────────────────────────────────────────────

    def execute(self) -> List[Dict[str, Any]]:
        """
        Fetch news for all tracked stocks + general market news.

        Returns:
            List of news dicts (also saved to DB).
        """
        self.log_execution()
        all_news: List[Dict[str, Any]] = []

        # General market news
        logger.info("Fetching general market news …")
        all_news.extend(self._fetch_feed(ET_MARKETS_RSS, symbol=None))
        all_news.extend(self._fetch_feed(MONEYCONTROL_RSS, symbol=None))

        # Stock-specific news
        for symbol in self.stocks:
            logger.info(f"Fetching news for {symbol} …")
            url = GOOGLE_NEWS_RSS.format(query=quote_plus(symbol))
            all_news.extend(self._fetch_feed(url, symbol=symbol))

        # Deduplicate by URL
        seen: set = set()
        unique_news: List[Dict] = []
        for article in all_news:
            if article["url"] not in seen:
                seen.add(article["url"])
                unique_news.append(article)

        # Persist to DB
        if unique_news:
            try:
                self.db.save_news(unique_news)
                logger.info(f"Saved {len(unique_news)} news articles to database")
            except Exception as exc:
                logger.error(f"Failed to persist news: {exc}")

        logger.info(f"News Agent fetched {len(unique_news)} unique articles")
        return unique_news

    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("NewsAgent cleanup")

    # ── Private helpers ────────────────────────────────────────────────────────

    def _fetch_feed(self, url: str, symbol: Optional[str]) -> List[Dict[str, Any]]:
        """Parse a single RSS feed and return article dicts."""
        articles: List[Dict[str, Any]] = []
        cutoff = datetime.utcnow() - timedelta(hours=self.lookback_hours)

        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[: self.max_articles_per_stock * 2]:
                # Parse published date
                published_at = datetime.utcnow()
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published_at = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass

                if published_at < cutoff:
                    continue

                title = getattr(entry, "title", "")
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                # Strip HTML tags from summary
                summary = re.sub(r"<[^>]+>", " ", summary).strip()
                link = getattr(entry, "link", "")
                source = getattr(feed.feed, "title", url.split("/")[2])
                sentiment = _simple_sentiment(f"{title} {summary}")

                articles.append(
                    {
                        "symbol": symbol.upper() if symbol else None,
                        "title": title[:499],
                        "summary": summary[:2000],
                        "url": link[:999],
                        "source": source[:99],
                        "published_at": published_at,
                        "sentiment": sentiment,
                    }
                )
                if len(articles) >= self.max_articles_per_stock:
                    break

        except Exception as exc:
            logger.warning(f"Failed to fetch feed {url}: {exc}")

        return articles
