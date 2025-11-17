"""
Admin endpoints for Settings module (Tenant, Users, Teams, Plans).

Follows Layer 2, Layer 3, and Layer 4 rules:
- Settings write → min role admin
- Destructive actions (delete org, billing critical ops) → role owner
- All queries MUST be tenant-scoped
- ALWAYS use Pydantic models for request/response
- Never allow cross-tenant access
"""
from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from core.auth import auth_required, Authed
from core.db import get_conn
from core.roles import require_min_role, require_roles
from core.errors import http_error, ErrorCode
from core.s3 import s3_client
from core.config import settings
from core.security import hash_password
from core.logger import log_security_event
from urllib.parse import quote
import json

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# =========================
# Tenants
# =========================

class TenantUpsert(BaseModel):
    """Request schema for tenant upsert."""
    id: str = Field(..., description="Tenant identifier")
    name: str = Field(..., description="Tenant name")
    domain: str = Field(..., description="Tenant domain")
    timezone: str = Field(default="America/Santiago", description="Timezone")
    locale: str = Field(default="es-CL", description="Locale")
    description: str | None = Field(default=None, description="Tenant description")
    website: str | None = Field(default=None, description="Website URL")
    industry: str | None = Field(default=None, description="Industry")
    logo_url: str | None = Field(default=None, description="Logo URL")


@router.post("/tenants")
def upsert_tenant(
    t: TenantUpsert,
    auth: Authed = Depends(require_min_role("admin")),
) -> dict:
    """
    Create or update tenant profile.
    
    Follows Layer 2 and Layer 4 rules:
    - Settings write → min role admin
    - Tenant isolation enforced (only update own tenant)
    
    Args:
        t: Tenant data
        auth: Authenticated user context (min role: admin)
    
    Returns:
        Dict with success status and tenant_id
    
    Raises:
        HTTPException: 403 if trying to update different tenant
    """
    # Enforce tenant isolation - only allow updating own tenant
    if t.id != auth.tenant_id:
        raise http_error(
            status_code=403,
            code=ErrorCode.FORBIDDEN,
            message="You can only update your own tenant",
        )
    
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO tenants (id,name,domain,timezone,locale,description,website,industry,logo_url,updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
            ON CONFLICT (id) DO UPDATE
            SET name=EXCLUDED.name,
                domain=EXCLUDED.domain,
                timezone=EXCLUDED.timezone,
                locale=EXCLUDED.locale,
                description=EXCLUDED.description,
                website=EXCLUDED.website,
                industry=EXCLUDED.industry,
                logo_url=EXCLUDED.logo_url,
                updated_at=now()
            RETURNING id
        """, (
            t.id, t.name, t.domain, t.timezone, t.locale,
            t.description, t.website, t.industry, t.logo_url
        ))
        tid = cur.fetchone()[0]
        conn.commit()
    
    log_security_event(
        action="tenant_update",
        result="success",
        user_id=auth.user_id,
        tenant_id=tid,
    )
    
    return {"ok": True, "tenant_id": tid}


# =========================
# Users + membership (Teams)
# =========================

class UserCreate(BaseModel):
    """Request schema for user creation."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")
    full_name: str = Field(..., description="Full name")
    tenant_id: str = Field(..., description="Tenant identifier")
    role: str = Field(default="agent", description="Role: owner | admin | agent | observer")


