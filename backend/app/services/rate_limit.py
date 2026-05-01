import os
import time
from collections import deque


class InMemoryRateLimiter:
    """Simple per-key request counter rate limiter.

    Tracks the number of times each key has called allow() and
    returns False once the count exceeds the configured limit.

    Note: counts are never reset — suitable for hard lifetime caps in tests.
    """

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.counts: dict[str, int] = {}

    def allow(self, key: str) -> bool:
        next_count = self.counts.get(key, 0) + 1
        self.counts[key] = next_count
        return next_count <= self.limit


class SlidingWindowRateLimiter:
    """Fixed sliding-window limiter: at most ``max_requests`` per ``window_seconds`` per key."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        if max_requests < 1:
            raise ValueError("max_requests must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        dq = self._hits.setdefault(key, deque())
        while dq and now - dq[0] > self.window_seconds:
            dq.popleft()
        if len(dq) >= self.max_requests:
            return False
        dq.append(now)
        return True


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def session_creation_limiter_from_env() -> SlidingWindowRateLimiter:
    """Limiter for POST /api/sessions (Daily room + bot spawn)."""
    return SlidingWindowRateLimiter(
        max_requests=_env_int("SESSION_RATE_LIMIT_MAX", 30),
        window_seconds=_env_float("SESSION_RATE_LIMIT_WINDOW_SECONDS", 60.0),
    )


def validate_config_limiter_from_env() -> SlidingWindowRateLimiter:
    """Limiter for POST /api/validate-config (cheap but abuse-prone)."""
    return SlidingWindowRateLimiter(
        max_requests=_env_int("VALIDATE_CONFIG_RATE_LIMIT_MAX", 120),
        window_seconds=_env_float("VALIDATE_CONFIG_RATE_LIMIT_WINDOW_SECONDS", 60.0),
    )
