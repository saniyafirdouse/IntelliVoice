"""
Run ONLY the login + admin part of the backend (no Whisper or other AI
models). Run from backend/:   python -m uvicorn run_admin_only:app --reload
Then open http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from database.connection import close_mongo_connection, connect_to_mongo  # noqa: E402
from routes.admin import router as admin_router  # noqa: E402
from routes.auth import router as auth_router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(title="IntelliVoice Admin API (admin only)", lifespan=lifespan)
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])