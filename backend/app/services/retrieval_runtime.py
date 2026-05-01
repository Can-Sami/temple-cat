"""Per-turn Help Center retrieval (Qdrant + OpenAI embeddings)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.services.openai_embeddings import embed_texts_openai
from app.services.openai_key_env import openai_api_key_from_env
from app.services.qdrant_http import search_points
from app.services.rag_env import (
    embeddings_model_from_env,
    qdrant_collection_from_env,
    qdrant_top_k_from_env,
    qdrant_url_from_env,
    rag_enabled_from_env,
)
from app.services.retrieval import format_retrieval_context
from app.services.retries import httpx_retryable, retry_async

_logger = logging.getLogger(__name__)

HELP_CENTER_CONTEXT_HEADER = "### Help Center Context (retrieved; may be incomplete)"

REQUEST_TIMEOUT_S = 5.0


def build_help_center_context_block(entries: list[dict[str, str]]) -> str:
    """Full second-system-message body (header + formatted Q&A)."""
    body = format_retrieval_context(entries)
    if not body:
        return ""
    return f"{HELP_CENTER_CONTEXT_HEADER}\n\n{body}"


def _is_help_center_system_message(message: Any) -> bool:
    if not isinstance(message, dict):
        return False
    if message.get("role") != "system":
        return False
    content = message.get("content")
    if isinstance(content, str) and content.startswith(HELP_CENTER_CONTEXT_HEADER):
        return True
    return False


def strip_help_center_messages(messages: list[Any]) -> list[Any]:
    return [m for m in messages if not _is_help_center_system_message(m)]


def _user_message_text(message: dict[str, Any]) -> str | None:
    content = message.get("content")
    if isinstance(content, str):
        t = content.strip()
        return t or None
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        t = " ".join(parts).strip()
        return t or None
    return None


def latest_user_query_text(messages: list[Any]) -> str | None:
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            return _user_message_text(m)
    return None


def insert_help_center_system_message(messages: list[Any], content: str) -> list[Any]:
    """Insert Help Center system block immediately after the first system message."""
    msg: dict[str, Any] = {"role": "system", "content": content}
    out = list(messages)
    insert_at = 0
    for i, m in enumerate(out):
        if isinstance(m, dict) and m.get("role") == "system":
            insert_at = i + 1
            break
    out.insert(insert_at, msg)
    return out


async def retrieve_help_center_entries(query: str, *, client: httpx.AsyncClient | None = None) -> list[dict[str, str]]:
    """Return top-k Q&A payload dicts for ``query``. Empty list if disabled or on failure."""
    if not rag_enabled_from_env():
        return []

    q = query.strip()
    if not q:
        return []

    api_key = openai_api_key_from_env()
    if not api_key:
        return []

    base = qdrant_url_from_env()
    collection = qdrant_collection_from_env()
    top_k = qdrant_top_k_from_env()
    model = embeddings_model_from_env()

    async def run(http: httpx.AsyncClient) -> list[dict[str, str]]:
        async def embed_job():
            vecs = await embed_texts_openai(
                [q],
                api_key=api_key,
                model=model,
                timeout_seconds=REQUEST_TIMEOUT_S,
                client=http,
            )
            return vecs[0] if vecs else []

        vector = await retry_async(embed_job, max_attempts=2, retry_if=httpx_retryable, label="openai_embed_query")
        if not vector:
            return []

        async def search_job():
            hits = await search_points(
                base,
                collection,
                vector=vector,
                limit=top_k,
                timeout=REQUEST_TIMEOUT_S,
                client=http,
            )
            return hits

        hits = await retry_async(search_job, max_attempts=2, retry_if=httpx_retryable, label="qdrant_search")

        entries: list[dict[str, str]] = []
        for hit in hits:
            payload = hit.get("payload")
            if not isinstance(payload, dict):
                continue
            qq = str(payload.get("question", "")).strip()
            aa = str(payload.get("answer", "")).strip()
            if qq and aa:
                entries.append({"question": qq, "answer": aa})
        return entries

    try:
        if client is not None:
            return await run(client)
        async with httpx.AsyncClient() as http:
            return await run(http)
    except Exception:
        _logger.warning("Help Center retrieval failed; continuing without injected context", exc_info=True)
        return []
