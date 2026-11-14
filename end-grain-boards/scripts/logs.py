"""Log build: cut the board face into small closed logs, the way patterned end-grain boards are built.

Makers do not glue a long row of bevelled bars, and they do not glue zigzag logs. They glue three or four
bars into a small log whose outside is a triangle (60 degree patterns, in a V cradle) or a rectangle
(45 and 90 degree patterns, in corner cauls or flat cauls), machine every face of that log flat, crosscut
it, glue the slices into straight rows, true the rows, and glue the rows into the board.

    plan(polys, trim, cells, wood_of, recipe_ok) -> {"logs": [...], "rows": [...], "info": {...}}

polys: [{"pts", "role"}] the face, inches.  cells: what the generator says the natural log is:
    {"kind": "tri", "side": L, "origin": [x, y], "angle": deg, "levels": 1 or 2}
        a triangular grid of side L with one edge direction at `angle` (rows of triangles run that way);
        levels 2 glues four side-L logs into a side-2L log before crosscutting.
    {"kind": "blocks", ...}   square blocks built from quarter logs (eight-point stars; see stars8_plan)
    {"kind": "panel"}         square-edged strips glued into flat panels, slices are whole rows

A log type is a dict:
    id, kind ("tri" | "rect" | "panel"), outline (local pts), cells [(role, pts)] (its whole cross-section),
    stages [{"parts": [part], "jig": str}], part = {"bar": True, "role", "pts"} or {"log": id, "pts", "cells"},
    w, h, crosscut (True for the logs that are sliced), level
A row is {"n", "pucks": [{"log": id, "pts": outline on the board, "ref": (a, b) the reference-face edge,
"flip": bool, "cells": [(role, pts)]}], "pts": the row's outline}.
"""
import math

S3 = math.sqrt(3)
EPS = 1e-6


# ------------------------------------------------------------------------------------- geometry
def area(p):
    return 0.5 * sum(p[i - 1][0] * p[i][1] - p[i][0] * p[i - 1][1] for i in range(len(p)))


def ccw(p):
    return list(p) if area(p) > 0 else list(p)[::-1]


def clip_half(pts, a, b):
    """Keep the part of convex polygon pts to the left of the line a -> b."""
    def side(p): return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    out = []
    n = len(pts)
    for i in range(n):
        p, q = pts[i - 1], pts[i]
        sp, sq = side(p), side(q)
        if sq >= -1e-9:
            if sp < -1e-9:
                t = sp / (sp - sq); out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
            out.append(tuple(q))
        elif sp >= -1e-9:
            t = sp / (sp - sq); out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    clean = []
    for v in out:
        if not clean or math.dist(v, clean[-1]) > 1e-5: clean.append(v)
    if len(clean) > 1 and math.dist(clean[0], clean[-1]) < 1e-5: clean.pop()
    return clean if len(clean) >= 3 and abs(area(clean)) > 1e-5 else None


def clip_poly(pts, cell):
    cell = ccw(cell); out = [tuple(v) for v in pts]
    for i in range(len(cell)):
        out = clip_half(out, cell[i], cell[(i + 1) % len(cell)])
        if not out: return None
    return out


def simplify(p):
    """Drop collinear and duplicate vertices."""
    out = []
    n = len(p)
    for i in range(n):
        a, b, c = p[i - 1], p[i], p[(i + 1) % n]
        if math.dist(a, b) < 1e-5: continue
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cr) < 1e-5 * max(1.0, math.dist(a, b) * math.dist(b, c)): continue
        out.append(b)
    return out


def is_convex(p):
    n = len(p)
    for i in range(n):
        a, b, c = p[i], p[(i + 1) % n], p[(i + 2) % n]
        if (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) < -1e-6: return False
    return True


def _r(v, nd=3):
    # the small offset keeps values such as 0.375 or 0.825 off a rounding boundary
    return (round(v[0] + 0.00137, nd) + 0.0, round(v[1] + 0.00137, nd) + 0.0)


