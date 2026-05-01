# Voice AI Interview Project Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Shipped on `main`:** Voice stack + optional **OpenTelemetry → Jaeger** (Compose profile `otel`). **Not shipped:** Qdrant/RAG in compose or `bot.py`. Archived Qdrant design: `docs/superpowers/specs/2026-05-01-qdrant-rag-design.md`.

**Goal:** Build and deploy a real-time configurable Voice AI app with Pipecat, Daily, live bot-state telemetry, optional Pipecat OpenTelemetry traces (Jaeger), and interview-ready docs/artifacts.

**Architecture:** Use an integration-first vertical slice: bootstrap working frontend-backend voice path first, then layer runtime config mapping, live state/latency telemetry, reliability controls, deployment polish, and optional OTLP export from bot subprocesses. Backend owns all session orchestration and emits deterministic state/timing events; frontend is a thin validated control + dashboard surface.

**Tech Stack:** Next.js (TypeScript), TanStack Query, Python (FastAPI + Pipecat), Daily transport, Deepgram, OpenAI, Cartesia, Docker Compose, Pytest, Vitest + Testing Library; optional Jaeger (OTLP) via Compose profile.

---

## File structure map

- `docker-compose.yml` — service orchestration for frontend/backend (optional `otel` profile for Jaeger)
- `.env.example` — required env vars contract
- `DEPLOY.md` — one-page deployment/runbook for EC2
- `demo/WALKTHROUGH.md` — interview walkthrough script
- `frontend/package.json` — Next.js scripts/deps
- `frontend/src/app/page.tsx` — app shell
- `frontend/src/features/session-config/SessionConfigForm.tsx` — pre-session config UI
- `frontend/src/features/session-control/SessionControlPanel.tsx` — start/stop/reconnect UI
- `frontend/src/features/dashboard/BotStateBadge.tsx` — listening/thinking/speaking indicator
- `frontend/src/features/dashboard/LatencyPanel.tsx` — latency metrics view
- `frontend/src/lib/api/client.ts` — HTTP session bootstrap client
- `frontend/src/lib/realtime/events.ts` — WebSocket/SSE event consumer
- `frontend/src/lib/state/session-store.ts` — minimal local session state reducer
- `frontend/src/features/**/__tests__/*.test.tsx` — frontend component/interaction tests
- `backend/pyproject.toml` — backend deps/scripts
- `backend/app/main.py` — FastAPI entrypoint
- `backend/app/api/sessions.py` — session create/start endpoints
- `backend/app/models/config.py` — validated input params schema
- `backend/app/services/pipeline.py` — Pipecat pipeline orchestrator
- `backend/app/services/interruptibility.py` — interruptibility mapping logic
- `backend/app/services/metrics.py` — latency calculator + event payloads
- `backend/app/services/retrieval.py` — formats retrieval context strings (tests only; no live Qdrant in shipped stack)
- `backend/app/services/retries.py` — bounded retry utility
- `backend/app/services/rate_limit.py` — request limiter
- `backend/tests/**/*.py` — backend unit tests

### Task 1: Repository scaffold and runtime contracts

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `frontend/package.json`
- Create: `backend/pyproject.toml`
- Test: `docker-compose.yml` via `docker compose config`

- [ ] **Step 1: Write the failing environment contract check**

```bash
grep -E 'OPENAI_API_KEY|DEEPGRAM_API_KEY|CARTESIA_API_KEY|DAILY_API_KEY' .env.example
```

- [ ] **Step 2: Run check to verify it fails**

Run: `grep -E 'OPENAI_API_KEY|DEEPGRAM_API_KEY|CARTESIA_API_KEY|DAILY_API_KEY' .env.example`
Expected: FAIL with `No such file or directory`

- [ ] **Step 3: Write minimal scaffold implementation**

```yaml
# docker-compose.yml
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    env_file: [.env]
    depends_on: [backend]
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: [.env]
    depends_on: [qdrant]
  qdrant:
    image: qdrant/qdrant:v1.13.2
    ports: ["6333:6333"]
    volumes: [qdrant_data:/qdrant/storage]
volumes:
  qdrant_data:
```

```dotenv
# .env.example
OPENAI_API_KEY=
DEEPGRAM_API_KEY=
CARTESIA_API_KEY=
DAILY_API_KEY=
QDRANT_URL=http://qdrant:6333
FRONTEND_ORIGIN=http://localhost:3000
```

- [ ] **Step 4: Run compose validation**

