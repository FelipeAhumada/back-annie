"""
OpenAI embedding service.

Follows Layer 5 rules:
- All configuration from centralized settings (config.py)
- Never use os.getenv directly
"""
from __future__ import annotations
import httpx
from core.config import settings


async def embed_async(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts using OpenAI API.
    
    Args:
        texts: List of text strings to embed
    
    Returns:
        List of embedding vectors (list of floats)
    
    Raises:
        RuntimeError: If OPENAI_API_KEY is not configured
        httpx.HTTPStatusError: If API request fails
    """
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY missing in configuration")
    
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            url,
            headers=headers,
            json={"model": settings.EMBED_MODEL, "input": texts}
        )
        r.raise_for_status()
        data = r.json()
        return [d["embedding"] for d in data["data"]]
