# 📊 MarketMind AI – Financial Intelligence Agent System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green)](https://flask.palletsprojects.com)
[![Gemini](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-orange)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MarketMind AI is an autonomous multi-agent system that monitors Indian stock markets (NSE), generates AI-powered trading signals, and delivers rich HTML email digests — all without manual intervention. It ships with a **mobile-first web dashboard** and a full **CLI** so you can run it however you like.

---

## 🏗️ Agent Pipeline

```
MarketDataAgent   →  NSE API / yfinance fallback
       ↓
  NewsAgent        →  RSS feeds (Google News, ET Markets, Moneycontrol)
       ↓
AIAnalysisAgent    →  Google Gemini 2.5 Flash (batched per cycle)
       ↓
SignalGenerator    →  Rule-based BUY / HOLD / SELL scoring
       ↓
ReportGenerator    →  matplotlib charts (price, signal, sentiment)
       ↓
EmailAlertAgent    →  HTML digest with embedded charts → N recipients
       ↓
  SQLite DB        ←  Every stage upserts / deduplicates results
       ↓
Flask Dashboard    →  Mobile-first browser UI
```

---

## ✨ Features

| Feature | Status |
|---|---|
| Live NSE/yfinance market data | ✅ |
| RSS news aggregation + sentiment | ✅ |
| Gemini AI batch analysis | ✅ |
| BUY / HOLD / SELL signals with confidence % | ✅ |
| matplotlib report charts (PNG) | ✅ |
| HTML email digest → multiple recipients | ✅ |
| SQLite persistence (upsert / no duplicates) | ✅ |
| Mobile-first dark/light web dashboard | ✅ |
| Interactive stock picker (80+ NSE symbols) | ✅ |
| Multi-email tag input (N users per run) | ✅ |
| CLI + scheduler + REST API | ✅ |

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- [Google Gemini API key](https://aistudio.google.com/app/apikey) (free tier works)
- Gmail account with an [App Password](https://myaccount.google.com/apppasswords) for email alerts

### 2. Install

```bash
git clone <repo-url>
cd MarkerMind_AI

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configure `.env`

Create a `.env` file in the project root:

```env
# AI Provider
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Email (Gmail SMTP with App Password)
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your_gmail_app_password

# Flask
FLASK_PORT=5050
FLASK_SECRET_KEY=change_me_to_a_random_string
```

### 4. (Optional) Edit `config/config.yaml`

Set default stocks and the default sender/recipient for unattended scheduled runs:

```yaml
agents:
  market_data_agent:
    stocks: ["TCS", "INFY", "RELIANCE", "HDFCBANK", "DMART"]

  email_alert_agent:
    smtp:
      sender: "you@gmail.com"
      recipients:
        - "you@gmail.com"
```

---

## 🖥️ How to Run

### Option A — Web Dashboard (recommended)

```bash
python3 app.py
# Open http://localhost:5050
```

- Click **Run Analysis** (navbar or the ▶ floating button on mobile)
- **Pick stocks** from 80+ NSE symbols grouped by sector, use the search box, or choose a preset
- **Add recipients** — type emails one by one (press `Enter` or `,` after each); add as many as you need
- Hit **Run Analysis** — the pipeline runs in the background, the page refreshes when done

### Option B — CLI

```bash
# Run once with defaults from config.yaml
python3 main.py

# Custom stocks and single recipient
python3 main.py --stocks TCS,INFY,HDFCBANK --email you@gmail.com

# Multiple recipients
python3 main.py --stocks RELIANCE,ONGC --email alice@co.com,bob@co.com

# Scheduled mode (runs every N minutes as set in config.yaml)
python3 main.py --schedule
python3 main.py --stocks TCS,INFY --email you@gmail.com --schedule

# Browse available stocks
python3 main.py --list-stocks

# Search stocks by name or sector
python3 main.py --search-stocks banking
python3 main.py --search-stocks pharma
```

### Option C — REST API

```bash
# Trigger pipeline programmatically
curl -X POST http://localhost:5050/api/run \
  -H "Content-Type: application/json" \
  -d '{"stocks": ["TCS","INFY"], "email": ["alice@co.com","bob@co.com"]}'

# Get latest signals
curl http://localhost:5050/api/signals

# Browse the stock catalog
curl http://localhost:5050/api/stocks
curl "http://localhost:5050/api/stocks?search=banking"

# Pipeline status
curl http://localhost:5050/api/pipeline/status
```

---

## 🌐 Web Dashboard Pages

| URL | Description |
|---|---|
| `/` | Dashboard — KPI cards, signals table, news feed, signal donut chart |
| `/stock/<SYMBOL>` | Stock detail — price history, AI analysis, charts, bulk deals |
| `/alerts` | Email alert history — recipients shown as coloured pill tags |
| `/api/*` | REST JSON API endpoints |

### Dashboard Features
- **Dark / Light mode** toggle (persists via localStorage)
- **Mobile bottom navigation** — Dashboard, Alerts, ▶ Run (floating pill)
- **Real-time pipeline badge** — Idle / Running (animated) / Done ✓
- **Toast notifications** for every action
- **No page stale data** — upsert logic ensures each run refreshes rather than duplicates

---

## 📋 CLI Reference

```
python3 main.py [OPTIONS]

Options:
  --stocks SYM1,SYM2,...    NSE symbols to analyse (overrides config.yaml)
  --email  E1,E2,...        Recipient emails (overrides config.yaml)
  --schedule                Run on a repeating schedule (interval in config.yaml)
  --list-stocks             Print all 80+ supported NSE stocks by sector and exit
  --search-stocks KEYWORD   Search stocks by sector name or symbol keyword and exit
  --config PATH             Path to config.yaml (default: config/config.yaml)
```

---

## 🗂️ Project Structure

```
MarkerMind_AI/
├── main.py                      # CLI entry point (--stocks, --email, --schedule, --list-stocks)
├── app.py                       # Flask web server + REST API
├── config/
│   └── config.yaml              # Non-sensitive configuration
├── .env                         # Secrets (API keys, SMTP) — never commit this
├── requirements.txt
├── src/
│   ├── orchestrator.py          # 6-stage agent pipeline with apply_overrides()
│   ├── agents/
│   │   ├── base_agent.py        # ABC with initialize / execute / cleanup
│   │   ├── market_data_agent.py # NSE primary + yfinance fallback
│   │   ├── news_agent.py        # RSS feeds (no API key needed)
│   │   ├── ai_analysis_agent.py # Gemini / OpenAI dual-provider, batched
│   │   ├── signal_generator_agent.py  # Rule-based BUY/HOLD/SELL
│   │   ├── report_generator_agent.py  # matplotlib PNG charts
│   │   └── email_alert_agent.py       # STARTTLS HTML digest, N recipients
│   ├── data_sources/
│   │   └── nse_fetcher.py
│   ├── database/
│   │   └── db_manager.py        # SQLite / SQLAlchemy — upsert on every stage
│   └── models/
│       ├── market_data.py
│       └── analysis_models.py
├── frontend/
│   ├── templates/               # Jinja2 templates (mobile-first dark UI)
│   │   ├── base.html            # Navbar, bottom nav, Run modal, theme toggle
│   │   ├── dashboard.html       # KPIs, signals, news, doughnut chart
│   │   ├── stock_detail.html    # Per-stock detail page
│   │   └── alerts.html          # Email history with recipient tags
│   └── static/
│       ├── style.css            # CSS variables, dark/light themes
│       └── main.js              # Stock picker, email tag input, pipeline polling
├── data/
│   ├── marketmind.db            # SQLite database (auto-created)
│   └── reports/                 # Generated chart PNGs
└── logs/
    └── marketmind.log
```

---

## ⚙️ Configuration Reference (`config/config.yaml`)

```yaml
agents:
  market_data_agent:
    enabled: true
    stocks: ["TCS", "WIPRO", "DMART", "RELIANCE", "INFY"]  # default watchlist

  news_agent:
    enabled: true
    max_articles_per_stock: 5
    lookback_hours: 24

  ai_analysis_agent:
    enabled: true
    provider: "gemini"           # "gemini" or "openai"
    model: "gemini-2.5-flash"    # or "gpt-4o-mini" for OpenAI

  signal_generator_agent:
    risk_tolerance: "medium"     # low / medium / high

  email_alert_agent:
    smtp:
      host: "smtp.gmail.com"
      port: 587
      sender: "you@gmail.com"
      recipients:
        - "you@gmail.com"        # default recipients (overridden at runtime)

scheduler:
  run_interval_minutes: 30       # used by --schedule mode
```

---

## 🔌 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Dashboard HTML page |
| `GET` | `/stock/<symbol>` | Stock detail HTML page |
| `GET` | `/alerts` | Alert history HTML page |
| `GET` | `/api/signals?limit=N&symbol=SYM` | Latest trading signals (JSON) |
| `GET` | `/api/news?limit=N&symbol=SYM` | Latest news articles (JSON) |
| `GET` | `/api/summary` | Dashboard KPI summary (JSON) |
| `GET` | `/api/alerts?limit=N` | Alert history (JSON) |
| `GET` | `/api/stocks?search=KEYWORD` | NSE stock catalog by sector (JSON) |
| `GET` | `/api/stock/<symbol>/history` | Price history (JSON) |
| `GET` | `/api/pipeline/status` | `{"running": true/false}` |
| `POST` | `/api/run` | Trigger pipeline; body: `{"stocks":[…], "email":[…]}` |
| `GET` | `/charts/<filename>` | Serve generated PNG charts |

---

## 🔒 Security

| Concern | Implementation |
|---|---|
| API credentials | Env vars only (`.env`); never in `config.yaml` or source |
| SMTP password | `SMTP_PASSWORD` env var; STARTTLS enforced |
| `.env` in git | Listed in `.gitignore` |
| SQL injection | SQLAlchemy ORM parameterised queries |
| Duplicate data | Upsert by `symbol + date` for signals/analysis; deduplicate news by URL |
| Error handling | Every agent stage try/caught; failures don't crash the pipeline |

---

## 📊 Supported NSE Stocks (80+)

Stocks are grouped by sector in the web UI and CLI. Use `--list-stocks` to see all:

| Sector | Examples |
|---|---|
| IT | TCS, INFY, WIPRO, HCLTECH, TECHM, LTIM… |
| Banking | HDFCBANK, ICICIBANK, SBIN, KOTAKBANK… |
| Finance | BAJFINANCE, BAJAJFINSV, CHOLAFIN… |
| Pharma | SUNPHARMA, DRREDDY, CIPLA, DIVISLAB… |
| FMCG | HINDUNILVR, ITC, NESTLEIND, BRITANNIA… |
| Energy | RELIANCE, ONGC, NTPC, POWERGRID… |
| Auto | MARUTI, TATAMOTORS, M&M, BAJAJ-AUTO… |
| Retail/Consumer | DMART, TITAN, TRENT, ZOMATO, NYKAA… |
| Metals | TATASTEEL, JSWSTEEL, HINDALCO… |
| Infra/Cement | ULTRACEMCO, LT, SIEMENS, AMBUJACEM… |

---

## 🗺️ Roadmap

- [x] Multi-agent pipeline (6 stages)
- [x] Gemini + OpenAI dual-provider support
- [x] Mobile-first web dashboard with dark/light mode
- [x] Interactive stock picker with sector tabs and search
- [x] Multi-email tag input (send to N users in one run)
- [x] Upsert deduplication (no stale/duplicate data per day)
- [x] CLI flags: `--stocks`, `--email`, `--list-stocks`, `--search-stocks`
- [ ] WhatsApp / Telegram notifications
- [ ] Portfolio tracker (P&L across multiple runs)
- [ ] Options chain analysis
- [ ] ML-based signal confidence scoring
- [ ] Docker container for one-command deployment
- [ ] Multi-region support (BSE, global markets)

---

## ⚠️ Disclaimer

MarketMind AI is an educational / research tool. Nothing it generates constitutes financial advice. Always conduct your own due diligence before making investment decisions.

---

**Built with ❤️ for retail investors and traders**
