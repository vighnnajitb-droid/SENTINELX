"""Unit tests for backend/dashboard_logic.py (pure functions, no DB needed)."""
from datetime import date, datetime, timedelta

from backend import dashboard_logic as L

NOW = datetime(2026, 11, 21, 12, 0)


def test_ip_scope():
    assert L.ip_scope("10.1.2.3") == "internal"
    assert L.ip_scope("192.168.0.9") == "internal"
    assert L.ip_scope("127.0.0.1") == "internal"
    assert L.ip_scope("185.220.101.7") == "external"
    assert L.ip_scope("not-an-ip") == "unknown"
    assert L.ip_scope(None) == "unknown"


def test_intrusion_and_malware_classification():
    assert L.is_intrusion_event("port_scan", None)
    assert L.is_intrusion_event("login", "FAILED")
    assert not L.is_intrusion_event("login", "success")
    assert not L.is_intrusion_event("api_call", "failed")
    assert L.is_malware_event("Ransomware")
    assert not L.is_malware_event("data_exfiltration")


def test_daily_series_is_zero_filled_and_ordered():
    stamps = [NOW, NOW - timedelta(hours=1), NOW - timedelta(days=2), None]
    series = L.daily_series(stamps, 4, NOW.date())
    assert [p["date"] for p in series] == ["2026-11-18", "2026-11-19", "2026-11-20", "2026-11-21"]
    assert [p["count"] for p in series] == [0, 1, 0, 2]


def test_build_network_aggregates_and_flags():
    events = [
        {"source_ip": "185.1.1.1", "destination_ip": "10.0.0.5", "event_type": "port_scan", "status": None},
        {"source_ip": "185.1.1.1", "destination_ip": "10.0.0.5", "event_type": "login", "status": "failed"},
        {"source_ip": "10.0.0.5", "destination_ip": "10.0.0.6", "event_type": "api_call", "status": None},
        {"source_ip": "", "destination_ip": "10.0.0.6", "event_type": "api_call", "status": None},
    ]
    net = L.build_network(events, {"185.1.1.1": "simulated_malicious"})
    assert len(net["edges"]) == 2                      # the event with no source is skipped
    hot = net["edges"][0]                              # intrusion edges sort first
    assert (hot["source"], hot["events"], hot["intrusion_events"]) == ("185.1.1.1", 2, 2)
    nodes = {n["id"]: n for n in net["nodes"]}
    assert nodes["185.1.1.1"]["flagged"] and nodes["185.1.1.1"]["scope"] == "external"
    assert not nodes["10.0.0.6"]["flagged"] and nodes["10.0.0.6"]["scope"] == "internal"


def test_build_network_truncation_flag():
    events = [{"source_ip": f"10.0.0.{i}", "destination_ip": "10.0.1.1", "event_type": "x", "status": None} for i in range(10)]
    net = L.build_network(events, {}, edge_limit=4)
    assert net["truncated"] and len(net["edges"]) == 4


def test_timeline_open_incident_has_first_pending_stage_active():
    inc = {"id": "a", "title": "t", "status": "investigating", "severity": "high", "created_at": NOW}
    tl = L.build_timeline(inc, [{"status": "running", "created_at": NOW + timedelta(minutes=5)}], [])
    states = [s["state"] for s in tl["stages"]]
    assert states == ["done", "done", "active", "pending"]
    assert tl["stages"][2]["ts"] is None               # no approval => no invented timestamp


def test_timeline_resolved_uses_real_timestamps_only():
    inc = {"id": "a", "status": "resolved", "created_at": NOW, "updated_at": NOW + timedelta(hours=3)}
    inv = [{"status": "completed", "created_at": NOW + timedelta(minutes=2)}]
    apps = [{"status": "approved", "resolved_at": NOW + timedelta(hours=1)}]
    tl = L.build_timeline(inc, inv, apps)
    assert [s["state"] for s in tl["stages"]] == ["done"] * 4
    assert tl["stages"][3]["ts"] == (NOW + timedelta(hours=3)).isoformat()


def test_timeline_rejected_approval_and_failed_investigation_are_red():
    inc = {"id": "a", "status": "open", "created_at": NOW}
    rejected = L.build_timeline(inc, [{"status": "completed", "created_at": NOW}],
                                [{"status": "rejected", "resolved_at": NOW}])
    assert rejected["stages"][2]["state"] == "failed" and rejected["stages"][2]["ts"] is None
    failed = L.build_timeline(inc, [{"status": "failed", "created_at": NOW}], [])
    assert failed["stages"][1]["state"] == "failed"
    assert not any(s["state"] == "active" for s in failed["stages"])


def test_extract_flagged_indicators_keeps_reputation_verbatim():
    outputs = [{"enriched_indicators": [
        {"indicator": "1.2.3.4", "reputation": "simulated_malicious"},
        {"indicator": "5.6.7.8", "reputation": "clean"}]}, None, {"enriched_indicators": "bad"}]
    assert L.extract_flagged_indicators(outputs) == {"1.2.3.4": "simulated_malicious"}


def test_threat_sort_unresolved_then_severity_then_recent():
    items = [
        {"id": "r", "status": "resolved", "severity": "critical", "created_at": NOW},
        {"id": "m", "status": "open", "severity": "medium", "created_at": NOW},
        {"id": "c_old", "status": "open", "severity": "critical", "created_at": NOW - timedelta(days=1)},
        {"id": "c_new", "status": "open", "severity": "critical", "created_at": NOW},
    ]
    assert [i["id"] for i in sorted(items, key=L.threat_sort_key)] == ["c_new", "c_old", "m", "r"]


def test_audit_link_consistency():
    ok = [{"previous_hash": None, "current_hash": "a"}, {"previous_hash": "a", "current_hash": "b"}]
    assert L.audit_link_consistency(ok) == {"checked": 2, "broken_links": 0}
    broken = ok + [{"previous_hash": "zzz", "current_hash": "c"}]
    assert L.audit_link_consistency(broken)["broken_links"] == 1
