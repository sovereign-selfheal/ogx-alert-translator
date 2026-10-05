from __future__ import annotations

import json

import httpx
import pytest

from app.agent_client import forward_to_triage_agent
from app.config import Settings


@pytest.mark.asyncio
async def test_forward_posts_input_to_trigger_endpoint() -> None:
    calls: list[tuple[str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((str(request.url), request.read()))
        return httpx.Response(202, json={"status": "accepted"})

    transport = httpx.MockTransport(handler)
    settings = Settings(triage_agent_url="http://triage-agent.agentic-triage.svc:7860")

    # Patch the client construction to use the mock transport by monkeypatching httpx.AsyncClient
    original_async_client = httpx.AsyncClient

    class _MockedAsyncClient(original_async_client):  # type: ignore[misc]
        def __init__(self, *args, **kwargs) -> None:
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    import app.agent_client as agent_client_module

    agent_client_module.httpx.AsyncClient = _MockedAsyncClient  # type: ignore[attr-defined]
    try:
        await forward_to_triage_agent("investigate this alert", settings)
    finally:
        agent_client_module.httpx.AsyncClient = original_async_client  # type: ignore[attr-defined]

    assert len(calls) == 1
    url, body = calls[0]
    assert url == "http://triage-agent.agentic-triage.svc:7860/trigger"
    assert json.loads(body) == {"input": "investigate this alert"}


@pytest.mark.asyncio
async def test_forward_sends_the_namespaces() -> None:
    calls: list[bytes] = []
    transport = httpx.MockTransport(
        lambda request: calls.append(request.read()) or httpx.Response(202, json={})
    )
    original_async_client = httpx.AsyncClient

    class _MockedAsyncClient(original_async_client):  # type: ignore[misc]
        def __init__(self, *args, **kwargs) -> None:
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    import app.agent_client as agent_client_module

    agent_client_module.httpx.AsyncClient = _MockedAsyncClient  # type: ignore[attr-defined]
    try:
        await forward_to_triage_agent("x", Settings(triage_agent_url="http://t:7860"), ["payments"])
    finally:
        agent_client_module.httpx.AsyncClient = original_async_client  # type: ignore[attr-defined]
    assert json.loads(calls[0]) == {"input": "x", "namespaces": ["payments"]}


@pytest.mark.asyncio
async def test_forward_swallows_errors(caplog: pytest.LogCaptureFixture) -> None:
    settings = Settings(triage_agent_url="http://127.0.0.1:1")  # nothing listening
    # Should not raise even though the connection fails.
    await forward_to_triage_agent("investigate this alert", settings)
