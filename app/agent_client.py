from __future__ import annotations

import logging

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


async def forward_to_triage_agent(prompt: str, settings: Settings, namespace: str) -> None:
    """Fire-and-forget: hand the alert-derived prompt to triage-agent's `/trigger` endpoint.

    triage-agent (its `agent.py`) owns the system prompt, MCP tool wiring, knowledge base
    and model selection — this service does not duplicate any of that, and does not call
    OGX directly. It only builds the user-facing input text from the Alertmanager payload
    (see `prompt_builder.py`) and forwards it here.

    One agent runs per monitored-application namespace (same Service name everywhere): the
    `namespace` argument is the alert's own namespace (`prompt_builder.target_namespace`),
    so this call always reaches that namespace's own agent, never a single fixed instance.

    triage-agent returns 202 immediately and runs the agent to completion in its own
    background task, so this call only needs a short timeout to wait for that ack.
    """
    url = f"http://{settings.triage_agent_service}.{namespace}.svc:{settings.triage_agent_port}/trigger"
    timeout = httpx.Timeout(
        connect=settings.request_timeout_seconds,
        read=settings.request_timeout_seconds,
        write=settings.request_timeout_seconds,
        pool=settings.request_timeout_seconds,
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json={"input": prompt})
            response.raise_for_status()
            logger.info("Forwarded alert prompt to triage-agent %s -> %s", url, response.status_code)
    except Exception:
        logger.exception("Failed to forward alert prompt to triage-agent at %s", url)
