# app/api/v1/plans.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.auth import auth_required, Authed
from repositories.plan_repo import list_pricing, create_plan, set_tenant_plan, upsert_limit, get_plan_limits

router = APIRouter(prefix="/api/v1/plans", tags=["plans"])

@router.get("")
def plans(auth: Authed = Depends(auth_required)):
    return {"plans": list_pricing(auth.tenant_id)}

class PlanIn(BaseModel):
    name: str
    uf: float | None = None
    clp: int | None = None
    features: list = []

@router.post("")
def plan_create(p: PlanIn, auth: Authed = Depends(auth_required)):
    pid = create_plan(auth.tenant_id, p.name, p.uf, p.clp, p.features)
    return {"ok": True, "plan_id": pid}

class AssignIn(BaseModel):
    plan_id: str

@router.post("/assign")
def assign(p: AssignIn, auth: Authed = Depends(auth_required)):
    set_tenant_plan(auth.tenant_id, p.plan_id)
    return {"ok": True}

class LimitIn(BaseModel):
    plan_id: str
    key: str
    value: int

@router.post("/limits")
def limit_set(p: LimitIn, auth: Authed = Depends(auth_required)):
    upsert_limit(p.plan_id, p.key, p.value)
    return {"ok": True}

@router.get("/limits/{plan_id}")
def limits_get(plan_id: str, auth: Authed = Depends(auth_required)):
    return get_plan_limits(plan_id)
