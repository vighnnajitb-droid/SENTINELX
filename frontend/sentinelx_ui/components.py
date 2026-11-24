"""HTML/SVG building blocks for the Command Center (pure functions).

All text that originates from data (incident titles, IPs, statuses) passes
through ``esc`` before it is placed in markup. Output is minified (no blank
lines, no indentation) because Markdown would otherwise split or code-fence
the HTML block.
"""
from __future__ import annotations

import base64
import hashlib
import math
import re
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import metrics

COLORS = {"critical": "#FF303D", "high": "#FF643D", "medium": "#FFB547", "low": "#35C7D5",
          "ok": "#25E58A", "blue": "#087BFF", "bright": "#00A8FF", "cyan": "#00D9FF"}
ASSETS = Path(__file__).resolve().parent.parent / "assets"


def esc(value: Any) -> str:
    return escape("" if value is None else str(value), quote=True)


def minify(html: str) -> str:
    """Collapse markup to one line for Markdown safety, but keep <pre> blocks readable
    (their indentation and line breaks matter); only blank lines are removed there."""
    out = []
    for part in re.split(r"(<pre\b.*?</pre>)", html, flags=re.S):
        if part.startswith("<pre"):
            out.append("\n".join(line for line in part.splitlines() if line.strip()) + "\n")
        else:
            out.append("".join(line.strip() for line in part.splitlines() if line.strip()))
    return "".join(out)


# ------------------------------------------------------------------ gauges
SWEEP_START, SWEEP_SPAN = 210.0, 240.0   # degrees, clockwise on screen


def _pt(cx: float, cy: float, r: float, frac: float) -> Tuple[float, float]:
    theta = math.radians(SWEEP_START - SWEEP_SPAN * frac)
    return cx + r * math.cos(theta), cy - r * math.sin(theta)


def _band(cx, cy, r_out, r_in, f0, f1, fill, extra="") -> str:
    x0, y0 = _pt(cx, cy, r_out, f0)
    x1, y1 = _pt(cx, cy, r_out, f1)
    x2, y2 = _pt(cx, cy, r_in, f1)
    x3, y3 = _pt(cx, cy, r_in, f0)
    large = 1 if (f1 - f0) * SWEEP_SPAN > 180 else 0
    return (f'<path d="M{x0:.1f} {y0:.1f}A{r_out} {r_out} 0 {large} 1 {x1:.1f} {y1:.1f}'
            f'L{x2:.1f} {y2:.1f}A{r_in} {r_in} 0 {large} 0 {x3:.1f} {y3:.1f}Z" fill="{fill}" {extra}/>')


