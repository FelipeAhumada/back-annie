# app/repositories/crm_repo.py
import json
from core.db import get_conn
from core.redis_client import rds

def get_hours(tenant_id: str):
    k = f"business_hours:{tenant_id}"
    c = rds.get(k)
    if c: return json.loads(c)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT day_of_week, open, close FROM business_hours WHERE tenant_id=%s ORDER BY day_of_week",(tenant_id,))
        rows = [{"day":r[0],"open":str(r[1]),"close":str(r[2])} for r in cur.fetchall()]
    rds.setex(k, 3600, json.dumps(rows))
    return rows

def set_hours(tenant_id: str, items: list[dict]):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM business_hours WHERE tenant_id=%s",(tenant_id,))
        for it in items:
            cur.execute("""INSERT INTO business_hours (tenant_id, day_of_week, open, close) VALUES (%s,%s,%s,%s)""",
                        (tenant_id, it["day"], it["open"], it["close"]))
        conn.commit()
    rds.delete(f"business_hours:{tenant_id}")

def get_availability(tenant_id: str, limit: int = 6):
    k = f"availability_next:{tenant_id}"
    c = rds.get(k)
    if c: return json.loads(c)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""SELECT start_ts, end_ts, bookable FROM availability_slots
                       WHERE tenant_id=%s AND start_ts>now() ORDER BY start_ts ASC LIMIT %s""",(tenant_id, limit))
        rows = [{"start":r[0].isoformat(),"end":r[1].isoformat(),"bookable":r[2]} for r in cur.fetchall()]
    rds.setex(k, 60, json.dumps(rows))
    return rows

def set_availability(tenant_id: str, slots: list[dict]):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM availability_slots WHERE tenant_id=%s AND start_ts>now()", (tenant_id,))
        for s in slots:
            cur.execute("""INSERT INTO availability_slots (tenant_id, start_ts, end_ts, bookable) VALUES (%s,%s,%s,%s)""",
                        (tenant_id, s["start"], s["end"], s.get("bookable", True)))
        conn.commit()
    rds.delete(f"availability_next:{tenant_id}")
