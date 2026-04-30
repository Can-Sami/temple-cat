from typing import Callable, TypeVar

T = TypeVar("T")


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
