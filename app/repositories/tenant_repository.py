# app/repositories/tenant_repository.py
from core.redis import rds
from core.db import get_conn
import json

def get_tenant_by_domain(domain: str):
    cache_key = f"tenant:by-domain:{domain}"
    cached = rds.get(cache_key)
    if cached:
        return json.loads(cached)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id,name,timezone,locale FROM tenants WHERE domain=%s", (domain,))
        r = cur.fetchone()
        if not r:
            return None
        data = {"tenant_id": r[0], "name": r[1], "timezone": r[2], "locale": r[3]}
        rds.setex(cache_key, 3600, json.dumps(data))
        rds.setex(f"tenant:{r[0]}", 3600, json.dumps(data))
        return data