Run: `docker compose config`
Expected: PASS with normalized compose output and no schema errors

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml .env.example frontend/package.json backend/pyproject.toml
git commit -m "chore: scaffold voice ai project runtime contracts"
```

### Task 2: Backend config schema and InputParams validation

**Files:**
- Create: `backend/app/models/config.py`
- Create: `backend/tests/test_config_schema.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_config_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_config_schema.py
import pytest
from app.models.config import SessionConfig


def test_rejects_interruptibility_out_of_range():
    with pytest.raises(ValueError):
        SessionConfig(interruptibility_percentage=120)


def test_accepts_valid_config():
    cfg = SessionConfig(
        system_prompt="You are helpful",
        llm_temperature=0.4,
        llm_max_tokens=256,
        stt_temperature=0.0,
        tts_voice="sonic",
        tts_speed=1.0,
        tts_temperature=0.3,
        interruptibility_percentage=70,
    )
    assert cfg.interruptibility_percentage == 70
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_config_schema.py -v`
Expected: FAIL with `ModuleNotFoundError` for `app.models.config`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/models/config.py
from pydantic import BaseModel, Field


class SessionConfig(BaseModel):
    system_prompt: str = Field(min_length=1)
    llm_temperature: float = Field(ge=0.0, le=2.0)
    llm_max_tokens: int = Field(ge=1, le=4096)
    stt_temperature: float = Field(ge=0.0, le=1.0)
    tts_voice: str = Field(min_length=1)
    tts_speed: float = Field(ge=0.5, le=2.0)
    tts_temperature: float = Field(ge=0.0, le=1.0)
    interruptibility_percentage: int = Field(ge=0, le=100)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_config_schema.py -v`
Expected: PASS with 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/config.py backend/tests/test_config_schema.py backend/app/main.py
git commit -m "feat: add validated session config model"
```

### Task 3: Interruptibility policy mapping

**Files:**
- Create: `backend/app/services/interruptibility.py`
- Create: `backend/tests/test_interruptibility.py`
- Test: `backend/tests/test_interruptibility.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_interruptibility.py
from app.services.interruptibility import build_interruptibility_policy


def test_high_percentage_allows_fast_preemption():
    policy = build_interruptibility_policy(90)
    assert policy.min_user_speech_ms <= 120
    assert policy.preemption_aggressiveness == "high"


def test_low_percentage_requires_longer_user_speech():
    policy = build_interruptibility_policy(10)
    assert policy.min_user_speech_ms >= 280
    assert policy.preemption_aggressiveness == "low"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_interruptibility.py -v`
Expected: FAIL with `ModuleNotFoundError` for `app.services.interruptibility`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/interruptibility.py
from dataclasses import dataclass


@dataclass(frozen=True)
class InterruptibilityPolicy:
    min_user_speech_ms: int
    preemption_aggressiveness: str


def build_interruptibility_policy(percentage: int) -> InterruptibilityPolicy:
    if percentage >= 75:
        return InterruptibilityPolicy(min_user_speech_ms=100, preemption_aggressiveness="high")
    if percentage >= 40:
        return InterruptibilityPolicy(min_user_speech_ms=200, preemption_aggressiveness="medium")
    return InterruptibilityPolicy(min_user_speech_ms=300, preemption_aggressiveness="low")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_interruptibility.py -v`
Expected: PASS with 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/interruptibility.py backend/tests/test_interruptibility.py
git commit -m "feat: implement interruptibility policy mapping"
```

### Task 4: Session bootstrap API contract

**Files:**
- Create: `backend/app/api/sessions.py`
- Create: `backend/tests/test_sessions_api.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_sessions_api.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_sessions_api.py
from fastapi.testclient import TestClient
from app.main import app


def test_create_session_returns_session_id():
    client = TestClient(app)
    payload = {
        "system_prompt": "be concise",
        "llm_temperature": 0.5,
        "llm_max_tokens": 256,
        "stt_temperature": 0.0,
        "tts_voice": "sonic",
        "tts_speed": 1.0,
        "tts_temperature": 0.3,
        "interruptibility_percentage": 70,
    }
    res = client.post("/api/sessions", json=payload)
    assert res.status_code == 201
    assert "session_id" in res.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_sessions_api.py -v`
Expected: FAIL with 404 or missing route

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/api/sessions.py
from uuid import uuid4
from fastapi import APIRouter
from app.models.config import SessionConfig

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", status_code=201)
def create_session(config: SessionConfig) -> dict[str, str]:
    return {"session_id": str(uuid4())}
```

