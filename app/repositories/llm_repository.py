# app/repositories/llm_repo.py
import json
from core.db import get_conn
from core.redis import rds

def get_llm_settings(tenant_id: str):
    key = f"llm_settings:{tenant_id}"
    c = rds.get(key)
    if c: return json.loads(c)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""SELECT provider, model, temperature, top_p, frequency_penalty, presence_penalty, max_tokens,
                              system_prompt, tools, api_key_ref, meta
                       FROM llm_settings WHERE tenant_id=%s LIMIT 1""", (tenant_id,))
        r = cur.fetchone()
        if not r: return None
        data = {
            "provider":r[0], "model":r[1], "temperature":float(r[2]), "top_p":float(r[3]),
            "frequency_penalty":float(r[4]), "presence_penalty":float(r[5]),
            "max_tokens":r[6], "system_prompt":r[7], "tools":r[8], "api_key_ref":r[9], "meta":r[10],
        }
        rds.setex(key, 1800, json.dumps(data))
        return data

def upsert_llm_settings(tenant_id: str, s: dict):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO llm_settings
            (tenant_id, provider, model, temperature, top_p, frequency_penalty, presence_penalty, max_tokens, system_prompt, tools, api_key_ref, meta)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (tenant_id, provider) DO UPDATE SET
              model=EXCLUDED.model, temperature=EXCLUDED.temperature, top_p=EXCLUDED.top_p,
              frequency_penalty=EXCLUDED.frequency_penalty, presence_penalty=EXCLUDED.presence_penalty,
              max_tokens=EXCLUDED.max_tokens, system_prompt=EXCLUDED.system_prompt,
              tools=EXCLUDED.tools, api_key_ref=EXCLUDED.api_key_ref, meta=EXCLUDED.meta
            """,
            (tenant_id, s.get("provider","openai"), s["model"], s.get("temperature",0.2), s.get("top_p",1.0),
             s.get("frequency_penalty",0.0), s.get("presence_penalty",0.0), s.get("max_tokens"),
             s.get("system_prompt"), json.dumps(s.get("tools",[])), s.get("api_key_ref"), json.dumps(s.get("meta",{}))
            )
        )
        conn.commit()
    rds.delete(f"llm_settings:{tenant_id}")

def delete_llm_settings(tenant_id: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM llm_settings WHERE tenant_id=%s", (tenant_id,))
        conn.commit()
    rds.delete(f"llm_settings:{tenant_id}")
