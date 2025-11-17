"""
Service layer for Settings operations.

Follows Layer 4 rules:
- Data access MUST be routed through repository/service layers
- Keep clean separation: API → service → repository → DB
"""
from __future__ import annotations
from typing import Optional
from repositories.general_settings_repo import get_general_settings, upsert_general_settings
from schemas.settings import GeneralSettingsUpdate, GeneralSettingsRead


def get_settings(tenant_id: str) -> GeneralSettingsRead:
    """
    Get general settings for a tenant.
    
    Returns default values if no settings exist yet.
    
    Args:
        tenant_id: Tenant identifier
    
    Returns:
        GeneralSettingsRead with settings or defaults
    """
    data = get_general_settings(tenant_id)
    
    if not data:
        # Return defaults (lazy creation on first update)
        return GeneralSettingsRead(
            tenant_id=tenant_id,
            name="",
            logo_url=None,
            website_url=None,
            short_description=None,
            mission=None,
            vision=None,
            purpose=None,
            customer_problems=None,
            created_at="",
            updated_at="",
        )
    
    return GeneralSettingsRead(**data)


def update_settings(tenant_id: str, data: GeneralSettingsUpdate) -> GeneralSettingsRead:
    """
    Update general settings for a tenant.
    
    Creates record if it doesn't exist.
    
    Args:
        tenant_id: Tenant identifier
        data: Settings update data
    
    Returns:
        Updated GeneralSettingsRead
    """
    # Convert Pydantic model to dict, excluding None values for partial updates
    update_dict = data.model_dump(exclude_unset=True)
    
    # Ensure name is set (required field)
    if "name" not in update_dict or not update_dict["name"]:
        existing = get_general_settings(tenant_id)
        if existing and existing.get("name"):
            update_dict["name"] = existing["name"]
        else:
            update_dict["name"] = "Unnamed Organization"
    
    result = upsert_general_settings(tenant_id, update_dict)
    return GeneralSettingsRead(**result)

