# from fastapi import APIRouter

# router = APIRouter()

# @router.get("/dashboard")
# async def admin_dashboard():
#     return {"message": "Admin dashboard — coming in Day 4"}
"""
routes/admin.py — Admin Panel API. Every endpoint needs an admin login token
(header  Authorization: Bearer <token>, from POST /auth/login with role "admin").

Mounted in main.py under /api/admin, so the frontend's Express server
forwards it like every other /api/... request.

Data updates (Excel)
  GET  /api/admin/datasets                          what can be updated + last update date
  GET  /api/admin/datasets/{name}/template          download Excel pre-filled with current data
  POST /api/admin/datasets/{name}/upload            upload file -> PREVIEW (nothing saved yet)
  POST /api/admin/uploads/{upload_id}/confirm       apply the previewed changes
  POST /api/admin/uploads/{upload_id}/cancel        throw the preview away
  POST /api/admin/uploads/{upload_id}/undo          roll an applied upload back
  GET  /api/admin/uploads                           upload history (?dataset=fees)
  GET  /api/admin/uploads/{upload_id}               one upload with all its changes

Insights
  GET  /api/admin/dashboard?days=7                  analytics dashboard
  GET  /api/admin/unanswered?days=7                 questions we couldn't answer
  POST /api/admin/unanswered/resolve                {"log_ids": [...]} mark as handled

Activity log (2026-10-15)
  GET  /api/admin/activity?limit=100                who did what, newest first

College website (2026-10-30)
  POST /api/admin/website/refresh                   read saividya.ac.in again (pages + PDFs), in the background
  GET  /api/admin/website/status                    is it running? what changed last time?
"""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from database.connection import get_database
from engines import analytics_engine
from engines.knowledge_engine import invalidate_cache   # 2026-10-12: uploads show up instantly
from utils import data_import as di
from utils.admin_activity import list_activity, log_activity
from utils.auth import require_admin
from utils.datasets import DATASETS, get_dataset
from engines import website_engine                     # 2026-10-30: "Fetch updated data from website"

router = APIRouter(dependencies=[Depends(require_admin)])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


def _db():
    db = get_database()
    if db is None:
        raise HTTPException(503, detail="Database is not connected. Please try again shortly.")
    return db


def _dataset_or_404(name: str) -> dict:
    ds = get_dataset(name)
    if not ds:
        raise HTTPException(404, detail=f"Unknown dataset '{name}'. Available: {', '.join(DATASETS)}")
    return ds


def _batch_error(e: di.BatchError):
    content = {"detail": e.message}
    if e.details:
        content["records"] = e.details
    return JSONResponse(status_code=e.status_code, content=content)


# ── Datasets ───────────────────────────────────────────────────────────────
@router.get("/datasets")
async def list_datasets():
    db = _db()
    out = []
    for name, ds in DATASETS.items():
        coll = db[ds["collection"]]
        count = await coll.count_documents({})
        latest = await coll.find({"last_updated": {"$exists": True}}).sort("last_updated", -1).limit(1).to_list(1)
        out.append({
            "name": name,
            "title": ds["title"],
            "records": count,
            "last_updated": latest[0]["last_updated"] if latest else None,
            "columns": [{"field": c["field"], "required": bool(c.get("required")), "help": c.get("help", "")}
                        for c in ds["columns"]],
        })
    return {"datasets": out}


@router.get("/datasets/{name}/template")
async def download_template(name: str, admin: dict = Depends(require_admin)):
    ds = _dataset_or_404(name)
    docs = await _db()[ds["collection"]].find({}).to_list(length=None)
    await log_activity(_db(), admin["sub"], "template_download", name)
    content = di.build_template(name, ds, docs)
    filename = f"intellivoice_{name}_{di.today_ist()}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/datasets/{name}/upload")
async def upload_preview(name: str, file: UploadFile = File(...), admin: dict = Depends(require_admin)):
    ds = _dataset_or_404(name)
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, detail="File is too large (max 5 MB).")
    try:
        result = await di.create_preview(_db(), name, ds, file.filename, content, admin["sub"])
        await log_activity(_db(), admin["sub"], "upload_preview", f"{name}: {file.filename}")
        return result
    except di.SheetError as e:
        raise HTTPException(400, detail=str(e))


# ── Upload batches ─────────────────────────────────────────────────────────
@router.get("/uploads")
async def upload_history(dataset: str | None = None, limit: int = Query(20, ge=1, le=100)):
    return {"uploads": await di.list_batches(_db(), dataset, limit)}


@router.get("/uploads/{upload_id}")
async def upload_detail(upload_id: str):
    try:
        return await di.get_batch_summary(_db(), upload_id)
    except di.BatchError as e:
        return _batch_error(e)


