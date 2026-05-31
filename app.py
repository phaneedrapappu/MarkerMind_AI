"""
MarketMind AI – Flask Web Dashboard
Provides a browser-based UI backed by the SQLite database.

Endpoints:
  GET  /                     – Dashboard (signals + news summary)
  GET  /stock/<symbol>       – Stock detail page
  GET  /alerts               – Alert history
  GET  /subscribe            – Subscription sign-up page
  GET  /unsubscribe?token=…  – One-click unsubscribe
  GET  /api/signals          – JSON: latest trading signals
  GET  /api/news             – JSON: latest news (Indian market)
  GET  /api/news/global      – JSON: world/global market news
  GET  /api/summary          – JSON: dashboard KPI summary
  POST /api/run              – Trigger a pipeline run (background thread)
  POST /api/subscribe        – Subscribe email + stock list
  POST /api/unsubscribe      – Unsubscribe by token
  GET  /api/stocks           – Hardcoded NSE catalog (fast)
  GET  /api/stocks/live      – Dynamic NSE equity list (live CSV)
"""
import json
import os
import sys
import threading
from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo

import hashlib
import hmac
import requests as http_requests

from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from flask_cors import CORS
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user,
)
from dotenv import load_dotenv

# Ensure project root is on the path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv()

from src.database.db_manager import DatabaseManager
from src.orchestrator import AgentOrchestrator
from src.stock_discovery import get_catalog_grouped, search_stocks, fetch_all_nse_stocks
from src.email_utils import send_welcome_email, send_update_email, send_unsubscribe_lookup_email
from src.technical.indicators import get_indicators
from src.telegram_utils import send_pipeline_alerts

try:
    import holidays as pyholidays
except Exception:
    pyholidays = None

# Same catalog as main.py so the dashboard can offer stock discovery
_NSE_STOCK_CATALOG = {
    "IT": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTIM", "MPHASIS", "COFORGE", "PERSISTENT", "OFSS"],
    "Banking": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "INDUSINDBK", "BANDHANBNK", "FEDERALBNK", "IDFCFIRSTB", "PNB"],
    "Finance": ["BAJFINANCE", "BAJAJFINSV", "CHOLAFIN", "MUTHOOTFIN", "MANAPPURAM", "LICHSGFIN", "RECLTD", "PFC"],
    "Auto": ["MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "HEROMOTOCO", "EICHERMOT", "TVSMOTOR", "ASHOKLEY"],
    "Pharma": ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "AUROPHARMA", "TORNTPHARM", "ALKEM", "BIOCON"],
    "FMCG": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR", "MARICO", "COLPAL", "GODREJCP"],
    "Energy": ["RELIANCE", "ONGC", "NTPC", "POWERGRID", "ADANIGREEN", "TATAPOWER", "ADANIPORTS", "COALINDIA"],
    "Retail/Consumer": ["DMART", "TITAN", "TRENT", "NYKAA", "ZOMATO", "PAYTM", "NAUKRI", "IRCTC"],
    "Metals": ["TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "SAIL", "NMDC", "NATIONALUM"],
    "Infra/Cement": ["ULTRACEMCO", "GRASIM", "AMBUJACEM", "ACC", "SHREECEM", "DALMIACEMX", "LT", "SIEMENS"],
}

app = Flask(__name__, template_folder="frontend/templates", static_folder="frontend/static")
_flask_secret = os.getenv("FLASK_SECRET_KEY", "")
if not _flask_secret:
    import warnings
    warnings.warn(
        "FLASK_SECRET_KEY is not set — using an insecure temporary key. "
        "Set FLASK_SECRET_KEY in your .env file before any real deployment.",
        stacklevel=2,
    )
    import secrets as _secrets_mod
    _flask_secret = _secrets_mod.token_hex(32)   # random per-process; sessions lost on restart
app.secret_key = _flask_secret
CORS(app)

# ── Flask-Login ────────────────────────────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"

@login_manager.unauthorized_handler
def _unauthorized():
    """Return JSON 401 for API requests; redirect to login for browser pages."""
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not logged in", "redirect": "/login"}), 401
    return redirect(url_for(login_manager.login_view, next=request.url))


class _FlaskUser(UserMixin):
    """Thin wrapper so Flask-Login is happy."""
    def __init__(self, user_dict: dict):
        self._d = user_dict

    @property
    def id(self):
        return str(self._d["id"])

    def __getattr__(self, item):
        return self._d.get(item)


@login_manager.user_loader
def load_user(user_id: str):
    db = get_db()
    data = db.get_user_by_id(int(user_id))
    return _FlaskUser(data) if data else None

CONFIG_PATH = str(ROOT / "config" / "config.yaml")
_db: DatabaseManager = None
_pipeline_lock = threading.Lock()
_pipeline_running = False
_last_pipeline_result: dict = {}
_news_fetch_lock = threading.Lock()
_news_fetching = False
_market_fetch_lock = threading.Lock()
_market_fetching = False


def _fetch_news_standalone():
    """Run only the NewsAgent in a background thread to populate news without a full pipeline."""
    global _news_fetching
    if not _news_fetch_lock.acquire(blocking=False):
        return  # already running
    _news_fetching = True
    try:
        import yaml
        from src.agents.news_agent import NewsAgent
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        agent_cfgs = cfg.get("agents", {})
        stocks = agent_cfgs.get("market_data_agent", {}).get("stocks", [])
        news_cfg = agent_cfgs.get("news_agent", {})
        news_cfg.setdefault("stocks", stocks)
        db = get_db()
        agent = NewsAgent(news_cfg, db_manager=db)
        if agent.initialize():
            agent.execute()
    except Exception as exc:
        app.logger.warning(f"Standalone news fetch error: {exc}")
    finally:
        _news_fetching = False
        _news_fetch_lock.release()


def _fetch_market_data_standalone():
    """Run only the MarketDataAgent in a background thread to populate stock prices."""
    global _market_fetching
    if not _market_fetch_lock.acquire(blocking=False):
        return  # already running
    _market_fetching = True
    try:
        import yaml
        from src.agents.market_data_agent import MarketDataAgent
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        agent_cfgs = cfg.get("agents", {})
        mda_cfg = agent_cfgs.get("market_data_agent", {})
        db = get_db()
        agent = MarketDataAgent(mda_cfg, db_manager=db)
        if agent.initialize():
            agent.execute()
    except Exception as exc:
        app.logger.warning(f"Standalone market data fetch error: {exc}")
    finally:
        _market_fetching = False
        _market_fetch_lock.release()

_IST = ZoneInfo("Asia/Kolkata")
_NSE_OPEN = time(9, 15)
_NSE_CLOSE = time(15, 30)


def get_db() -> DatabaseManager:
    global _db
    if _db is None:
        import yaml
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        db_path = cfg.get("database", {}).get("path", "data/marketmind.db")
        _db = DatabaseManager(db_path)
    return _db


def _public_holiday_name(day):
    """Return India public holiday name for the given date, if available."""
    if pyholidays is None:
        return None
    try:
        holiday_map = pyholidays.India(years=[day.year])
        return holiday_map.get(day)
    except Exception:
        return None


def _next_market_open(now_ist, max_days=14):
    """Find the next market opening datetime in IST."""
    # Same day, before opening bell
    if now_ist.weekday() < 5 and not _public_holiday_name(now_ist.date()) and now_ist.time() < _NSE_OPEN:
        return now_ist.replace(hour=_NSE_OPEN.hour, minute=_NSE_OPEN.minute, second=0, microsecond=0)

    start_day = now_ist.date() + timedelta(days=1)
    for offset in range(max_days):
        day = start_day + timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        if _public_holiday_name(day):
            continue
        return datetime.combine(day, _NSE_OPEN, tzinfo=_IST)
    return None


def get_market_status(now_ist=None):
    """Return current NSE market status with holiday/closure context."""
    now_ist = now_ist or datetime.now(_IST)
    day = now_ist.date()
    reason = None
    is_holiday = False

    public_holiday = _public_holiday_name(day)
    if now_ist.weekday() >= 5:
        is_open = False
        is_holiday = True
        reason = "Weekend"
    elif public_holiday:
        is_open = False
        is_holiday = True
        reason = f"Public holiday: {public_holiday}"
    elif now_ist.time() < _NSE_OPEN:
        is_open = False
        reason = "Pre-market"
    elif now_ist.time() > _NSE_CLOSE:
        is_open = False
        reason = "Post-market"
    else:
        is_open = True
        reason = "Regular market hours"

    next_open_dt = _next_market_open(now_ist)
    next_open_human = next_open_dt.strftime("%a, %d %b %Y · %I:%M %p IST") if next_open_dt else None

    return {
        "is_open": is_open,
        "is_holiday": is_holiday,
        "reason": reason,
        "timestamp_ist": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "next_open": next_open_dt.isoformat() if next_open_dt else None,
        "next_open_human": next_open_human,
    }


