import asyncio
import logging
import os
from typing import Awaitable, Callable, TypeVar

import aiohttp

T = TypeVar("T")

logger = logging.getLogger(__name__)


def retry_sync(fn: Callable[[], T], max_attempts: int) -> T:
    """Retry a callable up to max_attempts times on any exception.

    Raises the last exception if all attempts are exhausted.
    """
    last_error: BaseException | None = None
    for _ in range(max_attempts):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
    assert last_error is not None  # always set if max_attempts >= 1
    raise last_error


def daily_api_retryable(exc: BaseException) -> bool:
    """Whether a Daily / aiohttp failure is worth retrying."""
    if isinstance(exc, aiohttp.ClientResponseError):
        return exc.status >= 500 or exc.status == 429
    if isinstance(exc, aiohttp.ClientError):
        return True
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, OSError):
        return True
    return False


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int,
    base_delay_seconds: float = 0.25,
    max_delay_seconds: float = 3.0,
    retry_if: Callable[[BaseException], bool] | None = None,
    label: str = "operation",
) -> T:
    """Retry an async callable with exponential backoff (bounded).

    ``retry_if`` defaults to :func:`daily_api_retryable` when omitted.
    """
    decide = retry_if or daily_api_retryable
    last_error: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return await fn()
        except Exception as exc:
            last_error = exc
            if attempt == max_attempts - 1 or not decide(exc):
                raise
            delay = min(base_delay_seconds * (2**attempt), max_delay_seconds)
            logger.warning(
                "%s failed (attempt %s/%s): %s; retrying in %.2fs",
                label,
                attempt + 1,
                max_attempts,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error


def daily_api_max_attempts() -> int:
    raw = os.environ.get("DAILY_API_MAX_ATTEMPTS", "3").strip()
    try:
        n = int(raw)
    except ValueError:
        return 3
    return max(1, min(n, 10))
