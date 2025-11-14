# app/api/v1/admin_tenant_logo.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core.auth import auth_required, Authed
from core.s3 import s3_client
from core.db import get_conn
from core.config import settings
from urllib.parse import quote
import os

router = APIRouter(prefix="/api/v1/admin/tenants", tags=["admin"])

class LogoReq(BaseModel):
    content_type: str = "image/png"  # o "image/jpeg"

@router.put("/{tenant_id}/logo")
def tenant_logo_presign(tenant_id: str, body: LogoReq, auth: Authed = Depends(auth_required)):
    # Requiere rol admin/manager del tenant si lo deseas (opcional)
    bucket = os.getenv("DO_BUCKET") or getattr(settings, "DO_BUCKET", None)
    if not bucket:
        raise HTTPException(500, "bucket not configured")

    # 🔧 KEY CORRECTA (sin prefijo 'tenants/'):
    # any-ai/{tenant_id}/branding/logo.png
    key = f"{tenant_id}/branding/logo.png"

    s3 = s3_client()

    # URL firmada tipo PUT (single-part) + ACL pública
    try:
        upload_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ContentType": body.content_type,
                "ACL": "public-read",
            },
            ExpiresIn=600,  # 10min
        )
    except Exception as e:
        raise HTTPException(500, f"Failed to presign: {e}")

    # Base pública (CDN si configuraste SPACES_PUBLIC_BASE; si no, origin)
    base_public = getattr(settings, "SPACES_PUBLIC_BASE", None) \
                  or f"https://{bucket}.{getattr(settings, 'DO_SPACES_ENDPOINT', 'sfo3.digitaloceanspaces.com')}"
    public_url = f"{base_public}/{quote(key)}"

    # Guarda optimista en BD
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE tenants SET logo_url=%s, updated_at=now() WHERE id=%s",
            (public_url, tenant_id),
        )
        conn.commit()

    # 🔧 Devuelve headers para que el front los use TAL CUAL
    return {
        "upload_url": upload_url,
        "public_url": public_url,
        "key": key,
        "headers": {
            "Content-Type": body.content_type,
            "x-amz-acl": "public-read",
        },
    }
