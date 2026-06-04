from __future__ import annotations

from fastapi import APIRouter

from app.database.session import check_db_connection
from app.database.redis import check_redis_connection
from app.core.config import settings

router = APIRouter()


@router.get("", summary="Health check")
async def health_check() -> dict:
    """Returns service health status."""
    db_ok = await check_db_connection()
    redis_ok = await check_redis_connection()

    status = "healthy" if (db_ok and redis_ok) else "degraded"

    return {
        "status": status,
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV.value,
        "services": {
            "database": "up" if db_ok else "down",
            "cache": "up" if redis_ok else "down",
        },
    }


@router.get("/live", summary="Liveness probe")
async def liveness() -> dict:
    """Kubernetes liveness probe — always returns 200 if process is alive."""
    return {"status": "alive"}


@router.get("/ready", summary="Readiness probe")
async def readiness() -> dict:
    """Kubernetes readiness probe — checks all dependencies."""
    db_ok = await check_db_connection()
    redis_ok = await check_redis_connection()

    if not db_ok or not redis_ok:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "database": "up" if db_ok else "down",
                "cache": "up" if redis_ok else "down",
            },
        )

    return {"status": "ready"}
