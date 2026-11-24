# SENTINELX — Autonomous Incident Response Network

AI-powered Security Operations Center. Six cooperating agents (LangGraph) investigate security
incidents, a human approves response actions, and every step is written to a hash-chained audit trail.

| Layer | Technology |
|---|---|
| Frontend | Streamlit **>= 1.41** (Python 3.11) |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL 15 |
| Agents | LangGraph: Detection, Investigation, Threat Intelligence, Risk Assessment, Audit, Response |
| Automation | n8n webhook (optional) |

## The eight workspaces

| Page | Purpose | Backend data |
|---|---|---|
| **Command Center** | Timeline, severity index, system health, network map, alert statistics, top threats | `/dashboard/summary`, `/health` |
| **Log Explorer** | Search/filter/inspect events; ingest CSV or JSON logs; start investigations | `/events`, `/logs/upload`, `/investigations/{id}/run` |
| **Investigation Center** | Run an investigation, agent progress, timeline, findings, evidence, **approve / reject** response actions | `/incidents/{id}`, `/incidents/{id}/investigations`, `/approvals/{id}` |
| **Agent Operations** | Status and history of all six agents, workflow diagram, orchestration, retry failed runs | `/agents/overview` |
| **Risk Assessment** | Severity distribution, confidence, trends, per-incident evidence | `/risk/overview` |
| **Audit Trail** | Audit records with backend hash-chain verification; evidence integrity per incident | `/audit` |
| **Reports** | Evidence-based incident report; export JSON, Markdown, printable HTML | `/reports/{id}` + the endpoints above |
| **Settings** | Connection, authentication posture, integrations, LLM mode, safe-configuration guide | `/system/info`, `/health` |

Nothing on any page is fabricated. When data is missing the page shows an *unavailable* or *empty* state;
when the backend fails it shows an error state. Methodology notes are available as tooltips (ⓘ) on the dashboard.

## Run with Docker (everything)

```bash
export OPENAI_API_KEY=sk-...        # optional; without it the agents run in deterministic mock mode
docker-compose up --build
```

* Streamlit UI: http://localhost:8501 &nbsp;·&nbsp; API docs: http://localhost:8000/docs &nbsp;·&nbsp; n8n: http://localhost:5678
* The compose file seeds an operator `admin` / `changeme` (override with `ADMIN_USERNAME` / `ADMIN_PASSWORD`).
* **Change `SECRET_KEY`** in `docker-compose.yml` before any real use. The Settings page shows a red warning while the
  built-in default is active.

## Run locally (without Docker)

Requires **Python 3.11** and a PostgreSQL instance.

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Database (any Postgres 15 works; this starts one in Docker)
docker run -d --name sentinelx-db -p 5432:5432 \
  -e POSTGRES_USER=user -e POSTGRES_PASSWORD=password -e POSTGRES_DB=sentinelx postgres:15

# 2. Backend configuration
export DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/sentinelx
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
export ALGORITHM=HS256
export OPENAI_API_KEY=sk-...        # optional (mock mode when unset)
export N8N_WEBHOOK_URL=...          # optional

alembic upgrade head
python seed_db.py --username admin --password 'choose-a-password'
uvicorn backend.main:app --reload --port 8000

# 3. Frontend (second terminal, same virtualenv)
export API_URL=http://localhost:8000/api/v1
streamlit run frontend/app.py
```

Open http://localhost:8501, sign in, and you land on the Command Center. Use **Log Explorer → Ingest logs** with a
file from `sample_data/` (each sample can be downloaded there) to create an incident, then start the AI investigation.

## Environment variables

| Variable | Where | Purpose |
|---|---|---|
| `DATABASE_URL` | backend | PostgreSQL connection string |
| `SECRET_KEY` | backend | JWT signing key (long random value) |
| `ALGORITHM` | backend | JWT algorithm, default `HS256` |
| `OPENAI_API_KEY` | backend | Live LLM agents (mock mode when unset) |
| `N8N_WEBHOOK_URL` | backend | Incident notification webhook (optional) |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | seed script | Bootstrap operator |
| `API_URL` | frontend | Backend base URL, e.g. `http://localhost:8000/api/v1` |
| `SENTINELX_API_TIMEOUT` | frontend | Request timeout in seconds (default 10) |

