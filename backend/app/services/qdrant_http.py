from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable

import httpx


@dataclass(frozen=True)
class QdrantPoint:
    id: int
    vector: list[float]
    payload: dict[str, Any]


def qdrant_url_from_env() -> str:
    return os.environ.get("QDRANT_URL", "http://qdrant:6333").rstrip("/")


def qdrant_collection_from_env() -> str:
    return os.environ.get("QDRANT_COLLECTION", "help_center")


def qdrant_top_k_from_env() -> int:
    try:
        v = int(os.environ.get("QDRANT_TOP_K", "3"))
    except ValueError:
        v = 3
    return max(1, min(20, v))


async def ensure_collection(
    *,
    client: httpx.AsyncClient,
    base_url: str,
    collection: str,
    vector_size: int,
    distance: str = "Cosine",
) -> None:
    # Check exists
    r = await client.get(f"{base_url}/collections/{collection}")
    if r.status_code == 200:
        return
    if r.status_code not in (404,):
        r.raise_for_status()

    # Create
    create_body = {"vectors": {"size": vector_size, "distance": distance}}
    r = await client.put(f"{base_url}/collections/{collection}", json=create_body)
    r.raise_for_status()


async def upsert_points(
    *,
    client: httpx.AsyncClient,
    base_url: str,
    collection: str,
    points: Iterable[QdrantPoint],
) -> None:
    body = {
        "points": [
            {"id": p.id, "vector": p.vector, "payload": p.payload}
            for p in points
        ]
    }
    r = await client.put(f"{base_url}/collections/{collection}/points?wait=true", json=body)
    r.raise_for_status()


async def search(
    *,
    client: httpx.AsyncClient,
    base_url: str,
    collection: str,
    vector: list[float],
    limit: int,
    with_payload: bool = True,
) -> list[dict[str, Any]]:
    body: dict[str, Any] = {
        "vector": vector,
        "limit": limit,
        "with_payload": with_payload,
    }
    r = await client.post(f"{base_url}/collections/{collection}/points/search", json=body)
    r.raise_for_status()
    data = r.json()
    result = data.get("result")
    if not isinstance(result, list):
        return []
    return result

