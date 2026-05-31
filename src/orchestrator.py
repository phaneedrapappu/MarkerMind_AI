"""
Agent Orchestrator - Manages and coordinates all six agents in sequence:
  1. MarketDataAgent   – fetch live price / FII / bulk-deal data
  2. NewsAgent         – fetch financial news for tracked stocks
  3. AIAnalysisAgent   – batch LLM analysis (one API call)
  4. SignalGeneratorAgent – rule-based BUY/HOLD/SELL signals
  5. ReportGeneratorAgent – matplotlib charts
  6. EmailAlertAgent   – HTML digest email with embedded charts
"""
import logging
import yaml
from typing import Dict, List, Any
from pathlib import Path

from .agents.market_data_agent import MarketDataAgent
from .agents.news_agent import NewsAgent
from .agents.ai_analysis_agent import AIAnalysisAgent
from .agents.signal_generator_agent import SignalGeneratorAgent
from .agents.report_generator_agent import ReportGeneratorAgent
from .agents.email_alert_agent import EmailAlertAgent
from .database.db_manager import DatabaseManager
from .models.market_data import StockData, MarketDataSnapshot


class AgentOrchestrator:
    """
    Clean, sequential orchestration of all MarketMind AI agents.
    Each agent is self-contained; the orchestrator passes outputs
    from one stage as inputs to the next.
    """

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        self.db: DatabaseManager = None
        self.agents: Dict[str, Any] = {}
        self.tracked_stocks: List[str] = []
        self.logger = logging.getLogger("MarketMindAI.Orchestrator")

    # ── Config & logging ───────────────────────────────────────────────────────

    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as exc:
            print(f"Error loading config: {exc}")
            return {}

    def apply_overrides(self, overrides: Dict[str, Any]):
        """
        Apply runtime overrides before initialize_agents() is called.
        Supported keys:
          stocks     – list[str] of NSE symbols, replaces config stocks list
          recipients – list[str] of email addresses, replaces config recipients
        """
        if not overrides:
            return
        agent_cfgs = self.config.setdefault("agents", {})

        if "stocks" in overrides:
            mda = agent_cfgs.setdefault("market_data_agent", {})
            mda["stocks"] = overrides["stocks"]

        if "recipients" in overrides:
            email_cfg = agent_cfgs.setdefault("email_alert_agent", {})
            smtp = email_cfg.setdefault("smtp", {})
            smtp["recipients"] = overrides["recipients"]

        if "unsubscribe_url" in overrides:
            email_cfg = agent_cfgs.setdefault("email_alert_agent", {})
            email_cfg["unsubscribe_url"] = overrides["unsubscribe_url"]

        if "app_url" in overrides:
            email_cfg = agent_cfgs.setdefault("email_alert_agent", {})
            email_cfg["app_url"] = overrides["app_url"]

    def _setup_logging(self):
        log_cfg = self.config.get("logging", {})
        log_level = getattr(logging, log_cfg.get("level", "INFO"))
        log_format = log_cfg.get(
            "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        log_file = log_cfg.get("file", "logs/marketmind.log")
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        )
        self.logger.info("Logging configured")

    # ── Initialisation ─────────────────────────────────────────────────────────

    def initialize_agents(self):
        """Initialise database and all enabled agents."""
        self._setup_logging()
        self.logger.info("Initialising agents …")

        # ── Database ──────────────────────────────────────────────────────────
        db_cfg = self.config.get("database", {})
        db_path = db_cfg.get("path", "data/marketmind.db")
        self.db = DatabaseManager(db_path)

        agent_cfgs = self.config.get("agents", {})
        stocks = agent_cfgs.get("market_data_agent", {}).get("stocks", [])
        self.tracked_stocks = stocks

        # ── Market Data Agent ─────────────────────────────────────────────────
        mda_cfg = agent_cfgs.get("market_data_agent", {})
        if mda_cfg.get("enabled", False):
            agent = MarketDataAgent(mda_cfg, db_manager=self.db)
            if agent.initialize():
                self.agents["market_data_agent"] = agent
                self.logger.info("✅ MarketDataAgent initialised")

        # ── News Agent ────────────────────────────────────────────────────────
        news_cfg = agent_cfgs.get("news_agent", {})
        if news_cfg.get("enabled", False):
            news_cfg.setdefault("stocks", stocks)
            agent = NewsAgent(news_cfg, db_manager=self.db)
            if agent.initialize():
                self.agents["news_agent"] = agent
                self.logger.info("✅ NewsAgent initialised")

        # ── AI Analysis Agent ─────────────────────────────────────────────────
        ai_cfg = agent_cfgs.get("ai_analysis_agent", {})
        if ai_cfg.get("enabled", False):
            agent = AIAnalysisAgent(ai_cfg, db_manager=self.db)
            if agent.initialize():
                self.agents["ai_analysis_agent"] = agent
                self.logger.info("✅ AIAnalysisAgent initialised")

        # ── Signal Generator Agent ────────────────────────────────────────────
        sig_cfg = agent_cfgs.get("signal_generator_agent", {})
        if sig_cfg.get("enabled", False):
            agent = SignalGeneratorAgent(sig_cfg, db_manager=self.db)
            if agent.initialize():
                self.agents["signal_generator_agent"] = agent
                self.logger.info("✅ SignalGeneratorAgent initialised")

        # ── Report Generator Agent ────────────────────────────────────────────
        rpt_cfg = agent_cfgs.get("report_generator_agent", {})
        if rpt_cfg.get("enabled", False):
            agent = ReportGeneratorAgent(rpt_cfg, db_manager=self.db)
            if agent.initialize():
                self.agents["report_generator_agent"] = agent
                self.logger.info("✅ ReportGeneratorAgent initialised")

        # ── Email Alert Agent ─────────────────────────────────────────────────
        email_cfg = agent_cfgs.get("email_alert_agent", {})
        if email_cfg.get("enabled", False):
            agent = EmailAlertAgent(email_cfg, db_manager=self.db)
            if agent.initialize():
                self.agents["email_alert_agent"] = agent
                self.logger.info("✅ EmailAlertAgent initialised")

        self.logger.info(f"Initialised {len(self.agents)} agent(s)")

    # ── Main execution pipeline ────────────────────────────────────────────────

    def run_agents(self) -> Dict[str, Any]:
        """
        Run the full pipeline in a clean, sequential order.
        Each stage's output is passed to the next stage.
        """
        self.logger.info("Starting agent pipeline …")
        results: Dict[str, Any] = {}

        # ── Stage 1: Market Data ──────────────────────────────────────────────
        market_data = []
        if "market_data_agent" in self.agents:
            self.logger.info("Stage 1/6: Market Data Agent")
            agent = self.agents["market_data_agent"]
            agent.start()
            try:
                market_data = agent.execute()
                results["market_data_agent"] = {
                    "status": "success",
                    "data_count": len(market_data),
                }
                self.logger.info(f"  → {len(market_data)} snapshot(s) collected")
            except Exception as exc:
                self.logger.error(f"Market Data Agent error: {exc}")
                results["market_data_agent"] = {"status": "error", "error": str(exc)}
                return results   # Nothing to analyse without market data

        if not market_data:
            self.logger.warning("No live market data – attempting DB fallback …")
            market_data = self._load_market_data_from_db()
            if not market_data:
                self.logger.warning("No market data in DB either – aborting pipeline")
                return results
            self.logger.info(f"DB fallback: loaded {len(market_data)} cached snapshot(s)")

        # ── Stage 2: News ─────────────────────────────────────────────────────
        news: List[Dict] = []
        if "news_agent" in self.agents:
            self.logger.info("Stage 2/6: News Agent")
            agent = self.agents["news_agent"]
            agent.start()
            try:
                news = agent.execute()
                results["news_agent"] = {"status": "success", "article_count": len(news)}
                self.logger.info(f"  → {len(news)} article(s) fetched")
            except Exception as exc:
                self.logger.error(f"News Agent error: {exc}")
                results["news_agent"] = {"status": "error", "error": str(exc)}

        # ── Stage 3: AI Analysis ──────────────────────────────────────────────
        analysis_reports = []
        if "ai_analysis_agent" in self.agents:
            self.logger.info("Stage 3/6: AI Analysis Agent")
            agent = self.agents["ai_analysis_agent"]
            agent.start()
            try:
                analysis_reports = agent.execute(market_data)
                results["ai_analysis_agent"] = {
                    "status": "success",
                    "analysis_count": len(analysis_reports),
                }
                self.logger.info(f"  → {len(analysis_reports)} analysis report(s) generated")
            except Exception as exc:
                self.logger.error(f"AI Analysis Agent error: {exc}")
                results["ai_analysis_agent"] = {"status": "error", "error": str(exc)}

        # ── Stage 4: Signal Generation ────────────────────────────────────────
        signals = []
        if analysis_reports and "signal_generator_agent" in self.agents:
            self.logger.info("Stage 4/6: Signal Generator Agent")
            agent = self.agents["signal_generator_agent"]
            agent.start()
            try:
                signals = agent.execute(analysis_reports)
                results["signal_generator_agent"] = {
                    "status": "success",
                    "signal_count": len(signals),
                    "signals": signals,
                }
                self.logger.info(f"  → {len(signals)} signal(s) generated")
            except Exception as exc:
                self.logger.error(f"Signal Generator Agent error: {exc}")
                results["signal_generator_agent"] = {"status": "error", "error": str(exc)}

        # ── Stage 5: Report Generation ────────────────────────────────────────
        chart_paths: Dict[str, List[str]] = {}
        if "report_generator_agent" in self.agents:
            self.logger.info("Stage 5/6: Report Generator Agent")
            agent = self.agents["report_generator_agent"]
            agent.start()
            try:
                chart_paths = agent.execute(market_data, analysis_reports, signals, news)
                total_charts = sum(len(v) for v in chart_paths.values())
                results["report_generator_agent"] = {
                    "status": "success",
                    "chart_count": total_charts,
                }
                self.logger.info(f"  → {total_charts} chart(s) generated")
            except Exception as exc:
                self.logger.error(f"Report Generator Agent error: {exc}")
                results["report_generator_agent"] = {"status": "error", "error": str(exc)}

        # ── Stage 6: Email Alert ──────────────────────────────────────────────
        if "email_alert_agent" in self.agents:
            self.logger.info("Stage 6/6: Email Alert Agent")
            agent = self.agents["email_alert_agent"]
            agent.start()
            try:
                email_result = agent.execute(
                    market_data, analysis_reports, signals, news, chart_paths
                )
                results["email_alert_agent"] = email_result
                self.logger.info(f"  → Email result: {email_result.get('status')}")
            except Exception as exc:
                self.logger.error(f"Email Alert Agent error: {exc}")
                results["email_alert_agent"] = {"status": "error", "error": str(exc)}

        self.logger.info("Pipeline complete.")
        return results

    # ── Lifecycle helpers ──────────────────────────────────────────────────────

    # ── DB fallback ────────────────────────────────────────────────────────────

    def _load_market_data_from_db(self) -> List[MarketDataSnapshot]:
        """Build MarketDataSnapshot objects from the most recent DB records."""
        if not self.db:
            return []
        from datetime import datetime as _dt
        snapshots: List[MarketDataSnapshot] = []
        for symbol in self.tracked_stocks:
            try:
                rows = self.db.get_recent_stock_data(symbol, limit=1)
                if not rows:
                    continue
                r = rows[0]
                ts = r.get("timestamp")
                if isinstance(ts, str):
                    try:
                        ts = _dt.fromisoformat(ts)
                    except Exception:
                        ts = _dt.utcnow()
                stock = StockData(
                    symbol=r.get("symbol", symbol),
                    company_name=r.get("company_name", symbol),
                    timestamp=ts or _dt.utcnow(),
                    price=r.get("price") or 0.0,
                    open_price=r.get("open_price") or 0.0,
                    high=r.get("high") or 0.0,
                    low=r.get("low") or 0.0,
                    close_price=r.get("close_price") or 0.0,
                    volume=r.get("volume") or 0,
                    change=r.get("change") or 0.0,
                    change_percent=r.get("change_percent") or 0.0,
                    source=r.get("source", "CACHED"),
                )
                snapshots.append(MarketDataSnapshot(
                    stock_data=stock,
                    bulk_block_deals=[],
                    institutional_activity=[],
                ))
            except Exception as exc:
                self.logger.warning(f"DB fallback failed for {symbol}: {exc}")
        return snapshots

    def stop_agents(self):
        for name, agent in self.agents.items():
            try:
                agent.stop()
                self.logger.info(f"Stopped {name}")
            except Exception as exc:
                self.logger.error(f"Error stopping {name}: {exc}")

    def get_status(self) -> Dict[str, Any]:
        return {name: agent.get_status() for name, agent in self.agents.items()}

    def get_db(self) -> DatabaseManager:
        return self.db
