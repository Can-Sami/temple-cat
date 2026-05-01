import time

from app.services.rate_limit import InMemoryRateLimiter, SlidingWindowRateLimiter


def test_sliding_window_blocks_then_allows_after_window():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=0.05)
    key = "client-a"
    assert limiter.allow(key) is True
    assert limiter.allow(key) is True
    assert limiter.allow(key) is False
    time.sleep(0.06)
    assert limiter.allow(key) is True


def test_sliding_window_tracks_keys_independently():
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60.0)
    assert limiter.allow("a") is True
    assert limiter.allow("b") is True
    assert limiter.allow("a") is False


def test_sliding_window_rejects_invalid_constructor():
    import pytest

    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(max_requests=0, window_seconds=1.0)
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(max_requests=1, window_seconds=0.0)


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
