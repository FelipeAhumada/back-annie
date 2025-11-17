"""
Centralized logging module for Annie-AI backend.

Follows Layer 6 rules:
- Structured logging suitable for Grafana/Prometheus/Loki/ELK
- Appropriate log levels (info, warning, error)
- NEVER logs passwords, tokens, secrets, or full request bodies with sensitive data
- Security-sensitive actions emit structured logs with user_id, tenant_id, action, result, timestamp
"""
import logging
import json
from typing import Any, Dict, Optional
from datetime import datetime

# Configure root logger
logger = logging.getLogger("annie")
logger.setLevel(logging.INFO)

# Console handler with JSON formatter for structured logs
_handler = logging.StreamHandler()
_handler.setLevel(logging.INFO)

# JSON formatter for structured logging
class JSONFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "tenant_id"):
            log_data["tenant_id"] = record.tenant_id
        if hasattr(record, "action"):
            log_data["action"] = record.action
        if hasattr(record, "result"):
            log_data["result"] = record.result
        if hasattr(record, "meta"):
            log_data["meta"] = record.meta
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

_handler.setFormatter(JSONFormatter())
logger.addHandler(_handler)

# Prevent duplicate logs
logger.propagate = False


def log_security_event(
    action: str,
    result: str,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    level: str = "info",
) -> None:
    """
    Log security-sensitive actions (login, failed login, role changes, billing changes).
    
    Emits structured logs with:
    - user_id, tenant_id, action, result, timestamp
    - Additional metadata in meta dict
    
    Args:
        action: Action name (e.g., "login", "role_change", "billing_update")
        result: Result status (e.g., "success", "failure", "denied")
        user_id: User ID (optional)
        tenant_id: Tenant ID (optional)
        meta: Additional metadata dict (optional)
        level: Log level ("info", "warning", "error")
    """
    log_method = getattr(logger, level.lower(), logger.info)
    extra = {
        "action": action,
        "result": result,
    }
    if user_id:
        extra["user_id"] = user_id
    if tenant_id:
        extra["tenant_id"] = tenant_id
    if meta:
        extra["meta"] = meta
    
    log_method("Security event", extra=extra)

