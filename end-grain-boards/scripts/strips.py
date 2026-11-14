"""Straight-strip build: cut the board face into parallel strips so every glue-up ends in flat faces.

A board glued from units and zigzag logs leaves V-grooves for glue faces: they can't be planed, sanded
or scraped clean, so squeeze-out and rip errors turn into gaps. Instead, cut the face with parallel
lines (vertical "x" or horizontal "y") and split any bar a line crosses. Each strip is a log: its bars
glue up single file into a panel whose two broad faces are flat and can be cleaned before crosscutting,
and the slices are straight-edged strips that glue up like any end-grain board.

    split(polys, trim, cfg) -> (polys, info)

cfg (design["build"]): {"method": "strips", "axis": "x"|"y", "pitch": inches, "offset": inches,
"min_pitch": 0.5, "max_pitch": 3.0}. Missing axis/pitch/offset are searched: the lines run through
bar corners, and the choice with the fewest split bars wins, with every bar spanning its strip
(single file, so every joint is one flat face) and no slivers.
"""
import math

EPS = 1.5e-3


def _ext(p, ax):
    v = [q[ax] for q in p["pts"]]; return min(v), max(v)


def _lines_in(lo, hi, off, pitch):
    a = math.ceil((lo + 2e-3 - off) / pitch); b = math.floor((hi - 2e-3 - off) / pitch)
    return [off + k * pitch for k in range(a, b + 1)]


def _cut(pts, ax, c, keep_low):
    out = []
    n = len(pts)
    for i in range(n):
        a, b = pts[i - 1], pts[i]
        ia = (a[ax] <= c + EPS) if keep_low else (a[ax] >= c - EPS)
        ib = (b[ax] <= c + EPS) if keep_low else (b[ax] >= c - EPS)
        if ib:
            if not ia: out.append(_ix(a, b, ax, c))
            out.append(b)
        elif ia: out.append(_ix(a, b, ax, c))
    clean = []
    for v in out:
        if not clean or math.dist(v, clean[-1]) > 1e-4: clean.append(v)
    if len(clean) > 1 and math.dist(clean[0], clean[-1]) < 1e-4: clean.pop()
    return clean


def _ix(a, b, ax, c):
    t = (c - a[ax]) / (b[ax] - a[ax]); p = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]; p[ax] = c
    return tuple(p)


def _area(p):
    return 0.5 * sum(p[i - 1][0] * p[i][1] - p[i][0] * p[i - 1][1] for i in range(len(p)))


def _score(polys, trim, ax, pitch, off):
    """(split bars, bars narrower than their strip, slivers) for one choice of lines."""
    cuts = narrow = sliver = 0
    for p in polys:
        lo, hi = _ext(p, ax)
        tl, th = _ext({"pts": [(trim[0], trim[1]), (trim[2], trim[3])]}, ax)
        if hi <= tl + 1e-4 or lo >= th - 1e-4: continue
        ls = _lines_in(lo, hi, off, pitch)
        cuts += len(ls)
        edges = [lo] + ls + [hi]
        k0 = math.floor((lo + 2e-3 - off) / pitch)
        for a, b in zip(edges, edges[1:]):
            if b - a < 0.3: sliver += 1
            sl, sh = off + k0 * pitch, off + (k0 + 1) * pitch
            if a > sl + 1e-3 or b < sh - 1e-3: narrow += 1
            k0 += 1
    return cuts, narrow, sliver


