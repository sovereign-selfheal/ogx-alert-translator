from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


@pytest.fixture
def client() -> TestClient:
    settings = Settings(triage_agent_service="triage-agent", triage_agent_port=9999)
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        app.state.settings = settings
        yield test_client
    get_settings.cache_clear()


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_webhook_accepts_firing(client: TestClient, firing_payload: dict) -> None:
    with patch("app.main.forward_to_triage_agent", new_callable=AsyncMock) as mock_forward:
        response = client.post("/webhook", json=firing_payload)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["namespace"] == "agentic-triage"
    mock_forward.assert_called_once()
    prompt, _settings, namespace = mock_forward.call_args[0]
    assert "HighErrorRate" in prompt
    assert namespace == "agentic-triage"


def test_webhook_ignores_resolved(client: TestClient, resolved_payload: dict) -> None:
    with patch("app.main.forward_to_triage_agent", new_callable=AsyncMock) as mock_forward:
        response = client.post("/webhook", json=resolved_payload)
    assert response.status_code == 202
    assert response.json()["status"] == "ignored"
    mock_forward.assert_not_called()


def test_webhook_ignores_alerts_without_namespace(
    client: TestClient, firing_payload_without_namespace: dict
) -> None:
    with patch("app.main.forward_to_triage_agent", new_callable=AsyncMock) as mock_forward:
        response = client.post("/webhook", json=firing_payload_without_namespace)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "ignored"
    assert body["reason"] == "no_namespace_label"
    mock_forward.assert_not_called()
