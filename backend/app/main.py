import os

from fastapi import FastAPI
from fastapi import Body
from fastapi.middleware.cors import CORSMiddleware

from app.models.config import SessionConfig
from app.api.sessions import router as sessions_router

app = FastAPI(title="Temple-cat Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router)


@app.get("/")
async def root():
    return {"status": "ok"}


@app.post("/api/validate-config")
async def validate_config(cfg: SessionConfig = Body(...)):
    # Minimal runtime integration: validate incoming SessionConfig and acknowledge
    return {"valid": True, "message": "SessionConfig accepted"}