def choose(polys, trim, cfg):
    axes = [{"x": 0, "y": 1}[cfg["axis"]]] if cfg.get("axis") else [0, 1]
    lo_p, hi_p = float(cfg.get("min_pitch", 0.5)), float(cfg.get("max_pitch", 3.0))
    best = None
    for ax in axes:
        vd = {}
        for p in polys:
            for q in p["pts"]: vd.setdefault(round(q[ax], 3), q[ax])
        vals = sorted(vd.values())
        if cfg.get("pitch"):
            pitches = [float(cfg["pitch"])]
        else:
            pd = {}
            for i, a in enumerate(vals):
                for b in vals[i + 1:]:
                    if lo_p - 1e-6 <= b - a <= hi_p + 1e-6: pd.setdefault(round(b - a, 3), b - a)
            pitches = sorted(pd.values())
        for pitch in pitches:
            offs = [float(cfg["offset"])] if cfg.get("offset") is not None else list({round(v % pitch, 3): v % pitch for v in vals}.values())
            for off in offs:
                cuts, narrow, sliver = _score(polys, trim, ax, pitch, off)
                key = (sliver * 50 + narrow * 4 + cuts, -pitch)
                if best is None or key < best[0]:
                    best = (key, ax, pitch, off, cuts, narrow, sliver)
    _, ax, pitch, off, cuts, narrow, sliver = best
    return {"axis": "xy"[ax], "pitch": pitch, "offset": off, "split": cuts, "narrow": narrow, "slivers": sliver}


def split(polys, trim, cfg=None):
    cfg = dict(cfg or {})
    ch = choose(polys, trim, cfg)
    ax = 0 if ch["axis"] == "x" else 1; pitch, off = ch["pitch"], ch["offset"]
    out = []
    for src, p in enumerate(polys):
        pts = [tuple(v) for v in p["pts"]]
        lo, hi = min(v[ax] for v in pts), max(v[ax] for v in pts)
        k = math.floor((lo + 2e-3 - off) / pitch)
        rest = pts
        while rest:
            c = off + (k + 1) * pitch
            if max(v[ax] for v in rest) <= c + 2e-3:
                piece, rest = rest, None
            else:
                piece, rest = _cut(rest, ax, c, True), _cut(rest, ax, c, False)
            if piece and len(piece) >= 3 and abs(_area(piece)) > 1e-5 and _overlaps(piece, trim):
                out.append({"pts": [[round(x, 6), round(y, 6)] for x, y in piece], "role": p["role"], "slice": f"s{k}",
                            "unit": None, "src": src})
            k += 1
    ch["strips"] = len({q["slice"] for q in out})
    ch["slice_type"] = _templates(out, ax, pitch, off)
    for q in out:     # snap strip-line coordinates so neighbouring strips meet exactly
        for v in q["pts"]:
            k = round((v[ax] - off) / pitch); c = off + k * pitch
            if abs(v[ax] - c) < 2e-3: v[ax] = round(c, 6)
            v[0], v[1] = round(v[0], 6), round(v[1], 6)
    return out, ch


