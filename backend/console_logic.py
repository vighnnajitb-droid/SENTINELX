"""Pure helpers for the SENTINELX console endpoints (events, audit, agents, system).

No database or framework imports, so everything is unit-testable. Nothing here
fabricates data: when a value cannot be derived the helpers return ``None``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

CANONICAL_AGENTS = [
    "DetectionAgent", "InvestigationAgent", "ThreatIntelAgent",
    "RiskAssessmentAgent", "AuditAgent", "ResponseAgent",
]

USER_KEYS = ("user", "username", "user_name", "account", "user.name")
STATUS_KEYS = ("status", "result", "outcome")
MESSAGE_KEYS = ("message", "description", "details", "info")


def like_pattern(text: str) -> str:
    """Escape LIKE wildcards in user input (use with escape='\\\\')."""
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def duration_seconds(start: Optional[datetime], end: Optional[datetime]) -> Optional[float]:
    if isinstance(start, datetime) and isinstance(end, datetime):
        return max(0.0, (end - start).total_seconds())
    return None


def first_present(data: Any, keys: Iterable[str]) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def event_view(raw_data: Any) -> Dict[str, Optional[str]]:
    """Pull optional user/status/message out of an event's raw payload."""
    return {
        "user": first_present(raw_data, USER_KEYS),
        "status": first_present(raw_data, STATUS_KEYS),
        "message": first_present(raw_data, MESSAGE_KEYS),
    }


# ----------------------------------------------------------------- audit chain
def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def is_known_record_type(entry: Dict[str, Any]) -> bool:
    """Record types whose hash format this module can reproduce."""
    action = entry.get("action") or ""
    entity_type = entry.get("entity_type")
    return ((entity_type == "Investigation" and action == "started")
            or (entity_type == "Approval" and action in ("approve", "reject"))
            or (action.startswith("Agent ") and action.endswith(" execution")))


def recompute_hash(entry: Dict[str, Any], previous_hash: Optional[str]) -> Optional[str]:
    """Recompute an audit hash using the exact formats written by the backend.

    Returns None when the hash cannot be recomputed. For a *known* record type
    that means required inputs are missing (see ``is_known_record_type``), which
    the verifier treats as a failure rather than as an unknown format."""
    prev = previous_hash or ""
    action = entry.get("action") or ""
    entity_type = entry.get("entity_type")
    details = entry.get("details")
    entity_id = entry.get("entity_id")
    user = details.get("user") if isinstance(details, dict) else None

    if entity_type == "Investigation" and action == "started" and user and entity_id:
        return _digest(f"{prev}{entity_id}_started_{user}")
    if entity_type == "Approval" and action in ("approve", "reject") and user and entity_id:
        return _digest(f"{prev}{entity_id}_{action}_{user}")
    if action.startswith("Agent ") and action.endswith(" execution") and details is not None:
        return _digest(f"{prev}{json.dumps(details, sort_keys=True)}")
    return None


