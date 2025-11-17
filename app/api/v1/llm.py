"""
LLM settings endpoints for Settings module.

Follows Layer 2 and Layer 3 rules:
- Settings read → min role observer
- Settings write → min role admin
- All queries MUST be tenant-scoped
- ALWAYS use Pydantic models for request/response
"""
from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from core.auth import auth_required, Authed
from core.roles import require_min_role
from core.errors import http_error, ErrorCode
from repositories.llm_repository import get_llm_settings, upsert_llm_settings, delete_llm_settings

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])

# Sensible default values
DEFAULTS = dict(
    temperature=0.2,
    top_p=1.0,
    top_k=None,
    max_tokens=None,
    frequency_penalty=0.0,
    presence_penalty=0.0,
    stop=[],
    reasoning_enabled=False,
)

ALLOWED_PROVIDERS = {"openai", "gemini", "grok"}


class LLMUpsert(BaseModel):
    """Request schema for LLM settings upsert."""
    provider: str = Field(..., description="LLM provider: openai | gemini | grok")
    model: str = Field(..., description="Model name")
    
    # Decoding controls
    temperature: float = Field(default=DEFAULTS["temperature"], ge=0.0, le=2.0)
    top_p: float = Field(default=DEFAULTS["top_p"], ge=0.0, le=1.0)
    top_k: int | None = Field(default=DEFAULTS["top_k"], ge=1)
    max_tokens: int | None = Field(default=DEFAULTS["max_tokens"], ge=1)
    
    # Penalties and stops
    frequency_penalty: float = Field(default=DEFAULTS["frequency_penalty"], ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=DEFAULTS["presence_penalty"], ge=-2.0, le=2.0)
    stop: list[str] = Field(default_factory=list, description="Stop sequences")
    
    # Reasoning / role / prompt
    reasoning_enabled: bool = Field(default=DEFAULTS["reasoning_enabled"])
    system_prompt: str | None = Field(default=None, description="System prompt")
    role: str | None = Field(default="system", description="Role for the LLM")
    
    # Keys / tools / extras
    api_key_ref: str | None = Field(default=None, description="API key reference")
    tools: list = Field(default_factory=list, description="Available tools")
    meta: dict = Field(default_factory=dict, description="Provider-specific options")


@router.get("/settings")
def llm_get(auth: Authed = Depends(require_min_role("observer"))) -> dict:
    """
    Get LLM settings for the tenant.
    
    Follows Layer 2 rules:
    - Settings read → min role observer
    - Tenant isolation enforced via auth.tenant_id
    
    Args:
        auth: Authenticated user context (min role: observer)
    
    Returns:
        Dict with LLM settings (with defaults applied)
    
    Raises:
        HTTPException: 404 if settings not found
    """
    data = get_llm_settings(auth.tenant_id)
    if not data:
        raise http_error(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="LLM settings not found",
        )
    
    # Apply defaults for frontend compatibility
    for k, v in DEFAULTS.items():
        data.setdefault(k, v)
    data.setdefault("stop", [])
    data.setdefault("role", "system")
    data.setdefault("tools", [])
    data.setdefault("meta", {})
    return data


@router.post("/settings")
def llm_set(
    p: LLMUpsert,
    auth: Authed = Depends(require_min_role("admin")),
) -> dict:
    """
    Update LLM settings for the tenant.
    
    Follows Layer 2 and Layer 3 rules:
    - Settings write → min role admin
    - Tenant isolation enforced via auth.tenant_id
    - Input validation with Pydantic
    
    Args:
        p: LLM settings request body
        auth: Authenticated user context (min role: admin)
    
    Returns:
        Dict with success status
    
    Raises:
        HTTPException: 400 if provider is invalid
    """
    if p.provider not in ALLOWED_PROVIDERS:
        raise http_error(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message=f"Provider must be one of {sorted(ALLOWED_PROVIDERS)}",
        )

    payload = p.model_dump()
    # Provider-specific normalizations (examples):
    if p.provider == "gemini":
        # Gemini ignores frequency/presence penalties; keep for uniformity
        pass
    if p.provider == "grok":
        # Grok typically uses top_p/temperature/max_tokens; top_k is ignored
        pass

    upsert_llm_settings(auth.tenant_id, payload)
    return {"ok": True}


@router.delete("/settings")
def llm_del(auth: Authed = Depends(require_min_role("admin"))) -> dict:
    """
    Delete LLM settings for the tenant.
    
    Follows Layer 2 rules:
    - Settings write → min role admin
    - Tenant isolation enforced via auth.tenant_id
    
    Args:
        auth: Authenticated user context (min role: admin)
    
    Returns:
        Dict with success status
    """
    delete_llm_settings(auth.tenant_id)
    return {"ok": True}
