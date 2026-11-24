"""SENTINELX Command Center.

Every number on this page comes from the backend:
    GET /api/v1/dashboard/summary   incident / event / approval aggregates
    GET /api/v1/health              live health checks
Anything that cannot be retrieved is rendered as an explicit "unavailable"
state. See sentinelx_ui/metrics.py for the documented index methodology.
"""
from datetime import datetime

import streamlit as st

from sentinelx_ui import api, components as C, metrics as M
from sentinelx_ui.navigation import page_setup

# A threat-row click stores the target and reruns the app; the page switch
# happens here, outside any fragment, so it works with auto-refresh on or off.
_goto = st.session_state.pop("_sx_goto", None)
if _goto:
    st.session_state["selected_incident_id"] = _goto
    st.switch_page("pages/3_Investigation_Center.py")

page_setup("Command Center", "🛡️", dashboard=True)

THREAT_ROWS = 4
REFRESH_CHOICES = [15, 30, 60, 120, 300]
AGENTS = [
    ("01", "Detection Agent", "Analyzes incoming security events and identifies suspicious activity.", "#35BFFF"),
    ("02", "Investigation Agent", "Connects evidence and builds incident investigation context.", "#A78BFA"),
    ("03", "Threat Intelligence Agent", "Enriches findings with available threat intelligence.", "#22D3EE"),
    ("04", "Risk Assessment Agent", "Evaluates severity, confidence and potential impact.", "#FBBF24"),
    ("05", "Audit Agent", "Maintains evidence records and accountability.", "#4ADE80"),
    ("06", "Response Agent", "Coordinates human-approved defensive response workflows.", "#FB923C"),
]


def md_safe(text, limit: int = 58) -> str:
    """Button labels render Markdown; neutralise it and truncate."""
    text = (text or "Untitled incident").replace("\n", " ")
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    for ch in "\\`*_{}[]()#+-!|~<>$":
        text = text.replace(ch, "\\" + ch)
    return text


def panel_title(title: str, info: str = "") -> None:
    tip = f'<span class="sx-info" title="{C.esc(info)}" tabindex="0">i</span>' if info else ""
    st.markdown(f'<div class="sx-ptitle">{C.esc(title)}{tip}</div>', unsafe_allow_html=True)


def go_to_incident(incident_id: str) -> None:
    st.session_state["_sx_goto"] = incident_id
    try:
        st.rerun(scope="app")
    except TypeError:       # Streamlit without fragment scopes
        st.rerun()


