"""Illustrated assembly drawings: the build steps drawn in 3D, in the manner of printed step-by-step
woodworking plans. Bars, units, logs and slices are drawn as solid prisms in their woods (end grain
darker on the cut ends), glue faces in blue, push and clamp directions as orange block arrows,
parts called out with circled letters on leaders, the grain direction as a long arrow, and saw cuts
as red lines.

  Scene: add prisms and marks, then .svg(). drawings.py composes the figures.

Pure Python: an orthographic projection and a painter's sort, which is exact for the separated
(exploded) parts drawn here.
"""
import html, math

AZ, EL = math.radians(-32), math.radians(30)
GLUE = "#7fb7d4"; ARROW = "#f39a1e"; CUT = "#d62f2f"; INK = "#1e2327"


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
                el.append(f'<text x="18" y="{y}" font-size="12"{w} fill="{INK}">{html.escape(line)}</text>'); y += 17
        t = f"<title>{html.escape(title)}</title>" if title else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {H:.0f}" width="{width}" height="{H:.0f}" '
                f'font-family="IBM Plex Mono, ui-monospace, Menlo, monospace">{t}<rect width="100%" height="100%" fill="#fff"/>' + "".join(el) + "</svg>")


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
                f'<text x="{mx:.1f}" y="{my - 8:.1f}" font-size="11" text-anchor="middle" '
                f'transform="rotate({ang:.1f} {mx:.1f} {my:.1f})">grain runs along the log</text>')
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
        return "".join(f'<text x="{ax + dx:.1f}" y="{ay + dy + 15 * i:.1f}" font-size="11.5" fill="{INK}" '
                       f'{"font-weight=\"bold\" " if i == 0 and len(m) > 4 and m[4] else ""}paint-order="stroke" stroke="#fff" stroke-width="3">'
                       f'{html.escape(t)}</text>' for i, t in enumerate(lines))
    return ""
