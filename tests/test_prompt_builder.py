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