@app.context_processor
def inject_market_status():
    return {"market_status": get_market_status()}


# ── Live news fallback (used when DB is empty on first run) ───────────────────
def _fetch_live_news_and_save(db: "DatabaseManager") -> list:
    """
    Fetch fresh news directly from RSS feeds without running the full pipeline.
    Saves results to DB so subsequent calls are instant.
    Called automatically when the DB has no news yet.
    """
    import re
    import feedparser
    from datetime import timedelta

    ET_MARKETS_RSS = "https://economictimes.indiatimes.com/markets/rss.cms"
    MONEYCONTROL_RSS = "https://www.moneycontrol.com/rssfeeds/marketsnews.xml"
    LIVE_FEEDS = [
        (ET_MARKETS_RSS, None),
        (MONEYCONTROL_RSS, None),
    ]

    POSITIVE_KW = ["rally","surge","gain","bull","profit","growth","strong","beat","upgrade","buy","outperform","record high"]
    NEGATIVE_KW = ["fall","drop","crash","bear","loss","weak","miss","downgrade","sell","underperform","record low","breakdown"]

    def _sentiment(text):
        t = text.lower()
        p = sum(1 for k in POSITIVE_KW if k in t)
        n = sum(1 for k in NEGATIVE_KW if k in t)
        return "POSITIVE" if p > n else "NEGATIVE" if n > p else "NEUTRAL"

    articles = []
    seen_urls = set()
    cutoff = datetime.now() - timedelta(hours=48)

    for url, symbol in LIVE_FEEDS:
        try:
            feed = feedparser.parse(url)
            source = getattr(feed.feed, "title", url.split("/")[2])
            for entry in feed.entries[:15]:
                link = getattr(entry, "link", "")
                if not link or link in seen_urls:
                    continue
                pub = datetime.now()
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        pub = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass
                if pub < cutoff:
                    continue
                title = getattr(entry, "title", "").strip()
                summary = re.sub(r"<[^>]+>", " ", getattr(entry, "summary", "") or "").strip()
                articles.append({
                    "symbol": symbol,
                    "title": title[:499],
                    "summary": summary[:2000],
                    "url": link[:999],
                    "source": source[:99],
                    "published_at": pub,
                    "sentiment": _sentiment(f"{title} {summary}"),
                })
                seen_urls.add(link)
        except Exception as e:
            app.logger.warning(f"Live news fallback feed error ({url}): {e}")

    if articles:
        try:
            db.save_news(articles)
        except Exception as e:
            app.logger.warning(f"Live news fallback save error: {e}")

    return articles


def _fetch_live_global_news_and_save(db: "DatabaseManager") -> list:
    """
    Fetch global market news from RSS on first run when DB is empty.
    """
    import re
    import feedparser
    from datetime import timedelta

    GLOBAL_SYMBOL = "__GLOBAL__"
    GLOBAL_FEEDS = [
        ("https://news.google.com/rss/search?q=India+stock+market+NSE&hl=en-IN&gl=IN&ceid=IN:en", GLOBAL_SYMBOL),
        ("https://news.google.com/rss/search?q=crude+oil+price+India&hl=en-IN&gl=IN&ceid=IN:en", GLOBAL_SYMBOL),
        ("https://news.google.com/rss/search?q=USD+INR+exchange+rate&hl=en-IN&gl=IN&ceid=IN:en", GLOBAL_SYMBOL),
    ]

    POSITIVE_KW = ["rally","surge","gain","bull","profit","growth","strong","beat"]
    NEGATIVE_KW = ["fall","drop","crash","bear","loss","weak","miss","downgrade"]

    def _sentiment(text):
        t = text.lower()
        p = sum(1 for k in POSITIVE_KW if k in t)
        n = sum(1 for k in NEGATIVE_KW if k in t)
        return "POSITIVE" if p > n else "NEGATIVE" if n > p else "NEUTRAL"

    articles = []
    seen_urls = set()
    cutoff = datetime.now() - timedelta(hours=48)

    for url, symbol in GLOBAL_FEEDS:
        try:
            feed = feedparser.parse(url)
            source = getattr(feed.feed, "title", url.split("/")[2])
            for entry in feed.entries[:10]:
                link = getattr(entry, "link", "")
                if not link or link in seen_urls:
                    continue
                pub = datetime.now()
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        pub = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass
                if pub < cutoff:
                    continue
                title = getattr(entry, "title", "").strip()
                summary = re.sub(r"<[^>]+>", " ", getattr(entry, "summary", "") or "").strip()
                articles.append({
                    "symbol": symbol,
                    "title": title[:499],
                    "summary": summary[:2000],
                    "url": link[:999],
                    "source": source[:99],
                    "published_at": pub,
                    "sentiment": _sentiment(f"{title} {summary}"),
                })
                seen_urls.add(link)
        except Exception as e:
            app.logger.warning(f"Live global news fallback error ({url}): {e}")

    if articles:
        try:
            db.save_news(articles)
        except Exception as e:
            app.logger.warning(f"Live global news fallback save error: {e}")

    return articles


# ── Pages ──────────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    db = get_db()
    summary = db.get_dashboard_summary()
    signals = db.get_latest_signals(10)
    signals_all = db.get_latest_signals(100)
    news = db.get_news(limit=10)
    # Auto-fetch live news on first run so dashboard isn't empty
    if not news:
        news = _fetch_live_news_and_save(db)[:10]
    alerts = db.get_recent_alerts(5)
    # Auto-fetch in the background if DB has no data yet
    if not news:
        threading.Thread(target=_fetch_news_standalone, daemon=True).start()
    if not summary["total_stocks_tracked"]:
        threading.Thread(target=_fetch_market_data_standalone, daemon=True).start()
    return render_template(
        "dashboard.html",
        summary=summary,
        signals=signals,
        signals_all=signals_all,
        news=news,
        alerts=alerts,
        now=datetime.now().strftime("%d %b %Y, %I:%M %p"),
    )