def gauge_svg(uid: str, value: Optional[float], bands: Sequence[Tuple[float, float, str, str]],
              state_color: str, caption: str, subcaption: str = "") -> str:
    """Semicircular (240 degree) gauge. ``bands``: (from, to, colour, label) with 0..1 fractions.
    ``value`` None renders the unavailable state (dim ring, em dash, no needle)."""
    cx, cy, ro, ri = 150, 142, 108, 80
    gap = 0.006
    avail = value is not None
    frac = 0.0 if not avail else max(0.0, min(1.0, value / 100.0))
    parts = [f'<svg class="sx-gauge" viewBox="0 0 300 250" role="img" aria-label="{esc(caption)}" xmlns="http://www.w3.org/2000/svg">']
    parts.append(
        f'<defs><linearGradient id="{uid}m" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5b6f90"/>'
        f'<stop offset=".5" stop-color="#1a2640"/><stop offset="1" stop-color="#4a5d7d"/></linearGradient>'
        f'<radialGradient id="{uid}c" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#050d1d"/>'
        f'<stop offset="1" stop-color="#091a33"/></radialGradient>'
        f'<filter id="{uid}g" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3"/></filter></defs>')
    # metallic outer ring + ticks
    x0, y0 = _pt(cx, cy, ro + 9, 0); x1, y1 = _pt(cx, cy, ro + 9, 1)
    parts.append(f'<path d="M{x0:.1f} {y0:.1f}A{ro+9} {ro+9} 0 1 1 {x1:.1f} {y1:.1f}" fill="none" stroke="url(#{uid}m)" stroke-width="9" stroke-linecap="round"/>')
    for i in range(0, 21):
        a, b = _pt(cx, cy, ri - 6, i / 20), _pt(cx, cy, ri - (11 if i % 5 == 0 else 8), i / 20)
        parts.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#3b5174" stroke-width="{1.4 if i % 5 == 0 else .8}"/>')
    # coloured bands (dim) + lit progress overlay
    for f0, f1, colour, label in bands:
        dim = "opacity:.30" if avail else "opacity:.16"
        parts.append(_band(cx, cy, ro, ri, f0 + gap, f1 - gap, colour, f'style="{dim}"'))
    if avail:
        for f0, f1, colour, label in bands:
            if frac > f0:
                parts.append(_band(cx, cy, ro, ri, f0 + gap, min(f1, frac) - (gap if frac >= f1 else 0), colour, ""))
        # glow under lit part
        for f0, f1, colour, label in bands:
            if frac > f0:
                parts.append(_band(cx, cy, ro + 2, ri - 2, f0 + gap, min(f1, frac), colour, f'filter="url(#{uid}g)" style="opacity:.45"'))
    for f0, f1, colour, label in bands:
        lx, ly = _pt(cx, cy, (ro + ri) / 2, (f0 + f1) / 2)
        parts.append(f'<text x="{lx:.1f}" y="{ly+3:.1f}" text-anchor="middle" class="sx-gl">{esc(label)}</text>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{ri-14}" fill="url(#{uid}c)" stroke="#16315a" stroke-width="1"/>')
    if avail:
        nx, ny = _pt(cx, cy, ro + 4, frac)
        bx, by = _pt(cx, cy, ri - 10, frac)
        parts.append(f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="{state_color}" stroke-width="5" opacity=".55" filter="url(#{uid}g)"/>')
        parts.append(f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#fff" stroke-width="2" stroke-linecap="round"/>')
        parts.append(f'<text x="{cx}" y="{cy+6}" text-anchor="middle" class="sx-gv">{round(value)}<tspan class="sx-gu" dx="3">/100</tspan></text>')
    else:
        parts.append(f'<text x="{cx}" y="{cy+8}" text-anchor="middle" class="sx-gv sx-na">—</text>')
    parts.append(f'<text x="{cx}" y="{cy+30}" text-anchor="middle" class="sx-gcap" fill="{state_color}">{esc(caption)}</text>')
    if subcaption:
        parts.append(f'<text x="{cx}" y="{cy+46}" text-anchor="middle" class="sx-gsub">{esc(subcaption)}</text>')
    parts.append("</svg>")
    return minify("".join(parts))


def severity_gauge(index: Dict[str, Any]) -> str:
    bands = [(0, .375, "#B3202D", "Low"), (.375, .625, "#D8283A", "Medium"),
             (.625, .875, "#F2303E", "High"), (.875, 1, "#FF4A57", "Critical")]
    if not index.get("available"):
        return gauge_svg("sg", None, bands, COLORS["critical"], "Unavailable", index.get("reason", ""))
    color = {"Low": COLORS["low"], "Medium": COLORS["medium"], "High": COLORS["high"], "Critical": COLORS["critical"]}[index["label"]]
    return gauge_svg("sg", index["value"], bands, color, f'{index["label"]} severity index',
                     f'{index["scored"]} unresolved scored')


def health_gauge(health: Dict[str, Any]) -> str:
    bands = [(0, .5, "#FF303D", "Critical"), (.5, .75, "#FFB547", "Degraded"),
             (.75, .9, "#00D9FF", "Warning"), (.9, 1, "#25E58A", "Normal")]
    if not health.get("available"):
        return gauge_svg("hg", None, bands, COLORS["cyan"], "Unavailable", health.get("reason", ""))
    color = {"Normal": COLORS["ok"], "Warning": COLORS["cyan"], "Degraded": COLORS["medium"],
             "Critical": COLORS["critical"]}[health["state"]]
    return gauge_svg("hg", health["value"], bands, color, health["state"],
                     f'{len(health["checks"])} live check{"s" if len(health["checks"]) != 1 else ""}')


# --------------------------------------------------------------- sparkline
def sparkline(values: Optional[List[int]], color: str, uid: str, w: int = 150, h: int = 46) -> str:
    if not values:
        return f'<svg class="sx-spark" viewBox="0 0 {w} {h}"><line x1="0" y1="{h-4}" x2="{w}" y2="{h-4}" stroke="#2a3b57" stroke-dasharray="3 4"/></svg>'
    top = max(max(values), 1)
    step = w / max(len(values) - 1, 1)
    pts = [(i * step, h - 5 - (v / top) * (h - 12)) for i, v in enumerate(values)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"0,{h} " + line + f" {w},{h}"
    lx, ly = pts[-1]
    return minify(
        f'<svg class="sx-spark" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
        f'<defs><linearGradient id="{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{color}" stop-opacity=".55"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
        f'<polygon points="{area}" fill="url(#{uid})"/>'
        f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="1.6" stroke-linejoin="round"/>'
        f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="2.6" fill="{color}"/></svg>')


def alert_card(key: str, title: str, value: Optional[int], unit: str, series: Optional[List[int]],
               color: str, tone: str, unavailable_reason: str, wide: bool = False) -> str:
    if value is None:
        body = f'<div class="sx-ac-val sx-na">Unavailable</div><div class="sx-ac-unit">{esc(unavailable_reason)}</div>'
        spark = sparkline(None, color, f"sp{key}")
    else:
        body = f'<div class="sx-ac-val">{value:,}</div><div class="sx-ac-unit">{esc(unit)}</div>'
        spark = sparkline(series, color, f"sp{key}")
    return (f'<div class="sx-ac {tone}{" wide" if wide else ""}" style="--ac:{color}" tabindex="0" '
            f'title="{esc(title)}: {esc(unit if value is not None else unavailable_reason)}">'
            f'<div class="sx-ac-title">{esc(title)}</div>{body}<div class="sx-ac-spark">{spark}</div></div>')


def alert_grid(summary: Dict[str, Any]) -> str:
    a = summary.get("alerts") or {}
    s = a.get("series") or {}
    sv = lambda k: metrics.series_values(s.get(k))
    cards = [
        alert_card("ta", "Total Alerts", a.get("total_alerts"), "incident records", sv("total_alerts"), COLORS["bright"], "blue",
                   "Incident data unavailable"),
        alert_card("ca", "Critical Alerts", a.get("critical_alerts"), "critical-severity incidents", sv("critical_alerts"),
                   COLORS["critical"], "red", "Incident data unavailable"),
        alert_card("ia", "Intrusion Attempts", a.get("intrusion_attempts"), "events: port scans + failed logins",
                   sv("intrusion_attempts"), COLORS["high"], "red", "Needs event-level backend data"),
        alert_card("ma", "Malware Detections", a.get("malware_detections"), "events typed as malware",
                   sv("malware_detections"), COLORS["bright"], "blue",
                   "Pipeline has no malware classifier", wide=True),
        alert_card("pa", "Pending Approvals", a.get("pending_approvals"), "response actions awaiting a human",
                   sv("pending_approvals"), COLORS["medium"], "amber", "Needs approval data", wide=True),
    ]
    return minify('<div class="sx-ag">' + "".join(cards) + "</div>")


# ---------------------------------------------------------------- timeline
def timeline(tl: Optional[Dict[str, Any]], counters: List[Tuple[str, Optional[int], Optional[int]]]) -> str:
    if not tl:
        stages_html = '<div class="sx-empty">No incident timeline available.</div>'
    else:
        stages = tl["stages"]
        segs = []
        for i in range(3):
            nxt = stages[i + 1]["state"]
            cls = {"done": "done", "failed": "failed", "active": "active"}.get(nxt, "pending")
            if stages[i]["state"] in ("pending", "unavailable"):
                cls = "pending"
            segs.append(f'<span class="seg {cls}" style="left:{12.5 + 25*i}%;width:25%"></span>')
        nodes = []
        for st_ in stages:
            ts = metrics.fmt_clock(st_["ts"])
            # pending/in-progress are real states; "unavailable" is reserved for missing data
            fallback = {"pending": "pending", "active": "in progress"}.get(st_["state"], "unavailable")
            nodes.append(
                f'<div class="st {st_["state"]}"><span class="dot"></span><b>{esc(st_["label"])}</b>'
                f'<i>{esc(ts) if ts else fallback}</i></div>')
        stages_html = f'<div class="sx-tl">{"".join(segs)}{"".join(nodes)}</div>'
    rows = []
    for label, value, total in counters:
        if value is None:
            rows.append(f'<div class="sx-row"><span>{esc(label)}</span><span class="bar"></span><em class="sx-na">n/a</em></div>')
        else:
            pct = metrics.ratio(value, total) * 100
            rows.append(f'<div class="sx-row"><span>{esc(label)}</span><span class="bar"><u style="width:{pct:.0f}%"></u></span><em>{value:,}</em></div>')
    return minify(stages_html + '<div class="sx-rows">' + "".join(rows) + "</div>")


# ----------------------------------------------------------------- network
VBW, VBH = 720, 300


def _iso(u: float, v: float) -> Tuple[float, float]:
    return 360 + (u - v) * 285, 46 + (u + v) * 100


def _hash01(text: str, salt: str) -> float:
    return int(hashlib.md5((salt + text).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def network_svg(network: Optional[Dict[str, Any]], max_nodes: int = 28) -> str:
    nodes = (network or {}).get("nodes") or []
    edges = (network or {}).get("edges") or []
    parts = [f'<svg class="sx-net" viewBox="0 0 {VBW} {VBH}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Network traffic map">']
    parts.append('<defs><linearGradient id="nslab" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b2347"/><stop offset="1" stop-color="#050f22"/></linearGradient>'
                 '<filter id="nglow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="3.2"/></filter></defs>')
    corners = [_iso(0, 0), _iso(1, 0), _iso(1, 1), _iso(0, 1)]
    thick = 16
    side = (f'M{corners[3][0]:.0f} {corners[3][1]:.0f}L{corners[2][0]:.0f} {corners[2][1]:.0f}L{corners[2][0]:.0f} {corners[2][1]+thick:.0f}'
            f'L{corners[3][0]:.0f} {corners[3][1]+thick:.0f}Z')
    side2 = (f'M{corners[2][0]:.0f} {corners[2][1]:.0f}L{corners[1][0]:.0f} {corners[1][1]:.0f}L{corners[1][0]:.0f} {corners[1][1]+thick:.0f}'
             f'L{corners[2][0]:.0f} {corners[2][1]+thick:.0f}Z')
    parts.append(f'<path d="{side}" fill="#071a38" stroke="#0e4a9c" stroke-width=".8"/><path d="{side2}" fill="#050f24" stroke="#0e4a9c" stroke-width=".8"/>')
    parts.append('<polygon points="' + " ".join(f"{x:.0f},{y:.0f}" for x, y in corners) + '" fill="url(#nslab)" stroke="#087BFF" stroke-width="1.2"/>')
    for i in range(1, 12):
        t = i / 12
        a, b = _iso(t, 0), _iso(t, 1)
        c, d = _iso(0, t), _iso(1, t)
        parts.append(f'<line x1="{a[0]:.0f}" y1="{a[1]:.0f}" x2="{b[0]:.0f}" y2="{b[1]:.0f}" stroke="#0a67c8" stroke-opacity=".28" stroke-width=".7"/>'
                     f'<line x1="{c[0]:.0f}" y1="{c[1]:.0f}" x2="{d[0]:.0f}" y2="{d[1]:.0f}" stroke="#0a67c8" stroke-opacity=".28" stroke-width=".7"/>')

    if not nodes or not edges:
        msg = "Network data unavailable" if network is None else "No source/destination events recorded yet"
        parts.append(f'<text x="{VBW/2}" y="{VBH/2+10}" text-anchor="middle" class="sx-net-empty">{msg}</text></svg>')
        return minify("".join(parts))

    degree: Dict[str, int] = {}
    for e in edges:
        degree[e["source"]] = degree.get(e["source"], 0) + e["events"]
        degree[e["target"]] = degree.get(e["target"], 0) + e["events"]
    ranked = sorted(nodes, key=lambda n: (not n["flagged"], -degree.get(n["id"], 0)))[:max_nodes]
    keep = {n["id"] for n in ranked}
    regions = {"internal": (0.06, 0.46), "unknown": (0.3, 0.7), "external": (0.54, 0.94)}
    pos = {}
    for n in ranked:
        lo, hi = regions[n["scope"]]
        pos[n["id"]] = _iso(lo + (hi - lo) * _hash01(n["id"], "u"), 0.1 + 0.8 * _hash01(n["id"], "v"))

    maxev = max((e["events"] for e in edges), default=1)
    for e in sorted(edges, key=lambda x: x["events"]):
        if e["source"] not in keep or e["target"] not in keep:
            continue
        (x1, y1), (x2, y2) = pos[e["source"]], pos[e["target"]]
        lift = 8 + 0.26 * math.hypot(x2 - x1, y2 - y1)
        mx, my = (x1 + x2) / 2, min(y1, y2) - lift
        hot = e["intrusion_events"] > 0
        color = COLORS["critical"] if hot else COLORS["cyan"]
        width = 0.9 + 1.8 * (e["events"] / maxev)
        types = ", ".join(f"{k} x{v}" for k, v in (e.get("types") or {}).items())
        parts.append(
            f'<g class="sx-edge{" hot" if hot else ""}"><title>{esc(e["source"])} → {esc(e["target"])}: {e["events"]} events'
            f'{" (" + esc(types) + ")" if types else ""}{", " + str(e["intrusion_events"]) + " intrusion-type" if hot else ""}</title>'
            f'<path d="M{x1:.0f} {y1:.0f}Q{mx:.0f} {my:.0f} {x2:.0f} {y2:.0f}" fill="none" stroke="{color}" stroke-width="{width:.1f}" stroke-opacity=".75"/></g>')
    first_flag = None
    for n in ranked:
        x, y = pos[n["id"]]
        flagged = n["flagged"]
        color = COLORS["critical"] if flagged else (COLORS["bright"] if n["scope"] == "internal" else COLORS["cyan"])
        r = 4 + min(4, degree.get(n["id"], 1) ** 0.5 * 0.6)
        rep = f', reputation: {n["reputation"]}' if n.get("reputation") else ""
        parts.append(
            f'<g class="sx-node"><title>{esc(n["id"])} · {esc(n["scope"])} · {degree.get(n["id"], 0)} events{esc(rep)}</title>'
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r*2.2:.1f}" fill="{color}" opacity=".35" filter="url(#nglow)"/>'
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="{color}" stroke="#fff" stroke-opacity=".7" stroke-width=".8"/></g>')
        if flagged and first_flag is None:
            first_flag = (x, y)

    def label(text, anchor_xy, tx, ty, align="start"):
        ax, ay = anchor_xy
        parts.append(f'<g class="sx-lbl"><polyline points="{tx:.0f},{ty+4:.0f} {tx+(110 if align=="start" else -110):.0f},{ty+4:.0f} {ax:.0f},{ay:.0f}" fill="none" stroke="#2c7fd8" stroke-width=".8" stroke-opacity=".7"/>'
                     f'<text x="{tx:.0f}" y="{ty:.0f}" text-anchor="{align}">{esc(text)}</text></g>')

    internals = [pos[n["id"]] for n in ranked if n["scope"] == "internal"]
    externals = [pos[n["id"]] for n in ranked if n["scope"] == "external"]
    if internals:
        label("Internal Network", min(internals, key=lambda p: p[0]), 14, 52)
    if externals:
        label("External Sources", max(externals, key=lambda p: p[1]), 14, 284)
    if first_flag:
        label("Suspicious Indicators", first_flag, VBW - 14, 52, "end")
    parts.append("</svg>")
    return minify("".join(parts))


def network_caption(network: Optional[Dict[str, Any]], max_nodes: int = 28) -> str:
    nodes = (network or {}).get("nodes") or []
    edges = (network or {}).get("edges") or []
    if not nodes:
        return "No network relationships to display."
    flagged = [n for n in nodes if n["flagged"]]
    sim = any(str(n.get("reputation", "")).startswith("simulated") for n in flagged)
    bits = [f"{len(nodes)} hosts · {len(edges)} observed flows"]
    if len(nodes) > max_nodes:
        bits.append(f"showing top {max_nodes} hosts")
    if (network or {}).get("truncated"):
        bits.append("flow list truncated")
    if flagged:
        bits.append(f"{len(flagged)} flagged by threat intel" + (" (simulated reputation data)" if sim else ""))
    bits.append("topology reconstructed from stored events")
    return " · ".join(bits)


# ------------------------------------------------------------------- table
def sev_pill(sev: Optional[str]) -> str:
    s = (sev or "").lower()
    if s not in ("critical", "high", "medium", "low"):
        return '<span class="sx-sevp na">Unscored</span>'
    return f'<span class="sx-sevp {s}">{s.capitalize()}</span>'


def status_pill(status: Optional[str], awaiting: bool = False) -> str:
    s = (status or "unknown").lower()
    label = s.replace("_", " ").capitalize()
    cls = {"resolved": "ok", "closed": "ok", "investigating": "active", "open": "open"}.get(s, "open")
    extra = '<span class="sx-await" title="A response action awaits human approval">approval pending</span>' if awaiting else ""
    return f'<span class="sx-stat {cls}"><i></i>{esc(label)}</span>{extra}'


def robot_img() -> str:
    path = ASSETS / "sentinel_ai.svg"
    if not path.exists():
        return ""
    uri = base64.b64encode(path.read_bytes()).decode()
    return f'<img class="sx-robot" alt="SENTINELX security AI" src="data:image/svg+xml;base64,{uri}"/>'
