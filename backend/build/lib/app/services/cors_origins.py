"""Build CORS allow_origins from environment (no wildcard by default)."""

from __future__ import annotations

import os


def cors_allow_origins_from_env() -> list[str]:
    """Parse ``FRONTEND_ORIGIN`` into a list for Starlette CORSMiddleware.

    - Comma-separated HTTPS/HTTP origins (whitespace trimmed).
    - If unset or empty, defaults to ``http://localhost:3000`` for local dev.
    - ``FRONTEND_ORIGIN=*`` opts into permissive CORS (discouraged; emergencies only).
    """
    raw = os.environ.get("FRONTEND_ORIGIN", "").strip()
    if not raw:
        return ["http://localhost:3000"]
    if raw == "*":
        return ["*"]
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins if origins else ["http://localhost:3000"]
