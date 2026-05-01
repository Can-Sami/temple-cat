# DEPLOY.md — Temple-cat Voice AI Deployment Runbook

## 1. Target Infrastructure

| Setting | Value |
|---|---|
| Cloud | AWS |
| Region | `us-east-1` (recommended for lowest Daily.co latency from US) |
| AMI | `ami-0c02fb55956c7d316` — Ubuntu 22.04 LTS (HVM, SSD, x86_64) |
| Instance type | `t3.medium` (2 vCPU, 4 GiB RAM) |
| Storage | 20 GiB gp3 root volume |

---

## 2. AWS Security Group — Required Open Ports

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 22 | TCP | Your IP | SSH access |
| 80 | TCP | 0.0.0.0/0 | HTTP (redirect to app) |
| 443 | TCP | 0.0.0.0/0 | HTTPS (Cloudflare Tunnel) |
| 3000 | TCP | 0.0.0.0/0 | Next.js frontend |
| 8000 | TCP | 0.0.0.0/0 | FastAPI backend |
| 8080 | TCP | `127.0.0.1` only | Dozzle (optional container logs UI; only started if you enable the `debug` profile) |
| 6333 | TCP | (optional) | Qdrant (RAG vector DB). Prefer **not** exposing publicly; internal-to-compose is enough. |

> **Note:** If using Cloudflare Tunnel, only port 22 needs to be open to the public. The tunnel handles 80/443 routing.

Set **`FRONTEND_ORIGIN`** in `.env` to your real browser origin (e.g. `https://your-tunnel.example.com` or a comma-separated list). The backend rejects cross-origin browser calls from hosts not listed there (no wildcard by default).

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
        │                           ├────▶ Qdrant :6333 (RAG, internal-to-compose)
        │                           │
        └──────── Daily.co ─────────┘  (WebRTC — external)
```

- **Frontend** depends on **backend** (`service_healthy`) — waits for the backend health check to pass before starting.
- **Backend** depends on **Qdrant** (`service_healthy`) — waits for Qdrant so the startup seed step can run deterministically.
- **Bot processes** (`bot.py`) are spawned by the backend as detached subprocesses when a session is created. They join a Daily.co room via WebRTC. Stdout/stderr for each bot is appended to **`/app/logs/bot-<session_id>.log`** inside the backend container (persisted via the `bot_logs` named volume).
- **Dozzle** (optional) listens on **127.0.0.1:8080** only and is behind a compose profile — start it with `docker compose --profile debug up -d dozzle` (or just use `docker compose logs`).

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
| `QDRANT_URL` | optional | Qdrant base URL (compose default `http://qdrant:6333`) |
| `QDRANT_COLLECTION` | optional | Qdrant collection name (default `help_center`) |
| `QDRANT_TOP_K` | optional | Retrieval top-k (default `3`) |
| `EMBEDDINGS_MODEL` | optional | OpenAI embeddings model (default `text-embedding-3-small`) |
| `RAG_ENABLED` | optional | Set `0` to disable RAG while keeping the voice bot functional |

> ⚠️ **Never commit `.env` to git.** Only `.env.example` is committed.

---

## 8. Cloudflare Tunnel Setup (Recommended)

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
