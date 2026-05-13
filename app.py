"""
MarketMind AI – Flask Web Dashboard
Provides a browser-based UI backed by the SQLite database.

Endpoints:
  GET  /                  – Dashboard (signals + news summary)
  GET  /stock/<symbol>    – Stock detail page
  GET  /alerts            – Alert history
  GET  /api/signals       – JSON: latest trading signals
  GET  /api/news          – JSON: latest news
  GET  /api/summary       – JSON: dashboard KPI summary
  POST /api/run           – Trigger a pipeline run (background thread)
"""
import json
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, abort
from flask_cors import CORS
from dotenv import load_dotenv

# Ensure project root is on the path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv()

from src.database.db_manager import DatabaseManager
from src.orchestrator import AgentOrchestrator

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
    news = db.get_news(limit=10)
    alerts = db.get_recent_alerts(5)
    return render_template(
        "dashboard.html",
        summary=summary,
        signals=signals,
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
    """Trigger a full pipeline run in a background thread."""
    global _pipeline_running
    if not _pipeline_lock.acquire(blocking=False):
        return jsonify({"status": "already_running"}), 409
    
    _pipeline_running = True

    def _run():
        global _pipeline_running
        try:
            orch = AgentOrchestrator(CONFIG_PATH)
            orch.initialize_agents()
            orch.run_agents()
            orch.stop_agents()
        finally:
            _pipeline_running = False
            _pipeline_lock.release()

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/api/pipeline/status")
def api_pipeline_status():
    return jsonify({"running": _pipeline_running})


# ── Static chart serving ───────────────────────────────────────────────────────

@app.route("/charts/<filename>")
def serve_chart(filename: str):
    from flask import send_from_directory
    charts_dir = ROOT / "data" / "reports"
    return send_from_directory(str(charts_dir), filename)


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=False)
