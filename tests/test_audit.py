import pytest
from agents.audit import AuditAgent
from agents.schemas import AgentInput

def test_audit_agent_tamper_detection():
    agent = AuditAgent()
    agent.is_mock = True
    
    # Event with an incorrect hash (simulating tampering)
    input_data = AgentInput(
        incident_id="test",
        events=[{"source_ip": "1.1.1.1", "event_hash": "wrong_hash"}]
    )
    
    # For testing, we mock _verify_hashes to return False if hash is 'wrong_hash'
    original_verify = agent._verify_hashes
    agent._verify_hashes = lambda evts: False if any(e.get("event_hash") == "wrong_hash" for e in evts) else True
    
    result = agent.run(input_data)
    
    assert result.audit_trail_valid is False
    assert result.evidence_verified is False
    assert any("invalid" in item and "tampered" in item for item in result.discrepancies)
    
    agent._verify_hashes = original_verify

def test_audit_agent_missing_evidence():
    agent = AuditAgent()
    agent.is_mock = True
    
    # Empty events list
    input_data = AgentInput(incident_id="test", events=[])
    result = agent.run(input_data)
    
    assert result.evidence_verified is False
    assert "No events provided" in result.discrepancies[0]


