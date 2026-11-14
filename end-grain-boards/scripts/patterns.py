"""Pattern generators for end-grain boards.

Every generator returns the board face as a list of polygons, inches, y up:

    {"pts": [[x, y], ...] (counter-clockwise, convex),   one bar's cross-section
     "role": "a",                                       species role (design["species"] maps it)
     "slice": "r3",                                     the slice (one log cross-section) it lands in
     "unit": "r3/h2" or None}                           the sub-assembly glued before the log

plus "trim": [x0, y0, x1, y1] (the finished board), and "notes" for the plan.

The face is what the cut end of a log looks like: each polygon is a long bar of that cross-section,
bars are glued into units, units (or bars) into logs, logs are crosscut into slices, and slices are
glued edge to edge into the board. So any pattern made of convex polygons can be built this way.
A design can also give "polygons" and "trim" directly ("pattern": "custom").
"""
import math

S3 = math.sqrt(3)


def _poly(pts, role, slc, unit=None):
    return {"pts": [[round(x, 6), round(y, 6)] for x, y in pts], "role": role, "slice": slc, "unit": unit}


def _fit(target, unit, offset=0.0, lo=1):
    """Count of repeating units whose span (offset + n*unit) is nearest the target size."""
    n = max(lo, round((target - offset) / unit))
    return n


