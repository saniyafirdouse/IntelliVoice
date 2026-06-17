from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database.connection import connect_to_mongo, close_mongo_connection
from routes.health import router as health_router
from routes.voice import router as voice_router
from routes.admin import router as admin_router
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(
    title="IntelliVoice API",
    description="Multilingual voice assistant backend for SVIT college",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(voice_router, prefix="/voice", tags=["Voice"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])

@app.get("/")
async def root():
    return {
        "project": "IntelliVoice",
        "version": "1.0.0",
        "status": "running",
        "college": "SVIT"
    }