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
                "stock_width": 5.5, "spare_slices": 1, "rip_oversize": 1 / 32, "true_skim": 0.01, "hold_end": 2.0, "edge_clean": 0.125, "sander_opening": 3.0,
                "glue_extra": 0.5, "blank_remainder": 1.0, "max_cut_height": 3.125, "sled_base": 0.5, "min_bar_face": 0.375}
S3 = math.sqrt(3)
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


RIP_TEXT = ("Every bevelled bar is cut on the rip sled (sheet 06, step 2), the sliding rip jig with toggle clamps that the builders in the best practices guide use. "
       "The sled runs against the rip fence, and the fence stays on the side the blade leans away from: its usual place on a left-tilt saw; on a right-tilt saw move the fence to the left of the blade. "
       "The fence deck, between the fence and the blade, carries the locating fence and the toggle clamps. The landing deck, beyond the blade and under its lean, catches what comes off. "
       "Nothing is ever loose on the saw table. Trapezoids and diamonds start as square-edged strips and are clamped to the fence deck for both bevels; only a waste sliver drops on the landing deck. "
       "A triangle leaves no flat for a clamp, so there the wide blank is clamped and the triangle bar comes off on the landing deck, held between its stop strip and the blade, and rides along with the sled. "
       "After every pass push the sled on until the work is clear of the blade, or switch off and wait for the blade to stop, before lifting anything out. Keep the riving knife in place.")


RIP = "Cut on the rip sled as in The bevel rip at the top of this sheet; this bar's setup is drawn above."


