# 📊 MarketMind AI – Financial Intelligence Agent System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green)](https://flask.palletsprojects.com)
[![Claude](https://img.shields.io/badge/AI-Claude%20Opus%204.5-blueviolet)](https://anthropic.com)
[![Gemini](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-orange)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MarketMind AI is an autonomous multi-agent system that monitors Indian stock markets (NSE), generates AI-powered trading signals, delivers rich HTML email digests, and ships a **mobile-first web dashboard** with technical indicators, stock screener, signal backtesting, user authentication, portfolio management, and real-time Telegram alerts — all without manual intervention.

---

## 🏗️ Agent Pipeline

```
MarketDataAgent       →  NSE API / yfinance fallback
       ↓
  NewsAgent            →  RSS feeds (Google News, ET Markets, Moneycontrol)
       ↓
AIAnalysisAgent        →  Claude / Gemini / OpenAI (batched per cycle)
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
| **Multi-provider AI — Claude (default), Gemini, OpenAI** | ✅ |
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
| **Per-user watchlist (drives scheduled Telegram alerts)** | ✅ |
| **Telegram bot alerts via deep-link subscribe flow** | ✅ |
| **Global market status strip (open/closed/public holiday)** | ✅ |
| **Setup warning banner on new machines (missing API key / SMTP / secret key)** | ✅ |
| **`/api/health` endpoint — config check for all services** | ✅ |
| **First-load fallback — popular stocks shown before pipeline runs** | ✅ |

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- An AI API key — **Claude** (recommended, Anthropic), Gemini (Google free tier), or OpenAI
- Gmail account with an [App Password](https://myaccount.google.com/apppasswords) for email alerts
- A Telegram bot token from [@BotFather](https://t.me/BotFather) *(optional, for mobile alerts)*

> **Full system requirements & platform-specific setup?** See [SYSTEM_REQUIREMENTS.md](SYSTEM_REQUIREMENTS.md) for Windows, macOS, Linux, and troubleshooting.

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
# ── AI Provider (choose one: claude | gemini | openai) ────────────────────────
LLM_PROVIDER=claude          # claude is the default

# Anthropic / Claude (recommended)
CLAUDE_API_KEY=sk-ant-api03-xxxxxxx
CLAUDE_MODEL=claude-opus-4-5

# Google Gemini (free tier available)
# GEMINI_API_KEY=your_gemini_api_key
# GEMINI_MODEL=gemini-2.5-flash

# OpenAI
# OPENAI_API_KEY=sk-xxxx

# ── Email (Gmail SMTP with App Password) ─────────────────────────────────────
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your_gmail_app_password

# ── Flask ────────────────────────────────────────────────────────────────────
FLASK_PORT=5050
FLASK_SECRET_KEY=change_me_to_a_long_random_string

# ── Telegram (optional) ──────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
# Leave blank for localhost/polling mode.
# Set to your public URL for webhook mode (production):
# TELEGRAM_WEBHOOK_URL=https://marketmind.yourdomain.com
```

> **Switch AI providers instantly** — just change `LLM_PROVIDER` and restart. No other changes needed.

#### 4. (Optional) Edit `config/config.yaml`

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

### Option A — One-click (start.sh / start.bat)

See **Quick Start → Option A** above. Handles venv, deps, `.env`, and startup in one step.

### Option B — Web Dashboard (manual)

```bash
source venv/bin/activate
python3 app.py
# Open http://localhost:5050
```

- Click **Run Analysis** in the navbar (or the ▶ button on mobile) — **login required**; non-logged-in users see a "Login to Run" button that redirects to `/login`
- **Pick stocks** from 80+ NSE symbols grouped by sector, use the search box, or choose a preset
- **Add recipients** (Step 2 — one-time) — type emails one by one (press `Enter` or `,` after each); add as many as you need
- **Optional: Daily Digest toggle** — if an email is entered, a `📬 Also subscribe for Daily Digest` toggle appears. Check it to also set up automated 2× daily emails for those stocks in one step — no need to visit `/daily-digest` separately
- Hit **Run Analysis** — the pipeline runs in the background, the page refreshes when done

### Option C — CLI

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

### Option D — REST API

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

| URL | Login Required | Description |
|---|---|---|
| `/` | No | Dashboard — KPI cards, signals table, **India + Global news tabs**, signal donut chart |
| `/stock/<SYMBOL>` | No | Stock detail — price history, **RSI / MACD / Bollinger charts**, AI analysis |
| `/screener` | No | **Stock Screener** — filter by sector, signal, RSI range, MACD trend |
| `/backtest` | No | **Signal Backtesting** — simulate historical signals, P&L log, equity curve chart |
| `/alerts` | No | Email alert history |
| `/subscribe` | No | **Daily Digest** — pick stocks, subscribe for automated 2×/day emails (nav shows "Daily Digest") |
| `/unsubscribe?token=…` | No | One-click email unsubscribe |
| `/login` | — | User login page |
| `/register` | — | User registration page |
| `/logout` | — | Log out |
| `/portfolio` | **Yes** | Portfolio, watchlist, Telegram subscribe |
| Run Analysis button | **Yes** | Opens the analysis modal; shows "Login to Run" → redirects to `/login` when not logged in |

### Dashboard Features
- **Dark / Light mode** toggle (persists via localStorage)
- **Mobile bottom navigation** — Dashboard, Markets, Screener, Portfolio/Login, ▶ Run
- **Real-time pipeline badge** — Idle / Running (animated) / Done ✓
- **NSE market status strip** — shows Open/Closed/Public Holiday + next opening time on all pages
- **Toast notifications** for every action
- **India / Global news tabs** — switch between Indian market news and world market news
- **No page stale data** — upsert logic ensures each run refreshes rather than duplicates
- **Technical indicator charts** on every stock detail page (RSI, MACD, Bollinger Bands)
- **Login-aware nav** — shows Portfolio/Logout when authenticated, Login otherwise
- **Login-gated Run Analysis** — navbar shows "Login to Run" for unauthenticated users; clicking redirects to `/login`

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
- **Telegram subscribe** — one-tap deep-link button; no manual chat ID entry

---

### Telegram Alerts

MarketMind AI uses a **single shared bot** owned by the app. Users subscribe via a one-tap Telegram deep-link — no manual chat ID entry required.

#### Subscribe flow

1. Create your bot: open Telegram → search **@BotFather** → `/newbot` → copy token → add to `.env` as `TELEGRAM_BOT_TOKEN`
2. Restart the app
3. Go to **Portfolio page** → scroll to **Telegram Alerts** → click **Subscribe to Alerts**
4. Click **Open Telegram** or **Open Telegram Web** (if desktop browser blocks the popup)
5. Press **Start** in the bot chat
6. Bot replies: *"✅ You're now subscribed to MarketMind AI alerts"*
7. Portfolio page auto-detects the link and shows **Connected ✅** (polls every 3 s for up to 60 s)

> **Linux browser shows "open xdg-open"?**  — Use the **Open Telegram Web** button, sign in to [web.telegram.org](https://web.telegram.org), then paste the `/start <token>` command shown on the page.

#### What the Telegram message looks like

```
📊 MarketMind AI Signal Alert

🟢 TCS       →  BUY   (82%)
🔴 INFY      →  SELL  (71%)
🟡 HDFCBANK  →  HOLD
🟢 RELIANCE  →  BUY   (76%)

🔗 Open Dashboard
```

#### Who receives which alerts

| Run type | Stocks you receive alerts for |
|---|---|
| **Manual Run Analysis** (dashboard modal) | All stocks you selected |
| **Scheduled digest (8:45 AM / 4:15 PM IST)** | Only stocks in your personal **Watchlist** |

> Add stocks to your Watchlist on the Portfolio page to personalise your scheduled alert feed. Users with an empty watchlist are skipped gracefully during scheduled runs.

#### Polling vs Webhook mode

| Mode | How it activates | Recommended for |
|---|---|---|
| **Polling** (default) | App pulls messages from Telegram every 30 s — starts automatically when `TELEGRAM_WEBHOOK_URL` is blank | Localhost / development |
| **Webhook** | Telegram pushes updates to your URL instantly | Production server with a public domain |

To switch to webhook mode add to `.env`:
```env
TELEGRAM_WEBHOOK_URL=https://marketmind.yourdomain.com
```
The app registers the webhook automatically on startup. You can also manage it manually:
```bash
python3 setup_telegram_webhook.py set https://marketmind.yourdomain.com
python3 setup_telegram_webhook.py info    # verify
python3 setup_telegram_webhook.py delete  # revert to polling
```

---

### Daily Digest Page (`/subscribe`) — *navbar: "Daily Digest"*
A standalone subscription page for setting up **automated recurring emails** (distinct from one-time Run Analysis):
- Enter your email address and choose stocks to track
- The app sends a full AI digest **2 times per day**:
  - **8:45 AM IST** — pre-market signal preview before NSE opens
  - **4:15 PM IST** — post-market summary after NSE closes
- Unsubscribe with a single click (token-based link included in every email)
- No login required — email is the identity

> **Tip:** You can also subscribe from within the **Run Analysis** modal (Step 2 → check *Also subscribe for Daily Digest*) without navigating away.

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

**Via Run Analysis modal (recommended — one flow):**
1. Click **Run Analysis** in the navbar
2. Pick stocks (Step 1)
3. Enter email (Step 2 — marked *One-time*)
4. Check **📬 Also subscribe for Daily Digest** toggle that appears
5. Click **Run Analysis** — analysis runs AND subscription is created simultaneously

**Via Daily Digest page (standalone):**
1. Visit `/subscribe` in the browser (or navigate via the *Daily Digest* navbar link)
2. Choose the NSE stocks you want to track
3. Enter your email and click **Subscribe / Update Daily Digest**
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
├── app.py                       # Flask web server + REST API + all routes
├── start.sh                     # One-click launcher for Linux / macOS
├── start.bat                    # One-click launcher for Windows
├── config/
│   └── config.yaml              # Non-sensitive configuration
├── .env                         # Secrets (API keys, SMTP, Telegram) — never commit this
├── .env.example                 # Template — copy to .env and fill in
├── requirements.txt             # All Python dependencies (includes bcrypt)
├── src/
│   ├── orchestrator.py          # 6-stage agent pipeline with apply_overrides()
│   ├── stock_discovery.py       # Dynamic NSE equity list fetcher + cache
│   ├── telegram_utils.py        # Telegram message builder + send_pipeline_alerts()
│   ├── email_utils.py           # Standalone SMTP helpers (welcome/update/lookup emails)
│   ├── agents/
│   │   ├── base_agent.py        # ABC with initialize / execute / cleanup
│   │   ├── market_data_agent.py # NSE primary + yfinance fallback
│   │   ├── news_agent.py        # RSS feeds (no API key needed)
│   │   ├── ai_analysis_agent.py # Claude / Gemini / OpenAI — batched per cycle
│   │   ├── signal_generator_agent.py  # Rule-based BUY/HOLD/SELL
│   │   ├── report_generator_agent.py  # matplotlib PNG charts
│   │   └── email_alert_agent.py       # STARTTLS HTML digest, N recipients
│   ├── technical/
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
│   │   ├── base.html            # Navbar, market status strip, theme toggle
│   │   ├── dashboard.html       # KPIs, signals, India + Global news tabs, setup warning banner
│   │   ├── stock_detail.html    # Per-stock: price, RSI/MACD/Bollinger charts, AI analysis
│   │   ├── stocks.html          # Markets page — trending, sector leaders, screener
│   │   ├── screener.html        # Multi-criteria stock screener
│   │   ├── backtest.html        # Signal backtesting + equity curve
│   │   ├── portfolio.html       # Portfolio + watchlist + Telegram subscribe
│   │   ├── login.html           # Login form
│   │   ├── register.html        # Registration form
│   │   ├── alerts.html          # Email history with recipient tags
│   │   └── subscribe.html       # Subscription sign-up with live stock picker
│   └── static/
│       ├── style.css            # CSS variables, dark/light themes, market strip
│       └── main.js              # Stock picker, email tags, pipeline polling, health check
├── data/
│   ├── marketmind.db            # SQLite DB (auto-created)
│   └── reports/                 # Generated chart PNGs
└── logs/
    └── app.log
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
    provider: "claude"           # claude | gemini | openai  (overridden by LLM_PROVIDER env var)
    model: "claude-opus-4-5"    # or gemini-2.5-flash / gpt-4o-mini

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
| `GET` | `/api/pipeline/status` | `{"running": true/false, "last_error": "..."}` — last error empty on success |
| `GET` | `/api/health` | **Configuration status** — LLM key, SMTP, Telegram, secret key, DB; returns `warnings[]` list |
| `GET` | `/api/market/status` | Market open/closed/holiday status + next opening time (JSON) |
| `GET` | `/api/screener?sector=&signal=&rsi_min=&rsi_max=&macd_trend=` | **Screener results (JSON)** |
| `GET` | `/api/backtest/<symbol>` | **Backtest results for symbol (JSON)** |
| `GET` | `/api/portfolio` | **Open positions with live P&L** (auth required, JSON) |
| `POST` | `/api/portfolio/add` | **Add a position**; body: `{"symbol", "quantity", "avg_buy_price", "notes"}` |
| `POST` | `/api/portfolio/close/<id>` | **Close a position**; body: `{"sell_price"}` |
| `DELETE` | `/api/portfolio/delete/<id>` | **Delete a position** |
| `GET` | `/api/watchlist` | **Get user watchlist** (auth required, JSON) |
| `POST` | `/api/watchlist/toggle/<symbol>` | **Add or remove symbol from watchlist** |
| `GET` | `/api/telegram/status` | Telegram link status for current user |
| `GET` | `/api/telegram/subscribe-link` | Generate one-time deep-link for bot subscribe |
| `POST` | `/api/telegram/webhook` | Receive Telegram updates (webhook mode) |
| `POST` | `/api/telegram/unsubscribe` | Remove Telegram link for current user |
| `POST` | `/api/telegram/test` | **Send a test Telegram message** |
| `GET` | `/api/telegram/run-info` | Subscriber count shown in Run Analysis modal |
| `POST` | `/api/run` | Trigger pipeline *(login required)*; body: `{"stocks":[…], "email":[…]}` |
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
| User passwords | Hashed with **bcrypt** (salted, ≥4.0.0); plain-text never stored |
| Session security | Flask-Login cookies; signed by `FLASK_SECRET_KEY` — must be set in `.env` |
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
- [ ] Docker container for one-command deployment on any machine
- [ ] Options chain analysis
- [ ] ML-based signal confidence scoring
- [ ] Multi-region support (BSE, global markets)
- [ ] WhatsApp notifications (Twilio)
- [ ] Strategy builder (custom entry/exit rules)

---

## ⚠️ Disclaimer

MarketMind AI is an educational / research tool. Nothing it generates constitutes financial advice. Always conduct your own due diligence before making investment decisions.

---

**Built for retail investors and traders**
