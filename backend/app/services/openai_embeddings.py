"""OpenAI embeddings API (HTTP, async)."""

from __future__ import annotations

from typing import Any

import httpx

OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


async def embed_texts_openai(
    texts: list[str],
    *,
    api_key: str,
    model: str,
    timeout_seconds: float,
    client: httpx.AsyncClient | None = None,
) -> list[list[float]]:
    """Return embedding vectors in the same order as ``texts``."""
    if not texts:
        return []
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body: dict[str, Any] = {"model": model, "input": texts}

    async def _post(http: httpx.AsyncClient) -> Any:
        r = await http.post(
            OPENAI_EMBEDDINGS_URL,
            headers=headers,
            json=body,
            timeout=timeout_seconds,
        )
        r.raise_for_status()
        return r.json()

    if client is not None:
        data = await _post(client)
    else:
        async with httpx.AsyncClient() as http:
            data = await _post(http)

    items = data.get("data") or []
    if not items:
        return []
    if all(isinstance(it, dict) and "index" in it for it in items):
        indexed: list[tuple[int, list[float]]] = []
        for item in items:
            vec = item.get("embedding")
            if not isinstance(vec, list):
                continue
            indexed.append((int(item["index"]), [float(x) for x in vec]))
        indexed.sort(key=lambda t: t[0])
        return [vec for _, vec in indexed]
    # Fallback: preserve API array order
    out: list[list[float]] = []
    for item in items:
        vec = item.get("embedding") if isinstance(item, dict) else None
        if isinstance(vec, list):
            out.append([float(x) for x in vec])
    return out