def try_merge(p, q):
    """Union of two convex ccw polygons that share a whole edge, if the union is convex; else None."""
    n, m = len(p), len(q)
    for i in range(n):
        a, b = _r(p[i]), _r(p[(i + 1) % n])
        for j in range(m):
            if _r(q[j]) == b and _r(q[(j + 1) % m]) == a:
                u = [p[(i + 1 + k) % n] for k in range(n)] + [q[(j + 2 + k) % m] for k in range(m - 2)]
                # p from b round to a, then q from the vertex after a round to the one before b
                u = [p[(i + 1 + k) % n] for k in range(n)]            # b ... a
                u += [q[(j + 2 + k) % m] for k in range(m - 2)]         # after a ... before b
                u = simplify(u)
                if len(u) >= 3 and is_convex(u) and abs(abs(area(u)) - abs(area(p)) - abs(area(q))) < 1e-5:
                    return u
    return None


def merge_all(items, ok=None):
    """items [(wood, role, pts)]: merge same-wood neighbours while the union stays convex (and ok(pts))."""
    items = [(w, r, ccw(simplify(list(p)))) for w, r, p in items]
    changed = True
    while changed:
        changed = False
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if items[i][0] != items[j][0]: continue
                u = try_merge(items[i][2], items[j][2])
                if u and (ok is None or ok(u)):
                    items[i] = (items[i][0], items[i][1], ccw(u)); items.pop(j); changed = True; break
            if changed: break
    return items


def xform(pts, rot, mirror, shift=(0, 0), pre=(0, 0)):
    c, s = math.cos(rot), math.sin(rot); out = []
    for x, y in pts:
        x, y = x - pre[0], y - pre[1]
        x, y = x * c - y * s, x * s + y * c
        if mirror: x = -x
        out.append((x + shift[0], y + shift[1]))
    return out[::-1] if mirror else out


def key_of(items):
    """The same for any two cross-sections that are the same woods in the same places: sample points, not vertices,
    so it does not depend on how the pieces happen to be cut up."""
    out = []
    for w, _, p in items:
        p = simplify(list(p))
        if len(p) < 3: continue
        out.append((w, tuple(sorted(_r(v, 2) for v in p))))
    return tuple(sorted(out))


# ------------------------------------------------------------------------------------- triangle logs
def _tri_local(cell):
    """The six ways an equilateral cell can sit tip-down at the origin: [(k, mirror, fn)]."""
    cell = ccw(cell); out = []
    cx = sum(v[0] for v in cell) / 3; cy = sum(v[1] for v in cell) / 3
    for k in range(3):
        tip = cell[k]; ang = math.atan2(cy - tip[1], cx - tip[0]); rot = math.pi / 2 - ang
        for m in (False, True):
            out.append((k, m, (lambda pts, tip=tip, rot=rot, m=m: xform(pts, rot, m, pre=tip))))
    return out


def _stages(parts):
    """Split parts (each with 'pts', tip-down frame) into glue-ups at heights where a flat face crosses no part."""
    ys = sorted({round(v[1], 3) for p in parts for v in p["pts"]})
    top = ys[-1]; cuts = []
    for y in ys[1:]:
        if all(not (min(v[1] for v in p["pts"]) < y - 1e-3 and max(v[1] for v in p["pts"]) > y + 1e-3) for p in parts):
            cuts.append(y)
    if not cuts or abs(cuts[-1] - top) > 1e-3: cuts.append(top)
    st = []; lo = -1e9
    for y in cuts:
        grp = [p for p in parts if lo - 1e-3 <= min(v[1] for v in p["pts"]) and max(v[1] for v in p["pts"]) <= y + 1e-3
               and min(v[1] for v in p["pts"]) >= lo - 1e-3 and not any(p is q for s_ in st for q in s_)]
        if grp: st.append(grp)
        lo = y
    # a single part is not a glue-up, and three or four bars are one cradle load: merge neighbours up to four parts
    merged = []
    for grp in st:
        if merged and len(merged[-1]) + len(grp) <= 4: merged[-1] = merged[-1] + grp
        else: merged.append(list(grp))
    for grp in merged: grp.sort(key=lambda p: (round(min(v[1] for v in p["pts"]), 3), sum(v[0] for v in p["pts"]) / len(p["pts"])))
    return merged


