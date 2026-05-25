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
| Dynamic live stock list from NSE open data | ✅ |
| Multi-email tag input (N users per run) | ✅ |
| **Email subscription — 2× daily automated digest** | ✅ |
| **Global / world market news tab** | ✅ |
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
| `/` | Dashboard — KPI cards, signals table, **India + Global news tabs**, signal donut chart |
| `/stock/<SYMBOL>` | Stock detail — price history, AI analysis, charts, bulk deals |
| `/alerts` | Email alert history — recipients shown as coloured pill tags |
| `/subscribe` | **Subscription sign-up** — pick stocks, enter email, subscribe for 2×/day digests |
| `/unsubscribe?token=…` | One-click unsubscribe |
| `/api/*` | REST JSON API endpoints |

### Dashboard Features
- **Dark / Light mode** toggle (persists via localStorage)
- **Mobile bottom navigation** — Dashboard, Alerts, Subscribe, ▶ Run (floating pill)
- **Real-time pipeline badge** — Idle / Running (animated) / Done ✓
- **Toast notifications** for every action
- **India / Global news tabs** — switch between Indian market news and world market news
- **No page stale data** — upsert logic ensures each run refreshes rather than duplicates

### Subscribe Page (`/subscribe`)
A standalone subscription page that works like a lightweight SaaS product:
- Enter your email address and choose stocks to track
- The app sends a full AI digest **2 times per day**:
  - **8:45 AM IST** — pre-market signal preview before NSE opens
  - **4:15 PM IST** — post-market summary after NSE closes
- Unsubscribe with a single click (token-based link included in every email)
- No login required — email is the identity

---

## 🌍 Global Market News

The dashboard has a two-tab news panel:

| Tab | Coverage |
|---|---|
| 🇮🇳 India | ET Markets, Moneycontrol, Google News India (per-stock) |
| 🌐 Global | Reuters Business & Tech, Yahoo Finance, Google News Global, Investing.com, Livemint |

Global news is fetched every time the pipeline runs (tagged internally as `__GLOBAL__` in the DB) and rendered live in the browser tab via `/api/news/global`.

---

## 📬 Email Subscription System

### How it works

1. Visit `/subscribe` in the browser (or navigate via the *Subscribe* navbar link)
2. Choose the NSE stocks you want to track
3. Enter your email and click **Subscribe / Update Watchlist**
4. Automated digests land in your inbox **2 times every trading day**:
   - **08:45 AM IST** — pre-market analysis before NSE opens (9:15 AM)
   - **04:15 PM IST** — post-market recap after NSE closes (3:30 PM)
5. Each email contains: AI analysis, BUY/HOLD/SELL signals, news sentiment, embedded charts
6. Click the unsubscribe link at the bottom of any email to opt out instantly

### Updating your watchlist (re-subscribe with same email)

You can re-subscribe at any time with the same email address and a **different stock list** — your watchlist is updated immediately and a confirmation email is sent. The unsubscribe token/link stays the same.

| Action | What happens |
|---|---|
| Submit with a **new email** | New subscription created; welcome email sent |
| Submit with an **existing email + same stocks** | No-op update; update confirmation email sent |
| Submit with an **existing email + new stocks** | Watchlist replaced with new list; update confirmation email sent |
| Submit with an **existing email** (previously unsubscribed) | Subscription reactivated with new stocks; welcome email sent |

> **Re-subscribing does not change your unsubscribe token** — your existing unsubscribe link stays valid.

### Confirmation emails

| Scenario | Email received |
|---|---|
| First-time subscribe | **Welcome email** — schedule, chosen stocks, unsubscribe link |
| Re-subscribe / update | **Watchlist updated email** — new stock list, next digest time, unsubscribe link |
| Request unsubscribe link | **Management email** — unsubscribe link resent |
| Scheduled digest | **Full AI digest** — signals, analysis, charts + unsubscribe link in footer |

### Subscription API

```bash
# Subscribe (new)
curl -X POST http://localhost:5050/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "stocks": ["TCS","INFY","HDFCBANK"]}'
# Response: {"status": "subscribed", "email": "...", "stocks": [...], "unsubscribe_url": "..."}

# Update watchlist (same email, different stocks)
curl -X POST http://localhost:5050/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "stocks": ["RELIANCE","ONGC","NTPC"]}'
# Response: {"status": "updated", "email": "...", "stocks": [...], "unsubscribe_url": "..."}

# Unsubscribe
curl -X POST http://localhost:5050/api/unsubscribe \
  -H "Content-Type: application/json" \
  -d '{"token": "TOKEN_FROM_EMAIL"}'

# Resend unsubscribe link via email
curl -X POST http://localhost:5050/api/subscription/lookup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'

# List active subscribers (admin)
curl http://localhost:5050/api/subscribers
```

