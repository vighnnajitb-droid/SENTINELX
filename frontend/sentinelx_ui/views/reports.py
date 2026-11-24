"""Report preview builders (pure HTML) built from the report model in reporting.py."""
from __future__ import annotations

from typing import Any, Dict

from ..components import esc
from ..widgets import (badge, bullet_list, chips, empty_state, expand_table, fmt_dur, fmt_pct, fmt_ts, kpi, kpi_row, kv_grid,
                       kv_grid_html, notice, severity_badge, status_badge, vtimeline)


def header_kpis(r: Dict[str, Any]) -> str:
    i, inv = r["incident"], r["investigation"]
    return kpi_row([
        kpi("Status", (i.get("status") or "unknown").capitalize(), "", "blue"),
        kpi("Severity", (i.get("severity") or "unscored").capitalize(), "", {"critical": "critical", "high": "high"}.get((i.get("severity") or "").lower(), "cyan")),
        kpi("Events", r["evidence"]["events_total"], "recorded", "cyan"),
        kpi("Investigation", (inv["status"] if inv else "none").replace("_", " ").capitalize(), f'{inv["runs_recorded"]} run(s)' if inv else "not run", "blue"),
        kpi("Agents reported", len(r["agents"]), "of 6", "ok" if len(r["agents"]) == 6 else "medium"),
    ])


def sections(r: Dict[str, Any]) -> Dict[str, str]:
    i, f = r["incident"], r["findings"]
    tl = vtimeline([{"title": t["title"], "time": fmt_ts(t["time"]) if t["time"] else None, "body": t.get("detail"),
                     "state": "failed" if "failed" in t["title"] or "rejected" in t["title"] else "done"} for t in r["timeline"]])
    details = kv_grid([("Incident ID", i.get("id")), ("Created", fmt_ts(i.get("created_at"))), ("Last updated", fmt_ts(i.get("updated_at"))),
                       ("Report generated", r["generated_at"])], 1) + (f'<div class="sx-sub">Description</div><div style="font-size:13px;color:var(--sx-text2)">{esc(i["description"])}</div>' if i.get("description") else "")
    if r["investigation"]:
        susp = {True: badge("Suspicious activity flagged", "critical"), False: badge("No suspicious activity flagged", "ok")}.get(f["suspicious"], badge("Detection result unavailable", "muted"))
        findings = (susp + '<div class="sx-sub">Detection findings</div>' + bullet_list(f["detection"], "No findings recorded")
                    + '<div class="sx-sub">Correlation summary</div>'
                    + f'<div style="font-size:13px;color:var(--sx-text2)">{esc(f.get("correlation_summary") or "None recorded")}</div>'
                    + ('<div class="sx-sub">Entities involved</div>' + chips(f["entities"], "info") if f["entities"] else "")
                    + ('<div class="sx-sub">Threat intelligence indicators</div>' + chips(f["indicators"][:15]) if f["indicators"] else ""))
    else:
        findings = empty_state("No investigation findings", "No investigation has been run for this incident.")
    risk = r["risk"]
    risk_html = (kv_grid_html([("Severity", severity_badge(risk.get("severity"))), ("Confidence", esc(fmt_pct(risk.get("confidence"))))], 2)
                 + f'<div style="font-size:13px;color:var(--sx-text2);margin-top:6px">{esc(risk.get("justification") or "No justification recorded")}</div>'
                 if risk else empty_state("No risk assessment recorded"))
    rec = r["recommendations"]
    rec_html = ('<div class="sx-sub">Recommendations</div>' + bullet_list(rec["recommendations"]) + '<div class="sx-sub">Proposed automated actions</div>'
                + bullet_list(rec["proposed_actions"], "None proposed")) if rec else ""
    cols = [{"label": "Agent", "width": "2fr"}, {"label": "Status", "width": "1fr"}, {"label": "Completed", "width": "1.5fr"}, {"label": "Duration", "width": ".8fr"}]
    agents = expand_table(cols, [{"cells": [esc(a["agent"]), status_badge(a.get("status")), f'<span class="sx-mono">{esc(fmt_ts(a.get("completed_at")))}</span>', esc(fmt_dur(a.get("duration_s")))]} for a in r["agents"]],
                          empty="No agent runs recorded")
    ev = r["evidence"]
    evidence = (kv_grid([("Events", ev["events_total"]), ("Event types", ", ".join(f"{k} ({v})" for k, v in ev["by_type"].items()) or None),
                         ("Top sources", ", ".join(f"{k} ({v})" for k, v in ev["top_sources"]) or None),
                         ("Top destinations", ", ".join(f"{k} ({v})" for k, v in ev["top_destinations"]) or None)], 1))
    audit = r.get("audit")
    audit_html = (kv_grid([("Audit records for this incident", audit["records"])], 1) + notice(audit["note"], "info")) if audit else empty_state("Audit data unavailable")
    return {"summary": f'<div style="font-size:14px;line-height:1.65;color:var(--sx-text)">{esc(r["executive_summary"])}</div>',
            "details": details, "timeline": tl, "findings": findings, "risk": risk_html + rec_html, "agents": agents,
            "evidence": evidence, "audit": audit_html}
