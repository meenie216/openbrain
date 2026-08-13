import os

import httpx

OLLAMA_BASE_URL = os.environ["OLLAMA_BASE_URL"]
OLLAMA_EMBED_MODEL = os.environ["OLLAMA_EMBED_MODEL"]


async def embed(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]
