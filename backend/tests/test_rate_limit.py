from app.services.rate_limit import InMemoryRateLimiter


def test_rate_limiter_blocks_after_threshold():
    limiter = InMemoryRateLimiter(limit=2)
    key = "session-1"
    assert limiter.allow(key) is True
    assert limiter.allow(key) is True
    assert limiter.allow(key) is False


def test_rate_limiter_tracks_keys_independently():
    limiter = InMemoryRateLimiter(limit=1)
    assert limiter.allow("key-a") is True
    assert limiter.allow("key-b") is True  # different key, should pass
    assert limiter.allow("key-a") is False  # key-a exhausted


def test_rate_limiter_limit_of_zero_always_blocks():
    limiter = InMemoryRateLimiter(limit=0)
    assert limiter.allow("any-key") is False
