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


GENERATORS = {"cubes": cubes, "tumbling-blocks": cubes, "stars6": stars6, "snowflakes": snowflakes, "snowflake": snowflakes, "stars8": stars8,
              "lemoyne": stars8, "checker": checker, "checkerboard": checker, "brick": brick}


def generate(design):
    pat = design["pattern"]
    if pat == "custom":
        return {"polygons": design["polygons"], "trim": design["trim"],
                "roles": sorted({p["role"] for p in design["polygons"]}), "notes": design.get("notes", [])}
    if pat not in GENERATORS:
        raise SystemExit(f"unknown pattern {pat!r}; one of {sorted(GENERATORS)} or 'custom'")
    return GENERATORS[pat](design.get("params", {}), design["board"])