### Scheduler details

The scheduler is started automatically when you run `python3 app.py`. It uses APScheduler 3.x with timezone `Asia/Kolkata`. To change the times, edit `_start_scheduler()` in `app.py`.

---

## 🖥️ Deployment — Running 24/7

The subscription scheduler lives **inside the Flask process**. The app must be running when the scheduled times (8:45 AM and 4:15 PM IST) arrive or those digests will be skipped (APScheduler does not backfill missed jobs).

### Option A — `systemd` service *(recommended for always-on)*

A ready-made service file is included at `marketmind.service`.

```bash
# 1. Copy the service file
sudo cp marketmind.service /etc/systemd/system/

# 2. Reload systemd and enable auto-start on reboot
sudo systemctl daemon-reload
sudo systemctl enable marketmind

# 3. Start the service
sudo systemctl start marketmind

# 4. Check it's running
sudo systemctl status marketmind

# View live logs
sudo journalctl -u marketmind -f
```

To stop or restart:
```bash
sudo systemctl stop marketmind
sudo systemctl restart marketmind
```

### Option B — `nohup` *(quick background run, no reboot survival)*

```bash
cd /home/rajasekharreddysuggu/code/MarkerMind_AI
nohup python3 app.py > logs/app.log 2>&1 &
echo $! > logs/app.pid        # save the PID

# Tail logs
tail -f logs/app.log

# Stop later
kill $(cat logs/app.pid)
```

### Option C — Foreground terminal *(development / testing)*

```bash
python3 app.py
# Open http://localhost:5050
# Press Ctrl+C to stop
```

### Which option should I use?

| Scenario | Recommended option |
|---|---|
| Development / testing / demo | Option C — foreground terminal |
| Always-on on a personal Linux machine | Option A — systemd |
| Quick overnight run without rebooting | Option B — nohup |
| Cloud VM / VPS (DigitalOcean, AWS EC2…) | Option A — systemd |

---

## 🧪 End-to-End Test Guide

Use this checklist to verify the complete subscription flow **without waiting for 8:45 AM or 4:15 PM**.

### Prerequisites

- App is running (`python3 app.py`)
- `.env` has valid `GEMINI_API_KEY`, `SMTP_USER`, and `SMTP_PASSWORD`

### Step 1 — Subscribe

Open the browser: **http://localhost:5050/subscribe**

Or via curl:
```bash
curl -X POST http://localhost:5050/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "you@gmail.com", "stocks": ["TCS","INFY"]}'
```

Expected response:
```json
{
  "status": "subscribed",
  "email": "you@gmail.com",
  "stocks": ["TCS", "INFY"],
  "unsubscribe_url": "http://localhost:5050/unsubscribe?token=<TOKEN>"
}
```

### Step 2 — Confirm the subscriber was saved

```bash
curl http://localhost:5050/api/subscribers
```

Expected: your email appears with `last_sent_at: null` (not yet sent).

### Step 3 — Trigger an immediate test digest

```bash
curl -X POST http://localhost:5050/api/test-digest \
  -H "Content-Type: application/json" \
  -d '{"email": "you@gmail.com"}'
```

This fires the full pipeline immediately for that subscriber — no need to wait for the scheduled time.

Response:
```json
{"status": "started", "target": "you@gmail.com"}
```

The pipeline runs in a background thread. Watch progress in the terminal where `app.py` is running, or in `logs/marketmind.log`.

### Step 4 — Verify the email arrived

Check your inbox. The digest email contains:
- BUY / HOLD / SELL signals for each stock you subscribed to
- AI-generated summary and reasoning
- News sentiment snippets
- Embedded price charts (PNG)
- A one-click **Unsubscribe** link at the bottom

### Step 5 — Confirm `last_sent_at` was updated

```bash
curl http://localhost:5050/api/subscribers
```

`last_sent_at` should now show the current timestamp — confirming delivery.

### Step 6 — Test unsubscribe

Use the link from the email, or:
```bash
curl -X POST http://localhost:5050/api/unsubscribe \
  -H "Content-Type: application/json" \
  -d '{"token": "<TOKEN_FROM_SUBSCRIBE_RESPONSE>"}'
```

Response: `{"status": "unsubscribed"}`

Verify: `GET /api/subscribers` no longer lists that email.

### Quick reference — test commands

