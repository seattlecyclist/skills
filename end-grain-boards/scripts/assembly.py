"""Illustrated assembly drawings: the build steps drawn in 3D, in the manner of printed step-by-step
woodworking plans. Bars, units, logs and slices are drawn as solid prisms in their woods (end grain
darker on the cut ends), glue faces in yellow, push and clamp directions as orange block arrows,
parts called out with circled letters on leaders, the grain direction as a long arrow, and saw cuts
as red lines.

  figures(plan) -> {"asm_rip": svg, "asm_unit1": svg, "asm_log0": svg, "asm_cut": svg, "asm_board": svg, "asm_trim": svg}

Pure Python: an orthographic projection and a painter's sort, which is exact for the separated
(exploded) parts drawn here.
"""
import html, math

AZ, EL = math.radians(-32), math.radians(30)
GLUE = "#f2cf3a"; ARROW = "#f39a1e"; CUT = "#d62f2f"; INK = "#1e2327"


def _hex(c):
    c = c.lstrip("#"); return [int(c[i:i + 2], 16) for i in (0, 2, 4)]


def _shade(c, k):
    r, g, b = _hex(c)
    if k >= 1:
        t = k - 1; r, g, b = (int(v + (255 - v) * t) for v in (r, g, b))
    else:
        r, g, b = (int(v * k) for v in (r, g, b))
    return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"


def _cam(p):
    X, Y, Z = p
    x = X * math.cos(AZ) - Y * math.sin(AZ); y = X * math.sin(AZ) + Y * math.cos(AZ)
    return (x, Z * math.cos(EL) + y * math.sin(EL), y * math.cos(EL) - Z * math.sin(EL))   # screen x, screen up, depth


def _view_dot(n):
    x = n[0] * math.cos(AZ) - n[1] * math.sin(AZ); y = n[0] * math.sin(AZ) + n[1] * math.cos(AZ)
    return -y * math.cos(EL) + n[2] * math.sin(EL)


