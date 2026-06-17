from fastapi import APIRouter

router = APIRouter()

@router.get("/dashboard")
async def admin_dashboard():
    return {"message": "Admin dashboard — coming in Day 4"}
