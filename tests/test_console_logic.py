"""Unit tests for backend/console_logic.py (audit verification, agent stats, event views)."""
import hashlib
import json
from datetime import datetime, timedelta

from backend import console_logic as L

T0 = datetime(2026, 11, 21, 10, 0)


def _h(text):
    return hashlib.sha256(text.encode()).hexdigest()


def build_chain():
    """Write a chain exactly the way backend/main.py does."""
    entries, prev = [], None
    inv_id, appr_id = "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"

    def add(entity_id, entity_type, action, details, hash_text):
        nonlocal prev
        current = _h(f"{prev}{hash_text}" if prev else hash_text)
        entries.append({"id": f"e{len(entries)}", "entity_id": entity_id, "entity_type": entity_type, "action": action,
                        "details": details, "timestamp": T0 + timedelta(seconds=len(entries)),
                        "previous_hash": prev, "current_hash": current})
        prev = current

    add(inv_id, "Investigation", "started", {"incident_id": "i1", "user": "admin"}, f"{inv_id}_started_admin")
    out = {"is_suspicious": True, "findings": ["x"], "score": 0.5}
    add(inv_id, "Investigation", "Agent DetectionAgent execution", out, json.dumps(out, sort_keys=True))
    add(appr_id, "Approval", "approve", {"user": "admin", "investigation_id": inv_id}, f"{appr_id}_approve_admin")
    return entries


def test_untampered_chain_is_fully_verified():
    res = L.verify_audit_chain(build_chain())
    assert [r["status"] for r in res.values()] == ["verified"] * 3
    assert L.summarize_verification(res) == {"checked": 3, "verified": 3, "linked": 0, "broken_link": 0, "hash_mismatch": 0}


def test_tampered_details_are_a_hash_mismatch():
    chain = build_chain()
    chain[1]["details"] = {"is_suspicious": False, "findings": [], "score": 0.5}
    res = L.verify_audit_chain(chain)
    assert res["e1"]["status"] == "hash_mismatch" and res["e0"]["status"] == "verified"


def test_deleted_record_breaks_the_link():
    chain = build_chain()
    del chain[1]
    res = L.verify_audit_chain(chain)
    assert res["e2"]["status"] == "broken_link"


def test_swapped_actor_is_detected():
    chain = build_chain()
    chain[2]["details"]["user"] = "mallory"
    assert L.verify_audit_chain(chain)["e2"]["status"] == "hash_mismatch"


def test_unknown_record_type_is_linked_not_verified():
    chain = build_chain()
    prev = chain[-1]["current_hash"]
    chain.append({"id": "x", "entity_id": None, "entity_type": "Other", "action": "custom", "details": {},
                  "timestamp": T0 + timedelta(minutes=1), "previous_hash": prev, "current_hash": _h("whatever")})
    assert L.verify_audit_chain(chain)["x"]["status"] == "linked"


def test_first_record_must_have_no_previous_hash():
    chain = build_chain()
    chain[0]["previous_hash"] = "deadbeef"
    assert L.verify_audit_chain(chain)["e0"]["status"] == "broken_link"


def test_actor_and_related_incident():
    chain = build_chain()
    assert L.actor_of(chain[0]) == "admin"
    assert L.actor_of(chain[1]) == "system (agent pipeline)"
    inv_to_inc = {"11111111-1111-1111-1111-111111111111": "i1"}
    app_to_inv = {"22222222-2222-2222-2222-222222222222": "11111111-1111-1111-1111-111111111111"}
    ids = {"i1"}
    assert L.related_incident_id(chain[0], ids, inv_to_inc, app_to_inv) == "i1"
    assert L.related_incident_id(chain[1], ids, inv_to_inc, app_to_inv) == "i1"
    assert L.related_incident_id(chain[2], ids, inv_to_inc, app_to_inv) == "i1"
    assert L.related_incident_id({"entity_id": "zzz", "details": None}, ids, inv_to_inc, app_to_inv) is None