@app.route("/stock/<symbol>")
def stock_detail(symbol: str):
    symbol = symbol.upper()
    db = get_db()
    history = db.get_recent_stock_data(symbol, limit=30)
    signals = db.get_signals_for_symbol(symbol, limit=10)
    news = db.get_news(symbol=symbol, limit=10)
    analysis = db.get_analysis_history(symbol, limit=5)
    bulk_deals = db.get_bulk_block_deals(symbol, limit=20)

    # Latest chart paths (PNG files)
    report_dir = ROOT / "data" / "reports"
    charts = sorted(report_dir.glob(f"{symbol}_*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    chart_names = [c.name for c in charts[:6]]  # Show last 6 charts

    return render_template(
        "stock_detail.html",
        symbol=symbol,
        history=history,
        signals=signals,
        news=news,
        analysis=analysis,
        bulk_deals=bulk_deals,
        chart_names=chart_names,
    )


@app.route("/alerts")
def alerts_page():
    db = get_db()
    alerts = db.get_recent_alerts(50)
    return render_template("alerts.html", alerts=alerts)


# ── REST API ───────────────────────────────────────────────────────────────────

@app.route("/api/signals")
def api_signals():
    limit = int(request.args.get("limit", 20))
    symbol = request.args.get("symbol")
    db = get_db()
    if symbol:
        data = db.get_signals_for_symbol(symbol.upper(), limit=limit)
    else:
        data = db.get_latest_signals(limit=limit)
    return jsonify(data)


@app.route("/api/news")
def api_news():
    limit = int(request.args.get("limit", 20))
    symbol = request.args.get("symbol")
    db = get_db()
    data = db.get_news(symbol=symbol.upper() if symbol else None, limit=limit)
    # Auto-fetch live from RSS on first run when DB has no news
    if not data and not symbol:
        data = _fetch_live_news_and_save(db)[:limit]
    return jsonify(data)


@app.route("/api/stock/<symbol>/history")
def api_stock_history(symbol: str):
    limit = int(request.args.get("limit", 30))
    db = get_db()
    data = db.get_recent_stock_data(symbol.upper(), limit=limit)
    return jsonify(data)


@app.route("/api/summary")
def api_summary():
    db = get_db()
    return jsonify(db.get_dashboard_summary())


@app.route("/api/alerts")
def api_alerts():
    limit = int(request.args.get("limit", 20))
    db = get_db()
    return jsonify(db.get_recent_alerts(limit))


@app.route("/api/run", methods=["POST"])
@login_required
def api_run_pipeline():
    """
    Trigger a full pipeline run in a background thread.
    Requires an authenticated session to prevent unauthenticated pipeline abuse.
    Optional JSON body:
      {
        "stocks": ["TCS", "INFY"],          // override tracked stocks
        "email":  ["you@gmail.com"]          // override recipients
      }
    """
    global _pipeline_running
    if not _pipeline_lock.acquire(blocking=False):
        return jsonify({"status": "already_running"}), 409

    _pipeline_running = True

    # Parse optional overrides from request body
    body = request.get_json(silent=True) or {}
    overrides = {}
    if body.get("stocks"):
        if isinstance(body["stocks"], str):
            overrides["stocks"] = [s.strip().upper() for s in body["stocks"].split(",") if s.strip()]
        else:
            overrides["stocks"] = [s.strip().upper() for s in body["stocks"] if s.strip()]
    # Email — if supplied use those; if omitted, fall back to all active DB subscribers
    if body.get("email"):
        if isinstance(body["email"], str):
            overrides["recipients"] = [e.strip() for e in body["email"].split(",") if e.strip()]
        else:
            overrides["recipients"] = [e.strip() for e in body["email"] if e.strip()]
    else:
        # Auto-include every active subscriber so manual runs also trigger delivery
        try:
            _db_for_subs = get_db()
            active_subs = _db_for_subs.get_active_subscribers()
            sub_emails = [s["email"] for s in active_subs if s.get("email")]
            if sub_emails:
                overrides["recipients"] = sub_emails
                app.logger.info(f"[Run] Auto-adding {len(sub_emails)} DB subscriber(s) as recipients")
        except Exception as _sub_exc:
            app.logger.warning(f"[Run] Could not fetch subscribers: {_sub_exc}")

    # Always pass the current host URL so unsubscribe links work outside localhost
    overrides["app_url"] = request.host_url.rstrip("/")

    # Capture the explicit stocks chosen in the modal for use in Telegram alerts
    explicit_stocks = list(overrides.get("stocks", []))

    def _run():
        global _pipeline_running, _last_pipeline_result
        try:
            orch = AgentOrchestrator(CONFIG_PATH)
            orch.apply_overrides(overrides)
            orch.initialize_agents()
            pipeline_result = orch.run_agents()
            orch.stop_agents()
            # Store result for frontend polling
            email_res = pipeline_result.get("email_alert_agent", {})
            _last_pipeline_result = {
                "signals": pipeline_result.get("signal_generator_agent", {}).get("signal_count", 0),
                "email_status": email_res.get("status", "not_run"),
                "email_sent_to": email_res.get("recipients", []),
                "email_reason": email_res.get("reason", ""),
                "email_error": email_res.get("error", ""),
            }
            if email_res.get("status") == "error":
                app.logger.error(f"[Run] Email send failed: {email_res.get('error')}")
            elif email_res.get("status") == "skipped":
                app.logger.warning(f"[Run] Email skipped: {email_res.get('reason')}")
            else:
                app.logger.info(f"[Run] Email sent to: {email_res.get('recipients', [])}")
            # Send Telegram alerts.
            # For manual runs, pass the explicit stock list so every subscribed
            # user gets alerts for what they chose — regardless of watchlist.
            # (Watchlist filter only applies to scheduled/automated runs.)
            try:
                db = get_db()
                signals = db.get_latest_signals(limit=50)
                send_pipeline_alerts(db, signals, explicit_symbols=explicit_stocks or None)
            except Exception as tg_exc:
                app.logger.warning(f"Telegram alert error: {tg_exc}")
        except Exception as run_exc:
            app.logger.error(f"[Run] Pipeline error: {run_exc}")
            _last_pipeline_result = {"email_status": "error", "email_error": str(run_exc)}
        finally:
            _pipeline_running = False
            _pipeline_lock.release()

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started", "overrides": overrides})


@app.route("/api/pipeline/status")
def api_pipeline_status():
    return jsonify({"running": _pipeline_running, "last_result": _last_pipeline_result})


@app.route("/api/startup/status")
def api_startup_status():
    """Return current state of background startup data fetches."""
    db = get_db()
    summary = db.get_dashboard_summary()
    return jsonify({
        "fetching_news":        _news_fetching,
        "fetching_market":      _market_fetching,
        "has_news":             bool(db.get_news(limit=1)),
        "total_stocks_tracked": summary["total_stocks_tracked"],
    })


@app.route("/api/market/status")
def api_market_status():
    return jsonify(get_market_status())


@app.route("/api/stocks")
def api_stocks():
    """Return the NSE stock catalog grouped by sector (fast hardcoded list)."""
    keyword = request.args.get("search", "").strip().upper()
    if keyword:
        filtered = {
            sector: tickers
            for sector, tickers in _NSE_STOCK_CATALOG.items()
            if keyword in sector.upper()
            or any(keyword in t for t in tickers)
        }
        return jsonify(filtered)
    return jsonify(_NSE_STOCK_CATALOG)


@app.route("/api/stocks/live")
def api_stocks_live():
    """
    Return all NSE-listed equities fetched dynamically from NSE open data.
    Falls back to hardcoded catalog if the live fetch fails.
    Grouped as {sector: [{symbol, name}, …]}.
    """
    force = request.args.get("refresh", "").lower() in ("1", "true")
    keyword = request.args.get("search", "").strip()

    if keyword:
        results = search_stocks(keyword)
        return jsonify(results)

    try:
        catalog = get_catalog_grouped(force_refresh=force)
        return jsonify({"source": "live", "catalog": catalog})
    except Exception as exc:
        return jsonify({"source": "fallback", "catalog": _NSE_STOCK_CATALOG, "error": str(exc)})


# ── Subscription routes ───────────────────────────────────────────────────────

@app.route("/subscribe")
def subscribe_page():
    return render_template("subscribe.html")


@app.route("/unsubscribe")
def unsubscribe_page():
    token = request.args.get("token", "").strip()
    db = get_db()
    if not token:
        return render_template("subscribe.html", unsubscribe_error="Invalid unsubscribe link.")
    ok = db.deactivate_subscriber(token)
    if ok:
        return render_template("subscribe.html", unsubscribed=True)
    return render_template("subscribe.html", unsubscribe_error="Token not found or already unsubscribed.")


@app.route("/api/subscribe", methods=["POST"])
def api_subscribe():
    """
    Subscribe or update an email subscription for 2x/day automated alerts.
    Body: {"email": "you@example.com", "stocks": ["TCS","INFY"]}
    - New subscriber  → sends a welcome confirmation email.
    - Existing email  → updates stock list, sends an update confirmation email.
    """
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    stocks = body.get("stocks") or []

    if not email or "@" not in email:
        return jsonify({"error": "Valid email required"}), 400
    if not stocks:
        return jsonify({"error": "Select at least one stock"}), 400

    db = get_db()
    upper_stocks = [s.upper() for s in stocks]
    record = db.save_subscriber(email, upper_stocks)
    is_new = record.get("is_new", True)
    app_url = request.host_url.rstrip("/")
    unsubscribe_url = f"{app_url}/unsubscribe?token={record['unsubscribe_token']}"

    # Send appropriate confirmation email in a background thread
    def _send_confirmation():
        try:
            if is_new:
                send_welcome_email(
                    email=email,
                    stocks=upper_stocks,
                    unsubscribe_url=unsubscribe_url,
                    app_url=app_url,
                )
                app.logger.info(f"Welcome email sent to {email}")
            else:
                send_update_email(
                    email=email,
                    stocks=upper_stocks,
                    unsubscribe_url=unsubscribe_url,
                    app_url=app_url,
                )
                app.logger.info(f"Update confirmation email sent to {email}")
        except Exception as exc:
            app.logger.error(f"Confirmation email failed for {email}: {exc}")

    threading.Thread(target=_send_confirmation, daemon=True).start()

    return jsonify({
        "status": "subscribed" if is_new else "updated",
        "email": email,
        "stocks": upper_stocks,
        "unsubscribe_url": unsubscribe_url,
    })


@app.route("/api/unsubscribe", methods=["POST"])
def api_unsubscribe():
    body = request.get_json(silent=True) or {}
    token = (body.get("token") or request.args.get("token", "")).strip()
    if not token:
        return jsonify({"error": "Token required"}), 400
    db = get_db()
    ok = db.deactivate_subscriber(token)
    return jsonify({"status": "unsubscribed" if ok else "not_found"})


@app.route("/api/subscribers")
@login_required
def api_subscribers():
    """Admin: list active subscribers. Requires authenticated admin user."""
    if not getattr(current_user, 'is_admin', False):
        return jsonify({"error": "Admin access required"}), 403
    db = get_db()
    subs = db.get_active_subscribers()
    # Strip unsubscribe_token from API response
    safe = [{"email": s["email"], "stocks": s["stocks"],
             "subscribed_at": s["subscribed_at"], "last_sent_at": s["last_sent_at"]}
            for s in subs]
    return jsonify(safe)


@app.route("/api/subscription/lookup", methods=["POST"])
def api_subscription_lookup():
    """
    Send the subscriber their unsubscribe link via email.
    Body: {"email": "you@example.com"}
    Used by the "Manage Subscription" form when user doesn't have the link.
    """
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "Valid email required"}), 400

    db = get_db()
    # Find subscriber by email (need the token)
    with db.session() as sess:
        from src.database.db_manager import SubscriberRecord
        record = sess.query(SubscriberRecord).filter_by(email=email, is_active=True).first()
        if not record:
            # Don't reveal whether email exists — always return success
            app.logger.info(f"Subscription lookup for unknown/inactive email: {email}")
            return jsonify({"status": "sent"})
        token = record.unsubscribe_token

    app_url = request.host_url.rstrip("/")
    unsubscribe_url = f"{app_url}/unsubscribe?token={token}"

    def _send():
        try:
            send_unsubscribe_lookup_email(
                email=email,
                unsubscribe_url=unsubscribe_url,
                app_url=app_url,
            )
            app.logger.info(f"Unsubscribe lookup email sent to {email}")
        except Exception as exc:
            app.logger.error(f"Lookup email failed for {email}: {exc}")

    threading.Thread(target=_send, daemon=True).start()
    return jsonify({"status": "sent"})


