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
| 6333 | TCP | VPC only | Qdrant (internal only) |

> **Note:** If using Cloudflare Tunnel, only port 22 needs to be open to the public. The tunnel handles 80/443 routing.

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
┌──────────────┐      ┌──────────────────┐      ┌─────────────┐
│   Frontend   │─────▶│     Backend      │─────▶│   Qdrant    │
│  (Next.js)   │      │  (FastAPI + bot) │      │  (VectorDB) │
│  :3000       │      │  :8000           │      │  :6333      │
└──────────────┘      └──────────────────┘      └─────────────┘
        │                     │
        └──── Daily.co ───────┘  (WebRTC — external)
              (WebRTC Room)
```

- **Frontend** depends on **backend** (`service_healthy`) — waits for the backend health check to pass before starting.
- **Backend** depends on **qdrant** (`service_healthy`) — waits for Qdrant's `/healthz` to respond before starting.
- **Bot processes** (`bot.py`) are spawned by the backend as detached subprocesses when a session is created. They join a Daily.co room via WebRTC.
- **Qdrant** stores vector embeddings on a named volume (`qdrant_data`) — persists across restarts.

---

## 5. Log Locations

All services use Docker's `json-file` logging driver with rotation (10 MB / 3 files).

```bash
# View live logs for all services
docker compose logs -f

# View logs for a specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f qdrant

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
docker compose down && docker compose up -d
```

---

## 7. Environment Variables Reference

All keys are loaded from `.env` at the repo root. See `.env.example` for the full list.

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | OpenAI API key for LLM |
| `DEEPGRAM_API_KEY` | ✅ | Deepgram API key for STT |
| `CARTESIA_API_KEY` | ✅ | Cartesia API key for TTS |
| `DAILY_API_KEY` | ✅ | Daily.co API key for WebRTC rooms |
| `QDRANT_URL` | ✅ | Qdrant URL (default: `http://qdrant:6333`) |
| `FRONTEND_ORIGIN` | ✅ | Allowed CORS origin (default: `http://localhost:3000`) |

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
