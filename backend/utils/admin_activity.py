"""
utils/admin_activity.py — admin activity log + login lockout (2026-10-15).

1) Activity log
   Every important admin action is written to the MongoDB collection
   "admin_activity": who did it, what, when, and a short detail line.
   Admins can read it in the admin panel (GET /api/admin/activity).

       await log_activity(db, "admin@saividya.ac.in", "upload_confirm", "fees: 12 changes")

   Logging never breaks the real action: if the write fails, we only print it.

2) Login lockout
   After MAX_FAILED wrong passwords for the same email, that email is locked
   for LOCK_MINUTES. Stored in the collection "login_attempts" (one document
   per email). A correct login clears the counter.
"""

from datetime import datetime, timedelta, timezone

ACTIVITY = "admin_activity"
ATTEMPTS = "login_attempts"

MAX_FAILED = 3          # wrong passwords allowed before the lock
LOCK_MINUTES = 15       # how long the account stays locked

# Shown in the admin panel. Anything not listed here shows as the raw action name.
ACTION_LABELS = {
    "login": "Signed in",
    "login_failed": "Wrong password",
    "login_locked": "Account locked (too many wrong passwords)",
    "upload_preview": "Uploaded a file for preview",
    "upload_confirm": "Applied an upload",
    "upload_cancel": "Cancelled an upload",
    "upload_undo": "Undid an upload",
    "template_download": "Downloaded an Excel template",
    "unanswered_resolve": "Marked questions as handled",
    "callback_update": "Updated a callback request",
    "website_refresh": "Fetched updated data from the college website",   # 2026-10-30
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt):
    """Mongo gives back naive datetimes (UTC). Make them comparable with _now()."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ── 1) activity log ────────────────────────────────────────────────────────
async def log_activity(db, admin_email: str, action: str, details: str = "") -> None:
    if db is None:
        return
    try:
        await db[ACTIVITY].insert_one({
            "admin": (admin_email or "").lower(),
            "action": action,
            "details": (details or "")[:300],
            "at": _now(),
        })
    except Exception as e:   # never block the real action because of the log
        print(f"[admin_activity] could not log {action}: {e}")


async def list_activity(db, limit: int = 100, admin: str | None = None, action: str | None = None) -> dict:
    query = {}
    if admin:
        query["admin"] = admin.lower()
    if action:
        query["action"] = action
    docs = await db[ACTIVITY].find(query).sort("at", -1).to_list(length=limit)
    items = []
    for d in docs:
        at = _aware(d.get("at"))
        items.append({
            "id": str(d["_id"]),
            "admin": d.get("admin", ""),
            "action": d.get("action", ""),
            "label": ACTION_LABELS.get(d.get("action", ""), d.get("action", "")),
            "details": d.get("details", ""),
            "at": at.isoformat() if at else None,
        })
    return {"items": items, "actions": ACTION_LABELS}


# ── 2) login lockout ───────────────────────────────────────────────────────
async def locked_minutes_left(db, email: str) -> int:
    """0 if the email may try to log in, otherwise minutes until the lock ends."""
    doc = await db[ATTEMPTS].find_one({"email": email})
    until = _aware(doc.get("locked_until")) if doc else None
    if until and until > _now():
        return max(1, int((until - _now()).total_seconds() // 60) + 1)
    return 0


async def record_failed_login(db, email: str) -> int:
    """Counts one wrong password. Returns how many tries are left (0 = now locked)."""
    doc = await db[ATTEMPTS].find_one({"email": email})
    count = (doc.get("failed", 0) if doc else 0)
    # an expired lock starts a fresh count
    if doc and _aware(doc.get("locked_until")) and _aware(doc["locked_until"]) <= _now():
        count = 0
    count += 1
    update = {"email": email, "failed": count, "last_failed_at": _now(), "locked_until": None}
    if count >= MAX_FAILED:
        update["locked_until"] = _now() + timedelta(minutes=LOCK_MINUTES)
    await db[ATTEMPTS].update_one({"email": email}, {"$set": update}, upsert=True)
    return max(0, MAX_FAILED - count)


async def clear_failed_logins(db, email: str) -> None:
    await db[ATTEMPTS].delete_one({"email": email})
