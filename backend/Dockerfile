# Minimal backend Dockerfile to satisfy compose build contract
FROM python:3.11-slim
WORKDIR /app
COPY . .
# Default command for local dev; compose can override as needed
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]