# DEPLOY.md — Temple-cat Voice AI Deployment Runbook

One-page checklist: **region / AMI / instance**, **security group ports**, **Compose wiring**, **logs**, **reboot/restart**. Optional OpenTelemetry details are in **§8**.

## 1. Target Infrastructure

| Setting | Value |
|---|---|
| Cloud | AWS |
| Region | **`eu-central-1`** |
| AMI | **Ubuntu 22.04 LTS** — amd64, HVM. Resolve the current ID in-region (recommended): `aws ssm get-parameter --region eu-central-1 --name /aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id --query Parameter.Value --output text` (or pick **Ubuntu 22.04 LTS** from the EC2 launch wizard). |
| Instance type | **`c7i-flex.large`** |
| Storage | 20 GiB gp3 root volume (adjust as needed) |

**Optional add-on (Freya brief — pick one):** This project implements **Pipecat OpenTelemetry → Jaeger**, not Qdrant/RAG. Jaeger is behind Compose profile **`otel`**; see **§8**. Default `docker compose up -d` runs only frontend, backend, and Dozzle.

---

## 2. AWS Security Group — Inbound Ports

Public HTTP/S is **not** exposed on the instance Security Group. Use **Cloudflare Tunnel** (or ngrok) on the host so browsers hit Cloudflare’s edge; `cloudflared` forwards to **`http://127.0.0.1:3000`** locally.

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| **22** | TCP | **Your IP** (or bastion) only | **SSH — only inbound rule required** |

**Inbound:** no `80` / `443` / `3000` / `8000` rules toward `0.0.0.0/0` are needed for evaluators to use the app.

**Outbound:** default “allow all” (or at minimum HTTPS to reach Daily, OpenAI, Deepgram, Cartesia, Cloudflare).

**Inside the instance:** `docker-compose.yml` still publishes **3000** (frontend) and **8000** (backend) on the host so the stack and tunnel can reach them; the Security Group blocks the open internet from connecting directly to those ports.

Set **`FRONTEND_ORIGIN`** in `.env` to your real browser origin (e.g. `https://your-tunnel.example.com` or a comma-separated list). The backend rejects cross-origin browser calls from hosts not listed there (no wildcard by default).

**Dozzle** binds to **`127.0.0.1:8080`** only — use **SSH port-forward** if you want the UI remotely: `ssh -L 8080:127.0.0.1:8080 ubuntu@<host>`.

---

## 3. First-Time EC2 Setup

```bash
# 1. SSH into the instance
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>

# 2. Install Docker and Docker Compose
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker ubuntu
newgrp docker

# 3. Clone the repository
git clone <your-repo-url>
cd <repo-name>

# 4. Set up environment variables (never commit this file)
cp .env.example .env
nano .env   # Fill in all API keys

# 5. Start all services
docker compose up -d

# 6. Verify services are running
docker compose ps
```

---

## 4. Docker Compose Service Wiring

```
┌──────────────┐      ┌──────────────────────────────┐
│   Frontend   │─────▶│     Backend                  │
│  (Next.js)   │      │  (FastAPI + bot subprocesses) │
│  :3000       │      │  :8000, bot logs → volume    │
└──────────────┘      └──────────────────────────────┘
        │                           │
        └──────── Daily.co ─────────┘  (WebRTC — external)
```

