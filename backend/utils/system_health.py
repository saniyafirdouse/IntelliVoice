"""
utils/system_health.py — live problems list for the admin "System health" page (2026-11-01).

Kept in the server's memory (the last 50 problems), so it shows what went wrong
since the backend started: a Sarvam key out of credits, a failed reply, and so on.
Nothing here can ever break a reply: every function swallows its own errors.
"""

import time
from collections import deque
from datetime import datetime, timezone

STARTED_AT = time.time()
_problems: deque = deque(maxlen=50)


def record_problem(source: str, detail: str) -> None:
    """source: "Sarvam", "Groq", "Pipeline"... detail: one short line (never a key or password)."""
    try:
        _problems.appendleft({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                              "source": source, "detail": str(detail)[:300]})
    except Exception:
        pass


def recent_problems(limit: int = 10) -> list:
    return list(_problems)[:limit]


def uptime_seconds() -> int:
    return int(time.time() - STARTED_AT)


# ── Phone visitors (2026-11-01, expo) ─────────────────────────────────────
# "Phone visitors" = questions that came through the Cloudflare tunnel.
# The admin can pause them with one click (System Health page); the stall laptop
# is never affected. Kept in memory: a backend restart turns phone access back on.
PHONE_HOURLY_CAP = 200          # all phone visitors together, spoken-reply questions per hour
_phone_paused = False
_phone_hits: deque = deque(maxlen=5000)


def phone_paused() -> bool:
    return _phone_paused


def set_phone_paused(paused: bool) -> None:
    global _phone_paused
    _phone_paused = bool(paused)


def phone_questions_last_hour() -> int:
    cutoff = time.time() - 3600
    while _phone_hits and _phone_hits[0] < cutoff:
        _phone_hits.popleft()
    return len(_phone_hits)


def phone_cap_reached() -> bool:
    return phone_questions_last_hour() >= PHONE_HOURLY_CAP


def count_phone_question() -> None:
    _phone_hits.append(time.time())
