"""
Report Generator Agent - Creates matplotlib charts and PDF/PNG reports
for each stock analysis cycle.  Charts are attached to emails.
"""
import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")           # Non-interactive backend – safe in server/CLI mode
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import numpy as np

from .base_agent import BaseAgent
from ..database.db_manager import DatabaseManager

logger = logging.getLogger("MarketMindAI.ReportGeneratorAgent")

REPORTS_DIR = Path("data/reports")


class ReportGeneratorAgent(BaseAgent):
    """
    Generates graphical reports for each stock and returns file paths
    so they can be attached to emails.
    """

    def __init__(self, config: Dict[str, Any], db_manager: DatabaseManager):
        super().__init__("ReportGeneratorAgent", config)
        self.db = db_manager
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> bool:
        try:
            logger.info("Report Generator Agent initialised")
            return True
        except Exception as exc:
            logger.error(f"Report Generator init failed: {exc}")
            return False

    # ── Public interface ───────────────────────────────────────────────────────

    def execute(
        self,
        market_data: List[Any],
        analysis_reports: List[Any],
        signals: List[Any],
        news: List[Dict],
    ) -> Dict[str, List[str]]:
        """
        Build per-stock report images.

        Returns:
            {symbol: [list of absolute file paths to PNG images]}
        """
        self.log_execution()
        result: Dict[str, List[str]] = {}

        for snapshot in market_data:
            symbol = snapshot.stock_data.symbol
            logger.info(f"Generating report charts for {symbol} …")

            analysis = next(
                (a for a in analysis_reports if a.symbol == symbol), None
            )
            signal = next(
                (s for s in signals if s.symbol == symbol), None
            )
            stock_news = [n for n in news if n.get("symbol") == symbol][: 5]

            paths: List[str] = []

            # 1. Price / volume chart
            path = self._price_volume_chart(snapshot, signal)
            if path:
                paths.append(path)

            # 2. Signal summary chart
            path = self._signal_summary_chart(symbol, signal, analysis)
            if path:
                paths.append(path)

            # 3. News sentiment chart
            path = self._news_sentiment_chart(symbol, stock_news)
            if path:
                paths.append(path)

            # 4. Historical signals chart (from DB)
            path = self._historical_signals_chart(symbol)
            if path:
                paths.append(path)

            result[symbol] = paths
            logger.info(f"  → {len(paths)} chart(s) generated for {symbol}")

        return result

    # ── Chart builders ─────────────────────────────────────────────────────────

    def _price_volume_chart(self, snapshot: Any, signal: Optional[Any]) -> Optional[str]:
        """OHLCV bar chart + volume bars from DB history + current snapshot."""
        symbol = snapshot.stock_data.symbol
        history = self.db.get_recent_stock_data(symbol, limit=30)
        stock = snapshot.stock_data

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=False,
                                       gridspec_kw={"height_ratios": [3, 1]})
        fig.suptitle(f"{stock.company_name} ({symbol})  |  "
                     f"₹{stock.price:,.2f}  ({stock.change_percent:+.2f}%)",
                     fontsize=13, fontweight="bold")

        if len(history) >= 2:
            dates = [datetime.fromisoformat(r["timestamp"]) for r in reversed(history)]
            prices = [r["price"] for r in reversed(history)]
            volumes = [r["volume"] for r in reversed(history)]

            color = "green" if prices[-1] >= prices[0] else "red"
            ax1.plot(dates, prices, color=color, linewidth=2, label="Close Price")
            ax1.fill_between(dates, prices, alpha=0.1, color=color)
            ax1.set_ylabel("Price (₹)", fontsize=10)
            ax1.legend(loc="upper left", fontsize=9)
            ax1.grid(True, alpha=0.3)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
            fig.autofmt_xdate()

            bar_colors = ["green" if v > 0 else "red" for v in volumes]
            ax2.bar(dates, volumes, color=bar_colors, alpha=0.7)
            ax2.set_ylabel("Volume", fontsize=10)
            ax2.grid(True, alpha=0.3)
        else:
            # Single data point fallback
            labels = ["Open", "High", "Low", "Close"]
            vals = [stock.open_price, stock.high, stock.low, stock.price]
            bar_c = ["blue", "green", "red", "orange"]
            ax1.bar(labels, vals, color=bar_c, alpha=0.8)
            ax1.set_ylabel("Price (₹)", fontsize=10)
            ax1.grid(True, alpha=0.3)
            ax2.bar(["Volume"], [stock.volume], color="steelblue", alpha=0.8)
            ax2.set_ylabel("Volume", fontsize=10)

        # Signal annotation
        if signal:
            color_map = {"BUY": "green", "SELL": "red", "HOLD": "orange"}
            ax1.set_title(
                f"Signal: {signal.signal_type}  |  Confidence: {signal.confidence_ratio:.0%}  |  Risk: {signal.risk_level_str}",
                fontsize=9, color=color_map.get(signal.signal_type, "black")
            )

        plt.tight_layout()
        path = str(REPORTS_DIR / f"{symbol}_price_volume_{_ts()}.png")
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        return path

    def _signal_summary_chart(
        self, symbol: str, signal: Optional[Any], analysis: Optional[Any]
    ) -> Optional[str]:
        """Gauge-style chart showing signal strength and factors."""
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        fig.suptitle(f"{symbol} — Signal Summary", fontsize=13, fontweight="bold")

        # Left: Signal gauge (simple bar)
        ax = axes[0]
        if signal:
            confidence = signal.confidence_ratio
            color = {"BUY": "green", "SELL": "red", "HOLD": "orange"}.get(signal.signal_type, "gray")
            ax.barh(["Confidence"], [confidence], color=color, alpha=0.8)
            ax.barh(["Confidence"], [1.0], color="lightgray", alpha=0.3)
            ax.set_xlim(0, 1)
            ax.set_xlabel("Confidence Score")
            ax.text(
                confidence / 2, 0,
                f"{signal.signal_type}\n{confidence:.0%}",
                ha="center", va="center", fontsize=14, fontweight="bold", color="white"
            )
            ax.set_title("Trading Signal", fontsize=11)
        else:
            ax.text(0.5, 0.5, "No Signal", ha="center", va="center", fontsize=14)
            ax.axis("off")

        # Right: Supporting vs risk factors count
        ax2 = axes[1]
        if signal:
            sup_count = len(signal.supporting_factors)
            risk_count = len(signal.risk_factors)
            bars = ax2.bar(
                ["Supporting\nFactors", "Risk\nFactors"],
                [sup_count, risk_count],
                color=["green", "red"],
                alpha=0.8,
                width=0.5
            )
            for bar, val in zip(bars, [sup_count, risk_count]):
                ax2.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.1,
                    str(val), ha="center", va="bottom", fontsize=12, fontweight="bold"
                )
            ax2.set_ylim(0, max(sup_count + risk_count, 5) + 1)
            ax2.set_title("Factor Breakdown", fontsize=11)
            ax2.grid(True, alpha=0.3, axis="y")
        else:
            ax2.axis("off")

        plt.tight_layout()
        path = str(REPORTS_DIR / f"{symbol}_signal_{_ts()}.png")
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        return path

    def _news_sentiment_chart(self, symbol: str, news_list: List[Dict]) -> Optional[str]:
        """Pie chart of news sentiment distribution."""
        if not news_list:
            return None

        from collections import Counter
        counts = Counter(n.get("sentiment", "NEUTRAL") for n in news_list)

        labels = list(counts.keys())
        sizes = list(counts.values())
        colors = [
            {"POSITIVE": "#2ecc71", "NEGATIVE": "#e74c3c", "NEUTRAL": "#95a5a6"}.get(l, "gray")
            for l in labels
        ]

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.pie(sizes, labels=labels, colors=colors, autopct="%1.0f%%",
               startangle=90, textprops={"fontsize": 11})
        ax.set_title(f"{symbol} — News Sentiment ({len(news_list)} articles)",
                     fontsize=12, fontweight="bold")

        plt.tight_layout()
        path = str(REPORTS_DIR / f"{symbol}_news_sentiment_{_ts()}.png")
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        return path

    def _historical_signals_chart(self, symbol: str) -> Optional[str]:
        """Bar chart of historical BUY/SELL/HOLD signal counts from DB."""
        history = self.db.get_signals_for_symbol(symbol, limit=20)
        if not history:
            return None

        from collections import Counter
        counts = Counter(r["signal_type"] for r in history)
        labels = ["BUY", "SELL", "HOLD"]
        values = [counts.get(l, 0) for l in labels]
        colors = ["green", "red", "orange"]

        fig, ax = plt.subplots(figsize=(6, 4))
        bars = ax.bar(labels, values, color=colors, alpha=0.8, width=0.5)
        for bar, val in zip(bars, values):
            if val:
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.1, str(val),
                        ha="center", va="bottom", fontsize=12, fontweight="bold")
        ax.set_title(f"{symbol} — Historical Signals (last {len(history)})",
                     fontsize=12, fontweight="bold")
        ax.set_ylabel("Count")
        ax.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()
        path = str(REPORTS_DIR / f"{symbol}_signal_history_{_ts()}.png")
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        return path


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
