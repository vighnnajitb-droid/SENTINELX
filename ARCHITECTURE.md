# SENTINELX Architecture

## Overview
SENTINELX uses a modern Python-based microservice architecture, separating the presentation layer, business logic, agent orchestration, and background processing.

## Components

1. **Frontend (Streamlit)**
   - Located in `frontend/`.
   - Provides the interactive SOC dashboard with pages for Log Explorer, Command Center, Agent Operations, Risk Assessment, and Audit.
   - Communicates with the Backend via REST API using authenticated JWT tokens.

2. **Backend (FastAPI)**
   - Located in `backend/`.
   - Handles REST endpoints for authentication, log ingestion, triggering investigations, and querying the database.
   - Background tasks trigger the LangGraph execution so HTTP requests aren't blocked by slow LLMs.

3. **Database (PostgreSQL + SQLAlchemy)**
   - Located in `database/`.
   - Maintains state for users, incidents, security events, investigation runs, approvals, and the tamper-evident audit log.
   - Alembic manages schema migrations.

4. **Agent Orchestration (LangGraph)**
   - Located in `agents/`.
   - A state graph routes data sequentially:
     - **Detection**: Flags anomalies.
     - **Investigation**: Correlates events into a timeline.
     - **Threat Intel**: Enriches indicators.
     - **Risk Assessment**: Scores severity and confidence.
     - **Audit**: Verifies hashes and reasoning. Fails safe.
     - **Response**: Generates recommendations; tags consequential ones for human approval.

5. **Workflow Automation (n8n)**
   - Webhook integrations defined in `n8n-workflows/`.
   - Handles external notifications (Slack mock) and periodic reporting without cluttering core agent logic.


## Command Center (redesign) — data contracts and methodology

Frontend package: `frontend/sentinelx_ui/` (`theme.py`, `api.py`, `metrics.py`, `components.py`, `dashboard.css`);
global tokens live in `frontend/theme.css`. Every page calls `apply_theme()`; no page carries its own CSS block.

Additive backend endpoints (both require a bearer token **and** an active account):

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/dashboard/summary?days=14` | Incident/event/approval aggregates, daily series, network edges, top threats, per-incident timelines |
| `GET /api/v1/health` | Live checks: database round trip, agent graph compiles, LLM mode (mock = degraded), audit hash-link consistency |

`GET /api/v1/incidents` and `GET /api/v1/incidents/{id}` gained an `updated_at` field (additive).
Pure aggregation logic is in `backend/dashboard_logic.py` (unit-tested without a database).

**Threat Severity** is a *normalized index (0-100)*, not a measured percentage: mean of weights
(low 25, medium 50, high 75, critical 100) over unresolved incidents that have a severity.

**System Health** = (ok checks + 0.5 x degraded checks) / total checks, over the server checks plus measured
API reachability and latency. Any degraded check caps the state at Warning, any failed check at Degraded;
a failed database check, an unreachable API, or a score under 50 is Critical.

**Alert Statistics units differ per card and are labelled on the card:** Total/Critical = incident records,
Intrusion = events (`port_scan` + failed logins), Malware = events typed as malware (Unavailable when the
pipeline recorded none: it has no malware classifier), Pending Approvals = approval rows.

Auto-refresh is off by default; when enabled it runs in an `st.fragment` at >= 15 s, and reruns inside a 10 s
window reuse the per-session cached response.