def recipe(key, p, L, A, shop, outside=False):
    """How to make this cross-section: rip it 1/32" over on the table saw, then machine the sawn faces to size.
    outside=True: the sawn faces end up on the outside of a glue-up and are machined with it, so they keep the allowance.
    Returns kind, label, blank thickness, the width each bar uses across the blank, blade tilt, steps, warnings."""
    kerf = shop["kerf"]; ov = shop.get("rip_oversize", 1 / 32); n = len(p); warn = []
    eq = lambda a, b, t=1e-3: abs(a - b) < t
    tan = lambda d: math.tan(math.radians(d)); cos = lambda d: math.cos(math.radians(d))
    def deep(stock, tilt):
        cap = shop["max_cut_height"] * cos(tilt) - shop["sled_base"]
        if stock > cap - 0.02: warn.append(f"The {tilt:.0f} degree rip through {short(stock)} stock on the rip sled is deeper than the saw cuts at that tilt (about {short(cap)}); make the pattern smaller.")
        return (f" This cut is {short(stock)} deep over the sled with the blade tilted, close to the limit of a 10\" saw (about {short(cap)}): raise the blade fully and feed slowly."
                if stock > cap - 0.35 else "")
    if n == 4 and all(eq(a, 90, 0.05) for a in A):
        w, h = max(L[0], L[1]), min(L[0], L[1])
        sq = eq(w, h)
        return {"kind": "square" if sq else "rect", "label": f"{short(w)} square" if sq else f"{short(h)} x {short(w)} rectangle",
                "dims": {"width": w, "thick": h}, "stock": h, "per_bar": w + ov + kerf, "lead": 0.0, "tilt": 0, "stop": w + ov, "setup": "square",
                "steps": [f"Mill the blank to {dim(h)} thick.",
                          f"Blade square. Rip bars {dim(w + ov)} wide with the fence {short(w + ov)} from the blade.",
                          f"Stand the bars on edge, a handful side by side, and plane the sawn edges to {dim(w)}: half off each edge, every bar at one planer setting."],
                "warn": warn}
    if n == 4 and eq(L[0], L[2]) and eq(L[1], L[3]) and eq(A[0], A[2], 0.05):
        th = min(A); pside, qside = (L[0], L[1])
        if qside > pside: pside, qside = qside, pside
        sn = math.sin(math.radians(th)); t = qside * sn; d2 = pside * sn; tilt = 90 - th
        kind = "rhombus" if eq(pside, qside) else "parallelogram"
        if tilt > 45.01:
            warn.append(f"Needs a {tilt:.1f} degree blade tilt, past a table saw's 45; change the angle.")
        stop = pside + (2 * ov if outside else ov) / sn; strip = stop + t * tan(tilt) + 0.0625
        st = [f"Mill the blank to {dim(t)} thick (the bar's height lying on its {short(pside)} face).",
              f"Blade square. Rip square-edged strips {dim(strip)} wide, the ordinary way, fence {short(strip)} from the blade.",
              f"Tilt the blade {tilt:.1f} degrees from vertical; set it with a digital angle gauge, not the saw's scale. " + RIP +
              f" Clamp a strip against the locating fence and bevel one edge. Then roll the strip over (the same end leading, the other face up) so the sawn edge is against the locating fence, "
              f"its sharp corner down on the deck, and bevel the other edge. The two bevels come out parallel. Set the locating fence with test strips until the face lying on the deck measures {dim(stop)} "
              f"({short(pside)} plus the allowance); that one setting does both passes." + deep(t, tilt)]
        if outside:
            st.append("Leave the two sawn faces as they are. They carry the allowance and are planed with the band after it is glued; the two planed faces are the glue faces.")
        else:
            st.append(f"Machine the two sawn faces: lay the bars on a sawn face, packed tight side by side between two fences on a flat carrier board (they lean on each other like roof tiles; "
                      f"tape across both ends), and plane or drum-sand to {dim(d2)}, half from each sawn face"
                      + (", which is the setting the blank was milled at." if kind == "rhombus" else "."))
        st.append(f"Check: corners {th:.0f} and {180 - th:.0f} degrees, " + (f"all four faces {dim(pside)}." if kind == "rhombus" and not outside else f"planed faces {dim(pside)}."))
        return {"kind": kind, "label": f"{th:.0f}-degree {'diamond' if kind == 'rhombus' else 'parallelogram'}, {short(pside)} faces" + ("" if kind == "rhombus" else f" x {short(qside)}"),
                "dims": {"side": pside, "slant": qside, "angle": th, "thick": t}, "stock": t, "stop": stop, "setup": "para", "lead": 0.0, "strip": strip,
                "per_bar": strip + kerf, "tilt": tilt, "steps": st, "warn": warn}
    if n == 4:   # isosceles trapezoid
        for i in range(4):
            if eq(A[i], A[(i + 1) % 4], 0.05) and eq(A[i] + A[(i + 2) % 4], 180, 0.05) and eq(L[i - 1], L[(i + 1) % 4]) and A[i] < 89.9:
                th = A[i]; long_, short_, leg = L[i], L[(i + 2) % 4], L[i - 1]
                H = leg * math.sin(math.radians(th)); tilt = 90 - th
                if tilt > 45.01: warn.append(f"Needs a {tilt:.1f} degree tilt, past a table saw's 45.")
                e_ = ov / math.sin(math.radians(th)); v60 = eq(th, 60, 0.05)
                strip = long_ + e_ + 0.0625
                st = [f"Mill the blank to {dim(H)} thick (the trapezoid's height).",
                      f"Blade square. Rip square-edged strips {dim(strip)} wide, the ordinary way, fence {short(strip)} from the blade.",
                      f"Tilt the blade {tilt:.1f} degrees from vertical (digital angle gauge). " + RIP +
                      f" Clamp a strip against the locating fence and bevel one edge. Turn the strip end for end, the same face up, sawn edge against the locating fence, and bevel the other edge. "
                      f"The bar sits wide face up, under the caul. Set the locating fence with test strips until the wide face measures {dim(long_ + e_)}; that one setting does both passes." + deep(H, tilt),
                      (f"True the two sawn faces in the {short(long_)} V block (sheet 06, step 2): wide face against one wall, a sawn face up and level. One light pass, turn the bar end for end, one more; "
                       f"every bar at one setting, until the wide face is {dim(long_)} and the narrow face {dim(short_)}." if v60 else
                       f"True the two sawn faces with the bar held in a carrier that tips a sawn face level, one light pass each, until the wide face is {dim(long_)} and the narrow face {dim(short_)}."),
                      f"Check: {th:.0f} degree corners on the wide face, slanted faces {dim(leg)}."]
                return {"kind": "trapezoid", "label": f"{th:.0f}-degree trapezoid, {short(long_)} and {short(short_)} faces",
                        "dims": {"long": long_, "short": short_, "leg": leg, "angle": th, "thick": H}, "stock": H, "stop": long_ + e_, "setup": "trap", "strip": strip,
                        "lead": 0.0, "vsize": long_ if v60 else None,
                        "per_bar": strip + kerf, "tilt": tilt, "steps": st, "warn": warn}
    if n == 6 and all(eq(a, 120, 0.05) for a in A) and all(eq(l, L[0]) for l in L):
        s_ = L[0]; ff = s_ * math.sqrt(3)
        st = [f"Mill the blank to {dim(ff)} thick (the hexagon across its flats) and rip strips {dim(2 * s_ + ov)} wide, blade square.",
              "Tilt the blade 30.0 degrees from vertical (digital angle gauge).",
              f"Bevel all four long corners of each strip: flat face on the table, fence set so the cut ends at mid-thickness, rip, turn the strip end for end, rip, then flip it over and repeat. Every face is then {dim(s_)}.",
              "True the four sawn faces with one light pass each.",
              "Check every corner is 120 degrees and the three across-flats measurements match."]
        return {"kind": "hexagon", "label": f"regular hexagon, {short(s_)} faces", "dims": {"side": s_, "flats": ff, "thick": ff},
                "stock": ff, "per_bar": 2 * s_ + ov + kerf, "lead": 0.0, "tilt": 30.0, "steps": st, "warn": warn, "stop": 2 * s_ + ov, "setup": None}
    if n == 3:
        for i in range(3):
            a_, b_ = L[i - 1], L[i]
            if eq(a_, b_):
                phi = A[i]; base = L[(i + 1) % 3]; H = a_ * cos(phi / 2); tilt = phi / 2
                equi = eq(phi, 60, 0.05) and eq(base, a_)
                kind = "equilateral triangle" if equi else ("right isosceles triangle" if eq(phi, 90, 0.05) else "isosceles triangle")
                if tilt > 45.01: warn.append(f"Needs a {tilt:.1f} degree tilt, past a table saw's 45.")
                pf = ov if (outside or not equi) else ov / 2                     # allowance on each sawn face
                dH = pf / math.sin(math.radians(tilt)); e_ = 2 * pf / cos(tilt)
                st = [f"Mill the blank to {dim(H + dH)} thick (the triangle's height plus the allowance).",
                      f"Tilt the blade {tilt:.1f} degrees from vertical (digital angle gauge). " + RIP + " Clamp the blank on the fence deck with its free edge over the slot and rip one bevel along it; that strip is waste." + deep(H + dH, tilt),
                      f"For every bar: turn the blank over end for end (the same edge stays toward the blade, the other face goes down), slide it across until its sharp lower edge touches the landing stop, "
                      f"close the clamps on it and push the sled through. The bar is left on the landing deck, base down and point up, between the stop and the blade. "
                      f"Screw the landing stop {dim(base + e_)} from the blade at the deck, then confirm on a test bar. When the blank gets too narrow for the clamp pads, lay the caul across it and a scrap of the same thickness."]
                if outside or not equi:
                    st.append(f"Leave the two sawn faces as they are. They end up on the outside of the glue-up and are machined with it; the planed base is the glue face.")
                else:
                    st.append(f"True the two sawn faces in the {short(base)} V block (sheet 06, step 2): base against one wall, a sawn face up and level. Light passes, every bar at one setting, "
                              f"until all three faces are {dim(base)}.")
                st.append(f"Check: {phi:.0f} degrees at the point" + (f", all three faces {dim(base)}." if equi and not outside else f"; the base is {dim(base + e_)} as sawn and {dim(base)} once the glue-up is trued."))
                return {"kind": kind, "label": f"{kind}, {short(base)} " + ("faces" if equi else "base"), "dims": {"base": base, "leg": a_, "apex": phi, "thick": H + dH},
                        "stock": H + dH, "stop": base + e_, "setup": "flip", "lead": (H + dH) * tan(tilt) + 0.125, "vsize": base if equi and not outside else None,
                        "per_bar": (base + e_) / 2 + kerf / cos(tilt), "tilt": tilt, "steps": st, "warn": warn}
    if n == 3:
        for i in range(3):
            if eq(A[i], 90, 0.05):
                l1, l2 = L[i - 1], L[i]; short_, long_ = min(l1, l2), max(l1, l2)
                tilt = math.degrees(math.atan2(short_, long_)); hyp = math.hypot(short_, long_)
                st = [f"Mill the blank to {dim(long_)} thick and rip strips {dim(short_)} wide, blade square.",
                      f"Tilt the blade {tilt:.1f} degrees from vertical (digital angle gauge) and rip each strip corner to corner, standing on its narrow face in a carrier that holds it against the fence. Both halves are bars.",
                      f"Check: faces {dim(short_)} and {dim(long_)}, long face {dim(hyp)}, corners 90, {90 - tilt:.0f} and {tilt:.0f} degrees."]
                return {"kind": "right triangle", "label": f"{tilt:.0f}/{90 - tilt:.0f}-degree right triangle, {short(short_)} x {short(long_)}",
                        "dims": {"short": short_, "long": long_, "hyp": hyp, "thick": long_}, "stock": long_, "stop": short_, "setup": None, "lead": 0.0,
                        "per_bar": short_ / 2 + kerf / 2 / cos(tilt), "tilt": tilt, "steps": st, "warn": warn}
    xs = [v[0] for v in p]; ys = [v[1] for v in p]
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    warn.append("Irregular cross-section with no table-saw setup; change the pattern or the log size.")
    return {"kind": "polygon", "label": f"{n}-sided bar", "dims": {"bbox": [bw, bh]}, "stock": min(bw, bh), "stop": None, "setup": None, "lead": 0.0,
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
        self.el = []; self.title = title; self.ext = None

    def _see(self, x, y):
        e = self.ext
        self.ext = [x, y, x, y] if e is None else [min(e[0], x), min(e[1], y), max(e[2], x), max(e[3], y)]

    def P(self, x, y):
        q = (self.pad + (x - self.x0) * self.s, self.pad + (self.y1 - y) * self.s)
        self._see(*q); return q

    def poly(self, pts, fill="none", stroke="#222", sw=0.6, dash=None, op=1):
        d = " ".join(f"{a:.2f},{b:.2f}" for a, b in (self.P(*v) for v in pts))
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.el.append(f'<polygon points="{d}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}"{da} stroke-linejoin="round"/>')

    def line(self, a, b, stroke="#222", sw=1, dash=None, raw=False):
        (x1, y1), (x2, y2) = (a, b) if raw else (self.P(*a), self.P(*b))
        self._see(x1, y1); self._see(x2, y2)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.el.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{stroke}" stroke-width="{sw}"{da}/>')

    def text(self, xy, s, size=12, anchor="middle", fill="#222", raw=False, weight="normal", rot=0, halo=False):
        x, y = xy if raw else self.P(*xy)
        tw = 0.62 * size * len(s) + 4; x_a = x - (tw / 2 if anchor == "middle" else tw if anchor == "end" else 0)
        if rot: self._see(x - size, y - tw / 2); self._see(x + size, y + tw / 2)
        else: self._see(x_a, y - size * 0.8); self._see(x_a + tw, y + size * 0.8)
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
        m = 12; e = self.ext or [0, 0, self.w, self.h]     # the drawing is cropped to what was drawn, so nothing is clipped and nothing floats in white
        vx, vy, vw, vh = e[0] - m, e[1] - m, e[2] - e[0] + 2 * m, e[3] - e[1] + 2 * m
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx:.0f} {vy:.0f} {vw:.0f} {vh:.0f}" width="{vw:.0f}" '
                f'height="{vh:.0f}" font-family="{FONT}">{t}<rect x="{vx:.0f}" y="{vy:.0f}" width="{vw:.0f}" height="{vh:.0f}" fill="#fff"/>'
                + "".join(self.el) + "</svg>")


def bbox_of(polys):
    xs = [v[0] for p in polys for v in p]; ys = [v[1] for p in polys for v in p]
    return (min(xs), min(ys), max(xs), max(ys))


