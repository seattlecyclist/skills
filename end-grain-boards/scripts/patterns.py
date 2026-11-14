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
    cols = int(p.get("cols") or _fit(board["width"], w, -0.5 * w, 2))
    rows = int(p.get("rows") or _fit(board["length"], 1.5 * s, -0.5 * s, 2))
    polys = []
    for j in range(rows):
        cy = 1.5 * j * s
        for col in range(cols):
            cx = col * w + (w / 2 if j % 2 else 0)
            i = col - j // 2                      # axial coordinate
            T, B = (cx, cy + s), (cx, cy - s)
            UR, LR = (cx + w / 2, cy + s / 2), (cx + w / 2, cy - s / 2)
            UL, LL = (cx - w / 2, cy + s / 2), (cx - w / 2, cy - s / 2)
            C = (cx, cy)
            unit = f"r{j}/h{col}"
            for name, pts in (("lid", [C, UR, T, UL]), ("left", [C, UL, LL, B]), ("right", [C, B, LR, UR])):
                polys.append(_poly(pts, colour(name, i, j), f"r{j}", unit))
    trim = [0.0, -s / 2, (cols - 0.5) * w, 1.5 * (rows - 1) * s + s / 2]
    return polys, trim, rows, cols


def cubes(p, board):
    """Tumbling blocks: every hexagon is a cube seen corner-on; lid, left and right faces each get
    their own species (light lid, medium and dark sides reads best)."""
    polys, trim, rows, cols = _rhombille(p, board, lambda name, i, j: name)
    s = float(p.get("side", 1.25))
    return {"polygons": polys, "trim": trim, "roles": ["lid", "left", "right"],
            "notes": [f"{rows} rows of {cols} cubes; every cube is 3 rhombus bars (60/120 degrees, {s:g}\" sides) "
                      "glued into a hexagon, hexagons glued side by side into a row log, row slices nested with "
                      "a half-cube offset.",
                      "Light lid, medium left, dark right gives light from the top left; swap left and right to move the light."]}


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
        if any(chosen(*e) for e in ends):
            return f"star_{name}" if shade else "star"
        return "field"

    polys, trim, rows, cols = _rhombille(p, board, colour)
    roles = (["star_lid", "star_left", "star_right"] if shade else ["star"]) + ["field"]
    return {"polygons": polys, "trim": trim, "roles": roles,
            "notes": [f"{rows} rows of {cols} hexagons of 3 rhombi each; the six rhombi around every chosen point form a "
                      f"six-point star ({spacing} spacing), the rest is field. Rows that differ get their own row log.",
                      "Every bar is the same 60 degree rhombus: one saw setup for the whole board."]}


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
    edges, cores = set(), set()
    def add(a, b, centre=False):
        e = (min(a, b), max(a, b)); edges.add(e)
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
    R = arm + 2
    # flake centres: columns 'spacing' apart, flake rows 2k hexagon rows apart (straight up, so every
    # flake row lines up with the hexagon rows and the row logs repeat every 2k rows)
    k = int(p.get("rise") or max(1, round(m / S3)))
    stagger = bool(p.get("stagger", False))
    for a in range(-8, 9):
        for b in range(-8, 9):
            c = (ic + a * m - b * k + ((m // 2) if stagger and b % 2 else 0), jc + 2 * k * b)
            for (u, v), centre in flake:
                add((c[0] + u[0], c[1] + u[1]), (c[0] + v[0], c[1] + v[1]), centre)

    def colour(name, i, j):
        ends = {"lid": ((i - 1, j + 1), (i, j + 1)), "left": ((i - 1, j + 1), (i, j)),
                "right": ((i, j + 1), (i, j))}[name]
        e = (min(ends), max(ends))
        if e in cores and core: return "core"
        return "flake" if e in edges else "field"

    polys, trim, rows, cols = _rhombille(dict(p, side=s, cols=cols, rows=rows), board, colour)
    roles = (["core"] if core else []) + ["flake", "field"]
    return {"polygons": polys, "trim": trim, "roles": roles,
            "notes": [f"Snowflakes with six arms of {arm} diamonds and side branches, repeating every {m} diamonds; "
                      f"{rows} rows of {cols} hexagons, each hexagon 3 rhombus bars. Every bar is the same 60 degree "
                      "rhombus. The flakes don't line up with the rows, so several rows differ and each gets its own log."]}


# --------------------------------------------------------------------------------------------
# Eight-point (LeMoyne) star blocks: 8 rhombi of 45 degrees, 4 corner squares, 4 edge triangles.
# Built as quarter-block units (2 rhombi, a square, 2 half-triangles), four quarters per block log.
# --------------------------------------------------------------------------------------------
def stars8(p, board):
    a = float(p.get("side", 1.0))                 # rhombus side
    S = a * (2 + math.sqrt(2))                    # block side
    alternate = bool(p.get("alternate", True))
    cols = int(p.get("cols") or _fit(board["width"], S))
    rows = int(p.get("rows") or _fit(board["length"], S))
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
    return {"polygons": polys, "trim": [0, 0, cols * S, rows * S], "roles": roles,
            "notes": [f"{rows} x {cols} LeMoyne star blocks, {S:.3f}\" square. Each block is four identical "
                      "quarter units turned 90 degrees to each other, so one block log makes every block.",
                      "The edge triangles are made as two half-triangles (one in each quarter); the glue line "
                      "between them is same-species and disappears in end grain."]}


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
    return {"polygons": polys, "trim": [0, 0, cols * s, rows * s], "roles": ["a", "b"],
            "notes": [f"{rows} rows of {cols} squares. The row log is just a strip panel: alternating strips "
                      f"{s:g}\" wide and {s:g}\" thick, edge glued."]}


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
    return {"polygons": polys, "trim": [0, 0, cols * bw, rows * bh], "roles": ["a", "b"],
            "notes": [f"{rows} courses; even rows carry a half brick past each end that is trimmed off."]}


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
    for j in range(rows):
        i0 = -((j + 1) // 2) - 1
        for i in range(i0, i0 + cols + 3):
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
    def tone_of(f):
        k, ring = f; t = sector_tone[k]
        if ring == 0 and n > 2: t -= 1
        if ring == n - 1 and n > 2 and p.get("rim", True): t += 1
        return max(1, min(K, t))
    tone = {o: tone_of(o) for o in set(offs)}
    polys = [_poly(pts, f"tone{tone[o]}", f"r{j}") for (kind, j, pts), o in zip(tris, offs)]
    roles = [f"tone{k}" for k in range(1, K + 1)]
    return {"polygons": polys, "trim": trim, "roles": roles,
            "notes": [f"{rows} rows of equilateral triangles ({s:g}\" sides). Domes are hexagons {n} triangles a side "
                      f"({6 * n * n} facets, {2 * n * s:.2f}\" across), shaded in {K} woods as if lit from the upper left.",
                      f"Every bar is the same equilateral triangle: one saw setup for the whole board. The dome pattern "
                      f"repeats every {n} rows (shifted along), so with the rows a whole board wide there are {2 * n} different row logs (rows {n} apart repeat the domes half a pattern along)."]}


def kagome(p, board):
    """Kagome (trihexagonal) star lattice: regular hexagons on a triangular grid, the gaps between
    them up- and down-pointing triangles; every hexagon is ringed by six triangles, so the board
    reads as interlocking six-point stars. Hexagons are made from two trapezoid bars (half-hexagons)
    in adjacent row slices, so each row is a flat-sided strip: trapezoids alternating with triangles.
    Roles: hex, up, down (use one wood for up and down for a single row log)."""
    a = float(p.get("side", 0.9)); h = a * S3 / 2
    rows = int(p.get("rows") or _fit(board["length"], h))
    cols = int(p.get("cols") or max(1, round(board["width"] / (2 * a))))
    polys = []
    for j in range(rows):
        y0, y1 = j * h, (j + 1) * h
        # hexagon rows sit on even lines y = 2kh with centres every 2a, odd hexagon rows shifted by a
        if j % 2 == 0:      # tops of the hexagons centred on y0 (wide at the bottom), down triangles between
            off = (j // 2 % 2) * a
            for k in range(-1, cols + 1):
                cx = off + 2 * k * a
                polys.append(_poly([(cx - a, y0), (cx + a, y0), (cx + a / 2, y1), (cx - a / 2, y1)], "hex", f"r{j}"))
                polys.append(_poly([(cx + a, y0), (cx + 1.5 * a, y1), (cx + a / 2, y1)], "down", f"r{j}"))
        else:               # bottoms of the hexagons centred on y1 (wide at the top), up triangles between
            off = ((j + 1) // 2 % 2) * a
            for k in range(-1, cols + 1):
                cx = off + 2 * k * a
                polys.append(_poly([(cx - a / 2, y0), (cx + a / 2, y0), (cx + a, y1), (cx - a, y1)], "hex", f"r{j}"))
                polys.append(_poly([(cx + a / 2, y0), (cx + 1.5 * a, y0), (cx + a, y1)], "up", f"r{j}"))
    trim = [0.0, 0.0, cols * 2 * a, rows * h]
    return {"polygons": polys, "trim": trim, "roles": ["hex", "up", "down"],
            "notes": [f"{rows} row strips {h:.3f}\" tall: half-hexagon trapezoids ({2 * a:g}\" and {a:g}\" across) "
                      f"alternating with {a:g}\" triangles. Each hexagon is two trapezoids from neighbouring rows; "
                      "their glue line is same-species and disappears in end grain, but only if the rows land exactly.",
                      "Trapezoids and triangles are both ripped at a 30 degree tilt, flipping the blank every pass."]}


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


GENERATORS = {"cubes": cubes, "tumbling-blocks": cubes, "stars6": stars6, "snowflakes": snowflakes, "snowflake": snowflakes, "stars8": stars8,
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
