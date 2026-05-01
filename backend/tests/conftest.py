import sys
import os

import pytest
from unittest.mock import AsyncMock, patch

# Ensure tests can import 'app' package when run from repo root or CI
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(autouse=True)
def _disable_rag_for_unit_tests(monkeypatch):
    """Avoid retrieval during bot tests; API tests patch startup seed separately."""
    monkeypatch.setenv("RAG_ENABLED", "0")


@pytest.fixture
def client(monkeypatch):
    """FastAPI TestClient with Help Center seed skipped (no Docker Qdrant required)."""
    monkeypatch.setenv("RAG_ENABLED", "0")
    from fastapi.testclient import TestClient

    from app.main import app

    with patch("app.main.seed_help_center_safe", new_callable=AsyncMock):
        with TestClient(app) as test_client:
            yield test_client
