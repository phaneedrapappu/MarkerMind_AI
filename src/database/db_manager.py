"""
Database Manager - SQLite database using SQLAlchemy ORM
Handles persistence for market data, analysis reports, signals, and news
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from datetime import date as date_type

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, Text, ForeignKey, JSON, func
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("MarketMindAI.Database")

Base = declarative_base()


# ─── ORM Models ──────────────────────────────────────────────────────────────

class StockDataRecord(Base):
    __tablename__ = "stock_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    company_name = Column(String(200))
    timestamp = Column(DateTime, nullable=False)
    price = Column(Float)
    open_price = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close_price = Column(Float)
    volume = Column(Integer)
    change = Column(Float)
    change_percent = Column(Float)
    source = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)


class BulkBlockDealRecord(Base):
    __tablename__ = "bulk_block_deals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    deal_type = Column(String(10))          # BULK or BLOCK
    client_name = Column(String(200))
    quantity = Column(Integer)
    price = Column(Float)
    transaction_type = Column(String(20))
    source = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)


class InstitutionalActivityRecord(Base):
    __tablename__ = "institutional_activity"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    institution_type = Column(String(10))   # FII or DII
    symbol = Column(String(20))             # None = market-wide
    buy_value = Column(Float)
    sell_value = Column(Float)
    net_value = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class AnalysisReportRecord(Base):
    __tablename__ = "analysis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    analysis_date = Column(DateTime, nullable=False)
    model_used = Column(String(50))
    raw_llm_response = Column(Text)
    overall_sentiment = Column(String(20))
    signal_strength = Column(Float)        # -1 to +1
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class TradingSignalRecord(Base):
    __tablename__ = "trading_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_date = Column(DateTime, nullable=False)
    signal_type = Column(String(10))        # BUY / SELL / HOLD
    confidence = Column(Float)
    risk_level = Column(String(10))
    target_price = Column(Float)
    stop_loss = Column(Float)
    supporting_factors = Column(Text)       # JSON list stored as text
    risk_factors = Column(Text)             # JSON list stored as text
    current_price = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class NewsRecord(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), index=True)  # None = general market
    title = Column(String(500))
    summary = Column(Text)
    url = Column(String(1000))
    source = Column(String(100))
    published_at = Column(DateTime)
    sentiment = Column(String(20))          # POSITIVE / NEGATIVE / NEUTRAL
    created_at = Column(DateTime, default=datetime.utcnow)


class AlertRecord(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), index=True)
    alert_type = Column(String(50))
    subject = Column(String(500))
    body = Column(Text)
    recipients = Column(Text)              # comma-separated email list
    sent_at = Column(DateTime)
    success = Column(Boolean, default=False)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Database Manager ─────────────────────────────────────────────────────────

class DatabaseManager:
    """Manages SQLite database operations"""

    def __init__(self, db_path: str = "data/marketmind.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False
        )
        self._SessionFactory = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        logger.info(f"Database initialised at {db_path}")

    def session(self) -> Session:
        return self._SessionFactory()

    # ── Stock Data ──────────────────────────────────────────────────────────

    def save_stock_data(self, stock_dict: Dict[str, Any]) -> int:
        """Upsert stock data – if a record for the same symbol exists from today, update it."""
        with self.session() as sess:
            today = datetime.utcnow().date()
            existing = (
                sess.query(StockDataRecord)
                .filter(
                    StockDataRecord.symbol == stock_dict.get("symbol", "").upper(),
                    func.date(StockDataRecord.timestamp) == today,
                )
                .order_by(StockDataRecord.timestamp.desc())
                .first()
            )
            if existing:
                for k, v in stock_dict.items():
                    setattr(existing, k, v)
                sess.commit()
                return existing.id
            record = StockDataRecord(**stock_dict)
            sess.add(record)
            sess.commit()
            return record.id

    def get_recent_stock_data(self, symbol: str, limit: int = 30) -> List[Dict]:
        with self.session() as sess:
            rows = (
                sess.query(StockDataRecord)
                .filter(StockDataRecord.symbol == symbol.upper())
                .order_by(StockDataRecord.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [self._to_dict(r) for r in rows]

    # ── Bulk/Block Deals ────────────────────────────────────────────────────

    def save_bulk_block_deals(self, records: List[Dict]) -> None:
        with self.session() as sess:
            for r in records:
                sess.add(BulkBlockDealRecord(**r))
            sess.commit()

    def get_bulk_block_deals(self, symbol: str, limit: int = 50) -> List[Dict]:
        with self.session() as sess:
            rows = (
                sess.query(BulkBlockDealRecord)
                .filter(BulkBlockDealRecord.symbol == symbol.upper())
                .order_by(BulkBlockDealRecord.date.desc())
                .limit(limit)
                .all()
            )
            return [self._to_dict(r) for r in rows]

    # ── Institutional Activity ──────────────────────────────────────────────

    def save_institutional_activity(self, records: List[Dict]) -> None:
        with self.session() as sess:
            for r in records:
                sess.add(InstitutionalActivityRecord(**r))
            sess.commit()

    # ── Analysis Reports ────────────────────────────────────────────────────

    def save_analysis_report(self, report_dict: Dict[str, Any]) -> int:
        """Upsert – update if a report for the same symbol already exists today."""
        with self.session() as sess:
            today = datetime.utcnow().date()
            existing = (
                sess.query(AnalysisReportRecord)
                .filter(
                    AnalysisReportRecord.symbol == report_dict.get("symbol", "").upper(),
                    func.date(AnalysisReportRecord.analysis_date) == today,
                )
                .first()
            )
            if existing:
                for k, v in report_dict.items():
                    setattr(existing, k, v)
                sess.commit()
                return existing.id
            record = AnalysisReportRecord(**report_dict)
            sess.add(record)
            sess.commit()
            return record.id

    def get_analysis_history(self, symbol: str, limit: int = 10) -> List[Dict]:
        with self.session() as sess:
            rows = (
                sess.query(AnalysisReportRecord)
                .filter(AnalysisReportRecord.symbol == symbol.upper())
                .order_by(AnalysisReportRecord.analysis_date.desc())
                .limit(limit)
                .all()
            )
            return [self._to_dict(r) for r in rows]

    # ── Trading Signals ─────────────────────────────────────────────────────

    def save_trading_signal(self, signal_dict: Dict[str, Any]) -> int:
        """Upsert – update if a signal for the same symbol already exists today."""
        with self.session() as sess:
            today = datetime.utcnow().date()
            existing = (
                sess.query(TradingSignalRecord)
                .filter(
                    TradingSignalRecord.symbol == signal_dict.get("symbol", "").upper(),
                    func.date(TradingSignalRecord.signal_date) == today,
                )
                .first()
            )
            if existing:
                for k, v in signal_dict.items():
                    setattr(existing, k, v)
                sess.commit()
                return existing.id
            record = TradingSignalRecord(**signal_dict)
            sess.add(record)
            sess.commit()
            return record.id

    def get_latest_signals(self, limit: int = 20) -> List[Dict]:
        """Return the single latest signal per symbol (no duplicates in UI)."""
        with self.session() as sess:
            # Subquery: latest signal_date per symbol
            subq = (
                sess.query(
                    TradingSignalRecord.symbol,
                    func.max(TradingSignalRecord.signal_date).label("max_date"),
                )
                .group_by(TradingSignalRecord.symbol)
                .subquery()
            )
            rows = (
                sess.query(TradingSignalRecord)
                .join(
                    subq,
                    (TradingSignalRecord.symbol == subq.c.symbol)
                    & (TradingSignalRecord.signal_date == subq.c.max_date),
                )
                .order_by(TradingSignalRecord.signal_date.desc())
                .limit(limit)
                .all()
            )
            return [self._to_dict(r) for r in rows]

    def get_signals_for_symbol(self, symbol: str, limit: int = 10) -> List[Dict]:
        with self.session() as sess:
            rows = (
                sess.query(TradingSignalRecord)
                .filter(TradingSignalRecord.symbol == symbol.upper())
                .order_by(TradingSignalRecord.signal_date.desc())
                .limit(limit)
                .all()
            )
            return [self._to_dict(r) for r in rows]

    # ── News ────────────────────────────────────────────────────────────────

    def save_news(self, records: List[Dict]) -> None:
        """Insert news articles – skip duplicates by URL."""
        with self.session() as sess:
            # Build set of already-stored URLs to avoid duplicates
            existing_urls = {
                row[0] for row in sess.query(NewsRecord.url).filter(
                    NewsRecord.url.isnot(None)
                ).all()
            }
            new_records = [
                NewsRecord(**r) for r in records
                if r.get("url") not in existing_urls
            ]
            if new_records:
                sess.add_all(new_records)
                sess.commit()

    def get_news(self, symbol: Optional[str] = None, limit: int = 20) -> List[Dict]:
        with self.session() as sess:
            q = sess.query(NewsRecord)
            if symbol:
                q = q.filter(NewsRecord.symbol == symbol.upper())
            rows = q.order_by(NewsRecord.published_at.desc()).limit(limit).all()
            return [self._to_dict(r) for r in rows]

    # ── Alerts ──────────────────────────────────────────────────────────────

    def save_alert(self, alert_dict: Dict[str, Any]) -> int:
        with self.session() as sess:
            record = AlertRecord(**alert_dict)
            sess.add(record)
            sess.commit()
            return record.id

    def get_recent_alerts(self, limit: int = 20) -> List[Dict]:
        with self.session() as sess:
            rows = (
                sess.query(AlertRecord)
                .order_by(AlertRecord.created_at.desc())
                .limit(limit)
                .all()
            )
            return [self._to_dict(r) for r in rows]

    # ── Dashboard summary ───────────────────────────────────────────────────

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Return counts and today's fresh data for dashboard display."""
        with self.session() as sess:
            today = datetime.utcnow().date()
            return {
                "total_stocks_tracked": sess.query(StockDataRecord.symbol).distinct().count(),
                # Count distinct symbols with a signal today (not all-time rows)
                "total_signals": (
                    sess.query(TradingSignalRecord.symbol).distinct()
                    .filter(func.date(TradingSignalRecord.signal_date) == today)
                    .count()
                ),
                # Count unique news articles (by URL)
                "total_news": (
                    sess.query(func.count(func.distinct(NewsRecord.url)))
                    .scalar() or 0
                ),
                "total_alerts_sent": (
                    sess.query(AlertRecord)
                    .filter(AlertRecord.success == True)
                    .count()
                ),
                "latest_signals": self.get_latest_signals(5),
                "latest_news": self.get_news(limit=5),
            }

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _to_dict(obj) -> Dict[str, Any]:
        result = {}
        for col in obj.__table__.columns:
            val = getattr(obj, col.name)
            if isinstance(val, datetime):
                val = val.isoformat()
            result[col.name] = val
        return result
