# app/repositories/plan_repo.py
import json
from core.db import get_conn
from core.redis_client import rds

def list_pricing(tenant_id: str):
    key = f"pricing_plans:{tenant_id}"
    c = rds.get(key)
    if c: return json.loads(c)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""SELECT id, name, uf, clp, features FROM pricing_plans WHERE tenant_id=%s ORDER BY id""",(tenant_id,))
        rows = [{"id":str(x[0]),"name":x[1],"uf":(float(x[2]) if x[2] is not None else None),"clp":x[3],"features":x[4]} for x in cur.fetchall()]
    rds.setex(key, 900, json.dumps(rows))
    return rows

def create_plan(tenant_id: str, name: str, uf: float | None, clp: int | None, features: list):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO pricing_plans (tenant_id,name,uf,clp,features) VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                    (tenant_id, name, uf, clp, json.dumps(features)))
        pid = str(cur.fetchone()[0]); conn.commit()
    rds.delete(f"pricing_plans:{tenant_id}")
    return pid

def set_tenant_plan(tenant_id: str, plan_id: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO tenant_plan (tenant_id, plan_id) VALUES (%s,%s)
                       ON CONFLICT (tenant_id) DO UPDATE SET plan_id=EXCLUDED.plan_id""",
                    (tenant_id, plan_id))
        conn.commit()
    rds.delete(f"tenant_plan:{tenant_id}")

def upsert_limit(plan_id: str, key: str, value: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO plan_limits (plan_id, key, value) VALUES (%s,%s,%s)
                       ON CONFLICT (plan_id, key) DO UPDATE SET value=EXCLUDED.value""",
                    (plan_id, key, value))
        conn.commit()
    rds.delete(f"plan_limits:{plan_id}")

def get_plan_limits(plan_id: str):
    key = f"plan_limits:{plan_id}"
    c = rds.get(key)
    if c: return json.loads(c)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT key, value FROM plan_limits WHERE plan_id=%s",(plan_id,))
        rows = {k:int(v) for (k,v) in cur.fetchall()}
    rds.setex(key, 1800, json.dumps(rows))
    return rows
