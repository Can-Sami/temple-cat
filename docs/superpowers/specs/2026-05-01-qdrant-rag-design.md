## Goal

> **Status:** **Not implemented** on `main`. Freya’s brief allows Qdrant RAG *or* Pipecat OpenTelemetry; this repository shipped **OpenTelemetry → Jaeger** instead. The content below is an **alternate design** retained for reference.

Add the “Help Center (Qdrant RAG)” add-on in a production-minded way:

- A `qdrant` service comes up via `docker compose up -d` alongside frontend + backend.
- The backend seeds an artificial help-center Q&A collection into Qdrant **idempotently**.
- During a live voice session, each finalized user utterance triggers retrieval (top-k) and the retrieved context is injected into the LLM prompt for that turn.
- Documentation reflects the actual running stack (no spec/doc drift).
- Add focused backend tests around seeding/retrieval and prompt injection.

Non-goals:

- Long-term conversation memory beyond “retrieval for current turn”.
- Full observability/OTel tracing (separate optional addon).

---

## Architecture

### Services (Docker Compose)

- **frontend**: Next.js app on `:3000` (unchanged)
- **backend**: FastAPI on `:8000`, spawns `bot.py` subprocess per session (unchanged)
- **qdrant**: Qdrant vector DB on `:6333` (new)
  - Persist data via a named volume.
  - Healthcheck gate: backend depends on qdrant being healthy.

### Data model

- A committed seed fixture file: `backend/app/data/help_center_seed.json`
  - Format: an array of `{ "question": string, "answer": string }`.

### Vectorization strategy (production-minded, simple)

- Use **OpenAI embeddings** for each question (and optionally “question + answer” for better recall).
- Vector size determined by the embedding model (kept configurable).
- Store in Qdrant with payload:
  - `question`, `answer`, `source="seed"`, `version`, optional tags.

### Backend components

Add a small retrieval subsystem under `backend/app/services/`:

1. `qdrant_client.py` (new)
   - Create Qdrant client from `QDRANT_URL`.
   - Provide helpers:
     - `ensure_collection(name, vector_size, distance="Cosine")`
     - `upsert_points(...)`
     - `search(...)`
   - Timeouts + retries for transient errors.

2. `embeddings.py` (new)
   - Compute embeddings using `OPENAI_API_KEY`.
   - Keep model configurable via env:
     - `EMBEDDINGS_MODEL` default `text-embedding-3-small`.
   - Minimal caching (in-process LRU) to reduce repeat calls in tests/dev.

3. `retrieval_seed.py` (new)
   - Load seed JSON fixture.
   - On backend startup, seed if missing:
     - Use a deterministic point ID per entry (e.g. hash of question).
     - Upsert is idempotent; avoid duplicates.

4. `retrieval.py` (extend existing)
   - Keep `format_retrieval_context(entries)` as the prompt formatter.
   - Add:
     - `retrieve_help_center(query: str) -> list[{question, answer}]`
     - `build_help_center_context_block(entries) -> str` (delimited block)

### Pipeline integration (Pipecat)

Modify `backend/bot.py` so that **for each user turn**:

- When the user transcript is finalized (post-STT, before LLM):
  - Compute embeddings for the transcript.
  - Query Qdrant `top_k` (env-configurable; default 3).
  - Inject retrieved context into the LLM context for this turn:
    - Preserve the user-supplied `system_prompt` as the base system message.
    - Append a second system message containing a delimited context block:
      - “Help Center Context (retrieved; may be incomplete)” + formatted Q/A pairs.
    - If no results, skip the retrieval context message entirely.

Implementation detail:

- Use Pipecat’s existing context aggregator (`LLMContextAggregatorPair`) and add a small processor/hook that can mutate or append system messages right before the LLM call. Keep this logic isolated in a service module so it’s unit-testable without standing up Pipecat end-to-end.

### Configuration (env)

Add to `.env.example` and document in `DEPLOY.md`:

- `QDRANT_URL` (default `http://qdrant:6333`)
- `QDRANT_COLLECTION` (default `help_center`)
- `QDRANT_TOP_K` (default `3`)
- `EMBEDDINGS_MODEL` (default `text-embedding-3-small`)
- Optional: `RAG_ENABLED` (default `1`) to quickly disable retrieval in emergencies.

---

## Error handling & resilience

- If Qdrant is unavailable:
  - Bot should continue without retrieval context (log warning); do not crash the session.
- If embeddings call fails:
  - Same behavior: continue without retrieval context.
- Seed step should be idempotent and safe to retry on startup.
- Add conservative timeouts (e.g. 2–5s) for embeddings and Qdrant calls.

---

## Security & hygiene

- No secrets committed.
- Qdrant is internal-to-compose by default (not necessarily exposed publicly on EC2).
- Only the backend needs `OPENAI_API_KEY` for embeddings; frontend unchanged.

---

## Tests

Backend (pytest):

- **Unit**: `format_retrieval_context()` formatting (already exists; keep).
- **Unit**: deterministic point IDs / idempotent seeding behavior (mock Qdrant).
- **Unit**: prompt injection logic appends context only when results exist.
- **Integration-light**: retrieval adapter calls Qdrant search with expected vector and `top_k` (mock OpenAI embeddings + Qdrant client).

Frontend:

- No new frontend tests required for RAG (it’s backend/agent behavior). Keep current suite as-is.

---

## Documentation updates

- Update `DEPLOY.md`:
  - mention qdrant service, volume, healthcheck ordering
  - add env var docs
  - include where qdrant data lives and how to inspect (optional)
- Update `demo/WALKTHROUGH.md` to match actual behavior and commands.
- Remove or correct any docs that claim Qdrant is running if it wasn’t previously wired in compose.

---

## Success criteria

- `docker compose up -d` starts frontend + backend + qdrant successfully on a clean host.
- Asking a question that is semantically close to a seeded entry results in an answer that clearly reflects the retrieved policy text (not just generic LLM output).
- If Qdrant is stopped, the bot still works (without RAG) and logs an explicit warning.

