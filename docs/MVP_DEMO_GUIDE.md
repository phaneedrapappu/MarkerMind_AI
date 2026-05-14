# MarketMind AI — MVP Demo Guide

> **Version:** 1.0 MVP  
> **Date:** May 2026  
> **Stack:** Python 3.10 · Flask · SQLite · Gemini 2.5-Flash · APScheduler  

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Feature Walkthrough](#2-feature-walkthrough)
3. [Technical Architecture](#3-technical-architecture)
4. [AI Agent Pipeline](#4-ai-agent-pipeline)
5. [REST API Reference](#5-rest-api-reference)
6. [Data Models](#6-data-models)
7. [Configuration Reference](#7-configuration-reference)
8. [Environment Setup](#8-environment-setup)
9. [Demo Script — Step by Step](#9-demo-script--step-by-step)
10. [QA Checklist](#10-qa-checklist)
11. [Known Limitations (MVP Scope)](#11-known-limitations-mvp-scope)

---

## 1. Product Overview

**MarketMind AI** is an autonomous multi-agent financial intelligence platform for Indian equity markets. It continuously monitors NSE-listed stocks, fetches real-time market data and news, runs AI-powered analysis via Google Gemini, generates BUY/SELL/HOLD signals, and delivers personalised email digests to subscribers — all without manual intervention.

### Core Value Proposition

| User Pain | MarketMind AI Solution |
|---|---|
| Information overload from financial news | AI-summarised sentiment + signals per stock |
| Manual chart analysis | Automated technical signal generation with confidence scores |
| Missing market moves | Scheduled pre-market (08:45 IST) and post-market (16:15 IST) digests |
| Generic market newsletters | Per-subscriber personalised watchlist digests |

---

## 2. Feature Walkthrough

### 2.1 Dashboard (`/`)

The main dashboard is a real-time single-page view with the following panels:

**KPI Cards (top row)**
- Total Signals generated
- Latest signal BUY/SELL/HOLD badge with confidence
- Total news articles collected
- Email alerts sent
- Subscriber count

**Trading Signals Panel** *(scrollable, 360px cap)*
- Table of latest signals: Symbol · Signal type · Confidence bar · Risk level · Date
- Click any row → navigates to the stock detail page
- "View all →" link to full alerts history

**Market News Panel** *(scrollable, 440px fixed height)*
- Two tabs: 🇮🇳 India (NSE/Indian RSS feeds) and 🌐 Global (Reuters, Yahoo Finance, Google News)
- Global news loaded lazily on first tab switch via `/api/news/global`
- Colour-coded sentiment dots: green (positive), red (negative), grey (neutral)

**Signal Distribution Chart**
- Doughnut chart showing BUY / SELL / HOLD breakdown (Chart.js)

**Recent Alerts Panel** *(scrollable, 300px cap)*
- Last 20 email digests: timestamp · symbol · sent/failed status · subject line

---

### 2.2 Stock Detail Page (`/stock/<SYMBOL>`)

Deep-dive page per NSE symbol:

- **Price History chart** — line chart of last 30 data points with trend colouring (green if up, red if down)
- **Signal History sidebar** *(scrollable, 340px)* — badge list of all BUY/SELL/HOLD signals with confidence and date
- **Generated Report Charts** — saved chart images from the pipeline run
- **AI Analysis** *(scrollable, 320px)* — timestamped Gemini analysis records with sentiment badge (Bullish / Bearish / Neutral) and LLM response preview
- **News for Symbol** *(scrollable, 360px)* — all collected news articles for that stock with sentiment badge and source/date

---

### 2.3 Alert History (`/alerts`)

Full table of all email digests ever sent:
- Timestamps, symbol, recipient list, sent/failed status, subject line, error message on failure
- Table is horizontally scrollable on mobile with a 600px vertical cap + scrollbar

---

### 2.4 Subscribe Page (`/subscribe`)

Self-service email subscription page:

**Subscription Form**
- Email input field
- Live stock picker loaded dynamically from NSE (1700+ stocks via `/api/stocks/live`)
  - Sector tabs (scrollable horizontally — no wrapping)
  - Text search across symbol + company name
  - One-click preset watchlists (Large Cap, IT, Banking, Pharma, Energy)
  - Selected stocks displayed as removable chips
- Button label: **"Subscribe / Update Watchlist"**
  - New subscribers → welcome email sent immediately
  - Existing subscribers → update email sent, watchlist updated
- Success message distinguishes between new subscription and watchlist update

**Manage Subscription Card**
- Enter email → system emails a one-click unsubscribe link to that address
- Security-safe: always returns "sent" regardless of whether email exists

**Unsubscribe Flow**
- One-click link in every digest email footer → `GET /unsubscribe?token=<uuid>`
- Deactivates subscriber record immediately
- Confirmation page shown

---

### 2.5 Run Analysis Modal (available from all pages)

Accessible via the **"Run Analysis"** button in the navbar and mobile bottom bar:

- **Stock selection**: sector tabs + search + chips (same picker as subscribe page)
- **Email recipients**: comma-separated recipient list
- **Run type**: Full Pipeline / Market Data Only / Signals Only
- Triggers `POST /api/run` which executes the full 6-agent pipeline asynchronously
- Live status polling via `/api/pipeline/status` with spinner

---

### 2.6 Automated Email Digests

- **Pre-market digest**: daily at **08:45 IST** (30 min before NSE open)
- **Post-market digest**: daily at **16:15 IST** (15 min after NSE close)
- Every digest email contains:
  - Per-stock AI analysis summary
  - BUY/SELL/HOLD signal with confidence
  - Top news headlines with sentiment
  - Unsubscribe link footer
  - "Manage Subscription" link footer

---

## 3. Technical Architecture

```
Browser (Flask-served HTML + Chart.js)
        │
        ▼
┌─────────────────────────────────┐
│         Flask App (app.py)      │  port 5050
│  19 routes · APScheduler 2×/day │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│        Orchestrator             │  src/orchestrator.py
│  Coordinates 6-agent pipeline   │
└──┬──┬──┬──┬──┬──┬───────────────┘
   │  │  │  │  │  │
   ▼  ▼  ▼  ▼  ▼  ▼
 MDA NA  AI  SGA RGA EAA
  (1)(2)(3)  (4) (5) (6)
             │
             ▼
┌─────────────────────────────────┐
│     SQLite Database             │  data/marketmind.db
│  SQLAlchemy ORM · 7 tables      │
└─────────────────────────────────┘
```

**Agent abbreviations:**
- MDA — MarketDataAgent
- NA  — NewsAgent
- AI  — AIAnalysisAgent (Gemini 2.5-Flash)
- SGA — SignalGeneratorAgent
- RGA — ReportGeneratorAgent
- EAA — EmailAlertAgent

### Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Language | Python | 3.10.12 |
| Web framework | Flask | 3.x |
| ORM | SQLAlchemy | 2.x |
| Database | SQLite | (bundled) |
| AI / LLM | Google Gemini 2.5-Flash | via `google-generativeai` |
| Scheduler | APScheduler | 3.11.2 |
| Charts | Chart.js | CDN 4.x |
| CSS framework | Bootstrap | CDN 5.3 |
| Icons | Bootstrap Icons | CDN 1.11 |
| Email | Gmail SMTP STARTTLS | port 587 |
| News | RSS feeds (`feedparser`) | multiple sources |
| NSE data | NSE open data CSV + HTTP headers | `EQUITY_L.csv` |

---

## 4. AI Agent Pipeline

The pipeline runs sequentially. Each agent receives the output of the previous and writes results to the database.

### Agent 1 — MarketDataAgent (`src/agents/market_data_agent.py`)

- Fetches live NSE price, volume, 52w high/low, P/E, market cap for each configured symbol
- Uses NSE cookie-based HTTP client with rotating user-agent headers
- Stores: `StockData` records in SQLite
- Output passed downstream: list of stock dicts with current price

### Agent 2 — NewsAgent (`src/agents/news_agent.py`)

- Fetches two categories of news:
  1. **Indian market news** — per-stock Google News RSS + Moneycontrol feed
  2. **Global market news** — 6 international RSS feeds tagged `__GLOBAL__`:
     - Reuters Business, Reuters Technology
     - Yahoo Finance, Google News Global
     - Investing.com, Livemint
- Deduplicates by URL (upsert on `url` unique constraint)
- Runs basic keyword sentiment classification (POSITIVE / NEGATIVE / NEUTRAL)
- Stores: `NewsRecord` rows

### Agent 3 — AIAnalysisAgent (`src/agents/ai_analysis_agent.py`)

- Builds a structured prompt per stock containing:
  - Current price metrics
  - Last 5 news headlines with sentiment
  - Historical signal context
- Sends to **Gemini 2.5-Flash** via `google-generativeai` SDK
- Parses structured response: `overall_sentiment`, `key_factors`, `risk_assessment`, `raw_llm_response`
- Stores: `AnalysisReport` records
- Supports OpenAI API as alternative (configurable in `config.yaml`)

### Agent 4 — SignalGeneratorAgent (`src/agents/signal_generator_agent.py`)

- Consumes AI analysis + market data to produce trading signals
- Signal logic:
  - Gemini sentiment (`Bullish` / `Bearish` / `Neutral`) → maps to BUY / SELL / HOLD
  - Confidence score calculated from sentiment strength + news volume
  - Risk level (`LOW` / `MEDIUM` / `HIGH`) driven by `risk_tolerance` config
- Deduplication: only saves a new signal if it differs from the latest one for that symbol
- Stores: `TradingSignal` records

### Agent 5 — ReportGeneratorAgent (`src/agents/report_generator_agent.py`)

- Generates chart images (signal history, price trend) saved to `data/charts/`
- Creates plain-text + HTML summary report
- Output consumed by EmailAlertAgent

### Agent 6 — EmailAlertAgent (`src/agents/email_alert_agent.py`)

- Composes HTML email digest from report output
- Appends unsubscribe footer block to every recipient email containing:
  - One-click unsubscribe link (`/unsubscribe?token=<uuid4>`)
  - "Manage Subscription" link
- Sends via Gmail SMTP STARTTLS (port 587)
- Stores: `AlertRecord` with success/failure + error message

---

## 5. REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Dashboard HTML page |
| `GET` | `/stock/<symbol>` | Stock detail HTML page |
| `GET` | `/alerts` | Alert history HTML page |
| `GET` | `/subscribe` | Subscription HTML page |
| `GET` | `/unsubscribe?token=<uuid>` | One-click unsubscribe handler |
| `GET` | `/api/signals?limit=N` | Latest trading signals (JSON) |
| `GET` | `/api/news?symbol=X&limit=N` | News articles, optionally filtered by symbol |
| `GET` | `/api/news/global` | Global market news (`__GLOBAL__` tag) |
| `GET` | `/api/stock/<symbol>/history?limit=N` | Price history for Chart.js |
| `GET` | `/api/summary` | KPI counts (signals, news, alerts, subscribers) |
| `GET` | `/api/alerts?limit=N` | Alert send history |
| `GET` | `/api/stocks` | Hardcoded catalog of 80 stocks grouped by sector |
| `GET` | `/api/stocks/live?search=X&refresh=1` | Live NSE stock catalog (1700+ stocks, 6h cache) |
| `GET` | `/api/pipeline/status` | Current pipeline run status |
| `GET` | `/api/subscribers` | Count of active subscribers |
| `POST` | `/api/run` | Trigger full pipeline run (JSON body: `stocks`, `recipients`, `run_type`) |
| `POST` | `/api/subscribe` | Subscribe or update watchlist (JSON: `email`, `stocks[]`) |
| `POST` | `/api/unsubscribe` | Unsubscribe by token (JSON: `token`) |
| `POST` | `/api/subscription/lookup` | Email self-service unsubscribe link (JSON: `email`) |
| `POST` | `/api/test-digest` | Fire immediate digest for all or one subscriber |

---

## 6. Data Models

All models defined in `src/database/db_manager.py` via SQLAlchemy ORM — SQLite in development, compatible with PostgreSQL for production.

### StockData
Stores fetched NSE price snapshots.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `symbol` | VARCHAR | NSE ticker, e.g. `RELIANCE` |
| `price` | FLOAT | Last traded price (₹) |
| `volume` | INTEGER | Day's volume |
| `market_cap` | FLOAT | In crores |
| `pe_ratio` | FLOAT | |
| `week_52_high` | FLOAT | |
| `week_52_low` | FLOAT | |
| `timestamp` | DATETIME | UTC |

### NewsRecord
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `symbol` | VARCHAR | NSE ticker or `__GLOBAL__` |
| `title` | TEXT | |
| `url` | VARCHAR UNIQUE | Deduplication key |
| `source` | VARCHAR | |
| `sentiment` | VARCHAR | POSITIVE / NEGATIVE / NEUTRAL |
| `published_at` | VARCHAR | |
| `created_at` | DATETIME | |

### AnalysisReport
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `symbol` | VARCHAR | |
| `overall_sentiment` | VARCHAR | Bullish / Bearish / Neutral |
| `key_factors` | TEXT | JSON list |
| `risk_assessment` | TEXT | |
| `raw_llm_response` | TEXT | Full Gemini response |
| `analysis_date` | DATETIME | |

### TradingSignal
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `symbol` | VARCHAR | |
| `signal_type` | VARCHAR | BUY / SELL / HOLD |
| `confidence` | FLOAT | 0.0 – 1.0 |
| `risk_level` | VARCHAR | LOW / MEDIUM / HIGH |
| `reasoning` | TEXT | |
| `signal_date` | DATETIME | |

### AlertRecord
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `symbol` | VARCHAR | |
| `recipients` | TEXT | Comma-separated |
| `subject` | TEXT | |
| `success` | BOOLEAN | |
| `error_message` | TEXT | |
| `sent_at` / `created_at` | DATETIME | |

### SubscriberRecord
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `email` | VARCHAR UNIQUE | Upsert key |
| `stocks` | TEXT | JSON array of symbols |
| `is_active` | BOOLEAN | False = unsubscribed |
| `subscribed_at` | DATETIME | First subscription time |
| `last_sent_at` | DATETIME | Last digest timestamp |
| `unsubscribe_token` | VARCHAR UNIQUE | UUID4 for one-click unsubscribe |
| `created_at` | DATETIME | |

---

## 7. Configuration Reference

All settings in `config/config.yaml`:

```yaml
agents:
  ai_analysis_agent:
    provider: "gemini"           # or "openai"
    model: "gemini-2.5-flash"    # Gemini or GPT model name

  signal_generator_agent:
    risk_tolerance: "medium"     # low / medium / high

  email_alert_agent:
    smtp:
      host: "smtp.gmail.com"
      port: 587
      sender: "your@gmail.com"
      recipients:
        - "default@example.com"  # fallback if no subscribers

scheduler:
  run_interval_minutes: 30       # pipeline cadence in --continuous mode
```

### Required Environment Variables

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API access |
| `OPENAI_API_KEY` | OpenAI access (if provider = openai) |
| `SMTP_USER` | Gmail address for sending |
| `SMTP_PASSWORD` | Gmail App Password (not account password) |

---

## 8. Environment Setup

```bash
# 1. Clone and enter project
cd /path/to/MarkerMind_AI

# 2. Create virtual environment
python3 -m venv venv && source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
export GEMINI_API_KEY="your-key-here"
export SMTP_USER="you@gmail.com"
export SMTP_PASSWORD="your-app-password"

# 5. Start the server
python3 app.py
# → http://localhost:5050
```

### Production (24/7) via systemd

```bash
sudo cp marketmind.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable marketmind
sudo systemctl start marketmind
```

---

## 9. Demo Script — Step by Step

Use this script to demonstrate all MVP features end-to-end.

### Step 1 — Show the Dashboard
1. Open `http://localhost:5050`
2. Highlight the KPI cards: signals count, news count, subscribers
3. Point out the Signals panel — scrolls vertically, click any row
4. Switch News tab from 🇮🇳 India → 🌐 Global (watch lazy load)

### Step 2 — Run the AI Pipeline
1. Click **"Run Analysis"** (navbar or bottom bar)
2. On the modal — select 3–4 stocks using sector tabs or search
3. Add a recipient email
4. Click **Run Pipeline**
5. Watch the spinner → status updates → "Pipeline complete"
6. Dashboard KPI counts increment live

### Step 3 — Inspect a Stock
1. Click a signal row on the dashboard
2. Show the price history line chart
3. Show the signal history sidebar — BUY/SELL/HOLD badges with confidence
4. Scroll to AI Analysis — show Gemini's summary + sentiment badge
5. Scroll to News — show linked articles with sentiment

### Step 4 — Email Subscription
1. Navigate to `/subscribe`
2. Enter an email address
3. Use sector tabs to pick stocks (demonstrate horizontal scroll)
4. Use search to find a specific stock
5. Click **Subscribe / Update Watchlist**
6. Show success toast + check inbox for welcome email
7. Re-submit same email with different stocks → shows "Watchlist Updated"

### Step 5 — Manage Subscription
1. Scroll down on subscribe page to "Manage Subscription"
2. Enter the subscribed email → click Send Link
3. Open the received email → click Unsubscribe
4. Show unsubscribe confirmation page

### Step 6 — Alert History
1. Navigate to `/alerts`
2. Show the scrollable full table — sent timestamp, recipients, status
3. Point out failed rows have error message in red

### Step 7 — Automated Scheduling
1. Open `config/config.yaml` and show cron schedule comment
2. Explain: 08:45 pre-market and 16:15 post-market digests fire automatically
3. Explain: each subscriber gets their personal watchlist digest, not a generic blast

---

## 10. QA Checklist

Run through this before any live demo.

### Server
- [ ] `python3 app.py` starts without errors on port 5050
- [ ] No import errors in terminal output
- [ ] `logs/marketmind.log` is being written

### Dashboard
- [ ] KPI cards all show numbers (not "None" or blank)
- [ ] Signals panel scrolls vertically — does NOT push page height
- [ ] News panel scrolls vertically at 440px fixed height
- [ ] India / Global news tabs switch correctly
- [ ] Global news loads on first tab click (spinner → articles)
- [ ] Recent Alerts panel scrolls at 300px cap
- [ ] Signal Distribution chart renders

### Pipeline Run
- [ ] Run modal opens from navbar button
- [ ] Stock picker loads from `/api/stocks/live` (or falls back to `/api/stocks`)
- [ ] Sector tabs scroll horizontally without wrapping
- [ ] Search box filters stocks live
- [ ] Pipeline completes and "Pipeline complete" appears
- [ ] New signals appear in dashboard after run
- [ ] Email delivered to recipient inbox

### Stock Detail
- [ ] All three scrollable panels (signal history, analysis, news) cap at height and scroll
- [ ] Price chart renders with correct trend colour
- [ ] Clicking "Back" returns to dashboard

### Subscriptions
- [ ] New subscription triggers welcome email within ~5 seconds
- [ ] Re-subscribing same email with different stocks sends "update" email
- [ ] Lookup endpoint sends link email
- [ ] Token-based unsubscribe sets `is_active = False` in DB
- [ ] Unsubscribed user no longer receives scheduled digests

### Alerts Page
- [ ] Table renders with horizontal scroll on narrow viewport
- [ ] Vertical scroll cap at 600px works
- [ ] Failed alerts show error message

### Responsive / Mobile
- [ ] Bottom navigation bar visible on mobile
- [ ] All tables have horizontal scroll (no horizontal page overflow)
- [ ] Sector tabs scroll horizontally on narrow screen

---

## 11. Known Limitations (MVP Scope)

| Area | Limitation | Planned Fix |
|---|---|---|
| Market data | NSE scraping may fail if NSE changes session/cookie mechanism | Integrate paid data API (Zerodha Kite, Upstox) |
| AI analysis | Gemini 2.5-Flash has rate limits on free tier | Batch requests with retry + exponential backoff |
| Signal quality | Signals based purely on LLM sentiment, no technical indicators | Add RSI, MACD, Bollinger Bands to signal logic |
| Database | SQLite — single-writer, not suitable for concurrent production load | Migrate to PostgreSQL |
| Auth | No user login — anyone with URL can run pipeline or view data | Add JWT-based auth for pipeline trigger endpoint |
| Global news | 6 RSS feeds — limited international coverage | Add Bloomberg, FT, CNBC feeds |
| Email delivery | Uses Gmail SMTP — may be throttled at volume | Migrate to SendGrid / AWS SES |
| Backtesting | No signal performance history / P&L tracking | Build backtesting module |
| Alerts | No push / WhatsApp / Telegram notifications | Add Telegram bot integration |

---

*MarketMind AI — Built for autonomous equity intelligence on Indian markets.*
