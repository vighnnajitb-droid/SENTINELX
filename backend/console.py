"""Read-only console endpoints used by the SENTINELX Streamlit pages.

Added alongside the existing API (nothing existing is changed). Every endpoint
requires a valid bearer token and an active account.

    GET /api/v1/events                           searchable security events + facets/stats
    GET /api/v1/incidents/{id}/investigations    investigations with agent runs and approvals
    GET /api/v1/agents/overview                  per-agent statistics and recent runs
    GET /api/v1/audit                            audit records with hash-chain verification
    GET /api/v1/system/info                      non-secret platform configuration/status
"""

from __future__ import annotations

import os
import platform
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Text, cast, func, or_, text
from sqlalchemy.orm import Session

from database.models import (AgentRun, Approval, AuditLog, Incident,
                             Investigation, SecurityEvent)
from database.session import get_db
from backend import console_logic as logic

ESC = "\\"
AUDIT_FETCH_LIMIT = 50000
RUN_SCAN_LIMIT = 2000
RUN_OUTPUT_LIMIT = 30


def _uuid(value: str, name: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {name}")


def _csv(value: Optional[str]) -> List[str]:
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def _iso(value: Any) -> Optional[str]:
    return value.isoformat() if isinstance(value, (datetime,)) or hasattr(value, "isoformat") else None


def build_console_router(get_current_user: Callable, config: Dict[str, Any]) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["console"])

    def require_active_user(user=Depends(get_current_user)):
        if not getattr(user, "is_active", False):
            raise HTTPException(status_code=403, detail="Inactive user")
        return user

    # ------------------------------------------------------------------ events
    @router.get("/events")
    def list_events(
        q: Optional[str] = Query(None, max_length=200, description="Free-text search"),
        event_type: Optional[str] = Query(None, description="Comma-separated event types"),
        severity: Optional[str] = Query(None, description="Comma-separated incident severities (or 'unscored')"),
        incident_id: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        order: str = Query("desc", pattern="^(asc|desc)$"),
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=200),
        db: Session = Depends(get_db),
        _user=Depends(require_active_user),
    ) -> Dict[str, Any]:
        ts = func.coalesce(SecurityEvent.timestamp, SecurityEvent.created_at)
        incident_uuid = _uuid(incident_id, "incident_id") if incident_id else None
        types = _csv(event_type)
        severities = [s.lower() for s in _csv(severity)]

        def apply(query):
            if incident_uuid:
                query = query.filter(SecurityEvent.incident_id == incident_uuid)
            if q:
                pattern = logic.like_pattern(q)
                query = query.filter(or_(
                    SecurityEvent.source_ip.ilike(pattern, escape=ESC),
                    SecurityEvent.destination_ip.ilike(pattern, escape=ESC),
                    SecurityEvent.event_type.ilike(pattern, escape=ESC),
                    cast(SecurityEvent.raw_data, Text).ilike(pattern, escape=ESC)))
            if types:
                query = query.filter(SecurityEvent.event_type.in_(types))
            if severities:
                conds = []
                real = [s for s in severities if s != "unscored"]
                if real:
                    conds.append(func.lower(Incident.severity).in_(real))
                if "unscored" in severities:
                    conds.append(Incident.severity.is_(None))
                query = query.filter(or_(*conds))
            if start:
                query = query.filter(ts >= start)
            if end:
                query = query.filter(ts <= end)
            return query

        def joined(*columns):
            return apply(db.query(*columns).select_from(SecurityEvent)
                         .outerjoin(Incident, SecurityEvent.incident_id == Incident.id))

        total = joined(func.count(SecurityEvent.id)).scalar() or 0
        rows = (joined(SecurityEvent, Incident.title, Incident.severity)
                .order_by(ts.asc() if order == "asc" else ts.desc(), SecurityEvent.id)
                .offset((page - 1) * page_size).limit(page_size).all())

        items = []
        for event, incident_title, incident_severity in rows:
            view = logic.event_view(event.raw_data)
            items.append({
                "id": str(event.id),
                "incident_id": str(event.incident_id) if event.incident_id else None,
                "incident_title": incident_title,
                "incident_severity": (incident_severity or "").lower() or None,
                "timestamp": _iso(event.timestamp or event.created_at),
                "event_type": event.event_type,
                "source_ip": event.source_ip,
                "destination_ip": event.destination_ip,
                "user": view["user"], "status": view["status"], "message": view["message"],
                "event_hash": event.event_hash,
                "raw_data": event.raw_data,
            })

        by_type = {(t or "unknown"): c for t, c in
                   joined(SecurityEvent.event_type, func.count(SecurityEvent.id))
                   .group_by(SecurityEvent.event_type).all()}
        by_severity = {((s or "unscored").lower()): c for s, c in
                       joined(Incident.severity, func.count(SecurityEvent.id))
                       .group_by(Incident.severity).all()}
        day = func.date(ts)
        day_rows = (joined(day, func.count(SecurityEvent.id)).group_by(day)
                    .order_by(day.desc()).limit(30).all())
        failed_logins = (joined(func.count(SecurityEvent.id))
                         .filter(func.lower(SecurityEvent.event_type) == "login",
                                 func.lower(SecurityEvent.raw_data["status"].astext) == "failed").scalar() or 0)
        return {
            "items": items, "total": total, "page": page, "page_size": page_size,
            "stats": {
                "total": total,
                "distinct_sources": joined(func.count(func.distinct(SecurityEvent.source_ip))).scalar() or 0,
                "distinct_destinations": joined(func.count(func.distinct(SecurityEvent.destination_ip))).scalar() or 0,
                "failed_logins": failed_logins,
                "by_type": by_type, "by_incident_severity": by_severity,
                "by_day": [{"date": d.isoformat() if hasattr(d, "isoformat") else str(d), "count": c}
                           for d, c in reversed(day_rows)],
            },
        }

    # ----------------------------------------------------- incident investigations
    @router.get("/incidents/{incident_id}/investigations")
    def incident_investigations(incident_id: str, db: Session = Depends(get_db),
                                _user=Depends(require_active_user)) -> Dict[str, Any]:
        iid = _uuid(incident_id, "incident_id")
        incident = db.query(Incident).filter(Incident.id == iid).first()
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        investigations = (db.query(Investigation).filter(Investigation.incident_id == iid)
                          .order_by(Investigation.created_at.desc()).all())
        result = []
        for inv in investigations:
            runs = (db.query(AgentRun).filter(AgentRun.investigation_id == inv.id)
                    .order_by(AgentRun.started_at).all())
            approvals = (db.query(Approval).filter(Approval.investigation_id == inv.id)
                         .order_by(Approval.created_at).all())
            result.append({
                "id": str(inv.id), "status": inv.status, "summary": inv.summary,
                "confidence_score": inv.confidence_score,
                "created_at": _iso(inv.created_at), "updated_at": _iso(inv.updated_at),
                "agent_runs": [{
                    "id": str(r.id), "agent_name": r.agent_name, "status": r.status,
                    "started_at": _iso(r.started_at), "completed_at": _iso(r.completed_at),
                    "duration_s": logic.duration_seconds(r.started_at, r.completed_at),
                    "error_message": r.error_message, "output_data": r.output_data,
                } for r in runs],
                "approvals": [{
                    "id": str(a.id), "action_type": a.action_type, "status": a.status,
                    "reason": a.reason, "created_at": _iso(a.created_at), "resolved_at": _iso(a.resolved_at),
                } for a in approvals],
            })
        return {
            "incident": {"id": str(incident.id), "title": incident.title, "description": incident.description,
                         "status": incident.status, "severity": incident.severity,
                         "created_at": _iso(incident.created_at), "updated_at": _iso(incident.updated_at)},
            "investigations": result,
        }

    # ------------------------------------------------------------------ agents
    @router.get("/agents/overview")
    def agents_overview(db: Session = Depends(get_db), _user=Depends(require_active_user)) -> Dict[str, Any]:
        run_rows = (db.query(AgentRun.id, AgentRun.investigation_id, AgentRun.agent_name, AgentRun.status,
                             AgentRun.started_at, AgentRun.completed_at, AgentRun.error_message)
                    .order_by(AgentRun.started_at.desc()).limit(RUN_SCAN_LIMIT).all())
        runs = [{"id": str(r.id), "investigation_id": str(r.investigation_id), "agent_name": r.agent_name,
                 "status": r.status, "started_at": r.started_at, "completed_at": r.completed_at,
                 "error_message": r.error_message} for r in run_rows]

        inv_rows = db.query(Investigation.id, Investigation.incident_id, Investigation.status,
                            Investigation.confidence_score, Investigation.created_at,
                            Investigation.updated_at).order_by(Investigation.created_at.desc()).all()
        inv_by_id = {str(i.id): i for i in inv_rows}
        incident_titles = {str(i.id): (i.title, i.severity) for i in
                           db.query(Incident.id, Incident.title, Incident.severity).all()}

        recent_ids = [r["id"] for r in runs[:RUN_OUTPUT_LIMIT]]
        outputs = {}
        if recent_ids:
            outputs = {str(o.id): o.output_data for o in
                       db.query(AgentRun.id, AgentRun.output_data).filter(AgentRun.id.in_(recent_ids)).all()}

        recent_runs = []
        for r in runs[:100]:
            inv = inv_by_id.get(r["investigation_id"])
            title = incident_titles.get(str(inv.incident_id), (None, None))[0] if inv else None
            recent_runs.append({
                "id": r["id"], "agent_name": r["agent_name"], "status": r["status"],
                "started_at": _iso(r["started_at"]), "completed_at": _iso(r["completed_at"]),
                "duration_s": logic.duration_seconds(r["started_at"], r["completed_at"]),
                "error_message": r["error_message"], "investigation_id": r["investigation_id"],
                "incident_id": str(inv.incident_id) if inv else None, "incident_title": title,
                "output_data": outputs.get(r["id"]),
            })

        by_status: Dict[str, int] = {}
        for inv in inv_rows:
            by_status[inv.status or "unknown"] = by_status.get(inv.status or "unknown", 0) + 1
        stats = logic.agent_stats(runs)
        for s in stats:
            s["last_run_at"] = _iso(s["last_run_at"])
        return {
            "agents": stats,
            "runs": recent_runs,
            "runs_scanned": len(runs),
            "investigations": {
                "by_status": by_status, "total": len(inv_rows),
                "recent": [{
                    "id": str(i.id), "incident_id": str(i.incident_id), "status": i.status,
                    "incident_title": incident_titles.get(str(i.incident_id), (None, None))[0],
                    "confidence_score": i.confidence_score,
                    "created_at": _iso(i.created_at), "updated_at": _iso(i.updated_at),
                    "duration_s": logic.duration_seconds(i.created_at, i.updated_at)
                    if (i.status or "") in ("completed", "failed", "awaiting_review") else None,
                } for i in inv_rows[:20]],
            },
            "pending_approvals": db.query(func.count(Approval.id)).filter(Approval.status == "pending").scalar() or 0,
        }

    # ------------------------------------------------------------------- audit
    @router.get("/audit")
    def list_audit(
        entity_type: Optional[str] = None,
        action: Optional[str] = Query(None, max_length=100),
        q: Optional[str] = Query(None, max_length=200),
        incident_id: Optional[str] = None,
        verification: Optional[str] = Query(None, description="verified|linked|broken_link|hash_mismatch"),
        page: int = Query(1, ge=1),
        page_size: int = Query(25, ge=1, le=200),
        db: Session = Depends(get_db),
        _user=Depends(require_active_user),
    ) -> Dict[str, Any]:
        rows = (db.query(AuditLog).order_by(AuditLog.timestamp.asc()).limit(AUDIT_FETCH_LIMIT).all())
        entries = [{"id": str(r.id), "entity_id": str(r.entity_id) if r.entity_id else None,
                    "entity_type": r.entity_type, "action": r.action, "details": r.details,
                    "timestamp": r.timestamp, "previous_hash": r.previous_hash, "current_hash": r.current_hash}
                   for r in rows]
        results = logic.verify_audit_chain(entries)

        incidents = {str(i.id): i.title for i in db.query(Incident.id, Incident.title).all()}
        inv_to_incident = {str(i.id): str(i.incident_id) for i in db.query(Investigation.id, Investigation.incident_id).all()}
        app_to_inv = {str(a.id): str(a.investigation_id) for a in db.query(Approval.id, Approval.investigation_id).all()}
        incident_ids = set(incidents)

        shaped = []
        for e in reversed(entries):   # newest first
            related = logic.related_incident_id(e, incident_ids, inv_to_incident, app_to_inv)
            shaped.append({
                "id": e["id"], "timestamp": _iso(e["timestamp"]), "entity_type": e["entity_type"],
                "entity_id": e["entity_id"], "action": e["action"], "actor": logic.actor_of(e),
                "incident_id": related, "incident_title": incidents.get(related) if related else None,
                "previous_hash": e["previous_hash"], "current_hash": e["current_hash"],
                "details": e["details"], "verification": results[e["id"]],
            })

        def keep(item) -> bool:
            if entity_type and (item["entity_type"] or "").lower() != entity_type.lower():
                return False
            if action and action.lower() not in (item["action"] or "").lower():
                return False
            if incident_id and item["incident_id"] != incident_id:
                return False
            if verification and item["verification"]["status"] != verification:
                return False
            if q:
                needle = q.lower()
                hay = " ".join(str(item.get(k) or "") for k in
                               ("action", "actor", "entity_type", "entity_id", "incident_title", "current_hash")).lower()
                if needle not in hay:
                    return False
            return True

        filtered = [i for i in shaped if keep(i)]
        start = (page - 1) * page_size
        return {
            "items": filtered[start:start + page_size], "total": len(filtered),
            "page": page, "page_size": page_size,
            "verification": {**logic.summarize_verification(results),
                             "truncated": len(rows) >= AUDIT_FETCH_LIMIT,
                             "method": ("Each record's previous_hash is compared with the preceding record's hash, and the "
                                        "hash is recomputed for investigation-start, approval and agent-execution records. "
                                        "Other record types are reported as 'linked' only.")},
            "entity_types": sorted({i["entity_type"] for i in shaped if i["entity_type"]}),
        }

    # -------------------------------------------------------------------- risk
    @router.get("/risk/overview")
    def risk_overview(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db),
                      _user=Depends(require_active_user)) -> Dict[str, Any]:
        incidents = (db.query(Incident.id, Incident.title, Incident.status, Incident.severity, Incident.created_at)
                     .order_by(Incident.created_at.desc()).limit(1000).all())
        latest: Dict[str, Any] = {}
        for inv in db.query(Investigation).order_by(Investigation.created_at.desc()).all():
            latest.setdefault(str(inv.incident_id), inv)     # newest first => first one wins
        inv_ids = [i.id for i in latest.values()]
        outputs: Dict[str, Dict[str, Any]] = {}
        if inv_ids:
            wanted = ["RiskAssessmentAgent", "DetectionAgent", "ThreatIntelAgent", "InvestigationAgent", "AuditAgent"]
            for run in (db.query(AgentRun.investigation_id, AgentRun.agent_name, AgentRun.output_data)
                        .filter(AgentRun.investigation_id.in_(inv_ids), AgentRun.agent_name.in_(wanted)).all()):
                outputs.setdefault(str(run.investigation_id), {})[run.agent_name] = run.output_data
        pending = {str(a.investigation_id) for a in
                   db.query(Approval.investigation_id).filter(Approval.status == "pending").all()}

        rows = []
        for inc in incidents:
            inv = latest.get(str(inc.id))
            agents = outputs.get(str(inv.id), {}) if inv else {}
            risk = logic.risk_from_agent_runs(agents)
            confidence = risk.get("confidence") if risk["available"] else None
            if confidence is None and inv is not None:
                confidence = inv.confidence_score
            rows.append({
                "incident_id": str(inc.id), "title": inc.title, "status": inc.status,
                "severity": (inc.severity or "").lower() or None,
                "created_at": inc.created_at, "assessed_at": inv.created_at if inv else None,
                "investigation_id": str(inv.id) if inv else None,
                "investigation_status": inv.status if inv else None,
                "assessed": risk["available"], "risk_severity": risk.get("severity"),
                "confidence": confidence, "justification": risk.get("justification"),
                "evidence": logic.evidence_from_outputs(agents) if agents else None,
                "awaiting_approval": bool(inv and str(inv.id) in pending),
            })
        assessed = [r for r in rows if r["assessed"]]
        distribution: Dict[str, int] = {}
        for r in rows:
            distribution[r["severity"] or "unscored"] = distribution.get(r["severity"] or "unscored", 0) + 1
        confidences = [r["confidence"] for r in rows if isinstance(r["confidence"], (int, float))]
        cutoff = datetime.utcnow().timestamp() - days * 86400
        trend_rows = [{"created_at": r["assessed_at"], "severity": r["risk_severity"], "confidence": r["confidence"]}
                      for r in assessed if r["assessed_at"] and r["assessed_at"].timestamp() >= cutoff]
        for r in rows:
            r["created_at"], r["assessed_at"] = _iso(r["created_at"]), _iso(r["assessed_at"])
        return {
            "incidents": rows,
            "totals": {"incidents": len(rows), "assessed": len(assessed), "unassessed": len(rows) - len(assessed),
                       "awaiting_approval": sum(1 for r in rows if r["awaiting_approval"])},
            "distribution": distribution,
            "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else None,
            "confidence_buckets": logic.confidence_buckets(confidences),
            "trend": logic.risk_trend(trend_rows),
        }

    # ------------------------------------------------------------------ system
    @router.get("/system/info")
    def system_info(db: Session = Depends(get_db), _user=Depends(require_active_user)) -> Dict[str, Any]:
        started = time.perf_counter()
        try:
            db.execute(text("SELECT 1"))
            database = {"status": "ok", "latency_ms": round((time.perf_counter() - started) * 1000, 1)}
        except Exception:
            database = {"status": "fail", "latency_ms": None}
        database["engine"] = getattr(getattr(db.bind, "dialect", None), "name", None)

        key = (os.getenv("OPENAI_API_KEY", "dummy") or "").strip()
        mock = (not key) or key == "dummy" or key.startswith("your_")
        webhook = os.getenv("N8N_WEBHOOK_URL")
        host = None
        if webhook:
            try:
                parsed = urlparse(webhook)
                host = f"{parsed.scheme}://{parsed.hostname}" if parsed.hostname else None
            except ValueError:
                host = None
        return {
            "application": {"name": "SENTINELX API", "version": config.get("version"),
                            "python": sys.version.split()[0], "platform": platform.system()},
            "database": database,
            "authentication": {
                "scheme": "OAuth2 password flow with JWT bearer tokens",
                "algorithm": config.get("algorithm"),
                "token_lifetime_minutes": config.get("token_minutes"),
                "secret_key_configured": bool(os.getenv("SECRET_KEY")) and not config.get("secret_key_is_default", True),
                "uses_default_secret_key": bool(config.get("secret_key_is_default", True)),
                "bootstrap_admin_configured": bool(os.getenv("ADMIN_USERNAME") and os.getenv("ADMIN_PASSWORD")),
            },
            "agents": {"llm_mode": "mock" if mock else "live", "llm_key_configured": not mock,
                       "agent_names": logic.CANONICAL_AGENTS},
            "n8n": {"webhook_configured": bool(webhook), "host": host},
        }

    return router
