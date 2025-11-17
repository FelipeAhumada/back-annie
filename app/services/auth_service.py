"""
Authentication service for user login and tenant switching.

Follows Layer 1 and Layer 6 rules:
- Validates credentials securely
- Returns minimal information on failure (no "user not found vs wrong password" distinction)
- Logs security events (login attempts)
- NEVER logs plaintext passwords or hashes
"""
from __future__ import annotations
from core.db import get_conn
from core.auth import sign_jwt
from core.errors import http_error, ErrorCode
from core.logger import log_security_event
import bcrypt


def _to_bytes(x):
    """Convert input to bytes for bcrypt."""
    if x is None:
        return b""
    if isinstance(x, (bytes, bytearray)):
        return bytes(x)
    return str(x).encode()


def _fetch_user_by_email(cur, email: str):
    """
    Fetch user by email from database.
    
    Args:
        cur: Database cursor
        email: User email address
    
    Returns:
        Tuple of (user_id, password_hash, is_active) or None
    """
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


def _fetch_user_tenants(cur, user_id: str):
    """
    Fetch all tenants associated with a user.
    
    Args:
        cur: Database cursor
        user_id: User identifier
    
    Returns:
        List of tuples (tenant_id, tenant_name, role)
    """
    cur.execute("""
        SELECT t.id AS tenant_id, t.name, r.name AS role
        FROM user_tenants ut
        JOIN tenants t ON t.id = ut.tenant_id
        JOIN roles   r ON r.id = ut.role_id
        WHERE ut.user_id = %s
        ORDER BY t.name
    """, (user_id,))
    return cur.fetchall()


def login_issue_token(
    email: str,
    password: str,
    user_agent: str | None,
    ip: str | None
) -> dict:
    """
    Authenticate user and issue JWT token.
    
    Follows Layer 1 rules:
    - Returns minimal information on failure (no "user not found vs wrong password" distinction)
    - Logs security events for audit
    
    Args:
        email: User email address
        password: Plaintext password (will be hashed and compared)
        user_agent: HTTP User-Agent header (optional, for logging)
        ip: Client IP address (optional, for logging)
    
    Returns:
        Dict with token, current_tenant, and tenants list
    
    Raises:
        HTTPException: 401 for invalid credentials, 403 for disabled user or no tenants
    """
    with get_conn() as conn, conn.cursor() as cur:
        ur = _fetch_user_by_email(cur, email)
        if not ur:
            # Log failed login attempt (no user found)
            log_security_event(
                action="login",
                result="failure",
                meta={"reason": "user_not_found", "email": email}
            )
            raise http_error(
                status_code=401,
                code=ErrorCode.UNAUTHORIZED,
                message="Invalid credentials",
            )

        user_id, pwd_hash, is_active = ur
        if not is_active:
            log_security_event(
                action="login",
                result="failure",
                user_id=str(user_id),
                meta={"reason": "user_disabled", "email": email}
            )
            raise http_error(
                status_code=403,
                code=ErrorCode.FORBIDDEN,
                message="Invalid credentials",
            )

        if not bcrypt.checkpw(_to_bytes(password), _to_bytes(pwd_hash)):
            log_security_event(
                action="login",
                result="failure",
                user_id=str(user_id),
                meta={"reason": "invalid_password", "email": email}
            )
            raise http_error(
                status_code=401,
                code=ErrorCode.UNAUTHORIZED,
                message="Invalid credentials",
            )

        rows = _fetch_user_tenants(cur, user_id)
        if not rows:
            log_security_event(
                action="login",
                result="failure",
                user_id=str(user_id),
                meta={"reason": "no_tenants", "email": email}
            )
            raise http_error(
                status_code=403,
                code=ErrorCode.FORBIDDEN,
                message="Invalid credentials",
            )

        # Token with the FIRST tenant as default
        default_tenant_id, default_tenant_name, default_role = rows[0]
        token = sign_jwt(str(user_id), default_tenant_id, default_role)

        tenants = [{"tenant_id": r[0], "tenant_name": r[1], "role": r[2]} for r in rows]
        
        # Log successful login
        log_security_event(
            action="login",
            result="success",
            user_id=str(user_id),
            tenant_id=default_tenant_id,
            meta={"role": default_role}
        )
        
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
    """
    Switch user's active tenant and issue new token.
    
    Verifies that the user belongs to the target tenant before issuing token.
    
    Args:
        user_id: User identifier
        target_tenant_id: Target tenant identifier
    
    Returns:
        Dict with new token, tenant_id, and role
    
    Raises:
        HTTPException: 403 if user is not in target tenant
    """
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
            raise http_error(
                status_code=403,
                code=ErrorCode.FORBIDDEN,
                message="User not in target tenant",
            )
        role_name = rr[0]
    
    # Log tenant switch
    log_security_event(
        action="tenant_switch",
        result="success",
        user_id=str(user_id),
        tenant_id=target_tenant_id,
        meta={"role": role_name}
    )
    
    return {
        "token": sign_jwt(user_id, target_tenant_id, role_name),
        "tenant_id": target_tenant_id,
        "role": role_name
    }
