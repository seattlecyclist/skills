"""Sandwich bars: build a 60 degree pattern from rectangles, the way production shops do.

Glue flat boards face to face into a *sandwich*. Rip the sandwich into slabs with the blade tilted. Lay each
slab on a sawn face and rip its two points off square: that is a rectangular *bar* with slanted stripes.
Glue bars side by side into a plank, plane it, crosscut it into rows. Every glue-up is flat faces under
ordinary clamps; no piece is ever a triangle.

The face decides whether this works. Cut the face into rows `row` high and each row into bars `bar` wide.
A bar can come out of one sandwich exactly when every line where two woods meet inside it is parallel to
every other and runs right across it. Then the bar is a slice of a stack of flat layers, and the layers,
the blade tilt and the two squaring cuts all follow from the face.

    layout(polys, trim, wood_of, shop) -> cells {"kind": "bars", "angle", "row", "bar", "origin"} or None
    bar_plan(polys, trim, cells, wood_of) -> {"logs", "rows", "info"}     (the same shape logs.plan returns)
    verify(plan_rows, polys, wood_of) -> worst mismatch, sq in             (the face rebuilt from the sandwiches)

Bar frame: x across the bar from its centre, y through the row. A bar is {theta, layers}: theta is the
direction of the glue lines in degrees (0 to 180, from the x axis), layers are (wood, role, lo, hi) measured
along the normal (-sin theta, cos theta) from the bar's centre.
"""
import math
from logs import clip_half, area, ccw

IDS = [a for a in "ABCDEFGHJKLMNPQRSTUVWXYZ"] + [a + b for a in "ABCDEFGH" for b in "ABCDEFGHJKLMNPQRSTUVWXYZ"]
SYM = ((1, 1), (-1, -1), (-1, 1), (1, -1))      # as cut; rolled over; turned end for end; end for end and rolled


def _frame(angle):
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    return (lambda p: (p[0] * c + p[1] * s, -p[0] * s + p[1] * c)), (lambda p: (p[0] * c - p[1] * s, p[0] * s + p[1] * c))


class _Index:
    """The face in the row frame, bucketed so a bar only looks at the pieces near it."""
    def __init__(self, polys, wood_of, G):
        self.b = {}
        for p in polys:
            pts = [G(v) for v in p["pts"]]
            bb = (min(v[0] for v in pts), min(v[1] for v in pts), max(v[0] for v in pts), max(v[1] for v in pts))
            it = (wood_of(p["role"]), p["role"], pts, bb)
            for i in range(math.floor(bb[0]), math.floor(bb[2]) + 1):
                for j in range(math.floor(bb[1]), math.floor(bb[3]) + 1):
                    self.b.setdefault((i, j), []).append(it)

    def content(self, r):
        """Every piece of the face inside rectangle r = (x0, y0, x1, y1), clipped to it: [(wood, role, pts)]."""
        x0, y0, x1, y1 = r; seen = set(); out = []
        box = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        for i in range(math.floor(x0), math.floor(x1) + 1):
            for j in range(math.floor(y0), math.floor(y1) + 1):
                for it in self.b.get((i, j), ()):
                    if id(it) in seen: continue
                    seen.add(id(it)); bb = it[3]
                    if bb[2] <= x0 + 1e-7 or bb[0] >= x1 - 1e-7 or bb[3] <= y0 + 1e-7 or bb[1] >= y1 - 1e-7: continue
                    q = [tuple(v) for v in it[2]]
                    for k in range(4):
                        q = clip_half(q, box[k], box[(k + 1) % 4])
                        if not q: break
                    if q and abs(area(q)) > 1e-7: out.append((it[0], it[1], q))
        return out


def _strip(p, c, th, a, b):
    """The part of convex polygon p between the lines at normal distance a and b from point c."""
    t = (math.cos(math.radians(th)), math.sin(math.radians(th))); n = (-t[1], t[0])
    pa = (c[0] + a * n[0], c[1] + a * n[1]); pb = (c[0] + b * n[0], c[1] + b * n[1])
    q = clip_half(p, pa, (pa[0] + t[0], pa[1] + t[1]))
    return clip_half(q, (pb[0] + t[0], pb[1] + t[1]), pb) if q else None


