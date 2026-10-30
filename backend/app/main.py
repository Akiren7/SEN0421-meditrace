"""MediTrace API entry point (skeleton). Real endpoints arrive with PLN-04."""
from fastapi import FastAPI

app = FastAPI(title="MediTrace", version="0.1.0")


@app.get("/health")
def health() -> dict:
    """Liveness check used by CI and Docker."""
    return {"status": "ok"}
