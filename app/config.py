from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    log_level: str = "INFO"
    # triage-agent runs once per monitored-application namespace (one TriageAgent CR per
    # namespace, same Service name everywhere). This service never calls OGX directly and
    # never duplicates triage-agent's system prompt, MCP tool wiring, or model selection —
    # it only forwards the alert-derived input text to the `/trigger` endpoint of the agent
    # that runs in the alert's own namespace: http://{service}.{namespace}.svc:{port}/trigger.
    triage_agent_service: str = "triage-agent"
    triage_agent_port: int = 7860
    # Short timeout: we only wait for the 202 ack. triage-agent runs the actual agent
    # loop (which can take minutes) as its own background task.
    request_timeout_seconds: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
