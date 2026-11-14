"""Every drawing on the plan page, from the computed plan.

  make(plan) -> {"face", "layout", "bars", "log_<id>", "asm_log_<id>", "asm_rip", "jigs", "asm_true", "asm_cut", "row", "board", "trim"}

Flat drawings (end views, layouts) use cbplan.Svg; the exploded glue-ups and the crosscut are drawn in 3D with
assembly.Scene. One look throughout: woods in their end-grain colours, glue faces yellow, clamp pressure as orange
block arrows, jigs in MDF grey, cuts in red, labels in the page's mono face.
"""
import html, math
from collections import OrderedDict

from assembly import Scene, GLUE, ARROW, CUT, INK
import cbplan as CB
from cbplan import Svg, short, bbox_of, centroid, FONT

MDF = "#d8d2c4"; MDF_E = "#8d8676"; REF = "#b3402a"
S3 = math.sqrt(3)


def _cen(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def _chip(s, xy, text, r=10, fill="#fff", raw=False, size=11.5):
    x, y = xy if raw else s.P(*xy)
    r = r if len(text) <= 2 else r + 3
    s.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{INK}" stroke-width="1.2"/>'
          f'<text x="{x:.1f}" y="{y + 0.5:.1f}" font-size="{size}" font-weight="600" text-anchor="middle" dominant-baseline="middle" fill="{INK}">{html.escape(text)}</text>')


def _arrow(s, a, b, raw=False, w=6, hw=13, hl=15):
    (ax, ay), (bx, by) = (a, b) if raw else (s.P(*a), s.P(*b))
    dx, dy = bx - ax, by - ay; d = math.hypot(dx, dy) or 1; ux, uy = dx / d, dy / d; nx, ny = -uy, ux
    pts = [(ax + nx * w, ay + ny * w), (bx - ux * hl + nx * w, by - uy * hl + ny * w), (bx - ux * hl + nx * hw, by - uy * hl + ny * hw),
           (bx, by), (bx - ux * hl - nx * hw, by - uy * hl - ny * hw), (bx - ux * hl - nx * w, by - uy * hl - ny * w), (ax - nx * w, ay - ny * w)]
    s.raw('<polygon points="' + " ".join("%.1f,%.1f" % p for p in pts) + f'" fill="{ARROW}" stroke="#b86a00" stroke-width="1"/>')


def _legend(s, plan, y):
    x = s.pad
    for w in plan["woods"]:
        s.raw(f'<rect x="{x}" y="{y - 8}" width="16" height="16" fill="{w["end"]}" stroke="{INK}" stroke-width="0.6"/>')
        s.text((x + 22, y), w["name"], 11.5, anchor="start", raw=True)
        x += 34 + 7.3 * len(w["name"])


def _edge_key(a, b):
    a = (round(a[0], 2), round(a[1], 2)); b = (round(b[0], 2), round(b[1], 2)); return (min(a, b), max(a, b))


def _glue_edges(new, old):
    """Edges of the new parts that lie against another part (new or old): [(a, b)]."""
    cnt = {}; keep = {}
    for grp, isnew in ((new, True), (old, False)):
        for p in grp:
            for i in range(len(p)):
                k = _edge_key(p[i - 1], p[i]); c = cnt.setdefault(k, [0, 0]); c[0] += 1; c[1] += isnew; keep[k] = (p[i - 1], p[i])
    return [keep[k] for k, c in cnt.items() if c[0] > 1 and c[1] >= 1]


def _part_polys(part):
    return [c[1] for c in part["cells"]] if "log" in part else [part["pts"]]


def _draw_part(s, plan, part, shift, op=1.0, label=True, bold=True):
    sp = plan["species"]
    if "log" in part:
        for r, pts in part["cells"]:
            s.poly([(x + shift, y) for x, y in pts], sp[r]["end"], "#1e232766", 0.5, op=op)
        s.poly([(x + shift, y) for x, y in part["pts"]], "none", INK, 1.5 if bold else 0.7)
        if label: _chip(s, (_cen(part["pts"])[0] + shift, _cen(part["pts"])[1]), part["log"] + ("′" if part.get("flip") else ""))
    else:
        s.poly([(x + shift, y) for x, y in part["pts"]], sp[part["role"]]["end"], INK, 1.3 if bold else 0.6, op=op)
        if label:
            c = centroid(part["pts"]); _chip(s, (c[0] + shift, c[1]), part["bar"], r=9, size=10.5)


