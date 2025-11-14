# app/api/v1/tenants_profile.py
from fastapi import APIRouter, Depends, HTTPException
from core.auth import auth_required, Authed
from core.db import get_conn

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])

@router.get("/{tenant_id}/profile")
def tenant_profile(tenant_id: str, auth: Authed = Depends(auth_required)):
    # cualquier miembro del tenant puede ver
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, name, domain, timezone, locale,
                   COALESCE(description,''), COALESCE(website,''), COALESCE(industry,''), COALESCE(logo_url,'')
            FROM tenants
            WHERE id=%s
            """, (tenant_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "tenant not found")
    return {
        "id": row[0],            # slug si usas id como slug
        "name": row[1],
        "domain": row[2],
        "timezone": row[3],
        "locale": row[4],
        "description": row[5],
        "website": row[6],
        "industry": row[7],
        "logo_url": row[8],
    }
