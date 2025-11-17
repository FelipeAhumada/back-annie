"""
RBAC (Role-Based Access Control) module for Annie-AI backend.

Follows Layer 2 rules:
- Roles are: owner, admin, agent, observer (lowercase)
- All endpoints that change data MUST enforce role checks
- RBAC logic MUST live in this dedicated module, not scattered
- Clear rules:
  - Settings read → min role observer
  - Settings write → min role admin
  - Destructive actions (delete org, billing critical ops) → role owner
- Never trust role or tenant information from client; always from JWT claims
"""
from __future__ import annotations
from typing import Callable
from core.errors import http_error, ErrorCode

# Role hierarchy (lower number = higher privilege)
ROLE_HIERARCHY = {
    "owner": 0,
    "admin": 1,
    "agent": 2,
    "observer": 3,
}


def require_roles(*allowed: str) -> Callable:
    """
    Guard that ensures the caller's role (from auth) is in `allowed`.
    
    Uses a stable error shape for the frontend (i18n-ready).
    
    Args:
        *allowed: Allowed role names (e.g., "admin", "owner")
    
    Returns:
        Dependency function that validates role
    
    Example:
        @router.post("/endpoint")
        def endpoint(auth: Authed = Depends(require_roles("admin", "owner"))):
            ...
    """
    def _inner(auth):
        role = getattr(auth, "role", None)
        if not role or role not in allowed:
            raise http_error(
                status_code=403,
                code=ErrorCode.FORBIDDEN,
                message="You do not have permission for this action",
                meta={
                    "required_roles": list(allowed),
                    "current_role": role,
                    "tenant_id": getattr(auth, "tenant_id", None),
                },
            )
        return auth
    return _inner


def require_min_role(min_role: str) -> Callable:
    """
    Guard that ensures the caller's role meets minimum privilege level.
    
    Role hierarchy: owner > admin > agent > observer
    
    Args:
        min_role: Minimum required role (e.g., "admin" allows admin and owner)
    
    Returns:
        Dependency function that validates minimum role
    
    Example:
        @router.get("/settings")
        def get_settings(auth: Authed = Depends(require_min_role("observer"))):
            ...
    """
    if min_role not in ROLE_HIERARCHY:
        raise ValueError(f"Invalid role: {min_role}. Must be one of {list(ROLE_HIERARCHY.keys())}")
    
    min_level = ROLE_HIERARCHY[min_role]
    
    def _inner(auth):
        role = getattr(auth, "role", None)
        if not role:
            raise http_error(
                status_code=403,
                code=ErrorCode.FORBIDDEN,
                message="You do not have permission for this action",
                meta={
                    "required_min_role": min_role,
                    "current_role": None,
                    "tenant_id": getattr(auth, "tenant_id", None),
                },
            )
        
        user_level = ROLE_HIERARCHY.get(role, 999)  # Unknown roles = lowest privilege
        if user_level > min_level:
            raise http_error(
                status_code=403,
                code=ErrorCode.FORBIDDEN,
                message="You do not have permission for this action",
                meta={
                    "required_min_role": min_role,
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
    
    Args:
        auth: Authenticated user context
    
    Returns:
        auth if valid
    
    Raises:
        HTTPException: If not authenticated
    """
    if not getattr(auth, "user_id", None):
        raise http_error(
            status_code=401,
            code=ErrorCode.UNAUTHORIZED,
            message="Authentication is required.",
        )
    return auth
