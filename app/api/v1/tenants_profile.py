"""
Tenant profile endpoints for Settings module.

Follows Layer 2 rules:
- Settings read → min role observer
- Settings write → min role admin
- All queries MUST be tenant-scoped
"""
from __future__ import annotations
from fastapi import APIRouter, Depends
from core.auth import auth_required, Authed
from core.db import get_conn
from core.roles import require_min_role
from core.errors import http_error, ErrorCode

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


@router.get("/{tenant_id}/profile")
def tenant_profile(
    tenant_id: str,
    auth: Authed = Depends(require_min_role("observer")),
) -> dict:
    """
    Get tenant profile information.
    
    Follows Layer 2 rules:
    - Settings read → min role observer
    - Tenant isolation enforced (only access own tenant)
    
    Args:
        tenant_id: Tenant identifier (must match auth.tenant_id)
        auth: Authenticated user context (min role: observer)
    
    Returns:
        Dict with tenant profile information
    
    Raises:
        HTTPException: 403 if tenant_id doesn't match auth, 404 if tenant not found
    """
    # Enforce tenant isolation - prevent cross-tenant access
    if auth.tenant_id != tenant_id:
        raise http_error(
            status_code=403,
            code=ErrorCode.FORBIDDEN,
            message="Access denied to this tenant",
        )
    
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, name, domain, timezone, locale,
                   COALESCE(description,''), COALESCE(website,''), COALESCE(industry,''), COALESCE(logo_url,'')
            FROM tenants
            WHERE id=%s
            """, (tenant_id,))
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
