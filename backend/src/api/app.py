from __future__ import annotations
from fastapi import FastAPI

app = FastAPI(title="GarminCoach")

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
