#!/usr/bin/env python3
"""End-grain cutting board: design.json -> checked build plan.

  python3 scripts/cbplan.py design.json out/ [--photo render.jpg]

Writes into out/:
  plan.json        everything computed: face, bars, logs, rows of slices, stock, steps, checks
  plan.html        the shop plan (self-contained: inline SVG diagrams, embedded photo if given)
  svg/*.svg        each diagram on its own
  board.obj/.mtl   the finished board in meters, a material per species (for plan-to-photo)
  guide.png        a colour-coded perspective of the board (the image Nano Banana photographs)
  spec.md          the board described in words for plan-to-photo's nano_banana.py

The board is built the way patterned end-grain boards are built (references/technique.md): bars are glued
three or four at a time into small logs whose outside is a triangle or a rectangle, every face of every log
is machined flat, the logs are crosscut into slices, slices are glued into straight rows and rows into the
board. logs.py works out the logs from the face; this file sizes, counts and checks everything.
Exit status 1 if any check fails.
"""
import argparse, base64, html, json, math, os, sys
from collections import OrderedDict, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patterns, species as SP

DEFAULT_SHOP = {"kerf": 0.125, "max_log_length": 24.0, "flatten_allowance": 0.125, "end_trim": 0.75,
                "stock_width": 5.5, "spare_slices": 1, "rip_oversize": 1 / 32, "true_skim": 1 / 64, "edge_clean": 0.125,
                "glue_extra": 0.5, "blank_remainder": 1.0, "max_cut_height": 3.125, "sled_base": 0.5, "min_bar_face": 0.375}
FONT = "IBM Plex Mono, ui-monospace, Menlo, monospace"


# ------------------------------------------------------------------------------------- geometry
def area(p):
    return 0.5 * sum(p[i][0] * p[i - 1][1] - p[i - 1][0] * p[i][1] for i in range(len(p))) * -1


def centroid(p):
    a = area(p)
    cx = cy = 0
    for i in range(len(p)):
        x0, y0 = p[i - 1]; x1, y1 = p[i]
        c = x0 * y1 - x1 * y0
        cx += (x0 + x1) * c; cy += (y0 + y1) * c
    return (cx / (6 * a), cy / (6 * a)) if a else tuple(sum(v) / len(p) for v in zip(*p))


def ccw(p):
    return p if area(p) > 0 else p[::-1]


def convex(p):
    n = len(p); sgn = 0
    for i in range(n):
        a, b, c = p[i], p[(i + 1) % n], p[(i + 2) % n]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cr) < 1e-9: continue
        s = 1 if cr > 0 else -1
        if sgn and s != sgn: return False
        sgn = s
    return True


def clip_rect(p, r):
    x0, y0, x1, y1 = r
    def clip(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            a, b = pts[i - 1], pts[i]
            ia, ib = inside(a), inside(b)
            if ib:
                if not ia: out.append(inter(a, b))
                out.append(b)
            elif ia: out.append(inter(a, b))
        return out
    def ix(xc):
        return lambda a, b: (xc, a[1] + (b[1] - a[1]) * (xc - a[0]) / (b[0] - a[0]))
    def iy(yc):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (yc - a[1]) / (b[1] - a[1]), yc)
    pts = [tuple(v) for v in p]
    for ins, it in ((lambda v: v[0] >= x0, ix(x0)), (lambda v: v[0] <= x1, ix(x1)),
                    (lambda v: v[1] >= y0, iy(y0)), (lambda v: v[1] <= y1, iy(y1))):
        if not pts: break
        pts = clip(pts, ins, it)
    # drop duplicate points
    out = []
    for v in pts:
        if not out or math.dist(v, out[-1]) > 1e-7: out.append(v)
    if len(out) > 1 and math.dist(out[0], out[-1]) < 1e-7: out.pop()
    return out if len(out) >= 3 and abs(area(out)) > 1e-6 else None


XF = OrderedDict([  # the eight ways a slice or unit can lie: turn it on the bench, or flip it over
    ("id",   lambda x, y: (x, y)),
    ("r180", lambda x, y: (-x, -y)),
    ("fx",   lambda x, y: (-x, y)),
    ("fy",   lambda x, y: (x, -y)),
    ("r90",  lambda x, y: (-y, x)),
    ("r270", lambda x, y: (y, -x)),
    ("d",    lambda x, y: (y, x)),
    ("ad",   lambda x, y: (-y, -x)),
])
XF_TEXT = {"id": "as cut", "r180": "turned end for end (180 degrees on the bench)",
           "fx": "flipped over left to right", "fy": "flipped over top to bottom",
           "r90": "turned 90 degrees counter-clockwise", "r270": "turned 90 degrees clockwise",
           "d": "flipped over on its diagonal", "ad": "flipped over on its other diagonal"}
XF_MARK = {"id": "", "r180": "↻180", "fx": "⇋", "fy": "⇵", "r90": "↺90", "r270": "↻90", "d": "⤢", "ad": "⤡"}


def norm_key(items, g="id"):
    """items: [(role, pts)] -> a key that is the same for any translation of the same arrangement."""
    f = XF[g]
    tp = [(r, [f(*v) for v in pts]) for r, pts in items]
    mx = min(v[0] for _, pts in tp for v in pts); my = min(v[1] for _, pts in tp for v in pts)
    return tuple(sorted((r, tuple(sorted((round(v[0] - mx, 3) + 0.0, round(v[1] - my, 3) + 0.0) for v in pts)))
                        for r, pts in tp))


class Matcher:
    """Group arrangements that are the same up to translation and the eight bench moves."""
    def __init__(self):
        self.types, self.index = [], {}

    def add(self, items, allowed=tuple(XF)):
        k = norm_key(items)
        if k in self.index:
            t, g = self.index[k]
            return t, g
        t = len(self.types)
        self.types.append(items)
        for g in allowed:
            kg = norm_key(items, g)
            self.index.setdefault(kg, (t, g))
        return t, "id"


# ------------------------------------------------------------------------------------- formatting
def frac(x, den=32):
    n = round(abs(x) * den)
    w, r = divmod(n, den)
    d = den
    while r and r % 2 == 0: r //= 2; d //= 2
    s = (f"{w}" if w else "") + (("-" if w else "") + f"{r}/{d}" if r else "")
    return ("-" if x < 0 else "") + (s or "0")


def dim(x):
    """Decimal with the nearest fraction, or just the fraction when it is exact."""
    if abs(x - round(x * 32) / 32) < 6e-4: return f'{frac(x)}"'
    return f'{x:.3f}" (≈{frac(x)}")'


def short(x):
    return f'{frac(x)}"' if round(abs(x) * 32) or not x else f'{frac(x, 64)}"'


# ------------------------------------------------------------------------------------- bars
def shape_of(pts):
    p = ccw([tuple(v) for v in pts]); n = len(p)
    L = [math.dist(p[i], p[(i + 1) % n]) for i in range(n)]
    A = []
    for i in range(n):
        a, b, c = p[i - 1], p[i], p[(i + 1) % n]
        v1 = (a[0] - b[0], a[1] - b[1]); v2 = (c[0] - b[0], c[1] - b[1])
        cosv = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2))
        A.append(math.degrees(math.acos(max(-1, min(1, cosv)))))
    toks = [(round(A[i], 1), round(L[i], 3)) for i in range(n)]
    rev = [(round(A[i], 1), round(L[i - 1], 3)) for i in range(n)][::-1]
    cands = [tuple(t[k:] + t[:k]) for t in (toks, rev) for k in range(n)]
    return min(cands), p, L, A


