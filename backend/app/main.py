from fastapi import Body
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.sessions import router as sessions_router
from app.models.config import SessionConfig
from app.services.cors_origins import cors_allow_origins_from_env
from app.services.rate_limit import validate_config_limiter_from_env
from app.services.request_identity import client_ip

app = FastAPI(title="Temple-cat Backend")

_validate_config_limiter = validate_config_limiter_from_env()

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
