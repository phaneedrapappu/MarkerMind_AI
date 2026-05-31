#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  MarketMind AI – One-click launcher (Linux / macOS)
#  Usage:  bash start.sh          (first run: sets everything up)
#          bash start.sh --reset  (wipe venv and reinstall)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERR]${NC}   $*"; exit 1; }

echo ""
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo -e "${CYAN}         MarketMind AI – Startup              ${NC}"
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo ""

# ── Handle --reset flag ───────────────────────────────────────────────────────
if [[ "${1:-}" == "--reset" ]]; then
    warn "Removing existing virtual environment…"
    rm -rf venv
fi

# ── 1. Check Python ───────────────────────────────────────────────────────────
info "Checking Python version…"
PY=""
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" -c "import sys; print(sys.version_info[:2])" 2>/dev/null)
        MAJOR=$("$cmd" -c "import sys; print(sys.version_info.major)")
        MINOR=$("$cmd" -c "import sys; print(sys.version_info.minor)")
        if [[ "$MAJOR" -ge 3 && "$MINOR" -ge 10 ]]; then
            PY="$cmd"
            ok "Found $cmd ($VER)"
            break
        fi
    fi
done
if [[ -z "$PY" ]]; then
    error "Python 3.10+ is required but not found.\n  Install: https://www.python.org/downloads/"
fi

# ── 2. Create virtual environment ────────────────────────────────────────────
if [[ -d "venv" && ! -f "venv/bin/activate" ]]; then
    warn "Virtual environment is incomplete/corrupt — recreating…"
    rm -rf venv
fi

if [[ ! -d "venv" ]]; then
    info "Creating virtual environment…"
    if ! "$PY" -m venv venv 2>/tmp/venv_err; then
        rm -rf venv
        cat /tmp/venv_err >&2
        echo ""
        echo -e "${RED}  Failed to create virtual environment.${NC}"
        echo -e "${YELLOW}  The 'venv' module is missing for ${PY}. Fix with:${NC}"
        echo ""
        # Detect package manager and suggest the right command
        if command -v apt &>/dev/null; then
            PY_VER=$("$PY" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            echo -e "      ${CYAN}sudo apt install python${PY_VER}-venv${NC}"
        elif command -v dnf &>/dev/null; then
            echo -e "      ${CYAN}sudo dnf install python3-virtualenv${NC}"
        elif command -v brew &>/dev/null; then
            echo -e "      ${CYAN}brew install python${NC}"
        else
            echo -e "      Install the venv package for your Python version"
        fi
        echo ""
        echo -e "  Then re-run:  ${CYAN}bash start.sh${NC}"
        echo ""
        exit 1
    fi
    ok "Virtual environment created"
else
    ok "Virtual environment exists"
fi

# ── 3. Activate and install dependencies ─────────────────────────────────────
info "Activating virtual environment…"
# shellcheck disable=SC1091
source venv/bin/activate

info "Installing / updating dependencies…"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
ok "Dependencies installed"

# ── 4. Create required directories ───────────────────────────────────────────
mkdir -p data logs data/reports
ok "Directories ready"

# ── 5. Set up .env if missing ─────────────────────────────────────────────────
if [[ ! -f ".env" ]]; then
    warn ".env not found — creating from .env.example"
    cp .env.example .env

    # Auto-generate a secure FLASK_SECRET_KEY
    SK=$("$PY" -c "import secrets; print(secrets.token_hex(32))")
    # Replace the placeholder on any OS (use Python for portability)
    "$PY" -c "
import re, pathlib
p = pathlib.Path('.env')
text = p.read_text()
text = re.sub(r'FLASK_SECRET_KEY=.*', 'FLASK_SECRET_KEY=${SK}', text)
p.write_text(text)
"
    ok "Created .env with auto-generated FLASK_SECRET_KEY"
    echo ""
    echo -e "${YELLOW}  ┌──────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${YELLOW}  │  ACTION REQUIRED: Edit .env and fill in your API keys                │${NC}"
    echo -e "${YELLOW}  │                                                                      │${NC}"
    echo -e "${YELLOW}  │  1. LLM key (at least one):                                          │${NC}"
    echo -e "${YELLOW}  │     • Claude : https://console.anthropic.com/                        │${NC}"
    echo -e "${YELLOW}  │     • Gemini : https://aistudio.google.com/app/apikey (free)         │${NC}"
    echo -e "${YELLOW}  │                                                                      │${NC}"
    echo -e "${YELLOW}  │  2. Email (optional, for alert emails):                              │${NC}"
    echo -e "${YELLOW}  │     SMTP_USER + SMTP_PASSWORD (Gmail App Password)                   │${NC}"
    echo -e "${YELLOW}  │     https://myaccount.google.com/apppasswords                       │${NC}"
    echo -e "${YELLOW}  │                                                                      │${NC}"
    echo -e "${YELLOW}  │  3. Telegram (optional): TELEGRAM_BOT_TOKEN                          │${NC}"
    echo -e "${YELLOW}  │     Create bot at https://t.me/botfather                             │${NC}"
    echo -e "${YELLOW}  └──────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
    read -rp "  Open .env in your editor now? [y/N] " REPLY
    if [[ "${REPLY,,}" == "y" ]]; then
        ${EDITOR:-nano} .env
    fi
else
    ok ".env file exists"
fi

# ── 6. Check critical env vars are set ───────────────────────────────────────
info "Checking configuration…"
"$PY" -c "
from dotenv import load_dotenv; load_dotenv()
import os, sys

issues = []
sk = os.getenv('FLASK_SECRET_KEY','')
if not sk or 'change_me' in sk:
    issues.append('FLASK_SECRET_KEY is not set — sessions will not persist across restarts')

provider = os.getenv('LLM_PROVIDER','gemini').lower()
key_map = {'claude': 'CLAUDE_API_KEY', 'gemini': 'GEMINI_API_KEY', 'openai': 'OPENAI_API_KEY'}
llm_key = os.getenv(key_map.get(provider, 'GEMINI_API_KEY'),'')
placeholder_vals = {'your-claude-api-key-here','your-gemini-api-key-here','sk-your-openai-api-key-here',''}
if llm_key in placeholder_vals:
    issues.append(f'{key_map.get(provider)} is not configured — Run Analysis will fail')

if not os.getenv('SMTP_USER') or os.getenv('SMTP_USER','').endswith('@gmail.com') and 'your_email' in os.getenv('SMTP_USER',''):
    issues.append('SMTP_USER not configured — email alerts will be skipped (optional)')

for i in issues:
    print(f'  \033[1;33m[WARN]\033[0m  {i}')
sys.exit(0)
"
echo ""

# ── 7. Start the app ─────────────────────────────────────────────────────────
PORT=$(grep -E "^FLASK_PORT=" .env 2>/dev/null | cut -d'=' -f2 | tr -d ' \r' || echo "5050")
PORT="${PORT:-5050}"

ok "Starting MarketMind AI on http://localhost:${PORT}"
echo ""
echo -e "  Press ${CYAN}Ctrl+C${NC} to stop"
echo ""

"$PY" app.py
