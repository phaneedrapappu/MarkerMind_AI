"""
AI Analysis Agent - Analyses market data via LLM (Gemini, OpenAI, or Claude).
All stocks are sent in ONE batched prompt to minimise API cost.

Provider selection (via config.yaml or LLM_PROVIDER env var):
  gemini  – Google Gemini (default, free tier available)
  openai  – OpenAI GPT (paid)
  claude  – Anthropic Claude (paid, highest quality)
"""
import logging
import os
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..agents.base_agent import BaseAgent
from ..models.market_data import MarketDataSnapshot
from ..models.analysis_models import (
    AIAnalysisReport, DailyTradingAnalysis, BulkBlockAnalysis,
    InstitutionalAnalysis, PromoterAnalysis
)

# ── Provider availability checks ───────────────────────────────────────────────
try:
    from google import genai as google_genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    google_genai = None

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

try:
    import anthropic as anthropic_sdk
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    anthropic_sdk = None


class AIAnalysisAgent(BaseAgent):
    """
    AI Analysis Agent - Analyzes market data via Gemini (default), OpenAI, or Claude.
    Provider and model configurable via config.yaml or environment variables.
    All stocks are analysed in a single batched LLM call to save cost.
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__("AIAnalysisAgent", config)
        self.db = db_manager
        self.analysis_results: List[AIAnalysisReport] = []

        # ── Provider selection ─────────────────────────────────────────────────
        # Read from config first, then env var fallback
        self.llm_provider = (
            config.get("provider", "").strip().lower() or
            os.getenv("LLM_PROVIDER", "claude").lower().strip()
        )

        # Gemini settings
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model_name = (
            config.get("model", "").strip() or
            os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
        )
        self._gemini_client = None   # initialised in initialize()

        # OpenAI settings
        self.openai_api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY", "")
        self.openai_model = (
            config.get("model", "").strip() or
            config.get("openai_model", "gpt-4o-mini").strip()
        )
        self._openai_client = None

        # Claude / Anthropic settings
        self.claude_api_key = os.getenv("CLAUDE_API_KEY", "").strip()
        self.claude_model = (
            config.get("model", "").strip() or
            os.getenv("CLAUDE_MODEL", "claude-opus-4-5").strip()
        )
        self._claude_client = None

        # model label shown in logs / DB
        self.model = (
            self.gemini_model_name if self.llm_provider == "gemini"
            else self.claude_model if self.llm_provider == "claude"
            else self.openai_model
        )

    def initialize(self) -> bool:
        try:
            self.logger.info(f"Initialising AI Analysis Agent  [provider={self.llm_provider}]")

            if self.llm_provider == "gemini":
                if not GEMINI_AVAILABLE:
                    self.logger.error("google-genai not installed. Run: pip install google-genai")
                    return False
                if not self.gemini_api_key:
                    self.logger.error("GEMINI_API_KEY env var not set.")
                    return False
                self._gemini_client = google_genai.Client(api_key=self.gemini_api_key)
                self.logger.info(f"Gemini client ready – model: {self.gemini_model_name}")

            elif self.llm_provider == "openai":
                if not OPENAI_AVAILABLE:
                    self.logger.error("openai package not installed. Run: pip install openai")
                    return False
                if not self.openai_api_key:
                    self.logger.error("OPENAI_API_KEY env var not set.")
                    return False
                self._openai_client = OpenAI(api_key=self.openai_api_key)
                self.logger.info(f"OpenAI client ready – model: {self.openai_model}")

            elif self.llm_provider == "claude":
                if not CLAUDE_AVAILABLE:
                    self.logger.error("anthropic package not installed. Run: pip install anthropic")
                    return False
                if not self.claude_api_key:
                    self.logger.error("CLAUDE_API_KEY env var not set.")
                    return False
                self._claude_client = anthropic_sdk.Anthropic(api_key=self.claude_api_key)
                self.logger.info(f"Claude client ready – model: {self.claude_model}")

            else:
                self.logger.error(f"Unknown LLM_PROVIDER '{self.llm_provider}'. Use 'gemini', 'openai', or 'claude'.")
                return False

            return True

        except Exception as exc:
            self.logger.error(f"Failed to initialise AI Analysis Agent: {exc}")
            return False
    
    def execute(self, market_data: List[MarketDataSnapshot]) -> List[AIAnalysisReport]:
        """
        Execute the agent – analyse all stocks in a SINGLE batched LLM call.
        Falls back to per-stock calls if JSON parsing fails.
        """
        self.log_execution()
        self.logger.info(f"Batch-analysing {len(market_data)} stock(s) using {self.model}")

        self.analysis_results = []

        if not market_data:
            return self.analysis_results

        try:
            self.analysis_results = self._batch_analyze(market_data)
        except Exception as exc:
            self.logger.warning(f"Batch analysis failed ({exc}), falling back to per-stock mode")
            for snapshot in market_data:
                try:
                    analysis = self._analyze_snapshot(snapshot)
                    if analysis:
                        self.analysis_results.append(analysis)
                        self._print_analysis_summary(analysis)
                except Exception as inner_exc:
                    self.logger.error(f"Error analysing {snapshot.stock_data.symbol}: {inner_exc}")

        # Persist to DB
        if self.db:
            for analysis in self.analysis_results:
                try:
                    self.db.save_analysis_report({
                        "symbol": analysis.symbol,
                        "analysis_date": analysis.timestamp,
                        "model_used": self.model,
                        "raw_llm_response": analysis.raw_llm_response,
                        "overall_sentiment": analysis.overall_sentiment,
                        "signal_strength": 0.0,
                        "summary": "; ".join(analysis.key_highlights[:3]),
                    })
                except Exception as db_exc:
                    self.logger.warning(f"DB persist failed for {analysis.symbol}: {db_exc}")

        return self.analysis_results

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _extract_json(self, text: str):
        """Robustly extract a JSON object/array from an LLM response."""
        text = text.strip()
        # 1. Direct parse
        try:
            return json.loads(text)
        except Exception:
            pass
        # 2. Fenced code block
        m = re.search(r"```(?:json)?\s*([\[\{][\s\S]*?[\]\}])\s*```", text)
        if m:
            return json.loads(m.group(1))
        # 3. First JSON array or object found anywhere
        m = re.search(r"([\[\{][\s\S]*[\]\}])", text)
        if m:
            return json.loads(m.group(1))
        raise ValueError("No valid JSON found in LLM response")

    def _call_llm(self, system_msg: str, user_msg: str) -> str:
        """Route the LLM call to the configured provider. Returns raw text."""
        if self.llm_provider == "gemini":
            if not self._gemini_client:
                raise RuntimeError("Gemini client not initialised")
            full_prompt = f"{system_msg}\n\n{user_msg}"
            try:
                response = self._gemini_client.models.generate_content(
                    model=self.gemini_model_name,
                    contents=full_prompt,
                )
            except Exception as exc:
                err_str = str(exc)
                if "403" in err_str or "PERMISSION_DENIED" in err_str or "denied access" in err_str.lower():
                    self.logger.error(
                        "Gemini API 403 PERMISSION_DENIED — the project key has been denied. "
                        "Go to https://aistudio.google.com, create a new API key, and update "
                        "GEMINI_API_KEY in your .env file."
                    )
                    raise RuntimeError(
                        "Gemini API access denied (403). Please rotate your GEMINI_API_KEY."
                    ) from exc
                raise
            return response.text or ""

        elif self.llm_provider == "openai":
            if not self._openai_client:
                raise RuntimeError("OpenAI client not initialised")
            response = self._openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
                max_tokens=2000,
            )
            return response.choices[0].message.content.strip()

        elif self.llm_provider == "claude":
            if not self._claude_client:
                raise RuntimeError("Claude client not initialised")
            response = self._claude_client.messages.create(
                model=self.claude_model,
                max_tokens=4096,
                system=system_msg,
                messages=[{"role": "user", "content": user_msg}],
            )
            return response.content[0].text.strip()

        raise ValueError(f"Unknown provider: {self.llm_provider}")

    # ── Batch LLM call ─────────────────────────────────────────────────────────

    def _batch_analyze(self, snapshots: List[MarketDataSnapshot]) -> List[AIAnalysisReport]:
        """Send all stocks in one prompt and parse structured JSON response."""
        stocks_summary = ""
        for i, snapshot in enumerate(snapshots, 1):
            stock = snapshot.stock_data
            stocks_summary += f"\n--- Stock {i}: {stock.symbol} ({stock.company_name}) ---\n"
            stocks_summary += (
                f"Price: Rs{stock.price:,.2f}  Change: {stock.change_percent:+.2f}%\n"
                f"Open: Rs{stock.open_price:,.2f}  High: Rs{stock.high:,.2f}  Low: Rs{stock.low:,.2f}\n"
                f"Volume: {stock.volume:,}\n"
            )
            if snapshot.bulk_block_deals:
                stocks_summary += f"Bulk/Block deals: {len(snapshot.bulk_block_deals)} deal(s)\n"
            if snapshot.institutional_activity:
                for a in snapshot.institutional_activity:
                    stocks_summary += f"{a.institution_type}: Net Rs{a.net_value:+,.0f}Cr\n"

            # Attach recent news headlines from DB
            news_pos = news_neg = news_total = 0
            if self.db:
                try:
                    recent_news = self.db.get_news(symbol=stock.symbol, limit=8)
                    if recent_news:
                        news_total = len(recent_news)
                        headlines = []
                        for n in recent_news:
                            sent = n.get("sentiment", "NEUTRAL")
                            if sent == "POSITIVE":
                                news_pos += 1
                            elif sent == "NEGATIVE":
                                news_neg += 1
                            headlines.append(f"[{sent}] {n.get('title','')[:80]}")
                        stocks_summary += f"Recent news ({news_total} articles, +{news_pos}/-{news_neg}):\n"
                        stocks_summary += "\n".join(f"  • {h}" for h in headlines[:5]) + "\n"
                except Exception:
                    pass
            # Store news counts on snapshot so we can attach them to the report later
            snapshot._news_pos   = news_pos    # type: ignore[attr-defined]
            snapshot._news_neg   = news_neg    # type: ignore[attr-defined]
            snapshot._news_total = news_total  # type: ignore[attr-defined]

        system_msg = (
            "You are an expert financial analyst specialising in Indian stock markets. "
            "Return ONLY a valid JSON array (no markdown fences, no extra commentary) "
            "where each element has exactly these keys:\n"
            "  symbol       – NSE ticker (string)\n"
            "  sentiment    – one of: Bullish, Bearish, Neutral\n"
            "  signal       – one of: BUY, SELL, HOLD\n"
            "  confidence   – integer 0-100 reflecting your conviction based on price action, "
                              "news sentiment, volume, and available data quality. "
                              "Use the full range: strong signal with good data = 75-95, "
                              "weak/mixed evidence = 40-60, contradictory signals = 30-50.\n"
            "  highlights   – list of 3 concise strings (key positive factors)\n"
            "  concerns     – list of 1-2 concise strings (key risk factors)\n"
            "  analysis     – 2-3 sentence plain-text summary\n"
        )
        user_msg = (
            f"Analyse the following {len(snapshots)} Indian stocks. "
            f"Set confidence independently per stock based on the evidence provided.\n"
            f"{stocks_summary}"
        )

        raw = self._call_llm(system_msg, user_msg)
        parsed = self._extract_json(raw)   # Raises on bad JSON – caught by caller

        results: List[AIAnalysisReport] = []
        for snapshot in snapshots:
            stock = snapshot.stock_data
            item = next((p for p in parsed if p.get("symbol") == stock.symbol), {})
            sentiment    = item.get("sentiment", "Neutral")
            highlights   = item.get("highlights", [])
            concerns     = item.get("concerns", [])
            analysis_text = item.get("analysis", raw)
            llm_confidence = float(item.get("confidence", 55))

            daily = DailyTradingAnalysis(
                symbol=stock.symbol,
                date=stock.timestamp,
                price_movement=f"{stock.change_percent:+.2f}% move",
                volume_analysis=f"{stock.volume:,} shares traded",
                buyer_seller_balance=sentiment,
                key_observations=highlights,
            )
            report = AIAnalysisReport(
                symbol=stock.symbol,
                company_name=stock.company_name,
                timestamp=datetime.now(),
                daily_trading=daily,
                overall_sentiment=sentiment,
                key_highlights=highlights,
                concerns=concerns,
                raw_llm_response=analysis_text,
                llm_confidence=llm_confidence,
                price_change_pct=stock.change_percent,
                news_pos=getattr(snapshot, "_news_pos", 0),
                news_neg=getattr(snapshot, "_news_neg", 0),
                news_total=getattr(snapshot, "_news_total", 0),
            )
            self._print_analysis_summary(report)
            results.append(report)

        return results
    
    def _analyze_snapshot(self, snapshot: MarketDataSnapshot) -> Optional[AIAnalysisReport]:
        """
        Analyse a single stock snapshot (used as fallback when batch JSON parse fails).
        """
        prompt = self._build_analysis_prompt(snapshot)
        system_msg = (
            "You are an expert financial analyst specialising in Indian stock markets. "
            "Analyse market data and provide clear, actionable insights."
        )
        try:
            llm_response = self._call_llm(system_msg, prompt)
            return self._parse_llm_response(snapshot, llm_response)
        except Exception as exc:
            self.logger.error(f"Error calling {self.llm_provider} API: {exc}")
            return None
    
    def _build_analysis_prompt(self, snapshot: MarketDataSnapshot) -> str:
        """
        Build detailed prompt for GPT analysis
        
        Args:
            snapshot: MarketDataSnapshot
            
        Returns:
            Formatted prompt string
        """
        stock = snapshot.stock_data
        
        prompt = f"""Analyze this Indian stock market data for {stock.company_name} ({stock.symbol}):

