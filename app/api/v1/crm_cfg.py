"""
CRM configuration endpoints (hours, availability).

Follows Layer 2 and Layer 4 rules:
- Settings read → min role observer
- Settings write → min role admin
- All queries MUST be tenant-scoped
"""
from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from core.auth import auth_required, Authed
from core.roles import require_min_role
from repositories.crm_repo import get_hours, set_hours, get_availability, set_availability

router = APIRouter(prefix="/api/v1/crm", tags=["crm-config"])


class HourItem(BaseModel):
    """Schema for business hours item."""
    day: int = Field(..., ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    open: str = Field(..., description="Opening time (HH:MM format)")
    close: str = Field(..., description="Closing time (HH:MM format)")


class SlotItem(BaseModel):
    """Schema for availability slot."""
    start: str = Field(..., description="Start time (HH:MM format)")
    end: str = Field(..., description="End time (HH:MM format)")
    bookable: bool = Field(default=True, description="Whether slot is bookable")


@router.get("/hours")
def hours_get(auth: Authed = Depends(require_min_role("observer"))) -> dict:
    """
    Get business hours for the tenant.
    
    Follows Layer 2 rules:
    - Settings read → min role observer
    - Tenant isolation enforced via auth.tenant_id
    
    Args:
        auth: Authenticated user context (min role: observer)
    
    Returns:
        Dict with hours list
    """
    return {"hours": get_hours(auth.tenant_id)}


@router.post("/hours")
def hours_set(
    items: list[HourItem],
    auth: Authed = Depends(require_min_role("admin")),
) -> dict:
    """
    Update business hours for the tenant.
    
    Follows Layer 2 rules:
    - Settings write → min role admin
    - Tenant isolation enforced via auth.tenant_id
    
    Args:
        items: List of hour items
        auth: Authenticated user context (min role: admin)
    
    Returns:
        Dict with success status
    """
    set_hours(auth.tenant_id, [i.model_dump() for i in items])
    return {"ok": True}


@router.get("/availability")
def availability_get(auth: Authed = Depends(require_min_role("observer"))) -> dict:
    """
    Get availability slots for the tenant.
    
    Follows Layer 2 rules:
    - Settings read → min role observer
    - Tenant isolation enforced via auth.tenant_id
    
    Args:
        auth: Authenticated user context (min role: observer)
    
    Returns:
        Dict with slots list
    """
    return {"slots": get_availability(auth.tenant_id)}


@router.post("/availability")
def availability_set(
    slots: list[SlotItem],
    auth: Authed = Depends(require_min_role("admin")),
) -> dict:
    """
    Update availability slots for the tenant.
    
    Follows Layer 2 rules:
    - Settings write → min role admin
    - Tenant isolation enforced via auth.tenant_id
    
    Args:
        slots: List of slot items
        auth: Authenticated user context (min role: admin)
    
    Returns:
        Dict with success status
    """
    set_availability(auth.tenant_id, [s.model_dump() for s in slots])
    return {"ok": True}

