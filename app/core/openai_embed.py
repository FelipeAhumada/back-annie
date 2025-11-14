# app/core/openai_embed.py
import os, httpx
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBED_MODEL = os.getenv("EMBED_MODEL","text-embedding-3-small")

async def embed_async(texts: list[str]) -> list[list[float]]:
    if not OPENAI_API_KEY: raise RuntimeError("OPENAI_API_KEY missing")
    url = "https://api.openai.com/v1/embeddings"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type":"application/json"}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers=headers, json={"model": EMBED_MODEL, "input": texts})
        r.raise_for_status()
        data = r.json()
        return [d["embedding"] for d in data["data"]]
