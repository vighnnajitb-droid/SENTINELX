"""Unit tests for the Command Center metric methodology (frontend/sentinelx_ui/metrics.py)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "frontend"))
from sentinelx_ui import components as C, metrics as M  # noqa: E402


def test_severity_index_is_weighted_mean_of_unresolved_scored():
    r = M.severity_index({"critical": 1, "high": 2, "low": 1}, unscored=3)
    assert r["available"] and r["value"] == round((100 + 150 + 25) / 4) and r["scored"] == 4
    assert r["unscored"] == 3 and "not a probability" in r["method"]


def test_severity_index_unavailable_not_zero():
    assert M.severity_index(None)["available"] is False
    r = M.severity_index({})
    assert r["available"] is False and "value" not in r


def test_severity_labels_cover_band_edges():
    assert M.severity_index({"low": 1})["label"] == "Low"
    assert M.severity_index({"medium": 1})["label"] == "Medium"
    assert M.severity_index({"high": 1})["label"] == "High"
    assert M.severity_index({"critical": 1})["label"] == "Critical"


def _srv(**status):
    ids = ["database", "agent_graph", "agent_mode", "audit_chain"]
    return [{"id": i, "label": i, "status": status.get(i, "ok")} for i in ids]


def test_health_all_ok_is_normal_100():
    h = M.health_score(_srv(), True, 200)
    assert (h["value"], h["state"]) == (100, "Normal")


def test_mock_mode_is_warning_never_normal():
    h = M.health_score(_srv(agent_mode="degraded"), True, 200)
    assert h["state"] == "Warning" and h["value"] < 100


def test_failed_check_is_degraded_and_db_failure_is_critical():
    assert M.health_score(_srv(audit_chain="fail"), True, 200)["state"] == "Degraded"
    assert M.health_score(_srv(database="fail"), True, 200)["state"] == "Critical"


def test_slow_api_lowers_score():
    fast = M.health_score(_srv(), True, 100)["value"]
    slow = M.health_score(_srv(), True, 2500)["value"]
    assert slow < fast


def test_unreachable_backend_is_measured_critical_not_healthy():
    h = M.health_score(None, False, None)
    assert h["available"] and h["value"] == 0 and h["state"] == "Critical"


def test_missing_health_endpoint_is_unavailable():
    h = M.health_score(None, True, 120)
    assert h["available"] is False


def test_fallback_summary_marks_underivable_metrics_none():
    d = M.derive_from_incidents([
        {"id": 1, "title": "a", "status": "open", "severity": "critical", "created_at": None},
        {"id": 2, "title": "b", "status": "resolved", "severity": "low", "created_at": None}])
    assert d["alerts"]["intrusion_attempts"] is None and d["alerts"]["pending_approvals"] is None
    assert d["incidents"]["resolved_today"] is None and d["incidents"]["unresolved_by_severity"] == {"critical": 1}


def test_series_values_accepts_backend_shape():
    assert M.series_values([{"date": "d", "count": 3}, {"date": "e", "count": 0}]) == [3, 0]
    assert M.series_values(None) is None


def test_components_escape_untrusted_text():
    html = C.sev_pill("<script>alert(1)</script>") + C.status_pill("<img src=x onerror=alert(1)>")
    assert "<script" not in html and "<img" not in html
    net = {"nodes": [{"id": "<b>x</b>", "scope": "unknown", "flagged": False, "reputation": None},
                     {"id": "10.0.0.1", "scope": "internal", "flagged": False, "reputation": None}],
           "edges": [{"source": "<b>x</b>", "target": "10.0.0.1", "events": 1, "intrusion_events": 0, "types": {}}]}
    assert "<b>x</b>" not in C.network_svg(net)


def test_unavailable_card_never_shows_a_number():
    html = C.alert_card("m", "Malware Detections", None, "events", None, "#fff", "blue", "No classifier")
    assert "Unavailable" in html and "0" not in html.split("sx-ac-val")[1].split("</div>")[0]


def test_html_blocks_have_no_blank_lines_or_code_indentation():
    for html in (C.severity_gauge({"available": True, "value": 50, "label": "Medium", "scored": 2}),
                 C.alert_grid({}), C.timeline(None, [("x", 1, 2)])):
        assert "\n" not in html


def test_timeline_counters_show_na_when_value_missing():
    html = C.timeline(None, [("Resolved Today", None, None), ("Active Incidents", 3, 10)])
    assert "n/a" in html and ">3<" in html


def test_network_distinguishes_unavailable_from_empty():
    assert "Network data unavailable" in C.network_svg(None)
    assert "No source/destination events" in C.network_svg({"nodes": [], "edges": []})


def test_gauge_caption_pluralises():
    one = C.health_gauge({"available": True, "value": 0, "state": "Critical", "checks": [{}]})
    assert "1 live check<" in one and "live checks" not in one
