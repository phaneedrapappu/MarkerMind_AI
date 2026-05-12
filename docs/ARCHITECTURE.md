# MarketMind AI - Multi-Agent Architecture Documentation

## Overview

MarketMind AI is built on a **multi-step, multi-agent architecture** where specialized agents work together in an orchestrated pipeline to deliver real-time financial intelligence.

## Architecture Principles

1. **Modularity**: Each agent is independent and handles a specific responsibility
2. **Scalability**: Agents can be scaled independently based on load
3. **Fault Tolerance**: Failure in one agent doesn't crash the entire system
4. **Extensibility**: New agents can be added without modifying existing ones
5. **Real-time Processing**: Continuous data flow through message queues

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR LAYER                          │
│  - Agent Lifecycle Management                                   │
│  - Task Scheduling & Coordination                               │
│  - Health Monitoring                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────────┐
        │                                              │
        ▼                                              ▼
┌─────────────────┐                          ┌─────────────────┐
│  MARKET DATA    │                          │  NEWS ANALYSIS  │
│     AGENT       │                          │     AGENT       │
└─────────────────┘                          └─────────────────┘
        │                                              │
        │  ┌─────────────┐   ┌─────────────┐         │
        └─▶│  NSE API    │   │  News APIs  │◀────────┘
           └─────────────┘   └─────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  MESSAGE QUEUE    │
                    │  (Kafka/RabbitMQ) │
                    └───────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────────┐
        │                                              │
        ▼                                              ▼
┌─────────────────┐                          ┌─────────────────┐
│  UNUSUAL        │                          │  CORRELATION    │
│  ACTIVITY       │                          │  & SIGNAL       │
│  AGENT          │                          │  AGENT          │
└─────────────────┘                          └─────────────────┘
        │                                              │
        └──────────────────┬───────────────────────────┘
                           ▼
                  ┌─────────────────┐
                  │  ALERT AGENT    │
                  └─────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  NOTIFICATION   │
                  │  SERVICE        │
                  │  (WhatsApp)     │
                  └─────────────────┘
                           │
                           ▼
                    ┌──────────┐
                    │  USERS   │
                    └──────────┘
```

---

## Agent Details

### 1. Market Data Agent ✅ (Implemented)

**Purpose**: Fetch real-time market data from stock exchanges

**Responsibilities**:
- Real-time stock quotes (price, volume, high/low)
- Bulk and block deals monitoring
- FII/DII institutional flows tracking
- Promoter holding patterns

**Data Sources**:
- NSE (National Stock Exchange of India)
- BSE (Bombay Stock Exchange) - planned

**Output**:
- `MarketDataSnapshot` objects containing:
  - Stock data
  - Bulk/block deals
  - Institutional activity
  - Promoter holdings

**Execution Frequency**: Every 5 minutes (configurable)

**Technology**: Python, requests, BeautifulSoup4

---

### 2. News Analysis Agent 🚧 (Planned)

**Purpose**: Scrape and analyze global financial news

**Responsibilities**:
- News ingestion from multiple sources
- Entity extraction (companies, sectors, events)
- Sentiment analysis (positive/negative/neutral)
- Event detection (earnings, mergers, regulatory changes)
- Geographic filtering (US, Europe, China, India)

**Data Sources**:
- RSS feeds from major financial news outlets
- News APIs (NewsAPI, Google News)
- Economic calendars

**Output**:
- `NewsArticle` objects with:
  - Title, content, source
  - Sentiment score
  - Extracted entities
  - Impact score

**Technology**: Python, spaCy, Transformers (BERT/FinBERT), NLTK

---

### 3. Unusual Activity Detection Agent 🚧 (Planned)

**Purpose**: Detect abnormal market patterns and unusual activities

**Responsibilities**:
- Volume spike detection (>3x average volume)
- Price movement anomalies (>5% intraday move)
- Unusual bulk/block deals (>2% of market cap)
- Sector rotation detection
- Institutional flow anomalies
- Correlation breaks

**Input**:
- Historical market data
- Real-time market data from Market Data Agent
- Statistical baselines

**Output**:
- `UnusualActivity` alerts with:
  - Activity type
  - Severity score
  - Affected stocks/sectors
  - Context and explanation

**Technology**: Python, pandas, numpy, scikit-learn (statistical models)

---

### 4. Correlation & Signal Agent 🚧 (Planned)

**Purpose**: Correlate market data with news to generate trading signals

**Responsibilities**:
- Link market movements to news events
- Cross-reference institutional activity with news sentiment
- Generate composite signals (buy/sell/hold)
- Risk assessment
- Confidence scoring

**Input**:
- Market data snapshots
- News articles with sentiment
- Unusual activity alerts

**Output**:
- `TradingSignal` objects with:
  - Stock symbol
  - Signal type (buy/sell/hold)
  - Confidence score
  - Supporting evidence
  - Risk level

**Technology**: Python, ML models (Random Forest, XGBoost)

---

### 5. Alert Agent 🚧 (Planned)

**Purpose**: Prioritize and deliver actionable alerts to users

**Responsibilities**:
- Alert prioritization based on user preferences
- Deduplication of similar alerts
- Alert formatting for readability
- Rate limiting (avoid alert fatigue)
- User preference management

**Input**:
- Trading signals
- Unusual activity alerts
- User preferences

**Output**:
- Formatted notifications ready for delivery

**Technology**: Python, rule-based system

---

### 6. Notification Agent 🚧 (Planned)

**Purpose**: Deliver alerts via multiple channels

**Responsibilities**:
- WhatsApp message delivery
- SMS/Email fallback (optional)
- Delivery confirmation
- Rate limiting compliance

**Technology**: Twilio WhatsApp Business API

---

## Data Flow: Multi-Step Pipeline

### Step 1: Data Acquisition
```
Market Data Agent → NSE/BSE APIs
News Agent → News APIs/RSS Feeds
     ↓
