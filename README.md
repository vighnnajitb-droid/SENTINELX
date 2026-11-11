# SENTINELX - Autonomous Incident Response Network

Tagline: Detect. Investigate. Verify. Respond.

SENTINELX is an AI-powered cybersecurity investigation platform designed to automate and augment the capabilities of a Security Operations Center (SOC) using a network of six specialized AI agents orchestrated by LangGraph.

## Architecture

See `ARCHITECTURE.md` for a detailed breakdown of the system components.

## Features

- **Automated Ingestion**: Upload CSV and JSON security logs.
- **AI Orchestration**: Six distinct agents (Detection, Investigation, Threat Intel, Risk Assessment, Audit, Response) that collaborate on log analysis.
- **Tamper-Evident Audit Trail**: Event hashing and chain of custody tracking ensure evidence integrity.
- **Human-in-the-Loop**: Consequential actions (e.g., blocking IPs) or failed audits automatically route to a human operator for review.
- **n8n Integration**: Built-in workflows for alerts and daily summaries.

## Getting Started

### Local Development

1. Clone the repository and install requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Setup environment variables:
   ```bash
   cp .env.example .env
   # Add your OPENAI_API_KEY
   ```
3. Initialize the database:
   ```bash
   alembic upgrade head
   ```
4. Run the backend:
   ```bash
   uvicorn backend.main:app --reload
   ```
5. Run the frontend:
   ```bash
   streamlit run frontend/app.py
   ```

### Docker Deployment

To run the entire stack (PostgreSQL, FastAPI, Streamlit, n8n) locally:

```bash
docker-compose up --build
```

### Cloud Deployment (Render)

A `render.yaml` blueprint is provided. Connect your GitHub repository to Render and it will automatically provision the PostgreSQL database, Backend API, and Frontend dashboard. Ensure you manually set `OPENAI_API_KEY` in the Render dashboard for the backend service.

## Testing

Run the automated test suite using pytest:

```bash
pytest tests/
```
## user and password
```User: sentinelx_judge
Password: demo123#
```
