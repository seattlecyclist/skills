"""Every drawing on the plan page, from the computed plan.

  make(plan) -> {"face", "layout", "bars", "log_<id>", "asm_log_<id>", "ripsled", "jigs", "asm_true", "asm_cut", "row", "board", "trim"}

Flat drawings (end views, layouts) use cbplan.Svg; the exploded glue-ups and the crosscut are drawn in 3D with
assembly.Scene. One look throughout: woods in their end-grain colours, glue faces blue, clamp pressure as orange
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
    """Where a new part lies against another part (new or old): the shared stretch of each pair of edges, [(a, b)]."""
    out = []; parts = [(p, True) for p in new] + [(p, False) for p in old]
    for i, (p, pn) in enumerate(parts):
        for q, qn in parts[i + 1:]:
            if not (pn or qn): continue
            for k in range(len(p)):
                a, b = p[k - 1], p[k]; L = math.dist(a, b)
                if L < 1e-6: continue
                ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                for m in range(len(q)):
                    c, d = q[m - 1], q[m]
                    if abs((c[0] - a[0]) * uy - (c[1] - a[1]) * ux) > 2e-3 or abs((d[0] - a[0]) * uy - (d[1] - a[1]) * ux) > 2e-3: continue
                    t0, t1 = sorted(((c[0] - a[0]) * ux + (c[1] - a[1]) * uy, (d[0] - a[0]) * ux + (d[1] - a[1]) * uy))
                    lo, hi = max(0, t0), min(L, t1)
                    if hi - lo > 0.02: out.append(((a[0] + ux * lo, a[1] + uy * lo), (a[0] + ux * hi, a[1] + uy * hi)))
    return out


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
    W, L = plan["board"]["width"], plan["board"]["length"]
    trim = (plan["board"].get("frame") or {}).get("outer") or plan["board"]["trim"]
    sc = min(560 / W, 680 / L)
    s = Svg(trim, sc, pad=58, extra_h=34, title="Finished board, top face")
    from assembly import _shade
    for f in plan["face"]:
        col = plan["species"][f["role"]]["end"]; s.poly(f["pts"], col, col, 0.7)
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
            s.poly(pk["pts"], "none", INK, 1.0)
            c = _cen(pk["pts"])
            if plan["info"]["kind"] == "hex":
                _chip(s, c, pk["log"] + ("½" if pk.get("half") else ""), r=8 if small else 10, size=10 if small else 11.5)
            elif plan["info"]["kind"] != "panel":
                a, b = pk["ref"]; k = 0.16
                a2 = (a[0] + (c[0] - a[0]) * k, a[1] + (c[1] - a[1]) * k); b2 = (b[0] + (c[0] - b[0]) * k, b[1] + (c[1] - b[1]) * k)
                a3 = (a2[0] + (b2[0] - a2[0]) * 0.12, a2[1] + (b2[1] - a2[1]) * 0.12); b3 = (b2[0] + (a2[0] - b2[0]) * 0.12, b2[1] + (a2[1] - b2[1]) * 0.12)
                s.line(a3, b3, "#ffffff", 3.6); s.line(a3, b3, INK, 1.6)
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
    """One card per bar shape: the cross-section with sizes and angles, and the table saw seen from the front."""
    bts = plan["bar_types"]; W, H = 470, 536
    used = {}; out = {}
    for b in plan["bars"]: used.setdefault(b["bar"], []).append(b)
    wood = {w["key"]: w for w in plan["woods"]}
    T = lambda x, y, s_, size=11, anchor="middle", fill=INK, weight="400": (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">{html.escape(s_)}</text>')
    for n, bt in enumerate(bts):
        el = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">'
              f'<title>Bar {bt["id"]}: cross-section and saw setup</title><rect width="100%" height="100%" fill="#fff"/>']
        pts = _flat(bt["pts"]); b = bbox_of([pts]); bw, bh = b[2] - b[0], b[3] - b[1]
        sc = min(190 / bw, 104 / bh)
        P = lambda x, y: (W / 2 + (x - (b[0] + b[2]) / 2) * sc, 62 + 104 / 2 + bh * sc / 2 - (y - b[1]) * sc)
        fill = wood[used[bt["id"]][0]["species"]]["end"] if bt["id"] in used else "#ddd"
        el.append(T(W / 2, 26.5, "The section", 11, weight="600"))
        el.append('<polygon points="' + " ".join("%.1f,%.1f" % P(*v) for v in pts) + f'" fill="{fill}" stroke="{INK}" stroke-width="1.4"/>')
        c = centroid(pts); cx, cy = P(*c); k = len(pts)
        for i in range(k):
            a, bb_ = pts[i - 1], pts[i]; m = P((a[0] + bb_[0]) / 2, (a[1] + bb_[1]) / 2)
            dx, dy = m[0] - cx, m[1] - cy; d = math.hypot(dx, dy) or 1
            el.append(T(m[0] + dx / d * 30, m[1] + dy / d * 15 + 4, short(math.dist(a, bb_)), 11.5))
        for i, v in enumerate(pts):
            q = P(*v); dx, dy = q[0] - cx, q[1] - cy; d = math.hypot(dx, dy) or 1
            a_, c_ = pts[i - 1], pts[(i + 1) % k]
            v1 = (a_[0] - v[0], a_[1] - v[1]); v2 = (c_[0] - v[0], c_[1] - v[1])
            angd = math.degrees(math.acos(max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2))))))
            el.append(T(q[0] + dx / d * 20, q[1] + dy / d * 13 + 4, f"{angd:.0f}°", 10.5, fill="#5b6167"))
        uses = "; ".join(f'{x["total_bars"]} + {x["total_spares"]} spare, {wood[x["species"]]["name"].split()[-1].lower()}' for x in used.get(bt["id"], []))
        el.append(T(W / 2, 206, uses, 11))
        # the saw from the front
        t = bt.get("stock") or bh; tilt = bt["tilt"] or 0; tt = t * math.tan(math.radians(tilt)); w = bt.get("stop") or bw; mode = bt.get("setup"); K = 0.125
        el.append(f'<line x1="16" y1="222" x2="{W - 16}" y2="222" stroke="#d9d4c7"/>')
        if mode:
            Wb = max(w + 0.7, min(2.2 * w, 3.4)); fh = max(1.7, t + 0.45); D = 0.5 if mode != "square" else 0.0
            if mode == "square":
                x_lo, x_hi = -Wb - 0.2, K + w + 1.0
            elif mode == "flip":
                x_lo, x_hi = -w - 1.9, K + Wb + 2.6; fh = t + 1.2
            else:
                xf = K + w if mode == "para" else K - tt + w
                x_lo, x_hi = -tt - 1.5, xf + 3.3; fh = t + 1.2
            kk = min((W - 60) / (x_hi - x_lo), 182 / (fh + 0.5 + D)); y0 = H - 102 - D * kk
            X = lambda x: 30 + ((W - 60) - (x_hi - x_lo) * kk) / 2 + (x - x_lo) * kk
            Y = lambda y: y0 - y * kk
            pg = lambda q, f, st=INK, sw=1.2, dash="": ('<polygon points="' + " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in q) + f'" fill="{f}" stroke="{st}" stroke-width="{sw}"'
                                                       + (f' stroke-dasharray="{dash}"' if dash else "") + '/>')
            R = lambda x0, x1, ya_, yb_, f=MDF, st=MDF_E: pg([(x0, ya_), (x1, ya_), (x1, yb_), (x0, yb_)], f, st)
            blank_c = "#f3ead8"; dimy = 0.0; lab = "bar width as sawn, at the table"
            def clamp(xp, xc, top):
                """Toggle clamp: base at xc on the deck, arm over to a caul lying on the work at xp."""
                hy = top + 0.75
                return (R(xp - 0.25, xp + 0.25, top, top + 0.38, "#e9dfc6", INK) + R(xc - 0.3, xc + 0.3, 0, 0.3, "#9aa3ab", "#59616a")
                        + f'<path d="M{X(xc):.1f},{Y(0.3):.1f} V{Y(hy):.1f} H{X(xp):.1f} V{Y(top + 0.38):.1f}" fill="none" stroke="#59616a" stroke-width="3" stroke-linejoin="round"/>'
                        + T(X((xp + xc) / 2), Y(hy) - 6, "toggle clamp on a caul", 10.5))
            if mode == "square":
                el.append(pg([(-Wb, 0), (0, 0), (0, t), (-Wb, t)], blank_c)); el.append(pg([(K, 0), (K + w, 0), (K + w, t), (K, t)], fill, sw=1.5))
                el.append(pg([(K + w, 0), (K + w + 0.8, 0), (K + w + 0.8, fh), (K + w, fh)], MDF, MDF_E))
                el.append(T(X(K + w + 0.4), Y(fh) - 6, "fence", 10.5)); el.append(T(X(-Wb / 2), Y(t / 2) + 4, "blank", 10.5)); barx = K + w / 2
                d0, d1 = K, K + w
            else:
                el.append(R(x_lo + 0.25, -0.02, -D, 0, "#e6dcc3", MDF_E)); el.append(R(K + 0.02, x_hi - 0.85, -D, 0, "#e6dcc3", MDF_E))
                el.append(R(x_hi - 0.85, x_hi - 0.1, -D, 1.3)); el.append(T(X(x_hi - 0.48), Y(1.3) - 6, "rip fence", 10.5))
                if mode == "flip":
                    bar = [(-w, 0), (0, 0), (-tt, t), (-w + tt, t)]
                    el.append(pg([(K, 0), (K + Wb, 0), (K + Wb, t), (K - tt, t)], blank_c))
                    nx = (K + w - 2 * tt, K + w - tt)
                    if nx[0] > K + 0.05 and max(nx) < K + Wb - 0.05:
                        el.append(f'<line x1="{X(nx[0]):.1f}" y1="{Y(0):.1f}" x2="{X(nx[1]):.1f}" y2="{Y(t):.1f}" stroke="{CUT}" stroke-width="1" stroke-dasharray="4 3"/>')
                    el.append(pg(bar, fill, sw=1.5))
                    hs = min(0.75, t - 0.08); el.append(pg([(-w - 0.9, 0), (-w, 0), (-w + hs * math.tan(math.radians(tilt)), hs), (-w - 0.9, hs)], MDF, MDF_E)); el.append(T(X(-w - 0.5), Y(hs) - 6, "leaning stop", 10.5))
                    el.append(clamp(K + Wb * 0.62, K + Wb + 0.75, t)); el.append(T(X(K + Wb * 0.62), Y(t / 2) + 4, "blank", 10.5))
                    barx, bary = -w / 2, t * 0.36; d0, d1 = -w, 0
                else:
                    bar = [(K, 0), (K + w, 0), (K + w - tt, t), (K - tt, t)] if mode == "para" else [(K, 0), (xf - tt, 0), (xf, t), (K - tt, t)]
                    el.append(pg([(-tt, 0), (0, 0), (-tt, t)], "#fff", "#8d8676", 1, "3 3")); el.append(T(X(-tt) - 6, Y(t / 2) + 4, "waste", 10, "end", "#5b6167"))
                    el.append(pg(bar, fill, sw=1.5))
                    el.append(R(xf, xf + 0.75, 0, max(1.0, t + 0.2))); el.append(T(X(xf + 0.38), Y(-D) + 30, "locating fence", 10.5))
                    el.append(clamp((max(bar[0][0], bar[3][0]) + min(bar[1][0], bar[2][0])) / 2, xf + 1.5, t))
                    barx, bary = sum(v[0] for v in bar) / 4, t * 0.5
                    if mode == "para": d0, d1 = K, K + w; lab = "the face on the deck, as sawn"
                    else: d0, d1 = K - tt, xf; dimy = t; lab = "the wide face, as sawn"
            # blade
            ya, yb = -D, t + 0.55; xa = K / 2 + ya * math.tan(math.radians(tilt)) * -1; xb = K / 2 - yb * math.tan(math.radians(tilt))
            el.append(f'<line x1="{X(xa):.1f}" y1="{Y(ya):.1f}" x2="{X(xb):.1f}" y2="{Y(yb):.1f}" stroke="#7d848b" stroke-width="{max(2.5, K * kk):.1f}"/>')
            el.append(T(X(xb) - (8 if tilt else 0), Y(yb) - 6, f"blade {tilt:.0f}°" if tilt else "blade square", 10.5, "end" if tilt else "middle", fill="#5b6167"))
            el.append(f'<line x1="{X(x_lo):.1f}" y1="{Y(-D):.1f}" x2="{X(x_hi):.1f}" y2="{Y(-D):.1f}" stroke="{INK}" stroke-width="2"/>')
            if mode == "square": bary = t * 0.5
            el.append(f'<circle cx="{X(barx):.1f}" cy="{Y(bary):.1f}" r="9" fill="#fff" stroke="{INK}" stroke-width="1.1"/>' + T(X(barx), Y(bary) + 4, bt["id"], 10.5, weight="600"))
            if dimy:
                yd = Y(dimy) - 30
                el.append(f'<path d="M{X(d0):.1f},{yd - 4} v8 M{X(d1):.1f},{yd - 4} v8 M{X(d0):.1f},{yd} H{X(d1):.1f}" stroke="{REF}" stroke-width="1.1" fill="none"/>')
                el.append(_dimlab(T, X(d0), X(d1), yd, short(w)))
            else:
                yd = Y(-D) + 9
                el.append(f'<path d="M{X(d0):.1f},{yd - 4} v8 M{X(d1):.1f},{yd - 4} v8 M{X(d0):.1f},{yd} H{X(d1):.1f}" stroke="{REF}" stroke-width="1.1" fill="none"/>')
                el.append(_dimlab(T, X(d0), X(d1), yd, short(w)))
            cap = {"para": "roll the strip over for the second bevel", "trap": "turn the strip end for end for the second bevel", "flip": "turn the blank end for end every pass",
                   "square": "bar between blade and fence"}[mode]
            el.append(T(W / 2, 240, "The saw from the front" + ("" if mode == "square" else ", second bevel" if mode != "flip" else ""), 11, weight="600"))
            el.append(T(W / 2, H - 42, f"strip {short(bt['strip'])} wide, {short(t)} thick" if bt.get("strip") else f"blank {short(t)} thick", 10.5, weight="600"))
            el.append(T(W / 2, H - 26, cap, 10.5))
            el.append(T(W / 2, H - 10, "red figure: " + lab, 10.5, fill="#5b6167"))
        else:
            el.append(T(W / 2, 300, f"blank {short(t)} thick · see the steps beside this drawing", 11))
        el.append("</svg>"); out[f"bar_{bt['id']}"] = "".join(el)
    return out


def _dimlab(T, xa, xb, yd, txt):
    """Dimension figure: on the line when the line is long enough, beside it when it is not."""
    if abs(xb - xa) >= 64:
        xm = (xa + xb) / 2
        return f'<rect x="{xm - 24:.1f}" y="{yd - 8}" width="48" height="16" fill="#fff"/>' + T(xm, yd + 4, txt, 11, fill=REF, weight="600")
    return T(max(xa, xb) + 8, yd + 4, txt, 11, fill=REF, weight="600", anchor="start")


def _flat(pts):
    """Turn a cross-section so its longest side lies on the table."""
    pts = [tuple(p) for p in pts]; n = len(pts)
    i = max(range(n), key=lambda i: math.dist(pts[i], pts[(i + 1) % n]))
    a, b = pts[i], pts[(i + 1) % n]; ang = -math.atan2(b[1] - a[1], b[0] - a[0]); c, s_ = math.cos(ang), math.sin(ang)
    out = [((x - a[0]) * c - (y - a[1]) * s_, (x - a[0]) * s_ + (y - a[1]) * c) for x, y in pts]
    if sum(y for _, y in out) < 0: out = [(x, -y) for x, y in out][::-1]
    return out


def _vb(plan, size, h=None):
    return CB._vb(plan, size, h)


def _cradle(s, cx, hb, tape=True, layers=True):
    """A V block, end view: two side pieces hb high on a base, faces at 60 degrees."""
    e = hb / S3 + 0.75
    s.poly([(cx - e - 0.15, -0.3), (cx + e + 0.15, -0.3), (cx + e + 0.15, 0), (cx - e - 0.15, 0)], MDF, MDF_E, 1)
    for sg in (-1, 1):
        s.poly([(cx, 0), (cx + sg * hb / S3, hb), (cx + sg * e, hb), (cx + sg * e, 0)], MDF, MDF_E, 1)
        if layers:
            y = 0.75
            while y < hb - 0.05:
                s.line((cx + sg * y / S3, y), (cx + sg * e, y), MDF_E, 0.6); y += 0.75
        if tape: s.line((cx, 0), (cx + sg * hb / S3, hb), "#c9a227", 2.2)


def _ref_tick(s, part, sh=0.0):
    if "ref" not in part: return
    a, b = part["ref"]; c = _cen(part["pts"]); k = 0.2
    a2 = (a[0] + (c[0] - a[0]) * k + sh, a[1] + (c[1] - a[1]) * k); b2 = (b[0] + (c[0] - b[0]) * k + sh, b[1] + (c[1] - b[1]) * k)
    a3 = (a2[0] + (b2[0] - a2[0]) * 0.18, a2[1] + (b2[1] - a2[1]) * 0.18); b3 = (b2[0] + (a2[0] - b2[0]) * 0.18, b2[1] + (a2[1] - b2[1]) * 0.18)
    s.line(a3, b3, "#ffffff", 5.0); s.line(a3, b3, INK, 2.4)


def log_stages(plan, lg):
    """End view of a log, one panel per glue-up: what goes in, where the glue goes, how it is held."""
    st = lg["stages"]; w, h = lg["w"], lg["h"]; tri = lg["kind"] == "tri"; shape = lg["shape"]
    if shape == "half":       # drawn as it is glued: the two trued star-corner faces down on the flat base, joint upright
        tp = lambda pts: [(y, w - x) for x, y in pts]
        st = [dict(g, parts=[dict(p, pts=tp(p["pts"]), **({"cells": [(r, tp(c)) for r, c in p["cells"]]} if "cells" in p else {})) for p in g["parts"]]) for g in st]
        w, h = h, w
    gapx = w + (2.4 if tri else 2.6); n = len(st)
    wm = max(l["w"] for l in plan["logs"]); hm = max(l["h"] for l in plan["logs"])
    sc = min(96, 520 / (n * gapx), 250 / (h + 2.35))
    x0 = -w / 2 - 1.2 if tri else -1.3
    s = Svg((x0, -0.75, x0 + n * gapx, h + 1.6), sc, pad=22, extra_h=18, title=f"{lg['name']}, end view")
    done = []
    for k, stg in enumerate(st):
        sh = k * gapx; solo = n == 1 and len(stg["parts"]) == 1
        top = max(v[1] for p in done + stg["parts"] for v in p["pts"])
        if tri and not solo: _cradle(s, sh, _vb(plan, stg.get("vsize", w), top)["hb"])
        elif shape == "band":
            q = h; s.poly([(sh - 1.0, -0.25), (sh + w + 0.9, -0.25), (sh + w + 0.9, 0), (sh - 1.0, 0)], MDF, MDF_E, 1)
            s.poly([(sh - 0.9, 0), (sh, 0), (sh + q + 0.12, q + 0.12), (sh - 0.9, q + 0.12)], MDF, MDF_E, 1)
            s.poly([(sh + w, 0), (sh + w + 0.45, 0), (sh + w + 0.45, q + 0.1), (sh + w, q + 0.1)], MDF, MDF_E, 1)
            s.poly([(sh + q + 0.2, q), (sh + w - 0.05, q), (sh + w - 0.05, q + 0.26), (sh + q + 0.2, q + 0.26)], MDF, MDF_E, 1)
        elif shape == "quarter":
            lw = max(0.4, w - 0.4)
            s.poly([(sh - 0.28, -0.28), (sh + lw, -0.28), (sh + lw, 0), (sh, 0), (sh, lw), (sh - 0.28, lw)], MDF, MDF_E, 1)
            s.poly([(sh + w + 0.28, h + 0.28), (sh + w - lw, h + 0.28), (sh + w - lw, h), (sh + w, h), (sh + w, h - lw), (sh + w + 0.28, h - lw)], MDF, MDF_E, 1)
        elif shape == "hex":
            c0 = (sh + w / 2, h / 2)
            band = [(c0[0] + (x - w / 2) * 1.07, c0[1] + (y - h / 2) * 1.07) for x, y in lg["outline"]]
            s.poly(band, "#8fb8e8", "#3f78c0", 1.2, op=0.55)
        elif not solo and not tri:
            s.line((sh - 0.6, 0), (sh + w + 0.6, 0), MDF_E, 2)
        for p in done: _draw_part(s, plan, p, sh, op=0.45, label=False, bold=False)
        for p in stg["parts"]: _draw_part(s, plan, p, sh, label=False)
        newp = [[(x + sh, y) for x, y in p["pts"]] for p in stg["parts"]]
        oldp = [[(x + sh, y) for x, y in p["pts"]] for p in done]
        for a, b in _glue_edges(newp, oldp): s.line(a, b, GLUE, 3.4)
        for p in stg["parts"]:
            _ref_tick(s, p, sh)
            c = centroid(p["pts"]) if "log" not in p else _cen(p["pts"])
            _chip(s, (c[0] + sh, c[1]), (p["log"] + ("′" if p.get("flip") else "")) if "log" in p else p["bar"], r=9, size=10.5)
        if solo: pass
        elif shape == "hex":
            s.text((sh + w / 2, -0.45), "painter's tape wrapped tight round the bundle", 10.5)
        elif tri:
            hw = top / S3 - 0.08
            s.poly([(sh - hw, top), (sh + hw, top), (sh + hw, top + 0.28), (sh - hw, top + 0.28)], MDF, MDF_E, 1)
            _arrow(s, (sh, top + 1.12), (sh, top + 0.32))
        elif shape == "band":
            _arrow(s, (sh + w + 1.25, h / 2), (sh + w + 0.5, h / 2)); _arrow(s, (sh + (h + w) / 2, h + 1.1), (sh + (h + w) / 2, h + 0.3))
        elif shape == "quarter":
            _arrow(s, (sh + w + 1.15, h / 2), (sh + w + 0.33, h / 2)); _arrow(s, (sh + w / 2, h + 1.15), (sh + w / 2, h + 0.33))
        else:
            cs = [_cen(p["pts"]) for p in stg["parts"]]
            if max(c[1] for c in cs) - min(c[1] for c in cs) > max(c[0] for c in cs) - min(c[0] for c in cs) and lg["kind"] != "panel":
                _arrow(s, (sh + w / 2, top + 0.95), (sh + w / 2, top + 0.08)); _arrow(s, (sh + w / 2, -0.75), (sh + w / 2, -0.06))
            else:
                _arrow(s, (sh - 0.95, h / 2), (sh - 0.06, h / 2)); _arrow(s, (sh + w + 0.95, h / 2), (sh + w + 0.06, h / 2))
                if shape == "half":
                    s.poly([(sh + 0.1, h), (sh + w - 0.1, h), (sh + w - 0.1, h + 0.24), (sh + 0.1, h + 0.24)], MDF, MDF_E, 1); s.text((sh + w / 2, h + 0.5), "caul", 10.5)
        lab = "Solid bar, no glue-up" if solo else f"Glue-up {k + 1}" if n > 1 else "One glue-up, held by tape" if shape == "hex" else "One glue-up"
        s.text((sh + (0 if tri else w / 2), h + 1.72), lab, 12, weight="600")
        if tri and not solo: s.text((sh, h + 1.42), _vb(plan, stg.get('vsize', w), top)['name'], 10.5)
        done += stg["parts"]
    return s.svg()


def jigs(plan):
    """Every V block at one scale, with what sits in it."""
    vb = plan["vblocks"]; gap = 1.1
    xs = []; x = 0.0
    for v in vb:
        e = v["hb"] / S3 + 0.9; xs.append(x + e); x += 2 * e + gap
    Hm = max(v["size"] for v in vb) * S3 / 2
    sc = min(64, 720 / x)
    s = Svg((-0.2, -1.8, x - gap + 0.2, Hm + 0.7), sc, pad=24, extra_h=4, title="V blocks, end view")
    bt = {f"bar {b['id']}": b for b in plan["bar_types"]}
    for v, cx in zip(vb, xs):
        S_ = v["size"]; H = S_ * S3 / 2
        _cradle(s, cx, v["hb"])
        trap = next((bt[u] for u in v["uses"] if u in bt and bt[u]["kind"] == "trapezoid" and abs(bt[u].get("vwall", -1) - v["hb"]) < 0.13), None)
        if not trap and v["hb"] < H - 0.4:       # a first glue-up: flat-topped, 3/16" above the sides
            ht = v["hb"] + 0.1875
            s.poly([(cx, 0), (cx + ht / S3, ht), (cx - ht / S3, ht)], "#f3ead8", INK, 1.2); s.line((cx - ht / S3, ht), (cx + ht / S3, ht), CUT, 2.4)
            s.poly([(cx, 0), (cx + S_ / 2, H), (cx - S_ / 2, H)], "none", INK, 0.9, dash="5 4")
            trap = "done"
        if trap == "done": pass
        elif trap:
            leg = trap["dims"]["leg"]
            s.poly([(cx, 0), (cx + leg / 2, leg * S3 / 2), (cx - S_ / 2 + leg, H), (cx - S_ / 2, H)], "#f3ead8", INK, 1.2)
            s.line((cx - S_ / 2, H), (cx - S_ / 2 + leg, H), CUT, 2.4)
            s.poly([(cx, 0), (cx + S_ / 2, H), (cx - S_ / 2, H)], "none", INK, 0.9, dash="5 4")
        else:
            s.poly([(cx, 0), (cx + S_ / 2, H), (cx - S_ / 2, H)], "#f3ead8", INK, 1.2)
            s.line((cx - S_ / 2, H), (cx + S_ / 2, H), CUT, 2.4)
        s.text((cx, -0.78), f"sides {short(v['hb'])} high", 11.5, weight="600")
        us = list(v["uses"]); h_ = (len(us) + 1) // 2 if len(", ".join(us)) > 24 else len(us)
        s.text((cx, -1.26), ", ".join(us[:h_]) + ("," if us[h_:] else ""), 10.5, fill="#5b6167")
        if us[h_:]: s.text((cx, -1.56), ", ".join(us[h_:]), 10.5, fill="#5b6167")
    s.text(((x - gap) / 2, Hm + 0.78), "the part stands 3/16\" proud · red: the face being sanded", 11.5)
    s.text(((x - gap) / 2, Hm + 0.42), "tape lines the V · one side slackens for gluing", 11.5)
    return s.svg()


def ripsled(plan):
    """The rip sled seen from above."""
    Ls = math.ceil(max(bl["blank_length"] for b in plan["bars"] for bl in b["lengths"]) + 8)
    s = Svg((-1.5, -4.6, Ls + 1.5, 20.5), 560 / (Ls + 3), pad=16, extra_h=4, title="Rip sled, from above")
    ply = "#e6dcc3"
    s.poly([(-1.5, 16), (Ls + 1.5, 16), (Ls + 1.5, 18.4), (-1.5, 18.4)], MDF, MDF_E, 1); s.text((Ls / 2, 17.55), "rip fence, stays put", 12)
    s.poly([(0, 7), (Ls, 7), (Ls, 16), (0, 16)], ply, MDF_E, 1); s.poly([(0, 0), (Ls, 0), (Ls, 6.8), (0, 6.8)], ply, MDF_E, 1)
    for x in (0, Ls - 0.75): s.poly([(x, 0), (x + 0.75, 0), (x + 0.75, 16), (x, 16)], "#cdbf9c", MDF_E, 1)
    s.line((-1.2, 6.9), (Ls + 1.9, 6.9), CUT, 1.8, dash="7 4")
    s.poly([(1.5, 9.6), (Ls - 1.5, 9.6), (Ls - 1.5, 10.35), (1.5, 10.35)], MDF, MDF_E, 1)
    s.poly([(1.5, 7.05), (Ls - 1.5, 7.05), (Ls - 1.5, 9.6), (1.5, 9.6)], "#f3ead8", INK, 1.1)
    s.poly([(2.5, 8.0), (Ls - 2.5, 8.0), (Ls - 2.5, 8.7), (2.5, 8.7)], "#d9c9a0", INK, 0.9)
    for fx in (0.2, 0.5, 0.8):
        x = Ls * fx; s.poly([(x - 0.9, 11.2), (x + 0.9, 11.2), (x + 0.9, 13.2), (x - 0.9, 13.2)], "#9aa3ab", "#59616a", 1); s.line((x, 11.2), (x, 8.35), "#59616a", 4)
    has_tri = any("triangle" in bt.get("kind", "") for bt in plan["bar_types"])
    if has_tri: s.poly([(1.5, 4.3), (Ls - 1.5, 4.3), (Ls - 1.5, 4.9), (1.5, 4.9)], MDF, MDF_E, 1)
    s.text((Ls / 2, 14.9), "fence deck: three toggle clamps", 12, weight="600")
    for y, yl, lab, x0_, col in ((9.98, 11.4, "locating fence", Ls - 1.5, INK), (9.1, 9.9, "strip", Ls - 1.5, INK), (8.35, 8.4, "caul", Ls - 2.5, INK), (6.9, 6.9, "blade", Ls + 1.2, CUT), (4.6, 4.6, "stop strip, for triangle bars", Ls - 1.5, INK))[:5 if has_tri else 4]:
        if col == INK: s.line((x0_, y), (Ls + 0.4, y), INK, 0.7); s.line((Ls + 0.4, y), (Ls + 1.9, yl), INK, 0.7)
        s.text((Ls + 2.2, yl), lab, 12, anchor="start", fill=col)
    s.text((Ls / 2, 2.2), "landing deck", 12, weight="600")
    s.text((0.4, -1.1), "bridge", 11.5, anchor="start"); s.text((Ls - 0.4, -1.1), "bridge", 11.5, anchor="end")
    _arrow(s, (Ls * 0.38, -1.2), (Ls * 0.62, -1.2), w=4, hw=9, hl=12)
    s.text((Ls / 2, -2.9), "the blade saws the base in two; the 4\" bridges hold the decks together", 11.5)
    return s.svg()


def true_fig(plan):
    lg = next(l for l in plan["logs"] if l["kind"] == "tri"); L = lg["w"]; H = lg["h"]; vb = _vb(plan, L, H)
    sc = min(56, 300 / (L + 2.4))
    s = Svg((-L / 2 - 1.4, -1.0, L / 2 + 1.4, H + 1.5), sc, pad=26, extra_h=0, title="Truing a log in its V block")
    _cradle(s, 0, vb["hb"])
    for r, pts in lg["cells"]: s.poly(pts, plan["species"][r]["end"], INK, 0.8)
    s.poly(lg["outline"], "none", INK, 1.5)
    s.line((-L / 2, H), (L / 2, H), CUT, 2.6)
    cx, cy = s.P(0, H + 0.72); r = 0.66 * sc; s.P(0, H + 1.42)
    s.raw(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="#eee9dc" stroke="{MDF_E}" stroke-width="1.2"/>'
          f'<path d="M{cx - r * .55:.1f},{cy - r * .2:.1f} a{r * .6:.1f},{r * .6:.1f} 0 0 1 {r * 1.1:.1f},0" fill="none" stroke="{INK}" stroke-width="1.2"/>'
          f'<path d="M{cx + r * .55:.1f},{cy - r * .2:.1f} l-7,-2 l4,7 z" fill="{INK}"/>')
    s.text((0, H + 0.6), "drum", 10.5)
    s.text((0, -0.6), "sand the top face, turn the log, repeat", 10.5)
    return s.svg()


def cut_setup(plan):
    """The crosscut sled from the operator's side: how the log is held."""
    lg = max((l for l in plan["logs"] if l["crosscut"]), key=lambda l: l["slices"]); tri = lg["kind"] == "tri"
    w = lg["w"]; h = lg["h"]; sp = plan["species"]; hexl = lg["kind"] == "hex"
    if hexl:                      # lying on one flat: the end view turned a quarter turn
        lg = dict(lg, cells=[(r, [(h - y, x) for x, y in pts]) for r, pts in lg["cells"]]); w, h = h, w
    sc = min(58, 300 / (w + 4.2))
    s = Svg((-2.0, -0.9, w + 2.6, max(h, 2.6) + 0.8), sc, pad=22, extra_h=0, title="Log on the crosscut sled, seen along the cut")
    s.poly([(-1.9, -0.5), (w + 2.5, -0.5), (w + 2.5, 0), (-1.9, 0)], MDF, MDF_E, 1)
    fh = max(h, 2.2) + 0.2
    s.poly([(-1.9, 0), (-1.2, 0), (-1.2, fh), (-1.9, fh)], MDF, MDF_E, 1); s.text((-1.55, fh + 0.22), "sled fence", 10.5)
    if tri:
        cells = [(r, [(w / 2 - x, h - y) for x, y in pts]) for r, pts in lg["cells"]]
        e = h * 0.62; ex = e / S3
        s.poly([(-1.2, 0), (0, 0), (ex, e), (-1.2, e)], MDF, MDF_E, 1)
        s.poly([(w, 0), (w + 1.2, 0), (w + 1.2, e), (w - ex, e)], MDF, MDF_E, 1)
        s.text((-0.5, e / 2), "fixed", 10); s.text((w + 0.62, e / 2), "loose", 10)
        _arrow(s, (w + 2.4, e / 2), (w + 1.25, e / 2))
        s.line((0.3, 0), (w - 0.3, 0), INK, 3)
        s.text((w / 2, -0.75), "reference face down, between two 30° strips", 10.5)
    else:
        cells = [(r, [(x, y) for x, y in pts]) for r, pts in lg["cells"]]
        s.poly([(-1.2, 0), (0, 0), (0, 0.01), (-1.2, 0.01)], MDF, MDF_E, 0.5)
        cells = [(r, [(x - 1.2 + 0.0, y) for x, y in pts]) for r, pts in cells]
        _arrow(s, (w / 2 - 1.2, h + 0.95), (w / 2 - 1.2, h + 0.08)); s.text((w / 2 + 0.2, h + 0.62), "hold-down", 10.5, anchor="start")
        s.text((w / 2, -0.75), "log on one flat, a corner against the fence, clamped down" if hexl else "log against the fence, clamped down", 10.5)
    for r, pts in cells: s.poly(pts, sp[r]["end"], "#1e232760", 0.5)
    xs_ = [v[0] for _, p in cells for v in p]; ys_ = [v[1] for _, p in cells for v in p]
    out = [(0, 0), (w, 0), (w / 2, h)] if tri else [(-1.2, h / 2), (-1.2 + w / 4, 0), (-1.2 + 3 * w / 4, 0), (-1.2 + w, h / 2), (-1.2 + 3 * w / 4, h), (-1.2 + w / 4, h)] if hexl else [(min(xs_), 0), (max(xs_), 0), (max(xs_), max(ys_)), (min(xs_), max(ys_))]
    s.poly(out, "none", INK, 1.5)
    return s.svg()


