# app/repositories/kb_meta_repo.py
import json
from core.db import get_conn
from core.redis_client import rds

def get_doc_meta(doc_id: str):
    k = f"kb_doc_meta:{doc_id}"
    c = rds.get(k)
    if c: return json.loads(c)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, tenant_id, title, status, meta FROM kb_documents WHERE id=%s",(doc_id,))
        r = cur.fetchone()
        if not r: return None
        data = {"id":str(r[0]),"tenant_id":r[1],"title":r[2],"status":r[3],"meta":r[4]}
    rds.setex(k, 3600, json.dumps(data))
    return data

def invalidate_doc_meta(doc_id: str):
    rds.delete(f"kb_doc_meta:{doc_id}")
