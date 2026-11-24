"""Single API client for the Streamlit frontend.

* one timeout policy, one auth header builder, one 401/403 policy
* per-session cache so widget reruns do not hit the backend again
  (the token never leaves st.session_state; nothing is shared across users)
* auto-refresh interval is enforced by the caller; ``MIN_REFRESH_SECONDS``
  prevents configuring a request storm.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
import streamlit as st

from . import metrics

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TIMEOUT = float(os.getenv("SENTINELX_API_TIMEOUT", "10"))
MIN_REFRESH_SECONDS = 15
DEDUPE_SECONDS = 10  # reruns within this window reuse the last response


@dataclass
class ApiResult:
    status: Optional[int]          # None => network failure
    data: Any = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None

    @property
    def reachable(self) -> bool:
        return self.status is not None

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300

    @property
    def unauthorized(self) -> bool:
        return self.status in (401, 403)


def auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {st.session_state.get('token', '')}"}


def get(path: str, params: Optional[Dict[str, Any]] = None) -> ApiResult:
    started = time.perf_counter()
    try:
        resp = requests.get(f"{API_URL}{path}", headers=auth_headers(), params=params, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return ApiResult(None, error=type(exc).__name__)
    latency = (time.perf_counter() - started) * 1000
    try:
        data = resp.json()
    except ValueError:
        data = None
    return ApiResult(resp.status_code, data, latency,
                     None if resp.ok else (data.get("detail") if isinstance(data, dict) else resp.reason))


def require_login() -> None:
    """Same gate every page used before: stop unless a token exists."""
    if not st.session_state.get("token"):
        st.warning("Please log in from the home page.")
        st.stop()


def end_session() -> None:
    st.session_state.pop("token", None)
    st.session_state.pop("_sx_cache", None)


def _cached(key: str, force: bool, fetch):
    cache = st.session_state.setdefault("_sx_cache", {})
    hit = cache.get(key)
    if hit and not force and time.time() - hit[0] < DEDUPE_SECONDS:
        return hit[1]
    value = fetch()
    cache[key] = (time.time(), value)
    return value


def load_dashboard(days: int = 14, force: bool = False) -> Dict[str, Any]:
    """Everything the Command Center needs in at most three requests."""
    def fetch() -> Dict[str, Any]:
        out: Dict[str, Any] = {"summary": None, "server_checks": None, "reachable": True,
                               "latency_ms": None, "auth_error": False, "errors": [],
                               "fallback": False, "fetched_at": time.time()}
        summary = get("/dashboard/summary", {"days": days})
        out["reachable"], out["latency_ms"] = summary.reachable, summary.latency_ms
        if summary.unauthorized:
            out["auth_error"] = True
            return out
        if summary.ok and isinstance(summary.data, dict):
            out["summary"] = summary.data
        elif summary.status == 404:  # older backend without the new endpoint
            legacy = get("/incidents")
            if legacy.unauthorized:
                out["auth_error"] = True
                return out
            if legacy.ok and isinstance(legacy.data, list):
                out["summary"], out["fallback"] = metrics.derive_from_incidents(legacy.data), True
                out["errors"].append("Backend has no /dashboard/summary; showing the subset derivable from /incidents.")
            else:
                out["errors"].append("Incident data could not be loaded.")
        elif not summary.reachable:
            out["errors"].append("Backend unreachable.")
        else:
            out["errors"].append(f"Dashboard summary failed (HTTP {summary.status}).")

        if out["reachable"]:
            health = get("/health")
            if health.unauthorized:
                out["auth_error"] = True
            elif health.ok and isinstance(health.data, dict):
                out["server_checks"] = health.data.get("checks")
        return out

    return _cached(f"dash:{days}", force, fetch)


# ---------------------------------------------------------------------------
# Generic helpers shared by every page
# ---------------------------------------------------------------------------
def fetch(path: str, params: Optional[Dict[str, Any]] = None, ttl: int = DEDUPE_SECONDS,
          force: bool = False) -> ApiResult:
    """Cached GET. Identical requests within ``ttl`` seconds reuse the stored
    response (per browser session). Failed responses are never cached."""
    key = "get:" + path + ":" + repr(sorted((params or {}).items()))
    cache = st.session_state.setdefault("_sx_cache", {})
    hit = cache.get(key)
    if hit and not force and time.time() - hit[0] < ttl:
        return hit[1]
    result = get(path, params)
    if result.ok:
        cache[key] = (time.time(), result)
    else:
        cache.pop(key, None)
    return result


def post(path: str, json_body: Optional[Dict[str, Any]] = None, files: Optional[Dict[str, Any]] = None,
         timeout: float = 60) -> ApiResult:
    started = time.perf_counter()
    try:
        resp = requests.post(f"{API_URL}{path}", headers=auth_headers(), json=json_body, files=files, timeout=timeout)
    except requests.RequestException as exc:
        return ApiResult(None, error=type(exc).__name__)
    try:
        data = resp.json()
    except ValueError:
        data = None
    detail = None
    if not resp.ok:
        detail = data.get("detail") if isinstance(data, dict) and data.get("detail") else (resp.text or resp.reason)[:300]
    return ApiResult(resp.status_code, data, (time.perf_counter() - started) * 1000, detail)


def invalidate() -> None:
    """Drop every cached response (call after a write such as an upload or approval)."""
    st.session_state.pop("_sx_cache", None)


def _jwt_claims() -> Dict[str, Any]:
    """Read (not verify) the payload of the session token for display only."""
    import base64
    import json
    token = st.session_state.get("token") or ""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload.encode()))
    except Exception:
        return {}


def username() -> str:
    return st.session_state.get("username") or _jwt_claims().get("sub") or "operator"


def session_expiry() -> Optional[float]:
    exp = _jwt_claims().get("exp")
    return float(exp) if isinstance(exp, (int, float)) else None


def incident_list(force: bool = False) -> ApiResult:
    return fetch("/incidents", ttl=20, force=force)
