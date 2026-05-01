# Interview Walkthrough — Temple-cat Voice AI

This script walks through the key features of the system during a live demo or review.

---

## Step 1 — Show the Configuration Panel

> **Goal:** Demonstrate that all session parameters are configurable before a call starts.

1. Open the frontend at `http://localhost:3000`
2. The configuration panel is pre-loaded with sensible defaults
3. Point out every field:
   - **System Prompt** — shapes the bot's personality/role
   - **LLM Temperature / Max Tokens** — controls OpenAI response style
   - **STT Temperature** — controls Deepgram transcription confidence
   - **TTS Voice / Speed / Temperature** — configures the Cartesia voice
   - **Interruptibility Percentage** — custom field; maps to Silero VAD `stop_secs` in the pipeline

4. Change the system prompt to something demonstrable:
   ```
   You are a concise customer support agent for a software company.
   Answer questions in 1–2 sentences max.
   ```
5. Set **Interruptibility Percentage** to `90` (very interruptible)

---

## Step 2 — Start the Session and Speak

> **Goal:** Show the full bootstrap flow: API call → Daily room provisioning → bot spawning → WebRTC join.

1. Click **Start Session**
2. The frontend calls `POST /api/sessions` with the full config payload
3. The backend:
   - Validates the config via `SessionConfig` Pydantic model
   - Calls Daily REST API to create a room
   - Spawns `bot.py` as a subprocess with the config JSON
   - Returns `{session_id, room_url, token}` to the frontend
4. The frontend joins the Daily room via `@pipecat-ai/client-js`
5. The **Bot State Badge** shows **Listening** 🟢

Speak a question: *"What is your return policy?"*

---

## Step 3 — Demonstrate Interruption and State Shifts

> **Goal:** Show real-time state machine transitions and the interruptibility feature.

1. While the bot is speaking (**Speaking** 🔵), start talking mid-sentence
2. The bot **yields quickly** (because interruptibility is at 90%)
3. The **Bot State Badge** transitions: `Speaking → Interrupted` (you spoke over bot audio), then back toward **`Listening` / `Thinking` / `Speaking`** on the next turn
4. After you finish speaking, it transitions: `Listening → Thinking → Speaking`

Now set **Interruptibility Percentage** to `10` and start a new session.  
Try to interrupt — the bot will hold the floor much longer before yielding.

**Point out:** This is driven by `SileroVADAnalyzer(stop_secs=...)` in `bot.py`, computed via `build_vad_stop_secs()` which calls our `build_interruptibility_policy()` service.

---

## Step 4 — Latency and optional OpenTelemetry (Jaeger)

> **Goal:** Show client-visible latency and (optional) Pipecat traces — Freya’s brief allows **either** Qdrant RAG **or** OpenTelemetry; **this repo ships telemetry**, not Qdrant.

1. Point to the **Round Trip Latency** panel — milliseconds from **user stopped speaking** (RTVI `UserStoppedSpeaking`) to **bot started speaking** (`BotStartedSpeaking`), measured in the browser.
2. **Optional tracing:** On the server, run Jaeger and enable tracing per **`DEPLOY.md` §8**:
   ```bash
   docker compose --profile otel up -d
   ```
   Set `ENABLE_TRACING=1` (and OTLP endpoint) on the backend so each `bot.py` subprocess exports Pipecat spans (conversation → STT / LLM / TTS). Inspect traces in the Jaeger UI (typically via SSH tunnel to `127.0.0.1:16686`).
3. **Not in stack:** There is **no** Qdrant service or live RAG retrieval in `docker compose`. `backend/app/services/retrieval.py` only formats retrieval text for tests / future use.

---

## Step 5 — Show Deployment Command and Running Services

> **Goal:** Prove the one-command deployment story.

On the EC2 instance:

```bash
# The entire stack starts with one command
git clone <repo> && cd <repo> && docker compose up -d

# Check all services are healthy
docker compose ps
```

Expected output (default profile — voice stack only):
```
NAME        IMAGE     STATUS                   PORTS
frontend    ...       running (healthy)        0.0.0.0:3000->3000/tcp
backend     ...       running (healthy)        0.0.0.0:8000->8000/tcp
dozzle      ...       running                  127.0.0.1:8080->8080/tcp
```

With **`docker compose --profile otel up -d`**, you also get **Jaeger** on `127.0.0.1:16686` / OTLP `127.0.0.1:4317` (see **`DEPLOY.md`**).

Point out:
- `restart: unless-stopped` — services survive reboots
- Structured JSON logs with rotation via `docker compose logs`
- No secrets in git — all keys from `.env`
- Health checks: **backend** healthy before **frontend** starts

---

## Key Architecture Points to Highlight

| Criterion | Implementation |
|---|---|
| **State management** | RTVI protocol via `@pipecat-ai/client-js` — `BotStartedSpeaking`, `BotStoppedSpeaking` events drive UI instantly |
| **Framework mastery** | `SessionConfig` Pydantic model → JSON-serialized → passed to `bot.py --config` → consumed as `InputParams` |
| **Code hygiene** | Each service has one responsibility; focused pytest + Vitest suites (~40 backend cases + 24 frontend tests) |
| **Optional add-on** | **OpenTelemetry → Jaeger** (Compose profile `otel`), not Qdrant RAG |
| **Deployment hygiene** | Single `docker compose up -d`; health checks; `restart: unless-stopped`; JSON log rotation |
| **Interruptibility** | `interruptibility_percentage` → `build_vad_stop_secs()` → `SileroVADAnalyzer(stop_secs=...)` — fully tested mapping |
