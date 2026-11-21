from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.app.config import get_settings
from backend.app.db import initialize_database
from backend.app.routers import (
    agent,
    applications,
    challenges,
    diagnostic,
    intake,
    interviews,
    market,
    planning,
    portfolio,
    scanner,
    workspaces,
)

ROOT = Path(__file__).resolve().parents[2]
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="PivotPilot AI",
    description="Adaptive career pivot coaching API with safe demo fallbacks.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

for route in (
    workspaces.router,
    intake.router,
    diagnostic.router,
    market.router,
    planning.router,
    portfolio.router,
    interviews.router,
    applications.router,
    scanner.router,
    challenges.router,
    agent.router,
):
    app.include_router(route)


@app.get("/api/v1/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "app": "PivotPilot AI",
        "demo_mode": settings.demo_mode,
        "gemini_configured": bool(settings.gemini_api_key),
        "auth_configured": bool(settings.supabase_url and settings.supabase_anon_key),
    }


@app.get("/supabase/schema.sql", include_in_schema=False)
def supabase_setup_sql() -> FileResponse:
    return FileResponse(ROOT / "supabase" / "schema.sql", media_type="text/plain")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(ROOT / "index.html", media_type="text/html")
