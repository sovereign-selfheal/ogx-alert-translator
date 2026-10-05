from __future__ import annotations

from app.alertmanager import Alert, AlertmanagerPayload

ALERT_PREFIX = """An automated alert was fired in the cluster. Investigate and follow the standard triage workflow (metrics, pods if available, diagnosis, incident ticket).

"""


def _format_alert(alert: Alert, index: int) -> str:
    lines = [f"### Alert {index + 1} ({alert.status})"]
    if alert.labels:
        lines.append("**Labels:**")
        for key, value in sorted(alert.labels.items()):
            lines.append(f"- `{key}`: {value}")
    if alert.annotations:
        lines.append("**Annotations:**")
        for key, value in sorted(alert.annotations.items()):
            lines.append(f"- `{key}`: {value}")
    if alert.startsAt:
        lines.append(f"- **startsAt:** {alert.startsAt}")
    if alert.generatorURL:
        lines.append(f"- **generatorURL:** {alert.generatorURL}")
    if alert.fingerprint:
        lines.append(f"- **fingerprint:** {alert.fingerprint}")
    return "\n".join(lines)


def _selected_alerts(payload: AlertmanagerPayload) -> list[Alert]:
    """The alerts that go into the prompt: the firing ones, or all when none is firing."""
    firing = [a for a in payload.alerts if a.status == "firing"]
    return firing if firing else payload.alerts


def alert_namespaces(payload: AlertmanagerPayload) -> list[str]:
    """The `namespace` labels of the alerts in the prompt, in order and without duplicates.

    triage-agent sends them to the router (body field `selfheal_namespaces`): a request about
    a namespace labelled `sovereign-selfheal.io/data-class=restricted` stays on the local model.
    """
    names: list[str] = []
    candidates = [payload.commonLabels.get("namespace", ""), payload.groupLabels.get("namespace", "")]
    candidates += [a.labels.get("namespace", "") for a in _selected_alerts(payload)]
    for name in candidates:
        name = name.strip()
        if name and name not in names:
            names.append(name)
    return names


def build_prompt(payload: AlertmanagerPayload) -> str:
    """Turn an Alertmanager webhook payload into the OGX agent user message."""
    parts = [ALERT_PREFIX.strip(), ""]
    if payload.groupLabels:
        parts.append("**Group labels:**")
        for key, value in sorted(payload.groupLabels.items()):
            parts.append(f"- `{key}`: {value}")
        parts.append("")
    if payload.commonAnnotations:
        parts.append("**Common annotations:**")
        for key, value in sorted(payload.commonAnnotations.items()):
            parts.append(f"- `{key}`: {value}")
        parts.append("")
    for i, alert in enumerate(_selected_alerts(payload)):
        parts.append(_format_alert(alert, i))
        parts.append("")
    parts.append(
        "Use the alert labels (especially `namespace`, `alertname`, `severity`) to focus the investigation."
    )
    return "\n".join(parts).strip()
