#!/usr/bin/env python3
"""End-grain cutting board: design.json -> checked build plan.

  python3 scripts/cbplan.py design.json out/ [--photo render.jpg]

Writes into out/:
  plan.json        everything computed: face, bars, units, logs, stock, steps, checks
  plan.html        the shop plan (self-contained: inline SVG diagrams, embedded photo if given)
  svg/*.svg        each diagram on its own (face, layout, bars, units, logs)
  board.obj/.mtl   the finished board in meters, a material per species (for plan-to-photo)
  guide.png        a colour-coded perspective of the board (the image Nano Banana photographs)
  spec.md          the board described in words for plan-to-photo's nano_banana.py

The design is checked before anything is drawn: bars must tile the board with no gaps or overlaps,
every bar must be a convex shape a table saw can rip, slices and units are matched by shape so one
log makes every identical slice. Exit status 1 if any check fails.
"""
import argparse, base64, html, json, math, os, sys
from collections import OrderedDict, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patterns, species as SP

DEFAULT_SHOP = {"kerf": 0.125, "max_log_length": 24.0, "flatten_allowance": 0.125, "end_trim": 0.75,
                "stock_width": 5.5, "spare_slices": 1, "min_slice_glue": 2}


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
    return f'{x:.3f}" (≈{frac(x)}")'


def short(x):
    return f'{frac(x)}"'


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
    """How to rip this cross-section on a table saw. Returns kind, label, stock thickness, the width each
    bar uses across the blank, blade tilt, steps and warnings."""
    kerf = shop["kerf"]; n = len(p); warn = []
    eq = lambda a, b, t=1e-3: abs(a - b) < t
    if n == 4 and all(eq(a, 90, 0.05) for a in A):
        w, h = max(L[0], L[1]), min(L[0], L[1])
        sq = eq(w, h)
        return {"kind": "square" if sq else "rect", "label": f"{short(w)} square" if sq else f"{short(h)} x {short(w)} rectangle",
                "dims": {"width": w, "thick": h}, "stock": h, "per_bar": w + kerf, "tilt": 0,
                "steps": [f"Mill the blank to {dim(h)} thick.", f"Rip bars {dim(w)} wide, blade square to the table."],
                "warn": warn}
    if n == 4 and eq(L[0], L[2]) and eq(L[1], L[3]) and eq(A[0], A[2], 0.05):
        th = min(A); pside, qside = (L[0], L[1])
        # lay the longer side flat so the blank is thinner and the bar more stable
        if qside > pside: pside, qside = qside, pside
        t = qside * math.sin(math.radians(th)); tilt = 90 - th
        kind = "rhombus" if eq(pside, qside) else "parallelogram"
        if tilt > 45.01:
            warn.append(f"Needs a {tilt:.1f} degree blade tilt, past a table saw's 45: cut the bevels on a tilting sled or a "
                        "bandsaw with a jointer jig, or change the angle.")
        st = [f"Mill the blank to {dim(t)} thick (the height of the {th:.0f}-degree parallelogram).",
              f"Tilt the blade {tilt:.1f} degrees from vertical (set it with a digital angle gauge, not the saw's scale). "
              "Rip the first bevel to establish the edge and discard the strip.",
              f"Without changing the tilt, rip each bar off the same edge: {dim(pside)} from the blade at the table "
              "(a thin-rip jig against the blank's bevelled edge makes every bar identical). Each pass cuts the next "
              "bar's leading edge, so bars come off as parallelograms with no flipping.",
              f"Check the first bar: {th:.1f} and {180 - th:.1f} degree corners, every side {dim(qside)} on the slant"
              + ("" if kind == "rhombus" else f" and {dim(pside)} across the faces") + "."]
        return {"kind": kind, "label": f"{th:.0f}-degree {kind}, {short(pside)} side" + ("" if kind == "rhombus" else f" x {short(qside)}"),
                "dims": {"side": pside, "slant": qside, "angle": th, "thick": t}, "stock": t,
                "per_bar": pside + kerf / math.cos(math.radians(tilt)), "tilt": tilt, "steps": st, "warn": warn}
    if n == 3:
        for i in range(3):   # apex i: the two sides meeting there equal
            a_, b_ = L[i - 1], L[i]
            if eq(a_, b_):
                phi = A[i]; base = L[(i + 1) % 3]; H = a_ * math.cos(math.radians(phi / 2)); tilt = phi / 2
                kind = "equilateral triangle" if eq(phi, 60, 0.05) and eq(base, a_) else (
                    "right isosceles triangle" if eq(phi, 90, 0.05) else "isosceles triangle")
                if tilt > 45.01:
                    warn.append(f"Needs a {tilt:.1f} degree tilt; cut it on a sled.")
                st = [f"Mill the blank to {dim(H)} thick (the triangle's height).",
                      f"Tilt the blade {tilt:.1f} degrees and rip the first bevel; discard the strip.",
                      f"Flip the blank over (face for face) before every pass so the bevels alternate; each pass releases a "
                      f"triangle {dim(base)} across its base with the base on the table side of the cut.",
                      f"Check: equal sides {dim(a_)}, apex {phi:.1f} degrees."]
                return {"kind": kind, "label": f"{kind}, {short(base)} base", "dims": {"base": base, "leg": a_, "apex": phi, "thick": H},
                        "stock": H, "per_bar": base / 2 + kerf / math.cos(math.radians(tilt)), "tilt": tilt, "steps": st, "warn": warn}
    xs = [v[0] for v in p]; ys = [v[1] for v in p]
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    warn.append("Irregular cross-section: cut each face from a square blank with a sled or jig; make a test bar first.")
    return {"kind": "polygon", "label": f"{n}-sided bar", "dims": {"bbox": [bw, bh]}, "stock": min(bw, bh),
            "per_bar": max(bw, bh) + kerf, "tilt": None,
            "steps": [f"Rip a blank {dim(bw)} x {dim(bh)}.",
                      "Cut each other face at the corner angles shown (" + ", ".join(f"{a:.1f}" for a in A) + " degrees)."],
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
    cnt = np.zeros(X.shape, dtype=np.int16)
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
            m &= (bx - ax) * (sy - ay) - (by - ay) * (sx - ax) > 1e-9
        cnt[j0:j1, i0:i1] += m
    over = np.argwhere(cnt > 1)
    t0, s0, t1, s1 = trim
    inside = (X > t0 + step) & (X < t1 - step) & (Y > s0 + step) & (Y < s1 - step)
    gaps = np.argwhere(inside & (cnt == 0))
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
                f'height="{self.h:.0f}" font-family="Helvetica, Arial, sans-serif">{t}<rect width="100%" height="100%" fill="#fff"/>'
                + "".join(self.el) + "</svg>")


