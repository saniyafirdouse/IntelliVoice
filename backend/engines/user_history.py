"""
Memory across visits (2026-10-13) — logged-in users only.

Bhuvana's memory_engine remembers a conversation while it lasts (one
session). This keeps a short history per logged-in user in MongoDB
(collection "user_history"), so a returning student can be greeted with
"Last time you asked about CSE fees — any follow-up questions?".

Privacy:
  * only for users who are logged in (their login email is the key)
  * only the last MAX_TURNS questions are kept
  * the user can delete everything (DELETE /api/me/history)

2026-11-20: whole conversations ("Your chats", like ChatGPT).
  Collection "conversations": one document per chat (= one chat session_id) with
  every question AND Eva's answer, typed or spoken (voice chat included).
  The signed-in student can list, open and continue, rename, search and delete
  their chats. Limits: MAX_CONVERSATIONS chats per user, MAX_MESSAGES per chat.
"""

import re

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from database.connection import get_database

COLLECTION = "user_history"
CONVERSATIONS = "conversations"     # 2026-11-20
SAVED = "saved_answers"             # 2026-11-20: ⭐ answers the student saved
CHECKLIST = "checklist_progress"    # 2026-11-20: ticked documents / steps
PROFILES = "user_profiles"          # 2026-11-20: exam, rank, category, preferred branches
MAX_SAVED = 200
MAX_CONVERSATIONS = 100
MAX_MESSAGES = 200
MAX_TEXT = 4000
MAX_TURNS = 20
SKIP_INTENTS = {"greet", "fallback", None}

INTENT_LABELS = {
    "ask_fees_branch": "fees", "ask_cutoff": "cutoffs", "ask_rank_prediction": "which branch you can get with your rank",
    "ask_placement_by_branch": "placements", "ask_top_recruiters": "recruiters", "ask_hostel_facilities": "the hostel",
    "ask_transport_routes": "college buses", "ask_scholarship_available": "scholarships",
    "ask_scholarship_eligibility": "scholarship eligibility", "ask_admission_process": "the admission process",
    "ask_required_documents": "admission documents", "ask_courses_offered": "courses and seats",
    "ask_branch_difference": "comparing branches", "ask_branch_recommendation": "choosing a branch",
    "ask_about_college": "the college", "ask_safety": "campus safety", "ask_campus_visit": "visiting the campus",
    "ask_fee_payment": "paying fees", "ask_lateral_pg_admission": "lateral entry / MBA admission",
    "ask_higher_studies": "higher studies", "ask_sports": "sports", "ask_contact_admission_office": "contacting the office",
}
BRANCH_LABELS = {"CSE-AIML": "AIML", "CSE-DS": "Data Science", "CSE-CyberSecurity": "Cyber Security",
                 "CS-BusinessSystems": "Business Systems"}


def topic_label(intent: str | None, entities: dict | None = None) -> str:
    label = INTENT_LABELS.get(intent) or (intent or "").replace("ask_", "").replace("_", " ").strip() or "admissions"
    branch = (entities or {}).get("branch")
    if branch and intent in {"ask_fees_branch", "ask_cutoff", "ask_placement_by_branch", "ask_seat_availability"}:
        label = f"{BRANCH_LABELS.get(branch, branch)} {label}"
    return label


async def record_turn(email: str, question: str, intent: str | None, entities: dict | None,
                      language: str | None) -> None:
    """Remember one answered question for this user (called in the background)."""
    if not email or intent in SKIP_INTENTS:
        return
    db = get_database()
    if db is None:
        return
    turn = {
        "question": (question or "")[:300],
        "intent": intent,
        "topic": topic_label(intent, entities),
        "entities": {k: v for k, v in (entities or {}).items() if k != "topic"},
        "language": language,
        "at": datetime.now(timezone.utc),
    }
    try:
        await db[COLLECTION].update_one(
            {"email": email},
            {"$push": {"turns": {"$each": [turn], "$slice": -MAX_TURNS}},
             "$set": {"updated_at": turn["at"]}},
            upsert=True,
        )
    except Exception as e:
        print(f"⚠️  Could not save user history: {e}")


async def get_summary(email: str) -> dict:
    db = get_database()
    doc = await db[COLLECTION].find_one({"email": email}) if db is not None else None
    turns = (doc or {}).get("turns") or []
    if not turns:
        return {"has_history": False, "welcome_message": None, "last_topic": None, "recent_topics": []}
    last = turns[-1]
    recent = []
    for t in reversed(turns):
        if t.get("topic") and t["topic"] not in recent:
            recent.append(t["topic"])
        if len(recent) == 3:
            break
    return {
        "has_history": True,
        "last_topic": last.get("topic"),
        "last_question": last.get("question"),
        "last_asked_at": last["at"].isoformat() if last.get("at") else None,
        "recent_topics": recent,
        "welcome_message": f"Welcome back! Last time you asked about {last.get('topic')}. "
                           "Do you have any follow-up questions?",
    }


