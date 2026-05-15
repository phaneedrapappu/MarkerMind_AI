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
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv

# Ensure project root is on the path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv()

from src.database.db_manager import DatabaseManager
from src.orchestrator import AgentOrchestrator
from src.stock_discovery import get_catalog_grouped, search_stocks, fetch_all_nse_stocks
from src.email_utils import send_welcome_email, send_update_email, send_unsubscribe_lookup_email

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
CORS(app)

CONFIG_PATH = str(ROOT / "config" / "config.yaml")
_db: DatabaseManager = None
_pipeline_lock = threading.Lock()
_pipeline_running = False


def get_db() -> DatabaseManager:
    global _db
    if _db is None:
        import yaml
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        db_path = cfg.get("database", {}).get("path", "data/marketmind.db")
        _db = DatabaseManager(db_path)
    return _db


# ── Pages ──────────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    db = get_db()
    summary = db.get_dashboard_summary()
    signals = db.get_latest_signals(10)
    signals_all = db.get_latest_signals(100)
    news = db.get_news(limit=10)
    alerts = db.get_recent_alerts(5)
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
def api_run_pipeline():
    """
    Trigger a full pipeline run in a background thread.
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
    if body.get("email"):
        if isinstance(body["email"], str):
            overrides["recipients"] = [e.strip() for e in body["email"].split(",") if e.strip()]
        else:
            overrides["recipients"] = [e.strip() for e in body["email"] if e.strip()]

    def _run():
        global _pipeline_running
        try:
            orch = AgentOrchestrator(CONFIG_PATH)
            orch.apply_overrides(overrides)
            orch.initialize_agents()
            orch.run_agents()
            orch.stop_agents()
        finally:
            _pipeline_running = False
            _pipeline_lock.release()

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started", "overrides": overrides})


@app.route("/api/pipeline/status")
def api_pipeline_status():
    return jsonify({"running": _pipeline_running})


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
def api_subscribers():
    """Admin: list active subscribers (no auth for MVP)."""
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
def api_test_digest():
    """
    DEV/TEST: Immediately trigger one digest run for all active subscribers
    (or a specific email in the body).
    Body (optional): {"email": "you@example.com"}
    """
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
    return jsonify(db.get_global_news(limit=limit))


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
    if not gemini_key:
        return jsonify({"error": "GEMINI_API_KEY not configured"}), 503

    db = get_db()
    # Fetch recent Indian market + global news
    indian_news = db.get_news(limit=20)
    global_news = db.get_global_news(limit=15)
    all_news = indian_news + global_news

    if not all_news:
        return jsonify({"error": "No news in database yet. Run the pipeline first."}), 404

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
        from google import genai as google_genai
        client = google_genai.Client(api_key=gemini_key)
        model  = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        # Retry up to 3 times on 503 / overload with exponential backoff
        last_exc = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                break
            except Exception as e:
                last_exc = e
                err_str = str(e).lower()
                is_overload = ("503" in err_str or "unavailable" in err_str or
                               "high demand" in err_str or "overloaded" in err_str)
                if is_overload and attempt < 2:
                    wait = 4 * (2 ** attempt)   # 4s, 8s
                    app.logger.warning(f"Gemini 503 on attempt {attempt+1}, retrying in {wait}s")
                    _t.sleep(wait)
                    continue
                raise
        else:
            raise last_exc

        raw = response.text or ""

        # Parse JSON from response
        raw = raw.strip()
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
        return jsonify({"suggestions": suggestions, "cached": False})

    except Exception as exc:
        err_str = str(exc).lower()
        is_overload = ("503" in err_str or "unavailable" in err_str or
                       "high demand" in err_str or "overloaded" in err_str)
        app.logger.error(f"News suggestions error: {exc}")
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
    s = sym.replace("&", "%26")
    return s if s.endswith(".NS") else s + ".NS"


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
        symbols = NIFTY50_SYMBOLS[:35]
        yf_syms = [_yf_sym(s) for s in symbols]
        df = yf.download(yf_syms, period="2d", interval="1d",
                         progress=False, auto_adjust=True)
        close = df.get("Close", df)
        results = []
        for sym, yfs in zip(symbols, yf_syms):
            try:
                col = close[yfs] if yfs in close.columns else None
                if col is None:
                    col = close[sym] if sym in close.columns else None
                if col is None:
                    continue
                vals = col.dropna().values
                if len(vals) < 2:
                    continue
                prev_p, last_p = float(vals[-2]), float(vals[-1])
                chg_pct = (last_p - prev_p) / prev_p * 100 if prev_p else 0
                results.append({
                    "symbol": sym, "price": round(last_p, 2),
                    "change_pct": round(chg_pct, 2), "change": round(last_p - prev_p, 2),
                })
            except Exception:
                continue
        results.sort(key=lambda x: x["change_pct"], reverse=True)
        gainers = [r for r in results if r["change_pct"] > 0][:8]
        losers  = sorted([r for r in results if r["change_pct"] < 0],
                         key=lambda x: x["change_pct"])[:8]
        data = {"gainers": gainers, "losers": losers}
        _live_cache["movers"] = {"ts": now, "data": data}
        return jsonify(data)
    except Exception as exc:
        app.logger.error(f"Movers error: {exc}")
        return jsonify({"gainers": [], "losers": [], "error": str(exc)})


@app.route("/api/stocks/trending")
def api_stocks_trending():
    """Most active stocks based on DB signals + news (no external call)."""
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
    return jsonify(trending)


@app.route("/api/stocks/sector-leaders")
def api_sector_leaders():
    """Best BUY signal per sector from DB."""
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


if __name__ == "__main__":
    _start_scheduler()
    port = int(os.getenv("FLASK_PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=False)
