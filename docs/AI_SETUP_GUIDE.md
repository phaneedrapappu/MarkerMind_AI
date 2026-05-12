# AI-Powered Multi-Agent Setup Guide

## 🤖 New Agents Added

Your MarketMind AI now has **3 coordinated agents**:

1. **Market Data Agent** ✅ - Fetches real-time stock data from NSE
2. **AI Analysis Agent** 🆕 - Analyzes data using GPT
3. **Signal Generator Agent** 🆕 - Generates BUY/HOLD/SELL signals

---

## 🚀 Quick Setup

### Step 1: Install OpenAI Library

```bash
# Activate your environment (if using venv)
source venv/bin/activate

# Install OpenAI
pip install openai

# Or install all requirements
pip install -r requirements.txt
```

### Step 2: Get OpenAI API Key

1. **Go to**: https://platform.openai.com/api-keys
2. **Sign up** or log in
3. **Create new API key**
4. **Copy the key** (starts with `sk-...`)

### Step 3: Set API Key

**Option A: Environment Variable (Recommended)**
```bash
# Linux/Mac
export OPENAI_API_KEY="sk-your-key-here"

# Or add to ~/.bashrc or ~/.zshrc for permanent setup
echo 'export OPENAI_API_KEY="sk-your-key-here"' >> ~/.bashrc
source ~/.bashrc

# Windows (Command Prompt)
set OPENAI_API_KEY=sk-your-key-here

# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-your-key-here"
```

**Option B: Config File**
Edit `config/config.yaml`:
```yaml
agents:
  ai_analysis_agent:
    enabled: true
    model: "gpt-4o-mini"
    api_key: "sk-your-key-here"  # Add your key here
```

⚠️ **Security Note**: Don't commit API keys to git. Use environment variables in production.

---

## 📊 How It Works

### Agent Flow

```
User runs: python main.py
    ↓
┌─────────────────────────────────────────────┐
│ Step 1: Market Data Agent                  │
│ • Fetches TCS, WIPRO, DMART data from NSE  │
│ • Gets FII/DII flows, bulk deals           │
│ • Output: MarketDataSnapshot objects       │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Step 2: AI Analysis Agent                  │
│ • Sends data to GPT-4o-mini                │
│ • Gets AI analysis of:                     │
│   - Daily trading patterns                 │
│   - Bulk/block deal significance           │
│   - FII/DII sentiment                      │
│   - Overall market view                    │
│ • Output: AIAnalysisReport objects         │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Step 3: Signal Generator Agent             │
│ • Analyzes AI reports                      │
│ • Generates trading signals:               │
│   - STRONG_BUY / BUY / HOLD /              │
│     REDUCE_EXPOSURE / SELL                 │
│ • Confidence score (0-100%)                │
│ • Risk assessment                          │
│ • Output: TradingSignal objects            │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
            Display Results
```

---

## 💰 Cost Estimation

### GPT-4o-mini Pricing (Current)
- **Input**: ~$0.15 per 1M tokens
- **Output**: ~$0.60 per 1M tokens

### Typical Analysis Cost
```
Per Stock Analysis:
- Input tokens: ~1,000 (market data)
- Output tokens: ~500 (AI analysis)

Cost per analysis: ~$0.0004 (₹0.03)

Daily Cost (3 stocks, 10 times/day):
3 stocks × 10 analyses = 30 analyses
30 × ₹0.03 = ₹0.90/day

Monthly Cost: ₹27 (~$0.33/month)
```

**Very affordable!** 💪

---

## 🎯 Example Usage

### Basic Run

```bash
python main.py
```

**Expected Output:**