def recipe(key, p, L, A, shop):
    """How to make this cross-section: rip it 1/32" over on the table saw, then machine the sawn faces to size.
    Returns kind, label, blank thickness, the width each bar uses across the blank, blade tilt, steps, warnings."""
    kerf = shop["kerf"]; ov = shop.get("rip_oversize", 1 / 32); n = len(p); warn = []
    eq = lambda a, b, t=1e-3: abs(a - b) < t
    free = ("Set a thin-rip stop on the open side of the blade (the side the blade leans away from) and move the fence in for each cut "
            "so the blank touches the stop: the bar falls free outside the blade and is never trapped against the fence.")
    if n == 4 and all(eq(a, 90, 0.05) for a in A):
        w, h = max(L[0], L[1]), min(L[0], L[1])
        sq = eq(w, h)
        return {"kind": "square" if sq else "rect", "label": f"{short(w)} square" if sq else f"{short(h)} x {short(w)} rectangle",
                "dims": {"width": w, "thick": h}, "stock": h, "per_bar": w + ov + kerf, "tilt": 0, "stop": w + ov,
                "steps": [f"Mill the blank to {dim(h)} thick.",
                          f"Blade square. Rip bars {dim(w + ov)} wide: fence {short(w + ov)} from the blade while the blank is wider than 3\", then use the thin-rip stop.",
                          f"Stand the bars on edge, a handful side by side, and plane the sawn edges to {dim(w)}: half off each edge, every bar at one planer setting."],
                "warn": warn}
    if n == 4 and eq(L[0], L[2]) and eq(L[1], L[3]) and eq(A[0], A[2], 0.05):
        th = min(A); pside, qside = (L[0], L[1])
        if qside > pside: pside, qside = qside, pside
        sn = math.sin(math.radians(th)); t = qside * sn; d2 = pside * sn; tilt = 90 - th
        kind = "rhombus" if eq(pside, qside) else "parallelogram"
        if tilt > 45.01:
            warn.append(f"Needs a {tilt:.1f} degree blade tilt, past a table saw's 45; change the angle.")
        stop = pside + ov / sn
        st = [f"Mill the blank to {dim(t)} thick (the bar's height lying on its {short(pside)} face).",
              f"Tilt the blade {tilt:.1f} degrees from vertical; set it with a digital angle gauge, not the saw's scale. Rip one bevel along the blank's edge and discard the strip.",
              free + f" Set the stop so each bar measures {dim(stop)} across its bottom face ({short(pside)} plus the allowance). Every pass cuts the next bar's leading bevel, so the blank is never flipped.",
              f"Machine the two sawn faces: lay the bars on a sawn face on a flat carrier board with a low fence, and plane or drum-sand to {dim(d2)}, half from each sawn face"
              + (", which is the planer setting the blank was milled at." if kind == "rhombus" else "."),
              f"Check: corners {th:.0f} and {180 - th:.0f} degrees, " + (f"all four faces {dim(pside)}." if kind == "rhombus" else f"faces {dim(pside)} and {dim(qside)}.")]
        return {"kind": kind, "label": f"{th:.0f}-degree {'diamond' if kind == 'rhombus' else 'parallelogram'}, {short(pside)} faces" + ("" if kind == "rhombus" else f" x {short(qside)}"),
                "dims": {"side": pside, "slant": qside, "angle": th, "thick": t}, "stock": t, "stop": stop,
                "per_bar": stop + kerf / math.cos(math.radians(tilt)), "tilt": tilt, "steps": st, "warn": warn}
    if n == 4:   # isosceles trapezoid
        for i in range(4):
            if eq(A[i], A[(i + 1) % 4], 0.05) and eq(A[i] + A[(i + 2) % 4], 180, 0.05) and eq(L[i - 1], L[(i + 1) % 4]) and A[i] < 89.9:
                th = A[i]; long_, short_, leg = L[i], L[(i + 2) % 4], L[i - 1]
                H = leg * math.sin(math.radians(th)); tilt = 90 - th
                if tilt > 45.01: warn.append(f"Needs a {tilt:.1f} degree tilt, past a table saw's 45.")
                e_ = ov / math.sin(math.radians(th))
                st = [f"Mill the blank to {dim(H)} thick (the trapezoid's height).",
                      f"Tilt the blade {tilt:.1f} degrees from vertical (digital angle gauge). Rip one bevel along the blank's edge and discard the strip.",
                      free + f" Flip the blank face for face before every pass so the bevels alternate. Set the stop so each bar measures {dim(long_ + e_)} across its wide face, which is down on the table.",
                      f"True the two sawn faces in the sanding sled, one light pass each at one setting, until the wide face is {dim(long_)} and the narrow face {dim(short_)}.",
                      f"Check: {th:.0f} degree corners on the wide face, slanted faces {dim(leg)}."]
                return {"kind": "trapezoid", "label": f"{th:.0f}-degree trapezoid, {short(long_)} and {short(short_)} faces",
                        "dims": {"long": long_, "short": short_, "leg": leg, "angle": th, "thick": H}, "stock": H, "stop": long_ + e_,
                        "per_bar": (long_ + short_) / 2 + e_ + kerf / math.cos(math.radians(tilt)), "tilt": tilt, "steps": st, "warn": warn}
    if n == 6 and all(eq(a, 120, 0.05) for a in A) and all(eq(l, L[0]) for l in L):
        s_ = L[0]; ff = s_ * math.sqrt(3)
        st = [f"Mill the blank to {dim(ff)} thick (the hexagon across its flats) and rip strips {dim(2 * s_ + ov)} wide, blade square.",
              "Tilt the blade 30.0 degrees from vertical (digital angle gauge).",
              f"Bevel all four long corners of each strip: flat face on the table, fence set so the cut ends at mid-thickness, rip, turn the strip end for end, rip, then flip it over and repeat. Every face is then {dim(s_)}.",
              "True the four sawn faces in the sanding sled with one light pass each.",
              "Check every corner is 120 degrees and the three across-flats measurements match."]
        return {"kind": "hexagon", "label": f"regular hexagon, {short(s_)} faces", "dims": {"side": s_, "flats": ff, "thick": ff},
                "stock": ff, "per_bar": 2 * s_ + ov + kerf, "tilt": 30.0, "steps": st, "warn": warn, "stop": 2 * s_ + ov}
    if n == 3:
        for i in range(3):
            a_, b_ = L[i - 1], L[i]
            if eq(a_, b_):
                phi = A[i]; base = L[(i + 1) % 3]; H = a_ * math.cos(math.radians(phi / 2)); tilt = phi / 2
                equi = eq(phi, 60, 0.05) and eq(base, a_)
                kind = "equilateral triangle" if equi else ("right isosceles triangle" if eq(phi, 90, 0.05) else "isosceles triangle")
                if tilt > 45.01: warn.append(f"Needs a {tilt:.1f} degree tilt, past a table saw's 45.")
                dH = ov if equi else 0.0; e_ = dH / math.tan(math.radians(90 - tilt)) * 2 if equi else 0.0
                st = [f"Mill the blank to {dim(H + dH)} thick (the triangle's height" + (", plus the allowance)." if equi else ")."),
                      f"Tilt the blade {tilt:.1f} degrees from vertical (digital angle gauge). Rip one bevel along the blank's edge and discard the strip.",
                      free + f" Flip the blank face for face before every pass. Set the stop so each bar measures {dim(base + e_)} across its base, which is down on the table."]
                if equi:
                    st.append(f"True the two sawn faces: set each bar in the sanding sled with a sawn face up and take light passes, every bar at one setting, until all three faces are {dim(base)}.")
                else:
                    st.append("The sawn faces end up on the outside of the log and are trued with it; the planed base is the glue face.")
                st.append(f"Check: equal faces {dim(a_)}, {phi:.0f} degrees between them.")
                return {"kind": kind, "label": f"{kind}, {short(base)} " + ("faces" if equi else "base"), "dims": {"base": base, "leg": a_, "apex": phi, "thick": H + dH},
                        "stock": H + dH, "stop": base + e_, "per_bar": (base + e_) / 2 + kerf / math.cos(math.radians(tilt)), "tilt": tilt, "steps": st, "warn": warn}
    if n == 3:
        for i in range(3):
            if eq(A[i], 90, 0.05):
                l1, l2 = L[i - 1], L[i]; short_, long_ = min(l1, l2), max(l1, l2)
                tilt = math.degrees(math.atan2(short_, long_)); hyp = math.hypot(short_, long_)
                st = [f"Mill the blank to {dim(long_)} thick and rip strips {dim(short_)} wide, blade square.",
                      f"Tilt the blade {tilt:.1f} degrees from vertical (digital angle gauge) and rip each strip corner to corner, standing on its narrow face in a carrier that holds it against the fence. Both halves are bars.",
                      f"Check: faces {dim(short_)} and {dim(long_)}, long face {dim(hyp)}, corners 90, {90 - tilt:.0f} and {tilt:.0f} degrees."]
                return {"kind": "right triangle", "label": f"{tilt:.0f}/{90 - tilt:.0f}-degree right triangle, {short(short_)} x {short(long_)}",
                        "dims": {"short": short_, "long": long_, "hyp": hyp, "thick": long_}, "stock": long_, "stop": short_,
                        "per_bar": short_ / 2 + kerf / 2 / math.cos(math.radians(tilt)), "tilt": tilt, "steps": st, "warn": warn}
    xs = [v[0] for v in p]; ys = [v[1] for v in p]
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    warn.append("Irregular cross-section with no table-saw setup; change the pattern or the log size.")
    return {"kind": "polygon", "label": f"{n}-sided bar", "dims": {"bbox": [bw, bh]}, "stock": min(bw, bh), "stop": None,
            "per_bar": max(bw, bh) + kerf, "tilt": None,
            "steps": [f"Rip a blank {dim(bw)} x {dim(bh)}.", "Cut each other face at the corner angles shown (" + ", ".join(f"{a:.1f}" for a in A) + " degrees)."],
            "warn": warn}


