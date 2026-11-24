"""Pure metric logic for the Command Center (no Streamlit imports => testable).

Every function returns ``None`` (or an explicit ``available: False`` payload)
when the underlying data cannot be retrieved. Nothing is estimated or invented.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------
# Threat Severity Index  (normalized score, NOT a measured percentage)
# --------------------------------------------------------------------------
SEVERITY_WEIGHTS = {"low": 25, "medium": 50, "high": 75, "critical": 100}
SEVERITY_BANDS = [  # (upper bound exclusive, label)
    (37.5, "Low"), (62.5, "Medium"), (87.5, "High"), (100.01, "Critical")]

SEVERITY_METHOD = (
    "Normalized severity index (0-100), not a probability or measured percentage. "
    "Mean of severity weights (low=25, medium=50, high=75, critical=100) over "
    "unresolved incidents that have a severity assigned. Resolved/closed "
    "incidents and incidents without a severity are excluded."
)


def severity_index(unresolved_by_severity: Optional[Dict[str, int]], unscored: int = 0) -> Dict[str, Any]:
    if unresolved_by_severity is None:
        return {"available": False, "reason": "Incident data unavailable", "method": SEVERITY_METHOD}
    counts = {k.lower(): int(v) for k, v in unresolved_by_severity.items() if k.lower() in SEVERITY_WEIGHTS}
    scored = sum(counts.values())
    if scored == 0:
        return {"available": False, "reason": "No unresolved incidents with a severity",
                "scored": 0, "unscored": unscored, "method": SEVERITY_METHOD}
    value = round(sum(SEVERITY_WEIGHTS[k] * n for k, n in counts.items()) / scored)
    label = next(lbl for bound, lbl in SEVERITY_BANDS if value < bound)
    return {"available": True, "value": value, "label": label, "scored": scored,
            "unscored": unscored, "method": SEVERITY_METHOD}


# --------------------------------------------------------------------------
# System Health score = weighted share of passing live checks
# --------------------------------------------------------------------------
CHECK_WEIGHTS = {"ok": 1.0, "degraded": 0.5, "fail": 0.0}

HEALTH_METHOD = (
    "Health score = (passing checks + 0.5 x degraded checks) / total checks. "
    "Checks come from the backend /api/v1/health endpoint plus two measured "
    "client-side checks (API reachability and response latency). State: Normal if "
    "every check passes; Warning if any check is degraded (e.g. agents in mock "
    "mode); Degraded if any check fails; Critical if the score is below 50, the "
    "database check fails, or the API is unreachable."
)


def client_checks(reachable: bool, latency_ms: Optional[float]) -> List[Dict[str, Any]]:
    checks = [{"id": "api_reachable", "label": "API reachable",
               "status": "ok" if reachable else "fail",
               "detail": "Backend responded" if reachable else "No response from backend"}]
    if reachable and latency_ms is not None:
        status = "ok" if latency_ms < 1500 else ("degraded" if latency_ms < 4000 else "fail")
        checks.append({"id": "api_latency", "label": "API latency", "status": status,
                       "detail": f"{latency_ms:.0f} ms round trip", "latency_ms": latency_ms})
    return checks


def health_score(server_checks: Optional[List[Dict[str, Any]]], reachable: bool,
                 latency_ms: Optional[float]) -> Dict[str, Any]:
    """``server_checks`` is None when /health could not be retrieved while the
    API itself answered (old backend, 404...). That yields 'unavailable'."""
    if not reachable:
        checks = client_checks(False, None)
        return {"available": True, "value": 0, "state": "Critical", "checks": checks,
                "method": HEALTH_METHOD, "note": "Backend unreachable"}
    if server_checks is None:
        return {"available": False, "reason": "Health endpoint unavailable on this backend",
                "checks": client_checks(True, latency_ms), "method": HEALTH_METHOD}
    checks = server_checks + client_checks(True, latency_ms)
    score = round(100 * sum(CHECK_WEIGHTS.get(c["status"], 0) for c in checks) / len(checks))
    statuses = {c["status"] for c in checks}
    db_failed = any(c["id"] == "database" and c["status"] == "fail" for c in checks)
    if score < 50 or db_failed:
        state = "Critical"
    elif "fail" in statuses:
        state = "Degraded"
    elif "degraded" in statuses:
        state = "Warning"
    else:
        state = "Normal"
    return {"available": True, "value": score, "state": state, "checks": checks, "method": HEALTH_METHOD}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def ratio(value: Optional[int], total: Optional[int]) -> float:
    if not value or not total:
        return 0.0
    return max(0.0, min(1.0, value / total))


def parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def fmt_clock(value: Optional[str]) -> Optional[str]:
    ts = parse_ts(value)
    return ts.strftime("%H:%M UTC") if ts else None


def fmt_datetime(value: Optional[str]) -> str:
    ts = parse_ts(value)
    return ts.strftime("%Y-%m-%d %H:%M") if ts else "unavailable"


def series_values(series: Optional[List[Dict[str, Any]]]) -> Optional[List[int]]:
    if series is None:
        return None
    return [int(p.get("count", 0)) if isinstance(p, dict) else int(p) for p in series]


def derive_from_incidents(incidents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Partial summary built only from the legacy GET /incidents payload, used
    when the backend does not provide /dashboard/summary (older deployment).
    Anything that cannot be derived from that payload is left as None."""
    resolved = {"resolved", "closed"}
    by_sev: Dict[str, int] = {}
    unresolved: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    for inc in incidents:
        st = str(inc.get("status") or "unknown").lower()
        sev = str(inc.get("severity") or "").lower()
        by_status[st] = by_status.get(st, 0) + 1
        if sev:
            by_sev[sev] = by_sev.get(sev, 0) + 1
            if st not in resolved:
                unresolved[sev] = unresolved.get(sev, 0) + 1
    unscored = sum(1 for i in incidents
                   if not i.get("severity") and str(i.get("status") or "").lower() not in resolved)
    top = [{"id": str(i["id"]), "title": i.get("title"), "status": str(i.get("status") or "").lower(),
            "severity": str(i.get("severity") or "").lower() or None, "created_at": i.get("created_at"),
            "event_types": [], "sources": [], "awaiting_approval": False} for i in incidents[:25]]
    return {
        "_fallback": True,
        "incidents": {"total": len(incidents), "by_status": by_status, "by_severity": by_sev,
                      "unresolved_by_severity": unresolved, "unscored_unresolved": unscored,
                      "active": sum(n for k, n in by_status.items() if k in ("open", "investigating")),
                      "containment_in_progress": None, "resolved_today": None,
                      "escalated": sum(1 for i in incidents
                                       if str(i.get("severity") or "").lower() == "critical"
                                       and str(i.get("status") or "").lower() not in resolved),
                      "series": None, "critical_series": None},
        "events": {"total": None, "series": None, "by_type": {}},
        "alerts": {"total_alerts": len(incidents), "critical_alerts": by_sev.get("critical", 0),
                   "intrusion_attempts": None, "malware_detections": None, "pending_approvals": None,
                   "series": {}},
        "network": {"nodes": [], "edges": [], "truncated": False},
        "top_threats": top, "timelines": [],
    }
