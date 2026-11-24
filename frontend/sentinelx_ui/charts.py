"""Pure SVG/HTML charts (no Streamlit/Plotly dependency).

Every chart takes real data and returns markup; with no data it returns an
explicit empty state instead of drawing placeholder shapes. Labels are escaped.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .components import COLORS, esc, minify
from .widgets import empty_state

PALETTE = ["#00A8FF", "#00D9FF", "#25E58A", "#FFB547", "#FF643D", "#FF303D", "#8B7CFF", "#35C7D5"]
SEV_COLORS = {"critical": "#FF303D", "high": "#FF643D", "medium": "#FFB547", "low": "#35C7D5", "unscored": "#6F829F"}


def _nice_max(value: float) -> float:
    """Axis maximum such that 4 equal grid intervals fall on whole, readable numbers."""
    if value <= 4:
        return 4.0
    unit = 10 ** math.floor(math.log10(value / 4))
    for step in (1, 2, 5, 10):
        if 4 * step * unit >= value:
            return 4.0 * step * unit
    return 40.0 * unit


def _fmt(v: float) -> str:
    return f"{v:,.0f}" if abs(v - round(v)) < 1e-9 else f"{v:,.2f}"


# ---------------------------------------------------------------- bar chart
def bar_chart(items: Sequence[Tuple[str, float]], uid: str = "bc", color: str = "#00A8FF",
              height: int = 190, empty: str = "No data in this range", width: int = 520) -> str:
    items = [(str(l), float(v)) for l, v in items]
    if not items or all(v == 0 for _, v in items):
        return empty_state(empty, icon="▁")
    W, H, pl, pr, pt, pb = width, height, 36, 8, 10, 26
    top = _nice_max(max(v for _, v in items))
    iw, ih = W - pl - pr, H - pt - pb
    n = len(items)
    slot = iw / n
    bw = max(3.0, min(34.0, slot * 0.62))
    parts = [f'<svg class="sx-chart" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" role="img">'
             f'<defs><linearGradient id="{uid}g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{color}"/>'
             f'<stop offset="1" stop-color="{color}" stop-opacity=".25"/></linearGradient></defs>']
    for i in range(5):
        y = pt + ih - ih * i / 4
        parts.append(f'<line x1="{pl}" x2="{W - pr}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>'
                     f'<text x="{pl - 6}" y="{y + 3:.1f}" text-anchor="end" class="ax">{_fmt(top * i / 4)}</text>')
    step = max(1, math.ceil(n / 10))
    for i, (label, value) in enumerate(items):
        x = pl + slot * i + (slot - bw) / 2
        h = ih * value / top
        parts.append(f'<g class="bar"><title>{esc(label)}: {_fmt(value)}</title>'
                     f'<rect x="{x:.1f}" y="{pt + ih - h:.1f}" width="{bw:.1f}" height="{max(h, 0):.1f}" rx="2" fill="url(#{uid}g)"/></g>')
        if i % step == 0:
            parts.append(f'<text x="{x + bw / 2:.1f}" y="{H - 8}" text-anchor="middle" class="ax">{esc(label[-5:] if len(label) > 8 else label)}</text>')
    parts.append("</svg>")
    return minify("".join(parts))


# ------------------------------------------------------ horizontal bar list
def hbar_list(items: Sequence[Tuple[str, float]], colors: Optional[Dict[str, str]] = None, limit: int = 8,
              empty: str = "No data") -> str:
    items = [(str(l), float(v)) for l, v in items if v]
    if not items:
        return empty_state(empty, icon="▤")
    items = sorted(items, key=lambda x: -x[1])[:limit]
    top = max(v for _, v in items)
    rows = []
    for i, (label, value) in enumerate(items):
        color = (colors or {}).get(label.lower()) or PALETTE[i % len(PALETTE)]
        rows.append(f'<div class="sx-hb" title="{esc(label)}: {_fmt(value)}"><span class="l">{esc(label)}</span>'
                    f'<span class="b"><u style="width:{value / top * 100:.0f}%;background:{color}"></u></span>'
                    f'<em>{_fmt(value)}</em></div>')
    return f'<div class="sx-hbs">{"".join(rows)}</div>'


# -------------------------------------------------------------------- donut
def donut(segments: Sequence[Tuple[str, float, str]], center_value: Any = None, center_label: str = "",
          empty: str = "No data") -> str:
    segs = [(str(l), float(v), c) for l, v, c in segments if v and v > 0]
    total = sum(v for _, v, _ in segs)
    if total <= 0:
        return empty_state(empty, icon="◔")
    cx = cy = 80
    r, w = 62, 18
    parts = ['<svg class="sx-donut" viewBox="0 0 160 160" role="img">',
             f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#0e1f3a" stroke-width="{w}"/>']
    angle = -90.0
    for label, value, color in segs:
        sweep = 360 * value / total
        if len(segs) == 1:
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{w}"><title>{esc(label)}: {_fmt(value)}</title></circle>')
        else:
            a0, a1 = math.radians(angle + 0.8), math.radians(angle + sweep - 0.8)
            x0, y0, x1, y1 = cx + r * math.cos(a0), cy + r * math.sin(a0), cx + r * math.cos(a1), cy + r * math.sin(a1)
            parts.append(f'<path d="M{x0:.2f} {y0:.2f}A{r} {r} 0 {1 if sweep > 180 else 0} 1 {x1:.2f} {y1:.2f}" fill="none" '
                         f'stroke="{color}" stroke-width="{w}"><title>{esc(label)}: {_fmt(value)} ({value / total:.0%})</title></path>')
        angle += sweep
    if center_value is not None:
        parts.append(f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" class="dv">{esc(center_value)}</text>'
                     f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" class="dl">{esc(center_label)}</text>')
    parts.append("</svg>")
    legend = "".join(f'<span class="lg"><i style="background:{c}"></i>{esc(l)} <b>{_fmt(v)}</b></span>' for l, v, c in segs)
    return f'<div class="sx-donut-wrap">{"".join(parts)}<div class="sx-legend">{legend}</div></div>'


# --------------------------------------------------------------- line chart
def line_chart(series: Sequence[Tuple[str, Sequence[Optional[float]], str]], labels: Sequence[str], uid: str = "lc",
               height: int = 190, ymax: Optional[float] = None, percent: bool = False,
               empty: str = "Not enough history to draw a trend") -> str:
    labels = [str(l) for l in labels]
    if len(labels) < 2 or not any(v is not None for _, vals, _ in series for v in vals):
        return empty_state(empty, "A trend needs at least two time points of real data.", icon="⌁")
    W, H, pl, pr, pt, pb = 520, height, 40, 10, 12, 26
    top = ymax if ymax is not None else _nice_max(max(v for _, vals, _ in series for v in vals if v is not None))
    iw, ih = W - pl - pr, H - pt - pb
    n = len(labels)
    xs = [pl + iw * i / (n - 1) for i in range(n)]
    parts = [f'<svg class="sx-chart" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" role="img"><defs>']
    for k, (_, _, color) in enumerate(series):
        parts.append(f'<linearGradient id="{uid}{k}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{color}" stop-opacity=".35"/>'
                     f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient>')
    parts.append("</defs>")
    for i in range(5):
        y = pt + ih - ih * i / 4
        val = top * i / 4
        parts.append(f'<line x1="{pl}" x2="{W - pr}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>'
                     f'<text x="{pl - 6}" y="{y + 3:.1f}" text-anchor="end" class="ax">{f"{val:.0%}" if percent else _fmt(val)}</text>')
    step = max(1, math.ceil(n / 8))
    for i, label in enumerate(labels):
        if i % step == 0:
            parts.append(f'<text x="{xs[i]:.1f}" y="{H - 8}" text-anchor="middle" class="ax">{esc(label[-5:])}</text>')
    for k, (name, vals, color) in enumerate(series):
        pts = [(xs[i], pt + ih - ih * (v / top)) for i, v in enumerate(vals) if v is not None]
        if len(pts) >= 2:
            path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            parts.append(f'<polygon points="{pts[0][0]:.1f},{pt + ih} {path} {pts[-1][0]:.1f},{pt + ih}" fill="url(#{uid}{k})"/>'
                         f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>')
        for i, v in enumerate(vals):
            if v is not None:
                parts.append(f'<circle cx="{xs[i]:.1f}" cy="{pt + ih - ih * (v / top):.1f}" r="3.2" fill="{color}" class="pt">'
                             f'<title>{esc(name)} · {esc(labels[i])}: {f"{v:.0%}" if percent else _fmt(v)}</title></circle>')
    parts.append("</svg>")
    legend = "".join(f'<span class="lg"><i style="background:{c}"></i>{esc(n_)}</span>' for n_, _, c in series)
    return minify("".join(parts)) + f'<div class="sx-legend row">{legend}</div>'


# -------------------------------------------------------------------- radar
def radar(axes: Sequence[Tuple[str, float]], color: str = "#FF643D", empty: str = "No data") -> str:
    axes = [(str(l), float(v)) for l, v in axes]
    if len(axes) < 3 or all(v == 0 for _, v in axes):
        return empty_state(empty, icon="✦")
    top = _nice_max(max(v for _, v in axes))
    cx, cy, R = 160, 112, 74
    n = len(axes)
    pt = lambda i, frac: (cx + R * frac * math.sin(2 * math.pi * i / n), cy - R * frac * math.cos(2 * math.pi * i / n))
    parts = ['<svg class="sx-radar" viewBox="0 0 320 230" role="img">']
    for ring in (0.25, 0.5, 0.75, 1.0):
        parts.append('<polygon points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, ring) for i in range(n))) + '" class="ring"/>')
    for i, (label, value) in enumerate(axes):
        x, y = pt(i, 1.0)
        lx, ly = pt(i, 1.2)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" class="ring"/>'
                     f'<text x="{lx:.1f}" y="{ly + 3:.1f}" text-anchor="middle" class="ax">{esc(label)} · {_fmt(value)}</text>')
    shape = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, v / top) for i, (_, v) in enumerate(axes)))
    parts.append(f'<polygon points="{shape}" fill="{color}" fill-opacity=".22" stroke="{color}" stroke-width="2"/>')
    for i, (label, value) in enumerate(axes):
        x, y = pt(i, value / top)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}"><title>{esc(label)}: {_fmt(value)}</title></circle>')
    parts.append("</svg>")
    return minify("".join(parts))


# ------------------------------------------------------ agent pipeline diagram
AGENT_FLOW = [("DetectionAgent", "Detection", "01"), ("InvestigationAgent", "Investigation", "02"),
              ("ThreatIntelAgent", "Threat Intel", "03"), ("RiskAssessmentAgent", "Risk Assessment", "04"),
              ("AuditAgent", "Audit", "05"), ("ResponseAgent", "Response", "06")]
STATE_COLOR = {"completed": "#25E58A", "running": "#00A8FF", "failed": "#FF303D", "pending": "#31507f",
               "not_run": "#31507f", "awaiting_review": "#FFB547"}


def pipeline_svg(states: Dict[str, Dict[str, Any]], note: str = "") -> str:
    """Six-node workflow. ``states[agent] = {"state": ..., "detail": "..."}``; agents absent are shown as not run."""
    W, H = 880, 150
    xs = [70 + i * 148 for i in range(6)]
    parts = [f'<svg class="sx-pipe" viewBox="0 0 {W} {H}" role="img" aria-label="Agent workflow">',
             '<defs><marker id="pa" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0 0L8 4L0 8Z" fill="#2c7fd8"/></marker>'
             '<filter id="pg" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="4"/></filter></defs>']
    for i in range(5):
        parts.append(f'<line x1="{xs[i] + 34}" y1="62" x2="{xs[i + 1] - 36}" y2="62" stroke="#2c7fd8" stroke-width="1.6" marker-end="url(#pa)" class="flow"/>')
    for x, (key, label, num) in zip(xs, AGENT_FLOW):
        info = states.get(key) or {"state": "not_run", "detail": "no recorded run"}
        state = info.get("state", "not_run")
        color = STATE_COLOR.get(state, "#31507f")
        glow = state in ("completed", "running", "failed", "awaiting_review")
        parts.append(
            f'<g class="pn"><title>{esc(label)} — {esc(state.replace("_", " "))}: {esc(info.get("detail", ""))}</title>'
            + (f'<circle cx="{x}" cy="62" r="30" fill="{color}" opacity=".35" filter="url(#pg)"/>' if glow else "")
            + f'<circle cx="{x}" cy="62" r="29" fill="#071326" stroke="{color}" stroke-width="2.2"/>'
            f'<text x="{x}" y="67" text-anchor="middle" class="pnum" fill="{color}">{num}</text>'
            f'<text x="{x}" y="112" text-anchor="middle" class="plab">{esc(label)}</text>'
            f'<text x="{x}" y="128" text-anchor="middle" class="psub" fill="{color}">{esc(state.replace("_", " "))}</text></g>')
    parts.append("</svg>")
    return minify("".join(parts)) + (f'<div class="sx-netcap">{esc(note)}</div>' if note else "")
