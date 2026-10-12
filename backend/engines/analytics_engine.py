"""
engines/analytics_engine.py — Engine 6: Analytics

Two jobs:
  1. log_query()        Called once per question from routes/voice.py.
                        Saves what was asked, the language, the intent and
                        whether the assistant could answer it (collection "query_logs").
  2. Reports for the admin panel:
       get_unanswered() "Questions we couldn't answer", grouped so the admin
                        sees what data is missing ("23 parents asked about bus routes").
       get_dashboard()  Most-asked topics, language split, busiest hours, etc.

Logging must NEVER break a parent's answer, so log_query() swallows its own
errors and only prints them.

How a question is classed (field "status"):
  answered      normal answer from MongoDB data (or greetings, which need no data)
  no_data       we understood the question, but MongoDB has no matching record
                -> the admin should ADD this data
  out_of_scope  the question was outside what IntelliVoice understands
  error         a technical problem (e.g. database error)
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bson import ObjectId

LOGS = "query_logs"
IST = ZoneInfo("Asia/Kolkata")
MAX_DOCS = 50000   # safety cap for one report


def classify_status(intelligence_result: dict, knowledge_result: dict | None) -> str:
    if (intelligence_result.get("confidence_zone") == "out_of_scope"
            or intelligence_result.get("intent") == "fallback"):
        return "out_of_scope"
    if knowledge_result and not knowledge_result.get("found"):
        reason = knowledge_result.get("reason")
        if reason in ("no_matching_document",):
            return "no_data"
        if reason in ("database_error", "database_not_connected"):
            return "error"
    return "answered"


async def log_query(db, *, session_id: str, text: str, language: dict | None,
                    intelligence_result: dict, knowledge_result: dict | None = None,
                    input_type: str = "text", response_time_ms: int | None = None) -> None:
    """Save one question. Safe to call even if something is missing."""
    try:
        if db is None:
            return
        language = language or {}
        kr = intelligence_result.get("knowledge_request") or {}
        await db[LOGS].insert_one({
            "timestamp": datetime.now(timezone.utc),
            "session_id": session_id,
            "text": (text or "")[:500],
            "input_type": input_type,
            "language": language.get("primary"),
            "is_code_switched": bool(language.get("is_code_switched")),
            "intent": intelligence_result.get("intent"),
            "category": intelligence_result.get("category"),
            "confidence": intelligence_result.get("confidence"),
            "confidence_zone": intelligence_result.get("confidence_zone"),
            "emotion": intelligence_result.get("emotion"),
            "entities": intelligence_result.get("entities") or {},
            "collection": kr.get("collection"),
            "response_mode": intelligence_result.get("response_mode"),
            "needs_escalation": bool(intelligence_result.get("needs_escalation")),
            "status": classify_status(intelligence_result, knowledge_result),
            "response_time_ms": response_time_ms,
            "resolved": False,
        })
    except Exception as e:  # never let analytics break the voice pipeline
        print(f"⚠️ Analytics log failed: {e}")


async def _recent_logs(db, days: int, extra: dict | None = None) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = {"timestamp": {"$gte": since}, **(extra or {})}
    cursor = db[LOGS].find(query).sort("timestamp", -1).limit(MAX_DOCS)
    return await cursor.to_list(length=MAX_DOCS)


def _ist(ts: datetime) -> datetime:
    if ts.tzinfo is None:  # MongoDB returns naive UTC datetimes
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(IST)


def _pct(part: int, total: int) -> float:
    return round(100 * part / total, 1) if total else 0.0


# ── "Questions we couldn't answer" ─────────────────────────────────────────
async def get_unanswered(db, days: int = 7, include_resolved: bool = False) -> dict:
    extra = {"status": {"$in": ["no_data", "out_of_scope"]}}
    if not include_resolved:
        extra["resolved"] = {"$ne": True}
    logs = await _recent_logs(db, days, extra)

    # Missing data: group by intent (+ the entities asked for)
    missing = defaultdict(lambda: {"count": 0, "examples": [], "entities_asked": Counter(), "ids": []})
    for log in (l for l in logs if l["status"] == "no_data"):
        g = missing[(log.get("intent"), log.get("collection"))]
        g["count"] += 1
        g["ids"].append(str(log["_id"]))
        for k, v in (log.get("entities") or {}).items():
            g["entities_asked"][f"{k}: {v}"] += 1
        if len(g["examples"]) < 5:
            g["examples"].append({"text": log["text"], "language": log.get("language"),
                                  "asked_at": _ist(log["timestamp"]).isoformat()})

    missing_data = sorted(
        ({"intent": intent, "collection": coll, "count": g["count"],
          "entities_asked": [{"value": v, "count": n} for v, n in g["entities_asked"].most_common(5)],
          "examples": g["examples"], "log_ids": g["ids"]}
         for (intent, coll), g in missing.items()),
        key=lambda x: -x["count"])

    # Out of scope: group identical questions (case/spacing ignored)
    oos = defaultdict(lambda: {"count": 0, "text": "", "ids": [], "language": None, "last_asked": None})
    for log in (l for l in logs if l["status"] == "out_of_scope"):
        key = " ".join((log.get("text") or "").lower().split())
        g = oos[key]
        g["count"] += 1
        g["ids"].append(str(log["_id"]))
        if not g["text"]:  # logs are newest first
            g["text"], g["language"] = log["text"], log.get("language")
            g["last_asked"] = _ist(log["timestamp"]).isoformat()

    out_of_scope = sorted(
        ({"text": g["text"], "count": g["count"], "language": g["language"],
          "last_asked": g["last_asked"], "log_ids": g["ids"]} for g in oos.values()),
        key=lambda x: (-x["count"], x["text"]))[:100]

    return {
        "days": days,
        "total_unanswered": len(logs),
        "missing_data": missing_data,
        "out_of_scope": out_of_scope,
    }


async def mark_resolved(db, log_ids: list[str]) -> int:
    ids = []
    for i in log_ids:
        try:
            ids.append(ObjectId(i))
        except Exception:
            continue
    if not ids:
        return 0
    result = await db[LOGS].update_many({"_id": {"$in": ids}}, {"$set": {"resolved": True}})
    return result.modified_count


# ── Dashboard ──────────────────────────────────────────────────────────────
async def get_dashboard(db, days: int = 7) -> dict:
    logs = await _recent_logs(db, days)
    total = len(logs)

    status = Counter(l.get("status") for l in logs)
    languages = Counter(l.get("language") or "unknown" for l in logs)
    emotions = Counter(l.get("emotion") or "unknown" for l in logs)
    inputs = Counter(l.get("input_type") or "text" for l in logs)
    intents = Counter(l.get("intent") for l in logs if l.get("status") != "out_of_scope" and l.get("intent"))
    categories = Counter(l.get("category") for l in logs if l.get("status") != "out_of_scope" and l.get("category"))
    hours = Counter(_ist(l["timestamp"]).hour for l in logs)

    today = datetime.now(IST).date()
    per_day = Counter(_ist(l["timestamp"]).date() for l in logs)
    daily = [{"date": (today - timedelta(days=i)).isoformat(),
              "count": per_day.get(today - timedelta(days=i), 0)}
             for i in range(days - 1, -1, -1)]

    times = [l["response_time_ms"] for l in logs if isinstance(l.get("response_time_ms"), (int, float))]
    lang_names = {"en": "English", "hi": "Hindi", "kn": "Kannada"}

    return {
        "days": days,
        "total_queries": total,
        "unique_sessions": len({l.get("session_id") for l in logs}),
        "answered_rate": _pct(status.get("answered", 0), total),
        "status": {s: status.get(s, 0) for s in ("answered", "no_data", "out_of_scope", "error")},
        "escalations": sum(1 for l in logs if l.get("needs_escalation")),
        "top_intents": [{"intent": i, "count": n} for i, n in intents.most_common(10)],
        "top_categories": [{"category": c, "count": n} for c, n in categories.most_common(8)],
        "languages": [{"language": lang_names.get(k, k), "code": k, "count": n, "percent": _pct(n, total)}
                      for k, n in languages.most_common()],
        "code_switched_percent": _pct(sum(1 for l in logs if l.get("is_code_switched")), total),
        "emotions": [{"emotion": e, "count": n} for e, n in emotions.most_common()],
        "input_types": dict(inputs),
        "busiest_hours": [{"hour": h, "label": f"{h:02d}:00", "count": hours.get(h, 0)} for h in range(24)],
        "daily_queries": daily,
        "avg_response_time_ms": round(sum(times) / len(times)) if times else None,
    }
