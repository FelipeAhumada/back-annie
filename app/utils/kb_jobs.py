# app/utils/kb_jobs.py
from core.redis import rds
import json, time

def job_set_status(doc_id: str, status: str):
    key = f"job:{doc_id}"
    rds.setex(key, 259200, status)  # TTL 3 días

def job_get_status(doc_id: str):
    key = f"job:{doc_id}"
    return rds.get(key) or "unknown"

def job_set_progress(doc_id: str, progress: int):
    key = f"job:{doc_id}:progress"
    rds.setex(key, 259200, progress)

def job_get_progress(doc_id: str):
    key = f"job:{doc_id}:progress"
    return int(rds.get(key) or 0)
