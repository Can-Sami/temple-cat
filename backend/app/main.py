from fastapi import FastAPI
from .models.config import SessionConfig

app = FastAPI(title="Goatcat Backend")

@app.get("/")
async def root():
    return {"status": "ok"}
