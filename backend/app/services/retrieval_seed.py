"""Idempotent Help Center seeding into Qdrant (startup)."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import httpx

from app.services.openai_embeddings import embed_texts_openai
from app.services.openai_key_env import openai_api_key_from_env
from app.services.qdrant_http import ensure_collection, upsert_points
from app.services.rag_env import (
    embeddings_model_from_env,
    embeddings_vector_size_from_env,
    qdrant_collection_from_env,
    qdrant_url_from_env,
    rag_enabled_from_env,
)
from app.services.retries import httpx_retryable, retry_async

_logger = logging.getLogger(__name__)

TIMEOUT_S = 30.0


def seed_fixture_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "help_center_seed.json"


def point_id_for_question(question: str) -> int:
    digest = hashlib.sha256(question.strip().encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)


def build_seed_points(
    entries: list[dict[str, str]],
    vectors: list[list[float]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row, vec in zip(entries, vectors, strict=True):
        q = row["question"]
        rows.append(
            {
                "id": point_id_for_question(q),
                "vector": vec,
                "payload": {
                    "question": q,
                    "answer": row["answer"],
                    "source": "seed",
                },
            }
        )
    return rows


def load_seed_entries() -> list[dict[str, str]]:
    path = seed_fixture_path()
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("help_center_seed.json must be a JSON array")
    out: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        q = str(item.get("question", "")).strip()
        a = str(item.get("answer", "")).strip()
        if q and a:
            out.append({"question": q, "answer": a})
    return out


async def seed_help_center_qdrant() -> None:
    """Ensure collection exists and upsert seed Q&A (idempotent)."""
    if not rag_enabled_from_env():
        _logger.info("RAG disabled (RAG_ENABLED); skipping Help Center Qdrant seed")
        return

    api_key = openai_api_key_from_env()
    if not api_key:
        _logger.warning("OPENAI_API_KEY missing; skipping Help Center Qdrant seed")
        return

    entries = load_seed_entries()
    if not entries:
        _logger.warning("Help Center seed file empty; nothing to upsert")
        return

    base = qdrant_url_from_env()
    collection = qdrant_collection_from_env()
    model = embeddings_model_from_env()
    override_dim = embeddings_vector_size_from_env()

    texts = [e["question"] for e in entries]

    async with httpx.AsyncClient() as client:

        async def embed_job():
            return await embed_texts_openai(
                texts,
                api_key=api_key,
                model=model,
                timeout_seconds=TIMEOUT_S,
                client=client,
            )

        vectors = await retry_async(embed_job, max_attempts=3, retry_if=httpx_retryable, label="openai_embed_seed")

        if len(vectors) != len(entries):
            raise RuntimeError(
                f"embedding count mismatch: got {len(vectors)} vectors for {len(entries)} seed rows"
            )

        dim = override_dim if override_dim is not None else len(vectors[0])
        if override_dim is not None and len(vectors[0]) != override_dim:
            _logger.warning(
                "EMBEDDINGS_VECTOR_SIZE=%s does not match embedding length %s; using embedding length",
                override_dim,
                len(vectors[0]),
            )
            dim = len(vectors[0])

        async def ensure():
            await ensure_collection(
                base,
                collection,
                vector_size=dim,
                timeout=TIMEOUT_S,
                client=client,
            )

        await retry_async(ensure, max_attempts=3, retry_if=httpx_retryable, label="qdrant_ensure_collection")

        points = build_seed_points(entries, vectors)

        async def upsert():
            await upsert_points(base, collection, points, timeout=TIMEOUT_S, client=client)

        await retry_async(upsert, max_attempts=3, retry_if=httpx_retryable, label="qdrant_upsert_seed")

    _logger.info(
        "Help Center Qdrant seed complete collection=%s points=%s model=%s",
        collection,
        len(points),
        model,
    )


async def seed_help_center_safe() -> None:
    """Never raises — logs warning so API/bot still start without RAG."""
    try:
        await seed_help_center_qdrant()
    except Exception:
        _logger.warning("Help Center Qdrant seed failed; bot will run without retrieval context", exc_info=True)
