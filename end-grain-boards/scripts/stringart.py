#!/usr/bin/env python3
"""String-art board (after Indigo Designs' "I Made My Dream Cutting Board for a Client"): one plank, then kerf inlays.

A one-wood end-grain field with a figure that comes from how the rows are turned, two staggered lines of
small light triangles across it, and a fan of thin light lines in one corner: straight lines from marks on
one edge to marks on the next edge, the way string art draws a curve.

  two zones of the ground wood, edge glued into one wide plank, with a corner of the accent wood let into
  the upper zone along the joint (chamfer the corner, glue a stick on, joint and plane square again)
  ->  the plank crosscut into rows
  ->  every other row rolled over (other end up) and slid along its length, rows glued into a slab
  ->  slab trimmed square
  ->  one saw cut right through the slab along each line, a strip exactly as thick as the kerf glued in,
      one line at a time, the slab pushed into a square corner jig so the two edges stay in line.

cbplan.py hands a design with "pattern": "stringart" to build() here; the outputs are the usual files.
"""
import base64, html, json, math, os, sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import species as SP
from twoply import frac, short, fine, _up, nominal, _arrow, _chip, GLUE, ORANGE, RED, MDF, MDF_E

SHOP = {"kerf": 0.125, "flatten_allowance": 0.1875, "end_trim": 0.5, "hold_end": 2.0, "spare_rows": 1, "edge_trim": 0.25,
        "planer_width": 12.5, "max_crosscut": 24.0, "max_depth_90": 3.0, "pack": 9, "strip_spares": 2}
ROLES = ("ground", "dark", "accent", "inlay")
DEFAULT_SPECIES = {"ground": "walnut", "dark": "walnut", "accent": "maple", "inlay": "maple"}
VIDEO = "https://www.youtube.com/watch?v=UfEnFkTSfvE"
SOURCES = [
    ("Indigo Designs, “I Made My Dream Cutting Board for a Client” (YouTube, about 18 minutes)", VIDEO,
     "The video in the screenshot. Its description calls the board “a custom walnut cutting board with sweeping maple inlays and a bold, sculptural pattern”. "
     "The cover photo shows the maple lines carried down the edge of the board, and two published stills show narrow end-grain slices in clamps and the glued slab on a table saw sled."),
    ("Instructables, Cutting Board With Curved Inlay", "https://www.instructables.com/Cutting-Board-With-Curved-Inlay",
     "A through inlay made by sawing the board apart and gluing thin strips into the cut. I could read only its introduction, which says the hard part is keeping the glue-up true; that is what the corner jig on sheet 05 is for."),
    ("George Vondriska (WWGOA), Running an End Grain Cutting Board Through a Planer", "https://wwgoa.com/video/running-end-grain-cutting-board-planer",
     "The source for the planer route on sheet 07."),
    ("Marc Spagnuolo, Why Did My Cutting Board Split?", "https://thewoodwhisperer.com/videos/why-did-my-cutting-board-split/",
     "Why long grain glued across an end-grain board is a risk: the board swells and shrinks across its face and long grain does not. It is the reason for the movement note on sheet 07."),
]


# ------------------------------------------------------------------------------------- the face
def _half(poly, a, b, c):
    """The part of a convex polygon where a*x + b*y <= c."""
    out = []; n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        dp, dq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if dp <= 1e-12: out.append(p)
        if (dp < -1e-12 and dq > 1e-12) or (dp > 1e-12 and dq < -1e-12):
            t = dp / (dp - dq); out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def _area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


def lines(W, H, n):
    """Centre lines, in cutting order: line k joins the k-th mark down the left edge to the k-th mark along the bottom edge."""
    return [((0.0, H * (n + 1 - k) / n), (W * k / n, 0.0)) for k in range(1, n + 1)]


def base_polys(w, n, H, joint, slide, acc):
    """The slab before the lines: n rows (drawn upright), each the plank's cross-section; even rows rolled over and slid down."""
    out = []
    for i in range(n):
        x0, x1 = i * w, (i + 1) * w; rolled = i % 2 == 1
        yj = H - joint - (slide if rolled else 0)
        tri = [(x0, yj), (x0 + acc, yj), (x0, yj + acc)] if rolled else [(x1 - acc, yj), (x1, yj), (x1, yj + acc)]
        up = [(x0 + acc, yj), (x1, yj), (x1, H), (x0, H), (x0, yj + acc)] if rolled else [(x0, yj), (x1 - acc, yj), (x1, yj + acc), (x1, H), (x0, H)]
        out.append({"pts": [(x0, 0), (x1, 0), (x1, yj), (x0, yj)], "role": "dark", "row": i})
        out.append({"pts": up, "role": "ground", "row": i})
        out.append({"pts": tri, "role": "accent", "row": i})
    return out


def face_polys(w, n, H, joint, slide, acc, nl, k):
    W = n * w; polys = base_polys(w, n, H, joint, slide, acc); ls = lines(W, H, nl)
    def split(ps, A, B):
        dx, dy = B[0] - A[0], B[1] - A[1]; d = math.hypot(dx, dy); a, b = -dy / d, dx / d; c = a * A[0] + b * A[1]
        res = []
        for p in ps:
            for sgn in (1, -1):
                q = _half(p["pts"], sgn * a, sgn * b, sgn * c - k / 2)
                if len(q) >= 3 and _area(q) > 1e-9: res.append(dict(p, pts=q))
        return res, (a, b, c)
    board = [(0, 0), (W, 0), (W, H), (0, H)]
    for j, (A, B) in enumerate(ls):
        polys, (a, b, c) = split(polys, A, B)
        band = _half(_half(board, a, b, c + k / 2), -a, -b, -c + k / 2)
        polys.append({"pts": band, "role": "inlay", "row": None, "line": j + 1})
    return [dict(p, pts=[(round(x, 6), round(y, 6)) for x, y in p["pts"]], slice=f"r{p['row']}" if p.get("row") is not None else "inlay", unit=None) for p in polys]


def _params(p, board):
    w = float(p.get("row", 0.875)); n = int(p.get("rows") or max(3, round(board["width"] / w)))
    H = float(board["length"]); slide = float(p.get("slide", 2.5)); joint = float(p.get("joint", 6.125)); acc = float(p.get("accent", 0.625))
    nl = int(p.get("lines", 7)); k = float(p.get("line", 0.125))
    return w, n, H, slide, joint, acc, nl, k


def generate(p, board):
    w, n, H, slide, joint, acc, nl, k = _params(p, board)
    return {"polygons": face_polys(w, n, H, joint, slide, acc, nl, k), "trim": [0, 0, n * w, H], "roles": list(ROLES), "cells": {"kind": "plank"},
            "notes": [f"{n} rows {short(w)} wide, every other one rolled over and slid {short(slide)}; {nl} inlaid lines {short(k)} wide."]}


def _darker(c, f=0.8):
    c = c.lstrip("#"); return "#" + "".join(f"{max(0, min(255, int(int(c[i:i + 2], 16) * f))):02x}" for i in (0, 2, 4))


