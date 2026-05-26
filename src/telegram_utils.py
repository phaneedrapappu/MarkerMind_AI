"""
MarketMind AI — Telegram alert utilities
=========================================
Sends signal summaries to users who have Telegram alerts enabled.

Credentials are read from the per-user DB record (telegram_bot_token /
telegram_chat_id) with a fallback to the process-level env vars
TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID set in .env.

Usage
-------
    from src.telegram_utils import send_pipeline_alerts
    send_pipeline_alerts(db, signals)        # call after every pipeline run
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

SIGNAL_EMOJI = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}


def _send_message(bot_token: str, chat_id: str, text: str) -> bool:
    """POST a single message. Returns True on success."""
    try:
        url = _TELEGRAM_API.format(token=bot_token)
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("Telegram send failed: %s", exc)
        return False


def build_signal_message(signals: list[dict[str, Any]]) -> str:
    """
    Format a list of signal dicts into a concise Telegram message.
    Each signal dict is expected to have: symbol, signal_type, confidence, reasoning.
    """
    if not signals:
        return "📊 <b>MarketMind AI</b>\nPipeline ran — no new signals generated."

    lines = ["📊 <b>MarketMind AI Signal Alert</b>\n"]
    for s in signals[:10]:  # cap at 10 so the message stays readable
        sym = s.get("symbol", "?")
        sig = s.get("signal_type", "HOLD")
        conf = s.get("confidence", "")
        emoji = SIGNAL_EMOJI.get(sig, "⚪")
        conf_str = f"  <i>({conf}%)</i>" if conf else ""
        lines.append(f"{emoji} <b>{sym}</b>  →  {sig}{conf_str}")

    if len(signals) > 10:
        lines.append(f"\n…and {len(signals) - 10} more signals in the dashboard.")

    lines.append("\n🔗 <a href='http://localhost:5050'>Open Dashboard</a>")
    return "\n".join(lines)


def send_pipeline_alerts(
    db: Any,
    signals: list[dict[str, Any]],
    explicit_symbols: list[str] | None = None,
) -> None:
    """
    Send signal alerts via Telegram to every subscribed user.

    explicit_symbols (manual run):
        The stocks the user explicitly chose in Run Analysis.
        ALL subscribed users receive alerts for these stocks — watchlist ignored.

    No explicit_symbols (scheduled/automated run):
        Each user only receives alerts for stocks in their personal watchlist.
        Users with no watchlist are skipped.
    """
    if not signals:
        return

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.debug("TELEGRAM_BOT_TOKEN not set — skipping Telegram alerts")
        return

    # Pre-filter signals to the explicit symbol list when provided
    if explicit_symbols:
        explicit_set = set(s.upper() for s in explicit_symbols)
        run_signals = [s for s in signals if s.get("symbol", "") in explicit_set]
    else:
        run_signals = signals

    if not run_signals:
        logger.debug("No signals to send via Telegram")
        return

    # Send to every registered user who enabled Telegram alerts
    try:
        with db.session() as sess:
            from src.database.db_manager import UserRecord
            users = sess.query(UserRecord).filter_by(
                is_active=True, telegram_alerts=True
            ).all()

        for user in users:
            chat = user.telegram_chat_id or ""
            if not chat:
                continue

            if explicit_symbols:
                # Manual run — send all signals from the chosen stocks
                user_signals = run_signals
            else:
                # Scheduled run — personalise to user's watchlist
                watchlist = db.get_watchlist(user.id)
                if not watchlist:
                    logger.debug("User %s has no watchlist — skipping scheduled alert", user.id)
                    continue
                user_signals = [s for s in run_signals if s.get("symbol") in set(watchlist)]
                if not user_signals:
                    logger.debug("No signals matched watchlist for user %s", user.id)
                    continue

            user_text = build_signal_message(user_signals)
            ok = _send_message(bot_token, chat, user_text)
            logger.info(
                "Telegram alert %s for user %s (%d signals)",
                "sent" if ok else "FAILED",
                user.id,
                len(user_signals),
            )
    except Exception as exc:
        logger.warning("Telegram user-alert loop error: %s", exc)


def send_custom_message(text: str) -> bool:
    """
    Send an arbitrary text to the process-level Telegram target.
    Returns True if sent successfully.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        logger.debug("Telegram not configured — skipping custom message")
        return False
    return _send_message(token, chat, text)


# ── Long-polling bot (works on localhost, no public URL needed) ───────────────

def _handle_update(update: dict, db: Any) -> None:
    """
    Process a single Telegram update received via getUpdates polling.
    Handles /start <token> to complete the subscribe deep-link flow.
    """
    message = update.get("message") or update.get("edited_message", {})
    if not message:
        return

    text = (message.get("text") or "").strip()
    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))
    first_name = chat.get("first_name", "there")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    if text.startswith("/start") and chat_id and bot_token:
        parts = text.split(" ", 1)
        link_token = parts[1].strip() if len(parts) > 1 else ""

        if link_token:
            ok = db.link_telegram_by_token(link_token, chat_id)
            reply = (
                f"\u2705 Hi {first_name}! You're now subscribed to MarketMind AI alerts.\n"
                "You'll receive trading signals whenever the pipeline runs."
                if ok else
                "\u26a0\ufe0f This link has already been used or has expired. "
                "Please generate a new subscribe link from the app."
            )
        else:
            reply = (
                f"\U0001f44b Hi {first_name}! I'm the MarketMind AI alerts bot.\n"
                "Open the MarketMind AI dashboard \u2192 Portfolio page \u2192 click "
                "\"Subscribe to Alerts\" to link your account."
            )

        _send_message(bot_token, chat_id, reply)


def start_polling(db: Any) -> "threading.Thread | None":
    """
    Start a daemon thread that long-polls Telegram for updates.
    Works on localhost — no public URL or webhook needed.

    Call once at app startup:
        from src.telegram_utils import start_polling
        start_polling(db)
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.debug("TELEGRAM_BOT_TOKEN not set — polling not started")
        return None

    # Clear any existing webhook so getUpdates works
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getWebhookInfo", timeout=5
        )
        if r.json().get("result", {}).get("url"):
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/deleteWebhook",
                json={"drop_pending_updates": False},
                timeout=5,
            )
            logger.info("Telegram: cleared existing webhook to enable polling")
    except Exception as exc:
        logger.debug("Telegram webhook check failed: %s", exc)

    def _poll_loop() -> None:
        offset = 0
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        logger.info("Telegram polling started")
        while True:
            try:
                resp = requests.get(
                    url,
                    params={"timeout": 30, "offset": offset,
                            "allowed_updates": ["message"]},
                    timeout=40,
                )
                for update in resp.json().get("result", []):
                    try:
                        _handle_update(update, db)
                    except Exception as exc:
                        logger.warning("Telegram update handler error: %s", exc)
                    offset = update["update_id"] + 1
            except requests.exceptions.Timeout:
                pass  # normal long-poll expiry, loop again
            except Exception as exc:
                logger.warning("Telegram poll error: %s — retrying in 5 s", exc)
                time.sleep(5)

    t = threading.Thread(target=_poll_loop, name="telegram-polling", daemon=True)
    t.start()
    return t