def row_fig(plan):
    rows = plan["rows"]; sp = plan["species"]; kind = plan["info"]["kind"]
    r = max(rows, key=lambda r_: len(r_["pucks"]))
    ang = math.radians(plan["info"].get("angle", 0)); c, sn = math.cos(ang), math.sin(ang)
    G = lambda p: (p[0] * c + p[1] * sn, -p[0] * sn + p[1] * c)
    pk = [{"pts": [G(v) for v in q["pts"]], "cells": [(ro, [G(v) for v in pts]) for ro, pts in q["cells"]], "log": q["log"], "flip": q["flip"]} for q in r["pucks"]]
    pk.sort(key=lambda q: _cen(q["pts"])[0]); more = len(pk) > 6 and kind == "tri"
    if more: pk = pk[:6]
    b = bbox_of([q["pts"] for q in pk]); hgt = b[3] - b[1]; fw = max(0.5, 0.3 * hgt)
    wg = 0.55 if kind != "panel" else 0
    bb = (b[0] - 1.9, b[1] - fw - 0.75, b[2] + 1.9, b[3] + fw + wg + (0.9 if wg else 0.5))
    sc = min(700 / (bb[2] - bb[0]), 78)
    s = Svg(bb, sc, pad=22, extra_h=20, title=f"Row {r['n']} in the row jig, seen from above")
    if more: s.text((b[2] + 1.2, b[1] - fw - 0.35), f"first 6 of the {len(r['pucks'])} slices in row {r['n']}", 10.5, anchor="end")
    if kind != "panel":
        s.poly([(b[0] - 1.2, b[1] - fw), (b[2] + 1.2, b[1] - fw), (b[2] + 1.2, b[1]), (b[0] - 1.2, b[1])], MDF, MDF_E, 1)
        s.text(((b[0] + b[2]) / 2, b[1] - fw / 2), "fixed fence, screwed down", 10.5)
        segs = []
        for q in pk:      # one loose block behind every slice whose base is on this side
            xs_ = sorted(v[0] for v in q["pts"] if abs(v[1] - b[3]) < 1e-3)
            if len(xs_) >= 2 and xs_[-1] - xs_[0] > 0.2: segs.append((xs_[0] + 0.04, xs_[-1] - 0.04))
        if not segs: segs = [(b[0] - 0.6, b[2] + 0.6)]
        for xa, xb in segs: s.poly([(xa, b[3]), (xb, b[3]), (xb, b[3] + fw), (xa, b[3] + fw)], MDF, MDF_E, 1)
        s.text((b[2] + 0.25, b[3] + fw / 2), "loose blocks", 10.5, anchor="start")
        y1 = b[3] + fw; y2 = y1 + wg
        s.poly([(b[0] - 1.2, y2), (b[2] + 1.2, y2), (b[2] + 1.2, y2 + 0.3), (b[0] - 1.2, y2 + 0.3)], MDF, MDF_E, 1)
        s.text(((b[0] + b[2]) / 2, y2 + 0.15), "cleat, screwed down", 10.5)
        for xa, xb in segs:
            x = (xa + xb) / 2 - 0.5
            s.poly([(x, y1), (x + 1.0, y1), (x + 1.0, y1 + wg * 0.45), (x, y2)], "#e9c46a", "#9c7a1e", 1)
        s.text((b[2] + 0.25, y1 + wg / 2), "a wedge each", 10.5, anchor="start")
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
        s.text((b[0] - 1.2, b[1] - fw - 0.35), "end blocks: a spare slice cut in half", 10.5, anchor="start")
    _arrow(s, (b[0] - 1.75, (b[1] + b[3]) / 2), (b[0] - 0.08, (b[1] + b[3]) / 2)); _arrow(s, (b[2] + 1.75, (b[1] + b[3]) / 2), (b[2] + 0.08, (b[1] + b[3]) / 2))
    if kind != "panel": s.dimy(b[1], b[3], b[0] - 1.25, short(hgt))
    return s.svg()


