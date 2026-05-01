from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

from app.services.openai_embeddings import embeddings_model_from_env, embed_texts
from app.services.qdrant_http import QdrantPoint, ensure_collection, qdrant_collection_from_env, qdrant_url_from_env, upsert_points

_logger = logging.getLogger(__name__)


def rag_enabled_from_env() -> bool:
    v = os.environ.get("RAG_ENABLED", "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def point_id_for_question(question: str) -> int:
    # Stable 64-bit positive integer ID (qdrant supports int IDs).
    h = hashlib.sha256(question.encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big") & 0x7FFF_FFFF_FFFF_FFFF


def load_seed_entries() -> list[dict[str, str]]:
    seed_path = Path(__file__).resolve().parent.parent / "data" / "help_center_seed.json"
    raw = json.loads(seed_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("help_center_seed.json must be a JSON array")
    entries: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        q = item.get("question")
        a = item.get("answer")
        if isinstance(q, str) and q.strip() and isinstance(a, str) and a.strip():
            entries.append({"question": q.strip(), "answer": a.strip()})
    return entries


def build_seed_points(*, entries: list[dict[str, str]], vectors: list[list[float]]) -> list[dict[str, Any]]:
    if len(entries) != len(vectors):
        raise ValueError("entries and vectors length mismatch")
    points: list[dict[str, Any]] = []
    for e, v in zip(entries, vectors, strict=True):
        points.append(
            {
                "id": point_id_for_question(e["question"]),
                "vector": v,
                "payload": {"question": e["question"], "answer": e["answer"], "source": "seed"},
            }
        )
    return points


async def seed_help_center_collection() -> None:
    if not rag_enabled_from_env():
        _logger.info("rag disabled; skipping qdrant seed")
        return

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        _logger.warning("OPENAI_API_KEY missing; skipping qdrant seed")
        return

    base_url = qdrant_url_from_env()
    collection = qdrant_collection_from_env()
    model = embeddings_model_from_env()

    entries = load_seed_entries()
    if not entries:
        _logger.warning("help center seed is empty; skipping")
        return

    async with httpx.AsyncClient(timeout=5.0) as client:
        vectors = await embed_texts(
            client=client,
            api_key=api_key,
            model=model,
            texts=[e["question"] for e in entries],
        )
        if not vectors:
            _logger.warning("no embeddings returned; skipping qdrant seed")
            return

        vector_size = len(vectors[0])
        await ensure_collection(client=client, base_url=base_url, collection=collection, vector_size=vector_size)

        qpoints = [
            QdrantPoint(id=p["id"], vector=p["vector"], payload=p["payload"])
            for p in build_seed_points(entries=entries, vectors=vectors)
        ]
        await upsert_points(client=client, base_url=base_url, collection=collection, points=qpoints)

    _logger.info("seeded qdrant collection=%s entries=%s", collection, len(entries))
