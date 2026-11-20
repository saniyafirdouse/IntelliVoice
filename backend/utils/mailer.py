"""
utils/mailer.py — "Email me" for signed-in students (2026-11-20).

Sends from a Gmail account using a Google *App Password* (not the real password).
Put these 2 lines in .env (San edits .env himself; the values are never printed):
    SMTP_USER=the.gmail.address@gmail.com
    SMTP_APP_PASSWORD=sixteenletterspw          (no spaces)
Optional:
    MAIL_FROM_NAME=Eva – SVIT Admissions

If the 2 lines are missing, email_enabled() is False and the "Email me" buttons stay hidden.
Each student can send at most MAX_PER_HOUR emails per hour (no misuse).
"""

import asyncio
import os
import smtplib
import ssl
import threading
import time
from email.message import EmailMessage
from email.utils import formataddr

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465             # SSL; if this network blocks it, port 587 (STARTTLS) is tried next
MAX_PER_HOUR = 5

_sent: dict = {}            # email -> [timestamps]
_lock = threading.Lock()


def _settings():
    user = (os.getenv("SMTP_USER") or "").strip()
    password = (os.getenv("SMTP_APP_PASSWORD") or "").replace(" ", "").strip()
    name = (os.getenv("MAIL_FROM_NAME") or "Eva – SVIT Admissions").strip()
    return user, password, name


def email_enabled() -> bool:
    user, password, _ = _settings()
    return bool(user and password)


def allowed(to: str) -> bool:
    """True if this student may send another email now (and counts it)."""
    now = time.time()
    with _lock:
        recent = [t for t in _sent.get(to, []) if now - t < 3600]
        if len(recent) >= MAX_PER_HOUR:
            _sent[to] = recent
            return False
        recent.append(now)
        _sent[to] = recent
        return True


def _send(to: str, subject: str, text: str, html: str, attachments: list) -> None:
    user, password, name = _settings()
    msg = EmailMessage()
    msg["From"] = formataddr((name, user))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    for filename, data, mime in attachments or []:
        main, sub = mime.split("/", 1)
        msg.add_attachment(data, maintype=main, subtype=sub, filename=filename)
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ssl.create_default_context(), timeout=20) as server:
            server.login(user, password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        raise
    except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, OSError) as first:
        # 2026-11-20: some Wi-Fi networks / antivirus programs block port 465 -> try 587 with STARTTLS
        print(f"⚠️  Email: port 465 failed ({type(first).__name__}: {first}); trying port 587")
        with smtplib.SMTP(SMTP_HOST, 587, timeout=20) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(user, password)
            server.send_message(msg)


async def send_email(to: str, subject: str, text: str, html: str, attachments: list | None = None) -> None:
    """Raises RuntimeError with a friendly message if sending fails."""
    if not email_enabled():
        raise RuntimeError("Email is not set up yet.")
    try:
        await asyncio.to_thread(_send, to, subject, text, html, attachments or [])
    except smtplib.SMTPAuthenticationError:
        print("⚠️  Email: Gmail refused the login (check SMTP_USER / SMTP_APP_PASSWORD in .env)")
        raise RuntimeError("Email couldn't be sent right now. Please try again later.")
    except Exception as e:
        print(f"⚠️  Email not sent: {type(e).__name__}: {e}")     # (never contains the password)
        raise RuntimeError("Email couldn't be sent right now. Please try again later.")
