"""FastAPI entrypoint for the Career Intelligence API.

Run from backend/:  uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings  # noqa: F401  validates .env at import time (fail fast)
from api import (
    assessments,
    auth,
    careers,
    gaps,
    interviews,
    jobs,
    progress,
    profiles,
    resources,
    resumes,
    roadmaps,
    simulations,
)

app = FastAPI(title="Career Intelligence API")

# Allow all origins during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    resumes.router,
    profiles.router,
    careers.router,
    gaps.router,
    simulations.router,
    roadmaps.router,
    resources.router,
    progress.router,
    assessments.router,
    jobs.router,
    interviews.router,
):
    app.include_router(router)


@app.on_event("startup")
async def on_startup() -> None:
    print("Career Intelligence API Started")


@app.get("/health", tags=["health"])
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "version": "1.0.0"}
