# 📊 MarketMind AI – Financial Intelligence Agent System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green)](https://flask.palletsprojects.com)
[![Gemini](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-orange)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MarketMind AI is an autonomous multi-agent system that monitors Indian stock markets (NSE), generates AI-powered trading signals, delivers rich HTML email digests, and now includes **Phase 2 features**: technical indicators (RSI/MACD/Bollinger Bands), a stock screener, signal backtesting, user authentication, per-user portfolio management, and Telegram alerts — all without manual intervention. It ships with a **mobile-first web dashboard** and a full **CLI**.

---

## 🏗️ Agent Pipeline

```
MarketDataAgent       →  NSE API / yfinance fallback
       ↓
  NewsAgent            →  RSS feeds (Google News, ET Markets, Moneycontrol)
       ↓
AIAnalysisAgent        →  Google Gemini 2.5 Flash (batched per cycle)
       ↓
SignalGenerator        →  Rule-based BUY / HOLD / SELL scoring
       ↓
TechnicalIndicators    →  RSI / MACD / Bollinger Bands (yfinance + DB fallback)
       ↓
ReportGenerator        →  matplotlib charts (price, signal, sentiment)
       ↓
EmailAlertAgent        →  HTML digest with embedded charts → N recipients
  + TelegramAlerts     →  Real-time Telegram bot notifications
       ↓
  SQLite DB            ←  Every stage upserts / deduplicates results
       ↓
Flask Dashboard        →  Mobile-first browser UI (auth, portfolio, screener)
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
| **Technical indicators — RSI, MACD, Bollinger Bands** | ✅ Phase 2 |
| **Stock screener with multi-criteria filters** | ✅ Phase 2 |
| **Signal backtesting with P&L performance tracking** | ✅ Phase 2 |
| **User authentication (register / login / logout)** | ✅ Phase 2 |
| **Per-user portfolio with real-time unrealised P&L** | ✅ Phase 2 |
| **Per-user watchlist** | ✅ Phase 2 |
| **Telegram bot alerts** | ✅ Phase 2 |

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
FLASK_SECRET_KEY=change_me_to_a_random_string   # required for session security

# Telegram (Phase 2 — optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
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
| `/stock/<SYMBOL>` | Stock detail — price history, **RSI / MACD / Bollinger charts**, AI analysis, bulk deals |
| `/screener` | **Stock Screener** — filter by sector, signal, RSI range, MACD trend |
| `/backtest` | **Signal Backtesting** — simulate historical signals, P&L log, equity curve chart |
| `/portfolio` | **Portfolio dashboard** — open positions, real-time P&L, watchlist, Telegram config |
| `/login` | User login page |
| `/register` | User registration page |
| `/logout` | Log out and redirect to login |
| `/alerts` | Email alert history — recipients shown as coloured pill tags |
| `/subscribe` | **Subscription sign-up** — pick stocks, enter email, subscribe for 2×/day digests |
| `/unsubscribe?token=…` | One-click unsubscribe |
| `/api/*` | REST JSON API endpoints |

### Dashboard Features
- **Dark / Light mode** toggle (persists via localStorage)
- **Mobile bottom navigation** — Dashboard, Markets, Screener, Portfolio/Login, ▶ Run
- **Real-time pipeline badge** — Idle / Running (animated) / Done ✓
- **Toast notifications** for every action
- **India / Global news tabs** — switch between Indian market news and world market news
- **No page stale data** — upsert logic ensures each run refreshes rather than duplicates
- **Technical indicator charts** on every stock detail page (RSI, MACD, Bollinger Bands)
- **Login-aware nav** — shows Portfolio/Logout when authenticated, Login otherwise

### Stock Screener (`/screener`)

Filter 80+ NSE stocks simultaneously using any combination of:
- **Sector** — IT, Banking, Finance, Auto, Pharma, FMCG, Energy, Retail, Metals, Infra/Cement
- **Technical signal** — BUY / SELL / HOLD (from indicator summary)
- **RSI range** — e.g. oversold (<30), overbought (>70), neutral (40–60)
- **MACD trend** — bullish / bearish / neutral

Results show RSI value, MACD trend direction, Bollinger %B, MA20 price, and bullish vs bearish signal count for each stock. The screener fetches live indicators with a 10-minute cache so repeated queries are instant.

---

### Signal Backtesting (`/backtest`)

Simulates every stored trading signal for a symbol using a **5-day forward price window**:
- Select any NSE symbol from the input field and click **Run Backtest**
- Results include: total trades, win/loss count, win rate %, average return %
- Full trade log with entry date, exit date, entry/exit prices, and per-trade P&L
- **Cumulative equity curve** chart (Chart.js line chart)

Backtest data is sourced from existing `TradingSignalRecord` rows in the SQLite DB — run the AI pipeline first to populate signals.

---

### User Authentication

Register at `/register`, sign in at `/login`. Passwords are hashed with **bcrypt** (no plain-text storage). Flask-Login manages session cookies. Protected pages (`/portfolio`) redirect to `/login` automatically.

---

### Portfolio Management (`/portfolio`)

After signing in:
- **Add positions** — enter symbol, quantity, average buy price, and optional notes
- **Live P&L** — current price is fetched from the DB; unrealised gain/loss and % return shown per position
- **Close positions** — mark as closed at a specified sell price
- **Delete positions** — remove positions from tracking
- **Watchlist** — add/remove any NSE symbol; chips link directly to stock detail page
- **Telegram configuration** — enter your bot token and chat ID, then test with one click

---

### Telegram Alerts

MarketMind AI sends a **formatted signal summary** to your Telegram every time the AI pipeline runs — whether triggered manually from the dashboard, via the CLI, or by the automatic 2×/day scheduler.

#### What the Telegram message contains

```
📊 MarketMind AI Signal Alert

🟢 TCS      →  BUY   (82%)
🔴 INFY     →  SELL  (71%)
🟡 HDFCBANK →  HOLD
🟢 RELIANCE →  BUY   (76%)
…and 3 more signals in the dashboard.

🔗 Open Dashboard
```

#### When alerts are sent

| Trigger | Telegram sent? |
|---|---|
| Manual **Run Analysis** from dashboard | ✅ Yes — immediately after pipeline completes |
| CLI `python3 main.py` | ✅ Yes — via `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` env vars |
| **8:45 AM IST** automated scheduler | ✅ Yes — after each subscriber digest |
| **4:15 PM IST** automated scheduler | ✅ Yes — after each subscriber digest |
| `/api/telegram/test` | ✅ Yes — sends a one-off test message only |

#### Who receives the alerts

- Any registered user who has saved their bot token + chat ID on the **Portfolio page** and has **alerts enabled**
- Additionally, the process-level `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` in `.env` always receives alerts — useful before any user registers, or when running headlessly via CLI / cron

#### Setup (2 minutes)

1. Open Telegram → search **`@BotFather`** → send `/newbot` → copy the **Bot Token**
2. Start a chat with your new bot (send it any message)
3. Get your Chat ID — easiest way: message **`@userinfobot`** on Telegram and it replies instantly
4. Add to your `.env`:

```env
TELEGRAM_BOT_TOKEN=1234567890:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=123456789
```

5. Restart the server — alerts will fire automatically from the next pipeline run
6. Test immediately: go to `/portfolio` → paste token + chat ID → click **Save** → click **Test**

> **Tip:** The bot is free. Your phone number is never in the token or chat ID. If the token is ever compromised, open `@BotFather` → `/revoke` → pick your bot — a new token is issued instantly.

---

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
├── app.py                       # Flask web server + REST API + Phase 2 routes
├── config/
│   └── config.yaml              # Non-sensitive configuration
├── .env                         # Secrets (API keys, SMTP, Telegram) — never commit this
├── requirements.txt
├── src/
│   ├── orchestrator.py          # 6-stage agent pipeline with apply_overrides()
│   ├── stock_discovery.py       # Dynamic NSE equity list fetcher + cache
│   ├── telegram_utils.py        # Telegram message builder + send_pipeline_alerts()
│   ├── agents/
│   │   ├── base_agent.py        # ABC with initialize / execute / cleanup
│   │   ├── market_data_agent.py # NSE primary + yfinance fallback
│   │   ├── news_agent.py        # RSS feeds (no API key needed)
│   │   ├── ai_analysis_agent.py # Gemini / OpenAI dual-provider, batched
│   │   ├── signal_generator_agent.py  # Rule-based BUY/HOLD/SELL
│   │   ├── report_generator_agent.py  # matplotlib PNG charts
│   │   └── email_alert_agent.py       # STARTTLS HTML digest, N recipients
│   ├── technical/               # ── Phase 2 ──
│   │   ├── __init__.py          # Exports get_indicators, compute_rsi/macd/bollinger
│   │   └── indicators.py        # RSI, MACD, Bollinger Bands, MA engine (yfinance + DB fallback)
│   ├── data_sources/
│   │   └── nse_fetcher.py
│   ├── database/
│   │   └── db_manager.py        # SQLite / SQLAlchemy ORM — upsert + User/Portfolio/Watchlist models
│   └── models/
│       ├── market_data.py
│       └── analysis_models.py
├── frontend/
│   ├── templates/               # Jinja2 templates (mobile-first dark UI)
│   │   ├── base.html            # Navbar (Screener, Backtest, Portfolio, Login/Logout), theme toggle
│   │   ├── dashboard.html       # KPIs, signals, India + Global news tabs, doughnut chart
│   │   ├── stock_detail.html    # Per-stock: price, RSI/MACD/Bollinger charts, AI analysis
│   │   ├── screener.html        # ── Phase 2 ── Multi-criteria stock screener
│   │   ├── backtest.html        # ── Phase 2 ── Signal backtesting + equity curve
│   │   ├── portfolio.html       # ── Phase 2 ── Portfolio + watchlist + Telegram config
│   │   ├── login.html           # ── Phase 2 ── Login form
│   │   ├── register.html        # ── Phase 2 ── Registration form
│   │   ├── alerts.html          # Email history with recipient tags
│   │   └── subscribe.html       # Subscription sign-up form with live stock picker
│   └── static/
│       ├── style.css            # CSS variables, dark/light themes
│       └── main.js              # Stock picker, email tag input, pipeline polling
├── data/
│   ├── marketmind.db            # SQLite database (auto-created; includes users/portfolio/watchlist)
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
| `GET` | `/screener` | **Stock screener page** |
| `GET` | `/backtest` | **Signal backtesting page** |
| `GET` | `/portfolio` | **Portfolio page** (login required) |
| `GET` | `/login` | Login page |
| `GET` | `/register` | Registration page |
| `GET` | `/logout` | Log out |
| `GET` | `/alerts` | Alert history HTML page |
| `GET` | `/subscribe` | Subscription sign-up page |
| `GET` | `/unsubscribe?token=TOKEN` | One-click unsubscribe |
| `GET` | `/api/signals?limit=N&symbol=SYM` | Latest trading signals (JSON) |
| `GET` | `/api/news?limit=N&symbol=SYM` | Latest news articles — Indian market (JSON) |
| `GET` | `/api/news/global?limit=N` | World / global market news (JSON) |
| `GET` | `/api/summary` | Dashboard KPI summary — includes subscriber count (JSON) |
| `GET` | `/api/alerts?limit=N` | Alert history (JSON) |
| `GET` | `/api/stocks?search=KEYWORD` | NSE stock catalog — hardcoded (fast, JSON) |
| `GET` | `/api/stocks/live?search=KEYWORD` | Full NSE equity list from live CSV (JSON) |
| `GET` | `/api/stock/<symbol>/history` | Price history (JSON) |
| `GET` | `/api/stock/<symbol>/indicators` | **RSI / MACD / Bollinger Bands (10-min cached, JSON)** |
| `GET` | `/api/pipeline/status` | `{"running": true/false}` |
| `GET` | `/api/screener?sector=&signal=&rsi_min=&rsi_max=&macd_trend=` | **Screener results (JSON)** |
| `GET` | `/api/backtest/<symbol>` | **Backtest results for symbol (JSON)** |
| `GET` | `/api/portfolio` | **Open positions with live P&L** (auth required, JSON) |
| `POST` | `/api/portfolio/add` | **Add a position**; body: `{"symbol", "quantity", "avg_buy_price", "notes"}` |
| `POST` | `/api/portfolio/close/<id>` | **Close a position**; body: `{"sell_price"}` |
| `DELETE` | `/api/portfolio/delete/<id>` | **Delete a position** |
| `GET` | `/api/watchlist` | **Get user watchlist** (auth required, JSON) |
| `POST` | `/api/watchlist/toggle/<symbol>` | **Add or remove symbol from watchlist** |
| `POST` | `/api/telegram/configure` | **Save Telegram bot token + chat ID** |
| `POST` | `/api/telegram/test` | **Send a test Telegram message** |
| `POST` | `/api/run` | Trigger pipeline; body: `{"stocks":[…], "email":[…]}` |
| `POST` | `/api/subscribe` | Subscribe or update watchlist; body: `{"email":"…", "stocks":[…]}` |
| `POST` | `/api/unsubscribe` | Unsubscribe; body: `{"token":"…"}` |
| `POST` | `/api/subscription/lookup` | Email the user their unsubscribe link; body: `{"email":"…"}` |
| `GET` | `/api/subscribers` | List active subscribers (admin) |
| `GET` | `/charts/<filename>` | Serve generated PNG charts |

---

## 🔒 Security

| Concern | Implementation |
|---|---|
| API credentials | Env vars only (`.env`); never in `config.yaml` or source |
| SMTP password | `SMTP_PASSWORD` env var; STARTTLS enforced |
| User passwords | Hashed with **bcrypt** (salted); plain-text never stored |
| Session security | Flask-Login cookies; signed by `FLASK_SECRET_KEY` |
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

**Phase 1 — Complete ✅**
- [x] Multi-agent pipeline (6 stages)
- [x] Gemini + OpenAI dual-provider support
- [x] Mobile-first web dashboard with dark/light mode
- [x] Interactive stock picker with sector tabs and search
- [x] Multi-email tag input (send to N users in one run)
- [x] Upsert deduplication (no stale/duplicate data per day)
- [x] CLI flags: `--stocks`, `--email`, `--list-stocks`, `--search-stocks`
- [x] Global / world market news tab (Reuters, Yahoo Finance, Google News)
- [x] Email subscription system with 2×/day automated digest (APScheduler)
- [x] Dynamic live NSE stock list via open NSE CSV (1000+ stocks)

**Phase 2 — Complete ✅**
- [x] **Technical indicators — RSI (14), MACD (12,26,9), Bollinger Bands (20,2)** with interactive Chart.js panels on stock detail page
- [x] **Stock screener** — filter 80+ NSE stocks by sector, signal, RSI range, MACD trend simultaneously
- [x] **Signal backtesting** — 5-day forward P&L simulation with win rate stats and equity curve chart
- [x] **User authentication** — register / login / logout with bcrypt password hashing (Flask-Login)
- [x] **Per-user portfolio management** — add/close/delete positions, real-time unrealised P&L
- [x] **Per-user watchlist** — add/remove symbols, chips link to stock detail
- [x] **Telegram bot alerts** — configure bot token + chat ID via UI; `/api/telegram/test` for one-click verification
- [x] RSI/MACD/Bollinger chart panels embedded in stock detail page
- [x] Login-aware navigation (Portfolio/Logout when signed in, Login otherwise)

**Phase 3 — Planned**
- [ ] Options chain analysis
- [ ] ML-based signal confidence scoring
- [ ] Docker container for one-command deployment
- [ ] Multi-region support (BSE, global markets)
- [ ] WhatsApp notifications (Twilio)
- [ ] Strategy builder (custom entry/exit rules)

---

## ⚠️ Disclaimer

MarketMind AI is an educational / research tool. Nothing it generates constitutes financial advice. Always conduct your own due diligence before making investment decisions.

---

**Built for retail investors and traders**
