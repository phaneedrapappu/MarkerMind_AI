"""
Database Manager - SQLite database using SQLAlchemy ORM
Handles persistence for market data, analysis reports, signals, and news
"""
import json
import logging
import secrets
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


class SubscriberRecord(Base):
    """Email subscribers who receive 2x/day automated digests."""
    __tablename__ = "subscribers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(200), nullable=False, unique=True, index=True)
    stocks = Column(Text)                  # JSON list e.g. '["TCS","INFY"]'
    is_active = Column(Boolean, default=True)
    subscribed_at = Column(DateTime, default=datetime.utcnow)
    last_sent_at = Column(DateTime)
    unsubscribe_token = Column(String(64), default=lambda: secrets.token_urlsafe(32))
    created_at = Column(DateTime, default=datetime.utcnow)


class UserRecord(Base):
    """Registered users for the web dashboard (Phase 2 auth)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), nullable=False, unique=True, index=True)
    email = Column(String(200), nullable=False, unique=True, index=True)
    password_hash = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    telegram_chat_id = Column(String(50))       # set automatically via bot deep-link flow
    telegram_bot_token = Column(String(200))     # legacy; unused — kept for migration safety
    telegram_alerts = Column(Boolean, default=False)
    telegram_link_token = Column(String(64))     # one-time token for bot-subscribe deep-link
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime)


class PortfolioRecord(Base):
    """Tracks user portfolio positions."""
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    quantity = Column(Float, default=0)
    avg_buy_price = Column(Float, nullable=False)
    buy_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    is_open = Column(Boolean, default=True)     # False = position closed
    sell_price = Column(Float)
    sell_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WatchlistRecord(Base):
    """Per-user watchlist (separate from portfolio)."""
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)


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
        self._run_migrations()
        logger.info(f"Database initialised at {db_path}")

    def _run_migrations(self) -> None:
        """
        Lightweight additive migrations: add any columns declared in the ORM
        models that are missing from the live SQLite tables.  Only ADD COLUMN
        is needed (SQLite does not support DROP/ALTER).
        """
        import sqlalchemy as _sa
        inspector = _sa.inspect(self.engine)
        with self.engine.connect() as conn:
            for table in Base.metadata.sorted_tables:
                if not inspector.has_table(table.name):
                    continue  # create_all already handled new tables
                existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
                for col in table.columns:
                    if col.name not in existing_cols:
                        col_type = col.type.compile(dialect=self.engine.dialect)
                        nullable = "" if col.nullable else " NOT NULL"
                        default_clause = ""
                        if col.default is not None and col.default.is_scalar:
                            raw = col.default.arg
                            if isinstance(raw, bool):
                                default_clause = f" DEFAULT {int(raw)}"
                            elif isinstance(raw, (int, float)):
                                default_clause = f" DEFAULT {raw}"
                            elif isinstance(raw, str):
                                escaped = raw.replace("'", "''")
                                default_clause = f" DEFAULT '{escaped}'"
                        ddl = (
                            f'ALTER TABLE "{table.name}" '
                            f'ADD COLUMN "{col.name}" {col_type}{default_clause}'
                        )
                        try:
                            conn.execute(_sa.text(ddl))
                            conn.commit()
                            logger.info(f"Migration: added column {table.name}.{col.name}")
                        except Exception as exc:
                            logger.warning(
                                f"Migration skipped for {table.name}.{col.name}: {exc}"
                            )

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

    # ── Subscribers ─────────────────────────────────────────────────────────

    def save_subscriber(self, email: str, stocks: List[str]) -> Dict[str, Any]:
        """Upsert subscriber. Returns the record dict plus an 'is_new' boolean."""
        with self.session() as sess:
            existing = sess.query(SubscriberRecord).filter_by(email=email).first()
            if existing:
                existing.stocks = json.dumps(stocks)
                existing.is_active = True
                sess.commit()
                result = self._to_dict(existing)
                result["is_new"] = False
                return result
            record = SubscriberRecord(
                email=email,
                stocks=json.dumps(stocks),
                is_active=True,
                unsubscribe_token=secrets.token_urlsafe(32),
            )
            sess.add(record)
            sess.commit()
            result = self._to_dict(record)
            result["is_new"] = True
            return result

    def get_active_subscribers(self) -> List[Dict[str, Any]]:
        with self.session() as sess:
            rows = (
                sess.query(SubscriberRecord)
                .filter(SubscriberRecord.is_active == True)
                .order_by(SubscriberRecord.subscribed_at.desc())
                .all()
            )
            result = []
            for r in rows:
                d = self._to_dict(r)
                try:
                    d["stocks"] = json.loads(d["stocks"] or "[]")
                except Exception:
                    d["stocks"] = []
                result.append(d)
            return result

    def deactivate_subscriber(self, token: str) -> bool:
        """Unsubscribe via token. Returns True if found and deactivated."""
        with self.session() as sess:
            record = sess.query(SubscriberRecord).filter_by(unsubscribe_token=token).first()
            if record:
                record.is_active = False
                sess.commit()
                return True
            return False

    def update_subscriber_sent(self, email: str) -> None:
        with self.session() as sess:
            record = sess.query(SubscriberRecord).filter_by(email=email).first()
            if record:
                record.last_sent_at = datetime.utcnow()
                sess.commit()

    def get_subscribers_count(self) -> int:
        with self.session() as sess:
            return sess.query(SubscriberRecord).filter(SubscriberRecord.is_active == True).count()

    # ── Global News ──────────────────────────────────────────────────────────

    def get_global_news(self, limit: int = 30) -> List[Dict]:
        """Return world/global market news (tagged __GLOBAL__ by NewsAgent)."""
        with self.session() as sess:
            rows = (
                sess.query(NewsRecord)
                .filter(NewsRecord.symbol == "__GLOBAL__")
                .order_by(NewsRecord.published_at.desc())
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
                "total_subscribers": (
                    sess.query(SubscriberRecord)
                    .filter(SubscriberRecord.is_active == True)
                    .count()
                ),
                "latest_signals": self.get_latest_signals(5),
                "latest_news": self.get_news(limit=5),
            }

    # ── Helpers ─────────────────────────────────────────────────────────────

    # Fields that must never be serialised into dicts returned to callers.
    _SENSITIVE_COLS = frozenset({"password_hash", "telegram_bot_token", "telegram_link_token", "unsubscribe_token"})

    @staticmethod
    def _to_dict(obj) -> Dict[str, Any]:
        result = {}
        for col in obj.__table__.columns:
            if col.name in DatabaseManager._SENSITIVE_COLS:
                continue   # never expose secrets via serialisation
            val = getattr(obj, col.name)
            if isinstance(val, datetime):
                val = val.isoformat()
            result[col.name] = val
        return result

    # ── User Auth ──────────────────────────────────────────────────────────

    def create_user(self, username: str, email: str, password_hash: str) -> Dict[str, Any]:
        with self.session() as sess:
            existing = sess.query(UserRecord).filter(
                (UserRecord.email == email) | (UserRecord.username == username)
            ).first()
            if existing:
                return {"error": "email_or_username_taken"}
            user = UserRecord(username=username, email=email, password_hash=password_hash)
            sess.add(user)
            sess.commit()
            sess.refresh(user)
            return self._to_dict(user)

    def create_user_with_password(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """
        Hash the password internally and create the user record.
        Keeps bcrypt out of the view/route layer so the plaintext password
        and resulting hash never propagate beyond the DB layer.
        """
        import bcrypt as _bcrypt
        ph = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
        return self.create_user(username, email, ph)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with self.session() as sess:
            u = sess.query(UserRecord).filter_by(email=email, is_active=True).first()
            return self._to_dict(u) if u else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self.session() as sess:
            u = sess.query(UserRecord).filter_by(id=user_id, is_active=True).first()
            return self._to_dict(u) if u else None

    def verify_user_password(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Check email + password against the stored bcrypt hash.
        Password verification is done here so the hash never leaves the DB layer.
        Returns the safe user dict (no password_hash) on success, None on failure.
        """
        import bcrypt as _bcrypt
        with self.session() as sess:
            u = sess.query(UserRecord).filter_by(email=email, is_active=True).first()
            if not u:
                return None
            try:
                match = _bcrypt.checkpw(password.encode(), u.password_hash.encode())
            except Exception:
                return None
            return self._to_dict(u) if match else None

    def update_user_login(self, user_id: int) -> None:
        with self.session() as sess:
            u = sess.query(UserRecord).filter_by(id=user_id).first()
            if u:
                u.last_login_at = datetime.utcnow()
                sess.commit()

    def update_user_telegram(self, user_id: int, chat_id: str, enabled: bool) -> None:
        with self.session() as sess:
            u = sess.query(UserRecord).filter_by(id=user_id).first()
            if u:
                u.telegram_chat_id = chat_id
                u.telegram_alerts = enabled
                sess.commit()

    def get_user_telegram(self, user_id: int) -> dict:
        """Return Telegram config for a user (chat_id + enabled flag only)."""
        with self.session() as sess:
            u = sess.query(UserRecord).filter_by(id=user_id).first()
            if not u:
                return {}
            return {
                "chat_id": u.telegram_chat_id or "",
                "enabled": bool(u.telegram_alerts),
                "linked": bool(u.telegram_chat_id),
            }

    def generate_telegram_link_token(self, user_id: int) -> str:
        """Create a one-time token used in the bot deep-link subscribe flow."""
        import uuid
        token = uuid.uuid4().hex
        with self.session() as sess:
            u = sess.query(UserRecord).filter_by(id=user_id).first()
            if u:
                u.telegram_link_token = token
                sess.commit()
        return token

    def link_telegram_by_token(self, token: str, chat_id: str) -> bool:
        """
        Called from the webhook when a user sends /start <token> to the bot.
        Finds the matching user, saves their chat_id, clears the token.
        Returns True on success, False if token not found / already used.
        """
        with self.session() as sess:
            u = sess.query(UserRecord).filter_by(telegram_link_token=token).first()
            if not u:
                return False
            u.telegram_chat_id = chat_id
            u.telegram_alerts = True
            u.telegram_link_token = None   # consume the token
            sess.commit()
        return True

    def unlink_telegram(self, user_id: int) -> None:
        """Remove Telegram association for a user."""
        with self.session() as sess:
            u = sess.query(UserRecord).filter_by(id=user_id).first()
            if u:
                u.telegram_chat_id = None
                u.telegram_alerts = False
                u.telegram_link_token = None
                sess.commit()

    # ── Portfolio ─────────────────────────────────────────────────────────

    def add_position(self, user_id: int, symbol: str, quantity: float,
                     avg_buy_price: float, notes: str = "") -> Dict[str, Any]:
        with self.session() as sess:
            pos = PortfolioRecord(
                user_id=user_id, symbol=symbol.upper(),
                quantity=quantity, avg_buy_price=avg_buy_price, notes=notes,
            )
            sess.add(pos)
            sess.commit()
            sess.refresh(pos)
            return self._to_dict(pos)

    def get_portfolio(self, user_id: int) -> List[Dict[str, Any]]:
        with self.session() as sess:
            rows = (
                sess.query(PortfolioRecord)
                .filter_by(user_id=user_id, is_open=True)
                .order_by(PortfolioRecord.buy_date.desc())
                .all()
            )
            return [self._to_dict(r) for r in rows]

    def get_portfolio_history(self, user_id: int) -> List[Dict[str, Any]]:
        """All positions (open + closed) for backtesting / P&L."""
        with self.session() as sess:
            rows = (
                sess.query(PortfolioRecord)
                .filter_by(user_id=user_id)
                .order_by(PortfolioRecord.buy_date.desc())
                .all()
            )
            return [self._to_dict(r) for r in rows]

    def close_position(self, position_id: int, sell_price: float) -> Dict[str, Any]:
        with self.session() as sess:
            pos = sess.query(PortfolioRecord).filter_by(id=position_id).first()
            if not pos:
                return {"error": "not_found"}
            pos.is_open = False
            pos.sell_price = sell_price
            pos.sell_date = datetime.utcnow()
            sess.commit()
            return self._to_dict(pos)

    def delete_position(self, position_id: int, user_id: int) -> bool:
        with self.session() as sess:
            pos = sess.query(PortfolioRecord).filter_by(
                id=position_id, user_id=user_id
            ).first()
            if not pos:
                return False
            sess.delete(pos)
            sess.commit()
            return True

    # ── Watchlist ─────────────────────────────────────────────────────────

    def get_watchlist(self, user_id: int) -> List[str]:
        with self.session() as sess:
            rows = sess.query(WatchlistRecord).filter_by(user_id=user_id).all()
            return [r.symbol for r in rows]

    def toggle_watchlist(self, user_id: int, symbol: str) -> bool:
        """Returns True if added, False if removed."""
        sym = symbol.upper()
        with self.session() as sess:
            existing = sess.query(WatchlistRecord).filter_by(
                user_id=user_id, symbol=sym
            ).first()
            if existing:
                sess.delete(existing)
                sess.commit()
                return False
            sess.add(WatchlistRecord(user_id=user_id, symbol=sym))
            sess.commit()
            return True

    # ── Backtesting data ──────────────────────────────────────────────────

    def get_all_signals_for_backtest(self, symbol: str = None) -> List[Dict]:
        """Return all signals sorted by date (oldest first) for P&L simulation."""
        with self.session() as sess:
            q = sess.query(TradingSignalRecord)
            if symbol:
                q = q.filter(TradingSignalRecord.symbol == symbol.upper())
            rows = q.order_by(TradingSignalRecord.signal_date.asc()).all()
            return [self._to_dict(r) for r in rows]

    def get_price_at_date(self, symbol: str, date_str: str) -> Optional[float]:
        """Get closest stored price for a symbol near a given date string."""
        with self.session() as sess:
            from sqlalchemy import func as sqlfunc
            row = (
                sess.query(StockDataRecord)
                .filter(StockDataRecord.symbol == symbol.upper())
                .order_by(
                    sqlfunc.abs(
                        sqlfunc.julianday(StockDataRecord.timestamp)
                        - sqlfunc.julianday(date_str)
                    )
                )
                .first()
            )
            return row.price if row else None
