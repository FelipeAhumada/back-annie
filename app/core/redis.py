# app/core/redis.py
import os, redis
ssl = os.getenv("REDIS_SSL", "false").lower() in ("1","true","yes")
rds = redis.Redis(
    host=os.getenv("REDIS_HOST","localhost"),
    port=int(os.getenv("REDIS_PORT","6379")),
    password=os.getenv("REDIS_PASSWORD") or None,
    ssl=ssl,
    ssl_cert_reqs=None,  # DO Valkey usa TLS sin cliente; evita fallar por CA
    decode_responses=True,
    socket_keepalive=True,
)