# ------------------------------------------------------------------------------------- flat drawings
def face(plan):
    trim = plan["board"]["trim"]; W, L = plan["board"]["width"], plan["board"]["length"]
    sc = min(560 / W, 680 / L)
    s = Svg(trim, sc, pad=58, extra_h=34, title="Finished board, top face")
    from assembly import _shade
    for f in plan["face"]:
        col = plan["species"][f["role"]]["end"]; s.poly(f["pts"], col, _shade(col, 0.8), 0.6)
    s.poly([(trim[0], trim[1]), (trim[2], trim[1]), (trim[2], trim[3]), (trim[0], trim[3])], stroke=INK, sw=1.4)
    s.dimx(trim[0], trim[2], trim[1], short(W)); s.dimy(trim[1], trim[3], trim[0], short(L))
    _legend(s, plan, s.h - 22)
    return s.svg()


def layout(plan):
    rows = plan["rows"]; trim = plan["board"]["trim"]; sp = plan["species"]
    ang = math.radians(plan["info"].get("angle", 0)); u = (math.cos(ang), math.sin(ang))
    bb = bbox_of([r["pts"] for r in rows]); m = 0.9
    bb = (bb[0] - m, bb[1] - m, bb[2] + m, bb[3] + m)
    sc = min(680 / (bb[2] - bb[0]), 860 / (bb[3] - bb[1]))
    s = Svg(bb, sc, pad=26, extra_h=40, title="Slice layout before trimming")
    for r in rows:
        for pk in r["pucks"]:
            for role, pts in pk["cells"]: s.poly(pts, sp[role]["end"], "#1e232740", 0.4)
    # veil over what the trim removes
    x0, y0, x1, y1 = bb
    for q in ([(x0, y0), (x1, y0), (x1, trim[1]), (x0, trim[1])], [(x0, trim[3]), (x1, trim[3]), (x1, y1), (x0, y1)],
              [(x0, trim[1]), (trim[0], trim[1]), (trim[0], trim[3]), (x0, trim[3])], [(trim[2], trim[1]), (x1, trim[1]), (x1, trim[3]), (trim[2], trim[3])]):
        s.poly(q, "#ffffff", "none", 0, op=0.55)
    small = sc * rows[0]["height"] < 46
    for r in rows:
        for pk in r["pucks"]:
            s.poly(pk["pts"], "none", INK, 1.5)
            c = _cen(pk["pts"])
            if plan["info"]["kind"] != "panel":
                a, b = pk["ref"]; k = 0.16
                a2 = (a[0] + (c[0] - a[0]) * k, a[1] + (c[1] - a[1]) * k); b2 = (b[0] + (c[0] - b[0]) * k, b[1] + (c[1] - b[1]) * k)
                a3 = (a2[0] + (b2[0] - a2[0]) * 0.12, a2[1] + (b2[1] - a2[1]) * 0.12); b3 = (b2[0] + (a2[0] - b2[0]) * 0.12, b2[1] + (a2[1] - b2[1]) * 0.12)
                s.line(a3, b3, REF, 3.2)
                _chip(s, c, pk["log"] + ("′" if pk["flip"] else ""), r=8 if small else 10, size=10 if small else 11.5)
            else:
                _chip(s, (pk["pts"][0][0] - 0.45, c[1]), pk["log"] + ("′" if pk["flip"] else ""))
        c = _cen(r["pts"]); half = r["length"] / 2 + 0.5
        if plan["info"]["kind"] == "panel": pos = (r["pts"][1][0] + 0.45, c[1])
        else: pos = (c[0] - u[0] * half, c[1] - u[1] * half)
        s.text(pos, f"R{r['n']}", 11.5, weight="600", fill=REF)
    s.poly([(trim[0], trim[1]), (trim[2], trim[1]), (trim[2], trim[3]), (trim[0], trim[3])], stroke=CUT, sw=1.6, dash="7 4")
    _legend(s, plan, s.h - 24)
    return s.svg()


