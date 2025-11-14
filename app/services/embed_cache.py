# app/services/embed_cache.py
import hashlib, json
from core.redis_client import rds

def qhash(q: str) -> str:
    return hashlib.sha1(q.encode()).hexdigest()

def set_query_vec(q: str, vec: list[float]):
    rds.setex(f"emb:{qhash(q)}", 300, json.dumps(vec))

def get_query_vec(q: str):
    v = rds.get(f"emb:{qhash(q)}")
    return json.loads(v) if v else None
