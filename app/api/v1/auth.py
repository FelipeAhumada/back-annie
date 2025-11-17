"""
Authentication endpoints.

Follows Layer 1 and Layer 3 rules:
- Validate input with Pydantic schemas
- Return minimal information on failure
- ALWAYS use Pydantic models for request/response
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr
from core.auth import auth_required, Authed
from services.auth_service import login_issue_token, switch_tenant

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginIn(BaseModel):
    """Request schema for user login."""
    email: EmailStr = EmailStr(..., description="User email address")
    password: str = ..., description="User password")


class LoginOut(BaseModel):
    """Response schema for successful login."""
    ok: bool
    token: str
    current_tenant: dict
    tenants: list[dict]


class MeOut(BaseModel):
    """Response schema for /me endpoint."""
    ok: bool
    user_id: str
    tenant_id: str
    role: str


class SwitchTenantIn(BaseModel):
    """Request schema for tenant switch."""
    tenant_id: str = ..., description="Target tenant identifier")


class SwitchTenantOut(BaseModel):
    """Response schema for tenant switch."""
    ok: bool
    token: str
    tenant_id: str
    role: str


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, req: Request) -> dict:
    """
    Authenticate user and issue JWT token.
    
    Follows Layer 1 rules:
    - Validate input with Pydantic schemas
    - Return minimal information on failure (no "user not found vs wrong password" distinction)
    
    Args:
        body: Login credentials
        req: FastAPI Request object (for user-agent and IP)
    
    Returns:
        Dict with token, current_tenant, and tenants list
    """
    ua = req.headers.get("user-agent")
    ip = req.client.host if req.client else None
    return login_issue_token(body.email, body.password, ua, ip)


@router.get("/me", response_model=MeOut)
def me(auth: Authed = Depends(auth_required)) -> dict:
    """
    Get current authenticated user information.
    
    Args:
        auth: Authenticated user context
    
    Returns:
        Dict with user_id, tenant_id, and role
    """
    return {
        "ok": True,
        "user_id": auth.user_id,
        "tenant_id": auth.tenant_id,
        "role": auth.role
    }


@router.post("/switch-tenant", response_model=SwitchTenantOut)
def switch(p: SwitchTenantIn, auth: Authed = Depends(auth_required)) -> dict:
    """
    Switch user's active tenant.
    
    Args:
        p: Target tenant identifier
        auth: Authenticated user context
    
    Returns:
        Dict with new token, tenant_id, and role
    """
    data = switch_tenant(auth.user_id, p.tenant_id)
    return {"ok": True, **data}
