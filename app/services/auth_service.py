# app/services/auth_service.py
from fastapi import HTTPException
from core.db import get_conn
from core.auth import sign_jwt
import bcrypt

def _to_bytes(x):
    if x is None:
        return b""
    if isinstance(x, (bytes, bytearray)):
        return bytes(x)
    return str(x).encode()

def _fetch_user_by_email(cur, email: str):
    # Schema Annie: users(email, password_hash, is_active, ...)
    cur.execute(
        """
        SELECT id, password_hash, is_active
        FROM users
        WHERE email = %s
        LIMIT 1
        """,
        (email,)
    )
    return cur.fetchone()

def _fetch_user_tenants(cur, user_id):
    cur.execute("""
        SELECT t.id AS tenant_id, t.name, r.name AS role
        FROM user_tenants ut
        JOIN tenants t ON t.id = ut.tenant_id
        JOIN roles   r ON r.id = ut.role_id
        WHERE ut.user_id = %s
        ORDER BY t.name
    """, (user_id,))
    return cur.fetchall()

def login_issue_token(email: str, password: str, user_agent: str | None, ip: str | None):
    with get_conn() as conn, conn.cursor() as cur:
        ur = _fetch_user_by_email(cur, email)
        if not ur:
            raise HTTPException(401, "Invalid credentials")

        user_id, pwd_hash, is_active = ur
        if not is_active:
            raise HTTPException(403, "User disabled")

        if not bcrypt.checkpw(_to_bytes(password), _to_bytes(pwd_hash)):
            raise HTTPException(401, "Invalid credentials")

        rows = _fetch_user_tenants(cur, user_id)
        if not rows:
            raise HTTPException(403, "User has no tenants")

        # token con el PRIMER tenant por defecto
        default_tenant_id, default_tenant_name, default_role = rows[0]
        token = sign_jwt(str(user_id), default_tenant_id, default_role)

        tenants = [{"tenant_id": r[0], "tenant_name": r[1], "role": r[2]} for r in rows]
        return {
            "ok": True,
            "token": token,
            "current_tenant": {
                "tenant_id": default_tenant_id,
                "tenant_name": default_tenant_name,
                "role": default_role
            },
            "tenants": tenants
        }

def switch_tenant(user_id: str, target_tenant_id: str) -> dict:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT r.name
            FROM user_tenants ut
            JOIN roles r ON r.id = ut.role_id
            WHERE ut.user_id = %s AND ut.tenant_id = %s
            LIMIT 1
        """, (user_id, target_tenant_id))
        rr = cur.fetchone()
        if not rr:
            raise HTTPException(403, "User not in target tenant")
        role_name = rr[0]
    return {
        "token": sign_jwt(user_id, target_tenant_id, role_name),
        "tenant_id": target_tenant_id,
        "role": role_name
    }
