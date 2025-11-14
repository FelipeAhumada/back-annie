# Compatibilidad hacia atrás: antes se importaba core.redis_client
# Ahora todo vive en core/redis.py
from .redis import *  # exporta rds y lo que ya tengas allí