def bars(plan):
    bts = plan["bar_types"]; cellw, cellh = 340, 300
    cols = min(3, len(bts)); nrows = math.ceil(len(bts) / cols)
    W, H = cols * cellw, nrows * cellh
    el = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">'
          '<title>Bar cross-sections and rip setups</title><rect width="100%" height="100%" fill="#fff"/>']
    used = {}
    for b in plan["bars"]: used.setdefault(b["bar"], []).append(b)
    wood = {w["key"]: w for w in plan["woods"]}
    for n, bt in enumerate(bts):
        ox, oy = (n % cols) * cellw, (n // cols) * cellh
        pts = _flat(bt["pts"]); b = bbox_of([pts]); bw, bh = b[2] - b[0], b[3] - b[1]
        sc = min(150 / bw, 96 / bh)
        P = lambda x, y: (ox + 95 + (x - b[0]) * sc + (150 - bw * sc) / 2, oy + 52 + (b[3] - y) * sc)
        fill = wood[used[bt["id"]][0]["species"]]["end"] if bt["id"] in used else "#ddd"
        el.append(f'<circle cx="{ox + 24}" cy="{oy + 22}" r="11" fill="#fff" stroke="{INK}" stroke-width="1.2"/><text x="{ox + 24}" y="{oy + 26}" font-size="12" font-weight="600" text-anchor="middle">{bt["id"]}</text>'
                  f'<text x="{ox + 44}" y="{oy + 26}" font-size="11.5">{html.escape(bt["label"])}</text>')
        el.append('<polygon points="' + " ".join("%.1f,%.1f" % P(*v) for v in pts) + f'" fill="{fill}" stroke="{INK}" stroke-width="1.3"/>')
        c = centroid(pts); cx, cy = P(*c); k = len(pts)
        seen = set()
        for i in range(k):
            a, bb_ = pts[i - 1], pts[i]; ln = short(math.dist(a, bb_))
            m = P((a[0] + bb_[0]) / 2, (a[1] + bb_[1]) / 2)
            dx, dy = m[0] - cx, m[1] - cy; d = math.hypot(dx, dy) or 1
            el.append(f'<text x="{m[0] + dx / d * 24:.1f}" y="{m[1] + dy / d * 15:.1f}" font-size="10.5" text-anchor="middle" dominant-baseline="middle">{html.escape(ln)}</text>')
        for i, v in enumerate(pts):
            q = P(*v); dx, dy = cx - q[0], cy - q[1]; d = math.hypot(dx, dy) or 1
            a_, c_ = pts[i - 1], pts[(i + 1) % k]
            v1 = (a_[0] - v[0], a_[1] - v[1]); v2 = (c_[0] - v[0], c_[1] - v[1])
            angd = math.degrees(math.acos(max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2))))))
            el.append(f'<text x="{q[0] + dx / d * 19:.1f}" y="{q[1] + dy / d * 15:.1f}" font-size="9.5" fill="{INK}" paint-order="stroke" stroke="#fff" stroke-width="2.6" stroke-opacity="0.85" text-anchor="middle" dominant-baseline="middle">{angd:.0f}°</text>')
        # the blank, end view, with the cuts
        y0 = oy + 196; t = bt["dims"].get("thick") or bh; kk = min(30, 44 / t)
        bx0 = ox + 30; blen = 280
        el.append(f'<rect x="{bx0}" y="{y0}" width="{blen}" height="{t * kk:.1f}" fill="#f3ead8" stroke="{INK}"/>')
        tilt = bt["tilt"] or 0; dxs = t * kk * math.tan(math.radians(tilt)); stop = (bt.get("stop") or bw) * kk
        if bt["kind"] in ("rhombus", "parallelogram"):
            x = bx0 + 14
            while x + dxs < bx0 + blen - 30:
                el.append(f'<line x1="{x:.1f}" y1="{y0 + t * kk:.1f}" x2="{x + dxs:.1f}" y2="{y0}" stroke="{CUT}" stroke-width="1.4"/>'); x += stop
        elif bt["kind"] == "right triangle":
            x = bx0 + 10
            while x + stop + 4 < bx0 + blen:
                el.append(f'<line x1="{x + stop:.1f}" y1="{y0}" x2="{x + stop:.1f}" y2="{y0 + t * kk:.1f}" stroke="{CUT}" stroke-width="1.4"/>')
                el.append(f'<line x1="{x:.1f}" y1="{y0 + t * kk:.1f}" x2="{x + stop:.1f}" y2="{y0}" stroke="{CUT}" stroke-width="1" stroke-dasharray="3 2"/>')
                x += stop + 4
        elif "triangle" in bt["kind"] or bt["kind"] == "trapezoid":
            top_w = (bt["dims"].get("short") or 0) * kk; x = bx0 + 14; flip = False
            while x + dxs + stop < bx0 + blen:
                if not flip: el.append(f'<line x1="{x:.1f}" y1="{y0 + t * kk:.1f}" x2="{x + dxs:.1f}" y2="{y0}" stroke="{CUT}" stroke-width="1.4"/>')
                else: el.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x + dxs:.1f}" y2="{y0 + t * kk:.1f}" stroke="{CUT}" stroke-width="1.4"/>')
                x += (top_w + dxs) if not flip else top_w + dxs; flip = not flip
        else:
            x = bx0
            while x + stop < bx0 + blen - 30:
                x += stop
                el.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y0 + t * kk:.1f}" stroke="{CUT}" stroke-width="1.4"/>')
        el.append(f'<text x="{bx0}" y="{y0 - 8}" font-size="10">blank, end view · last 1&quot; is waste</text>')
        el.append(f'<text x="{bx0}" y="{y0 + t * kk + 16:.1f}" font-size="10.5">{html.escape(short(t))} thick · '
                  + (f'blade {tilt:.1f}° from vertical' if tilt else 'blade square') + '</text>')
        if bt.get("stop"):
            el.append(f'<text x="{bx0}" y="{y0 + t * kk + 31:.1f}" font-size="10.5">stop to blade {html.escape(short(bt["stop"]))} at the table</text>')
        uses = "; ".join(f'{x["total_bars"]} + {x["total_spares"]} {wood[x["species"]]["name"].split()[-1].lower()}' for x in used.get(bt["id"], []))
        el.append(f'<text x="{bx0}" y="{y0 + t * kk + 46:.1f}" font-size="10.5">{html.escape(uses)}</text>')
    el.append("</svg>")
    return "".join(el)


