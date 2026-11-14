"""Row planks: logs glued side by side, long grain to long grain, into a plank whose end is one row of the board.
Every crosscut of the plank is then a whole row, so nothing is assembled from loose slices.

Rows that are the same sequence of logs come off the same plank: as cut, turned end for end, or turned over.
A row that is the same sequence slid along comes off it too; the plank is made a log or two wider to cover it.

  plan(rows) -> [{"id", "pucks": [{"log", "flip", "pts", "cells", "ref"}], "n", "width", "height", "uses": [{"row", "op", "at"}]}]

Plank coordinates: x across the plank from 0, y through its thickness from 0. Each row gets "plank", "op", "at".
"""
import math
from logs import key_of, ccw

# as cut; turned end for end (same face up); turned over sideways (like a page); rolled over about its length
OPS = (("", 1, 1), ("r", -1, -1), ("m", -1, 1), ("f", 1, -1))
OP_TEXT = {"": "as cut", "r": "turned end for end", "m": "turned over like a page", "f": "rolled over, far edge toward you"}
OP_SHORT = {"": "as cut", "r": "end for end", "m": "turned over", "f": "rolled over"}


def _moments(items):
    """Per wood role: area, centroid and second moments. The same for the same woods in the same places,
    however the pieces happen to be cut up."""
    acc = {}
    for role, pts in items:
        pts = ccw(pts); x0, y0 = pts[0]
        for i in range(1, len(pts) - 1):
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            a = ((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / 2
            m = acc.setdefault(role, [0.0] * 6)
            m[0] += a; m[1] += a * (x0 + x1 + x2) / 3; m[2] += a * (y0 + y1 + y2) / 3
            m[3] += a * (x0 * x0 + x1 * x1 + x2 * x2 + x0 * x1 + x1 * x2 + x0 * x2) / 6
            m[4] += a * (y0 * y0 + y1 * y1 + y2 * y2 + y0 * y1 + y1 * y2 + y0 * y2) / 6
            m[5] += a * (x0 * y0 + x1 * y1 + x2 * y2 + (x0 * y1 + x1 * y0 + x1 * y2 + x2 * y1 + x0 * y2 + x2 * y0) / 2) / 6
    return tuple(sorted((r, tuple(round(v, 2) + 0.0 for v in m)) for r, m in acc.items()))


def _local(row, ax, su, sv):
    """The row's slices in order along the row after an op, each with a key that says what it is and how it sits."""
    out = []
    for pk in row["pucks"]:
        loc = lambda p: (su * (p[0] * ax[0] + p[1] * ax[1]), sv * (-p[0] * ax[1] + p[1] * ax[0]))
        o = [loc(v) for v in pk["pts"]]; cu = sum(v[0] for v in o) / len(o); cv = sum(v[1] for v in o) / len(o)
        rel = lambda ps: [(v[0] - cu, v[1] - cv) for v in ps]
        cells = [(r, [loc(v) for v in p]) for r, p in pk["cells"]]
        out.append({"key": (key_of([("", "", rel(o))]), _moments([(r, rel(p)) for r, p in cells])), "cu": cu, "cv": cv,
                    "log": pk["log"], "flip": bool(pk.get("flip")) ^ (su * sv < 0),      # a mirrored log is the log turned end for end
                    "pts": o, "cells": cells, "ref": [loc(v) for v in pk["ref"]] if pk.get("ref") else None})
    out.sort(key=lambda t: t["cu"])
    return out


def _move(pucks, du, dv):
    mv = lambda ps: [(x + du, y + dv) for x, y in ps]
    for p in pucks:
        p["pts"] = mv(p["pts"]); p["cells"] = [(r, mv(q)) for r, q in p["cells"]]; p["cu"] += du; p["cv"] += dv
        if p["ref"]: p["ref"] = mv(p["ref"])


def _find(seq, sub):
    n, m = len(seq), len(sub)
    for i in range(n - m + 1):
        if seq[i:i + m] == sub: return i
    return None


def _fit(pl, lp, maxw):
    """Where this row sits on the plank, widening the plank if the row overhangs one end. None: a different plank."""
    seq = [p["key"] for p in pl["pucks"]]; tk = [p["key"] for p in lp]; m = len(tk)
    at = _find(seq, tk)
    if at is not None: return at
    sh = _find(tk, seq)
    if sh is not None:                                   # the row covers the plank and more
        _move(lp, pl["pucks"][0]["cu"] - lp[sh]["cu"], pl["pucks"][0]["cv"] - lp[sh]["cv"])
        for u in pl["uses"]: u["at"] += sh
        pl["pucks"] = lp; return 0
    pitch = (lp[-1]["cu"] - lp[0]["cu"]) / max(1, m - 1)
    for ov in range(m - 1, max(m // 2, 1) - 1, -1):      # the row overlaps one end by at least half its length
        if (len(seq) + m - ov + 1) * pitch > maxw: break     # a plank wider than the sled can crosscut is no use
        if seq[-ov:] == tk[:ov]:
            a = pl["pucks"][len(seq) - ov]; _move(lp, a["cu"] - lp[0]["cu"], a["cv"] - lp[0]["cv"])
            pl["pucks"] += lp[ov:]; return len(seq) - ov
        if seq[:ov] == tk[-ov:]:
            a = pl["pucks"][0]; _move(lp, a["cu"] - lp[m - ov]["cu"], a["cv"] - lp[m - ov]["cv"])
            for u in pl["uses"]: u["at"] += m - ov
            pl["pucks"] = lp[:m - ov] + pl["pucks"]; return 0
    return None


def plan(rows, angle=0.0, maxw=24.0):
    planks = []; ax = (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
    for row in rows:
        at = None
        for pl in planks:
            for name, su, sv in OPS:
                at = _fit(pl, _local(row, ax, su, sv), maxw)
                if at is not None:
                    pl["uses"].append({"row": row["n"], "op": name, "at": at}); row["plank"] = pl["id"]; row["op"] = name; break
            if at is not None: break
        if at is None:
            pl = {"id": f"P{len(planks) + 1}", "pucks": _local(row, ax, 1, 1), "uses": [{"row": row["n"], "op": "", "at": 0}]}
            planks.append(pl); row["plank"] = pl["id"]; row["op"] = ""
    for pl in planks:
        u0 = min(v[0] for p in pl["pucks"] for v in p["pts"]); v0 = min(v[1] for p in pl["pucks"] for v in p["pts"])
        _move(pl["pucks"], -u0, -v0)
        for p in pl["pucks"]:
            del p["key"], p["cu"], p["cv"]
            p["pts"] = ccw(p["pts"]); p["cells"] = [(r, ccw(q)) for r, q in p["cells"]]
        pl["n"] = len(pl["pucks"])
        pl["width"] = max(v[0] for p in pl["pucks"] for v in p["pts"]); pl["height"] = max(v[1] for p in pl["pucks"] for v in p["pts"])
    # where each row's whole crosscut lies on the board, overhang included: plank coordinates -> board
    for pl in planks:
        for u in pl["uses"]:
            row = next(r for r in rows if r["n"] == u["row"]); row["at"] = u["at"]
            su, sv = next((a, b) for nm, a, b in OPS if nm == u["op"])
            lp = _local(row, ax, su, sv); a = pl["pucks"][u["at"]]["pts"]; b = lp[0]["pts"]
            du = sum(v[0] for v in a) / len(a) - lp[0]["cu"]; dv = sum(v[1] for v in a) / len(a) - lp[0]["cv"]
            def back(p, su=su, sv=sv, du=du, dv=dv):
                lu, lv = su * (p[0] - du), sv * (p[1] - dv)
                return (lu * ax[0] - lv * ax[1], lu * ax[1] + lv * ax[0])
            row["slice"] = {"cells": [(r, [back(v) for v in q]) for pk in pl["pucks"] for r, q in pk["cells"]],
                            "outline": [back(v) for v in _hull_pts([v for pk in pl["pucks"] for v in pk["pts"]])],
                            "mark": [back((0.3 * pl["height"], pl["height"] / 2)), back((0.3 * pl["height"] + min(1.6, pl["width"] / 5), pl["height"] / 2))], "face_up": su * sv > 0}
    return planks


def _hull_pts(pts):
    from logs import _hull
    return _hull(pts)
