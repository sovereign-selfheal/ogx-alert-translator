from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Alert(BaseModel):
    status: Literal["firing", "resolved"]
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: str = ""
    endsAt: str = ""
    generatorURL: str = ""
    fingerprint: str = ""


class AlertmanagerPayload(BaseModel):
    """Prometheus Alertmanager webhook notification (v4-compatible JSON)."""

    version: str = "4"
    groupKey: str = ""
    truncatedAlerts: int = 0
    status: Literal["firing", "resolved"]
    receiver: str = ""
    groupLabels: dict[str, str] = Field(default_factory=dict)
    commonLabels: dict[str, str] = Field(default_factory=dict)
    commonAnnotations: dict[str, str] = Field(default_factory=dict)
    externalURL: str = ""
    alerts: list[Alert] = Field(default_factory=list)

    @classmethod
    def model_validate_flexible(cls, data: Any) -> AlertmanagerPayload:
        """Validate raw JSON dict from the webhook body."""
        return cls.model_validate(data)
