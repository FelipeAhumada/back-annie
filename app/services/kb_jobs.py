# app/services/kb_jobs.py
from core.redis_client import rds

def job_set_status(doc_id: str, status: str):
    rds.setex(f"job:{doc_id}", 259200, status)  # 3 días

def job_get_status(doc_id: str) -> str:
    return rds.get(f"job:{doc_id}") or "unknown"

def job_set_progress(doc_id: str, n: int):
    rds.setex(f"job:{doc_id}:progress", 259200, int(n))

def job_get_progress(doc_id: str) -> int:
    v = rds.get(f"job:{doc_id}:progress")
    return int(v) if v else 0
