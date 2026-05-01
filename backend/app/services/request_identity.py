import os

from starlette.requests import Request


def client_ip(request: Request) -> str:
    """Best-effort client IP for rate limiting.

    Honors ``X-Forwarded-For`` only when ``TRUST_PROXY_HEADERS`` is truthy
    (set when running behind nginx/ALB/Cloudflare).
    """
    if os.environ.get("TRUST_PROXY_HEADERS", "").lower() in ("1", "true", "yes"):
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
