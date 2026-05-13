# 📊 MarketMind AI – Financial Intelligence Agent System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green)](https://flask.palletsprojects.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MarketMind AI is an autonomous multi-agent system that monitors Indian stock markets (NSE), generates AI-powered trading signals, and delivers rich HTML email digests with embedded charts – all without manual intervention.

---

## Architecture – Agent Pipeline

```
MarketDataAgent  →  NSE API / yfinance fallback
       ↓
  NewsAgent       →  RSS feeds (Google News, ET Markets, Moneycontrol)
       ↓
AIAnalysisAgent   →  OpenAI GPT (single batched API call per cycle)
       ↓
SignalGenerator   →  Rule-based BUY / HOLD / SELL scoring
       ↓
ReportGenerator   →  matplotlib charts (price, signal, news sentiment)
       ↓
EmailAlertAgent   →  HTML email digest with embedded charts
       ↓
  SQLite DB       ←  Every stage persists results
       ↓
  Flask Dashboard →  Browser UI (dashboard, stock detail, alerts)
```

---

## Quick Start

### 1. Prerequisites

- Python 3.10 or higher
- An [OpenAI API key](https://platform.openai.com/api-keys) (for `gpt-4o-mini`)
- A Gmail account with an [App Password](https://myaccount.google.com/apppasswords) for email alerts (optional but recommended)

### 2. Clone & Install

```bash
git clone <repo-url>
cd MarkerMind_AI

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env and fill in:
#   OPENAI_API_KEY  – your OpenAI key
#   SMTP_USER       – your Gmail address
#   SMTP_PASSWORD   – Gmail App Password
```

### 4. Configure Stocks & Recipients

Edit `config/config.yaml`:

```yaml
agents:
  market_data_agent:
    stocks:
      - "TCS"
      - "WIPRO"
      - "RELIANCE"
      # Add more NSE symbols …

  email_alert_agent:
    smtp:
      sender: "your_email@gmail.com"
      recipients:
        - "recipient1@example.com"
        - "recipient2@example.com"
```

### 5. Run the Agent Pipeline (CLI)

**Run once:**
```bash
python main.py
```

**Run on a repeating schedule** (interval in `config.yaml → scheduler.run_interval_minutes`):
```bash
python main.py --schedule
```

### 6. Run the Web Dashboard

```bash
python app.py
# Open http://localhost:5050 in your browser
```

The dashboard lets you:
- View latest trading signals, news, and email alert history
- Drill into any stock for price history, AI analysis, and charts
- Trigger a pipeline run via the **Run Pipeline** button

---

## Project Structure

```
MarkerMind_AI/
├── main.py                     # CLI entry point
├── app.py                      # Flask web dashboard
├── config/
│   └── config.yaml             # All agent configuration (non-sensitive)
├── .env.example                # Template for secrets
├── requirements.txt
├── src/
│   ├── orchestrator.py         # 6-stage agent pipeline
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── market_data_agent.py    # NSE + yfinance fallback
│   │   ├── news_agent.py           # RSS news fetcher
│   │   ├── ai_analysis_agent.py    # Batched GPT analysis
│   │   ├── signal_generator_agent.py
│   │   ├── report_generator_agent.py # matplotlib charts
│   │   └── email_alert_agent.py    # HTML email with charts
│   ├── data_sources/
│   │   └── nse_fetcher.py
│   ├── database/
│   │   └── db_manager.py       # SQLite / SQLAlchemy ORM
│   └── models/
│       ├── market_data.py
│       └── analysis_models.py
├── frontend/
│   ├── templates/              # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── stock_detail.html
│   │   └── alerts.html
│   └── static/                 # CSS + JS
│       ├── style.css
│       └── main.js
├── data/
│   ├── marketmind.db           # SQLite database (auto-created)
│   └── reports/                # Generated PNG charts
└── logs/
    └── marketmind.log
```

---

## Security Compliance

| Concern | Implementation |
|---|---|
| API credentials | Loaded from environment variables only (`.env`); never in code or config.yaml |
| SMTP password | `SMTP_PASSWORD` env var; STARTTLS enforced by default |
| `.env` in git | `.gitignore` must include `.env` |
| SQL injection | SQLAlchemy ORM parameterised queries |
| Rate limiting | 1 s sleep between NSE requests; batched LLM calls |
| Error handling | Every agent stage is try/caught; failures don't crash the pipeline |

---

## Use Cases

1. **Daily Market Digest** – Automated morning email with price snapshots, signals, and news sentiment for a custom watchlist.
2. **Bulk/Block Deal Alerts** – Detect and report large institutional block deals as they appear.
3. **FII/DII Flow Tracking** – Monitor foreign and domestic institutional activity across the index.
4. **Signal History** – SQLite DB stores every BUY/SELL/HOLD signal for back-inspection.
5. **News Sentiment Monitoring** – RSS-aggregated headline sentiment per stock.
6. **Web Dashboard** – Always-on browser UI for quick market checks without running the CLI.

---

## LLM Cost Optimisation

- All stocks in a watchlist are analysed in **one batched GPT prompt** per cycle (not one call per stock).
- Uses `gpt-4o-mini` by default – the most cost-effective OpenAI chat model.
- Rule-based signal scoring requires **zero LLM calls** on its own.
- News sentiment is done locally with keyword matching (no LLM needed).

---

## Extending the System

- **Add a new stock**: append the symbol to `config.yaml → agents.market_data_agent.stocks`.
- **Change the LLM model**: set `agents.ai_analysis_agent.model` in config.yaml.
- **Use PostgreSQL** instead of SQLite: change the `db_path` to a SQLAlchemy URL and update `db_manager.py → create_engine`.
- **Add more data sources**: extend `src/data_sources/` and wire into `MarketDataAgent`.

---

## Disclaimer

MarketMind AI is an educational/research tool. Nothing it generates constitutes financial advice. Always conduct your own due diligence before making investment decisions.


## 🌟 Features

### Core Features
- **Real-time Market Data**: Fetch live stock prices, volume, and trading activity from NSE/BSE
- **🤖 AI-Powered Analysis**: GPT-based intelligent analysis of market data
- **🎯 Trading Signals**: Automated BUY/HOLD/SELL signal generation
- **Institutional Activity Tracking**: Monitor FII/DII (Foreign & Domestic Institutional Investors) flows
- **Bulk & Block Deals Detection**: Track large institutional trades
- **Multi-Agent Architecture**: Modular, scalable agent-based system
- **Free Data Sources**: Uses publicly available data from NSE

### NEW: AI Intelligence Layer ✨
- **GPT-4 Integration**: Advanced AI analysis of market patterns
- **Intelligent Insights**: Daily buy/sell analysis with reasoning
- **Signal Confidence**: 0-100% confidence scores on trading signals
- **Risk Assessment**: Automatic risk level evaluation
- **Supporting Factors**: Clear explanation of signal reasoning

## 🏗️ Architecture

### Multi-Agent System Components

1. **Market Data Agent** ✅ (Implemented)
   - Fetches real-time stock quotes
   - Monitors bulk and block deals
   - Tracks FII/DII institutional flows
   - Analyzes promoter holdings

2. **AI Analysis Agent** ✅ (NEW - Implemented)
   - Sends market data to GPT-4
   - Generates intelligent analysis
   - Interprets trading patterns
   - Provides market insights

3. **Signal Generator Agent** ✅ (NEW - Implemented)
   - Generates BUY/HOLD/SELL signals
   - Calculates confidence scores
   - Assesses risk levels
   - Provides clear reasoning

## 📂 Project Structure

```
MarkerMind_AI/
├── config/
│   └── config.yaml              # Configuration file
├── src/
│   ├── agents/
│   │   ├── base_agent.py        # Base agent class
│   │   └── market_data_agent.py # Market data fetching agent
│   ├── data_sources/
│   │   └── nse_fetcher.py       # NSE data fetcher
│   ├── models/
│   │   └── market_data.py       # Data models
│   └── orchestrator.py          # Agent orchestrator
├── data/                        # Local data storage
├── logs/                        # Application logs
├── main.py                      # Main entry point
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
```bash
cd /home/phaneendrapappu/workspace/minna_project/MarkerMind_AI
```

2. **Create a virtual environment** (recommended)
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up OpenAI API Key** (for AI analysis)
```bash
# Get your key from: https://platform.openai.com/api-keys
export OPENAI_API_KEY="sk-your-key-here"

# Or create .env file
cp .env.example .env
# Edit .env and add your API key
```

5. **Configure the system**
   
   Edit `config/config.yaml` to customize:
   - Stock symbols to monitor
   - Data fetch intervals
   - Agent settings

### Usage

**Run the Market Data Agent**

```bash
python main.py
```

This will:
- Initialize the Market Data Agent
- Fetch real-time data for configured stocks (TCS, WIPRO, DMART)
- Display stock prices, volume, and institutional activity
- Log all activities to `logs/marketmind.log`

**Run with custom config**

```bash
python main.py --config /path/to/custom_config.yaml
```

## 📊 Sample Output

```
======================================================================
              🤖 MarketMind AI - Financial Intelligence Agent
======================================================================

🚀 Starting agent execution...

============================================================
📊 Tata Consultancy Services Limited (TCS)
============================================================
💰 Current Price: ₹3,845.50
📈 Change: ₹+45.30 (+1.19%)
📊 Open: ₹3,800.20 | High: ₹3,850.00 | Low: ₹3,795.50
📦 Volume: 2,458,932
🕒 Last Updated: 2026-05-11 15:30:45

🏦 Institutional Activity:
  - FII: Buy ₹1,250Cr | Sell ₹980Cr | Net ₹+270Cr
  - DII: Buy ₹850Cr | Sell ₹920Cr | Net ₹-70Cr
============================================================
```

## 🔧 Configuration

Edit `config/config.yaml`:

```yaml
agents:
  market_data_agent:
    enabled: true
    fetch_interval: 300  # seconds
    stocks:
      - "TCS"
      - "WIPRO"
      - "DMART"
      - "RELIANCE"  # Add more stocks
```

## 🛠️ Development

### Adding New Agents

1. Create a new agent class inheriting from `BaseAgent`
2. Implement required methods: `initialize()`, `execute()`, `cleanup()`
3. Register the agent in `orchestrator.py`
4. Enable in `config.yaml`

### Data Sources

Currently supports:
- **NSE (National Stock Exchange)** - Primary source
- **BSE (Bombay Stock Exchange)** - Coming soon

## 📝 API Data Sources

This project uses publicly available data from:
- NSE India: https://www.nseindia.com
- BSE India: https://www.bseindia.com

**Note**: Please respect the terms of service and rate limits of these platforms.

## 🔮 Roadmap

### Phase 1: Foundation ✅ (COMPLETE)
- [x] Project structure
- [x] Market Data Agent
- [x] Configuration system
- [x] Logging
- [x] Documentation

### Phase 2: AI Intelligence ✅ (COMPLETE)
- [x] AI Analysis Agent with GPT-4 integration
- [x] Signal Generator Agent
- [x] Multi-agent orchestration
- [x] BUY/HOLD/SELL signal generation

### Phase 3: Enhanced Intelligence 🚧 (IN PROGRESS)
- [ ] News Analysis Agent
- [ ] Unusual Activity Detection Agent
- [ ] Database integration
- [ ] Historical data tracking

### Phase 4: Delivery 🔮
- [ ] Alert Agent
- [ ] WhatsApp notifications
- [ ] Web dashboard
- [ ] API endpoints

### Phase 5: Scale 🔮
- [ ] ML models for predictions
- [ ] Multi-region support
- [ ] Advanced analytics
- [ ] Portfolio tracking

## ⚠️ Disclaimer

This software is for educational and informational purposes only. It is not financial advice. Always do your own research and consult with qualified financial advisors before making investment decisions.

## 📄 License

MIT License - Feel free to use and modify

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues and pull requests.

## 📧 Support

For questions or support, please open an issue on the repository.

---

**Built with ❤️ for retail investors and traders**
