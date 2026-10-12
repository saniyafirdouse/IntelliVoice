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
"""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from database.connection import get_database
from engines import analytics_engine
from utils import data_import as di
from utils.auth import require_admin
from utils.datasets import DATASETS, get_dataset

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
async def download_template(name: str):
    ds = _dataset_or_404(name)
    docs = await _db()[ds["collection"]].find({}).to_list(length=None)
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
        return await di.create_preview(_db(), name, ds, file.filename, content, admin["sub"])
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
        return await di.confirm_batch(_db(), upload_id, admin["sub"])
    except di.BatchError as e:
        return _batch_error(e)


@router.post("/uploads/{upload_id}/cancel")
async def upload_cancel(upload_id: str):
    try:
        return await di.cancel_batch(_db(), upload_id)
    except di.BatchError as e:
        return _batch_error(e)


@router.post("/uploads/{upload_id}/undo")
async def upload_undo(upload_id: str, admin: dict = Depends(require_admin)):
    try:
        return await di.undo_batch(_db(), upload_id, admin["sub"])
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
async def resolve_unanswered(body: ResolveRequest):
    return {"resolved": await analytics_engine.mark_resolved(_db(), body.log_ids)}
