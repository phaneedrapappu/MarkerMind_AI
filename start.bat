@echo off
:: ─────────────────────────────────────────────────────────────────────────────
::  MarketMind AI – One-click launcher (Windows)
::  Usage:  Double-click start.bat  OR  run from command prompt
::          start.bat --reset       (wipe venv and reinstall)
:: ─────────────────────────────────────────────────────────────────────────────
setlocal enabledelayedexpansion
title MarketMind AI

cd /d "%~dp0"

echo.
echo ══════════════════════════════════════════════
echo          MarketMind AI – Startup
echo ══════════════════════════════════════════════
echo.

:: ── Handle --reset ────────────────────────────────────────────────────────────
if "%1"=="--reset" (
    echo [WARN]  Removing existing virtual environment...
    if exist venv rmdir /s /q venv
)

:: ── 1. Check Python ───────────────────────────────────────────────────────────
echo [INFO]  Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERR]   Python not found. Install from https://www.python.org/downloads/
    echo         Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [ OK ]  Found Python %PYVER%

:: ── 2. Create virtual environment ────────────────────────────────────────────
if not exist venv (
    echo [INFO]  Creating virtual environment...
    python -m venv venv
    echo [ OK ]  Virtual environment created
) else (
    echo [ OK ]  Virtual environment exists
)

:: ── 3. Activate and install dependencies ─────────────────────────────────────
echo [INFO]  Activating virtual environment...
call venv\Scripts\activate.bat

echo [INFO]  Installing / updating dependencies...
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERR]   Dependency installation failed. Check your internet connection.
    pause
    exit /b 1
)
echo [ OK ]  Dependencies installed

:: ── 4. Create required directories ───────────────────────────────────────────
if not exist data mkdir data
if not exist logs mkdir logs
if not exist data\reports mkdir data\reports
echo [ OK ]  Directories ready

:: ── 5. Set up .env if missing ─────────────────────────────────────────────────
if not exist .env (
    echo [WARN]  .env not found — creating from .env.example
    copy .env.example .env >nul

    :: Auto-generate FLASK_SECRET_KEY
    for /f %%k in ('python -c "import secrets; print(secrets.token_hex(32))"') do set SK=%%k
    python -c "import re,pathlib; p=pathlib.Path('.env'); t=p.read_text(); t=re.sub(r'FLASK_SECRET_KEY=.*','FLASK_SECRET_KEY=!SK!',t); p.write_text(t)"

    echo [ OK ]  Created .env with auto-generated FLASK_SECRET_KEY
    echo.
    echo  ┌──────────────────────────────────────────────────────────────────┐
    echo  │  ACTION REQUIRED: Edit .env and fill in your API keys            │
    echo  │                                                                  │
    echo  │  1. LLM key (at least one):                                      │
    echo  │     Claude : https://console.anthropic.com/                      │
    echo  │     Gemini : https://aistudio.google.com/app/apikey  (free)      │
    echo  │                                                                  │
    echo  │  2. Email (optional):                                            │
    echo  │     SMTP_USER + SMTP_PASSWORD (Gmail App Password)               │
    echo  │     https://myaccount.google.com/apppasswords                   │
    echo  │                                                                  │
    echo  │  3. Telegram (optional): TELEGRAM_BOT_TOKEN                      │
    echo  │     Create bot at https://t.me/botfather                         │
    echo  └──────────────────────────────────────────────────────────────────┘
    echo.
    set /p OPEN_ENV="  Open .env in Notepad now? [y/N] "
    if /i "!OPEN_ENV!"=="y" notepad .env
    echo  Rerun start.bat after saving your API keys.
    pause
    exit /b 0
) else (
    echo [ OK ]  .env file exists
)

:: ── 6. Check config warnings ─────────────────────────────────────────────────
echo [INFO]  Checking configuration...
python -c "
from dotenv import load_dotenv; load_dotenv()
import os
issues = []
sk = os.getenv('FLASK_SECRET_KEY','')
if not sk or 'change_me' in sk:
    issues.append('FLASK_SECRET_KEY not set — sessions reset on restart')
provider = os.getenv('LLM_PROVIDER','gemini').lower()
key_map = {'claude':'CLAUDE_API_KEY','gemini':'GEMINI_API_KEY','openai':'OPENAI_API_KEY'}
llm_key = os.getenv(key_map.get(provider,'GEMINI_API_KEY'),'')
if llm_key in {'your-claude-api-key-here','your-gemini-api-key-here','sk-your-openai-api-key-here',''}:
    issues.append(key_map.get(provider)+' not set — Run Analysis will fail')
for i in issues: print('  [WARN] ',i)
"
echo.

:: ── 7. Start the app ─────────────────────────────────────────────────────────
echo [ OK ]  Starting MarketMind AI...
echo.
echo   Opening http://localhost:5050 in your browser in 3 seconds...
echo   Press Ctrl+C to stop the server
echo.
timeout /t 3 /nobreak >nul
start http://localhost:5050
python app.py

pause
