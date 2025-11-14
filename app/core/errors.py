# app/core/errors.py
from typing import Any, Dict, Optional
from fastapi import HTTPException
from enum import Enum

class ErrorCode(str, Enum):
    UNAUTHORIZED = "unauthorized"        # 401
    FORBIDDEN = "forbidden"              # 403
    NOT_FOUND = "not_found"              # 404
    CONFLICT = "conflict"                # 409
    VALIDATION_ERROR = "validation_error"# 422
    RATE_LIMITED = "rate_limited"        # 429
    INTERNAL_ERROR = "internal_error"    # 500
    BAD_REQUEST = "bad_request"          # 400

def http_error(
    *,
    status_code: int,
    code: ErrorCode,
    message: str,
    meta: Optional[Dict[str, Any]] = None,
) -> HTTPException:
    """
    Standardized HTTPException factory.
    Frontend should key on `detail.code` for i18n and behavior.
    """
    detail = {
        "code": code.value,
        "message": message,
    }
    if meta:
        detail["meta"] = meta
    return HTTPException(status_code=status_code, detail=detail)