# --------------------------------------------------------------------------------------------
# Rhombille tiling (60 degree rhombi): tumbling blocks (3D cubes) and six-point stars share it.
# Pointy-top hexagons of circumradius s, each made of three rhombi: lid (top), left and right.
# --------------------------------------------------------------------------------------------
def _rhombille(p, board, colour):
    s = float(p.get("side", 1.25))
    w = S3 * s
    # the logs are triangles of side 3s standing in columns 1.5 hexagons wide: the board is a whole number of columns
    kcol = int(p.get("columns") or max(2, round(board["width"] / (1.5 * w))))
    cols = int(math.ceil(kcol * 1.5 + 0.5)) + 1
    rows = int(p.get("rows") or _fit(board["length"], 1.5 * s, -0.5 * s, 2))
    polys = []
    for j in range(-4, rows + 4):
        cy = 1.5 * j * s
        for col in range(-3, cols + 3):
            cx = col * w + (w / 2 if j % 2 else 0)
            i = col - j // 2                      # axial coordinate
            T, B = (cx, cy + s), (cx, cy - s)
            UR, LR = (cx + w / 2, cy + s / 2), (cx + w / 2, cy - s / 2)
            UL, LL = (cx - w / 2, cy + s / 2), (cx - w / 2, cy - s / 2)
            C = (cx, cy)
            unit = f"r{j}/h{col}"
            for name, pts in (("lid", [C, UR, T, UL]), ("left", [C, UL, LL, B]), ("right", [C, B, LR, UR])):
                role = colour(name, i, j); mot = None
                if isinstance(role, tuple):               # (role, (i, j) of the 6-way vertex at the motif's centre)
                    role, (mi, mj) = role; mc = mi + mj // 2
                    mot = [mc * w + (w / 2 if mj % 2 else 0), 1.5 * mj * s - s]
                q = _poly(pts, role, f"r{j}", unit)
                if mot: q["motif"] = mot
                polys.append(q)
    y0 = float(p.get("y0", -s / 2)) * 1.0
    trim = [0.0, y0, kcol * 1.5 * w, y0 + 1.5 * (rows - 1) * s + s]
    _rhombille.cells = {"kind": "tri", "side": 3 * s, "origin": [0.0, -s], "angle": 90, "levels": int(p.get("levels", 1))}
    def hexc(i, j):                               # centre of hexagon (i, j) in axial coordinates
        col = i + j // 2
        return (col * w + (w / 2 if j % 2 else 0), 1.5 * j * s)
    _rhombille.hexc = hexc
    _rhombille.vertex = lambda i, j: (hexc(i, j)[0], hexc(i, j)[1] - s)      # the 6-way vertex at the bottom of hexagon (i, j)
    _rhombille.span = [(i, j) for j in range(-2, rows + 3) for i in range(-3 - j // 2, cols + 3 - j // 2)]
    return polys, trim, rows, kcol


def cubes(p, board):
    """Tumbling blocks: every hexagon is a cube seen corner-on; lid, left and right faces each get
    their own species (light lid, medium and dark sides reads best)."""
    polys, trim, rows, cols = _rhombille(p, board, lambda name, i, j: name)
    s = float(p.get("side", 1.25))
    notes = [f"Every cube is three {s:g}\" diamonds: lid, left face, right face.",
             "Light lid, medium left, dark right reads as light from the top left; swap left and right to move the light."]
    if p.get("build", "hexagon") != "triangle":
        # Built the way makers build tumbling blocks: three diamond bars taped into a hexagon log, sliced into pucks.
        # The side cuts run through the centres of every other row (half pucks there), the end cuts across the upright flats.
        w = S3 * s; n = max(2, round(board["width"] / (w / 2)))
        return {"polygons": polys, "trim": [0.0, trim[1], n * w / 2, trim[3]], "roles": ["lid", "left", "right"],
                "cells": {"kind": "hex", "side": s}, "notes": notes}
    return {"polygons": polys, "trim": trim, "roles": ["lid", "left", "right"], "cells": _rhombille.cells,
            "period": 1.5 * s,
            "centers": [(c[0], c[1] + 0.5 * s) for c in (_rhombille.hexc(i, j) for i, j in _rhombille.span)],     # both end cuts run through the middle of a row of lids
            "notes": notes}


def stars6(p, board):
    """Six-point stars on the same rhombille tiling. A star is the six rhombi meeting at one of the
    tiling's 6-way vertices; every third such vertex (a 3-colouring of their triangular lattice) gets
    a star, so no rhombus is in two stars. The rest is field. 'shade': true colours the star rhombi
    by orientation (star_lid / star_left / star_right) for a faceted 3D star. 'spacing': touching (2/3 of
    the board is star), open (default, half) or sparse (2/7)."""
    shade = bool(p.get("shade", False))
    spacing = p.get("spacing", "open")

    def chosen(i, j):
        if spacing == "touching":          # every third 6-way vertex: stars meet tip to tip
            return (i + 2 * j) % 3 == 0
        if spacing == "sparse":            # one in seven: stars stand well apart
            return (i + 3 * j) % 7 == 0
        return i % 2 == 0 and j % 2 == 0   # "open": one in four, stars a rhombus apart

    def colour(name, i, j):
        # the rhombus's two 60-degree corners are 6-way vertices: B of hexes (i,j), (i-1,j+1) [UL], (i,j+1) [UR]
        ends = {"lid": ((i - 1, j + 1), (i, j + 1)), "left": ((i - 1, j + 1), (i, j)),
                "right": ((i, j + 1), (i, j))}[name]
        for e in ends:
            if chosen(*e): return (f"star_{name}" if shade else "star", e)
        return "field"

    polys, trim, rows, cols = _rhombille(p, board, colour)
    roles = (["star_lid", "star_left", "star_right"] if shade else ["star"]) + ["field"]
    return {"polygons": polys, "trim": trim, "roles": roles, "cells": _rhombille.cells,
            "centers": [_rhombille.vertex(i, j) for i, j in _rhombille.span if chosen(i, j)],
            "motif": {"radius": S3 * float(p.get("side", 1.25)), "ground": "field"},
            "notes": [f"Six {float(p.get('side', 1.0)):g}\" diamonds around a point make each star ({spacing} spacing); the field is the same diamond in the ground wood.",
                      "Every piece is a 60 degree diamond or a triangle cut at the same blade tilt."]}


def snowflakes(p, board):
    """Snowflakes on the rhombille tiling. Every rhombus joins two neighbouring 6-way vertices of the
    tiling's triangular lattice, so a snowflake is drawn as lattice edges: six arms of 'arm' edges from
    a centre, with side branches of 'branch' edges at 60 degrees from each arm point listed in
    'branch_at'. Flakes repeat 'spacing' edges apart across the board and 'rise' x 2 hexagon rows apart along it
    ('stagger' shifts every other flake row half a spacing). Roles: flake, field
    (and core, the six rhombi at the centre, if 'core' is true)."""
    arm = int(p.get("arm", 3)); branch = int(p.get("branch", 1))
    branch_at = [int(b) for b in p.get("branch_at", [1, 2] if arm >= 3 else [1])]
    m = int(p.get("spacing", 2 * arm + 1)); core = bool(p.get("core", False))
    rot = lambda d, k: d if k == 0 else rot((-d[1], d[0] + d[1]), k - 1)
    dirs = [rot((1, 0), k) for k in range(6)]
    edges, cores = {}, set()
    def add(a, b, centre=False, c=None):
        e = (min(a, b), max(a, b)); edges[e] = c
        if centre: cores.add(e)
    flake = []
    for d in dirs:
        for t in range(arm):
            flake.append((((t * d[0], t * d[1]), ((t + 1) * d[0], (t + 1) * d[1])), t == 0))
        for b in branch_at:
            if b >= arm: continue
            P = (b * d[0], b * d[1])
            for side in (1, 5):
                e = rot(d, side)
                for t in range(branch):
                    flake.append((((P[0] + t * e[0], P[1] + t * e[1]), (P[0] + (t + 1) * e[0], P[1] + (t + 1) * e[1])), False))
    # centre the flake lattice on the middle of the board
    s = float(p.get("side", 0.75)); w = S3 * s
    cols = int(p.get("cols") or _fit(board["width"], w, -0.5 * w, 2))
    rows = int(p.get("rows") or _fit(board["length"], 1.5 * s, -0.5 * s, 2))
    jc = rows // 2; ic = cols // 2 - jc // 2
    ic -= (ic + 2 * jc) % 3            # flake centres on the corners of the triangle logs
    R = arm + 2
    # flake centres: columns 'spacing' apart, flake rows 2k hexagon rows apart (straight up, so every
    # flake row lines up with the hexagon rows and the row logs repeat every 2k rows)
    k = int(p.get("rise") or max(1, round(m / S3)))
    stagger = bool(p.get("stagger", False))
    fc = []
    for a in range(-8, 9):
        for b in range(-8, 9):
            c = (ic + a * m - b * k + ((m // 2) if stagger and b % 2 else 0), jc + 2 * k * b)
            fc.append(c)
            for (u, v), centre in flake:
                add((c[0] + u[0], c[1] + u[1]), (c[0] + v[0], c[1] + v[1]), centre, c)

    def colour(name, i, j):
        ends = {"lid": ((i - 1, j + 1), (i, j + 1)), "left": ((i - 1, j + 1), (i, j)),
                "right": ((i, j + 1), (i, j))}[name]
        e = (min(ends), max(ends))
        if e in cores and core: return ("core", edges[e])
        return ("flake", edges[e]) if e in edges else "field"

    polys, trim, rows, cols = _rhombille(dict(p, side=s, cols=cols, rows=rows), board, colour)
    roles = (["core"] if core else []) + ["flake", "field"]
    return {"polygons": polys, "trim": trim, "roles": roles, "cells": _rhombille.cells,
            "centers": [_rhombille.vertex(*c) for c in fc],
            "motif": {"radius": S3 * s * (arm + (0.5 if any(x == arm - 1 for x in branch_at) and branch else 0)), "ground": "field"},
            "notes": [f"Each snowflake has six arms of {arm} diamonds with side branches, and the flakes repeat every {m} diamonds.",
                      "Every piece is a 60 degree diamond or a triangle cut at the same blade tilt."]}


# --------------------------------------------------------------------------------------------
# Eight-point (LeMoyne) star blocks: 8 rhombi of 45 degrees, 4 corner squares, 4 edge triangles.
# Built as quarter-block units (2 rhombi, a square, 2 half-triangles), four quarters per block log.
# --------------------------------------------------------------------------------------------
def stars8(p, board):
    a = float(p.get("side", 1.0))                 # rhombus side
    S = a * (2 + math.sqrt(2))                    # block side
    alternate = bool(p.get("alternate", True))
    bw = float(p.get("border", 1.0))              # plain border in the ground wood, so no star point is cut by the edge
    cols = int(p.get("cols") or _fit(board["width"] - 2 * bw, S))
    rows = int(p.get("rows") or _fit(board["length"] - 2 * bw, S))
    h = S / 2
    rt = 2 * a * math.cos(math.radians(22.5))

    def P(r, deg):
        return (r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)))

    def quarter():
        """First quadrant of a block centred on the origin; the others are this turned 90 degrees."""
        out = []
        for k, phi in ((0, 22.5), (1, 67.5)):
            pts = [(0, 0), P(a, phi - 22.5), P(rt, phi), P(a, phi + 22.5)]
            out.append((pts, ("star_a" if k == 0 else "star_b") if alternate else "star_a"))
        n = P(a, 45)
        out.append(([n, P(rt, 22.5), (h, h), P(rt, 67.5)], "field"))           # corner square
        out.append(([(a, 0), (h, 0), P(rt, 22.5)], "field"))                    # half of the right triangle
        out.append(([(0, a), P(rt, 67.5), (0, h)], "field"))                    # half of the top triangle
        return out

    def rot(pt, q):
        x, y = pt
        for _ in range(q):
            x, y = -y, x
        return (x, y)

    polys = []
    for r in range(rows):
        for c in range(cols):
            cx, cy = (c + 0.5) * S, (r + 0.5) * S
            for q in range(4):
                for pts, role in quarter():
                    pts = [rot(pt, q) for pt in pts]
                    polys.append(_poly([(x + cx, y + cy) for x, y in pts], role, f"b{r}-{c}", f"b{r}-{c}/q{q}"))
    roles = ["star_a", "star_b", "field"] if alternate else ["star_a", "field"]
    X, Y = cols * S, rows * S
    if bw:
        for x0, y0, x1, y1 in ((-bw, -bw, X + bw, 0), (-bw, Y, X + bw, Y + bw), (-bw, 0, 0, Y), (X, 0, X + bw, Y)):
            polys.append(_poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "field", "border"))
    return {"polygons": polys, "trim": [-bw, -bw, X + bw, Y + bw], "roles": roles,
            "cells": {"kind": "blocks", "side": a, "cols": cols, "rows": rows, "border": bw,
                      "roles": {"a": "star_a", "b": "star_b" if alternate else "star_a", "field": "field"}},
            "notes": [f"{rows} x {cols} star blocks, each {S:.3f}\" square. A block is four identical quarter logs turned 90 degrees to each other.",
                      "The ground triangles on each block edge are made as two halves, one in each quarter; that glue line joins the same wood and disappears in end grain."]}


# --------------------------------------------------------------------------------------------
# Checkerboard: square bars in alternating species, rows shifted one square.
# --------------------------------------------------------------------------------------------
def checker(p, board):
    s = float(p.get("side", 1.5))
    cols = int(p.get("cols") or _fit(board["width"], s))
    rows = int(p.get("rows") or _fit(board["length"], s))
    polys = []
    for j in range(rows):
        for i in range(cols):
            x, y = i * s, j * s
            polys.append(_poly([(x, y), (x + s, y), (x + s, y + s), (x, y + s)],
                               "a" if (i + j) % 2 == 0 else "b", f"r{j}"))
    return {"polygons": polys, "trim": [0, 0, cols * s, rows * s], "roles": ["a", "b"], "cells": {"kind": "panel"},
            "notes": [f"{rows} rows of {cols} squares, {s:g}\" each."]}


# --------------------------------------------------------------------------------------------
# Brick: rectangles, alternating species along the row, each row offset half a brick.
# --------------------------------------------------------------------------------------------
def brick(p, board):
    bw, bh = float(p.get("brick", 2.0)), float(p.get("course", 1.0))
    cols = int(p.get("cols") or _fit(board["width"], bw, -0.5 * bw))
    rows = int(p.get("rows") or _fit(board["length"], bh))
    polys = []
    for j in range(rows):
        for i in range(cols + 1 if j % 2 == 0 else cols):
            x, y = (i * bw - bw / 2 if j % 2 == 0 else i * bw), j * bh
            polys.append(_poly([(x, y), (x + bw, y), (x + bw, y + bh), (x, y + bh)],
                               "a" if i % 2 == 0 else "b", f"r{j}"))
    return {"polygons": polys, "trim": [0, 0, cols * bw, rows * bh], "roles": ["a", "b"], "cells": {"kind": "panel"},
            "notes": [f"{rows} courses; alternate courses carry a half brick past each end that is trimmed off."]}


# --------------------------------------------------------------------------------------------
# Triangle tiling helpers: lattice points (i, j) -> ((i + j/2)·s, j·s·√3/2). Row j holds the up
# triangles (i,j),(i+1,j),(i,j+1) and down triangles (i+1,j),(i+1,j+1),(i,j+1).
# --------------------------------------------------------------------------------------------
def _tri_rows(s, board, p):
    h = s * S3 / 2
    rows = int(p.get("rows") or _fit(board["length"], h))
    width = float(p.get("width") or board["width"])
    cols = int(p.get("cols") or max(1, round(width / s)))
    L = lambda i, j: ((i + j / 2) * s, j * h)
    out = []
    pad = int(p.get("_pad", 0))
    for j in range(-pad, rows + pad):
        i0 = -((j + 1) // 2) - 1 - pad
        for i in range(i0, i0 + cols + 3 + 2 * pad):
            out.append(("up", j, [L(i, j), L(i + 1, j), L(i, j + 1)]))
            out.append(("down", j, [L(i + 1, j), L(i + 1, j + 1), L(i, j + 1)]))
    return out, [0.0, 0.0, cols * s, rows * h], rows, cols, h


def geodomes(p, board):
    """Geodesic domes: the board is an equilateral-triangle tiling. Flat-top hexagons of 'freq'
    triangles a side tile it (6·freq² triangles each), and every triangle is a flat facet of a
    sphere over its hexagon: lit by a light from the upper left, its brightness picks one of the
    tone woods (roles tone1 = lightest ... toneN = darkest): the two sides facing the light lightest,
    the side away from it darkest, the crown a tone lighter and the rim a tone darker ('rim': false
    to skip). Rows of triangles are the slices; the domes repeat every 2·'freq' rows, so 2·'freq' row logs."""
    s = float(p.get("side", 0.8)); n = int(p.get("freq", 4)); K = int(p.get("tones", 4))
    lx, ly, lz = p.get("light", [-0.55, 0.6, 0.58])
    ln = math.sqrt(lx * lx + ly * ly + lz * lz); lx, ly, lz = lx / ln, ly / ln, lz / ln
    p = dict(p); p["rows"] = int(p.get("rows") or max(n, n * round(board["length"] / (s * S3 / 2) / n))); p["_pad"] = 2 * n
    tris, trim, rows, cols, h = _tri_rows(s, board, p)
    # dome centres: lattice spanned by A = n(1,1) and B = n(-1,2) in (i, j); shift so a dome sits mid-board
    ox, oy = trim[2] / 2, trim[3] / 2
    jc = round(oy / h / n) * n; ic = round(ox / s - jc / 2)
    cen = lambda i, j: ((i + j / 2) * s, j * h)
    A, B = (n, n), (-n, 2 * n)
    def dome_of(c):
        best = None
        # solve approx lattice coords then search neighbours
        x, y = c; jj = y / h; ii = x / s - jj / 2
        di, dj = ii - ic, jj - jc
        # (di, dj) = a·A + b·B  ->  a = (2di + dj)/(3n), b = (dj - di)/(3n)
        a0 = (2 * di + dj) / (3 * n); b0 = (dj - di) / (3 * n)
        for a in range(math.floor(a0) - 1, math.floor(a0) + 3):
            for b in range(math.floor(b0) - 1, math.floor(b0) + 3):
                ci, cj = ic + a * A[0] + b * B[0], jc + a * A[1] + b * B[1]
                cx, cy = cen(ci, cj)
                d = math.hypot(x - cx, y - cy)
                if best is None or d < best[0] - 1e-9: best = (d, cx, cy)
        return best[1], best[2]
    # each dome is faceted like a geodesic dome: six sectors (one per hexagon side) and 'freq' rings of
    # triangles, every sector-ring band a flat facet tilted more steeply towards the rim
    def facet(dx, dy):
        ang = math.degrees(math.atan2(dy, dx))
        k = int(((ang - 0) % 360) // 60)                  # sector k spans 60k .. 60k+60, its side's normal at 60k+30
        nrm = math.radians(60 * k + 30)
        d = dx * math.cos(nrm) + dy * math.sin(nrm)       # distance towards that side
        ring = min(n - 1, int(d / h))
        return k, ring
    offs = []
    for kind, j, pts in tris:
        c = (sum(q[0] for q in pts) / 3, sum(q[1] for q in pts) / 3)
        cx, cy = dome_of(c)
        offs.append(facet(c[0] - cx, c[1] - cy))
    # the six sides lit in order of how squarely they face the light: lit pair, half-lit pair, shade, dark;
    # the crown (centre ring) one tone lighter and the rim (outer ring) one darker, so each dome bulges
    la = math.atan2(ly, lx)
    order = sorted(range(6), key=lambda k: -math.cos(math.radians(60 * k + 30) - la))
    base = {4: [1, 1, 2, 2, 3, 4], 3: [1, 1, 2, 2, 3, 3], 5: [1, 2, 2, 3, 4, 5]}.get(K, [1 + i * (K - 1) // 5 for i in range(6)])
    sector_tone = {k: base[r] for r, k in enumerate(order)}
    mode = p.get("shade", "light")
    dark = set(order[3:])                      # the three sides turned away from the light
    def tone_of(f):
        k, ring = f; t = sector_tone[k]
        if mode == "rings":                    # concentric: pale crown, darker towards the rim
            return max(1, min(K, 1 + round(ring * (K - 1) / max(1, n - 1))))
        if mode == "dome":                     # rings, with the far side of each ring a tone darker
            return max(1, min(K, 1 + ring + (1 if k in dark and ring > 0 else 0)))
        if ring == 0 and n > 2: t -= 1
        if ring == n - 1 and n > 2 and p.get("rim", True): t += 1
        return max(1, min(K, t))
    tone = {o: tone_of(o) for o in set(offs)}
    polys = [_poly(pts, f"tone{tone[o]}", f"r{j}") for (kind, j, pts), o in zip(tris, offs)]
    roles = [f"tone{k}" for k in range(1, K + 1)]
    return {"polygons": polys, "trim": trim, "roles": roles,
            "cells": {"kind": "tri", "side": n * s, "origin": list(cen(ic, jc)), "angle": 0},
            "centers": [cen(ic + a * A[0] + b * B[0], jc + a * A[1] + b * B[1]) for a in range(-4, 5) for b in range(-4, 5)],
            "notes": [f"Domes are hexagons {n} triangles to a side ({6 * n * n} facets, {2 * n * s:.2f}\" across), shaded in {K} woods as if lit from the upper left.",
                      f"Every bar is the same {s:g}\" equilateral triangle: one saw setup for the whole board."]}


def kagome(p, board):
    """Kagome (trihexagonal) star lattice: regular hexagons on a triangular grid, the gaps between
    them up- and down-pointing triangles; every hexagon is ringed by six triangles, so the board
    reads as interlocking six-point stars. Hexagons are made from two trapezoid bars (half-hexagons)
    in adjacent row slices, so each row is a flat-sided strip: trapezoids alternating with triangles.
    Roles: hex, up, down (use one wood for up and down for a single row log)."""
    a = float(p.get("side", 0.9)); h = a * S3 / 2
    rows = int(p.get("rows") or max(4, 4 * round(board["length"] / h / 4)))
    cols = int(p.get("cols") or max(1, round(board["width"] / (2 * a))))
    polys = []
    for j in range(-8, rows + 8):
        y0, y1 = j * h, (j + 1) * h
        # hexagon rows sit on even lines y = 2kh with centres every 2a, odd hexagon rows shifted by a
        if j % 2 == 0:      # tops of the hexagons centred on y0 (wide at the bottom), down triangles between
            off = (j // 2 % 2) * a
            for k in range(-4, cols + 4):
                cx = off + 2 * k * a
                polys.append(_poly([(cx - a, y0), (cx + a, y0), (cx + a / 2, y1), (cx - a / 2, y1)], "hex", f"r{j}"))
                polys.append(_poly([(cx + a, y0), (cx + 1.5 * a, y1), (cx + a / 2, y1)], "down", f"r{j}"))
        else:               # bottoms of the hexagons centred on y1 (wide at the top), up triangles between
            off = ((j + 1) // 2 % 2) * a
            for k in range(-4, cols + 4):
                cx = off + 2 * k * a
                polys.append(_poly([(cx - a / 2, y0), (cx + a / 2, y0), (cx + a, y1), (cx - a, y1)], "hex", f"r{j}"))
                polys.append(_poly([(cx + a / 2, y0), (cx + 1.5 * a, y0), (cx + a, y1)], "up", f"r{j}"))
    trim = [0.0, 0.0, cols * 2 * a, rows * h]
    return {"polygons": polys, "trim": trim, "roles": ["hex", "up", "down"],
            "cells": {"kind": "tri", "side": 2 * a, "origin": [-a, 0.0], "angle": 0, "levels": int(p.get("levels", 2))},
            "centers": [((m % 2) * a + 2 * k * a, 2 * m * h) for m in range(-2, rows // 2 + 3) for k in range(-2, cols + 3)],
            "notes": [f"Hexagons {2 * a:g}\" across with {a:g}\" triangles between them. Each hexagon is built from pieces in neighbouring logs; "
                      "those glue lines join the same wood and disappear in end grain.",
                      "Every bar is ripped at a 30 degree blade tilt."]}


def rosettes(p, board):
    """Rhombitrihexagonal (3.4.6.4) rosettes: regular hexagons, squares and equilateral triangles of
    one edge length 'side', every corner a triangle, square, hexagon and square. Each hexagon carries
    a unit of three squares (right, upper right, upper left) and two triangles; units glue into
    zigzag row logs that nest with a half-unit offset. Roles: hex, square, tri (or 'tri_up' and
    'tri_down' with 'split_tri': true)."""
    a = float(p.get("side", 0.75)); D = a * (1 + S3); V = D * S3 / 2
    split = bool(p.get("split_tri", False))
    cols = int(p.get("cols") or _fit(board["width"], D))
    rows = int(p.get("rows") or _fit(board["length"], V))
    def P(r, deg): return (r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)))
    hexv = [P(a, 30 + 60 * k) for k in range(6)]          # pointy top: 30 (upper right), 90 (top), 150, ...
    def sq_on(p0, p1):
        # square built outward on edge p0->p1 of a CCW polygon (outward = right-hand side)
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        nx, ny = dy, -dx
        return [p0, (p0[0] + nx, p0[1] + ny), (p1[0] + nx, p1[1] + ny), p1]
    sqR = sq_on(hexv[5], hexv[0])     # right edge (330 -> 30)
    sqUR = sq_on(hexv[0], hexv[1])    # upper right edge (30 -> 90)
    sqUL = sq_on(hexv[1], hexv[2])    # upper left edge (90 -> 150)
    triT = [hexv[1], sqUR[2], sqUL[1]]                    # above the top corner: points down
    triR = [hexv[0], sqR[2], sqUR[1]]                     # at the upper right corner: points up
    polys = []
    for j in range(0, rows + 1):
        for i in range(-1, cols + 1):
            cx, cy = i * D + (D / 2 if j % 2 else 0), j * V
            u = f"r{j}/u{i}"
            mv = lambda pts: [(x + cx, y + cy) for x, y in pts]
            polys.append(_poly(mv(hexv), "hex", f"r{j}", u))
            for q in (sqR, sqUR, sqUL): polys.append(_poly(mv(q), "square", f"r{j}", u))
            polys.append(_poly(mv(triT), "tri_down" if split else "tri", f"r{j}", u))
            polys.append(_poly(mv(triR), "tri_up" if split else "tri", f"r{j}", u))
    trim = [0.0, 0.0, cols * D, rows * V]
    roles = ["hex", "square"] + (["tri_up", "tri_down"] if split else ["tri"])
    return {"polygons": polys, "trim": trim, "roles": roles,
            "notes": [f"{rows} rows of {cols} rosettes; every edge is {a:g}\". Built as straight strips: the strip lines run "
                      "through hexagon centres, so some hexagons are two trapezoids and some squares and triangles are halves; "
                      "the halves' glue lines are same-species and disappear in end grain.",
                      "Inside each strip the pieces nest two across, so tape-glue each strip on a full-size template, then "
                      "flatten both broad faces before crosscutting.",
                      "Three bar shapes and three saw setups: hexagon (four 30 degree bevels), square, triangle (30 degrees)."]}


def pinwheel(p, board):
    """Pinwheel rosettes: the rosette pattern (hexagon, ring of six, small triangles) redrawn on the triangle
    grid so it can be built from triangle logs. Regular hexagons of side 'side' on a lattice (2,1),(-1,3); each
    hexagon is ringed by six 60 degree diamonds that lean the same way round, each diamond bridging two hexagons,
    and two small triangles fill what is left (the snub trihexagonal tiling). Roles: hex, diamond, tri."""
    a = float(p.get("side", 0.75)); h = a * S3 / 2
    rows = int(p.get("rows") or max(2, 2 * round(board["length"] / h / 2)))
    cols = int(p.get("cols") or max(2, 2 * round(board["width"] / a / 2)))
    L = lambda i, j: ((i + j / 2) * a, j * h)
    def is_c(i, j):                       # hexagon centres: i - 2j = 0 mod 7  (lattice (2,1), (-1,3))
        return (i - 2 * j) % 7 == 0
    nb = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
    def centre_of(v):
        if is_c(*v): return v
        for d in nb:
            c = (v[0] + d[0], v[1] + d[1])
            if is_c(*c): return c
        return None
    polys = []; petals = {}
    for j in range(-8, rows + 8):
        i0 = -((j + 1) // 2) - 8
        for i in range(i0, i0 + cols + 17):
            if is_c(i, j):
                polys.append(_poly([L(i + d[0], j + d[1]) for d in nb], "hex", f"r{j}"))
            for tri in ([(i, j), (i + 1, j), (i, j + 1)], [(i + 1, j), (i + 1, j + 1), (i, j + 1)]):
                if any(is_c(*v) for v in tri): continue            # part of a hexagon
                cs = [centre_of(v) for v in tri]
                pair = [c for c in set(cs) if cs.count(c) >= 2]    # two corners on one hexagon's rim: a petal
                if not pair: polys.append(_poly([L(*v) for v in tri], "tri", f"r{j}")); continue
                petals[tuple(sorted(tri))] = tri
    used = set()
    for k, tri in petals.items():          # petals pair up across a shared edge into diamonds
        if k in used: continue
        for k2, t2 in petals.items():
            if k2 == k or k2 in used: continue
            sh = set(tri) & set(t2)
            if len(sh) == 2:
                a_ = [v for v in tri if v not in sh][0]; b_ = [v for v in t2 if v not in sh][0]; s0, s1 = sorted(sh)
                polys.append(_poly([L(*a_), L(*s0), L(*b_), L(*s1)], "diamond", "r0")); used.add(k); used.add(k2); break
        else:
            polys.append(_poly([L(*v) for v in tri], "diamond", "r0"))
    trim = [0.0, 0.0, cols * a, rows * h]
    return {"polygons": polys, "trim": trim, "roles": ["hex", "diamond", "tri"],
            "cells": {"kind": "tri", "side": 2 * a, "origin": [0.0, 0.0], "angle": 0, "levels": int(p.get("levels", 1))},
            "centers": [L(i, j) for j in range(-4, rows + 5) for i in range(-((j + 1) // 2) - 4, -((j + 1) // 2) + cols + 9) if is_c(i, j)],
            "notes": [f"Hexagons {2 * a:g}\" across, each ringed by six diamonds leaning the same way, with small triangles between: "
                      "a rosette drawn on a triangle grid so every piece has 60 degree corners."]}


GENERATORS = {"pinwheel": pinwheel, "pinwheel-rosettes": pinwheel, "cubes": cubes, "tumbling-blocks": cubes, "stars6": stars6, "snowflakes": snowflakes, "snowflake": snowflakes, "stars8": stars8,
              "lemoyne": stars8, "checker": checker, "checkerboard": checker, "brick": brick,
              "geodomes": geodomes, "geodesic": geodomes, "kagome": kagome, "trihex": kagome,
              "rosettes": rosettes, "rhombitrihex": rosettes}


def generate(design):
    pat = design["pattern"]
    if pat == "custom":
        return {"polygons": design["polygons"], "trim": design["trim"],
                "roles": sorted({p["role"] for p in design["polygons"]}), "notes": design.get("notes", [])}
    if pat not in GENERATORS:
        raise SystemExit(f"unknown pattern {pat!r}; one of {sorted(GENERATORS)} or 'custom'")
    return GENERATORS[pat](design.get("params", {}), design["board"])


# --------------------------------------------------------------------------------------------
# Lattice patterns: colourings of a fine triangular lattice (small triangles of side t), built from
# triangle logs k small triangles on a side. Same-wood neighbours inside a log merge into one bar.
# --------------------------------------------------------------------------------------------
def _lattice(p, board, t, k, colour, quarter=False, centre=None):
    """colour(u, v) -> role for the small triangle whose centroid is (u, v) in lattice units (edges along
    (1, 0) and (0, 1), 60 degrees apart). quarter=True turns the lattice a quarter turn (pointy-top hexagons).
    centre: lattice vertex to put at the middle of the board (one centred motif)."""
    from logs import merge_all
    L = k * t; H = L * S3 / 2
    W, Ln = board["width"], board["length"]
    if quarter:      # log rows run along the board: columns of logs H wide
        ncol = max(2, round(W / H)); nrow = max(2, round(Ln / (L / 2))); gw, gh = nrow * L / 2, ncol * H
    else:
        ncol = max(2, round(W / (L / 2))); nrow = max(2, round(Ln / H)); gw, gh = ncol * L / 2, nrow * H
    P = lambda i, j: ((i + j / 2) * t, j * t * S3 / 2)
    ox = oy = 0.0
    if centre is not None:
        cx, cy = P(*centre); ox, oy = gw / 2 - cx, gh / 2 - cy
        ox = round(ox / (L / 2)) * (L / 2) if False else ox
    polys = []
    J0 = -2; J1 = int(gh / H) + 3
    for J in range(J0 - 4, J1 + 4):
        I0 = int((-ox - (J + 1) * L / 2) / L) - 3; I1 = int((gw - ox - J * L / 2) / L) + 3
        for I in range(I0 - 2, I1 + 2):
            for up in (True, False):
                items = []
                for a in range(k):
                    for b in range(k - a):
                        i, j = (I * k + a, J * k + b) if up else (I * k + k - 1 - a, J * k + k - 1 - b)
                        tris = [(i + 1 / 3, j + 1 / 3, [P(i, j), P(i + 1, j), P(i, j + 1)])] if up else [(i + 2 / 3, j + 2 / 3, [P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)])]
                        if a + b < k - 1:      # the triangle of the other hand that sits inside the same log
                            tris.append((i + 2 / 3, j + 2 / 3, [P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)]) if up else (i + 1 / 3, j + 1 / 3, [P(i, j), P(i + 1, j), P(i, j + 1)]))
                        for u, v, pts in tris:
                            r = colour(u, v); items.append((r, r, pts))
                for _, r, pts in merge_all(items):
                    pts = [(x + ox, y + oy) for x, y in pts]
                    if quarter: pts = [(gh - y, x) for x, y in pts]
                    polys.append(_poly(pts, r, f"r{J}"))
    if quarter:
        trim = [0.0, 0.0, gh, gw]; cells = {"kind": "tri", "side": L, "origin": [gh - oy, ox], "angle": 90, "levels": int(p.get("levels", 1))}
    else:
        trim = [0.0, 0.0, gw, gh]; cells = {"kind": "tri", "side": L, "origin": [ox, oy], "angle": 0, "levels": int(p.get("levels", 1))}
    return polys, trim, cells


def _hexdist(u, v):
    return max(abs(u), abs(v), abs(u + v))


def _sector(u, v):
    """0..5: which sixth of the plane round the origin (u, v) is in, counter-clockwise from the (1, 0) edge."""
    x, y = u + v / 2, v * S3 / 2
    return int((math.degrees(math.atan2(y, x)) % 360) // 60)


def chevrons(p, board):
    """Stepped chevrons, the board Mike Dillen built after SPALM: every triangle log is three identical
    trapezoid bars set pinwheel fashion, one of each wood. Roles: a, b, c."""
    t = float(p.get("side", 0.75))
    def colour(u, v):
        a, b = u % 3, v % 3
        up = (a + b) < 3
        if not up: a, b = 3 - a, 3 - b
        if b < 1 and a + b < 2: r = 0
        elif a < 1: r = 2
        else: r = 1
        return "abc"[r]
    polys, trim, cells = _lattice(p, board, t, 3, colour)
    return {"polygons": polys, "trim": trim, "roles": ["a", "b", "c"], "cells": cells,
            "notes": [f"One log, one bar: three trapezoids ({2 * t:g}\" and {t:g}\" faces) glued pinwheel fashion into a {3 * t:g}\" triangle. No triangle bar anywhere.",
                      "This is the build Mike Dillen documented after SPALM's board: trapezoid sticks in a V cradle, every face sanded flat."]}


def gems(p, board):
    """Faceted gems: hexagons cut like stones, six trapezoid facets round a small hexagon table, the facets
    shaded in four woods as if lit from the top left, so no facet meets its own wood in the next gem.
    Roles: light, pale, shade, dark, table."""
    t = float(p.get("side", 0.75))
    def colour(u, v):
        best = None
        for ci in range(int(u // 2) * 2 - 4, int(u // 2) * 2 + 6, 2):
            for cj in range(int(v // 2) * 2 - 4, int(v // 2) * 2 + 6, 2):
                if (ci // 2 - cj // 2) % 3: continue
                d = _hexdist(u - ci, v - cj)
                if best is None or d < best[0]: best = (d, ci, cj)
        d, ci, cj = best
        if d < 1: return "table"
        return ["shade", "pale", "light", "pale", "shade", "dark"][_sector(u - ci, v - cj)]
    polys, trim, cells = _lattice(p, board, t, 2, colour)
    return {"polygons": polys, "trim": trim, "roles": ["light", "pale", "shade", "dark", "table"], "cells": cells,
            "notes": [f"Each gem is a hexagon {4 * t:g}\" across its points: a {2 * t:g}\" table ringed by six facets.",
                      f"Every log is one trapezoid facet bar and one small triangle of the table, so a gem is six {2 * t:g}\" triangle logs meeting at its centre."]}


def ziggurat(p, board):
    """Ziggurat: one stepped hexagonal pyramid seen from above, centred on the board. Hexagonal rings one
    lattice step wide alternate between a dark line and a terrace; the terraces are shaded by which way they
    face. Roles: light, mid, dark, line."""
    t = float(p.get("side", 0.75))
    def colour(u, v):
        d = int(_hexdist(u, v))
        if d % 2: return "line"
        return ["dark", "mid", "light", "light", "mid", "dark"][_sector(u, v)]     # lit from the left: the top half mirrors the bottom, so each plank gives two rows
    polys, trim, cells = _lattice(p, board, t, 2, colour, centre=(0, 0))
    return {"polygons": polys, "trim": trim, "roles": ["light", "mid", "dark", "line"], "cells": cells,
            "notes": [f"Concentric hexagonal steps {t:g}\" wide round the middle of the board; the terraces face six ways and are shaded in three woods.",
                      "One motif, not a repeat: the top half mirrors the bottom half, so each plank gives one row for each half."]}


def ribbons(p, board):
    """Folded ribbons: zigzag ribbons of diamonds running the length of the board, each ribbon in a lit wood
    and a shaded wood so it reads as pleated paper. Roles: a_lit, a_shade, b_lit, b_shade."""
    t = float(p.get("side", 0.75)); wide = int(p.get("wide", 1))
    def colour(u, v):
        j = math.floor(v); i = math.floor(u); up = (u - i) + (v - j) < 1
        if j % 2 == 0: col = i              # diamonds lean right: up(i,j) + down(i,j)
        else: col = i if up else i + 1      # diamonds lean left: down(i-1,j) + up(i,j)
        c = col + j // 2
        return ("a" if (c // wide) % 2 == 0 else "b") + ("_lit" if j % 2 == 0 else "_shade")
    polys, trim, cells = _lattice(p, board, t, 2, colour)
    return {"polygons": polys, "trim": trim, "roles": ["a_lit", "a_shade", "b_lit", "b_shade"], "cells": cells,
            "notes": [f"Every piece is a {t:g}\" diamond; a ribbon is a zigzag column of them, lit on one slope and shaded on the other."]}


def notched(p, board):
    """Notched cubes: tumbling blocks with a small cube bitten out of the near corner of every block, so each
    block shows three outer faces and the three inner faces of the notch. Roles: lid, left, right."""
    t = float(p.get("side", 0.5))
    def colour(u, v):
        best = None
        for ci in range(int(u // 2) * 2 - 6, int(u // 2) * 2 + 8, 2):
            for cj in range(int(v // 2) * 2 - 6, int(v // 2) * 2 + 8, 2):
                if (ci // 2 - cj // 2) % 3: continue
                d = _hexdist(u - ci, v - cj)
                if best is None or d < best[0]: best = (d, ci, cj)
        d, ci, cj = best
        s = _sector(u - ci, v - cj)          # lattice turned a quarter turn: sector 0 starts pointing up the board
        outer = {0: "lid", 1: "left", 2: "left", 3: "right", 4: "right", 5: "lid"}[s]
        inner_ = {0: "right", 1: "right", 2: "lid", 3: "lid", 4: "left", 5: "left"}[s]
        return inner_ if d < 1 else outer
    polys, trim, cells = _lattice(p, board, t, int(p.get("log", 3)), colour, quarter=True)
    return {"polygons": polys, "trim": trim, "roles": ["lid", "left", "right"], "cells": cells,
            "notes": [f"Blocks {4 * t:g}\" across their points, each with a {t:g}\" notch at the near corner."]}


GENERATORS.update({"chevrons": chevrons, "gems": gems, "ziggurat": ziggurat, "ribbons": ribbons, "notched": notched})
