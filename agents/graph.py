import json
from typing import Dict, Any, TypedDict, Optional, List
from langgraph.graph import StateGraph, END
from agents.schemas import (
    InvestigationState, AgentInput, 
    DetectionOutput, InvestigationOutput, ThreatIntelOutput,
    RiskAssessmentOutput, AuditOutput, ResponseOutput
)
from agents.detection import DetectionAgent
from agents.investigation import InvestigationAgent
from agents.threat_intel import ThreatIntelAgent
from agents.risk_assessment import RiskAssessmentAgent
from agents.audit import AuditAgent
from agents.response import ResponseAgent
from datetime import datetime

# Define the state for LangGraph
class GraphState(TypedDict):
    incident_id: str
    events: List[Dict[str, Any]]
    context: Dict[str, Any]
    detection_result: Optional[DetectionOutput]
    investigation_result: Optional[InvestigationOutput]
    threat_intel_result: Optional[ThreatIntelOutput]
    risk_assessment_result: Optional[RiskAssessmentOutput]
    audit_result: Optional[AuditOutput]
    response_result: Optional[ResponseOutput]
    status: str
    attempts: int

# Agent instances
detection_agent = DetectionAgent()
investigation_agent = InvestigationAgent()
threat_intel_agent = ThreatIntelAgent()
risk_assessment_agent = RiskAssessmentAgent()
audit_agent = AuditAgent()
response_agent = ResponseAgent()

# Node functions
def detect(state: GraphState) -> Dict:
    input_data = AgentInput(incident_id=state["incident_id"], events=state["events"], context=state["context"])
    result = detection_agent.run(input_data)
    context = state["context"]
    context["detection_findings"] = result.findings
    return {"detection_result": result, "context": context}

def investigate(state: GraphState) -> Dict:
    input_data = AgentInput(incident_id=state["incident_id"], events=state["events"], context=state["context"])
    result = investigation_agent.run(input_data)
    context = state["context"]
    context["entities_involved"] = result.entities_involved
    return {"investigation_result": result, "context": context}

def enrich(state: GraphState) -> Dict:
    input_data = AgentInput(incident_id=state["incident_id"], events=state["events"], context=state["context"])
    result = threat_intel_agent.run(input_data)
    context = state["context"]
    context["threat_intel"] = result.model_dump()
    return {"threat_intel_result": result, "context": context}

def assess_risk(state: GraphState) -> Dict:
    input_data = AgentInput(incident_id=state["incident_id"], events=state["events"], context=state["context"])
    result = risk_assessment_agent.run(input_data)
    context = state["context"]
    context["risk_assessment"] = result.model_dump()
    return {"risk_assessment_result": result, "context": context}

def audit(state: GraphState) -> Dict:
    input_data = AgentInput(incident_id=state["incident_id"], events=state["events"], context=state["context"])
    result = audit_agent.run(input_data)
    return {"audit_result": result}

def recommend_response(state: GraphState) -> Dict:
    """Generate a response recommendation only after a successful audit."""
    audit_result = state.get("audit_result")

    if (
        not audit_result
        or not audit_result.evidence_verified
        or not audit_result.audit_trail_valid
    ):
        return {
            "response_result": None,
            "status": "awaiting_review"
        }

    input_data = AgentInput(
        incident_id=state["incident_id"],
        events=state["events"],
        context=state["context"]
    )

    result = response_agent.run(input_data)

    final_status = (
        "awaiting_review"
        if result.requires_human_approval
        else "completed"
    )

    return {
        "response_result": result,
        "status": final_status
    }

# Conditional logic
def should_investigate(state: GraphState) -> str:
    # Always investigate for this workflow to get the full report, or skip if no suspicious activity
    result = state.get("detection_result")
    if result and result.is_suspicious:
        return "investigate"
    # Even if not suspicious, we might want to run through to say it's benign, 
    # but for efficiency let's skip to audit or response with benign context
    return "investigate" # Force full chain for demo completeness

def mark_awaiting_review(state: GraphState) -> Dict:
    """Stop automated response when evidence verification fails."""
    return {
        "status": "awaiting_review",
        "response_result": None
    }


def check_audit(state: GraphState) -> str:
    result = state.get("audit_result")

    if (
        result
        and result.evidence_verified
        and result.audit_trail_valid
    ):
        return "recommend_response"

    return "awaiting_review"

# Build Graph
def create_investigation_graph():
    workflow = StateGraph(GraphState)
    
    workflow.add_node("detect", detect)
    workflow.add_node("investigate", investigate)
    workflow.add_node("enrich", enrich)
    workflow.add_node("assess_risk", assess_risk)
    workflow.add_node("audit", audit)
    workflow.add_node("recommend_response", recommend_response)
    workflow.add_node("awaiting_review", mark_awaiting_review)
    
    workflow.set_entry_point("detect")
    
    workflow.add_conditional_edges(
        "detect",
        should_investigate,
        {
            "investigate": "investigate"
        }
    )
    
    workflow.add_edge("investigate", "enrich")
    workflow.add_edge("enrich", "assess_risk")
    workflow.add_edge("assess_risk", "audit")
    
    workflow.add_conditional_edges(
        "audit",
        check_audit,
        {
            "recommend_response": "recommend_response",
            "awaiting_review": "awaiting_review"
        }
    )
    
    workflow.add_edge("recommend_response", END)
    workflow.add_edge("awaiting_review", END)
    
    return workflow.compile()

# Instantiate the graph
app_graph = create_investigation_graph()

def run_investigation(incident_id: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
    initial_state = {
        "incident_id": incident_id,
        "events": events,
        "context": {},
        "detection_result": None,
        "investigation_result": None,
        "threat_intel_result": None,
        "risk_assessment_result": None,
        "audit_result": None,
        "response_result": None,
        "status": "running",
        "attempts": 1
    }
    
    # Run the graph
    result = app_graph.invoke(initial_state)
    return result

