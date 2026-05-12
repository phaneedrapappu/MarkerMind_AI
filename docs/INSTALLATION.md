# Installation & Setup Guide

## Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu/Debian recommended), macOS, or Windows with WSL
- **Python**: 3.8 or higher
- **RAM**: Minimum 2GB
- **Internet**: Stable connection for API calls

### Required Software
```bash
# Check Python version
python3 --version  # Should be 3.8+

# Check pip
pip3 --version
```

---

## Installation Methods

### Method 1: Quick Setup (Recommended)

```bash
# Navigate to project directory
cd /home/phaneendrapappu/workspace/minna_project/MarkerMind_AI

# Run the quick setup script
chmod +x setup.sh
./setup.sh
```

This script will:
1. Create a virtual environment
2. Install all dependencies
3. Create necessary directories

---

### Method 2: Manual Setup

#### Step 1: Install Python Virtual Environment Package (Ubuntu/Debian)

```bash
# Install python3-venv if not already installed
sudo apt update
sudo apt install python3-venv python3-pip -y
```

#### Step 2: Create Virtual Environment

```bash
cd /home/phaneendrapappu/workspace/minna_project/MarkerMind_AI

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate     # Windows
```

#### Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

#### Step 4: Verify Installation

```bash
# Check installed packages
pip list
```

---

### Method 3: User-Level Installation (No Virtual Environment)

If you can't create a virtual environment:

```bash
# Install dependencies for current user only
pip3 install -r requirements.txt --user
```

**Note**: This installs packages globally for your user. Not recommended for production but fine for testing.

---

## Post-Installation Configuration

### 1. Configure Stock Symbols

Edit `config/config.yaml`:

```yaml
agents:
  market_data_agent:
    enabled: true
    fetch_interval: 300  # 5 minutes
    stocks:
      - "TCS"          # Tata Consultancy Services
      - "WIPRO"        # Wipro Limited
      - "DMART"        # Avenue Supermarts (DMart)
      - "RELIANCE"     # Add more stocks as needed
      - "INFY"         # Infosys
      - "HDFCBANK"     # HDFC Bank
```

### 2. Adjust Fetch Interval

```yaml
agents:
  market_data_agent:
    fetch_interval: 300  # seconds (300 = 5 minutes)
```

**Recommended intervals**:
- Aggressive: 60 seconds (1 minute)
- Normal: 300 seconds (5 minutes)
- Conservative: 900 seconds (15 minutes)

**Note**: Too frequent requests may get rate-limited by NSE.

---

## Verify Installation

### Test 1: Quick Connection Test

```bash
# Activate virtual environment first
source venv/bin/activate

# Run connection test
python test_connection.py
```

Expected output:
```
============================================================
  Testing NSE Data Fetcher
============================================================

📊 Fetching data for TCS...
✅ SUCCESS: Tata Consultancy Services Limited
   Price: ₹3,845.50
   Change: +1.19%
   Volume: 2,458,932
```

### Test 2: Run Full System

```bash
python main.py
```

Expected output:
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
...
```

---

## Troubleshooting

### Issue 1: `ensurepip is not available`

**Error**:
```
The virtual environment was not created successfully because ensurepip is not available.
```

**Solution**:
```bash
# Ubuntu/Debian
sudo apt install python3-venv

# Fedora/RHEL
sudo dnf install python3-virtualenv

# macOS (using Homebrew)
brew install python3
```

---

### Issue 2: `requests module not found`

**Error**:
```
ModuleNotFoundError: No module named 'requests'
```

**Solution**:
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt
```

---

### Issue 3: NSE Connection Errors

**Error**:
```
Request failed with status code: 403
```

**Solution**:
NSE may block automated requests. This is usually temporary. Try:

1. Wait a few minutes and retry
2. Check your internet connection
3. Verify NSE website is accessible: https://www.nseindia.com
4. The script includes proper headers to avoid blocks, but NSE may have updated their policies

