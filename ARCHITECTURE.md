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
