"""
email_utils.py
==============
Standalone SMTP helpers used outside the full pipeline — e.g. for sending
a welcome email immediately after a new subscription, or a "here is your
unsubscribe link" help email.

Credentials are read from SMTP_USER / SMTP_PASSWORD env vars (same as the
full EmailAlertAgent).
"""
import logging
import os
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

logger = logging.getLogger("MarketMindAI.EmailUtils")

_UNSUBSCRIBE_FOOTER = """
<div style="margin-top:28px;padding-top:16px;border-top:1px solid #e0e0e0;
            text-align:center;font-size:11px;color:#aaa">
  You're receiving this because you subscribed to MarketMind AI alerts.<br>
  To stop receiving emails:&nbsp;
  <a href="{unsubscribe_url}" style="color:#e74c3c;font-weight:bold">
    Unsubscribe in one click
  </a>
  &nbsp;|&nbsp;
  <a href="{app_url}/subscribe" style="color:#3498db">Manage Subscription</a>
</div>
"""


def _smtp_send(to: List[str], subject: str, html: str) -> None:
    """Low-level SMTP send using env-var credentials."""
    username = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))

    if not username or not password:
        logger.warning("SMTP_USER / SMTP_PASSWORD not set — skipping email to %s", to)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = username
    msg["To"] = ", ".join(to)
    msg.attach(MIMEText(html, "html", "utf-8"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls(context=ctx)
        server.ehlo()
        server.login(username, password)
        server.sendmail(username, to, msg.as_string())
    logger.info("Email sent: '%s' → %s", subject, to)


# ── Public helpers ─────────────────────────────────────────────────────────────

def send_welcome_email(
    email: str,
    stocks: List[str],
    unsubscribe_url: str,
    app_url: str,
) -> None:
    """
    Send a "You are subscribed" confirmation email immediately after sign-up.
    """
    now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
    stocks_html = "".join(
        f'<span style="display:inline-block;background:#e8f4fd;color:#1a6fa6;'
        f'border-radius:4px;padding:3px 10px;margin:3px;font-size:13px;'
        f'font-weight:bold">{s}</span>'
        for s in stocks
    )

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;background:#f4f6f8;padding:24px;color:#222">
  <div style="max-width:600px;margin:auto">

    <!-- Header -->
    <div style="background:#1a1a2e;color:#fff;padding:24px;border-radius:10px 10px 0 0;text-align:center">
      <div style="font-size:40px">📊</div>
      <h1 style="margin:8px 0 4px;font-size:24px">Welcome to MarketMind AI!</h1>
      <p style="margin:0;color:#a0a0c0;font-size:14px">Your subscription is confirmed — {now_str}</p>
    </div>

    <!-- Body -->
    <div style="background:#fff;padding:28px;border-radius:0 0 10px 10px;
                box-shadow:0 2px 10px rgba(0,0,0,.08)">

      <p style="font-size:16px;margin:0 0 16px">
        🎉 <strong>You're all set!</strong> You'll receive AI-powered market digests
        for your selected stocks twice every trading day:
      </p>

      <div style="background:#f0faf4;border-radius:8px;padding:16px;margin-bottom:20px">
        <table style="width:100%;font-size:14px">
          <tr>
            <td style="padding:6px 0">
              <span style="font-size:20px">🌅</span>
              <strong>&nbsp;Pre-Market</strong>
            </td>
            <td style="color:#555">8:45 AM IST — before NSE opens (9:15 AM)</td>
          </tr>
          <tr>
            <td style="padding:6px 0">
              <span style="font-size:20px">🌇</span>
              <strong>&nbsp;Post-Market</strong>
            </td>
            <td style="color:#555">4:15 PM IST — after NSE closes (3:30 PM)</td>
          </tr>
        </table>
      </div>

      <p style="font-size:14px;color:#555;margin:0 0 8px">
        <strong>Stocks you're tracking:</strong>
      </p>
      <div style="margin-bottom:20px">{stocks_html}</div>

      <p style="font-size:14px;color:#555;margin:0 0 20px">
        Each digest includes:
        <strong>BUY / HOLD / SELL signals</strong>,
        AI-generated analysis (powered by Google Gemini),
        news sentiment, and embedded price charts.
      </p>

      <div style="text-align:center;margin:24px 0">
        <a href="{app_url}"
           style="background:#3498db;color:#fff;padding:12px 28px;border-radius:6px;
                  text-decoration:none;font-weight:bold;font-size:15px">
          View Live Dashboard →
        </a>
      </div>

      {_UNSUBSCRIBE_FOOTER.format(unsubscribe_url=unsubscribe_url, app_url=app_url)}
    </div>

    <p style="text-align:center;font-size:11px;color:#bbb;margin-top:12px">
      MarketMind AI · Not financial advice · Always do your own research
    </p>
  </div>
</body>
</html>"""

    subject = "🎉 You're subscribed to MarketMind AI Daily Alerts"
    _smtp_send([email], subject, html)


def send_update_email(
    email: str,
    stocks: List[str],
    unsubscribe_url: str,
    app_url: str,
) -> None:
    """
    Send a "Your stock watchlist has been updated" confirmation email
    when an existing subscriber re-subscribes with a new stock list.
    """
    now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
    stocks_html = "".join(
        f'<span style="display:inline-block;background:#e8f4fd;color:#1a6fa6;'
        f'border-radius:4px;padding:3px 10px;margin:3px;font-size:13px;'
        f'font-weight:bold">{s}</span>'
        for s in stocks
    )

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;background:#f4f6f8;padding:24px;color:#222">
  <div style="max-width:600px;margin:auto">

    <!-- Header -->
    <div style="background:#1a1a2e;color:#fff;padding:24px;border-radius:10px 10px 0 0;text-align:center">
      <div style="font-size:40px">🔄</div>
      <h1 style="margin:8px 0 4px;font-size:24px">Watchlist Updated</h1>
      <p style="margin:0;color:#a0a0c0;font-size:14px">MarketMind AI · {now_str}</p>
    </div>

    <!-- Body -->
    <div style="background:#fff;padding:28px;border-radius:0 0 10px 10px;
                box-shadow:0 2px 10px rgba(0,0,0,.08)">

      <p style="font-size:16px;margin:0 0 16px">
        ✅ Your stock watchlist for <strong>{email}</strong> has been updated.
        You'll now receive alerts for:
      </p>

      <div style="margin-bottom:20px">{stocks_html}</div>

      <p style="font-size:14px;color:#555;margin:0 0 20px">
        Your next digest will arrive at the next scheduled time:
      </p>

      <div style="background:#f0faf4;border-radius:8px;padding:16px;margin-bottom:20px">
        <table style="width:100%;font-size:14px">
          <tr>
            <td style="padding:6px 0">
              <span style="font-size:20px">🌅</span>
              <strong>&nbsp;Pre-Market</strong>
            </td>
            <td style="color:#555">8:45 AM IST — before NSE opens</td>
          </tr>
          <tr>
            <td style="padding:6px 0">
              <span style="font-size:20px">🌇</span>
              <strong>&nbsp;Post-Market</strong>
            </td>
            <td style="color:#555">4:15 PM IST — after NSE closes</td>
          </tr>
        </table>
      </div>

      <div style="text-align:center;margin:24px 0">
        <a href="{app_url}/subscribe"
           style="background:#3498db;color:#fff;padding:12px 28px;border-radius:6px;
                  text-decoration:none;font-weight:bold;font-size:15px">
          Update Watchlist Again →
        </a>
      </div>

      {_UNSUBSCRIBE_FOOTER.format(unsubscribe_url=unsubscribe_url, app_url=app_url)}
    </div>

    <p style="text-align:center;font-size:11px;color:#bbb;margin-top:12px">
      MarketMind AI · Not financial advice · Always do your own research
    </p>
  </div>
</body>
</html>"""

    subject = "🔄 MarketMind AI — Your stock watchlist has been updated"
    _smtp_send([email], subject, html)


def send_unsubscribe_lookup_email(
    email: str,
    unsubscribe_url: str,
    app_url: str,
) -> None:
    """
    Send the user their unsubscribe link when they request it via the
    "Manage Subscription" form on the subscribe page.
    """
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;background:#f4f6f8;padding:24px;color:#222">
  <div style="max-width:520px;margin:auto">
    <div style="background:#1a1a2e;color:#fff;padding:20px;border-radius:10px 10px 0 0;text-align:center">
      <h2 style="margin:0">📊 MarketMind AI</h2>
      <p style="margin:4px 0;color:#a0a0c0;font-size:13px">Subscription Management</p>
    </div>
    <div style="background:#fff;padding:24px;border-radius:0 0 10px 10px;
                box-shadow:0 2px 10px rgba(0,0,0,.08)">
      <p style="font-size:15px;margin:0 0 16px">
        You requested your unsubscribe link for <strong>{email}</strong>.
      </p>
      <div style="text-align:center;margin:24px 0">
        <a href="{unsubscribe_url}"
           style="background:#e74c3c;color:#fff;padding:12px 28px;border-radius:6px;
                  text-decoration:none;font-weight:bold;font-size:15px">
          Unsubscribe Now
        </a>
      </div>
      <p style="font-size:13px;color:#888;text-align:center">
        Or copy this link:<br>
        <code style="font-size:11px;word-break:break-all;color:#555">{unsubscribe_url}</code>
      </p>
      <p style="font-size:13px;color:#aaa;text-align:center;margin-top:16px">
        If you didn't request this, you can safely ignore this email.
      </p>
    </div>
  </div>
</body>
</html>"""

    subject = "MarketMind AI — Your unsubscribe link"
    _smtp_send([email], subject, html)
