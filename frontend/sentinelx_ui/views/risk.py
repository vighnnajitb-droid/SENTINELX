"""Risk Assessment view builders (pure HTML). Values are only what agents reported."""
from __future__ import annotations

from typing import Any, Dict, List

from .. import charts
from ..components import esc, gauge_svg
from ..widgets import (badge, bullet_list, chips, empty_state, expand_table, fmt_pct, fmt_ts, kpi, kpi_row, kv_grid,
                       kv_grid_html, notice, progress, severity_badge, status_badge)

ORDER = ["low", "medium", "high", "critical"]
CONF_METHOD = ("Average of the confidence values recorded by the Risk Assessment Agent (falling back to the investigation "
               "record). It measures the agent's stated confidence, not the probability that an incident is real.")


def kpis(ov: Dict[str, Any]) -> str:
    t, d = ov.get("totals", {}), ov.get("distribution", {})
    hi = d.get("critical", 0) + d.get("high", 0)
    return kpi_row([
        kpi("Incidents assessed", t.get("assessed"), f'of {t.get("incidents", 0):,} incidents', "blue"),
        kpi("Critical + High", hi, "by assigned severity", "critical" if hi else "muted"),
        kpi("Average confidence", fmt_pct(ov.get("avg_confidence")) if ov.get("avg_confidence") is not None else None,
            "agent-stated", "ok", unavailable="no confidence recorded"),
        kpi("Not yet assessed", t.get("unassessed"), "no risk assessment on record", "medium" if t.get("unassessed") else "muted"),
        kpi("Awaiting approval", t.get("awaiting_approval"), "response actions pending", "medium" if t.get("awaiting_approval") else "muted"),
    ])


def distribution(ov: Dict[str, Any]) -> Dict[str, str]:
    d = ov.get("distribution", {})
    total = sum(d.values())
    segs = [(k.capitalize(), d[k], charts.SEV_COLORS[k]) for k in ["critical", "high", "medium", "low", "unscored"] if d.get(k)]
    return {
        "donut": charts.donut(segs, center_value=f"{total:,}", center_label="incidents", empty="No incidents recorded"),
        "radar": charts.radar([(k.capitalize(), d.get(k, 0)) for k in ORDER], empty="No severity data"),
    }


def confidence_gauge(avg) -> str:
    bands = [(0, .5, "#FF303D", "Low"), (.5, .7, "#FFB547", "Fair"), (.7, .9, "#00D9FF", "Good"), (.9, 1, "#25E58A", "High")]
    if avg is None:
        return gauge_svg("cg", None, bands, "#00D9FF", "Unavailable", "no confidence recorded")
    color = "#25E58A" if avg >= .9 else "#00D9FF" if avg >= .7 else "#FFB547" if avg >= .5 else "#FF303D"
    return gauge_svg("cg", avg * 100, bands, color, "Average confidence", "agent-stated")


def confidence_chart(ov: Dict[str, Any]) -> str:
    return charts.bar_chart([(b["label"], b["count"]) for b in ov.get("confidence_buckets", [])], uid="rc",
                            color="#00D9FF", height=200, width=300, empty="No confidence values recorded")


def trend_chart(ov: Dict[str, Any]) -> str:
    trend = ov.get("trend") or []
    labels = [t["date"][5:] for t in trend]
    series = [("Avg confidence", [t["avg_confidence"] for t in trend], "#00D9FF")]
    return charts.line_chart(series, labels, uid="rt", ymax=1.0, percent=True,
                             empty="Not enough history to draw a trend")


def counts_chart(ov: Dict[str, Any]) -> str:
    trend = ov.get("trend") or []
    return charts.line_chart([("High + critical", [t["by_severity"].get("high", 0) + t["by_severity"].get("critical", 0) for t in trend], "#FF643D"),
                              ("All assessments", [t["count"] for t in trend], "#00A8FF")],
                             [t["date"][5:] for t in trend], uid="rn", empty="Not enough history to draw a trend")


def filter_rows(rows: List[Dict[str, Any]], severities: List[str], only_assessed: bool, sort: str) -> List[Dict[str, Any]]:
    out = [r for r in rows if (not severities or (r.get("severity") or "unscored") in severities)
           and (not only_assessed or r.get("assessed"))]
    if sort == "confidence":
        out.sort(key=lambda r: (r["confidence"] is None, -(r["confidence"] or 0)))
    elif sort == "severity":
        rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        out.sort(key=lambda r: rank.get(r.get("severity"), 4))
    return out


def risk_table(rows: List[Dict[str, Any]]) -> str:
    cols = [{"label": "Incident", "width": "2.6fr"}, {"label": "Severity", "width": ".9fr"}, {"label": "Confidence", "width": "1.4fr"},
            {"label": "Investigation", "width": "1.1fr"}, {"label": "Assessed", "width": "1.4fr"}]
    out = []
    for r in rows:
        conf = r.get("confidence")
        conf_html = (f'<div style="display:flex;align-items:center;gap:8px"><div style="flex:1">{progress((conf or 0) * 100, "ok" if conf >= .7 else "medium" if conf >= .5 else "critical")}</div>'
                     f'<span>{esc(fmt_pct(conf))}</span></div>') if isinstance(conf, (int, float)) else '<span class="sx-muted">not recorded</span>'
        ev = r.get("evidence") or {}
        detail = kv_grid_html([("Assigned severity", severity_badge(r.get("severity"))), ("Confidence", esc(fmt_pct(conf))),
                               ("Incident status", status_badge(r.get("status"))), ("Awaiting approval", badge("Yes", "medium") if r.get("awaiting_approval") else badge("No", "muted"))], 4)
        if r.get("assessed"):
            detail += ('<div class="sx-sub">Agent justification</div>'
                       f'<div style="font-size:13px;color:var(--sx-text2)">{esc(r.get("justification") or "No justification recorded")}</div>'
                       '<div class="sx-sub">Supporting evidence (as reported by agents)</div>'
                       + kv_grid_html([("Suspicious activity", badge("Yes", "critical") if ev.get("is_suspicious") else (badge("No", "ok") if ev.get("is_suspicious") is False else '<span class="na">unavailable</span>')),
                                       ("Known threats matched", badge("Yes", "critical") if ev.get("known_threats_found") else (badge("No", "ok") if ev.get("known_threats_found") is False else '<span class="na">unavailable</span>'))], 2)
                       + bullet_list(ev.get("findings") or [], "No detection findings recorded")
                       + ('<div class="sx-sub">Flagged indicators</div>' + chips(ev["flagged_indicators"], "critical") if ev.get("flagged_indicators") else "")
                       + ('<div class="sx-sub">Entities involved</div>' + chips(ev["entities"], "info") if ev.get("entities") else ""))
        else:
            detail += notice("No risk assessment has been recorded for this incident. Run an investigation to produce one.", "warn")
        detail += kv_grid([("Incident ID", r.get("incident_id")), ("Investigation ID", r.get("investigation_id")), ("Incident created", fmt_ts(r.get("created_at")))], 3)
        out.append({"cells": [esc(r.get("title") or "Untitled"), severity_badge(r.get("severity")) if r.get("assessed") or r.get("severity") else badge("Not assessed", "muted", dot=False),
                              conf_html, status_badge(r.get("investigation_status")) if r.get("investigation_status") else '<span class="sx-muted">none</span>',
                              f'<span class="sx-mono">{esc(fmt_ts(r.get("assessed_at")) if r.get("assessed_at") else "—")}</span>'],
                    "detail": detail, "tone": r.get("severity") if r.get("severity") in ("critical", "high") else ""})
    return expand_table(cols, out, empty="No incidents match the current filters")