def nominal(t):
    for q, lim in ((4, 0.8125), (5, 1.0625), (6, 1.3125), (8, 1.75), (10, 2.25), (12, 2.75), (16, 3.75)):
        if t <= lim: return q
    return None


# ------------------------------------------------------------------------------------- checks
def coverage(polys, trim, step):
    """Sample a grid: count how many bars cover each point. Returns (overlap points, gap points in trim)."""
    import numpy as np
    allx = [v[0] for p in polys for v in p["pts"]]; ally = [v[1] for p in polys for v in p["pts"]]
    x0, x1, y0, y1 = min(allx), max(allx), min(ally), max(ally)
    off = step * 0.3719
    xs = np.arange(x0 + off, x1, step); ys = np.arange(y0 + off * 1.31, y1, step)
    X, Y = np.meshgrid(xs, ys)
    cnt = np.zeros(X.shape, dtype=np.int16); near = np.zeros(X.shape, bool)   # points on an edge prove nothing
    for p in polys:
        pts = ccw([tuple(v) for v in p["pts"]])
        px = [v[0] for v in pts]; py = [v[1] for v in pts]
        i0, i1 = np.searchsorted(xs, min(px)), np.searchsorted(xs, max(px))
        j0, j1 = np.searchsorted(ys, min(py)), np.searchsorted(ys, max(py))
        if i1 <= i0 or j1 <= j0: continue
        sx, sy = X[j0:j1, i0:i1], Y[j0:j1, i0:i1]
        m = np.ones(sx.shape, bool)
        for k in range(len(pts)):
            (ax, ay), (bx, by) = pts[k - 1], pts[k]
            cr = (bx - ax) * (sy - ay) - (by - ay) * (sx - ax)
            m &= cr > 1e-9
            ln = math.hypot(bx - ax, by - ay) or 1
            near[j0:j1, i0:i1] |= (np.abs(cr) / ln < 2e-4) & (np.minimum(ax, bx) - 2e-4 <= sx) & (sx <= np.maximum(ax, bx) + 2e-4) \
                & (np.minimum(ay, by) - 2e-4 <= sy) & (sy <= np.maximum(ay, by) + 2e-4)
        cnt[j0:j1, i0:i1] += m
    over = np.argwhere((cnt > 1) & ~near)
    t0, s0, t1, s1 = trim
    inside = (X > t0 + step) & (X < t1 - step) & (Y > s0 + step) & (Y < s1 - step)
    gaps = np.argwhere(inside & (cnt == 0) & ~near)
    pt = lambda ij: (round(float(xs[ij[1]]), 2), round(float(ys[ij[0]]), 2))
    return len(over), (pt(over[0]) if len(over) else None), len(gaps), (pt(gaps[0]) if len(gaps) else None)


def outline_edges(polys):
    """Edges of a group of polygons that are not shared inside the group: its outline."""
    cnt = defaultdict(int); keep = {}
    for pts in polys:
        for i in range(len(pts)):
            a, b = tuple(round(c, 3) for c in pts[i - 1]), tuple(round(c, 3) for c in pts[i])
            k = (min(a, b), max(a, b)); cnt[k] += 1; keep[k] = (pts[i - 1], pts[i])
    return [keep[k] for k, c in cnt.items() if c == 1]


def flat_faces(polys):
    """Which sides of a cross-section's bounding box are flat (fully on the outline)."""
    xs = [v[0] for p in polys for v in p]; ys = [v[1] for p in polys for v in p]
    bx = (min(xs), min(ys), max(xs), max(ys)); res = {}
    edges = outline_edges(polys)
    for side, (axis, val, span) in {"bottom": (1, bx[1], bx[2] - bx[0]), "top": (1, bx[3], bx[2] - bx[0]),
                                    "left": (0, bx[0], bx[3] - bx[1]), "right": (0, bx[2], bx[3] - bx[1])}.items():
        tot = sum(math.dist(a, b) for a, b in edges if abs(a[axis] - val) < 1e-3 and abs(b[axis] - val) < 1e-3)
        res[side] = tot >= span - 1e-3
    return res


# ------------------------------------------------------------------------------------- SVG
class Svg:
    def __init__(self, bbox, scale, pad=40, extra_h=0, title=""):
        self.x0, self.y0, self.x1, self.y1 = bbox; self.s = scale; self.pad = pad
        self.w = (self.x1 - self.x0) * scale + 2 * pad
        self.h = (self.y1 - self.y0) * scale + 2 * pad + extra_h
        self.el = []; self.title = title

    def P(self, x, y):
        return (self.pad + (x - self.x0) * self.s, self.pad + (self.y1 - y) * self.s)

    def poly(self, pts, fill="none", stroke="#222", sw=0.6, dash=None, op=1):
        d = " ".join(f"{a:.2f},{b:.2f}" for a, b in (self.P(*v) for v in pts))
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.el.append(f'<polygon points="{d}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}"{da} stroke-linejoin="round"/>')

    def line(self, a, b, stroke="#222", sw=1, dash=None, raw=False):
        (x1, y1), (x2, y2) = (a, b) if raw else (self.P(*a), self.P(*b))
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.el.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{stroke}" stroke-width="{sw}"{da}/>')

    def text(self, xy, s, size=12, anchor="middle", fill="#222", raw=False, weight="normal", rot=0, halo=False):
        x, y = xy if raw else self.P(*xy)
        tr = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot else ""
        h = ' paint-order="stroke" stroke="#fff" stroke-width="3"' if halo else ""
        self.el.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
                       f'font-weight="{weight}" dominant-baseline="middle"{tr}{h}>{html.escape(s)}</text>')

    def raw(self, s):
        self.el.append(s)

    def dimx(self, xa, xb, y, label, below=True):
        off = 18 if below else -18
        (ax, ay), (bx, _) = self.P(xa, y), self.P(xb, y)
        yy = ay + off
        self.line((ax, ay + (4 if below else -4)), (ax, yy + (4 if below else -4)), sw=0.6, raw=True)
        self.line((bx, ay + (4 if below else -4)), (bx, yy + (4 if below else -4)), sw=0.6, raw=True)
        self.line((ax, yy), (bx, yy), sw=0.8, raw=True)
        for x, d in ((ax, 1), (bx, -1)):
            self.el.append(f'<path d="M{x:.1f},{yy:.1f} l{6*d},-3 l0,6 z" fill="#222"/>')
        self.text(((ax + bx) / 2, yy + (11 if below else -9)), label, 11, raw=True, halo=True)

    def dimy(self, ya, yb, x, label, left=True):
        off = -18 if left else 18
        (ax, ay), (_, by) = self.P(x, ya), self.P(x, yb)
        xx = ax + off
        self.line((ax + (-4 if left else 4), ay), (xx + (-4 if left else 4), ay), sw=0.6, raw=True)
        self.line((ax + (-4 if left else 4), by), (xx + (-4 if left else 4), by), sw=0.6, raw=True)
        self.line((xx, ay), (xx, by), sw=0.8, raw=True)
        for y, d in ((ay, -1), (by, 1)):
            self.el.append(f'<path d="M{xx:.1f},{y:.1f} l-3,{6*d} l6,0 z" fill="#222"/>')
        self.text((xx + (-10 if left else 10), (ay + by) / 2), label, 11, raw=True, rot=-90, halo=True)

    def svg(self):
        t = f"<title>{html.escape(self.title)}</title>" if self.title else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w:.0f} {self.h:.0f}" width="{self.w:.0f}" '
                f'height="{self.h:.0f}" font-family="{FONT}">{t}<rect width="100%" height="100%" fill="#fff"/>'
                + "".join(self.el) + "</svg>")


