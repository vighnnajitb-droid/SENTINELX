"""Risk Assessment: risk distribution, confidence and per-incident risk details.

Data: GET /risk/overview (RiskAssessmentAgent output per incident plus supporting
evidence from the other agents). Charts are drawn only from recorded data.
"""
import streamlit as st

from sentinelx_ui import api
from sentinelx_ui.navigation import header, page_setup, show_api_error
from sentinelx_ui.views import risk as V
from sentinelx_ui.widgets import section_title

page_setup("Risk Assessment", "⚠️")
header("Risk Assessment", "Severity, confidence and supporting evidence for every assessed incident.",
       eyebrow="INTELLIGENCE / RISK ASSESSMENT")

f = st.columns([1.6, 1.3, 1.5, 1])
window = f[3].selectbox("Trend window", [7, 14, 30, 90], index=2, key="ra_days", label_visibility="collapsed",
                        format_func=lambda d: f"Trend: last {d} days")
if f[2].button("↻ Refresh", key="ra_refresh", use_container_width=False):
    api.invalidate()

res = api.fetch("/risk/overview", {"days": window}, ttl=15)
if not res.ok:
    show_api_error(res, "risk assessments")
ov = res.data

st.markdown(V.kpis(ov), unsafe_allow_html=True)
dist = V.distribution(ov)
c1, c2, c3 = st.columns([1.7, 1, 0.9])
with c1, st.container(key="sxp_ra_dist"):
    st.markdown(section_title("Severity distribution", "Incidents by the severity assigned by the Risk Assessment Agent."), unsafe_allow_html=True)
    d1, d2 = st.columns([1, 1])
    d1.markdown(dist["donut"], unsafe_allow_html=True)
    d2.markdown(dist["radar"], unsafe_allow_html=True)
with c2, st.container(key="sxp_ra_conf"):
    st.markdown(section_title("Confidence distribution", "Number of assessments per confidence band."), unsafe_allow_html=True)
    st.markdown(V.confidence_chart(ov), unsafe_allow_html=True)
with c3, st.container(key="sxp_ra_gauge"):
    st.markdown(section_title("Average confidence", V.CONF_METHOD), unsafe_allow_html=True)
    st.markdown(V.confidence_gauge(ov.get("avg_confidence")), unsafe_allow_html=True)

t1, t2 = st.columns(2)
with t1, st.container(key="sxp_ra_trend"):
    st.markdown(section_title("Confidence trend", "Daily mean confidence of assessments made in the selected window."), unsafe_allow_html=True)
    st.markdown(V.trend_chart(ov), unsafe_allow_html=True)
with t2, st.container(key="sxp_ra_counts"):
    st.markdown(section_title("Assessments over time", "Assessments recorded per day, and how many were high or critical."), unsafe_allow_html=True)
    st.markdown(V.counts_chart(ov), unsafe_allow_html=True)

st.markdown(section_title("Incident risk register"), unsafe_allow_html=True)
g = st.columns([1.8, 1.2, 1.4, 2])
sev = g[0].multiselect("Severity", ["critical", "high", "medium", "low", "unscored"], key="ra_sev", placeholder="All severities",
                       label_visibility="collapsed")
sort = g[1].selectbox("Sort", ["recent", "severity", "confidence"], key="ra_sort", label_visibility="collapsed",
                      format_func=lambda s: {"recent": "Most recent", "severity": "Highest severity", "confidence": "Highest confidence"}[s])
only = g[2].toggle("Assessed only", value=False, key="ra_only")
rows = V.filter_rows(ov["incidents"], sev, only, sort)
st.markdown(V.risk_table(rows[:100]), unsafe_allow_html=True)
if len(rows) > 100:
    st.caption(f"Showing the first 100 of {len(rows)} incidents.")

if rows:
    pick = st.columns([3, 1.4])
    labels = {r["incident_id"]: f'{(r.get("severity") or "unscored").capitalize()} · {r.get("title") or "Untitled"}' for r in rows[:100]}
    chosen = pick[0].selectbox("Open an incident", list(labels), key="ra_pick", format_func=lambda i: labels[i][:80],
                               label_visibility="collapsed")
    if pick[1].button("Open in Investigation Center", key="ra_open", use_container_width=True, icon=":material/arrow_forward:"):
        st.session_state["selected_incident_id"] = chosen
        st.switch_page("pages/3_Investigation_Center.py")