```bash
# Subscribe (new)
curl -X POST http://localhost:5050/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "you@gmail.com", "stocks": ["TCS","INFY","HDFCBANK"]}'

# Update watchlist (same email, new stocks — returns "status":"updated")
curl -X POST http://localhost:5050/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "you@gmail.com", "stocks": ["RELIANCE","ONGC","DMART"]}'

# List subscribers
curl http://localhost:5050/api/subscribers

# Fire immediate digest (test without waiting for scheduled time)
curl -X POST http://localhost:5050/api/test-digest \
  -H "Content-Type: application/json" \
  -d '{"email": "you@gmail.com"}'

# Fire digest for ALL subscribers at once
curl -X POST http://localhost:5050/api/test-digest \
  -H "Content-Type: application/json" \
  -d '{}'

# Resend unsubscribe link to email
curl -X POST http://localhost:5050/api/subscription/lookup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@gmail.com"}'

# Unsubscribe
curl -X POST http://localhost:5050/api/unsubscribe \
  -H "Content-Type: application/json" \
  -d '{"token": "TOKEN"}'

# Check pipeline status while digest is running
curl http://localhost:5050/api/pipeline/status
```

### Scheduler behaviour summary

| Situation | What happens |
|---|---|
| App running, 8:45 AM IST arrives | Digests auto-sent to all active subscribers |
| App running, 4:15 PM IST arrives | Digests auto-sent to all active subscribers |
| App was stopped at scheduled time | That digest is **skipped** (not backfilled) |
| App restarted after being stopped | Scheduler resumes; next window fires normally |
| New subscriber added between schedule windows | They receive the next scheduled digest automatically |

---

## 📡 Dynamic NSE Stock List

The app fetches the full NSE equity list (1700+ stocks) from the NSE open-data CSV at runtime:

```
https://www1.nseindia.com/content/equities/EQUITY_L.csv
```

Results are cached in memory for **6 hours**. If the NSE CSV is unreachable (network issue, rate-limit), the system automatically falls back to the 80+ hardcoded catalog — so the UI never breaks.

### Stock discovery endpoints

```bash
# Get all NSE stocks dynamically grouped by sector (with company names)
curl http://localhost:5050/api/stocks/live

# Force-refresh the cache
curl "http://localhost:5050/api/stocks/live?refresh=1"

# Search any stock by symbol prefix or company name
curl "http://localhost:5050/api/stocks/live?search=HDFC"
```

The **Run Analysis** modal and **Subscribe** page both use the live endpoint with automatic fallback.

---

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
│   ├── stock_discovery.py       # Dynamic NSE equity list fetcher + cache
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
│   │   ├── base.html            # Navbar (+ Subscribe link), bottom nav, Run modal, theme toggle
│   │   ├── dashboard.html       # KPIs, signals, India + Global news tabs, doughnut chart
│   │   ├── stock_detail.html    # Per-stock detail page
│   │   ├── alerts.html          # Email history with recipient tags
│   │   └── subscribe.html       # Subscription sign-up form with live stock picker
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
| `GET` | `/subscribe` | Subscription sign-up page |
| `GET` | `/unsubscribe?token=TOKEN` | One-click unsubscribe |
| `GET` | `/api/signals?limit=N&symbol=SYM` | Latest trading signals (JSON) |
| `GET` | `/api/news?limit=N&symbol=SYM` | Latest news articles — Indian market (JSON) |
| `GET` | `/api/news/global?limit=N` | **World / global market news (JSON)** |
| `GET` | `/api/summary` | Dashboard KPI summary — includes subscriber count (JSON) |
| `GET` | `/api/alerts?limit=N` | Alert history (JSON) |
| `GET` | `/api/stocks?search=KEYWORD` | NSE stock catalog — hardcoded (fast, JSON) |
| `GET` | `/api/stocks/live?search=KEYWORD` | **Full NSE equity list from live CSV (JSON)** |
| `GET` | `/api/stock/<symbol>/history` | Price history (JSON) |
| `GET` | `/api/pipeline/status` | `{"running": true/false}` |
| `POST` | `/api/run` | Trigger pipeline; body: `{"stocks":[…], "email":[…]}` |
| `POST` | `/api/subscribe` | Subscribe or **update watchlist**; body: `{"email":"…", "stocks":[…]}`; returns `"status":"subscribed"` or `"status":"updated"` |
| `POST` | `/api/unsubscribe` | Unsubscribe; body: `{"token":"…"}` |
| `POST` | `/api/subscription/lookup` | Email the user their unsubscribe link; body: `{"email":"…"}` |
| `GET` | `/api/subscribers` | List active subscribers (admin, no auth for MVP) |
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
- [x] **Global / world market news tab (Reuters, Yahoo Finance, Google News)**
- [x] **Email subscription system with 2×/day automated digest (APScheduler)**
- [x] **Dynamic live NSE stock list via open NSE CSV (1000+ stocks)**
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

**Built for retail investors and traders**