async def forget(email: str) -> int:
    """Forget everything: the topics AND all saved chats (2026-11-20)."""
    db = get_database()
    if db is None:
        return 0
    result = await db[COLLECTION].delete_many({"email": email})
    chats = await db[CONVERSATIONS].delete_many({"email": email})
    return result.deleted_count + chats.deleted_count
    # (saved answers and the checklist are kept: the student saved them on purpose)


# ── whole conversations (2026-11-20) ───────────────────────────────────────
def _utc(at) -> str | None:
    if not at:
        return None
    if at.tzinfo is None:                       # MongoDB gives UTC back without a time zone
        at = at.replace(tzinfo=timezone.utc)
    return at.isoformat()


def _title(question: str) -> str:
    text = " ".join((question or "").split())
    if not text:
        return "Voice chat"
    return text if len(text) <= 60 else text[:57].rstrip() + "…"


def _oid(conversation_id: str):
    try:
        return ObjectId(conversation_id)
    except (InvalidId, TypeError):
        return None


async def record_message(email: str, session_id: str, question: str, reply: dict,
                         mode: str = "text", language: str | None = None, intent: str | None = None) -> None:
    """Add one question + Eva's reply to this user's chat for this session (called in the background).

    reply: the same reply the page got (text, language, PDF buttons, help card...), so an
    old chat looks the same when it is opened again (only the voice is not kept).
    """
    if not email or not session_id:
        return
    db = get_database()
    if db is None:
        return
    now = datetime.now(timezone.utc)
    user_msg = {"role": "user", "text": (question or "")[:MAX_TEXT], "mode": mode, "language": language, "at": now}
    eva_msg = {"role": "eva", "text": ((reply or {}).get("text") or "")[:MAX_TEXT], "at": now,
               "language": (reply or {}).get("language"), "intent": intent,
               "extra": (reply or {}).get("extra") or {}}
    try:
        result = await db[CONVERSATIONS].update_one(
            {"email": email, "session_id": session_id},
            {"$push": {"messages": {"$each": [user_msg, eva_msg], "$slice": -MAX_MESSAGES}},
             "$set": {"updated_at": now},
             "$inc": {"count": 1},
             "$setOnInsert": {"title": _title(question), "created_at": now}},
            upsert=True,
        )
        if result.upserted_id is not None:        # a new chat: keep only the newest MAX_CONVERSATIONS
            old = await db[CONVERSATIONS].find({"email": email}, {"_id": 1}) \
                .sort([("updated_at", -1), ("_id", -1)]).skip(MAX_CONVERSATIONS).to_list(length=1000)
            if old:
                await db[CONVERSATIONS].delete_many({"_id": {"$in": [d["_id"] for d in old]}})
    except Exception as e:
        print(f"⚠️  Could not save the chat: {e}")


async def list_conversations(email: str, search: str | None = None, limit: int = MAX_CONVERSATIONS) -> list:
    db = get_database()
    if db is None:
        return []
    query: dict = {"email": email}
    search = (search or "").strip()
    if search:
        pattern = re.compile(re.escape(search[:100]), re.IGNORECASE)
        query["$or"] = [{"title": pattern}, {"messages.text": pattern}]
    docs = await db[CONVERSATIONS].find(query, {"messages": {"$slice": -1}, "title": 1, "count": 1,
                                                "created_at": 1, "updated_at": 1, "session_id": 1}) \
        .sort([("updated_at", -1), ("_id", -1)]).to_list(length=limit)
    out = []
    for d in docs:
        last = (d.get("messages") or [{}])[-1]
        out.append({
            "id": str(d["_id"]),
            "session_id": d.get("session_id"),
            "title": d.get("title") or "Chat",
            "questions": d.get("count") or 0,
            "preview": (last.get("text") or "")[:120],
            "created_at": _utc(d.get("created_at")),
            "updated_at": _utc(d.get("updated_at")),
        })
    return out


async def get_conversation(email: str, conversation_id: str) -> dict | None:
    db = get_database()
    oid = _oid(conversation_id)
    if db is None or oid is None:
        return None
    d = await db[CONVERSATIONS].find_one({"_id": oid, "email": email})    # only the owner's own chat
    if not d:
        return None
    return {
        "id": str(d["_id"]),
        "session_id": d.get("session_id"),
        "title": d.get("title") or "Chat",
        "created_at": _utc(d.get("created_at")),
        "updated_at": _utc(d.get("updated_at")),
        "messages": [{**{k: v for k, v in m.items() if k != "at"}, "at": _utc(m.get("at"))}
                     for m in d.get("messages") or []],
    }


async def rename_conversation(email: str, conversation_id: str, title: str) -> bool:
    db = get_database()
    oid = _oid(conversation_id)
    title = " ".join((title or "").split())[:80]
    if db is None or oid is None or not title:
        return False
    result = await db[CONVERSATIONS].update_one({"_id": oid, "email": email}, {"$set": {"title": title}})
    return result.matched_count == 1


