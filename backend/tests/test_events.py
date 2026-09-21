"""Tests for event ingestion endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_event(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/events", json={
        "event_type": "CONTENT_VIEW",
        "entity_type": "content",
        "entity_id": 1,
        "metadata": {"source": "test"},
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["event_type"] == "CONTENT_VIEW"
    assert data["entity_id"] == 1


@pytest.mark.asyncio
async def test_create_event_invalid_type(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/events", json={
        "event_type": "INVALID_TYPE",
    }, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_batch_events(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/events/batch", json={
        "events": [
            {"event_type": "APP_OPEN"},
            {"event_type": "SEARCH", "metadata": {"query": "test"}},
            {"event_type": "CONTENT_VIEW", "entity_type": "content", "entity_id": 1},
        ]
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_event_requires_auth(client: AsyncClient):
    resp = await client.post("/api/events", json={
        "event_type": "APP_OPEN",
    })
    assert resp.status_code == 401
