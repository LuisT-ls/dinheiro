"""FastAPI application entrypoint for Vercel and local development."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import db
from .routes import quotes, services


app = FastAPI(
    title="Dinheiro API",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:4173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https://[a-zA-Z0-9-]+\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(services.router, prefix="/api")
app.include_router(quotes.router, prefix="/api")


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Return service status and perform a read-only Firestore check."""

    if db is None:
        return {
            "status": "ok",
            "firestore": "not_configured",
        }

    try:
        # A bounded, read-only query validates credentials and connectivity
        # without creating or modifying any Firestore documents.
        db.collection("_health").limit(1).get()
    except Exception:
        return {
            "status": "degraded",
            "firestore": "disconnected",
        }

    return {
        "status": "ok",
        "firestore": "connected",
    }
