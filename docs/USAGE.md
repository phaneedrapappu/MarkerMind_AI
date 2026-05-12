# Usage Guide - MarketMind AI

## Quick Start

```bash
# 1. Navigate to project
cd /home/phaneendrapappu/workspace/minna_project/MarkerMind_AI

# 2. Activate virtual environment
source venv/bin/activate

# 3. Run the system
python main.py
```

---

## Basic Usage

### Running the Market Data Agent

The simplest way to use MarketMind AI:

```bash
python main.py
```

This will:
1. Initialize the Market Data Agent
2. Fetch real-time data for all configured stocks
3. Display stock prices, volume, and institutional activity
4. Save logs to `logs/marketmind.log`

---

## Understanding the Output

### Stock Data Display

```
============================================================
📊 Tata Consultancy Services Limited (TCS)
============================================================
💰 Current Price: ₹3,845.50
📈 Change: ₹+45.30 (+1.19%)
📊 Open: ₹3,800.20 | High: ₹3,850.00 | Low: ₹3,795.50
📦 Volume: 2,458,932
🕒 Last Updated: 2026-05-11 15:30:45

🔔 Bulk/Block Deals: 2
  - BULK: ABC Capital Ltd | Qty: 50,000 @ ₹3,840.00
  - BLOCK: XYZ Investments | Qty: 100,000 @ ₹3,845.00

🏦 Institutional Activity:
  - FII: Buy ₹1,250Cr | Sell ₹980Cr | Net ₹+270Cr
  - DII: Buy ₹850Cr | Sell ₹920Cr | Net ₹-70Cr
============================================================
```

### What Each Field Means

| Field | Description |
|-------|-------------|
| **Current Price** | Last traded price (LTP) |
| **Change** | Absolute and percentage change from previous close |
| **Open** | Opening price for the day |
| **High/Low** | Intraday high and low prices |
| **Volume** | Total shares traded |
| **Bulk Deals** | Large trades (>0.5% of market cap) |
| **Block Deals** | Very large trades (>0.75% of market cap) |
| **FII** | Foreign Institutional Investors activity |
| **DII** | Domestic Institutional Investors activity |

---

## Configuration

### Adding/Removing Stocks

Edit `config/config.yaml`:

```yaml
agents:
  market_data_agent:
    stocks:
      - "TCS"        # Add stocks
      - "WIPRO"
      - "INFY"
      - "RELIANCE"
      # - "HDFCBANK"  # Comment out to disable
```

**Popular NSE Symbols**:
- **IT**: TCS, INFY, WIPRO, TECHM, HCLTECH
- **Banking**: HDFCBANK, ICICIBANK, SBIN, KOTAKBANK, AXISBANK
- **Auto**: MARUTI, TATAMOTORS, M&M, BAJAJ-AUTO
- **FMCG**: HINDUNILVR, ITC, NESTLEIND, BRITANNIA, DABUR
- **Pharma**: SUNPHARMA, DRREDDY, CIPLA, DIVISLAB
- **Energy**: RELIANCE, ONGC, BPCL, IOC

### Changing Update Frequency

```yaml
agents:
  market_data_agent:
    fetch_interval: 300  # seconds
```

**Recommendations**:
- **Day Trading**: 60-120 seconds
- **Swing Trading**: 300-600 seconds
- **Long-term Investors**: 900-1800 seconds

⚠️ **Warning**: Very frequent requests may trigger rate limiting from NSE.

---

## Advanced Usage

### 1. Run Once and Exit

```bash
python main.py --run-once
```

This runs the agents once and exits. Useful for:
- Testing
- Scheduled cron jobs
- Manual data collection

### 2. Custom Configuration File

```bash
python main.py --config /path/to/custom_config.yaml
```

### 3. Scheduled Execution with Cron

Add to crontab (`crontab -e`):

```bash
# Run every 5 minutes during market hours (9:15 AM - 3:30 PM)
*/5 9-15 * * 1-5 cd /home/phaneendrapappu/workspace/minna_project/MarkerMind_AI && source venv/bin/activate && python main.py --run-once
```

---

## Interpreting Institutional Activity

### FII (Foreign Institutional Investors)

**Positive Net (Buy > Sell)**:
- ✅ Foreign investors are bullish on Indian markets
- Usually indicates strong market sentiment
- Look for consistent buying over multiple days

**Negative Net (Sell > Buy)**:
- ⚠️ Foreign investors are exiting
- May indicate concerns about market/economy
- Check news for reasons (currency, global factors)

### DII (Domestic Institutional Investors)

**Positive Net**:
- ✅ Local institutions are buying
- Often stabilizes the market
- Can counter-balance FII selling

**Negative Net**:
- ⚠️ Local institutions are selling
- Combined with FII selling = strong negative signal

### Ideal Scenario
```
FII: Net ₹+500Cr (Buying)
DII: Net ₹+300Cr (Buying)
```
→ Strong institutional support, positive for markets

### Warning Scenario
```
FII: Net ₹-800Cr (Selling)
DII: Net ₹-400Cr (Selling)
```
→ Heavy institutional selling, bearish signal

---

## Understanding Bulk & Block Deals

### Bulk Deals
- Trades where quantity > 0.5% of company's equity
- Visible to the market during trading hours
- Indicates significant interest from large investors

### Block Deals
- Trades where quantity > 0.75% of company's equity (min ₹10Cr)
- Executed in special trading windows
- Usually institutional transactions
- More impactful than bulk deals

### How to Interpret

**Bulk/Block Buy**:
- ✅ Large investor is accumulating
- Positive signal if buyer is known quality investor
- Check if it's a one-time buy or accumulation pattern

