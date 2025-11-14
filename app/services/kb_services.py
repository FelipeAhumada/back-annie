# app/services/kb_service.py
from datetime import datetime, timedelta, timezone
import uuid
from fastapi import HTTPException
from core.s3 import s3_client
from core.config import settings
from repositories.kb_repo import insert_file_and_doc, search_chunks

MAX_SINGLE = 50 * 1024 * 1024  # 50MB

def _tenant_key(tenant_id: str, filename: str) -> str:
    safe = filename.replace("/", "_").strip()
    uid = str(uuid.uuid4())
    return f"tenants/{tenant_id}/kb/raw/{uid}_{safe}"

def presign_upload(tenant_id: str, filename: str, size_bytes: int, mime_type: str | None):
    """
    Retorna:
      - mode=single + put_url
      - mode=multipart + upload_id  (las parts se firman con sign_part)
    """
    key = _tenant_key(tenant_id, filename)
    s3 = s3_client()
    expires = 3600
    expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=expires)

    if size_bytes <= MAX_SINGLE:
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.DO_BUCKET,
                "Key": key,
                "ContentType": mime_type or "application/octet-stream",
            },
            ExpiresIn=expires,
            HttpMethod="PUT",
        )
        return {
            "mode": "single",
            "storage_key": key,
            "put_url": url,
            "expires_at": expires_at.isoformat(),
        }

    # Multipart
    create = s3.create_multipart_upload(
        Bucket=settings.DO_BUCKET,
        Key=key,
        ContentType=mime_type or "application/octet-stream",
    )
    upload_id = create["UploadId"]
    # Configura el tamaño de parte en el front (10MB recomendado)
    return {
        "mode": "multipart",
        "storage_key": key,
        "expires_at": expires_at.isoformat(),
        "multipart": {
            "upload_id": upload_id,
            "part_size": 10 * 1024 * 1024,
        },
    }

def sign_part(storage_key: str, upload_id: str, part_number: int, content_length: int | None = None):
    """
    Devuelve URL firmada para subir una parte (PUT).
    """
    if part_number < 1:
        raise HTTPException(400, "part_number debe ser >= 1")

    s3 = s3_client()
    params = {
        "Bucket": settings.DO_BUCKET,
        "Key": storage_key,
        "UploadId": upload_id,
        "PartNumber": part_number,
    }
    # Nota: S3 ignora ContentLength en el presign; el front manda el header real.
    url = s3.generate_presigned_url(
        ClientMethod="upload_part",
        Params=params,
        ExpiresIn=3600,
        HttpMethod="PUT",
    )
    return {"put_url": url}

def complete_multipart(storage_key: str, upload_id: str, parts: list[dict]):
    """
    parts: [{ "ETag": "...", "PartNumber": n }, ...] en orden ascendente.
    """
    if not parts:
        raise HTTPException(400, "parts vacío")

    s3 = s3_client()
    out = s3.complete_multipart_upload(
        Bucket=settings.DO_BUCKET,
        Key=storage_key,
        UploadId=upload_id,
        MultipartUpload={"Parts": parts},
    )
    # out: {'Location': 'https://bucket.endpoint/key', 'Bucket':..., 'Key':..., 'ETag':...}
    return {
        "ok": True,
        "location": out.get("Location"),
        "bucket": out.get("Bucket"),
        "key": out.get("Key"),
        "etag": out.get("ETag"),
    }

def abort_multipart(storage_key: str, upload_id: str):
    s3 = s3_client()
    s3.abort_multipart_upload(
        Bucket=settings.DO_BUCKET,
        Key=storage_key,
        UploadId=upload_id,
    )
    return {"ok": True}

def commit_file(tenant_id: str, file_payload: dict, title: str | None, lang: str, source: str):
    """
    Valida ownership y persiste filas en 'files' y 'kb_documents' usando tu repo.
    file_payload:
      - mode: single|multipart
      - storage_key: tenants/{tenant}/...
      - (opcional) location, etag
    """
    storage_key = str(file_payload.get("storage_key", ""))
    if not storage_key.startswith(f"tenants/{tenant_id}/"):
        raise HTTPException(403, "storage_key fuera del tenant")

    return insert_file_and_doc(tenant_id, file_payload, title, lang, source)

def semantic_search(tenant_id: str, embedder, q: str, k: int = 5):
    vec = embedder(q, tenant_id)
    rows = search_chunks(tenant_id, vec, k)
    return [
        {
            "doc_id": str(r[0]),
            "text": r[1],
            "score": float(r[2]),
            "file_id": str(r[3]),
        }
        for r in rows
    ]
