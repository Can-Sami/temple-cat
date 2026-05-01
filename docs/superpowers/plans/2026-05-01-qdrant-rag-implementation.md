# Qdrant Help Center RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a production-minded Qdrant + OpenAI-embeddings RAG add-on: `docker compose up -d` brings up `qdrant`, backend seeds help-center Q&A, and each user utterance retrieves top-k Q&A and injects it into the LLM prompt for that turn.

**Architecture:** Add a `qdrant` service to compose, a small backend retrieval subsystem that talks to Qdrant via HTTP and calls OpenAI embeddings via HTTP, seed a committed Q&A fixture on backend startup, and wire per-turn retrieval into `backend/bot.py` by appending a delimited system message to the `LLMContext` before each LLM call.

**Tech Stack:** Docker Compose, Qdrant (REST), FastAPI, httpx, Pipecat, OpenAI embeddings API (HTTP).

---

## File structure (creates/modifies)

**Create:**
- `backend/app/data/help_center_seed.json` — artificial help-center Q&A seed set
- `backend/app/services/qdrant_http.py` — minimal Qdrant REST client (create collection, upsert, search)
- `backend/app/services/openai_embeddings.py` — minimal OpenAI embeddings HTTP client
- `backend/app/services/retrieval_seed.py` — idempotent seeding logic
- `backend/app/services/retrieval_runtime.py` — per-query retrieval + prompt block builder
- `backend/tests/test_retrieval_seed.py` — seed idempotency + point-id tests (mocked HTTP)
- `backend/tests/test_rag_prompt_injection.py` — prompt injection formatting tests

**Modify:**
- `docker-compose.yml` — add `qdrant` service + volume + healthchecks + backend env
- `.env.example` — add Qdrant/RAG env vars
- `backend/app/main.py` — add FastAPI lifespan startup hook to seed Qdrant
- `backend/bot.py` — wire retrieval into per-turn LLM context
- `DEPLOY.md` — document qdrant service, env vars, logs, ports, restart
- `demo/WALKTHROUGH.md` — make the walkthrough match reality (qdrant exists + how to demo)

---

## Task 1: Add Qdrant to Docker Compose

**Files:**
- Modify: `docker-compose.yml`
- Create/modify: (none)

- [ ] **Step 1: Edit `docker-compose.yml` to include `qdrant`**
  - Add service:
    - image: `qdrant/qdrant:v1.13.2`
    - port mapping: `6333:6333` (for local debugging; in EC2 you can choose to not expose publicly)
    - volume: `qdrant_data:/qdrant/storage`
    - healthcheck: `GET http://localhost:6333/healthz` (or equivalent)
  - Make `backend` depend on `qdrant` with `condition: service_healthy`
  - Add `QDRANT_URL=http://qdrant:6333` to backend environment

- [ ] **Step 2: Verify compose parses**
  - Run: `docker compose config`
  - Expected: exits 0

---

## Task 2: Add env vars + docs for Qdrant/RAG knobs

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Add env vars**
  - Add:
    - `QDRANT_URL=http://qdrant:6333`
    - `QDRANT_COLLECTION=help_center`
    - `QDRANT_TOP_K=3`
    - `EMBEDDINGS_MODEL=text-embedding-3-small`
    - `RAG_ENABLED=1`

- [ ] **Step 2: Update `DEPLOY.md` + `demo/WALKTHROUGH.md`**
  - Document `qdrant` service + data volume, and how to check health/logs.
  - Ensure walkthrough references `qdrant` only if it is actually started by compose.

---

## Task 3: Seed help-center Q&A into Qdrant (idempotent)

**Files:**
- Create: `backend/app/data/help_center_seed.json`
- Create: `backend/app/services/qdrant_http.py`
- Create: `backend/app/services/openai_embeddings.py`
- Create: `backend/app/services/retrieval_seed.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_retrieval_seed.py`

- [ ] **Step 1: Write failing seed idempotency test**

```python
def test_point_id_is_deterministic_for_same_question():
    from app.services.retrieval_seed import point_id_for_question
    assert point_id_for_question("Refund policy?") == point_id_for_question("Refund policy?")

def test_seed_is_idempotent(monkeypatch):
    # Seed should call upsert with deterministic IDs; calling twice should not change IDs.
    from app.services.retrieval_seed import build_seed_points
    entries = [{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}]
    pts1 = build_seed_points(entries, vectors=[[0.0, 0.0], [1.0, 1.0]])
    pts2 = build_seed_points(entries, vectors=[[0.0, 0.0], [1.0, 1.0]])
    assert [p["id"] for p in pts1] == [p["id"] for p in pts2]
```

- [ ] **Step 2: Implement minimal seeding utilities**
  - `point_id_for_question(question: str) -> int` (stable hash → 64-bit positive int)
  - `build_seed_points(entries, vectors) -> list[dict]` (payload includes question/answer)

- [ ] **Step 3: Implement Qdrant REST helper**
  - `ensure_collection(...)`
  - `upsert_points(...)`

- [ ] **Step 4: Implement embeddings HTTP helper**
  - `embed_texts(texts: list[str]) -> list[list[float]]`
  - Use `httpx` to call `POST https://api.openai.com/v1/embeddings`

- [ ] **Step 5: Wire FastAPI startup seeding**
  - Add a lifespan startup hook in `backend/app/main.py` that:
    - checks `RAG_ENABLED`
    - ensures collection exists
    - loads seed fixture
    - embeds seed questions
    - upserts into Qdrant
  - Failure should log warning and continue (bot still works without RAG).

---

## Task 4: Retrieval + prompt injection for each user turn

**Files:**
- Create: `backend/app/services/retrieval_runtime.py`
- Modify: `backend/app/services/retrieval.py`
- Modify: `backend/bot.py`
- Test: `backend/tests/test_rag_prompt_injection.py`

- [ ] **Step 1: Write failing prompt injection test**

```python
def test_help_center_context_block_is_delimited():
    from app.services.retrieval_runtime import build_help_center_context_block
    entries = [{"question": "What is the refund policy?", "answer": "30 days."}]
    block = build_help_center_context_block(entries)
    assert "Help Center Context" in block
    assert "Q:" in block and "A:" in block
```

- [ ] **Step 2: Implement retrieval runtime**
  - `retrieve_help_center(query: str) -> list[dict[str, str]]`:
    - embed query
    - qdrant search top-k
    - return payload entries
  - Build delimited system message block for injection.

- [ ] **Step 3: Wire into `bot.py`**
  - On each finalized user transcript, fetch retrieval context and append a **second** system message to the `LLMContext` for that turn:
    - base: user’s `system_prompt`
    - + retrieved block (if any)
  - If retrieval fails: log warning, proceed without injection.

---

## Task 5: Verification

**Files:**
- (none)

- [ ] **Step 1: Run frontend tests**
  - Run: `cd frontend && npm test -- --run`
  - Expected: PASS

- [ ] **Step 2: Run backend tests in Docker**
  - Run: `docker compose build backend && docker compose run --rm backend python -m pytest -q`
  - Expected: PASS

- [ ] **Step 3: Smoke test local stack**
  - Run: `docker compose up -d`
  - Expected: `qdrant` healthy; backend healthy; frontend healthy.

