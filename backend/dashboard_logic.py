"""Pure aggregation helpers for the SENTINELX dashboard endpoints.

Nothing in this module touches the database or FastAPI, so every function can
be unit-tested with plain dictionaries. All functions operate on data that was
really stored by the platform; nothing here invents values. When a quantity
cannot be derived, the helpers return ``None`` so callers can surface an
explicit "unavailable" state.
"""

from __future__ import annotations

import ipaddress
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

RESOLVED_STATUSES = {"resolved", "closed"}
ACTIVE_STATUSES = {"open", "investigating"}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Event types the detection agent already treats as hostile reconnaissance.
INTRUSION_EVENT_TYPES = {"port_scan"}
# The ingestion pipeline has no malware classifier. Only events whose
# event_type explicitly names malware are counted, otherwise the metric is
# reported as unavailable (None).
MALWARE_EVENT_TYPES = {"malware", "malware_detection", "ransomware", "virus", "trojan"}


def norm(value: Any) -> str:
    return str(value or "").strip().lower()


def is_failed_login(event_type: Any, status: Any) -> bool:
    return norm(event_type) == "login" and norm(status) == "failed"


def is_intrusion_event(event_type: Any, status: Any) -> bool:
    return norm(event_type) in INTRUSION_EVENT_TYPES or is_failed_login(event_type, status)


def is_malware_event(event_type: Any) -> bool:
    return norm(event_type) in MALWARE_EVENT_TYPES


def ip_scope(value: Optional[str]) -> str:
    """Return 'internal' for private/loopback ranges, 'external' for public
    addresses and 'unknown' when the value is not a valid IP."""
    if not value:
        return "unknown"
    try:
        address = ipaddress.ip_address(str(value).strip())
    except ValueError:
        return "unknown"
    if address.is_private or address.is_loopback or address.is_link_local:
        return "internal"
    return "external"


def iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if isinstance(value, datetime) else None


def daily_series(timestamps: Iterable[Optional[datetime]], days: int, today: date) -> List[Dict[str, Any]]:
    """Count timestamps per UTC calendar day for the last ``days`` days
    (oldest first, zero-filled so charts have a stable x axis)."""
    days = max(1, int(days))
    counts: Counter = Counter()
    for stamp in timestamps:
        if isinstance(stamp, datetime):
            counts[stamp.date()] += 1
    first = today - timedelta(days=days - 1)
    return [
        {"date": (first + timedelta(days=offset)).isoformat(),
         "count": counts.get(first + timedelta(days=offset), 0)}
        for offset in range(days)
    ]


def build_network(events: List[Dict[str, Any]], flagged: Dict[str, str], edge_limit: int = 150) -> Dict[str, Any]:
    """Aggregate observed source->destination pairs into a node/edge graph.

    ``events`` need ``source_ip``, ``destination_ip``, ``event_type`` and
    ``status``. ``flagged`` maps an IP to the reputation string reported by
    the threat-intel agent (simulated in mock mode).
    """
    edges: Dict[tuple, Dict[str, Any]] = {}
    for event in events:
        src, dst = (event.get("source_ip") or "").strip(), (event.get("destination_ip") or "").strip()
        if not src or not dst:
            continue
        edge = edges.setdefault((src, dst), {"source": src, "target": dst, "events": 0, "intrusion_events": 0, "types": Counter()})
        edge["events"] += 1
        edge["types"][norm(event.get("event_type")) or "unknown"] += 1
        if is_intrusion_event(event.get("event_type"), event.get("status")):
            edge["intrusion_events"] += 1

    ordered = sorted(edges.values(), key=lambda e: (-e["intrusion_events"], -e["events"]))
    truncated = len(ordered) > edge_limit
    ordered = ordered[:edge_limit]

    node_ids = {e["source"] for e in ordered} | {e["target"] for e in ordered}
    nodes = [
        {"id": ip, "scope": ip_scope(ip), "flagged": ip in flagged, "reputation": flagged.get(ip)}
        for ip in sorted(node_ids)
    ]
    return {
        "nodes": nodes,
        "edges": [
            {**{k: v for k, v in e.items() if k != "types"},
             "types": dict(e["types"].most_common(5))}
            for e in ordered
        ],
        "truncated": truncated,
    }


