from __future__ import annotations

from app.alertmanager import AlertmanagerPayload
from app.prompt_builder import build_prompt, target_namespace


def test_build_prompt_includes_labels_and_annotations(firing_payload: dict) -> None:
    payload = AlertmanagerPayload.model_validate(firing_payload)
    prompt = build_prompt(payload)
    assert "HighErrorRate" in prompt
    assert "agentic-triage" in prompt
    assert "Elevated 5xx rate" in prompt
    assert "automated alert" in prompt.lower()


def test_target_namespace_prefers_group_labels(firing_payload: dict) -> None:
    firing_payload["groupLabels"]["namespace"] = "payments"
    payload = AlertmanagerPayload.model_validate(firing_payload)
    assert target_namespace(payload) == "payments"


def test_target_namespace_falls_back_to_common_labels(firing_payload: dict) -> None:
    payload = AlertmanagerPayload.model_validate(firing_payload)
    # firing_payload has no `namespace` in groupLabels, only in commonLabels/alerts.
    assert target_namespace(payload) == "agentic-triage"


def test_target_namespace_falls_back_to_alert_labels(firing_payload: dict) -> None:
    firing_payload["commonLabels"] = {"severity": "warning"}
    payload = AlertmanagerPayload.model_validate(firing_payload)
    assert target_namespace(payload) == "agentic-triage"


def test_target_namespace_none_when_missing(firing_payload_without_namespace: dict) -> None:
    payload = AlertmanagerPayload.model_validate(firing_payload_without_namespace)
    assert target_namespace(payload) is None