📊 STOCK DATA:
- Current Price: ₹{stock.price:,.2f}
- Change: ₹{stock.change:+.2f} ({stock.change_percent:+.2f}%)
- Open: ₹{stock.open_price:,.2f} | High: ₹{stock.high:,.2f} | Low: ₹{stock.low:,.2f}
- Volume: {stock.volume:,} shares
- Date: {stock.timestamp.strftime('%Y-%m-%d')}

"""
        
        # Add bulk/block deals if available
        if snapshot.bulk_block_deals:
            prompt += f"""🔔 BULK/BLOCK DEALS ({len(snapshot.bulk_block_deals)} deals):
"""
            for deal in snapshot.bulk_block_deals[:5]:  # Limit to 5 deals
                prompt += f"- {deal.deal_type}: {deal.client_name} | Qty: {deal.quantity:,} @ ₹{deal.price:.2f}\n"
            prompt += "\n"
        
        # Add institutional activity if available
        if snapshot.institutional_activity:
            prompt += "🏦 INSTITUTIONAL ACTIVITY:\n"
            for activity in snapshot.institutional_activity:
                prompt += f"- {activity.institution_type}: Buy ₹{activity.buy_value:,.0f}Cr | Sell ₹{activity.sell_value:,.0f}Cr | Net ₹{activity.net_value:+,.0f}Cr\n"
            prompt += "\n"
        
        prompt += """
