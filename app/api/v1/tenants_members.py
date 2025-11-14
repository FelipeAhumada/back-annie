# app/api/v1/tenants_members.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from core.auth import auth_required, Authed
from core.db import get_conn

router = APIRouter(prefix="/api/v1", tags=["team"])

@router.get("/tenants/{tenant_id}/members")
def list_members(
    tenant_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    auth: Authed = Depends(auth_required),
):
    # Evitar cross-tenant por token
    if getattr(auth, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wrong tenant in token")

    offset = (page - 1) * size

    sql = """
      SELECT
        u.id                AS user_id,
        u.email             AS email,
        u.full_name         AS full_name,
        r.name              AS role,
        u.country_id        AS country_id,
        c.name              AS country_name,
        c.phone_code        AS country_phone_code,
        c.flag_emoji        AS flag_emoji,
        u.phone_national    AS phone_national,
        u.avatar_url        AS avatar_url
      FROM user_tenants ut
      JOIN users u   ON u.id = ut.user_id
      JOIN roles r   ON r.id = ut.role_id
      LEFT JOIN countries c ON c.id = u.country_id
      WHERE ut.tenant_id = %s
      ORDER BY
        CASE WHEN u.full_name IS NULL OR u.full_name = '' THEN 1 ELSE 0 END,
        lower(u.full_name),
        lower(u.email)
      LIMIT %s OFFSET %s;
    """

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (tenant_id, size, offset))
        rows = cur.fetchall()

    items = []
    for (user_id, email, full_name, role, country_id, country_name,
         country_phone_code, flag_emoji, phone_national, avatar_url) in rows:
        phone_e164 = f"+{country_phone_code}{phone_national}" if country_phone_code and phone_national else None
        items.append({
            "user_id": user_id,
            "email": email,
            "full_name": full_name,
            "role": role,
            "country": {
                "id": country_id,
                "name": country_name,
                "phone_code": country_phone_code,
                "flag_emoji": flag_emoji,
            } if country_id else None,
            "phone": {
                "national": phone_national,
                "e164": phone_e164,
            },
            "avatar_url": avatar_url,
        })

    return {"items": items}
