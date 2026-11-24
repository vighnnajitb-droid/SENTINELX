"""Audit Trail: audit records with backend hash-chain verification.

Data: GET /audit (records + verification computed by the backend),
GET /incidents/{id}/investigations (Audit Agent report). Verification is never
claimed unless the backend actually computed it.
"""
import math

import streamlit as st

from sentinelx_ui import api
from sentinelx_ui.navigation import header, page_setup, show_api_error
from sentinelx_ui.views import audit as V
from sentinelx_ui.widgets import empty_state, notice, pager_text, section_title

page_setup("Audit Trail", "🧾")
header("Audit Trail", "Tamper-evident record of investigations, agent executions and approvals.",
       eyebrow="INTELLIGENCE / AUDIT TRAIL")

tab_records, tab_integrity = st.tabs(["Audit records", "Evidence integrity"])

with tab_records:
    base = api.fetch("/audit", {"page_size": 1}, ttl=20)
    if not base.ok:
        show_api_error(base, "the audit trail")
    summary = base.data["verification"]
    st.markdown(V.kpis(summary), unsafe_allow_html=True)
    st.markdown(V.chain_banner(summary), unsafe_allow_html=True)
    with st.expander("How verification works and its limits"):
        st.markdown(f'<div style="font-size:13px;color:var(--sx-text2)">{summary.get("method", "")}<br><br>{V.LIMITS}</div>', unsafe_allow_html=True)

    inc = api.incident_list()
    inc_labels = {i["id"]: f'{(i.get("severity") or "unscored").capitalize()} · {i.get("title") or "Untitled"}' for i in (inc.data or [])} if inc.ok else {}

    with st.form("au_form", border=True):
        r1 = st.columns([2.6, 1.6, 1.8, 1.8])
        q = r1[0].text_input("Search", key="au_q", placeholder="Actor, action, entity ID, incident title or hash…")
        etype = r1[1].selectbox("Entity type", ["All entity types"] + base.data.get("entity_types", []), key="au_et")
        ver = r1[2].selectbox("Verification", ["any", "verified", "linked", "broken_link", "hash_mismatch"], key="au_ver",
                              format_func=lambda s: "Any verification" if s == "any" else s.replace("_", " ").capitalize())
        incident = r1[3].selectbox("Incident", ["all"] + list(inc_labels), key="au_inc",
                                   format_func=lambda i: "All incidents" if i == "all" else inc_labels[i][:44])
        r2 = st.columns([2.6, 1.6, 1.8, 1.8])
        action = r2[0].text_input("Action contains", key="au_act", placeholder="e.g. started, approve, Agent")
        page_size = r2[1].selectbox("Rows per page", [25, 50, 100], key="au_ps")
        go = r2[2].form_submit_button("Apply filters", type="primary", use_container_width=True)
    if go:
        st.session_state["au_page"] = 1
    page = st.session_state.get("au_page", 1)

    params = {"page": page, "page_size": page_size}
    if q.strip():
        params["q"] = q.strip()
    if etype != "All entity types":
        params["entity_type"] = etype
    if ver != "any":
        params["verification"] = ver
    if incident != "all":
        params["incident_id"] = incident
    if action.strip():
        params["action"] = action.strip()

    with st.spinner("Loading audit records…"):
        res = api.fetch("/audit", params, ttl=15)
    if not res.ok:
        show_api_error(res, "audit records")
    d = res.data
    st.markdown(section_title("Audit event timeline", right_html=f'<span class="sx-muted">{pager_text(page, page_size, d["total"])}</span>'),
                unsafe_allow_html=True)
    st.markdown(V.audit_table(d["items"]), unsafe_allow_html=True)
    pages = max(1, math.ceil(d["total"] / page_size))
    nav = st.columns([1, 1, 5])
    if nav[0].button("← Previous", key="au_prev", disabled=page <= 1, use_container_width=True):
        st.session_state["au_page"] = page - 1
        st.rerun()
    if nav[1].button("Next →", key="au_next", disabled=page >= pages, use_container_width=True):
        st.session_state["au_page"] = page + 1
        st.rerun()
    nav[2].markdown(f'<div class="sx-pager">Page {page} of {pages}</div>', unsafe_allow_html=True)

with tab_integrity:
    if not inc_labels:
        st.markdown(empty_state("No incidents yet", "Evidence integrity is reported per incident."), unsafe_allow_html=True)
    else:
        pick = st.selectbox("Incident", list(inc_labels), key="au_int_pick", format_func=lambda i: inc_labels[i][:90])
        a = api.fetch("/audit", {"incident_id": pick, "page_size": 200}, ttl=15)
        v = api.fetch(f"/incidents/{pick}/investigations", ttl=15)
        if not a.ok:
            show_api_error(a, "audit records", stop=False)
        elif not v.ok:
            show_api_error(v, "investigation data", stop=False)
        else:
            latest = (v.data["investigations"] or [{}])[0]
            with st.container(key="sxp_au_integrity"):
                st.markdown(section_title("Evidence integrity", "Two independent sources are shown separately on purpose."), unsafe_allow_html=True)
                st.markdown(V.integrity_panel(latest, a.data), unsafe_allow_html=True)
