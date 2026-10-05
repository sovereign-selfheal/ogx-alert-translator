from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse

from app.agent_client import forward_to_triage_agent
from app.alertmanager import AlertmanagerPayload
from app.config import Settings, get_settings
from app.prompt_builder import alert_namespaces, build_prompt

logger = logging.getLogger(__name__)


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _configure_logging(settings.log_level)
    app.state.settings = settings
    logger.info("ogx-alert-translator started triage_agent_url=%s", settings.triage_agent_url)
    yield


app = FastAPI(title="ogx-alert-translator", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.post("/webhook", status_code=202)
async def webhook(
    payload: AlertmanagerPayload,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    settings: Settings = app.state.settings
    if payload.status != "firing":
        logger.info("Ignoring webhook status=%s receiver=%s", payload.status, payload.receiver)
        return JSONResponse(
            status_code=202,
            content={"status": "ignored", "reason": "not_firing", "webhook_status": payload.status},
        )
    firing_count = sum(1 for a in payload.alerts if a.status == "firing")
    if firing_count == 0 and payload.alerts:
        logger.info("Ignoring webhook: no firing alerts in group")
        return JSONResponse(
            status_code=202,
            content={"status": "ignored", "reason": "no_firing_alerts"},
        )
    prompt = build_prompt(payload)
    namespaces = alert_namespaces(payload)
    background_tasks.add_task(forward_to_triage_agent, prompt, settings, namespaces)
    logger.info(
        "Accepted alert webhook receiver=%s alerts=%d groupKey=%s namespaces=%s",
        payload.receiver,
        len(payload.alerts),
        payload.groupKey,
        namespaces,
    )
    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "alerts": len(payload.alerts),
            "firing": firing_count or len(payload.alerts),
        },
    )
