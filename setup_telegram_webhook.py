#!/usr/bin/env python3
"""
Register (or inspect / delete) the Telegram webhook for MarketMind AI.

Usage:
    python3 setup_telegram_webhook.py set    <public_url>
    python3 setup_telegram_webhook.py info
    python3 setup_telegram_webhook.py delete

Examples:
    python3 setup_telegram_webhook.py set https://yourdomain.com
    python3 setup_telegram_webhook.py set https://abc123.ngrok-free.app   # local dev

The script appends /api/telegram/webhook to the URL automatically.

Requirements:
    TELEGRAM_BOT_TOKEN must be set in .env or the environment.
"""

import os
import sys
import requests
from pathlib import Path

# Load .env
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
    sys.exit(1)

BASE = f"https://api.telegram.org/bot{TOKEN}"


def cmd_info():
    r = requests.get(f"{BASE}/getWebhookInfo", timeout=10)
    info = r.json().get("result", {})
    print(f"  URL          : {info.get('url') or '(not set)'}")
    print(f"  Pending count: {info.get('pending_update_count', 0)}")
    print(f"  Last error   : {info.get('last_error_message') or 'none'}")


def cmd_set(base_url: str):
    webhook_url = base_url.rstrip("/") + "/api/telegram/webhook"
    r = requests.post(f"{BASE}/setWebhook", json={"url": webhook_url}, timeout=10)
    result = r.json()
    if result.get("ok"):
        print(f"✅ Webhook set to: {webhook_url}")
    else:
        print(f"❌ Failed: {result}")


def cmd_delete():
    r = requests.post(f"{BASE}/deleteWebhook", timeout=10)
    print("✅ Webhook deleted." if r.json().get("ok") else f"❌ {r.json()}")


action = sys.argv[1] if len(sys.argv) > 1 else "info"

if action == "info":
    cmd_info()
elif action == "set":
    if len(sys.argv) < 3:
        print("Usage: python3 setup_telegram_webhook.py set <public_url>")
        sys.exit(1)
    cmd_set(sys.argv[2])
elif action == "delete":
    cmd_delete()
else:
    print(__doc__)
