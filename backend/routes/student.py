"""
routes/student.py — student-side extras (2026-10-13).

Document checklist (no login needed):
  POST   /api/checklist        {admission_type, category?, name?}  -> PDF download
         admission_type: KCET | COMEDK | Management | Lateral | MBA
         category:       General | SC | ST | OBC

Memory across visits (needs the student's login token):
  GET    /api/me/history       "Welcome back! Last time you asked about CSE fees..."
  DELETE /api/me/history       forget everything IntelliVoice remembered about me
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from engines import user_history
from engines.doc_checklist import ADMISSION_TYPES, CATEGORIES, checklist_pdf
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


@router.get("/me/history")
async def my_history(user: dict = Depends(require_user)):
    return await user_history.get_summary(user["sub"])


@router.delete("/me/history")
async def forget_my_history(user: dict = Depends(require_user)):
    removed = await user_history.forget(user["sub"])
    return {"ok": True, "removed": removed, "message": "Done. IntelliVoice has forgotten your earlier questions."}