Please provide a structured analysis in the following format:

1. DAILY TRADING ANALYSIS:
   - Price movement interpretation
   - Volume analysis (compared to typical volumes)
   - Buyer/seller balance

2. BULK/BLOCK DEALS ANALYSIS (if any):
   - Number of shares traded: [exact number]
   - Significance of these deals
   - Impact assessment (Bullish/Bearish/Neutral)

3. FII/DII ACTIVITY ANALYSIS (if available):
   - FII sentiment (Bullish/Bearish/Neutral)
   - DII sentiment (Bullish/Bearish/Neutral)
   - Overall interpretation

4. OVERALL ASSESSMENT:
   - Overall sentiment (Bullish/Bearish/Neutral)
   - Key highlights (3-4 points)
   - Concerns (if any)
   - Opportunities (if any)

Keep analysis concise and actionable. Focus on what the data tells us about market sentiment and potential moves.
"""
        
        return prompt
    
    def _parse_llm_response(self, snapshot: MarketDataSnapshot, llm_response: str) -> AIAnalysisReport:
        """
        Parse LLM response into structured analysis
        
        Args:
            snapshot: Original market data snapshot
            llm_response: Raw LLM response text
            
        Returns:
            AIAnalysisReport
        """
        stock = snapshot.stock_data
        
        # Create daily trading analysis
        daily_trading = DailyTradingAnalysis(
            symbol=stock.symbol,
            date=stock.timestamp,
            price_movement=f"{stock.change_percent:+.2f}% move",
            volume_analysis=f"{stock.volume:,} shares traded",
            buyer_seller_balance="Analyzing..."
        )
        
        # Create bulk/block analysis if deals exist
        bulk_block_analysis = None
        if snapshot.bulk_block_deals:
            total_shares = sum(deal.quantity for deal in snapshot.bulk_block_deals)
            significant_deals = [
                f"{deal.client_name}: {deal.quantity:,} shares @ ₹{deal.price:.2f}"
                for deal in snapshot.bulk_block_deals[:3]
            ]
            
            bulk_block_analysis = BulkBlockAnalysis(
                symbol=stock.symbol,
                date=stock.timestamp,
                total_deals=len(snapshot.bulk_block_deals),
                significant_deals=significant_deals,
                interpretation=f"Total {total_shares:,} shares in bulk/block deals",
                impact_assessment="Analyzing..."
            )
        
        # Create institutional analysis if data exists
        institutional_analysis = None
        if snapshot.institutional_activity:
            fii_data = next((a for a in snapshot.institutional_activity if a.institution_type == 'FII'), None)
            dii_data = next((a for a in snapshot.institutional_activity if a.institution_type == 'DII'), None)
            
            if fii_data or dii_data:
                net_flow = (fii_data.net_value if fii_data else 0) + (dii_data.net_value if dii_data else 0)
                
                institutional_analysis = InstitutionalAnalysis(
                    symbol=stock.symbol,
                    date=stock.timestamp,
                    fii_sentiment="Analyzing..." if fii_data else "N/A",
                    dii_sentiment="Analyzing..." if dii_data else "N/A",
                    net_institutional_flow=net_flow,
                    interpretation="Analyzing institutional flows...",
                    confidence_level="Medium"
                )
        
        # Extract key insights from LLM response
        key_highlights = []
        concerns = []
        overall_sentiment = "Neutral"
        
        # Simple parsing - look for sentiment indicators
        response_lower = llm_response.lower()
        if "bullish" in response_lower or "positive" in response_lower or "buy" in response_lower:
            overall_sentiment = "Bullish"
        elif "bearish" in response_lower or "negative" in response_lower or "sell" in response_lower:
            overall_sentiment = "Bearish"
        
        # Create analysis report
        analysis = AIAnalysisReport(
            symbol=stock.symbol,
            company_name=stock.company_name,
            timestamp=datetime.now(),
            daily_trading=daily_trading,
            bulk_block_analysis=bulk_block_analysis,
            institutional_analysis=institutional_analysis,
            overall_sentiment=overall_sentiment,
            key_highlights=key_highlights,
            concerns=concerns,
            raw_llm_response=llm_response
        )
        
        return analysis
    
    def _print_analysis_summary(self, analysis: AIAnalysisReport):
        """Print analysis summary"""
        print(f"\n{'='*70}")
        print(f"🤖 AI ANALYSIS: {analysis.company_name} ({analysis.symbol})")
        print(f"{'='*70}")
        print(f"\n📊 Overall Sentiment: {analysis.overall_sentiment}")
        print(f"\n💡 GPT Analysis:")
        print(analysis.raw_llm_response)
        print(f"{'='*70}\n")
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up AI Analysis Agent")
        self.client = None
    
    def get_analysis_results(self) -> List[AIAnalysisReport]:
        """Get the analysis results"""
        return self.analysis_results