@app.route("/api/test-digest", methods=["POST"])
@login_required
def api_test_digest():
    """
    DEV/TEST: Immediately trigger one digest run for all active subscribers
    (or a specific email in the body). Requires admin.
    Body (optional): {"email": "you@example.com"}
    """
    if not getattr(current_user, 'is_admin', False):
        return jsonify({"error": "Admin access required"}), 403
    body = request.get_json(silent=True) or {}
    target_email = body.get("email", "").strip().lower()

    def _run():
        db = get_db()
        subs = db.get_active_subscribers()
        if target_email:
            subs = [s for s in subs if s["email"] == target_email]
        if not subs:
            app.logger.warning("[test-digest] No matching subscribers found")
            return
        for sub in subs:
            stocks = sub.get("stocks") or []
            email = sub.get("email", "")
            if not stocks or not email:
                continue
            try:
                with db.session() as sess:
                    from src.database.db_manager import SubscriberRecord
                    rec = sess.query(SubscriberRecord).filter_by(email=email).first()
                    token = rec.unsubscribe_token if rec else ""
                app_url = os.getenv("APP_URL", "http://localhost:5050")
                unsubscribe_url = f"{app_url}/unsubscribe?token={token}" if token else ""

                orch = AgentOrchestrator(CONFIG_PATH)
                orch.apply_overrides({
                    "stocks": stocks,
                    "recipients": [email],
                    "unsubscribe_url": unsubscribe_url,
                    "app_url": app_url,
                })
                orch.initialize_agents()
                orch.run_agents()
                orch.stop_agents()
                db.update_subscriber_sent(email)
                app.logger.info(f"[test-digest] Sent to {email}")
            except Exception as exc:
                app.logger.error(f"[test-digest] Failed for {email}: {exc}")

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started", "target": target_email or "all subscribers"})


# ── Global news route ─────────────────────────────────────────────────────────

@app.route("/api/news/global")
def api_news_global():
    """Return world/global market news (tagged __GLOBAL__ by NewsAgent)."""
    limit = int(request.args.get("limit", 30))
    db = get_db()
    data = db.get_global_news(limit=limit)
    # Auto-fetch live global news on first run when DB is empty
    if not data:
        data = _fetch_live_global_news_and_save(db)[:limit]
    return jsonify(data)


# ── News-based AI stock suggestions ───────────────────────────────────────────
_news_suggestions_cache: dict = {"ts": None, "data": None}
_NEWS_CACHE_SECONDS = 900   # 15 minutes

