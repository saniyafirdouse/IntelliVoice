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
"""

from datetime import datetime, timezone

from database.connection import get_database

COLLECTION = "user_history"
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
    db = get_database()
    if db is None:
        return 0
    result = await db[COLLECTION].delete_many({"email": email})
    return result.deleted_count
