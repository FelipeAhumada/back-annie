# app/api/v1/llm.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from core.auth import auth_required, Authed
from repositories.llm_repository import get_llm_settings, upsert_llm_settings, delete_llm_settings

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])

# valores por defecto sensatos
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
    # proveedor + modelo
    provider: str = Field(..., description="openai | gemini | grok")
    model: str

    # controles de decodificación
    temperature: float = DEFAULTS["temperature"]
    top_p: float = DEFAULTS["top_p"]
    top_k: int | None = DEFAULTS["top_k"]
    max_tokens: int | None = DEFAULTS["max_tokens"]

    # penalizaciones y stops
    frequency_penalty: float = DEFAULTS["frequency_penalty"]
    presence_penalty: float = DEFAULTS["presence_penalty"]
    stop: list[str] = Field(default_factory=list)

    # razonamiento / rol / prompt
    reasoning_enabled: bool = DEFAULTS["reasoning_enabled"]
    system_prompt: str | None = None
    role: str | None = "system"  # por si el front lo quiere visible

    # claves / herramientas / extras
    api_key_ref: str | None = None
    tools: list = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)  # provider_options, safety_settings, etc.

@router.get("/settings")
def llm_get(auth: Authed = Depends(auth_required)):
    data = get_llm_settings(auth.tenant_id)
    if not data:
        raise HTTPException(404, "not found")
    # compat: si vienen nulos, completar defaults esperados por el front
    for k, v in DEFAULTS.items():
        data.setdefault(k, v)
    data.setdefault("stop", [])
    data.setdefault("role", "system")
    data.setdefault("tools", [])
    data.setdefault("meta", {})
    return data

@router.post("/settings")
def llm_set(p: LLMUpsert, auth: Authed = Depends(auth_required)):
    if p.provider not in ALLOWED_PROVIDERS:
        raise HTTPException(400, f"provider must be one of {sorted(ALLOWED_PROVIDERS)}")

    payload = p.model_dump()
    # normalizaciones mínimas por proveedor (ejemplos):
    if p.provider == "gemini":
        # Gemini ignora frequency/presence penalties; conservar igual para uniformidad
        pass
    if p.provider == "grok":
        # Grok suele usar top_p/temperature/max_tokens; top_k es ignorado
        pass

    upsert_llm_settings(auth.tenant_id, payload)
    return {"ok": True}

@router.delete("/settings")
def llm_del(auth: Authed = Depends(auth_required)):
    delete_llm_settings(auth.tenant_id)
    return {"ok": True}
