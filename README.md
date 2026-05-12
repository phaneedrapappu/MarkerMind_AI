# MarketMind AI 🤖

A **multi-agent AI ecosystem** for financial intelligence, designed to help retail investors and traders make faster and smarter market decisions using real-time institutional activity, AI-powered analysis, and intelligent trading signals.

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