class Scene:
    """az/el: long parts use az 50 so their cut ends face the viewer at the lower left; flat slices use az -28."""
    def __init__(self, az=50, el=28):
        self.prisms = []; self.marks = []; self.notes = []; self.az, self.el = math.radians(az), math.radians(el)

    def note(self, text, bold_first=True):
        self.notes.append((text, bold_first))

    def prism(self, sect, length, place, end_col, side_col, glue=(), outline=INK, cap_lines=()):
        """sect: 2D cross-section (ccw); place(u, v, w) -> world point, w along the length."""
        self.prisms.append({"sect": sect, "L": length, "place": place, "end": end_col, "side": side_col,
                            "glue": set(glue), "outline": outline, "cap_lines": cap_lines})

    # marks are drawn after the solids: ("arrow", p0, p1) ("label", p, text, offset) ("line", p0, p1, col, dash) ("text", p, s)
    def mark(self, *m):
        self.marks.append(m)

    def svg(self, width=760, title=""):
        global AZ, EL
        AZ, EL = self.az, self.el
        faces = []
        for pr in self.prisms:
            s, L, f = pr["sect"], pr["L"], pr["place"]
            n = len(s)
            caps = [[f(u, v, 0) for u, v in s][::-1], [f(u, v, L) for u, v in s]]
            for k, cap in enumerate(caps):
                nrm = _normal(cap)
                if _view_dot(nrm) > 1e-6:
                    faces.append((cap, pr["end"], 1.0, nrm, pr, ("cap", k)))
            for i in range(n):
                a, b = s[i], s[(i + 1) % n]
                q = [f(*a, 0), f(*b, 0), f(*b, L), f(*a, L)]
                nrm = _normal(q)
                if _view_dot(nrm) > 1e-6:
                    faces.append((q, GLUE if i in pr["glue"] else pr["side"], None, nrm, pr, ("side", i)))
        pts = [p for fc in faces for p in fc[0]] + [p for m in self.marks for p in m[1:] if isinstance(p, tuple) and len(p) == 3]
        cp = [_cam(p) for p in pts] or [(0, 0, 0)]
        x0, x1 = min(c[0] for c in cp), max(c[0] for c in cp); y0, y1 = min(c[1] for c in cp), max(c[1] for c in cp)
        pad = 60; top = 24 + 17 * sum(len(t.split("\n")) for t, _ in self.notes) if self.notes else 0
        sc = min((width - 2 * pad) / max(x1 - x0, 1e-6), 430 / max(y1 - y0, 1e-6))
        ox = (width - (x1 - x0) * sc) / 2
        H = (y1 - y0) * sc + 2 * pad + top
        P = lambda p: (ox + (_cam(p)[0] - x0) * sc, pad + top + (y1 - _cam(p)[1]) * sc)
        light = (-0.45, -0.55, 0.7); ln = math.sqrt(sum(v * v for v in light)); light = [v / ln for v in light]
        # painter: whole prisms far to near, then each prism's faces far to near
        order = _paint_order(self.prisms)
        el = []
        for i in order:
            pr = self.prisms[i]
            fs = sorted((fc for fc in faces if fc[4] is pr), key=lambda fc: -sum(_cam(p)[2] for p in fc[0]) / len(fc[0]))
            for q, col, k, nrm, _, kind in fs:
                lam = 0.72 + 0.38 * max(0, sum(a * b for a, b in zip(nrm, light)))
                fill = _shade(col, lam if col != GLUE else 1.0)
                el.append('<polygon points="' + " ".join("%.1f,%.1f" % P(p) for p in q) +
                          f'" fill="{fill}" stroke="{pr["outline"]}" stroke-width="0.9" stroke-linejoin="round"/>')
                if kind[0] == "cap" and kind[1] == 1:
                    for a, b, c in pr["cap_lines"]:
                        A, B = P(pr["place"](*a, pr["L"])), P(pr["place"](*b, pr["L"]))
                        el.append(f'<line x1="{A[0]:.1f}" y1="{A[1]:.1f}" x2="{B[0]:.1f}" y2="{B[1]:.1f}" stroke="{c}" stroke-width="1.6"/>')
        for m in self.marks:
            el.append(_mark(m, P))
        y = 26
        for t, bold in self.notes:
            for i, line in enumerate(t.split("\n")):
                w = ' font-weight="bold"' if bold and i == 0 else ""
                el.append(f'<text x="18" y="{y}" font-size="13"{w} fill="{INK}">{html.escape(line)}</text>'); y += 17
        t = f"<title>{html.escape(title)}</title>" if title else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {H:.0f}" width="{width}" height="{H:.0f}" '
                f'font-family="Helvetica, Arial, sans-serif">{t}<rect width="100%" height="100%" fill="#fff"/>' + "".join(el) + "</svg>")


def _normal(q):
    a, b, c = q[0], q[1], q[2]
    u = [b[i] - a[i] for i in range(3)]; v = [c[i] - a[i] for i in range(3)]
    n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    l = math.sqrt(sum(x * x for x in n)) or 1
    return [x / l for x in n]


def _verts(pr):
    s, L, f = pr["sect"], pr["L"], pr["place"]
    return [f(u, v, 0) for u, v in s] + [f(u, v, L) for u, v in s]


def _planes(pr):
    s, L, f = pr["sect"], pr["L"], pr["place"]; n = len(s)
    caps = [[f(u, v, 0) for u, v in s][::-1], [f(u, v, L) for u, v in s]]
    sides = [[f(*s[i], 0), f(*s[(i + 1) % n], 0), f(*s[(i + 1) % n], L)] for i in range(n)]
    out = []
    for q in caps + sides:
        nm = _normal(q); out.append((nm, sum(a * b for a, b in zip(nm, q[0]))))
    return out


def _behind(A, B, D):
    """+1 if prism A must be painted before B (A is farther), -1 if after, 0 if no face plane separates them."""
    for src, sign in ((A, 1), (B, -1)):
        for nm, d0 in src["_pl"]:
            da = [sum(a * b for a, b in zip(nm, p)) - d0 for p in A["_v"]]
            db = [sum(a * b for a, b in zip(nm, p)) - d0 for p in B["_v"]]
            e = 1e-6
            if max(da) <= e and min(db) >= -e: sa = -1
            elif min(da) >= -e and max(db) <= e: sa = 1
            else: continue
            k = sum(a * b for a, b in zip(nm, D))
            if abs(k) < 1e-9: return 0
            return 1 if sa * k > 0 else -1     # A on the side that is deeper along the view
    return 0


