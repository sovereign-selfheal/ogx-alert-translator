from __future__ import annotations

from app.alertmanager import AlertmanagerPayload
from app.prompt_builder import build_prompt


def test_build_prompt_includes_labels_and_annotations(firing_payload: dict) -> None:
    payload = AlertmanagerPayload.model_validate(firing_payload)
    prompt = build_prompt(payload)
    assert "HighErrorRate" in prompt
    assert "agentic-triage" in prompt
    assert "Elevated 5xx rate" in prompt
    assert "automated alert" in prompt.lower()


def test_alert_namespaces_from_labels(firing_payload: dict) -> None:
    from app.alertmanager import AlertmanagerPayload
    from app.prompt_builder import alert_namespaces

    data = dict(firing_payload)
    data["commonLabels"] = {"severity": "warning"}
    data["alerts"] = [
        {**firing_payload["alerts"][0], "labels": {"alertname": "A", "namespace": "payments"}},
        {**firing_payload["alerts"][0], "labels": {"alertname": "B", "namespace": "agentic-triage"}},
        {**firing_payload["alerts"][0], "labels": {"alertname": "C", "namespace": "payments"}},
        {**firing_payload["alerts"][0], "status": "resolved", "labels": {"namespace": "old-ns"}},
        {**firing_payload["alerts"][0], "labels": {"alertname": "D"}},
    ]
    assert alert_namespaces(AlertmanagerPayload.model_validate(data)) == ["payments", "agentic-triage"]


def test_alert_namespaces_empty_without_labels(firing_payload: dict) -> None:
    from app.alertmanager import AlertmanagerPayload
    from app.prompt_builder import alert_namespaces

    data = dict(firing_payload)
    data["commonLabels"] = {}
    data["alerts"] = [{**firing_payload["alerts"][0], "labels": {"alertname": "A"}}]
    assert alert_namespaces(AlertmanagerPayload.model_validate(data)) == []
