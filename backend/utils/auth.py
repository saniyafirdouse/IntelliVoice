"""
utils/auth.py — password hashing + login tokens (JWT)

Used by routes/auth.py (login/signup) and routes/admin.py (protects every
admin endpoint).

- Passwords are stored as bcrypt hashes, never as plain text.
- After login the user gets a token. The frontend sends it back on every
  request as the header:   Authorization: Bearer <token>
- `require_admin` is a FastAPI dependency: any admin route that uses it
  returns 401/403 unless a valid admin token is sent.

Needs SECRET_KEY in backend/.env (any long random string).
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
TOKEN_HOURS = 12  # admin stays logged in for one working day

_bearer = HTTPBearer(auto_error=False)


# ── passwords ──────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ── tokens ─────────────────────────────────────────────────────────────────
def _secret() -> str:
    if not SECRET_KEY:
        raise HTTPException(500, detail="Server is missing SECRET_KEY in .env")
    return SECRET_KEY


def create_token(email: str, role: str, name: str = "") -> str:
    payload = {
        "sub": email,
        "role": role,
        "name": name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid login. Please log in again.")


# ── FastAPI dependencies ───────────────────────────────────────────────────
async def require_admin(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """Use as: `admin = Depends(require_admin)`. Returns the token payload."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Please log in as admin.")
    payload = decode_token(creds.credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Admin access only.")
    return payload
