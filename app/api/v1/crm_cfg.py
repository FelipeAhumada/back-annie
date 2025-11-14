# app/api/v1/crm_cfg.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.auth import auth_required, Authed
from repositories.crm_repo import get_hours, set_hours, get_availability, set_availability

router = APIRouter(prefix="/api/v1/crm", tags=["crm-config"])

@router.get("/hours")
def hours_get(auth: Authed = Depends(auth_required)):
    return {"hours": get_hours(auth.tenant_id)}

class HourItem(BaseModel):
    day: int
    open: str
    close: str

@router.post("/hours")
def hours_set(items: list[HourItem], auth: Authed = Depends(auth_required)):
    set_hours(auth.tenant_id, [i.model_dump() for i in items])
    return {"ok": True}

@router.get("/availability")
def availability_get(auth: Authed = Depends(auth_required)):
    return {"slots": get_availability(auth.tenant_id)}

class SlotItem(BaseModel):
    start: str
    end: str
    bookable: bool = True

@router.post("/availability")
def availability_set(slots: list[SlotItem], auth: Authed = Depends(auth_required)):
    set_availability(auth.tenant_id, [s.model_dump() for s in slots])
    return {"ok": True}
