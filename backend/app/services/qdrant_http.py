"""Minimal Qdrant REST helpers (async, httpx)."""

from __future__ import annotations

from typing import Any

import httpx


async def collection_exists(base_url: str, collection: str, *, timeout: float, client: httpx.AsyncClient) -> bool:
    r = await client.get(f"{base_url}/collections/{collection}", timeout=timeout)
    if r.status_code == 404:
        return False
    r.raise_for_status()
    return True


async def ensure_collection(
    base_url: str,
    collection: str,
    *,
    vector_size: int,
    timeout: float,
    client: httpx.AsyncClient,
) -> None:
    if await collection_exists(base_url, collection, timeout=timeout, client=client):
        return
    payload = {"vectors": {"size": vector_size, "distance": "Cosine"}}
    r = await client.put(f"{base_url}/collections/{collection}", json=payload, timeout=timeout)
    # Race: another replica might have created it.
    if r.status_code in (409, 200):
        return
    r.raise_for_status()


async def upsert_points(
    base_url: str,
    collection: str,
    points: list[dict[str, Any]],
    *,
    timeout: float,
    client: httpx.AsyncClient,
) -> None:
    if not points:
        return
    r = await client.put(
        f"{base_url}/collections/{collection}/points",
        params={"wait": "true"},
        json={"points": points},
        timeout=timeout,
    )
    r.raise_for_status()


async def search_points(
    base_url: str,
    collection: str,
    *,
    vector: list[float],
    limit: int,
    timeout: float,
    client: httpx.AsyncClient,
) -> list[dict[str, Any]]:
    body = {"vector": vector, "limit": limit, "with_payload": True}
    r = await client.post(
        f"{base_url}/collections/{collection}/points/search",
        json=body,
        timeout=timeout,
    )
    r.raise_for_status()
    data = r.json()
    return list(data.get("result") or [])
