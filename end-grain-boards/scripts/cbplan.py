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
import planks as PK

DEFAULT_SHOP = {"kerf": 0.125, "max_log_length": 24.0, "flatten_allowance": 0.125, "end_trim": 0.75,
                "stock_width": 5.5, "spare_slices": 1, "rip_oversize": 1 / 32, "true_skim": 0.01, "hold_end": 2.0, "edge_clean": 0.125, "sander_opening": 3.0,
                "glue_extra": 0.5, "length_slack": 0.5, "blank_remainder": 1.5, "max_cut_height": 3.125, "sled_base": 0.5, "min_bar_face": 0.375,
                "max_crosscut": 24.0, "planer_width": 12.5, "planer_min_length": 14.0, "min_sandwich_bar": 0.4}
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


RIP_POINTS = [
    ("The sled", "Every bevelled bar is cut on the rip sled (sheet 06, step 2), the sliding rip jig with toggle clamps that the builders in the best practices guide use. "
     "It runs against the rip fence, which stays on the side the blade leans away from: its usual place on a left-tilt saw; on a right-tilt saw move the fence to the left of the blade."),
    ("Two decks", "The fence deck, between the fence and the blade, carries the locating fence and the toggle clamps. The landing deck, beyond the blade and under its lean, catches what comes off. Nothing is ever loose on the saw table."),
    ("Trapezoids and diamonds", "They start as square-edged strips and are clamped to the fence deck for both bevels; only a waste sliver drops on the landing deck."),
    ("Triangles", "A triangle has no flat left for a clamp, so it is never the piece that is held. This is Vaughn McMillan's cut from Woodcraft Magazine's quilt-pattern board: bevel the edge of a wide board, turn the board over, "
     "and rip again so the triangle comes away as the offcut on the open side of the blade, never between blade and fence. McMillan runs a board at least 5\" wide along the rip fence with a push block and lets the strip land on the outfeed table. "
     "Here the same wide blank is clamped to the fence deck instead, so no hand is near the blade, and the strip lands on the landing deck and rides out with the sled. "
     "The sliding fence with its spacer stack is this plan's addition to his cut: it sets the bar's width from behind the blank, so the landing side stays open as in McMillan's cut and the freed bar is never between the blade and a stop. No builder has tested it: cut test bars in scrap first."),
    ("After every pass", "Push the sled on until the work is clear of the blade, or switch off and wait for the blade to stop, before lifting anything out. Keep the riving knife in place.")]
RIP_TEXT = " ".join(t for _, t in RIP_POINTS)
BAR_TRUE = " Use the V block that step 2 on sheet 06 lists for this bar. The makers in the guide sand glued triangle logs this way on a drum sander; doing it to single bars follows the same idea but is not shown there. Take the first sawn face at one setting on every bar, then lower the head for the second face. With a planer only, truing single bars this way is this plan's own adaptation: prove it on two scrap bars first, feed several bars one behind the other, and if a bar chatters, true the bars by hand instead: 80 grit paper glued to a flat board, the bar in its V block, the same count of even strokes on every bar, checked with calipers. Do not skip the truing: the bars are ripped over size, and untrued bars make a log too big to close on its neighbours."


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
            st.append(f"Machine the two sawn faces: lay the bars on a sawn face, packed tight side by side between the two fences of the bar carrier (step 2 on sheet 06; they lean on each other like roof tiles; "
                      f"tape across both ends), and plane or drum-sand to {dim(d2)}, half from each sawn face"
                      + ". Measure the bars with calipers, not the machine's scale: the carrier adds its own thickness.")
        st.append(f"Check: corners {th:.0f} and {180 - th:.0f} degrees, " + (f"all four faces {dim(pside)}." if kind == "rhombus" and not outside else f"the two planed faces measure {dim(stop)} as sawn and come to {dim(pside)} once the sawn faces are machined."))
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
                      f" Clamp a strip against the locating fence and bevel one edge. Turn the strip end for end, the same face up, sawn edge against the locating fence, and bevel the other edge. For this second pass only the sharp top corner of the sawn edge would touch a square fence, and a sharp corner crushes: rip a filler strip at the same tilt and stick it to the locating fence with double-sided tape, slanted face out, so the whole sawn edge bears on it. "
                      f"The bar sits wide face up, under the caul. The filler is a wedge as long as the strip and as high as the blank is thick, ripped at this same blade tilt so it tapers to a feather edge at the top; with it in place the fence line at the top face has not moved. Set the locating fence with test strips, both bevels cut, until the wide face measures {dim(long_ + e_)}." + deep(H, tilt),
                      (f"True the two sawn faces in a V block: wide face against one wall, a sawn face up and level. One light pass on that face. Then roll the bar over so its wide face lies against the other wall: the sawn face just trued goes down into the V and the untouched sawn face comes up. One light pass on that face too; "
                       f"every bar at one setting, until the wide face is {dim(long_)} and the narrow face {dim(short_)}. By calipers: the wide face is {long_ + e_:.3f}\" off the saw, about {long_ + e_ / 2:.3f}\" after the first sawn face and {long_:.3f}\" after the second." + BAR_TRUE if v60 else
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
                      f"For every bar: turn the blank over end for end (the same edge stays toward the blade, the other face goes down), push it back against the locating fence, close the clamps and push the sled through. "
                      f"The bar comes away on the open side of the blade and lies on the landing deck, base down and point up, on the sandpaper strip. Nothing stands beside it: it is never held between the blade and a stop. Push the sled on until the bar is past the blade, stop the saw, and lift it away.",
                      f"The bar's width is set from behind the blank. The locating fence and its clamps slide as one unit; between the fence and the fixed back rail goes a stack of spacer strips, each {dim((base + e_) / 2 + kerf / cos(tilt))} wide, which is what one bar takes off the blank. "
                      f"Set the first cut with test pieces until the bar's base measures {dim(base + e_)} as sawn; after that, each pass is: open the clamps, loosen the fence, add one spacer, push the fence up to the stack, tighten, clamp. "
                      f"Rip {max(4, int((shop['stock_width'] - shop['blank_remainder']) // ((base + e_) / 2 + kerf / cos(tilt))))} spacers from scrap at one fence setting. Stop when less than {short(shop['blank_remainder'])} of blank is left; that strip is waste."]
                if outside or not equi:
                    st.append(f"Leave the two sawn faces as they are. They end up on the outside of the glue-up and are machined with it; the planed base is the glue face.")
                else:
                    st.append(f"True the two sawn faces in a V block: base against one wall, a sawn face up and level. Light passes, every bar at one setting, "
                              f"until all three faces are {dim(base)}." + BAR_TRUE)
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
LEVEL_NAME = {"sandwich": "sandwich", "sbar": "bar", "tri": "triangle log", "hex": "hexagon log", "band": "band", "quarter": "quarter log", "half": "half log", "block": "block log", "border": "border bar", "panel": "strip panel"}
NO_LOG_BUILD = {
    "rosettes": "The hexagon-square-triangle rosette (3.4.6.4) has no sound build: every way of cutting it into logs either "
                "leaves a re-entrant glue-up that cannot be machined flat or splits the hexagons and squares into slivers. "
                "Use pattern \"pinwheel\" instead: hexagons each ringed by six diamonds with small triangles between, which "
                "builds from trued triangle logs.",
    "rhombitrihex": None}


def _up(x, step=0.25):
    return math.ceil(x / step - 1e-9) * step