```python
# backend/app/main.py
from fastapi import FastAPI
from app.api.sessions import router as sessions_router

app = FastAPI()
app.include_router(sessions_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_sessions_api.py -v`
Expected: PASS with 1 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/sessions.py backend/app/main.py backend/tests/test_sessions_api.py
git commit -m "feat: add session bootstrap endpoint"
```

### Task 5: Pipeline orchestrator + latency metrics

**Files:**
- Create: `backend/app/services/pipeline.py`
- Create: `backend/app/services/metrics.py`
- Create: `backend/tests/test_metrics.py`
- Create: `backend/tests/test_pipeline_state_transitions.py`
- Test: `backend/tests/test_metrics.py`
- Test: `backend/tests/test_pipeline_state_transitions.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_metrics.py
from app.services.metrics import round_trip_latency_ms


def test_round_trip_latency_from_t0_to_t1():
    assert round_trip_latency_ms(10.0, 10.245) == 245
```

```python
# backend/tests/test_pipeline_state_transitions.py
from app.services.pipeline import next_state


def test_state_transitions_for_standard_turn():
    assert next_state("Listening", "user_turn_closed") == "Thinking"
    assert next_state("Thinking", "tts_started") == "Speaking"
    assert next_state("Speaking", "tts_completed") == "Listening"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_metrics.py tests/test_pipeline_state_transitions.py -v`
Expected: FAIL with missing modules/functions

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/metrics.py
def round_trip_latency_ms(t0_seconds: float, t1_seconds: float) -> int:
    return int(round((t1_seconds - t0_seconds) * 1000))
```

```python
# backend/app/services/pipeline.py
def next_state(current: str, event: str) -> str:
    transitions = {
        ("Listening", "user_turn_closed"): "Thinking",
        ("Thinking", "tts_started"): "Speaking",
        ("Speaking", "tts_completed"): "Listening",
        ("Speaking", "interrupt_detected"): "Listening",
    }
    return transitions[(current, event)]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_metrics.py tests/test_pipeline_state_transitions.py -v`
Expected: PASS with 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline.py backend/app/services/metrics.py backend/tests/test_metrics.py backend/tests/test_pipeline_state_transitions.py
git commit -m "feat: add deterministic state transitions and latency metrics"
```

### Task 6: Qdrant retrieval adapter

**Files:**
- Create: `backend/app/services/retrieval.py`
- Create: `backend/tests/test_retrieval.py`
- Test: `backend/tests/test_retrieval.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_retrieval.py
from app.services.retrieval import format_retrieval_context


def test_formats_top_k_entries_for_prompt_context():
    entries = [
        {"question": "refund policy", "answer": "30 days"},
        {"question": "shipping speed", "answer": "2 business days"},
    ]
    ctx = format_retrieval_context(entries)
    assert "Q: refund policy" in ctx
    assert "A: 30 days" in ctx
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_retrieval.py -v`
Expected: FAIL with missing module/function

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/retrieval.py
from typing import Iterable


def format_retrieval_context(entries: Iterable[dict[str, str]]) -> str:
    lines: list[str] = []
    for entry in entries:
        lines.append(f"Q: {entry['question']}")
        lines.append(f"A: {entry['answer']}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_retrieval.py -v`
Expected: PASS with 1 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/retrieval.py backend/tests/test_retrieval.py
git commit -m "feat: add qdrant retrieval context formatter"
```

### Task 7: Frontend session configuration form

**Files:**
- Create: `frontend/src/features/session-config/SessionConfigForm.tsx`
- Create: `frontend/src/features/session-config/__tests__/SessionConfigForm.test.tsx`
- Create: `frontend/src/lib/api/client.ts`
- Test: `frontend/src/features/session-config/__tests__/SessionConfigForm.test.tsx`

- [ ] **Step 1: Write the failing component test**

```tsx
// frontend/src/features/session-config/__tests__/SessionConfigForm.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionConfigForm } from "../SessionConfigForm";

