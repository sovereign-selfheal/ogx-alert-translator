# ogx-alert-translator

Stateless **Alertmanager webhook bridge** for the Sovereign Self-Healing demo. It accepts
Prometheus Alertmanager v4 JSON on `POST /webhook`, turns firing alerts into a plain-text
prompt, and forwards it to **triage-agent** (`POST /trigger` with `{"input": "...", "namespaces": [...]}`).
`namespaces` holds the `namespace` labels of the alerts (omitted when there are none): triage-agent
sends them to the router, which keeps the requests about a namespace labelled
`sovereign-selfheal.io/data-class=restricted` on the local model (router v0.11.0, namespace policy).

This service does **not** run OGX or define the troubleshooting agent. System prompt, MCP
tools, knowledge base, and model selection live only in
[`triage-agent`](https://github.com/sovereign-selfheal/triage-agent).

## Layout

- `app/main.py` — FastAPI: `/webhook`, `/healthz`, `/readyz`
- `app/alertmanager.py` — Alertmanager payload models
- `app/prompt_builder.py` — alert JSON → input text, and the `namespace` labels of the alerts
- `app/agent_client.py` — async POST to triage-agent `/trigger`
- `app/config.py` — settings from environment

See [AGENTS.md](AGENTS.md) for architecture and contracts with `gitops` and `triage-agent`.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `TRIAGE_AGENT_URL` | `http://triage-agent.agentic-triage.svc:7860` | triage-agent base URL (no path) |
| `REQUEST_TIMEOUT_SECONDS` | `10` | Timeout waiting for triage-agent's 202 ack only |
| `LOG_LEVEL` | `INFO` | Logging level |

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export TRIAGE_AGENT_URL=http://localhost:7860
uvicorn app.main:app --reload --port 8080
```

```bash
pytest -q
```

## Build

```bash
podman build -t quay.io/sovereign-selfheal/ogx-alert-translator:<tag> .
```

CI (`.github/workflows/build.yml`) runs on pull requests and `main` to verify the image
builds (no push). Quay builds/pushes tagged release images separately.

## Consumer

Kubernetes manifests (Deployment, Service, KEDA scaling) live in the
[`gitops`](https://github.com/sovereign-selfheal/gitops) repo,
`components/ogx-alert-translator/`.