# ------------------------------------------------------------------------------------- main build
LEVEL_NAME = {"tri": "triangle log", "band": "band", "quarter": "quarter log", "half": "half log", "block": "block log", "border": "border bar", "panel": "strip panel"}
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
    frame = design.get("frame") or None; rings = []       # rings round the field, inner first: an optional liner, then the frame
    if frame:
        if frame.get("liner"): rings.append(("liner", float(frame["liner"].get("width", 0.375)), frame["liner"].get("species", "maple")))
        rings.append(("frame", float(frame.get("width", 1.0)), frame.get("species", "walnut")))
    fw = sum(r[1] for r in rings)
    g = patterns.generate(dict(design, board=dict(board, width=board["width"] - 2 * fw, length=board["length"] - 2 * fw)) if frame else design)
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
    # Sizes after truing. Every truing pass takes a skim off the faces it machines, so logs, rows and the board all
    # finish a little under the drawn pattern. The pattern is laid out at its drawn size, then scaled to the trued size.
    skim = shop["true_skim"]; ec = shop["edge_clean"]; S3_ = math.sqrt(3)
    kind0 = cells.get("kind", "panel"); ang = math.radians(cells.get("angle", 0)); ca, sa = math.cos(ang), math.sin(ang)
    drawn = list(trim); cen = ((trim[0] + trim[2]) / 2, (trim[1] + trim[3]) / 2)
    G = lambda p: (p[0] * ca + p[1] * sa, -p[0] * sa + p[1] * ca)          # board -> row frame (u along the rows, v across them)
    Bd = lambda p: (p[0] * ca - p[1] * sa, p[0] * sa + p[1] * ca)
    across_x = abs(sa) > 0.5
    ku = kv = 1.0; sizes = {}; plan_trim = list(trim)
    if kind0 == "tri":
        L1 = float(cells["side"]); lv = int(cells.get("levels", 1)); S0 = L1 * lv
        t1 = L1 - 2 * S3_ * skim; sizes[1] = (L1, t1); St = t1
        if lv == 2: St = 2 * t1 - 2 * S3_ * skim; sizes[2] = (2 * t1, St)
        H0 = S0 * S3_ / 2; Ht = St * S3_ / 2 - 2 * skim; ku = St / S0; kv = Ht / H0
        Wq, Lq = trim[2] - trim[0], trim[3] - trim[1]
        across_req, along_req = (Wq, Lq) if across_x else (Lq, Wq)
        n = max(1, round((across_req + 2 * ec) / Ht))
        v0 = G(cells.get("origin", (0, 0)))[1]
        best = None
        for c in sorted(g.get("centers") or [cen], key=lambda c: math.dist(c, cen))[:40]:
            cv = G(c)[1] - v0; half = 0.0
            for m0 in range(math.floor(cv / H0 - n / 2) - 1, math.floor(cv / H0 - n / 2) + 3):
                half = max(half, min(cv - m0 * H0, (m0 + n) * H0 - cv))
            half = min(across_req / kv / 2, half - ec / kv)
            sc_ = (round(-half, 3), math.dist(c, cen))
            if best is None or sc_ < best[0]: best = (sc_, c, half)
        _, cen, half = best
        if g.get("period"):       # no mirror line across the rows: end both cuts at the same point of the repeat
            along_req = max(1, round(along_req / (g["period"] * ku))) * g["period"] * ku
        cu, cv = G(cen); hu = along_req / ku / 2
        def rect(du, dv):
            q = [Bd((cu + a * (hu + du), cv + b * (half + dv))) for a in (-1, 1) for b in (-1, 1)]
            return [min(v[0] for v in q), min(v[1] for v in q), max(v[0] for v in q), max(v[1] for v in q)]
        trim = rect(0, 0); plan_trim = rect(ec / ku + 0.01, -1e-4)
        mo = g.get("motif")       # a motif the trim would cut through is left out: its pieces become ground
        if mo and design.get("whole_motifs", True):
            rr = mo["radius"] - 0.02
            for p in polys:
                c = p.get("motif")
                if c and not (trim[0] + rr <= c[0] <= trim[2] - rr and trim[1] + rr <= c[1] <= trim[3] - rr): p["role"] = mo["ground"]
    elif kind0 == "blocks":
        S_ = float(cells["side"]) * (2 + math.sqrt(2)); ku = kv = (S_ - 6 * skim) / S_
    lp = LG.plan(polys, plan_trim, cells, lambda r: sp[r]["key"], bar_ok)
    logs = lp["logs"]; rows = lp["rows"]; kind = lp["info"]["kind"]
    cu, cv = G(cen)
    def SC(p):
        u, v = G(p); return Bd((cu + (u - cu) * ku, cv + (v - cv) * kv))
    for r in rows:
        r["pts"] = [SC(v) for v in r["pts"]]; r["height"] *= kv; r["length"] *= ku
        for pk in r["pucks"]:
            pk["pts"] = [SC(v) for v in pk["pts"]]; pk["ref"] = tuple(SC(v) for v in pk["ref"])
            pk["cells"] = [(ro, [SC(v) for v in pts]) for ro, pts in pk["cells"]]
    polys = [dict(p, pts=[SC(v) for v in p["pts"]]) for p in polys]
    q = [SC((trim[a], trim[b])) for a in (0, 2) for b in (1, 3)]
    trim = [min(v[0] for v in q), min(v[1] for v in q), max(v[0] for v in q), max(v[1] for v in q)]
    _ax = 0 if across_x else 1
    rows.sort(key=lambda r: sum(v[_ax] for v in r["pts"]) / len(r["pts"]))
    for n_, r in enumerate(rows): r["n"] = n_ + 1
    byid = {lg["id"]: lg for lg in logs}
    for lg in logs:
        lg["shape"] = lg.get("shape") or lg["kind"]
        lg["name"] = f"Log {lg['id']}"
        lg["what"] = LEVEL_NAME.get(lg["shape"], "log")
        if lg["kind"] == "tri": lg["glued"], lg["trued"] = sizes[lg["level"]]
    if kind == "blocks":
        h_ = S_ / 2; d_ = skim; q_ = float(cells["side"]) / math.sqrt(2)
        bsz = {"band": ((h_, q_ + 2 * shop["rip_oversize"]), (h_, q_)), "quarter": ((h_, h_), (h_ - d_, h_ - d_)),
               "half": ((h_ - d_, 2 * (h_ - d_)), (h_ - 2 * d_, 2 * h_ - 2 * d_)), "block": ((S_ - 4 * d_, S_ - 2 * d_), (S_ - 6 * d_, S_ - 4 * d_))}
        for lg in logs:
            if lg["shape"] in bsz: lg["glued"], lg["trued"] = bsz[lg["shape"]]
    lp["info"]["row_height"] = rows[0]["height"]; lp["info"]["scale"] = (ku, kv)
    xs = [v[0] for r in rows for v in r["pts"]]; ys = [v[1] for r in rows for v in r["pts"]]
    glued = [min(xs), min(ys), max(xs), max(ys)]
    if kind != "tri":
        trim = [trim[0] + ec, trim[1] + ec, trim[2] - ec, trim[3] - ec]
        trim = [max(trim[0], glued[0] + ec), max(trim[1], glued[1] + ec), min(trim[2], glued[2] - ec), min(trim[3], glued[3] - ec)]
    def covered(rc):
        if rc[2] - rc[0] <= 0 or rc[3] - rc[1] <= 0: return False
        a_ = sum(abs(area(c)) for r in rows for pk in r["pucks"] for c in [clip_rect(pk["pts"], rc)] if c)
        return abs(a_ - (rc[2] - rc[0]) * (rc[3] - rc[1])) < 2e-6 * (rc[2] - rc[0]) * (rc[3] - rc[1])
    full = list(trim)                     # how far each cut could move out before it ran off the slices
    for i in range(4):
        lo, hi = trim[i], glued[i]
        for _ in range(14):
            mid = (lo + hi) / 2; t_ = list(trim); t_[i] = mid
            if covered(t_): lo = mid
            else: hi = mid
        full[i] = lo
    W, Lb = trim[2] - trim[0], trim[3] - trim[1]; Wf, Lf = W, Lb
    margins = [trim[0] - full[0], full[2] - trim[2], trim[1] - full[1], full[3] - trim[3]]
    zig = ([False, False, True, True] if across_x else [True, True, False, False]) if kind == "tri" else [False] * 4

    face = []
    for r in rows:      # the face as it is really built: one polygon per piece of wood in each slice
        for pk in r["pucks"]:
            for role, pts in pk["cells"]:
                c = clip_rect(pts, trim)
                if c: face.append({"pts": c, "role": role})
    pa = sum(abs(area(c)) for r in rows for pk in r["pucks"] for c in [clip_rect(pk["pts"], trim)] if c)
    frame_out = None
    if frame:
        cur = list(trim); long_x = W > Lb; ro = []
        for role, rw, spc in rings:
            fsp = SP.get(spc); sp[role] = fsp; woods.setdefault(fsp["key"], fsp)
            t0, t1, t2, t3 = cur
            if long_x: pcs = [[t0, t1 - rw, t2, t1], [t0, t3, t2, t3 + rw], [t0 - rw, t1 - rw, t0, t3 + rw], [t2, t1 - rw, t2 + rw, t3 + rw]]
            else: pcs = [[t0 - rw, t1, t0, t3], [t2, t1, t2 + rw, t3], [t0 - rw, t1 - rw, t2 + rw, t1], [t0 - rw, t3, t2 + rw, t3 + rw]]
            for a, b, c, d in pcs: face.append({"pts": [(a, b), (c, b), (c, d), (a, d)], "role": role})
            ro.append({"role": role, "width": rw, "species": fsp["name"], "key": fsp["key"], "pieces": pcs, "inner": list(cur),
                       "long": max(t2 - t0, t3 - t1), "short": min(t2 - t0, t3 - t1) + 2 * rw})
            cur = [t0 - rw, t1 - rw, t2 + rw, t3 + rw]
        frame_out = {"width": fw, "species": ro[-1]["species"], "outer": cur, "rings": ro}
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
    ends = shop["end_trim"] + shop["hold_end"]; usable = shop["max_log_length"] - ends
    for lg in logs: lg["make"] = defaultdict(int)
    for lg in logs:
        if not lg["crosscut"]: continue
        n = npk[lg["id"]]; need = n + max(shop["spare_slices"], math.ceil(n * 0.05))
        k = max(1, math.ceil(need * pitch / usable)); per = math.ceil(need / k)
        length = _up(per * pitch + ends)
        lg.update(slices=n, spares=k * per - n, per_log=per); lg["make"][length] += k
    bar_types = OrderedDict(); need = defaultdict(lambda: defaultdict(int))
    for lg in sorted(logs, key=lambda l: -l["level"]):
        for st in lg["stages"]:
            for part in st["parts"]:
                for ln, k in list(lg["make"].items()):
                    if "log" in part:
                        byid[part["log"]]["make"][_up(ln + shop["glue_extra"])] += k
                    else:
                        key, pp, L, A = shape_of(part["pts"]); key = (key, bool(part.get("outside")))
                        if key not in bar_types:
                            bar_types[key] = {"id": None, "recipe": recipe(key[0], pp, L, A, shop, key[1]), "pts": pp, "sides": L, "angles": A}
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
    check(not small, f"No bar has a face under {short(shop['min_bar_face'])}", ", ".join(small) + ("; make the pattern larger" if small else ""), "warn")

    bars_out = []
    for (key, wkey), byl in need.items():
        bt = bar_types[key]; rc = bt["recipe"]
        per_blank = max(1, int((shop["stock_width"] - shop["blank_remainder"] - rc.get("lead", 0)) // rc["per_bar"]))
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
    if frame:       # each ring: a board planed to the ring's width, crosscut into blocks that stand on end
        sw = shop["stock_width"] - 0.25
        for r in frame_out["rings"]:
            run = 2 * r["long"] + 2 * r["short"] + 4.0; rw = r["width"]
            per = (math.ceil((r["long"] + 0.5) / sw), math.ceil((r["short"] + 0.5) / sw))
            nblk = 2 * (per[0] + per[1]) + 1; fl = math.ceil(nblk * pitch + shop["hold_end"] + shop["end_trim"])
            q = nominal(rw); r.update(blocks=nblk, block_len=sw, stock_len=fl, per_side=per)
            st = stock.setdefault(r["key"], {"species": r["species"], "items": [], "bf": 0})
            st["items"].append({"bar": r["role"], "mill_to": rw, "rough": f"{q}/4" if q else "glue up", "per_blank": nblk,
                                "blanks": [{"n": 1, "size": f'{short(rw)} x {short(sw)} x {fl}"', "yield": f"{nblk} {r['role']} blocks"}]})
            st["bf"] += (q or 8) / 4 * shop["stock_width"] * fl / 144
    for st in stock.values():
        st["bf_buy"] = math.ceil(st["bf"] * 1.25 * 2) / 2

    # shop limits
    for lg in logs:
        if lg["crosscut"]:
            hh = lg["trued"] * math.sqrt(3) / 2 if lg["kind"] == "tri" else min(lg["trued"]) if "trued" in lg else lg["h"]
            cap = shop["max_cut_height"] - shop["sled_base"]
            check(hh <= cap + 1e-6, f"{lg['name']} fits under the saw on the crosscut sled",
                  f'{short(hh)} tall on a {short(shop["sled_base"])} sled base; the blade clears {short(shop["max_cut_height"])}'
                  + ("" if hh <= cap + 1e-6 else ". Make the pattern smaller, or crosscut on a bandsaw or a 12 inch saw and set shop.max_cut_height"))
    mx = max(len(st["parts"]) for lg in logs for st in lg["stages"] if lg["kind"] != "panel")if any(lg["kind"] != "panel" for lg in logs) else 0
    check(mx <= 4, "No log glue-up has more than four parts", f"largest has {mx}" if mx else "", "warn")
    crossed = [lg for lg in logs if lg["crosscut"]]
    check(len(logs) <= 8, "A manageable number of log types", f"{len(logs)} log types, {len(crossed)} of them sliced", "warn")
    check(min(margins) >= ec - 3e-3, f"At least {short(ec)} to trim on every edge", ", ".join(f"{short(m)}" for m in margins) + " (left, right, bottom, top)")
    check(T >= 1.0, "Board at least 1\" thick (end grain under 1\" can split)", f"{T}\"")
    W, Lb = W + 2 * fw, Lb + 2 * fw
    check(max(W, Lb) / T <= 18, "Board not too large for its thickness", f"{W:.1f} x {Lb:.1f} x {T}", "warn")

    plan = {"name": design.get("name", design["pattern"]), "description": design.get("description", ""), "pattern": design["pattern"],
            "board": {"width": W, "length": Lb, "thickness": T, "trim": trim, "glued": glued, "full": full, "zig": zig, "drawn": drawn, "margins": margins, "center": list(cen), "field": [Wf, Lf], "frame": frame_out},
            "shop": shop, "species": {r: sp[r] for r in list(roles) + [r[0] for r in rings]}, "woods": list(woods.values()),
            "notes": g.get("notes", []) + design.get("notes", []), "options": design.get("options", {}),
            "face": face, "polygons": polys,
            "bar_types": [dict(id=bt["id"], label=bt["recipe"]["label"], kind=bt["recipe"]["kind"], dims=bt["recipe"]["dims"], tilt=bt["recipe"]["tilt"],
                               steps=bt["recipe"]["steps"], pts=bt["pts"], sides=bt["sides"], angles=bt["angles"], stop=bt["recipe"].get("stop"),
                               setup=bt["recipe"].get("setup"), strip=bt["recipe"].get("strip"), vsize=bt["recipe"].get("vsize"), stock=bt["recipe"]["stock"]) for bt in bar_types.values()],
            "bars": bars_out, "logs": logs, "rows": rows, "info": lp["info"], "stock": list(stock.values()), "checks": checks, "method": "logs",
            "slice_cut": cut, "n_slices": sum(len(r["pucks"]) for r in rows)}
    plan["vblocks"] = vblocks(plan)
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


def vblocks(plan):
    """V blocks: one per size of three-cornered part and per height. The walls stop 3/16" under the top of the part,
    so they bear on nearly all of it and the top still stands proud for the caul or the sander."""
    need = []
    def add(size, h, what):
        wall = max(0.25, math.floor((h - 0.1875) * 16 + 1e-6) / 16)
        for v in need:
            if abs(v["size"] - size) < 2e-3 and abs(v["hb"] - wall) < 0.13:
                v["hb"] = min(v["hb"], wall)
                if what not in v["uses"]: v["uses"].append(what)
                return v
        need.append({"size": size, "hb": wall, "uses": [what]}); return need[-1]
    for bt in plan["bar_types"]:
        if bt.get("vsize"):
            hh = bt["vsize"] * S3 / 2; bt["vwall"] = add(bt["vsize"], hh, f"bar {bt['id']}")["hb"]
    for lg in plan["logs"]:
        if lg["kind"] != "tri": continue
        top = 0.0; n = len(lg["stages"])
        for k, st in enumerate(lg["stages"]):
            top = max(top, max(v[1] for p in st["parts"] for v in p["pts"]))
            st["vsize"] = top / (S3 / 2)
            if k < n - 1: add(st["vsize"], top, f"log {lg['id']} glue-up {k + 1}")
        add(lg["w"], lg["h"], f"log {lg['id']}")
    mg = []
    for v in sorted(need, key=lambda v: (v["hb"], -v["size"])):      # a V has no size but its wall height: parts needing the same wall share a block
        m = next((o for o in mg if abs(o["hb"] - v["hb"]) < 1e-3), None)
        if m:
            m["sizes"].append(v["size"]); m["uses"] += [u for u in v["uses"] if u not in m["uses"]]
        else:
            v["sizes"] = [v["size"]]; mg.append(v)
    out = sorted(mg, key=lambda v: v["hb"])
    opening = plan["shop"].get("sander_opening", 3.0)
    for v in out:
        nl = math.ceil(v["hb"] / 0.75 - 1e-6)
        v["mat"] = f"{short(v['hb'])} plywood or hardboard" if v["hb"] <= 0.5 and abs(v["hb"] * 8 - round(v["hb"] * 8)) < 1e-6 else ("3/4\" MDF" if nl == 1 else f"{nl} layers of 3/4\" MDF glued up") + ("" if abs(nl * 0.75 - v["hb"]) < 1e-6 else f", ripped or planed to {short(v['hb'])} thick")
        v["tall"] = v["size"] * S3 / 2; v["base"] = 0.75 if v["tall"] + 0.75 <= opening - 0.1 else 0.25
        v["name"] = f"V block with {short(v['hb'])} sides"
    return out


def _flat_pts(pts):
    pts = [tuple(p) for p in pts]; n = len(pts)
    i = max(range(n), key=lambda i: math.dist(pts[i], pts[(i + 1) % n]))
    a, b = pts[i], pts[(i + 1) % n]; ang = -math.atan2(b[1] - a[1], b[0] - a[0]); c, s_ = math.cos(ang), math.sin(ang)
    out = [((x - a[0]) * c - (y - a[1]) * s_, (x - a[0]) * s_ + (y - a[1]) * c) for x, y in pts]
    return [(x, -y) for x, y in out] if sum(y for _, y in out) < 0 else out


def _vb(plan, size, h=None):
    """The block for a part of this size; h (the part's height) picks between blocks of one size."""
    c = [v for v in plan["vblocks"] if any(abs(z - size) < 2e-3 for z in v["sizes"])] or [min(plan["vblocks"], key=lambda v: abs(v["size"] - size))]
    if h is None: return max(c, key=lambda v: v["hb"])
    ok = [v for v in c if v["hb"] < h - 0.05] or c
    return max(ok, key=lambda v: v["hb"])




def _join(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def steps(plan, design):
    sh = plan["shop"]; T = plan["board"]["thickness"]; cut = plan["slice_cut"]; kind = plan["info"]["kind"]
    logs = plan["logs"]; rows = plan["rows"]; skim = sh["true_skim"]; byid = {lg["id"]: lg for lg in logs}
    sk = f"{skim:.2f}\""
    S = []
    woods = ", ".join(w["name"] for w in plan["woods"])
    S.append({"title": "Buy and acclimate the lumber", "figs": [], "see": ["materials"],
              "text": [f"Buy the boards in the material list ({woods}) and let them sit in the shop for a week, stickered.",
                       "Pick straight-grained stock, quartersawn or rift where you can: it moves less and the end grain shows tight, even rings."]})

    # ---- jigs first: the bars are trued in them
    sliced = [lg for lg in logs if lg["crosscut"]]
    rowh = max(r["height"] for r in rows); rowl = max(r["length"] for r in rows)
    jig = []
    tl = sorted({round(bt["tilt"], 1) for bt in plan["bar_types"] if bt.get("tilt") and bt.get("setup") in ("para", "trap", "flip")})
    if tl:
        Ls = math.ceil(max(bl["blank_length"] for b in plan["bars"] for bl in b["lengths"]) + 8)
        jig += [f"Rip sled, for every bevelled bar. It is the sliding rip jig with toggle clamps from the best practices guide. Start with a base of {short(sh['sled_base'])} plywood about {Ls}\" x 16\", one long edge straight to run against the rip fence. "
                "Glue and screw a bridge of 3/4\" x 4\" hardwood, standing on edge, across each end. Tilt the blade to " + " or ".join(f"{t:g}" for t in tl) + " degrees, raise it fully, set the rip fence 9\" from it and push the sled through: "
                "the blade saws the base into two decks and notches both bridges, which are tall enough to stay whole above the cut and hold the decks together."
                + (" Make one sled for each tilt." if len(tl) > 1 else ""),
                "The 9\" deck beside the rip fence is the fence deck. Screw a straight locating fence, 3/4\" x 1-1/2\", flat on it and parallel to the cut, through slotted holes so it can be reset for each bar shape, "
                "and mount three toggle clamps behind it with their pads reaching over it. The pads close on a caul, a straight strip about 1/2\" x 1\" laid along the top of the work, so the pressure is spread and no pad is near the blade. "
                "The other deck is the landing deck. For triangle bars a stop strip of 1/4\" hardboard is screwed to it parallel to the cut. Leave the rip fence where it is for the whole run; every setting is made on the sled."]
    if kind == "tri":
        vb = plan["vblocks"]; longest = max(lg["length"] for lg in logs) + sh["glue_extra"]
        thin = [v for v in vb if v["base"] < 0.5]; tallest = max(v["tall"] + v["base"] for v in vb)
        jig += ["V blocks hold every three-cornered part, for gluing and for truing. The sides of a block stop 3/16\" under the top of the part: high enough to bear on nearly the whole part, "
                "low enough that the top stands proud for the caul or the sander. A V has no size except the height of its sides, so the blocks are named by that. Make "
                + "; ".join(f"a {v['name']} ({v['mat']}; each side piece about {short(_up(v['hb'] / S3 + 1.5, 0.25))} wide), for {_join(v['uses'])}" for v in vb) + ".",
                "To make one: rip one edge of each side piece at 30 degrees from vertical, so the cut face leans back at 60 degrees. Glue and screw one side piece to a flat base ("
                + ("3/4\" MDF" if not thin else "3/4\" MDF, but 1/4\" hardboard for the " + _join(v["name"] for v in thin) + ", to keep the stack low under the sander") + "). "
                "Stand a 60 degree drafting triangle on its point against that face (or dry-fit three test bars) and slide the second side piece up until its sharp lower edge meets the first. "
                "Fix this second side with screws through slotted holes, so it can be slackened: for gluing it is left loose and a clamp across the block closes it on the parts; "
                "for truing it is screwed tight against the drafting triangle. The two faces form a 60 degree V with no gap at the bottom.",
                f"Under the drum sander the tallest block and log stand {short(_up(tallest, 0.125))} high: check your sander opens that far before starting. If it does not, true those logs in the block with a jack plane.",
                f"Make each block 2\" longer than the longest part it holds (the longest log is {short(longest)}). Line the V with packing tape so glue lets go, "
                "screw a stop across one end so the drum sander cannot push the part out, and stand the block on two battens when gluing so clamp jaws reach under the base. "
                "A second block of the largest size lets you glue one log while another cures."]
        jig += [f"Row jig: a flat melamine or waxed MDF base about {math.ceil(rowl + 6)}\" x 9\". Screw one straight fence along it and a cleat parallel to it about {short(_up(rowh + 2.25, 0.25))} away. "
                "The second fence is loose and sawn into short blocks, one for every slice that has its base on that side and one for the end block that sits on that side, each with its own wedge between it and the cleat. "
                "Driving or easing one wedge moves one slice without disturbing the others. Set the blocks to the slices themselves, never to a number.",
                f"Row truing carrier: a flat board with two straight, square rails screwed down {short(cut)} apart (a slice thick), about {short(max(0.75, _up(rowh - 0.5, 0.25)))} high. "
                "A glued row stands on edge between the rails with its top edge proud, so the drum sander can skim it.",
                f"Crosscut sled with a stop block and a 1\" spacer. Its base must be {short(sh['sled_base'])} or thinner: the tallest log stands {short(max(l['trued'] * S3 / 2 for l in sliced))} on it and the blade, fully raised, clears {short(sh['max_cut_height'])}. "
                "Raise the blade and check it clears the top of the log before the first cut. For these three-cornered logs add a cradle: two strips with one edge ripped at 30 degrees (offcuts from the V blocks). "
                "Screw one to the sled base against the sled fence, sloping face toward the log; the log lies on one face on the sled base with a sloping face against that strip, "
                "and the second strip is clamped to the sled base against its other sloping face. Both strips stop 1/4\" short of the blade's path, so the slice comes off free of the cradle. "
                "The log is then held on all three faces (drawing at the crosscut step)."]
    elif kind == "blocks":
        hq = min(min(lg["w"], lg["h"]) for lg in logs if lg["shape"] == "quarter")
        jig += ["Band cradle: a flat base of 3/4\" MDF with packing tape on it, and a stop strip screwed along one side whose inner edge is ripped at 45 degrees so it leans over the work. "
                "The diamond bar's free bevel tucks under that edge. A straight loose caul on the other side takes the clamps, and a taped caul on top keeps the band flat (drawing on sheet 04).",
                f"Corner cauls: two L-shaped cauls, each two strips of 3/4\" plywood glued at exactly 90 degrees with inside legs {short(_up(hq - 0.375, 0.125))} wide, inside faces taped, as long as the logs. "
                "The legs are narrower than the log so the two cauls never touch each other before the log is tight.",
                f"Row jig: a flat melamine or waxed MDF base about {math.ceil(rowl + 6)}\" x 9\" with one straight fence and an end stop square to it. "
                "A loose second fence is pushed up to the slices and held by wedges against a cleat.",
                f"Row truing carrier: a flat board with two straight, square rails screwed down {short(cut)} apart (a slice thick), about {short(max(0.75, _up(rowh - 0.5, 0.25)))} high. "
                "A glued row stands on edge between the rails with its top edge proud."
                + (f" Make a second, low carrier the same way with rails {short(max(0.375, _up(min(r['height'] for r in rows) - 0.5, 0.125)))} high for the two border rows." if any(lg["shape"] == "border" for lg in logs) else ""),
                "Crosscut sled with a hold-down clamp, a stop block and a 1\" spacer. Check it cuts square in both directions."]
    else:
        jig += ["Flat cauls: four straight 2x2s with packing tape on one face, as long as the panels are wide.",
                "Crosscut sled with a hold-down clamp, a stop block and a 1\" spacer. Check it cuts square in both directions."]
    S.append({"title": "Make the jigs", "text": jig, "figs": (["ripsled"] if tl else []) + (["jigs"] if kind == "tri" else []), "see": []})

    thick = sorted({round(b["stock"], 4) for b in plan["bars"]})
    nsp = sum(b["total_spares"] for b in plan["bars"]); nb = sum(b["total_bars"] for b in plan["bars"])
    tx = [f"Joint one face and one edge of every blank, then plane to thickness: {', '.join(dim(t) for t in thick)} "
          f"(material list, sheet 02). Set the planer with calipers, not a tape, and plane every blank of one thickness in the same session without moving the planer between them.",
          "Crosscut the blanks to the lengths in the cut list. Then rip and true each bar shape as set out on sheet 03, which draws the saw and the rip sled from the front for every bevelled bar. "
          "Bars are ripped a little over and then machined to size, so the saw only has to be close.",
          "Test each setup on scrap first: rip three short bars, true them, and dry-fit them" + (" in their V block" if kind == "tri" else " against a square") + ". "
          "Half a degree of bevel error shows as a gap you can slip paper into; fix the tilt before cutting good wood.",
          f"The cut list has {nb} bars plus {nsp} spares (one in ten, and at least one of every bar in every wood). Rip every bar of a shape in one run, spares included, "
          f"then check a handful with calipers: all within {short(1 / 64)}."]
    S.append({"title": "Mill the blanks and rip the bars", "text": tx, "figs": [], "see": ["bars"],
              "dont": "rip a bevel with the work loose on the saw table, or with a bar between the tilted blade and the fence. Every bevel is cut with the work clamped to the rip sled. "
                      f"Stop when a triangle blank is narrower than {short(sh['blank_remainder'])}; that last strip is waste."})

    levels = sorted({lg["level"] for lg in logs})
    GL = "Spread a thin, even coat of Titebond III with a small roller on one face of each joint. Put painter's tape on the outside faces beside the joints so squeeze-out lifts off."
    END = "When the glue has cured, square both ends on the crosscut sled, taking only what cleans them."
    for lv in levels:
        here = [lg for lg in logs if lg["level"] == lv]
        main = next((lg for lg in here if lg["shape"] != "border"), here[0])
        what = main["what"]
        if sum(1 for l2 in levels if next(l for l in logs if l["level"] == l2)["what"] == what) > 1: what = f'{short(main["w"])} {what}'
        tx = []
        for lg in here:
            sl = f", for {lg['slices']} slices plus {lg['spares']} spare" if lg["crosscut"] else ""
            if len(lg["stages"]) == 1 and len(lg["stages"][0]["parts"]) == 1:
                tx.append(f"{lg['name']} is one solid bar (bar {lg['stages'][0]['parts'][0]['bar']}): nothing to glue. Make {_made(lg)}{sl}, and true it with the other logs.")
            elif len(lg["stages"]) == 1:
                tx.append(f"{lg['name']}: glue {_parts_text(plan, lg['stages'][0])} as drawn on sheet 04"
                          + (f", in the {_vb(plan, lg['w'], lg['h'])['name']}" if lg["kind"] == "tri" else "") + f". Make {_made(lg)}{sl}.")
            else:
                tx.append(f"{lg['name']}: make {_made(lg)}{sl}, in {len(lg['stages'])} glue-ups. "
                          + " ".join(f"Glue-up {i + 1}: {_parts_text(plan, st)}" + (f" in the {_vb(plan, st['vsize'], st['vsize'] * S3 / 2)['name']}" if lg["kind"] == "tri" else "")
                                     + (", stacked on glue-up " + str(i) if i else "") + "." for i, st in enumerate(lg["stages"])))
        dont = None
        if main["kind"] == "tri":
            sub = lv > levels[0]
            tx += [("Dry-fit first, with no glue: set the small logs in the block in the drawn order. " if sub else "Dry-fit first, with no glue: stack the bars in the block in the drawn order. ")
                   + "The top must come out flat and level with nothing rocking, and the corners must meet at a point at both ends."]
            if sub:
                tx.append("Each small log has a marked end and a reference face (pencilled when it was made). Put every one in with its marked end toward you and turn it until its reference face "
                          "sits where the short heavy line is drawn on sheet 04. A letter with a prime (B′) goes in the other way round, marked end away from you.")
            tx += [GL + " Stack the parts in the block with its second side slack, lay a taped caul stick on the flat top (a little narrower than the top), and clamp down through the caul to the underside of the base every 4 to 5 inches, snug rather than hard. "
                   "Then put a clamp across the block every 8 inches or so to close the loose side on the parts. The sides push the parts together while the caul pushes them down.",
                   "Check both ends before the glue grabs: corners meeting at a point, nothing slid along its length. Tap a part to line it up.",
                   "After an hour take the log out and scrape the squeeze-out while it is rubbery. Leave it overnight."]
            if any(len(lg["stages"]) > 1 for lg in here):
                tx.append("Where a log takes two glue-ups, the first is made in its own smaller V block. Once it has cured, true its flat top there with one light pass, "
                          "then dry-stack all the remaining bars on it in the full-size block. That pass makes the first glue-up a few thousandths low, so the upper bars may sit a hair wide and hold the joint under them open: "
                          "if a feeler shows a gap there, take one sanding stroke off the inner faces of the upper bars and try again. Glue only when the stack closes everywhere.")
            tx.append("Mark every log as it comes out: look at the end that matches the sheet 04 drawing, and on that end grain pencil the log letter and a line along the top face (the face under the caul). "
                      "That end is the marked end and that face is the reference face. " + END.replace("both ends", "both ends (re-mark the end afterwards)"))
            dont = "put more than four parts in one glue-up or skip the dry fit. Parts slide on wet glue; a stack that rocks dry will cure crooked."
        elif main["shape"] == "band":
            tx += ["Dry-fit in the band cradle: the diamond bar lies on a sawn face with its free bevel tucked under the 45 degree stop; the triangle bar sits beside it on a sawn face, "
                   "its planed base against the diamond's other bevel. The two planed faces are the joint.",
                   GL + " Push the triangle in with the loose caul and clamps across the cradle every 4 to 5 inches: the push wedges the triangle under the diamond's bevel and closes the joint. "
                   "Clamp a taped caul down on top so neither bar can ride up.",
                   "Scrape the squeeze-out when rubbery and leave overnight. Pencil a mark on one end of every band; every later log carries that marked end, and it always faces you. " + END]
        elif main["shape"] == "quarter":
            tx += ["Dry-fit in the corner cauls: the two bands lie in the lower caul, one against each leg, with their star bars meeting on the diagonal at the caul's corner; the square bar fills the open corner on top.",
                   "Look at the end against sheet 04: the two star woods are side by side at the corner. A band with a prime (B′) is turned end for end.",
                   GL + " Seat the parts in the lower caul, close the second caul over the square bar, and clamp both ways every 4 to 5 inches. "
                   "Sight both ends: the diagonal joint must run exactly corner to corner.",
                   "Scrape when rubbery; leave overnight. " + END]
        elif main["shape"] == "half":
            tx += ["Glue two quarter logs side by side so their star corners touch and the two faces in the joint are of different star woods (sheet 04). "
                   "Lay both with a trued star-corner face down on a flat taped surface, star corners touching at the joint; those trued faces are the register, not the outer faces. "
                   "Clamp across the joint between flat taped cauls every 4 to 5 inches.",
                   "Line up the star points at the joint at both ends before the clamps go tight.",
                   "Scrape when rubbery; leave overnight. " + END]
        elif main["shape"] == "block":
            tx += ["Glue two half logs with their star centres together. Keep the marked ends of both halves toward you and roll the second half half a turn about its length, so the star woods alternate all the way round; do not turn it end for end. Eight star points must meet at the centre: "
                   "line them up at both ends, clamp lightly, look again, then tighten.",
                   "Scrape when rubbery; leave overnight. " + END]
            dont = "glue all four quarter logs at once. Two joints at right angles under clamps slide; halves first, then the block."
        else:
            tx += ["Square-edged strips are the one case where many parts can be glued at once: lay the strips in order on taped cauls, glue the edges, "
                   "clamp across the panel every 6 inches with cauls above and below to keep it flat.",
                   "Scrape when rubbery; leave overnight."]
        S.append({"title": f"Glue the {what}s", "text": tx, "figs": [f"log_{lg['id']}" for lg in here if not (len(lg['stages']) == 1 and len(lg['stages'][0]['parts']) == 1)][:3],
                  "see": ["logs"], "glue": True, **({"dont": dont} if dont else {})})

        # true them
        if main["kind"] == "tri":
            g_, t_ = main["glued"], main["trued"]; vbk = _vb(plan, main["w"], main["h"])
            tx = [f"Every face of a log is a glue face later, so every face gets machined. Scribble pencil across the top face, set the log in the {vbk['name']} (second side screwed tight) and run it through the "
                  f"drum sander with 80 or 100 grit until the scribble just disappears; turn the log and do the other two faces. "
                  f"No drum sander: clamp the block in the vise and plane the top face with a jack plane, checking with a straightedge.",
                  f"Work in rounds: every log through with its first face up at one drum setting, then every log with its second face up, then the third. "
                  f"The log sits a hair lower once a sanded face is against the block, so lower the drum by that hair at the start of each round until it just takes the pencil off; what matters is that every log gets the same setting in each round. "
                  f"That takes about {sk} off a face: the logs glue up {dim(g_)} on a side and finish about {dim(t_)}. "
                  f"The exact figure does not matter; that all the logs match within a few thousandths does. Sizes from here on are these finished sizes.",
                  "Check each log: the 60 degree triangle fits every corner, a straightedge shows no light along any face, and calipers read the same at both ends."]
        elif main["shape"] == "band":
            tx = [f"Plane both broad faces of each band, equal cuts from each face, all bands at one planer setting, down to {dim(main['trued'][1])} thick. "
                  "The sawn faces of the bars carried the allowance for this. A band has one bevelled edge that ends in a feather. Nest the bands in pairs: lay one wide face down and roll its partner over, wide face up, the same end leading, "
                  "so the two bevels lap and the pair is a rectangle. Tape the pair down to a flat carrier board; it goes through as a rectangle and no thin edge leads into the knives. Turn the pair over as one to plane the other faces.",
                  f"Then bring every band to width at one saw setting: blade square, the band wide face down, its bevelled edge against an auxiliary fence that sits tight on the table so the feather cannot slip under it, "
                  f"and rip the square edge (the triangle bar's outer face) so the wide face measures {dim(main['trued'][0] + 1 / 64)}. Finish with one jointer pass on that sawn edge, every band at the same jointer setting, to {dim(main['trued'][0])}. "
                  "This width decides whether the corner cauls close the diagonal joints of the star, so check a few bands with calipers: all within a few thousandths."]
        elif main["shape"] == "quarter":
            tx = [f"True the two inner faces, the ones that lay in the lower caul and meet at the star corner: one light jointer pass each, about {sk}, keeping them square to each other. "
                  f"Leave the two outer faces alone until the block is whole. The quarter logs come out about {dim(main['trued'][0])} square."]
        elif main["shape"] == "half":
            tx = [f"True the one long face that carries both star corners (the next glue face): a light jointer pass, about {sk}. Check it is flat and square to the ends. "
                  f"Halves are then about {dim(main['trued'][0])} x {dim(main['trued'][1])}."]
        elif main["shape"] == "block":
            tw = main["trued"]
            tx = [f"Joint one face of each block log, joint an adjacent face square to it, then plane the other two faces parallel, every log through the planer at one setting. "
                  f"Take as little as cleans each face, about {sk}. The block logs finish about {dim(tw[0])} across the last glue line and {dim(tw[1])} along it; that they all match within a few thousandths matters more than the figure. "
                  f"Chalk one of the two faces that show the last glue line running down their middle (they are the faces {dim(tw[0])} wide). At the saw that chalked face goes down on the sled and it becomes a long edge of the row, so every slice is {dim(tw[0])} along the row.",
                  "Check each log is square at both ends."]
            if any(lg["shape"] == "border" for lg in here):
                bl = next(lg for lg in here if lg["shape"] == "border")
                tx.append(f"Plane the border bar ({bl['name']}) to the same width as the block logs at the same planer setting ({dim(tw[1])}), so its slices line up with theirs.")
        elif main["kind"] == "rect":
            tx = [f"Joint one face of each log, joint an adjacent face square to it, then plane the other two faces parallel: every log through the planer at one setting, about {sk} a face."]
        else:
            tx = ["Plane both faces of each panel clean and parallel, all panels at one planer setting. These faces are the glue faces of the board. "
                  f"Bring the panels to {dim(main['h'])} thick."]
        S.append({"title": f"True the {what}s", "text": tx, "figs": ["true"] if main["kind"] == "tri" and lv == levels[0] else [], "see": [],
                  "dont": "leave a glue face as it came out of the clamps. Dried glue and a part standing a few thousandths proud hold the next joint open."})

    # crosscut
    ns = sum(lg["slices"] + lg["spares"] for lg in sliced)
    lay = ("Lay the log in the sled cradle on its reference face, marked end away from the stop. Push the second strip hard against the log and clamp it to the sled base with two clamps, both on the side of the blade away from the stop: the log is pinched between the two strips, and that is what holds it for every cut. To move the log on, slacken one clamp, slide the log, tighten." if kind == "tri"
           else "Lay the log on its chalked face against the sled fence, marked end away from the stop, and clamp it down." if kind == "blocks"
           else "Lay the panel against the sled fence and clamp it down.")
    tx = [f"Square the unmarked end of each log first. {lay}" if kind != "panel" else f"Square one end of each panel first. {lay}",
          f"Set the stop block {dim(cut + 1.0)} from the blade and use the 1\" spacer: slide the log up to the spacer, clamp the log, take the spacer away, then cut. "
          f"The slice comes off {dim(cut)} thick (finished {short(T)} plus {short(sh['flatten_allowance'])} to flatten) with an inch of room beside it, so it cannot bind between blade and stop.",
          f"Cut {ns} slices in all" + ": " + ", ".join(f"{lg['slices']} + {lg['spares']} spare from log {lg['id']}" for lg in sliced) + ". "
          + ("As each slice comes off, turn up the face that was toward the blade and pencil a short line on it along the edge that lay on the sled. "
             "That line is the mark sheet 05 draws inside every slice. Stack the slices by letter." if kind != "panel" else "Stack them in order."),
          "Hold the slice down on the sled base with a push stick as the blade comes through, hand well clear. Push the sled on until the slice is past the blade, "
          "stop, and lift the slice away before pulling the sled back.",
          f"The last {short(sh['hold_end'])} of each log is the part the clamp holds. It is never sliced: stop there."]
    S.append({"title": "Crosscut the slices", "text": tx, "figs": ["cut_setup", "asm_cut"], "see": [],
              "dont": "cut a slice against a fixed stop with no spacer, or slice into the last 2 inches of a log. A trapped slice is thrown; a short stub cannot be held."})

    # rows
    nrow = len(rows); per = max(len(r["pucks"]) for r in rows)
    if kind == "panel":
        tx = [f"The slices are the rows: {nrow} of them. Lay them out end grain up in the order on sheet 05, turning the ones marked with a prime end for end."]
    else:
        tx = [f"Lay out the whole board dry on a flat surface from sheet 05: {nrow} rows of up to {per} slices. Each slice goes pencil line up, with the line on the edge where the drawing shows it. "
              "A letter with a prime (A′) is turned over, line underneath; the drawing still shows which edge the line is on. Look at the whole pattern before any glue goes on.",
              "The glue faces here are the trued sides of the logs: long grain. Roll a thin coat on one face of each joint and keep glue off the end grain."]
        if kind == "tri":
            tx += ["Cut a spare slice in half on the band saw, from one corner to the middle of the opposite side. The two halves are the end blocks: they turn the slanted ends of a row into square faces for the clamps.",
                   "Glue the slices in pairs first, in the row jig: slices 1 and 2 of the row, 3 and 4, and so on (an odd last slice waits). Two slices make a diamond. "
                   "Set the pair between the two end blocks. One end block has its short edge on the fixed fence; the other has it on the loose side and gets a loose block and wedge behind it, like a slice, so the clamp cannot push it up the slope. "
                   "Bring up the loose blocks, wedge them lightly, and put one clamp along the jig across the end blocks. Stick packing tape on the end blocks' slanted faces so they do not get glued in. "
                   "Lay a taped caul on top with a weight. Thirty minutes a pair.",
                   "Then glue pairs into fours, and fours into the row, the same way: end blocks, wedged fence, one or two clamps along the row, caul and weight on top. "
                   "Before tightening, tap each slice down flat and check its points meet its neighbours'; ease or drive the wedge beside any slice that needs it.",
                   f"Each row comes out about {dim(rows[0]['height'] + 2 * skim)} wide before truing."]
        else:
            tx += ["Glue the slices of each row against the fixed fence of the row jig, two at a time, then the pairs to each other, clamping along the row with the loose fence wedged and a caul on top. "
                   "Line up the star points across each joint before tightening.",
                   "The two border rows are slices of the border bar laid end to end; glue them the same way." if any(lg["shape"] == "border" for lg in logs) else
                   "Rows must come out straight: sight along the fence before the glue sets."]
    S.append({"title": "Glue the slices into rows", "text": tx, "figs": ["row"], "see": ["layout"], "glue": True,
              "dont": "trust a row that rocks in the jig. A slice that sits proud of the fence line will hold the next row off; take it out and find out why."})
    brd = any(lg["shape"] == "border" for lg in logs)
    if kind != "panel":
        tx = ["Scrape the glue from each row. Its two long edges are the glue faces for the board, and every one of them gets machined.",
              f"Stand the row on edge in the truing carrier, scribble pencil along the top edge, and pass it under the drum sander until the scribble just goes, about {sk}. "
              f"Turn the row over and do the other edge. Every row gets the same passes at the same setting, so all " + ("star " if brd else "") + f"rows finish the same width, about {dim(max(r['height'] for r in rows))}"
              + (f". The two border rows are slices glued end to end as well, so true their edges the same way in the low carrier; they finish about {dim(min(r['height'] for r in rows))} wide." if brd else "."),
              "No drum sander: glue 80 grit paper to a flat board, hold the row against a square block, and take the same number of even strokes on every edge. "
              "Keep rows off the jointer and out of the planer: the knives hit the fibres end-on at the trailing edge and break it out."]
        S.append({"title": "True the rows", "text": tx, "figs": [], "see": []})

    tx = [f"Dry-fit the {nrow} rows in order" + (". Slide each row along its neighbour until the corners of the slices meet corner to corner along the whole joint, then draw a pencil line across every joint so the rows go back in register under glue."
                                                if kind != "panel" else " and line up the pattern, then draw a pencil line across every joint."),
          "Glue two or three rows at a time, then glue those sections together. Clamp across the rows every 4 to 5 inches with moderate pressure, "
          "with taped cauls clamped across the top and bottom near each end, inside the ragged ends, to keep the rows in one plane.",
          "The faces being glued are long grain (the sides of the logs): one thin rolled coat on one face of each joint. "
          "The pencil lines hold the register: check them after the clamps are on and tap a row back if it has crept.",
          "Scrape the squeeze-out when rubbery. Leave the board in clamps overnight and out of clamps a day before flattening."]
    S.append({"title": "Glue the rows into the board", "text": tx, "figs": ["board"], "see": ["layout"], "glue": True,
              "dont": "glue every row at once. More than three joints open at a time creep out of plane and out of register before the clamps are on."})

    bd = plan["board"]; W, L = bd["field"]; m = bd["margins"]; zig = bd["zig"]; fr_ = bd.get("frame")
    def cutline(i, name):
        return (f"the {name} cut {short(m[i])} inside the deepest notch of the ragged {name} edge" if zig[i] else f"the {name} cut {short(m[i])} in from the {name} edge")
    tx = ["Flatten first, trim second. Flatten both faces with a drum sander (60 or 80 grit, light passes) or a router sled; "
          f"the slices were cut {short(sh['flatten_allowance'])} thick of finished for this. "
          + (f"Stop as soon as both faces are clean and the board is an even thickness; leave it over {short(T)}, because it is flattened once more with its frame on." if fr_ else f"Stop at {short(T)}."),
          f"Then trim to {dim(W)} x {dim(L)} with a track saw or on a crosscut sled. The trim lines are centred on the pattern (sheet 05 shows them against the slices): "
          f"make {cutline(0, 'left')} and {cutline(2, 'bottom')}, square to each other, then cut the right and top edges parallel to them at the finished size. "
          f"That leaves about {short(m[1])} of waste on the right and {short(m[3])} at the top. "
          "Tape the cut line and back the exit edge with scrap so the end grain does not chip.",
          ] + ([] if fr_ else ["Sand both faces 80, 120, 180; wipe with a damp cloth to raise the grain, let it dry, then sand 220."])
    S.append({"title": "Flatten, then trim", "text": tx, "figs": ["trim"], "see": [],
              "dont": "run the board through a thickness planer. End grain breaks out at the trailing edge and the planer can throw pieces."})
    if fr_:
        cutl = plan["slice_cut"]; rg = fr_["rings"]; two = len(rg) > 1
        tx = [(f"Round the field goes a {short(rg[0]['width'])} line of {rg[0]['species']} and then a {short(rg[1]['width'])} frame of {rg[1]['species']}. " if two else f"The frame is {rg[0]['species']}. ")
              + "All of it stands on end like everything else, so it swells and shrinks with the field. A long-grain frame would split the board."]
        for r in rg:
            n1, n2 = r["per_side"]; nm = "line" if r["role"] == "liner" else "frame"
            tx.append(f"The {nm}: plane the {r['species']} board to {dim(r['width'])} thick with both edges jointed parallel. Crosscut {r['blocks']} blocks from it on the sled, each {short(cutl)} long, "
                      "with the same spacer stop and setting used for the slices; the board lies flat on the sled under a hold-down, and the last 2 inches are not cut. "
                      f"Stand the blocks on end: each is {short(r['width'])} x {short(r['block_len'])} seen from above. Glue them edge to edge into four strips against the fixed fence of the row jig, "
                      f"one clamp along each strip: two strips of {n1} blocks for the long sides (at least {short(r['long'] + 0.5)} long) and two of {n2} for the ends (at least {short(r['short'] + 0.5)}). "
                      "These joints are long grain to long grain, and in one wood they disappear.")
        tx += ["Scrape each strip and pass the face that meets the board under the drum sander once, so it is flat across the block joints.",
               ("Work one ring at a time, the line first. " if two else "")
               + "Glue the two long strips to the long edges, overhanging both ends, with clamps across the board every 4 to 5 inches and a taped caul over each joint to keep the strips level with the field. "
               "When the glue has set, saw the overhanging ends flush with the short edges on the sled, taking the strip ends and no more than a shaving of the field.",
               "Glue the two end strips across the ends the same way, clamping along the length of the board, then saw their overhang flush with the long sides."
               + (" Then do the same with the frame strips round the line." if two else ""),
               f"Flatten both faces again with light passes until frame and field are in one plane, and stop at {short(T)}. The board is now {dim(bd['width'])} x {dim(bd['length'])}.",
               "Sand both faces 80, 120, 180; wipe with a damp cloth to raise the grain, let it dry, then sand 220."]
        S.append({"title": "Add the frame", "text": tx, "figs": ["frame"], "see": [], "glue": True,
                  "dont": "frame the board with strips whose grain runs along the edge. The field moves across its width and length; long-grain strips do not, and the board cracks."})
    opts = plan["options"]
    tx = [f"Ease every edge with a {opts.get('edge', '1/8 inch chamfer')} and break the corners: sharp end-grain edges chip."]
    if opts.get("feet"): tx.append("Add four rubber feet with stainless screws, inset 1\" from the corners, so the board dries evenly underneath.")
    if opts.get("juice_groove"): tx.append("Rout a juice groove with a 1/2\" core-box bit, 3/4\" from the edge, in two light passes.")
    if opts.get("handles"): tx.append("Cut a finger grip in each end on the router table with a 3/4\" core-box bit: 1/4\" deep, 4\" long, centred on the end and on the board's thickness. "
                                      "Stand the board on its end against a tall auxiliary fence, a backer board clamped behind it, with start and stop blocks clamped to the fence, and take three shallow passes, raising the bit each time. "
                                      "The lips left above and below the groove are 3/8\" thick.")
    tx.append("Flood with food-grade mineral oil until it stops soaking in (several coats over two days), then buff on a board butter of mineral oil and beeswax. Re-oil monthly.")
    S.append({"title": "Edges and finish", "text": tx, "figs": [], "see": []})
    seen = set()
    for st in S:            # a warning repeated word for word is said once
        if st.get("dont") in seen: st.pop("dont")
        elif st.get("dont"): seen.add(st["dont"])
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