def board_fig(plan):
    rows = plan["rows"]; sp = plan["species"]
    ang = math.radians(plan["info"].get("angle", 0)); nrm = (-math.sin(ang), math.cos(ang)); u = (math.cos(ang), math.sin(ang))
    gap = 0.9; n = len(rows)
    pr = [sum(v[0] * nrm[0] + v[1] * nrm[1] for v in r["pts"]) / len(r["pts"]) for r in rows]
    rank = {i: k for k, i in enumerate(sorted(range(n), key=lambda i: pr[i]))}
    off = [((rank[i] - (n - 1) / 2) * gap * nrm[0], (rank[i] - (n - 1) / 2) * gap * nrm[1]) for i in range(n)]
    mv = lambda pts, o: [(x + o[0], y + o[1]) for x, y in pts]
    allp = [mv(r["pts"], o) for r, o in zip(rows, off)]
    b = bbox_of(allp); m = 1.7
    bb = (b[0] - m, b[1] - m, b[2] + m, b[3] + m)
    sc = min(640 / (bb[2] - bb[0]), 640 / (bb[3] - bb[1]))
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
    for t in (-0.68, 0.68):   # cauls across the rows
        a = (cx + u[0] * t * ext_u, cy + u[1] * t * ext_u); hw = 0.28
        q = [(a[0] + nrm[0] * sg1 * (ext_n + 0.9) + u[0] * sg2 * hw, a[1] + nrm[1] * sg1 * (ext_n + 0.9) + u[1] * sg2 * hw) for sg1, sg2 in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        s.poly(q, MDF, MDF_E, 1.2, dash="6 4", op=0.25)
    a = (cx + u[0] * 0.68 * ext_u, cy + u[1] * 0.68 * ext_u)
    if abs(nrm[0]) > 0.5:
        sgx = 1 if nrm[0] > 0 else -1
        s.text((cx + u[0] * 0.86 * ext_u + sgx * nrm[0] * (ext_n + 0.3), cy + u[1] * 0.86 * ext_u), "cauls across (dashed), near each end", 11, anchor="start")
    else:
        sgy = 1 if nrm[1] > 0 else -1
        s.text((cx, cy + sgy * nrm[1] * (ext_n + 1.95)), "cauls across the rows (dashed), near each end", 11)
    for r, o in zip(rows, off):
        c = _cen(mv(r["pts"], o)); half = r["length"] / 2 + 0.45
        s.text((c[0] - u[0] * half, c[1] - u[1] * half), f"R{r['n']}", 11, weight="600", fill=REF)
    return s.svg()


def hexboard_fig(plan):
    """Every puck glued at once inside a clamped frame of four boards."""
    rows = plan["rows"]; sp = plan["species"]
    b = bbox_of([pk["pts"] for r in rows for pk in r["pucks"]]); fw = 0.75; m = 2.3
    sc = min(600 / (b[2] - b[0] + 2 * m), 640 / (b[3] - b[1] + 2 * m))
    s = Svg((b[0] - m, b[1] - m, b[2] + m, b[3] + m), sc, pad=20, extra_h=20, title="Pucks glued inside the clamped frame, seen from above")
    for r in rows:
        for pk in r["pucks"]:
            for ro, pts in pk["cells"]: s.poly(pts, sp[ro]["end"], "#1e232730", 0.3)
            s.poly(pk["pts"], "none", INK, 1.0)
    ex = 1.6
    for x0, x1 in ((b[0] - fw, b[0]), (b[2], b[2] + fw)): s.poly([(x0, b[1] - ex), (x1, b[1] - ex), (x1, b[3] + ex), (x0, b[3] + ex)], MDF, MDF_E, 1.2)
    for y0, y1 in ((b[1] - fw, b[1]), (b[3], b[3] + fw)): s.poly([(b[0], y0), (b[2], y0), (b[2], y1), (b[0], y1)], MDF, MDF_E, 1.2)
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    for f in (0.2, 0.5, 0.8):
        y = b[1] + f * (b[3] - b[1]); x = b[0] + f * (b[2] - b[0])
        _arrow(s, (b[0] - fw - 1.3, y), (b[0] - fw - 0.08, y)); _arrow(s, (b[2] + fw + 1.3, y), (b[2] + fw + 0.08, y))
        if f != 0.5: continue
        _arrow(s, (x, b[1] - fw - 1.3), (x, b[1] - fw - 0.08)); _arrow(s, (x, b[3] + fw + 1.3), (x, b[3] + fw + 0.08))
    for f in (0.27, 0.73):
        x = b[0] + f * (b[2] - b[0])
        s.poly([(x - 0.3, b[1] - fw - 1.2), (x + 0.3, b[1] - fw - 1.2), (x + 0.3, b[3] + fw + 1.2), (x - 0.3, b[3] + fw + 1.2)], MDF, MDF_E, 1.2, dash="6 4", op=0.25)
    c = max((pk for r in rows for pk in r["pucks"] if not pk.get("half")), key=lambda pk: -math.dist(_cen(pk["pts"]), (cx, cy)))
    _chip(s, _cen(c["pts"]), "1", r=11, fill="#ffe9a8")
    s.text((cx, b[3] + fw + 1.75), "four 1x3 boards lying flat, bar clamps over the top at the arrows; start at puck 1", 11)
    s.text((cx, b[1] - fw - 1.75), "dashed: two cauls lengthwise on the pucks, ends clamped down to the base", 11)
    return s.svg()


def trim_fig(plan):
    bd = plan["board"]; g = bd["glued"]; trim = bd["trim"]; sp = plan["species"]
    bb = (g[0] - 0.4, g[1] - 0.4, g[2] + 0.4, g[3] + 0.9)
    sc = min(520 / (bb[2] - bb[0]), 620 / (bb[3] - bb[1]))
    s = Svg(bb, sc, pad=56, extra_h=10, title="Trim lines on the flattened board")
    for r in plan["rows"]:
        for pk in r["pucks"]:
            for ro, pts in pk["cells"]: s.poly(pts, sp[ro]["end"], "#1e232730", 0.3, op=0.45)
            if plan["info"]["kind"] == "hex": s.poly(pk["pts"], "none", INK, 0.9)
        if plan["info"]["kind"] != "hex": s.poly(r["pts"], "none", INK, 0.9)
    for f in plan["face"]:
        if f["role"] not in ("frame", "liner"): s.poly(f["pts"], sp[f["role"]]["end"], "#1e232740", 0.3)
    s.poly([(trim[0], trim[1]), (trim[2], trim[1]), (trim[2], trim[3]), (trim[0], trim[3])], stroke=CUT, sw=1.8, dash="7 4")
    s.dimx(trim[0], trim[2], g[1], short(bd["field"][0])); s.dimy(trim[1], trim[3], g[0], short(bd["field"][1]))
    m = bd["margins"]; f = bd["full"]
    px = trim[0] + 0.3 * (trim[2] - trim[0]); py = trim[1] + 0.3 * (trim[3] - trim[1])
    def tag(x, y, lab, dx, dy):
        X, Y = s.P(x, y); X += dx; Y += dy; wd = 7.2 * len(lab) + 12
        s.raw(f'<rect x="{X - wd / 2:.1f}" y="{Y - 10:.1f}" width="{wd:.1f}" height="19" rx="3" fill="#fff" stroke="{REF}" stroke-width="1"/>'
              f'<text x="{X:.1f}" y="{Y + 4:.1f}" font-size="11" text-anchor="middle" fill="{REF}" font-weight="600">{html.escape(lab)}</text>')
    s.line((f[0], py), (trim[0], py), REF, 2.2); tag(trim[0], py, short(m[0]), 30, 0)
    s.line((px, f[1]), (px, trim[1]), REF, 2.2); tag(px, trim[1], short(m[2]), 0, -18)
    s.text(((g[0] + g[2]) / 2, g[3] + 0.5), "red tags: how far inside the edge, or its deepest notch, the first two cuts go", 10.5)
    return s.svg()


def frame_fig(plan):
    bd = plan["board"]; fr = bd["frame"]; t = bd["trim"]; o = fr["outer"]; sp = plan["species"]; ov = 0.5
    bb = (o[0] - 1.6, o[1] - 2.2, o[2] + 1.6, o[3] + 1.6)
    sc = min(520 / (bb[2] - bb[0]), 600 / (bb[3] - bb[1]))
    s = Svg(bb, sc, pad=30, extra_h=22, title="The frame, seen from above")
    for f in plan["face"]:
        if f["role"] not in ("frame", "liner"): s.poly(f["pts"], sp[f["role"]]["end"], "#1e232730", 0.3, op=0.5)
    rings = fr["rings"]
    for ri, r in enumerate(rings):
        col = sp[r["role"]]["end"]; last = ri == len(rings) - 1; fw = r["width"]; ti = r["inner"]
        for k, (a, b, c, d) in enumerate(r["pieces"]):
            horiz = (c - a) > (d - b); e = ov if (k < 2 and last) else 0
            if horiz: a -= e; c += e
            else: b -= e; d += e
            s.poly([(a, b), (c, b), (c, d), (a, d)], col, INK, 1.3 if last else 0.8)
            if not last: continue
            n = r["per_side"][0 if k < 2 else 1]; ln = (c - a) if horiz else (d - b)
            for i in range(1, n):
                x = i * ln / n
                if horiz: s.line((a + x, b), (a + x, d), "#f3ead8", 1)
                else: s.line((a, b + x), (c, b + x), "#f3ead8", 1)
            cx, cy = (a + c) / 2, (b + d) / 2
            _chip(s, (cx, cy), "1" if k < 2 else "2", r=10, size=11)
            dx, dy = (0, 1) if horiz else (1, 0); sg = 1 if (cy if horiz else cx) > ((ti[1] + ti[3]) / 2 if horiz else (ti[0] + ti[2]) / 2) else -1
            for u in (-0.3, 0.3):
                px, py = (cx + u * ln, cy) if horiz else (cx, cy + u * ln)
                _arrow(s, (px + dx * sg * (fw / 2 + 1.3), py + dy * sg * (fw / 2 + 1.3)), (px + dx * sg * (fw / 2 + 0.08), py + dy * sg * (fw / 2 + 0.08)))
    s.poly([(t[0], t[1]), (t[2], t[1]), (t[2], t[3]), (t[0], t[3])], stroke=INK, sw=1.2)
    s.text(((o[0] + o[2]) / 2, o[1] - 1.75), "1: long sides first, sawn flush · 2: ends across", 11)
    if len(rings) > 1: s.text(((o[0] + o[2]) / 2, o[1] - 2.35), "the thin line goes on first, the same way", 11)
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


def asm_cut(plan):
    lg = max((l for l in plan["logs"] if l["crosscut"]), key=lambda l: l["slices"]); sp = plan["species"]; cut = plan["slice_cut"]
    H = lg["h"]
    if lg["kind"] == "hex":
        lg = dict(lg, cells=[(r, [(H - y, x) for x, y in pts]) for r, pts in lg["cells"]], w=lg["h"], h=lg["w"]); H = lg["h"]
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
    s.mark("text", (body + g / 2, max(xs) + 0.5, H + 0.4), "red: the saw cut", (0, -12))
    return s.svg(title=f"Crosscutting {lg['name']} into slices")


def make(plan):
    out = OrderedDict()
    out["face"] = face(plan); out["layout"] = layout(plan); out.update(bars(plan))
    for lg in plan["logs"]:
        out[f"log_{lg['id']}"] = log_stages(plan, lg)
        if lg["kind"] != "panel": out[f"asm_log_{lg['id']}"] = asm_log(plan, lg)
    if plan["info"]["kind"] == "tri":
        out["jigs"] = jigs(plan); out["true"] = true_fig(plan)
    if any(bt.get("setup") in ("para", "trap", "flip") and bt.get("tilt") for bt in plan["bar_types"]): out["ripsled"] = ripsled(plan)
    out["cut_setup"] = cut_setup(plan)
    out["asm_cut"] = asm_cut(plan); out["row"] = row_fig(plan); out["board"] = hexboard_fig(plan) if plan["info"]["kind"] == "hex" else board_fig(plan); out["trim"] = trim_fig(plan)
    if plan["board"].get("frame"): out["frame"] = frame_fig(plan)
    return out
