"""Basic integration tests for critical MoniTe endpoints.

These tests spin up the FastAPI application and verify that the
endpoints defined in the API contract respond successfully.  They
provide a guard against accidental removal or renaming of routes in
future refactorings.  The tests do not assert the full response
payload but merely check that a 2xx status code is returned.

Run these tests with ``pytest``.  The asynchronous lifecycle of the
application is handled automatically by httpx's ``AsyncClient``.
"""

import pytest
from httpx import AsyncClient

from monite_web.backend.app.main import app


@pytest.mark.asyncio
async def test_hosts_routes_exist() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        # List hosts (collection) should succeed without redirect
        resp = await client.get("/hosts")
        assert resp.status_code == 200
        # Create host route exists (even if body missing, expect 422)
        resp = await client.post("/hosts")
        assert resp.status_code != 404


@pytest.mark.asyncio
async def test_health_routes_exist() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Per‑host list of health info
        resp = await client.get("/hosts/summary/health")
        assert resp.status_code == 200
        # Aggregate stats
        resp = await client.get("/hosts/summary/health-stats")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_config_route_exists() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/config")
        assert resp.status_code == 200