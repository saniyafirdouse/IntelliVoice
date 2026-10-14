"""
routes/callbacks.py — "Ask the admission office to call me back" (2026-10-13).

When IntelliVoice can't answer, or a parent is worried, the chat offers a
callback. The parent leaves a name and phone number; the request is saved
in MongoDB (collection "callback_requests") with the question and the last
few chat turns, so the office knows what it is about. Staff see the list in
the admin panel and mark each one as called / resolved.

Public (no login — it is the parent asking):
  POST  /api/callback                      {name, phone, question?, language?, preferred_time?, session_id?}

Admin (admin login token, like routes/admin.py):
  GET   /api/admin/callbacks?status=new    list requests (status: new | called | resolved | all)
  PATCH /api/admin/callbacks/{id}          {status?, note?}  update one request
"""

import re
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from database.connection import get_database
from engines.memory_engine import memory_engine
from utils.auth import require_admin

COLLECTION = "callback_requests"
STATUSES = ("new", "called", "resolved")
DUPLICATE_WINDOW = timedelta(minutes=10)   # same phone again within 10 min -> same request

public_router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])


def _db():
    db = get_database()
    if db is None:
        raise HTTPException(503, detail="Database is not connected. Please try again shortly.")
    return db


def _now():
    return datetime.now(timezone.utc)


def clean_phone(raw: str) -> str | None:
    """Indian mobile/landline -> digits only ('+91 91085 75191' -> '9108575191'), or None if invalid."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    return digits if len(digits) == 10 else None


class CallbackRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    phone: str = Field(..., min_length=10, max_length=20)
    question: str | None = Field(None, max_length=500)
    language: str | None = Field(None, max_length=10)
    preferred_time: str | None = Field(None, max_length=60)
    session_id: str | None = Field(None, max_length=100)


class CallbackUpdate(BaseModel):
    status: str | None = None
    note: str | None = Field(None, max_length=500)


def _public_view(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "phone": doc.get("phone"),
        "question": doc.get("question"),
        "language": doc.get("language"),
        "preferred_time": doc.get("preferred_time"),
        "recent_conversation": doc.get("recent_conversation") or [],
        "status": doc.get("status"),
        "note": doc.get("note") or "",
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
        "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
        "handled_by": doc.get("handled_by"),
    }


@public_router.post("/callback")
async def create_callback(body: CallbackRequest):
    phone = clean_phone(body.phone)
    if not phone:
        raise HTTPException(422, detail="Please enter a valid 10-digit phone number.")
    name = " ".join(body.name.split())
    if not name:
        raise HTTPException(422, detail="Please enter your name.")

    db = _db()
    # Same phone within a few minutes (double tap / resend): update, don't duplicate.
    recent = await db[COLLECTION].find_one(
        {"phone": phone, "status": "new", "created_at": {"$gte": _now() - DUPLICATE_WINDOW}}
    )

    turns = []
    if body.session_id:
        context = memory_engine.get_context(body.session_id, last_n=4)
        turns = [{"question": t["user_text"], "answer": t["response_text"]} for t in context["turns"]]

    question = (body.question or "").strip() or (turns[-1]["question"] if turns else None)
    fields = {
        "name": name,
        "phone": phone,
        "question": question,
        "language": body.language,
        "preferred_time": (body.preferred_time or "").strip() or None,
        "session_id": body.session_id,
        "recent_conversation": turns,
        "updated_at": _now(),
    }
    if recent:
        # Keep what we already have (chat turns, question...) if this resend lacks it.
        fields = {k: v for k, v in fields.items() if v not in (None, [], "")}
        await db[COLLECTION].update_one({"_id": recent["_id"]}, {"$set": fields})
        ref = recent["_id"]
    else:
        result = await db[COLLECTION].insert_one({**fields, "status": "new", "note": "", "created_at": _now()})
        ref = result.inserted_id

    return {
        "ok": True,
        "reference": str(ref)[-6:].upper(),
        "message": "Thank you. The SVIT admission office will call you back during office hours "
                   "(Monday to Friday 8:30 am to 4:10 pm, Saturday 8:30 am to 12:50 pm).",
    }


@admin_router.get("")
async def list_callbacks(status: str = Query("new"), limit: int = Query(100, ge=1, le=500)):
    if status != "all" and status not in STATUSES:
        raise HTTPException(422, detail=f"status must be one of: all, {', '.join(STATUSES)}")
    db = _db()
    query = {} if status == "all" else {"status": status}
    docs = await db[COLLECTION].find(query).sort("created_at", -1).to_list(length=limit)
    counts = {s: await db[COLLECTION].count_documents({"status": s}) for s in STATUSES}
    return {"items": [_public_view(d) for d in docs], "counts": counts}


@admin_router.patch("/{callback_id}")
async def update_callback(callback_id: str, body: CallbackUpdate, admin: dict = Depends(require_admin)):
    if body.status is not None and body.status not in STATUSES:
        raise HTTPException(422, detail=f"status must be one of: {', '.join(STATUSES)}")
    try:
        oid = ObjectId(callback_id)
    except (InvalidId, TypeError):
        raise HTTPException(404, detail="Callback request not found.")
    changes = {"updated_at": _now(), "handled_by": admin.get("email") or admin.get("sub")}
    if body.status is not None:
        changes["status"] = body.status
    if body.note is not None:
        changes["note"] = body.note.strip()
    db = _db()
    result = await db[COLLECTION].find_one_and_update({"_id": oid}, {"$set": changes}, return_document=True)
    if not result:
        raise HTTPException(404, detail="Callback request not found.")
    return _public_view(result)
