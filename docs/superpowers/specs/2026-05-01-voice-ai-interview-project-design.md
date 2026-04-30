# Voice AI Interview Project - Design Spec

## 1. Problem and goals

Build a production-minded, real-time Voice AI system where users can configure assistant behavior before session start, then talk to a live bot with immediate state feedback and latency visibility. The solution must be deployable with one Docker Compose command on a clean Ubuntu 22.04 EC2 host and include a prioritized Qdrant RAG add-on.

Primary goals:
- Real-time conversational loop with stable interruption handling.
- Dynamic runtime configuration from frontend to Pipecat backend.
- Accurate bot state synchronization (`Listening`, `Thinking`, `Speaking`) in UI.
- Measurable round-trip latency from user silence to first bot audio.
- Clean deployment and interview-ready artifacts (repo, live URL, walkthrough script).

## 2. Scope and assumptions

### In scope
- Next.js + TypeScript frontend for configuration, session control, and live dashboard.
- Python + Pipecat backend with Daily transport and VAD -> STT -> LLM -> TTS pipeline.
- Deepgram (STT), OpenAI (LLM), Cartesia (TTS), Qdrant (RAG).
- Docker Compose orchestration for frontend, backend, and Qdrant.
- Security baseline (env secrets, CORS, validation, injection prevention basics).
- Focused frontend/backend tests for critical behavior.
- `DEPLOY.md` with EC2 setup and operations guidance.

### Out of scope
- Multi-region high availability and autoscaling.
- Enterprise auth/SSO.
- Full observability stack (Prometheus/Grafana/ELK).
- Advanced long-term memory beyond scoped Qdrant retrieval.

### Assumptions
- Greenfield repo.
- Balanced execution strategy: quality with realistic speed.
- Final deliverables include live demo URL and short walkthrough script.

## 3. Recommended architecture (integration-first)

Two primary services plus vector store:
1. **Frontend service (Next.js):** configuration form, session controls, live telemetry dashboard.
2. **Backend service (Python/Pipecat):** session bootstrap, transport setup, real-time voice pipeline orchestration, event emission.
3. **Qdrant service:** local vector database for retrieval-augmented context.

Conversation path:
1. User fills config and starts session from frontend.
2. Frontend sends validated `InputParams` payload to backend (system prompt, LLM/STT/TTS settings, interruptibility percentage).
3. Backend initializes Pipecat pipeline for the session:
   - `VAD -> Deepgram STT -> (Qdrant retrieval optional per turn) -> OpenAI LLM -> Cartesia TTS`.
4. Backend streams bot state + latency events to frontend over a session event channel (WebSocket or SSE).
5. Frontend updates dashboard state in near real-time and presents latency.

## 4. Component design

## Frontend modules

### 4.1 Session Configuration Panel
- Inputs:
  - LLM: `systemPrompt`, `temperature`, `maxTokens`
  - STT: `temperature`
  - TTS: `voice`, `speed`, `temperature`
  - Custom: `interruptibilityPercentage` (0-100)
- Validation with explicit field-level errors and defaults.
- Payload normalization before submit (types, ranges).

### 4.2 Session Control
- Start session, stop session, reconnect flow.
- Visible connection status and actionable error states.
- Prevent duplicate starts and invalid transitions.

### 4.3 Live Dashboard
- Bot state indicator:
  - `Listening`: waiting for user input / interruption received.
  - `Thinking`: post-STT, pre-TTS generation.
  - `Speaking`: TTS audio actively streaming.
- Latency view:
  - Current round-trip latency value.
  - Recent trend list (or small sparkline if time permits).

## Backend modules

### 4.4 Session Bootstrap API
- Accepts and validates session config payload.
- Creates session context and applies runtime settings.
- Initializes Daily/Pipecat bindings for session.

### 4.5 Pipeline Orchestrator
- Builds and runs Pipecat processor chain for each session.
- Handles provider wiring (Deepgram/OpenAI/Cartesia).
- Inserts Qdrant retrieval step during LLM turn construction.

### 4.6 Interruptibility Controller
- Maps `interruptibilityPercentage` into interruption policy:
  - Lower values: stricter interruption thresholds.
  - Higher values: more aggressive user speech preemption.
- Applies policy during speaking state to preempt TTS and return to listening.

