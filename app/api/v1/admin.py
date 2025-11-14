# app/api/v1/admin.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from core.auth import auth_required, Authed
from core.db import get_conn
from core.roles import require_roles
from core.s3 import s3_client
from core.config import settings
from urllib.parse import quote
import json
import os

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# =========================
# Tenants
# =========================
class TenantUpsert(BaseModel):
    id: str
    name: str
    domain: str
    timezone: str = "America/Santiago"
    locale: str = "es-CL"
    description: str | None = None
    website: str | None = None
    industry: str | None = None
    logo_url: str | None = None

@router.post("/tenants")
def upsert_tenant(t: TenantUpsert, auth: Authed = Depends(auth_required)):
    require_roles("admin")(auth)
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
    return {"ok": True, "tenant_id": tid}

# =========================
# Users + membership
# =========================
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    tenant_id: str
    role: str = "admin"  # admin | manager | agent | viewer

@router.post("/users")
def create_user(u: UserCreate, auth: Authed = Depends(auth_required)):
    require_roles("admin", "manager")(auth)
    from core.security import hash_password
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM roles WHERE name = %s", (u.role,))
        rrow = cur.fetchone()
        if not rrow:
            raise HTTPException(status_code=400, detail=f"Invalid role '{u.role}'")
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
    return {"ok": True}

class UserUpdate(BaseModel):
    user_id: str
    full_name: str | None = None
    is_active: bool | None = None
    country_id: str | None = None
    phone_national: str | None = None
    avatar_url: str | None = None

@router.post("/users/update")
def update_user(p: UserUpdate, auth: Authed = Depends(auth_required)):
    require_roles("admin", "manager")(auth)
    sets, vals = [], []
    if p.full_name is not None:
        sets.append("full_name=%s"); vals.append(p.full_name)
    if p.is_active is not None:
        sets.append("is_active=%s"); vals.append(p.is_active)
    if p.country_id is not None:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM countries WHERE id = %s", (p.country_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=400, detail="Invalid country_id")
        sets.append("country_id=%s"); vals.append(p.country_id)
    if p.phone_national is not None:
        if p.phone_national and not p.phone_national.isdigit():
            raise HTTPException(status_code=400, detail="phone_national must contain only digits")
        sets.append("phone_national=%s"); vals.append(p.phone_national)
    if p.avatar_url is not None:
        sets.append("avatar_url=%s"); vals.append(p.avatar_url)

    if not sets:
        raise HTTPException(status_code=400, detail="Nothing to update")

    vals.append(p.user_id)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(f"UPDATE users SET {', '.join(sets)}, updated_at = now() WHERE id=%s", tuple(vals))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
        conn.commit()
    return {"ok": True}

# =========================
# Avatar - PRESIGN (misma lógica que logo)
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
    content_type: str
    filename: str | None = None  # opcional

class AvatarPresignOut(BaseModel):
    upload_url: str
    public_url: str
    key: str
    headers: dict

@router.put("/users/{user_id}/avatar", response_model=AvatarPresignOut)
def presign_user_avatar(
    user_id: str,
    body: AvatarPresignIn,
    auth: Authed = Depends(auth_required)
):
    require_roles("admin", "manager")(auth)

    tenant_id = auth.tenant_id
    # forzamos a guardar SIEMPRE como .../users/logo.<ext> (sin user_id en la ruta)
    ext = _CT_TO_EXT.get((body.content_type or "").lower(), "png")
    key = f"{tenant_id}/users/logo.{ext}"

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
        raise HTTPException(status_code=500, detail=f"Failed to presign: {e}")

    base_public = getattr(settings, "SPACES_PUBLIC_BASE", None) or f"https://{bucket}.{settings.DO_SPACES_ENDPOINT}"
    public_url = f"{base_public}/{quote(key)}"

    # Aquí NO escribimos en BD. El front sube y luego hace POST /api/v1/admin/users/update con avatar_url.
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
# Pricing plans
# =========================
class PlanUpsert(BaseModel):
    tenant_id: str
    name: str
    uf: float | None = None
    clp: int | None = None
    features: list = Field(default_factory=list)

@router.post("/plans")
def upsert_plan(p: PlanUpsert, auth: Authed = Depends(auth_required)):
    require_roles("admin")(auth)
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
    return {"ok": True, "plan_id": pid}

class AvatarPresignIn(BaseModel):
    filename: str
    content_type: str

@router.put("/users/{user_id}/avatar")
def presign_user_avatar(user_id: str, body: AvatarPresignIn, auth: Authed = Depends(auth_required)):
    # Solo admin/manager (o permite self-update si quieres)
    from core.roles import require_roles
    require_roles("admin", "manager")(auth)

    bucket = os.getenv("DO_BUCKET") or getattr(settings, "DO_BUCKET", None)
    if not bucket:
        raise HTTPException(status_code=500, detail="bucket not configured")

    tenant_id = auth.tenant_id

    # Validación de extensión/MIME
    _, ext = os.path.splitext(body.filename or "")
    ext = (ext or "").lower().strip(".")
    if ext not in {"png", "jpg", "jpeg", "webp"}:
        raise HTTPException(status_code=400, detail="Invalid file extension")

    # 🔧 KEY pedida: any-ai/{tenant_id}/users/logo.ext
    key = f"{tenant_id}/users/logo.{ext}"

    s3 = s3_client()

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
        raise HTTPException(status_code=500, detail=f"Failed to presign: {e}")

    base_public = getattr(settings, "SPACES_PUBLIC_BASE", None) \
                  or f"https://{bucket}.{getattr(settings, 'DO_SPACES_ENDPOINT', 'sfo3.digitaloceanspaces.com')}"
    public_url = f"{base_public}/{quote(key)}"

    # Guarda en BD (optimista)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET avatar_url=%s, updated_at=now() WHERE id=%s", (public_url, user_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
        conn.commit()

    return {
        "upload_url": upload_url,
        "public_url": public_url,
        "key": key,
        "headers": {
            "Content-Type": body.content_type,
            "x-amz-acl": "public-read",
        },
    }
