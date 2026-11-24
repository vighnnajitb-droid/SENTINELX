"""Read-only dashboard endpoints for the SENTINELX Command Center.

Added in addition to the existing API; no existing route or response field is
changed. The dashboard summary requires a valid bearer token and an active
account. The health endpoint is public so monitoring and startup checks can
verify backend availability without logging in.

    GET /api/v1/dashboard/summary   aggregated, real metrics for the UI
    GET /api/v1/health              live backend health checks

The router is created through ``build_dashboard_router`` so it can reuse the
application's ``get_current_user`` dependency without a circular import.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database.models import (AgentRun, Approval, AuditLog, Incident,
                             Investigation, SecurityEvent)
from database.session import get_db
from backend import dashboard_logic as logic

EVENT_SCAN_LIMIT = 20000      # most recent events inspected for aggregation
INCIDENT_LIMIT = 5000
TIMELINE_INCIDENTS = 25
TOP_THREATS = 25

_graph_check_cache: Dict[str, Any] = {"at": 0.0, "result": None}


def build_dashboard_router(get_current_user: Callable) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["dashboard"])

    def require_active_user(user=Depends(get_current_user)):
        # get_current_user validates the token; additionally refuse accounts
        # that were deactivated after the token was issued.
        if not getattr(user, "is_active", False):
            raise HTTPException(status_code=403, detail="Inactive user")
        return user

    # ------------------------------------------------------------------
    @router.get("/dashboard/summary")
    def dashboard_summary(
        days: int = Query(14, ge=1, le=90, description="Length of trend windows in days"),
        db: Session = Depends(get_db),
        _user=Depends(require_active_user),
    ) -> Dict[str, Any]:
        now = datetime.utcnow()
        today = now.date()
        start_of_day = datetime(now.year, now.month, now.day)

        # ---- incidents --------------------------------------------------
        incident_rows = (
            db.query(Incident.id, Incident.title, Incident.status, Incident.severity,
                     Incident.created_at, Incident.updated_at)
            .order_by(Incident.created_at.desc()).limit(INCIDENT_LIMIT).all()
        )
        incidents = [
            {"id": str(r.id), "title": r.title, "status": logic.norm(r.status) or "unknown",
             "severity": logic.norm(r.severity) or None,
             "created_at": r.created_at, "updated_at": r.updated_at}
            for r in incident_rows
        ]
        total_incidents = db.query(func.count(Incident.id)).scalar() or 0

        unresolved = [i for i in incidents if i["status"] not in logic.RESOLVED_STATUSES]
        by_status: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        unresolved_by_severity: Dict[str, int] = {}
        for i in incidents:
            by_status[i["status"]] = by_status.get(i["status"], 0) + 1
            if i["severity"]:
                by_severity[i["severity"]] = by_severity.get(i["severity"], 0) + 1
        for i in unresolved:
            if i["severity"]:
                unresolved_by_severity[i["severity"]] = unresolved_by_severity.get(i["severity"], 0) + 1

        # ---- approvals & investigations ---------------------------------
        approval_rows = db.query(Approval.id, Approval.investigation_id, Approval.status,
                                 Approval.created_at, Approval.resolved_at).all()
        inv_rows = db.query(Investigation.id, Investigation.incident_id, Investigation.status,
                            Investigation.created_at).all()
        inv_to_incident = {str(r.id): str(r.incident_id) for r in inv_rows}

        approvals_by_incident: Dict[str, List[Dict[str, Any]]] = {}
        for a in approval_rows:
            incident_id = inv_to_incident.get(str(a.investigation_id))
            if incident_id:
                approvals_by_incident.setdefault(incident_id, []).append(
                    {"status": logic.norm(a.status), "resolved_at": a.resolved_at})
        investigations_by_incident: Dict[str, List[Dict[str, Any]]] = {}
        investigations_by_status: Dict[str, int] = {}
        for r in inv_rows:
            investigations_by_incident.setdefault(str(r.incident_id), []).append(
                {"status": logic.norm(r.status), "created_at": r.created_at})
            key = logic.norm(r.status) or "unknown"
            investigations_by_status[key] = investigations_by_status.get(key, 0) + 1

        pending_approvals = sum(1 for a in approval_rows if logic.norm(a.status) == "pending")

        unresolved_ids = {i["id"] for i in unresolved}
        containment_in_progress = sum(
            1 for incident_id, items in approvals_by_incident.items()
            if incident_id in unresolved_ids and any(x["status"] == "approved" for x in items))
        resolved_today = sum(
            1 for i in incidents
            if i["status"] in logic.RESOLVED_STATUSES and i["updated_at"] and i["updated_at"] >= start_of_day)
        escalated = sum(1 for i in unresolved if i["severity"] == "critical")

        # ---- events (most recent EVENT_SCAN_LIMIT) -----------------------
        total_events = db.query(func.count(SecurityEvent.id)).scalar() or 0
        event_rows = (
            db.query(SecurityEvent.incident_id, SecurityEvent.source_ip,
                     SecurityEvent.destination_ip, SecurityEvent.event_type,
                     SecurityEvent.created_at,
                     SecurityEvent.raw_data["status"].astext.label("status"))
            .order_by(SecurityEvent.created_at.desc()).limit(EVENT_SCAN_LIMIT).all()
        )
        events = [
            {"incident_id": str(r.incident_id) if r.incident_id else None,
             "source_ip": r.source_ip, "destination_ip": r.destination_ip,
             "event_type": r.event_type, "created_at": r.created_at, "status": r.status}
            for r in event_rows
        ]
        by_type: Dict[str, int] = {}
        for e in events:
            key = logic.norm(e["event_type"]) or "unknown"
            by_type[key] = by_type.get(key, 0) + 1

        intrusion_events = [e for e in events if logic.is_intrusion_event(e["event_type"], e["status"])]
        malware_events = [e for e in events if logic.is_malware_event(e["event_type"])]

        # ---- threat intel indicators (as reported by the agent) ----------
        ti_outputs = [r.output_data for r in
                      db.query(AgentRun.output_data)
                      .filter(AgentRun.agent_name == "ThreatIntelAgent")
                      .order_by(AgentRun.started_at.desc()).limit(500).all()]
        flagged = logic.extract_flagged_indicators(ti_outputs)

        # ---- assemble ----------------------------------------------------
        profile = logic.incident_event_profile(events)
        pending_incident_ids = {
            inv_to_incident.get(str(a.investigation_id)) for a in approval_rows
            if logic.norm(a.status) == "pending"}
        top_threats = []
        for i in sorted(incidents, key=logic.threat_sort_key)[:TOP_THREATS]:
            p = profile.get(i["id"], {})
            top_threats.append({
                "id": i["id"], "title": i["title"], "status": i["status"], "severity": i["severity"],
                "created_at": logic.iso(i["created_at"]),
                "event_types": p.get("event_types", []), "sources": p.get("sources", []),
                "awaiting_approval": i["id"] in pending_incident_ids,
            })

        timelines = [
            logic.build_timeline(
                {**i, "created_at": i["created_at"], "updated_at": i["updated_at"]},
                investigations_by_incident.get(i["id"], []),
                approvals_by_incident.get(i["id"], []))
            for i in incidents[:TIMELINE_INCIDENTS]
        ]

        return {
            "generated_at": now.isoformat() + "Z",
            "window_days": days,
            "incidents": {
                "total": total_incidents, "returned": len(incidents),
                "by_status": by_status, "by_severity": by_severity,
                "unresolved_by_severity": unresolved_by_severity,
                "unscored_unresolved": sum(1 for i in unresolved if not i["severity"]),
                "active": sum(1 for i in incidents if i["status"] in logic.ACTIVE_STATUSES),
                "containment_in_progress": containment_in_progress,
                "resolved_today": resolved_today,
                "escalated": escalated,
                "series": logic.daily_series((i["created_at"] for i in incidents), days, today),
                "critical_series": logic.daily_series(
                    (i["created_at"] for i in incidents if i["severity"] == "critical"), days, today),
            },
            "events": {
                "total": total_events, "scanned": len(events),
                "truncated": total_events > len(events),
                "by_type": by_type,
                "series": logic.daily_series((e["created_at"] for e in events), days, today),
            },
            "alerts": {
                # Units differ per metric on purpose; the UI labels each one.
                "total_alerts": total_incidents,
                "critical_alerts": by_severity.get("critical", 0),
                "intrusion_attempts": len(intrusion_events),
                "malware_detections": len(malware_events) if malware_events else None,
                "pending_approvals": pending_approvals,
                "series": {
                    "total_alerts": logic.daily_series((i["created_at"] for i in incidents), days, today),
                    "critical_alerts": logic.daily_series(
                        (i["created_at"] for i in incidents if i["severity"] == "critical"), days, today),
                    "intrusion_attempts": logic.daily_series(
                        (e["created_at"] for e in intrusion_events), days, today),
                    "malware_detections": logic.daily_series(
                        (e["created_at"] for e in malware_events), days, today) if malware_events else None,
                    "pending_approvals": logic.daily_series(
                        (a.created_at for a in approval_rows if logic.norm(a.status) == "pending"), days, today),
                },
            },
            "investigations": {"by_status": investigations_by_status},
            "network": {**logic.build_network(events, flagged),
                        "threat_intel_mode_note":
                        "Reputation labels come from the ThreatIntelAgent; values prefixed "
                        "'simulated' are demo indicators, not verified threat feeds."},
            "top_threats": top_threats,
            "timelines": timelines,
        }

    # ------------------------------------------------------------------
    @router.get("/health")
    def health(db: Session = Depends(get_db)) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []

        # Database round trip
        started = time.perf_counter()
        try:
            db.execute(text("SELECT 1"))
            checks.append({"id": "database", "label": "Database", "status": "ok",
                           "detail": "Query round trip succeeded",
                           "latency_ms": round((time.perf_counter() - started) * 1000, 1)})
        except Exception:
            checks.append({"id": "database", "label": "Database", "status": "fail",
                           "detail": "Database query failed"})

        # Agent graph compiles (cached 60 s; compiling is not free)
        now = time.time()
        if _graph_check_cache["result"] is None or now - _graph_check_cache["at"] > 60:
            try:
                from agents.graph import create_investigation_graph
                create_investigation_graph()
                result = {"id": "agent_graph", "label": "Agent pipeline", "status": "ok",
                          "detail": "LangGraph pipeline compiled"}
            except Exception:
                result = {"id": "agent_graph", "label": "Agent pipeline", "status": "fail",
                          "detail": "LangGraph pipeline failed to compile"}
            _graph_check_cache.update(at=now, result=result)
        checks.append(_graph_check_cache["result"])

        # LLM mode, mirrors the mock-detection logic used inside the agents
        key = (os.getenv("OPENAI_API_KEY", "dummy") or "").strip()
        mock = (not key) or key == "dummy" or key.startswith("your_")
        checks.append({
            "id": "agent_mode", "label": "Agent LLM mode",
            "status": "degraded" if mock else "ok",
            "detail": ("Agents run in deterministic mock mode (no LLM key configured)"
                       if mock else "LLM key configured")})

        # Audit log hash-link consistency
        try:
            rows = db.query(AuditLog.previous_hash, AuditLog.current_hash).all()
            result = logic.audit_link_consistency(
                [{"previous_hash": r.previous_hash, "current_hash": r.current_hash} for r in rows])
            broken = result["broken_links"]
            checks.append({
                "id": "audit_chain", "label": "Audit trail links",
                "status": "ok" if broken == 0 else "fail",
                "detail": (f"{result['checked']} entries, all hash links resolve"
                           if broken == 0 else f"{broken} of {result['checked']} entries reference a missing predecessor")})
        except Exception:
            checks.append({"id": "audit_chain", "label": "Audit trail links", "status": "fail",
                           "detail": "Audit log could not be read"})

        statuses = {c["status"] for c in checks}
        overall = "fail" if "fail" in statuses else ("degraded" if "degraded" in statuses else "ok")
        return {"checked_at": datetime.utcnow().isoformat() + "Z", "overall": overall, "checks": checks}

    return router
