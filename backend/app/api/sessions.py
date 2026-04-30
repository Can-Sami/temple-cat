from uuid import uuid4

from fastapi import APIRouter

from app.models.config import SessionConfig

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", status_code=201)
def create_session(config: SessionConfig) -> dict[str, str]:
    """Bootstrap a new voice session and return its ID.

    The config is validated by the SessionConfig Pydantic model (FastAPI
    automatically returns 422 on any validation failure).  A UUID is minted
    per-call; downstream tasks will attach pipeline state to it.
    """
    return {"session_id": str(uuid4())}
