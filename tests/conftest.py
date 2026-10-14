from __future__ import annotations

import pytest

from app.alertmanager import AlertmanagerPayload


@pytest.fixture
def firing_payload() -> dict:
    return {
        "version": "4",
        "groupKey": '{}:{alertname="HighErrorRate"}',
        "status": "firing",
        "receiver": "ogx-translator",
        "groupLabels": {"alertname": "HighErrorRate"},
        "commonLabels": {"severity": "warning", "namespace": "agentic-triage"},
        "commonAnnotations": {"summary": "Elevated 5xx rate"},
        "externalURL": "http://alertmanager:9093",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HighErrorRate",
                    "namespace": "agentic-triage",
                    "severity": "warning",
                },
                "annotations": {"description": "5xx above threshold"},
                "startsAt": "2026-10-04T10:00:00Z",
                "endsAt": "0001-01-01T00:00:00Z",
                "generatorURL": "http://prometheus/graph",
                "fingerprint": "abc123",
            }
        ],
    }


@pytest.fixture
def resolved_payload(firing_payload: dict) -> dict:
    data = dict(firing_payload)
    data["status"] = "resolved"
    data["alerts"] = [{**data["alerts"][0], "status": "resolved"}]
    return data


@pytest.fixture
def firing_payload_without_namespace(firing_payload: dict) -> dict:
    data = {**firing_payload, "groupLabels": {"alertname": "HighErrorRate"}}
    data["commonLabels"] = {"severity": "warning"}
    data["alerts"] = [
        {**alert, "labels": {k: v for k, v in alert["labels"].items() if k != "namespace"}}
        for alert in firing_payload["alerts"]
    ]
    return data


@pytest.fixture
def firing_model(firing_payload: dict) -> AlertmanagerPayload:
    return AlertmanagerPayload.model_validate(firing_payload)