def tri_plan(polys, trim, cells, wood_of, bar_ok=None):
    L = float(cells["side"]); H = L * S3 / 2; ox, oy = cells.get("origin", (0, 0)); th = math.radians(cells.get("angle", 0))
    levels = int(cells.get("levels", 1))
    c, s = math.cos(th), math.sin(th)
    to_grid = lambda p: ((p[0] - ox) * c + (p[1] - oy) * s, -(p[0] - ox) * s + (p[1] - oy) * c)
    to_board = lambda p: (ox + p[0] * c - p[1] * s, oy + p[0] * s + p[1] * c)
    gp = [{"pts": [to_grid(v) for v in p["pts"]], "role": p["role"], "wood": wood_of(p["role"])} for p in polys]
    for p in gp: p["bb"] = (min(v[0] for v in p["pts"]), min(v[1] for v in p["pts"]), max(v[0] for v in p["pts"]), max(v[1] for v in p["pts"]))
    tg = [to_grid(v) for v in ((trim[0], trim[1]), (trim[2], trim[1]), (trim[2], trim[3]), (trim[0], trim[3]))]

    def cells_at(side):
        Hh = side * S3 / 2
        ys = [v[1] for v in tg]; xs = [v[0] for v in tg]
        out = []
        for j in range(math.floor(min(ys) / Hh + 1e-6), math.ceil(max(ys) / Hh - 1e-6)):
            i0 = math.floor((min(xs) - (j + 1) * side / 2) / side) - 1; i1 = math.ceil((max(xs) - j * side / 2) / side) + 1
            Pt = lambda i, jj: (i * side + jj * side / 2, jj * Hh)
            for i in range(i0, i1 + 1):
                for kind, tri in (("up", [Pt(i, j), Pt(i + 1, j), Pt(i, j + 1)]), ("down", [Pt(i + 1, j), Pt(i + 1, j + 1), Pt(i, j + 1)])):
                    if clip_poly(tri, tg): out.append({"i": i, "j": j, "kind": kind, "tri": tri})
        return out

    def content(tri):
        bb = (min(v[0] for v in tri), min(v[1] for v in tri), max(v[0] for v in tri), max(v[1] for v in tri))
        items = []
        for p in gp:
            if p["bb"][2] <= bb[0] + 1e-6 or p["bb"][0] >= bb[2] - 1e-6 or p["bb"][3] <= bb[1] + 1e-6 or p["bb"][1] >= bb[3] - 1e-6: continue
            f = clip_poly(p["pts"], tri)
            if f: items.append((p["wood"], p["role"], f))
        return items

    types = {}; order = []

    def classify(tri, items):
        """-> (type key, tip index k, mirror) with the type's canonical cross-section registered."""
        best = None
        for k, m, fn in _tri_local(tri):
            loc = [(w, r, ccw(fn(p))) for w, r, p in items]
            kk = key_of(loc)
            if kk in types: return kk, k, m
            if best is None or (kk, m) < (best[0], best[3]): best = (kk, k, loc, m)
        # new type: pick the tip that gives the best glue-up order (mirror kept out of the canonical form)
        cands = []
        for k, m, fn in _tri_local(tri):
            if m: continue
            loc = merge_all([(w, r, ccw(fn(p))) for w, r, p in items], bar_ok)
            parts = [{"bar": True, "wood": w, "role": r, "pts": p} for w, r, p in loc]
            st = _stages(parts)
            mx = max(len(g) for g in st)
            cands.append(((max(mx, 4), len(st), mx, k), k, loc, st, key_of([(w, r, ccw(fn(p))) for w, r, p in items])))
        cands.sort(key=lambda c_: c_[0])
        _, k, loc, st, kk = cands[0]
        types[kk] = {"cells": [(r, p) for _, r, p in loc], "stages": st}; order.append(kk)
        return kk, k, False

    base = cells_at(L)
    for cl in base:
        cl["items"] = content(cl["tri"])
        cl["type"], cl["k"], cl["flip"] = classify(cl["tri"], cl["items"])
        cl["items"] = merge_all(cl["items"], bar_ok)
    logs = []
    ids = [a for a in "ABCDEFGHJKLMNPQRSTUVWXYZ"] + [a + b for a in "ABCDEFGH" for b in "ABCDEFGHJKLMNPQRSTUVWXYZ"]
    for n, kk in enumerate(order):
        t = types[kk]
        logs.append({"id": ids[n], "key": kk, "kind": "tri", "level": 1, "side": L, "w": L, "h": H,
                     "outline": [(0, 0), (L / 2, H), (-L / 2, H)], "cells": t["cells"],
                     "stages": [{"parts": g, "jig": "V block"} for g in t["stages"]], "crosscut": levels == 1})
    idx = {lg["key"]: lg["id"] for lg in logs}
    top = base; top_side = L
    if levels == 2:
        L2 = 2 * L; H2 = L2 * S3 / 2
        by = {(cl["i"], cl["j"], cl["kind"]): cl for cl in base}
        big = cells_at(L2); ptypes = {}; porder = []
        # children: every side-L cell inside the trim got a type; cells outside it are classified on demand
        for cl in big:
            ch = _children(cl["tri"])
            kids = []
            for tri in ch:
                items = content(tri); kk, k, fl = classify(tri, items); items = merge_all(items, bar_ok)
                if kk not in idx:
                    t = types[kk]; n = len(logs)
                    logs.append({"id": ids[n], "key": kk, "kind": "tri", "level": 1, "side": L, "w": L, "h": H,
                                 "outline": [(0, 0), (L / 2, H), (-L / 2, H)], "cells": t["cells"],
                                 "stages": [{"parts": g, "jig": "V block"} for g in t["stages"]], "crosscut": False})
                    idx[kk] = logs[-1]["id"]
                kids.append((idx[kk], tri, k, fl, items))
            found = None
            for k, m, fn in _tri_local(cl["tri"]):
                sig = tuple(sorted((lid, tuple(sorted(_r(v, 2) for v in fn(tri))), ) for lid, tri, _, _, _ in kids))
                full = key_of([(w, r, ccw(fn(p))) for _, _, _, _, items in kids for w, r, p in items])
                if (sig, full) in ptypes: found = ((sig, full), k, m); break
            if not found:
                k, m, fn = _tri_local(cl["tri"])[0]
                sig = tuple(sorted((lid, tuple(sorted(_r(v, 2) for v in fn(tri))), ) for lid, tri, _, _, _ in kids))
                full = key_of([(w, r, ccw(fn(p))) for _, _, _, _, items in kids for w, r, p in items])
                parts = []
                for lid, tri, kc, fl, items in kids:
                    ctri = ccw(tri)
                    parts.append({"log": lid, "pts": ccw(fn(tri)), "flip": fl, "ref": _ref_edge([fn([v])[0] for v in ctri], kc),
                                  "cells": [(r, ccw(fn(p))) for _, r, p in items]})
                ptypes[(sig, full)] = {"parts": parts}; porder.append((sig, full)); found = ((sig, full), k, m)
            cl["type"], cl["k"], cl["flip"] = found
            cl["items"] = [it for _, _, _, _, items in kids for it in items]
        for kk in porder:
            t = ptypes[kk]; n = len(logs)
            logs.append({"id": ids[n], "key": kk, "kind": "tri", "level": 2, "side": L2, "w": L2, "h": H2,
                         "outline": [(0, 0), (L2 / 2, H2), (-L2 / 2, H2)],
                         "cells": [c_ for p in t["parts"] for c_ in p["cells"]],
                         "stages": [{"parts": sorted(t["parts"], key=lambda p: (round(min(v[1] for v in p["pts"]), 3), sum(v[0] for v in p["pts"]))), "jig": "V block"}],
                         "crosscut": True})
            idx[kk] = logs[-1]["id"]
        top = big; top_side = L2
    rows = {}
    for cl in top:
        tri = ccw(cl["tri"])
        puck = {"log": idx[cl["type"]], "pts": [to_board(v) for v in tri], "flip": cl["flip"],
                "ref": tuple(to_board(v) for v in _ref_edge(tri, cl["k"])), "cells": [(r, [to_board(v) for v in p]) for _, r, p in cl["items"]],
                "x": sum(v[0] for v in tri) / 3}
        rows.setdefault(cl["j"], []).append(puck)
    out_rows = []
    Ht = top_side * S3 / 2
    for n, j in enumerate(sorted(rows)):
        pk = sorted(rows[j], key=lambda p: p["x"])
        x0 = min(to_grid(v)[0] for p in pk for v in p["pts"]); x1 = max(to_grid(v)[0] for p in pk for v in p["pts"])
        out_rows.append({"n": n + 1, "pucks": pk, "height": Ht, "length": x1 - x0,
                         "pts": [to_board(v) for v in _hull([to_grid(v) for p in pk for v in p["pts"]])]})
    return {"logs": logs, "rows": out_rows, "info": {"kind": "tri", "side": top_side, "row_height": Ht, "angle": cells.get("angle", 0), "levels": levels}}


