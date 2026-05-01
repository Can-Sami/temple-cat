from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.services.openai_embeddings import embeddings_model_from_env, embed_texts
from app.services.qdrant_http import qdrant_collection_from_env, qdrant_top_k_from_env, qdrant_url_from_env, search
from app.services.retrieval import format_retrieval_context
from app.services.retrieval_seed import rag_enabled_from_env

_logger = logging.getLogger(__name__)


def build_help_center_context_block(entries: list[dict[str, str]]) -> str:
    if not entries:
        return ""
    formatted = format_retrieval_context(entries)
    if not formatted:
        return ""
    return "\n".join(
        [
            "Help Center Context (retrieved; may be incomplete):",
            "-----",
            formatted,
            "-----",
        ]
    )


async def retrieve_help_center(query: str) -> list[dict[str, str]]:
    if not rag_enabled_from_env():
        return []

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return []

    q = query.strip()
    if not q:
        return []

    base_url = qdrant_url_from_env()
    collection = qdrant_collection_from_env()
    top_k = qdrant_top_k_from_env()
    model = embeddings_model_from_env()

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            vectors = await embed_texts(client=client, api_key=api_key, model=model, texts=[q])
            if not vectors:
                return []
            hits = await search(
                client=client,
                base_url=base_url,
                collection=collection,
                vector=vectors[0],
                limit=top_k,
                with_payload=True,
            )
    except Exception:
        _logger.exception("rag retrieval failed; continuing without context")
        return []

    entries: list[dict[str, str]] = []
    for hit in hits:
        payload = hit.get("payload") if isinstance(hit, dict) else None
        if not isinstance(payload, dict):
            continue
        qv = payload.get("question")
        av = payload.get("answer")
        if isinstance(qv, str) and isinstance(av, str):
            entries.append({"question": qv, "answer": av})
    return entries


async def maybe_build_help_center_system_message(user_text: str) -> dict[str, Any] | None:
    entries = await retrieve_help_center(user_text)
    block = build_help_center_context_block(entries)
    if not block:
        return None
    return {"role": "system", "content": block}

