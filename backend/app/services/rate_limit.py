class InMemoryRateLimiter:
    """Simple per-key request counter rate limiter.

    Tracks the number of times each key has called allow() and
    returns False once the count exceeds the configured limit.

    Note: counts are never reset — suitable for per-session
    lifetime limits (e.g. max sessions per IP). For time-window
    rate limiting, replace this with a sliding-window implementation.
    """

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.counts: dict[str, int] = {}

    def allow(self, key: str) -> bool:
        next_count = self.counts.get(key, 0) + 1
        self.counts[key] = next_count
        return next_count <= self.limit