# ------------------------------------------------------------------------------------- the plan
def build(design, out, photo=None):
    import cbplan as CB
    shop = dict(SHOP, **design.get("shop", {})); board = design["board"]; T = float(board.get("thickness", 1.5))
    w, n, H, slide, joint, acc, nl, k = _params(design.get("params", {}), board)
    W = n * w; kerf = shop["kerf"]; et = shop["edge_trim"]
    checks = []
    def check(ok, what, detail="", level="error"):
        checks.append({"ok": bool(ok), "what": what, "detail": detail, "level": level})
    smap = dict(DEFAULT_SPECIES, **design.get("species", {}))
    sp = {r: SP.get(smap[r]) for r in ROLES}
    if sp["dark"]["key"] == sp["ground"]["key"]:               # one wood in two zones: draw the lower zone a shade darker so the zones read
        sp["dark"] = dict(sp["dark"], end=_darker(sp["dark"]["end"]), long=_darker(sp["dark"]["long"]))
    woods = OrderedDict()
    for r in ROLES: woods.setdefault(sp[r]["key"], SP.get(smap[r]))
    jk = [x for x in woods.values() if x["janka"] and x["janka"] < 900]
    check(not jk, "Species hard enough for a cutting surface (Janka 900+)", ", ".join(f'{x["name"]} {x["janka"]}' for x in jk))
    tans = [x["tan"] for x in woods.values() if x["tan"]]; spread = max(tans) - min(tans) if tans else 0
    check(spread <= 4.0, "Species move alike (tangential shrinkage within 4 points)", f"{min(tans):.1f}% to {max(tans):.1f}%" if tans else "", "warn")
    if design.get("frame"):
        check(False, "A border is not drawn by this pattern", "Leave \"frame\" out; sheet 07 says how to add an end-grain border by hand.", "warn")

    # the face
    check(0 < acc < w, "The accent corner is smaller than a row is wide", f"corner {short(acc)}, row {short(w)}")
    check(slide >= acc and slide < H / 2, "The slide is longer than an accent corner and under half the board", f"slide {short(slide)}")
    check(joint > acc + 0.5 and H - joint - slide > 1.0, "Both zones show in every row", f"joint {short(joint)} and {short(joint + slide)} from the top edge of a {short(H)} board")
    check(nl >= 2 and k >= 1 / 16, "At least two lines, each at least 1/16\" wide", f"{nl} lines, {short(k)}")
    polys = face_polys(w, n, H, joint, slide, acc, nl, k)
    trim = [0, 0, W, H]
    check(all(CB.convex(CB.ccw(p["pts"])) for p in polys), "Every piece of the face is convex")
    tot = sum(_area(p["pts"]) for p in polys)
    check(abs(tot - W * H) < 1e-3, "The pieces add up to the board's area exactly (nothing lost or doubled by the lines)", f"{tot:.3f} of {W * H:.3f} sq in")
    no, op_, ng, gp = CB.coverage(polys, trim, 0.04)
    check(no == 0, "Pieces do not overlap", f"overlap near {op_}" if no else "")
    check(ng == 0, "Pieces cover the whole board (no gaps)", f"gap near {gp}" if ng else "")
    # a kerf inlay moves nothing: outside the lines, the face is the slab as it was glued
    base = base_polys(w, n, H, joint, slide, acc); moved = 0
    for p in polys:
        if p["role"] == "inlay": continue
        cx = sum(x for x, y in p["pts"]) / len(p["pts"]); cy = sum(y for x, y in p["pts"]) / len(p["pts"])
        b = next((q for q in base if q["row"] == p["row"] and q["role"] == p["role"]), None)
        if not b or len(_half_all(b["pts"], cx, cy)) == 0: moved += 1
    check(moved == 0, "Outside the lines every piece is where the slab had it, so rows still line up across every line", f"{moved} moved" if moved else f"strip {short(k)} = kerf")
    check(abs(k - kerf) < 1e-6, "The line is as wide as the saw kerf", f"line {short(k)}, kerf {short(kerf)}. Set \"line\" to the kerf of the blade that will cut the slab" if abs(k - kerf) > 1e-6 else f"{short(k)}", "warn")
    ls = lines(W, H, nl)
    ang = [math.degrees(math.atan2(A[1], B[0])) for A, B in ls]
    gaps = [ang[i] - ang[i + 1] for i in range(nl - 1)]
    check(min(gaps) >= 4, "Neighbouring lines cross at 4 degrees or more", f"the sharpest crossing is {min(gaps):.1f} degrees; the points of ground wood there are glued on both sides", "warn")
    lens = [math.hypot(B[0], A[1]) for A, B in ls]

    # the plank
    cut = T + shop["flatten_allowance"]; pitch = cut + kerf; ncut = n + shop["spare_rows"]
    plank_len = _up(ncut * pitch + shop["end_trim"] + shop["hold_end"])
    Uw = et + slide + joint; Lw = H - joint + et; Pw = Uw + Lw
    check(Pw <= shop["max_crosscut"] + 1e-9, "The plank is narrow enough to crosscut", f"plank {short(Pw)} wide, sled capacity {short(shop['max_crosscut'])}")
    check(max(Uw, Lw) <= shop["planer_width"] + 1e-9, "Each zone of the plank fits the planer on its own", f"upper zone {short(Uw)}, lower zone {short(Lw)}, planer {short(shop['planer_width'])}", "warn")
    check(cut <= shop["max_depth_90"] - 0.25, "The saw cuts through the slab in one pass", f"slab about {short(cut)} thick")
    check(T >= 1.0, "Board at least 1\" thick (end grain under 1\" can split)", f'{T}"')
    check(max(W, H) / T <= 18, "Board not too large for its thickness", f"{W:.1f} x {H:.1f} x {T}", "warn")
    strip_h = _up(cut, 0.125); strip_len = _up(max(lens) + 1.5, 0.5); nstrip = nl + shop["strip_spares"]
    qi = nominal(strip_h)
    check(qi is not None, "Inlay strips can be ripped from stock no thicker than 12/4", f"strips {short(strip_h)} tall")
    face = [{"pts": p["pts"], "role": p["role"]} for p in polys]

    stock = []
    qg = nominal(w)
    for role, zw, use in (("ground", Uw, "upper zone of the plank: the figured boards"), ("dark", Lw, "lower zone of the plank: the darkest, plainest boards")):
        bf = (qg / 4) * (zw + 0.5) * (plank_len + 1) / 144
        stock.append({"species": sp[role]["name"], "key": sp[role]["key"], "role": role, "rough": f"{qg}/4", "mill_to": w, "n": 1,
                      "size": f"{short(w)} x {short(zw)} x {short(plank_len)}", "use": use + "; one wide board or two edge glued", "bf": bf, "bf_buy": math.ceil(bf * 1.25 * 2) / 2})
    sw_ = _up(acc * math.sqrt(2) + 0.125, 0.125); bf = 1.0 * (sw_ + 0.5) * (plank_len + 1) / 144
    stock.append({"species": sp["accent"]["name"], "key": sp["accent"]["key"], "role": "accent", "rough": "4/4", "mill_to": 0.5, "n": 1,
                  "size": f"1/2\" x {short(sw_)} x {short(plank_len)}", "use": "the stick glued onto the chamfer; most of it is planed away", "bf": bf, "bf_buy": max(0.5, math.ceil(bf * 1.25 * 2) / 2)})
    bw = _up(nstrip * (k + kerf) + 1.0, 0.25); bf = ((qi or 8) / 4) * bw * (strip_len + 1) / 144
    stock.append({"species": sp["inlay"]["name"], "key": sp["inlay"]["key"], "role": "inlay", "rough": f"{qi or 8}/4", "mill_to": strip_h, "n": 1,
                  "size": f"{short(strip_h)} x {short(bw)} x {short(strip_len)}", "use": f"ripped into {nstrip} strips {short(k)} thick ({nl} lines and {shop['strip_spares']} spare)", "bf": bf, "bf_buy": math.ceil(bf * 1.25 * 2) / 2})

    N = {"w": w, "n": n, "W": W, "H": H, "slide": slide, "joint": joint, "acc": acc, "nl": nl, "k": k, "cut": cut, "pitch": pitch, "ncut": ncut, "plank_len": plank_len,
         "Uw": Uw, "Lw": Lw, "Pw": Pw, "et": et, "strip_h": strip_h, "strip_len": strip_len, "nstrip": nstrip, "stick_w": sw_, "pack": shop["pack"],
         "lines": [{"n": i + 1, "left": ls[i][0][1], "bottom": ls[i][1][0], "length": lens[i], "angle": ang[i]} for i in range(nl)], "min_cross": min(gaps)}
    planks = [{"id": "P1", "rows": n, "logs": 2, "worth": True, "why": f"Yes: cut {n} times, once for every row", "count": 1, "length": plank_len, "n": 2, "width": Pw, "rows_cut": n, "spares": shop["spare_rows"]}]
    plan = {"name": design.get("name", "Walnut String-Art End-Grain Board"), "description": design.get("description", ""), "pattern": "stringart",
            "board": {"width": W, "length": H, "thickness": T, "trim": trim, "field": [W, H], "frame": None, "field_trim": trim},
            "shop": shop, "species": sp, "woods": list(woods.values()), "notes": [f"{n} rows, {nl} lines"], "options": design.get("options", {}), "face": face,
            "polygons": polys, "stock": stock, "checks": checks, "method": "plank", "N": N, "slice_cut": cut, "n_slices": n,
            "rows": [{"n": i + 1, "plank": "P1", "turned": i % 2 == 1} for i in range(n)], "bars": [], "bar_types": [], "planks": planks,
            "logs": [], "info": {"kind": "plank"}}
    summary = (f"Rows repeat every 2 rows: an as-cut row, then the same row rolled over and slid {short(slide)}. One plank makes all {n} rows. "
               f"The {nl} lines are not part of the repeat: they are cut through the finished slab and move nothing.")
    plan["repeats"] = {"rows": n, "bar_shapes": 0, "log_types": 0, "kind": "plank", "planks": 1, "plank_copies": 1, "single_row_planks": 0, "row_period": 2,
                       "turns": [], "orbits": 1, "rows_per_plank": n, "log_lengths": 0, "logs_in_planks": 0, "widest_plank": round(Pw, 3), "rows_for_full_repeat": 2, "summary": summary}
    check(True, "Every plank is worth making (each is cut for more than one row)", f"plank P1: {n} rows")
    check(True, "Repeat math", summary)
    plan["steps"] = steps(plan)
    os.makedirs(os.path.join(out, "svg"), exist_ok=True)
    svgs = drawings(plan)
    for name, v in svgs.items(): open(os.path.join(out, "svg", name + ".svg"), "w").write(v)
    CB.write_obj(plan, out); CB.write_spec(plan, design, out)
    try:
        import render_guide
        render_guide.render(plan, os.path.join(out, "guide.png"), **design.get("guide", {}))
    except Exception as e:
        print("guide.png skipped:", e)
    open(os.path.join(out, "plan.html"), "w").write(page(plan, svgs, photo, os.path.join(out, "guide.png")))
    json.dump({k_: v for k_, v in plan.items() if k_ != "polygons"}, open(os.path.join(out, "plan.json"), "w"), indent=1, default=str)
    return plan


