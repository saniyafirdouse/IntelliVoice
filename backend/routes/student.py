"""
routes/student.py — student-side extras (2026-10-13).

Document checklist (no login needed):
  POST   /api/checklist        {admission_type, category?, name?}  -> PDF download
         admission_type: KCET | COMEDK | Management | Lateral | MBA
         category:       General | SC | ST | OBC

College brochure (no login needed, 2026-10-15):
  GET    /api/brochure         full "College at a glance" brochure -> PDF download

Memory across visits (needs the student's login token):
  GET    /api/me/history       "Welcome back! Last time you asked about CSE fees..."
  DELETE /api/me/history       forget everything IntelliVoice remembered about me (all chats too)

"Your chats" (2026-11-20, needs the login token; only your own chats):
  GET    /api/me/conversations?q=     list (newest first), optional search
  GET    /api/me/conversations/{id}   one whole chat (to open and continue it)
  PATCH  /api/me/conversations/{id}   {title}  rename
  DELETE /api/me/conversations/{id}   delete one chat

"My callback requests" (2026-11-20):
  GET    /api/me/callbacks            the callback requests this student sent, with their status

⭐ Saved answers (2026-11-20):
  GET    /api/me/saved                list
  POST   /api/me/saved                {question, answer, language?}
  DELETE /api/me/saved/{id}

My profile (2026-11-20): exam, rank, category, preferred branches.
  GET    /api/me/profile
  PUT    /api/me/profile              {exam?, rank?, category?, branches?}
  Eva uses exam + rank (+ category) when the student asks about cutoffs / which branch they can get,
  and the checklist starts with their exam + category.

"Email me" (2026-11-20; needs SMTP_USER + SMTP_APP_PASSWORD in .env, else hidden):
  GET    /api/me/email                {enabled, to}
  POST   /api/me/email                {kind: answer | starred | checklist, question?, answer?}
         sends to the student's own login email (max 5 per hour)

My admission checklist with tick-boxes (2026-11-20):
  GET    /api/me/checklist?admission_type=&category=   the items + what is ticked
  PUT    /api/me/checklist            {admission_type, category, done: [item, ...]}
"""

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from database.connection import get_database
from engines import user_history
from engines.college_overview import brochure_pdf, build_overview
from engines.doc_checklist import ADMISSION_TYPES, CATEGORIES, NEXT_STEPS, build_checklist, checklist_pdf
from engines.college_profile import CONTACT
from utils import mailer
from utils.auth import decode_token

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


async def require_user(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    """Any logged-in user (student or admin)."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Please log in to use this.")
    payload = decode_token(creds.credentials)
    if not payload.get("sub"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid login. Please log in again.")
    return payload


def optional_user_email(authorization: str | None) -> str | None:
    """Email from an 'Authorization: Bearer ...' header, or None (never raises)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        return decode_token(authorization.split(" ", 1)[1].strip()).get("sub")
    except Exception:
        return None


class ChecklistRequest(BaseModel):
    admission_type: str
    category: str = "General"
    name: str | None = Field(None, max_length=80)


@router.post("/checklist")
async def document_checklist(body: ChecklistRequest):
    if body.admission_type not in ADMISSION_TYPES:
        raise HTTPException(422, detail=f"admission_type must be one of: {', '.join(ADMISSION_TYPES)}")
    if body.category not in CATEGORIES:
        raise HTTPException(422, detail=f"category must be one of: {', '.join(CATEGORIES)}")
    pdf = checklist_pdf(body.admission_type, body.category, (body.name or "").strip() or None)
    filename = f"SVIT_document_checklist_{body.admission_type}_{body.category}.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/brochure")
async def college_brochure():
    """Built fresh from the database each time, so admin uploads show up straight away."""
    pdf = brochure_pdf(await build_overview(trim=False))
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="SVIT_brochure_2026-27.pdf"'})


@router.get("/me/history")
async def my_history(user: dict = Depends(require_user)):
    return await user_history.get_summary(user["sub"])


@router.delete("/me/history")
async def forget_my_history(user: dict = Depends(require_user)):
    removed = await user_history.forget(user["sub"])
    return {"ok": True, "removed": removed, "message": "Done. IntelliVoice has forgotten your earlier questions."}


# ── "Your chats" (2026-11-20) ──────────────────────────────────────────────
class RenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=80)


@router.get("/me/conversations")
async def my_conversations(q: str | None = None, user: dict = Depends(require_user)):
    return {"items": await user_history.list_conversations(user["sub"], q)}


@router.get("/me/conversations/{conversation_id}")
async def my_conversation(conversation_id: str, user: dict = Depends(require_user)):
    chat = await user_history.get_conversation(user["sub"], conversation_id)
    if not chat:
        raise HTTPException(404, detail="This chat was not found. It may have been deleted.")
    return chat


@router.patch("/me/conversations/{conversation_id}")
async def rename_my_conversation(conversation_id: str, body: RenameRequest, user: dict = Depends(require_user)):
    if not await user_history.rename_conversation(user["sub"], conversation_id, body.title):
        raise HTTPException(404, detail="This chat was not found. It may have been deleted.")
    return {"ok": True}


