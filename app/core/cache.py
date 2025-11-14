# app/core/cache.py
import json, functools
from core.redis import rds

def cached(key: str, ttl: int):
    def deco(fn):
        @functools.wraps(fn)
        def wrap(*args, **kwargs):
            k = key.format(**kwargs)
            hit = rds.get(k)
            if hit is not None:
                return json.loads(hit)
            res = fn(*args, **kwargs)
            rds.setex(k, ttl, json.dumps(res, default=str))
            return res
        return wrap
    return deco

def invalidate(*keys: str):
    return rds.delete(*keys) if keys else 0