def _paint_order(prisms):
    """Far-to-near order for convex prisms: face-plane separation between pairs whose drawings overlap, then a
    topological sort (centre depth breaks ties and cycles)."""
    D = (math.sin(AZ) * math.cos(EL), math.cos(AZ) * math.cos(EL), -math.sin(EL))
    n = len(prisms); box = []
    for pr in prisms:
        pr["_v"] = _verts(pr); pr["_pl"] = _planes(pr)
        c = [_cam(p) for p in pr["_v"]]
        box.append((min(x for x, _, _ in c), max(x for x, _, _ in c), min(y for _, y, _ in c), max(y for _, y, _ in c)))
    depth = [_prism_depth(pr) for pr in prisms]
    succ = [set() for _ in range(n)]; indeg = [0] * n
    for i in range(n):
        for j in range(i + 1, n):
            a, b = box[i], box[j]
            if a[1] <= b[0] or b[1] <= a[0] or a[3] <= b[2] or b[3] <= a[2]: continue
            r = _behind(prisms[i], prisms[j], D)
            if r == 0: continue
            i0, j0 = (i, j) if r > 0 else (j, i)
            if j0 not in succ[i0]: succ[i0].add(j0); indeg[j0] += 1
    import heapq
    done = [False] * n; out = []
    heap = [(-depth[i], i) for i in range(n) if indeg[i] == 0]; heapq.heapify(heap)
    while len(out) < n:
        if not heap:                            # a cycle: take the deepest remaining
            i = max((k for k in range(n) if not done[k]), key=lambda k: depth[k]); indeg[i] = 0; heapq.heappush(heap, (-depth[i], i))
        _, i = heapq.heappop(heap)
        if done[i]: continue
        done[i] = True; out.append(i)
        for j in succ[i]:
            indeg[j] -= 1
            if indeg[j] == 0 and not done[j]: heapq.heappush(heap, (-depth[j], j))
    return out


def _prism_depth(pr):
    s, L, f = pr["sect"], pr["L"], pr["place"]
    cu = sum(u for u, _ in s) / len(s); cv = sum(v for _, v in s) / len(s)
    return _cam(f(cu, cv, L / 2))[2]


def _mark(m, P):
    kind = m[0]
    if kind == "arrow":                       # orange block arrow from p0 toward p1 (the push)
        (ax, ay), (bx, by) = P(m[1]), P(m[2])
        dx, dy = bx - ax, by - ay; d = math.hypot(dx, dy) or 1; ux, uy = dx / d, dy / d; nx, ny = -uy, ux
        w, hw, hl = 7, 15, 18
        pts = [(ax + nx * w, ay + ny * w), (bx - ux * hl + nx * w, by - uy * hl + ny * w), (bx - ux * hl + nx * hw, by - uy * hl + ny * hw),
               (bx, by), (bx - ux * hl - nx * hw, by - uy * hl - ny * hw), (bx - ux * hl - nx * w, by - uy * hl - ny * w), (ax - nx * w, ay - ny * w)]
        return '<polygon points="' + " ".join("%.1f,%.1f" % p for p in pts) + f'" fill="{ARROW}" stroke="#b86a00" stroke-width="1"/>'
    if kind == "grain":                       # thin black arrow with a label: direction of the wood grain
        (ax, ay), (bx, by) = P(m[1]), P(m[2])
        dx, dy = bx - ax, by - ay; d = math.hypot(dx, dy) or 1; ux, uy = dx / d, dy / d
        ang = math.degrees(math.atan2(dy, dx))
        mx, my = (ax + bx) / 2, (ay + by) / 2
        return (f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{INK}" stroke-width="1.4"/>'
                f'<path d="M{bx:.1f},{by:.1f} l{-ux * 11 - uy * 5:.1f},{-uy * 11 + ux * 5:.1f} l{uy * 10:.1f},{-ux * 10:.1f} z" fill="{INK}"/>'
                f'<text x="{mx:.1f}" y="{my - 8:.1f}" font-size="12" font-style="italic" text-anchor="middle" '
                f'transform="rotate({ang:.1f} {mx:.1f} {my:.1f})">Direction of wood grain</text>')
    if kind == "label":                       # circled letter on a leader
        (ax, ay) = P(m[1]); dx, dy = m[3] if len(m) > 3 else (-40, -40)
        cx, cy = ax + dx, ay + dy; r = 13 if len(m[2]) <= 2 else 17
        return (f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{cx:.1f}" y2="{cy:.1f}" stroke="{INK}" stroke-width="0.9"/>'
                f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="2" fill="{INK}"/>'
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="#fff" stroke="{INK}" stroke-width="1.3"/>'
                f'<text x="{cx:.1f}" y="{cy + 0.5:.1f}" font-size="12" font-weight="bold" text-anchor="middle" dominant-baseline="middle">{html.escape(m[2])}</text>')
    if kind == "line":
        (ax, ay), (bx, by) = P(m[1]), P(m[2])
        dash = f' stroke-dasharray="{m[4]}"' if len(m) > 4 and m[4] else ""
        return f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{m[3]}" stroke-width="1.8"{dash}/>'
    if kind == "text":
        (ax, ay) = P(m[1]); dx, dy = m[3] if len(m) > 3 else (0, 0)
        lines = m[2].split("\n")
        return "".join(f'<text x="{ax + dx:.1f}" y="{ay + dy + 15 * i:.1f}" font-size="12.5" fill="{INK}" '
                       f'{"font-weight=\"bold\" " if i == 0 and len(m) > 4 and m[4] else ""}paint-order="stroke" stroke="#fff" stroke-width="3">'
                       f'{html.escape(t)}</text>' for i, t in enumerate(lines))
    return ""