def _flat(pts):
    """Turn a cross-section so its longest side lies on the table."""
    pts = [tuple(p) for p in pts]; n = len(pts)
    i = max(range(n), key=lambda i: math.dist(pts[i], pts[(i + 1) % n]))
    a, b = pts[i], pts[(i + 1) % n]; ang = -math.atan2(b[1] - a[1], b[0] - a[0]); c, s_ = math.cos(ang), math.sin(ang)
    out = [((x - a[0]) * c - (y - a[1]) * s_, (x - a[0]) * s_ + (y - a[1]) * c) for x, y in pts]
    if sum(y for _, y in out) < 0: out = [(x, -y) for x, y in out][::-1]
    return out


def _cradle(s, cx, L, H, tape=True):
    yc = H * 0.82; e = L / 2 + 0.55
    s.poly([(cx - e - 0.15, -0.32), (cx + e + 0.15, -0.32), (cx + e + 0.15, 0), (cx - e - 0.15, 0)], MDF, MDF_E, 1)
    for sg in (-1, 1):
        s.poly([(cx, 0), (cx + sg * yc / S3, yc), (cx + sg * e, yc), (cx + sg * e, 0)], MDF, MDF_E, 1)
        if tape: s.line((cx, 0), (cx + sg * yc / S3, yc), "#c9a227", 2.2)


def log_stages(plan, lg):
    """End view of a log, one panel per glue-up: what goes in, where the glue goes, how it is held."""
    st = lg["stages"]; w, h = lg["w"], lg["h"]; tri = lg["kind"] == "tri"
    gapx = w + (2.0 if tri else 1.6); n = len(st)
    sc = min(64, 250 / (w + 1.6), 190 / (h + 1.0))
    x0 = -w / 2 - 0.9 if tri else -0.8
    s = Svg((x0, -0.5, x0 + n * gapx, h + 1.5), sc, pad=24, extra_h=18, title=f"{lg['name']}, end view")
    done = []
    for k, stg in enumerate(st):
        sh = k * gapx
        if tri: _cradle(s, sh, w, h)
        else: s.line((sh - 0.5, 0), (sh + w + 0.5, 0), MDF_E, 2)
        for p in done: _draw_part(s, plan, p, sh, op=0.45, label=False, bold=False)
        for p in stg["parts"]: _draw_part(s, plan, p, sh, label=False)
        newp = [[(x + sh, y) for x, y in q] for p in stg["parts"] for q in ([p["pts"]])]
        oldp = [[(x + sh, y) for x, y in p["pts"]] for p in done]
        for a, b in _glue_edges(newp, oldp): s.line(a, b, GLUE, 3.4)
        for p in stg["parts"]:
            c = centroid(p["pts"]) if "bar" in p and "log" not in p else _cen(p["pts"])
            _chip(s, (c[0] + sh, c[1]), (p["log"] + ("′" if p.get("flip") else "")) if "log" in p else p["bar"], r=9, size=10.5)
        top = max(v[1] for p in done + stg["parts"] for v in p["pts"])
        solo = n == 1 and len(stg["parts"]) == 1
        if solo: pass
        elif tri:
            hw = top / S3 - 0.06
            s.poly([(sh - hw, top), (sh + hw, top), (sh + hw, top + 0.28), (sh - hw, top + 0.28)], MDF, MDF_E, 1)
            _arrow(s, (sh, top + 1.15), (sh, top + 0.32))
        else:
            _arrow(s, (sh + w / 2, top + 1.0), (sh + w / 2, top + 0.1))
            if lg["shape"] != "band" and lg["kind"] != "panel" or lg["kind"] == "panel":
                _arrow(s, (sh - 0.75, h / 2), (sh - 0.05, h / 2)); _arrow(s, (sh + w + 0.75, h / 2), (sh + w + 0.05, h / 2))
        lab = "Solid bar, no glue-up" if solo else f"Glue-up {k + 1}" if n > 1 else "One glue-up"
        s.text((sh + (0 if tri else w / 2), h + 1.32), lab, 11.5, weight="600")
        done += stg["parts"]
    return s.svg()


