import json
from core.db import get_conn

def insert_file_and_doc(tenant_id: str, file_payload: dict, title: str|None, lang: str, source: str) -> tuple[str,str]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO files (tenant_id, kind, filename, mime_type, size_bytes, storage_key, checksum, status, meta)
                VALUES (%s,'kb',%s,%s,%s,%s,%s,'stored','{}'::jsonb)
                RETURNING id
                """,
                (tenant_id, file_payload.get("filename"), file_payload.get("mime_type"), file_payload.get("size_bytes"), file_payload.get("storage_key"), file_payload.get("checksum"))
            )
            file_id = str(cur.fetchone()[0])
            cur.execute(
                """
                INSERT INTO kb_documents (tenant_id, file_id, source, title, lang, status, meta)
                VALUES (%s,%s,%s,%s,%s,'ingesting','{}'::jsonb)
                RETURNING id
                """,
                (tenant_id, file_id, source, title, lang)
            )
            doc_id = str(cur.fetchone()[0])
            conn.commit()
            return file_id, doc_id

def search_chunks(tenant_id: str, qvec: list[float], k: int = 5):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT kc.doc_id, kc.text, (kc.embedding <-> %s::vector) AS score, kd.file_id
                FROM kb_chunks kc
                JOIN kb_documents kd ON kd.id = kc.doc_id
                WHERE kc.tenant_id = %s
                ORDER BY kc.embedding <-> %s::vector
                LIMIT %s
                """,
                (qvec, tenant_id, qvec, k)
            )
            return cur.fetchall()



def get_kb_doc_meta(doc_id: str):
    key = f"kb_doc_meta:{doc_id}"
    val = rds.get(key)
    if val: return json.loads(val)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id,title,status,meta FROM kb_documents WHERE id=%s", (doc_id,))
        r = cur.fetchone()
        if not r: return None
        data = {"id":r[0],"title":r[1],"status":r[2],"meta":r[3]}
        rds.setex(key, 3600, json.dumps(data))
        return data
