"""
LLM client for multiple providers (OpenAI, Gemini, Grok).

Follows Layer 5 rules:
- All API keys from centralized settings (config.py)
- Never use os.getenv directly
"""
from __future__ import annotations
from typing import Any
import requests
from core.config import settings


class LLMError(Exception):
    """Exception raised for LLM API errors."""
    pass


def _resolve_api_key(api_key_ref: str | None, provider: str) -> str | None:
    """
    Resolve API key for LLM provider.
    
    Priority:
    1. If api_key_ref is provided, look it up (future: Vault/secret manager)
    2. Fallback to provider-specific key from settings
    
    Args:
        api_key_ref: Optional API key reference identifier
        provider: LLM provider name (openai, gemini, grok)
    
    Returns:
        API key string or None if not found
    """
    # TODO: Implement proper secret manager lookup for api_key_ref
    # For now, if api_key_ref is provided, we could look it up from a secret store
    # This is a placeholder for future implementation
    
    # Fallback to provider-specific keys from centralized settings
    if provider == "openai":
        return settings.OPENAI_API_KEY
    if provider == "gemini":
        return settings.GEMINI_API_KEY
    if provider == "grok":
        return settings.GROK_API_KEY
    return None

def generate_text(cfg: dict, messages: list[dict[str, Any]]) -> dict:
    """
    cfg: lo que guardamos en LLM settings (provider, model, temperature, top_p, top_k, max_tokens, penalties, stop, reasoning_enabled, system_prompt, tools, api_key_ref, meta)
    messages: [{"role":"system/user/assistant","content":"..."}]
    """
    provider = cfg["provider"]
    api_key = _resolve_api_key(cfg.get("api_key_ref"), provider)
    if not api_key:
        raise LLMError(f"Missing API key for provider {provider}")

    # Inserta system_prompt si lo configuraste
    sys = cfg.get("system_prompt")
    role = cfg.get("role") or "system"
    if sys:
        messages = [{"role": role, "content": sys}] + messages

    if provider == "openai":
        return _openai_chat(cfg, api_key, messages)
    elif provider == "gemini":
        return _gemini_chat(cfg, api_key, messages)
    elif provider == "grok":
        return _grok_chat(cfg, api_key, messages)
    else:
        raise LLMError(f"Unsupported provider {provider}")

def _openai_chat(cfg, api_key, messages):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    body = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": cfg.get("temperature"),
        "top_p": cfg.get("top_p"),
        "max_tokens": cfg.get("max_tokens"),
        "frequency_penalty": cfg.get("frequency_penalty"),
        "presence_penalty": cfg.get("presence_penalty"),
        "stop": cfg.get("stop") or None,
        # tools si aplican al modelo
        "tools": cfg.get("tools") or None,
    }
    resp = requests.post(url, json=body, headers=headers, timeout=60)
    if resp.status_code >= 300:
        raise LLMError(resp.text)
    j = resp.json()
    text = j["choices"][0]["message"]["content"]
    return {"text": text, "raw": j}

def _gemini_chat(cfg, api_key, messages):
    # Gemini usa Google AI Studio; modelos "gemini-1.5-pro" etc.
    # Formato típico: messages → contents (role->"user"/"model")
    def to_contents(msgs):
        contents = []
        for m in msgs:
            role = m["role"]
            parts = [{"text": m["content"]}]
            if role == "assistant":
                contents.append({"role": "model", "parts": parts})
            else:
                contents.append({"role": "user", "parts": parts})
        return contents

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{cfg['model']}:generateContent?key={api_key}"
    body = {
        "contents": to_contents(messages),
        "generationConfig": {
            "temperature": cfg.get("temperature"),
            "topP": cfg.get("top_p"),
            "topK": cfg.get("top_k"),
            "maxOutputTokens": cfg.get("max_tokens"),
            # stop isn't always supported; omit or map to safety if needed
        },
        # safety_settings y extras
    }
    resp = requests.post(url, json=body, timeout=60)
    if resp.status_code >= 300:
        raise LLMError(resp.text)
    j = resp.json()
    text = j["candidates"][0]["content"]["parts"][0].get("text", "")
    return {"text": text, "raw": j}

def _grok_chat(cfg, api_key, messages):
    # Grok (xAI) API (chat.completions compatible con OpenAI-style en varias libs)
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    body = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": cfg.get("temperature"),
        "top_p": cfg.get("top_p"),
        "max_tokens": cfg.get("max_tokens"),
        "stop": cfg.get("stop") or None,
    }
    resp = requests.post(url, json=body, headers=headers, timeout=60)
    if resp.status_code >= 300:
        raise LLMError(resp.text)
    j = resp.json()
    text = j["choices"][0]["message"]["content"]
    return {"text": text, "raw": j}