def build(design, out, photo=None):
    if design["pattern"] in patterns.PLANK:          # rows crosscut from one glued-up plank: its own builder
        import importlib
        return importlib.import_module(patterns.PLANK[design["pattern"]]).build(design, out, photo)
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
        if rc["kind"] in ("polygon", "hexagon") or rc["warn"]: return False      # a hexagon bar needs four bevel rips; two trapezoids do the same job
        return not ("triangle" in rc["kind"] and max(A) > 90.5)
    # Sizes after truing. Every truing pass takes a skim off the faces it machines, so logs, rows and the board all
    # finish a little under the drawn pattern. The pattern is laid out at its drawn size, then scaled to the trued size.
    ec = shop["edge_clean"]; S3_ = math.sqrt(3)
    kind0 = cells.get("kind", "panel"); ang = math.radians(cells.get("angle", 0)); ca, sa = math.cos(ang), math.sin(ang)
    drawn = list(trim); cen = ((trim[0] + trim[2]) / 2, (trim[1] + trim[3]) / 2)
    G = lambda p: (p[0] * ca + p[1] * sa, -p[0] * sa + p[1] * ca)          # board -> row frame (u along the rows, v across them)
    Bd = lambda p: (p[0] * ca - p[1] * sa, p[0] * sa + p[1] * ca)
    across_x = abs(sa) > 0.5
    # The build. Rectangles first: sandwiches ripped into striped bars (bars.py). The triangle or hexagon logs stay as
    # the named exception: asked for with "build": "logs", or used when no bar of a workable size is a slice of one sandwich.
    import bars as BR
    wood = lambda r: sp[r]["key"]
    bmode = str(design.get("build") or (design.get("params") or {}).get("build") or "auto")
    want_bars = kind0 in ("tri", "hex") and not design.get("cells") and bmode in ("auto", "bars", "sandwich")
    trim0 = list(trim); roles0 = [p["role"] for p in polys]; cen0 = cen; bcells = None; bars_why = ""
    for use_bars in ([True, False] if want_bars else [False]):
        trim = list(trim0); cen = cen0; skim = 0.0 if use_bars else shop["true_skim"]
        for p, r0 in zip(polys, roles0): p["role"] = r0
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
                ex_ = float(g.get("period_extra", 0))      # a part repeat on top of the whole ones, so both sides end on the same wood
                along_req = (max(1, math.floor(along_req / (g["period"] * ku) - ex_ + 0.5 + 1e-6)) + ex_) * g["period"] * ku
            cu, cv = G(cen); hu = along_req / ku / 2
            if g.get("band"):         # a stripe runs along every row: start and end the board on it, so both ends look alike
                f0, f1 = g["band"]; nf = max(1, round((across_req - (f1 - f0) * Ht) / Ht))
                if g.get("band_centred"):      # one centred motif: take the row count whose two cuts sit the same distance from it
                    off = lambda n_: abs(((cv - v0) / H0 - (n_ + f0 + f1) / 2 + 0.5) % 1 - 0.5)
                    nf = min((n_ for n_ in (nf, nf + 1, nf - 1) if n_ >= 1), key=lambda n_: (round(off(n_), 6), abs(n_ * Ht + (f1 - f0) * Ht - across_req)))
                m0 = round((cv - v0) / H0 - (nf + f0 + f1) / 2)
                jt_ = g.get("band_joints"); j0 = ec / kv if jt_ or abs(f0 - round(f0)) < 1e-6 else 0.0; j1 = ec / kv if jt_ or abs(f1 - round(f1)) < 1e-6 else 0.0      # a cut on a row joint moves in by the clean-up cut
                vlo = v0 + (m0 + f0) * H0 + j0; vhi = v0 + (m0 + nf + f1) * H0 - j1
                cv = (vlo + vhi) / 2; half = (vhi - vlo) / 2
            if g.get("period") and not g.get("keep_phase") and g.get("phase") is None:       # no slivers: slide the two side cuts along the repeat to where the narrowest piece they leave is widest
                per_ = float(g["period"]); gp = [[G(v) for v in p["pts"]] for p in polys]
                gp = [q for q in gp if max(v[1] for v in q) > cv - half and min(v[1] for v in q) < cv + half]
                def narrowest(c):
                    w = per_
                    for q in gp:
                        lo, hi = min(v[0] for v in q), max(v[0] for v in q)
                        for edge, sg in ((c - hu, 1), (c + hu, -1)):
                            if lo < edge - 1e-6 and hi > edge + 1e-6: w = min(w, (hi - edge) if sg > 0 else (edge - lo))
                    return w
                cu = max((cu + k * per_ / 24 for k in range(24)), key=lambda c: (round(narrowest(c), 4), -abs(c - cu)))
            if g.get("phase") is not None:      # the generator names where a side cut belongs in the repeat
                per_ = float(g["period"]); cu = float(g["phase"]) + hu + round((cu - hu - float(g["phase"])) / per_) * per_
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
        if not use_bars: break
        if kind0 != "tri": plan_trim = list(trim)
        else: plan_trim = [trim[0] - ec - 0.01, trim[1] - ec - 0.01, trim[2] + ec + 0.01, trim[3] + ec + 0.01]
        bcells = BR.layout(polys, plan_trim, wood, shop)
        if bcells and g.get("row_edges"):      # the two edges along the rows fall on row joints: whole rows, planed faces, nothing sawn off
            Gb, Bb = BR._frame(bcells["angle"]); Hb = float(bcells["row"]); ovb = bcells["origin"][1]
            qb = [Gb((trim[a_], trim[b_])) for a_ in (0, 2) for b_ in (1, 3)]
            U0b, U1b = min(v[0] for v in qb), max(v[0] for v in qb); V0b, V1b = min(v[1] for v in qb), max(v[1] for v in qb)
            V0n = ovb + round((V0b - ovb) / Hb) * Hb; V1n = V0n + max(1, round((V1b - V0b) / Hb)) * Hb
            qb = [Bb(p_) for p_ in ((U0b, V0n), (U1b, V1n))]
            trim = [min(qb[0][0], qb[1][0]), min(qb[0][1], qb[1][1]), max(qb[0][0], qb[1][0]), max(qb[0][1], qb[1][1])]
        if bcells and kind0 == "tri":      # rows run past the trim by the clean-up cut; the outside rows end on planed faces and need none
            e_ = ec + 0.01; plan_trim = [trim[0] - e_, trim[1] + 1e-4, trim[2] + e_, trim[3] - 1e-4] if bcells["angle"] == 0 else [trim[0] + 1e-4, trim[1] - e_, trim[2] - 1e-4, trim[3] + e_]
        if bcells: break
        bars_why = (f"no rectangular bar {short(shop['min_sandwich_bar'])} or more on its narrow side is a slice of one flat sandwich "
                    f"that fits under the tilted blade, so this board is built from {'triangle' if kind0 == 'tri' else 'hexagon'} logs")
    if bcells:
        ang = math.radians(bcells["angle"]); ca, sa = math.cos(ang), math.sin(ang); across_x = abs(sa) > 0.5      # the bars' own row direction
        ws = BR.widths(shop); bcells["sandwich_width"] = shop.get("sandwich_width") or ws[1]
        lp = BR.bar_plan(polys, plan_trim, bcells, wood)
        if not shop.get("sandwich_width"):      # one board wide if every sandwich still gives three slabs
            if all(BR.per_sandwich({"tilt": lg["tilt"], "slab": lg["slab"], "stack": lg["stack"]}, ws[0], shop) >= 3 for lg in lp["logs"] if lg["shape"] == "sandwich"):
                bcells["sandwich_width"] = ws[0]; lp = BR.bar_plan(polys, plan_trim, bcells, wood)
    else:
        lp = LG.plan(polys, plan_trim, cells, wood, bar_ok)
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
        lg["name"] = f"Sandwich {lg['id']}" if lg["shape"] == "sandwich" else f"Bar {lg['id']}" if lg["shape"] == "sbar" else f"Log {lg['id']}"
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
    ecs = [float(v) for v in g.get("edge_clean", [ec] * 4)]      # left, bottom, right, top: what each edge loses to the clean-up cut
    tri_like = kind == "tri" or (kind == "bars" and kind0 == "tri")       # the trim was already set inside the glued rows
    if not tri_like:
        trim = [trim[0] + ecs[0], trim[1] + ecs[1], trim[2] - ecs[2], trim[3] - ecs[3]]
        trim = [max(trim[0], glued[0] + ecs[0]), max(trim[1], glued[1] + ecs[1]), min(trim[2], glued[2] - ecs[2]), min(trim[3], glued[3] - ecs[3])]
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
    zig = ([False, False, True, True] if across_x else [True, True, False, False]) if kind == "tri" else [False, False, True, True] if kind == "hex" else [False] * 4

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
    check(abs(pa - W * Lb) < 1e-3 * W * Lb, ("Rows" if kind in ("tri", "blocks", "bars") else "Slices") + " cover the whole board", f"{pa:.2f} of {W * Lb:.2f} sq in" if abs(pa - W * Lb) >= 1e-3 * W * Lb else (f"{len(rows)} rows" if kind in ("tri", "blocks", "bars") else f"{sum(len(r['pucks']) for r in rows)} slices in {len(rows)} rows"))
    for lg in logs:
        a_parts = sum(abs(area(p["pts"])) for st in lg["stages"] for p in st["parts"]); a_out = abs(area(lg["outline"]))
        if abs(a_parts - a_out) > 2e-3 * a_out:
            check(False, f"{lg['name']} cross-section is complete", f"parts {a_parts:.3f} sq in, outline {a_out:.3f}")
    check(True, "Every sandwich's layers and every bar fill their cross-sections" if kind == "bars" else "Every log's parts fill its cross-section")
    if kind == "bars":      # the proof: the face rebuilt from the sandwiches alone is the pattern
        nb_, tot_, bad_ = BR.verify(rows, polys, wood, trim); sw_ = [lg for lg in logs if lg["shape"] == "sandwich"]; bk_ = [lg for lg in logs if lg["shape"] == "sbar"]
        check(True, "Every bar is a slice of one flat sandwich", f"{nb_} bars of {len(bk_)} kind{'s' if len(bk_) > 1 else ''}, each {short(lp['info']['bar'])} x {short(lp['info']['row'])}, from {len(sw_)} sandwich{'es' if len(sw_) != 1 else ''}"
              + (f"; {sum(1 for l in bk_ if not l.get('sandwich'))} kind{'s are' if sum(1 for l in bk_ if not l.get('sandwich')) > 1 else ' is'} one solid wood" if any(not l.get("sandwich") for l in bk_) else ""))
        check(bad_ <= 2e-5 * tot_ + 2e-5 * nb_, "The face rebuilt from the sandwiches matches the pattern", f"every bar redrawn from its layers, the blade tilt and the two squaring cuts, laid over the pattern: {tot_:.1f} sq in compared, {bad_:.4f} sq in differ")
        for lg in sw_:
            if lg["tilt"] > 0:
                cap_ = shop["max_cut_height"] * math.cos(math.radians(lg["tilt"]))
                check(lg["h"] <= cap_ + 1e-6, f"{lg['name']} fits under the blade tilted {lg['tilt']:g} degrees", f"{short(lg['h'])} thick; the blade cuts {short(cap_)} deep at that tilt ({short(shop['max_cut_height'])} upright)")
        thin_ = [f"{lg['name']} {short(t)}" for lg in sw_ for _, _, t in lg["stack"] if t < 0.25 - 1e-6]
        check(not thin_, "No sandwich layer is under 1/4\" thick", ", ".join(thin_) + ("; make the pattern larger" if thin_ else ""), "warn")
    elif bars_why:
        check(False, "Built from rectangles (sandwich bars)", bars_why[0].upper() + bars_why[1:] + ". Make the pattern larger to get a bar build.", "warn")

    # how many of each log, and how long
    cut = T + shop["flatten_allowance"]; pitch = cut + shop["kerf"]
    npk = defaultdict(int)
    for r in rows:
        for pk in r["pucks"]: npk[pk["log"]] += 1
    ends = shop["end_trim"] + shop["hold_end"]; usable = shop["max_log_length"] - ends
    for lg in logs: lg["make"] = defaultdict(int)
    # rows of bevelled logs are not built slice by slice: the logs are glued into planks and each crosscut is a row
    planks = PK.plan(rows, lp["info"].get("angle", 0), shop["max_crosscut"]) if kind in ("tri", "blocks", "bars") else []
    if planks:      # trim margins measured on the rows as they really leave the plank, overhang included
        ai = 1 if across_x else 0; oi = 1 - ai; lows = []; highs = []; olo = []; ohi = []
        for r in rows:
            o0 = r["slice"]["outline"]; olo.append(min(v[oi] for v in o0)); ohi.append(max(v[oi] for v in o0))
            o_ = clip_rect(o0, [trim[0] - 1e-6, -1e6, trim[2] + 1e-6, 1e6] if across_x else [-1e6, trim[1] - 1e-6, 1e6, trim[3] + 1e-6]) or o0      # only the part of the row the board keeps
            c_ = sum(v[ai] for v in o_) / len(o_)
            lows.append(max(v[ai] for v in o_ if v[ai] < c_)); highs.append(min(v[ai] for v in o_ if v[ai] > c_))
        fa = (max(lows), min(highs)); fo = (min(olo), max(ohi))
        full[:] = [fo[0], fa[0], fo[1], fa[1]] if across_x else [fa[0], fo[0], fa[1], fo[1]]
        margins[:] = [trim[0] - full[0], full[2] - trim[2], trim[1] - full[1], full[3] - trim[3]]
        r1 = rows[0]["slice"]["outline"]; tip1 = [trim[0] - min(v[0] for v in r1), trim[1] - min(v[1] for v in r1)]
    else: tip1 = None
    for pl in planks:
        n = len(pl["uses"]); need = n + shop["spare_slices"]
        k = max(1, math.ceil(need * pitch / usable)); per = math.ceil(need / k)
        pl.update(rows_cut=n, spares=k * per - n, per_plank=per, count=k, length=max(_up(per * pitch + ends + shop["length_slack"]), shop["planer_min_length"]))      # never shorter than the planer can feed
        # is this plank worth making: is its row repeated, as cut or turned?
        by = OrderedDict()
        for u in pl["uses"]: by[u["op"]] = by.get(u["op"], 0) + 1
        slid = len({u["at"] for u in pl["uses"]}) > 1
        if n == 1:
            pl["worth"] = False
            pl["why"] = f"Not repeated. Row {pl['uses'][0]['row']} is the only row with this sequence of logs, as cut or turned, so this plank saves no work: it is that one row, glued once."
        else:
            pl["worth"] = True
            pl["why"] = (f"Repeated {n} times: " + _join(f"{c} {'row' if c == 1 else 'rows'} {PK.OP_TEXT[o]}" for o, c in by.items())
                         + (", some slid along" if slid else "") + f". One glue-up gives all {n} rows.")
        for pk in pl["pucks"]:
            lg = byid[pk["log"]]; lg["make"][pl["length"]] += k
            lg.setdefault("planks", []); lg["planks"] += [] if pl["id"] in lg["planks"] else [pl["id"]]
    for lg in logs:
        if planks and lg["crosscut"]: lg.update(slices=sum(lg["make"].values()), spares=0, per_log=0)
    for lg in logs:
        if not lg["crosscut"] or planks: continue
        n = npk[lg["id"]]; need = n + max(shop["spare_slices"], math.ceil(n * 0.05))
        k = max(1, math.ceil(need * pitch / usable)); per = math.ceil(need / k)
        length = _up(per * pitch + ends + shop["length_slack"])
        if lg.get("graded"):      # one panel, planed thinner between cuts: it must stay long enough for the planer to the last cut
            k, per = 1, n; length = _up(n * pitch + max(ends, shop["planer_min_length"]))
            hs = sorted({round(r["height"], 4) for r in rows}, reverse=True)
            lg["grades"] = [{"thick": h, "rows": [r["n"] for r in rows if abs(r["height"] - h) < 1e-3]} for h in hs]
        lg.update(slices=n, spares=k * per - n, per_log=per); lg["make"][length] += k
    bar_types = OrderedDict(); need = defaultdict(lambda: defaultdict(int))
    slabs = defaultdict(lambda: defaultdict(int))
    for lg in sorted(logs, key=lambda l: -l["level"]):
        if lg["shape"] == "sandwich":       # a sandwich is ripped into slabs, one slab a bar: how many sandwiches the bars need
            cut_ = {"tilt": lg["tilt"], "slab": lg["slab"], "stack": lg["stack"]}
            lg["per"] = BR.per_sandwich(cut_, lg["w"], shop); lg["slabs"] = 0; lg["slab_spares"] = 0
            kk = sum(slabs[lg["id"]].values()); nn = math.ceil((kk + max(1, math.ceil(kk * 0.1))) / max(1, lg["per"])) if kk else 1
            w2 = lg["w"]; wb_ = shop.get("sandwich_width") or BR.widths(shop)[1]
            if nn > 4 and wb_ > w2 and BR.per_sandwich(cut_, wb_, shop) > lg["per"]:      # more than four of one sandwich: make them two boards wide instead
                w2 = wb_; nn = math.ceil((kk + max(1, math.ceil(kk * 0.1))) / BR.per_sandwich(cut_, wb_, shop))
            while w2 - 0.25 >= 3.0 and BR.per_sandwich(cut_, w2 - 0.25, shop) * nn >= kk + max(1, math.ceil(kk * 0.1)): w2 -= 0.25      # no wider than the slabs need
            if abs(w2 - lg["w"]) > 1e-6:
                f_ = w2 / lg["w"]; sx_ = lambda ps: [(x * f_, y) for x, y in ps]
                lg["w"] = w2; lg["outline"] = sx_(lg["outline"]); lg["cells"] = [(r, sx_(q)) for r, q in lg["cells"]]; lg["per"] = BR.per_sandwich(cut_, w2, shop)
                for st in lg["stages"]:
                    for part in st["parts"]: part["pts"] = sx_(part["pts"])
            for ln, k in sorted(slabs[lg["id"]].items()):
                sp_ = max(1, math.ceil(k * 0.1)); n_ = math.ceil((k + sp_) / max(1, lg["per"]))
                lg["make"][ln] += n_; lg["slabs"] += k; lg["slab_spares"] += n_ * lg["per"] - k
        for st in lg["stages"]:
            for part in st["parts"]:
                for ln, k in list(lg["make"].items()):
                    if part.get("cut"):
                        slabs[part["log"]][_up(ln + shop["glue_extra"])] += k
                    elif "log" in part:
                        byid[part["log"]]["make"][_up(ln + shop["glue_extra"])] += k
                    elif part.get("layer"):
                        t_ = max(v[1] for v in part["pts"]) - min(v[1] for v in part["pts"]); nb_ = max(1, math.ceil((lg["w"] - 0.01) / shop["stock_width"]))
                        key = (("layer", round(t_, 4), nb_, bool(part.get("outer"))), False)
                        if key not in bar_types:
                            w1 = lg["w"] if nb_ == 1 else lg["w"] / nb_ + 0.125
                            bar_types[key] = {"id": None, "pts": [(0, 0), (lg["w"], 0), (lg["w"], t_), (0, t_)], "sides": [lg["w"], t_, lg["w"], t_], "angles": [90] * 4,
                                "recipe": {"kind": "board", "label": f"{short(t_)} x {short(lg['w'])} layer", "dims": {"width": lg["w"], "thick": t_}, "stock": t_, "per_bar": shop["stock_width"], "lead": 0.0, "blank_width": _up(w1 + 0.25, 0.25),
                                           "tilt": 0, "stop": None, "setup": None, "warn": [], "boards": nb_, "outer": bool(part.get("outer")),
                                           "steps": ([f"Each layer is {nb_} boards edge-glued: joint one face and both edges of {nb_} boards about {short(w1)} wide, glue them edge to edge on flat cauls, and plane the panel once the glue has cured. A joint inside a layer is one wood glued to itself and disappears in the end grain."] if nb_ > 1 else
                                                     ["Each layer is one board: joint one face and one edge."])
                                                    + [f"Plane to {dim(t_)}" + (". This is an outside layer: it only has to be at least this thick, and a little over does no harm." if part.get("outer") else
                                                         ". This is an inside layer and its thickness is a width on the face of the board: set the planer with calipers and take the last pass on every layer of this thickness, in every wood, without moving the handwheel."),
                                                       f"Rip or joint the layer to {short(lg['w'])} wide, edges square. Both faces are glue faces: plane them the day they are glued."]}}
                        part["shape"] = key
                        need[(key, part["wood"])][_up(ln + shop["glue_extra"])] += k * nb_
                    else:
                        key, pp, L, A = shape_of(part["pts"]); key = (key, bool(part.get("outside")))
                        if key not in bar_types:
                            bar_types[key] = {"id": None, "recipe": recipe(key[0], pp, L, A, shop, key[1]), "pts": pp, "sides": L, "angles": A}
                        if lg["kind"] == "panel" and bar_types[key].get("graded") is None and (lg.get("graded") or bar_types[key]["recipe"]["kind"] in ("square", "rect")):
                            # a strip of a graded panel: the blank is planed to the panel's first thickness and the strip is ripped to its width
                            wx = max(v[0] for v in part["pts"]) - min(v[0] for v in part["pts"]); tp = lg["h"] + 1 / 8
                            ov_ = shop.get("rip_oversize", 1 / 32)
                            bar_types[key]["graded"] = True
                            bar_types[key]["recipe"] = {"kind": "rect", "label": f"{short(wx)} strip", "dims": {"width": wx, "thick": tp}, "stock": tp,
                                "per_bar": wx + ov_ + shop["kerf"], "lead": 0.0, "tilt": 0, "stop": wx + ov_, "setup": "square", "warn": [],
                                "steps": [f"Mill the blank to {dim(tp)} thick: the panel's {'first ' if lg.get('graded') else ''}thickness plus 1/8\" to clean up after glue. Pencil a squiggle along both planed faces before ripping: in the panel those faces lie up and down, and the squiggle tells them from the sawn edges once the strip is nearly square.",
                                          f"Blade square. Rip the strip {dim(wx + ov_)} wide with the fence {short(wx + ov_)} from the blade. Sheet 02 lists what each blank yields, spares included: rip each blank full length, then crosscut every strip to its length in the cut list below.",
                                          f"Stand it on edge and plane the sawn edges to {dim(wx)}, half off each edge. Take the last pass on every strip of this width, both woods, at one planer setting without touching the handwheel, so the strips of every panel are the same width and the grid lines of one panel meet those of the next. Measure with calipers: this width is a grid line that runs the whole board."]}
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
    tilts = [bt["recipe"]["tilt"] for bt in bar_types.values() if bt["recipe"]["tilt"]] + [lg["tilt"] for lg in logs if lg["shape"] == "sandwich" and lg["tilt"]]
    check(all(t <= 45.01 for t in tilts), "Every bevel is 45 degrees or less from vertical")
    small = [f'bar {bt["id"]} ({short(min(bt["sides"]))} face)' for bt in bar_types.values() if min(bt["sides"]) < shop["min_bar_face"] - 1e-6 and bt["recipe"]["kind"] != "board"]
    check(not small, f"No bar has a face under {short(shop['min_bar_face'])}", ", ".join(small) + ("; make the pattern larger" if small else ""), "warn")

    bars_out = []
    for (key, wkey), byl in need.items():
        bt = bar_types[key]; rc = bt["recipe"]
        per_blank = max(1, int((shop["stock_width"] - (shop["blank_remainder"] if "triangle" in rc["kind"] else 0.25) - rc.get("lead", 0)) // rc["per_bar"]))
        blanks = []
        for ln, c in sorted(byl.items()):
            spare = 0 if rc["kind"] == "board" else max(1, math.ceil(c * 0.1))      # spare slabs are already counted into the sandwiches
            blanks.append({"bar_length": ln, "bars": c, "spares": spare, "blanks": math.ceil((c + spare) / per_blank), "blank_length": math.ceil(ln + 1)})
        bars_out.append({"bar": bt["id"], "species": wkey, "label": rc["label"], "kind": rc["kind"], "stock": rc["stock"], "per_blank": per_blank,
                         "lengths": blanks, "total_bars": sum(byl.values()), "total_spares": sum(b["spares"] for b in blanks)})
    bars_out.sort(key=lambda b: (int(b["bar"]), b["species"]))

    stock = OrderedDict()
    for b in bars_out:
        q = nominal(b["stock"]); rough_t = (q or 16) / 4
        bw_ = next(bt["recipe"].get("blank_width") for bt in bar_types.values() if bt["id"] == b["bar"]) or shop["stock_width"]
        bf = sum(bl["blanks"] * rough_t * (bw_ + 0.5) * bl["blank_length"] / 144 for bl in b["lengths"])
        st = stock.setdefault(b["species"], {"species": woods[b["species"]]["name"], "items": [], "bf": 0})
        st["items"].append({"bar": b["bar"], "mill_to": b["stock"], "rough": f"{q}/4" if q else "glue up", "per_blank": b["per_blank"],
                            "blanks": [{"n": bl["blanks"], "size": f'{short(b["stock"])} x {short(bw_)} x {bl["blank_length"]}"',
                                        "yield": (f'{bl["bars"]} boards for the layers' if b["kind"] == "board" else f'{bl["bars"]} + {bl["spares"]} spare')} for bl in b["lengths"]]})
        st["bf"] += bf
        if not q: check(False, f"Bar {b['bar']} stock", f"{b['stock']:.2f}\" thick is more than 16/4; laminate blanks first")
    if lp["info"]["kind"] == "panel" and all(bt.get("graded") for bt in bar_types.values()):      # every strip is the same thickness: rip them all from shared blanks, not one blank per width
        usable_w = shop["stock_width"] - 0.25
        for wkey, st in stock.items():
            mine = [b for b in bars_out if b["species"] == wkey]; b0 = mine[0]; q = nominal(b0["stock"])
            # every strip this wood needs, longest first, packed across blanks: each blank is listed with what it yields
            strips = []
            for b in mine:
                pb = bar_types[next(k_ for k_, bt in bar_types.items() if bt["id"] == b["bar"])]["recipe"]["per_bar"]
                for l in b["lengths"]: strips += [(l["bar_length"], pb, b["bar"])] * (l["bars"] + l["spares"])
            strips.sort(key=lambda t: (-t[0], t[2])); blanks = []
            for ln_, pb, bid in strips:
                bl = next((x for x in blanks if x["w"] + pb <= usable_w + 1e-6), None)
                if bl is None: bl = {"w": 0.0, "len": math.ceil(ln_ + 1), "got": []}; blanks.append(bl)
                bl["w"] += pb; bl["got"].append((bid, ln_))
            rowsb = OrderedDict()
            for bl in blanks:
                cnt = OrderedDict()
                for g_ in bl["got"]: cnt[g_] = cnt.get(g_, 0) + 1
                yl = ", ".join(f'{c} x bar {bid} at {short(ln_)}' for (bid, ln_), c in cnt.items())
                rowsb[(bl["len"], yl)] = rowsb.get((bl["len"], yl), 0) + 1
            st["items"] = [{"bar": f'{mine[0]["bar"]}-{mine[-1]["bar"]}' if len(mine) > 1 else mine[0]["bar"], "mill_to": b0["stock"], "rough": f"{q}/4" if q else "glue up", "per_blank": max(len(bl["got"]) for bl in blanks),
                            "blanks": [{"n": n_, "size": f'{short(b0["stock"])} x {short(shop["stock_width"])} x {ln_}"', "yield": yl} for (ln_, yl), n_ in rowsb.items()]}]
            st["bf"] = sum((q or 16) / 4 * (shop["stock_width"] + 0.5) * bl["len"] / 144 for bl in blanks)
    if frame:
        thin = [r for r in frame_out["rings"] if r["width"] < 0.375 - 1e-6]
        check(not thin, "Frame rings at least 3/8\" wide", ", ".join(f'{r["role"]} {short(r["width"])}' for r in thin) + ("; a thinner end-grain strip breaks before it is glued on" if thin else ""), "warn")
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
    if planks:
        hh = max(pl["height"] for pl in planks); cap = shop["max_cut_height"] - shop["sled_base"]
        check(hh <= cap + 1e-6, "The planks fit under the saw on the crosscut sled", f'{short(hh)} thick on a {short(shop["sled_base"])} sled base; the blade clears {short(shop["max_cut_height"])}')
    for lg in logs:
        if lg["crosscut"] and not planks:
            hh = lg["trued"] * math.sqrt(3) / 2 if lg["kind"] == "tri" else min(lg["trued"]) if "trued" in lg else min(lg["w"], lg["h"]) if lg["kind"] == "hex" else lg["h"]
            cap = shop["max_cut_height"] - shop["sled_base"]
            check(hh <= cap + 1e-6, f"{lg['name']} fits under the saw on the crosscut sled",
                  f'{short(hh)} tall on a {short(shop["sled_base"])} sled base; the blade clears {short(shop["max_cut_height"])}'
                  + ("" if hh <= cap + 1e-6 else ". Make the pattern smaller, or crosscut on a bandsaw or a 12 inch saw and set shop.max_cut_height"))
    for pl in planks:
        check(pl["width"] <= shop["max_crosscut"] + 1e-6, f"Plank {pl['id']} fits the crosscut sled",
              f'{short(pl["width"])} wide; the sled crosscuts {short(shop["max_crosscut"])}' + ("" if pl["width"] <= shop["max_crosscut"] + 1e-6 else ". Make the board narrower across the rows, or set shop.max_crosscut"), "warn")
    if planks:
        once = [pl["id"] for pl in planks if pl["rows_cut"] == 1]; rep = sum(pl["rows_cut"] for pl in planks if pl["rows_cut"] > 1)
        check(len(once) * 2 <= len(planks), "Planks are worth making: most rows repeat, as cut or turned",
              f"{rep} of {len(rows)} rows come from a plank that is cut more than once; {len(planks)} plank type{'s' if len(planks) > 1 else ''} in all"
              + (f". {_join(once)} {'is' if len(once) == 1 else 'are'} cut for a single row" if once else "")
              + ("; this pattern does not repeat from row to row at this size, so planks save little. Change the pattern, its colouring or the board size" if len(once) * 2 > len(planks) else ""), "warn")
    mx = max(len(st["parts"]) for lg in logs for st in lg["stages"] if lg["kind"] != "panel")if any(lg["kind"] != "panel" for lg in logs) else 0
    if kind == "bars":
        nsw_ = sum(1 for lg in logs if lg["shape"] == "sandwich"); nbk_ = len(logs) - nsw_
        check(nsw_ <= 4 and nbk_ <= 8, "A manageable number of sandwiches and bar kinds", f"{nsw_} sandwich{'es' if nsw_ != 1 else ''}, {nbk_} bar kind{'s' if nbk_ != 1 else ''}", "warn")
    elif mx: check(mx <= 4, "No log glue-up has more than four parts", f"largest has {mx}", "warn")
    crossed = [lg for lg in logs if lg["crosscut"]]
    if kind != "bars": check(len(logs) <= 8, "A manageable number of log types", f"{len(logs)} log types, {len(crossed)} of them " + ("glued into planks" if planks else "sliced"), "warn")
    need_ = [ecs[0], ecs[2], ecs[1], ecs[3]] if not tri_like else [ec] * 4
    if kind == "bars" and tri_like: need_ = [0, 0, ec, ec] if across_x else [ec, ec, 0, 0]      # the first and last rows end on planed plank faces
    check(all(m >= n_ - 3e-3 for m, n_ in zip(margins, need_)), f"At least {short(ec)} to trim on every sawn edge" if min(need_) < ec else f"At least {short(ec)} to trim on every edge",
          ", ".join(f"{short(m)}" if m > 1e-3 else "none (a planed face)" for m in margins) + " (left, right, bottom, top)")
    check(T >= 1.0, "Board at least 1\" thick (end grain under 1\" can split)", f"{T}\"")
    W, Lb = W + 2 * fw, Lb + 2 * fw
    check(max(W, Lb) / T <= 18, "Board not too large for its thickness", f"{W:.1f} x {Lb:.1f} x {T}", "warn")

    plan = {"name": design.get("name", design["pattern"]), "description": design.get("description", ""), "pattern": design["pattern"],
            "bar_true": BAR_TRUE, "board": {"width": W, "length": Lb, "thickness": T, "trim": trim, "glued": glued, "full": full, "zig": zig, "drawn": drawn, "margins": margins, "tip1": tip1, "center": list(cen), "field": [Wf, Lf], "frame": frame_out},
            "shop": shop, "species": {r: sp[r] for r in list(roles) + [r[0] for r in rings]}, "woods": list(woods.values()),
            "notes": g.get("notes", []) + design.get("notes", []), "options": design.get("options", {}),
            "face": face, "polygons": polys,
            "bar_types": [dict(id=bt["id"], label=bt["recipe"]["label"], kind=bt["recipe"]["kind"], dims=bt["recipe"]["dims"], tilt=bt["recipe"]["tilt"],
                               steps=bt["recipe"]["steps"], pts=bt["pts"], sides=bt["sides"], angles=bt["angles"], stop=bt["recipe"].get("stop"),
                               setup=bt["recipe"].get("setup"), strip=bt["recipe"].get("strip"), vsize=bt["recipe"].get("vsize"), stock=bt["recipe"]["stock"]) for bt in bar_types.values()],
            "bars": bars_out, "logs": logs, "rows": rows, "info": lp["info"], "stock": list(stock.values()), "checks": checks, "method": "planks" if planks else "logs", "planks": planks,
            "slice_cut": cut, "n_slices": sum(len(r["pucks"]) for r in rows)}
    import repeats as RP
    plan["repeats"] = RP.analyse(plan)
    if plan["repeats"].get("summary"):
        check(True, "Repeat math", plan["repeats"]["summary"])
    plan["vblocks"] = vblocks(plan)
    plan["steps"] = steps(plan, design)
    for w in plan["woods"]:      # what the wood list warns of is said again at the step where it bites
        note = str(SP.SPECIES.get(w["key"], ("",) * 7)[6]); nm = w["name"]
        if "wipe with solvent" in note:
            for st in plan["steps"]:
                if st.get("glue"): st["text"].append(f"{nm}: wipe every glue face of it with acetone or denatured alcohol just before the glue goes on, and let it flash off. Its colour and oil otherwise bleed into the paler wood beside it.")
        if "splinters" in note:
            for st in plan["steps"]:
                if st["title"].startswith("Mill"): st["text"].append(f"{nm} splinters, and the splinters fester: wear gloves when handling it rough, ease the arrises of every blank with a pass of sandpaper, and take lighter cuts in it than in the other woods.")
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


def _rows_level(plan, rows):
    """True when every row's end sits level with row 1's, so there is no slide to set."""
    try:
        a_ = math.radians(plan["info"].get("angle", 0)); ux, uy = math.cos(a_), math.sin(a_)
        e_ = [min(v[0] * ux + v[1] * uy for v in r["slice"]["outline"]) for r in rows]
        return all(abs(x - e_[0]) < 0.01 for x in e_)
    except Exception:
        return False


def _plank_steps(S, plan):
    """Logs -> planks -> rows -> board, for every board whose rows are made of bevelled logs."""
    if plan["info"]["kind"] == "bars" and not plan.get("_words"):      # the same steps, said of bars
        import re
        plan["_words"] = True; n0 = len(S); _plank_steps(S, plan); del plan["_words"]
        sub = lambda t: re.sub(r"\blog(s?)\b", r"bar\1", re.sub(r"\bLog(s?)\b", r"Bar\1", t)).replace("trued faces of the bars", "planed faces of the bars")
        for st in S[n0:]:
            st["text"] = [sub(t) for t in st["text"]]; st["title"] = sub(st["title"])
            if st.get("dont"): st["dont"] = sub(st["dont"])
        return
    sh = plan["shop"]; T = plan["board"]["thickness"]; cut = plan["slice_cut"]; kind = plan["info"]["kind"]
    rows = plan["rows"]; planks = plan["planks"]; skim = sh["true_skim"]; sk = f"{skim:.2f}\""
    nrow = len(rows); npl = sum(pl["count"] for pl in planks); tri = kind == "tri"
    rowh = max(pl["height"] for pl in planks); wide = max(pl["width"] for pl in planks)
    flips = any(pk["flip"] for pl in planks for pk in pl["pucks"])
    split = wide > sh["planer_width"] + 1e-6; big = max(planks, key=lambda p_: p_["width"]); n1 = (big["n"] + 1) // 2; n2 = big["n"] - n1
    hw_ = (lambda k: big["width"] * (k + 1) / (big["n"] + 1)) if tri else (lambda k: big["width"] * k / big["n"])
    hw = hw_
    if tri and n1 % 2 and hw(n1 + 1) <= sh["planer_width"]: n1 += 1; n2 -= 1      # whole pairs in the first half
    def seq(a, k):
        pr = k // 2; one = k % 2
        t = f"logs {a} to {a + k - 1}: " + (f"{pr} pairs" if pr > 1 else "1 pair") + (", then pairs joined two at a time" if pr > 1 else "") + (f", and log {a + k - 1} added last as a single" if one else "")
        return t
    halves_txt = f"{n1} logs, about {short(hw(n1))} wide, and {n2} logs, about {short(hw(n2))} wide"
    sect = ((f"For this plank, counting logs from the left of the sheet 05 drawing: half 1 is {seq(1, n1)}; half 2 is {seq(n1 + 1, n2)}. " if split else f"For this plank, counting from the left of the sheet 05 drawing: {seq(1, big['n'])}. ") + "A section with an even count of logs is a parallelogram and takes one strip each way, like a pair. A section with an odd count has both outside faces leaning the same way: both strips bevel down if its outside logs are point up, both bevel up if they are point down.") if tri else ""
    def of(pl):
        rs = [u["row"] for u in pl["uses"]]
        return (f"Plank {pl['id']}: make {pl['count']}, {dim(pl['length'])} long, {pl['n']} logs across and {short(pl['width'])} wide, for row" + ("s " if len(rs) > 1 else " ") + _join(str(r) for r in rs) + ".")
    tx = [f"A plank is one row of the board made long. The logs lie side by side, long grain to long grain, and every crosscut of the plank is a whole row, so no row is put together from loose slices. "
          f"This board takes {npl}. " + " ".join(of(pl) for pl in planks),
          "Why planks pay here: " + " ".join(f"{pl['id']}: {pl['why']}" for pl in planks),
          "Sheet 05 draws the end of each plank as you see it from the marked ends of the logs: which log lies where, which way up, and where its reference face is (the short heavy line). "
          + ("A letter with a prime (A′) is a log turned end for end, its marked end at the far end of the plank. " if flips else "Every log has its marked end at the same end of the plank. ")
          + "Lay each plank out dry on the taped base and look at its end against the drawing before any glue goes on.",
          "The glue faces are the trued faces of the logs. Roll a thin coat on one face of each joint."]
    if tri:
        tx += ["Glue the logs in pairs first: one point down, one point up, one joint. A pair is a parallelogram, so its two outside faces lean the same way: one edge strip goes bevel down against the face that leans out over the base, the other bevel up under the face that overhangs, both taped. "
               "The joint leans at 60 degrees to the clamps, so part of the clamp force tries to slide one log up the other, and a bevel-down strip tries to climb. Stop both before any clamp goes across: clamp the bevel-down strip to the base at each end, and clamp a caul down across the top every 6 inches, snug, bearing on the logs and on both strips (the strips are the same thickness as the logs for this reason). Then clamp across the strips every 6 inches, through the middle of the logs' height, with moderate pressure. Do the first pair dry, with no glue, and look: corners of the logs meeting at both ends, no step along the top, strips lying still. This plank stage is the plan's own, so that dry clamp-up is the test of it. Forty-five minutes a pair in clamps.",
               "Then glue pairs into fours and fours together the same way, one joint at a time: edge strips as the outside faces need them, cauls snug first, then clamps across. " + sect]
    elif kind == "bars":
        tx += ["Glue in sections of three or four bars. Lay them on the base in the order drawn, each with its pencil line where sheet 05 shows it, clamp across every 6 inches with moderate pressure, then clamp two taped cauls down across the top, to the base, so no bar rides up. "
               "The bars are square, so they clamp like any panel. Before tightening, sight across both ends: the stripes of one bar must meet the stripes of the next where the drawing shows them meeting, and the marked ends must be flush.",
               "Then glue the sections to each other the same way until the plank is whole."]
    else:
        tx += ["Glue in sections of three or four logs. Lay them on the base in the order drawn, clamp across every 6 inches with moderate pressure, then clamp two taped cauls down across the top, to the base, so no log rides up. "
               "Line up the star points at both ends before tightening.",
               "Then glue the sections to each other the same way until the plank is whole."]
    if split:
        tx.append(f"The plank is {short(wide)} wide, wider than a {short(sh['planer_width'])} planer, so it is built as two half planks ({halves_txt}). Leave the halves overnight, then true each half in the next step, both at the same planer setting, so they are the same thickness. They are joined at the end of that step, after planing.")
        join_tx = ("Joining the halves. " + ("Then glue the two halves together on the flat base like a panel: clamps across, with a caul clamped down each side of the joint and across it at both ends, so the planed faces stay in one plane. " if kind == "bars" else "Run the two gluing edge strips through the planer with the halves at that same last setting, so strips and halves are one thickness and the cauls bear on all of them. Then glue the two halves together on the flat base, an edge strip against each outside face as before, the bevel-down strip clamped to the base, with a caul clamped down each side of the joint and across it at both ends, so the planed faces stay in one plane. ") +
                  "Check the joint on both faces with a straightedge. Planed halves glued on a flat base should show no step, and then the faces are finished. If there is a step, take it out with the router sled that flattens the board (or a drum sander wide enough for the plank), the lightest pass that clears pencil scribble from both sides of the joint; re-measure the plank and use that thickness for every plank.")
    S.append({"title": "Glue the logs into planks", "text": tx, "figs": (["pair"] if kind == "tri" else []) + [f"plank_{pl['id']}" for pl in planks[:1]], "see": ["layout"], "glue": True,
              "dont": "glue a whole plank in one go. More than three joints open at once slide on the glue before the clamps are on."})

    tx = ["Scrape the glue from both wide faces. These two faces are the glue faces between the rows of the board, so both get machined.",
          f"Scribble pencil across a face and pass the plank through the planer or under the drum sander, light passes, until the scribble just goes: about {sk}. Turn it over and do the other face. "
          "A plank is long grain from end to end, so the planer is safe here; feed it with the grain of most logs and take 1/64\" or less a pass.",
          (f"The plank starts at the size the bars were cut, {dim(rowh + 1 / 32)}. Plane the first-cut faces of the bars until the knifed glue line reaches the corner at the bar ends, then take the rest off the other face. " if kind == "bars" else f"The plank starts about {dim(rowh + 2 * skim)} thick. ") + f"Finish every plank at the same machine setting, so every row comes out the same width: about {dim(rowh)}."]
    if any(pl["rows_cut"] * plan["slice_cut"] < sh["planer_min_length"] - 4 for pl in planks):
        tx.append(f"Every plank is at least {short(sh['planer_min_length'])} long, longer than its rows need, because a planer cannot feed a shorter piece safely: the rollers lose it between them. The extra length is the price of planing the plank safely; it is waste or spare rows, and the material list counts it.")
    if any(pl["width"] > sh["planer_width"] for pl in planks):
        tx.insert(0, "A plank built as two halves: true both halves here first, at one setting, then glue the halves together as step " + str(len(S)) + " describes and check the joint with a straightedge. The order is halves glued, halves trued, halves joined, joint checked.")
    if split: tx.append(join_tx)
    S.append({"title": "True the planks", "text": tx, "figs": [], "see": [],
              "dont": "leave one plank a pass thicker than the others. Rows of different widths walk the pattern out of line across the board."})

    edge = ("Lay the plank flat on the sled, the face that was up in the glue-up still up, marked ends of the logs to your left, away from the stop. Stand at the marked ends and look at the end of the plank: you see the sheet 05 drawing the right way up, with the sled fence on your right. So the edge where the red arrow starts on sheet 05 (the left of the drawing) is the edge away from the fence. One edge strip is screwed to the sled fence as a fixed face, with screws on both sides of the blade line, turned bevel down or bevel up to suit the plank edge that meets it, and that edge bears on it bevel to bevel; the blade cuts through the strip on the first pass and the strip stays put, so nothing loose is ever beside the blade. " if tri
            else "Lay the plank flat on the sled, the face that was up in the glue-up still up, marked ends of the logs to your left, away from the stop. Stand at the marked ends and look at the end of the plank: you see the sheet 05 drawing the right way up, with the sled fence on your right. So the edge where the red arrow starts on sheet 05 (the left of the drawing) is the edge away from the fence. ")
    nr = sum(pl["rows_cut"] + pl["spares"] for pl in planks)
    tx = [edge + "Clamp it down with the hold-down. Square the end nearest the stop (the unmarked end) first, taking only what cleans it.",
          f"Set the stop block {dim(cut + 1.0)} from the blade and use the 1\" spacer: slide the plank up to the spacer, clamp the plank, take the spacer away, then cut. "
          f"The row comes off {dim(cut)} thick (finished {short(T)} plus {short(sh['flatten_allowance'])} to flatten) with an inch of room beside it, so it cannot bind between blade and stop.",
          f"Cut {nr} rows in all: " + ", ".join(f"{pl['rows_cut']} + {pl['spares']} spare from plank {pl['id']}" for pl in planks) + ". "
          "As each row comes off, turn up the face that was toward the blade and pencil an arrow on it, starting at the end that was away from the fence and pointing along the row toward the fence end, with the plank's number beside it. "
          "Sheet 05 draws that arrow on every row, so you lay each row with its arrow pointing the way the drawing shows" + (": solid when the arrow is face up, dashed when the row is turned over." if any(r.get("op") in ("m", "f") for r in rows) else "."),
          "Hold the row down on the sled base with a push stick as the blade comes through, hand well clear. Push the sled on until the row is past the blade, stop, and lift the row away before pulling the sled back.",
          f"The last {short(sh['hold_end'])} of each plank is the part the clamp holds. It is never cut into rows: stop there."]
    S.append({"title": "Crosscut the planks into rows", "text": tx, "figs": ["cut_plank"], "see": [],
              "dont": "cut a row against a fixed stop with no spacer, or cut into the last 2 inches of a plank. A trapped row is thrown; a short stub cannot be held."})

    turned = sorted({r["op"] for r in rows if r.get("op")})
    tx = [f"Lay the {nrow} rows out dry in the order on sheet 05, each with its pencil arrow pointing the way its red arrow is drawn. "
          + ("The table on sheet 05 says which rows go in as cut and which are " + _join(PK.OP_TEXT[o] for o in turned) + ". " if turned else "Every row goes in as cut, number at the same side. ")
          + (lambda lv_: "Every row lies with its ends level with row 1: there is no slide on this board. Check that the corners of the logs meet corner to corner along the whole joint, as drawn. Truing" if lv_ else "Slide each row along its neighbour until the corners of the logs meet corner to corner along the whole joint, as drawn. The table on sheet 05 gives the slide as a figure: how far, and which way, the end of each row sits from the end of row 1. The figure is the starting point and the eye governs: truing")(_rows_level(plan, rows)) + "  took a few thousandths off every log, so points and strand edges land within about 1/64\" rather than dead on; split any difference evenly along the joint. Then draw a pencil line across every joint so the rows go back in register under glue.",
          "Glue two or three rows at a time, then glue those sections together. Clamp across the rows every 4 to 5 inches with moderate pressure, "
          "with taped cauls clamped across the top and bottom near each end, inside the ragged ends, to keep the rows in one plane.",
          "Before any glue, take the saw fuzz off the sawn arrises of each row with one stroke of 220 paper on a block, and clamp a scrap block to the bench against the end of the first row so nothing can creep lengthwise.",
          "The faces being glued are the machined faces of the planks, long grain: one thin rolled coat on one face of each joint. "
          "The pencil lines hold the register: check them after the clamps are on and tap a row back if it has crept.",
          "Scrape the squeeze-out when rubbery. Leave the board in clamps overnight and out of clamps a day before flattening."]
    S.append({"title": "Glue the rows into the board", "text": tx, "figs": ["board"], "see": ["layout"], "glue": True,
              "dont": "glue every row at once. More than three joints open at a time creep out of plane and out of register before the clamps are on."})


def steps(plan, design):
    sh = plan["shop"]; T = plan["board"]["thickness"]; cut = plan["slice_cut"]; kind = plan["info"]["kind"]
    logs = plan["logs"]; rows = plan["rows"]; skim = sh["true_skim"]; byid = {lg["id"]: lg for lg in logs}
    sk = f"{skim:.2f}\""
    S = []
    woods = ", ".join(w["name"] for w in plan["woods"])
    S.append({"title": "Buy and acclimate the lumber", "figs": [], "see": ["materials"],
              "text": [f"Buy the boards in the material list ({woods}) and let them sit in the shop for a week, stickered.",
                       "Pick straight-grained stock, quartersawn or rift where you can: it moves less and the end grain shows tight, even rings."]})

    if kind == "bars":
        _bar_steps(S, plan); _plank_steps(S, plan)
        return _finish_steps(S, plan)
    # ---- jigs first: the bars are trued in them
    sliced = [lg for lg in logs if lg["crosscut"]]
    rowh = max(r["height"] for r in rows); rowl = max(r["length"] for r in rows)
    planks = plan.get("planks") or []
    plw = max((pl["width"] for pl in planks), default=0); pll = max((pl["length"] for pl in planks), default=0)
    jig = []
    tl = sorted({round(bt["tilt"], 1) for bt in plan["bar_types"] if bt.get("tilt") and bt.get("setup") in ("para", "trap", "flip")})
    has_tri = any(bt.get("setup") == "flip" for bt in plan["bar_types"])
    halves = [pk for r in rows for pk in r["pucks"] if pk.get("half")]; npuck = sum(len(r["pucks"]) for r in rows)
    if any(bt.get("kind") in ("parallelogram", "rhombus", "diamond") or "parallelogram" in bt.get("label", "") or "diamond" in bt.get("label", "") for bt in plan["bar_types"]) and kind == "tri":
        jig_carrier = ("Bar carrier, for the parallelogram and diamond bars: a flat board of 3/4\" MDF, as long as the bars plus 4\", with two straight fences screwed to it a little lower than the bars. "
                       f"Rip the inside edge of each fence at {tl[0] if tl else 30:g} degrees from vertical so it leans the way the bars lean: the first bar lies against one fence, the rest lean on it like roof tiles, and the second fence is pushed up to the last bar and screwed down so nothing can tip. Screw a stop across the end that goes into the machine last.")
    else: jig_carrier = None
    if tl:
        Ls = math.ceil(max(bl["blank_length"] for b in plan["bars"] for bl in b["lengths"]) + 8)
        dkw = math.ceil(sh["stock_width"] + 5 + 0.75 + 0.5) if has_tri else 9      # fence deck: blank and spacers (together one blank wide), the 5" carriage, the back rail
        jig += [f"Rip sled: for every bevelled bar. It is the sliding rip jig with toggle clamps from the best practices guide. Start with a base of {short(sh['sled_base'])} plywood about {Ls}\" x {dkw + 7}\", one long edge straight to run against the rip fence. "
                "Glue and screw a bridge of 3/4\" x 4\" hardwood, standing on edge, across each end. Tilt the blade to " + " or ".join(f"{t:g}" for t in tl) + " degrees, raise it fully, set the rip fence " + str(dkw) + "\" from it and push the sled through: "
                "the blade saws the base into two decks and notches both bridges, which are tall enough to stay whole above the cut and hold the decks together."
                + (" Make one sled for each tilt." if len(tl) > 1 else ""),
                f"Fence deck: the {dkw}\" deck beside the rip fence" + (f" ({dkw}\" because it has to hold the back rail, the spacers, the 5\" carriage and a {short(sh['stock_width'])} blank at once)." if has_tri else ".") + " The locating fence is a straight strip, 3/4\" x 1-1/2\", screwed along the front edge of a clamp board (3/4\" plywood about 5\" wide, 1\" shorter than the space between the bridges) that carries three toggle clamps. Fence and clamps are one carriage: it lies flat on the deck parallel to the cut and is held by two 1/4\" carriage bolts, one near each end, that come up through the deck (heads counterbored flush underneath so the sled still slides) and through slots cut across the clamp board, with a washer and wing nut on top. Cut a row of bolt holes in the deck about 2\" apart across its width, so with the slots the carriage can be set anywhere on the deck for each bar shape, nudged by a tap and locked. For the first setting, tap it; for a change of a few thousandths, add a strip of masking tape to the face of the locating fence or to a spacer. For the bar rips set the blade one tooth higher than the work, not fully raised, "
                "and the pads always reach the same distance over the work. The pads close on a caul, a straight strip 1/2\" wide and 3/4\" high laid along the top of the work, so the pressure is spread and no pad is near the blade. Lay the caul over the part of the work that has deck under it, toward the locating fence, never out over a leaning edge. "
                ,
                ("Back rail, for triangle bars: a straight strip screwed along the rip-fence edge of the fence deck, parallel to the cut. The carriage is set off it with spacer strips that lie on the deck between the rail and the back edge of the clamp board (each bar card gives their width), one more for every bar cut, so the blank steps toward the blade by exactly one bar each pass. The rail is 3/4\" wide and the slots in the clamp board are as long as one blank's whole travel (the spacer width times the bars one blank gives, plus 1/2\"), so the bolts never have to move to other holes part way through a blank. The spacers only count from a fixed start. The start is the cut that takes the waste bevel off the edge of a fresh blank: when that position has been found by test cuts, fit a starter strip that just fills the gap between the rail and the back of the clamp board, and leave it there. Starter strip alone is the waste bevel; starter plus one spacer is bar 1; one more spacer for every bar after. If the bars come out wide or narrow, change the spacer width, not the start. Screw a small stop across the back end of both decks so neither the blank nor a freed bar can be pushed back along the sled, and switch off and let the blade stop before lifting a bar off the landing deck. "
                 "Landing deck: the other deck. Stick a strip of 120 grit sandpaper along it where the bars land, and fix nothing else to it: a freed bar must have open deck beside it. Leave the rip fence where it is for the whole run; every setting is made on the sled." if has_tri else
                 "Landing deck: the other deck. Only waste slivers land on it. Leave the rip fence where it is for the whole run; every setting is made on the sled.")]
    if kind == "tri":
        vb = plan["vblocks"]; longest = max(lg["length"] for lg in logs) + sh["glue_extra"]
        nlog_ = sum(lg.get("count", 1) for lg in logs if lg["kind"] == "tri"); nblk_ = min(6, max(2, math.ceil(nlog_ / 20)))
        njoint_ = sum(pl["count"] * (pl["n"] - 1) for pl in plan["planks"]); nstrip_ = min(4, max(2, math.ceil(njoint_ / 30)))
        thin = [v for v in vb if v["base"] < 0.5]; tallest = max(v["tall"] + v["base"] for v in vb)
        jig += ["V blocks: they hold every three-cornered part, for gluing and for truing. The sides of a block stop 3/16\" under the top of the part: high enough to bear on nearly the whole part, "
                "low enough that the top stands proud for the caul or the sander. A V has no size except the height of its sides, so the blocks are named by that. Make "
                + "; ".join(f"a {v['name']} ({v['mat']}; each side piece about {short(_up(v['hb'] / S3 + 1.5, 0.25))} wide), for {_join(v['uses'])}" for v in vb) + ".",
                "To make a V block: rip one edge of each side piece at 30 degrees from vertical, so the cut face leans back at 60 degrees. Glue and screw one side piece to a flat base ("
                + ("3/4\" MDF" if not thin else "3/4\" MDF, but 1/4\" hardboard for the " + _join(v["name"] for v in thin) + ", to keep the stack low under the sander") + "). "
                "Stand a 60 degree drafting triangle on its point against that face (or dry-fit three test bars) and slide the second side piece up until its sharp lower edge meets the first. "
                "Fix this second side with screws through slotted holes, so it can be slackened: for gluing it is left loose and a clamp across the block closes it on the parts; "
                "for truing it is screwed tight against the drafting triangle. The two faces form a 60 degree V with no gap at the bottom.",
                f"Machine height: under the drum sander or planer the tallest block and log stand {short(_up(tallest, 0.125))} high: check your machine opens that far before starting. If it does not, true those logs in the block with a jack plane.",
                f"Block length: make each gluing block 2\" longer than the longest part it holds (the longest part is {short(longest)}). Line its V with packing tape so glue lets go, and stand it on two battens when gluing so clamp jaws reach under the base. "
                f"Each log is an hour in the block. This board has {nlog_} logs, so with one block that is {nlog_} hours at the clamps: make {nblk_} gluing blocks of the largest size, which brings it to about {math.ceil(nlog_ / nblk_)} sessions of an hour. "
                f"Truing block: a separate block of each size, 6\" longer than the part, with its V lined with 120 grit paper instead of tape so the part cannot slip, and a stop screwed across each end, 1/4\" lower than the top of the part so the cutter clears it. The extra length holds a 3\" scrap of the same section in front of and behind the part, so planer snipe falls on the scrap; cut the scraps from the spare bars and from one extra log glued for the purpose, and count that log into the bars you rip. Under a drum sander the gluing block with one stop at the trailing end will do."]
        jig += [f"Plank base: a flat piece of melamine or waxed MDF about {math.ceil(plw + 8)}\" x {math.ceil(pll + 2)}\", for gluing the logs side by side into planks. Stand it on two battens so clamps reach under it.",
                f"Three edge strips: straight strips as long as the planks, as thick as the trued logs (about {short(rowh + 2 * sh['true_skim'])}; plane them to match a trued log) and 2\" wide on the wide face, with one edge ripped at 30 degrees from vertical (the V block setting). Make them of straight scrap or of MDF glued up to thickness. Like the V block sides they are jig parts, wide and flat, and are ripped the ordinary way: wide face down on the saw table, square edge against the rip fence, fence on the side the blade leans away from. The rule that every bevel is cut on the rip sled is for the bars. "
                + (f"The planks take {njoint_} glue-ups of 45 minutes, one joint at a time, and a pair of strips serves one glue-up: make {nstrip_} pairs of gluing strips and as many bases, or allow {math.ceil(njoint_ * 0.75)} hours at the clamps. " if njoint_ > 12 else "") +
                "The outside faces of a plank section lean at 60 degrees; a strip lies against each, bevel to bevel, turned bevel down or bevel up as the face leans, and gives the clamps a square face. Tape the bevels so they do not get glued in. "
                "The third strip is screwed to the crosscut sled's fence, on both sides of the blade line, as the fixed face the plank bears on at the crosscut.",
                "Four flat cauls: straight 2x2s with packing tape on one face, a little longer than the planks are wide, to hold the logs down flat on the base.",
                f"Crosscut sled: with a hold-down clamp, a stop block and a 1\" spacer. It must crosscut {short(_up(plw + 2.0, 0.5))}, the width of the widest plank plus the 2\" edge strip on its fence, and cut square: check it with a five-cut test before the first row. "
                + (f"The plank is {short(rowh)} thick: the sled's base must be {short(sh['sled_base'])} or thinner and the blade must rise {short(rowh + sh['sled_base'] + 0.0625)} above the table. Check your saw before buying wood. If it cannot, crosscut the rows on a band saw against a fence and true the two sawn faces of every row on the router sled, or make the pattern smaller. " if rowh + sh["sled_base"] > 2.5 else "")
                + "Put the hold-down over the middle of the plank, on the side of the blade away from the stop."]
    elif kind == "hex":
        bd_ = plan["board"]; gw = bd_["glued"][2] - bd_["glued"][0]; gl = bd_["glued"][3] - bd_["glued"][1]; lgh = sliced[0]
        jig += ["Sanding board: a flat offcut of MDF or melamine about 12\" x 18\" with a sheet of 120 grit paper stuck down with spray adhesive. The sides of the pucks are cleaned on it, and the sawn faces of the half pucks.",
                f"Glue-up base: a flat piece of melamine or MDF about {math.ceil(gw + 8)}\" x {math.ceil(gl + 8)}\", covered with packing tape so glue lets go. Stand it on two battens so the caul clamps can reach under it.",
                f"Frame boards: four straight boards of 1x3, the frame Tom Silva clamps round his pucks. Two are {math.ceil(gl + 4)}\" long for the long sides. Two are cut to {dim(gw - 0.125)}, a hair under the width of the glue-up, "
                "so they fit between the long boards and push on the two end rows. Tape the inside edges. They lie flat on the base, loose, round the pucks, and stand lower than the pucks. "
                "Bar clamps go over the top of the pucks with their jaws on the outside edges of the frame boards: three across the width, one along the length down the middle.",
                f"Two cauls: straight 2x2s with packing tape on one face, about {math.ceil(gl + 8)}\" long, to hold the pucks flat while the frame closes. They lie lengthwise on the pucks, one each side of the long clamp, and are clamped down to the base at their ends, beyond the frame.",
                f"Crosscut sled: with a hold-down clamp, a stop block and a 1\" spacer. Its base must be {short(sh['sled_base'])} or thinner: the log lies on one flat and stands {short(min(lgh['w'], lgh['h']))} tall on it, and the blade, fully raised, clears {short(sh['max_cut_height'])}. "
                "That leaves little to spare: measure your own blade's height above the sled base before the first cut. If it does not clear the log by 1/16\", cut the pucks on a miter saw instead, as Silva does: log clamped to the saw's fence, stop block set once, the same 1\" spacer."]
    elif kind == "blocks":
        hq = min(min(lg["w"], lg["h"]) for lg in logs if lg["shape"] == "quarter")
        jig += ["Band cradle: a flat base of 3/4\" MDF with packing tape on it, and a stop strip screwed along one side whose inner edge is ripped at 45 degrees so it leans over the work. "
                "The diamond bar's free bevel tucks under that edge. A straight loose caul on the other side takes the clamps, and a taped caul on top keeps the band flat (drawing on sheet 04).",
                f"Corner cauls: two L-shaped cauls, each two strips of 3/4\" plywood glued at exactly 90 degrees with inside legs {short(_up(hq - 0.375, 0.125))} wide, inside faces taped, as long as the logs. "
                "The legs are narrower than the log so the two cauls never touch each other before the log is tight.",
                f"Plank base: a flat piece of melamine or waxed MDF about {math.ceil(plw + 8)}\" x {math.ceil(pll + 2)}\", for gluing the logs side by side into planks. Stand it on two battens so clamps reach under it.",
                "Four flat cauls: straight 2x2s with packing tape on one face, a little longer than the planks are wide, to hold the logs down flat on the base.",
                f"Crosscut sled: with a hold-down clamp, a stop block and a 1\" spacer. It must crosscut {short(_up(plw + 0.5, 0.5))} or more (the widest plank is {short(plw)}), and cut square: check it with a five-cut test before the first row."]
    else:
        bd_ = plan["board"]; gw = bd_["glued"][2] - bd_["glued"][0]; gl = bd_["glued"][3] - bd_["glued"][1]
        jig += [f"Flat cauls: eight straight 2x2s (four pairs) with packing tape on one face, about {math.ceil(max(gw, gl) + 4)}\" long, so they overhang both the panels and the finished board and the clamps have something to bear on.",
                "Crosscut sled: with a hold-down clamp, a stop block and a 1\" spacer. Check it cuts square in both directions."]
    if jig_carrier: jig.insert(max(0, len(jig) - 2), jig_carrier)
    S.append({"title": "Make the jigs", "text": jig, "figs": (["ripsled"] if tl else []) + (["jigs"] if kind == "tri" else []), "see": []})

    thick = sorted({round(b["stock"], 4) for b in plan["bars"]})
    nsp = sum(b["total_spares"] for b in plan["bars"]); nb = sum(b["total_bars"] for b in plan["bars"])
    tx = [f"Joint one face and one edge of every blank, then plane to thickness: {', '.join(dim(t) for t in thick)} "
          f"(material list, sheet 02). Set the planer with calipers, not a tape, and plane every blank of one thickness in the same session without moving the planer between them.",
          ("Rip each blank full length into the strips sheet 02 lists for it, then crosscut every strip to its length in the cut list. Sheet 03 sets out the rip and the truing, and draws the saw " if kind == "panel" else "Crosscut the blanks to the lengths in the cut list. Then rip and true each bar shape as set out on sheet 03, which draws the saw ") + ("and the rip sled from the front for every bevelled bar. " if any(bt.get("tilt") for bt in plan["bar_types"]) else "from the front for each strip. ")
          + "Bars are ripped a little over and then machined to size, so the saw only has to be close.",
          ("Test the setup on scrap first: rip three short bars, true them, and tape them into a hexagon. The three must meet at the centre with no gap, and no light may show at the three outer joints. "
           "Silva and Dillen both tune the saw this way, by test cuts, until three pieces close. A quarter of a degree of bevel error leaves the hexagon three quarters of a degree short of closing; fix the tilt before cutting good wood." if kind == "hex" else
           "Test each setup on scrap first: rip three short bars, true them, and dry-fit them" + (" in their V block" if kind == "tri" else " against a square") + ". "
           "Half a degree of bevel error shows as a gap you can slip paper into; fix the tilt before cutting good wood."),
          f"The cut list has {nb} bars plus {nsp} spares (one in ten, and at least one of every bar in every wood). Rip every bar of a shape in one run, spares included, "
          f"then check a handful with calipers: all within {short(1 / 64)}" + (" off the saw, and within a few thousandths of each other after the last planer pass." if kind == "panel" else ".")]
    if kind == "hex":
        tx.append("Cut and true every diamond bar of all three woods in one session, at one saw setting and one planer setting. A hexagon log is never machined after it is glued, so the bars are the only place the fit is made. "
                  "The maker lanwater ran short, cut a second batch at a new setup, and it did not match the first; that came back in the glue-up.")
    S.append({"title": "Mill the blanks and rip the bars", "text": tx, "figs": [], "see": ["bars"],
              "dont": ("rip a bevel with the work loose on the saw table, or with a bar between the tilted blade and the fence. Every bevel is cut with the work clamped to the rip sled."
                      + (f" Stop when a triangle blank is narrower than {short(sh['blank_remainder'])}; that last strip is waste." if has_tri else "")) if any(bt.get("tilt") for bt in plan["bar_types"]) else
                      "rip a strip narrower than the gap between blade and fence without a push block, or change the fence between strips of one width. Every strip of a width comes off one setting."})

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
            sl = "" if planks else f", for {lg['slices']} slices plus {lg['spares']} spare" if lg["crosscut"] else ""
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
                      "That end is the marked end and that face is the reference face. Leave the ends of the log as they are: the plank's end is squared once, at the crosscut.")
            dont = "put more than four parts in one glue-up or skip the dry fit. Parts slide on wet glue; a stack that rocks dry will cure crooked."
        elif main["kind"] == "hex":
            names = [plan_name(plan, p["wood"]).split()[-1].lower() for p in main["stages"][0]["parts"]]
            tx += [f"Dry-fit first, with no glue: hold the three bars together so their wide corners meet at the centre, and look at the end. Mark one end of every bar before you start and keep the marked ends together. "
                   f"Seen from the marked end, every log has the same wood in the same place as on sheet 04: {names[0]} at the top, {names[1]} and {names[2]} below it. A log built the other way round has its cubes lit from the other side.",
                   "Roll a thin, even coat of Titebond III on one face of each of the three joints. Bring the bars together and wrap painter's tape tightly round the bundle every 3 inches along its length, as Silva does; "
                   "thick rubber bands or band clamps do the same job. Tape pulls evenly toward the centre, where a bar clamp would make the bevels slide.",
                   "Check both ends before the glue grabs: three joints meeting at one point in the centre, the six outside corners sharp, nothing slid along its length. Wipe the squeeze-out and lay the log on a flat taped surface so it cures straight.",
                   "Glue the three spare bars into one more log in the same session: it replaces a log that measures out in the next step, and gives spare pucks. Silva unwraps after 30 minutes. Leave the logs overnight before sawing them. " + END]
            dont = "clamp a hexagon bundle with bar clamps. Bevelled faces slide under a clamp; tape or bands pull every joint closed at once."
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
                   "clamp across the panel every 6 inches with a pair of cauls, one above and one below, clamped near each end to keep it flat. Squiggled faces up and down, planed edges to the glue.",
                   "Glue one panel at a time unless you have clamps and cauls for two.",
                   "Scrape when rubbery; leave overnight."]
        S.append({"title": f"Glue the {what}s", "text": tx, "figs": [f"log_{lg['id']}" for lg in here if not (len(lg['stages']) == 1 and len(lg['stages'][0]['parts']) == 1)][:3],
                  "see": ["logs"], "glue": True, **({"dont": dont} if dont else {})})

        # true them
        if main["kind"] == "tri":
            g_, t_ = main["glued"], main["trued"]; vbk = _vb(plan, main["w"], main["h"])
            tx = [f"Every face of a log is a glue face later, so every face gets machined. Scribble pencil across the top face, set the log in the {vbk['name']} (second side screwed tight) and run it through the "
                  f"drum sander with 80 or 100 grit until the scribble just disappears; turn the log and do the other two faces.",
                  "No drum sander: a thickness planer can do this job, because these faces are long grain. The makers in the guide plane long-grain stock but sand their triangle logs, so carrying the V block through the planer is this plan's adaptation: glue one extra log from the spare bars and prove it on that first. Use the truing block from step 2: sandpaper-lined V, a stop at each end below the top of the log, a 3\" scrap of the same section in front of and behind the log so planer snipe falls on the scrap. Passes of 1/64\" or less. The other route with no drum sander is the router sled that flattens the board, run over the log in the same block clamped to the bench, passes of 1/32\" or less; it is slower but nothing is fed through rollers. "
                  " A helical head leaves the cleanest face; with straight knives feed so the grain runs downhill. "
                  "With neither machine, clamp the block in the vise and use a jack plane and a straightedge.",
                  f"Work in rounds: every log through with its first face up at one drum setting, then every log with its second face up, then the third. "
                  f"The log sits a hair lower once a sanded face is against the block, so lower the drum by that hair at the start of each round until it just takes the pencil off; what matters is that every log gets the same setting in each round. "
                  f"That takes about {sk} off a face: the logs glue up {dim(g_)} on a side and finish about {dim(t_)}. "
                  f"The exact figure does not matter; that all the logs match within a few thousandths does. Sizes from here on are these finished sizes.",
                  "Check each log: the 60 degree triangle fits every corner, a straightedge shows no light along any face, and calipers read the same at both ends."]
        elif main["kind"] == "hex":
            tx = ["Scrape the dried glue off all six faces with a card scraper. The makers who build this way do not machine the log: its six faces are the planed faces of the bars. If you have a drum sander, one very light pass over each of the three pairs of flats, every log at the same setting, is this plan's own optional addition; no published build does it, so skip it if the logs already measure alike.",
                  f"Check each log with calipers across all three pairs of flats, at both ends. Every reading should be {dim(min(main['w'], main['h']))} and the logs should match each other within a few thousandths. "
                  "A log that is out is set aside, and the spare log takes its place: its pucks would hold their neighbours apart.",
                  "This is the known weak point of the method. Nothing is machined between this glue-up and the board, so any error in the bars arrives at the board. Silva's own build ends by filling small gaps, and this plan keeps that step."]
        elif main["shape"] == "band":
            tx = [f"Plane both broad faces of each band, equal cuts from each face, all bands at one planer setting, down to {dim(main['trued'][1])} thick. "
                  "The sawn faces of the bars carried the allowance for this. A band has one bevelled edge that ends in a feather. Nest the bands in pairs: lay one wide face down and roll its partner over, wide face up, the same end leading, "
                  "so the two bevels lap and the pair is a rectangle. Lay the pair on a flat carrier board between two straight rails screwed down a snug fit apart and lower than the bands, and tape across both ends: "
                  "the rails stop the lapped bevels from wedging apart under the feed rollers, the pair goes through as a rectangle, and no thin edge leads into the knives. Turn the pair over as one to plane the other faces.",
                  f"Then bring every band to width at one setting, working from its solid edge. First take one light jointer pass on the square edge (the triangle bar's outer face) to clean it. "
                  f"Then put the band on the rip sled with the blade still at 45 degrees: wide face up under the caul, the jointed square edge against the locating fence, and skim the bevelled edge so the wide face measures {dim(main['trued'][0])}. "
                  f"Set the locating fence once with a test band and run all the bands at that setting. The skim also leaves the bevel, which is the next glue face, freshly cut. "
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
                tx.append(f"Plane the border bar ({bl['name']}) to the same width as the block logs at the same planer setting ({dim(tw[1])}), so it sits level with them in the plank.")
        elif main["kind"] == "rect":
            tx = [f"Joint one face of each log, joint an adjacent face square to it, then plane the other two faces parallel: every log through the planer at one setting, about {sk} a face."]
        else:
            tx = ["Plane both faces of each panel clean and parallel, all panels at one planer setting. These faces are the glue faces of the board. "
                  f"The strips were milled 1/8\" over for this: take about half of it off each face and bring the panels to {dim(main['h'])} thick. Set the planer with calipers on the panel.",
                  f"The panels are {short(max(lg['w'] for lg in here))} wide" + (f", which a {short(sh['planer_width'])} planer takes." if max(lg['w'] for lg in here) <= sh['planer_width'] else f", wider than a {short(sh['planer_width'])} planer: glue each panel as two halves, plane the halves at one setting, then glue the halves together on a flat base and skim both faces on the router sled.")]
            if main.get("graded"):
                tx = [f"Plane both faces of the panel clean and parallel and bring it to {dim(main['h'])}, the first and thickest setting. These faces are the glue faces of the board. The next step takes it thinner two slices at a time."]
        S.append({"title": f"Clean and check the {what}s" if main["kind"] == "hex" else f"True the {what}s", "text": tx, "figs": ["true"] if main["kind"] == "tri" and lv == levels[0] else [], "see": [],
                  "dont": "leave dried glue on a face. A bead a few thousandths high holds the next joint open." if main["kind"] == "hex" else
                          "leave a glue face as it came out of the clamps. Dried glue and a part standing a few thousandths proud hold the next joint open."})

    if planks:
        _plank_steps(S, plan)
    else:
        # crosscut
        ns = sum(lg["slices"] + lg["spares"] for lg in sliced)
        lay = ("Lay the log in the sled cradle on its reference face, marked end away from the stop. Push the second strip hard against the log and put two bar clamps across the sled fence and that strip, both on the side of the blade away from the stop (clamp jaws cannot reach under a sled, so the clamps squeeze fence, log and strip together above the base): the log is pinched between the two strips. Add a hold-down on the sled fence (a toggle clamp or a hand screw) pressing on the log's top edge through a scrap, so neither the log nor the loose strip can ride up. To move the log on, slacken one clamp, slide the log, tighten." if kind == "tri"
               else "Lay the log on one flat with a corner touching the sled fence, marked end away from the stop, and clamp it down with the hold-down on its top flat. The squaring cut was made after the glue-up; repeat it only if the end is not clean." if kind == "hex"
               else "Lay the log on its chalked face against the sled fence, marked end away from the stop, and clamp it down." if kind == "blocks"
               else "Lay the panel against the sled fence and clamp it down.")
        graded = next((lg for lg in sliced if lg.get("grades")), None)
        if graded:
            gr = graded["grades"]; last = graded["length"] - (len(rows) - len(gr[-1]["rows"])) * (cut + sh["kerf"])
            tx = [f"One panel makes every row. It starts at {dim(gr[0]['thick'])} and is planed thinner before each set of slices, {len(gr)} settings in all, thickest first. "
                  f"Plane both faces a little at each setting so the panel stays flat, and set the planer with calipers on the panel, not by the scale.",
                  "Settings and the rows cut at each: " + "; ".join(f"{dim(g['thick'])} for rows {_join(str(n) for n in g['rows'])}" for g in gr) + ".",
                  f"At each setting: plane, square the end if it is not clean, then crosscut one slice for each row listed. {lay} "
                  f"Set the stop block {dim(cut + 1.0)} from the blade and use the 1\" spacer: slide the panel up to the spacer, clamp it, take the spacer away, then cut. Each slice comes off {dim(cut)} long (finished {short(T)} plus {short(sh['flatten_allowance'])} to flatten).",
                  "Pencil its row number on the end grain of each slice as it comes off and stack them in order. Slices of neighbouring settings differ by as little as 1/32\" and cannot be told apart later.",
                  f"The panel is made {dim(graded['length'])} long so it is still about {short(last)} long at the last planer setting; most planers need 12\" to 14\". There are no spare slices, so cut slowly and measure every setting.",
                  "Hold the slice down on the sled base with a push stick as the blade comes through, hand well clear. Push the sled on until the slice is past the blade, stop, and lift the slice away before pulling the sled back."]
            S.append({"title": "Plane and crosscut, thickest first", "text": tx, "figs": ["cut_setup", "asm_cut"], "see": [],
                      "dont": "plane the panel once it is shorter than your planer's minimum length, or cut a slice against a fixed stop with no spacer."})
        else:
            tx = [f"Square the unmarked end of each log first. {lay}" if kind != "panel" else f"Square one end of each panel first. {lay}",
                  f"Set the stop block {dim(cut + 1.0)} from the blade and use the 1\" spacer: slide the {'panel' if kind == 'panel' else 'log'} up to the spacer, clamp it, take the spacer away, then cut. "
                  f"The slice comes off {dim(cut)} thick (finished {short(T)} plus {short(sh['flatten_allowance'])} to flatten) with an inch of room beside it, so it cannot bind between blade and stop.",
                  f"Cut {ns} slices in all" + ": " + ", ".join(f"{lg['slices']} + {lg['spares']} spare from {'panel' if kind == 'panel' else 'log'} {lg['id']}" for lg in sliced) + ". "
                  + ("As each slice comes off, turn up the face that was toward the blade and pencil an X on it. Every puck goes into the board X up, so every cube is lit from the same side." if kind == "hex" else
                     "As each slice comes off, turn up the face that was toward the blade and pencil a short line on it along the edge that lay on the sled. "
                     "That line is the mark sheet 05 draws inside every slice. Stack the slices by letter." if kind != "panel" else "Pencil the panel letter on the end grain of each slice and keep two stacks."),
                  "Hold the slice down on the sled base with a push stick as the blade comes through, hand well clear. Push the sled on until the slice is past the blade, "
                  "stop, and lift the slice away before pulling the sled back.",
                  f"The last {short(sh['hold_end'])} of each {'panel' if kind == 'panel' else 'log'} is the part the clamp holds. It is never sliced: stop there. Lengths carry {short(sh['length_slack'])} of slack for a second squaring cut."]
            S.append({"title": "Crosscut the slices", "text": tx, "figs": ["cut_setup", "asm_cut"], "see": [],
                      "dont": "cut a slice against a fixed stop with no spacer, or slice into the last 2 inches of a log. A trapped slice is thrown; a short stub cannot be held."})

        if kind == "hex":
            nrow = len(rows); nh = len(halves); nr_ = sum(1 for pk in halves if pk["half"] == "right"); lgh = sliced[0]
            names = [plan_name(plan, p["wood"]).split()[-1].lower() for p in lgh["stages"][0]["parts"]]
            tx = ["Sand the sides of each puck lightly with 120 grit, as Silva does: stand the puck on one side on the sanding board and take two or three light strokes, then the next side, the same count on all six. "
                  "This takes off saw fuzz and any glue. It must not change the shape, so keep the puck flat on the board and stop as soon as the side is clean.",
                  f"Set aside {nh} good pucks for the half pucks along the two long edges (sheet 05 marks them with a half sign). Saw each one in two from point to point: the cut starts at the outer corner of the {names[0]} diamond, "
                  f"passes through the centre and runs out along the joint between the {names[1]} and the {names[2]}. Stand the puck on one flat on the band saw table, clamped in a wooden hand screw so fingers stay away from the blade, and saw just on the waste side of the line. "
                  f"Keep the half with the {names[2]} for {nr_} of them and the half with the {names[1]} for the other {nh - nr_}: sheet 05 shows which edge each goes on. Then rub the sawn face on the sanding board until the half measures {dim(lgh['w'] / 2)} from sawn face to the opposite flat, never more: a half that is over holds the frame board off the whole pucks beside it."]
            S.append({"title": "Sand the pucks and make the half pucks", "text": tx, "figs": [], "see": ["layout"],
                      "dont": "sand a side until it looks perfect. Every stroke changes the hexagon; a few strokes clean it, a dozen make a gap."})
            tx = [f"Dry-lay the whole board on the taped base from sheet 05: {nrow} rows, {npuck - nh} whole pucks and {nh} halves, every puck X up and turned so its {names[0]} diamond is at the top. "
                  "The half pucks go at the ends of every other row with their sawn faces outward, so both long sides are straight.",
                  "Close the four frame boards round the pucks and snug the clamps with no glue. Look at every joint. Swap or turn pucks until the layout closes, then pencil a number on each puck, row by row, and lift them off in order.",
                  f"Use a glue with a long open time: there are {npuck} pieces to place. Use Titebond II Extend, which Dillen chose for his board for this reason; ordinary Titebond III gives only about ten minutes. Work with a second person. "
                  "Working alone, glue the board in two sessions instead: glue the rows of one half, leave the other half in the frame dry as packing with a strip of packing tape on the joint between the halves, clamp, and glue the second half the next day. That split is this plan's suggestion, not Silva's; he glues every puck at once.",
                  "Start at the centre of the board and work outward, as Silva does: brush a thin coat on the sides of each puck that meet pucks already down, and press it home. Keep the coat thin. Too much glue holds the joints open.",
                  "Close the frame boards and bring up the clamps a little at a time, across the width and along the length in turn, until every board bears. The long boards push on the straight sides. "
                  "The end boards push on the points of the end rows, which seats each of those pucks into the V of the two behind it.",
                  "Before the clamps are tight, lay the two cauls lengthwise on the pucks, clamp their ends lightly down to the base, and tap any proud puck level with a mallet. Then tighten the frame clamps firmly, not hard, and wipe the squeeze-out.",
                  "Leave the board in the frame overnight and out of clamps a day before flattening."]
            S.append({"title": "Glue the pucks into the board", "text": tx, "figs": ["board"], "see": ["layout"], "glue": True,
                      "dont": "tighten one direction fully before the other. The honeycomb locks, and a puck that has not seated cannot move afterwards."})
        else:
            # rows
            nrow = len(rows); per = max(len(r["pucks"]) for r in rows)
            if kind == "panel":
                prime_ = any(pk.get("flip") for r in rows for pk in r["pucks"])
                tx = [f"The slices are the rows: {nrow} of them. Lay them out end grain up in the order on sheet 05"
                      + (", turning the ones marked with a prime end for end." if prime_ else ": slices of " + _join("panel " + lg["id"] for lg in sliced) + " take turns, and the first and last rows are both panel " + rows[0]["pucks"][0]["log"] + ". No slice is turned over or end for end.")
                      + " The faces that touch are the planed faces of the panels.",
                      "Look at the whole board before any glue goes on: squares line up down the length, and the corners match.",
                      "Take the saw fuzz off the sawn arrises of each slice with one stroke of 220 paper on a block."]
                if plan["info"].get("graded"):
                    tx += ["Each thickness was cut for rows on both sides of the middle. Every second row is turned end for end, which swaps the woods and makes the checker.",
                           f"The thinnest slices are {dim(min(r['height'] for r in rows))} thick and {dim(cut)} tall, so they tip. Glue the board in packs of five or six slices between taped cauls, with a square scrap block taped outside the first and last slice of a pack so the clamps bear on something that stands up, then glue the packs together."]
            else:
                tx = [f"Lay out the whole board dry on a flat surface from sheet 05: {nrow} rows of up to {per} slices. Each slice goes pencil line up, with the line on the edge where the drawing shows it. "
                      + ("A letter with a prime (A′) is turned over, line underneath; the drawing still shows which edge the line is on. " if any(pk.get("flip") for r in rows for pk in r["pucks"]) else "No slice in this board is turned over. ")
                      + "Look at the whole pattern before any glue goes on.",
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
            if kind == "panel":
                S.append({"title": "Lay out the slices", "text": tx, "figs": [], "see": ["layout"],
                          "dont": "spread glue before the whole board lies dry in order and the pattern looks right."})
            else:
                S.append({"title": "Glue the slices into rows", "text": tx, "figs": ["row"], "see": ["layout"], "glue": True,
                      "dont": "trust a row that rocks in the jig. A slice that sits proud of the fence line will hold the next row off; take it out and find out why."})
            brd = any(lg["shape"] == "border" for lg in logs)
            if kind != "panel":
                tx = ["Scrape the glue from each row. Its two long edges are the glue faces for the board, and every one of them gets machined.",
                      f"Stand the row on edge in the truing carrier, scribble pencil along the top edge, and pass it under the drum sander until the scribble just goes, about {sk}. "
                      f"Turn the row over and do the other edge. Every row gets the same passes at the same setting, so all " + ("star " if brd else "") + f"rows finish the same width, about {dim(max(r['height'] for r in rows))}"
                      + (f". The two border rows are slices glued end to end as well, so true their edges the same way in the low carrier; they finish about {dim(min(r['height'] for r in rows))} wide." if brd else "."),
                      "No drum sander: the guide keeps the planer for stock that is still long grain, and a row's edge is cut across the grain. The route that stays inside the guide is by hand: glue 80 grit paper to a flat board, hold the row against a square block, and take the same number of even strokes on every edge. A helical-head planer is this plan's adaptation, not the guide's, and the risk is a broken-out last slice: only with the row in the carrier, a scrap block of the same height taped tight behind the trailing end, passes of 1/64\" or less, and a test row first. Never with straight knives, never a row loose, and keep rows off the jointer."]
                S.append({"title": "True the rows", "text": tx, "figs": [], "see": []})

            tx = [f"Dry-fit the {nrow} rows in order" + (". Slide each row along its neighbour until the corners of the slices meet corner to corner along the whole joint, then draw a pencil line across every joint so the rows go back in register under glue."
                                                        if kind != "panel" else " and line up the squares along a straightedge clamped to the bench at one side, then draw a pencil line across every joint."),
                  (f"Glue three rows at a time ({nrow} rows make {nrow // 3} sections" + (f", the last of {3 + nrow % 3}" if nrow % 3 else "") + "), then glue the sections together. " if kind == "panel" and nrow >= 6 else "Glue two or three rows at a time, then glue those sections together. ")
                  + ("Put a taped scrap strip between the clamp jaws and the outside rows, so the jaws never mark the board. " if kind == "panel" else "")
                  + "Clamp across the rows every 4 to 5 inches with moderate pressure, "
                  + ("with a pair of taped cauls, one above and one below, clamped across the rows near each end to keep them in one plane." if kind == "panel" else "with taped cauls clamped across the top and bottom near each end, inside the ragged ends, to keep the rows in one plane."),
                  ("The faces being glued are long grain (the planed faces of the panels)" if kind == "panel" else "The faces being glued are long grain (the sides of the logs)") + ": one thin rolled coat on one face of each joint. "
                  "The pencil lines hold the register: check them after the clamps are on and tap a row back if it has crept.",
                  "Scrape the squeeze-out when rubbery. Leave the board in clamps overnight and out of clamps a day before flattening."]
            S.append({"title": "Glue the rows into the board", "text": tx, "figs": ["board"], "see": ["layout"], "glue": True,
                      "dont": "glue every row at once. More than three joints open at a time creep out of plane and out of register before the clamps are on."})

    return _finish_steps(S, plan)


def _square_marks(lg):
    """Where the glue lines lie on the slab's upper and lower sawn faces, measured from the first square cut.
    The slab lies with the sharp corner of its fence edge down on the table."""
    c = lg["cut"]; th = lg["theta"]; S_ = c["square"]
    if c["upright"]: top, bot = c["faces"][0], c["faces"][1]; low = th < 90
    else: top, bot = c["faces"][1], c["faces"][0]; low = th > 90
    f = (lambda ps: list(ps)) if low else (lambda ps: sorted(round(S_ - p, 4) for p in ps))
    return f(top), f(bot)


def _bar_steps(S, plan):
    """Layer boards -> sandwiches -> slabs -> bars. The planks, rows and board follow in _plank_steps."""
    sh = plan["shop"]; logs = plan["logs"]; kerf = sh["kerf"]; ov = sh.get("slab_oversize", 1 / 16)
    sws = [l for l in logs if l["shape"] == "sandwich"]; sbs = [l for l in logs if l["shape"] == "sbar"]
    cutb = [l for l in sbs if l.get("cut")]; solid = [l for l in sbs if not l.get("cut")]
    planks = plan["planks"]; plw = max(pl["width"] for pl in planks); pll = max(pl["length"] for pl in planks)
    B, H = plan["info"]["bar"], plan["info"]["row"]
    wn = lambda k: plan_name(plan, k).split()[-1].lower()
    tilts = sorted({l["tilt"] for l in sws if l["tilt"]}); maxh = max(l["h"] for l in sws) if sws else 0; maxw = max(l["w"] for l in sws) if sws else 0
    sl = max((l["length"] for l in sws), default=0)
    S.append({"title": "Make the jigs", "figs": [], "see": [], "text": [
        f"Flat cauls: eight straight 2x3s, jointed on one edge and taped on it, about {math.ceil(maxw + 4)}\" long, to clamp the sandwiches. Clamped in pairs, above and below, they keep the pressure even across the whole width. Eight make four pairs, enough for one sandwich: glue the sandwiches one at a time.",
        "Auxiliary rip fence: a straight board of 3/4\" plywood or MDF, 4\" high and as long as the rip fence, clamped to it with its lower edge tight on the saw table. "
        "The slabs have sharp edges; this fence leaves no gap for one to slide under.",
        f"Plank base: a flat piece of melamine or waxed MDF about {math.ceil(plw + 8)}\" x {math.ceil(pll + 2)}\", for gluing the bars side by side into planks. Stand it on two battens so clamps reach under it.",
        "Four more cauls: straight 2x2s with packing tape on one face, a little longer than the planks are wide, to hold the bars down flat on the base.",
        f"Crosscut sled: with a hold-down clamp, a stop block and a 1\" spacer. It must crosscut {short(_up(plw + 0.5, 0.5))} or more (the widest plank is {short(plw)}), and cut square: check it with a five-cut test before the first row.",
        "That is all. This build has no V blocks, no bevel sled and no edge strips: every part is a rectangle or lies on a flat sawn face."]})

    inner = sorted({round(t, 4) for l in sws for i, (_, _, t) in enumerate(l["stack"]) if 0 < i < len(l["stack"]) - 1 or not l["tilt"]})
    tx = ["Sheet 02 lists the boards and sheet 03 the layers, one card for each thickness. Joint one face and one edge of every board, then plane to thickness.",
          ("An inside layer shows on the face of the board at its full thickness, so its thickness is a pattern size: " + _join(dim(t) for t in inner) + ". Set the planer with calipers and plane every inside layer of one thickness, in every wood, at the same setting. " if inner else "")
          + "An outside layer is cut away at an angle by the squaring cuts, so its thickness is not a pattern size, but it does set where the squaring fence finds the glue line: plane every outside layer of one kind at one setting too, to the listed figure or a little over, never under.",
          "Where a layer is wider than one board, edge-glue boards to make it, then plane the panel. The joint is one wood glued to itself.",
          "Plane both faces of every layer fresh on the day it is glued. Cut the layers of one sandwich to the same length and width."]
    for l in solid:
        tx.append(f"{l['name']} is one solid wood ({wn(l['stages'][0]['parts'][0]['wood'])}), not a sandwich: rip and plane it to {dim(B)} x {dim(H + 1 / 32)}, the size the striped bars finish at. Make {_made(l)}.")
    S.append({"title": "Mill the layer boards", "text": tx, "figs": [], "see": ["materials", "bars"],
              "dont": "plane an inside layer by the tape measure. Its thickness is a stripe on the board; two layers a few thousandths apart show as a step in the pattern."})

    tx = ["A sandwich is the layers glued face to face, flat. " + " ".join(
            f"{l['name']}: " + ", ".join(f"{wn(w)} {short(t)}" for w, _, t in l["stack"]) + f" (bottom to top), {short(l['w'])} wide and {short(l['h'])} thick. Make {_made(l)}." for l in sws),
          "Roll a thin, even coat of Titebond III on one face of each joint. Stack the layers on two cauls, edges and ends flush, and rub each one down to grab.",
          "Clamp cauls in pairs, one above and one below, every 6 inches, snug in the middle first and then outward, with moderate pressure. Before the last turn, tap the layers flush at one long edge and check the ends: wet layers slide on each other. A brad in the waste at each end, within 1/4\" of the end, stops it.",
          "Scrape the squeeze-out when rubbery. A wide face-to-face joint dries slowly: leave each sandwich in its clamps overnight.",
          "When the glue has cured, crosscut both ends of every sandwich, taking the brads with them, to leave " + _join(f"{l['name']} {short(max((b['length'] for b in cutb if b.get('sandwich') == l['id']), default=l['length'] - 0.5))} long" for l in sws) + ". That is the length of the bars and of the plank; the layers were cut longer for this. Nothing with a brad in it goes near the rip blade or the planer. Then scrape the glue off both faces and lay a straightedge across each: the bottom face is what the tilted rip is measured from, so it must be flat and clean. If a face is cupped or the scraper leaves a bead, take one planer pass of 1/64\" or less off that face, the same on every sandwich; the outside layers carry 1/32\" for it and no more.",
          "Joint one long edge of each sandwich square to its faces: that edge runs against the rip fence. Scribble pencil across the whole of one end and write the sandwich's number on it; that is the marked end, and every slab and bar cut from it carries a piece of the scribble."]
    S.append({"title": "Glue the sandwiches", "text": tx, "figs": [f"log_{l['id']}" for l in sws][:3], "see": ["logs"], "glue": True,
              "dont": "glue more than three joints in one go. A tall wet stack skates out of line before the clamps are on; glue a sandwich of more than four layers in two sessions."})

    tx = []
    for l in sws:
        if l["tilt"]:
            pitch = (l["slab"] + ov + kerf) / math.cos(math.radians(l["tilt"]))
            tx.append(f"{l['name']}: blade tilted {l['tilt']:g} degrees from vertical, checked with a digital angle gauge and a test cut. Each slab is {dim(l['slab'] + ov)} thick, measured square across its sawn faces "
                      f"({short(ov)} over, for planing). The fence moves {dim(pitch)} toward the blade between cuts: rip {l['per'] + 1} gauge strips exactly that wide from scrap and use them as below, never the tape. One sandwich gives {l['per']} slabs; cut {l['slabs']} + {l['slab_spares']} spare in all.")
        else:
            tx.append(f"{l['name']}: blade square. Rip slabs {dim(l['slab'] + ov)} wide; one sandwich gives {l['per']}. Cut {l['slabs']} + {l['slab_spares']} spare in all.")
    if tilts:
        tx += ["The sandwich lies flat on the table with its jointed edge against the rip fence, and the fence on the side the blade leans away from, so the blade never leans over the wood between itself and the fence. "
               "The slab comes off the open side of the blade, the side away from the fence. It is taller than it is wide on the table and it leans outward, so it tips over away from the blade as it comes free. That is expected and it is not trapped: clear the table on that side, let it fall, and keep both hands on the part against the fence. Finish the cut, switch off, wait for the blade to stop and only then lift the slab away. The part against the fence is the part you hold, and it gets narrower with each cut. The drawing below shows the setup from the infeed side.",
               "First cut: set the fence so the blade takes a wedge off the open edge and leaves that edge a clean slanted face from top to bottom. Now clamp a stop block to the saw table (or the fence rail) touching the back of the fence, on the side away from the blade. For each slab: slacken the fence, slide it toward the blade, drop one more gauge strip between the stop block and the fence, push the fence back against the strips and lock it. Every move is then exactly one strip. Cut the first slab, check its thickness with calipers, square across the two sawn faces, and if it is off, re-rip the gauge strips before going on.",
               f"The cut is deep: the thickest sandwich is {short(maxh)} and the blade is close to its full height. The riving knife or a splitter must be on the saw for this cut. Use a sharp rip blade and push blocks that bear down on the top face and in against the fence. No featherboard: the open edge is a slanted face and a featherboard has nothing square to press on. Feed steadily. If the saw labours, make each cut in two passes, the first at half height.",
               "Cut the number of slabs given above from each sandwich and stop, whatever is left. The part against the fence is wider at the top than on the table, so judge it by its bottom face: never make a cut that would leave less than 1\" of it on the table. That last piece is waste; so is the first wedge. Both are counted in the material list.",
               "The pictures this method comes from show the slabs and the finished bars, not the saw setup. The fence side, the order of cuts and the stopping point above are this plan's working out. Before the first real cut, glue up a short sandwich of scrap as thick as the real one and rip two slabs from it with this setup. If the cut does not feel controlled on your saw, stop there; do not go on to the real sandwiches. A band saw with its table tilted to the same angle and a fence makes the same cut with nothing that can be thrown; the sawn faces are rougher, so leave 1/32\" more for the planer. That is this plan's suggestion, not something its source shows.",
               "The drawing shows a saw whose blade leans to the right. On a saw that leans left, everything is mirrored: fence on the right, slabs falling to the left."]
    tx += [f"Plane each slab on its two sawn faces to {dim(B if any(l['cut']['upright'] for l in cutb) else H)}, a light pass a face. The slab lies flat on a sawn face; the planer is safe here because the slab is long grain. "
           "Plane every slab of the board at the same setting, without moving the handwheel for the last pass: this thickness is the width of a bar, and it is a pattern size.",
           "Stack the slabs marked end to marked end. On each sawn face the glue lines now show as straight stripes."]
    S.append({"title": "Rip the sandwiches into slabs", "text": tx, "figs": [f"log_{l['id']}" for l in cutb][:1], "see": ["logs"],
              "dont": "put the sandwich between a blade that leans toward the fence and the fence. A slab trapped under a leaning blade is thrown."})

    tx = ["Blade back to square; check it. Clamp the auxiliary fence to the rip fence, tight on the table. A slab lies on a sawn face and its two long edges slant: they are the old faces of the sandwich. Both slanted points come off square.",
          "First cut: lay the slab with the sharp corner of one slanted edge down on the table and against the auxiliary fence. Which edge is labelled \"to the fence first\" on each bar's drawing on sheet 04. That corner is thin: bring it up to the fence gently and do not force it, because a crushed corner moves the cut. Mark the cut on the upper face at the far edge, as given below for each bar, set the fence to the mark and rip the far point off.",
          f"Second cut: turn the slab round so the fresh square edge is against the fence and rip the other point off. Set the fence {short(1 / 32)} over the bar's size; the planks are planed to size later, half off each face."]
    for l in cutb:
        top, bot = _square_marks(l); c = l["cut"]; sq = c["square"]
        first = (f"knife a line where a glue line meets the upper face at the far edge; the first cut goes {short(1 / 64)} outside that line, and the plank planing brings the face back to it" if top and abs(top[0]) < 0.01 else
                 f"the first cut is {dim(top[0])} outside the nearest glue line on the upper face" if top else f"the first cut takes off just the point")
        chk = "; ".join(f"{nm} face, glue lines at " + _join(("the edge" if p < 0.01 or p > sq - 0.01 else short(p)) for p in ps) for nm, ps in (("upper", top), ("lower", bot)) if ps)
        tx.append(f"{l['name']} (from sandwich {l['sandwich']}): {first}. Second cut {dim(sq + 1 / 32)} from the first. Check against the drawing on sheet 04: measured from the first cut edge, {chk}. Make {_made(l)}.")
    tx += ["Measure from the glue lines, never from the slanted edges: the glue lines are the pattern. Set up the first bar of each kind with a marking knife and a square, cut it, and hold its end against the sheet 04 drawing before cutting the rest. The fence bears on a slanted edge, so one setting holds only for slabs whose outside layer is the same thickness: check the first slab of every sandwich against the blade before cutting it, and reset the fence to the knifed line if the glue line has moved.",
           "As each bar comes off, hold its marked end toward you and turn it until the end matches its drawing on sheet 04. Pencil the bar's letter on that end. Then stand the bar the way sheet 05 draws it in the plank, marked end still toward you and the woods matching the drawing, and pencil a line along the narrow edge that is then on the bench. That edge goes down on the plank base; sheet 05 shows it as the short heavy line on every bar.",
           "As with the tilted rip, the squaring setup is this plan's working out; the source shows only the result. Try it on a spare slab."]
    S.append({"title": "Square the slabs into bars", "text": tx, "figs": [f"log_{l['id']}" for l in cutb][1:3], "see": ["logs"],
              "dont": "measure a squaring cut from the slanted edge. The edge is wherever the sandwich's outside face happened to be; the glue line is where the pattern is."})


def _finish_steps(S, plan):
    """Flatten, trim, frame and finish: the same for every build."""
    sh = plan["shop"]; T = plan["board"]["thickness"]; kind = plan["info"]["kind"]; planks = plan.get("planks") or []
    bd = plan["board"]; W, L = bd["field"]; m = bd["margins"]; zig = bd["zig"]; fr_ = bd.get("frame")
    def cutline(i, name):
        t1 = bd.get("tip1")
        return (f"the {name} cut {short(m[i])} inside the deepest notch of the ragged {name} edge" + (f" (that is {dim(t1[0 if name == 'left' else 1])} in from the {name} tip of row 1's long edge; mark it there with a square)" if t1 and name in ("left", "bottom") else "")
                if zig[i] else f"the {name} cut {short(m[i])} in from the {name} edge")
    tx = ["Flatten first, trim second. Flatten both faces with a drum sander (60 or 80 grit, light passes) or a router sled (wedge the board in a frame, spoilboard bit, passes of 1/32\" or less, outside edges first), "
          "then a random-orbit sander; a router sled does the whole job if there is no drum sander. "
          f"The {'rows' if planks else 'slices'} were cut {short(sh['flatten_allowance'])} thick of finished for this. "
          + (f"Stop as soon as both faces are clean and the board is an even thickness; leave it over {short(T)}, because it is flattened once more with its frame on." if fr_ else (f"Stop about 1/32\" over {short(T)}; the last pass after filling brings it to size." if kind == "hex" else f"Stop at {short(T)}.")),
          (f"Then trim to {dim(W)} x {dim(L)} with a track saw or on the crosscut sled. Only the two edges where the slices end are sawn: {short(m[0])} off the left and {short(m[1])} off the right, parallel, "
           f"which brings the two outside strips, made {short(m[0])} over width for this, to the same width as the rest. Mark each cut from the nearest glue line, not from the uneven edge: one finished square outside that line. Each cut is {dim(L)} long and takes about one kerf: a track saw on its rail does it best; a crosscut sled only if it takes {short(L)} in front of the blade. "
           "The other two edges are planed faces of the first and last slice. The clamps bore on scrap strips, not on them, so they are not sawn: scrape off any glue and sand them with the faces, and the end squares stay full size. If an end is marked anyway, take a 1/32\" skim off both ends alike. "
           "Tape the cut line and back the exit edge with scrap so the end grain does not chip."
           if m[2] < 1e-3 and m[3] < 1e-3 else
           f"Then trim to {dim(W)} x {dim(L)} with a track saw or on the crosscut sled. The trim lines are centred on the pattern (sheet 05 shows them against the rows): "
           + " ".join((f"The {nm} edge is the planed face of an outside row and already on its line: leave it and measure from it." if m[i] < 2e-3 else f"Make {cutline(i, nm)}.") for i, nm in ((0, "left"), (2, "bottom")))
           + " Keep the two square to each other, then cut the right and top edges parallel to them at the finished size"
           + (f", which takes about {short(m[1])} off the right" if m[1] >= 2e-3 else ", where the right edge is already a planed face on its line") + (f" and {short(m[3])} off the top. " if m[3] >= 2e-3 else "; the top edge is already a planed face on its line. ")
           if kind == "bars" and min(m) < 2e-3 else
           f"Then trim to {dim(W)} x {dim(L)} with a track saw or on the crosscut sled. The trim lines are centred on the pattern (sheet 05 shows them against the rows): "
           f"make {cutline(0, 'left')} and {cutline(2, 'bottom')}, square to each other, then cut the right and top edges parallel to them at the finished size. "
           f"That leaves about {short(m[1])} of waste on the right and {short(m[3])} at the top. "
           "Tape the cut line and back the exit edge with scrap so the end grain does not chip."),
          ] + ([] if fr_ else ["Sand both faces 80, 120, 180; wipe with a damp cloth to raise the grain, let it dry, then sand 220."])
    if kind == "hex":
        tx.insert(1, "Fill before the last pass. Silva lists this as a step: mix fine sanding dust from the board with glue to the thickness of peanut butter, pack it into any open joint, let it cure, then take one more light flattening pass over both faces, down to " + short(T) + ".")
    S.append({"title": "Flatten, fill, then trim" if kind == "hex" else "Flatten, then trim", "text": tx, "figs": ["trim"], "see": [],
              "dont": "run the board through a thickness planer. End grain breaks out at the trailing edge and the planer can throw pieces."})
    if fr_:
        cutl = plan["slice_cut"]; rg = fr_["rings"]; two = len(rg) > 1
        tx = [(f"Round the field goes a {short(rg[0]['width'])} line of {rg[0]['species']} and then a {short(rg[1]['width'])} frame of {rg[1]['species']}. " if two else f"The frame is {rg[0]['species']}. ")
              + "All of it stands on end like everything else, so it swells and shrinks with the field. A long-grain frame would split the board."]
        tx.append("Making the strips: plane the board to the thickness below with both edges jointed parallel. Crosscut blocks from it on the sled, "
                  f"each {short(cutl)} long, with the same spacer stop and setting used for the slices; the board lies flat on the sled under a hold-down, and the last 2 inches are not cut. "
                  "Stand the blocks on end and glue them edge to edge into four strips in the row jig: against the fixed fence, the loose blocks wedged up to them so the strip cannot buckle sideways, "
                  "a taped caul with a weight on top, and one clamp along each strip with light pressure. These joints are long grain to long grain, and in one wood they disappear.")
        for r in rg:
            n1, n2 = r["per_side"]; nm = "The line" if r["role"] == "liner" else "The frame"
            tx.append(f"{nm}: {r['species']}, planed {dim(r['width'])} thick. {r['blocks']} blocks, each {short(r['width'])} x {short(r['block_len'])} seen from above: "
                      f"two strips of {n1} for the long sides (at least {short(r['long'] + 0.5)} long), two of {n2} for the ends (at least {short(r['short'] + 0.5)}), and one spare.")
        tx += ["Scrape each strip and pass the face that meets the board under the drum sander once (or take a few strokes on the 80 grit sanding board), so it is flat across the block joints.",
               ("Work one ring at a time, the line first. " if two else "")
               + "Glue the two long strips to the long edges, overhanging both ends, with clamps across the board every 4 to 5 inches and a taped caul over each joint to keep the strips level with the field. "
               "When the glue has set, saw the overhanging ends flush with the short edges on the sled, taking the strip ends and no more than a shaving of the field.",
               "Glue the two end strips across the ends the same way, clamping along the length of the board, then saw their overhang flush with the long sides."
               + (" The outside of the line is the glue face for the frame, so true it before going on: skim all four edges of the board with a light trim cut on the sled or track saw, a shaving only, so each is one flat, square face. "
                  "Then add the frame strips round the line the same way." if two else ""),
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
        print(f"  {l['name']} ({l['what']}): " + ", ".join(f"{k} x {ln:g} in" for ln, k in l["make"]) + (f" -> {l['slices']} slices (+{l['spares']})" if l["crosscut"] and not plan.get("planks") else ""))
    for pl in plan.get("planks") or []:
        print(f"  Plank {pl['id']}: {pl['count']} x {pl['length']:g} in, {pl['n']} logs across ({pl['width']:.2f} in) -> {pl['rows_cut']} rows (+{pl['spares']})")
    for s in plan["stock"]:
        print(f"  buy {s['species']}: {s['bf_buy']:g} bd ft")
    bad = [c for c in plan["checks"] if not c["ok"] and c["level"] != "warn"]
    for c in plan["checks"]:
        print(("  ok   " if c["ok"] else "  WARN " if c["level"] == "warn" else "  FAIL ") + c["what"] + (f" ({c['detail']})" if c["detail"] else ""))
    print("wrote", os.path.abspath(a.out))
    sys.exit(1 if bad else 0)