# ------------------------------------------------------------------------------------------------
def _shared_edges(polys):
    """For each polygon, the indices of its edges that lie against another polygon in the group."""
    def key(a, b):
        a = (round(a[0], 3), round(a[1], 3)); b = (round(b[0], 3), round(b[1], 3)); return (min(a, b), max(a, b))
    cnt = {}
    for p in polys:
        for i in range(len(p)): cnt[key(p[i], p[(i + 1) % len(p)])] = cnt.get(key(p[i], p[(i + 1) % len(p)]), 0) + 1
    return [{i for i in range(len(p)) if cnt[key(p[i], p[(i + 1) % len(p)])] > 1} for p in polys]


def _centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def _bar_id(plan, pts):
    from cbplan import shape_of
    k = shape_of(pts)[0]
    return next(bt["id"] for bt in plan["bar_types"] if shape_of(bt["pts"])[0] == k)


def figures(plan, unit_list, unit_type_of):
    polys = plan["polygons"]; sp = plan["species"]; out = {}
    end = lambda r: sp[r]["end"]; side = lambda r: sp[r]["long"]
    T = plan["board"]["thickness"]

    # long things (bars, units, logs) lie along world X; their cross-section is in world (Y, Z)
    def along(ox=0.0, oy=0.0, oz=0.0):
        return lambda u, v, w: (ox + w, oy + u, oz + v)

    # ---- rip: a blank with its bars coming off, each bar lying on its longest side as it is cut
    bt = plan["bar_types"][0]; b0 = next(b for b in plan["bars"] if b["bar"] == bt["id"])
    s = Scene(az=50, el=26)
    sect = _lay_flat(bt["pts"])
    th = max(y for _, y in sect); wdt = max(x for x, _ in sect)
    col = sp[b0["roles"][0]]; Lb = 9.0
    if bt["kind"] in ("rhombus", "parallelogram"):
        step = bt["dims"]["side"]
        blank = _hull([(x + k * step, y) for k in range(4) for x, y in sect])
    else:
        step = wdt; blank = [(0, 0), (4 * wdt, 0), (4 * wdt, th), (0, th)]
    bx = max(x for x, _ in blank)
    gap = 0.6
    s.prism([(x + 3 * (wdt + gap) + 0.3, y) for x, y in blank], Lb, along(), col["end"], col["long"])
    for k in range(3):
        s.prism([(x + k * (wdt + gap), y) for x, y in sect], Lb, along(), col["end"], col["long"])
        s.mark("label", (0, k * (wdt + gap) + wdt / 2, th * 0.5), bt["id"], (-30 - 6 * k, 34 + 12 * k))
    s.mark("grain", (1.0, -1.4, 0), (Lb - 1.0, -1.4, 0))
    tilt = f"Blade tilted {bt['tilt']:.0f} degrees from vertical" if bt["tilt"] else "Blade square to the table"
    s.note(f"Bar {bt['id']}: {bt['label']}\nMill the blank {_f(th)} thick. {tilt}.\n"
           f"Rip each bar {_f(step)} off the bevelled edge; the cut ends show the shape.")
    out["asm_rip"] = s.svg(title=f"Rip bar {bt['id']}")

    # ---- 1st glue-up: each unit type, bars exploded with glue faces and arrows
    for u in plan["units"]:
        bars = [polys[i] for i in u["bars"]]; pp = [b["pts"] for b in bars]
        c = _centroid([v for p in pp for v in p]); shared = _shared_edges(pp)
        span = max(max(v[0] for p in pp for v in p) - min(v[0] for p in pp for v in p), max(v[1] for p in pp for v in p) - min(v[1] for p in pp for v in p))
        s = Scene(az=34, el=30); L = max(3.0, 1.7 * span); gap = max(0.5, 0.3 * span)
        for b, p, gl in zip(bars, pp, shared):
            bc = _centroid(p); dx, dy = bc[0] - c[0], bc[1] - c[1]; d = math.hypot(dx, dy) or 1
            ox, oy = dx / d * gap, dy / d * gap
            sect = [(x - c[0] + ox, y - c[1] + oy) for x, y in p]
            s.prism(sect, L, along(), end(b["role"]), side(b["role"]), glue=gl)
            tip = (0, bc[0] - c[0] + ox, bc[1] - c[1] + oy)
            s.mark("label", tip, _bar_id(plan, p), (34 * (1 if dx >= 0 else -1), -30 if dy >= -0.01 else 30))
            far = (-0.2, (bc[0] - c[0]) / d * (gap + 0.45 * span + 1.2) + ox * 0, (bc[1] - c[1]) / d * (gap + 0.45 * span + 1.2))
            near = (-0.2, (bc[0] - c[0]) / d * (gap + 0.45 * span) , (bc[1] - c[1]) / d * (gap + 0.45 * span))
            s.mark("arrow", far, near)
        s.mark("grain", (0.5, -span, -span * 0.8), (L - 0.5, -span, -span * 0.8))
        s.note("Glue the yellow faces\nTape the outside, roll the bars together")
        out[f"asm_unit{u['type'] + 1}"] = s.svg(title=u["name"])

    # ---- 2nd glue-up: each log, units (or bars) side by side, pulled apart along the row, with arrows
    for lg in plan["logs"]:
        rep = next(sl for sl in plan["slices"] if sl["id"] == lg["rep"])
        groups = [[i for i in unit_list[uid]] for uid in lg["units"]] + [[i] for i in lg["loose_bars"]]
        gp = [[polys[i]["pts"] for i in g] for g in groups]
        cs = [_centroid([v for p in g for v in p]) for g in gp]
        order = sorted(range(len(groups)), key=lambda k: cs[k][0])
        bb = [min(v[0] for g in gp for p in g for v in p), min(v[1] for g in gp for p in g for v in p)]
        rw = max(v[0] for g in gp for p in g for v in p) - bb[0]
        L = max(5.0, min(lg["length"], 0.55 * rw)); gap = 0.7
        s = Scene()
        # glue faces: edges shared between different groups
        allp = [p for g in gp for p in g]; owner = [k for k, g in enumerate(gp) for _ in g]
        sh = _shared_edges(allp)
        own_sh = [_shared_edges(g) for g in gp]
        idx = 0
        for k in order:
            pass
        flat = []
        for k, g in enumerate(gp):
            for j, p in enumerate(g):
                inner = own_sh[k][j]
                ext = sh[sum(len(x) for x in gp[:k]) + j] - inner
                flat.append((k, p, groups[k][j], ext))
        rank = {k: r for r, k in enumerate(order)}
        gw = sorted(max(v[0] for p in g for v in p) - min(v[0] for p in g for v in p) for g in gp)[len(gp) // 2]
        gh = sorted(max(v[1] for p in g for v in p) - min(v[1] for p in g for v in p) for g in gp)[len(gp) // 2]
        C = _centroid(cs); off = [((cs[k][0] - C[0]) / max(gw, 0.1) * gap, (cs[k][1] - C[1]) / max(gh, 0.1) * gap) for k in range(len(gp))]
        mx0 = min(o[0] for o in off); my0 = min(o[1] for o in off); off = [(a - mx0, b - my0) for a, b in off]
        for k, p, pi, gl in flat:
            sect = [(x - bb[0] + off[k][0], y - bb[1] + off[k][1]) for x, y in p]
            s.prism(sect, L, along(), end(polys[pi]["role"]), side(polys[pi]["role"]), glue=gl)
        top = max(v[1] for g in gp for p in g for v in p) - bb[1] + max(o[1] for o in off)
        right = max(v[0] for g in gp for p in g for v in p) - bb[0] + max(o[0] for o in off)
        for k in order[:8]:
            cx = cs[k][0] - bb[0] + off[k][0]
            lab = (f"U{unit_type_of[lg['units'][k]][0] + 1}" if k < len(lg["units"]) else _bar_id(plan, gp[k][0]))
            gt = max(v[1] for p in gp[k] for v in p) - bb[1] + off[k][1]
            s.mark("label", (L, cx, gt), lab, (14, -34 - 10 * (rank[k] % 2)))
        s.mark("arrow", (-0.2, -3.0, top / 2), (-0.2, -0.4, top / 2))
        s.mark("arrow", (-0.2, right + 3.0, top / 2), (-0.2, right + 0.4, top / 2))
        s.mark("grain", (0.5, -1.0, -1.6), (L - 0.5, -1.0, -1.6))
        s.note(f"{lg['name']}: clamp together as shown,\ncauls above and below\nMake {lg['count']}, {_f(lg['length'])} long")
        out[f"asm_log{lg['type']}"] = s.svg(title=lg["name"])

    # ---- crosscut: the first log with cut lines and slices standing off the end
    lg = plan["logs"][0]; rep = next(sl for sl in plan["slices"] if sl["id"] == lg["rep"])
    pp = [polys[i] for i in rep["bars"]]
    bb = [min(v[0] for p in pp for v in p["pts"]), min(v[1] for p in pp for v in p["pts"])]
    wid = max(v[0] for p in pp for v in p["pts"]) - bb[0]; top = max(v[1] for p in pp for v in p["pts"]) - bb[1]
    cut = T + plan["shop"]["flatten_allowance"]; pitch = cut + plan["shop"]["kerf"]
    L = min(lg["length"], 4 * pitch + 2 * plan["shop"]["end_trim"])
    s = Scene(az=22, el=30)
    for p in pp:
        sect = [(x - bb[0], y - bb[1]) for x, y in p["pts"]]
        s.prism(sect, L, along(), end(p["role"]), side(p["role"]))
        for k in range(2):     # two slices cut off and moved along
            s.prism(sect, cut, along(-(k + 1) * (cut + 2.4), 0, 0), end(p["role"]), side(p["role"]))
    xcut = plan["shop"]["end_trim"]
    for k in range(4):
        x = L - xcut - (k + 1) * pitch + plan["shop"]["kerf"]
        if x <= 0.3: break
        s.mark("line", (x, 0, top + 0.02), (x, wid, top + 0.02), CUT, "")
        s.mark("line", (x, wid, 0), (x, wid, top), CUT, "")
    s.mark("line", (L * 0.15, wid * 0.25, top + 0.05), (L * 0.85, wid * 0.5, top + 0.05), "#555", "5 4")
    s.mark("line", (L * 0.85, wid * 0.5, top + 0.05), (L * 0.15, wid * 0.75, top + 0.05), "#555", "5 4")
    s.mark("text", (L * 0.5, wid * 0.5, top), "Pencil V across the top", (-70, -44))
    s.note(f"Slices {_f(cut)} thick on a crosscut sled\nwith a stop block, red lines")
    s.mark("grain", (0.3, -1.0, 0), (L - 0.3, -1.0, 0))
    out["asm_cut"] = s.svg(title="Crosscut the slices")

    # ---- 3rd glue-up: slices lying end grain up, rows pulled apart, numbered, arrows top and bottom
    sl = sorted(plan["slices"], key=lambda s_: s_["n"])
    show = sl[: min(len(sl), 5)]
    s = Scene(az=-28, el=40); gap = 2.2
    flat = lambda ox, oy, oz=0.0: (lambda u, v, w: (ox + u, oy + v, oz + w))
    by0 = min(v[1] for s_ in show for i in s_["bars"] for v in polys[i]["pts"])
    bx0 = min(v[0] for s_ in show for i in s_["bars"] for v in polys[i]["pts"])
    maxx = max(v[0] for s_ in show for i in s_["bars"] for v in polys[i]["pts"]) - bx0
    for r, s_ in enumerate(show):
        oy = r * gap
        for i in s_["bars"]:
            p = polys[i]
            s.prism([(x - bx0, y - by0 + oy) for x, y in p["pts"]], T, flat(0, 0), end(p["role"]), side(p["role"]))
        lowx = maxx + 0.2; cy = (s_["bbox"][1] + s_["bbox"][3]) / 2 - by0 + oy
        mark = {"id": "", "r180": " ↻", "fx": " ⇋", "fy": " ⇵"}.get(s_["xf"], " *")
        s.mark("label", (maxx, cy, T), f"{s_['n']}{mark}".strip(), (40, -6))
    tl = max(v[1] for s_ in show for i in s_["bars"] for v in polys[i]["pts"]) - by0 + gap * (len(show) - 1)
    s.mark("arrow", (maxx / 2, -3.5, T / 2), (maxx / 2, -0.8, T / 2))
    s.mark("arrow", (maxx / 2, tl + 3.5, T / 2), (maxx / 2, tl + 0.8, T / 2))
    s.note(f"End grain up. Glue {len(show) if len(show) < 5 else 'two to four'} slices at a time,\n"
                               "faces flush, cauls top and bottom")
    out["asm_board"] = s.svg(title="Glue the slices")

    # ---- trim: the glued board with trim lines
    s = Scene(az=-28, el=40); tr = plan["board"]["trim"]
    for p in polys:
        s.prism([(x, y) for x, y in p["pts"]], T, flat(0, 0), end(p["role"]), side(p["role"]))
    for a, b in (((tr[0], tr[1]), (tr[2], tr[1])), ((tr[2], tr[1]), (tr[2], tr[3])), ((tr[2], tr[3]), (tr[0], tr[3])), ((tr[0], tr[3]), (tr[0], tr[1]))):
        s.mark("line", (a[0], a[1], T + 0.02), (b[0], b[1], T + 0.02), CUT, "8 5")
    s.note(f"Trim to {_f(tr[2] - tr[0])} x {_f(tr[3] - tr[1])}\non the red lines, then flatten\nwith a router sled")
    out["asm_trim"] = s.svg(title="Trim and flatten")
    return out


def _lay_flat(pts):
    """Turn a bar section so its longest side lies on the table (x axis), corner at the origin."""
    n = len(pts); i = max(range(n), key=lambda k: math.dist(pts[k], pts[(k + 1) % n]))
    a, b = pts[i], pts[(i + 1) % n]; ang = -math.atan2(b[1] - a[1], b[0] - a[0])
    c, s_ = math.cos(ang), math.sin(ang)
    r = [((x - a[0]) * c - (y - a[1]) * s_, (x - a[0]) * s_ + (y - a[1]) * c) for x, y in pts]
    if max(y for _, y in r) <= 1e-9: r = [(x, -y) for x, y in r][::-1]
    mx, my = min(x for x, _ in r), min(y for _, y in r)
    return [(x - mx, y - my) for x, y in r]


def _hull(pts):
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in pts))
    def half(ps):
        h = []
        for p in ps:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0: h.pop()
            h.append(p)
        return h
    lo, up = half(pts), half(pts[::-1])
    return lo[:-1] + up[:-1]


def _f(x):
    from cbplan import frac
    return frac(x) + '"'
