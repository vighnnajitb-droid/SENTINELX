import pytest
from agents.detection import DetectionAgent
from agents.schemas import AgentInput

def test_detection_agent_mock():
    # Force mock mode by setting env var before initializing or using the fallback logic
    agent = DetectionAgent()
    agent.is_mock = True
    
    input_data = AgentInput(
        incident_id="test",
        events=[
            {"source_ip": "1.1.1.1", "status": "failed", "event_type": "login"},
            {"source_ip": "1.1.1.1", "status": "failed", "event_type": "login"},
            {"source_ip": "1.1.1.1", "status": "failed", "event_type": "login"}
        ]
    )
    
    result = agent.run(input_data)
    assert result.is_suspicious is True
    assert "Repeated failed login attempts from 1.1.1.1" in result.findings

from agents.investigation import InvestigationAgent
from agents.threat_intel import ThreatIntelAgent
from agents.risk_assessment import RiskAssessmentAgent
from agents.response import ResponseAgent
from agents.audit import AuditAgent

def test_investigation_agent_mock():
    agent = InvestigationAgent()
    agent.is_mock = True
    input_data = AgentInput(
        incident_id="test",
        events=[{"source_ip": "1.1.1.1", "status": "failed", "event_type": "login"}],
        context={"detection_findings": ["Brute force attempt"]}
    )
    result = agent.run(input_data)
    assert len(result.timeline) == 1
    assert "1.1.1.1" in result.entities_involved

def test_threat_intel_agent_mock():
    agent = ThreatIntelAgent()
    agent.is_mock = True
    input_data = AgentInput(
        incident_id="test",
        events=[],
        context={"entities_involved": ["203.0.113.45"]}
    )
    result = agent.run(input_data)
    assert result.known_threats_found is True
    assert result.enriched_indicators[0]["indicator"] == "203.0.113.45"

def test_risk_assessment_agent_mock():
    agent = RiskAssessmentAgent()
    agent.is_mock = True
    input_data = AgentInput(
        incident_id="test",
        events=[],
        context={"detection_findings": ["Brute force"], "threat_intel": {"known_threats_found": True}}
    )
    result = agent.run(input_data)
    assert result.severity == "high"
    assert result.confidence_score >= 0.8

def test_response_agent_mock():
    agent = ResponseAgent()
    agent.is_mock = True
    input_data = AgentInput(
        incident_id="test",
        events=[],
        context={"risk_assessment": {"severity": "critical"}, "entities_involved": ["203.0.113.45"]}
    )
    result = agent.run(input_data)
    assert result.requires_human_approval is True
    assert "Review blocking recommendation for 203.0.113.45" in result.automated_actions_proposed

def test_agent_invalid_input_fallback():
    # If the LLM throws an error (mocked by bad parsing), it should fallback to mock
    agent = DetectionAgent()
    agent.is_mock = False # Force LLM attempt
    # Since dummy key is used, LLM call will fail and it should gracefully fallback to mock
    agent.api_key = "dummy" 
    
    input_data = AgentInput(incident_id="test", events=[])
    result = agent.run(input_data)
    assert result.is_suspicious is False


