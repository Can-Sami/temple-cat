"""Normalize ``OPENAI_API_KEY`` — paste/shell artifacts break Bearer auth with 401."""

from __future__ import annotations

import os


def normalize_openai_api_key(raw: str) -> str:
    """Trim key string; strip wrapping quotes and stray trailing ``>`` / backticks."""
    key = (raw or "").strip()
    if not key:
        return ""
    if (key.startswith('"') and key.endswith('"')) or (key.startswith("'") and key.endswith("'")):
        key = key[1:-1].strip()
    while key.endswith((">", "`")):
        key = key[:-1].strip()
    return key


def openai_api_key_from_env() -> str:
    return normalize_openai_api_key(os.environ.get("OPENAI_API_KEY") or "")
