"""Reusable, pure HTML widgets shared by every page (no Streamlit imports).

Rules: any text that originates from data is escaped here with ``esc``; callers
pass plain strings, never pre-built markup, except where a parameter is named
``*_html``. Output is minified for Markdown safety.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .components import esc, minify

# ---------------------------------------------------------------- tone maps
SEVERITY_TONE = {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}
STATUS_TONE = {
    # investigations
    "pending": "muted", "running": "info", "completed": "ok", "failed": "critical", "awaiting_review": "medium",
    # incidents
    "open": "medium", "investigating": "info", "resolved": "ok", "closed": "ok",
    # approvals
    "approved": "ok", "rejected": "critical",
    # audit verification
    "verified": "ok", "linked": "info", "broken_link": "critical", "hash_mismatch": "critical",
    # agent runs / generic
    "error": "critical", "ok": "ok", "degraded": "medium", "fail": "critical", "not_run": "muted",
}
STATUS_LABEL = {"awaiting_review": "Awaiting review", "broken_link": "Broken link", "hash_mismatch": "Hash mismatch",
                "not_run": "Not run", "fail": "Failed", "ok": "OK"}


def badge(text: Any, tone: str = "muted", dot: bool = True, title: str = "") -> str:
    t = f' title="{esc(title)}"' if title else ""
    return f'<span class="sx-badge {esc(tone)}"{t}>{"<i></i>" if dot else ""}{esc(text)}</span>'


def severity_badge(severity: Optional[str]) -> str:
    s = (severity or "").lower()
    if s not in SEVERITY_TONE:
        return badge("Unscored", "muted", dot=False)
    return badge(s.capitalize(), SEVERITY_TONE[s], dot=False)


def status_badge(status: Optional[str]) -> str:
    s = (status or "").lower()
    if not s:
        return badge("Unknown", "muted")
    return badge(STATUS_LABEL.get(s, s.replace("_", " ").capitalize()), STATUS_TONE.get(s, "muted"))


# ------------------------------------------------------------------ headers
def page_header(title: str, subtitle: str = "", eyebrow: str = "", right_html: str = "") -> str:
    return minify(
        f'<div class="sx-ph"><div><div class="sx-eyebrow">{esc(eyebrow or "SENTINELX")}</div>'
        f'<h1>{esc(title)}</h1>{f"<p>{esc(subtitle)}</p>" if subtitle else ""}</div>'
        f'{f"<div class=sx-ph-right>{right_html}</div>" if right_html else ""}</div>')


def section_title(title: str, info: str = "", right_html: str = "") -> str:
    tip = f'<span class="sx-info" title="{esc(info)}" tabindex="0">i</span>' if info else ""
    return minify(f'<div class="sx-ptitle">{esc(title)}{tip}'
                  f'{f"<span class=sx-ptr>{right_html}</span>" if right_html else ""}</div>')


# --------------------------------------------------------------- KPI cards
def kpi(label: str, value: Any, sub: str = "", tone: str = "blue", unavailable: str = "",
        spark_html: str = "") -> str:
    if value is None:
        body = f'<div class="sx-kv-val na">Unavailable</div><div class="sx-kv-sub">{esc(unavailable or "No data")}</div>'
    else:
        shown = f"{value:,}" if isinstance(value, int) and not isinstance(value, bool) else esc(value)
        long_text = isinstance(value, str) and len(value) > 9
        body = f'<div class="sx-kv-val{" txt" if long_text else ""}">{shown}</div>{f"<div class=sx-kv-sub>{esc(sub)}</div>" if sub else ""}'
    return (f'<div class="sx-kpi {esc(tone)}" tabindex="0"><div class="sx-kv-label">{esc(label)}</div>'
            f'{body}{f"<div class=sx-kv-spark>{spark_html}</div>" if spark_html else ""}</div>')


def kpi_row(cards: Sequence[str]) -> str:
    return f'<div class="sx-kpis" style="--n:{len(cards)}">{"".join(cards)}</div>'


# ------------------------------------------------------------ state panels
def empty_state(title: str, message: str = "", icon: str = "◌") -> str:
    return minify(f'<div class="sx-state empty"><div class="ic">{esc(icon)}</div><b>{esc(title)}</b>'
                  f'{f"<span>{esc(message)}</span>" if message else ""}</div>')


def error_state(title: str, message: str = "") -> str:
    return minify(f'<div class="sx-state error" role="alert"><div class="ic">!</div><b>{esc(title)}</b>'
                  f'{f"<span>{esc(message)}</span>" if message else ""}</div>')


def notice(text: str, tone: str = "info") -> str:
    return f'<div class="sx-notice {esc(tone)}">{esc(text)}</div>'


# ----------------------------------------------------------- key/value + json
def kv_grid(pairs: Iterable[tuple], columns: int = 2) -> str:
    cells = []
    for label, value in pairs:
        shown = esc(value) if value not in (None, "") else '<span class="na">unavailable</span>'
        cells.append(f'<div class="sx-kvc"><span>{esc(label)}</span><b>{shown}</b></div>')
    return f'<div class="sx-kvg" style="--c:{columns}">{"".join(cells)}</div>'


def kv_grid_html(pairs: Iterable[tuple], columns: int = 2) -> str:
    """Like kv_grid but values are trusted HTML (badges etc.)."""
    cells = [f'<div class="sx-kvc"><span>{esc(l)}</span><b>{v}</b></div>' for l, v in pairs]
    return f'<div class="sx-kvg" style="--c:{columns}">{"".join(cells)}</div>'


def json_block(data: Any, limit: int = 6000) -> str:
    try:
        text = json.dumps(data, indent=2, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(data)
    suffix = "\n… (truncated)" if len(text) > limit else ""
    return f'<pre class="sx-json">{esc(text[:limit] + suffix)}</pre>'


def bullet_list(items: Iterable[Any], empty: str = "None reported") -> str:
    items = [i for i in items if i not in (None, "")]
    if not items:
        return f'<div class="sx-muted">{esc(empty)}</div>'
    return "<ul class=sx-ul>" + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>"


def chips(items: Iterable[Any], tone: str = "muted") -> str:
    return "".join(f'<span class="sx-chip2 {esc(tone)}">{esc(i)}</span>' for i in items if i not in (None, ""))


def progress(pct: float, tone: str = "blue", label: str = "") -> str:
    pct = max(0.0, min(100.0, pct))
    return (f'<div class="sx-prog {esc(tone)}" role="progressbar" aria-valuenow="{pct:.0f}" aria-valuemin="0" aria-valuemax="100">'
            f'<u style="width:{pct:.0f}%"></u></div>{f"<div class=sx-prog-l>{esc(label)}</div>" if label else ""}')


# ------------------------------------------------------- expandable table
def expand_table(columns: Sequence[Dict[str, Any]], rows: Sequence[Dict[str, Any]], empty: str = "No records",
                 template: Optional[str] = None) -> str:
    """Expandable rows built from <details>, no server round-trip needed.

    columns: [{"label": str, "width": "1.2fr"}]
    rows:    [{"cells": [html, ...], "detail": html, "tone": optional css modifier}]
    Cells and detail are trusted HTML; build them with esc()/badge()/kv_grid().
    """
    tpl = template or " ".join(c.get("width", "1fr") for c in columns)
    head = "".join(f'<span>{esc(c["label"])}</span>' for c in columns)
    if not rows:
        return minify(f'<div class="sx-xt"><div class="sx-xt-head" style="--tpl:28px {tpl}"><i></i>{head}</div>'
                      f'<div class="sx-xt-empty">{esc(empty)}</div></div>')
    body = []
    for row in rows:
        cells = "".join(f"<span>{c}</span>" for c in row["cells"])
        tone = f" {esc(row['tone'])}" if row.get("tone") else ""
        detail = row.get("detail")
        if detail:
            body.append(f'<details class="sx-xr{tone}"><summary style="--tpl:28px {tpl}"><i class="car"></i>{cells}</summary>'
                        f'<div class="sx-xd">{detail}</div></details>')
        else:
            body.append(f'<div class="sx-xr flat{tone}"><div class="sum" style="--tpl:28px {tpl}"><i></i>{cells}</div></div>')
    return minify(f'<div class="sx-xt"><div class="sx-xt-head" style="--tpl:28px {tpl}"><i></i>{head}</div>{"".join(body)}</div>')


# ---------------------------------------------------------- vertical timeline
def vtimeline(items: Sequence[Dict[str, Any]], empty: str = "No recorded activity") -> str:
    """items: {"title", "time", "state": done|active|failed|pending|info, "body"(optional text), "badge_html"}"""
    if not items:
        return empty_state(empty)
    out = []
    for it in items:
        body = f'<div class="b">{esc(it["body"])}</div>' if it.get("body") else ""
        out.append(
            f'<div class="sx-vt {esc(it.get("state", "done"))}"><span class="d"></span><div class="c">'
            f'<div class="t"><b>{esc(it["title"])}</b>{it.get("badge_html", "")}</div>'
            f'<div class="m">{esc(it.get("time") or "time unavailable")}</div>{body}</div></div>')
    return f'<div class="sx-vts">{"".join(out)}</div>'


def pager_text(page: int, page_size: int, total: int) -> str:
    if total == 0:
        return "No results"
    first = (page - 1) * page_size + 1
    last = min(page * page_size, total)
    return f"Showing {first:,}–{last:,} of {total:,}"


def short(text: Optional[str], n: int = 10) -> str:
    return (text or "")[:n]


# ------------------------------------------------------------------ formatters
def fmt_ts(value: Optional[str]) -> str:
    """ISO timestamp -> 'YYYY-MM-DD HH:MM:SS' (UTC as stored); 'unavailable' when missing."""
    if not value:
        return "unavailable"
    return str(value).replace("T", " ").split(".")[0].replace("Z", "")


def fmt_dur(seconds: Optional[float]) -> str:
    if seconds is None:
        return "—"
    if seconds < 1:
        return "<1s"
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s" if m < 60 else f"{m // 60}h {m % 60:02d}m"


def fmt_pct(value: Optional[float]) -> str:
    return f"{value * 100:.0f}%" if isinstance(value, (int, float)) else "—"