def layers_of(items, r):
    """The sandwich this bar is a slice of, or None. items [(wood, role, pts)] fill rectangle r.
    -> {"theta": None, "layers": [(wood, role)]} for one wood, else {"theta", "layers": [(wood, role, lo, hi)]}."""
    x0, y0, x1, y1 = r; c = ((x0 + x1) / 2, (y0 + y1) / 2)
    if abs(sum(abs(area(p)) for _, _, p in items) - (x1 - x0) * (y1 - y0)) > 1e-4 * (x1 - x0) * (y1 - y0): return None      # the face does not fill the bar
    if len({w for w, _, _ in items}) == 1: return {"theta": None, "layers": [(items[0][0], items[0][1])]}
    cands = set()
    for _, _, p in items:
        for i in range(len(p)):
            a, b = p[i - 1], p[i]
            if math.dist(a, b) < 1e-3: continue
            if any(abs(a[k] - e) < 1e-5 and abs(b[k] - e) < 1e-5 for k, e in ((0, x0), (0, x1), (1, y0), (1, y1))): continue
            cands.add(round(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180, 1) % 180)
    best = None
    for th in sorted(cands):
        n = (-math.sin(math.radians(th)), math.cos(math.radians(th)))
        proj = [[(v[0] - c[0]) * n[0] + (v[1] - c[1]) * n[1] for v in p] for _, _, p in items]
        cuts = []
        for d in sorted(d for ds in proj for d in ds):
            if not cuts or d - cuts[-1] > 1e-4: cuts.append(d)
        lay = []; ok = True
        for a, b in zip(cuts, cuts[1:]):
            here = {}; ar = {}
            for (w, role, p), ds in zip(items, proj):
                if max(ds) <= a + 1e-6 or min(ds) >= b - 1e-6: continue
                q = _strip(p, c, th, a, b)
                if q: ar[w] = ar.get(w, 0.0) + abs(area(q)); here.setdefault(w, role)
            here = {w: r_ for w, r_ in here.items() if ar[w] > 2e-4}      # a hair left by rounding is not a layer
            if not here:
                if lay: lay[-1] = lay[-1][:3] + (b,)
                continue
            if len(here) != 1: ok = False; break
            (w, role), = here.items()
            if lay and lay[-1][0] == w: lay[-1] = (w, lay[-1][1], lay[-1][2], b)
            else: lay.append((w, role, a, b))
        if ok and len(lay) > 1 and (best is None or len(lay) < len(best["layers"])):
            best = {"theta": th, "layers": [(w, role, round(a, 6) + 0.0, round(b, 6) + 0.0) for w, role, a, b in lay]}
    return best


def cells_of(B, H, bar):
    """The bar's cross-section rebuilt from its sandwich alone: [(wood, role, pts)], centred on the origin."""
    box = [(-B / 2, -H / 2), (B / 2, -H / 2), (B / 2, H / 2), (-B / 2, H / 2)]
    if bar["theta"] is None: return [(bar["layers"][0][0], bar["layers"][0][1], box)]
    out = []
    for w, role, a, b in bar["layers"]:
        q = _strip(box, (0, 0), bar["theta"], a - 1e-9, b + 1e-9)
        if q: out.append((w, role, ccw(q)))
    return out


def _key(bar):
    if bar["theta"] is None: return ("solid", bar["layers"][0][0])
    return (round(bar["theta"], 1), tuple((w, round(a, 3) + 0.0, round(b, 3) + 0.0) for w, _, a, b in bar["layers"]))


def canon(B, H, bar):
    """The bar turned every way a long bar can be turned (rolled over, end for end, both): the smallest key is its
    type. -> (key, the type's own description, (sx, sy) that carries the type onto this bar)."""
    if bar["theta"] is None: return _key(bar), bar, (1, 1)
    r = (-B / 2, -H / 2, B / 2, H / 2); cs = cells_of(B, H, bar); best = None
    for sx, sy in SYM:
        t = layers_of([(w, role, ccw([(x * sx, y * sy) for x, y in p])) for w, role, p in cs], r)
        k = _key(t)
        if best is None or k < best[0]: best = (k, t, (sx, sy))
    return best