### 4.7 Metrics and Event Emitter
- Emits state transition events and timing events to frontend.
- Computes and reports round-trip latency per turn.

## 5. Data flow and timing model

Per-turn timing:
1. User speech ends; VAD detects silence and records `T0`.
2. STT transcription completes.
3. Backend optionally retrieves top-k Q&A context from Qdrant.
4. LLM request is constructed (system prompt + retrieved snippets + user turn).
5. TTS starts streaming; first audio chunk time recorded as `T1`.
6. Round-trip latency = `T1 - T0`; emit immediately to frontend.

State transitions:
- `Listening -> Thinking`: after user turn closes.
- `Thinking -> Speaking`: when first TTS audio begins.
- `Speaking -> Listening`: after utterance completion or interruption event.

Interruption handling:
- During `Speaking`, if user speech is detected and policy threshold is met, backend cancels/preempts current TTS output.
- Backend emits interruption event and frontend updates state immediately.

## 6. Qdrant RAG design (prioritized add-on)

Dataset:
- Artificial Q&A corpus seeded on startup or via one-time script.

Indexing approach:
- Embed each Q&A entry and store vectors + metadata in Qdrant collection.

Query-time behavior:
- On user turn, embed query and fetch top-k relevant entries.
- Inject selected snippets into LLM context with clear delimiting.
- Keep bounded context size to avoid token bloat and latency spikes.

Failure behavior:
- If retrieval fails, continue without RAG and surface degraded-mode event/log.

## 7. Security and reliability baseline

Security:
- No secrets in git; all keys loaded from environment.
- Provide `.env.example` with required variables and placeholders.
- CORS allowlist for frontend origin(s).
- Input validation for all configurable parameters and session payloads.
- Basic prompt/tool input sanitation and bounded values.

Reliability:
- Timeouts per provider call.
- Retry with bounded backoff on transient errors.
- Explicit error propagation to UI and logs (no silent failures).
- Healthchecks and restart policies in Compose.

## 8. Testing strategy

Backend unit tests:
- Config parser and `InputParams` validation.
- Interruptibility mapping behavior.
- Latency calculator correctness.
- RAG context assembly logic.
- State transition behavior under interruption.

Frontend tests:
- Configuration form validation and payload shaping.
- Session controls and transition handling.
- Bot state indicator updates from event stream.
- Latency metric render/update behavior.
- Error state rendering for failed bootstrap/session issues.

## 9. Deployment design

Docker Compose services:
- `frontend` (Next.js)
- `backend` (Python/Pipecat)
- `qdrant` (vector DB)

Design requirements:
- One-command startup from clean host.
- Environment-driven configuration.
- Clear service dependencies and health conditions.
- Persistent volume for Qdrant data.

Operational doc (`DEPLOY.md`) must include:
- EC2 region, AMI, instance type.
- Required security group ports.
- Compose wiring and network explanation.
- Log locations per service.
- Restart procedures after reboot.

## 10. Phased execution plan (integration-first)

### Phase 1: Repository and runtime scaffold
- Initialize frontend/backend services and Compose skeleton.
- Define env contracts and `.env.example`.

### Phase 2: End-to-end baseline voice loop
- Wire Daily + Pipecat pipeline and verify live roundtrip audio.

### Phase 3: Dynamic configuration path
- Implement frontend config form and backend `InputParams` application.

### Phase 4: Live state + latency telemetry
- Implement deterministic state machine + latency metric streaming to UI.

### Phase 5: Qdrant retrieval integration
- Seed corpus, implement retrieval step, and attach context injection.

### Phase 6: Hardening
- Add validation, retries, rate limiting, logging, and error boundaries.

### Phase 7: Test and delivery artifacts
- Complete tests, deployment docs, live demo prep, and walkthrough script.

## 11. Definition of done

- `docker compose up -d` works on clean Ubuntu 22.04 EC2 without file edits.
- User can configure personality/settings pre-session and observe behavior changes.
- Real-time state indicator reflects interruptions immediately.
- Round-trip latency metric is computed and displayed per turn.
- Qdrant retrieval is active and influences responses.
- Security/reliability baseline controls are in place.
- Interview artifacts are complete: code repo, live URL, concise walkthrough script.