async def delete_conversation(email: str, conversation_id: str) -> bool:
    db = get_database()
    oid = _oid(conversation_id)
    if db is None or oid is None:
        return False
    result = await db[CONVERSATIONS].delete_one({"_id": oid, "email": email})
    return result.deleted_count == 1


# ── ⭐ saved answers (2026-11-20) ───────────────────────────────────────────
def _saved_view(d: dict) -> dict:
    return {"id": str(d["_id"]), "question": d.get("question") or "", "answer": d.get("answer") or "",
            "language": d.get("language"), "saved_at": _utc(d.get("saved_at"))}


async def save_answer(email: str, question: str, answer: str, language: str | None = None) -> dict | None:
    db = get_database()
    answer = (answer or "").strip()[:MAX_TEXT]
    if db is None or not email or not answer:
        return None
    existing = await db[SAVED].find_one({"email": email, "answer": answer})
    if existing:                                    # saved twice: keep one
        return _saved_view(existing)
    doc = {"email": email, "question": (question or "").strip()[:500], "answer": answer,
           "language": language, "saved_at": datetime.now(timezone.utc)}
    result = await db[SAVED].insert_one(doc)
    doc["_id"] = result.inserted_id
    old = await db[SAVED].find({"email": email}, {"_id": 1}).sort([("saved_at", -1), ("_id", -1)]) \
        .skip(MAX_SAVED).to_list(length=1000)
    if old:
        await db[SAVED].delete_many({"_id": {"$in": [d["_id"] for d in old]}})
    return _saved_view(doc)


async def list_saved(email: str) -> list:
    db = get_database()
    if db is None:
        return []
    docs = await db[SAVED].find({"email": email}).sort([("saved_at", -1), ("_id", -1)]).to_list(length=MAX_SAVED)
    return [_saved_view(d) for d in docs]


async def delete_saved(email: str, saved_id: str) -> bool:
    db = get_database()
    oid = _oid(saved_id)
    if db is None or oid is None:
        return False
    result = await db[SAVED].delete_one({"_id": oid, "email": email})
    return result.deleted_count == 1


# ── my admission checklist with tick-boxes (2026-11-20) ────────────────────
async def get_checklist_progress(email: str) -> dict:
    db = get_database()
    doc = await db[CHECKLIST].find_one({"email": email}) if db is not None else None
    return {"admission_type": (doc or {}).get("admission_type"), "category": (doc or {}).get("category"),
            "done": (doc or {}).get("done") or []}


async def save_checklist_progress(email: str, admission_type: str, category: str, done: list) -> None:
    db = get_database()
    if db is None:
        return
    await db[CHECKLIST].update_one(
        {"email": email},
        {"$set": {"admission_type": admission_type, "category": category,
                  "done": [str(x)[:200] for x in done][:100], "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


# ── my profile (2026-11-20) ─────────────────────────────────────────────────
PROFILE_EXAMS = ("KCET", "COMEDK", "Management", "Lateral", "MBA")
PROFILE_CATEGORIES = ("General", "SC", "ST", "OBC")
PROFILE_BRANCHES = ("CSE", "CSE-AIML", "CSE-DS", "CSE-CyberSecurity", "CS-BusinessSystems", "ECE", "Civil", "Mechanical")
RANK_EXAMS = {"KCET", "COMEDK"}       # the rank predictor has cutoffs for these two


async def get_profile(email: str) -> dict:
    db = get_database()
    doc = await db[PROFILES].find_one({"email": email}) if db is not None else None
    doc = doc or {}
    return {"exam": doc.get("exam"), "rank": doc.get("rank"), "category": doc.get("category"),
            "branches": doc.get("branches") or [], "updated_at": _utc(doc.get("updated_at"))}


async def save_profile(email: str, exam: str | None, rank: int | None, category: str | None, branches: list) -> dict:
    db = get_database()
    profile = {
        "exam": exam if exam in PROFILE_EXAMS else None,
        "rank": rank if isinstance(rank, int) and 1 <= rank <= 500000 else None,
        "category": category if category in PROFILE_CATEGORIES else None,
        "branches": [b for b in dict.fromkeys(branches or []) if b in PROFILE_BRANCHES],
    }
    if db is not None:
        await db[PROFILES].update_one({"email": email},
                                      {"$set": {**profile, "updated_at": datetime.now(timezone.utc)}}, upsert=True)
    return await get_profile(email)


async def profile_context(email: str) -> dict:
    """What Eva may use from the profile: {"rank", "category", "exam"} as a query-context dict.
    Rank and exam are only used for rank / cutoff questions (see routes/voice.py)."""
    p = await get_profile(email)
    out = {}
    if p.get("category"):
        out["category"] = p["category"]
    if p.get("exam") in RANK_EXAMS:
        out["exam"] = p["exam"]
        if p.get("rank"):
            out["rank"] = p["rank"]
    return out