def jigs(plan):
    L = max(lg["w"] for lg in plan["logs"]); H = L * S3 / 2
    sc = min(60, 300 / (L + 2))
    s = Svg((-L / 2 - 1.2, -0.6, L / 2 + 1.2, H + 1.0), sc, pad=44, extra_h=30, title="V cradle, end view")
    _cradle(s, 0, L, H)
    s.poly([(0, 0), (L / 2, H), (-L / 2, H)], "none", INK, 1, dash="5 4")
    s.text((0, H * 0.55), "log", 11, fill="#5b6167")
    s.text((0, 0.22 * H), "60°", 11.5, weight="600", fill=REF)
    s.text((-L / 2 - 0.3, H * 0.35), "3/4 MDF", 10); s.text((L / 2 + 0.3, H * 0.35), "edge at 30°", 10)
    s.text((0, -0.75), "flat base · V lined with packing tape", 10.5)
    s.dimx(-L / 2, L / 2, H, short(L), below=False)
    return s.svg()


def true_fig(plan):
    lg = next(l for l in plan["logs"] if l["kind"] == "tri"); L = lg["w"]; H = lg["h"]
    sc = min(60, 300 / (L + 2))
    s = Svg((-L / 2 - 1.2, -0.6, L / 2 + 1.2, H + 1.9), sc, pad=40, extra_h=30, title="Truing a log in the sanding sled")
    _cradle(s, 0, L, H, tape=False)
    for r, pts in lg["cells"]: s.poly(pts, plan["species"][r]["end"], INK, 0.8)
    s.poly(lg["outline"], "none", INK, 1.5)
    s.line((-L / 2, H), (L / 2, H), CUT, 2.6)
    cx, cy = s.P(0, H + 0.95); r = 0.9 * sc
    s.raw(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="#eee9dc" stroke="{MDF_E}" stroke-width="1.2"/>'
          f'<path d="M{cx - r * .55:.1f},{cy - r * .2:.1f} a{r * .6:.1f},{r * .6:.1f} 0 0 1 {r * 1.1:.1f},0" fill="none" stroke="{INK}" stroke-width="1.2"/>'
          f'<path d="M{cx + r * .55:.1f},{cy - r * .2:.1f} l-7,-2 l4,7 z" fill="{INK}"/>')
    s.text((0, H + 0.95), "drum", 10.5)
    s.text((0, -0.75), "sled: same V, no tape · sand the top face, turn, repeat", 10.5)
    return s.svg()


