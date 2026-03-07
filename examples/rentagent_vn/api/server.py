"""FastAPI application factory for RentAgent VN REST API."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from examples.rentagent_vn.db.connection import close_db, init_db

# ---------------------------------------------------------------------------
# Scan trigger callback — set by run_all.py to connect API → agent
# ---------------------------------------------------------------------------

_scan_trigger: Callable[[str, str | None], Awaitable[dict[str, Any]]] | None = None
_research_trigger: Callable[[str, str], Awaitable[None]] | None = None


def set_scan_trigger(
    trigger: Callable[[str, str | None], Awaitable[dict[str, Any]]] | None,
) -> None:
    """Register the function that triggers a scan from the API layer."""
    global _scan_trigger
    _scan_trigger = trigger


def get_scan_trigger() -> Callable[[str, str | None], Awaitable[dict[str, Any]]] | None:
    return _scan_trigger


def set_research_trigger(
    trigger: Callable[[str, str], Awaitable[None]] | None,
) -> None:
    """Register the function that triggers area research from the API layer."""
    global _research_trigger
    _research_trigger = trigger


def get_research_trigger() -> Callable[[str, str], Awaitable[None]] | None:
    return _research_trigger


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    logger.info("REST API database initialized")
    yield
    await close_db()
    logger.info("REST API database closed")


def create_api_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="RentAgent VN API",
        version="0.1.0",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from examples.rentagent_vn.api.routes.campaigns import router as campaigns_router
    from examples.rentagent_vn.api.routes.research import router as research_router
    from examples.rentagent_vn.api.routes.zalo import router as zalo_router

    app.include_router(campaigns_router)
    app.include_router(research_router)
    app.include_router(zalo_router)

    return app
