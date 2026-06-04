from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import ORJSONResponse

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.router import api_router
from app.database.session import close_db_connections
from app.database.redis import close_redis_connections
from app.middleware.error_handler import register_exception_handlers
from app.middleware.logging_middleware import RequestIDMiddleware, RequestLoggingMiddleware

# Setup structured logging before anything else
setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    logger.info(
        "astra_starting",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.APP_ENV.value,
    )
    yield
    # ─── Shutdown ────────────────────────────────────────────────────────────
    logger.info("astra_shutting_down")
    await close_db_connections()
    await close_redis_connections()
    logger.info("astra_stopped")


def create_app() -> FastAPI:
    """Application factory — returns a configured FastAPI instance."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="Enterprise Multi-Agent AI Research Platform API",
        version=settings.APP_VERSION,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ─── Security Middleware ──────────────────────────────────────────────────
    if settings.is_production:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Response-Time"],
    )

    # ─── Observability Middleware ─────────────────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # ─── Exception Handlers ───────────────────────────────────────────────────
    register_exception_handlers(app)

    # ─── API Routes ──────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