@router.post("/users")
def create_user(
    u: UserCreate,
    auth: Authed = Depends(require_min_role("admin")),
) -> dict:
    """
    Create user and add to tenant (Teams management).
    
    Follows Layer 2 and Layer 4 rules:
    - Settings write → min role admin
    - Tenant isolation enforced (only add users to own tenant)
    
    Args:
        u: User creation data
        auth: Authenticated user context (min role: admin)
    
    Returns:
        Dict with success status
    
    Raises:
        HTTPException: 400 if role is invalid, 403 if tenant mismatch
    """
    # Enforce tenant isolation
    if u.tenant_id != auth.tenant_id:
        raise http_error(
            status_code=403,
            code=ErrorCode.FORBIDDEN,
            message="You can only add users to your own tenant",
        )
    
    # Validate role
    valid_roles = {"owner", "admin", "agent", "observer"}
    if u.role not in valid_roles:
        raise http_error(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message=f"Invalid role. Must be one of: {sorted(valid_roles)}",
        )
    
    from core.db import get_conn
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM roles WHERE name = %s", (u.role,))
        rrow = cur.fetchone()
        if not rrow:
            raise http_error(
                status_code=400,
                code=ErrorCode.BAD_REQUEST,
                message=f"Invalid role '{u.role}'",
            )
        role_id = rrow[0]

        cur.execute("SELECT id FROM users WHERE email=%s", (u.email,))
        row = cur.fetchone()
        if row:
            user_id = row[0]
        else:
            cur.execute(
                "INSERT INTO users (email,password_hash,full_name,is_active) "
                "VALUES (%s,%s,%s,TRUE) RETURNING id",
                (u.email, hash_password(u.password), u.full_name)
            )
            user_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO user_tenants (user_id, tenant_id, role_id)
            VALUES (%s,%s,%s)
            ON CONFLICT (user_id, tenant_id) DO UPDATE SET role_id=EXCLUDED.role_id
            """,
            (user_id, u.tenant_id, role_id)
        )
        conn.commit()
    
    log_security_event(
        action="user_create",
        result="success",
        user_id=auth.user_id,
        tenant_id=u.tenant_id,
        meta={"created_user_id": str(user_id), "role": u.role}
    )
    
    return {"ok": True}


class UserUpdate(BaseModel):
    """Request schema for user update."""
    user_id: str = Field(..., description="User identifier")
    full_name: str | None = Field(default=None, description="Full name")
    is_active: bool | None = Field(default=None, description="Active status")
    country_id: str | None = Field(default=None, description="Country identifier")
    phone_national: str | None = Field(default=None, description="Phone number (national format)")
    avatar_url: str | None = Field(default=None, description="Avatar URL")


@router.post("/users/update")
def update_user(
    p: UserUpdate,
    auth: Authed = Depends(require_min_role("admin")),
) -> dict:
    """
    Update user information.
    
    Follows Layer 2 and Layer 4 rules:
    - Settings write → min role admin
    - Tenant isolation enforced (only update users in own tenant)
    
    Args:
        p: User update data
        auth: Authenticated user context (min role: admin)
    
    Returns:
        Dict with success status
    
    Raises:
        HTTPException: 400 for validation errors, 404 if user not found, 403 if tenant mismatch
    """
    # Verify user belongs to same tenant
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT ut.tenant_id FROM user_tenants ut
            WHERE ut.user_id = %s AND ut.tenant_id = %s
            LIMIT 1
        """, (p.user_id, auth.tenant_id))
        if not cur.fetchone():
            raise http_error(
                status_code=403,
                code=ErrorCode.FORBIDDEN,
                message="User not found in your tenant",
            )
    
    sets, vals = [], []
    if p.full_name is not None:
        sets.append("full_name=%s")
        vals.append(p.full_name)
    if p.is_active is not None:
        sets.append("is_active=%s")
        vals.append(p.is_active)
    if p.country_id is not None:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM countries WHERE id = %s", (p.country_id,))
            if cur.fetchone() is None:
                raise http_error(
                    status_code=400,
                    code=ErrorCode.BAD_REQUEST,
                    message="Invalid country_id",
                )
        sets.append("country_id=%s")
        vals.append(p.country_id)
    if p.phone_national is not None:
        if p.phone_national and not p.phone_national.isdigit():
            raise http_error(
                status_code=400,
                code=ErrorCode.BAD_REQUEST,
                message="phone_national must contain only digits",
            )
        sets.append("phone_national=%s")
        vals.append(p.phone_national)
    if p.avatar_url is not None:
        sets.append("avatar_url=%s")
        vals.append(p.avatar_url)

    if not sets:
        raise http_error(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Nothing to update",
        )

    vals.append(p.user_id)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(f"UPDATE users SET {', '.join(sets)}, updated_at = now() WHERE id=%s", tuple(vals))
        if cur.rowcount == 0:
            raise http_error(
                status_code=404,
                code=ErrorCode.NOT_FOUND,
                message="User not found",
            )
        conn.commit()
    
    log_security_event(
        action="user_update",
        result="success",
        user_id=auth.user_id,
        tenant_id=auth.tenant_id,
        meta={"updated_user_id": p.user_id}
    )
    
    return {"ok": True}


