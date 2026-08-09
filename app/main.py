"""Satellite Telemetry REST API.

Run with:
    uvicorn app.main:app --reload --port 3000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.telemetry import router as telemetry_router
from app.seed import TelemetrySeedGenerator
from app.store import store


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Seed from configuration so GET /telemetry has results immediately.
    settings = get_settings()
    if settings.seed.enabled:
        store.seed(TelemetrySeedGenerator(settings.seed).generate())
    yield


app = FastAPI(
    title="Satellite Telemetry API",
    description="REST API for managing satellite telemetry data",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telemetry_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