def _ref_edge(tri, k):
    """The edge opposite tip k: the log's reference face (the one that lay under the caul)."""
    return (tri[(k + 1) % 3], tri[(k + 2) % 3])


def _children(tri):
    a, b, c = ccw(tri); m = lambda p, q: ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    ab, bc, ca = m(a, b), m(b, c), m(c, a)
    return [[a, ab, ca], [ab, b, bc], [ca, bc, c], [ab, bc, ca]]


def _hull(pts):
    pts = sorted(set((round(x, 5), round(y, 5)) for x, y in pts))
    def half(ps):
        h = []
        for p in ps:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 1e-9: h.pop()
            h.append(p)
        return h
    lo, up = half(pts), half(pts[::-1])
    return lo[:-1] + up[:-1]


# ------------------------------------------------------------------------------------- panels (square-edged strips)
def panel_plan(polys, trim, wood_of):
    """Checkerboard, brick and other all-rectangle faces: each row is a slice of a flat strip panel."""
    by = {}
    for p in polys: by.setdefault(p["slice"], []).append(p)
    types = {}; logs = []; rows = []; ids = [a for a in "ABCDEFGHJKLMNPQRSTUVWXYZ"] + [a + b for a in "ABCDEFGH" for b in "ABCDEFGHJKLMNPQRSTUVWXYZ"]
    for n, sid in enumerate(sorted(by, key=lambda s_: min(v[1] for p in by[s_] for v in p["pts"]))):
        ps = by[sid]; x0 = min(v[0] for p in ps for v in p["pts"]); y0 = min(v[1] for p in ps for v in p["pts"])
        x1 = max(v[0] for p in ps for v in p["pts"]); y1 = max(v[1] for p in ps for v in p["pts"])
        found = None
        for flip in (False, True):
            loc = [(wood_of(p["role"]), p["role"], ccw([((x1 - v[0]) if flip else (v[0] - x0), v[1] - y0) for v in p["pts"]])) for p in ps]
            kk = key_of(loc)
            if kk in types: found = (kk, flip); break
        if not found:
            loc = [(wood_of(p["role"]), p["role"], ccw([(v[0] - x0, v[1] - y0) for v in p["pts"]])) for p in ps]
            kk = key_of(loc); loc.sort(key=lambda t: min(v[0] for v in t[2]))
            types[kk] = ids[len(logs)]
            logs.append({"id": ids[len(logs)], "key": kk, "kind": "panel", "level": 1, "w": x1 - x0, "h": y1 - y0,
                         "outline": [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)], "cells": [(r, p) for _, r, p in loc],
                         "stages": [{"parts": [{"bar": True, "wood": w, "role": r, "pts": p} for w, r, p in loc], "jig": "flat cauls"}], "crosscut": True})
            found = (kk, False)
        box = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        rows.append({"n": n + 1, "height": y1 - y0, "length": x1 - x0, "pts": box,
                     "pucks": [{"log": types[found[0]], "pts": box, "flip": found[1], "ref": (box[0], box[1]),
                                "cells": [(p["role"], p["pts"]) for p in ps]}]})
    return {"logs": logs, "rows": rows, "info": {"kind": "panel"}}


