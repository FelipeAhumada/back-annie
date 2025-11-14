import hashlib, json
from core.redis import rds

def set_query_vec(query: str, vec: list[float]):
    key = "emb:" + hashlib.sha1(query.encode()).hexdigest()
    rds.setex(key, 300, json.dumps(vec))

def get_query_vec(query: str):
    key = "emb:" + hashlib.sha1(query.encode()).hexdigest()
    val = rds.get(key)
    return json.loads(val) if val else None
