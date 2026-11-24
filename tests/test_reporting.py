"""Tests for frontend/sentinelx_ui/reporting.py: facts only, safe exports, graceful empties."""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "frontend"))
from sentinelx_ui import reporting as R  # noqa: E402

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
INCIDENT = {"id": "i1", "title": "Brute force <script>x</script>", "description": "d", "status": "investigating", "severity": "high",
            "created_at": "2026-11-21T10:00:00", "updated_at": "2026-11-21T11:00:00",
            "events": [{"type": "login", "source": "1.1.1.1", "destination": "10.0.0.1"},
                       {"type": "login", "source": "1.1.1.1", "destination": "10.0.0.2"},
                       {"type": "port_scan", "source": "2.2.2.2", "destination": "10.0.0.1"}]}
INV = {"id": "v1", "status": "completed", "summary": None, "confidence_score": 0.8, "created_at": "2026-11-21T10:05:00",
       "updated_at": "2026-11-21T10:09:00",
       "agent_runs": [
           {"agent_name": "DetectionAgent", "status": "completed", "completed_at": "2026-11-21T10:06:00", "duration_s": 3.0,
            "output_data": {"is_suspicious": True, "findings": ["repeated failures"]}},
           {"agent_name": "RiskAssessmentAgent", "status": "completed", "completed_at": "2026-11-21T10:07:00", "duration_s": 2.0,
            "output_data": {"severity": "high", "confidence_score": 0.82, "justification": "many failed logins"}}],
       "approvals": [{"action_type": "recommendation_approval", "status": "pending", "created_at": "2026-11-21T10:08:00", "resolved_at": None, "reason": "[]"}]}


def test_summary_contains_only_recorded_facts():
    r = R.build_report(INCIDENT, [INV], None, now=NOW)
    s = r["executive_summary"]
    assert "high severity" in s and "3 event(s)" in s and "login (2)" in s
    assert "confidence of 80%" in s and "flagged suspicious activity" in s
    assert "1 response approval(s) are awaiting" in s
    assert r["evidence"]["top_sources"][0] == ("1.1.1.1", 2)


def test_report_without_investigation_says_so_and_invents_nothing():
    r = R.build_report({**INCIDENT, "events": [], "severity": None}, [], None, now=NOW)
    assert "no assigned severity" in r["executive_summary"].lower()
    assert "No investigation has been run" in r["executive_summary"]
    assert r["investigation"] is None and r["risk"] is None and r["recommendations"] is None and r["agents"] == []
    md = R.to_markdown(r)
    assert "No investigation has been run." in md and "No risk assessment recorded." in md


def test_timeline_is_chronological_and_complete():
    r = R.build_report(INCIDENT, [INV], None, now=NOW)
    times = [t["time"] for t in r["timeline"]]
    assert times == sorted(times)
    titles = [t["title"] for t in r["timeline"]]
    assert titles[0] == "Incident created" and "Investigation started" in titles and "Investigation completed" in titles


def test_html_export_escapes_untrusted_content():
    html = R.to_html(R.build_report(INCIDENT, [INV], None, now=NOW))
    assert "<script>x</script>" not in html and "&lt;script&gt;" in html
    assert html.startswith("<!doctype html>") and "Executive summary" in html


def test_markdown_and_json_exports_roundtrip():
    import json
    r = R.build_report(INCIDENT, [INV], {"total": 4, "verification": {"verified": 3, "linked": 1}}, {"incident": {"title": "t"}}, now=NOW)
    md = R.to_markdown(r)
    assert md.startswith("# Incident Report:") and "## Audit" in md and "3 verified" in md
    assert json.loads(R.to_json(r))["api_report"] == {"incident": {"title": "t"}}
