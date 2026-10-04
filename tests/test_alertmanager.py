from __future__ import annotations

from app.alertmanager import AlertmanagerPayload


def test_firing_payload_parses(firing_payload: dict) -> None:
    payload = AlertmanagerPayload.model_validate(firing_payload)
    assert payload.status == "firing"
    assert len(payload.alerts) == 1
    assert payload.alerts[0].labels["alertname"] == "HighErrorRate"


def test_resolved_payload_parses(resolved_payload: dict) -> None:
    payload = AlertmanagerPayload.model_validate(resolved_payload)
    assert payload.status == "resolved"
    assert payload.alerts[0].status == "resolved"
