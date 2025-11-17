"""
Authentication and JWT token management module.

Follows Layer 1 rules:
- Sign tokens with strong, private signing keys from environment variables
- NEVER hardcode secrets or keys in the repository
- Include user_id, tenant_id, and role in JWT claims
- Set sensible expirations for access tokens
- Only accept tokens via secure headers (Authorization: Bearer <token>)
"""
from __future__ import annotations
import datetime
import jwt
from fastapi import Request, Depends
from pydantic import BaseModel
from core.config import settings
from core.errors import http_error, ErrorCode


class Authed(BaseModel):
    """Authenticated user context with tenant and role information."""
    user_id: str
    tenant_id: str
    role: str


def sign_jwt(user_id: str, tenant_id: str, role: str) -> str:
    """
    Sign a JWT token with user, tenant, and role information.
    
    Args:
        user_id: User identifier
        tenant_id: Tenant identifier
        role: User role in the tenant (owner, admin, agent, observer)
    
    Returns:
        Encoded JWT token string
    """
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
    """
    FastAPI dependency that validates JWT token from Authorization header.
    
    Follows Layer 1 rules:
    - Only accepts tokens via secure headers (Authorization: Bearer <token>)
    - Returns structured error responses
    
    Args:
        req: FastAPI Request object
    
    Returns:
        Authed: Authenticated user context
    
    Raises:
        HTTPException: 401 if token is missing, invalid, or expired
    """
    auth = req.headers.get("authorization") or req.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise http_error(
            status_code=401,
            code=ErrorCode.UNAUTHORIZED,
            message="Missing bearer token",
        )
    
    token = auth.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise http_error(
            status_code=401,
            code=ErrorCode.UNAUTHORIZED,
            message="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise http_error(
            status_code=401,
            code=ErrorCode.UNAUTHORIZED,
            message="Invalid or expired token",
        )
    except Exception:
        raise http_error(
            status_code=401,
            code=ErrorCode.UNAUTHORIZED,
            message="Invalid or expired token",
        )

    return Authed(
        user_id=str(payload.get("sub", "")),
        tenant_id=str(payload.get("tenant_id", "")),
        role=str(payload.get("role", "")),
    )