@router.post("/uploads/{upload_id}/confirm")
async def upload_confirm(upload_id: str, admin: dict = Depends(require_admin)):
    try:
        result = await di.confirm_batch(_db(), upload_id, admin["sub"])
        invalidate_cache()   # the assistant answers from the new data straight away
        await log_activity(_db(), admin["sub"], "upload_confirm", f"upload {upload_id[-6:]}")
        return result
    except di.BatchError as e:
        return _batch_error(e)


@router.post("/uploads/{upload_id}/cancel")
async def upload_cancel(upload_id: str, admin: dict = Depends(require_admin)):
    try:
        result = await di.cancel_batch(_db(), upload_id)
        await log_activity(_db(), admin["sub"], "upload_cancel", f"upload {upload_id[-6:]}")
        return result
    except di.BatchError as e:
        return _batch_error(e)


@router.post("/uploads/{upload_id}/undo")
async def upload_undo(upload_id: str, admin: dict = Depends(require_admin)):
    try:
        result = await di.undo_batch(_db(), upload_id, admin["sub"])
        invalidate_cache()   # back to the old data straight away
        await log_activity(_db(), admin["sub"], "upload_undo", f"upload {upload_id[-6:]}")
        return result
    except di.BatchError as e:
        return _batch_error(e)


# ── Insights ───────────────────────────────────────────────────────────────
@router.get("/dashboard")
async def dashboard(days: int = Query(7, ge=1, le=365)):
    return await analytics_engine.get_dashboard(_db(), days)


@router.get("/unanswered")
async def unanswered(days: int = Query(7, ge=1, le=365), include_resolved: bool = False):
    return await analytics_engine.get_unanswered(_db(), days, include_resolved)


class ResolveRequest(BaseModel):
    log_ids: list[str]


@router.post("/unanswered/resolve")
async def resolve_unanswered(body: ResolveRequest, admin: dict = Depends(require_admin)):
    resolved = await analytics_engine.mark_resolved(_db(), body.log_ids)
    await log_activity(_db(), admin["sub"], "unanswered_resolve", f"{len(body.log_ids)} question(s)")
    return {"resolved": resolved}


# ── System health (2026-11-01) ───────────────────────────────────────────
# Is everything working right now? Service status, time per step over the last
# questions, and recent problems. The page asks every 10 seconds; nothing here
# calls Groq or Sarvam (that would cost credits) — it reads the question logs.
HEALTH_STEPS = [            # (label, timing keys added together), in pipeline order
    ("Speech to text", ["stt"]),
    ("Language + correction", ["language_detect", "correction"]),
    ("Understanding", ["intelligence"]),
    ("Database lookup", ["knowledge"]),
    ("Writing the answer", ["generate"]),
    ("Kannada translate + polish", ["translate", "polish", "direct"]),
    ("Voice", ["tts"]),
]


def _avg(values):
    return round(sum(values) / len(values)) if values else None


def _p90(values):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(0.9 * (len(ordered) - 1))))]