def _templates(out, ax, pitch, off):
    """Strips that are windows of one longer strip come from one log. Merge strips into templates (translation
    along the strip only); add the template's missing pieces to the template's first strip as "extra" bars (they
    lie past the trim line, so the slice cut from the log carries them and they are trimmed off). Returns
    {slice id: (template number, "id")}."""
    al = 1 - ax
    by = {}
    for q in out: by.setdefault(q["slice"], []).append(q)
    def rel(q, base, d=0.0):
        r = []
        for v in q["pts"]:
            w = [0.0, 0.0]; w[ax] = v[ax] - base; w[al] = v[al] + d; r.append((round(w[0], 3), round(w[1], 3)))
        return (q["role"], tuple(sorted(r)))
    def span(key):
        vs = [v[al] for v in key[1]]; return min(vs), max(vs)
    full = {}
    temps = []   # {"pieces": {key}, "lo", "hi", "rep": sid, "rep_base": base, "rep_d": 0}
    result = {}
    for sid in sorted(by, key=lambda x: int(x[1:])):
        base = off + int(sid[1:]) * pitch
        keys0 = [rel(q, base) for q in by[sid]]
        placed = False; best = None
        XFN = {(0, 0): "id", (1, 1): "r180", (1, 0): "fx" if ax == 0 else "fy", (0, 1): "fy" if ax == 0 else "fx"}
        for ti, T in enumerate(temps):
            for (ma, ml), xname in XFN.items():
                raw = []
                for q in by[sid]:
                    r = []
                    for v in q["pts"]:
                        a_ = v[ax] - base; l_ = v[al]
                        if ma: a_ = pitch - a_
                        if ml: l_ = -l_
                        r.append((a_, l_))
                    raw.append((q["role"], r))
                def key(role, r, d):
                    out_ = []
                    for a_, l_ in r:
                        w = [0.0, 0.0]; w[ax] = a_; w[al] = l_ + d; out_.append((round(w[0], 3), round(w[1], 3)))
                    return (role, tuple(sorted(out_)))
                role0, r0 = raw[0]; lo0 = min(l_ for _, l_ in r0)
                cands = sorted({T["raw"][tk] - lo0 for tk in T["pieces"] if tk[0] == role0})
                for d in cands:
                    ks = [key(role, r, d) for role, r in raw]
                    ok = True; hits = 0
                    for k in ks:
                        if k in T["pieces"]: hits += 1; continue
                        lo, hi = span(k)
                        if any(span(t)[1] > lo + 1e-3 and span(t)[0] < hi - 1e-3 and _sat(k[1], t[1]) for t in T["pieces"]):
                            ok = False; break
                    if ok and hits >= max(min(len(ks), 2), 0.6 * len(ks)):
                        sc = (hits, xname == "id")
                        if best is None or sc > best[0]:
                            best = (sc, ti, xname, d, ma, ml, ks, raw)
            if best: break
        if best:
            _, ti, xname, d, ma, ml, ks, raw = best; T = temps[ti]
            for k, (role, r) in zip(ks, raw):
                if k not in T["pieces"]:
                    T["pieces"].add(k); lo, hi = span(k); T["lo"] = min(T["lo"], lo); T["hi"] = max(T["hi"], hi)
                    T["raw"][k] = min(l_ for _, l_ in r) + d
                    T["pts"][k] = [(a_, l_ + d) for a_, l_ in r]
            result[sid] = (ti, xname); full[sid] = (ti, d, ma, ml, set(ks)); placed = True
        if not placed:
            ks = set(keys0)
            temps.append({"pts": {k: [(v[ax] - base, v[al]) for v in q["pts"]] for k, q in zip(keys0, by[sid])}, "raw": {k: min(v[al] for v in q["pts"]) for k, q in zip(keys0, by[sid])}, "pieces": ks, "lo": min(span(k)[0] for k in ks), "hi": max(span(k)[1] for k in ks), "rep": sid, "base": base})
            result[sid] = (len(temps) - 1, "id"); full[sid] = (len(temps) - 1, 0.0, 0, 0, set(keys0))
    for sid, (ti, d, ma, ml, have) in full.items():
        T = temps[ti]; base = off + int(sid[1:]) * pitch
        for k in T["pieces"] - have:
            ab = []
            for a_, l_ in T["pts"][k]:
                l2 = l_ - d
                if ml: l2 = -l2
                a2 = pitch - a_ if ma else a_
                w = [0.0, 0.0]; w[ax] = a2 + base; w[al] = l2; ab.append(w)
            cx = sum(w[0] for w in ab) / len(ab); cy = sum(w[1] for w in ab) / len(ab)
            ab.sort(key=lambda w: math.atan2(w[1] - cy, w[0] - cx))
            out.append({"pts": ab, "role": k[0], "slice": sid, "unit": None, "src": None, "extra": True})
    return result


def _overlaps(pts, trim):
    xs = [v[0] for v in pts]; ys = [v[1] for v in pts]
    return min(xs) < trim[2] - 1e-4 and max(xs) > trim[0] + 1e-4 and min(ys) < trim[3] - 1e-4 and max(ys) > trim[1] + 1e-4


def _sat(a, b):
    """True if two convex polygons (vertex sets, any order) overlap by more than a hair."""
    def hull(ps):
        cx = sum(p[0] for p in ps) / len(ps); cy = sum(p[1] for p in ps) / len(ps)
        return sorted(ps, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
    A, B = hull(list(a)), hull(list(b))
    for P in (A, B):
        for i in range(len(P)):
            ex, ey = P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]
            n = (-ey, ex); ln = math.hypot(*n) or 1
            pa = [(q[0] * n[0] + q[1] * n[1]) / ln for q in A]; pb = [(q[0] * n[0] + q[1] * n[1]) / ln for q in B]
            if min(max(pa), max(pb)) - max(min(pa), min(pb)) < 2e-3: return False
    return True
