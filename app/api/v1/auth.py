# app/api/v1/auth.py
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr
from core.auth import auth_required, Authed
from services.auth_service import login_issue_token, switch_tenant

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

class LoginIn(BaseModel):
    email: EmailStr
    password: str

@router.post("/login")
def login(body: LoginIn, req: Request):
    ua = req.headers.get("user-agent")
    ip = req.client.host if req.client else None
    return login_issue_token(body.email, body.password, ua, ip)

@router.get("/me")
def me(auth: Authed = Depends(auth_required)):
    return {
        "ok": True,
        "user_id": auth.user_id,
        "tenant_id": auth.tenant_id,
        "role": auth.role
    }

class SwitchTenantIn(BaseModel):
    tenant_id: str

@router.post("/switch-tenant")
def switch(p: SwitchTenantIn, auth: Authed = Depends(auth_required)):
    data = switch_tenant(auth.user_id, p.tenant_id)
    return {"ok": True, **data}
