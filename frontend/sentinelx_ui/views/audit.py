"""Audit Trail view builders (pure HTML). Verification status always comes from the backend."""
from __future__ import annotations

from typing import Any, Dict, List

from ..components import esc
from ..widgets import (badge, bullet_list, expand_table, fmt_ts, json_block, kpi, kpi_row, kv_grid, kv_grid_html, notice,
                       status_badge)

LIMITS = ("Verification checks the internal consistency of the stored hash chain (each record links to the one before it, and "
          "hashes are recomputed where the format is reproducible). It does not use digital signatures or an external anchor, "
          "so it cannot detect an attacker who rewrites the entire chain consistently.")


def kpis(v: Dict[str, Any]) -> str:
    bad = v.get("broken_link", 0) + v.get("hash_mismatch", 0)
    return kpi_row([
        kpi("Audit records", v.get("checked"), "in the hash chain", "blue"),
        kpi("Verified", v.get("verified"), "link + recomputed hash match", "ok"),
        kpi("Linked only", v.get("linked"), "format not recomputable", "cyan"),
        kpi("Failed verification", bad, "broken link or hash mismatch", "critical" if bad else "muted"),
    ])


def chain_banner(v: Dict[str, Any]) -> str:
    bad = v.get("broken_link", 0) + v.get("hash_mismatch", 0)
    if not v.get("checked"):
        return notice("No audit records exist yet.", "info")
    if bad:
        return notice(f'{bad} of {v["checked"]} records failed backend verification '
                      f'({v.get("broken_link", 0)} broken link(s), {v.get("hash_mismatch", 0)} hash mismatch(es)). '
                      "Treat the affected evidence as unverified.", "critical")
    suffix = " Some records could only be link-checked." if v.get("linked") else ""
    trunc = " Only the first records were checked (limit reached)." if v.get("truncated") else ""
    return notice(f'All {v["checked"]} records passed backend verification: every hash link is intact and '
                  f'{v.get("verified", 0)} hashes were recomputed successfully.{suffix}{trunc}', "ok")


def audit_table(items: List[Dict[str, Any]]) -> str:
    cols = [{"label": "Timestamp", "width": "1.5fr"}, {"label": "Actor", "width": "1.2fr"}, {"label": "Action", "width": "2fr"},
            {"label": "Entity", "width": "1fr"}, {"label": "Related incident", "width": "2fr"}, {"label": "Verification", "width": "1.2fr"}]
    rows = []
    for a in items:
        ver = a.get("verification") or {}
        detail = (kv_grid_html([("Verification", status_badge(ver.get("status"))), ("Reason", esc(ver.get("reason") or ""))], 1)
                  + kv_grid([("Record ID", a.get("id")), ("Entity ID", a.get("entity_id")), ("Incident ID", a.get("incident_id")),
                             ("Actor", a.get("actor"))], 2)
                  + '<div class="sx-sub">Hashes (SHA-256)</div>'
                  + f'<div class="sx-mono" style="word-break:break-all;color:var(--sx-text2)">current: {esc(a.get("current_hash"))}<br>previous: {esc(a.get("previous_hash") or "none (first record)")}</div>'
                  + '<div class="sx-sub">Recorded details</div>' + json_block(a.get("details")))
        rows.append({"cells": [f'<span class="sx-mono">{esc(fmt_ts(a.get("timestamp")))}</span>', esc(a.get("actor") or "—"), esc(a.get("action")),
                               esc(a.get("entity_type") or "—"), esc(a.get("incident_title") or "—"), status_badge(ver.get("status"))],
                     "detail": detail, "tone": "critical" if ver.get("status") in ("broken_link", "hash_mismatch") else ""})
    return expand_table(cols, rows, empty="No audit records match the current filters")


def integrity_panel(inv: Dict[str, Any], audit: Dict[str, Any]) -> str:
    """Side-by-side: what the backend verified vs what the AuditAgent claimed for one incident."""
    v = audit.get("verification", {})
    items = audit.get("items", [])
    counts: Dict[str, int] = {}
    for i in items:
        counts[i["verification"]["status"]] = counts.get(i["verification"]["status"], 0) + 1
    backend = kv_grid_html([("Records for this incident", esc(audit.get("total", 0))),
                            ("Verified", badge(str(counts.get("verified", 0)), "ok")), ("Linked only", badge(str(counts.get("linked", 0)), "info")),
                            ("Failed", badge(str(counts.get("broken_link", 0) + counts.get("hash_mismatch", 0)),
                                             "critical" if counts.get("broken_link", 0) + counts.get("hash_mismatch", 0) else "muted"))], 2)
    run = None
    for r in (inv.get("agent_runs") or []):
        if r["agent_name"] == "AuditAgent" and isinstance(r.get("output_data"), dict):
            run = r["output_data"]
    if run:
        agent = (kv_grid_html([("Evidence verified (claimed)", badge("Yes", "ok") if run.get("evidence_verified") else badge("No", "medium")),
                               ("Audit trail valid (claimed)", badge("Yes", "ok") if run.get("audit_trail_valid") else badge("No", "medium"))], 2)
                 + '<div class="sx-sub">Discrepancies reported</div>' + bullet_list(run.get("discrepancies") or [], "None reported"))
    else:
        agent = notice("The Audit Agent has not reported for this incident yet.", "info")
    return (f'<div class="sx-sub">Backend verification (recomputed hashes)</div>{backend}'
            f'<div class="sx-sub">Audit Agent report (agent-reported, not backend verification)</div>{agent}')
