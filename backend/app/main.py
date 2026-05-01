import logging

from fastapi import Body
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.sessions import router as sessions_router
from app.models.config import SessionConfig
from app.services.cors_origins import cors_allow_origins_from_env
from app.services.rate_limit import validate_config_limiter_from_env
from app.services.request_identity import client_ip

app = FastAPI(title="Temple-cat Backend")

_logger = logging.getLogger(__name__)
_validate_config_limiter = validate_config_limiter_from_env()


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    """Structured JSON errors without double-wrapping dict payloads in ``detail``."""
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    _logger.exception("unhandled error path=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred.",
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins_from_env(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["Accept", "Content-Type"],
)

app.include_router(sessions_router)


@app.get("/")
async def root():
    return {"status": "ok"}


@app.post("/api/validate-config")
async def validate_config(request: Request, cfg: SessionConfig = Body(...)):
    if not _validate_config_limiter.allow(client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail="Too many validation requests from this client; try again later.",
        )
    return {"valid": True, "message": "SessionConfig accepted"}