```
======================================================================
              🤖 MarketMind AI - Financial Intelligence Agent
======================================================================

🚀 Starting agent execution...

Step 1/3: Executing Market Data Agent
============================================================
📊 Tata Consultancy Services Limited (TCS)
============================================================
💰 Current Price: ₹3,845.50
📈 Change: ₹+45.30 (+1.19%)
...

Step 2/3: Executing AI Analysis Agent
======================================================================
🤖 AI ANALYSIS: Tata Consultancy Services Limited (TCS)
======================================================================

📊 Overall Sentiment: Bullish

💡 GPT Analysis:
1. DAILY TRADING ANALYSIS:
   - Strong upward momentum with +1.19% gain
   - Volume 33% above average indicates genuine buying interest
   - Buyers clearly in control with consistent accumulation

2. BULK/BLOCK DEALS ANALYSIS:
   - 50,000 shares traded in bulk deals
   - Institutional accumulation at current levels is bullish
   - Shows strong confidence from large investors

3. FII/DII ACTIVITY:
   - FII sentiment: Bullish (Net buying ₹270Cr)
   - DII sentiment: Neutral (Minor selling ₹70Cr)
   - Strong net institutional inflow is positive for stock

4. OVERALL ASSESSMENT:
   - Overall sentiment: Bullish
   - Key highlights:
     • Strong FII buying support
     • Above-average trading volume
     • Institutional accumulation pattern
   - Opportunities: Consider accumulating on minor dips
======================================================================

Step 3/3: Executing Signal Generator Agent
======================================================================
🎯 TRADING SIGNAL: Tata Consultancy Services Limited (TCS)
======================================================================

✅ Signal: BUY
📊 Confidence: 78%
🟡 Risk Level: MEDIUM

💡 Reasoning: Positive market sentiment | Strong institutional buying support

✅ Supporting Factors:
   • Bullish sentiment indicated
   • Strong institutional buying (₹270Cr)
   • Above-average trading volume

⏰ Time Horizon: Short-term (1-3 months)
======================================================================

📊 Execution Summary
======================================================================
✅ Market Data Agent: SUCCESS - Collected 3 stock(s)
🤖 AI Analysis Agent: SUCCESS - Generated 3 analysis report(s)
🎯 Signal Generator Agent: SUCCESS - Generated 3 trading signal(s)
======================================================================

✅ MarketMind AI execution completed successfully!
```

---

## ⚙️ Configuration Options

### config/config.yaml

```yaml
agents:
  # Market Data Agent
  market_data_agent:
    enabled: true
    stocks:
      - "TCS"
      - "WIPRO"
      - "DMART"
      - "RELIANCE"  # Add more stocks
  
  # AI Analysis Agent
  ai_analysis_agent:
    enabled: true
    model: "gpt-4o-mini"  # Fast and cost-effective
    # Other options:
    # model: "gpt-4-turbo"  # More powerful but expensive
    # model: "gpt-3.5-turbo"  # Cheaper but less accurate
  
  # Signal Generator Agent
  signal_generator_agent:
    enabled: true
    risk_tolerance: "medium"  # low/medium/high
```

---

## 🎓 Understanding the Signals

### Signal Types

| Signal | Meaning | Action |
|--------|---------|--------|
| 🚀 **STRONG_BUY** | Very bullish | Consider significant position |
| ✅ **BUY** | Bullish | Consider accumulating |
| ⏸️ **HOLD** | Neutral | Maintain existing position |
| ⚠️ **REDUCE_EXPOSURE** | Bearish | Consider booking partial profits |
| ⬇️ **SELL** | Very bearish | Consider exiting |

### Confidence Levels

- **80-100%**: High confidence
- **60-80%**: Medium confidence
- **Below 60%**: Low confidence - monitor closely

### Risk Levels

- 🟢 **LOW**: Stable stock, limited downside
- 🟡 **MEDIUM**: Normal market risk
- 🟠 **HIGH**: Volatile, significant risk
- 🔴 **VERY_HIGH**: Extreme risk, avoid if risk-averse

---

## 🔧 Troubleshooting

### Error: "OpenAI library not installed"

```bash
pip install openai
```

### Error: "OpenAI API key not found"

Make sure you set the API key:
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

### Error: "Rate limit exceeded"

You're making too many API calls. Solutions:
1. Reduce number of stocks
2. Increase fetch_interval
3. Upgrade OpenAI account tier

### Error: "Insufficient balance"

Add credits to your OpenAI account:
https://platform.openai.com/account/billing

---

## 🚀 Next Steps

1. ✅ **Test the system**: Run `python main.py`
2. 📊 **Monitor signals**: Track accuracy over time
3. 🔧 **Customize**: Adjust risk tolerance, add more stocks
4. 📈 **Scale**: Add more analysis factors
5. 📱 **Automate**: Set up cron jobs or schedulers

---

## ⚠️ Important Disclaimers

1. **Not Financial Advice**: These are AI-generated suggestions, not professional advice
2. **Do Your Own Research**: Always verify with multiple sources
3. **Risk Management**: Never invest more than you can afford to lose
4. **Market Risks**: Past performance doesn't guarantee future results
5. **AI Limitations**: AI can make mistakes, always use human judgment

---

## 📞 Support

- **Logs**: Check `logs/marketmind.log` for detailed execution logs
- **Config**: Review `config/config.yaml` for settings
- **Docs**: Read `docs/ARCHITECTURE.md` for system design

---

**Happy Trading! 📈🤖**
