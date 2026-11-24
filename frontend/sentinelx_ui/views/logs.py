"""Log Explorer view builders (pure HTML)."""
from __future__ import annotations

from typing import Any, Dict, List

from .. import charts
from ..components import esc
from ..widgets import (badge, expand_table, fmt_ts, json_block, kpi, kpi_row, kv_grid, severity_badge)

COLUMNS = [{"label": "Timestamp", "width": "1.5fr"}, {"label": "Event type", "width": "1.1fr"},
           {"label": "Source", "width": "1.2fr"}, {"label": "Destination", "width": "1.2fr"},
           {"label": "User", "width": ".9fr"}, {"label": "Status", "width": ".8fr"},
           {"label": "Incident", "width": "2.1fr"}]


def kpis(stats: Dict[str, Any]) -> str:
    return kpi_row([
        kpi("Events matched", stats.get("total"), "current filters", "blue"),
        kpi("Distinct sources", stats.get("distinct_sources"), "source IPs", "cyan"),
        kpi("Distinct destinations", stats.get("distinct_destinations"), "destination IPs", "cyan"),
        kpi("Failed logins", stats.get("failed_logins"), "login events marked failed",
            "critical" if stats.get("failed_logins") else "muted"),
        kpi("Event types", len(stats.get("by_type") or {}), "distinct categories", "blue"),
    ])


def chart_panels(stats: Dict[str, Any]) -> Dict[str, str]:
    day = [(d["date"][5:], d["count"]) for d in stats.get("by_day") or []]
    by_type = list((stats.get("by_type") or {}).items())
    sev = stats.get("by_incident_severity") or {}
    order = ["critical", "high", "medium", "low", "unscored"]
    segs = [(k.capitalize(), sev[k], charts.SEV_COLORS[k]) for k in order if sev.get(k)]
    return {
        "day": charts.bar_chart(day, uid="lxd", empty="No events in this range"),
        "type": charts.hbar_list(by_type, empty="No event types"),
        "sev": charts.donut(segs, center_value=f'{stats.get("total", 0):,}', center_label="events",
                            empty="No incident severities"),
    }


def event_rows(items: List[Dict[str, Any]]) -> str:
    rows = []
    for e in items:
        sev = e.get("incident_severity")
        incident = (f'{severity_badge(sev)} <span title="{esc(e.get("incident_title") or "")}">{esc(e.get("incident_title") or "Unlinked event")}</span>'
                    if e.get("incident_id") else '<span class="sx-muted">No incident</span>')
        status = e.get("status")
        status_html = (badge(status, "critical" if status.lower() == "failed" else ("ok" if status.lower() in ("success", "succeeded", "ok") else "muted"))
                       if status else '<span class="sx-muted">—</span>')
        detail = (kv_grid([("Event ID", e.get("id")), ("Incident ID", e.get("incident_id")),
                           ("Timestamp", fmt_ts(e.get("timestamp"))), ("Event hash", e.get("event_hash")),
                           ("Message", e.get("message")), ("User", e.get("user"))], columns=2)
                  + '<div class="sx-sub">Raw event payload</div>' + json_block(e.get("raw_data")))
        rows.append({
            "cells": [f'<span class="sx-mono">{esc(fmt_ts(e.get("timestamp")))}</span>', esc(e.get("event_type") or "unknown"),
                      f'<span class="sx-mono">{esc(e.get("source_ip") or "—")}</span>',
                      f'<span class="sx-mono">{esc(e.get("destination_ip") or "—")}</span>',
                      esc(e.get("user") or "—"), status_html, incident],
            "detail": detail, "tone": sev if sev in ("critical", "high") else ""})
    return expand_table(COLUMNS, rows, empty="No events match the current filters")
