"""
routes/auth.py — login and sign-up (matches IntelliVoice_API_Contract.md §2)

    POST /auth/signup   {name, email, phone, password}       -> 201 {token, user}
    POST /auth/login    {email, password, role}              -> 200 {token, user}

- Sign-up only ever creates "student" accounts.
- Admin accounts are created by the team with:  python create_admin.py
- Users are stored in the MongoDB collection "users".
"""

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from database.connection import get_database
from utils.auth import create_token, hash_password, verify_password

router = APIRouter()

USERS = "users"


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=20)
    password: str = Field(min_length=6, max_length=100)


class LoginRequest(BaseModel):
    email: str
    password: str
    role: Literal["student", "admin"] = "student"


def _user_out(user: dict) -> dict:
    return {"name": user.get("name", ""), "email": user["email"], "role": user["role"]}


def _db():
    db = get_database()
    if db is None:
        raise HTTPException(503, detail="Database is not connected. Please try again shortly.")
    return db


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest):
    db = _db()
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(400, detail="Please enter a valid email address.")
    if await db[USERS].find_one({"email": email}):
        raise HTTPException(409, detail="An account with this email already exists. Please log in.")

    user = {
        "name": body.name.strip(),
        "email": email,
        "phone": body.phone,
        "password_hash": hash_password(body.password),
        "role": "student",
    }
    await db[USERS].insert_one(user)
    return {"token": create_token(email, "student", user["name"]), "user": _user_out(user)}


@router.post("/login")
async def login(body: LoginRequest):
    db = _db()
    email = body.email.strip().lower()
    user = await db[USERS].find_one({"email": email})

    # Same message for "no such user" and "wrong password" so nobody can
    # find out which emails are registered.
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(401, detail="Incorrect email or password.")
    if user.get("role") != body.role:
        raise HTTPException(403, detail=f"This account is not registered as {body.role}.")

    return {"token": create_token(email, user["role"], user.get("name", "")), "user": _user_out(user)}