Secrets are never displayed in the UI; Settings reports only whether each one is configured.

## API additions (read-only, all require a bearer token and an active account)

Existing routes are unchanged (`updated_at` was added to `/incidents` responses).

| Endpoint | Returns |
|---|---|
| `GET /api/v1/dashboard/summary?days=14` | Aggregates, daily series, network edges, top threats, per-incident timelines |
| `GET /api/v1/health` | Database, agent pipeline, LLM mode, audit-chain link checks |
| `GET /api/v1/events` | Searchable events (`q`, `event_type`, `severity`, `incident_id`, `start`, `end`, `order`, paging) with facets |
| `GET /api/v1/incidents/{id}/investigations` | Investigations with agent runs (timestamps, duration, output) and approvals |
| `GET /api/v1/agents/overview` | Per-agent statistics, recent runs, orchestration status |
| `GET /api/v1/risk/overview` | Per-incident risk as reported by the Risk Assessment Agent, with supporting evidence |
| `GET /api/v1/audit` | Audit records with backend verification status |
| `GET /api/v1/system/info` | Non-secret configuration status |

## How the numbers are defined

* **Threat Severity** is a *normalized index (0-100)*, not a measured percentage: the mean of severity weights
  (low 25, medium 50, high 75, critical 100) over unresolved incidents that have a severity.
* **System Health** = (passing checks + 0.5 × degraded checks) / total checks. Mock LLM mode counts as degraded;
  an unreachable API scores 0 (Critical).
* **Audit verification** checks each record's link to the previous one and *recomputes* the SHA-256 hash for
  investigation-start, approval and agent-execution records. Results: `verified`, `linked` (hash format not reproducible),
  `broken_link`, `hash_mismatch`. A record of a known type that has lost the fields needed to recompute its hash is
  reported as a mismatch. This proves internal consistency of the stored chain; it is not a digital signature and
  cannot detect a consistently rewritten chain. The Audit Agent's own `audit_trail_valid` flag is shown separately
  and labelled *agent-reported*.
* **Alert cards** state their own unit (incidents, events or approvals). *Malware detections* is shown as
  unavailable unless events are explicitly typed as malware, because the pipeline has no malware classifier.

## Tests

```bash
pip install pytest
pytest tests/test_dashboard_logic.py tests/test_console_logic.py tests/test_dashboard_metrics.py \
       tests/test_reporting.py tests/test_api_client.py tests/test_ui_components.py
```

These cover the aggregation and audit-verification logic, metric methodology, report generation, HTML escaping,
empty/error states and the frontend API client (run against a real local HTTP server). The older
`tests/test_api.py` and `integration_test.py` need a running backend and database, and `tests/test_api.py` expects a
root `/health` route and a 400 on bad login that the current API does not provide.

## Project layout

```
backend/            FastAPI app (main.py), dashboard.py + console.py (read-only endpoints), *_logic.py (pure, tested)
agents/             The six LangGraph agents (unchanged)
database/           SQLAlchemy models and session
frontend/
  app.py            Sign-in; forwards signed-in operators to the Command Center
  pages/            1_Command_Center ... 8_Settings
  sentinelx_ui/     Shared design system: theme, navigation (sidebar), api client, widgets, charts, views/*, reporting
  assets/           Original security-AI illustration
.streamlit/         Dark theme configuration
```

## Troubleshooting

* *"Authentication required" on a page*: your session token expired (30 minutes). Sign in again.
* *"... is not available on this backend version"*: update the backend; the page needs the endpoints listed above.
* *Layout looks unstyled or `st.container(key=...)` errors*: upgrade Streamlit (`pip install -U "streamlit>=1.41"`).
* *Agents report "Mock"*: set `OPENAI_API_KEY` on the **backend** and restart it.
