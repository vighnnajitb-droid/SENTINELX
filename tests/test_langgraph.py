import pytest
from agents.graph import app_graph
from utils.parser import prepare_security_events

def test_graph_routing_benign():
    initial_state = {
        "incident_id": "test",
        "events": [],
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
    
    result = app_graph.invoke(initial_state)
    
    assert result["detection_result"].is_suspicious is False
    assert result["audit_result"].evidence_verified is False # No events provided
    assert result["status"] == "awaiting_review" # Failed audit ALWAYS requires review

def test_graph_human_review_routing():
    initial_state = {
        "incident_id": "test",
        "events": prepare_security_events([
            {"source_ip": "203.0.113.45", "destination_ip": "", "status": "failed", "event_type": "login"},
            {"source_ip": "203.0.113.45", "destination_ip": "", "status": "failed", "event_type": "login"},
            {"source_ip": "203.0.113.45", "destination_ip": "", "status": "failed", "event_type": "login"}
        ]),
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
    
    result = app_graph.invoke(initial_state)
    
    # 203.0.113.45 triggers known threat, leading to high severity
    assert result["risk_assessment_result"].severity == "high"
    # High severity triggers response that requires human approval
    assert result["response_result"].requires_human_approval is True
    # The graph status must route to awaiting_review
    assert result["status"] == "awaiting_review"

def test_graph_failed_audit_never_verified():
    # If we pass an event with missing data or wrong hash to make audit fail
    initial_state = {
        "incident_id": "test",
        "events": [{"source_ip": "1.1.1.1", "event_hash": "wrong_hash"}],
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
    
    # Mock the audit verification logic for this test to force failure
    import agents.graph as g
    original_run = g.audit_agent.run
    
    from agents.schemas import AuditOutput
    def mock_fail_run(*args, **kwargs):
        return AuditOutput(evidence_verified=False, discrepancies=["Tampered"], audit_trail_valid=False)
        
    g.audit_agent.run = mock_fail_run
    
    try:
        result = app_graph.invoke(initial_state)
        # Verify it routes to awaiting_review if audit fails, and NEVER completes silently
        assert result["audit_result"].evidence_verified is False
        assert result["status"] == "awaiting_review"
    finally:
        g.audit_agent.run = original_run