@router.delete("/me/conversations/{conversation_id}")
async def delete_my_conversation(conversation_id: str, user: dict = Depends(require_user)):
    if not await user_history.delete_conversation(user["sub"], conversation_id):
        raise HTTPException(404, detail="This chat was not found. It may have been deleted.")
    return {"ok": True}


# ── "My callback requests" (2026-11-20) ────────────────────────────────────
CALLBACK_STATUS_TEXT = {
    "new": "Waiting: the admission office will call you during office hours",
    "called": "The admission office has called you",
    "resolved": "Resolved",
}


@router.get("/me/callbacks")
async def my_callbacks(user: dict = Depends(require_user)):
    db = get_database()
    if db is None:
        raise HTTPException(503, detail="Database is not connected. Please try again shortly.")
    docs = await db["callback_requests"].find({"email": user["sub"]}).sort("created_at", -1).to_list(length=50)
    items = []
    for d in docs:
        at = d.get("created_at")
        if at is not None and at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        items.append({
            "id": str(d["_id"]),
            "reference": str(d["_id"])[-6:].upper(),
            "question": d.get("question"),
            "phone": d.get("phone"),
            "preferred_time": d.get("preferred_time"),
            "status": d.get("status") or "new",
            "status_text": CALLBACK_STATUS_TEXT.get(d.get("status") or "new", d.get("status")),
            "created_at": at.isoformat() if at else None,
        })
    return {"items": items}


# ── ⭐ saved answers (2026-11-20) ───────────────────────────────────────────
class SaveAnswerRequest(BaseModel):
    question: str = Field("", max_length=500)
    answer: str = Field(..., min_length=1, max_length=8000)
    language: str | None = Field(None, max_length=12)


@router.get("/me/saved")
async def my_saved(user: dict = Depends(require_user)):
    return {"items": await user_history.list_saved(user["sub"])}


@router.post("/me/saved")
async def save_my_answer(body: SaveAnswerRequest, user: dict = Depends(require_user)):
    item = await user_history.save_answer(user["sub"], body.question, body.answer, body.language)
    if not item:
        raise HTTPException(503, detail="Couldn't save the answer. Please try again.")
    return item


@router.delete("/me/saved/{saved_id}")
async def delete_my_saved(saved_id: str, user: dict = Depends(require_user)):
    if not await user_history.delete_saved(user["sub"], saved_id):
        raise HTTPException(404, detail="This saved answer was not found.")
    return {"ok": True}


# ── my admission checklist with tick-boxes (2026-11-20) ────────────────────
class ChecklistProgress(BaseModel):
    admission_type: str
    category: str = "General"
    done: list[str] = Field(default_factory=list, max_length=100)


@router.get("/me/checklist")
async def my_checklist(admission_type: str | None = None, category: str | None = None,
                       user: dict = Depends(require_user)):
    saved = await user_history.get_checklist_progress(user["sub"])
    profile = await user_history.get_profile(user["sub"])      # first time: start from the profile
    kind = (admission_type if admission_type in ADMISSION_TYPES
            else saved["admission_type"] or (profile["exam"] if profile["exam"] in ADMISSION_TYPES else "KCET"))
    cat = (category if category in CATEGORIES
           else saved["category"] or (profile["category"] if profile["category"] in CATEGORIES else "General"))
    documents = build_checklist(kind, cat)
    items = set(documents) | set(NEXT_STEPS)
    return {
        "admission_type": kind,
        "category": cat,
        "admission_types": ADMISSION_TYPES,
        "categories": list(CATEGORIES),
        "documents": documents,
        "steps": list(NEXT_STEPS),
        "done": [d for d in saved["done"] if d in items],
        "note": "General checklist (demo data). Please confirm the final list with the SVIT admission office.",
    }


@router.put("/me/checklist")
async def save_my_checklist(body: ChecklistProgress, user: dict = Depends(require_user)):
    if body.admission_type not in ADMISSION_TYPES:
        raise HTTPException(422, detail=f"admission_type must be one of: {', '.join(ADMISSION_TYPES)}")
    if body.category not in CATEGORIES:
        raise HTTPException(422, detail=f"category must be one of: {', '.join(CATEGORIES)}")
    await user_history.save_checklist_progress(user["sub"], body.admission_type, body.category, body.done)
    return {"ok": True}


# ── my profile (2026-11-20) ─────────────────────────────────────────────────
class ProfileRequest(BaseModel):
    exam: str | None = Field(None, max_length=20)
    rank: int | None = Field(None, ge=1, le=500000)
    category: str | None = Field(None, max_length=20)
    branches: list[str] = Field(default_factory=list, max_length=10)


@router.get("/me/profile")
async def my_profile(user: dict = Depends(require_user)):
    return {**await user_history.get_profile(user["sub"]),
            "options": {"exams": ADMISSION_TYPES, "categories": list(user_history.PROFILE_CATEGORIES),
                        "branches": list(user_history.PROFILE_BRANCHES)}}


@router.put("/me/profile")
async def save_my_profile(body: ProfileRequest, user: dict = Depends(require_user)):
    return await user_history.save_profile(user["sub"], body.exam, body.rank, body.category, body.branches)


