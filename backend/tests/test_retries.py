from app.services.retries import retry_sync


def test_retry_sync_succeeds_after_transient_failure():
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("temporary")
        return "ok"

    assert retry_sync(flaky, max_attempts=2) == "ok"


def test_retry_sync_raises_after_exhausting_attempts():
    def always_fails():
        raise ValueError("permanent")

    import pytest
    with pytest.raises(ValueError, match="permanent"):
        retry_sync(always_fails, max_attempts=3)


def test_retry_sync_succeeds_on_first_try():
    assert retry_sync(lambda: "immediate", max_attempts=3) == "immediate"
