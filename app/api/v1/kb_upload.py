# app/api/v1/kb_upload.py
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from core.auth import auth_required, Authed
from services.kb_services import (
    presign_upload, sign_part, complete_multipart, commit_file
)

router = APIRouter(prefix="/api/v1/kb/files", tags=["kb"])

class PresignIn(BaseModel):
    filename: str
    size_bytes: int
    mime_type: str | None = None

@router.post("/presign")
def api_presign(body: PresignIn, auth: Authed = Depends(auth_required)):
    return presign_upload(auth.tenant_id, body.filename, body.size_bytes, body.mime_type)

@router.get("/sign-part")
def api_sign_part(
    key: str = Query(..., alias="key"),
    upload_id: str = Query(..., alias="upload_id"),
    n: int = Query(..., alias="part_number"),
    content_length: int | None = Query(None, alias="content_length"),
    auth: Authed = Depends(auth_required),
):
    if not key.startswith(f"tenants/{auth.tenant_id}/"):
        # evita fuga de keys de otros tenants
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="key fuera del tenant")
    return sign_part(key, upload_id, n, content_length)

class CompleteIn(BaseModel):
    storage_key: str
    upload_id: str
    parts: list[dict]  # [{"ETag": "...", "PartNumber": 1}, ...]

@router.post("/complete")
def api_complete(body: CompleteIn, auth: Authed = Depends(auth_required)):
    if not body.storage_key.startswith(f"tenants/{auth.tenant_id}/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="storage_key fuera del tenant")
    return complete_multipart(body.storage_key, body.upload_id, body.parts)

class CommitIn(BaseModel):
    file_payload: dict   # lo que devolvió presign/complete (incluye storage_key, etc.)
    title: str | None = None
    lang: str = "es"
    source: str = "upload"

@router.post("/commit")
def api_commit(body: CommitIn, auth: Authed = Depends(auth_required)):
    return commit_file(auth.tenant_id, body.file_payload, body.title, body.lang, body.source)