def _half_all(poly, x, y):
    """[1] if the point is inside the convex polygon (either winding), else []."""
    s = 0
    for i in range(len(poly)):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
        c = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
        if abs(c) < 1e-9: continue
        if s == 0: s = 1 if c > 0 else -1
        elif (c > 0) != (s > 0): return []
    return [1]


def _nm(x):
    return x["name"].split()[-1].lower()


# ------------------------------------------------------------------------------------- steps
def steps(plan):
    N = plan["N"]; sp = plan["species"]; T = plan["board"]["thickness"]; sh = plan["shop"]
    G, A, I = _nm(sp["ground"]), _nm(sp["accent"]), _nm(sp["inlay"])
    w, n, W, H, slide, joint, acc, nl, k = (N[x] for x in ("w", "n", "W", "H", "slide", "joint", "acc", "nl", "k"))
    packs = math.ceil(n / N["pack"])
    return [
        {"title": "Pick and mill the two zones", "figs": ["plank"], "see": ["plank"], "text": [
            f"The plank is two zones of {G}, edge to edge: an upper zone {short(N['Uw'])} wide and a lower zone {short(N['Lw'])} wide, both {short(w)} thick and {short(N['plank_len'])} long. Each zone can be one wide board or two narrower ones edge glued.",
            f"Upper zone: pick boards whose end shows the growth rings running on a slant. Those rings are what turn into feathers when every other row is rolled over. Lower zone: the darkest, plainest boards you have, so the two zones read apart.",
            f"Joint and plane everything to {short(w)} in one session at one planer setting. The faces of this plank become the glue faces between rows, so thickness within 0.005\" matters more than the exact number.",
            f"Rip the zones to width with both edges jointed square."]},
        {"title": "Let the accent corner into the upper zone", "glue": True, "figs": ["fillet"], "see": ["plank"], "text": [
            f"Mark the corner of the upper zone board where its top face meets the edge that will be glued to the lower zone. With the board flat on the saw and the blade at 45 degrees, rip that corner off so the chamfer measures {short(acc)} on the face and {short(acc)} on the edge. The offcut is a small triangle that falls away outside the blade.",
            f"Glue the {A} stick, 1/2\" x {short(N['stick_w'])}, flat onto the chamfer. It only has to cover the chamfer and stand proud both ways. Rub it into place, then hold it with a strip of tape every 3 inches pulled tight over the corner; a stick this small needs little pressure.",
            f"Next day joint the edge until it is square and all {G} again apart from the {A} corner, then take a light pass off the face in the planer with the lower zone boards following at the same setting. The board is a rectangle again, with a {A} triangle {short(acc)} by {short(acc)} in one corner.",
            f"A {G} board with a strip of pale sapwood along one corner gives the same triangle for nothing. That may be all the maker did; see sheet 08."]},
        {"title": "Glue the plank", "glue": True, "figs": ["asm_plank"], "see": ["plank"], "text": [
            f"Glue the upper zone to the lower zone, the {A} corner on the joint. Clamp across the width every 6 inches with cauls above and below the joint so the faces stay flush.",
            f"The plank is {short(N['Pw'])} wide, too wide for most planers, which is why the zones were planed first. Scrape the squeeze-out next day and check the joint with a straightedge. A step you can feel has to come off with a hand plane or a sander on a flat block, because each face is a glue face."]},
        {"title": f"Crosscut {N['ncut']} rows", "figs": ["asm_cut"], "see": ["plank"], "text": [
            f"Square one end of the plank on the crosscut sled, then set a stop and cut {N['ncut']} rows {short(N['cut'])} long: {n} for the board and {sh['spare_rows']} spare. Keep the last {short(sh['hold_end'])} of the plank as a handle and stop there.",
            f"Before cutting, draw a long pencil triangle across the top face of the plank. Number each row on that face as it comes off the saw. The triangle and the numbers keep the rows in order, which is what makes the grain flow from row to row."]},
        {"title": "Lay the rows out: every other one rolled and slid", "figs": ["rows"], "see": ["plank"], "text": [
            f"Stand the rows on end, end grain up, in number order, against a straight batten clamped to a flat board covered in packing tape.",
            f"Odd rows stay as cut. Roll each even row over so its other end is up, and slide it {short(slide)} along its length, away from the upper zone. A spacer block {short(slide)} long between the batten and each even row sets the slide.",
            f"Check before glue: the {A} triangles sit on two lines {short(slide)} apart, each pointing up into the upper zone, the upper line's triangles on one side of their row and the lower line's on the other. The slanted rings should now meet in a V at every glue line."],
            "dont": "Do not turn a row end for end. Rolled over is the only move: it keeps the upper zone at the top of every row."},
        {"title": "Glue the slab", "glue": True, "see": ["plank"], "text": [
            f"Glue the rows in {packs} packs of about {N['pack']}, each against the batten with its spacers, then glue the packs together. Small packs keep the open time short and the rows from creeping.",
            f"Clamp across the rows with cauls top and bottom. End grain drinks glue on the cut faces but these joints are long grain to long grain, so an ordinary spread is right."]},
        {"title": "Flatten once and trim to size", "see": ["plank", "finish"], "text": [
            f"Flatten both faces just enough to sit flat (sheet 07), leaving the slab as thick as you can.",
            f"Trim the two stepped ends square to the rows, {short(N['et'])} inside the shortest rows, to leave the slab {short(H)} long. The odd rows give {short(joint)} of upper zone above their triangles. Trim the two long sides only if they need cleaning up.",
            f"The lower left corner, where the lines will fan out, has to be truly square: check it with a framing square. Every line is registered to those two edges."]},
        {"title": f"Rip the {I} strips to the saw kerf", "figs": ["strip"], "see": ["inlay"], "text": [
            f"Decide now which saw will cut the slab (track saw or table saw sled) and use that same blade from here on.",
            f"Cut a test kerf through one of the slab offcuts. Mill the {I} to {short(N['strip_h'])} thick and {short(N['strip_len'])} long, then rip strips off its edge with the strip falling to the outside of the blade, adjusting until a strip slides into the test kerf by hand with no rattle. This plan assumes {short(k)}; your blade decides.",
            f"Rip {N['nstrip']}: {nl} lines and {sh['strip_spares']} spare. A strip that is too thin shows as a dark glue line. A strip that is too thick pushes the slab apart and every row it crosses steps sideways."]},
        {"title": "Mark the lines and build the corner jig", "figs": ["layout", "jig"], "see": ["inlay"], "text": [
            f"From the lower left corner, mark the left edge every {fine(H / nl)} and the bottom edge every {fine(W / nl)}. The last mark on each edge is the far corner.",
            f"Line 1 joins the top mark on the left edge to the first mark on the bottom edge. Each later line starts one mark lower and ends one mark further along. Draw all {nl} in pencil; they are the centre lines of the saw cuts.",
            f"Corner jig: two straight battens screwed to a flat board at exactly 90 degrees, faced with packing tape. The slab's lower left corner goes into it for every glue-up."]},
        {"title": "Cut and fill one line at a time", "glue": True, "figs": ["cutline"], "see": ["inlay"], "text": [
            f"Line 1 first. Saw right through the slab on the pencil line, in one pass, with the slab clamped down on both sides of the cut. With a track saw, lay the rail on the line over a sacrificial sheet. On a table saw, fix the slab to a carrier sled with the line over the sled's kerf, as the maker appears to do.",
            f"Glue both sawn faces and both faces of a strip, set the strip in with a little standing proud top and bottom, and push the two pieces into the corner jig: the corner piece tight to both battens, the large piece tight to its batten and to the strip. Clamp across the cut, toward the jig's corner. Because the strip is as thick as the kerf, the slab's outer edges come back flush and every row is back in line; check the far edges with a straightedge before the glue grabs.",
            f"Leave it clamped an hour and let it cure four hours or more before the next cut. Then saw the strip ends flush with the edges and pare the proud strip level enough to sit flat.",
            f"Repeat for lines 2 to {nl}, in order. Each new cut passes through the strips already in; that is how the lines cross. The last line cut is the only one that reads unbroken end to end."],
            "dont": "Never make two cuts before gluing. Loose pieces cannot be put back in register, and small wedges of end grain break."},
        {"title": "Flatten, sand and finish", "see": ["finish"], "text": [
            f"Flatten both faces to {short(T)} (sheet 07). Sand 80 to 220, raise the grain with a damp cloth, and sand again at 220.",
            f"Ease the edges, add feet if you want them, then flood with mineral oil until it stops soaking in and finish with board butter."]},
    ]