# ── "Email me" (2026-11-20) ────────────────────────────────────────────────
import html as _html
from typing import Literal

EMAIL_FOOTER_TEXT = ("\n\n—\nEva, SVIT admission assistant (IntelliVoice)\n"
                     "Please confirm important details with the SVIT admission office: "
                     f"{', '.join(CONTACT['mobile'])} · {CONTACT['email'][0]}")


def _html_page(title: str, body_html: str) -> str:
    return (f'<div style="font-family:Arial,sans-serif;max-width:620px;margin:auto;color:#222">'
            f'<h2 style="color:#4b2f6e;margin-bottom:4px">{_html.escape(title)}</h2>'
            f'<p style="color:#777;margin-top:0">From Eva, SVIT admission assistant</p>{body_html}'
            f'<hr style="border:none;border-top:1px solid #ddd;margin:24px 0">'
            f'<p style="color:#777;font-size:13px">Please confirm important details with the SVIT admission office: '
            f'{_html.escape(", ".join(CONTACT["mobile"]))} · {_html.escape(CONTACT["email"][0])}</p></div>')


def _qa_html(question: str, answer: str) -> str:
    q = f'<p style="color:#555;margin:0 0 4px"><b>Q:</b> {_html.escape(question)}</p>' if question else ""
    a = _html.escape(answer).replace("\n", "<br>")
    return f'<div style="background:#f6f2fb;border-radius:10px;padding:12px 14px;margin:10px 0">{q}<p style="margin:0">{a}</p></div>'


class EmailRequest(BaseModel):
    kind: Literal["answer", "starred", "checklist"]
    question: str = Field("", max_length=500)
    answer: str = Field("", max_length=8000)


@router.get("/me/email")
async def email_status(user: dict = Depends(require_user)):
    return {"enabled": mailer.email_enabled(), "to": user["sub"]}


@router.post("/me/email")
async def email_me(body: EmailRequest, user: dict = Depends(require_user)):
    if not mailer.email_enabled():
        raise HTTPException(503, detail="Email is not available right now.")
    to = user["sub"]
    attachments = []
    if body.kind == "answer":
        if not body.answer.strip():
            raise HTTPException(422, detail="Nothing to send.")
        subject = "Your answer from Eva – SVIT Admissions"
        text = (f"Q: {body.question}\n\n" if body.question else "") + body.answer
        html = _html_page("Your answer from Eva", _qa_html(body.question, body.answer))
    elif body.kind == "starred":
        items = await user_history.list_saved(to)
        if not items:
            raise HTTPException(422, detail="You haven't starred any answers yet.")
        subject = f"Your {len(items)} starred answer{'s' if len(items) != 1 else ''} from Eva"
        text = "\n\n".join((f"Q: {s['question']}\n" if s["question"] else "") + s["answer"] for s in items)
        html = _html_page("Your starred answers", "".join(_qa_html(s["question"], s["answer"]) for s in items))
    else:
        progress = await user_history.get_checklist_progress(to)
        profile = await user_history.get_profile(to)
        kind = progress["admission_type"] or (profile["exam"] if profile["exam"] in ADMISSION_TYPES else "KCET")
        cat = progress["category"] or (profile["category"] if profile["category"] in CATEGORIES else "General")
        done = set(progress["done"])
        documents, steps = build_checklist(kind, cat), list(NEXT_STEPS)
        mark = lambda item: ("✔ " if item in done else "☐ ") + item
        subject = "Your SVIT admission checklist"
        text = (f"{ADMISSION_TYPES[kind]} · {cat}\n\nDocuments to bring:\n" + "\n".join(mark(d) for d in documents)
                + "\n\nNext steps:\n" + "\n".join(mark(s) for s in steps) + "\n\nThe printable PDF is attached.")
        li = lambda items: "".join(f'<li style="margin:4px 0">{_html.escape(mark(i))}</li>' for i in items)
        html = _html_page("Your admission checklist",
                          f"<p><b>{_html.escape(ADMISSION_TYPES[kind])}</b> · {_html.escape(cat)} · "
                          f"{sum(1 for i in documents + steps if i in done)} of {len(documents) + len(steps)} done</p>"
                          f"<h3>Documents to bring</h3><ul style='list-style:none;padding:0'>{li(documents)}</ul>"
                          f"<h3>Next steps</h3><ul style='list-style:none;padding:0'>{li(steps)}</ul>"
                          f"<p>The printable PDF is attached.</p>")
        attachments.append((f"SVIT_document_checklist_{kind}_{cat}.pdf", checklist_pdf(kind, cat), "application/pdf"))
    if not mailer.allowed(to):
        raise HTTPException(429, detail=f"You can send up to {mailer.MAX_PER_HOUR} emails an hour. Please try again later.")
    try:
        await mailer.send_email(to, subject, text + EMAIL_FOOTER_TEXT, html, attachments)
    except RuntimeError as e:
        raise HTTPException(502, detail=str(e))
    return {"ok": True, "message": f"Sent to {to}. If you don't see it, check your Spam folder."}
