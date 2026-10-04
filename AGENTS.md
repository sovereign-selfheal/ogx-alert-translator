# AGENTS.md: `ogx-alert-translator` repository

Guidance for AI coding agents and humans working in this repo. Read it fully before you change anything.

## 1. Purpose

This repository builds **ogx-alert-translator**: a small, stateless HTTP service that receives
**Prometheus Alertmanager** webhook payloads (POST JSON, v4 format), turns firing alerts into a
structured natural-language prompt, and forwards it to the **triage-agent** workload already
deployed in the same OpenShift cluster.

The translator does **not** run an OGX sidecar, does **not** call OGX directly, and does **not**
define a system prompt, MCP tool list, or model selection. There is exactly **one** agent
definition in this platform, and it lives in `triage-agent/agent.py`. This service is a pure
bridge: Alertmanager → translator → `triage-agent` `POST /trigger` (plain JSON `{"input": "..."}`).
`triage-agent` owns everything about *how* the alert is investigated (prompt, tools, knowledge,
model); this repo only owns turning an Alertmanager payload into readable input text.

The service is designed to run at **zero replicas** when idle and scale up via **KEDA**
(Custom Metrics Autoscaler on OpenShift), deployed through the `gitops` repo component
`components/ogx-alert-translator`.

## 2. Repository structure

```
app/
  __init__.py
  main.py              # FastAPI: /webhook, /healthz, /readyz
  config.py              # Settings from environment (pydantic-settings)
  alertmanager.py        # Pydantic models for Alertmanager webhook JSON
  prompt_builder.py      # Alert payload → plain input text
  agent_client.py        # Async POST to triage-agent's /trigger endpoint
tests/
  conftest.py
  test_alertmanager.py
  test_prompt_builder.py
  test_webhook.py
Containerfile            # python:3.11-slim, non-root UID 1001
requirements.txt
requirements-dev.txt     # pytest, pytest-asyncio, httpx (CI/local only)
.github/workflows/build.yml
```

There is no `pyproject.toml` or installable package: same pattern as `triage-agent` (flat modules
under `app/`, image runs `uvicorn`).

## 3. Architecture rules

1. **Fire-and-forget to triage-agent.** The `/webhook` handler returns **202 Accepted** quickly
   after validating the payload. The call to triage-agent runs in a FastAPI `BackgroundTasks` task.
   It only waits for triage-agent's own 202 ack (`request_timeout_seconds`, short) — triage-agent
   runs the actual multi-minute agent loop as its own background task, not this one.
2. **Firing alerts only.** Ignore or short-circuit payloads with `status: resolved` unless product
   requirements explicitly ask to handle resolutions.
3. **No database.** No SQLite, Redis, or queues in this service. Logs are the audit trail.
4. **Single outbound dependency: triage-agent's `/trigger` endpoint.** `POST {TRIAGE_AGENT_URL}/trigger`
   with body `{"input": "<text>"}`. This service never talks to OGX, MCP servers, or the router
   directly — those are entirely triage-agent's concern.
5. **Never redefine the agent.** Do **not** add a system prompt, MCP tool list, model name, or
   knowledge file in this repo. That logic lives exactly once, in `triage-agent/agent.py`. This
   repo's only responsibility is turning an Alertmanager payload into a readable `input` string
   (`prompt_builder.py`).
6. **12-factor config.** All behavior toggles via environment variables; nothing cluster-specific
   hardcoded in Python.

## 4. Database rules

**Not applicable.** This service stores no data. Do not add persistence layers without an explicit
architecture change agreed with `gitops` and platform owners.

## 5. Security boundaries

| Boundary | Rule |
|---|---|
| **Identity** | Container runs as non-root UID **1001** (OpenShift-compatible), same as `triage-agent`. |
| **Network ingress** | Cluster-internal only: Alertmanager (or KEDA HTTP interceptor) POSTs to the Service. No public Route in gitops for this component. |
| **Network egress** | Only one cluster-internal URL: `TRIAGE_AGENT_URL` — not configured as an arbitrary URL from the webhook body. Everything triage-agent reaches (router, MCP servers, OGX) is entirely out of this service's control plane. |
| **Secrets** | No API keys or tokens in git or in this service. It calls triage-agent's plain HTTP `/trigger` route — no OGX credential, no router credential here. |
| **Webhook trust** | Treat webhook body as untrusted input: validate with Pydantic, bound sizes, reject malformed JSON. Optional shared secret / mTLS is a gitops/Ansible concern, not stored in repo. |
| **PII / alert labels** | Log alert names and namespaces; avoid logging full annotation blobs at DEBUG without need. |

## 6. Contract with the `gitops` repo

| Owner | Items |
|---|---|
| `ogx-alert-translator` (this repo) | Python source, `Containerfile`, CI build smoke test, image `quay.io/sovereign-selfheal/ogx-alert-translator` |
| `gitops` | Helm chart `components/ogx-alert-translator/`, image digest pin, Deployment, Service, KEDA `HTTPScaledObject` (or fallback `ScaledObject`), env vars, resource limits |

1. **Images by digest.** Same convention as other sovereign-selfheal images: comment with tag and
   resolve date; bump via PR in gitops only.
2. **Namespace.** Deployed to `agentic-triage` (`global.namespaces.triage`), wave **5** (after
   `triage-agent` wave 4).
3. **Replicas.** Default **0** at rest; KEDA scales up on HTTP traffic (or fallback metric).
4. **No cluster-scoped objects** in the component chart (gitops AppProject contract).

## 7. Contract with `triage-agent`

1. **One endpoint.** `POST http://triage-agent.<triage-ns>.svc:7860/trigger` with JSON
   `{"input": "<text>"}`. triage-agent's existing Service port (`7860`, already used by the Gradio
   UI) serves this route too — `triage-agent/app.py` mounts Gradio inside a FastAPI app that also
   exposes `/trigger`. No new Service port is needed.
2. **Response contract.** `202 {"status": "accepted"}` immediately; the actual agent run (system
   prompt, MCP tools, model, knowledge — all defined in `triage-agent/agent.py`) happens
   server-side in triage-agent's own background task.
3. **Ownership boundary.** This repo never sees or configures OGX, MCP server URLs, model names,
   or knowledge files. If any of that needs to change for alert-driven runs, change it in
   `triage-agent`, not here.

## 8. Contract with Alertmanager

- **Receiver URL** points at the translator Service (or KEDA HTTP interceptor fronting it),
  path **`/webhook`**.
- **Content-Type:** `application/json`.
- Expect **202** on success; Alertmanager may retry on 5xx/timeouts — keep handler fast.

## 9. Build and CI

- **Local / CI image build:** `podman build -t localhost/ogx-alert-translator:ci .`
- **CI workflow** builds only; Quay push on git tags (mirror `triage-agent` README pattern when added).
- **Tests:** `pytest` from repo root with `requirements-dev.txt` installed.

## 10. Out of scope

- Installing KEDA / Custom Metrics Autoscaler operator → `ansible` repo.
- Alertmanager routing rules and PrometheusRule definitions → platform/observability owners
  (may live outside this repo).
- OGX sidecar image, `stack_run_config.yaml`, system prompt, MCP tool wiring, knowledge base,
  model selection → all `triage-agent` (`agent.py`), never duplicated here.

## 11. When in doubt

- Prefer the smallest change that keeps the bridge stateless and the webhook fast.
- Ask before adding persistence, synchronous agent waits, or a second OGX instance in this pod.
