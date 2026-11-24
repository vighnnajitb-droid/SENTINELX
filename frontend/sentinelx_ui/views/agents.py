"""Agent Operations view builders (pure HTML, recorded data only)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .. import charts
from ..components import esc
from ..widgets import (badge, empty_state, expand_table, fmt_dur, fmt_pct, fmt_ts, json_block, kpi, kpi_row, kv_grid,
                       status_badge)

ROLE = {
    "DetectionAgent": ("01", "Analyzes incoming security events and identifies suspicious activity."),
    "InvestigationAgent": ("02", "Correlates evidence and builds the incident investigation context."),
    "ThreatIntelAgent": ("03", "Enriches indicators with available threat intelligence."),
    "RiskAssessmentAgent": ("04", "Evaluates severity, confidence and potential impact."),
    "AuditAgent": ("05", "Checks evidence and accountability records."),
    "ResponseAgent": ("06", "Proposes human-approved defensive response actions."),
}
LABEL = {k: l for k, l, _ in charts.AGENT_FLOW}


def kpis(ov: Dict[str, Any]) -> str:
    agents = ov.get("agents") or []
    total = sum(a["total_runs"] for a in agents)
    failed = sum(a["failed"] for a in agents)
    inv = ov.get("investigations", {}).get("by_status", {})
    durations = [a["avg_duration_s"] for a in agents if a.get("avg_duration_s") is not None]
    return kpi_row([
        kpi("Agent runs recorded", total, f'{ov.get("runs_scanned", 0):,} scanned', "blue"),
        kpi("Failed runs", failed, "agent run status failed", "critical" if failed else "muted"),
        kpi("Investigations", ov.get("investigations", {}).get("total"), f'{inv.get("running", 0)} running · {inv.get("failed", 0)} failed', "cyan"),
        kpi("Awaiting review", inv.get("awaiting_review", 0), "held for a human", "medium" if inv.get("awaiting_review") else "muted"),
        kpi("Pending approvals", ov.get("pending_approvals"), "response actions", "medium" if ov.get("pending_approvals") else "muted"),
        kpi("Avg agent duration", fmt_dur(sum(durations) / len(durations)) if durations else None, "completed runs with timestamps", "ok",
            unavailable="no timed runs"),
    ])


def flow_states(agents: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out = {}
    for a in agents:
        state = a.get("last_status") or "not_run"
        detail = ("never run" if not a["total_runs"] else f'{a["total_runs"]} run(s) · avg {fmt_dur(a.get("avg_duration_s"))}')
        out[a["name"]] = {"state": state if state in charts.STATE_COLOR else "completed", "detail": detail}
    return out


def agent_cards(agents: List[Dict[str, Any]]) -> str:
    cards = []
    for a in agents:
        num, desc = ROLE.get(a["name"], ("", ""))
        status = status_badge(a["last_status"]) if a.get("last_status") else badge("Not run yet", "muted")
        cards.append(
            f'<div class="sx-agent"><div class="h"><span class="n">AGENT / {esc(num)}</span>{status}</div>'
            f'<div class="nm">{esc(LABEL.get(a["name"], a["name"]))} Agent</div><div class="ds">{esc(desc)}</div>'
            f'<div class="st"><div><span>Runs</span><b>{a["total_runs"]}</b></div>'
            f'<div><span>Failed</span><b>{a["failed"]}</b></div>'
            f'<div><span>Avg time</span><b>{esc(fmt_dur(a.get("avg_duration_s")))}</b></div></div>'
            f'<div class="sx-netcap" style="margin-top:6px">Last run: {esc(fmt_ts(a["last_run_at"])) if a.get("last_run_at") else "never"}</div></div>')
    return f'<div class="sx-agrid">{"".join(cards)}</div>'


def run_history(runs: List[Dict[str, Any]]) -> str:
    cols = [{"label": "Agent", "width": "1.6fr"}, {"label": "Status", "width": "1fr"}, {"label": "Incident", "width": "2.2fr"},
            {"label": "Started", "width": "1.4fr"}, {"label": "Duration", "width": ".8fr"}]
    rows = []
    for r in runs:
        has_output = r.get("output_data") is not None
        detail = (kv_grid([("Run ID", r.get("id")), ("Investigation", r.get("investigation_id")), ("Incident ID", r.get("incident_id")),
                           ("Completed", fmt_ts(r.get("completed_at"))), ("Error", r.get("error_message"))], 2)
                  + '<div class="sx-sub">Agent output</div>'
                  + (json_block(r["output_data"]) if has_output else '<div class="sx-muted">Output is loaded for the 30 most recent runs only.</div>'))
        rows.append({"cells": [esc(LABEL.get(r["agent_name"], r["agent_name"])), status_badge(r.get("status")),
                               esc(r.get("incident_title") or "—"), f'<span class="sx-mono">{esc(fmt_ts(r.get("started_at")))}</span>',
                               esc(fmt_dur(r.get("duration_s")))],
                     "detail": detail, "tone": "critical" if (r.get("status") or "").lower() in ("failed", "error") else ""})
    return expand_table(cols, rows, empty="No agent runs match the current filters")


def orchestration(recent: List[Dict[str, Any]]) -> str:
    cols = [{"label": "Incident", "width": "2.2fr"}, {"label": "Status", "width": "1.5fr"},
            {"label": "Conf.", "width": ".8fr"}, {"label": "Time", "width": ".9fr"}]
    rows = [{"cells": [esc(i.get("incident_title") or i.get("incident_id")), status_badge(i.get("status")),
                       esc(fmt_pct(i.get("confidence_score"))), esc(fmt_dur(i.get("duration_s")))],
             "detail": kv_grid([("Investigation ID", i.get("id")), ("Incident ID", i.get("incident_id")),
                                ("Started", fmt_ts(i.get("created_at"))), ("Last update", fmt_ts(i.get("updated_at")))], 2),
             "tone": "critical" if (i.get("status") or "") == "failed" else ""} for i in recent]
    return expand_table(cols, rows, empty="No investigations have been orchestrated yet")
