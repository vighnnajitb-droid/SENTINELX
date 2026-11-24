"""Investigation Center view builders (pure HTML, real recorded data only)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .. import charts
from ..components import esc
from ..widgets import (badge, bullet_list, chips, empty_state, expand_table, fmt_dur, fmt_pct, fmt_ts, json_block,
                       kpi, kpi_row, kv_grid, kv_grid_html, notice, progress, severity_badge, status_badge, vtimeline)

AGENT_LABEL = {k: l for k, l, _ in charts.AGENT_FLOW}


def agent_states(inv: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """State of each of the six agents for one investigation, from recorded runs only."""
    runs = {r["agent_name"]: r for r in (inv or {}).get("agent_runs", [])}
    inv_status = ((inv or {}).get("status") or "").lower()
    out = {}
    for key, _, _ in charts.AGENT_FLOW:
        run = runs.get(key)
        if run:
            status = (run.get("status") or "").lower()
            state = "completed" if status == "completed" else ("failed" if status in ("failed", "error") else status or "completed")
            out[key] = {"state": state, "detail": f'duration {fmt_dur(run.get("duration_s"))}'}
        elif inv_status == "running":
            out[key] = {"state": "pending", "detail": "agent results are recorded when the pipeline finishes"}
        elif inv_status == "awaiting_review":
            out[key] = {"state": "awaiting_review", "detail": "held for human review; no output recorded"}
        elif inv_status == "failed":
            out[key] = {"state": "not_run", "detail": "investigation failed before this agent was recorded"}
        else:
            out[key] = {"state": "not_run", "detail": "no recorded run"}
    return out


def progress_pct(inv: Optional[Dict[str, Any]]) -> float:
    states = agent_states(inv)
    return 100.0 * sum(1 for s in states.values() if s["state"] == "completed") / len(states)


def kpis(incident: Dict[str, Any], inv: Optional[Dict[str, Any]], events_count: Optional[int], n_inv: int, pending: int) -> str:
    conf = (inv or {}).get("confidence_score")
    return kpi_row([
        kpi("Incident status", (incident.get("status") or "unknown").capitalize(), "", "blue"),
        kpi("Severity", (incident.get("severity") or "unscored").capitalize(), "assigned by Risk Assessment Agent" if incident.get("severity") else "not yet assessed",
            {"critical": "critical", "high": "high", "medium": "medium"}.get((incident.get("severity") or "").lower(), "cyan")),
        kpi("Investigation", ((inv or {}).get("status") or "none").replace("_", " ").capitalize(), f"{n_inv} run(s) recorded", "cyan"),
        kpi("Confidence", fmt_pct(conf) if isinstance(conf, (int, float)) else None, "investigation record", "ok",
            unavailable="not recorded"),
        kpi("Events", events_count, "linked to this incident", "blue"),
        kpi("Pending approvals", pending, "awaiting a human decision", "medium" if pending else "muted"),
    ])


def timeline(incident: Dict[str, Any], inv: Optional[Dict[str, Any]]) -> str:
    """Chronological activity from real timestamps; entries lacking a timestamp say so."""
    items = [{"t": incident.get("created_at"), "title": "Incident created", "state": "done", "body": incident.get("title")}]
    if inv:
        status = (inv.get("status") or "").lower()
        items.append({"t": inv.get("created_at"), "title": "Investigation started",
                      "state": "active" if status == "running" else "done", "body": None,
                      "badge": status_badge(status)})
        for run in inv.get("agent_runs", []):
            ok = (run.get("status") or "").lower() == "completed"
            items.append({"t": run.get("completed_at") or run.get("started_at"),
                          "title": f'{AGENT_LABEL.get(run["agent_name"], run["agent_name"])} {"completed" if ok else run.get("status")}',
                          "state": "done" if ok else "failed", "body": f'Duration {fmt_dur(run.get("duration_s"))}'
                          + (f' · {run["error_message"]}' if run.get("error_message") else "")})
        for a in inv.get("approvals", []):
            items.append({"t": a.get("created_at"), "title": f'Approval requested · {a.get("action_type")}', "state": "warn" if a.get("status") == "pending" else "done", "body": None})
            if a.get("resolved_at"):
                items.append({"t": a["resolved_at"], "title": f'Approval {a.get("status")}', "state": "failed" if a.get("status") == "rejected" else "done", "body": None})
        if status in ("completed", "failed"):
            items.append({"t": inv.get("updated_at"), "title": f"Investigation {status}", "state": "failed" if status == "failed" else "done", "body": None})
    items.sort(key=lambda i: i["t"] or "9999")
    return vtimeline([{"title": i["title"], "time": fmt_ts(i["t"]) if i["t"] else None, "state": i["state"],
                       "body": i["body"], "badge_html": i.get("badge", "")} for i in items])


def _out(inv: Optional[Dict[str, Any]], agent: str) -> Dict[str, Any]:
    for run in (inv or {}).get("agent_runs", []):
        if run["agent_name"] == agent and isinstance(run.get("output_data"), dict):
            return run["output_data"]
    return {}


def findings(inv: Optional[Dict[str, Any]]) -> str:
    if not inv or not inv.get("agent_runs"):
        return empty_state("No agent findings yet", "Run an investigation to produce findings. Nothing is shown until agents have reported.")
    det, invs, intel = _out(inv, "DetectionAgent"), _out(inv, "InvestigationAgent"), _out(inv, "ThreatIntelAgent")
    risk, audit, resp = _out(inv, "RiskAssessmentAgent"), _out(inv, "AuditAgent"), _out(inv, "ResponseAgent")
    parts = []
    if det:
        parts.append('<div class="sx-sub">Detection</div>' + kv_grid_html([("Suspicious activity", badge("Yes", "critical") if det.get("is_suspicious") else badge("No", "ok"))], 1)
                     + bullet_list(det.get("findings") or [], "No findings reported"))
    if invs:
        parts.append('<div class="sx-sub">Investigation</div>' + f'<div class="sx-findings">{esc(invs.get("correlation_summary") or "No correlation summary")}</div>'
                     + ('<div class="sx-sub">Entities involved</div>' + chips(invs.get("entities_involved") or [], "info") if invs.get("entities_involved") else ""))
    if intel:
        flagged = [i for i in (intel.get("enriched_indicators") or []) if isinstance(i, dict)]
        parts.append('<div class="sx-sub">Threat intelligence</div>'
                     + kv_grid_html([("Known threats matched", badge("Yes", "critical") if intel.get("known_threats_found") else badge("No", "ok")),
                                     ("Indicators enriched", esc(len(flagged)))], 2)
                     + chips([f'{i.get("indicator")} · {i.get("reputation")}' for i in flagged[:12]], "muted"))
    if risk:
        parts.append('<div class="sx-sub">Risk assessment</div>'
                     + kv_grid_html([("Severity", severity_badge(risk.get("severity"))), ("Confidence", esc(fmt_pct(risk.get("confidence_score"))))], 2)
                     + f'<div class="sx-findings" style="margin-top:6px">{esc(risk.get("justification") or "No justification recorded")}</div>')
    if audit:
        parts.append('<div class="sx-sub">Audit agent (agent-reported, not backend verification)</div>'
                     + kv_grid_html([("Evidence verified", badge("Yes", "ok") if audit.get("evidence_verified") else badge("No", "medium")),
                                     ("Audit trail valid", badge("Yes", "ok") if audit.get("audit_trail_valid") else badge("No", "medium"))], 2)
                     + bullet_list(audit.get("discrepancies") or [], "No discrepancies reported"))
    if resp:
        parts.append('<div class="sx-sub">Response recommendations</div>' + bullet_list(resp.get("recommendations") or [], "No recommendations")
                     + '<div class="sx-sub">Proposed automated actions</div>' + bullet_list(resp.get("automated_actions_proposed") or [], "None proposed")
                     + kv_grid_html([("Requires human approval", badge("Yes", "medium") if resp.get("requires_human_approval") else badge("No", "muted"))], 1))
    return "".join(parts) or empty_state("Agents reported no structured findings")


def evidence(events: List[Dict[str, Any]]) -> Dict[str, str]:
    if not events:
        return {"chart": empty_state("No events linked to this incident"), "table": ""}
    counts: Dict[str, int] = {}
    for e in events:
        counts[e.get("type") or "unknown"] = counts.get(e.get("type") or "unknown", 0) + 1
    cols = [{"label": "Timestamp", "width": "1.5fr"}, {"label": "Event type", "width": "1.2fr"},
            {"label": "Source", "width": "1.2fr"}, {"label": "Destination", "width": "1.2fr"}]
    rows = [{"cells": [f'<span class="sx-mono">{esc(fmt_ts(e.get("timestamp")) if e.get("timestamp") else "unavailable")}</span>',
                       esc(e.get("type") or "unknown"), f'<span class="sx-mono">{esc(e.get("source") or "—")}</span>',
                       f'<span class="sx-mono">{esc(e.get("destination") or "—")}</span>']} for e in events[:200]]
    note = f'<div class="sx-netcap">Showing {len(rows)} of {len(events)} events.</div>' if len(events) > 200 else ""
    return {"chart": charts.hbar_list(list(counts.items())), "table": expand_table(cols, rows) + note}


def agent_results(inv: Optional[Dict[str, Any]]) -> str:
    runs = (inv or {}).get("agent_runs") or []
    cols = [{"label": "Agent", "width": "2fr"}, {"label": "Status", "width": "1fr"},
            {"label": "Completed", "width": "1.5fr"}, {"label": "Duration", "width": ".8fr"}]
    rows = []
    for r in runs:
        detail = (kv_grid([("Started", fmt_ts(r.get("started_at"))), ("Completed", fmt_ts(r.get("completed_at"))),
                           ("Error", r.get("error_message"))], 3) + '<div class="sx-sub">Agent output</div>' + json_block(r.get("output_data")))
        rows.append({"cells": [esc(AGENT_LABEL.get(r["agent_name"], r["agent_name"])), status_badge(r.get("status")),
                               f'<span class="sx-mono">{esc(fmt_ts(r.get("completed_at")))}</span>', esc(fmt_dur(r.get("duration_s")))],
                     "detail": detail})
    return expand_table(cols, rows, empty="No agent runs recorded for this investigation")


def proposed_actions(reason: Optional[str]) -> List[str]:
    """Approval.reason stores the JSON list of proposed actions; fall back to the raw text."""
    if not reason:
        return []
    try:
        data = json.loads(reason)
        if isinstance(data, list):
            return [str(x) for x in data]
    except (TypeError, ValueError):
        pass
    return [str(reason)]


def approval_card(approval: Dict[str, Any]) -> str:
    return (f'<div class="sx-panel" style="margin-bottom:8px"><div class="sx-ptitle">{esc(approval.get("action_type"))}'
            f'<span class="sx-ptr">{status_badge(approval.get("status"))}</span></div>'
            + kv_grid([("Requested", fmt_ts(approval.get("created_at"))), ("Resolved", fmt_ts(approval.get("resolved_at")) if approval.get("resolved_at") else None)], 2)
            + '<div class="sx-sub">Proposed actions</div>' + bullet_list(proposed_actions(approval.get("reason")), "No actions listed") + "</div>")


def overview(incident: Dict[str, Any], events: List[Dict[str, Any]]) -> str:
    """Incident facts plus a compact evidence overview (recorded data only)."""
    counts: Dict[str, int] = {}
    for e in events:
        counts[e.get("type") or "unknown"] = counts.get(e.get("type") or "unknown", 0) + 1
    sources = {e["source"] for e in events if e.get("source")}
    dests = {e["destination"] for e in events if e.get("destination")}
    out = kv_grid_html([("Incident ID", f'<span class="sx-mono">{esc(incident.get("id"))}</span>'),
                        ("Status", status_badge(incident.get("status"))),
                        ("Created", esc(fmt_ts(incident.get("created_at")))), ("Last updated", esc(fmt_ts(incident.get("updated_at")))),
                        ("Distinct sources", esc(len(sources))), ("Distinct destinations", esc(len(dests)))], 2)
    if counts:
        out += '<div class="sx-sub">Event types</div>' + chips([f"{k} · {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])], "info")
    return out
