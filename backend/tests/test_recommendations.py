"""Tests for recommendation and ad interaction endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_ad_recommendations(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/recommendations/ads", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "user_id" in data
    assert "recommendations" in data
    assert "algorithm" in data
    assert "is_cold_start" in data


@pytest.mark.asyncio
async def test_get_content_recommendations(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/recommendations/content", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "user_id" in data
    assert "personalized" in data
    assert "trending" in data


@pytest.mark.asyncio
async def test_recommendations_require_auth(client: AsyncClient):
    resp = await client.get("/api/recommendations/ads")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_user_profile(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/users/me/profile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "user_id" in data
    assert "interests" in data
    assert "engagement_score" in data
    assert "is_cold_start" in data
    # New user should be cold start
    assert data["is_cold_start"] is True


@pytest.mark.asyncio
async def test_user_analytics(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/users/me/analytics", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_sessions" in data
    assert "total_events" in data
    assert "ctr" in data


@pytest.mark.asyncio
async def test_session_lifecycle(client: AsyncClient, auth_headers: dict):
    # Start session
    resp = await client.post("/api/sessions/start", headers=auth_headers)
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]
    assert session_id is not None

    # End session
    resp = await client.post(f"/api/sessions/{session_id}/end", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["duration_seconds"] is not None


@pytest.mark.asyncio
async def test_admin_overview(client: AsyncClient):
    resp = await client.get("/api/admin/analytics/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "total_events" in data
    assert "overall_ctr" in data