# ------------------------------------------------------------------------------------- eight-point star blocks
def blocks_plan(polys, trim, cells, wood_of):
    """LeMoyne / quilt star blocks built the way square-log quilt boards are: 45 degree strips into a planed band,
    two bands and a square into a quarter log in corner cauls, four quarter logs into a block log, block slices into rows."""
    a = float(cells["side"]); S = a * (2 + math.sqrt(2)); h = S / 2; q = a / math.sqrt(2)
    roles = cells["roles"]                     # {"a": star_a role, "b": star_b role, "field": role}
    cols, rows_n = int(cells["cols"]), int(cells["rows"])
    A, B, F = roles["a"], roles["b"], roles["field"]
    # band, lying flat: parallelogram (star) + right isosceles triangle (field); thickness q, width h at the bottom
    def band(role):
        par = [(0, 0), (a, 0), (a + q, q), (q, q)]; tri = [(a, 0), (h, 0), (h, q)]
        return [(role, par), (F, tri)]
    logs = []
    def add(lg): logs.append(lg); return lg["id"]
    band_out = [(0, 0), (h, 0), (h, q), (q, q)]
    for lid, role in (("A", A), ("B", B)) if wood_of(A) != wood_of(B) else (("A", A),):
        cs = band(role)
        add({"id": lid, "kind": "rect", "shape": "band", "level": 1, "w": h, "h": q, "outline": band_out, "cells": cs,
             "stages": [{"parts": [{"bar": True, "wood": wood_of(r), "role": r, "pts": p, "outside": True} for r, p in cs], "jig": "band cradle"}], "crosscut": False})
    bid_a = "A"; bid_b = "B" if wood_of(A) != wood_of(B) else "A"
    # quarter log, corner (star centre) at the origin, first quadrant: band a along x (below the diagonal), band b mirrored along y
    ba = band(A); bb_ = [(r, ccw([(y, x) for x, y in p])) for r, p in band(B)]
    sq = [(q, q), (h, q), (h, h), (q, h)]
    qid = "C" if bid_b == "B" else "B"
    qcells = ba + bb_ + [(F, sq)]
    add({"id": qid, "kind": "rect", "shape": "quarter", "level": 2, "w": h, "h": h, "outline": [(0, 0), (h, 0), (h, h), (0, h)], "cells": qcells,
         "stages": [{"parts": [{"log": bid_a, "pts": band_out, "cells": ba, "flip": False},
                               {"log": bid_b, "pts": ccw([(y, x) for x, y in band_out]), "cells": bb_, "flip": True},
                               {"bar": True, "wood": wood_of(F), "role": F, "pts": sq}], "jig": "corner cauls"}], "crosscut": False})
    rot = lambda pts, k: [_rot90(v, k) for v in pts]
    hid = chr(ord(qid) + 1); kid = chr(ord(hid) + 1)
    quarters = [{"log": qid, "pts": [(v[0] + h, v[1] + h) for v in ccw(rot([(0, 0), (h, 0), (h, h), (0, h)], k))],
                 "cells": [(r, [(v[0] + h, v[1] + h) for v in ccw(rot(p, k))]) for r, p in qcells], "flip": False, "turn": k} for k in range(4)]
    # two quarter logs make a half log, two half logs (one turned end for end) make the block
    left = sorted([qq for qq in quarters if sum(v[0] for v in qq["pts"]) / 4 < h], key=lambda p: p["pts"][0][1])
    add({"id": hid, "kind": "rect", "shape": "half", "level": 3, "w": h, "h": S, "outline": [(0, 0), (h, 0), (h, S), (0, S)],
         "cells": [c_ for qq in left for c_ in qq["cells"]], "stages": [{"parts": left, "jig": "flat cauls"}], "crosscut": False})
    turn = lambda pts: ccw([(S - x, S - y) for x, y in pts])
    hcells = logs[-1]["cells"]
    halves = [{"log": hid, "pts": [(0, 0), (h, 0), (h, S), (0, S)], "cells": hcells, "flip": False},
              {"log": hid, "pts": turn([(0, 0), (h, 0), (h, S), (0, S)]), "cells": [(r, turn(p)) for r, p in hcells], "flip": False}]
    add({"id": kid, "kind": "rect", "shape": "block", "level": 4, "w": S, "h": S, "outline": [(0, 0), (S, 0), (S, S), (0, S)],
         "cells": [c_ for hh in halves for c_ in hh["cells"]], "stages": [{"parts": halves, "jig": "flat cauls"}], "crosscut": True})
    out_rows = []
    by = {}
    for p in polys: by.setdefault(p["slice"], []).append(p)
    bw = float(cells.get("border", 0)); fid = chr(ord(kid) + 1)
    def bpuck(x0, y0, x1, y1):
        box = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return {"log": fid, "pts": box, "flip": False, "ref": (box[0], box[1]), "cells": [(F, box)]}
    if bw:       # a plain end-grain border in the ground wood: one solid bar, sliced like the logs
        add({"id": fid, "kind": "rect", "shape": "border", "level": 4, "w": S, "h": bw, "outline": [(0, 0), (S, 0), (S, bw), (0, bw)], "cells": [(F, [(0, 0), (S, 0), (S, bw), (0, bw)])],
             "stages": [{"parts": [{"bar": True, "wood": wood_of(F), "role": F, "pts": [(0, 0), (S, 0), (S, bw), (0, bw)]}], "jig": "none"}], "crosscut": True})
    def brow(y0):
        x0 = -S / 2; pk = [bpuck(x0 + i * S, y0, x0 + (i + 1) * S, y0 + bw) for i in range(cols + 1)]
        return {"n": 0, "pucks": pk, "height": bw, "length": (cols + 1) * S, "pts": [(x0, y0), (x0 + (cols + 1) * S, y0), (x0 + (cols + 1) * S, y0 + bw), (x0, y0 + bw)]}
    if bw: out_rows.append(brow(-bw))
    for r in range(rows_n):
        pk = []
        if bw: pk.append(bpuck(-bw, r * S, 0, r * S + S))
        for c in range(cols):
            x0, y0 = c * S, r * S; box = [(x0, y0), (x0 + S, y0), (x0 + S, y0 + S), (x0, y0 + S)]
            pk.append({"log": kid, "pts": box, "flip": False, "ref": (box[0], box[1]),
                       "cells": [(p["role"], p["pts"]) for p in by.get(f"b{r}-{c}", [])]})
        if bw: pk.append(bpuck(cols * S, r * S, cols * S + bw, r * S + S))
        out_rows.append({"n": r + 1, "pucks": pk, "height": S, "length": cols * S + 2 * bw, "pts": [(-bw, r * S), (cols * S + bw, r * S), (cols * S + bw, r * S + S), (-bw, r * S + S)]})
    if bw: out_rows.append(brow(rows_n * S))
    return {"logs": logs, "rows": out_rows, "info": {"kind": "blocks", "side": S}}


