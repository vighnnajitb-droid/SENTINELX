from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import List, Dict, Any
import os
import uuid
import json
import tempfile
import requests

from database.session import get_db, SessionLocal
from database.models import User, Incident, SecurityEvent, Investigation, AgentRun, Approval, AuditLog
from utils.parser import parse_log_file, prepare_security_events
from agents.graph import run_investigation

# For a real implementation, you'd use passlib and jose properly, here is a mock for brevity
import jwt
from passlib.context import CryptContext

app = FastAPI(title="SENTINELX API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here_for_jwt")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# --- Auth Dependencies ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid auth credentials")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid auth credentials")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# --- Setup basic user if not exists ---


@app.on_event("startup")
def create_judge_account():
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")

    if not username or not password:
        print("Judge account setup skipped: credentials not configured.")
        return

    db = SessionLocal()

    try:
        existing_user = db.query(User).filter(
            User.username == username
        ).first()

        if existing_user:
            print(f"Judge account '{username}' already exists.")
            return

        hashed_password = pwd_context.hash(password)

        judge = User(
            username=username,
            hashed_password=hashed_password,
            is_active=True
        )

        db.add(judge)
        db.commit()

        print(f"Judge account '{username}' created successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
# --- Log Upload & Incidents ---

@app.post("/api/v1/logs/upload")
async def upload_logs(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filename = os.path.basename(file.filename or "")

    if not filename.lower().endswith((".csv", ".json")):
        raise HTTPException(
            status_code=400,
            detail="Only CSV and JSON files are supported."
        )

    file_path = None

    try:
        # Save in the operating system's temporary directory.
        suffix = ".csv" if filename.lower().endswith(".csv") else ".json"

        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=suffix,
            prefix=f"sentinelx_{uuid.uuid4()}_",
            delete=False
        ) as temp_file:
            file_path = temp_file.name
            content = await file.read()
            temp_file.write(content)

        raw_events = parse_log_file(file_path)
        prepared_events = prepare_security_events(raw_events)

        incident = Incident(
            title=f"Log Upload: {filename}",
            description=f"Uploaded by {current_user.username}",
            status="open"
        )
        db.add(incident)
        db.flush()

        for pe in prepared_events:
            db_event = SecurityEvent(
                incident_id=incident.id,
                source_ip=pe.get("source_ip"),
                destination_ip=pe.get("destination_ip"),
                event_type=pe.get("event_type"),
                timestamp=(
                    pe.get("timestamp")
                    if isinstance(pe.get("timestamp"), datetime)
                    else datetime.utcnow()
                ),
                raw_data=pe.get("raw_data"),
                event_hash=pe.get("event_hash")
            )
            db.add(db_event)

        db.commit()

        try:
            webhook_url = os.getenv("N8N_WEBHOOK_URL")
            if webhook_url:
                requests.post(
                    webhook_url,
                    json={
                        "incident_id": str(incident.id),
                        "incident_title": incident.title,
                        "severity": "triage_pending"
                    },
                    timeout=10
                )
        except requests.RequestException as e:
            print(f"Failed to trigger webhook: {e}")

        return {
            "message": "Logs uploaded successfully",
            "incident_id": str(incident.id),
            "events_count": len(prepared_events)
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing or saving logs: {str(e)}"
        )
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        await file.close()

@app.get("/api/v1/incidents")
def get_incidents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    incidents = db.query(Incident).order_by(Incident.created_at.desc()).all()
    return [{
        "id": str(inc.id), 
        "title": inc.title, 
        "status": inc.status, 
        "severity": inc.severity,
        "created_at": inc.created_at
    } for inc in incidents]

@app.get("/api/v1/incidents/{incident_id}")
def get_incident(incident_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    events = db.query(SecurityEvent).filter(SecurityEvent.incident_id == incident_id).all()
    return {
        "id": str(incident.id),
        "title": incident.title,
        "description": incident.description,
        "status": incident.status,
        "severity": incident.severity,
        "events_count": len(events),
        "events": [
            {
                "id": str(e.id),
                "type": e.event_type,
                "timestamp": e.timestamp,
                "source": e.source_ip,
                "destination": e.destination_ip
            } for e in events
        ]
    }

# --- Investigations & Approvals ---
def run_investigation_task(investigation_id: str, incident_id: str, events: List[Dict]):
    db = next(get_db())
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    
    try:
        # Run the agent graph
        result = run_investigation(incident_id=incident_id, events=events)
        
        investigation.status = result.get("status", "completed")
        
        # Save results based on state
        risk_result = result.get("risk_assessment_result")
        if risk_result:
            investigation.confidence_score = getattr(risk_result, "confidence_score", None) if not isinstance(risk_result, dict) else risk_result.get("confidence_score")
            
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if incident:
            incident.status = "investigating" if investigation.status == "running" else "resolved"
            if risk_result:
                incident.severity = getattr(risk_result, "severity", None) if not isinstance(risk_result, dict) else risk_result.get("severity")
                
        # Create agent runs records
        agent_mapping = {
            "detection_result": "DetectionAgent",
            "investigation_result": "InvestigationAgent",
            "threat_intel_result": "ThreatIntelAgent",
            "risk_assessment_result": "RiskAssessmentAgent",
            "audit_result": "AuditAgent",
            "response_result": "ResponseAgent"
        }
        
        for key, agent_name in agent_mapping.items():
            res = result.get(key)
            if res:
                ar = AgentRun(
                    investigation_id=investigation_id,
                    agent_name=agent_name,
                    status="completed",
                    output_data=res if isinstance(res, dict) else (res.dict() if hasattr(res, "dict") else {"raw": str(res)}),
                    completed_at=datetime.utcnow()
                )
                db.add(ar)
                
                
                # Add to audit log
                last_audit = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).first()
                prev_hash = last_audit.current_hash if last_audit else None
                
                details_str = json.dumps(ar.output_data, sort_keys=True)
                hash_input = f"{prev_hash}{details_str}".encode() if prev_hash else details_str.encode()
                
                audit = AuditLog(
                    entity_id=investigation_id,
                    entity_type="Investigation",
                    action=f"Agent {agent_name} execution",
                    details=ar.output_data,
                    previous_hash=prev_hash,
                    current_hash=hashlib.sha256(hash_input).hexdigest()
                )
                db.add(audit)

                
        
        # Handle approvals if required
        resp = result.get("response_result")
        if resp and (getattr(resp, "requires_human_approval", False) if not isinstance(resp, dict) else resp.get("requires_human_approval", False)):
            approval = Approval(
                investigation_id=investigation_id,
                action_type="recommendation_approval",
                reason=json.dumps(getattr(resp, "automated_actions_proposed", []) if not isinstance(resp, dict) else resp.get("automated_actions_proposed", []))
            )
            db.add(approval)
            investigation.status = "awaiting_review"
            
        db.commit()
        
        # Webhook on investigation complete
        try:
            webhook_url = os.getenv("N8N_WEBHOOK_URL")
            if webhook_url:
                severity = risk_result.get("severity") if isinstance(risk_result, dict) else getattr(risk_result, "severity", "unknown") if risk_result else "unknown"
                requests.post(webhook_url, json={"incident_id": incident_id, "investigation_id": investigation_id, "status": investigation.status, "severity": severity})
        except Exception as e:
            print(f"Failed to trigger webhook on investigation completion: {e}")
            

    except Exception as e:
        investigation.status = "failed"
        investigation.summary = str(e)
        db.commit()

import hashlib

@app.post("/api/v1/investigations/{incident_id}/run")
def start_investigation(
    incident_id: str, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    events = db.query(SecurityEvent).filter(SecurityEvent.incident_id == incident_id).all()
    if not events:
        raise HTTPException(status_code=400, detail="No events to investigate")
        
    event_dicts = [
    {
        "source_ip": e.source_ip or "",
        "destination_ip": e.destination_ip or "",
        "event_type": e.event_type or "unknown",
        "timestamp": e.raw_data.get("timestamp") if isinstance(e.raw_data, dict) else None,
        "raw_data": e.raw_data or {},
        "event_hash": e.event_hash
    }
    for e in events
]
    
    investigation = Investigation(
        incident_id=incident_id,
        status="running"
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    
    
    # Audit trail
    last_audit = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).first()
    prev_hash = last_audit.current_hash if last_audit else None
    hash_input = f"{prev_hash}{investigation.id}_started_{current_user.username}".encode() if prev_hash else f"{investigation.id}_started_{current_user.username}".encode()
    
    audit = AuditLog(
        entity_id=investigation.id,
        entity_type="Investigation",
        action="started",
        details={"incident_id": incident_id, "user": current_user.username},
        previous_hash=prev_hash,
        current_hash=hashlib.sha256(hash_input).hexdigest()
    )

    db.add(audit)
    db.commit()
    
    # Run in background
    background_tasks.add_task(run_investigation_task, str(investigation.id), incident_id, event_dicts)
    
    return {"message": "Investigation started", "investigation_id": str(investigation.id)}

@app.get("/api/v1/investigations/{investigation_id}")
def get_investigation(investigation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return {
        "id": str(inv.id),
        "incident_id": str(inv.incident_id),
        "status": inv.status,
        "summary": inv.summary,
        "confidence_score": inv.confidence_score
    }

@app.get("/api/v1/investigations/{investigation_id}/agents")
def get_agent_runs(investigation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    runs = db.query(AgentRun).filter(AgentRun.investigation_id == investigation_id).all()
    return [{
        "id": str(r.id),
        "agent_name": r.agent_name,
        "status": r.status,
        "output_data": r.output_data,
        "completed_at": r.completed_at
    } for r in runs]

@app.post("/api/v1/approvals/{investigation_id}")
def process_approval(
    investigation_id: str,
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    action = payload.get("action") # approve or reject
    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    approval = db.query(Approval).filter(
        Approval.investigation_id == investigation_id,
        Approval.status == "pending"
    ).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="No pending approval found")
        
    approval.status = action + "d" # approved or rejected
    approval.user_id = current_user.id
    approval.resolved_at = datetime.utcnow()
    
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if inv:
        inv.status = "completed"
        
    
    # Audit log
    last_audit = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).first()
    prev_hash = last_audit.current_hash if last_audit else None
    hash_input = f"{prev_hash}{approval.id}_{action}_{current_user.username}".encode() if prev_hash else f"{approval.id}_{action}_{current_user.username}".encode()
    
    audit = AuditLog(
        entity_id=approval.id,
        entity_type="Approval",
        action=action,
        details={"user": current_user.username, "investigation_id": investigation_id},
        previous_hash=prev_hash,
        current_hash=hashlib.sha256(hash_input).hexdigest()
    )

    db.add(audit)
    db.commit()
    
    return {"message": f"Action {action}d successfully"}

@app.get("/api/v1/incidents/{incident_id}/audit")
def get_audit_logs(incident_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Find all investigations for this incident
    invs = db.query(Investigation).filter(Investigation.incident_id == incident_id).all()
    inv_ids = [str(i.id) for i in invs]
    
    logs = db.query(AuditLog).filter(
        (AuditLog.entity_id == incident_id) | 
        (AuditLog.entity_id.in_(inv_ids))
    ).order_by(AuditLog.timestamp.desc()).all()
    
    return [{
        "id": str(l.id),
        "entity_type": l.entity_type,
        "action": l.action,
        "details": l.details,
        "timestamp": l.timestamp,
        "current_hash": l.current_hash
    } for l in logs]

@app.get("/api/v1/reports/{incident_id}")
def generate_report(incident_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    investigations = db.query(Investigation).filter(Investigation.incident_id == incident_id).all()
    
    report = {
        "incident": {
            "title": incident.title,
            "status": incident.status,
            "severity": incident.severity
        },
        "investigations": []
    }
    
    for inv in investigations:
        runs = db.query(AgentRun).filter(AgentRun.investigation_id == inv.id).all()
        inv_data = {
            "status": inv.status,
            "agents": {r.agent_name: r.output_data for r in runs}
        }
        report["investigations"].append(inv_data)
        
    return report

@app.post("/api/v1/webhooks/n8n")
def n8n_webhook(payload: Dict[str, Any], current_user: User = Depends(get_current_user)):
    # Process n8n webhook (e.g., status updates from external systems)
    return {"message": "Webhook received", "payload": payload}



