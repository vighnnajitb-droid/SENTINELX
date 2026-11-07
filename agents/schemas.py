from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class AgentInput(BaseModel):
    incident_id: str
    events: List[Dict[str, Any]]
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)

class DetectionOutput(BaseModel):
    is_suspicious: bool = Field(description="Whether the events indicate suspicious activity")
    findings: List[str] = Field(description="List of suspicious findings or anomalies")
    related_event_ids: List[str] = Field(description="IDs of events associated with findings")

class InvestigationOutput(BaseModel):
    correlation_summary: str = Field(description="Summary of correlated events")
    timeline: List[Dict[str, str]] = Field(description="Timeline of activity")
    entities_involved: List[str] = Field(description="List of IPs, users, or assets involved")

class ThreatIntelOutput(BaseModel):
    enriched_indicators: List[Dict[str, Any]] = Field(description="Indicators with threat intel data")
    known_threats_found: bool = Field(description="Whether known threats were matched")

class RiskAssessmentOutput(BaseModel):
    severity: str = Field(description="Severity level (low, medium, high, critical)")
    confidence_score: float = Field(description="Confidence in the assessment (0.0 to 1.0)")
    justification: str = Field(description="Reasoning for the severity and confidence")

class AuditOutput(BaseModel):
    evidence_verified: bool = False
    discrepancies: List[str] = Field(default_factory=list)
    audit_trail_valid: bool = False
class ResponseOutput(BaseModel):
    recommendations: List[str] = Field(description="Defensive response recommendations")
    requires_human_approval: bool = Field(description="Whether the actions require human approval")
    automated_actions_proposed: List[str] = Field(description="Actions that could be automated (if approved)")

class InvestigationState(BaseModel):
    incident_id: str
    events: List[Dict[str, Any]]
    detection_result: Optional[DetectionOutput] = None
    investigation_result: Optional[InvestigationOutput] = None
    threat_intel_result: Optional[ThreatIntelOutput] = None
    risk_assessment_result: Optional[RiskAssessmentOutput] = None
    audit_result: Optional[AuditOutput] = None
    response_result: Optional[ResponseOutput] = None
    status: str = "pending"
    attempts: int = 0