def verify_audit_chain(entries_oldest_first: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """Verify each entry. Statuses:

    verified      link to previous entry is intact AND the hash was recomputed and matches
    linked        link is intact but the hash format is not reproducible (not recomputed)
    broken_link   previous_hash does not equal the preceding entry's hash
    hash_mismatch link intact but the recomputed hash differs from the stored one
    """
    results: Dict[str, Dict[str, str]] = {}
    expected_prev: Optional[str] = None
    for entry in entries_oldest_first:
        entry_id = str(entry.get("id"))
        stored_prev = entry.get("previous_hash") or None
        if stored_prev != expected_prev:
            results[entry_id] = {"status": "broken_link",
                                 "reason": "previous_hash does not match the preceding record's hash"}
        else:
            recomputed = recompute_hash(entry, stored_prev)
            if recomputed is None and is_known_record_type(entry):
                results[entry_id] = {"status": "hash_mismatch",
                                     "reason": "Record is missing the fields required to reproduce its stored hash"}
            elif recomputed is None:
                results[entry_id] = {"status": "linked",
                                     "reason": "Chain link intact; this record type's hash cannot be recomputed"}
            elif recomputed == entry.get("current_hash"):
                results[entry_id] = {"status": "verified",
                                     "reason": "Chain link intact and hash recomputed successfully"}
            else:
                results[entry_id] = {"status": "hash_mismatch",
                                     "reason": "Recomputed hash differs from the stored hash"}
        expected_prev = entry.get("current_hash")
    return results


def summarize_verification(results: Dict[str, Dict[str, str]]) -> Dict[str, int]:
    summary = {"checked": len(results), "verified": 0, "linked": 0, "broken_link": 0, "hash_mismatch": 0}
    for item in results.values():
        summary[item["status"]] += 1
    return summary


def actor_of(entry: Dict[str, Any]) -> Optional[str]:
    details = entry.get("details")
    if isinstance(details, dict) and isinstance(details.get("user"), str):
        return details["user"]
    if str(entry.get("action", "")).startswith("Agent "):
        return "system (agent pipeline)"
    return None


def related_incident_id(entry: Dict[str, Any], incident_ids: set,
                        investigation_to_incident: Dict[str, str],
                        approval_to_investigation: Dict[str, str]) -> Optional[str]:
    details = entry.get("details")
    entity_id = str(entry.get("entity_id")) if entry.get("entity_id") else None
    if isinstance(details, dict) and details.get("incident_id") and str(details["incident_id"]) in incident_ids:
        return str(details["incident_id"])
    if entity_id in incident_ids:
        return entity_id
    if entity_id in investigation_to_incident:
        return investigation_to_incident[entity_id]
    if entity_id in approval_to_investigation:
        return investigation_to_incident.get(approval_to_investigation[entity_id])
    if isinstance(details, dict) and details.get("investigation_id"):
        return investigation_to_incident.get(str(details["investigation_id"]))
    return None


# ---------------------------------------------------------------------- agents
def agent_stats(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per-agent statistics for the six canonical agents (zeros when never run)."""
    stats = {name: {"name": name, "total_runs": 0, "completed": 0, "failed": 0, "last_run_at": None,
                    "last_status": None, "_durations": []} for name in CANONICAL_AGENTS}
    for run in sorted(runs, key=lambda r: r.get("started_at") or datetime.min):
        entry = stats.get(run.get("agent_name"))
        if entry is None:
            continue
        entry["total_runs"] += 1
        status = (run.get("status") or "").lower()
        if status == "completed":
            entry["completed"] += 1
        elif status in ("failed", "error"):
            entry["failed"] += 1
        duration = duration_seconds(run.get("started_at"), run.get("completed_at"))
        if duration is not None:
            entry["_durations"].append(duration)
        entry["last_run_at"] = run.get("started_at")
        entry["last_status"] = status or None
    out = []
    for entry in stats.values():
        durations = entry.pop("_durations")
        entry["avg_duration_s"] = round(sum(durations) / len(durations), 2) if durations else None
        out.append(entry)
    return out


# ------------------------------------------------------------------------ risk
def risk_from_agent_runs(agents: Dict[str, Any]) -> Dict[str, Any]:
    """Extract what the RiskAssessmentAgent actually reported (never inferred)."""
    risk = agents.get("RiskAssessmentAgent") if isinstance(agents, dict) else None
    if not isinstance(risk, dict):
        return {"available": False}
    confidence = risk.get("confidence_score")
    return {
        "available": True,
        "severity": str(risk.get("severity")).lower() if risk.get("severity") else None,
        "confidence": float(confidence) if isinstance(confidence, (int, float)) else None,
        "justification": risk.get("justification"),
    }


# ------------------------------------------------------------- risk overview
def evidence_from_outputs(outputs: Dict[str, Any]) -> Dict[str, Any]:
    """Supporting evidence exactly as the other agents reported it."""
    def get(name):
        value = outputs.get(name) if isinstance(outputs, dict) else None
        return value if isinstance(value, dict) else {}

    detection, investigation, intel, audit = (get("DetectionAgent"), get("InvestigationAgent"),
                                              get("ThreatIntelAgent"), get("AuditAgent"))
    findings = detection.get("findings")
    flagged = [str(i.get("indicator")) for i in (intel.get("enriched_indicators") or [])
               if isinstance(i, dict) and i.get("indicator") and "malicious" in str(i.get("reputation", "")).lower()]
    entities = investigation.get("entities_involved")
    return {
        "is_suspicious": detection.get("is_suspicious") if isinstance(detection.get("is_suspicious"), bool) else None,
        "findings": [str(f) for f in findings][:5] if isinstance(findings, list) else [],
        "known_threats_found": intel.get("known_threats_found") if isinstance(intel.get("known_threats_found"), bool) else None,
        "flagged_indicators": flagged[:8],
        "entities": [str(e) for e in entities][:8] if isinstance(entities, list) else [],
        "evidence_verified": audit.get("evidence_verified") if isinstance(audit.get("evidence_verified"), bool) else None,
        "audit_trail_valid": audit.get("audit_trail_valid") if isinstance(audit.get("audit_trail_valid"), bool) else None,
    }


CONFIDENCE_BUCKETS = [("< 50%", 0.0, 0.5), ("50-70%", 0.5, 0.7), ("70-90%", 0.7, 0.9), ("90-100%", 0.9, 1.0001)]


def confidence_buckets(values: Iterable[Optional[float]]) -> List[Dict[str, Any]]:
    counts = [0] * len(CONFIDENCE_BUCKETS)
    for v in values:
        if isinstance(v, (int, float)):
            for i, (_, lo, hi) in enumerate(CONFIDENCE_BUCKETS):
                if lo <= v < hi:
                    counts[i] += 1
                    break
    return [{"label": b[0], "count": c} for b, c in zip(CONFIDENCE_BUCKETS, counts)]


def risk_trend(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per-day counts of risk assessments (by severity) and mean confidence.
    ``rows`` need created_at (datetime), severity, confidence."""
    days: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        created = row.get("created_at")
        if not isinstance(created, datetime):
            continue
        key = created.date().isoformat()
        day = days.setdefault(key, {"date": key, "count": 0, "by_severity": {}, "_conf": []})
        day["count"] += 1
        sev = row.get("severity") or "unscored"
        day["by_severity"][sev] = day["by_severity"].get(sev, 0) + 1
        if isinstance(row.get("confidence"), (int, float)):
            day["_conf"].append(row["confidence"])
    out = []
    for key in sorted(days):
        day = days[key]
        conf = day.pop("_conf")
        day["avg_confidence"] = round(sum(conf) / len(conf), 3) if conf else None
        out.append(day)
    return out