def cut_of(B, H, bar, allow=0.03125):
    """How the bar comes out of its sandwich: blade tilt, slab thickness between the tilted cuts, the squared size,
    the sandwich's layers bottom to top, and where each glue line meets the two sawn faces, measured from the first
    squared edge."""
    th = bar["theta"]; phi = min(th, 180 - th); rad = math.radians(th)
    upright = phi < 45 - 1e-6                         # the tilted cuts are the bar's upright sides
    tilt = phi if upright else 90 - phi
    slab, square = (B, H) if upright else (H, B)
    lay = bar["layers"]; ts = lay[-1][3] - lay[0][2]
    stack = [[w, role, b - a] for w, role, a, b in lay]
    if tilt > 1e-6: stack[0][2] += allow; stack[-1][2] += allow
    faces = []
    for sg in (-1, 1):
        pos = []
        for _, _, a, _ in lay[1:]:
            if upright: p = (a + sg * B / 2 * math.sin(rad)) / math.cos(rad) + H / 2
            else: p = (sg * H / 2 * math.cos(rad) - a) / math.sin(rad) + B / 2
            if -1e-6 <= p <= square + 1e-6: pos.append(round(p, 4) + 0.0)
        faces.append(sorted(pos))
    return {"tilt": round(tilt, 2), "slab": slab, "square": square, "upright": upright, "need": ts,
            "stack": [tuple(s) for s in stack], "faces": faces}