---

### Issue 4: No Data Returned

**Error**:
```
❌ FAILED: No data received
```

**Possible Causes**:
1. **Market Closed**: NSE only provides real-time data during market hours (9:15 AM - 3:30 PM IST)
2. **Incorrect Symbol**: Verify stock symbol is correct (use NSE symbols)
3. **API Changes**: NSE may have changed their API structure

**Solution**:
- Test during market hours (9:15 AM - 3:30 PM IST, Monday-Friday)
- Verify stock symbols at: https://www.nseindia.com
- Check logs in `logs/marketmind.log` for detailed errors

---

### Issue 5: Permission Denied

**Error**:
```
PermissionError: [Errno 13] Permission denied: 'logs/marketmind.log'
```

**Solution**:
```bash
# Create logs directory with proper permissions
mkdir -p logs data
chmod 755 logs data
```

---

## Directory Structure After Installation

```
MarkerMind_AI/
├── config/
│   └── config.yaml              # ✅ Configuration
├── src/
│   ├── agents/                  # ✅ Agent implementations
│   ├── data_sources/            # ✅ Data fetchers
│   └── models/                  # ✅ Data models
├── logs/
│   └── marketmind.log           # 📝 Generated after first run
├── data/                        # 📁 Data storage (created on first run)
├── venv/                        # 🐍 Virtual environment
├── main.py                      # ✅ Main entry point
├── test_connection.py           # ✅ Connection test
└── requirements.txt             # ✅ Dependencies
```

---

## Running in Production

### 1. Using Screen (Keeps Running After Logout)

```bash
# Start a screen session
screen -S marketmind

# Activate environment and run
cd /home/phaneendrapappu/workspace/minna_project/MarkerMind_AI
source venv/bin/activate
python main.py

# Detach from screen: Press Ctrl+A, then D

# Reattach later
screen -r marketmind
```

### 2. Using Systemd Service

Create `/etc/systemd/system/marketmind.service`:

```ini
[Unit]
Description=MarketMind AI Financial Intelligence Agent
After=network.target

[Service]
Type=simple
User=phaneendrapappu
WorkingDirectory=/home/phaneendrapappu/workspace/minna_project/MarkerMind_AI
Environment="PATH=/home/phaneendrapappu/workspace/minna_project/MarkerMind_AI/venv/bin"
ExecStart=/home/phaneendrapappu/workspace/minna_project/MarkerMind_AI/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable marketmind
sudo systemctl start marketmind

# Check status
sudo systemctl status marketmind

# View logs
sudo journalctl -u marketmind -f
```

### 3. Using Docker (Advanced)

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

Build and run:
```bash
docker build -t marketmind-ai .
docker run -d --name marketmind marketmind-ai
```

---

## Updating the System

```bash
# Activate virtual environment
source venv/bin/activate

# Pull latest code (if using git)
git pull

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart the application
python main.py
```

---

## Uninstallation

```bash
# Stop any running instances
# If using systemd:
sudo systemctl stop marketmind
sudo systemctl disable marketmind

# Remove virtual environment
rm -rf venv/

# Remove data and logs (optional)
rm -rf data/ logs/

# Remove the entire project (if desired)
cd ..
rm -rf MarkerMind_AI/
```

---

## Next Steps

After successful installation:

1. ✅ **Run the connection test**: `python test_connection.py`
2. ✅ **Configure your stocks**: Edit `config/config.yaml`
3. ✅ **Run the system**: `python main.py`
4. 📖 **Read the architecture**: `docs/ARCHITECTURE.md`
5. 🚀 **Explore the code**: Start with `src/agents/market_data_agent.py`

---

## Getting Help

- **Logs**: Check `logs/marketmind.log` for detailed error messages
- **Documentation**: Read `docs/ARCHITECTURE.md` for system design
- **Issues**: Report bugs or ask questions in the project repository

---

**Happy Trading! 📈**
