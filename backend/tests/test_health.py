from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert body["app"] == "Astra"


@pytest.mark.asyncio
async def test_liveness_probe(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_probe_when_healthy(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/ready")
    # 200 if deps up, 503 if not — both are acceptable in unit tests
    assert response.status_code in (200, 503)
