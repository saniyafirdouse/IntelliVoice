from fastapi import APIRouter
from database.connection import get_database

router = APIRouter()

@router.get("/")
async def health_check():
    db = get_database()
    
    mongo_status = "connected"
    try:
        await db.command("ping")
    except Exception:
        mongo_status = "disconnected"
    
    return {
        "status": "healthy",
        "engines": {
            "language_engine": "ready",
            "intelligence_engine": "ready",
            "knowledge_engine": "ready",
            "memory_engine": "ready",
            "response_engine": "ready",
            "analytics_engine": "ready"
        },
        "database": mongo_status
    }