Raw Data (JSON/XML)
```

### Step 2: Data Processing
```
Raw Data → Data Cleaning → Normalization → Entity Extraction
     ↓
Structured Data (StockData, NewsArticle objects)
```

### Step 3: Analysis
```
Structured Data → Unusual Activity Detection
                → Sentiment Analysis
                → Correlation Analysis
     ↓
Insights & Signals
```

### Step 4: Signal Generation
```
Insights → Correlation & Signal Agent → Trading Signals
     ↓
Prioritized Signals
```

### Step 5: Alert & Delivery
```
Trading Signals → Alert Agent → Notification Agent → User (WhatsApp)
```

---

## Message Queue Architecture

### Why Message Queues?

1. **Decoupling**: Agents don't need to know about each other
2. **Asynchronous Processing**: Non-blocking operations
3. **Scalability**: Easy to add more agent instances
4. **Reliability**: Messages are persisted
5. **Load Balancing**: Distribute work across agent instances

### Queue Design

```
┌────────────────┐
│  Market Data   │
│     Queue      │
└────────────────┘
        │
        ├─▶ Unusual Activity Agent (Consumer 1)
        ├─▶ Correlation Agent (Consumer 2)
        └─▶ Database Writer (Consumer 3)

┌────────────────┐
│  News Data     │
│     Queue      │
└────────────────┘
        │
        ├─▶ Sentiment Analysis Agent
        └─▶ Correlation Agent

┌────────────────┐
│  Signals       │
│     Queue      │
└────────────────┘
        │
        └─▶ Alert Agent
```

### Technology Options

- **Kafka**: Best for high-throughput, streaming data
- **RabbitMQ**: Best for message routing, priority queues
- **Redis Streams**: Lightweight, fast, good for simple cases

---

## Database Schema

### Tables

1. **stocks**
   - symbol, company_name, sector, market_cap

2. **stock_prices**
   - symbol, timestamp, price, volume, high, low, close

3. **bulk_block_deals**
   - symbol, date, deal_type, client_name, quantity, price

4. **institutional_activity**
   - date, institution_type, buy_value, sell_value, net_value

5. **news_articles**
   - title, content, source, published_at, sentiment_score

6. **trading_signals**
   - symbol, signal_type, confidence, generated_at

7. **alerts**
   - user_id, alert_type, message, sent_at, delivered

---

## Technology Stack

### Current Implementation
- **Language**: Python 3.8+
- **Data Fetching**: requests, BeautifulSoup4
- **Data Processing**: pandas, numpy
- **Configuration**: YAML
- **Logging**: Python logging module

### Planned Additions
- **NLP**: spaCy, Transformers (HuggingFace)
- **ML**: scikit-learn, XGBoost, PyTorch/TensorFlow
- **Database**: PostgreSQL, SQLAlchemy
- **Message Queue**: Kafka or RabbitMQ
- **API**: FastAPI (for web interface)
- **Notifications**: Twilio (WhatsApp Business API)
- **Containerization**: Docker, Kubernetes
- **Monitoring**: Prometheus, Grafana

---

## Deployment Architecture

```
┌───────────────────────────────────────────────────┐
│                 Load Balancer                     │
└───────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
   ┌────────┐   ┌────────┐   ┌────────┐
   │ Agent  │   │ Agent  │   │ Agent  │
   │ Pod 1  │   │ Pod 2  │   │ Pod 3  │
   └────────┘   └────────┘   └────────┘
        │             │             │
        └─────────────┼─────────────┘
                      ▼
              ┌───────────────┐
              │   Kafka       │
              │   Cluster     │
              └───────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  PostgreSQL   │
              │  Database     │
              └───────────────┘