def bbox_of(polys):
    xs = [v[0] for p in polys for v in p]; ys = [v[1] for p in polys for v in p]
    return (min(xs), min(ys), max(xs), max(ys))


# ------------------------------------------------------------------------------------- main build
LEVEL_NAME = {"tri": "triangle log", "band": "band", "quarter": "quarter log", "half": "half log", "block": "block log", "panel": "strip panel"}
NO_LOG_BUILD = {
    "rosettes": "The hexagon-square-triangle rosette (3.4.6.4) has no sound build: every way of cutting it into logs either "
                "leaves a re-entrant glue-up that cannot be machined flat or splits the hexagons and squares into slivers. "
                "Use pattern \"pinwheel\" instead: hexagons each ringed by six diamonds with small triangles between, which "
                "builds from trued triangle logs.",
    "rhombitrihex": None}


def _up(x, step=0.25):
    return math.ceil(x / step - 1e-9) * step


def build(design, out, photo=None):
    import logs as LG
    shop = dict(DEFAULT_SHOP, **design.get("shop", {}))
    board = design["board"]; T = float(board.get("thickness", 1.5))
    if design["pattern"] in NO_LOG_BUILD:
        raise SystemExit(f"pattern {design['pattern']!r} cannot be built soundly. " + (NO_LOG_BUILD[design["pattern"]] or NO_LOG_BUILD["rosettes"]))
    g = patterns.generate(design)
    polys = g["polygons"]; trim = [float(v) for v in g["trim"]]
    for p in polys: p["pts"] = [tuple(v) for v in ccw([tuple(v) for v in p["pts"]])]
    cells = design.get("cells") or g.get("cells") or {"kind": "panel"}
    checks = []
    def check(ok, what, detail="", level="error"):
        checks.append({"ok": bool(ok), "what": what, "detail": detail, "level": level})

    # species
    smap = design["species"]; roles = g["roles"]
    missing = [r for r in roles if r not in smap]
    if missing: raise SystemExit(f"design.species needs a species for roles {missing} (pattern roles: {roles})")
    sp = {r: SP.get(smap[r]) for r in roles}
    for r, c in design.get("species_colors", {}).items():
        sp[r]["end"] = c
    woods = OrderedDict()
    for r in roles: woods.setdefault(sp[r]["key"], sp[r])
    jk = [w for w in woods.values() if w["janka"] and w["janka"] < 900]
    check(not jk, "Species hard enough for a cutting surface (Janka 900+)", ", ".join(f'{w["name"]} {w["janka"]}' for w in jk))
    tans = [w["tan"] for w in woods.values() if w["tan"]]
    spread = (max(tans) - min(tans)) if tans else 0
    check(spread <= 4.0, "Species move alike (tangential shrinkage within 4 points)",
          (f"{min(tans):.1f}% to {max(tans):.1f}%" if tans else "") + ("; acclimate every species together and keep the board oiled so it moves evenly" if spread > 4 else ""), "warn")
    unknown = [w["name"] for w in woods.values() if w["janka"] is None]
    check(not unknown, "Every species in the species table", ", ".join(unknown), "warn")

    # the face
    bad = [i for i, p in enumerate(polys) if not convex(p["pts"])]
    check(not bad, "Every piece of the face is convex", f"{len(bad)} not convex" if bad else "")
    minside = min(min(math.dist(p["pts"][i - 1], p["pts"][i]) for i in range(len(p["pts"]))) for p in polys)
    step = max(0.01, min(0.04, minside / 8))
    no, op_, ng, gp = coverage(polys, trim, step)
    check(no == 0, "Pieces do not overlap", f"overlap near {op_}" if no else "")
    check(ng == 0, "Pieces cover the whole board (no gaps)", f"gap near {gp}" if ng else "")

    # logs, pucks and rows
    def bar_ok(pts):
        key, p, L, A = shape_of(pts); rc = recipe(key, p, L, A, shop)
        if rc["kind"] == "polygon" or rc["warn"]: return False
        return not ("triangle" in rc["kind"] and max(A) > 90.5)
    lp = LG.plan(polys, trim, cells, lambda r: sp[r]["key"], bar_ok)
    logs = lp["logs"]; rows = lp["rows"]; kind = lp["info"]["kind"]
    _ax = 0 if abs(math.sin(math.radians(lp["info"].get("angle", 0)))) > 0.5 else 1
    rows.sort(key=lambda r: sum(v[_ax] for v in r["pts"]) / len(r["pts"]))
    for n, r in enumerate(rows): r["n"] = n + 1
    byid = {lg["id"]: lg for lg in logs}
    for lg in logs:
        lg["shape"] = lg.get("shape") or lg["kind"]
        lg["name"] = f"Log {lg['id']}"
        lg["what"] = LEVEL_NAME.get(lg["shape"], "log")

    # sizes: truing takes a skim off every machined face, so the glued board comes out a little smaller than drawn
    skim = shop["true_skim"]
    xs = [v[0] for r in rows for v in r["pts"]]; ys = [v[1] for r in rows for v in r["pts"]]
    gb = [min(xs), min(ys), max(xs), max(ys)]
    ang = math.radians(lp["info"].get("angle", 0)); across_x = abs(math.sin(ang)) > 0.5      # rows stack along x when they run up the board
    npr = max(len(r["pucks"]) for r in rows)
    if kind == "tri": d_stack = len(rows) * 3 * skim; d_run = npr / 2 * 2 * math.sqrt(3) * skim
    elif kind == "blocks": d_stack = len(rows) * 2 * skim; d_run = npr * 2 * skim
    else: d_stack = d_run = 0.0
    dx, dy = (d_stack, d_run) if across_x else (d_run, d_stack)
    glued = [gb[0] + dx / 2, gb[1] + dy / 2, gb[2] - dx / 2, gb[3] - dy / 2]
    ec = shop["edge_clean"]; drawn = list(trim)
    trim = [max(trim[0], glued[0] + ec), max(trim[1], glued[1] + ec), min(trim[2], glued[2] - ec), min(trim[3], glued[3] - ec)]
    W, Lb = trim[2] - trim[0], trim[3] - trim[1]
    margins = [trim[0] - glued[0], glued[2] - trim[2], trim[1] - glued[1], glued[3] - trim[3]]

    face = []
    for r in rows:      # the face as it is really built: one polygon per piece of wood in each slice
        for pk in r["pucks"]:
            for role, pts in pk["cells"]:
                c = clip_rect(pts, trim)
                if c: face.append({"pts": c, "role": role})
    pa = sum(abs(area(c)) for r in rows for pk in r["pucks"] for c in [clip_rect(pk["pts"], trim)] if c)
    check(abs(pa - W * Lb) < 1e-3 * W * Lb, "Slices cover the whole board", f"{pa:.2f} of {W * Lb:.2f} sq in" if abs(pa - W * Lb) >= 1e-3 * W * Lb else f"{sum(len(r['pucks']) for r in rows)} slices in {len(rows)} rows")
    for lg in logs:
        a_parts = sum(abs(area(p["pts"])) for st in lg["stages"] for p in st["parts"]); a_out = abs(area(lg["outline"]))
        if abs(a_parts - a_out) > 2e-3 * a_out:
            check(False, f"{lg['name']} cross-section is complete", f"parts {a_parts:.3f} sq in, outline {a_out:.3f}")
    check(True, "Every log's parts fill its cross-section")

    # how many of each log, and how long
    cut = T + shop["flatten_allowance"]; pitch = cut + shop["kerf"]
    npk = defaultdict(int)
    for r in rows:
        for pk in r["pucks"]: npk[pk["log"]] += 1
    usable = shop["max_log_length"] - 2 * shop["end_trim"]
    for lg in logs: lg["make"] = defaultdict(int)
    for lg in logs:
        if not lg["crosscut"]: continue
        n = npk[lg["id"]]; need = n + max(shop["spare_slices"], math.ceil(n * 0.05))
        k = max(1, math.ceil(need * pitch / usable)); per = math.ceil(need / k)
        length = _up(per * pitch + 2 * shop["end_trim"])
        lg.update(slices=n, spares=k * per - n, per_log=per); lg["make"][length] += k
    bar_types = OrderedDict(); need = defaultdict(lambda: defaultdict(int))
    for lg in sorted(logs, key=lambda l: -l["level"]):
        for st in lg["stages"]:
            for part in st["parts"]:
                for ln, k in list(lg["make"].items()):
                    if "log" in part:
                        byid[part["log"]]["make"][_up(ln + shop["glue_extra"])] += k
                    else:
                        key, pp, L, A = shape_of(part["pts"])
                        if key not in bar_types:
                            bar_types[key] = {"id": None, "recipe": recipe(key, pp, L, A, shop), "pts": pp, "sides": L, "angles": A}
                        part["shape"] = key
                        need[(key, part["wood"])][_up(ln + shop["glue_extra"])] += k
    for n, (k, bt) in enumerate(bar_types.items()):
        bt["id"] = str(n + 1)
        for w in bt["recipe"]["warn"]:
            check(False, f"Bar {bt['id']} can be cut", w)
    for lg in logs:
        lg["make"] = sorted(lg["make"].items()); lg["count"] = sum(k for _, k in lg["make"])
        lg["length"] = max((ln for ln, _ in lg["make"]), default=0)
        for st in lg["stages"]:
            for part in st["parts"]:
                if "shape" in part: part["bar"] = bar_types[part.pop("shape")]["id"]
    tilts = [bt["recipe"]["tilt"] for bt in bar_types.values() if bt["recipe"]["tilt"]]
    check(all(t <= 45.01 for t in tilts), "Every bevel is 45 degrees or less from vertical")
    small = [f'bar {bt["id"]} ({short(min(bt["sides"]))} face)' for bt in bar_types.values() if min(bt["sides"]) < shop["min_bar_face"] - 1e-6]
    check(not small, f"No bar has a face under {short(shop['min_bar_face'])}", ", ".join(small) + ("; rip these from the wide blank with the thin-rip stop and a zero-clearance insert, or make the pattern larger" if small else ""), "warn")

    bars_out = []
    for (key, wkey), byl in need.items():
        bt = bar_types[key]; rc = bt["recipe"]
        per_blank = max(1, int((shop["stock_width"] - shop["blank_remainder"]) // rc["per_bar"]))
        blanks = []
        for ln, c in sorted(byl.items()):
            spare = max(1, math.ceil(c * 0.1))
            blanks.append({"bar_length": ln, "bars": c, "spares": spare, "blanks": math.ceil((c + spare) / per_blank), "blank_length": math.ceil(ln + 1)})
        bars_out.append({"bar": bt["id"], "species": wkey, "label": rc["label"], "kind": rc["kind"], "stock": rc["stock"], "per_blank": per_blank,
                         "lengths": blanks, "total_bars": sum(byl.values()), "total_spares": sum(b["spares"] for b in blanks)})
    bars_out.sort(key=lambda b: (int(b["bar"]), b["species"]))

    stock = OrderedDict()
    for b in bars_out:
        q = nominal(b["stock"]); rough_t = (q or 16) / 4
        bf = sum(bl["blanks"] * rough_t * (shop["stock_width"] + 0.5) * bl["blank_length"] / 144 for bl in b["lengths"])
        st = stock.setdefault(b["species"], {"species": woods[b["species"]]["name"], "items": [], "bf": 0})
        st["items"].append({"bar": b["bar"], "mill_to": b["stock"], "rough": f"{q}/4" if q else "glue up", "per_blank": b["per_blank"],
                            "blanks": [{"n": bl["blanks"], "size": f'{short(b["stock"])} x {short(shop["stock_width"])} x {bl["blank_length"]}"',
                                        "yield": f'{bl["bars"]} + {bl["spares"]} spare'} for bl in b["lengths"]]})
        st["bf"] += bf
        if not q: check(False, f"Bar {b['bar']} stock", f"{b['stock']:.2f}\" thick is more than 16/4; laminate blanks first")
    for st in stock.values():
        st["bf_buy"] = math.ceil(st["bf"] * 1.25 * 2) / 2

    # shop limits
    for lg in logs:
        if lg["crosscut"]:
            hh = lg["h"] if lg["kind"] != "panel" else min(lg["h"], lg["w"]) if False else lg["h"]
            if lg["kind"] == "panel": hh = lg["h"]
            cap = shop["max_cut_height"] - shop["sled_base"]
            check(hh <= cap + 1e-6, f"{lg['name']} fits under the saw on the crosscut sled",
                  f'{short(hh)} tall on a {short(shop["sled_base"])} sled base; the blade clears {short(shop["max_cut_height"])}'
                  + ("" if hh <= cap + 1e-6 else ". Make the pattern smaller, or crosscut on a bandsaw or a 12 inch saw and set shop.max_cut_height"))
    mx = max(len(st["parts"]) for lg in logs for st in lg["stages"] if lg["kind"] != "panel")if any(lg["kind"] != "panel" for lg in logs) else 0
    check(mx <= 4, "No log glue-up has more than four parts", f"largest has {mx}" if mx else "", "warn")
    crossed = [lg for lg in logs if lg["crosscut"]]
    check(len(logs) <= 8, "A manageable number of log types", f"{len(logs)} log types, {len(crossed)} of them sliced", "warn")
    check(min(margins) >= ec - 1e-6, f"At least {short(ec)} to trim on every edge", ", ".join(f"{short(m)}" for m in margins) + " (left, right, bottom, top)")
    check(T >= 1.0, "Board at least 1\" thick (end grain under 1\" can split)", f"{T}\"")
    check(max(W, Lb) / T <= 18, "Board not too large for its thickness", f"{W:.1f} x {Lb:.1f} x {T}", "warn")

    plan = {"name": design.get("name", design["pattern"]), "description": design.get("description", ""), "pattern": design["pattern"],
            "board": {"width": W, "length": Lb, "thickness": T, "trim": trim, "glued": glued, "drawn": drawn, "margins": margins},
            "shop": shop, "species": {r: sp[r] for r in roles}, "woods": list(woods.values()),
            "notes": g.get("notes", []) + design.get("notes", []), "options": design.get("options", {}),
            "face": face, "polygons": polys,
            "bar_types": [dict(id=bt["id"], label=bt["recipe"]["label"], kind=bt["recipe"]["kind"], dims=bt["recipe"]["dims"], tilt=bt["recipe"]["tilt"],
                               steps=bt["recipe"]["steps"], pts=bt["pts"], sides=bt["sides"], angles=bt["angles"], stop=bt["recipe"].get("stop")) for bt in bar_types.values()],
            "bars": bars_out, "logs": logs, "rows": rows, "info": lp["info"], "stock": list(stock.values()), "checks": checks, "method": "logs",
            "slice_cut": cut, "n_slices": sum(len(r["pucks"]) for r in rows)}
    plan["steps"] = steps(plan, design)
    os.makedirs(os.path.join(out, "svg"), exist_ok=True)
    import drawings
    svgs = drawings.make(plan)
    for name, s in svgs.items():
        open(os.path.join(out, "svg", name + ".svg"), "w").write(s)
    write_obj(plan, out)
    write_spec(plan, design, out)
    try:
        import render_guide
        render_guide.render(plan, os.path.join(out, "guide.png"), **design.get("guide", {}))
    except Exception as e:
        print("guide.png skipped:", e)
    open(os.path.join(out, "plan.html"), "w").write(page(plan, svgs, photo, os.path.join(out, "guide.png")))
    slim = {k: v for k, v in plan.items() if k not in ("polygons",)}
    json.dump(slim, open(os.path.join(out, "plan.json"), "w"), indent=1, default=str)
    return plan


# ------------------------------------------------------------------------------------- steps
def _made(lg):
    return " and ".join(f'{k} at {short(ln)} long' for ln, k in lg["make"])


def _parts_text(plan, st):
    names = []
    for p in st["parts"]:
        names.append(f"log {p['log']}" if "log" in p else f"bar {p['bar']} ({plan_name(plan, p['wood']).split()[-1].lower()})")
    cnt = OrderedDict()
    for n in names: cnt[n] = cnt.get(n, 0) + 1
    return ", ".join((f"{c} x {n}" if c > 1 else n) for n, c in cnt.items())


def steps(plan, design):
    sh = plan["shop"]; T = plan["board"]["thickness"]; cut = plan["slice_cut"]; kind = plan["info"]["kind"]
    logs = plan["logs"]; rows = plan["rows"]; skim = sh["true_skim"]
    S = []
    woods = ", ".join(w["name"] for w in plan["woods"])
    S.append({"title": "Buy and acclimate the lumber", "figs": [], "see": ["materials"],
              "text": [f"Buy the boards in the material list ({woods}) and let them sit in the shop for a week, stickered.",
                       "Pick straight-grained stock, quartersawn or rift where you can: it moves less and the end grain shows tight, even rings."]})
    thick = sorted({round(b["stock"], 4) for b in plan["bars"]})
    tx = [f"Joint one face and one edge of every blank, then plane to thickness: {', '.join(short(t) for t in thick)} "
          f"(material list, sheet 02). Plane every blank of one thickness in the same session without moving the planer between them.",
          "Rip and true each bar shape as set out on sheet 03. Bars are ripped 1/32\" over and then machined to size, so the saw only has to be close.",
          "Test each setup on scrap first: rip three short bars, true them, and dry-fit them in the cradle or against a square. "
          "Half a degree of bevel error shows as a gap you can slip paper into; fix the tilt before cutting good wood.",
          f"The cut list already includes one spare bar in ten. Rip every bar of a shape in one run, then check a handful with calipers: "
          f"all within {short(1 / 64)}."]
    S.append({"title": "Mill the blanks and rip the bars", "text": tx, "figs": ["asm_rip"], "see": ["bars"],
              "dont": "rip a bar between the blade and the fence when the blade is tilted, or keep ripping a blank narrower than "
                      f"{short(sh['blank_remainder'])}. The bar must fall free on the open side; the last strip of each blank is waste."})

    jig = []
    if kind == "tri":
        side = max(lg["w"] for lg in logs)
        jig += [f"V cradle for glue-ups: two strips of 3/4\" MDF, each with one edge ripped at 30 degrees, screwed to a flat base so the bevels form a "
                f"60 degree V at least {short(side * 0.9)} up each side and 2\" longer than the longest log. Cover the V with packing tape so glue lets go. "
                "Check the V with a 60 degree drafting triangle.",
                "Sanding sled: a second cradle the same shape, without tape, with a stop screwed across the trailing end. It carries bars and logs "
                "through the drum sander with one face up and level.",
                f"Row jig: a flat melamine base with two straight fences screwed down parallel, {short(plan['info']['row_height'])} apart less a paper shim "
                "(a row of slices must slide in snug). Wax it."]
    elif kind == "blocks":
        jig += ["Corner cauls: two straight L-shaped cauls (two strips of plywood glued at 90 degrees, faces taped) as long as the logs. "
                "They hold a square log square while clamps squeeze it from two directions.",
                "Row jig: a flat melamine base with one straight fence and an end stop square to it. Wax it."]
    else:
        jig += ["Flat cauls: four straight 2x2s with packing tape on one face, as long as the panels are wide."]
    jig.append(f"Crosscut sled with a hold-down and a stop block set {short(cut)} from the blade. Check it cuts square in both directions.")
    S.append({"title": "Make the jigs", "text": jig, "figs": ["jigs"] if kind == "tri" else [], "see": []})

    levels = sorted({lg["level"] for lg in logs})
    nglue = 0
    for lv in levels:
        here = [lg for lg in logs if lg["level"] == lv]
        what = here[0]["what"]
        tx = []
        for lg in here:
            sl = f", for {lg['slices']} slices plus {lg['spares']} spare" if lg["crosscut"] else ""
            if len(lg["stages"]) == 1 and len(lg["stages"][0]["parts"]) == 1:
                tx.append(f"{lg['name']} is one solid bar (bar {lg['stages'][0]['parts'][0]['bar']}): nothing to glue. Make {_made(lg)}{sl}, and true it with the other logs.")
            elif len(lg["stages"]) == 1:
                tx.append(f"{lg['name']} ({short(lg['w'])} {what}): glue {_parts_text(plan, lg['stages'][0])} as drawn on sheet 04. Make {_made(lg)}{sl}.")
            else:
                tx.append(f"{lg['name']} ({short(lg['w'])} {what}): make {_made(lg)}{sl}, in {len(lg['stages'])} glue-ups: "
                          + "; then ".join(f"glue-up {i + 1}: {_parts_text(plan, st)}" for i, st in enumerate(lg["stages"])) + ".")
        if here[0]["kind"] == "tri":
            tx += ["Dry-fit first: stack the bars in the cradle in the drawn order with no glue. The top must come out flat and level with no rocking.",
                   "Spread a thin, even coat of Titebond III on both faces of every joint (the faces are long grain: one coat each is right). "
                   "Stack the bars in the cradle, lay a taped caul on the flat top, and clamp down through the caul every 4 to 5 inches, snug rather than hard. "
                   "The V pushes the bars together sideways while the caul pushes them down.",
                   "Check both ends: the bars' corners must meet at a point. Tap a bar along its length to line it up before the glue grabs.",
                   "After an hour take the log out and scrape the squeeze-out while it is rubbery. Leave it overnight."]
            if any(len(lg["stages"]) > 1 for lg in here):
                tx.append(f"Where a log takes more than one glue-up, sand the flat top of the first glue-up clean in the sanding sled "
                          "(one light pass) before stacking the next layer on it.")
            dont = "put more than four bars in one glue-up or skip the dry fit. Bars slide on wet glue; a stack that rocks dry will cure crooked."
        elif here[0]["shape"] == "band":
            tx += ["Lay the two bars flat on a strip of packing tape, sawn bevels together, glue the bevels and close the joint. "
                   "Clamp the band flat between two taped cauls with light pressure across the joint from a third clamp; the cauls stop the bevels riding up.",
                   "Scrape the squeeze-out when rubbery and leave overnight."]
            dont = None
        elif here[0]["shape"] == "quarter":
            tx += ["Dry-fit in the corner cauls: the two bands lie against the cauls with their star bars meeting on the diagonal at the caul corner, and the square bar fills the open corner.",
                   "Glue all the faces that touch, seat the parts in one corner caul, close the second caul over them, and clamp both ways every 4 to 5 inches. "
                   "Sight the end: the diagonal joint must run corner to corner.",
                   "Scrape when rubbery; leave overnight."]
            dont = None
        elif here[0]["shape"] == "half":
            tx += ["Glue two quarter logs star corner to star corner, clamped between flat taped cauls with a clamp every 4 to 5 inches. "
                   "Line up the star points at the joint at both ends before the clamps go tight.",
                   "Scrape when rubbery; leave overnight."]
            dont = None
        elif here[0]["shape"] == "block":
            tx += ["Glue two half logs, star centres together. Four star points must meet at the centre: line them up at both ends, clamp lightly, look again, then tighten.",
                   "Scrape when rubbery; leave overnight."]
            dont = "glue all four quarter logs at once. Two joints at right angles under clamps slide; halves first, then the block."
        else:
            tx += ["Square-edged strips are the one case where many parts can be glued at once: lay the strips in order on taped cauls, glue the edges, "
                   "clamp across the panel every 6 inches with cauls above and below to keep it flat.",
                   "Scrape when rubbery; leave overnight."]
            dont = None
        nglue += 1
        S.append({"title": f"Glue the {what}s", "text": tx, "figs": [f"asm_log_{lg['id']}" for lg in here], "see": ["logs"], "glue": True, **({"dont": dont} if dont else {})})

        # true them
        if here[0]["kind"] == "tri":
            Hh = here[0]["h"]; Wd = here[0]["w"]
            tx = [f"Every face of a log is a glue face for the next step, so every face gets machined. Set the log in the sanding sled and run it through the "
                  f"drum sander with 80 grit until the top face is clean all the way across; turn it and do the other two faces. "
                  f"No drum sander: clamp the sled to the bench and plane the top face with a jack plane, checking with a straightedge.",
                  f"Take off as little as cleans the face, about {short(skim)}, and take the same passes on every log at the same sander setting. "
                  f"Logs glue up {short(Wd)} on a side; they finish near {dim(Wd - 2 * math.sqrt(3) * skim)} and they must all match within a few thousandths.",
                  "Check each log: the 60 degree triangle fits every corner, a straightedge shows no light along any face, and calipers read the same at both ends."]
        elif here[0]["shape"] == "band":
            tx = ["Plane both broad faces of each band clean, all bands at one planer setting, taking only what cleans them. "
                  "Then joint the square edge (the field triangle's outer face) at 90 degrees to the faces."]
        elif here[0]["kind"] == "rect":
            tx = [f"Joint one face of each log, joint an adjacent face square to it, then plane the other two faces parallel: every log through the planer at one setting. "
                  f"Take off as little as cleans the faces, about {short(skim)} a face.",
                  "Check each log is square at both ends and the same size as the others within a few thousandths."]
        else:
            tx = ["Plane both faces of each panel clean and parallel, all panels at one planer setting. These faces are the glue faces of the board. "
                  f"Bring the panels to {dim(here[0]['h'])} thick."]
        S.append({"title": f"True the {what}s", "text": tx, "figs": ["asm_true"] if here[0]["kind"] == "tri" and lv == levels[0] else [], "see": [],
                  "dont": "leave a face as it came out of the clamps. Dried glue and a bar standing a few thousandths proud hold the next joint open."})

    # crosscut
    ns = sum(lg["slices"] + lg["spares"] for lg in logs if lg["crosscut"])
    tx = ["Before cutting, mark each log: run a crayon stripe down its reference face (the face that was under the caul; on sheet 04 it is the top), "
          "write the log letter on that face every few inches, and draw a pencil line across one end. "
          "Every slice then carries the stripe on one edge, which the layout on sheet 05 uses to turn it the right way.",
          f"Square one end of each log on the sled. Then cut slices {dim(cut)} thick against the stop block (finished {short(T)} plus {short(sh['flatten_allowance'])} to flatten). "
          "Hold the log down on the fence side with a clamp or hold-down; the slice between blade and stop is free to move away, so stop the saw before reaching for it"
          + (", or use a stop that swings clear." if True else ""),
          f"Cut {ns} slices in all" + ": " + ", ".join(f"{lg['slices']} + {lg['spares']} spare from log {lg['id']}" for lg in logs if lg["crosscut"]) + ". "
          "As each slice comes off, put a pencil dot on the face that was toward the stop. Stack them by letter.",
          f"The last {short(sh['end_trim'])} of each log is waste" + (" and makes the end blocks for the row jig." if kind == "tri" else ".")]
    S.append({"title": "Crosscut the slices", "text": tx, "figs": ["asm_cut"], "see": []})

    # rows
    nrow = len(rows); per = max(len(r["pucks"]) for r in rows)
    if kind == "panel":
        tx = [f"The slices are the rows: {nrow} of them. Lay them out end grain up in the order on sheet 05, turning the ones marked with a prime end for end."]
    else:
        tx = [f"Lay out the whole board dry on a flat surface from sheet 05: {nrow} rows of up to {per} slices, each slice dot up with its crayon stripe on the edge the heavy line shows. "
              "A letter with a prime mark (A') is that log's slice turned dot down. Look at the pattern before any glue goes on.",
              "The glue faces here are the trued sides of the logs: long grain, one thin coat on each face, moderate clamp pressure."]
        if kind == "tri":
            tx += ["Glue the slices of a row in pairs first: two triangles make a diamond. Rub the joint, set the pair in the row jig against a fence, "
                   "and hold it with a spring clamp or a hand screw for 30 minutes.",
                   "Then glue the pairs into the row: slide them into the row jig between the fences, put a 60 degree end block (a waste slice cut in half) at each end "
                   "so the clamps bear on square faces, and clamp along the row. Lay a taped caul on top with a weight so nothing lifts. "
                   "Pressure along the row closes the slanted joints because the fences stop the triangles spreading.",
                   f"Glue no more than four pairs at a time; join the sections after they have set. Each row is {short(rows[0]['height'])} wide."]
        else:
            tx += ["Glue the slices of each row against the fence of the row jig, two at a time, then the pairs to each other, clamping along the row with a caul on top. "
                   "Line up the star points across each joint before tightening."]
    S.append({"title": "Glue the slices into rows", "text": tx, "figs": ["row"], "see": ["layout"], "glue": True,
              "dont": "trust a row that rocks in the jig. A slice that sits proud of the fence line will hold the next row off; take it out and find out why."})
    if kind != "panel":
        tx = ["Scrape the glue from each row and check its two long edges with a straightedge. They are the glue faces for the board and must be straight and square to the face.",
              "If an edge is out, tape the row to a straight carrier board and skim the edge on the table saw with a sharp blade, or rub it on 80 grit paper glued to a flat board. "
              "Take the same skim off the same edge of every row. Keep rows off the jointer and out of the planer: the knives hit the fibres end-on at the trailing edge and break it out."]
        S.append({"title": "True the rows", "text": tx, "figs": [], "see": []})

    tx = [f"Dry-fit the {nrow} rows in order" + (". Slide each row along its neighbour until the corners of the slices meet corner to corner along the whole joint, then draw a pencil line across every joint so the rows go back in register under glue."
                                                if kind != "panel" else " and line up the pattern, then draw a pencil line across every joint."),
          "Glue two or three rows at a time, then glue those sections together. Clamp across the rows every 4 to 5 inches with moderate pressure, "
          "with taped cauls clamped across the top and bottom near each end to keep the rows in one plane, and a stop clamped to the bench at one end so rows cannot slide along the joint.",
          "The faces being glued are long grain (the sides of the logs), so glue them as you would any edge joint: one thin coat on each face. "
          "Check the pencil lines after the clamps are on; tap a row back if it has crept.",
          "Scrape the squeeze-out when rubbery. Leave the board in clamps overnight and out of clamps a day before flattening."]
    S.append({"title": "Glue the rows into the board", "text": tx, "figs": ["board"], "see": ["layout"], "glue": True,
              "dont": "glue every row at once. More than three joints open at a time creep out of plane and out of register before the clamps are on."})

    W, L = plan["board"]["width"], plan["board"]["length"]; m = plan["board"]["margins"]
    tx = ["Flatten first, trim second. Flatten both faces with a drum sander (60 or 80 grit, light passes) or a router sled; "
          f"the slices were cut {short(sh['flatten_allowance'])} thick of finished for this. Stop at {short(T)}.",
          f"Then trim to {dim(W)} x {dim(L)} on the dashed lines on a crosscut sled or with a track saw: about {short(m[0])} comes off the left, {short(m[1])} off the right, "
          f"{short(m[2])} off the bottom and {short(m[3])} off the top, measured so the pattern stays centred as drawn. "
          "Tape the cut line and back the exit edge with scrap so the end grain does not chip.",
          "Sand both faces 80, 120, 180; wipe with a damp cloth to raise the grain, let it dry, then sand 220."]
    S.append({"title": "Flatten, then trim", "text": tx, "figs": ["trim"], "see": [],
              "dont": "run the board through a thickness planer. End grain breaks out at the trailing edge and the planer can throw pieces."})
    opts = plan["options"]
    tx = [f"Ease every edge with a {opts.get('edge', '1/8 inch chamfer')} and break the corners: sharp end-grain edges chip."]
    if opts.get("feet"): tx.append("Add four rubber feet with stainless screws, inset 1\" from the corners, so the board dries evenly underneath.")
    if opts.get("juice_groove"): tx.append("Rout a juice groove with a 1/2\" core-box bit, 3/4\" from the edge, in two light passes.")
    if opts.get("handles"): tx.append("Cut finger grips in both ends with a 1-1/4\" cove or core-box bit on the router table.")
    tx.append("Flood with food-grade mineral oil until it stops soaking in (several coats over two days), then buff on a board butter of mineral oil and beeswax. Re-oil monthly.")
    S.append({"title": "Edges and finish", "text": tx, "figs": [], "see": []})
    return S


def plan_name(plan, key):
    return next(w["name"] for w in plan["woods"] if w["key"] == key)


# ------------------------------------------------------------------------------------- OBJ + spec
def write_obj(plan, out):
    m = 0.0254; T = plan["board"]["thickness"]; tr = plan["board"]["trim"]
    cx, cy = (tr[0] + tr[2]) / 2, (tr[1] + tr[3]) / 2
    o = ["mtllib board.mtl"]; vi = 1; mtl = []
    for w in plan["woods"]:
        h = w["end"].lstrip("#"); r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        mtl.append(f"newmtl {w['key']}\nKd {r:.3f} {g:.3f} {b:.3f}\n")
    for n, f in enumerate(plan["face"]):
        pts = f["pts"]; k = len(pts)
        o.append(f"o bar_{n}_{plan['species'][f['role']]['key']}")
        o.append(f"usemtl {plan['species'][f['role']]['key']}")
        for z in (0, T):
            for x, y in pts: o.append(f"v {(x - cx) * m:.6f} {(y - cy) * m:.6f} {z * m:.6f}")
        o.append("f " + " ".join(str(vi + k + i) for i in range(k)))             # top
        o.append("f " + " ".join(str(vi + i) for i in reversed(range(k))))       # bottom
        for i in range(k):
            j = (i + 1) % k
            o.append(f"f {vi + i} {vi + j} {vi + k + j} {vi + k + i}")
        vi += 2 * k
    open(os.path.join(out, "board.obj"), "w").write("\n".join(o) + "\n")
    open(os.path.join(out, "board.mtl"), "w").write("\n".join(mtl))


def write_spec(plan, design, out):
    W, L, T = plan["board"]["width"], plan["board"]["length"], plan["board"]["thickness"]
    roles = OrderedDict()
    for r, w in plan["species"].items(): roles.setdefault(w["name"], (w["end"], []))[1].append(r)
    lines = [f"- The piece is an end-grain cutting board, {frac(W)} x {frac(L)} inches and {frac(T)} inches thick, "
             f"lying flat. The drawing is colour coded by wood; keep every piece of the pattern exactly where it is drawn, "
             f"same count, same shapes, same colours: " + "; ".join(f"{c} is {n}" for n, (c, _) in roles.items()) + ".",
             f"- Pattern: {design.get('description') or plan['name']}. It is made of end grain: every piece on the top shows "
             "fine end-grain pores and faint growth-ring arcs, the pieces meet at crisp, tight glue lines, and the pattern "
             "runs right to the edges. The four edges show the same woods as long-grain stripes running vertically.",
             "- " + design.get("finish_words", "Finish: sanded smooth, oiled with mineral oil and board butter, a soft satin sheen; "
                                               "edges eased with a small chamfer, corners slightly rounded.")]
    open(os.path.join(out, "spec.md"), "w").write("\n".join(lines) + "\n")
    room = design.get("render", {}).get("room") or (
        "A warm, modern kitchen: the board sits on a pale honed-marble or light oak counter near a window with soft "
        "late-morning daylight from the left. Beside it, but not covering it: a chef's knife, a few cherry tomatoes and "
        "a sprig of basil, a linen towel. Background softly out of focus: a white tile backsplash, a ceramic crock of "
        "wooden spoons. Shallow depth of field, the board sharp. Do not cover or hide any part of the board's top.")
    open(os.path.join(out, "room.md"), "w").write(room + "\n")


# ------------------------------------------------------------------------------------- HTML
from plan_page import page  # noqa: E402  (the sheet-style plan page)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("design"); ap.add_argument("out"); ap.add_argument("--photo")
    a = ap.parse_args()
    d = json.load(open(a.design))
    plan = build(d, a.out, a.photo)
    W, L, T = plan["board"]["width"], plan["board"]["length"], plan["board"]["thickness"]
    print(f"{plan['name']}: {W:.3f} x {L:.3f} x {T:.3f} in, {plan['n_slices']} slices in {len(plan['rows'])} rows, "
          f"{sum(b['total_bars'] for b in plan['bars'])} bars, {len(plan['bar_types'])} bar shapes, {len(plan['logs'])} log types")
    for b in plan["bar_types"]:
        print(f"  bar {b['id']}: {b['label']}" + (f", tilt {b['tilt']:.1f}" if b["tilt"] else ""))
    for l in plan["logs"]:
        print(f"  {l['name']} ({l['what']}): " + ", ".join(f"{k} x {ln:g} in" for ln, k in l["make"]) + (f" -> {l['slices']} slices (+{l['spares']})" if l["crosscut"] else ""))
    for s in plan["stock"]:
        print(f"  buy {s['species']}: {s['bf_buy']:g} bd ft")
    bad = [c for c in plan["checks"] if not c["ok"] and c["level"] != "warn"]
    for c in plan["checks"]:
        print(("  ok   " if c["ok"] else "  WARN " if c["level"] == "warn" else "  FAIL ") + c["what"] + (f" ({c['detail']})" if c["detail"] else ""))
    print("wrote", os.path.abspath(a.out))
    sys.exit(1 if bad else 0)
