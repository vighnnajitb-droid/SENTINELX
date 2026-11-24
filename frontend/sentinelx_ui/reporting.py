"""Incident report model and exporters (pure functions, no Streamlit).

The report is assembled exclusively from backend responses. The executive summary
is a template filled with recorded facts; nothing is generated or estimated.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from html import escape
from typing import Any, Dict, List, Optional

from .widgets import fmt_dur, fmt_pct, fmt_ts

AGENT_LABEL = {"DetectionAgent": "Detection", "InvestigationAgent": "Investigation", "ThreatIntelAgent": "Threat Intelligence",
               "RiskAssessmentAgent": "Risk Assessment", "AuditAgent": "Audit", "ResponseAgent": "Response"}


def _out(inv: Optional[Dict[str, Any]], agent: str) -> Dict[str, Any]:
    for run in (inv or {}).get("agent_runs", []):
        if run.get("agent_name") == agent and isinstance(run.get("output_data"), dict):
            return run["output_data"]
    return {}


def build_report(incident: Dict[str, Any], investigations: List[Dict[str, Any]], audit: Optional[Dict[str, Any]],
                 api_report: Optional[Dict[str, Any]] = None, now: Optional[datetime] = None) -> Dict[str, Any]:
    events = incident.get("events") or []
    inv = investigations[0] if investigations else None
    det, invs, intel = _out(inv, "DetectionAgent"), _out(inv, "InvestigationAgent"), _out(inv, "ThreatIntelAgent")
    risk, audit_agent, resp = _out(inv, "RiskAssessmentAgent"), _out(inv, "AuditAgent"), _out(inv, "ResponseAgent")

    types = Counter((e.get("type") or "unknown") for e in events)
    sources = Counter(e["source"] for e in events if e.get("source"))
    dests = Counter(e["destination"] for e in events if e.get("destination"))
    pending = [a for a in (inv or {}).get("approvals", []) if a.get("status") == "pending"]

    timeline = [{"time": incident.get("created_at"), "title": "Incident created", "detail": incident.get("title")}]
    if inv:
        timeline.append({"time": inv.get("created_at"), "title": "Investigation started", "detail": None})
        for run in inv.get("agent_runs", []):
            timeline.append({"time": run.get("completed_at") or run.get("started_at"),
                             "title": f'{AGENT_LABEL.get(run["agent_name"], run["agent_name"])} agent {run.get("status")}',
                             "detail": f'duration {fmt_dur(run.get("duration_s"))}'})
        for a in inv.get("approvals", []):
            timeline.append({"time": a.get("created_at"), "title": f'Approval requested ({a.get("action_type")})', "detail": None})
            if a.get("resolved_at"):
                timeline.append({"time": a["resolved_at"], "title": f'Approval {a.get("status")}', "detail": None})
        if inv.get("status") in ("completed", "failed"):
            timeline.append({"time": inv.get("updated_at"), "title": f'Investigation {inv.get("status")}', "detail": None})
    timeline.sort(key=lambda t: t["time"] or "9999")

    sev = (incident.get("severity") or "").lower() or None
    sentences = [f'Incident "{incident.get("title") or "Untitled"}" is {(incident.get("status") or "of unknown status").replace("_", " ")} '
                 f'with {sev + " severity" if sev else "no assigned severity"}.']
    if events:
        top = ", ".join(f"{t} ({c})" for t, c in types.most_common(3))
        sentences.append(f"{len(events)} event(s) are recorded, mainly {top}.")
    else:
        sentences.append("No events are linked to this incident.")
    if inv:
        conf = inv.get("confidence_score") if inv.get("confidence_score") is not None else risk.get("confidence_score")
        sentences.append(f"{len(investigations)} investigation run(s) are recorded; the latest is {str(inv.get('status')).replace('_', ' ')}"
                         + (f" with an agent-stated confidence of {fmt_pct(conf)}." if isinstance(conf, (int, float)) else "."))
        if det.get("is_suspicious") is True:
            sentences.append("The Detection Agent flagged suspicious activity.")
        elif det.get("is_suspicious") is False:
            sentences.append("The Detection Agent did not flag suspicious activity.")
        if risk.get("justification"):
            sentences.append(f'Risk assessment: {risk["justification"]}')
        if pending:
            sentences.append(f"{len(pending)} response approval(s) are awaiting a human decision.")
    else:
        sentences.append("No investigation has been run for this incident.")

    return {
        "generated_at": (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "incident": {k: incident.get(k) for k in ("id", "title", "description", "status", "severity", "created_at", "updated_at")},
        "executive_summary": " ".join(sentences),
        "timeline": timeline,
        "investigation": None if not inv else {
            "id": inv.get("id"), "status": inv.get("status"), "summary": inv.get("summary"),
            "confidence_score": inv.get("confidence_score"), "runs_recorded": len(investigations),
            "started_at": inv.get("created_at"), "updated_at": inv.get("updated_at")},
        "findings": {
            "suspicious": det.get("is_suspicious"), "detection": det.get("findings") or [],
            "correlation_summary": invs.get("correlation_summary"), "entities": invs.get("entities_involved") or [],
            "known_threats_found": intel.get("known_threats_found"),
            "indicators": [f'{i.get("indicator")} ({i.get("reputation")})' for i in (intel.get("enriched_indicators") or []) if isinstance(i, dict)]},
        "risk": None if not risk else {"severity": risk.get("severity"), "confidence": risk.get("confidence_score"),
                                       "justification": risk.get("justification")},
        "recommendations": None if not resp else {"recommendations": resp.get("recommendations") or [],
                                                  "proposed_actions": resp.get("automated_actions_proposed") or [],
                                                  "requires_human_approval": resp.get("requires_human_approval")},
        "agents": [{"agent": AGENT_LABEL.get(r["agent_name"], r["agent_name"]), "status": r.get("status"),
                    "completed_at": r.get("completed_at"), "duration_s": r.get("duration_s")} for r in (inv or {}).get("agent_runs", [])],
        "approvals": [{"action": a.get("action_type"), "status": a.get("status"), "requested": a.get("created_at"),
                       "resolved": a.get("resolved_at")} for a in (inv or {}).get("approvals", [])],
        "evidence": {"events_total": len(events), "by_type": dict(types), "top_sources": sources.most_common(5),
                     "top_destinations": dests.most_common(5)},
        "audit": None if not audit else {
            "records": audit.get("total"), "verification": {k: v for k, v in (audit.get("verification") or {}).items()
                                                             if k in ("verified", "linked", "broken_link", "hash_mismatch")},
            "note": "Counts shown are chain-wide; per-record verification is available in the Audit Trail."},
        "audit_agent_report": None if not audit_agent else {
            "evidence_verified": audit_agent.get("evidence_verified"), "audit_trail_valid": audit_agent.get("audit_trail_valid"),
            "discrepancies": audit_agent.get("discrepancies") or [], "note": "Agent-reported; not backend verification."},
        "api_report": api_report,
    }


def to_json(report: Dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, default=str)


def _bul(items: List[Any]) -> str:
    return "\n".join(f"- {i}" for i in items) if items else "- None recorded"


def to_markdown(r: Dict[str, Any]) -> str:
    i, f = r["incident"], r["findings"]
    lines = [f'# Incident Report: {i.get("title") or "Untitled"}', "", f'_Generated {r["generated_at"]} from SENTINELX backend data._', "",
             "## Executive summary", r["executive_summary"], "", "## Incident details",
             f'- **ID:** {i.get("id")}', f'- **Status:** {i.get("status")}', f'- **Severity:** {i.get("severity") or "unscored"}',
             f'- **Created:** {fmt_ts(i.get("created_at"))}', f'- **Last updated:** {fmt_ts(i.get("updated_at"))}']
    if i.get("description"):
        lines += ["", i["description"]]
    lines += ["", "## Timeline"] + [f'- {fmt_ts(t["time"]) if t["time"] else "time unavailable"}: **{t["title"]}**' + (f' ({t["detail"]})' if t.get("detail") else "") for t in r["timeline"]]
    lines += ["", "## Investigation findings"]
    if r["investigation"]:
        lines += [f'Latest investigation status: **{r["investigation"]["status"]}**', "", "**Detection findings**", _bul(f["detection"]), "",
                  f'**Correlation summary:** {f.get("correlation_summary") or "none recorded"}', "", "**Entities involved**", _bul(f["entities"]), "",
                  "**Threat intelligence indicators**", _bul(f["indicators"])]
    else:
        lines.append("No investigation has been run.")
    lines += ["", "## Risk assessment"]
    lines += ([f'- **Severity:** {r["risk"].get("severity")}', f'- **Confidence:** {fmt_pct(r["risk"].get("confidence"))}',
               f'- **Justification:** {r["risk"].get("justification") or "none recorded"}'] if r["risk"] else ["No risk assessment recorded."])
    if r["recommendations"]:
        lines += ["", "## Recommendations", _bul(r["recommendations"]["recommendations"]), "", "**Proposed automated actions**",
                  _bul(r["recommendations"]["proposed_actions"])]
    lines += ["", "## Agent findings"] + ([f'- {a["agent"]}: {a["status"]} ({fmt_dur(a.get("duration_s"))})' for a in r["agents"]] or ["- No agent runs recorded"])
    e = r["evidence"]
    lines += ["", "## Evidence summary", f'- **Events:** {e["events_total"]}',
              f'- **By type:** {", ".join(f"{k} ({v})" for k, v in e["by_type"].items()) or "none"}',
              f'- **Top sources:** {", ".join(f"{k} ({v})" for k, v in e["top_sources"]) or "none"}',
              f'- **Top destinations:** {", ".join(f"{k} ({v})" for k, v in e["top_destinations"]) or "none"}']
    if r["audit"]:
        v = r["audit"]["verification"]
        lines += ["", "## Audit", f'- Records for this incident: {r["audit"]["records"]}',
                  f'- Chain verification (backend): {v.get("verified", 0)} verified, {v.get("linked", 0)} linked only, '
                  f'{v.get("broken_link", 0) + v.get("hash_mismatch", 0)} failed']
    return "\n".join(lines) + "\n"


def to_html(r: Dict[str, Any]) -> str:
    """Self-contained, print-friendly HTML (use the browser's Print > Save as PDF)."""
    e = escape
    i, f = r["incident"], r["findings"]
    ul = lambda items: "<ul>" + "".join(f"<li>{e(str(x))}</li>" for x in items) + "</ul>" if items else "<p class=m>None recorded</p>"
    rows = lambda pairs: "".join(f"<tr><th>{e(k)}</th><td>{e(str(v)) if v not in (None, '') else '<span class=m>unavailable</span>'}</td></tr>" for k, v in pairs)
    tl = "".join(f'<tr><td class=t>{e(fmt_ts(t["time"]) if t["time"] else "unavailable")}</td><td><b>{e(t["title"])}</b>'
                 f'{" — " + e(str(t["detail"])) if t.get("detail") else ""}</td></tr>' for t in r["timeline"])
    ag = "".join(f'<tr><td>{e(a["agent"])}</td><td>{e(str(a["status"]))}</td><td>{e(fmt_dur(a.get("duration_s")))}</td></tr>' for a in r["agents"])
    ev = r["evidence"]
    risk = (f'<table>{rows([("Severity", r["risk"].get("severity")), ("Confidence", fmt_pct(r["risk"].get("confidence"))), ("Justification", r["risk"].get("justification"))])}</table>'
            if r["risk"] else "<p class=m>No risk assessment recorded.</p>")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Incident Report: {e(i.get("title") or "Untitled")}</title>
<style>body{{font:14px/1.55 -apple-system,Segoe UI,Inter,sans-serif;color:#10213a;max-width:860px;margin:32px auto;padding:0 20px}}
h1{{font-size:24px;margin:0 0 4px}}h2{{font-size:16px;border-bottom:2px solid #087BFF;padding-bottom:4px;margin-top:26px;color:#06307a}}
table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;padding:5px 8px;border-bottom:1px solid #dbe4f0;vertical-align:top}}th{{width:170px;color:#4a5f80;font-weight:600}}
.m{{color:#7a8aa3}}.t{{white-space:nowrap;color:#4a5f80;width:170px}}.tag{{display:inline-block;background:#e8f1ff;border:1px solid #b9d4ff;border-radius:4px;padding:1px 8px;font-size:12px}}
@media print{{body{{margin:0}}}}</style></head><body>
<div class="m">SENTINELX · Incident Report · generated {e(r["generated_at"])}</div><h1>{e(i.get("title") or "Untitled")}</h1>
<span class="tag">{e(str(i.get("status")))}</span> <span class="tag">severity: {e(str(i.get("severity") or "unscored"))}</span>
<h2>Executive summary</h2><p>{e(r["executive_summary"])}</p>
<h2>Incident details</h2><table>{rows([("Incident ID", i.get("id")), ("Created", fmt_ts(i.get("created_at"))), ("Last updated", fmt_ts(i.get("updated_at"))), ("Description", i.get("description"))])}</table>
<h2>Timeline</h2><table>{tl}</table>
<h2>Investigation findings</h2>{"<h3>Detection findings</h3>" + ul(f["detection"]) + "<h3>Correlation summary</h3><p>" + e(f.get("correlation_summary") or "None recorded") + "</p><h3>Entities involved</h3>" + ul(f["entities"]) + "<h3>Threat intelligence indicators</h3>" + ul(f["indicators"]) if r["investigation"] else "<p class=m>No investigation has been run.</p>"}
<h2>Risk assessment</h2>{risk}
<h2>Agent findings</h2><table><tr><th>Agent</th><th>Status</th><th>Duration</th></tr>{ag or "<tr><td colspan=3 class=m>No agent runs recorded</td></tr>"}</table>
<h2>Evidence summary</h2><table>{rows([("Events", ev["events_total"]), ("By type", ", ".join(f"{k} ({v})" for k, v in ev["by_type"].items())), ("Top sources", ", ".join(f"{k} ({v})" for k, v in ev["top_sources"])), ("Top destinations", ", ".join(f"{k} ({v})" for k, v in ev["top_destinations"]))])}</table>
</body></html>"""
