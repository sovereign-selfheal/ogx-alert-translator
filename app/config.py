from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    log_level: str = "INFO"
    # triage-agent's own HTTP endpoint (Gradio + FastAPI, see triage-agent/app.py's
    # `POST /trigger`). This service never calls OGX directly and never duplicates
    # triage-agent's system prompt, MCP tool wiring, or model selection — it only
    # forwards the alert-derived input text to this endpoint.
    triage_agent_url: str = "http://triage-agent.agentic-triage.svc:7860"
    # Short timeout: we only wait for the 202 ack. triage-agent runs the actual agent
    # loop (which can take minutes) as its own background task.
    request_timeout_seconds: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