@app.route("/api/news/suggestions", methods=["POST"])
def api_news_suggestions():
    """
    Analyse latest news from DB and return AI-generated stock suggestions.
    Uses Gemini to map news to NSE tickers with BUY / SELL / HOLD recommendations.
    Results are cached for 15 minutes to avoid repeated LLM calls.
    """
    import time
    now = time.time()

    # Serve from cache if fresh
    if (_news_suggestions_cache["ts"] and
            now - _news_suggestions_cache["ts"] < _NEWS_CACHE_SECONDS and
            _news_suggestions_cache["data"]):
        return jsonify({"suggestions": _news_suggestions_cache["data"], "cached": True})

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    # Only hard-require Gemini key when using Gemini; Claude/OpenAI are checked inside the try block
    llm_provider_check = os.getenv("LLM_PROVIDER", "claude").lower().strip()
    if llm_provider_check == "gemini" and not gemini_key:
        return jsonify({"error": "GEMINI_API_KEY not configured"}), 503

    db = get_db()
    # Fetch recent Indian market + global news
    indian_news = db.get_news(limit=20)
    global_news = db.get_global_news(limit=15)
    # Auto-fetch live on first run so suggestions work immediately
    if not indian_news:
        indian_news = _fetch_live_news_and_save(db)[:20]
    if not global_news:
        global_news = _fetch_live_global_news_and_save(db)[:15]
    all_news = indian_news + global_news

    if not all_news:
        # Auto-trigger a background news fetch so subsequent calls will have data
        threading.Thread(target=_fetch_news_standalone, daemon=True).start()
        return jsonify({
            "error": "Fetching news from market feeds — please retry in a moment.",
            "fetching": True,
        }), 202

    headlines = []
    for n in all_news[:35]:
        sent  = n.get("sentiment", "NEUTRAL")
        sym   = n.get("symbol", "")
        label = f"[{sym}] " if sym and sym != "__GLOBAL__" else "[GLOBAL] "
        headlines.append(f"{label}[{sent}] {n.get('title', '')[:100]}")

    news_block = "\n".join(f"  • {h}" for h in headlines)

    prompt = (
        "You are an expert Indian stock market analyst.\n"
        "Based on the following recent news headlines affecting Indian markets, "
        "identify NSE-listed stocks that investors should consider. "
        "Return ONLY a valid JSON array. Each element must have:\n"
        "  symbol    – NSE ticker (e.g. RELIANCE, TCS, HDFCBANK)\n"
        "  action    – one of: BUY, SELL, HOLD, WATCH\n"
        "  reason    – 1-2 sentence explanation directly referencing the news\n"
        "  confidence– integer 0-100\n"
        "  sector    – sector name (e.g. IT, Banking, Energy)\n\n"
        "Rules:\n"
        "- Only include stocks where the news has a clear, direct impact\n"
        "- GLOBAL news (FED rates, crude oil, USD/INR) should map to specific "
          "Indian sectors/stocks it affects\n"
        "- Return 5-10 suggestions maximum\n"
        "- Do not include stocks if the connection is speculative\n\n"
        f"News headlines:\n{news_block}"
    )

    try:
        import re, json as _json, time as _t

        llm_provider = os.getenv("LLM_PROVIDER", "claude").lower().strip()
        raw = ""

        if llm_provider == "claude":
            import anthropic as _anthropic
            claude_key = os.getenv("CLAUDE_API_KEY", "").strip()
            if not claude_key:
                return jsonify({"error": "CLAUDE_API_KEY not configured"}), 503
            claude_model = os.getenv("CLAUDE_MODEL", "claude-opus-4-5")
            client = _anthropic.Anthropic(api_key=claude_key)
            resp = client.messages.create(
                model=claude_model,
                max_tokens=2048,
                system="You are an expert Indian stock market analyst. Return only valid JSON arrays.",
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()

        elif llm_provider == "openai":
            from openai import OpenAI as _OpenAI
            oai_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not oai_key:
                return jsonify({"error": "OPENAI_API_KEY not configured"}), 503
            oai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            client = _OpenAI(api_key=oai_key)
            resp = client.chat.completions.create(
                model=oai_model,
                messages=[
                    {"role": "system", "content": "You are an expert Indian stock market analyst. Return only valid JSON arrays."},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.2, max_tokens=2048,
            )
            raw = resp.choices[0].message.content.strip()

        else:  # gemini (default)
            if not gemini_key:
                return jsonify({"error": "GEMINI_API_KEY not configured"}), 503
            from google import genai as google_genai
            gclient = google_genai.Client(api_key=gemini_key)
            gmodel  = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            last_exc = None
            for attempt in range(3):
                try:
                    response = gclient.models.generate_content(model=gmodel, contents=prompt)
                    raw = response.text or ""
                    break
                except Exception as e:
                    last_exc = e
                    err_str = str(e).lower()
                    is_overload = ("503" in err_str or "unavailable" in err_str or
                                   "high demand" in err_str or "overloaded" in err_str)
                    if is_overload and attempt < 2:
                        wait = 4 * (2 ** attempt)
                        app.logger.warning(f"Gemini 503 on attempt {attempt+1}, retrying in {wait}s")
                        _t.sleep(wait)
                        continue
                    raise
            else:
                raise last_exc

        # Parse JSON from whichever provider responded
        m = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", raw)
        if m:
            raw = m.group(1)
        else:
            m2 = re.search(r"(\[[\s\S]*\])", raw)
            if m2:
                raw = m2.group(1)
        suggestions = _json.loads(raw)

        _news_suggestions_cache["ts"]   = now
        _news_suggestions_cache["data"] = suggestions
        return jsonify({"suggestions": suggestions, "cached": False, "provider": llm_provider})

    except Exception as exc:
        err_str = str(exc).lower()
        is_overload = ("503" in err_str or "unavailable" in err_str or
                       "high demand" in err_str or "overloaded" in err_str)
        is_permission = ("403" in err_str or "permission_denied" in err_str or
                         "denied access" in err_str or "permission denied" in err_str)
        app.logger.error(f"News suggestions error: {exc}")
        if is_permission:
            return jsonify({
                "error": "permission_denied",
                "message": (
                    "Gemini API access has been denied for this project (403). "
                    "Go to https://aistudio.google.com, create a new API key, "
                    "update GEMINI_API_KEY in your .env file, then restart the server."
                ),
            }), 403
        if is_overload:
            return jsonify({
                "error": "503 — Gemini is experiencing high demand. Please try again in a minute.",
                "retry_after": 60,
            }), 503
        return jsonify({"error": str(exc)}), 500


# ── Live Market Data ───────────────────────────────────────────────────────────
import time as _time

_live_cache: dict = {}
_LIVE_CACHE_SECS = 60   # 1-minute cache for individual quotes
_MOVERS_CACHE_SECS = 300  # 5-minute cache for movers

# Nifty 50 representative symbols used for movers / discovery
NIFTY50_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "HINDUNILVR",
    "INFY", "ITC", "SBIN", "BAJFINANCE", "BHARTIARTL",
    "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
    "TITAN", "SUNPHARMA", "ULTRACEMCO", "WIPRO", "NESTLEIND",
    "TECHM", "HCLTECH", "TATAMOTORS", "ONGC", "POWERGRID",
    "NTPC", "JSWSTEEL", "TATASTEEL", "GRASIM", "ADANIPORTS",
    "DMART", "DRREDDY", "DIVISLAB", "CIPLA", "BAJAJ-AUTO",
    "M&M", "EICHERMOT", "HEROMOTOCO", "COALINDIA", "BPCL",
    "TATACONSUM", "BRITANNIA", "HINDALCO", "INDUSINDBK",
    "APOLLOHOSP", "HDFCLIFE", "SBILIFE", "ZOMATO", "NYKAA", "PAYTM",
]

def _yf_sym(sym: str) -> str:
    """Convert NSE symbol to Yahoo Finance .NS format."""
    # Do NOT URL-encode — Yahoo Finance expects M&M.NS, not M%26M.NS
    return sym if sym.endswith(".NS") else sym + ".NS"


@app.route("/stocks")
def stocks_page():
    db = get_db()
    signals = db.get_latest_signals(50)
    recently_analyzed = list({s["symbol"]: s for s in signals}.values())[:8]
    return render_template("stocks.html", recently_analyzed=recently_analyzed)


@app.route("/api/stock/<symbol>/range")
def api_stock_range(symbol: str):
    """Multi-period OHLC data for the chart range switcher."""
    sym      = symbol.upper()
    period   = request.args.get("period", "1mo")
    interval = request.args.get("interval", "1d")
    cache_key = f"range_{sym}_{period}_{interval}"
    now = _time.time()
    if cache_key in _live_cache and now - _live_cache[cache_key]["ts"] < 600:
        return jsonify(_live_cache[cache_key]["data"])
    try:
        import yfinance as yf
        df = yf.download(_yf_sym(sym), period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if df.empty:
            return jsonify([])
        records = []
        for ts, row in df.iterrows():
            try:
                cv = float(row["Close"].iloc[0]) if hasattr(row["Close"], "iloc") else float(row["Close"])
                records.append({"t": ts.strftime("%d %b" if interval in ("1d","1wk") else "%H:%M"),
                                 "c": round(cv, 2)})
            except Exception:
                continue
        _live_cache[cache_key] = {"ts": now, "data": records}
        return jsonify(records)
    except Exception as exc:
        app.logger.error(f"Range error for {sym}: {exc}")
        return jsonify([])


@app.route("/api/stock/<symbol>/live")
def api_stock_live(symbol: str):
    """Live quote for a single NSE stock using yfinance (1-min cache)."""
    sym = symbol.upper()
    cache_key = f"live_{sym}"
    now = _time.time()
    if cache_key in _live_cache and now - _live_cache[cache_key]["ts"] < _LIVE_CACHE_SECS:
        return jsonify(_live_cache[cache_key]["data"])
    try:
        import yfinance as yf
        fi = yf.Ticker(_yf_sym(sym)).fast_info
        change = fi.last_price - fi.previous_close
        change_pct = (change / fi.previous_close * 100) if fi.previous_close else 0
        data = {
            "symbol": sym,
            "price": round(fi.last_price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "open": round(fi.open, 2) if fi.open else None,
            "day_high": round(fi.day_high, 2) if fi.day_high else None,
            "day_low": round(fi.day_low, 2) if fi.day_low else None,
            "prev_close": round(fi.previous_close, 2),
            "year_high": round(fi.year_high, 2) if fi.year_high else None,
            "year_low": round(fi.year_low, 2) if fi.year_low else None,
            "volume": int(fi.last_volume) if fi.last_volume else None,
            "avg_volume": int(fi.three_month_average_volume) if fi.three_month_average_volume else None,
            "market_cap": int(fi.market_cap) if fi.market_cap else None,
            "year_change_pct": round(fi.year_change * 100, 2) if fi.year_change else None,
        }
        _live_cache[cache_key] = {"ts": now, "data": data}
        return jsonify(data)
    except Exception as exc:
        app.logger.error(f"Live quote error for {sym}: {exc}")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/stock/<symbol>/intraday")
def api_stock_intraday(symbol: str):
    """Intraday price history (1-min intervals, last 1 day)."""
    sym = symbol.upper()
    cache_key = f"intraday_{sym}"
    now = _time.time()
    if cache_key in _live_cache and now - _live_cache[cache_key]["ts"] < _LIVE_CACHE_SECS:
        return jsonify(_live_cache[cache_key]["data"])
    try:
        import yfinance as yf
        df = yf.download(_yf_sym(sym), period="1d", interval="5m",
                         progress=False, auto_adjust=True)
        if df.empty:
            return jsonify([])
        records = []
        for ts, row in df.iterrows():
            try:
                close_val = float(row["Close"].iloc[0]) if hasattr(row["Close"], "iloc") else float(row["Close"])
                vol_val   = int(row["Volume"].iloc[0]) if hasattr(row["Volume"], "iloc") else int(row["Volume"])
                records.append({"t": ts.strftime("%H:%M"), "c": round(close_val, 2), "v": vol_val})
            except Exception:
                continue
        _live_cache[cache_key] = {"ts": now, "data": records}
        return jsonify(records)
    except Exception as exc:
        app.logger.error(f"Intraday error for {sym}: {exc}")
        return jsonify([])


@app.route("/api/stocks/movers")
def api_stocks_movers():
    """Top gainers & losers from Nifty 50 (5-min cache)."""
    now = _time.time()
    if "movers" in _live_cache and now - _live_cache["movers"]["ts"] < _MOVERS_CACHE_SECS:
        return jsonify(_live_cache["movers"]["data"])
    try:
        import yfinance as yf
        symbols = NIFTY50_SYMBOLS[:30]
        yf_syms = [_yf_sym(s) for s in symbols]

        # group_by='ticker' works reliably across yfinance 0.2.x versions
        df = yf.download(
            yf_syms, period="5d", interval="1d",
            progress=False, auto_adjust=True, group_by="ticker"
        )

        results = []
        for sym, yfs in zip(symbols, yf_syms):
            try:
                # With group_by='ticker': df[ticker_sym]["Close"]
                if yfs in df.columns.get_level_values(0):
                    col = df[yfs]["Close"]
                else:
                    continue
                vals = col.dropna().values
                if len(vals) < 2:
                    continue
                prev_p, last_p = float(vals[-2]), float(vals[-1])
                chg_pct = (last_p - prev_p) / prev_p * 100 if prev_p else 0
                results.append({
                    "symbol": sym, "price": round(last_p, 2),
                    "change_pct": round(chg_pct, 2),
                    "change": round(last_p - prev_p, 2),
                })
            except Exception as sym_exc:
                app.logger.debug(f"Movers skip {sym}: {sym_exc}")
                continue

        if not results:
            raise ValueError("All symbols returned empty data from yfinance")

        results.sort(key=lambda x: x["change_pct"], reverse=True)
        gainers = [r for r in results if r["change_pct"] > 0][:8]
        losers  = sorted([r for r in results if r["change_pct"] < 0],
                         key=lambda x: x["change_pct"])[:8]
        # Weekend / market closed: still show top/bottom movers
        if not gainers and not losers and results:
            gainers = results[:5]
            losers  = results[-5:]
        data = {"gainers": gainers, "losers": losers}
        _live_cache["movers"] = {"ts": now, "data": data}
        return jsonify(data)
    except Exception as exc:
        app.logger.error(f"Movers error: {exc}")
        return jsonify({"gainers": [], "losers": [], "error": str(exc)})


@app.route("/api/stocks/trending")
def api_stocks_trending():
    """Most active stocks based on DB signals + news (no external call).
    Falls back to a curated default list on first run."""
    db = get_db()
    signals = db.get_latest_signals(50)
    from collections import Counter
    sym_counts = Counter(s["symbol"] for s in signals)
    sig_map = {s["symbol"]: s for s in signals}
    trending = []
    for sym, cnt in sym_counts.most_common(20):
        sig = sig_map.get(sym, {})
        trending.append({
            "symbol": sym, "signal_count": cnt,
            "signal_type": sig.get("signal_type", "HOLD"),
            "confidence": sig.get("confidence", 0),
            "risk_level": sig.get("risk_level", ""),
            "signal_date": sig.get("signal_date", ""),
        })
    # First-run fallback: return popular Nifty stocks so the page isn't empty
    if not trending:
        DEFAULT_TRENDING = ["TCS","RELIANCE","HDFCBANK","INFY","ICICIBANK",
                            "SBIN","BAJFINANCE","WIPRO","SUNPHARMA","TITAN"]
        trending = [{"symbol": s, "signal_count": 0, "signal_type": "WATCH",
                     "confidence": 0, "risk_level": "", "signal_date": "",
                     "is_default": True} for s in DEFAULT_TRENDING]
    return jsonify(trending)


@app.route("/api/stocks/sector-leaders")
def api_sector_leaders():
    """Best BUY signal per sector from DB.
    Falls back to top stock per sector on first run."""
    db = get_db()
    signals = db.get_latest_signals(100)
    sector_map = {}
    for sector, tickers in _NSE_STOCK_CATALOG.items():
        tset = set(tickers)
        sector_signals = [s for s in signals if s["symbol"] in tset and s.get("signal_type") == "BUY"]
        sector_signals.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        if sector_signals:
            best = sector_signals[0]
            sector_map[sector] = {
                "symbol": best["symbol"], "signal_type": best["signal_type"],
                "confidence": best.get("confidence", 0), "sector": sector,
                "risk_level": best.get("risk_level", ""),
            }
        else:
            # First-run fallback: show top stock per sector with WATCH signal
            sector_map[sector] = {
                "symbol": tickers[0], "signal_type": "WATCH",
                "confidence": 0, "sector": sector,
                "risk_level": "", "is_default": True,
            }
    return jsonify(list(sector_map.values()))


@app.route("/api/stocks/presets")
def api_stocks_presets():
    """Dynamic presets: AI-derived from DB signals + sector presets."""
    db = get_db()
    signals = db.get_latest_signals(50)
    recent = list({s["symbol"] for s in signals[:10]})[:6]
    buys  = [s["symbol"] for s in signals if s.get("signal_type") == "BUY"][:6]
    presets = [
        {"label": "IT Leaders",   "stocks": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"]},
        {"label": "Banking",      "stocks": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK"]},
        {"label": "Energy",       "stocks": ["RELIANCE", "ONGC", "NTPC", "TATAPOWER", "ADANIGREEN"]},
        {"label": "Nifty Mix",    "stocks": ["TCS", "INFY", "HDFCBANK", "RELIANCE", "TITAN", "ITC"]},
        {"label": "Pharma",       "stocks": ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "AUROPHARMA"]},
    ]
    if buys:
        presets.insert(0, {"label": "🤖 AI Buys", "stocks": buys})
    if recent:
        presets.insert(0, {"label": "⏱ Recent", "stocks": recent})
    return jsonify(presets)


# ── Static chart serving ───────────────────────────────────────────────────────

@app.route("/charts/<filename>")
def serve_chart(filename: str):
    from flask import send_from_directory
    charts_dir = ROOT / "data" / "reports"
    return send_from_directory(str(charts_dir), filename)


# ── 2x/day Subscriber Scheduler ──────────────────────────────────────────────

IST = ZoneInfo("Asia/Kolkata")

def _send_subscriber_digests(run_label: str) -> None:
    """Run the full pipeline for every active subscriber's stock list, then email them."""
    db = get_db()
    subscribers = db.get_active_subscribers()
    if not subscribers:
        return

    app.logger.info(f"[Scheduler/{run_label}] Sending digests to {len(subscribers)} subscribers")
    for sub in subscribers:
        stocks = sub.get("stocks") or []
        email = sub.get("email", "")
        if not stocks or not email:
            continue
        try:
            # Build each subscriber's personal unsubscribe URL using the stored token
            with db.session() as sess:
                from src.database.db_manager import SubscriberRecord
                rec = sess.query(SubscriberRecord).filter_by(email=email).first()
                token = rec.unsubscribe_token if rec else ""
            app_url = os.getenv("APP_URL", "http://localhost:5050")
            unsubscribe_url = f"{app_url}/unsubscribe?token={token}" if token else ""

            orch = AgentOrchestrator(CONFIG_PATH)
            orch.apply_overrides({
                "stocks": stocks,
                "recipients": [email],
                "unsubscribe_url": unsubscribe_url,
                "app_url": app_url,
            })
            orch.initialize_agents()
            orch.run_agents()
            orch.stop_agents()
            db.update_subscriber_sent(email)
            # Send Telegram signal summary for this subscriber's stocks
            try:
                signals = db.get_latest_signals(limit=20)
                send_pipeline_alerts(db, signals)
            except Exception as tg_exc:
                app.logger.warning(f"[Scheduler] Telegram alert error: {tg_exc}")
            app.logger.info(f"[Scheduler/{run_label}] Sent digest to {email}")
        except Exception as exc:
            app.logger.error(f"[Scheduler/{run_label}] Failed for {email}: {exc}")


def _start_scheduler():
    """Start APScheduler with two daily jobs (IST times)."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = BackgroundScheduler(timezone=IST)

        # Pre-market: 8:45 AM IST (NSE opens 9:15 AM)
        scheduler.add_job(
            lambda: _send_subscriber_digests("pre-market"),
            CronTrigger(hour=8, minute=45, timezone=IST),
            id="pre_market",
            replace_existing=True,
        )

        # Post-market: 4:15 PM IST (NSE closes 3:30 PM)
        scheduler.add_job(
            lambda: _send_subscriber_digests("post-market"),
            CronTrigger(hour=16, minute=15, timezone=IST),
            id="post_market",
            replace_existing=True,
        )

        scheduler.start()
        app.logger.info("Scheduler started: pre-market 08:45 IST, post-market 16:15 IST")
        return scheduler
    except ImportError:
        app.logger.warning(
            "APScheduler not installed — scheduled digests disabled. "
            "Run: pip install apscheduler"
        )
        return None


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 ROUTES
# ══════════════════════════════════════════════════════════════════════════════

_indicators_cache: dict = {}   # {symbol: (timestamp, result)}
_IND_CACHE_TTL = 600           # 10 minutes


def _cached_indicators(symbol: str, db_history=None):
    import time
    sym = symbol.upper()
    now = time.time()
    if sym in _indicators_cache:
        ts, data = _indicators_cache[sym]
        if now - ts < _IND_CACHE_TTL:
            return data
    data = get_indicators(sym, yfinance_first=True, db_history=db_history)
    _indicators_cache[sym] = (now, data)
    return data


# ── Technical Indicators API ──────────────────────────────────────────────────

@app.route("/api/stock/<symbol>/indicators")
def api_indicators(symbol: str):
    db = get_db()
    history = db.get_recent_stock_data(symbol.upper(), limit=200)
    result = _cached_indicators(symbol, db_history=history)
    return jsonify(result)


# ── Stock Screener ────────────────────────────────────────────────────────────

@app.route("/screener")
def screener():
    return render_template("screener.html")


@app.route("/api/screener")
def api_screener():
    """
    Query params: sector, signal (BUY/SELL/HOLD), min_conf (0-100),
                  risk (LOW/MEDIUM/HIGH), rsi_min, rsi_max, macd_trend (bullish/bearish)
    """
    sector = request.args.get("sector", "").strip()
    signal_filter = request.args.get("signal", "").upper()
    min_conf = int(request.args.get("min_conf", 0))
    risk_filter = request.args.get("risk", "").upper()
    rsi_min = float(request.args.get("rsi_min", 0))
    rsi_max = float(request.args.get("rsi_max", 100))
    macd_trend = request.args.get("macd_trend", "").lower()

    # Build candidate symbol list
    if sector and sector in _NSE_STOCK_CATALOG:
        candidates = _NSE_STOCK_CATALOG[sector]
    else:
        candidates = [s for lst in _NSE_STOCK_CATALOG.values() for s in lst]

    db = get_db()
    results = []
    for sym in candidates:
        try:
            # Skip symbols with no DB history on first run to prevent yfinance hang
            db_history = db.get_recent_stock_data(sym, limit=200)
            if not db_history:
                continue
            ind = _cached_indicators(sym, db_history=db_history)
            if ind.get("error"):
                continue
            rsi = ind.get("rsi", {}).get("value")
            macd_sig = ind.get("macd", {}).get("trend", "")
            tech_signal = ind.get("summary", {}).get("signal", "HOLD")
            latest = db.get_recent_stock_data(sym, limit=1)
            price = latest[0]["price"] if latest else None

            # Filters
            if signal_filter and tech_signal != signal_filter:
                continue
            if risk_filter:
                bb_pct = ind.get("bollinger", {}).get("percent_b")
                if risk_filter == "LOW" and (bb_pct is None or bb_pct > 0.7):
                    continue
                if risk_filter == "HIGH" and (bb_pct is None or bb_pct < 0.3):
                    continue
            if rsi is not None and not (rsi_min <= rsi <= rsi_max):
                continue
            if macd_trend and macd_sig.lower() != macd_trend:
                continue

            results.append({
                "symbol": sym,
                "price": price,
                "signal": tech_signal,
                "rsi": rsi,
                "macd_trend": macd_sig,
                "bb_percent_b": ind.get("bollinger", {}).get("percent_b"),
                "ma20": ind.get("moving_averages", {}).get("ma20"),
                "bullish_count": ind.get("summary", {}).get("bullish", 0),
                "bearish_count": ind.get("summary", {}).get("bearish", 0),
            })
        except Exception:
            continue

    filtered = bool(signal_filter or risk_filter or macd_trend
                    or min_conf > 0 or rsi_min > 0 or rsi_max < 100 or sector)
    return jsonify({"results": results, "count": len(results), "filtered": filtered})


# ── Backtesting ───────────────────────────────────────────────────────────────

@app.route("/backtest")
def backtest():
    return render_template("backtest.html")


@app.route("/api/backtest/<symbol>")
def api_backtest(symbol: str):
    db = get_db()
    sym = symbol.upper()
    signals = db.get_all_signals_for_backtest(sym)
    if not signals:
        return jsonify({"error": "no_signals", "symbol": sym})

    history = db.get_recent_stock_data(sym, limit=500)
    price_map = {row["timestamp"][:10]: row["price"] for row in history}

    trades = []
    wins = losses = 0
    total_pnl_pct = 0.0

    for sig in signals:
        entry_date = sig.get("signal_date", "")[:10]
        entry_price = price_map.get(entry_date)
        if entry_price is None:
            continue
        # Look 5 trading days ahead (simple: next available price key after entry)
        dates_after = sorted(k for k in price_map if k > entry_date)
        exit_date = dates_after[4] if len(dates_after) >= 5 else (dates_after[-1] if dates_after else None)
        if not exit_date:
            continue
        exit_price = price_map[exit_date]
        pnl_pct = (exit_price - entry_price) / entry_price * 100
        if sig.get("signal_type") == "SELL":
            pnl_pct = -pnl_pct
        total_pnl_pct += pnl_pct
        is_win = pnl_pct > 0
        if is_win:
            wins += 1
        else:
            losses += 1
        trades.append({
            "signal_type": sig.get("signal_type"),
            "signal_date": entry_date,
            "confidence": sig.get("confidence"),
            "entry_price": round(entry_price, 2),
            "exit_date": exit_date,
            "exit_price": round(exit_price, 2),
            "pnl_pct": round(pnl_pct, 2),
            "win": is_win,
        })

    n = len(trades)
    return jsonify({
        "symbol": sym,
        "total_trades": n,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / n * 100, 1) if n else 0,
        "avg_pnl_pct": round(total_pnl_pct / n, 2) if n else 0,
        "trades": trades,
    })


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        user_data = db.verify_user_password(email, password)
        if user_data:
            db.update_user_login(user_data["id"])
            login_user(_FlaskUser(user_data), remember=request.form.get("remember") == "on")
            next_page = request.args.get("next", url_for("dashboard"))
            return redirect(next_page)
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if password != confirm:
            flash("Passwords do not match.", "danger")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
        else:
            db = get_db()
            result = db.create_user_with_password(username, email, password)
            if "error" in result:
                flash("Email or username already taken.", "danger")
            else:
                flash("Account created! Please log in.", "success")
                return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ── Portfolio ─────────────────────────────────────────────────────────────────

@app.route("/portfolio")
@login_required
def portfolio():
    return render_template("portfolio.html")


@app.route("/api/portfolio")
@login_required
def api_portfolio_list():
    db = get_db()
    positions = db.get_portfolio(int(current_user.id))
    # Enrich with latest price + unrealised P&L
    enriched = []
    for pos in positions:
        latest = db.get_recent_stock_data(pos["symbol"], limit=1)
        current_price = latest[0]["price"] if latest else pos["avg_buy_price"]
        invested = pos["avg_buy_price"] * pos["quantity"]
        current_val = current_price * pos["quantity"]
        pnl = current_val - invested
        enriched.append({
            **pos,
            "current_price": round(current_price, 2),
            "current_value": round(current_val, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / invested * 100, 2) if invested else 0,
        })
    total_invested = sum(p["avg_buy_price"] * p["quantity"] for p in positions)
    total_current = sum(p["current_value"] for p in enriched)
    return jsonify({
        "positions": enriched,
        "summary": {
            "total_invested": round(total_invested, 2),
            "total_current": round(total_current, 2),
            "total_pnl": round(total_current - total_invested, 2),
            "total_pnl_pct": round((total_current - total_invested) / total_invested * 100, 2) if total_invested else 0,
        }
    })


@app.route("/api/portfolio/add", methods=["POST"])
@login_required
def api_portfolio_add():
    data = request.get_json() or request.form
    symbol = str(data.get("symbol", "")).upper()
    try:
        qty = float(data.get("quantity", 0))
        price = float(data.get("avg_buy_price", 0))
    except ValueError:
        return jsonify({"error": "invalid_numbers"}), 400
    if not symbol or qty <= 0 or price <= 0:
        return jsonify({"error": "bad_params"}), 400
    db = get_db()
    pos = db.add_position(int(current_user.id), symbol, qty, price,
                          notes=str(data.get("notes", "")))
    return jsonify(pos), 201


@app.route("/api/portfolio/close/<int:position_id>", methods=["POST"])
@login_required
def api_portfolio_close(position_id: int):
    data = request.get_json() or request.form
    try:
        sell_price = float(data.get("sell_price", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_price"}), 400
    db = get_db()
    result = db.close_position(position_id, sell_price)
    return jsonify(result)


@app.route("/api/portfolio/delete/<int:position_id>", methods=["DELETE"])
@login_required
def api_portfolio_delete(position_id: int):
    db = get_db()
    ok = db.delete_position(position_id, int(current_user.id))
    return jsonify({"success": ok})


# ── Watchlist ─────────────────────────────────────────────────────────────────

@app.route("/api/watchlist")
@login_required
def api_watchlist():
    db = get_db()
    symbols = db.get_watchlist(int(current_user.id))
    return jsonify({"watchlist": symbols})


@app.route("/api/watchlist/toggle/<symbol>", methods=["POST"])
@login_required
def api_watchlist_toggle(symbol: str):
    db = get_db()
    added = db.toggle_watchlist(int(current_user.id), symbol.upper())
    return jsonify({"added": added, "symbol": symbol.upper()})


# ── Telegram deep-link subscribe flow ────────────────────────────────────────
#
#  1. User clicks "Subscribe to Alerts" on /portfolio
#  2. Frontend calls GET /api/telegram/subscribe-link  → returns a t.me deep-link
#  3. User opens the link in Telegram and presses START
#  4. Telegram POSTs the /start <token> update to POST /api/telegram/webhook
#  5. Server finds user by token, saves chat_id, deletes the token
#  Requires:  TELEGRAM_BOT_TOKEN + TELEGRAM_WEBHOOK_URL in .env
# ─────────────────────────────────────────────────────────────────────────────

def _tg_bot_username() -> str:
    """Fetch the bot's @username from Telegram (cached in process memory)."""
    if not hasattr(_tg_bot_username, "_cache"):
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not token:
            _tg_bot_username._cache = ""
            return ""
        try:
            r = http_requests.get(
                f"https://api.telegram.org/bot{token}/getMe", timeout=5
            )
            _tg_bot_username._cache = r.json().get("result", {}).get("username", "")
        except Exception:
            _tg_bot_username._cache = ""
    return _tg_bot_username._cache


@app.route("/api/telegram/run-info", methods=["GET"])
@login_required
def api_telegram_run_info():
    """Summary shown in the Run Analysis modal — subscriber count + server status."""
    server_ok = bool(os.getenv("TELEGRAM_BOT_TOKEN", ""))
    count = 0
    if server_ok:
        try:
            with get_db().session() as sess:
                from src.database.db_manager import UserRecord
                count = sess.query(UserRecord).filter_by(
                    is_active=True, telegram_alerts=True
                ).count()
        except Exception:
            pass
    return jsonify({"server_configured": server_ok, "subscribers": count})


@app.route("/api/telegram/status", methods=["GET"])
@login_required
def api_telegram_status():
    """Return whether the current user has a linked Telegram account."""
    server_ok = bool(os.getenv("TELEGRAM_BOT_TOKEN", ""))
    tg = get_db().get_user_telegram(int(current_user.id))
    return jsonify({
        "server_configured": server_ok,
        "linked": tg.get("linked", False),
        "enabled": tg.get("enabled", False),
        "bot_username": _tg_bot_username() if server_ok else "",
    })


@app.route("/api/telegram/subscribe-link", methods=["GET"])
@login_required
def api_telegram_subscribe_link():
    """
    Generate a one-time deep-link the user can tap to subscribe.
    e.g.  https://t.me/MarketMindBot?start=abc123
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        return jsonify({"error": "Telegram is not enabled on this server."}), 503
    username = _tg_bot_username()
    if not username:
        return jsonify({"error": "Could not resolve bot username from Telegram API."}), 503
    token = get_db().generate_telegram_link_token(int(current_user.id))
    link = f"https://t.me/{username}?start={token}"
    return jsonify({
        "link": link,
        "bot_username": username,
        "start_token": token,
        "start_command": f"/start {token}",
        "web_login_url": "https://web.telegram.org/",
    })


@app.route("/api/telegram/webhook", methods=["POST"])
def api_telegram_webhook():
    """
    Telegram sends all bot updates here.
    When a user taps our deep-link and presses Start, Telegram delivers:
      { "message": { "text": "/start <token>", "chat": { "id": <chat_id> } } }
    We use the token to find the user and save their chat_id.
    This endpoint is intentionally unauthenticated (Telegram calls it).
    """
    update = request.get_json(silent=True) or {}
    message = update.get("message") or update.get("edited_message", {})
    text = (message.get("text") or "").strip()
    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))
    first_name = chat.get("first_name", "there")

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    if text.startswith("/start ") and chat_id and bot_token:
        link_token = text.split(" ", 1)[1].strip()
        ok = get_db().link_telegram_by_token(link_token, chat_id)
        reply = (
            f"✅ Hi {first_name}! You're now subscribed to MarketMind AI alerts.\n"
            "You'll receive trading signals whenever the pipeline runs."
            if ok else
            "⚠️ This link has already been used or has expired. "
            "Please generate a new subscribe link from the app."
        )
        http_requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": reply},
            timeout=5,
        )

    return jsonify({"ok": True})


@app.route("/api/telegram/unsubscribe", methods=["POST"])
@login_required
def api_telegram_unsubscribe():
    """Remove the user's Telegram link."""
    get_db().unlink_telegram(int(current_user.id))
    return jsonify({"success": True})


@app.route("/api/telegram/test", methods=["POST"])
@login_required
def api_telegram_test():
    """Send a test message to the authenticated user's saved chat_id."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        return jsonify({"error": "Telegram is not enabled on this server."}), 503
    tg = get_db().get_user_telegram(int(current_user.id))
    chat_id = tg.get("chat_id", "")
    if not chat_id:
        return jsonify({"error": "Not subscribed yet. Use the Subscribe button first."}), 400
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": "✅ MarketMind AI — Telegram alerts are working!"}
    try:
        resp = http_requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return jsonify({"success": True})
    except Exception:
        return jsonify({"error": "Could not send message. Make sure you've started the bot first."}), 500


if __name__ == "__main__":
    _start_scheduler()

    # Auto-fetch market data + news on first launch if the database is empty
    _initial_db = get_db()
    _has_market = bool(_initial_db.get_dashboard_summary()["total_stocks_tracked"])
    _has_news   = bool(_initial_db.get_news(limit=1) or _initial_db.get_global_news(limit=1))
    if not _has_market:
        app.logger.info("No market data in database — auto-fetching stock prices on startup …")
        threading.Thread(target=_fetch_market_data_standalone, daemon=True).start()
    if not _has_news:
        app.logger.info("No news in database — auto-fetching news on startup …")
        threading.Thread(target=_fetch_news_standalone, daemon=True).start()

    # ── Telegram: polling vs webhook, auto-detected ───────────────────────────
    # - If TELEGRAM_WEBHOOK_URL is set in .env → register webhook with Telegram
    #   (production mode: Telegram pushes updates to your public URL instantly)
    # - Otherwise → start long-polling in a background thread
    #   (dev/localhost mode: app pulls updates from Telegram every 30 s)
    from src.telegram_utils import start_polling
    _tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    _webhook_base = os.getenv("TELEGRAM_WEBHOOK_URL", "").rstrip("/")

    if _tg_token and _webhook_base:
        # Production: register webhook, polling thread not needed
        _webhook_url = f"{_webhook_base}/api/telegram/webhook"
        try:
            _r = http_requests.post(
                f"https://api.telegram.org/bot{_tg_token}/setWebhook",
                json={"url": _webhook_url, "allowed_updates": ["message"]},
                timeout=10,
            )
            if _r.json().get("ok"):
                print(f"[Telegram] Webhook registered → {_webhook_url}")
            else:
                print(f"[Telegram] Webhook registration failed: {_r.json()}")
        except Exception as _e:
            print(f"[Telegram] Webhook registration error: {_e}")
    else:
        # Dev / localhost: use long-polling (no public URL needed)
        start_polling(get_db())

    port = int(os.getenv("FLASK_PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=False)
