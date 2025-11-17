"""
Tenant logo upload endpoints.

Follows Layer 2 and Layer 4 rules:
- Settings write → min role admin
- Tenant isolation enforced (only update own tenant)
- All configuration from centralized settings
"""
from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from core.auth import auth_required, Authed
from core.s3 import s3_client
from core.db import get_conn
from core.config import settings
from core.roles import require_min_role
from core.errors import http_error, ErrorCode
from urllib.parse import quote

router = APIRouter(prefix="/api/v1/admin/tenants", tags=["admin"])


class LogoReq(BaseModel):
    """Request schema for logo upload."""
    content_type: str = Field(default="image/png", description="Content type (image/png or image/jpeg)")


class LogoPresignOut(BaseModel):
    """Response schema for logo presign."""
    upload_url: str
    public_url: str
    key: str
    headers: dict


@router.put("/{tenant_id}/logo", response_model=LogoPresignOut)
def tenant_logo_presign(
    tenant_id: str,
    body: LogoReq,
    auth: Authed = Depends(require_min_role("admin")),
) -> dict:
    """
    Generate presigned URL for tenant logo upload.
    
    Follows Layer 2 and Layer 4 rules:
    - Settings write → min role admin
    - Tenant isolation enforced (only update own tenant)
    
    Args:
        tenant_id: Tenant identifier (must match auth.tenant_id)
        body: Logo upload request
        auth: Authenticated user context (min role: admin)
    
    Returns:
        Dict with presigned URL and metadata
    
    Raises:
        HTTPException: 403 if tenant mismatch, 500 for S3 errors
    """
    # Enforce tenant isolation
    if tenant_id != auth.tenant_id:
        raise http_error(
            status_code=403,
            code=ErrorCode.FORBIDDEN,
            message="You can only update your own tenant logo",
        )
    
    if not settings.DO_BUCKET:
        raise http_error(
            status_code=500,
            code=ErrorCode.INTERNAL_ERROR,
            message="S3 bucket not configured",
        )

    # Key format: {tenant_id}/branding/logo.png
    key = f"{tenant_id}/branding/logo.png"

    s3 = s3_client()

    # Generate presigned PUT URL with public-read ACL
    try:
        upload_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.DO_BUCKET,
                "Key": key,
                "ContentType": body.content_type,
                "ACL": "public-read",
            },
            ExpiresIn=600,  # 10 minutes
        )
    except Exception as e:
        raise http_error(
            status_code=500,
            code=ErrorCode.INTERNAL_ERROR,
            message="Failed to generate presigned URL",
        )

    # Public base URL (CDN if SPACES_PUBLIC_BASE configured, otherwise origin)
    base_public = settings.SPACES_PUBLIC_BASE or f"https://{settings.DO_BUCKET}.{settings.DO_SPACES_ENDPOINT or 'sfo3.digitaloceanspaces.com'}"
    public_url = f"{base_public}/{quote(key)}"

    # Optimistically save to database
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE tenants SET logo_url=%s, updated_at=now() WHERE id=%s",
            (public_url, tenant_id),
        )
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