def row_fig(plan):
    rows = plan["rows"]; sp = plan["species"]; kind = plan["info"]["kind"]
    r = max(rows, key=lambda r_: len(r_["pucks"]))
    ang = math.radians(plan["info"].get("angle", 0)); c, sn = math.cos(ang), math.sin(ang)
    G = lambda p: (p[0] * c + p[1] * sn, -p[0] * sn + p[1] * c)
    pk = [{"pts": [G(v) for v in q["pts"]], "cells": [(ro, [G(v) for v in pts]) for ro, pts in q["cells"]], "log": q["log"], "flip": q["flip"]} for q in r["pucks"]]
    b = bbox_of([q["pts"] for q in pk]); hgt = b[3] - b[1]; fw = max(0.5, 0.3 * hgt)
    bb = (b[0] - 1.9, b[1] - fw - 0.5, b[2] + 1.9, b[3] + fw + 0.5)
    sc = min(720 / (bb[2] - bb[0]), 70)
    s = Svg(bb, sc, pad=22, extra_h=20, title=f"Row {r['n']} in the row jig, seen from above")
    if kind != "panel":
        for yy in ((b[1] - fw, b[1]), (b[3], b[3] + fw)):
            s.poly([(b[0] - 1.2, yy[0]), (b[2] + 1.2, yy[0]), (b[2] + 1.2, yy[1]), (b[0] - 1.2, yy[1])], MDF, MDF_E, 1)
        s.text(((b[0] + b[2]) / 2, b[3] + fw / 2), "fence", 10.5); s.text(((b[0] + b[2]) / 2, b[1] - fw / 2), "fence", 10.5)
    for q in pk:
        for ro, pts in q["cells"]: s.poly(pts, sp[ro]["end"], "#1e232740", 0.4)
    for q in pk:
        s.poly(q["pts"], "none", INK, 1.4)
        if kind != "panel": _chip(s, _cen(q["pts"]), q["log"] + ("′" if q["flip"] else ""), r=9, size=10.5)
    if kind == "tri":   # end blocks square the slanted ends
        xs = sorted(v[0] for q in pk for v in q["pts"])
        left = min(pk, key=lambda q: _cen(q["pts"])[0]); right = max(pk, key=lambda q: _cen(q["pts"])[0])
        for q, x_out, sg in ((left, b[0], -1), (right, b[2], 1)):
            ys = [v for v in q["pts"] if abs(v[0] - x_out) < 1e-6]
            tip = ys[0]; other_y = b[3] if abs(tip[1] - b[1]) < 1e-6 else b[1]
            far = [v for v in q["pts"] if abs(v[1] - other_y) < 1e-6]
            inner = min(far, key=lambda v: sg * -v[0]) if False else (min(far, key=lambda v: v[0]) if sg < 0 else max(far, key=lambda v: v[0]))
            s.poly([tip, (x_out, other_y), inner], MDF, MDF_E, 1)
        s.text((b[0] - 0.05, b[1] - fw - 0.28), "end blocks: a waste slice cut in half", 10.5, anchor="start")
    _arrow(s, (b[0] - 1.75, (b[1] + b[3]) / 2), (b[0] - 0.08, (b[1] + b[3]) / 2)); _arrow(s, (b[2] + 1.75, (b[1] + b[3]) / 2), (b[2] + 0.08, (b[1] + b[3]) / 2))
    if kind != "panel": s.dimy(b[1], b[3], b[0] - 1.25, short(hgt))
    return s.svg()


