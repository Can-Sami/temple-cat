from fastapi import FastAPI

app = FastAPI(title="Goatcat Backend")

@app.get("/")
async def root():
    return {"status": "ok"}
