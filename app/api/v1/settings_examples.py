"""
Example Settings endpoints demonstrating RBAC usage.

This file shows how to use require_min_role and require_roles
for different types of Settings operations.

Follows Layer 2 rules:
- Settings read → min role observer
- Settings write → min role admin
- Destructive actions → role owner
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from core.auth import auth_required, Authed
from core.roles import require_min_role, require_roles
from core.errors import http_error, ErrorCode
from core.db import get_conn

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


# ============================================================================
# Example 1: GET Settings (Read) - requires observer role
# ============================================================================

@router.get("/profile")
def get_settings_profile(auth: Authed = Depends(require_min_role("observer"))) -> dict:
    """
    Get tenant settings profile.
    
    Follows Layer 2: Settings read → min role observer
    
    All authenticated users with observer role or higher can read settings.
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, name, domain, timezone, locale, description, website, industry, logo_url
            FROM tenants
            WHERE id = %s
        """, (auth.tenant_id,))
        row = cur.fetchone()
        if not row:
            raise http_error(
                status_code=404,
                code=ErrorCode.NOT_FOUND,
                message="Tenant not found",
            )
    
    return {
        "id": row[0],
        "name": row[1],
        "domain": row[2],
        "timezone": row[3],
        "locale": row[4],
        "description": row[5],
        "website": row[6],
        "industry": row[7],
        "logo_url": row[8],
    }


# ============================================================================
# Example 2: PUT/POST Settings (Write) - requires admin role
# ============================================================================

class SettingsUpdate(BaseModel):
    """Request schema for settings update."""
    name: str | None = Field(default=None, description="Tenant name")
    description: str | None = Field(default=None, description="Tenant description")
    website: str | None = Field(default=None, description="Website URL")
    industry: str | None = Field(default=None, description="Industry")


@router.put("/profile")
def update_settings_profile(
    settings: SettingsUpdate,
    auth: Authed = Depends(require_min_role("admin")),
) -> dict:
    """
    Update tenant settings profile.
    
    Follows Layer 2: Settings write → min role admin
    
    Only users with admin or owner role can modify settings.
    """
    updates = []
    values = []
    
    if settings.name is not None:
        updates.append("name = %s")
        values.append(settings.name)
    if settings.description is not None:
        updates.append("description = %s")
        values.append(settings.description)
    if settings.website is not None:
        updates.append("website = %s")
        values.append(settings.website)
    if settings.industry is not None:
        updates.append("industry = %s")
        values.append(settings.industry)
    
    if not updates:
        raise http_error(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="No fields to update",
        )
    
    updates.append("updated_at = now()")
    values.append(auth.tenant_id)
    
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"UPDATE tenants SET {', '.join(updates)} WHERE id = %s",
            tuple(values)
        )
        if cur.rowcount == 0:
            raise http_error(
                status_code=404,
                code=ErrorCode.NOT_FOUND,
                message="Tenant not found",
            )
        conn.commit()
    
    return {"ok": True, "message": "Settings updated successfully"}


# ============================================================================
# Example 3: DELETE Organization (Destructive) - requires owner role
# ============================================================================

@router.delete("/organization")
def delete_organization(
    auth: Authed = Depends(require_roles("owner")),
) -> dict:
    """
    Delete the entire organization/tenant.
    
    Follows Layer 2: Destructive actions → role owner
    
    Only users with owner role can delete the organization.
    This is a critical operation that should be protected.
    """
    # Verify this is the owner's own tenant (extra safety check)
    with get_conn() as conn, conn.cursor() as cur:
        # Check if user is actually owner of this tenant
        cur.execute("""
            SELECT ut.user_id, r.name
            FROM user_tenants ut
            JOIN roles r ON r.id = ut.role_id
            WHERE ut.user_id = %s AND ut.tenant_id = %s AND r.name = 'owner'
        """, (auth.user_id, auth.tenant_id))
        if not cur.fetchone():
            raise http_error(
                status_code=403,
                code=ErrorCode.FORBIDDEN,
                message="Only organization owner can delete the organization",
            )
        
        # Delete tenant (cascade will handle user_tenants, etc.)
        cur.execute("DELETE FROM tenants WHERE id = %s", (auth.tenant_id,))
        if cur.rowcount == 0:
            raise http_error(
                status_code=404,
                code=ErrorCode.NOT_FOUND,
                message="Tenant not found",
            )
        conn.commit()
    
    return {"ok": True, "message": "Organization deleted successfully"}


# ============================================================================
# Example 4: GET Channels (Read) - requires observer role
# ============================================================================

@router.get("/channels")
def list_channels(
    auth: Authed = Depends(require_min_role("observer")),
) -> dict:
    """
    List all channels/integrations for the tenant.
    
    Follows Layer 2: Settings read → min role observer
    """
    # Example: Return channels from database
    # In real implementation, query channels table filtered by tenant_id
    return {
        "channels": [
            {"id": "whatsapp", "name": "WhatsApp", "enabled": True},
            {"id": "telegram", "name": "Telegram", "enabled": False},
        ]
    }


# ============================================================================
# Example 5: POST Channels (Write) - requires admin role
# ============================================================================

class ChannelConfig(BaseModel):
    """Request schema for channel configuration."""
    channel_type: str = Field(..., description="Channel type (whatsapp, telegram, etc.)")
    enabled: bool = Field(default=True, description="Whether channel is enabled")
    config: dict = Field(default_factory=dict, description="Channel-specific configuration")


@router.post("/channels")
def configure_channel(
    channel: ChannelConfig,
    auth: Authed = Depends(require_min_role("admin")),
) -> dict:
    """
    Configure a channel/integration for the tenant.
    
    Follows Layer 2: Settings write → min role admin
    
    Only admin or owner can configure channels.
    """
    # Example: Save channel configuration to database
    # In real implementation, upsert into channels table with tenant_id
    return {
        "ok": True,
        "message": f"Channel {channel.channel_type} configured successfully",
        "channel": channel.model_dump(),
    }


# ============================================================================
# Example 6: Using require_roles for specific role combinations
# ============================================================================

@router.get("/billing")
def get_billing_info(
    auth: Authed = Depends(require_roles("owner", "admin")),
) -> dict:
    """
    Get billing information.
    
    Only owner and admin can view billing details.
    Uses require_roles for specific role list (not hierarchy).
    """
    # Example: Return billing information
    return {
        "plan": "pro",
        "monthly_cost": 99.00,
        "next_billing_date": "2024-02-01",
    }


@router.post("/billing/upgrade")
def upgrade_plan(
    plan_name: str,
    auth: Authed = Depends(require_roles("owner", "admin")),
) -> dict:
    """
    Upgrade billing plan.
    
    Only owner and admin can upgrade plans.
    """
    # Example: Process plan upgrade
    return {
        "ok": True,
        "message": f"Plan upgraded to {plan_name}",
        "new_plan": plan_name,
    }

