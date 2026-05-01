# Minimal backend Dockerfile to satisfy compose build contract
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md requirements-docker.lock ./
RUN pip install --upgrade pip \
  && pip install --only-binary=:all: -r requirements-docker.lock
COPY . .
RUN pip install --only-binary=:all: --no-deps . \
  && mkdir -p /app/logs
# Default command for local dev; compose can override as needed
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
