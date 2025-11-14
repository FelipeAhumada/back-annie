from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.auth import auth_required, Authed
from services.kb_services import commit_file, semantic_search
from core.openai_embed import embed_async
from core.db import get_conn
from core.redis import rds
from fastapi import HTTPException

router = APIRouter(prefix="/api/v1/kb", tags=["kb"])

class CommitIn(BaseModel):
    file: dict
    title: str | None = None
    lang: str | None = "es"
    source: str = "upload"

@router.post("/files/commit")
def commit(p: CommitIn, auth: Authed = Depends(auth_required)):
    file_id, doc_id = commit_file(auth.tenant_id, p.file, p.title, p.lang or "es", p.source)
    return {"ok": True, "file_id": file_id, "doc_id": doc_id}

class SearchIn(BaseModel):
    q: str
    k: int = 5

# Placeholder de embedder (inyecta OpenAI real en prod)
def _embedder(q: str, tenant_id: str):
    return [0.0]*1536 # reemplazar por llamada real a OpenAI

@router.get("/search")
def search(q: str, k: int = 5, auth: Authed = Depends(auth_required)):
    return {"results": semantic_search(auth.tenant_id, _embedder, q, k)}


def _chunk(text: str, size=3500, overlap=400):
    # aproximación por caracteres
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        j = min(i+size, n)
        chunks.append(text[i:j])
        i = j - overlap if j - overlap > i else j
    return chunks

@router.post("/documents/{doc_id}/ingest")
async def ingest(doc_id: str, auth: Authed = Depends(auth_required)):
    # 1) obtener storage_key desde el doc
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""SELECT d.tenant_id, f.storage_key FROM kb_documents d
                       JOIN files f ON f.id=d.file_id WHERE d.id=%s""", (doc_id,))
        row = cur.fetchone()
        if not row: raise HTTPException(404,"doc not found")
        tenant_id, storage_key = row
    # 2) descargar archivo desde Spaces (usando URL presignada GET)
    from core.s3 import s3_client
    s3 = s3_client()
    import io
    b = io.BytesIO()
    s3.download_fileobj(Bucket=os.getenv("DO_BUCKET"), Key=storage_key, Fileobj=b)
    data = b.getvalue()
    # 3) extraer texto (MVP: texto plano / pdf simple con pypdf si lo agregas)
    text = data.decode("utf-8", errors="ignore")
    parts = _chunk(text)
    # 4) embeddings
    vecs = await embed_async(parts)
    # 5) insertar chunks
    with get_conn() as conn, conn.cursor() as cur:
        for i, (t, v) in enumerate(zip(parts, vecs)):
            cur.execute(
                "INSERT INTO kb_chunks (tenant_id, doc_id, chunk_index, text, embedding) VALUES (%s,%s,%s,%s,%s)",
                (tenant_id, doc_id, i, t, v)
            )
        cur.execute("UPDATE kb_documents SET status='ready' WHERE id=%s", (doc_id,))
        conn.commit()
    return {"ok": True, "chunks": len(parts)}


@router.get("/search")
async def search(q: str, k: int = 5, auth: Authed = Depends(auth_required)):
    vec = (await embed_async([q]))[0]
    rows = search_chunks(auth.tenant_id, vec, k)
    return {"results": [{"doc_id": str(r[0]), "text": r[1], "score": float(r[2]), "file_id": str(r[3])} for r in rows]}




@router.get("/documents/{doc_id}/status")
def doc_status(doc_id: str, auth: Authed = Depends(auth_required)):
    # Redis primero
    st = rds.get(f"job:{doc_id}") or "unknown"
    prog = int(rds.get(f"job:{doc_id}:progress") or 0)
    # Si Redis no sabe, consulta DB
    if st in ("unknown","done"):
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT status, tenant_id FROM kb_documents WHERE id=%s", (doc_id,))
            row = cur.fetchone()
            if not row: raise HTTPException(404,"doc not found")
            status_db, tenant_id = row
            if tenant_id != auth.tenant_id: raise HTTPException(403,"tenant mismatch")
            if st=="unknown": st = "ready" if status_db=="ready" else ("error" if status_db=="error" else "ingesting")
    # map
    status_map = {"pending":"pending","running":"running","ingesting":"running","ready":"ready","error":"error","done":"ready","unknown":"pending"}
    return {"status": status_map.get(st, "pending"), "progress": prog}