test("submits valid payload including interruptibility percentage", async () => {
  const onSubmit = vi.fn();
  render(<SessionConfigForm onSubmit={onSubmit} />);
  await userEvent.type(screen.getByLabelText(/System Prompt/i), "You are concise");
  await userEvent.type(screen.getByLabelText(/Interruptibility Percentage/i), "70");
  await userEvent.click(screen.getByRole("button", { name: /Start Session/i }));
  expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ interruptibilityPercentage: 70 }));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- SessionConfigForm.test.tsx`
Expected: FAIL with missing component/test setup

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/src/features/session-config/SessionConfigForm.tsx
import { useState } from "react";

export function SessionConfigForm({ onSubmit }: { onSubmit: (payload: { systemPrompt: string; interruptibilityPercentage: number }) => void }) {
  const [systemPrompt, setSystemPrompt] = useState("");
  const [interruptibilityPercentage, setInterruptibilityPercentage] = useState(70);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({ systemPrompt, interruptibilityPercentage });
      }}
    >
      <label>
        System Prompt
        <textarea aria-label="System Prompt" value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} />
      </label>
      <label>
        Interruptibility Percentage
        <input aria-label="Interruptibility Percentage" type="number" value={interruptibilityPercentage} onChange={(e) => setInterruptibilityPercentage(Number(e.target.value))} />
      </label>
      <button type="submit">Start Session</button>
    </form>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- SessionConfigForm.test.tsx`
Expected: PASS with 1 passed

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/session-config/SessionConfigForm.tsx frontend/src/features/session-config/__tests__/SessionConfigForm.test.tsx frontend/src/lib/api/client.ts
git commit -m "feat: add session config form with interruptibility input"
```

### Task 8: Frontend session control and real-time events

**Files:**
- Create: `frontend/src/features/session-control/SessionControlPanel.tsx`
- Create: `frontend/src/lib/realtime/events.ts`
- Create: `frontend/src/lib/state/session-store.ts`
- Create: `frontend/src/features/session-control/__tests__/SessionControlPanel.test.tsx`
- Test: `frontend/src/features/session-control/__tests__/SessionControlPanel.test.tsx`

- [ ] **Step 1: Write the failing interaction test**

```tsx
// frontend/src/features/session-control/__tests__/SessionControlPanel.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionControlPanel } from "../SessionControlPanel";

