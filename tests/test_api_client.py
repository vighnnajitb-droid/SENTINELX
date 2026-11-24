"""Integration tests for frontend/sentinelx_ui/api.py against a real local HTTP server.

Streamlit is replaced by a minimal stand-in exposing only ``session_state``; the
code under test (requests, headers, caching, error/fallback handling) is real."""
import json
import os
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "frontend"))
if "streamlit" not in sys.modules:
    fake = types.ModuleType("streamlit")
    fake.session_state = {}
    sys.modules["streamlit"] = fake
import streamlit as st  # noqa: E402

HITS = {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        HITS[path] = HITS.get(path, 0) + 1
        if self.headers.get("Authorization") != "Bearer good-token":
            return self._send(401, {"detail": "Could not validate credentials"})
        routes = {
            "/api/v1/events": {"items": [], "total": 0},
            "/api/v1/incidents": [{"id": "1", "title": "t", "status": "open", "severity": "critical", "created_at": None},
                                  {"id": "2", "title": "u", "status": "resolved", "severity": "low", "created_at": None}],
            "/api/v1/health": {"checks": [{"id": "database", "label": "Database", "status": "ok"}]},
            "/api/v1/boom": None,
        }
        if path == "/api/v1/boom":
            return self._send(500, {"detail": "database exploded"})
        if path in routes:
            return self._send(200, routes[path])
        self._send(404, {"detail": "Not Found"})   # note: /dashboard/summary is deliberately absent

    def do_POST(self):
        HITS[self.path] = HITS.get(self.path, 0) + 1
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/v1/approvals/inv1":
            return self._send(200, {"ok": True, "echo": body})
        self._send(400, {"detail": "No events to investigate"})


def _start():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _api(port):
    os.environ["API_URL"] = f"http://127.0.0.1:{port}/api/v1"
    for m in [k for k in sys.modules if k.startswith("sentinelx_ui")]:
        del sys.modules[m]
    from sentinelx_ui import api
    return api


def test_authenticated_fetch_cache_and_errors():
    server = _start()
    try:
        api = _api(server.server_port)
        st.session_state.clear()
        st.session_state["token"] = "good-token"
        HITS.clear()
        r1 = api.fetch("/events", {"page": 1})
        r2 = api.fetch("/events", {"page": 1})            # served from the per-session cache
        assert r1.ok and r2.ok and HITS["/api/v1/events"] == 1
        api.fetch("/events", {"page": 2})                 # different params => new request
        assert HITS["/api/v1/events"] == 2
        api.fetch("/events", {"page": 1}, force=True)     # force bypasses the cache
        assert HITS["/api/v1/events"] == 3

        bad = api.fetch("/boom")
        assert bad.status == 500 and bad.error == "database exploded" and not bad.ok
        HITS.clear()
        api.fetch("/boom"); api.fetch("/boom")            # failures are never cached
        assert HITS["/api/v1/boom"] == 2

        missing = api.get("/nope")
        assert missing.status == 404 and missing.reachable
        api.invalidate()
        assert "_sx_cache" not in st.session_state
    finally:
        server.shutdown()


def test_expired_or_missing_token_is_flagged_unauthorized():
    server = _start()
    try:
        api = _api(server.server_port)
        st.session_state.clear()
        st.session_state["token"] = "stale"
        res = api.get("/incidents")
        assert res.unauthorized and res.status == 401
        data = api.load_dashboard(14, force=True)
        assert data["auth_error"] is True and data["summary"] is None
    finally:
        server.shutdown()


def test_dashboard_falls_back_to_incidents_when_summary_endpoint_is_missing():
    server = _start()
    try:
        api = _api(server.server_port)
        st.session_state.clear()
        st.session_state["token"] = "good-token"
        d = api.load_dashboard(14, force=True)
        assert d["fallback"] is True and d["reachable"] is True
        assert d["summary"]["incidents"]["total"] == 2 and d["summary"]["alerts"]["intrusion_attempts"] is None
        assert d["server_checks"] and d["server_checks"][0]["id"] == "database"
        assert any("subset derivable" in e for e in d["errors"])
    finally:
        server.shutdown()


def test_post_reports_backend_detail_and_sends_json():
    server = _start()
    try:
        api = _api(server.server_port)
        st.session_state.clear()
        st.session_state["token"] = "good-token"
        ok = api.post("/approvals/inv1", {"action": "approve"})
        assert ok.ok and ok.data["echo"] == {"action": "approve"}
        failed = api.post("/investigations/inc9/run")
        assert failed.status == 400 and failed.error == "No events to investigate"
    finally:
        server.shutdown()


def test_unreachable_backend_is_reported_not_raised():
    api = _api(1)                                          # nothing listens on port 1
    st.session_state.clear()
    st.session_state["token"] = "good-token"
    res = api.get("/incidents")
    assert res.status is None and not res.reachable and not res.ok
    d = api.load_dashboard(14, force=True)
    assert d["reachable"] is False and d["summary"] is None and "Backend unreachable." in d["errors"]


def test_username_and_session_expiry_from_token_claims():
    import base64
    api = _api(1)
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "analyst", "exp": 1900000000}).encode()).decode().rstrip("=")
    st.session_state.clear()
    st.session_state["token"] = f"h.{payload}.s"
    assert api.username() == "analyst" and api.session_expiry() == 1900000000.0
    st.session_state["username"] = "chosen"
    assert api.username() == "chosen"
    st.session_state.clear()
    assert api.username() == "operator" and api.session_expiry() is None
