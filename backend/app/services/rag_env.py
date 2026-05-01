"""Environment toggles for Help Center RAG (Qdrant + embeddings)."""

from __future__ import annotations

import os


def rag_enabled_from_env() -> bool:
    raw = os.environ.get("RAG_ENABLED", "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def qdrant_url_from_env() -> str:
    return os.environ.get("QDRANT_URL", "http://qdrant:6333").strip().rstrip("/")


def qdrant_collection_from_env() -> str:
    return os.environ.get("QDRANT_COLLECTION", "help_center").strip()


def qdrant_top_k_from_env() -> int:
    raw = os.environ.get("QDRANT_TOP_K", "3").strip()
    try:
        k = int(raw)
    except ValueError:
        return 3
    return max(1, min(k, 20))


def embeddings_model_from_env() -> str:
    return os.environ.get("EMBEDDINGS_MODEL", "text-embedding-3-small").strip()


def embeddings_vector_size_from_env() -> int | None:
    """Optional override when using reduced-dimension embedding models."""
    raw = os.environ.get("EMBEDDINGS_VECTOR_SIZE", "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None