test("calls onStop when Stop Session is clicked", async () => {
  const onStop = vi.fn();
  render(<SessionControlPanel isActive={true} onStart={vi.fn()} onStop={onStop} />);
  await userEvent.click(screen.getByRole("button", { name: /Stop Session/i }));
  expect(onStop).toHaveBeenCalledTimes(1);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- SessionControlPanel.test.tsx`
Expected: FAIL with missing component

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/src/features/session-control/SessionControlPanel.tsx
export function SessionControlPanel({
  isActive,
  onStart,
  onStop,
}: {
  isActive: boolean;
  onStart: () => void;
  onStop: () => void;
}) {
  return isActive ? <button onClick={onStop}>Stop Session</button> : <button onClick={onStart}>Start Session</button>;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- SessionControlPanel.test.tsx`
Expected: PASS with 1 passed

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/session-control/SessionControlPanel.tsx frontend/src/lib/realtime/events.ts frontend/src/lib/state/session-store.ts frontend/src/features/session-control/__tests__/SessionControlPanel.test.tsx
git commit -m "feat: add session controls and realtime event scaffolding"
```

### Task 9: Dashboard state badge and latency panel

**Files:**
- Create: `frontend/src/features/dashboard/BotStateBadge.tsx`
- Create: `frontend/src/features/dashboard/LatencyPanel.tsx`
- Create: `frontend/src/features/dashboard/__tests__/Dashboard.test.tsx`
- Test: `frontend/src/features/dashboard/__tests__/Dashboard.test.tsx`

- [ ] **Step 1: Write the failing dashboard test**

```tsx
// frontend/src/features/dashboard/__tests__/Dashboard.test.tsx
import { render, screen } from "@testing-library/react";
import { BotStateBadge } from "../BotStateBadge";
import { LatencyPanel } from "../LatencyPanel";

test("renders speaking state and latency value", () => {
  render(
    <>
      <BotStateBadge state="Speaking" />
      <LatencyPanel latencyMs={245} />
    </>
  );
  expect(screen.getByText(/Speaking/i)).toBeInTheDocument();
  expect(screen.getByText(/245 ms/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- Dashboard.test.tsx`
Expected: FAIL with missing components

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/src/features/dashboard/BotStateBadge.tsx
export function BotStateBadge({ state }: { state: "Listening" | "Thinking" | "Speaking" }) {
  return <div aria-label="Bot State">{state}</div>;
}
```

```tsx
// frontend/src/features/dashboard/LatencyPanel.tsx
export function LatencyPanel({ latencyMs }: { latencyMs: number }) {
  return <div aria-label="Round Trip Latency">{latencyMs} ms</div>;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- Dashboard.test.tsx`
Expected: PASS with 1 passed

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/dashboard/BotStateBadge.tsx frontend/src/features/dashboard/LatencyPanel.tsx frontend/src/features/dashboard/__tests__/Dashboard.test.tsx
git commit -m "feat: add bot state and latency dashboard components"
```

### Task 10: Hardening (rate limit, retries, CORS, error surface)

**Files:**
- Create: `backend/app/services/retries.py`
- Create: `backend/app/services/rate_limit.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_retries.py`
- Create: `backend/tests/test_rate_limit.py`
- Test: `backend/tests/test_retries.py`
- Test: `backend/tests/test_rate_limit.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_retries.py
from app.services.retries import retry_sync


def test_retry_sync_succeeds_after_transient_failure():
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("temporary")
        return "ok"

    assert retry_sync(flaky, max_attempts=2) == "ok"
```

```python
# backend/tests/test_rate_limit.py
from app.services.rate_limit import InMemoryRateLimiter


def test_rate_limiter_blocks_after_threshold():
    limiter = InMemoryRateLimiter(limit=2)
    key = "session-1"
    assert limiter.allow(key) is True
    assert limiter.allow(key) is True
    assert limiter.allow(key) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_retries.py tests/test_rate_limit.py -v`
Expected: FAIL with missing modules

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/retries.py
def retry_sync(fn, max_attempts: int):
    last_error = None
    for _ in range(max_attempts):
        try:
            return fn()
        except Exception as exc:  # controlled wrapper in a single utility
            last_error = exc
    raise last_error
```

```python
# backend/app/services/rate_limit.py
class InMemoryRateLimiter:
    def __init__(self, limit: int):
        self.limit = limit
        self.counts: dict[str, int] = {}

    def allow(self, key: str) -> bool:
        next_count = self.counts.get(key, 0) + 1
        self.counts[key] = next_count
        return next_count <= self.limit
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_retries.py tests/test_rate_limit.py -v`
Expected: PASS with 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/retries.py backend/app/services/rate_limit.py backend/app/main.py backend/tests/test_retries.py backend/tests/test_rate_limit.py
git commit -m "feat: add reliability and basic rate limiting controls"
```

### Task 11: Deployment and interview artifacts

**Files:**
- Create: `DEPLOY.md`
- Create: `demo/WALKTHROUGH.md`
- Modify: `docker-compose.yml`
- Test: smoke startup command and service status

- [ ] **Step 1: Write the failing smoke command**

```bash
docker compose up -d
```

- [ ] **Step 2: Run smoke command to capture current failure**

Run: `docker compose up -d`
Expected: FAIL before final wiring is complete

- [ ] **Step 3: Write minimal deployment docs and final compose wiring**

```md
# DEPLOY.md
- Region/AMI/instance type
- Security group ports (22, 80/443, 3000, 8000)
- Compose service wiring
- Log paths and restart after reboot
```

```md
# demo/WALKTHROUGH.md
1. Show config panel and custom prompt.
2. Start session and speak.
3. Demonstrate interruption and state shift (including **Interrupted** badge when talking over the bot).
4. Show latency metric and (optional) Pipecat traces in Jaeger (`docker compose --profile otel`).
5. Show deployment command and running services.
```

- [ ] **Step 4: Run final smoke checks**

Run: `docker compose up -d && docker compose ps`
Expected: PASS with `frontend`, `backend` (and optionally `jaeger` when profile `otel` is enabled) in running/healthy state

- [ ] **Step 5: Commit**

```bash
git add DEPLOY.md demo/WALKTHROUGH.md docker-compose.yml
git commit -m "docs: add deploy runbook and interview walkthrough artifacts"
```

---

> ⚠️ **AMENDMENT — Pipecat Integration Tasks** (added after architecture review)
> 
> Tasks 1–11 build all the pure-logic units and frontend UI scaffolding. Tasks 12–14 wire everything
> into a real, running voice bot using Pipecat as intended: Daily room provisioning, subprocess-spawned
> bot process, RTVI event protocol, and `@pipecat-ai/client-js` on the frontend.

---

### Task 12: Pipecat bot process (`backend/bot.py`)

This is the core voice pipeline. It runs as a **subprocess** per session, joining a Daily room and
orchestrating the full STT → LLM → TTS chain with interruptibility support.

**Files:**
- Create: `backend/bot.py`
- Create: `backend/tests/test_bot_pipeline_unit.py`
- Modify: `backend/pyproject.toml` (add pipecat-ai deps)
- Test: `backend/tests/test_bot_pipeline_unit.py`

- [ ] **Step 1: Write the failing unit test**

```python
# backend/tests/test_bot_pipeline_unit.py
# Unit tests for bot.py helper logic only — no live Daily/Pipecat calls
from bot import build_system_messages, build_vad_stop_secs


def test_build_system_messages_wraps_prompt():
    msgs = build_system_messages("You are helpful")
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "You are helpful"


def test_build_vad_stop_secs_high_interruptibility():
    # High interruptibility → shorter VAD stop (bot yields faster)
    stop_secs = build_vad_stop_secs(interruptibility_percentage=90)
    assert stop_secs <= 0.25


def test_build_vad_stop_secs_low_interruptibility():
    # Low interruptibility → longer VAD stop (bot holds the floor)
    stop_secs = build_vad_stop_secs(interruptibility_percentage=10)
    assert stop_secs >= 0.55
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_bot_pipeline_unit.py -v`
Expected: FAIL with `ModuleNotFoundError` for `bot`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/bot.py
"""
Pipecat voice bot — spawned as a subprocess by the session endpoint.

Usage:
    python bot.py --room-url <url> --token <token> --config <json>

The --config JSON must match the SessionConfig schema:
    system_prompt, llm_temperature, llm_max_tokens,
    stt_temperature, tts_voice, tts_speed, tts_temperature,
    interruptibility_percentage
"""
import argparse
import asyncio
import json
import os

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.processors.aggregators.openai_llm_context import (
    OpenAILLMContext,
    OpenAILLMContextAggregatorPair,
)
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport

from app.services.interruptibility import build_interruptibility_policy
from app.services.metrics import round_trip_latency_ms


def build_system_messages(system_prompt: str) -> list[dict]:
    """Wrap the user-supplied prompt as an OpenAI system message."""
    return [{"role": "system", "content": system_prompt}]


def build_vad_stop_secs(interruptibility_percentage: int) -> float:
    """Map interruptibility % to Silero VAD stop_secs.

    High interruptibility → short stop_secs (bot yields to user quickly).
    Low interruptibility  → long stop_secs  (bot holds the floor).
    """
    policy = build_interruptibility_policy(interruptibility_percentage)
    # Map min_user_speech_ms linearly to VAD stop_secs range [0.15, 0.80]
    # policy.min_user_speech_ms is in [100, 300] from our interruptibility service
    clamped = max(100, min(300, policy.min_user_speech_ms))
    return 0.15 + (clamped - 100) / 200 * 0.65  # maps 100→0.15, 300→0.80


async def run_bot(room_url: str, token: str, config: dict) -> None:
    transport = DailyTransport(
        room_url,
        token,
        "VoiceBot",
        DailyParams(audio_in_enabled=True, audio_out_enabled=True),
    )

    stt = DeepgramSTTService(
        api_key=os.environ["DEEPGRAM_API_KEY"],
    )

    llm = OpenAILLMService(
        api_key=os.environ["OPENAI_API_KEY"],
        model="gpt-4o",
        params=OpenAILLMService.InputParams(
            temperature=config["llm_temperature"],
            max_tokens=config["llm_max_tokens"],
        ),
    )

    tts = CartesiaTTSService(
        api_key=os.environ["CARTESIA_API_KEY"],
        voice_id=config["tts_voice"],
        params=CartesiaTTSService.InputParams(
            speed=config["tts_speed"],
        ),
    )

    context = OpenAILLMContext(
        messages=build_system_messages(config["system_prompt"])
    )

    vad_stop_secs = build_vad_stop_secs(config["interruptibility_percentage"])
    context_aggregator = OpenAILLMContextAggregatorPair(
        llm,
        context,
        vad_analyzer=SileroVADAnalyzer(params=dict(stop_secs=vad_stop_secs)),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            context_aggregator.assistant(),
            transport.output(),
        ]
    )

    task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))
    runner = PipelineRunner()
    await runner.run(task)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--room-url", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--config", required=True, help="JSON-encoded SessionConfig")
    args = parser.parse_args()

    config = json.loads(args.config)
    asyncio.run(run_bot(args.room_url, args.token, config))
```

Add pipecat-ai deps to `backend/pyproject.toml`:
```toml
dependencies = [
  "fastapi>=0.95",
  "uvicorn[standard]>=0.22",
  "qdrant-client>=1.3",
  "pipecat-ai[daily,deepgram,openai,cartesia,silero]>=0.0.50",
  "aiohttp>=3.9",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_bot_pipeline_unit.py -v`
Expected: PASS with 3 passed (pure unit tests, no network calls)

- [ ] **Step 5: Commit**

```bash
git add backend/bot.py backend/tests/test_bot_pipeline_unit.py backend/pyproject.toml
git commit -m "feat: add pipecat voice bot pipeline with interruptibility and VAD"
```

---

### Task 13: Upgrade session endpoint — Daily room provisioning + bot subprocess

Amend `POST /api/sessions` so it actually creates a Daily room, mints tokens, spawns `bot.py` as a
subprocess, and returns `{session_id, room_url, token}` to the frontend.

**Files:**
- Modify: `backend/app/api/sessions.py`
- Create: `backend/app/services/daily_helper.py`
- Create: `backend/tests/test_daily_helper.py`
- Modify: `backend/tests/test_sessions_api.py`
- Test: `backend/tests/test_daily_helper.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_daily_helper.py
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.daily_helper import provision_daily_session


async def test_provision_daily_session_returns_room_and_token():
    mock_room = MagicMock()
    mock_room.url = "https://example.daily.co/test-room"

    with (
        patch("app.services.daily_helper.DailyRESTHelper") as MockHelper,
        patch("app.services.daily_helper.aiohttp.ClientSession"),
    ):
        helper_instance = MockHelper.return_value.__aenter__.return_value
        helper_instance.create_room = AsyncMock(return_value=mock_room)
        helper_instance.get_token = AsyncMock(return_value="test-token-xyz")

        result = await provision_daily_session(api_key="fake-key")

    assert result["room_url"] == "https://example.daily.co/test-room"
    assert result["token"] == "test-token-xyz"
```

Also update `test_sessions_api.py` to assert response now includes `room_url` and `token`:
```python
def test_create_session_response_includes_room_url_and_token(mocker):
    mocker.patch(
        "app.api.sessions.provision_daily_session",
        return_value={"room_url": "https://daily.co/room", "token": "tok"},
    )
    mocker.patch("app.api.sessions.spawn_bot_process")
    client = TestClient(app)
    res = client.post("/api/sessions", json=_VALID_PAYLOAD)
    assert res.status_code == 201
    body = res.json()
    assert "session_id" in body
    assert body["room_url"] == "https://daily.co/room"
    assert body["token"] == "tok"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_daily_helper.py tests/test_sessions_api.py -v`
Expected: FAIL with missing modules/updated contract

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/daily_helper.py
import os
import aiohttp
from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper, DailyRoomParams


async def provision_daily_session(api_key: str | None = None) -> dict[str, str]:
    """Create a Daily room and mint a bot token. Returns room_url and token."""
    key = api_key or os.environ["DAILY_API_KEY"]
    async with aiohttp.ClientSession() as session:
        helper = DailyRESTHelper(daily_api_key=key, aiohttp_session=session)
        room = await helper.create_room(DailyRoomParams())
        token = await helper.get_token(room.url)
    return {"room_url": room.url, "token": token}
```

```python
# backend/app/services/bot_launcher.py
import json
import subprocess
import sys


def spawn_bot_process(room_url: str, token: str, config: dict) -> None:
    """Fire-and-forget: spawn bot.py as a detached subprocess."""
    subprocess.Popen(
        [
            sys.executable,
            "bot.py",
            "--room-url", room_url,
            "--token", token,
            "--config", json.dumps(config),
        ],
        # Detach so the runner process doesn't block on the bot
        start_new_session=True,
    )
```

Update `backend/app/api/sessions.py`:
```python
from uuid import uuid4
from fastapi import APIRouter
from app.models.config import SessionConfig
from app.services.daily_helper import provision_daily_session
from app.services.bot_launcher import spawn_bot_process

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", status_code=201)
async def create_session(config: SessionConfig) -> dict:
    """Provision a Daily room, spawn the Pipecat bot, return join credentials."""
    daily = await provision_daily_session()
    spawn_bot_process(daily["room_url"], daily["token"], config.model_dump())
    return {
        "session_id": str(uuid4()),
        "room_url": daily["room_url"],
        "token": daily["token"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_daily_helper.py tests/test_sessions_api.py -v`
Expected: PASS (mocked Daily calls, real schema validation)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/daily_helper.py backend/app/services/bot_launcher.py backend/app/api/sessions.py backend/tests/test_daily_helper.py backend/tests/test_sessions_api.py
git commit -m "feat: upgrade session endpoint to provision Daily room and spawn pipecat bot"
```

---

### Task 14: Frontend Daily + RTVI integration

Wire the Next.js frontend to actually join the Daily room using `@pipecat-ai/client-js` and
`@pipecat-ai/daily-transport`, subscribe to RTVI bot-state events, and drive the
`BotStateBadge` + `LatencyPanel` with live data.

**Files:**
- Modify: `frontend/package.json` (add pipecat + daily deps)
- Create: `frontend/src/lib/realtime/pipecat-client.ts`
- Modify: `frontend/src/lib/state/session-store.ts`
- Create: `frontend/src/features/session-control/__tests__/pipecat-client.test.ts`
- Test: `frontend/src/features/session-control/__tests__/pipecat-client.test.ts`

- [ ] **Step 1: Write the failing unit test**

```ts
// frontend/src/features/session-control/__tests__/pipecat-client.test.ts
import { describe, it, expect, vi } from "vitest";
import { createPipecatClient } from "../../../lib/realtime/pipecat-client";

describe("createPipecatClient", () => {
  it("returns a client object with connect and disconnect methods", () => {
    const client = createPipecatClient({
      roomUrl: "https://example.daily.co/room",
      token: "tok",
      onStateChange: vi.fn(),
      onLatency: vi.fn(),
    });
    expect(typeof client.connect).toBe("function");
    expect(typeof client.disconnect).toBe("function");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- pipecat-client.test.ts`
Expected: FAIL with missing module

- [ ] **Step 3: Write minimal implementation**

Add to `frontend/package.json` dependencies:
```json
"@pipecat-ai/client-js": "^0.3",
"@pipecat-ai/daily-transport": "^0.3",
"@daily-co/daily-js": "^0.64"
```

```ts
// frontend/src/lib/realtime/pipecat-client.ts
import { PipecatClient, RTVIEvent } from "@pipecat-ai/client-js";
import { DailyTransport } from "@pipecat-ai/daily-transport";

export type BotState = "Listening" | "Thinking" | "Speaking";

export interface PipecatClientOptions {
  roomUrl: string;
  token: string;
  onStateChange: (state: BotState) => void;
  onLatency: (ms: number) => void;
}

export function createPipecatClient(opts: PipecatClientOptions) {
  const client = new PipecatClient({
    transport: new DailyTransport(),
    enableMic: true,
  });

  let userSilenceAt: number | null = null;

  client.on(RTVIEvent.BotStartedSpeaking, () => {
    if (userSilenceAt != null) {
      opts.onLatency(Date.now() - userSilenceAt);
      userSilenceAt = null;
    }
    opts.onStateChange("Speaking");
  });

  client.on(RTVIEvent.BotStoppedSpeaking, () => {
    opts.onStateChange("Listening");
  });

  client.on(RTVIEvent.UserStartedSpeaking, () => {
    opts.onStateChange("Listening");
  });

  client.on(RTVIEvent.UserStoppedSpeaking, () => {
    userSilenceAt = Date.now();
    opts.onStateChange("Thinking");
  });

  return {
    connect: () =>
      client.connect({
        endpoint: opts.roomUrl,
        token: opts.token,
      }),
    disconnect: () => client.disconnect(),
  };
}
```

Update `frontend/src/lib/state/session-store.ts` to expose `botState` and `latencyMs` driven by the
RTVI client above, consumed by `BotStateBadge` and `LatencyPanel` via React state or TanStack Query.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- pipecat-client.test.ts`
Expected: PASS with 1 passed

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/realtime/pipecat-client.ts frontend/src/lib/state/session-store.ts frontend/package.json frontend/src/features/session-control/__tests__/pipecat-client.test.ts
git commit -m "feat: integrate pipecat client-js and daily transport for live bot state events"
```

---

## Updated self-review checklist

- Spec coverage: shipped tasks — config ✅, pipeline ✅, real Pipecat wiring ✅,
  state sync via RTVI ✅, latency ✅, optional OpenTelemetry/Jaeger ✅, security ✅, tests ✅, deploy/docs ✅. Qdrant RAG archived only (`docs/superpowers/specs/2026-05-01-qdrant-rag-design.md`).
- Tasks 12–14 use Pipecat as officially recommended: bot.py subprocess pattern, DailyRESTHelper
  for room provisioning, SileroVADAnalyzer for interruptibility, RTVI protocol for state events.
- No fake SSE invented — RTVI + `@pipecat-ai/client-js` is the canonical event channel.
- Interruptibility maps to `SileroVADAnalyzer stop_secs` — the correct Pipecat 1.0+ API.
- `allow_interruptions` legacy flag kept in `PipelineParams` as fallback; primary control is VAD.
- Placeholder scan: no TODO/TBD used.
- Type consistency: naming consistent across all tasks.
```