def _rot90(v, k):
    x, y = v
    for _ in range(k % 4): x, y = -y, x
    return (x, y)


# ------------------------------------------------------------------------------------- hexagon logs (tumbling blocks)
def hex_plan(polys, trim, cells, wood_of):
    """Tumbling blocks the way makers build them: three diamond bars taped into a hexagon log, the log sliced into
    pucks, the pucks glued into the board inside a clamped frame. A hexagon whose centre is on a side trim line
    goes in as a half puck, so both sides of the glue-up are straight."""
    s = float(cells["side"]); w = S3 * s
    by = {}
    for p in polys: by.setdefault(p["unit"], []).append(p)
    ids = [a for a in "ABCDEFGHJKLMNPQRSTUVWXYZ"]
    types = {}; logs = []; rows = {}
    for unit, ps in by.items():
        if len(ps) != 3: continue
        vs = {}
        for p in ps:
            for v in p["pts"]: vs.setdefault(_r(v), []).append(v)
        c = next((v[0] for v in vs.values() if len(v) == 3), None)
        if c is None: continue
        if c[0] < trim[0] - 1e-6 or c[0] > trim[2] + 1e-6: continue
        if c[1] + s <= trim[1] + 1e-6 or c[1] - s >= trim[3] - 1e-6: continue
        half = "right" if c[0] < trim[0] + 1e-6 else "left" if c[0] > trim[2] - 1e-6 else None
        loc = [(wood_of(p["role"]), p["role"], ccw([(v[0] - c[0] + w / 2, v[1] - c[1] + s) for v in p["pts"]])) for p in ps]
        loc.sort(key=lambda t: -max(v[1] for v in t[2]))
        kk = key_of(loc)
        if kk not in types:
            types[kk] = ids[len(logs)]
            out = [(w / 2, 0), (w, s / 2), (w, 1.5 * s), (w / 2, 2 * s), (0, 1.5 * s), (0, s / 2)]
            logs.append({"id": types[kk], "key": kk, "kind": "hex", "shape": "hex", "level": 1, "side": s, "w": w, "h": 2 * s, "outline": out,
                         "cells": [(r, p_) for _, r, p_ in loc],
                         "stages": [{"parts": [{"bar": True, "wood": w_, "role": r, "pts": p_} for w_, r, p_ in loc], "jig": "tape"}], "crosscut": True})
        out = [(c[0], c[1] - s), (c[0] + w / 2, c[1] - s / 2), (c[0] + w / 2, c[1] + s / 2), (c[0], c[1] + s), (c[0] - w / 2, c[1] + s / 2), (c[0] - w / 2, c[1] - s / 2)]
        cl = [(p["role"], [tuple(v) for v in p["pts"]]) for p in ps]
        if half:
            box = [(c[0], c[1] - s - 1), (c[0] + w, c[1] - s - 1), (c[0] + w, c[1] + s + 1), (c[0], c[1] + s + 1)] if half == "right" else \
                  [(c[0] - w, c[1] - s - 1), (c[0], c[1] - s - 1), (c[0], c[1] + s + 1), (c[0] - w, c[1] + s + 1)]
            out = clip_poly(out, box); cl = [(r, q) for r, q in ((r, clip_poly(q, box)) for r, q in cl) if q]
        j = round(c[1] / (1.5 * s))
        rows.setdefault(j, []).append({"log": types[kk], "pts": out, "flip": False, "half": half, "ref": (out[0], out[1]), "cells": cl, "x": c[0]})
    out_rows = []
    for n, j in enumerate(sorted(rows)):
        pk = sorted(rows[j], key=lambda p: p["x"])
        xs = [v[0] for p in pk for v in p["pts"]]; ys = [v[1] for p in pk for v in p["pts"]]
        out_rows.append({"n": n + 1, "pucks": pk, "height": 2 * s, "length": max(xs) - min(xs),
                         "pts": [(min(xs), min(ys)), (max(xs), min(ys)), (max(xs), max(ys)), (min(xs), max(ys))]})
    return {"logs": logs, "rows": out_rows, "info": {"kind": "hex", "side": s, "angle": 0}}


def plan(polys, trim, cells, wood_of, bar_ok=None):
    kind = cells.get("kind", "panel")
    if kind == "hex": return hex_plan(polys, trim, cells, wood_of)
    if kind == "tri": return tri_plan(polys, trim, cells, wood_of, bar_ok)
    if kind == "blocks": return blocks_plan(polys, trim, cells, wood_of)
    return panel_plan(polys, trim, wood_of)