def per_sandwich(cut, width, shop):
    """Slabs one sandwich of this width gives. The first tilted cut takes a wedge off the open edge and the last
    leaves a wedge against the fence, each as wide as the sandwich's thickness times the tangent of the tilt."""
    ov = shop.get("slab_oversize", 1 / 16); total = sum(t for _, _, t in cut["stack"])
    if cut["tilt"] < 1e-6: return int((width - 0.25 + shop["kerf"]) // (cut["slab"] + ov + shop["kerf"]))
    cs = math.cos(math.radians(cut["tilt"])); lead = total * math.tan(math.radians(cut["tilt"]))
    return max(0, int((width - 2 * lead - 0.25) // ((cut["slab"] + ov + shop["kerf"]) / cs)))


def widths(shop):
    """The sandwich widths a shop can make: one board wide, or two boards edge-glued, as wide as the planer takes."""
    one = shop["stock_width"]; cap = shop.get("planer_width", 12.5) - 0.25
    return min(one, cap), min(2 * one - 0.25, cap)


def _skey(cut):
    """Bars share a sandwich when the woods, the inner layers and the blade tilt agree; the outer layers are made
    as thick as the hungriest bar needs."""
    st = cut["stack"]; f = tuple((w, round(t, 3) if 0 < i < len(st) - 1 else None) for i, (w, _, t) in enumerate(st))
    return (round(cut["tilt"], 1), min(f, f[::-1], key=str)), f != min(f, f[::-1], key=str)


def _grid(lo, hi, o, step):
    k0 = math.floor((lo - o) / step + 1e-6); k1 = math.ceil((hi - o) / step - 1e-6)
    return [o + k * step for k in range(k0, k1)]


def _steps(vals):
    v = []
    for x in sorted(vals):
        if not v or x - v[-1] > 1e-4: v.append(x)
    d = [b - a for a, b in zip(v, v[1:]) if b - a > 0.05]
    return min(d) if d else None


def layout(polys, trim, wood_of, shop):
    """The largest bar that works, or None. Fixed rules, so the same face always gives the same answer:
    a bar is at least shop.min_sandwich_bar on its narrow side, its sandwich is no thicker than the saw rips at
    the tilt, and a sandwich gives at least two slabs. Among layouts that pass, the fewest sandwiches win, then
    the fewest kinds of bar, then the largest bar, then the taller row, then rows across the board."""
    minb = shop.get("min_sandwich_bar", 0.4); best = None
    width = shop.get("sandwich_width") or widths(shop)[1]
    for angle in (0, 90):
        G, _ = _frame(angle); ix = _Index(polys, wood_of, G)
        q = [G((trim[a], trim[b])) for a in (0, 2) for b in (1, 3)]
        U0, U1 = min(v[0] for v in q), max(v[0] for v in q); V0, V1 = min(v[1] for v in q), max(v[1] for v in q)
        us = set(); vs = set()
        for its in ix.b.values():
            for it in its:
                for u, v in it[2]:
                    if U0 - 3 < u < U1 + 3 and V0 - 3 < v < V1 + 3: us.add(round(u, 6)); vs.add(round(v, 6))
        du, dv = _steps(us), _steps(vs)
        if not du or not dv: continue
        ou0 = min(us); ov0 = min(vs); cache = {}

        def bar_at(r):
            k = tuple(round(x, 5) for x in r)
            if k not in cache:
                b = layers_of(ix.content(r), r); ok = None
                if b:
                    key, typ, sym = canon(r[2] - r[0], r[3] - r[1], b); cut = None
                    if typ["theta"] is not None:
                        cut = cut_of(r[2] - r[0], r[3] - r[1], typ); total = sum(t for _, _, t in cut["stack"])
                        cap = shop["max_cut_height"] * math.cos(math.radians(cut["tilt"])) - 0.03
                        if total > cap or per_sandwich(cut, width, shop) < 2: key = None
                    ok = (key, cut) if key else None
                cache[k] = ok
            return cache[k]

        sizes = sorted(((dv * a, du * b) for a in range(1, 17) for b in range(1, 17)
                        if minb - 1e-6 <= dv * a <= 3.0 and minb - 1e-6 <= du * b <= 3.0), key=lambda s: (-s[0] * s[1], -s[0]))
        for H, B in sizes:
            for a in range(int(round(H / dv))):
                for b in range(int(round(B / du))):
                    ov, ou = ov0 + a * dv, ou0 + b * du
                    rects = [(u, v, u + B, v + H) for v in _grid(V0, V1, ov, H) for u in _grid(U0, U1, ou, B)]
                    mid = ((U0 + U1) / 2, (V0 + V1) / 2)
                    rects.sort(key=lambda r: (round(abs(r[0] - mid[0]) + abs(r[1] - mid[1]), 3), r))      # the middle of the board fails first
                    keys = set(); sand = set(); ok = True
                    for r in rects:
                        t = bar_at(r)
                        if not t: ok = False; break
                        keys.add(t[0])
                        if t[1]: sand.add(_skey(t[1])[0])
                    if not ok: continue
                    score = (-len(sand), -len(keys), round(H * B, 5), round(H, 5), -len(rects), -angle, -round(ov - V0, 5), -round(ou - U0, 5))
                    if best is None or score > best[0]:
                        best = (score, {"kind": "bars", "angle": angle, "row": H, "bar": B, "origin": [ou, ov]})
    return best[1] if best else None


def bar_plan(polys, trim, cells, wood_of):
    angle = cells.get("angle", 0); H = float(cells["row"]); B = float(cells["bar"]); ou, ov = cells.get("origin", (0, 0))
    allow = float(cells.get("allow", 0.03125)); width = float(cells.get("sandwich_width", 5.5))
    G, Bd = _frame(angle); ix = _Index(polys, wood_of, G)
    q = [G((trim[a], trim[b])) for a in (0, 2) for b in (1, 3)]
    U0, U1 = min(v[0] for v in q), max(v[0] for v in q); V0, V1 = min(v[1] for v in q), max(v[1] for v in q)
    types = {}; order = []; rows = []
    for n, v in enumerate(_grid(V0, V1, ov, H)):
        pk = []
        for u in _grid(U0, U1, ou, B):
            r = (u, v, u + B, v + H); bar = layers_of(ix.content(r), r)
            if bar is None: raise ValueError(f"the bar at {u:.3f}, {v:.3f} is not a slice of one sandwich")
            key, typ, (sx, sy) = canon(B, H, bar)
            if key not in types: types[key] = typ; order.append(key)
            c = (u + B / 2, v + H / 2)
            cl = [(role, [Bd((c[0] + x * sx, c[1] + y * sy)) for x, y in p]) for _, role, p in cells_of(B, H, types[key])]
            box = [Bd(p) for p in ((u, v), (u + B, v), (u + B, v + H), (u, v + H))]
            ref = (box[0], box[1]) if sy > 0 else (box[3], box[2])
            pk.append({"type": key, "pts": box, "flip": sx * sy < 0, "ref": ref, "cells": [(role, ccw(p)) for role, p in cl], "x": u})
        u0, u1 = pk[0]["x"], pk[-1]["x"] + B
        rows.append({"n": n + 1, "pucks": pk, "height": H, "length": u1 - u0, "pts": [Bd(p) for p in ((u0, v), (u1, v), (u1, v + H), (u0, v + H))]})
    logs = []; sand = {}; bar_id = {}; cuts_up = {}
    cuts = {k: (cut_of(B, H, types[k], allow) if types[k]["theta"] is not None else None) for k in order}
    for k in order:                                    # sandwiches first, in the order their bars first appear
        if not cuts[k]: continue
        sk, rev = _skey(cuts[k]); st = list(cuts[k]["stack"][::-1] if rev else cuts[k]["stack"])
        cuts_up[sk] = cuts[k]["upright"]
        if sk not in sand: sand[sk] = {"id": f"S{len(sand) + 1}", "stack": st}
        else:
            o = sand[sk]["stack"]
            sand[sk]["stack"] = [(w, role, max(t, o[i][2]) if i in (0, len(st) - 1) else t) for i, (w, role, t) in enumerate(st)]
    for sk, s in sand.items():
        y = 0.0; cs = []
        for w, role, t in s["stack"]:
            cs.append((w, role, [(0, y), (width, y), (width, y + t), (0, y + t)])); y += t
        logs.append({"id": s["id"], "key": sk, "kind": "rect", "shape": "sandwich", "level": 1, "w": width, "h": y, "slab": B if cuts_up[sk] else H, "stack": list(s["stack"]),
                     "outline": [(0, 0), (width, 0), (width, y), (0, y)], "cells": [(role, p) for _, role, p in cs], "tilt": sk[0],
                     "stages": [{"parts": [{"bar": True, "wood": w, "role": role, "pts": p, "layer": True, "outer": i in (0, len(cs) - 1) and sk[0] > 0}
                                           for i, (w, role, p) in enumerate(cs)], "jig": "flat cauls"}], "crosscut": False})
    for n, k in enumerate(order):
        typ = types[k]; bar_id[k] = IDS[n]; box = [(0, 0), (B, 0), (B, H), (0, H)]
        cs = [(w, role, [(x + B / 2, y + H / 2) for x, y in p]) for w, role, p in cells_of(B, H, typ)]
        lg = {"id": IDS[n], "key": k, "kind": "rect", "shape": "sbar", "level": 2, "w": B, "h": H, "outline": box,
              "cells": [(role, p) for _, role, p in cs], "crosscut": True}
        if cuts[k]:
            sid = sand[_skey(cuts[k])[0]]["id"]
            lg.update(sandwich=sid, cut=cuts[k], layers=[(w, role, a, b) for w, role, a, b in typ["layers"]], theta=typ["theta"],
                      stages=[{"parts": [{"log": sid, "pts": box, "cells": [(role, p) for _, role, p in cs], "flip": False, "cut": True}], "jig": "saw"}])
        else:
            lg["stages"] = [{"parts": [{"bar": True, "wood": typ["layers"][0][0], "role": typ["layers"][0][1], "pts": box}], "jig": "none"}]
        logs.append(lg)
    for r in rows:
        for pk in r["pucks"]: pk["log"] = bar_id[pk.pop("type")]
    return {"logs": logs, "rows": rows, "info": {"kind": "bars", "angle": angle, "row": H, "bar": B, "row_height": H}}


def verify(rows, polys, wood_of, trim=None):
    """The proof. Every bar on the board was redrawn from nothing but its sandwich's layers, the tilt and the two
    squaring cuts. Lay those redrawn bars over the pattern: wherever a redrawn piece of one wood lies, the pattern
    must be that wood. -> (bars checked, total area checked, area where the two disagree), sq in."""
    ix = _Index(polys, wood_of, lambda p: p)
    n = 0; tot = 0.0; bad = 0.0
    for r in rows:
        for pk in r["pucks"]:
            n += 1
            for role, pts in pk["cells"]:
                p = ccw([tuple(v) for v in pts])
                if trim:
                    box = [(trim[0], trim[1]), (trim[2], trim[1]), (trim[2], trim[3]), (trim[0], trim[3])]
                    for k in range(4):
                        p = clip_half(p, box[k], box[(k + 1) % 4])
                        if not p: break
                    if not p: continue
                a = abs(area(p)); tot += a; same = 0.0; w = wood_of(role)
                bb = (min(v[0] for v in p), min(v[1] for v in p), max(v[0] for v in p), max(v[1] for v in p))
                for ow, _, q in ix.content(bb):
                    if ow != w: continue
                    for k in range(len(p)):
                        q = clip_half(q, p[k], p[(k + 1) % len(p)])
                        if not q: break
                    if q: same += abs(area(q))
                bad += max(0.0, a - same)
    return n, tot, bad
