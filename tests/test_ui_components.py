"""Smoke and safety tests for the shared widgets, charts and per-page views."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "frontend"))
from sentinelx_ui import charts, components as C, widgets as W  # noqa: E402
from sentinelx_ui.views import agents as VA, audit as VU, investigation as VI, logs as VL, risk as VR, reports as VP, settings as VS  # noqa: E402

XSS = '<img src=x onerror=alert(1)>'


def _safe(html):
    assert "<img" not in html and "onerror=alert" not in html.replace("&lt;img src=x onerror=alert(1)&gt;", "")


def test_widgets_escape_everything_that_comes_from_data():
    for html in (W.badge(XSS), W.status_badge(XSS), W.severity_badge(XSS), W.kpi(XSS, XSS, XSS), W.empty_state(XSS, XSS),
                 W.error_state(XSS, XSS), W.kv_grid([(XSS, XSS)]), W.json_block({XSS: XSS}), W.bullet_list([XSS]), W.chips([XSS]),
                 W.vtimeline([{"title": XSS, "time": XSS, "body": XSS}]), W.page_header(XSS, XSS)):
        _safe(html)
    _safe(W.expand_table([{"label": XSS}], [{"cells": [W.badge(XSS)], "detail": W.kv_grid([(XSS, XSS)])}]))


def test_charts_show_empty_states_instead_of_fake_shapes():
    assert "sx-state" in charts.bar_chart([]) and "sx-state" in charts.bar_chart([("a", 0)])
    assert "sx-state" in charts.donut([]) and "sx-state" in charts.radar([("a", 0)] * 4)
    assert "sx-state" in charts.line_chart([("s", [1], "#fff")], ["d1"])               # a trend needs two points
    assert "sx-state" in charts.line_chart([("s", [None, None], "#fff")], ["d1", "d2"])
    assert "sx-state" in charts.hbar_list([])


def test_charts_escape_labels_and_use_whole_number_ticks():
    for html in (charts.bar_chart([(XSS, 3)]), charts.hbar_list([(XSS, 3)]), charts.donut([(XSS, 3, "#fff")])):
        _safe(html)
    assert charts._nice_max(3) == 4 and charts._nice_max(37) == 40 and charts._nice_max(50) == 80 and charts._nice_max(4.2) == 8
    assert all(float(charts._nice_max(v) / 4).is_integer() for v in (5, 9, 17, 33, 99, 120, 1500))


def test_pipeline_marks_missing_agents_as_not_run():
    html = charts.pipeline_svg({"DetectionAgent": {"state": "completed", "detail": "ok"}})
    assert html.count(">not run</text>") == 5 and html.count(">completed</text>") == 1


def test_minify_preserves_pre_blocks_but_not_markdown_hostile_whitespace():
    out = C.minify("<div>\n   <b>x</b>\n\n</div>\n<pre>a\n  b\n\n c</pre>\n<p>z</p>")
    assert "<div><b>x</b></div>" in out and "a\n  b\n c" in out and "\n\n" not in out


def test_log_and_audit_and_agent_views_handle_empty_and_hostile_data():
    ev = {"id": XSS, "incident_id": "i", "incident_title": XSS, "incident_severity": "high", "timestamp": None, "event_type": XSS,
          "source_ip": XSS, "destination_ip": None, "user": XSS, "status": XSS, "message": XSS, "event_hash": XSS, "raw_data": {XSS: XSS}}
    _safe(VL.event_rows([ev]))
    assert "No events match" in VL.event_rows([])
    assert "Unavailable" in VL.kpis({"total": None})
    audit = {"id": XSS, "timestamp": None, "entity_type": XSS, "entity_id": XSS, "action": XSS, "actor": XSS, "incident_id": None,
             "incident_title": XSS, "previous_hash": None, "current_hash": XSS, "details": {XSS: XSS},
             "verification": {"status": "hash_mismatch", "reason": XSS}}
    html = VU.audit_table([audit])
    _safe(html)
    assert "Hash mismatch" in html and "critical" in html
    assert "failed backend verification" in VU.chain_banner({"checked": 5, "verified": 4, "hash_mismatch": 1})
    assert "No audit records exist" in VU.chain_banner({"checked": 0})
    assert "passed backend verification" in VU.chain_banner({"checked": 3, "verified": 3})


def test_agent_states_never_invent_results():
    assert all(s["state"] == "not_run" for s in VI.agent_states(None).values())
    running = VI.agent_states({"status": "running", "agent_runs": []})
    assert all(s["state"] == "pending" for s in running.values())
    failed = VI.agent_states({"status": "failed", "agent_runs": [{"agent_name": "DetectionAgent", "status": "completed", "duration_s": 2.0}]})
    assert failed["DetectionAgent"]["state"] == "completed" and failed["AuditAgent"]["state"] == "not_run"
    assert VI.progress_pct({"status": "failed", "agent_runs": [{"agent_name": "DetectionAgent", "status": "completed"}]}) == 100 / 6


def test_agent_cards_show_zero_state_for_agents_that_never_ran():
    stats = [{"name": n, "total_runs": 0, "completed": 0, "failed": 0, "last_run_at": None, "last_status": None, "avg_duration_s": None}
             for n in VA.ROLE]
    html = VA.agent_cards(stats)
    assert html.count("Not run yet") == 6 and html.count("never") == 6


def test_risk_views_only_chart_real_data_and_filter_correctly():
    assert "sx-state" in VR.trend_chart({"trend": [{"date": "2026-01-01", "avg_confidence": 0.5, "count": 1, "by_severity": {}}]})
    rows = [{"incident_id": "a", "severity": "high", "assessed": True, "confidence": 0.5},
            {"incident_id": "b", "severity": None, "assessed": False, "confidence": None},
            {"incident_id": "c", "severity": "low", "assessed": True, "confidence": 0.9}]
    assert [r["incident_id"] for r in VR.filter_rows(rows, [], True, "confidence")] == ["c", "a"]
    assert [r["incident_id"] for r in VR.filter_rows(rows, ["unscored"], False, "recent")] == ["b"]
    assert "Unavailable" in VR.kpis({"totals": {}, "distribution": {}, "avg_confidence": None})


def test_settings_never_prints_secrets_and_masks_credentials():
    assert VS.mask_url("https://user:hunter2@host.example.com:8443/api/v1") == "https://host.example.com:8443/api/v1"
    info = {"authentication": {"scheme": "s", "algorithm": "HS256", "token_lifetime_minutes": 30, "secret_key_configured": False,
                               "uses_default_secret_key": True, "bootstrap_admin_configured": True}}
    html = VS.authentication(info, "admin", None)
    assert "built-in default SECRET_KEY" in html and "hunter2" not in html
    assert "Not configured" in html
    guide = VS.guidance()
    assert "never displays secret values" in guide
