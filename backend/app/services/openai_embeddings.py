from __future__ import annotations

import os
from typing import Any

import httpx


def embeddings_model_from_env() -> str:
    return os.environ.get("EMBEDDINGS_MODEL", "text-embedding-3-small")


async def embed_texts(
    *,
    client: httpx.AsyncClient,
    api_key: str,
    model: str,
    texts: list[str],
) -> list[list[float]]:
    if not texts:
        return []

    r = await client.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "input": texts},
        timeout=10.0,
    )
    r.raise_for_status()
    payload: dict[str, Any] = r.json()
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("OpenAI embeddings response missing data[]")

    vectors: list[list[float]] = []
    for item in data:
        emb = item.get("embedding") if isinstance(item, dict) else None
        if not isinstance(emb, list):
            raise ValueError("OpenAI embeddings response item missing embedding[]")
        vectors.append([float(x) for x in emb])
    return vectors

