"""
Redis/Valkey client configuration.

Follows Layer 5 rules:
- All configuration from centralized settings (config.py)
- Never use os.getenv directly
"""
from __future__ import annotations
import redis
from core.config import settings

ssl = settings.REDIS_SSL.lower() in ("1", "true", "yes")
rds = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    ssl=ssl,
    ssl_cert_reqs=None,  # DO Valkey uses TLS without client cert; avoids CA failure
    decode_responses=True,
    socket_keepalive=True,
)
