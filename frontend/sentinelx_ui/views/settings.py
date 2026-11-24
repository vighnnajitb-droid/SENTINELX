"""Settings view builders (pure HTML). Shows configuration *status*, never secret values."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from ..components import esc
from ..widgets import (badge, bullet_list, expand_table, fmt_dur, kv_grid, kv_grid_html, notice, status_badge)

SECTIONS = ["Connection", "Authentication", "Integrations", "Agents & LLM", "System", "Safe configuration"]

ENV_GUIDE = [
    ("SECRET_KEY", "Backend", "Signs JWT tokens. Must be a long random value; never the built-in default."),
    ("ALGORITHM", "Backend", "JWT signing algorithm (default HS256)."),
    ("DATABASE_URL", "Backend", "PostgreSQL connection string, including credentials. Keep out of source control."),
    ("OPENAI_API_KEY", "Backend", "Enables live LLM agents. When unset or a placeholder the agents run in deterministic mock mode."),
    ("N8N_WEBHOOK_URL", "Backend", "Webhook that receives incident notifications. The URL path can act as a secret."),
    ("ADMIN_USERNAME / ADMIN_PASSWORD", "Backend", "Optional bootstrap operator created at start-up. Remove after first use."),
    ("API_URL", "Frontend", "Base URL of the backend API, for example https://host/api/v1."),
]


def mask_url(url: str) -> str:
    """Remove any user:password@ portion before showing a URL."""
    try:
        p = urlparse(url)
        host = p.hostname + (f":{p.port}" if p.port else "") if p.hostname else ""
        return f"{p.scheme}://{host}{p.path}" if host else url
    except ValueError:
        return "(unparseable URL)"


def connection(api_url: str, health: Optional[Dict[str, Any]], info: Optional[Dict[str, Any]], latency_ms: Optional[float],
               reachable: bool) -> str:
    out = kv_grid_html([("API base URL", f'<span class="sx-mono">{esc(mask_url(api_url))}</span>'),
                        ("Backend reachable", badge("Yes", "ok") if reachable else badge("No", "critical")),
                        ("Last response time", esc(f"{latency_ms:.0f} ms" if latency_ms is not None else "—"))], 3)
    if info:
        db = info["database"]
        out += kv_grid_html([("Database", status_badge(db.get("status"))), ("Database engine", esc(db.get("engine") or "unknown")),
                             ("Database latency", esc(f'{db["latency_ms"]:.0f} ms' if db.get("latency_ms") is not None else "—"))], 3)
    if health:
        rows = [{"cells": [esc(c["label"]), status_badge(c["status"]), esc(c.get("detail") or "")]} for c in health.get("checks", [])]
        out += '<div class="sx-sub">Live health checks</div>' + expand_table(
            [{"label": "Check", "width": "1.4fr"}, {"label": "Status", "width": "1fr"}, {"label": "Detail", "width": "3fr"}], rows)
    return out


def authentication(info: Dict[str, Any], user: str, expiry: Optional[str]) -> str:
    a = info["authentication"]
    out = kv_grid_html([("Scheme", esc(a.get("scheme"))), ("Signing algorithm", esc(a.get("algorithm"))),
                        ("Token lifetime", esc(f'{a.get("token_lifetime_minutes")} minutes')),
                        ("JWT secret key", badge("Configured", "ok") if a.get("secret_key_configured") else badge("Not configured", "critical")),
                        ("Bootstrap operator", badge("Configured", "info") if a.get("bootstrap_admin_configured") else badge("Not set", "muted")),
                        ("Signed-in operator", esc(user)), ("Session expires", esc(expiry or "unavailable"))], 2)
    if a.get("uses_default_secret_key"):
        out += notice("The backend is using the built-in default SECRET_KEY. Anyone who knows it can forge tokens. "
                      "Set a long random SECRET_KEY before any real deployment.", "critical")
    return out


def integrations(info: Dict[str, Any], workflows: List[str]) -> str:
    n = info["n8n"]
    out = kv_grid_html([("n8n webhook", badge("Configured", "ok") if n.get("webhook_configured") else badge("Not configured", "muted")),
                        ("Webhook host", esc(n.get("host") or "—"))], 2)
    if not n.get("webhook_configured"):
        out += notice("N8N_WEBHOOK_URL is not set on the backend, so incident notifications are not sent to n8n.", "warn")
    out += '<div class="sx-sub">Workflow definitions shipped with this project</div>' + bullet_list(workflows, "No workflow files found")
    return out


def agents_llm(info: Dict[str, Any]) -> str:
    a = info["agents"]
    live = a.get("llm_mode") == "live"
    out = kv_grid_html([("LLM mode", badge("Live", "ok") if live else badge("Mock", "medium")),
                        ("LLM API key", badge("Configured", "ok") if a.get("llm_key_configured") else badge("Not configured", "muted"))], 2)
    if not live:
        out += notice("Agents run in deterministic mock mode. Findings are produced by built-in logic, not by a language model.", "warn")
    out += '<div class="sx-sub">Registered agents</div>' + bullet_list(a.get("agent_names") or [])
    return out


def system(info: Dict[str, Any], frontend_version: str) -> str:
    app = info["application"]
    return kv_grid([("Application", app.get("name")), ("API version", app.get("version")), ("Backend Python", app.get("python")),
                    ("Backend platform", app.get("platform")), ("Streamlit (frontend)", frontend_version)], 2)


def guidance() -> str:
    rows = [{"cells": [f'<span class="sx-mono">{esc(n)}</span>', esc(w), esc(d)]} for n, w, d in ENV_GUIDE]
    return (expand_table([{"label": "Variable", "width": "1.8fr"}, {"label": "Where", "width": ".8fr"}, {"label": "Purpose", "width": "4fr"}], rows)
            + '<div class="sx-sub">Safe practices</div>'
            + bullet_list(["Provide secrets through environment variables or your platform's secret manager, never in the repository.",
                           "Use a unique, random SECRET_KEY per environment and rotate it if it may have been exposed.",
                           "Serve the API over HTTPS and restrict allowed origins in production.",
                           "Remove bootstrap credentials after the first operator account is created.",
                           "This page never displays secret values; it only reports whether they are configured."]))
