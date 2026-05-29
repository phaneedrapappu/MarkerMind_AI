# 🖥️ System Requirements – MarketMind AI

Complete checklist of software, services, and configurations needed to run MarketMind AI on any machine.

---

## ⚙️ Core System Requirements

| Component | Minimum | Recommended | Details |
|---|---|---|---|
| **OS** | Windows 7 / macOS 10.14 / Linux (any) | Windows 10+ / macOS 11+ / Ubuntu 20.04+ | Any OS with Python 3.10+ support |
| **Python** | 3.10.x | 3.10.12+ | See [python.org](https://python.org); 3.11+ also works |
| **RAM** | 2 GB | 4+ GB | For pipeline + browser simultaneous use |
| **Disk Space** | 500 MB | 2 GB | Project files, DB, charts, logs |
| **Internet** | Required | Broadband (2+ Mbps) | For market data, news, LLM APIs |
| **Git** | ✅ Required | ✅ Required | Clone project; optional for version control |

---

## 📦 Installation Steps by OS

### Windows

#### 1. Install Python 3.10+
- Download from [python.org](https://python.org/downloads/)
- **Important:** Check "Add Python to PATH" during installation
- Verify: Open Command Prompt, run `python --version`

#### 2. Install Git (optional but recommended)
- Download from [git-scm.com](https://git-scm.com/)
- Use default options; adds Git Bash terminal

#### 3. Clone Repository
```cmd
# Using Git Bash or Command Prompt
git clone https://github.com/phaneedrapappu/MarkerMind_AI.git
cd MarkerMind_AI
```

#### 4. Create Virtual Environment
```cmd
python -m venv .venv
.venv\Scripts\activate
```

#### 5. Install Dependencies
```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

#### 6. Configure `.env` (see section below)

#### 7. Run Application
```cmd
python app.py
# Open http://localhost:5050
```

---

### macOS

#### 1. Install Python 3.10+
**Option A:** Using Homebrew (recommended)
```bash
brew install python@3.10
```

**Option B:** Direct download
- Download from [python.org](https://python.org/downloads/)

Verify: `python3 --version`

#### 2. Install Git
```bash
brew install git
```

#### 3. Clone Repository
```bash
git clone https://github.com/phaneedrapappu/MarkerMind_AI.git
cd MarkerMind_AI
```

#### 4. Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 5. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 6. Configure `.env` (see section below)

#### 7. Run Application
```bash
python3 app.py
# Open http://localhost:5050
```

---

### Linux (Ubuntu/Debian)

#### 1. Install Python 3.10+
```bash
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip
python3.10 --version
```

#### 2. Install Git
```bash
sudo apt install git
```

#### 3. Clone Repository
```bash
git clone https://github.com/phaneedrapappu/MarkerMind_AI.git
cd MarkerMind_AI
```

#### 4. Create Virtual Environment
```bash
python3.10 -m venv .venv
source .venv/bin/activate
```

#### 5. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 6. Configure `.env` (see section below)

#### 7. Run Application
```bash
python3.10 app.py
# Open http://localhost:5050
```

---

## 🔑 External Services & API Keys Required

MarketMind AI requires at least **one** of the following AI providers. All market data is **free**.

### AI Provider (Choose 1 – Claude recommended)

#### 1. Claude (Anthropic) — **Recommended**
- **Cost:** Paid usage
- **Free trial:** Available
- **Sign up:** [console.anthropic.com](https://console.anthropic.com)
- **Get API key:** Claude Console → API Keys → Create Key
- **Set in `.env`:** `CLAUDE_API_KEY=sk-ant-api03-...`
- **Model:** `claude-opus-4-5` (default, premium) or `claude-3-5-sonnet` (faster, cheaper)

#### 2. Google Gemini — Free Tier Available
- **Cost:** Free up to 15 requests/minute; paid beyond that
- **Sign up:** [ai.google.dev](https://ai.google.dev/pricing)
- **Get API key:** Go to API Console → Create Key
- **Set in `.env`:** `GEMINI_API_KEY=...`
- **Model:** `gemini-2.5-flash` (recommended)

#### 3. OpenAI (GPT-4o) — Paid
- **Cost:** ~$0.01–0.03 per request
- **Sign up:** [platform.openai.com](https://platform.openai.com/signup)
- **Get API key:** Billing → API Keys → Create New
- **Set in `.env`:** `OPENAI_API_KEY=sk-...`
- **Model:** `gpt-4o-mini` (recommended for cost)

### Email Alerts (for HTML email digest)

#### Gmail with App Password (Free)
1. Enable 2-factor authentication on your Google account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Select "Mail" and "Windows Computer" (or your OS)
4. Generate 16-character password
5. Set in `.env`:
   ```env
   SMTP_USER=your.email@gmail.com
   SMTP_PASSWORD=xxxx xxxx xxxx xxxx
   ```

### Telegram Alerts (optional)

For real-time Telegram bot notifications:

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Follow prompts (choose name, username)
4. Copy the **Bot Token** (format: `123456789:ABCDEFghijklmnopQRSTUVwxyz...`)
5. Set in `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCDEFghijklmnopQRSTUVwxyz...
   ```
6. Start a chat with your new bot (send any message)
7. Open [https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe](https://api.telegram.org/botYOUR_TOKEN/getMe) to verify

### Market Data (Free)

- **NSE (India):** Fetched automatically via `yfinance` / `requests`
- **News:** RSS feeds from Google News, ET Markets, Moneycontrol (free, no key needed)
- **Historical prices:** `yfinance` library (free)

---

## 📋 Complete `.env` Template

Copy this to `.env` in the project root and fill in your keys:

```env
# ═══════════════════════════════════════════════════════════════════════════════
# MarketMind AI Configuration
# ═══════════════════════════════════════════════════════════════════════════════

# ── AI Provider (MUST choose one: claude | gemini | openai) ──────────────────
#    Default: claude (Anthropic) — recommended for quality
LLM_PROVIDER=claude

# ── Anthropic / Claude ────────────────────────────────────────────────────────
CLAUDE_API_KEY=sk-ant-api03-YOUR_KEY_HERE
CLAUDE_MODEL=claude-opus-4-5

# ── Google Gemini (free tier: 15 req/min) ─────────────────────────────────────
# GEMINI_API_KEY=YOUR_GEMINI_KEY_HERE
# GEMINI_MODEL=gemini-2.5-flash

# ── OpenAI GPT ────────────────────────────────────────────────────────────────
# OPENAI_API_KEY=sk-YOUR_KEY_HERE
# OPENAI_MODEL=gpt-4o-mini

# ── Email Alerts (SMTP via Gmail) ─────────────────────────────────────────────
#    Requires: Gmail + 2FA enabled + App Password generated
SMTP_USER=your.email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx

# ── Flask Web Server ──────────────────────────────────────────────────────────
FLASK_PORT=5050
FLASK_SECRET_KEY=change-me-to-a-very-long-random-string-with-letters-numbers

# ── Telegram Alerts (optional) ────────────────────────────────────────────────
#    Get from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCDEFghijklmnopQRSTUVwxyz

# ── Telegram Webhook (production only) ────────────────────────────────────────
#    Leave blank for localhost (polling used automatically)
#    Set to public URL for production (webhook receives Telegram updates instantly)
# TELEGRAM_WEBHOOK_URL=https://marketmind.yourdomain.com

# ── Database ──────────────────────────────────────────────────────────────────
#    Default: data/marketmind.db (SQLite; auto-created)
# DATABASE_PATH=data/marketmind.db
```

---

## 🗂️ File Structure After Installation

```
MarkerMind_AI/
├── .venv/                      # Virtual environment (created on setup)
├── data/
│   ├── marketmind.db           # SQLite database (auto-created on first run)
│   └── reports/                # Generated PNG charts
├── logs/
│   └── app.log                 # Application logs
├── .env                        # Configuration (secrets) — NEVER commit
├── .gitignore
├── app.py                      # Flask web server
├── main.py                     # CLI entry point
├── requirements.txt            # Python dependencies
├── setup.sh                    # Quick setup script (Linux/macOS)
├── config/
│   └── config.yaml             # Non-secret configuration
├── src/                        # Source code
│   ├── agents/                 # AI agents
│   ├── database/               # DB layer
│   ├── technical/              # Indicators (RSI, MACD, etc.)
│   └── ...
├── frontend/
│   ├── templates/              # HTML pages
│   └── static/                 # CSS, JS
└── README.md
```

---

## 🔧 Troubleshooting Installation

### "Python not found" / "python3: command not found"

**Windows:**
- Add Python to PATH: Reinstall Python and check "Add Python 3.x to PATH"
- Or manually add: `C:\Users\YourName\AppData\Local\Programs\Python\Python310`

**macOS/Linux:**
- Use `python3` instead of `python`
- Or verify: `which python3` / `which python`

### "pip: command not found"

```bash
# Windows
python -m pip --version

# macOS/Linux
python3 -m pip --version

# Then use:
python -m pip install -r requirements.txt
```

### Virtual environment activation fails

**Windows:**
```cmd
# Try PowerShell (Run as Administrator)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
# Make sure you're in the project root
source .venv/bin/activate
```

### "ModuleNotFoundError: No module named 'X'"

- Ensure virtual env is activated: `source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows)
- Reinstall: `pip install -r requirements.txt`
- Check Python version: `python --version` (must be 3.10+)

### Port 5050 already in use

```bash
# Find what's using port 5050
# Windows
netstat -ano | findstr :5050

# macOS/Linux
lsof -i :5050

# Then either kill the process or change FLASK_PORT in .env
```

### API key errors

- Verify API key format is correct (no extra spaces, quotes)
- Test key in `.env` is set but commented lines are uncommented
- Check all required fields are filled (at least one AI provider)

### Database errors

- Delete `data/marketmind.db` to reset (all data will be lost)
- DB auto-migrates on startup; no manual setup needed

---

## 🌐 Network & Firewall

Ensure these are **not blocked** by your firewall:

| Service | Port | Direction | Why |
|---|---|---|---|
| Flask app | 5050 (default) | Inbound | Web dashboard |
| NSE/yfinance | 443 (HTTPS) | Outbound | Market data |
| Gmail SMTP | 587 | Outbound | Email sending |
| Telegram API | 443 (HTTPS) | Outbound | Telegram messages |
| LLM APIs | 443 (HTTPS) | Outbound | Claude / Gemini / OpenAI |

---

## 📊 Recommended Hardware for Production

| Scenario | CPU | RAM | Storage | Notes |
|---|---|---|---|---|
| **Local testing** | 2 cores | 2 GB | 500 MB | On your laptop |
| **Small pilot (5–10 users)** | 2 cores | 4 GB | 1 GB | VPS: Digital Ocean, Heroku |
| **Medium (50–100 users)** | 4 cores | 8 GB | 5 GB | Add background job queue (Celery) |
| **Large (1000+)** | 8+ cores | 16+ GB | 20+ GB | Postgres DB, load balancer, CDN |

---

## ✅ Verification Checklist

After installation, verify everything is working:

```bash
# 1. Python & pip
python --version          # Should be 3.10+
pip --version

# 2. Virtual environment activated
which python              # Should show path inside .venv

# 3. Dependencies installed
pip list | grep -E "requests|flask|pandas|anthropic"

# 4. .env file exists and has at least one API key
ls -la .env
cat .env | grep -E "CLAUDE_API_KEY|GEMINI_API_KEY|OPENAI_API_KEY"

# 5. Start the app
python app.py
# Should see: "WARNING in app.run: This is a development server..."
# Open http://localhost:5050 in browser

# 6. Dashboard loads
curl http://localhost:5050/
# Should return HTML (not error)

# 7. API working
curl http://localhost:5050/api/pipeline/status
# Should return: {"running": false}
```

---

## 🚀 Next Steps After Setup

1. **Create user account** → `/register`
2. **Add first stocks** → Run Analysis modal
3. **Subscribe to Telegram** (optional) → Portfolio page
4. **Set up email alerts** (optional) → Subscribe page
5. **Configure scheduler** → See [USAGE.md](docs/USAGE.md)

---

## 📞 Support & Troubleshooting

- **Installation issues?** Check this file first — most problems are environment-related
- **API key errors?** Verify key format, billing enabled, rate limits not exceeded
- **Performance slow?** Check network; NSE/API latency varies by time of day
- **Database errors?** Delete DB file to reset; auto-migration on restart
- **Deployment help?** See [INSTALLATION.md](docs/INSTALLATION.md) for systemd / Docker

---

**Ready to go?** Start with `python app.py` and open [http://localhost:5050](http://localhost:5050). 🚀