def bbox_of(polys):
    xs = [v[0] for p in polys for v in p]; ys = [v[1] for p in polys for v in p]
    return (min(xs), min(ys), max(xs), max(ys))


# ------------------------------------------------------------------------------------- main build
def build(design, out, photo=None):
    shop = dict(DEFAULT_SHOP, **design.get("shop", {}))
    board = design["board"]; T = float(board.get("thickness", 1.5))
    g = patterns.generate(design)
    polys = g["polygons"]; trim = [float(v) for v in g["trim"]]
    for p in polys: p["pts"] = [list(v) for v in ccw([tuple(v) for v in p["pts"]])]
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
          (f"{min(tans):.1f}% to {max(tans):.1f}%" if tans else "") + ("; common pairings like maple with padauk or "
          "purpleheart hold up, but acclimate every species together and keep the board oiled so it moves evenly" if spread > 4 else ""), "warn")
    unknown = [w["name"] for w in woods.values() if w["janka"] is None]
    check(not unknown, "Every species in the species table", ", ".join(unknown), "warn")

    # geometry
    bad = [i for i, p in enumerate(polys) if not convex(p["pts"])]
    check(not bad, "Every bar is convex (a saw can cut it)", f"{len(bad)} not convex" if bad else "")
    minside = min(min(math.dist(p["pts"][i - 1], p["pts"][i]) for i in range(len(p["pts"]))) for p in polys)
    step = max(0.01, min(0.04, minside / 8))
    no, op_, ng, gp = coverage(polys, trim, step)
    check(no == 0, "Bars do not overlap", f"overlap near {op_}" if no else "")
    check(ng == 0, "Bars cover the whole finished board (no gaps)", f"gap near {gp}" if ng else "")
    W, Lb = trim[2] - trim[0], trim[3] - trim[1]

    # face (clipped)
    face = []
    for i, p in enumerate(polys):
        c = clip_rect(p["pts"], trim)
        if c: face.append({"pts": c, "role": p["role"], "bar": i})

    # bar types
    bar_types = OrderedDict(); bar_of = []
    for p in polys:
        key, pp, L, A = shape_of(p["pts"])
        if key not in bar_types:
            bar_types[key] = {"id": None, "recipe": recipe(key, pp, L, A, shop), "pts": pp, "sides": L, "angles": A}
        bar_of.append(key)
    for n, (k, bt) in enumerate(bar_types.items()):
        bt["id"] = "ABCDEFGHJKLMNPQRSTUVWXYZ"[n]
        for w in bt["recipe"]["warn"]:
            check(False, f"Bar {bt['id']} can be cut", w)
    tilts = [bt["recipe"]["tilt"] for bt in bar_types.values() if bt["recipe"]["tilt"]]
    check(all(t <= 45.01 for t in tilts), "Every bevel is 45 degrees or less from vertical")

    # slices and their types
    slices = OrderedDict()
    for i, p in enumerate(polys): slices.setdefault(p["slice"], []).append(i)
    sm = Matcher(); slice_list = []
    for sid, idx in slices.items():
        items = [(polys[i]["role"], polys[i]["pts"]) for i in idx]
        t, gx = sm.add(items)
        bb = bbox_of([polys[i]["pts"] for i in idx])
        slice_list.append({"id": sid, "type": t, "xf": gx, "bars": idx, "bbox": bb})
    # number slices in glue order: bottom to top, then left to right
    order = sorted(range(len(slice_list)), key=lambda k: (round(slice_list[k]["bbox"][1], 2), slice_list[k]["bbox"][0]))
    for n, k in enumerate(order): slice_list[k]["n"] = n + 1
    rep_slice = {}
    for s in slice_list: rep_slice.setdefault(s["type"], s)

    # units: matched across the whole board
    um = Matcher(); unit_list = OrderedDict()
    for i, p in enumerate(polys):
        if p.get("unit"): unit_list.setdefault(p["unit"], []).append(i)
    unit_type_of = {}
    for uid, idx in unit_list.items():
        t, gx = um.add([(polys[i]["role"], polys[i]["pts"]) for i in idx])
        unit_type_of[uid] = (t, gx)

    # logs: one kind per slice type
    cut = T + shop["flatten_allowance"]; pitch = cut + shop["kerf"]
    logs = []
    LOGL = "LMNOPQRSTUVWXYZ" + "abcdefghijklmnopqrstuvwxyz"
    for t in range(len(sm.types)):
        n = sum(1 for s in slice_list if s["type"] == t)
        need = n + shop["spare_slices"]
        total = need * pitch + 2 * shop["end_trim"]
        k = max(1, math.ceil(total / shop["max_log_length"]))
        per = math.ceil(need / k)
        length = per * pitch + 2 * shop["end_trim"]
        rep = rep_slice[t]
        bars_in = [polys[i] for i in rep["bars"]]
        uids = list(OrderedDict.fromkeys(p["unit"] for p in bars_in if p.get("unit")))
        loose = [i for i in rep["bars"] if not polys[i].get("unit")]
        ff = flat_faces([p["pts"] for p in bars_in])
        logs.append({"type": t, "name": f"Log {LOGL[t]}", "slices": n, "spares": k * per - n, "count": k,
                     "slices_per_log": per, "length": length, "rep": rep["id"], "units": uids, "loose_bars": loose,
                     "bbox": rep["bbox"], "flat": ff})
    for s in slice_list: s["log"] = logs[s["type"]]["name"]

    # units needed: per unit type, pieces at each log length
    unit_types = []
    for t, items in enumerate(um.types):
        rep_uid = next(u for u, (tt, _) in unit_type_of.items() if tt == t)
        unit_types.append({"type": t, "name": f"Unit U{t + 1}", "rep": rep_uid, "bars": unit_list[rep_uid], "pieces": []})
    for lg in logs:
        cnt = defaultdict(int)
        for u in lg["units"]: cnt[unit_type_of[u][0]] += 1
        for t, c in cnt.items():
            unit_types[t]["pieces"].append({"count": c * lg["count"], "length": lg["length"], "log": lg["name"]})

    # bars needed: count x length per bar type and species
    need = defaultdict(lambda: defaultdict(int))  # (barkey, species) -> length -> count
    for lg in logs:
        for i in slices[lg["rep"]]:
            need[(bar_of[i], sp[polys[i]["role"]]["key"])][round(lg["length"], 3)] += lg["count"]
    bars_out = []
    for (key, wkey), byl in need.items():
        bt = bar_types[key]; rc = bt["recipe"]
        roles_here = sorted({p["role"] for i, p in enumerate(polys) if bar_of[i] == key and sp[p["role"]]["key"] == wkey})
        per_blank = max(1, int((shop["stock_width"] - 0.25) // rc["per_bar"]))
        blanks = []
        for ln, c in sorted(byl.items()):
            blanks.append({"bar_length": ln, "bars": c, "blanks": math.ceil(c / per_blank), "blank_length": math.ceil(ln + 1)})
        bars_out.append({"bar": bt["id"], "species": wkey, "roles": roles_here, "label": rc["label"],
                         "kind": rc["kind"], "stock": rc["stock"], "per_blank": per_blank, "lengths": blanks,
                         "total_bars": sum(byl.values()), "linear_in": sum(l * c for l, c in byl.items())})
    bars_out.sort(key=lambda b: (b["species"], b["bar"]))

    # stock / material list
    stock = OrderedDict()
    for b in bars_out:
        q = nominal(b["stock"])
        rough_t = (q or 16) / 4
        bf = sum(bl["blanks"] * rough_t * (shop["stock_width"] + 0.5) * bl["blank_length"] / 144 for bl in b["lengths"])
        st = stock.setdefault(b["species"], {"species": woods[b["species"]]["name"], "items": [], "bf": 0})
        st["items"].append({"bar": b["bar"], "mill_to": b["stock"], "rough": f"{q}/4" if q else "glue up",
                            "blanks": sum(bl["blanks"] for bl in b["lengths"]),
                            "blank": f'{short(b["stock"])} x {short(shop["stock_width"])} x ' + ", ".join(f'{bl["blank_length"]}"' for bl in b["lengths"])})
        st["bf"] += bf
        if not q: check(False, f"Bar {b['bar']} stock", f"{b['stock']:.2f}\" thick is more than 16/4; laminate blanks first")
    for st in stock.values():
        st["bf_buy"] = math.ceil(st["bf"] * 1.25 * 2) / 2   # 25% for defects and milling, to the half foot

    # final glue-up checks
    check(T >= 1.0, "Board at least 1\" thick (end grain under 1\" can split)", f"{T}\"")
    check(max(W, Lb) / T <= 18, "Board not too large for its thickness", f"{W:.1f} x {Lb:.1f} x {T}", "warn")
    for lg in logs:
        lw, lh = lg["bbox"][2] - lg["bbox"][0], lg["bbox"][3] - lg["bbox"][1]
        if not (lg["flat"]["bottom"] or lg["flat"]["top"]) or not (lg["flat"]["left"] or lg["flat"]["right"]):
            lg["carrier"] = True

    plan = {"name": design.get("name", design["pattern"]), "description": design.get("description", ""), "pattern": design["pattern"], "board": {
                "width": W, "length": Lb, "thickness": T, "trim": trim},
            "shop": shop, "species": {r: sp[r] for r in roles}, "woods": list(woods.values()),
            "notes": g.get("notes", []) + design.get("notes", []), "options": design.get("options", {}),
            "face": face, "polygons": polys, "bar_types": [dict(id=bt["id"], label=bt["recipe"]["label"], kind=bt["recipe"]["kind"],
                       dims=bt["recipe"]["dims"], tilt=bt["recipe"]["tilt"], steps=bt["recipe"]["steps"], pts=bt["pts"],
                       sides=bt["sides"], angles=bt["angles"]) for bt in bar_types.values()],
            "bars": bars_out, "units": unit_types, "logs": logs, "slices": slice_list, "stock": list(stock.values()),
            "checks": checks}
    plan["steps"] = steps(plan, design)
    os.makedirs(os.path.join(out, "svg"), exist_ok=True)
    svgs = diagrams(plan, unit_type_of, unit_list)
    for name, s in svgs.items():
        open(os.path.join(out, "svg", name + ".svg"), "w").write(s)
    write_obj(plan, out)
    write_spec(plan, design, out)
    try:
        import render_guide
        render_guide.render(plan, os.path.join(out, "guide.png"), **design.get("guide", {}))
    except ImportError as e:
        print("guide.png skipped:", e)
    open(os.path.join(out, "plan.html"), "w").write(page(plan, svgs, photo, os.path.join(out, "guide.png")))
    slim = {k: v for k, v in plan.items() if k not in ("polygons",)}
    json.dump(slim, open(os.path.join(out, "plan.json"), "w"), indent=1, default=str)
    return plan


# ------------------------------------------------------------------------------------- steps
def steps(plan, design):
    sh = plan["shop"]; T = plan["board"]["thickness"]; cut = T + sh["flatten_allowance"]
    S = []
    woods = ", ".join(w["name"] for w in plan["woods"])
    S.append({"title": "Buy and acclimate the lumber", "diagrams": [],
              "text": [f"Buy the boards in the material list ({woods}) and let them sit in the shop a week, stickered.",
                       "Pick straight-grained, quartersawn or rift stock for the bars where you can: it moves less and the end grain "
                       "shows tight, even rings."]})
    tx = [f"Joint and plane every blank flat and to its exact thickness (material list). Bars of one shape must come "
          "from blanks planed in the same session at the same setting, or they won't match."]
    for bt in plan["bar_types"]:
        tx.append(f"Bar {bt['id']} ({bt['label']}): " + " ".join(bt["steps"]))
    tx.append("Rip every bar of a shape in one session without touching the saw setup, and rip 10% spares. "
              "Dry-fit the first few bars into a unit or a short row before ripping the rest: half a degree of bevel "
              "error doubles at every joint and opens gaps across a row.")
    S.append({"title": "Rip the bars", "text": tx, "diagrams": ["bars"],
              "dont": "touch the blade tilt or the thin-rip jig partway through a shape. Bars from two setups never meet cleanly; rip every bar of a shape, plus spares, in one run."})
    if plan["units"]:
        tx = []
        for u in plan["units"]:
            pcs = ", ".join(f'{p["count"]} x {short(p["length"])} long (for {p["log"]})' for p in u["pieces"])
            tx.append(f"{u['name']}: glue {len(u['bars'])} bars as drawn; make {pcs}.")
        tx.append("Where a unit is needed at several lengths, glue it long and crosscut the pieces from it.")
        tx.append("Bevelled bars won't take bar clamps. Lay the bars face down edge to edge on packing tape in the drawn order, "
                  "glue the bevels, fold them up so the tape pulls the joints closed, and wrap with more tape or rubber "
                  "bands. Check each unit with the template from the diagram while the glue is wet.")
        tx.append("Let the glue (Titebond III, or II) cure overnight, then scrape the squeeze-out flush; "
                  "the units' outside faces are glue faces for the next step.")
        S.append({"title": "Glue the units", "text": tx, "diagrams": [f"unit{u['type'] + 1}" for u in plan["units"]]})
    tx = []
    for lg in plan["logs"]:
        what = (f"{len(lg['units'])} units" if lg["units"] else "") + (" and " if lg["units"] and lg["loose_bars"] else "") + \
               (f"{len(lg['loose_bars'])} bars" if lg["loose_bars"] else "")
        tx.append(f"{lg['name']}: glue {what} side by side as drawn; make {lg['count']} log{'s' if lg['count'] > 1 else ''}, "
                  f"{dim(lg['length'])} long, for {lg['slices']} slices" + (f" plus {lg['spares']} spare" if lg["spares"] else "") + ".")
    tx.append("Glue on a flat, waxed or papered surface with cauls across the faces so the bars stay in plane; "
              "a log that is twisted gives slices that won't sit flat together.")
    tx.append("Scrape the glue off, then square one end of each log.")
    S.append({"title": "Glue the logs", "text": tx, "diagrams": [f"log{l['type']}" for l in plan["logs"]]})
    tx = [f"Before cutting, draw a pencil V across the top of each log: every slice keeps a mark that says which way is up and "
          f"where it came from.",
          f"On a crosscut sled with a stop block, cut slices {dim(cut)} thick (finished {short(T)} plus "
          f"{short(sh['flatten_allowance'])} to flatten). Hold the off-cut side with a hold-down, never the fence side.",
          f"Cut {sum(l['slices'] + l['spares'] for l in plan['logs'])} slices in all; stack them in order."]
    if any(l.get("carrier") for l in plan["logs"]):
        tx.append("Logs without two flat adjacent faces rock on the sled: fix them to a straight plywood carrier with "
                  "double-sided tape or hot glue blocks first.")
    S.append({"title": "Crosscut the slices", "text": tx, "diagrams": []})
    turns = sorted({s["xf"] for s in plan["slices"]} - {"id"})
    tx = [f"Lay out the {len(plan['slices'])} slices as numbered in the layout drawing. "
          + ("Slices marked " + ", ".join(f"{XF_MARK[t]} are {XF_TEXT[t]}" for t in turns) + "; the rest go down as cut. " if turns else
             "Every slice goes down as cut. ")
          + "Dry-fit the whole board and look at it before any glue."]
    tx.append("Glue in stages of two to four slices, then glue the stages together. End grain drinks glue: brush a thin "
              "coat on both faces, wait two minutes, add a second coat, then clamp with moderate pressure and cauls top "
              "and bottom so the slices stay flush (the faces are end grain and are hard to plane flat).")
    if plan["pattern"] in ("cubes", "tumbling-blocks", "stars6"):
        tx.append("The rows nest by their zigzags, so each row centres itself on the one below. Clamp across the rows with "
                  "a little pressure from the ends too, or the rows can slide along the 60 degree faces.")
    S.append({"title": "Glue the board", "text": tx, "diagrams": ["layout"],
              "dont": "glue all the slices at once. With more than four joints the slices creep out of plane under clamp pressure, and end grain is slow to flatten."})
    W, L = plan["board"]["width"], plan["board"]["length"]
    S.append({"title": "Trim and flatten", "diagrams": ["face"], "dont": "run the board through a thickness planer. End grain blows out at the trailing edge and the planer can throw pieces.", "text": [
        f"Trim to {dim(W)} x {dim(L)} on the red lines (crosscut sled or track saw, with a backer to stop breakout).",
        "Flatten both faces with a router sled or a drum sander. Do not run end grain through a thickness planer: it "
        "blows out the trailing edge and can throw pieces.",
        "Sand both faces 80, 120, 180; wipe with a damp cloth to raise the grain, let dry, sand 220."]})
    opts = plan["options"]
    tx = [f"Ease every edge with a {opts.get('edge', '1/8\" chamfer')} and break the corners: end-grain edges chip if left sharp."]
    if opts.get("feet"): tx.append("Add four rubber feet with stainless screws, inset 1\" from the corners (feet let the board dry evenly underneath).")
    if opts.get("juice_groove"): tx.append("Rout a juice groove with a 1/2\" core-box bit, 3/4\" from the edge. On end grain, climb-cut slowly and take two passes.")
    if opts.get("handles"): tx.append("Cut finger grips in both ends with a 1-1/4\" cove or core-box bit on the router table.")
    tx.append("Flood with food-grade mineral oil until it stops soaking in (end grain takes a lot: several coats over two days), "
              "then buff on a board butter of mineral oil and beeswax. Re-oil monthly.")
    S.append({"title": "Edges, feet and finish", "text": tx, "diagrams": []})
    return S


# ------------------------------------------------------------------------------------- diagrams
def diagrams(plan, unit_type_of, unit_list):
    polys = plan["polygons"]; sp = plan["species"]; out = {}
    col = lambda r: sp[r]["end"]
    W, L = plan["board"]["width"], plan["board"]["length"]; trim = plan["board"]["trim"]

    # finished face
    sc = min(620 / W, 760 / L)
    s = Svg(trim, sc, pad=60, extra_h=40, title="Finished board, top face")
    for f in plan["face"]: s.poly(f["pts"], col(f["role"]), "#00000055", 0.5)
    s.poly([(trim[0], trim[1]), (trim[2], trim[1]), (trim[2], trim[3]), (trim[0], trim[3])], stroke="#222", sw=1.2)
    s.dimx(trim[0], trim[2], trim[1], short(W)); s.dimy(trim[1], trim[3], trim[0], short(L))
    legend(s, plan, s.h - 30)
    out["face"] = s.svg()

    # layout of slices before trim
    bb = bbox_of([p["pts"] for p in polys])
    sc = min(620 / (bb[2] - bb[0]), 760 / (bb[3] - bb[1]))
    s = Svg(bb, sc, pad=40, extra_h=10, title="Slice layout")
    for p in polys: s.poly(p["pts"], col(p["role"]), "#00000040", 0.4, op=0.55)
    for sl in plan["slices"]:
        for a, b in outline_edges([polys[i]["pts"] for i in sl["bars"]]): s.line(a, b, "#111", 1.6)
    for sl in plan["slices"]:
        c = centroid(bbox_poly(sl["bbox"]))
        lab = f'{sl["n"]} {sl["log"][-1]}' + (f' {XF_MARK[sl["xf"]]}' if sl["xf"] != "id" else "")
        s.text(c, lab, 12, weight="bold", halo=True)
    s.poly(bbox_poly(trim), stroke="#d22", sw=1.4, dash="6 4")
    out["layout"] = s.svg()

    # bars
    out["bars"] = bars_svg(plan)

    # units
    for u in plan["units"]:
        pts = [polys[i]["pts"] for i in u["bars"]]
        c = centroid(bbox_poly(bbox_of(pts)))
        exp = []
        for i in u["bars"]:
            pc = centroid(polys[i]["pts"]); dx, dy = pc[0] - c[0], pc[1] - c[1]; d = math.hypot(dx, dy) or 1
            k = 0.12
            exp.append(([(x + dx / d * k, y + dy / d * k) for x, y in polys[i]["pts"]], polys[i]["role"], i))
        b = bbox_of([e[0] for e in exp])
        s = Svg(b, min(70, 300 / max(b[2] - b[0], b[3] - b[1])), pad=30, title=u["name"])
        for p_, r, i in exp:
            s.poly(p_, col(r), "#222", 0.9)
            bid = next(bt["id"] for bt in plan["bar_types"] if True and shape_of(polys[i]["pts"])[0] == shape_of(bt["pts"])[0])
            s.text(centroid(p_), bid, 13, weight="bold", halo=True)
        out[f"unit{u['type'] + 1}"] = s.svg()

    # logs: end view (cross-section) and side view with the slices
    for lg in plan["logs"]:
        rep = next(sl for sl in plan["slices"] if sl["id"] == lg["rep"])
        pts = [polys[i]["pts"] for i in rep["bars"]]
        b = bbox_of(pts); bw, bh = b[2] - b[0], b[3] - b[1]
        sc = min(60, 560 / bw, 320 / bh)
        s = Svg(b, sc, pad=50, extra_h=150, title=lg["name"])
        for i in rep["bars"]: s.poly(polys[i]["pts"], col(polys[i]["role"]), "#00000066", 0.6)
        for u in lg["units"]:
            for a_, b_ in outline_edges([polys[i]["pts"] for i in unit_list[u]]): s.line(a_, b_, "#111", 1.8)
            t, gx = unit_type_of[u]
            lab = f"U{t + 1}" + (f" {XF_MARK[gx]}" if gx != "id" else "")
            s.text(centroid(bbox_poly(bbox_of([polys[i]["pts"] for i in unit_list[u]]))), lab, 11, weight="bold", halo=True)
        s.dimx(b[0], b[2], b[1], short(bw)); s.dimy(b[1], b[3], b[0], short(bh))
        # side view
        y0 = s.h - 95; x0 = s.pad; Lpx = min(s.w - 2 * s.pad, 600); k = Lpx / lg["length"]
        hpx = 40
        s.raw(f'<text x="{x0}" y="{y0 - 18}" font-size="12" font-weight="bold">Side view: {lg["count"]} x {html.escape(dim(lg["length"]))} '
              f'long, {lg["slices_per_log"]} slices each</text>')
        s.raw(f'<rect x="{x0}" y="{y0}" width="{Lpx:.1f}" height="{hpx}" fill="#f3ead8" stroke="#222"/>')
        et = plan["shop"]["end_trim"] * k
        for xx in (x0, x0 + Lpx - et):
            s.raw(f'<rect x="{xx:.1f}" y="{y0}" width="{et:.1f}" height="{hpx}" fill="#bbb" stroke="#222" stroke-width="0.5"/>')
        cutw = (plan["board"]["thickness"] + plan["shop"]["flatten_allowance"]) * k; kerf = plan["shop"]["kerf"] * k
        x = x0 + et
        for n in range(lg["slices_per_log"]):
            x += cutw
            s.raw(f'<rect x="{x:.1f}" y="{y0 - 3}" width="{max(kerf, 1):.1f}" height="{hpx + 6}" fill="#d22"/>')
            x += kerf
        s.raw(f'<text x="{x0}" y="{y0 + hpx + 18}" font-size="11">slice {html.escape(short(plan["board"]["thickness"] + plan["shop"]["flatten_allowance"]))}, '
              f'kerf {html.escape(short(plan["shop"]["kerf"]))}, ends trimmed {html.escape(short(plan["shop"]["end_trim"]))} (grey)</text>')
        out[f"log{lg['type']}"] = s.svg()
    return out


def bbox_poly(b):
    return [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])]