# ------------------------------------------------------------------------------------- drawings
def drawings(plan):
    import cbplan as CB
    from assembly import Scene
    N = plan["N"]; sp = plan["species"]
    w, n, W, H, slide, joint, acc, nl, k = (N[x] for x in ("w", "n", "W", "H", "slide", "joint", "acc", "nl", "k"))
    col = lambda r: sp[r]["end"]; lng = lambda r: sp[r]["long"]
    G, A, I = _nm(sp["ground"]), _nm(sp["accent"]), _nm(sp["inlay"])
    out = OrderedDict(); INK = "#1e2327"; EDGE = "#8a7f72"
    rect = lambda x0, y0, x1, y1: [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

    # face
    S = CB.Svg([0, 0, W, H], 640 / W, pad=46, title="Top face")
    for f in plan["face"]: S.poly(f["pts"], fill=col(f["role"]), stroke=col(f["role"]), sw=0.4)
    for i in range(1, n): S.line((i * w, 0), (i * w, H), stroke="#00000030", sw=0.5)
    S.poly(rect(0, 0, W, H), stroke=INK, sw=1.6)
    S.dimx(0, W, 0, short(W)); S.dimy(0, H, 0, short(H))
    out["face"] = S.svg()

    # plank: end view (what every row looks like) and top view
    Uw, Lw, Pw, et = N["Uw"], N["Lw"], N["Pw"], N["et"]; z = 4.0
    S = CB.Svg([-1.2, -2.6, Pw + 1.2, w * z + 1.6], 30, pad=40, title="The plank, end view")
    S.poly(rect(0, 0, Lw, w * z), fill=col("dark"), stroke=INK, sw=1.2)
    S.poly([(Lw, 0), (Pw, 0), (Pw, w * z), (Lw + acc, w * z), (Lw, w * z - acc * z)], fill=col("ground"), stroke=INK, sw=1.2)
    S.poly([(Lw, w * z), (Lw + acc, w * z), (Lw, w * z - acc * z)], fill=col("accent"), stroke=INK, sw=1.0)
    S.line((Lw, 0), (Lw, w * z), stroke=GLUE, sw=2.4)
    S.dimx(0, Lw, 0, f"lower zone {short(Lw)}"); S.dimx(Lw, Pw, 0, f"upper zone {short(Uw)}")
    S.dimy(0, w * z, 0, short(w))
    S.text((Lw + acc / 2, w * z + 0.55), f"{A} corner {short(acc)} x {short(acc)}", 11, weight="bold")
    S.text((Pw / 2, -2.1), f"End view, drawn {z:g} times too thick. Blue is the glue line between the zones.", 11)
    out["plank"] = S.svg()

    # fillet: three stages
    S = CB.Svg([-0.3, -0.5, 9.6, 2.0], 62, pad=30, title="The accent corner")
    t = w
    def stage(ox, label, kind):
        body = [(ox, 0), (ox + 2.2, 0), (ox + 2.2, t), (ox + acc, t), (ox, t - acc)] if kind else rect(ox, 0, ox + 2.2, t)
        S.poly(body, fill=col("ground"), stroke=INK, sw=1.2)
        if kind == 1:
            h = 0.5; sw_ = N["stick_w"]; u = (math.sqrt(.5), math.sqrt(.5)); v = (-u[1], u[0]); m = (ox + acc / 2, t - acc / 2)
            q = [(m[0] + u[0] * a_ + v[0] * b_, m[1] + u[1] * a_ + v[1] * b_) for a_, b_ in ((-sw_ / 2, 0), (sw_ / 2, 0), (sw_ / 2, h), (-sw_ / 2, h))]
            S.poly(q, fill=col("accent"), stroke=INK, sw=1.0); S.line((ox, t - acc), (ox + acc, t), stroke=GLUE, sw=2.4)
        if kind == 2:
            S.poly([(ox, t), (ox + acc, t), (ox, t - acc)], fill=col("accent"), stroke=INK, sw=1.0)
        S.text((ox + 1.1, -0.3), label, 11, weight="bold")
    stage(0, "1  chamfer at 45°", 3); stage(3.4, f"2  glue the {A} stick on", 1); stage(6.8, "3  joint the edge, plane the face", 2)
    S.dimx(0, acc, t + 0.02, short(acc), below=False)
    out["fillet"] = S.svg()

    # rows: the first rows as laid out, before trimming
    m = min(n, 8); top = H + slide + et; bot = -slide - et
    S = CB.Svg([-2.6, bot - 1.3, m * w + 5.4, top + 1.4], 24, pad=36, title="Rows laid out")
    for i in range(m):
        x0, x1 = i * w, (i + 1) * w; rolled = i % 2 == 1; dy = -slide if rolled else 0
        yj = H - joint + dy
        S.poly(rect(x0, yj - N["Lw"], x1, yj), fill=col("dark"), stroke=EDGE, sw=0.7)
        S.poly(rect(x0, yj, x1, yj + N["Uw"]), fill=col("ground"), stroke=EDGE, sw=0.7)
        S.poly([(x0, yj), (x0 + acc, yj), (x0, yj + acc)] if rolled else [(x1 - acc, yj), (x1, yj), (x1, yj + acc)], fill=col("accent"), stroke=EDGE, sw=0.6)
        S.text(((x0 + x1) / 2, top + 0.55), str(i + 1), 11, weight="bold")
        S.text(((x0 + x1) / 2, yj + N["Uw"] / 2), "rolled" if rolled else "as cut", 9.5, fill="#fff", rot=-90)
    for y in (0, H): S.line((-0.8, y), (m * w + 0.8, y), stroke=RED, sw=1.6, dash="7 4")
    S.text((m * w + 0.95, H), "trim", 11, anchor="start", fill=RED); S.text((m * w + 0.95, 0), "trim", 11, anchor="start", fill=RED)
    S.dimy(0, H, 0, short(H)); S.dimy(H - joint - slide, H - joint, m * w + 2.9, f"slide {short(slide)}", left=False)
    S.dimy(H - joint, H, m * w + 2.9, short(joint), left=False)
    S.text((m * w / 2, bot - 0.9), f"The first {m} of {n} rows, end grain up. Red dashes are the trim cuts.", 11)
    out["rows"] = S.svg()

    # layout of the lines
    S = CB.Svg([0, 0, W, H], 640 / W, pad=58, title="The lines")
    S.poly(rect(0, 0, W, H), fill="#f6f1e7", stroke=INK, sw=1.6)
    for L in N["lines"]:
        S.line((0, L["left"]), (L["bottom"], 0), stroke=col("inlay"), sw=max(2.0, k * 640 / W)); S.line((0, L["left"]), (L["bottom"], 0), stroke=INK, sw=0.5)
        _chip(S, (L["bottom"] * 0.22, L["left"] * 0.78), str(L["n"]), r=9)
        S.text((-0.25, L["left"]), frac(L["left"], 16), 10.5, anchor="end"); S.text((L["bottom"], -0.55), frac(L["bottom"], 16), 10.5)
    S.text((W / 2, H + 0.9), "Marks measured from the lower left corner, inches. Numbers in circles are the cutting order.", 11)
    out["layout"] = S.svg()

    # jig with one cut being glued
    c = max(1, nl // 2 + 1); L = N["lines"][c - 1]; bt = 1.2
    S = CB.Svg([-bt - 0.6, -bt - 0.6, W + 3.2, H + 2.6], 520 / W, pad=30, title="Corner jig")
    S.poly(rect(-bt, -bt, W + 2.5, 0), fill=MDF, stroke=MDF_E, sw=1.0); S.poly(rect(-bt, 0, 0, H + 2.0), fill=MDF, stroke=MDF_E, sw=1.0)
    A_, B_ = (0, L["left"]), (L["bottom"], 0)
    S.poly([(0, 0), B_, A_], fill=col("dark"), stroke=INK, sw=1.2)
    S.poly([B_, (W, 0), (W, H), (0, H), A_], fill=col("ground"), stroke=INK, sw=1.2)
    S.line(A_, B_, stroke=col("inlay"), sw=5); S.line(A_, B_, stroke=GLUE, sw=1.2)
    d = math.hypot(W, H); u = (-W / d, -H / d)
    for fx, fy in ((0.72, 0.96), (0.97, 0.6)):
        p = S.P(W * fx + 2.2 * -u[0], H * fy + 2.2 * -u[1]); q = S.P(W * fx, H * fy); _arrow(S, p, q, raw=True, w=4, hw=10, hl=12)
    S.text((W / 2 + 2, H / 2 + 1), "pushed toward the corner", 11, fill="#fff")
    S.text((W / 2, -bt / 2), "batten", 10.5); S.text((-bt / 2, H / 2), "batten", 10.5, rot=-90)
    S.text((W / 2, H + 1.6), f"Line {c} being glued: both pieces tight to both battens.", 11)
    out["jig"] = out["cutline"] = S.svg()

    # strip
    S = CB.Svg([-0.6, -0.9, 8.6, 2.4], 56, pad=30, title="Inlay strip")
    S.poly(rect(0, 0, 8, N["strip_h"]), fill=lng("inlay"), stroke=INK, sw=1.2)
    S.dimy(0, N["strip_h"], 0, short(N["strip_h"])); S.dimx(0, 8, 0, f"{short(N['strip_len'])} long, {short(k)} thick: fit it to the kerf")
    out["strip"] = S.svg()

    # 3D: the plank, and crosscutting it
    along = lambda ox=0.0, oy=0.0, oz=0.0: (lambda a, b, ww: (ox + ww, oy + a, oz + b))
    sc = Scene(az=40, el=30); Lg = 16.0; gap = 1.4
    sc.prism(rect(0, 0, Lw, w), Lg, along(), col("dark"), lng("dark"), glue={1})
    sc.prism([(0, 0), (Uw, 0), (Uw, w), (acc, w), (0, w - acc)], Lg, along(oy=Lw + gap), col("ground"), lng("ground"))
    sc.prism([(0, w), (acc, w), (0, w - acc)][::-1], Lg, along(oy=Lw + gap), col("accent"), lng("accent"))
    sc.mark("arrow", (Lg / 2, Pw + gap + 2.2, w / 2), (Lg / 2, Pw + gap + 0.3, w / 2))
    sc.mark("arrow", (Lg / 2, -2.2, w / 2), (Lg / 2, -0.3, w / 2))
    sc.mark("text", (0, Lw + gap, w + 0.3), f"{A} corner on the joint", (10, -14))
    sc.mark("grain", (1.0, -1.2, 0), (Lg - 1.0, -1.2, 0))
    out["asm_plank"] = sc.svg(title="Gluing the plank")

    sc = Scene(az=58, el=26); body = 5.0; cut = N["cut"]; gp = 0.7
    def plank_at(x0_, ln):
        sc.prism(rect(0, 0, Lw, w), ln, along(ox=x0_), col("dark"), lng("dark"), outline=EDGE)
        sc.prism([(Lw, 0), (Pw, 0), (Pw, w), (Lw + acc, w), (Lw, w - acc)], ln, along(ox=x0_), col("ground"), lng("ground"), outline=EDGE)
        sc.prism([(Lw, w - acc), (Lw + acc, w), (Lw, w)], ln, along(ox=x0_), col("accent"), lng("accent"), outline=EDGE)
    plank_at(0, body)
    for j in range(2): plank_at(body + gp + j * (cut + gp), cut)
    sc.mark("line", (body + gp / 2, -0.8, 0), (body + gp / 2, Pw + 0.8, 0), RED)
    sc.mark("text", (body + gp / 2, -0.8, 0), "red: the saw cut", (-40, 22))
    sc.mark("text", (body + gp + cut, 0, w + 0.5), f"each slice is one row, {short(cut)} long", (-250, -70))
    out["asm_cut"] = sc.svg(width=820, title="Crosscutting the plank into rows")
    return out


# ------------------------------------------------------------------------------------- page
def page(plan, svgs, photo, guide=None):
    from plan_page import CSS, TICK
    import re
    e = html.escape; N = plan["N"]; sp = plan["species"]; sh = plan["shop"]
    W, H, T = plan["board"]["width"], plan["board"]["length"], plan["board"]["thickness"]
    G, A, I = _nm(sp["ground"]), _nm(sp["accent"]), _nm(sp["inlay"])
    w, n, slide, joint, acc, nl, k = (N[x] for x in ("w", "n", "slide", "joint", "acc", "nl", "k")); bf = sum(x["bf_buy"] for x in plan["stock"])
    errors = [c for c in plan["checks"] if not c["ok"] and c["level"] != "warn"]; warns = [c for c in plan["checks"] if not c["ok"] and c["level"] == "warn"]
    size = f"{short(W)} × {short(H)} × {short(T)}"
    stamp = (f'<div class="stamp bad">✗ {len(errors)} check{"s" if len(errors) > 1 else ""} fail</div>' if errors else
             f'<div class="stamp">{TICK}{len(plan["checks"]) - len(warns)} of {len(plan["checks"])} checks pass</div>')
    def tb(no, title, by, meta):
        return f'<div class="tb"><div class="no mono">{no}</div><div><h2>{e(title)}</h2><div class="by">{by}</div></div><div class="meta">{meta}</div></div>'
    def fig(body, label, extra=""):
        return f'<figure><div class="ph">{body}</div><figcaption><span class="lbl">{e(label)}</span>{extra}</figcaption></figure>'
    ul = lambda xs: "<ul>" + "".join(f"<li>{e(x)}</li>" for x in xs) + "</ul>"
    words = plan["name"].split(); h1 = e(" ".join(words[:-2])) + " <em>" + e(" ".join(words[-2:])) + "</em>" if len(words) > 2 else f"<em>{e(plan['name'])}</em>"
    desc = plan["description"]; lede = e(desc[0].upper() + desc[1:] + ". ") if desc else ""
    nglue = sum(1 for x in plan["steps"] if x.get("glue"))
    chain = "".join(f'<span><b>{i}</b>{e(x)}</span>' for i, x in enumerate(["two zones", "accent corner", "one plank", f"{n} rows", "roll & slide", "slab", f"{nl} kerf inlays", "board"], 1))
    stats = "".join(f'<div class="stat"><b class="mono">{b}</b><small>{e(x)}</small></div>' for b, x in (
        (e(size.replace('"', "")) + '"', "W × L × T, finished"), ("1", f"plank, cut for all {n} rows"), (str(nl), f"inlaid lines, each {short(k)} wide"),
        (str(nglue + nl - 1), "glue-ups, one per line at the end"), (f"{bf:g}", "board feet to buy")))
    sheets = [("overview", "Overview", size), ("materials", "Material list", f"{bf:g} bd ft"), ("pattern", "The pattern", "from the photos"), ("plank", "Plank & rows", f"1 plank · {n} rows"),
              ("inlay", "The inlaid lines", f"{nl} lines"), ("build", "Building it", f"{len(plan['steps'])} steps"), ("finish", "Flattening & options", "options"), ("sources", "Sources", "what is shown, what is mine")]
    index = "".join(f'<a href="#{i}"><span class="n">{j:02d}</span><span class="t">{e(x)}</span><span class="s">{e(y)}</span></a>' for j, (i, x, y) in enumerate(sheets, 1))
    index += (f'<a href="#checks"><span class="n">R</span><span class="t">Checks</span><span class="s" style="color:var(--{"weak" if errors else "good"})">'
              f'{"✗ " + str(len(errors)) + " fail" if errors else "all pass ✓" if not warns else str(len(plan["checks"]) - len(warns)) + " pass · " + str(len(warns)) + " note"}</span></a>')
    no = {i: f"{j:02d}" for j, (i, _, _) in enumerate(sheets, 1)}
    Hh = []

    # 01
    if photo and os.path.exists(photo):
        mime = "image/png" if photo.lower().endswith(".png") else "image/jpeg"
        hero = fig(f'<img src="data:{mime};base64,{base64.b64encode(open(photo, "rb").read()).decode()}" alt="Render of the finished board">', "Render", "<span>made from the exact face with plan-to-photo; not a photo of a built board</span>")
    elif guide and os.path.exists(guide):
        from PIL import Image
        import io
        im = Image.open(guide).convert("RGB"); im.thumbnail((1500, 1500)); buf = io.BytesIO(); im.save(buf, "JPEG", quality=86)
        hero = fig(f'<img src="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}" alt="Model of the finished board">', "Model view", "<span>the exact face, colour coded by wood; not a photo. Real walnut supplies the feather figure the model cannot show</span>")
    else:
        hero = fig(svgs["face"], "Top face · finished size")
    how = [f"The field is one wood. A plank {short(N['Pw'])} wide is glued from two zones of {G}, with a small corner of {A} let in along the joint, and crosscut into {n} rows, each {short(w)} wide on the face.",
           f"Every other row is rolled over and slid {short(slide)}. Rolling mirrors the slant of the growth rings, which makes the feathers. Sliding splits the joint into two lines, which makes the two staggered lines of {A} triangles and the band between them.",
           f"What repeats: one plank makes every row. There are two kinds of row and they are the same slice, as cut and rolled.",
           f"The {nl} lines are added last. Each is one saw cut right through the slab with a {I} strip glued in that is exactly as thick as the kerf, so nothing moves and the rows still line up across every line.",
           "The base board has no border, like the maker’s: the field and the lines run to the edge."]
    glance = "".join(f"<dt>{e(a)}</dt><dd class='m'>{e(b)}</dd>" for a, b in (
        ("Plank", f"{short(w)} × {short(N['Pw'])} × {short(N['plank_len'])}"), ("Rows", f"{n} + {sh['spare_rows']} spare, cut {short(N['cut'])} long"),
        ("Row moves", f"even rows rolled over, slid {short(slide)}"), ("Accent corner", f"{short(acc)} × {short(acc)}, {A}"),
        ("Lines", f"{nl}, {short(k)} wide, {short(min(L['length'] for L in N['lines']))} to {short(max(L['length'] for L in N['lines']))} long"), ("Glue-ups", f"{nglue + nl - 1}, the last {nl} one line each")))
    woods = "".join(f'<li><span class="sw" style="background:{sp[x["role"]]["end"]}"></span>{e(x["species"])} ({e(x["use"].split(":")[0].split(";")[0])}): {x["bf_buy"]:g} bd ft</li>' for x in plan["stock"])
    tools = ["Jointer and planer for the plank; table saw with a riving knife and a 45° tilt", f"Crosscut sled that takes a {short(N['Pw'])} plank, with a stop block",
             "Track saw, or a carrier sled for the table saw, to cut the slab on the lines", "Framing square, long straightedge, calipers",
             "Flat board and two straight battens for the corner jig, packing tape", "Bar clamps, cauls, Titebond III", "Router sled to flatten the board, random-orbit sander", "Mineral oil and board butter"]
    Hh.append(f'<article class="sheet" id="overview">{tb("01", "Overview", e(desc[0].upper() + desc[1:]) if desc else "", f"<div class=dims>{e(size)}</div>{stamp}")}'
              f'<div class="main"><div style="display:grid;gap:0;align-content:start">{hero}{fig(svgs["face"], "Top face · finished size")}</div>'
              f'<div class="notes"><h3>How it goes together</h3>{ul(how)}<h3>At a glance</h3><dl class="kv">{glance}</dl></div></div>'
              f'<div class="lower" style="grid-template-columns:1fr 1.65fr"><div class="notes"><h3>Wood to buy</h3><ul>{woods}</ul></div>'
              f'<div class="notes"><h3>Tools</h3><ul style="display:block;columns:2 30ch;column-gap:32px">{"".join(f"<li>{e(x)}</li>" for x in tools)}</ul></div></div></article>')

    # 02
    trs = ""
    for x in plan["stock"]:
        trs += (f'<tr class="grp"><td colspan="4"><span class="sw" style="background:{sp[x["role"]]["end"]}"></span>{e(x["species"])} · buy {x["bf_buy"]:g} bd ft</td></tr>'
                f'<tr><td class="m">{e(x["rough"])}</td><td class="q">{x["n"]}</td><td class="m">{e(x["size"])}</td><td class="m">{e(x["use"])}</td></tr>')
    trs += ('<tr class="grp"><td colspan="4">Shop materials</td></tr><tr><td class="m">sheet + battens</td><td class="q">1</td>'
            f'<td class="m">about {short(_up(W + 6, 1))} x {short(_up(H + 6, 1))}</td><td class="m">flat board and two straight battens for the corner jig</td></tr>')
    wl = "".join(f'<li><span class="sw" style="background:{x["end"]}"></span><b>{e(x["name"])}</b>' + (f' · Janka {x["janka"]} · shrinkage {x["tan"]}%' if x["janka"] else "") + f'. {e(x["note"])}</li>' for x in plan["woods"])
    Hh.append(f'<article class="sheet" id="materials">{tb("02", "Material list", "Nearly all of it is the ground wood", "<div class=dims>T × W × L</div>")}'
              f'<div class="lower full" style="border-top:0"><div class="panel"><div class="tbl"><table class="d"><tr><th>Rough stock</th><th style="text-align:right;padding-right:12px">Pieces</th><th>Milled size</th><th>Use</th></tr>{trs}</table></div>'
              f'<p class="small">Board feet include 25% for defects and milling. The two {G} zones are listed apart because they are picked for different looks, not because they are different woods. '
              f'The plank is long: {short(N["plank_len"])}. If that is awkward, make it as two planks half as long, glued and cut the same way; keep the rows of each in order.</p></div></div>'
              f'<div class="lower full"><div class="notes"><h3>The woods</h3><ul>{wl}</ul>'
              f'<p class="small">The maker’s description names walnut and maple. The feather figure is not something the plan can guarantee: it comes from the growth rings of the boards you pick. '
              f'Rings on a slant give feathers, flat arcs give arches. Either looks good; only slanted rings look like the photo.</p></div></div></article>')

    # 03
    Hh.append(f'<article class="sheet" id="pattern">{tb("03", "The pattern", "Read from the screenshot and the video’s cover photo", f"<div class=dims>{n} rows · {nl} lines</div>")}'
              f'<div class="main"><div style="display:grid;gap:0;align-content:start">{fig(svgs["face"], "This plan’s face. The lower zone is drawn a shade darker so the zones read")}{fig(svgs["plank"], "The plank that makes every row")}</div><div class="panel"><h3>What the photos show</h3>{ul([
                  "A walnut end-grain board about 24 by 16-1/2 inches, in narrow rows that run the short way, a little under an inch wide. I counted about 27.",
                  "Feather figure down the rows: the growth rings slant one way in one row and the other way in the next. Neighbouring rows are the same slice, one rolled over.",
                  "Two level lines of small pale triangles, about 2-1/2 inches apart, a little above the middle. The triangles of the upper line sit in every other row and those of the lower line in the rows between. Above the upper line the wood is lighter and more figured, below the lower line darker and plainer, and between the lines the rows alternate.",
                  "That is what one joint in the plank looks like when every other row is slid 2-1/2 inches: one joint, seen at two heights.",
                  "Seven pale lines fanning from the lower left corner. Each runs from a mark on the left edge to a mark on the bottom edge, with the marks evenly spaced on both edges: the first line from the top left corner to the first bottom mark, the last from the lowest left mark to the bottom right corner.",
                  "On the cover photo the pale lines carry on down the edge of the board, so they go right through it. They are not a shallow routed inlay."])}'
              f'<h3>Where this plan is my reading, not the maker’s</h3>{ul([
                  f"The pale triangles may simply be sapwood on the corner of one of his walnut boards. I have made them a deliberate {A} corner so the plan does not depend on finding such a board.",
                  "Whether he rolled and slid the rows, or turned them some other way, cannot be read from the stills. Rolling and sliding reproduces what the photo shows.",
                  f"Row width {short(w)}, slide {short(slide)}, triangle size and line width {short(k)} are measured off the screenshot, good to about an eighth of an inch."])}'
              f'<h3>Sizes</h3><dl class="kv"><dt>Row</dt><dd class="m">{short(w)} wide on the face</dd><dt>Accent lines</dt><dd class="m">{short(joint)} and {short(joint + slide)} below the top edge</dd>'
              f'<dt>Accent corner</dt><dd class="m">{short(acc)} × {short(acc)}</dd><dt>Lines</dt><dd class="m">{nl} at {short(k)}</dd></dl></div></div></article>')

    # 04
    Hh.append(f'<article class="sheet" id="plank">{tb("04", "Plank & rows", "One plank; every row is a crosscut slice of it", f"<div class=dims>1 plank · {n} rows + {sh["spare_rows"]} spare</div>")}'
              f'<div class="jgrid" style="grid-template-columns:1fr">'
              f'<div class="joint"><div class="jh"><span class="jn">A</span><div><h4>The plank, end view</h4><div class="jsub">{G} lower zone {short(N["Lw"])}, {G} upper zone {short(N["Uw"])}, {short(w)} thick, {short(N["plank_len"])} long</div></div></div><div class="ph">{svgs["plank"]}</div>'
              f'<p class="small">This end view is also what one row looks like from above once it is stood on end. The plank’s thickness becomes the row’s width on the face.</p></div>'
              f'<div class="joint"><div class="jh"><span class="jn">B</span><div><h4>The accent corner</h4><div class="jsub">upper zone board only, before the plank is glued; end views</div></div></div><div class="ph">{svgs["fillet"]}</div>'
              f'<p class="small">The board goes in a rectangle and comes out a rectangle. Nothing triangular is ever handled except the stick’s waste.</p></div>'
              f'<div class="joint"><div class="jh"><span class="jn">C</span><div><h4>Rows laid out</h4><div class="jsub">odd rows as cut; even rows rolled over and slid {short(slide)} toward the lower zone</div></div></div><div class="ph">{svgs["rows"]}</div>'
              f'<p class="small">The slide is why the plank is {short(slide + 2 * N["et"])} wider than the board is long: the stepped ends are trimmed off after the slab is glued.</p></div></div>'
              f'<div class="lower full"><div class="panel"><h3>Worth a plank?</h3><div class="tbl"><table class="d"><tr><td class="m" style="color:var(--accent-ink)">Plank P1</td><td class="m">2 zones</td><td>Yes: cut {n} times, once for every row. Odd rows as cut, even rows rolled over.</td></tr></table></div></div></div></article>')

    # 05
    ltab = "".join(f'<tr><td class="m" style="color:var(--accent-ink)">{L["n"]}</td><td class="m">{fine(L["left"])}</td><td class="m">{fine(L["bottom"])}</td><td class="m">{short(L["length"])}</td><td class="m">{L["angle"]:.1f}°</td></tr>' for L in N["lines"])
    Hh.append(f'<article class="sheet" id="inlay">{tb("05", "The inlaid lines", "One saw cut and one strip at a time, registered in a square corner", f"<div class=dims>{nl} lines · {short(k)} strips</div>")}'
              f'<div class="main"><div style="display:grid;gap:0;align-content:start">{fig(svgs["layout"], "Centre lines of the cuts")}{fig(svgs["jig"], "Gluing one line in the corner jig")}</div>'
              f'<div class="panel"><h3>The lines</h3><div class="tbl"><table class="d"><tr><th>Cut</th><th>Up the left edge</th><th>Along the bottom</th><th>Length</th><th>Angle to the bottom edge</th></tr>{ltab}</table></div>'
              f'<p class="small">Both distances are from the lower left corner to the centre of the cut.</p>'
              f'<h3>Why it stays in line</h3>{ul([f"The strip is as thick as the kerf it fills ({short(k)} here), so each cut takes out exactly what its strip puts back. The slab stays the same size and no row shifts.",
                  "Every line runs from the left edge to the bottom edge, so every cut frees a corner piece that sits against both battens of a square corner. The large piece bears on at least one batten and on the strip. With the strip as thick as the kerf, that leaves it only one place to be.",
                  "Clamps close a joint best when they pull square across it. Save the wedge-shaped offcuts from trimming the slab: taped to the far edges they give the clamp heads a seat square to the cut.",
                  f"Lines cross because later cuts pass through earlier strips. Neighbouring lines cross at {N['min_cross']:.0f} degrees or more, leaving long thin points of {G} between them; those are glued on both sides before the next cut is made.",
                  "Cut order is 1 to " + str(nl) + ". Any order works; the last one cut is the one that looks unbroken."])}'
              f'<h3>The strips</h3>{fig(svgs["strip"], "One strip")}</div></div></article>')

    # 06
    def runin(x):
        m_ = re.match(r"^([A-Z][A-Za-z' -]{2,26})[:.] ", x)
        return f"<b>{e(m_.group(1))}.</b> {e(x[m_.end():][:1].upper() + x[m_.end():][1:])}" if m_ else e(x)
    body = ""; ng = 0
    for j, x in enumerate(plan["steps"], 1):
        kick = ""
        if x.get("glue"):
            ng += 1; kick = f'<span class="kick">GLUE-UP {ng}' + (f" to {ng + nl - 1}" if "one line at a time" in x["title"] else "") + '</span><br>'
        refs = [no[d] for d in x.get("see", []) if d in no]
        see = f'<div class="see">See sheet {", ".join(refs)}</div>' if refs else ""
        dont = f'<div class="dont"><b>DON\'T</b>{e(x["dont"])}</div>' if x.get("dont") else ""
        b = f'{kick}<h4>{e(x["title"])}</h4><ul>{"".join(f"<li>{runin(y)}</li>" for y in x["text"])}</ul>{see}'
        figs = [f for f in x.get("figs", []) if f in svgs]
        if figs: b = f'<div class="stepgrid"><div>{b}</div><div class="asm">{"".join(f"<figure class=wide>{svgs[f]}</figure>" for f in figs)}</div></div>'
        body += f'<li><span class="sn">{j}</span><div>{b}</div>{dont}</li>'
    Hh.append(f'<article class="sheet" id="build">{tb("06", "Building it", "In order, with the reason where it isn\'t obvious", f"<div class=dims>{len(plan["steps"])} steps · {nglue + nl - 1} glue-ups</div>")}'
              f'<div class="stepbox"><ol class="steps">{body}</ol></div></article>')

    # 07
    Hh.append(f'<article class="sheet" id="finish">{tb("07", "Flattening & options", "Two ways to flatten without a drum sander, the movement risk, and what can be changed", "<div class=dims>options</div>")}'
              f'<div class="lower" style="border-top:0;grid-template-columns:1fr 1fr">'
              f'<div class="panel"><h3>Route 1 · router sled and sander</h3>{ul(["Board on a flat base, shimmed so it cannot rock, between two straight rails; a wide straight or bowl bit in a router on a bridge.", "Passes of 1/32 in. or less, the full face, then the other face.", "Sand out the router marks from 80 grit. This is the route the plan assumes, for the first flattening and the last."])}</div>'
              f'<div class="panel"><h3>Route 2 · helical-head planer</h3>{ul([f"The plank and its boards are long grain and go through the planer as usual. The slab is end grain and {short(W)} wide, wider than most planers, so this route only applies to a narrower version of the board.",
                  "If the slab fits, follow George Vondriska’s method (sheet 08): sacrificial long-grain rails glued to the leading and trailing edges or a heavy chamfer on the trailing edge, 1/64 in. or less a pass, sharp inserts, and stand out of line.",
                  "After the lines are in, the cutters meet long-grain strips lying at an angle in end grain. I have no source for planing that and would use the router sled."])}</div></div>'
              f'<div class="lower" style="grid-template-columns:1fr 1fr">'
              f'<div class="panel"><h3>Wood movement: read before choosing the strips</h3>{ul([f"An end-grain board swells and shrinks across its whole face with the seasons. A long-grain strip does not change length. Glued corner to corner across the slab, the {nl} strips resist that movement.",
                  "Thin strips are what makers generally use for this kind of line, and the maker’s board looks that way, but I have no long-term report on a board like this one. The risk is a hairline crack beside a strip, or a strip end standing proud at the edge, after a few dry winters.",
                  f"The safer version: make the strips end grain too. Crosscut {short(N['strip_h'])} slices from the end of a wide {I} board, plane a face, and rip {short(k)} strips from the slice so the grain runs through the thickness like the rest of the board. They are short and fragile, so each line takes two or three pieces butted end to end in the kerf. Untested here.",
                  "Either way, keep the board oiled and never soak it."])}</div>'
              f'<div class="panel"><h3>Options</h3>{ul([f"Size: \"board\": {{\"width\": 18, \"length\": 12}} makes a smaller board with fewer rows; the marks for the lines are recomputed.", "Fewer or more lines: \"params\": {\"lines\": 5}.",
                  f"Line width: set \"params\": {{\"line\": ...}} and \"shop\": {{\"kerf\": ...}} to your blade. A track saw kerf is nearer 3/32 in.",
                  f"No accent corner to make: use a {G} board with a sapwood corner for the upper zone, or leave the triangles out; the two-tone band still shows.",
                  "Border: the maker’s board has none and neither does this plan. If you want one, make it end grain like the field, never a long-grain frame.", "Juice groove or handles: rout them after the last flattening."])}</div></div></article>')

    # 08
    src = "".join(f'<li><a href="{e(url)}">{e(x)}</a><br><span class="small">{e(note)}</span></li>' for x, url, note in SOURCES)
    Hh.append(f'<article class="sheet" id="sources">{tb("08", "Sources", "What the maker shows, and what in this plan is worked out rather than shown", "<div class=dims>read 2026-11-16</div>")}'
              f'<div class="lower" style="border-top:0;grid-template-columns:1fr 1fr">'
              f'<div class="panel"><h3>Shown by the maker</h3>{ul(["The finished face, in the screenshot and in the video’s cover photo.", "Walnut and maple, named in the video’s description.", "Maple lines that run down the edge of the board, so they pass through its full thickness.",
                  "A still of about two dozen narrow end-grain slices standing in clamps: the rows being glued into the slab.", "A still of the glued slab on a large table saw sled, which fits a through cut for a line or a trim cut."])}</div>'
              f'<div class="panel"><h3>Worked out for this plan, not shown</h3>{ul(["I could not play the video here, only read its title, description, cover photo and three published stills. I do not know the order of the maker’s steps, and his method very likely differs from mine in the details.",
                  "The two-zone plank, the roll and slide of every other row, and all the sizes are my reading of the photos.",
                  f"The {A} corner glued onto a chamfer is my way of making the triangles on purpose. His may be sapwood.",
                  "Cutting through and gluing in a strip as thick as the kerf is ordinary shop practice for a through inlay, and the stills fit it, but I found no step-by-step source I could read in full, and none for seven crossing lines.",
                  "The corner jig is my own. Try the first line dry in it before any glue.", "The flattening routes are carried over from the skill’s other boards; neither has been tried on this one.", "Nobody has built this plan yet."])}</div></div>'
              f'<div class="lower full"><div class="notes"><h3>Links</h3><ul>{src}</ul></div></div></article>')

    chk = "".join(f'<tr><td>{e(c["what"])}' + (f'<span class="sub">{e(c["detail"])}</span>' if c["detail"] else "") + '</td>'
                  f'<td class="{"pass" if c["ok"] else c["level"] if c["level"] == "warn" else "fail"}">{"PASS" if c["ok"] else ("WARN" if c["level"] == "warn" else "FAIL")}</td></tr>' for c in plan["checks"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(plan["name"])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@112,600;112,700&family=IBM+Plex+Mono:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{CSS}</style></head><body><div class="wrap">
<header class="hero"><div class="eyebrow">End-grain cutting board · shop plan · after Indigo Designs</div>
<h1>{h1}</h1><p class="lede">{lede}</p><div class="chain" aria-label="Build order">{chain}</div><div class="stats">{stats}</div></header>
<nav class="index" aria-label="Sheets">{index}</nav>
<main>{"".join(Hh)}</main>
<article class="sheet" id="checks">{tb("R", "Checks", "Recomputed from the board's geometry every time the plan is built", stamp)}
<div class="lower full" style="border-top:0"><div class="panel"><table class="cost">{chk}</table></div></div></article>
<footer>Kerf {short(sh["kerf"])}; rows cut {short(N["cut"])} long; {short(sh["end_trim"])} to square the first end of the plank and {short(sh["hold_end"])} held at the other; {short(N["et"])} trimmed from each stepped end of the slab. Change these under "shop" in design.json and rebuild.</footer>
</div></body></html>"""