- **Frontend** depends on **backend** (`service_healthy`) — waits for the backend health check to pass before starting.
- **Bot processes** (`bot.py`) are spawned by the backend as detached subprocesses when a session is created. They join a Daily.co room via WebRTC. Stdout/stderr for each bot is appended to **`/app/logs/bot-<session_id>.log`** inside the backend container (persisted via the `bot_logs` named volume).
- **Dozzle** (optional) listens on **127.0.0.1:8080** only — use SSH port-forward or inspect logs via `docker compose logs`.
- **Jaeger v2 (OpenTelemetry)** — optional Compose profile **`otel`**. Run `docker compose --profile otel up -d` to start the all-in-one Jaeger v2 image alongside the stack; OTLP gRPC on **`127.0.0.1:4317`**, UI on **`127.0.0.1:16686`**. Set **`ENABLE_TRACING=1`** and **`OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317`** on the **backend** service (same Docker network). See **§8** below. Upgrading from Jaeger v1 is covered in the [Jaeger v2 migration guide](https://docs.google.com/document/d/1z4QrNtB9dMgT5SHNx-7Vc38XPLqnjmM2jFIupvkAEHo/view) and [Jaeger docs](https://www.jaegertracing.io/docs/latest/getting-started/).

If the frontend logs **“Could not find a production build in the '.next' directory”** and shows **`next start`**, you are not running the standalone image (stale image, or a bind-mount replaced `/app` with raw source). Rebuild with **`docker compose build --no-cache frontend`** and **do not** mount `./frontend` over `/app` in production. The stack runs **`node server.js`** from the image build output.

---

## 5. Log Locations

All services use Docker's `json-file` logging driver with rotation (10 MB / 3 files).

```bash
# View live logs for all services
docker compose logs -f

# View logs for a specific service
docker compose logs -f backend
docker compose logs -f frontend

# Per-session Pipecat bots (same host as backend container):
docker compose exec backend ls -la /app/logs
docker compose exec backend tail -f /app/logs/bot-<session_id>.log

# View raw Docker log files (for log shipping)
/var/lib/docker/containers/<container-id>/<container-id>-json.log
```

---

## 6. Restart After System Reboot

All services have `restart: unless-stopped` configured in `docker-compose.yml`.

To ensure Docker starts automatically on reboot:
```bash
sudo systemctl enable docker
sudo systemctl start docker
```

After a reboot, services will auto-restart. To verify:
```bash
docker compose ps   # All services should show "running"
```

To manually restart a single service:
```bash
docker compose restart backend
```

To do a full stack restart:
```bash
docker compose down && docker compose up -d --remove-orphans
```

(`--remove-orphans` drops containers from older compose definitions that are no longer declared.)

---

## 7. Environment Variables Reference

All keys are loaded from `.env` at the repo root. See `.env.example` for the full list.

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | OpenAI API key for LLM |
| `DEEPGRAM_API_KEY` | ✅ | Deepgram API key for STT |
| `CARTESIA_API_KEY` | ✅ | Cartesia API key for TTS |
| `DAILY_API_KEY` | ✅ | Daily.co API key for WebRTC rooms |
| `FRONTEND_ORIGIN` | ✅ | CORS allow-list (comma-separated origins); default `http://localhost:3000`. Must include your public tunnel HTTPS origin in production. |
| `BOT_LOG_DIR` | optional | Directory for bot log files (default `/app/logs` in Compose) |
| `ENABLE_TRACING` | optional | Set `1` to enable Pipecat OpenTelemetry in each **`bot.py`** subprocess ([Pipecat tracing docs](https://docs.pipecat.ai/api-reference/server/utilities/opentelemetry)). |
| `OTEL_SERVICE_NAME` | optional | Trace resource name (default `temple-cat-voice-bot`). |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | optional | OTLP collector URL; default `http://localhost:4317` (gRPC). With Compose profile **`otel`**, use `http://jaeger:4317` on the backend container. |
| `OTEL_EXPORTER_OTLP_INSECURE` | optional | `true`/`false` for gRPC TLS (default `true` for local Jaeger). |
| `OTEL_EXPORTER_OTLP_TRACES_PROTOCOL` | optional | Set to `http/protobuf` for HTTP OTLP (e.g. Langfuse). |
| `OTEL_CONSOLE_EXPORT` | optional | Set `1` to print spans to stdout (debug). |

> ⚠️ **Never commit `.env` to git.** Only `.env.example` is committed.

---

## 8. OpenTelemetry / Jaeger (optional addon)

Pipecat emits hierarchical traces (conversation → turn → STT / LLM / TTS) when tracing is enabled.

Compose runs **Jaeger v2** (`cr.jaegertracing.io/jaegertracing/jaeger`), which accepts OTLP on port **4317** the same way as the old all-in-one image; no application changes are required beyond pulling the new image. Broader v1→v2 deployment changes (Kubernetes, storage, flags) are described in the [migration guide](https://docs.google.com/document/d/1z4QrNtB9dMgT5SHNx-7Vc38XPLqnjmM2jFIupvkAEHo/view).

In Jaeger UI, if you only see the **`jaeger`** service (internal telemetry) and not **`temple-cat-voice-bot`**:

1. **Leading spaces in `.env`** — lines must look like **`ENABLE_TRACING=1`**, not **` ENABLE_TRACING=1`**. Otherwise **`ENABLE_TRACING`** is unset inside the container (Compose/Python treat the key differently).
2. **Wrong OTLP host inside Docker** — **`localhost:4317`** hits the backend container, not Jaeger. **`docker-compose.yml`** defaults **`OTEL_EXPORTER_OTLP_ENDPOINT`** to **`http://jaeger:4317`** when omitted from `.env`; restart backend after changing compose.

Confirm tracing vars reach the backend: **`docker compose exec backend python -c "import os; print(os.getenv('ENABLE_TRACING'), os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT'))`** — expect **`1 http://jaeger:4317`** (or your overrides).

1. **Local / EC2 with Docker:** start Jaeger and rebuild the backend image so **`opentelemetry-exporter-otlp-proto-grpc`** is installed (declared in `backend/pyproject.toml`; Pipecat’s **`tracing`** extra alone does not include OTLP exporters):
   ```bash
   docker compose --profile otel up -d
   docker compose build backend && docker compose up -d backend
   ```
2. In `.env`, set:
   - `ENABLE_TRACING=1`
   - `OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317`
   - `OTEL_EXPORTER_OTLP_INSECURE=true`
3. Open **http://127.0.0.1:16686** (SSH tunnel from your laptop if the server binds to localhost) and search traces for service **`temple-cat-voice-bot`** (or your `OTEL_SERVICE_NAME`).

Each voice session passes **`--conversation-id`** (same as API `session_id`) into the bot for **`conversation.id`** / **`session.id`** span attributes.

---

## 9. Cloudflare Tunnel Setup (Recommended)

With **only SSH open** in AWS, run `cloudflared` **on the EC2 instance** (systemd service or `tmux`). Evaluators use the tunnel URL; they never need port 3000 on the Security Group.

```bash
# Install cloudflared
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Authenticate and create tunnel
cloudflared tunnel login
cloudflared tunnel create temple-cat-voice

# Route traffic
cloudflared tunnel route dns temple-cat-voice your-domain.com

# Start tunnel (points to frontend)
cloudflared tunnel --url http://localhost:3000 run temple-cat-voice
```
