import asyncio

import aiohttp
import pytest
from unittest.mock import MagicMock

from app.services.retries import daily_api_retryable, retry_async, retry_sync


@pytest.mark.asyncio
async def test_retry_async_recovers_after_connection_error():
    attempts = {"n": 0}

    async def flaky():
        await asyncio.sleep(0)
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise aiohttp.ClientConnectionError("transient")
        return "ok"

    assert await retry_async(flaky, max_attempts=3, label="test_op") == "ok"
    assert attempts["n"] == 2


@pytest.mark.asyncio
async def test_retry_async_does_not_retry_when_retry_if_false():
    calls = {"n": 0}

    async def failing():
        await asyncio.sleep(0)
        calls["n"] += 1
        raise RuntimeError("hard fail")

    with pytest.raises(RuntimeError, match="hard fail"):
        await retry_async(failing, max_attempts=3, retry_if=lambda _e: False, label="x")
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_retry_async_does_not_retry_client_response_400():
    calls = {"n": 0}

    async def bad_request():
        await asyncio.sleep(0)
        calls["n"] += 1
        raise aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=400,
            message="Bad Request",
        )

    with pytest.raises(aiohttp.ClientResponseError):
        await retry_async(bad_request, max_attempts=3, label="http")
    assert calls["n"] == 1


def test_daily_api_retryable_5xx_and_429():
    exc_500 = aiohttp.ClientResponseError(
        request_info=MagicMock(),
        history=(),
        status=500,
        message="",
    )
    exc_429 = aiohttp.ClientResponseError(
        request_info=MagicMock(),
        history=(),
        status=429,
        message="",
    )
    exc_404 = aiohttp.ClientResponseError(
        request_info=MagicMock(),
        history=(),
        status=404,
        message="",
    )

    assert daily_api_retryable(exc_500) is True
    assert daily_api_retryable(exc_429) is True
    assert daily_api_retryable(exc_404) is False


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

    with pytest.raises(ValueError, match="permanent"):
        retry_sync(always_fails, max_attempts=3)


def test_retry_sync_succeeds_on_first_try():
    assert retry_sync(lambda: "immediate", max_attempts=3) == "immediate"
