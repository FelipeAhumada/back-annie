# app/core/roles.py
from typing import Callable
from fastapi import HTTPException
from core.errors import http_error, ErrorCode

def require_roles(*allowed: str) -> Callable:
    """
    Guard that ensures the caller's role (from auth) is in `allowed`.
    - Uses a stable error shape for the frontend (i18n-ready).
    - Example: require_roles("admin", "manager")(auth)
    """
    def _inner(auth):
        role = getattr(auth, "role", None)
        if role not in allowed:
            raise http_error(
                status_code=403,
                code=ErrorCode.FORBIDDEN,
                message="You do not have permission to perform this action.",
                meta={
                    "required_roles": list(allowed),
                    "current_role": role,
                    "tenant_id": getattr(auth, "tenant_id", None),
                },
            )
        return auth
    return _inner

def require_authenticated(auth):
    """
    Optional helper if you want to explicitly guard 'authenticated' in some places.
    FastAPI's dependency usually handles this, but you can call it manually.
    """
    if not getattr(auth, "user_id", None):
        raise http_error(
            status_code=401,
            code=ErrorCode.UNAUTHORIZED,
            message="Authentication is required.",
        )
    return auth