def test_agent_stats_cover_all_six_agents_with_zeros():
    runs = [
        {"agent_name": "DetectionAgent", "status": "completed", "started_at": T0, "completed_at": T0 + timedelta(seconds=4)},
        {"agent_name": "DetectionAgent", "status": "completed", "started_at": T0 + timedelta(minutes=1), "completed_at": T0 + timedelta(minutes=1, seconds=2)},
        {"agent_name": "AuditAgent", "status": "failed", "started_at": T0, "completed_at": None},
        {"agent_name": "UnknownAgent", "status": "completed", "started_at": T0, "completed_at": T0},
    ]
    stats = {s["name"]: s for s in L.agent_stats(runs)}
    assert list(stats) == L.CANONICAL_AGENTS
    assert stats["DetectionAgent"]["total_runs"] == 2 and stats["DetectionAgent"]["avg_duration_s"] == 3.0
    assert stats["AuditAgent"]["failed"] == 1 and stats["AuditAgent"]["avg_duration_s"] is None
    assert stats["ResponseAgent"]["total_runs"] == 0 and stats["ResponseAgent"]["last_status"] is None


def test_event_view_and_like_pattern():
    assert L.event_view({"username": "bob", "result": "FAILED", "message": "x"}) == {"user": "bob", "status": "FAILED", "message": "x"}
    assert L.event_view(None) == {"user": None, "status": None, "message": None}
    assert L.like_pattern("50%_off") == "%50\\%\\_off%"


def test_risk_extraction_never_infers():
    assert L.risk_from_agent_runs({}) == {"available": False}
    r = L.risk_from_agent_runs({"RiskAssessmentAgent": {"severity": "HIGH", "confidence_score": 0.82, "justification": "j"}})
    assert (r["severity"], r["confidence"]) == ("high", 0.82)
    assert L.risk_from_agent_runs({"RiskAssessmentAgent": {"severity": "low"}})["confidence"] is None


def test_duration_handles_missing_values():
    assert L.duration_seconds(None, T0) is None
    assert L.duration_seconds(T0, T0 - timedelta(seconds=5)) == 0.0


def test_evidence_from_outputs_reports_only_what_agents_said():
    e = L.evidence_from_outputs({
        "DetectionAgent": {"is_suspicious": True, "findings": ["a", "b"]},
        "ThreatIntelAgent": {"known_threats_found": True, "enriched_indicators": [
            {"indicator": "1.1.1.1", "reputation": "simulated_malicious"}, {"indicator": "2.2.2.2", "reputation": "clean"}]},
        "AuditAgent": {"evidence_verified": False, "audit_trail_valid": True}})
    assert e["findings"] == ["a", "b"] and e["flagged_indicators"] == ["1.1.1.1"]
    assert e["evidence_verified"] is False and e["audit_trail_valid"] is True
    assert L.evidence_from_outputs({})["is_suspicious"] is None and L.evidence_from_outputs({})["findings"] == []


def test_confidence_buckets_and_risk_trend():
    b = L.confidence_buckets([0.2, 0.55, 0.75, 0.95, 1.0, None])
    assert [x["count"] for x in b] == [1, 1, 1, 2]
    rows = [{"created_at": T0, "severity": "high", "confidence": 0.8},
            {"created_at": T0 + timedelta(hours=1), "severity": "low", "confidence": 0.6},
            {"created_at": T0 + timedelta(days=1), "severity": None, "confidence": None}]
    t = L.risk_trend(rows)
    assert [d["count"] for d in t] == [2, 1] and t[0]["avg_confidence"] == 0.7 and t[1]["avg_confidence"] is None
    assert t[1]["by_severity"] == {"unscored": 1}


def test_known_record_type_missing_required_fields_is_not_silently_linked():
    """Stripping the fields needed to recompute a hash must NOT downgrade to 'linked'."""
    chain = build_chain()
    chain[0]["details"] = {"incident_id": "i1"}            # 'user' removed from an investigation-start record
    assert L.verify_audit_chain(chain)["e0"]["status"] == "hash_mismatch"
    chain = build_chain()
    chain[2]["details"] = {"investigation_id": "x"}        # approval record without its actor
    assert L.verify_audit_chain(chain)["e2"]["status"] == "hash_mismatch"
    chain = build_chain()
    chain[1]["details"] = None                             # agent execution with its output wiped
    assert L.verify_audit_chain(chain)["e1"]["status"] == "hash_mismatch"