def board_fig(plan):
    rows = plan["rows"]; sp = plan["species"]
    ang = math.radians(plan["info"].get("angle", 0)); nrm = (-math.sin(ang), math.cos(ang)); u = (math.cos(ang), math.sin(ang))
    gap = 0.45; n = len(rows)
    off = [((i - (n - 1) / 2) * gap * nrm[0], (i - (n - 1) / 2) * gap * nrm[1]) for i in range(n)]
    mv = lambda pts, o: [(x + o[0], y + o[1]) for x, y in pts]
    allp = [mv(r["pts"], o) for r, o in zip(rows, off)]
    b = bbox_of(allp); m = 1.7
    bb = (b[0] - m, b[1] - m, b[2] + m, b[3] + m)
    sc = min(640 / (bb[2] - bb[0]), 700 / (bb[3] - bb[1]))
    s = Svg(bb, sc, pad=20, extra_h=20, title="Rows glued into the board, seen from above")
    for r, o in zip(rows, off):
        for pk in r["pucks"]:
            for ro, pts in pk["cells"]: s.poly(mv(pts, o), sp[ro]["end"], "#1e232730", 0.3)
        s.poly(mv(r["pts"], o), "none", INK, 1.5)
    for i in range(n - 1):   # glue lines between rows
        pass
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    ext_n = max(abs((v[0] - cx) * nrm[0] + (v[1] - cy) * nrm[1]) for p in allp for v in p)
    ext_u = max(abs((v[0] - cx) * u[0] + (v[1] - cy) * u[1]) for p in allp for v in p)
    for t in (-0.6, 0, 0.6):
        for sg in (-1, 1):
            base = (cx + u[0] * t * ext_u + nrm[0] * sg * (ext_n + 1.5), cy + u[1] * t * ext_u + nrm[1] * sg * (ext_n + 1.5))
            tip = (cx + u[0] * t * ext_u + nrm[0] * sg * (ext_n + 0.1), cy + u[1] * t * ext_u + nrm[1] * sg * (ext_n + 0.1))
            _arrow(s, base, tip)
    for t in (-0.82, 0.82):   # cauls across the rows
        a = (cx + u[0] * t * ext_u, cy + u[1] * t * ext_u); hw = 0.28
        q = [(a[0] + nrm[0] * sg1 * (ext_n + 0.9) + u[0] * sg2 * hw, a[1] + nrm[1] * sg1 * (ext_n + 0.9) + u[1] * sg2 * hw) for sg1, sg2 in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        s.poly(q, MDF, MDF_E, 1, op=0.8)
    a = (cx + u[0] * 0.82 * ext_u, cy + u[1] * 0.82 * ext_u)
    s.text(a, "caul", 10.5, rot=0 if abs(nrm[0]) > 0.5 else -90)
    for r, o in zip(rows, off):
        c = _cen(mv(r["pts"], o)); half = r["length"] / 2 + 0.45
        s.text((c[0] - u[0] * half, c[1] - u[1] * half), f"R{r['n']}", 11, weight="600", fill=REF)
    return s.svg()


def trim_fig(plan):
    bd = plan["board"]; g = bd["glued"]; trim = bd["trim"]; sp = plan["species"]
    bb = (g[0] - 0.4, g[1] - 0.4, g[2] + 0.4, g[3] + 0.4)
    sc = min(520 / (bb[2] - bb[0]), 620 / (bb[3] - bb[1]))
    s = Svg(bb, sc, pad=56, extra_h=10, title="Trim lines on the flattened board")
    for p in plan["polygons"]:
        c = CB.clip_rect(p["pts"], g)
        if c: s.poly(c, sp[p["role"]]["end"], "#1e232730", 0.3, op=0.5)
    for f in plan["face"]: s.poly(f["pts"], sp[f["role"]]["end"], "#1e232740", 0.3)
    s.poly([(g[0], g[1]), (g[2], g[1]), (g[2], g[3]), (g[0], g[3])], "none", INK, 1.2)
    s.poly([(trim[0], trim[1]), (trim[2], trim[1]), (trim[2], trim[3]), (trim[0], trim[3])], stroke=CUT, sw=1.8, dash="7 4")
    s.dimx(trim[0], trim[2], g[1], short(bd["width"])); s.dimy(trim[1], trim[3], g[0], short(bd["length"]))
    return s.svg()


# ------------------------------------------------------------------------------------- 3D
def _along(ox=0.0, oy=0.0, oz=0.0):
    return lambda u, v, w: (ox + w, oy + u, oz + v)


def asm_log(plan, lg):
    sp = plan["species"]; parts = [p for st in lg["stages"] for p in st["parts"]]
    allp = [p["pts"] for p in parts]; c = _cen([v for p in allp for v in p])
    span = max(lg["w"], lg["h"]); L = max(3.0, 1.9 * span); gap = max(0.35, 0.22 * span)
    s = Scene(az=34, el=30)
    polys_all = []; owner = []
    for i, p in enumerate(parts):
        for q in _part_polys(p): polys_all.append(q); owner.append(i)
    cnt = {}
    for q in allp:
        for i in range(len(q)): cnt[_edge_key(q[i - 1], q[i])] = cnt.get(_edge_key(q[i - 1], q[i]), 0) + 1
    for i, p in enumerate(parts):
        bc = _cen(p["pts"]); dx, dy = bc[0] - c[0], bc[1] - c[1]; d = math.hypot(dx, dy) or 1
        ox, oy = (dx / d * gap, dy / d * gap) if d > 1e-6 else (0, 0)
        outer = {_edge_key(p["pts"][k - 1], p["pts"][k]) for k in range(len(p["pts"])) if cnt[_edge_key(p["pts"][k - 1], p["pts"][k])] > 1}
        pieces = [(r, q) for r, q in p["cells"]] if "log" in p else [(p["role"], p["pts"])]
        for r, q in pieces:
            q = CB.ccw([tuple(v) for v in q])
            gl = {k for k in range(len(q)) if _on_any(q[k], q[(k + 1) % len(q)], p["pts"], outer)}
            s.prism([(x - c[0] + ox, y - c[1] + oy) for x, y in q], L, _along(), sp[r]["end"], sp[r]["long"], glue=gl)
        lab = (p["log"] + ("′" if p.get("flip") else "")) if "log" in p else p["bar"]
        s.mark("label", (L, bc[0] - c[0] + ox, bc[1] - c[1] + oy), lab, (30 * (1 if dx >= 0 else -1), -26 if dy >= -0.01 else 26))
    s.mark("grain", (0.6, -span * 0.9 - gap, -span * 0.55), (L - 0.6, -span * 0.9 - gap, -span * 0.55))
    return s.svg(title=f"{lg['name']}: parts and glue faces")


def _on_any(a, b, outline, keys):
    """True if segment a-b lies on one of the outline's edges named in keys."""
    n = len(outline)
    for k in range(n):
        p, q = outline[k - 1], outline[k]
        if _edge_key(p, q) not in keys: continue
        ln = math.dist(p, q) or 1
        da = abs((q[0] - p[0]) * (a[1] - p[1]) - (q[1] - p[1]) * (a[0] - p[0])) / ln
        db = abs((q[0] - p[0]) * (b[1] - p[1]) - (q[1] - p[1]) * (b[0] - p[0])) / ln
        if da < 2e-3 and db < 2e-3: return True
    return False


def asm_rip(plan):
    bt = plan["bar_types"][0]; b0 = next(b for b in plan["bars"] if b["bar"] == bt["id"])
    col = next(w for w in plan["woods"] if w["key"] == b0["species"])
    s = Scene(az=50, el=26)
    sect = _flat(bt["pts"]); th = max(y for _, y in sect); wdt = max(x for x, _ in sect) - min(x for x, _ in sect)
    x0 = min(x for x, _ in sect); sect = [(x - x0, y) for x, y in sect]
    Lb = 9.0; gap = 0.5
    lean = sect[-1][0] if len(sect) == 4 else 0
    blank = [(0, 0), (3.2 * wdt, 0), (3.2 * wdt, th), (max(0.0, sect[-1][0] if len(sect) == 4 else 0), th)]
    s.prism([(x + 3 * (wdt + gap) + 0.2, y) for x, y in blank], Lb, _along(), col["end"], col["long"])
    for k in range(3):
        s.prism([(x + k * (wdt + gap), y) for x, y in sect], Lb, _along(), col["end"], col["long"])
        s.mark("label", (Lb, k * (wdt + gap) + wdt / 2, th * 0.5), bt["id"], (-30 - 6 * k, 38 + 10 * k))
    s.mark("grain", (1.0, -1.2, 0), (Lb - 1.0, -1.2, 0))
    return s.svg(title=f"Bars ripped from the blank")


def asm_cut(plan):
    lg = max((l for l in plan["logs"] if l["crosscut"]), key=lambda l: l["slices"]); sp = plan["species"]; cut = plan["slice_cut"]
    H = lg["h"]
    cells = [(r, CB.ccw([(-x, H - y) for x, y in pts])) for r, pts in lg["cells"]] if lg["kind"] == "tri" else [(r, CB.ccw([tuple(v) for v in pts])) for r, pts in lg["cells"]]
    s = Scene(az=50, el=26)
    body = max(3.5, 1.6 * lg["w"]); g = 0.55 * cut
    for r, pts in cells: s.prism(pts, body, _along(), sp[r]["end"], sp[r]["long"])
    for k in range(3):
        w0 = body + g + k * (cut + g)
        for r, pts in cells: s.prism(pts, cut, _along(ox=w0), sp[r]["end"], sp[r]["long"])
    xs = [v[0] for _, p in cells for v in p]
    s.mark("line", (body + g / 2, min(xs) - 0.5, 0), (body + g / 2, max(xs) + 0.5, 0), CUT)
    s.mark("line", (body + g / 2, max(xs) + 0.5, 0), (body + g / 2, max(xs) + 0.5, H + 0.4), CUT)
    s.mark("text", (body + 3 * (cut + g), _cen([v for _, p in cells for v in p])[0], H + 0.5), f"slices {short(cut)} thick", (-10, -22))
    return s.svg(title=f"Crosscutting {lg['name']} into slices")


def make(plan):
    out = OrderedDict()
    out["face"] = face(plan); out["layout"] = layout(plan); out["bars"] = bars(plan)
    for lg in plan["logs"]:
        out[f"log_{lg['id']}"] = log_stages(plan, lg)
        if lg["kind"] != "panel": out[f"asm_log_{lg['id']}"] = asm_log(plan, lg)
    out["asm_rip"] = asm_rip(plan)
    if plan["info"]["kind"] == "tri":
        out["jigs"] = jigs(plan); out["asm_true"] = true_fig(plan)
    out["asm_cut"] = asm_cut(plan); out["row"] = row_fig(plan); out["board"] = board_fig(plan); out["trim"] = trim_fig(plan)
    return out