```

### Kubernetes Deployment
- Each agent runs in a separate pod
- Horizontal Pod Autoscaling (HPA) based on queue depth
- Persistent volumes for database and logs
- ConfigMaps for configuration
- Secrets for API keys

---

## Scaling Strategy

### Horizontal Scaling
- Add more agent instances as load increases
- Use message queues for work distribution
- Stateless agents for easy scaling

### Vertical Scaling
- Increase resources (CPU/RAM) for ML-heavy agents
- GPU support for deep learning models

### Data Partitioning
- Partition by stock symbol
- Partition by time (historical vs. real-time)

---

## Error Handling & Resilience

1. **Retry Logic**: Exponential backoff for API failures
2. **Circuit Breakers**: Stop calling failing services
3. **Graceful Degradation**: Continue with partial data
4. **Dead Letter Queues**: Handle poison messages
5. **Health Checks**: Monitor agent status
6. **Alerting**: Notify admins of critical failures

---

## Security Considerations

1. **API Key Management**: Store in secrets manager
2. **Rate Limiting**: Respect exchange API limits
3. **Data Encryption**: Encrypt sensitive data at rest
4. **Access Control**: Role-based access for admin functions
5. **Audit Logging**: Track all system actions

---

## Performance Optimization

1. **Caching**: Cache frequently accessed data (Redis)
2. **Batch Processing**: Process multiple stocks together
3. **Async I/O**: Use asyncio for concurrent API calls
4. **Connection Pooling**: Reuse HTTP connections
5. **Compression**: Compress data in transit

---

## Monitoring & Observability

1. **Metrics**: Track agent execution time, success rate, queue depth
2. **Logs**: Centralized logging (ELK stack)
3. **Tracing**: Distributed tracing (Jaeger)
4. **Dashboards**: Real-time system health (Grafana)
5. **Alerts**: Alert on anomalies and failures

---

## Future Enhancements

1. **Machine Learning Models**:
   - LSTM for price prediction
   - Reinforcement learning for trading strategies
   - NLP models for advanced sentiment analysis

2. **Additional Data Sources**:
   - Options data
   - Futures & derivatives
   - Crypto markets
   - Global indices

3. **User Features**:
   - Portfolio tracking
   - Backtesting
   - Custom alert rules
   - Watchlists

4. **Advanced Analytics**:
   - Technical indicators (RSI, MACD, Bollinger Bands)
   - Fundamental analysis
   - Peer comparison
   - Sector analysis

---

## Development Roadmap

### Phase 1: Foundation ✅
- [x] Project structure
- [x] Market Data Agent
- [x] Configuration system
- [x] Logging

### Phase 2: Core Agents 🚧
- [ ] News Analysis Agent
- [ ] Unusual Activity Detection Agent
- [ ] Alert Agent
- [ ] Database integration

### Phase 3: Intelligence 🔮
- [ ] Correlation & Signal Agent
- [ ] ML models for prediction
- [ ] Advanced pattern detection

### Phase 4: Delivery 🔮
- [ ] WhatsApp integration
- [ ] Web dashboard
- [ ] Mobile app (optional)

### Phase 5: Scale 🔮
- [ ] Kubernetes deployment
- [ ] Message queue (Kafka)
- [ ] Multi-region support

---

## Contributing

Agents are designed to be independent. To add a new agent:

1. Create a new agent class inheriting from `BaseAgent`
2. Implement `initialize()`, `execute()`, and `cleanup()`
3. Add configuration in `config.yaml`
4. Register in `orchestrator.py`
5. Add tests

---

**Last Updated**: May 11, 2026
**Version**: 0.1.0
