#!/usr/bin/env python3
"""Repeat math: what in a board repeats, how the repeats are reached (slide, turn, roll, flip), and which
nearby boards repeat better.

  python3 scripts/repeats.py design.json            # the analysis, then ranked candidates
  python3 scripts/repeats.py design.json --no-candidates
  python3 scripts/repeats.py --variants out.html design.json [more.json]   # every face one plank can make

The rules and the reasoning are in references/repeats.md. Everything here is deterministic: the same
design gives the same numbers and the same ranking, on any machine.

  analyse(plan)      -> the "repeats" block stored in plan.json
  candidates(design) -> nearby designs, best first
"""
import copy, json, math, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import planks as PK

TURNS = (("r", "turned end for end"), ("f", "rolled over"), ("m", "turned over like a page"))


def _keys(row, ax, op):
    su, sv = next((a, b) for nm, a, b in PK.OPS if nm == op)
    return [p["key"] for p in PK._local(row, ax, su, sv)]


def _same(a, b):
    """Two rows are one plank if one is the other slid along: equal, contained, or overlapping by half."""
    if PK._find(a, b) is not None or PK._find(b, a) is not None: return True
    m = min(len(a), len(b))
    for ov in range(m - 1, max(m // 2, 1) - 1, -1):
        if a[-ov:] == b[:ov] or a[:ov] == b[-ov:]: return True
    return False


def analyse(plan):
    rows = plan["rows"]; N = len(rows); kind = plan["info"]["kind"]
    out = {"rows": N, "bar_shapes": len(plan["bar_types"]), "log_types": len(plan["logs"]), "kind": kind}
    planks = plan.get("planks") or []
    if not planks:
        out.update(planks=0, note="No planks: " + ("hexagon pucks are glued in a frame." if kind == "hex" else "each row is already one slice of a strip panel."))
        return out
    ang = math.radians(plan["info"].get("angle", 0)); ax = (math.cos(ang), math.sin(ang))
    K = {op: [_keys(r, ax, op) for r in rows] for op in ("", "r", "f", "m")}
    # 1. translation: the row period p is the smallest k with row j = row j+k (slid along) for every j
    # (k up to N/2 only: a period has to be seen at least twice to count)
    period = next((k for k in range(1, N // 2 + 1) if all(_same(K[""][j], K[""][j + k]) for j in range(N - k))), None)
    # 2. turns: an op that maps row i onto row c - i for one constant c pairs the rows about a centre line
    turns = []
    for op, name in TURNS:
        best = None
        for c in range(0, 2 * N - 1):                      # c = i + j, rows numbered from 0
            pairs = [(i, c - i) for i in range(N) if 0 <= c - i < N]
            if len(pairs) < 2: continue
            if all(_same(K[""][j], K[op][i]) for i, j in pairs):
                # prefer the centre nearest the middle of the board: it pairs the most rows
                if best is None or abs(c - (N - 1)) < abs(best - (N - 1)): best = c
        selfsym = sum(1 for i in range(N) if _same(K[""][i], K[op][i]))
        if best is not None or selfsym:
            turns.append({"op": op, "name": name, "centre": None if best is None else best / 2 + 1, "self": selfsym})
    # 3. orbits: how many planks the symmetry allows on this board
    parent = list(range(N))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i in range(N):
        for j in range(i + 1, N):
            if any(_same(K[""][i], K[op][j]) for op in ("", "r", "f", "m")): parent[find(j)] = find(i)
    orbits = len({find(i) for i in range(N)})
    np_ = len(planks); once = sum(1 for p in planks if p["rows_cut"] == 1)
    lengths = sum(p["n"] * p["count"] for p in planks)
    flips = sum(1 for p in planks for pk in p["pucks"] if pk["flip"]); nl = sum(p["n"] for p in planks)
    out.update(planks=np_, plank_copies=sum(p["count"] for p in planks), single_row_planks=once, row_period=period, turns=turns,
               orbits=orbits, rows_per_plank=round(N / np_, 2), log_lengths=lengths, logs_turned_end_for_end=flips, logs_in_planks=nl,
               widest_plank=round(max(p["width"] for p in planks), 3))
    # the board would need this many rows for every plank to be cut at least twice
    out["rows_for_full_repeat"] = None if period is None else (2 * period if not any(t["centre"] for t in turns) else period + 1)
    say = []
    if period: say.append(f"rows repeat every {period}" + (" row" if period == 1 else " rows") + " (slid along)")
    else: say.append("no row repeats another as cut on this board")
    for t in turns:
        if t["centre"]: say.append(f"a row {t['name']} is its mirror row about the line at row {t['centre']:g}")
    say.append(f"so {orbits} plank type{'s' if orbits != 1 else ''} can make all {N} rows" + ("" if orbits == np_ else f" (the plan uses {np_}: the width limit kept some apart)"))
    out["summary"] = "; ".join(say) + "."
    return out


def _score(rep, errs):
    """Lower is better. Fixed order: buildable, no one-off planks, fewest plank types, fewest log types, fewest glued lengths."""
    return (len(errs), rep.get("single_row_planks", 0), rep.get("planks", 0), rep["log_types"], rep.get("log_lengths", 0))


def candidates(design, steps=2):
    """The design as given, the board turned a quarter turn, and each a few rows longer or shorter."""
    import cbplan
    def build(d):
        with tempfile.TemporaryDirectory() as out:
            try: plan = cbplan.build(d, out)
            except SystemExit as e: return None, [str(e)]
            except Exception: return None, ["not buildable at this size"]      # a size the pattern cannot be cut to
            return plan, [c["what"] for c in plan["checks"] if not c["ok"] and c["level"] != "warn"]
    base, _ = build(design)
    if base is None: return []
    rh = max(r["height"] for r in base["rows"]); horiz = abs(math.cos(math.radians(base["info"].get("angle", 0)))) > 0.5
    W0, L0 = float(design["board"]["width"]), float(design["board"]["length"])
    seen = set(); out = []
    for turn in (False, True):
        W, L = (L0, W0) if turn else (W0, L0)
        for k in range(-steps, steps + 1):
            d = copy.deepcopy(design); d["board"]["width"] = W; d["board"]["length"] = L
            # rows stack along the board's length when they run across it
            key = "length" if horiz else "width"
            d["board"][key] = round(d["board"][key] + k * rh, 3)
            plan, errs = build(d)
            if plan is None: continue
            rep = analyse(plan); size = (round(plan["board"]["width"], 2), round(plan["board"]["length"], 2))
            sig = (size, rep["rows"], rep.get("planks"))
            if sig in seen: continue
            seen.add(sig)
            out.append({"board": d["board"], "size": size, "given": not turn and k == 0, "quarter_turn": turn, "rows_delta": k,
                        "repeats": rep, "errors": errs, "score": _score(rep, errs)})
    out.sort(key=lambda c: (c["score"], abs(c["size"][0] * c["size"][1] - W0 * L0), c["quarter_turn"], c["rows_delta"]))
    return out


# ---------------------------------------------------------------- variants: what else one plank can make

SLIDES = ((0, 1, "no slide"), (1, 2, "each row slid half a repeat"), (1, 3, "each row slid a third of a repeat"), (1, 4, "each row slid a quarter of a repeat"))
ROW2 = (("", "every row as cut"), ("r", "every other row turned end for end"), ("f", "every other row rolled over"), ("m", "every other row turned over like a page"))


def _period(pl):
    """(pucks in one repeat, its length along the plank), or (all the pucks, None) when the plank never repeats."""
    P = pl["pucks"]; n = len(P)
    def shape(u, dx):      # the puck as a set of coloured outlines, however its pieces happen to be listed
        return sorted((ro, tuple(sorted((round(x - dx, 2), round(y, 2)) for x, y in pts))) for ro, pts in u["cells"])
    def same(a, b, dx): return shape(a, 0) == shape(b, dx)
    left = lambda u: min(p[0] for p in u["pts"])
    for k in range(1, n // 2 + 1):
        dx = left(P[k]) - left(P[0])
        if dx > 1e-6 and all(same(P[i], P[i + k], dx) for i in range(n - k)): return P[:k], dx
    return P, None


def _inside(pt, poly):
    x, y = pt; c = False; n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1): c = not c
    return c


def variants(plan, pl):
    """Faces one plank can make when every row is the same crosscut: the second row as cut, turned, rolled or
    flipped, and each row slid a fixed fraction of the plank's repeat. Fixed order in, fixed order out; faces
    that come out the same (also seen from the other side or the other end) are listed once.
    `carry` is the share of each row seam where the wood is the same on both sides, so figures run through."""
    unit, d = _period(pl); W, H = pl["width"], pl["height"]; N = len(plan["rows"])
    x0 = min(p[0] for u in unit for p in u["pts"]); span = d or (max(p[0] for u in unit for p in u["pts"]) - x0)
    cells = [(ro, pts) for u in unit for ro, pts in u["cells"]]
    Bw = min(max(plan["board"]["width"], plan["board"]["length"]), 16.0) if d else span
    def role(x, y, op, off):
        su, sv = next((a, b) for nm, a, b in PK.OPS if nm == op)
        px = su * (x - off - W / 2) + W / 2; py = sv * (y - H / 2) + H / 2
        if d: px = x0 + (px - x0) % d
        for ro, pts in cells:
            if _inside((px, py), pts): return ro
        return "."
    out = []; seen = set(); nx = 48
    for op, opname in ROW2:
        for a, b, sname in (SLIDES if d else SLIDES[:1]):
            delta = span * a / b
            rows = [("" if j % 2 == 0 else op, j * delta) for j in range(N)]
            xs = [(i + 0.5) * Bw / nx for i in range(nx)]
            grid = ["".join(role(x, H * f, o, off) for x in xs) for o, off in rows for f in (0.04, 0.5, 0.96)]
            sigs = {"|".join(g) for g in (grid, grid[::-1], [r[::-1] for r in grid], [r[::-1] for r in grid[::-1]])}
            if sigs & seen: continue
            seen.add("|".join(grid))
            seam = [(grid[3 * j + 2], grid[3 * j + 3]) for j in range(N - 1)]
            carry = sum(p == q for t, u in seam for p, q in zip(t, u)) / max(1, sum(len(t) for t, _ in seam))
            out.append({"plank": pl["id"], "row2": op, "slide": [a, b], "slide_in": round(delta, 3), "carry": round(carry, 3),
                        "name": opname + (", " + sname if a else ""), "rows": rows, "width": Bw, "height": H * N,
                        "unit": cells, "x0": x0, "period": d, "span": span, "W": W, "H": H})
    out.sort(key=lambda v: (-v["carry"], ROW2.index((v["row2"], next(n for o, n in ROW2 if o == v["row2"]))), v["slide"][1]))
    return out


def variants_svg(plan, v, uid):
    sp = plan["species"]; W, H, Bw, d = v["W"], v["H"], v["width"], v["period"]; sc = 300 / Bw
    f = lambda t: f"{t:.2f}"
    o = [f'<svg viewBox="0 0 {f(Bw * sc)} {f(v["height"] * sc)}" role="img" aria-label="{v["name"]}"><defs><clipPath id="{uid}c"><rect width="{f(Bw * sc)}" height="{f(v["height"] * sc)}"/></clipPath>']
    for nm, su, sv in PK.OPS:
        if not any(op == nm for op, _ in v["rows"]): continue
        o.append(f'<g id="{uid}{nm or "a"}">')
        for ro, pts in v["unit"]:
            q = " ".join(f(( su * (x - W / 2) + W / 2) * sc) + "," + f((sv * (y - H / 2) + H / 2) * sc) for x, y in pts)
            o.append(f'<polygon points="{q}" fill="{sp[ro]["end"]}" stroke="{sp[ro]["end"]}" stroke-width=".4"/>')
        o.append("</g>")
    o.append(f'</defs><g clip-path="url(#{uid}c)">')
    for j, (op, off) in enumerate(v["rows"]):
        y = (len(v["rows"]) - 1 - j) * H * sc
        if d:
            m0 = int(math.floor((-off - W) / d)) - 1; m1 = int(math.ceil((Bw - off + W) / d)) + 1
        else: m0 = m1 = 0
        for m in range(m0, m1 + 1):
            o.append(f'<use href="#{uid}{op or "a"}" x="{f((off + m * (d or 0)) * sc)}" y="{f(y)}"/>')
    for j in range(1, len(v["rows"])): o.append(f'<line x1="0" x2="{f(Bw * sc)}" y1="{f(j * H * sc)}" y2="{f(j * H * sc)}" stroke="#00000030" stroke-width=".6"/>')
    o.append("</g></svg>")
    return "".join(o)


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Plank Turn Variants</title><style>
:root{--bg:#f4efe6;--card:#fbf8f2;--ink:#231f1a;--mute:#6d6558;--line:#d9cfbf;--acc:#7a4a2b}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#1b1815;--card:#24201c;--ink:#ece5d8;--mute:#a79d8d;--line:#3a332b;--acc:#d49a6a}}
:root[data-theme="dark"]{--bg:#1b1815;--card:#24201c;--ink:#ece5d8;--mute:#a79d8d;--line:#3a332b;--acc:#d49a6a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 Georgia,'Source Serif 4',serif}
main{max-width:1100px;margin:0 auto;padding:28px 16px 60px}h1{font:700 30px/1.15 'Archivo',system-ui,sans-serif;margin:0 0 8px}
h2{font:700 20px/1.2 'Archivo',system-ui,sans-serif;margin:44px 0 4px;padding-top:18px;border-top:2px solid var(--ink)}
p{margin:6px 0;max-width:68ch}.m{color:var(--mute);font-size:14px}
.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px;margin-top:14px}
figure{margin:0;background:var(--card);border:1px solid var(--line);padding:10px}svg{display:block;width:100%;height:auto}
figcaption{font:13px/1.35 system-ui,sans-serif;margin-top:8px}figcaption b{display:block}figcaption span{color:var(--mute);font-variant-numeric:tabular-nums}
table{border-collapse:collapse;margin:10px 0;font:14px/1.4 system-ui,sans-serif}td,th{border-bottom:1px solid var(--line);padding:5px 12px 5px 0;text-align:left;vertical-align:top}
</style></head><body><main>
<h1>What one plank can make</h1>
<p>Each board below is drawn from a single glued plank. Every row is the same crosscut; the only thing that changes is how the second row is turned and how far each row is slid. Nothing new is ripped or glued to get any of these.</p>
<table><tr><th>Move</th><th>What it does to the row on the board</th></tr>
<tr><td>Slide</td><td>Shifts the figure sideways. Half a repeat staggers it like bricks; a third or a quarter makes diagonals.</td></tr>
<tr><td>Turn end for end</td><td>Half turn, same face up. Points that leaned right lean left and what was at the top is at the bottom.</td></tr>
<tr><td>Roll over</td><td>Underside up, top edge to bottom edge. Mirrors the row top to bottom, so shapes meet their reflection at the seam.</td></tr>
<tr><td>Turn over like a page</td><td>Underside up, left end to right end. Mirrors the row left to right.</td></tr></table>
<p class="m">"Colour carries" is the share of each row seam where the same wood sits on both sides. High means figures run through the seams into larger shapes; low means a busier, broken face. Faces that come out identical are shown once.</p>
__BODY__
</main></body></html>"""


def variants_page(plans):
    body = []; k = 0
    for plan in plans:
        for pl in plan.get("planks") or []:
            vs = variants(plan, pl)
            _, d = _period(pl)
            rep = f"The plank repeats every {d:.2f} in." if d else "This plank never repeats along its length, so sliding is left out."
            body.append(f'<h2>{plan["name"]}, plank {pl["id"]}</h2><p class="m">{pl["n"]} logs, {pl["width"]:.1f} in wide. {rep} {len(vs)} different faces.</p><div class="g">')
            for v in vs:
                k += 1
                body.append(f'<figure>{variants_svg(plan, v, "v%d" % k)}<figcaption><b>{v["name"][0].upper() + v["name"][1:]}</b><span>colour carries {round(v["carry"] * 100)}%'
                            + (f' &middot; slide {v["slide_in"]:.2f} in' if v["slide"][0] else "") + '</span></figcaption></figure>')
            body.append("</div>")
    return PAGE.replace("__BODY__", "\n".join(body))


def main():
    import cbplan
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args: sys.exit(__doc__)
    if "--variants" in sys.argv:        # repeats.py --variants out.html design.json [design.json ...]
        plans = []
        for a in args[1:]:
            with tempfile.TemporaryDirectory() as out: plans.append(cbplan.build(json.load(open(a)), out))
        open(args[0], "w").write(variants_page(plans)); print("wrote", args[0]); return
    design = json.load(open(args[0]))
    with tempfile.TemporaryDirectory() as out:
        plan = cbplan.build(design, out)
    rep = plan["repeats"]
    print(f"{plan['name']}: {rep['rows']} rows, {rep['bar_shapes']} bar shapes, {rep['log_types']} log types, {rep.get('planks', 0)} plank types")
    if rep.get("summary"): print("  " + rep["summary"])
    else: print("  " + rep["note"]); return
    print(f"  rows per plank type {rep['rows_per_plank']}, planks cut for one row {rep['single_row_planks']}, log lengths glued into planks {rep['log_lengths']}, widest plank {rep['widest_plank']} in")
    if "--no-candidates" in sys.argv: return
    print("  candidates, best first (a quarter turn puts the rows along the other side of the board):")
    for c in candidates(design):
        r = c["repeats"]
        print(f"   {'*' if c['given'] else ' '} {c['size'][0]:g} x {c['size'][1]:g}  rows {r['rows']:>2}  plank types {r.get('planks', 0):>2}  one-off {r.get('single_row_planks', 0):>2}  "
              f"log types {r['log_types']:>2}  widest {r.get('widest_plank', 0):>5}"
              + ("  quarter turn" if c["quarter_turn"] else "") + (f"  [{'; '.join(c['errors'])[:60]}]" if c["errors"] else ""))
    print("   * is the design as given")


if __name__ == "__main__":
    main()