@router.get("/health")
async def system_health():
    import time as _time
    from datetime import datetime, timedelta, timezone
    from utils import sarvam_keys
    from utils.system_health import (PHONE_HOURLY_CAP, phone_paused, phone_questions_last_hour,
                                     recent_problems, uptime_seconds)

    db = get_database()
    services = {"backend": {"ok": True, "detail": f"running for {uptime_seconds() // 60} min"}}

    # MongoDB
    mongo_ms = None
    try:
        if db is None:
            raise RuntimeError("not connected")
        t0 = _time.perf_counter()
        await db.command("ping")
        mongo_ms = round((_time.perf_counter() - t0) * 1000)
        services["database"] = {"ok": True, "detail": f"MongoDB reachable ({mongo_ms} ms)"}
    except Exception as e:
        services["database"] = {"ok": False, "detail": f"MongoDB not reachable: {type(e).__name__}"}

    # Sarvam keys (numbers only, never the keys)
    try:
        st = sarvam_keys.status()
        resting = st.get("resting") or []
        ok = st["keys"] > 0 and len(resting) < st["keys"]
        services["sarvam"] = {"ok": ok, "keys": st["keys"], "in_use": st.get("in_use"), "resting": resting,
                              "detail": (f"key {st.get('in_use')} of {st['keys']} in use"
                                         + (f"; out of credits / refused: key {', '.join(map(str, resting))}" if resting else ""))}
    except Exception as e:
        services["sarvam"] = {"ok": False, "keys": 0, "in_use": None, "resting": [], "detail": f"No Sarvam key loaded ({type(e).__name__})"}

    # Recent questions (for Groq status, speed and errors)
    logs = []
    if db is not None:
        try:
            cursor = db[analytics_engine.LOGS].find(
                {"timings_ms": {"$exists": True}},
                {"timestamp": 1, "text": 1, "timings_ms": 1, "reply_ok": 1, "reply_path": 1, "tts_ok": 1,
                 "tts_error": 1, "status": 1, "language": 1, "response_time_ms": 1},
            ).sort("timestamp", -1).limit(100)
            logs = await cursor.to_list(length=100)
        except Exception as e:
            print(f"⚠️ System health: could not read logs: {e}")

    now = datetime.now(timezone.utc)
    def _aware(t):
        return t if t is None or t.tzinfo else t.replace(tzinfo=timezone.utc)
    hour = [l for l in logs if _aware(l.get("timestamp")) and now - _aware(l["timestamp"]) <= timedelta(hours=1)]

    replies = [l for l in logs if l.get("reply_ok") is not None]
    last_three = replies[:3]
    if not replies:
        services["groq"] = {"ok": None, "detail": "No questions answered yet since logging started"}
    elif last_three and all(l.get("reply_ok") is False for l in last_three):
        services["groq"] = {"ok": False, "detail": "The last 3 replies failed — check the Groq key / internet"}
    else:
        last_ok = next((l for l in replies if l.get("reply_ok")), None)
        when = _aware(last_ok["timestamp"]).isoformat() if last_ok else None
        services["groq"] = {"ok": True, "detail": "Answers are being written normally", "last_ok": when}

    # Time per step over the last 100 questions
    steps = []
    for label, keys in HEALTH_STEPS:
        vals = []
        for l in logs:
            t = l.get("timings_ms") or {}
            present = [t[k] for k in keys if isinstance(t.get(k), (int, float))]
            if present:
                vals.append(sum(present))
        steps.append({"label": label, "avg_ms": _avg(vals), "p90_ms": _p90(vals), "count": len(vals)})
    totals = [l["timings_ms"]["total"] for l in logs if isinstance((l.get("timings_ms") or {}).get("total"), (int, float))]

    # Problems in the last hour + recent problem list
    failed = [l for l in hour if l.get("reply_ok") is False]
    voice_failed = [l for l in hour if l.get("tts_ok") is False]
    unclear = [l for l in hour if l.get("reply_path") == "unclear"]
    problems = recent_problems(10)
    for l in logs:
        if len(problems) >= 10:
            break
        if l.get("reply_ok") is False or l.get("tts_ok") is False:
            problems.append({"at": _aware(l["timestamp"]).isoformat(timespec="seconds"),
                             "source": "Voice" if l.get("reply_ok") is not False else "Reply",
                             "detail": (l.get("tts_error") or "reply could not be generated") + f" — “{(l.get('text') or '')[:60]}”"})

    return {
        "checked_at": now.isoformat(timespec="seconds"),
        "services": services,
        "speed": {"questions": len(totals), "avg_total_ms": _avg(totals), "p90_total_ms": _p90(totals), "steps": steps},
        "last_hour": {"questions": len(hour), "failed_replies": len(failed), "voice_failed": len(voice_failed),
                      "could_not_hear": len(unclear)},
        "problems": problems[:10],
        # 2026-11-01: visitors on their own phones (through the Cloudflare tunnel)
        "phones": {"paused": phone_paused(), "questions_last_hour": phone_questions_last_hour(),
                   "hourly_cap": PHONE_HOURLY_CAP},
    }


class PhoneAccessRequest(BaseModel):
    paused: bool


@router.post("/phone-access")
async def set_phone_access(body: PhoneAccessRequest, admin: dict = Depends(require_admin)):
    """2026-11-01: one click pauses / resumes every visitor phone; the stall laptop keeps working."""
    from utils.system_health import set_phone_paused
    set_phone_paused(body.paused)
    try:
        await log_activity(_db(), admin["sub"], "phone_access", "paused" if body.paused else "resumed")
    except Exception:
        pass
    return {"paused": body.paused}


# ── Activity log ───────────────────────────────────────────────────────────
@router.get("/activity")
async def activity(limit: int = Query(100, ge=1, le=500), admin_email: str | None = None, action: str | None = None):
    return await list_activity(_db(), limit, admin_email, action)


# ── College website (2026-10-30) ─────────────────────────────────────────
_website_task = None


@router.post("/website/refresh")
async def website_refresh(admin: dict = Depends(require_admin)):
    """Starts reading the college website again; poll /website/status for the result."""
    global _website_task
    db = _db()
    if website_engine.status["running"]:
        return {"started": False, "status": website_engine.status}

    async def run():
        summary = await website_engine.refresh(db)
        if not summary.get("error"):
            invalidate_cache()
        details = (f"failed: {summary['error']}" if summary.get("error") else
                   f"{summary.get('pages')} pages, {summary.get('pdfs')} PDFs, {summary.get('new_pdfs')} new PDFs, "
                   f"{summary.get('changed_pages')} changed pages")
        await log_activity(db, admin["sub"], "website_refresh", details)

    import asyncio
    _website_task = asyncio.create_task(run())
    return {"started": True, "status": website_engine.status}


@router.get("/website/status")
async def website_status():
    return {"status": website_engine.status, "last_fetch": await website_engine.last_fetch(_db())}
