# Interview Walkthrough — Goatcat Voice AI

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
2. The bot **immediately stops** (because interruptibility is at 90%)
3. The **Bot State Badge** transitions: `Speaking → Listening`
4. After you finish speaking, it transitions: `Listening → Thinking → Speaking`

Now set **Interruptibility Percentage** to `10` and start a new session.  
Try to interrupt — the bot will hold the floor much longer before yielding.

**Point out:** This is driven by `SileroVADAnalyzer(stop_secs=...)` in `bot.py`, computed via `build_vad_stop_secs()` which calls our `build_interruptibility_policy()` service.

---

## Step 4 — Show Latency Metrics and Qdrant RAG

> **Goal:** Demonstrate the observability and retrieval features.

1. Point to the **Round Trip Latency** panel — it shows the ms from user silence to first bot audio byte
2. Ask a question from the Qdrant knowledge base (e.g., *"What is the refund policy?"*)
3. The Qdrant retrieval context is injected into the LLM prompt via `format_retrieval_context()`
4. The answer comes from the Q&A collection, not a hallucination

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

Expected output:
```
NAME        IMAGE     STATUS                   PORTS
frontend    ...       running                  0.0.0.0:3000->3000/tcp
backend     ...       running (healthy)        0.0.0.0:8000->8000/tcp
qdrant      ...       running (healthy)        0.0.0.0:6333->6333/tcp
```

Point out:
- `restart: unless-stopped` — services survive reboots
- Structured JSON logs with rotation via `docker compose logs`
- No secrets in git — all keys from `.env`
- Health checks ensure ordered startup (Qdrant → Backend → Frontend)

---

## Key Architecture Points to Highlight

| Criterion | Implementation |
|---|---|
| **State management** | RTVI protocol via `@pipecat-ai/client-js` — `BotStartedSpeaking`, `BotStoppedSpeaking` events drive UI instantly |
| **Framework mastery** | `SessionConfig` Pydantic model → JSON-serialized → passed to `bot.py --config` → consumed as `InputParams` |
| **Code hygiene** | Each service has one responsibility; TDD throughout; 40 backend + 12 frontend tests |
| **Deployment hygiene** | Single `docker compose up -d`; health checks; `restart: unless-stopped`; JSON log rotation |
| **Interruptibility** | `interruptibility_percentage` → `build_vad_stop_secs()` → `SileroVADAnalyzer(stop_secs=...)` — fully tested mapping |