# =========================
# Avatar - PRESIGN
# =========================
_ALLOWED_AVATAR_EXT = {"png", "jpg", "jpeg", "webp", "gif", "svg"}
_CT_TO_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/svg+xml": "svg",
}


class AvatarPresignIn(BaseModel):
    """Request schema for avatar presign."""
    content_type: str = Field(..., description="Content type (e.g., image/png)")
    filename: str | None = Field(default=None, description="Filename (optional)")


class AvatarPresignOut(BaseModel):
    """Response schema for avatar presign."""
    upload_url: str
    public_url: str
    key: str
    headers: dict


@router.put("/users/{user_id}/avatar", response_model=AvatarPresignOut)
def presign_user_avatar(
    user_id: str,
    body: AvatarPresignIn,
    auth: Authed = Depends(require_min_role("admin")),
) -> dict:
    """
    Generate presigned URL for user avatar upload.
    
    Follows Layer 2 rules:
    - Settings write → min role admin
    - Tenant isolation enforced
    
    Args:
        user_id: User identifier
        body: Avatar upload request
        auth: Authenticated user context (min role: admin)
    
    Returns:
        Dict with presigned URL and metadata
    
    Raises:
        HTTPException: 403 if user not in tenant, 500 for S3 errors
    """
    # Verify user belongs to same tenant
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT ut.tenant_id FROM user_tenants ut
            WHERE ut.user_id = %s AND ut.tenant_id = %s
            LIMIT 1
        """, (user_id, auth.tenant_id))
        if not cur.fetchone():
            raise http_error(
                status_code=403,
                code=ErrorCode.FORBIDDEN,
                message="User not found in your tenant",
            )

    tenant_id = auth.tenant_id
    ext = _CT_TO_EXT.get((body.content_type or "").lower(), "png")
    key = f"{tenant_id}/users/avatar_{user_id}.{ext}"

    s3 = s3_client()
    bucket = settings.DO_BUCKET
    try:
        upload_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ContentType": body.content_type,
                "ACL": "public-read",
            },
            ExpiresIn=600,
        )
    except Exception as e:
        raise http_error(
            status_code=500,
            code=ErrorCode.INTERNAL_ERROR,
            message="Failed to generate presigned URL",
        )

    base_public = getattr(settings, "SPACES_PUBLIC_BASE", None) or f"https://{bucket}.{settings.DO_SPACES_ENDPOINT}"
    public_url = f"{base_public}/{quote(key)}"

    # Note: Frontend should upload and then call POST /api/v1/admin/users/update with avatar_url
    return {
        "upload_url": upload_url,
        "public_url": public_url,
        "key": key,
        "headers": {
            "Content-Type": body.content_type,
            "x-amz-acl": "public-read",
        },
    }


# =========================
# Pricing plans (Billing)
# =========================

class PlanUpsert(BaseModel):
    """Request schema for pricing plan upsert."""
    tenant_id: str = Field(..., description="Tenant identifier")
    name: str = Field(..., description="Plan name")
    uf: float | None = Field(default=None, description="Price in UF")
    clp: int | None = Field(default=None, description="Price in CLP")
    features: list = Field(default_factory=list, description="Plan features")


@router.post("/plans")
def upsert_plan(
    p: PlanUpsert,
    auth: Authed = Depends(require_min_role("admin")),
) -> dict:
    """
    Create or update pricing plan.
    
    Follows Layer 2 and Layer 4 rules:
    - Settings write → min role admin
    - Tenant isolation enforced (only create plans for own tenant)
    
    Args:
        p: Plan data
        auth: Authenticated user context (min role: admin)
    
    Returns:
        Dict with success status and plan_id
    
    Raises:
        HTTPException: 403 if tenant mismatch
    """
    # Enforce tenant isolation
    if p.tenant_id != auth.tenant_id:
        raise http_error(
            status_code=403,
            code=ErrorCode.FORBIDDEN,
            message="You can only create plans for your own tenant",
        )
    
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pricing_plans (tenant_id,name,uf,clp,features)
            VALUES (%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (p.tenant_id, p.name, p.uf, p.clp, json.dumps(p.features))
        )
        pid = cur.fetchone()[0]
        conn.commit()
    
    log_security_event(
        action="plan_create",
        result="success",
        user_id=auth.user_id,
        tenant_id=p.tenant_id,
        meta={"plan_id": str(pid)}
    )
    
    return {"ok": True, "plan_id": pid}