**Bulk/Block Sell**:
- ⚠️ Large investor is exiting
- Check if it's profit booking or distress selling
- Monitor stock price reaction

---

## Best Practices

### 1. Check Logs Regularly

```bash
# View latest logs
tail -f logs/marketmind.log

# Search for errors
grep ERROR logs/marketmind.log

# Search for specific stock
grep "TCS" logs/marketmind.log
```

### 2. Monitor During Market Hours

NSE market hours: **9:15 AM - 3:30 PM IST** (Monday-Friday)

- Real-time data is only available during market hours
- Pre-market: 9:00 AM - 9:15 AM (limited data)
- Post-market: 3:30 PM - 4:00 PM (closing data)

### 3. Combine with Other Analysis

MarketMind AI is a **data aggregation tool**. Always combine with:
- Technical analysis (charts, indicators)
- Fundamental analysis (financial statements)
- News and market sentiment
- Your own research and judgment

### 4. Understand Limitations

- **Not real-time trading platform**: 5-minute delay is typical
- **Public data only**: No access to order book or depth
- **No trading recommendations**: This is an information tool
- **API rate limits**: Excessive requests may get blocked

---

## Common Use Cases

### Use Case 1: Morning Market Check

```bash
# Run once at market opening
python main.py --run-once
```

Review:
- Opening gaps (gap up/gap down)
- Pre-market institutional activity
- Any bulk/block deals overnight

### Use Case 2: Intraday Monitoring

```yaml
# config.yaml
fetch_interval: 180  # 3 minutes
```

```bash
# Run continuously
python main.py
```

Monitor:
- Price movements
- Volume spikes
- Intraday bulk deals

### Use Case 3: End of Day Analysis

```bash
# Run at 3:45 PM (after market close)
python main.py --run-once
```

Review:
- Closing prices
- Daily institutional flows
- Bulk/block deals summary

---

## Tips for Traders

### Day Traders
- ✅ Focus on volume and price movements
- ✅ Look for unusual spikes in the morning
- ✅ Monitor FII/DII flow changes
- ⚠️ Don't rely solely on this data for entries/exits

### Swing Traders
- ✅ Track bulk/block deals over days
- ✅ Monitor institutional accumulation patterns
- ✅ Look for sector-wide movements
- ⚠️ Combine with technical chart patterns

### Long-term Investors
- ✅ Focus on promoter holdings (coming soon)
- ✅ Track consistent institutional buying
- ✅ Monitor quarterly patterns
- ⚠️ Prioritize fundamental analysis

---

## Troubleshooting

### No Data During Market Hours

**Check**:
1. Is NSE website accessible? Visit https://www.nseindia.com
2. Are stock symbols correct? Verify at NSE website
3. Check logs: `tail -f logs/marketmind.log`

### Data Seems Stale

**Possible Causes**:
- Market is closed (check time)
- Stock is suspended/delisted
- API rate limit reached (wait and retry)

### Too Many Errors in Logs

```bash
# Check error frequency
grep -c ERROR logs/marketmind.log

# If too many (>10):
# 1. Increase fetch_interval to 600 (10 minutes)
# 2. Reduce number of stocks
# 3. Wait 1 hour before retrying
```

---

## Data Export (Coming Soon)

Future features:
- Export to CSV
- Export to Excel
- JSON API endpoint
- Database storage

---

## Integration with Other Tools

### Excel/Google Sheets
Currently: Copy output manually
Future: Direct CSV export

### Trading Platforms
Currently: Manual monitoring
Future: API integration with Zerodha, Upstox, etc.

### Alerting
Currently: Console output
Future: WhatsApp, Email, SMS notifications

---

## Example Workflow

### Morning Routine (9:00 AM)
```bash
# 1. Check overnight news (manually)
# 2. Run MarketMind AI
python main.py --run-once

# 3. Review stocks with unusual activity
# 4. Make watchlist for the day
# 5. Plan trading strategy
```

### Intraday (10:00 AM - 3:00 PM)
```bash
# Run continuously with 5-minute updates
python main.py

# Monitor for:
# - Volume spikes
# - Bulk/block deals
# - Institutional flow changes
```

### End of Day (4:00 PM)
```bash
# Final run for closing data
python main.py --run-once

# Review:
# - Day's performance
# - Update watchlist
# - Plan for tomorrow
```

---

## Performance Optimization

### For Multiple Stocks (>10)
```yaml
# Increase timeout
data_sources:
  nse:
    timeout: 60  # Increase from 30
```

### For Slower Internet
```yaml
# Decrease frequency
fetch_interval: 600  # 10 minutes instead of 5
```

---

## Safety & Disclaimers

⚠️ **Important Reminders**:

1. **Not Financial Advice**: This tool provides data, not recommendations
2. **Verify Data**: Always cross-check with official sources
3. **Risk Management**: Never invest more than you can afford to lose
4. **No Guarantees**: Past performance doesn't guarantee future results
5. **Do Your Research**: This is one tool among many in your toolkit

---

## Getting Help

**Issue**: Something not working?
**Solution**: Check `logs/marketmind.log` for detailed errors

**Question**: How to use a feature?
**Solution**: Read `docs/ARCHITECTURE.md` for technical details

**Request**: Want a new feature?
**Solution**: Open an issue on the project repository

---

## Next Steps

1. ✅ Master basic usage
2. 📊 Experiment with different stocks
3. 🔧 Customize configuration
4. 📖 Read architecture docs
5. 🚀 Contribute new features!

---

**Happy Analyzing! 📊📈**
