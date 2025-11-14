# app/core/db.py
from contextlib import contextmanager
from psycopg2.pool import SimpleConnectionPool
from .config import settings

_pool = SimpleConnectionPool(
    1, 10,
    host=settings.PG_HOST,
    port=settings.PG_PORT,
    dbname=settings.PG_DB,
    user=settings.PG_USER,
    password=settings.PG_PASSWORD,
    sslmode=settings.PG_SSLMODE,
    options=f"-c search_path={settings.PG_SCHEMA}",
)

@contextmanager
def get_conn():
    conn = _pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {settings.PG_SCHEMA};")  # 👈 blindaje extra
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)