def build_timeline(incident: Dict[str, Any], investigations: List[Dict[str, Any]],
                   approvals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Derive the four response stages for one incident from stored records.

    Stage state is one of: done, active, failed, pending, unavailable.
    A timestamp is only reported when a real record supports it.
    """
    status = norm(incident.get("status"))
    resolved = status in RESOLVED_STATUSES

    started = min((i["created_at"] for i in investigations if i.get("created_at")), default=None)
    inv_failed = any(norm(i.get("status")) == "failed" for i in investigations)

    resolved_approvals = [a for a in approvals if a.get("resolved_at")]
    last_resolution = max(resolved_approvals, key=lambda a: a["resolved_at"], default=None)
    rejected = bool(last_resolution) and norm(last_resolution.get("status")) == "rejected"
    contained_at = last_resolution["resolved_at"] if last_resolution and not rejected else None

    detection = {"key": "detection", "label": "Detection", "ts": iso(incident.get("created_at")),
                 "state": "done" if incident.get("created_at") else "unavailable"}
    analysis = {"key": "analysis", "label": "Analysis", "ts": iso(started),
                "state": "failed" if inv_failed else ("done" if started else "pending")}
    containment = {"key": "containment", "label": "Containment", "ts": iso(contained_at),
                   "state": "failed" if rejected else ("done" if contained_at else "pending")}
    resolution = {"key": "resolution", "label": "Resolution",
                  "ts": iso(incident.get("updated_at")) if resolved else None,
                  "state": "done" if resolved else "pending"}

    stages = [detection, analysis, containment, resolution]
    # The first stage that is still pending becomes the active one.
    if not resolved and not inv_failed:
        for stage in stages:
            if stage["state"] == "pending":
                stage["state"] = "active"
                break
    return {
        "incident_id": incident.get("id"),
        "title": incident.get("title"),
        "status": status or None,
        "severity": norm(incident.get("severity")) or None,
        "stages": stages,
    }


def extract_flagged_indicators(agent_outputs: Iterable[Optional[Dict[str, Any]]]) -> Dict[str, str]:
    """Collect IPs the threat-intel agent labelled malicious. Reputation is
    kept verbatim so the UI can show whether it is simulated."""
    flagged: Dict[str, str] = {}
    for output in agent_outputs:
        if not isinstance(output, dict):
            continue
        for item in output.get("enriched_indicators") or []:
            if not isinstance(item, dict):
                continue
            reputation = norm(item.get("reputation"))
            indicator = item.get("indicator")
            if indicator and "malicious" in reputation:
                flagged[str(indicator)] = reputation
    return flagged


def incident_event_profile(events: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Per-incident event types and source IPs, most frequent first."""
    types: Dict[str, Counter] = defaultdict(Counter)
    sources: Dict[str, Counter] = defaultdict(Counter)
    for event in events:
        incident_id = event.get("incident_id")
        if not incident_id:
            continue
        if event.get("event_type"):
            types[incident_id][norm(event["event_type"])] += 1
        if event.get("source_ip"):
            sources[incident_id][event["source_ip"]] += 1
    return {
        incident_id: {
            "event_types": [t for t, _ in types[incident_id].most_common(3)],
            "sources": [s for s, _ in sources[incident_id].most_common(3)],
        }
        for incident_id in set(types) | set(sources)
    }


def threat_sort_key(incident: Dict[str, Any]):
    unresolved = 0 if norm(incident.get("status")) not in RESOLVED_STATUSES else 1
    severity = SEVERITY_ORDER.get(norm(incident.get("severity")), 4)
    created = incident.get("created_at")
    return (unresolved, severity, -(created.timestamp() if isinstance(created, datetime) else 0))


def audit_link_consistency(entries: List[Dict[str, Any]]) -> Dict[str, int]:
    """Check that every audit entry's previous_hash points at an entry that
    exists. This is a link-consistency check, not a full cryptographic
    re-verification of every payload."""
    known = {e.get("current_hash") for e in entries if e.get("current_hash")}
    broken = sum(1 for e in entries if e.get("previous_hash") and e["previous_hash"] not in known)
    return {"checked": len(entries), "broken_links": broken}