with st.container(key="sx_frame"):
    # ------------------------------------------------------------- top bar
    with st.container(key="sx_bar"):
        st.markdown('<div class="sx-brand" style="flex-direction:row;align-items:baseline;gap:12px"><b>SENTINEL<span>X</span> Command Center</b>'
                    '<small>Autonomous Incident Response Network</small></div>', unsafe_allow_html=True)

    with st.container(key="sx_filters"):
        f = st.columns([1.5, 1.3, 1.0, 0.9, 0.9, 0.9, 1.7])
        sev_filter = f[0].multiselect("Severity filter", ["critical", "high", "medium", "low"],
                                      key="sx_sev", placeholder="All severities", label_visibility="collapsed")
        status_filter = f[1].selectbox("Status filter", ["all", "open", "investigating", "resolved"], key="sx_status",
                                       label_visibility="collapsed",
                                       format_func=lambda s: "All statuses" if s == "all" else f"Status: {s}")
        days = f[2].selectbox("Trend window", [7, 14, 30], index=1, key="sx_days", label_visibility="collapsed",
                           format_func=lambda d: f"Last {d} days")
        auto = f[3].toggle("Auto-refresh", value=False, key="sx_auto",
                           help="Off by default. When on, only this dashboard re-fetches, at the chosen interval.")
        interval = f[4].selectbox("Every", REFRESH_CHOICES, index=1, key="sx_interval", disabled=not auto,
                                  label_visibility="collapsed",
                                  format_func=lambda s: f"Every {s}s" if s < 60 else f"Every {s // 60}m")
        refresh_clicked = f[5].button("↻ Refresh", key="sx_refresh", use_container_width=True)
        asof_slot = f[6].empty()

    if refresh_clicked:   # a manual refresh must always bypass the short dedupe cache
        st.session_state.pop("_sx_cache", None)

    def render_body() -> None:
        with st.spinner("Loading telemetry…"):
            data = api.load_dashboard(days)

        if data["auth_error"]:
            st.error("Your session has expired or this account lacks access. Please log in again.")
            if st.button("Return to Login", key="sx_relogin"):
                api.end_session()
                st.rerun()
            return

        summary = data["summary"] or {}
        inc, events = summary.get("incidents") or {}, summary.get("events") or {}
        asof_slot.markdown(
            f'<div class="sx-asof">Updated {datetime.fromtimestamp(data["fetched_at"]):%H:%M:%S}<br>'
            f'{"auto every " + str(interval) + "s" if auto else "manual refresh"}</div>', unsafe_allow_html=True)

        for msg in data["errors"]:
            st.markdown(f'<div class="sx-banner{" err" if not data["reachable"] else ""}">{C.esc(msg)}</div>',
                        unsafe_allow_html=True)
        if events.get("truncated"):
            st.markdown(f'<div class="sx-banner">Event-level metrics use the most recent {events.get("scanned", 0):,} '
                        f'of {events.get("total", 0):,} events.</div>', unsafe_allow_html=True)

        # ---------------------------------------------------- SECTION A
        with st.container(key="sx_secA"):
            a1, a2, a3 = st.columns([1.5, 1.0, 1.0])

            with a1, st.container(key="sx_p_timeline"):
                panel_title("Incident Response Timeline",
                            "Stages are derived from stored records: detection = incident created, analysis = first "
                            "investigation started, containment = approved response action, resolution = incident "
                            "resolved. A stage without a supporting record shows 'unavailable'.")
                timelines = summary.get("timelines") or []
                chosen = None
                if timelines:
                    ids = [t["incident_id"] for t in timelines]
                    default = next((i for i, t in enumerate(timelines) if t["status"] not in ("resolved", "closed")), 0)
                    labels = {t["incident_id"]: f'{(t["severity"] or "unscored").capitalize()} · {(t["title"] or "Untitled")[:44]}'
                              for t in timelines}
                    pick = st.selectbox("Incident", ids, index=default, key="sx_tl_pick",
                                        label_visibility="collapsed", format_func=lambda i: labels.get(i, i))
                    chosen = next((t for t in timelines if t["incident_id"] == pick), None)
                total = inc.get("total")
                st.markdown(C.timeline(chosen, [
                    ("Active Incidents", inc.get("active"), total),
                    ("Containment in Progress", inc.get("containment_in_progress"), total),
                    ("Resolved Today", inc.get("resolved_today"), total),
                    ("Escalated Cases", inc.get("escalated"), total)]), unsafe_allow_html=True)

            sev = M.severity_index(inc.get("unresolved_by_severity") if inc else None,
                                   inc.get("unscored_unresolved", 0))
            with a2, st.container(key="sx_p_sev"):
                panel_title("Threat Severity", sev["method"])
                st.markdown(C.severity_gauge(sev), unsafe_allow_html=True)
                if sev.get("unscored"):
                    st.caption(f'{sev["unscored"]} unresolved incident(s) without a severity are excluded.')

            health = M.health_score(data["server_checks"], data["reachable"], data["latency_ms"])
            with a3, st.container(key="sx_p_health"):
                panel_title("System Health", health["method"])
                st.markdown(C.health_gauge(health), unsafe_allow_html=True)
                chips = "".join(
                    f'<span class="sx-chip {C.esc(c["status"])}" title="{C.esc(c.get("detail", ""))}">'
                    f'<i></i>{C.esc(c["label"])}</span>' for c in health.get("checks", []))
                st.markdown(f'<div class="sx-chips">{chips}</div>', unsafe_allow_html=True)

        # ---------------------------------------------------- SECTION B
        with st.container(key="sx_secB"):
            b1, b2 = st.columns([1.12, 1.4])
            with b1, st.container(key="sx_p_net"):
                panel_title("Network Traffic",
                            "Source/destination pairs reconstructed from stored security events. Hosts are classified "
                            "internal/external by private IP ranges. Red marks hosts flagged by the threat-intel agent "
                            "and flows that contain intrusion-type events.")
                net = summary.get("network")
                st.markdown(C.network_svg(net), unsafe_allow_html=True)
                st.markdown(f'<div class="sx-netcap">{C.esc(C.network_caption(net) if summary else "Network data unavailable.")}</div>',
                            unsafe_allow_html=True)
            with b2, st.container(key="sx_p_alerts"):
                panel_title("Alert Statistics",
                            "Each card states its own unit. Sparklines show daily counts over the selected window (UTC).")
                st.markdown(C.alert_grid(summary), unsafe_allow_html=True)

        # ---------------------------------------------------- SECTION C
        with st.container(key="sx_secC"):
            c1, c2 = st.columns([1.0, 3.3])
            with c1:
                st.markdown(C.robot_img(), unsafe_allow_html=True)
            with c2, st.container(key="sx_threats"):
                ratios = [3.3, 2.2, 2.2, 1.1, 2.0]
                h = st.columns(ratios)
                h[0].markdown('<div class="sx-th t">Top Threats</div>', unsafe_allow_html=True)
                for col, name in zip(h[1:], ["Type", "Source", "Severity", "Status"]):
                    col.markdown(f'<div class="sx-th">{name}</div>', unsafe_allow_html=True)

                threats = summary.get("top_threats") or []
                if sev_filter:
                    threats = [t for t in threats if (t.get("severity") or "") in sev_filter]
                if status_filter != "all":
                    threats = [t for t in threats if t.get("status") == status_filter]

                if not summary:
                    st.markdown('<div class="sx-empty">Incident data unavailable.</div>', unsafe_allow_html=True)
                elif not threats:
                    st.markdown('<div class="sx-empty">No incidents match the current filters.</div>', unsafe_allow_html=True)
                for t in threats[:THREAT_ROWS]:
                    r = st.columns(ratios)
                    if r[0].button(f"▸ {md_safe(t.get('title'))}", key=f"sx_open_{t['id']}",
                                   help="Open in Investigation Center"):
                        go_to_incident(t["id"])
                    types = ", ".join(t.get("event_types") or []) or "Unclassified"
                    srcs = ", ".join(t.get("sources") or []) or "—"
                    r[1].markdown(f'<div class="sx-cell mut" title="{C.esc(types)}">{C.esc(types)}</div>', unsafe_allow_html=True)
                    r[2].markdown(f'<div class="sx-cell mut" title="{C.esc(srcs)}">{C.esc(srcs)}</div>', unsafe_allow_html=True)
                    r[3].markdown(C.sev_pill(t.get("severity")), unsafe_allow_html=True)
                    r[4].markdown(C.status_pill(t.get("status"), t.get("awaiting_approval")), unsafe_allow_html=True)
                if len(threats) > THREAT_ROWS:
                    st.caption(f"Showing {THREAT_ROWS} of {len(threats)} matching incidents. "
                               "Open the Investigation Center for the full list.")

    # A fragment means only the dashboard reruns on the timer, never the whole app.
    if auto and hasattr(st, "fragment"):
        st.fragment(render_body, run_every=max(int(interval), api.MIN_REFRESH_SECONDS))()
    else:
        if auto:
            st.caption("Auto-refresh needs Streamlit 1.37 or newer.")
        render_body()

# ------------------------------------------------------ six-agent network
st.markdown('<div class="section-heading" style="margin-top:18px">Autonomous AI Agent Network</div>'
            '<div class="section-caption">Six specialized agents coordinate the defensive incident response workflow</div>',
            unsafe_allow_html=True)
agent_cols = st.columns(3)
for index, (number, name, description, color) in enumerate(AGENTS):
    with agent_cols[index % 3]:
        st.markdown(
            f'<div class="agent-card"><div class="agent-number" style="color:{color}">AGENT / {number}</div>'
            f'<div class="agent-title">{name}</div><div class="agent-desc">{description}</div></div>',
            unsafe_allow_html=True)

st.markdown('<div class="footer">SENTINELX · human-in-the-loop defensive response · '
            'all metrics are read from the live backend</div>', unsafe_allow_html=True)
