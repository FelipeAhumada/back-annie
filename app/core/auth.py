# app/core/auth.py
import datetime, jwt
from fastapi import HTTPException, Request
from pydantic import BaseModel
from core.config import settings
from core.db import get_conn

class Authed(BaseModel):
    user_id: str
    tenant_id: str
    role: str

def sign_jwt(user_id: str, tenant_id: str, role: str) -> str:
    now = datetime.datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": str(role),
        "iat": now,
        "exp": now + datetime.timedelta(minutes=settings.JWT_EXP_MIN),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def auth_required(req: Request) -> Authed:
    auth = req.headers.get("authorization") or req.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")

    return Authed(
        user_id=str(payload.get("sub")),
        tenant_id=str(payload.get("tenant_id")),
        role=str(payload.get("role")),
    )