def legend(s, plan, y):
    x = s.pad
    seen = OrderedDict()
    for r, w in plan["species"].items(): seen.setdefault(w["name"], (w["end"], []))[1].append(r)
    for name, (c, rs) in seen.items():
        s.raw(f'<rect x="{x}" y="{y - 8}" width="16" height="16" fill="{c}" stroke="#222" stroke-width="0.6"/>')
        lab = f"{name} ({', '.join(rs)})"
        s.text((x + 22, y), lab, 12, anchor="start", raw=True)
        x += 34 + 6.5 * len(lab)


def bars_svg(plan):
    bts = plan["bar_types"]; cellw, cellh = 330, 300
    cols = min(3, len(bts)); rows = math.ceil(len(bts) / cols)
    W, H = cols * cellw, rows * cellh
    el = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif">'
          '<title>Bar cross-sections and rip setups</title><rect width="100%" height="100%" fill="#fff"/>']
    used = {}
    for b in plan["bars"]: used.setdefault(b["bar"], []).append(b)
    for n, bt in enumerate(bts):
        ox, oy = (n % cols) * cellw, (n // cols) * cellh
        pts = bt["pts"]; b = bbox_of([pts]); bw, bh = b[2] - b[0], b[3] - b[1]
        sc = min(150 / bw, 110 / bh)
        P = lambda x, y: (ox + 30 + (x - b[0]) * sc + (150 - bw * sc) / 2 + 60, oy + 40 + (b[3] - y) * sc)
        fill = plan["species"][used[bt["id"]][0]["roles"][0]]["end"] if bt["id"] in used else "#ddd"
        el.append(f'<text x="{ox + 12}" y="{oy + 20}" font-size="14" font-weight="bold">Bar {bt["id"]}</text>'
                  f'<text x="{ox + 70}" y="{oy + 20}" font-size="12">{html.escape(bt["label"])}</text>')
        el.append('<polygon points="' + " ".join("%.1f,%.1f" % P(*v) for v in pts) + f'" fill="{fill}" stroke="#222" stroke-width="1.2"/>')
        c = centroid(pts); cx, cy = P(*c)
        for i in range(len(pts)):
            a, bb = pts[i - 1], pts[i]
            m = P((a[0] + bb[0]) / 2, (a[1] + bb[1]) / 2)
            dx, dy = m[0] - cx, m[1] - cy; d = math.hypot(dx, dy) or 1
            el.append(f'<text x="{m[0] + dx / d * 16:.1f}" y="{m[1] + dy / d * 14:.1f}" font-size="10.5" text-anchor="middle" paint-order="stroke" stroke="#fff" stroke-width="2.5" '
                      f'dominant-baseline="middle">{html.escape(short(math.dist(a, bb)))}</text>')
        for i, v in enumerate(pts):
            q = P(*v); dx, dy = cx - q[0], cy - q[1]; d = math.hypot(dx, dy) or 1
            ang = bt["angles"][i]
            el.append(f'<text x="{q[0] + dx / d * 17:.1f}" y="{q[1] + dy / d * 17:.1f}" font-size="9.5" fill="#b22" paint-order="stroke" stroke="#fff" stroke-width="2.5" text-anchor="middle" '
                      f'dominant-baseline="middle">{ang:.0f}°</text>')
        # rip diagram: blank end view with the cuts
        y0 = oy + 175; t = bt["dims"].get("thick") or bh; k = min(28, 50 / t)
        bx0 = ox + 30; blen = 270
        el.append(f'<rect x="{bx0}" y="{y0}" width="{blen}" height="{t * k:.1f}" fill="#f3ead8" stroke="#222"/>')
        tilt = bt["tilt"] or 0; dxs = t * k * math.tan(math.radians(tilt))
        if bt["kind"] in ("rhombus", "parallelogram"):
            step = bt["dims"]["side"] * k; x = bx0 + 20
            while x + step + dxs < bx0 + blen:
                el.append(f'<line x1="{x:.1f}" y1="{y0 + t * k:.1f}" x2="{x + dxs:.1f}" y2="{y0}" stroke="#d22" stroke-width="1.3"/>'); x += step
        elif "triangle" in bt["kind"]:
            half = bt["dims"]["base"] / 2 * k; x = bx0 + 20; flip = False
            while x + half * 2 < bx0 + blen:
                if not flip: el.append(f'<line x1="{x:.1f}" y1="{y0 + t * k:.1f}" x2="{x + half:.1f}" y2="{y0}" stroke="#d22" stroke-width="1.3"/>')
                else: el.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x + half:.1f}" y2="{y0 + t * k:.1f}" stroke="#d22" stroke-width="1.3"/>')
                x += half; flip = not flip
        else:
            step = (bt["dims"].get("width") or bw) * k; x = bx0 + 10
            while x + step < bx0 + blen:
                x += step
                el.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y0 + t * k:.1f}" stroke="#d22" stroke-width="1.3"/>')
        el.append(f'<text x="{bx0}" y="{y0 + t * k + 16:.1f}" font-size="10.5">Blank {html.escape(short(t))} thick'
                  + (f', blade tilted {tilt:.1f}°' if tilt else ', blade square') + '</text>')
        uses = "; ".join(f'{x["total_bars"]} in {plan_name(plan, x["species"])}' for x in used.get(bt["id"], []))
        el.append(f'<text x="{bx0}" y="{y0 + t * k + 32:.1f}" font-size="10.5">{html.escape(uses)}</text>')
    el.append("</svg>")
    return "".join(el)


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
    print(f"{plan['name']}: {W:.3f} x {L:.3f} x {T:.3f} in, {len(plan['slices'])} slices, "
          f"{sum(b['total_bars'] for b in plan['bars'])} bars, {len(plan['bar_types'])} bar shapes, "
          f"{len(plan['units'])} unit types, {len(plan['logs'])} log types")
    for b in plan["bar_types"]:
        print(f"  bar {b['id']}: {b['label']}" + (f", tilt {b['tilt']:.1f}" if b["tilt"] else ""))
    for l in plan["logs"]:
        print(f"  {l['name']}: {l['count']} x {l['length']:.2f}\" -> {l['slices']} slices (+{l['spares']})")
    for s in plan["stock"]:
        print(f"  buy {s['species']}: {s['bf_buy']:g} bd ft")
    bad = [c for c in plan["checks"] if not c["ok"] and c["level"] != "warn"]
    for c in plan["checks"]:
        print(("  ok   " if c["ok"] else "  WARN " if c["level"] == "warn" else "  FAIL ") + c["what"] + (f" ({c['detail']})" if c["detail"] else ""))
    print("wrote", os.path.abspath(a.out))
    sys.exit(1 if bad else 0)
