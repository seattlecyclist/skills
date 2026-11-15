#!/usr/bin/env python3
"""Star lattice (after Stammherz's "Out of This World" board): a plank build with one log and two planks.

A dark ground, thin strips of a second wood drawn as a lattice of six-sided cells, and a small diamond of
a third wood wherever four strips meet. The whole face is one square tile: a strip crossing a dark square
on a lean, from near one corner to near the opposite one. Stood upright the strip is steep; given a
quarter turn it is shallow. Rows of upright tiles alternate with rows of quarter-turned ones.

  three-ply blank (dark, strip wood, dark; face glued)  ->  slabs ripped off it with the blade tilted
  ->  slabs planed and ripped square: each one is a long square log with the strip leaning through it
  ->  plank A: logs side by side, upright, every other one end for end (a steep zigzag in the end view)
      plank B: the same logs on their sides, every other one end for end (a shallow zigzag)
  ->  V-grooves routed along the glue lines where the zigzags turn, a square stick of the star wood glued
      into each and planed flush (the diamonds)
  ->  both planks crosscut into rows  ->  rows glued A, B, A, B, none of them turned.

cbplan.py hands a design with "pattern": "starlattice" to build() here; the outputs are the usual files.
"""
import base64, html, json, math, os, sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import species as SP
from twoply import frac, short, fine, _up, nominal, _arrow, _chip, GLUE, ORANGE, RED, MDF, MDF_E

SHOP = {"kerf": 0.125, "flatten_allowance": 0.125, "end_trim": 0.5, "hold_end": 2.0, "spare_rows": 0, "slab_over": 1 / 16,
        "ply_margin": 0.04, "blank_width": 9.25, "blank_bearing": 1.5, "max_depth_90": 3.0, "planer_width": 12.5,
        "edge_clean": 1 / 32, "scrap": 0.75, "max_stick": 36.0, "vbit": 0.75}
ROLES = ("ground", "line", "star")
DEFAULT_SPECIES = {"ground": "wenge", "line": "purpleheart", "star": "padauk"}
VIDEO = "https://www.youtube.com/watch?v=vvD7LmchpLc"
SHORT = "https://www.youtube.com/shorts/GhvvXjdo7i4"
SOURCES = [
    ("Stammherz, “The Most Unusual Pattern Yet” (YouTube short)", SHORT,
     "The short in the screenshot. Its published stills show dark bars with thin pale strips between them being clamped side by side, and the finished board."),
    ("Stammherz, “I Built an Out of This World Cutting Board” (the full build video, 14 minutes)", VIDEO,
     "The cover photo is the finished board, sharp enough to read the pattern from. Its other published stills show a thick wenge beam being ripped into bars on the table saw, and a row of about eight dark blocks, each with a leaning purple strip and small pale pieces where the strips meet, being glued up in a clamping jig."),
    ("Stammherz shop and plans", "https://www.stammherz.de/diy-shop/", "The maker sells plans for some boards. Check there for his own plan of this one before building from mine."),
    ("Andrei Muntian (MTM Wood), Making a 3D End Grain Cutting Board #1 and #3", "https://www.instructables.com/Making-a-3D-end-grain-cutting-board-1/",
     "The family of method used here, shown step by step: laminate a blank, saw it into strips at an angle, plane, re-glue, crosscut the plank into rows."),
    ("Bob Chambers, Building an Optical Illusion End Grain Cutting Board (after MTM Wood)", "https://www.brwoodworkers.com/optical-illusion-end-grain-cutting-board/",
     "A second builder following the laminate, re-saw, re-glue, crosscut sequence, with the planing between glue-ups."),
    ("George Vondriska (WWGOA), Running an End Grain Cutting Board Through a Planer", "https://wwgoa.com/video/running-end-grain-cutting-board-planer",
     "The source for the planer route on sheet 07."),
    ("Marc Spagnuolo, Why Did My Cutting Board Split?", "https://thewoodwhisperer.com/videos/why-did-my-cutting-board-split/",
     "Why an optional border must be end grain like the field, never a long-grain frame."),
]


# ------------------------------------------------------------------------------------- the face
def _clip(p, a, b, c):
    """The part of convex polygon p where a*x + b*y <= c."""
    out = []
    for i in range(len(p)):
        P, Q = p[i - 1], p[i]; dp, dq = a * P[0] + b * P[1] - c, a * Q[0] + b * Q[1] - c
        if dp <= 1e-12:
            if not out or out[-1] != P: out.append(P)
        if (dp < -1e-12 and dq > 1e-12) or (dp > 1e-12 and dq < -1e-12):
            k = dp / (dp - dq); out.append((P[0] + k * (Q[0] - P[0]), P[1] + k * (Q[1] - P[1])))
    res = []
    for v in out:
        if not res or math.hypot(v[0] - res[-1][0], v[1] - res[-1][1]) > 1e-9: res.append(v)
    if len(res) > 1 and math.hypot(res[0][0] - res[-1][0], res[0][1] - res[-1][1]) < 1e-9: res.pop()
    return res if len(res) >= 3 else []


def tile(s, t, deg, c, stars=True):
    """The upright tile as the log's end, y up: the strip rises from near the bottom left corner to near the top right.
    Returns [(role, tag, pts)]; tag tells the two ground bars and the two star corners apart."""
    th = math.radians(deg); ct, st = math.cos(th), math.sin(th)
    sq = [(0, 0), (s, 0), (s, s), (0, s)]
    body = _clip(_clip(sq, -1, -1, -c), 1, 1, 2 * s - c) if stars else sq
    d0 = ct * s / 2 - st * s / 2                               # ct*x - st*y = d0 on the strip's centre line
    out = [("ground", "left", _clip(body, ct, -st, d0 - t / 2)),
           ("line", "strip", _clip(_clip(body, -ct, st, -(d0 - t / 2)), ct, -st, d0 + t / 2)),
           ("ground", "right", _clip(body, -ct, st, -(d0 + t / 2)))]
    if stars:
        out += [("star", "low", _clip(sq, 1, 1, c)), ("star", "high", _clip(sq, -1, -1, -(2 * s - c)))]
    return [(r, g, p) for r, g, p in out if p]


def placed(kind, i, s, t, deg, c, stars=True):
    """Tile i of a row. kind 'A': upright, 'B': on its side. Odd tiles are the same log end for end (a mirror image)."""
    out = []
    for r, g, p in tile(s, t, deg, c, stars):
        q = p if kind == "A" else [(s - y, x) for x, y in p]
        if i % 2: q = [(s - x, y) for x, y in q][::-1]
        out.append((r, g, [(x + i * s, y) for x, y in q]))
    return out


def row_kind(j, rows):
    return "A" if (rows - 1 - j) % 2 == 0 else "B"            # the top row is an A row


def face_polys(cols, rows, s, t, deg, c):
    out = []
    for j in range(rows):
        k = row_kind(j, rows)
        for i in range(cols):
            for r, g, p in placed(k, i, s, t, deg, c):
                out.append({"pts": [(round(x, 6), round(y + j * s, 6)) for x, y in p], "role": r, "slice": f"r{j}", "unit": None, "tile": (i, j), "kind": k})
    return out


def _params(p, board):
    s = float(p.get("tile", 1.5)); t = float(p.get("strip", 0.1875)); deg = float(p.get("lean", 35)); c = float(p.get("star", 0.375))
    cols = int(p.get("cols") or max(2, 2 * round(board["width"] / s / 2)))
    rows = int(p.get("rows") or max(2, 2 * round(board["length"] / s / 2)))
    return s, t, deg, c, cols, rows


def generate(p, board):
    s, t, deg, c, cols, rows = _params(p, board)
    return {"polygons": face_polys(cols, rows, s, t, deg, c), "trim": [0, 0, cols * s, rows * s], "roles": list(ROLES),
            "cells": {"kind": "plank"}, "cols": cols, "rows": rows,
            "notes": [f"{rows} rows of {cols} tiles, each {short(s)} square with one strip {short(t)} wide leaning {deg:g} degrees."]}


# ------------------------------------------------------------------------------------- the plan
def build(design, out, photo=None):
    import cbplan as CB
    shop = dict(SHOP, **design.get("shop", {})); board = design["board"]; T = float(board.get("thickness", 1.5))
    s, t, deg, c, cols, rows = _params(design.get("params", {}), board)
    polys = face_polys(cols, rows, s, t, deg, c)
    th = math.radians(deg); ct, tt = math.cos(th), math.tan(th)
    checks = []
    def check(ok, what, detail="", level="error"):
        checks.append({"ok": bool(ok), "what": what, "detail": detail, "level": level})
    smap = dict(DEFAULT_SPECIES, **design.get("species", {}))
    sp = {r: SP.get(smap[r]) for r in ROLES}
    woods = OrderedDict()
    for r in sp: woods.setdefault(sp[r]["key"], sp[r])
    jk = [w for w in woods.values() if w["janka"] and w["janka"] < 900]
    check(not jk, "Species hard enough for a cutting surface (Janka 900+)", ", ".join(f'{w["name"]} {w["janka"]}' for w in jk))
    tans = [w["tan"] for w in woods.values() if w["tan"]]; spread = max(tans) - min(tans) if tans else 0
    check(spread <= 4.0, "Species move alike (tangential shrinkage within 4 points)", f"{min(tans):.1f}% to {max(tans):.1f}%" if tans else "", "warn")
    if design.get("frame"):
        check(False, "A border is not drawn by this pattern", "Leave \"frame\" out; sheet 07 says how to add an end-grain border by hand.", "warn")

    # the face
    check(all(CB.convex(CB.ccw(p["pts"])) for p in polys), "Every piece of the face is convex")
    trim0 = [0, 0, cols * s, rows * s]
    no, op_, ng, gp = CB.coverage(polys, trim0, max(0.01, t / 5))
    check(no == 0, "Pieces do not overlap", f"overlap near {op_}" if no else "")
    check(ng == 0, "Pieces cover the whole board (no gaps)", f"gap near {gp}" if ng else "")
    xb = s / 2 * (1 - tt); xt = s / 2 * (1 + tt); hw = t / (2 * ct)        # where the strip's centre meets the two faces, and its half width along a face
    check(xb + hw <= c + 1e-9 and xb - hw >= -1e-9, "Both ends of every strip land on a star, so no strip end shows a mismatch",
          f"the strip meets the log's face {frac(max(0, xb - hw), 64)}\" to {frac(xb + hw, 64)}\" from the corner; the star covers {frac(c, 64)}\"")
    check(0 < deg < 45, "The strip leans less than 45 degrees, so the upright and the quarter-turned tile differ", f"{deg:g} degrees")
    # one log makes every tile: the tile is the same after half a turn, an odd tile is its mirror image, a B tile is it on its side
    key = lambda L: sorted((r, tuple(sorted((round(x, 5), round(y, 5)) for x, y in p))) for r, g, p in L)
    base = tile(s, t, deg, c)
    check(key(base) == key([(r, g, [(s - x, s - y) for x, y in p]) for r, g, p in base]), "The tile reads the same after half a turn, so a log has no wrong way up")
    check(cols % 2 == 0, "An even number of tiles in a row, so both edges of the board end on the same kind of seam", f"{cols} tiles")
    check(rows % 2 == 0, "An even number of rows, half from each plank", f"{rows} rows", "warn")
    # stars: every star corner of one row meets star corners of the next row
    def stars_at(j, top):
        y = (j + 1) * s if top else j * s
        return sorted({round(v[0] / s) for p in polys if p["role"] == "star" and p["tile"][1] == j for v in p["pts"] if abs(v[1] - y) < 1e-6 and abs(v[0] / s - round(v[0] / s)) < 1e-6})
    check(all(stars_at(j, True) == stars_at(j + 1, False) for j in range(rows - 1)), "Star halves of neighbouring rows meet seam for seam, with no row turned")

    # plies, blank, slabs
    m = shop["ply_margin"]; over = shop["slab_over"]; kerf = shop["kerf"]
    Td = _up(xt * ct - t / 2 + m, 1 / 16); TB = 2 * Td + t
    K = (Td + t / 2) / ct                                       # along a sawn face, from the strip's centre to the blank's face
    spare_ply = (K - xt) * ct
    check(spare_ply >= 1 / 32 - 1e-6, "Plies thick enough to rip every slab square", f"{spare_ply:.3f}\" spare")
    depth = shop["max_depth_90"] * ct
    check(TB <= depth + 1e-6, f"The blank fits under the blade tilted to {deg:g} degrees",
          f"blank {short(TB)} thick; a 10 in. saw cuts about {short(depth)} at that tilt" + ("" if TB <= depth else ". Use a smaller tile"))
    check(t >= 0.125 - 1e-9, "Strip at least 1/8\" thick", short(t), "warn")
    check(2 * c <= shop["vbit"] + 1e-9, "The groove fits the V bit", f"groove {short(2 * c)} wide, bit {short(shop['vbit'])}")
    check(c <= s / 3, "Stars small enough to leave the ground bars sound", f"{short(c)} of a {short(s)} tile")
    rough = s + over; stepx = (rough + kerf) / ct; first = TB * tt
    Wb = shop["blank_width"]; per_blank = int((Wb - first - shop["blank_bearing"]) // stepx + 1e-9)
    check(per_blank >= 1, "The blank is wide enough to rip a slab from", f"{short(Wb)} wide")
    cut = T + shop["flatten_allowance"]; pitch = cut + kerf
    nA, nB = (rows + 1) // 2, rows // 2
    plank_len = _up((nA + shop["spare_rows"]) * pitch + shop["end_trim"] + shop["hold_end"])
    per_stick = max(1, int((shop["max_stick"] - 0.25 + kerf) // (plank_len + kerf)))
    per_stick = min(per_stick, 3)
    stick_len = _up(per_stick * plank_len + (per_stick - 1) * kerf + 0.25); slab_len = stick_len + 0.25; blank_len = _up(slab_len + 0.5, 0.5)
    nlogs = 2 * cols; nslab = math.ceil(nlogs / per_stick)
    nblank = math.ceil((nslab + 1) / max(1, per_blank)); spare_slabs = nblank * per_blank - nslab
    scrap = shop["scrap"]; plank_w = cols * s + 2 * scrap
    groups = max(1, math.ceil(plank_w / shop["planer_width"] - 1e-9))
    while cols % groups: groups += 1
    per_group = cols // groups
    check(T >= 1.0, "Board at least 1\" thick (end grain under 1\" can split)", f'{T}"')
    ec = shop["edge_clean"]; W = cols * s; Lb = rows * s - 2 * ec
    trim = [0, ec, cols * s, rows * s - ec]
    face = [{"pts": q, "role": p["role"]} for p in polys for q in [CB.clip_rect(p["pts"], trim)] if q]
    check(max(W, Lb) / T <= 18, "Board not too large for its thickness", f"{W:.1f} x {Lb:.1f} x {T}", "warn")

    q = c * math.sqrt(2)                                        # the star stick: square, set corner down in a 90 degree groove
    ngroove = 2 * (cols + 1); nstar = math.ceil(ngroove / per_stick) + 1
    stock = []
    qd = nominal(Td); bf = 2 * nblank * (qd / 4) * (Wb + 0.5) * (blank_len + 1) / 144
    stock.append({"species": sp["ground"]["name"], "key": sp["ground"]["key"], "role": "ground", "rough": f"{qd}/4", "mill_to": Td, "n": 2 * nblank,
                  "size": f'{short(Td)} x {short(Wb)} x {short(blank_len)}', "use": "the two outer plies of each blank", "bf": bf, "bf_buy": math.ceil(bf * 1.25 * 2) / 2})
    nres = math.ceil(nblank / 2); bf = nres * 1.0 * (Wb + 0.5) * (blank_len + 1) / 144
    stock.append({"species": sp["line"]["name"], "key": sp["line"]["key"], "role": "line", "rough": "4/4", "mill_to": t, "n": nblank,
                  "size": f'{short(t)} x {short(Wb)} x {short(blank_len)}', "use": f"the middle ply of each blank; resaw {nres} board{'s' if nres > 1 else ''} in two", "bf": bf, "bf_buy": math.ceil(bf * 1.25 * 2) / 2})
    bf = 1.0 * (nstar * (q + kerf + 0.0625) + 1.0) * (stick_len + 1) / 144
    stock.append({"species": sp["star"]["name"], "key": sp["star"]["key"], "role": "star", "rough": "4/4", "mill_to": q, "n": nstar,
                  "size": f'{fine(q)} x {fine(q)} x {short(stick_len)}', "use": f"star sticks, one length of {short(plank_len)} for each of the {ngroove} grooves", "bf": bf, "bf_buy": math.ceil(bf * 1.25 * 2) / 2})
    yield_ = (nlogs * plank_len * s * s) / (2 * nblank * Td * Wb * blank_len)
    N = {"s": s, "t": t, "deg": deg, "c": c, "cols": cols, "rows": rows, "Td": Td, "TB": TB, "K": K, "xb": xb, "xt": xt, "hw": hw, "rough": rough, "stepx": stepx,
         "first": first, "fenceA": xt + K, "near": xb - hw, "far": s - xb - hw, "strip_face": 2 * hw, "slab_w": TB / ct, "Wb": Wb, "per_blank": per_blank, "nblank": nblank,
         "nslab": nslab, "spare_slabs": spare_slabs, "blank_len": blank_len, "slab_len": slab_len, "stick_len": stick_len, "per_stick": per_stick, "nlogs": nlogs,
         "plank_len": plank_len, "cut": cut, "pitch": pitch, "nA": nA, "nB": nB, "groups": groups, "per_group": per_group, "blade_reach": TB / ct, "q": q,
         "ngroove": ngroove, "nstar": nstar, "scrap": scrap, "plank_w": plank_w, "yield": yield_}
    planks = [{"id": "A", "rows": nA, "logs": cols, "worth": nA > 1, "why": f"Yes: cut {nA} times, rows " + ", ".join(f"R{rows - j}" for j in range(rows - 1, -1, -1) if row_kind(j, rows) == "A"),
               "count": 1, "length": plank_len, "n": cols, "width": cols * s, "rows_cut": nA, "spares": shop["spare_rows"]},
              {"id": "B", "rows": nB, "logs": cols, "worth": nB > 1, "why": f"Yes: cut {nB} times, rows " + ", ".join(f"R{rows - j}" for j in range(rows - 1, -1, -1) if row_kind(j, rows) == "B"),
               "count": 1, "length": plank_len, "n": cols, "width": cols * s, "rows_cut": nB, "spares": shop["spare_rows"]}]
    plan = {"name": design.get("name", "Star Lattice End-Grain Board"), "description": design.get("description", ""), "pattern": "starlattice",
            "board": {"width": W, "length": Lb, "thickness": T, "trim": trim, "field": [W, Lb], "frame": None, "field_trim": trim},
            "shop": shop, "species": sp, "woods": list(woods.values()), "notes": [f"{rows} rows of {cols} tiles"], "options": design.get("options", {}), "face": face,
            "polygons": polys, "stock": stock, "checks": checks, "method": "plank", "N": N, "slice_cut": cut, "n_slices": rows,
            "rows": [{"n": rows - j, "plank": row_kind(j, rows), "turned": False} for j in range(rows)], "bars": [], "bar_types": [], "planks": planks,
            "logs": [{"id": "L", "name": "Log", "what": "square log with one leaning strip", "make": [(stick_len, nslab)], "crosscut": True, "count": nlogs}],
            "info": {"kind": "plank"}}
    plan["steps"] = steps(plan)
    os.makedirs(os.path.join(out, "svg"), exist_ok=True)
    svgs = drawings(plan)
    for name, v in svgs.items(): open(os.path.join(out, "svg", name + ".svg"), "w").write(v)
    CB.write_obj(plan, out); CB.write_spec(plan, design, out)
    summary = (f"Rows repeat every 2 rows as cut; no row is turned. 1 slab shape makes 1 log type; the log upright makes plank A and the same log on its side makes plank B; "
               f"plank A is cut {nA} times and plank B {nB} times for the {rows} rows.")
    plan["repeats"] = {"rows": rows, "bar_shapes": 1, "log_types": 1, "kind": "plank", "planks": 2, "plank_copies": 1, "single_row_planks": sum(1 for p in planks if p["rows"] < 2),
                       "row_period": 2, "turns": [], "orbits": 2, "rows_per_plank": nA, "log_lengths": nslab, "logs_in_planks": nlogs, "widest_plank": round(plank_w, 3),
                       "rows_for_full_repeat": 2, "summary": summary}
    check(all(p["worth"] for p in planks), "Every plank is worth making (each is cut for more than one row)", "; ".join(f"plank {p['id']}: {p['rows']} rows" for p in planks), "warn")
    check(True, "Repeat math", summary)
    try:
        import render_guide
        render_guide.render(plan, os.path.join(out, "guide.png"), **design.get("guide", {}))
    except Exception as e:
        print("guide.png skipped:", e)
    open(os.path.join(out, "plan.html"), "w").write(page(plan, svgs, photo, os.path.join(out, "guide.png")))
    json.dump({k: v for k, v in plan.items() if k != "polygons"}, open(os.path.join(out, "plan.json"), "w"), indent=1, default=str)
    return plan


def _nm(w):
    return w["name"].split()[-1].lower()


# ------------------------------------------------------------------------------------- steps
def steps(plan):
    N = plan["N"]; sp = plan["species"]; T = plan["board"]["thickness"]; sh = plan["shop"]
    G, P, O = _nm(sp["ground"]), _nm(sp["line"]), _nm(sp["star"])
    s, t, deg, c = N["s"], N["t"], N["deg"], N["c"]; W, Lb = plan["board"]["field"]; cols = N["cols"]
    half = N["groups"] > 1
    parts = "two halves" if N["groups"] == 2 else f"{N['groups']} parts"
    return [
        {"title": "Mill the plies", "figs": ["blank"], "text": [
            f"Joint and plane {2 * N['nblank']} {G} boards to {short(N['Td'])} thick and {N['nblank']} {P} boards to {short(t)} thick, all {short(N['Wb'])} wide and {short(N['blank_len'])} long. Plane each wood in one session at one setting.",
            f"The {P} thickness is the width of every line in the pattern, so it is the one that shows: measure it with calipers, within 0.005\" board to board. The {G} only has to be at least {short(N['Td'])}.",
            f"For the {P}, resaw a 4/4 board in two on the bandsaw and plane both halves to {short(t)} on a flat carrier board. No {short(N['Wb'])} boards? Edge-glue narrower ones first; a seam inside a ply shows only as an ordinary glue line in one wood."]},
        {"title": "Glue the three-ply blanks", "glue": True, "figs": ["asm_blank"], "text": [
            f"Glue {G}, {P}, {G} face to face: {N['nblank']} blanks, each {short(N['TB'])} thick. Roll glue on both faces of the {P}, rub the boards together, and clamp between flat cauls with a clamp every 4 to 5 inches. Thin {P} cups as soon as it is wet, so have the clamps set before the glue goes on.",
            "Next day scrape the squeeze-out, joint one edge of each blank square to its faces and rip the other edge parallel. The jointed edge rides the fence in the next step."]},
        {"title": f"Rip the slabs with the blade at {deg:g} degrees", "figs": ["rip"], "text": [
            f"Tilt the blade to {deg:g} degrees from upright with a digital gauge, leaning away from the fence, and raise it to cut through the {short(N['TB'])} blank (the blade is in {N['blade_reach']:.2f}\" of wood, close to the limit of a 10 in. saw: use a sharp rip blade and feed steadily). Riving knife on, featherboard ahead of the blade, push blocks.",
            "The blank lies flat on the table with its jointed edge against the fence for every cut. The slab is the piece that comes off on the far side of the blade.",
            "First cut: set the fence so the blade just takes the top corner off the far edge. That waste is a triangle.",
            f"Then move the fence {fine(N['stepx'])} toward the blade for each slab. Each slab comes off about {short(N['rough'])} thick, with the {P} crossing it on a lean. Check the first with calipers and adjust the move.",
            f"Take {N['per_blank']} slabs from each blank and stop: the last {short(sh['blank_bearing'])} of the blank is what holds it flat. {N['nblank'] * N['per_blank']} slabs in all; {N['nslab']} are needed and {N['spare_slabs']} {'is' if N['spare_slabs'] == 1 else 'are'} for setting up step 5."],
         "dont": "rip the last slab from a blank that no longer sits flat with its edge on the fence."},
        {"title": "Plane the slabs", "figs": [], "text": [
            f"A slab lies flat on either sawn face, so it goes through the planer like any board. Plane every slab to exactly {short(s)}, taking the same from each face, all at the last setting in one session.",
            f"That {short(s)} is one side of the square log. The next step rips the other two sides to the same size."]},
        {"title": "Rip each slab square, twice", "figs": ["slab"], "text": [
            f"Blade back to 90 degrees. Each slab has two sloping edges, which are the old faces of the blank. Both come off square, at the right distance from the {P}.",
            f"Cut A. Lay the slab so that one of its two sharp corners is down on the table and against the fence, and set the fence {fine(N['fenceA'])} from the blade. The sloping edge on the far side of the blade falls away. Test on a spare slab and measure the {G} between the new square edge and the {P}: {fine(N['near'])} on the face that was up, {fine(N['far'])} on the face that was down. Nudge the fence until both are right, then run every slab.",
            f"Cut B. Turn the slab so the new square edge is against the fence and rip it to {short(s)} wide, or to the planed thickness if that measured a hair different. The log must come out square.",
            f"After both cuts every stick is {short(s)} square and reads the same from either face: {fine(N['near'])} of {G}, {fine(N['strip_face'])} of {P}, {fine(N['far'])} of {G}."]},
        {"title": "Cut the sticks into logs", "figs": [], "text": [
            f"Check each stick with calipers: as wide as it is tall within 0.005\". Half of the logs are used on their sides, so a stick that is not square makes a plank with steps in it.",
            f"Crosscut each stick into {N['per_stick']} logs of {short(N['plank_len'])}: {N['nlogs']} logs, {cols} for each plank." + (f" The spare stick{'s give' if N['spare_slabs'] > 1 else ' gives'} {N['spare_slabs'] * N['per_stick']} more." if N['spare_slabs'] else ""),
            f"Mill two scrap strips for each plank, any wood, {short(N['scrap'])} wide, {short(s)} thick and {short(N['plank_len'])} long. They go on the outside edges of the planks so the two edge grooves can be routed and filled like all the others."]},
        {"title": "Glue plank A: logs upright", "glue": True, "figs": ["plankA"], "text": [
            f"Stand {cols} logs so the {P} rises steeply, and turn every other log end for end so the {P} makes a zigzag across the end of the plank: {cols // 2} V shapes. A scrap strip goes on each outside edge.",
            f"Look at the end against the drawing before any glue. In plank A the strips come to {short(N['near'] * 2)} of each other at the turns of the zigzag.",
            (f"Glue in {parts}, {N['per_group']} logs and one scrap strip each, on flat cauls with cauls above, so each part fits a {sh['planer_width']:g}\" planer. Plane both faces of each part with the lightest pass that cleans them, both parts at the same setting. Then glue the parts edge to edge, faces flush."
             if half else "Glue all the logs on flat cauls with cauls above, and plane both faces with the lightest pass that cleans them."),
            "Keep the ends of the logs flush against a stop so no length is lost."]},
        {"title": "Glue plank B: the same logs on their sides", "glue": True, "figs": ["plankB"], "text": [
            f"Lay the other {cols} logs with a quarter turn, so the {P} runs at a shallow slope, and again turn every other log end for end. The zigzag is now low and wide, and its peaks and valleys stop {fine(N['xb'])} short of the faces.",
            f"Same glue-up as plank A, with a scrap strip on each outside edge" + (f", in {parts}, planed to the same thickness as plank A." if half else ", planed to the same thickness as plank A."),
            "Both planks must end up the same width, log seam for log seam. Lay one on the other and check before the glue sets on the second."]},
        {"title": "Rout the V-grooves", "figs": ["groove"], "text": [
            f"A 90 degree V-groove bit, {short(sh['vbit'])} or wider, in the router table, set {short(c)} high: the groove is {short(2 * c)} wide at the face and {short(c)} deep. Take it in two passes.",
            "The grooves run the length of the plank, each one centred on a glue line. In both planks they go on every other glue line on one face, and on the glue lines between those on the other face. The scrap seams count as glue lines.",
            f"Plank A: groove the glue lines where two strips come together at that face. The groove takes away the ends of both strips. Plank B: groove the glue lines where the zigzag comes nearest that face; the groove just reaches its peak.",
            f"That makes {cols // 2 + 1} grooves on one face and {cols // 2} on the other, {cols + 1} per plank. Mark every groove line with a pencil cross on the plank's end first, against the drawings on sheet 05, and stack the planks as they will meet in the board to see that the marks line up.",
            "Run the plank flat on the table with a featherboard holding it to the fence, and set the fence from the glue line itself each time, not from a measurement: the point of the bit follows the glue line."],
         "dont": "groove the same glue line on both faces. Every glue line gets one groove, on one face."},
        {"title": "Glue in the star sticks", "glue": True, "figs": ["asm_inlay"], "text": [
            f"Mill {N['nstar']} {O} sticks {fine(N['q'])} square and {short(N['stick_len'])} long, and cut them to {short(N['plank_len'])}: {N['ngroove']} pieces. Plane them to fit the groove, not to the number: a stick set corner down should fill the groove with its two upper corners level with the face.",
            f"Wipe {O} with acetone just before glue if it feels oily. Glue a stick corner down in every groove on one face, with half of it standing proud. Clamp through a caul that has the same V-groove routed in it, so the pressure goes straight down on the corner. Do one face, let it cure, then the other.",
            "Saw or plane the proud half off: at the planer, 1/32 in. a pass until the sticks are flush, then one cleaning pass. Both planks to the same final thickness.",
            f"Rip the scrap strips off both edges, splitting the edge sticks down the middle of the glue line. Each plank is now {short(cols * s)} wide and shows half a diamond at each edge groove."]},
        {"title": "Crosscut both planks into rows", "figs": ["asm_cut"], "text": [
            f"On the crosscut sled with a stop block, square one end of each plank, then cut {N['nA']} slices {short(N['cut'])} thick from plank A and {N['nB']} from plank B. Each slice is one whole row of the board.",
            f"Hold the plank down and against the sled fence for every cut. The {short(sh['hold_end'])} left at the end is what your hand holds; it is also the spare row if one slice goes wrong, cut last with the plank clamped to the sled.",
            "Pencil an arrow on the same edge of every slice and letter them A or B."]},
        {"title": "Lay out and glue the board", "glue": True, "figs": ["rows"], "text": [
            "Stand the slices on edge, end grain up, all with the same cut face up and every arrow pointing the same way. Alternate them A, B, A, B. No slice is turned or flipped.",
            f"Check each seam between rows: every half diamond on one slice meets a half diamond on the next, and every {P} strip that reaches a seam ends on a diamond. If the diamonds of two slices are a whole log apart, one of them is the wrong way round.",
            "Glue the rows with their ends flush against a stop, on taped cauls, clamps across the rows every 4 inches and cauls above to keep them level. These are long-grain faces: one coat of glue, normal pressure."]},
        {"title": "Flatten", "figs": [], "see": ["finish"], "text": [
            "Router sled first, then the random-orbit sander: 80 grit to remove the router marks, then 120, 180, 220. Raise the grain with a damp cloth before the last grit.",
            "A drum sander does the same job if you have one. For the helical planer, read sheet 07 before trying it."]},
        {"title": "Trim, ease the edges, finish", "figs": [], "text": [
            f"Take {fine(sh['edge_clean'])} off the two long edges on the table saw, just enough to clean them. The two short edges are the ends of the rows: if they are not dead flush, take the least you can off both on the crosscut sled with a backer, the same from each so the half diamonds stay equal. Finished size {short(W)} x {short(Lb)} x {short(T)}.",
            f"{plan['options'].get('edge', '1/8 in. round-over')} on every edge. Flood with mineral oil until it stops soaking in, then board butter." + (" Add four rubber feet." if plan["options"].get("feet", True) else "")]},
    ]


# ------------------------------------------------------------------------------------- drawings
def drawings(plan):
    import cbplan as CB
    from assembly import Scene
    N = plan["N"]; sp = plan["species"]; s, t, deg, c = N["s"], N["t"], N["deg"], N["c"]; cols, rows = N["cols"], N["rows"]
    th = math.radians(deg); tt = math.tan(th)
    col = lambda r: sp[r]["end"]; lng = lambda r: sp[r]["long"]
    G, P, O = _nm(sp["ground"]), _nm(sp["line"]), _nm(sp["star"])
    out = OrderedDict(); tr = plan["board"]["trim"]
    INK = "#1e2327"; EDGE = "#8a7f72"

    # face
    S = CB.Svg(tr, 640 / (tr[2] - tr[0]), pad=46, title="Top face")
    for f in plan["face"]: S.poly(f["pts"], fill=col(f["role"]), stroke=col(f["role"]), sw=0.4)
    S.poly([(tr[0], tr[1]), (tr[2], tr[1]), (tr[2], tr[3]), (tr[0], tr[3])], stroke=INK, sw=1.6)
    S.dimx(tr[0], tr[2], tr[1], short(tr[2] - tr[0])); S.dimy(tr[1], tr[3], tr[0], short(tr[3] - tr[1]))
    out["face"] = S.svg()

    # tile: the log's end, and the four ways it sits round one star
    S = CB.Svg([-0.25 * s, -0.3 * s, 3.3 * s, 1.25 * s], 150 / s * 1.25, pad=34, title="The tile")
    for r, g, p in tile(s, t, deg, c): S.poly(p, fill=col(r), stroke=EDGE, sw=0.6)
    S.poly([(0, 0), (s, 0), (s, s), (0, s)], stroke=INK, sw=1.6)
    S.dimx(0, s, 0, short(s)); S.dimy(0, s, 0, short(s))
    S.text((s / 2, s + 0.13 * s), "one tile = the end of a log", 11.5, weight="bold")
    ox = 1.85 * s; h = 0.5
    for j, k in ((1, "A"), (0, "B")):
        for i in range(2):
            for r, g, p in placed(k, i + 1, s, t, deg, c):
                S.poly([(ox + (x - s) * h, (y + j * s) * h) for x, y in p], fill=col(r), stroke=EDGE, sw=0.4)
            S.poly([(ox + i * s * h, j * s * h), (ox + (i + 1) * s * h, j * s * h), (ox + (i + 1) * s * h, (j + 1) * s * h), (ox + i * s * h, (j + 1) * s * h)], stroke=INK, sw=1.1)
        S.text((ox + 2 * s * h + 0.06 * s, (j + .5) * s * h), "upright (plank A)" if k == "A" else "on its side (plank B)", 10.5, anchor="start")
    S.text((ox + s * h, s + 0.13 * s), "four tiles round one star", 11.5, weight="bold")
    out["tile"] = S.svg()

    # blank, end view
    Wb, TB, Td = N["Wb"], N["TB"], N["Td"]
    S = CB.Svg([-0.6, -0.5, Wb + 0.6, TB + 0.6], 62, pad=40, title="Three-ply blank, end view")
    S.poly([(0, 0), (Wb, 0), (Wb, Td), (0, Td)], fill=col("ground"), stroke=INK, sw=1)
    S.poly([(0, Td), (Wb, Td), (Wb, Td + t), (0, Td + t)], fill=col("line"), stroke=INK, sw=1)
    S.poly([(0, Td + t), (Wb, Td + t), (Wb, TB), (0, TB)], fill=col("ground"), stroke=INK, sw=1)
    for y in (Td, Td + t): S.line((0, y), (Wb, y), stroke=GLUE, sw=1.8)
    S.dimx(0, Wb, 0, short(Wb)); S.dimy(0, Td, 0, f"{G} {short(Td)}"); S.dimy(Td + t, TB, 0, f"{G} {short(Td)}"); S.dimy(Td, Td + t, Wb, f"{P} {short(t)}", left=False)
    S.text((Wb / 2, TB + 0.3), f"three-ply blank, {short(TB)} thick, {short(N['blank_len'])} long: make {N['nblank']}", 11.5, weight="bold")
    out["blank"] = S.svg()

    # the tilted rip: seen from the infeed end, fence on the right, blade leaning left
    S = CB.Svg([-1.4, -0.9, Wb + 1.6, TB + 1.5], 62, pad=40, title=f"Ripping slabs, blade at {deg:g} degrees")
    S.poly([(-1.4, -0.35), (Wb + 1.6, -0.35), (Wb + 1.6, 0), (-1.4, 0)], fill="#c9ccd0", stroke="#5b6167", sw=0.8)
    S.poly([(Wb, 0), (Wb + 1.1, 0), (Wb + 1.1, 2.6), (Wb, 2.6)], fill=MDF, stroke=MDF_E, sw=1); S.text((Wb + 0.55, 1.3), "fence", 10.5, rot=-90)
    kx = plan["shop"]["kerf"] / math.cos(th)
    x0 = N["first"]; xs = [x0 + k * N["stepx"] for k in range(N["per_blank"] + 1)]
    lay = (("ground", 0, Td), ("line", Td, Td + t), ("ground", Td + t, TB))
    def quad(xa, xb_, y0, y1):       # between two leaning planes through (x, 0), and between two heights
        return [(max(0, xa - y0 * tt), y0), (xb_ - y0 * tt, y0), (xb_ - y1 * tt, y1), (max(0, xa - y1 * tt), y1)]
    for r, y0, y1 in lay:
        S.poly(quad(-99, x0 - kx, y0, y1), fill=col(r), stroke=EDGE, sw=0.6, op=0.35)
    for k in range(1, N["per_blank"] + 1):
        xa, xb_ = xs[k - 1], xs[k] - kx
        for r, y0, y1 in lay: S.poly(quad(xa, xb_, y0, y1), fill=col(r), stroke=INK, sw=0.9)
        _chip(S, ((xa + xb_) / 2 - TB * tt * 0.22, TB * 0.22), str(k))
    xa = xs[-1]
    for r, y0, y1 in lay: S.poly([(xa - y0 * tt, y0), (Wb, y0), (Wb, y1), (xa - y1 * tt, y1)], fill=col(r), stroke=INK, sw=0.9)
    S.text(((xa + Wb) / 2, Td / 2), "left over", 10.5, fill="#fff")
    bx = xs[1]; up = TB + 0.55
    S.poly([(bx + 0.35 * tt, -0.35), (bx - kx + 0.35 * tt, -0.35), (bx - kx - up * tt, up), (bx - up * tt, up)], fill="#8f969c", stroke="#444", sw=0.8, op=0.85)
    S.text((bx - up * tt - 0.2, TB + 0.9), f"blade at {deg:g}°, leaning away from the fence", 11, anchor="middle")
    S.text((0.42, 0.3), "waste", 10.5, fill="#fff")
    S.dimx(xs[-2], xs[-1], 0, f"fence moves {frac(N['stepx'], 32)}\" per slab")
    S.text((Wb / 2, -0.75), f"blank flat on the table, jointed edge on the fence; slabs come off the far side, {N['per_blank']} per blank", 11)
    out["rip"] = S.svg()

    # squaring a slab: lying on one sawn face
    K, xb, xt, hw = N["K"], N["xb"], N["xt"], N["hw"]
    S = CB.Svg([xb - K - 0.4, -1.0, xt + K + 0.5, s + 1.0], 120, pad=40, title="Squaring a slab")
    at = lambda x, y: (x + y * tt, y)
    S.poly([at(xb - K, 0), at(xb - hw, 0), at(xb - hw, s), at(xb - K, s)], fill=col("ground"), stroke=INK, sw=1)
    S.poly([at(xb - hw, 0), at(xb + hw, 0), at(xb + hw, s), at(xb - hw, s)], fill=col("line"), stroke=INK, sw=1)
    S.poly([at(xb + hw, 0), at(xb + K, 0), at(xb + K, s), at(xb + hw, s)], fill=col("ground"), stroke=INK, sw=1)
    S.poly([at(xb - K, 0), (0, 0), (0, s), at(xb - K, s)], fill="#fff", stroke="none", op=0.6)
    S.poly([(s, 0), at(xb + K, 0), at(xb + K, s), (s, s)], fill="#fff", stroke="none", op=0.6)
    for x, lab in ((0, "cut A"), (s, "cut B")):
        S.line((x, -0.25), (x, s + 0.25), stroke=RED, sw=1.8, dash="6 3"); S.text((x, s + 0.4), lab, 11.5, fill=RED, weight="bold")
    S.dimx(0, xb - hw, 0, f"{frac(N['near'], 64)}\""); S.dimx(xb + hw, s, 0, f"{G} {frac(N['far'], 64)}\"")
    S.dimx(0, xt - hw, s, f"{G} {frac(N['far'], 64)}\"", below=False); S.dimx(xt + hw, s, s, f"{frac(N['near'], 64)}\"", below=False)
    S.dimy(0, s, xb - K, short(s))
    _chip(S, at(xb + K, s), "F")
    S.text((s / 2, -0.62), f"the finished log is {short(s)} square; the pale ends are the sloping edges that come off", 11.5, weight="bold")
    S.text((s / 2, -0.84), f"cut A: roll the slab over so sharp corner F is down against the fence, fence {frac(N['fenceA'], 64)}\" ({N['fenceA']:.3f}) from the blade", 10.5)
    out["slab"] = S.svg()

    # planks, end view, after the stars are in; scrap strips dashed
    def plank_svg(kind):
        sc = N["scrap"]; Wd = cols * s
        S = CB.Svg([-sc - 0.3, -1.25, Wd + sc + 0.3, s + 1.9], 900 / (Wd + 2 * sc), pad=34, title=f"Plank {kind}, end view")
        for i in range(cols):
            for r, g, p in placed(kind, i, s, t, deg, c): S.poly(p, fill=col(r), stroke=EDGE, sw=0.5)
        for x0_, x1_, top_edge in ((-sc, 0, None), (Wd, Wd + sc, None)):
            S.poly([(x0_, 0), (x1_, 0), (x1_, s), (x0_, s)], fill="#efe9dc", stroke="#8d8676", sw=1, dash="5 3")
        # the half of each edge star that lies in the scrap
        low_even = kind == "A"                                   # plank A: stars on the bottom face at even seams; plank B: on the top face
        for xe, sgn in ((0, -1), (Wd, 1)):
            y0 = 0 if low_even else s; dy = c if low_even else -c
            S.poly([(xe, y0), (xe + sgn * c, y0), (xe, y0 + dy)], fill=col("star"), stroke=EDGE, sw=0.5, op=0.55)
        for i in range(0, cols + 1): S.line((s * i, 0), (s * i, s), stroke=GLUE, sw=1.6)
        S.poly([(0, 0), (Wd, 0), (Wd, s), (0, s)], stroke=INK, sw=1.3)
        for i in range(cols + 1):
            bottom = (i % 2 == 0) == low_even
            x, y = S.P(s * i, 0 if bottom else s)
            S.raw(f'<path d="M{x:.1f},{y + (16 if bottom else -16):.1f} l-5,{9 if bottom else -9} l10,0 z" fill="{RED}"/>')
        for i in range(cols): S.text((s * (i + .5), s + 0.85), "as cut" if i % 2 == 0 else "turned", 10.5)
        S.text((-sc / 2, s / 2), "scrap", 9.5, rot=-90); S.text((Wd + sc / 2, s / 2), "scrap", 9.5, rot=-90)
        S.dimx(0, Wd, 0, short(Wd)); S.dimy(0, s, -sc, short(s))
        S.text((Wd / 2, s + 1.45), f"plank {kind}: {cols} logs {'upright' if kind == 'A' else 'on their sides'}, every other one turned end for end · red marks: the {cols + 1} grooves", 12, weight="bold")
        if N["groups"] > 1:
            for gk in range(1, N["groups"]): S.line((gk * N["per_group"] * s, -0.12), (gk * N["per_group"] * s, s + 0.12), stroke=GLUE, sw=3.2)
        return S.svg()
    out["plankA"] = plank_svg("A"); out["plankB"] = plank_svg("B")

    # groove and stick, close up at one seam of plank A (two strips meeting at the bottom face, drawn with that face up)
    S = CB.Svg([-1.25 * s, -0.8, 1.25 * s, s * 0.62 + 0.75], 170, pad=36, title="Groove and star stick")
    flip = lambda p: [(x, s * 0.62 - y) for x, y in p]
    win = lambda p: _clip(_clip(_clip(p, 0, 1, s * 0.62), 1, 0, 1.2 * s), -1, 0, 1.2 * s)
    for i, sh_ in ((1, -2 * s), (2, -2 * s)):
        for r, g, p in placed("A", i, s, t, deg, c, stars=False):
            q = win([(x + sh_, y) for x, y in p])
            if q: S.poly(flip(q), fill=col(r), stroke=EDGE, sw=0.6)
    S.line((0, s * 0.62), (0, 0), stroke=GLUE, sw=1.6)
    yt = s * 0.62
    S.poly([(-c, yt), (0, yt - c), (c, yt), (0, yt + c)], fill=col("star"), stroke=INK, sw=1.2)
    S.poly([(-c, yt), (0, yt + c), (c, yt)], fill="#fff", stroke="none", op=0.5)
    S.line((-1.2 * s, yt), (1.2 * s, yt), stroke=INK, sw=1.2)
    S.line((-c, yt), (0, yt - c), stroke=INK, sw=1.4); S.line((0, yt - c), (c, yt), stroke=INK, sw=1.4)
    S.dimx(-c, c, yt + c, f"groove {short(2 * c)} wide", below=False)
    S.dimy(yt - c, yt, -1.2 * s, f"{short(c)} deep")
    S.text((c + 0.15, yt + c * 0.5), "proud half: planed off", 11.5, anchor="start")
    S.text((0, -0.56), f"{O} stick {frac(N['q'], 64)}\" square, set corner down", 11.5)
    S.text((0, -0.3), "the groove is centred on the glue line and takes the ends of both strips", 11.5, weight="bold")
    out["groove"] = S.svg()

    # rows
    S = CB.Svg([tr[0] - 1.4, tr[1], tr[2] + 2.3, tr[3]], 560 / (tr[2] - tr[0]), pad=40, title="Rows")
    for f in plan["face"]: S.poly(f["pts"], fill=col(f["role"]), stroke=col(f["role"]), sw=0.3)
    for j in range(1, rows): S.line((0, j * s), (cols * s, j * s), stroke=GLUE, sw=2.2)
    S.poly([(tr[0], tr[1]), (tr[2], tr[1]), (tr[2], tr[3]), (tr[0], tr[3])], stroke=INK, sw=1.4)
    for j in range(rows):
        k = row_kind(j, rows)
        S.text((-0.25, (j + .5) * s), f"R{rows - j}", 12, anchor="end", weight="bold", fill="#6b4630")
        S.text((cols * s + 0.25, (j + .5) * s), f"plank {k}, as cut", 10.5, anchor="start")
        ax, ay = S.P(s * 0.5, (j + .5) * s)
        S.raw(f'<path d="M{ax - 12:.1f},{ay:.1f} l24,0 m-8,-6 l8,6 l-8,6" fill="none" stroke="#fff" stroke-width="4"/>'
              f'<path d="M{ax - 12:.1f},{ay:.1f} l24,0 m-8,-6 l8,6 l-8,6" fill="none" stroke="{RED}" stroke-width="2"/>')
    ax, ay = S.P(cols * s / 2, tr[3]); _arrow(S, (ax, ay - 60), (ax, ay - 6))
    ax, ay = S.P(cols * s / 2, tr[1]); _arrow(S, (ax, ay + 60), (ax, ay + 6))
    out["rows"] = S.svg()

    # ------------------------------------------------------------------ 3D
    along = lambda ox=0.0, oy=0.0, oz=0.0: (lambda a, b, w: (ox + w, oy + a, oz + b))
    sc = Scene(az=40, el=28); Lg = 9.0; gap = 0.8
    sc.prism([(0, 0), (Wb, 0), (Wb, Td), (0, Td)], Lg, along(), col("ground"), lng("ground"), glue={2})
    sc.prism([(0, 0), (Wb, 0), (Wb, t), (0, t)], Lg, along(oz=Td + gap), col("line"), lng("line"), glue={2})
    sc.prism([(0, 0), (Wb, 0), (Wb, Td), (0, Td)], Lg, along(oz=Td + t + 2 * gap), col("ground"), lng("ground"))
    sc.mark("arrow", (Lg / 2, Wb / 2, TB + 2 * gap + 1.6), (Lg / 2, Wb / 2, TB + 2 * gap + 0.2))
    sc.mark("grain", (0.8, -1.0, 0), (Lg - 0.8, -1.0, 0))
    out["asm_blank"] = sc.svg(title="Three-ply blank")

    # inlay: a stretch of plank A with its grooves, sticks above the top face grooves
    sc = Scene(az=40, el=30); Lg = 5.0; n = min(cols, 4)
    for i in range(n):
        for r, g, p in placed("A", i, s, t, deg, c):
            if r == "star" and max(y for x, y in p) > s - 1e-6: continue          # the top face grooves are still open
            sc.prism(CB.ccw(p), Lg, along(), col(r), lng(r), outline=EDGE)
    for i in range(1, n, 2):
        sc.prism(CB.ccw([(i * s - c, 0), (i * s, -c), (i * s + c, 0), (i * s, c)]), Lg, along(oz=s + 1.0), col("star"), lng("star"))
        sc.mark("arrow", (Lg * 0.5, i * s, s + 1.0 - c - 0.05), (Lg * 0.5, i * s, s + 0.2))
    sc.mark("text", (0, n * s, s + 1.2), "star sticks, corner down", (12, -8))
    sc.mark("grain", (0.6, -0.9, 0), (Lg - 0.6, -0.9, 0))
    out["asm_inlay"] = sc.svg(title="Star sticks into the grooves")

    # crosscut
    sc = Scene(az=58, el=26); body = 4.0; cut = N["cut"]; gp = 0.6
    def plank_at(x0_, ln):
        for i in range(cols):
            for r, g, p in placed("A", i, s, t, deg, c):
                sc.prism(CB.ccw(p), ln, along(ox=x0_), col(r), lng(r), outline=EDGE)
    plank_at(0, body)
    for k in range(2): plank_at(body + gp + k * (cut + gp), cut)
    sc.mark("line", (body + gp / 2, -0.6, 0), (body + gp / 2, cols * s + 0.6, 0), RED)
    sc.mark("text", (body + gp / 2, -0.6, 0), "red: the saw cut", (-40, 22))
    sc.mark("text", (body + gp + cut, 0, s + 0.5), f"each slice is one row, {short(cut)} thick", (-250, -70))
    out["asm_cut"] = sc.svg(width=820, title="Crosscutting a plank into rows")
    return out


# ------------------------------------------------------------------------------------- page
def page(plan, svgs, photo, guide=None):
    from plan_page import CSS, TICK
    import re
    e = html.escape; N = plan["N"]; sp = plan["species"]; sh = plan["shop"]
    W, Lb, T = plan["board"]["width"], plan["board"]["length"], plan["board"]["thickness"]
    G, P, O = _nm(sp["ground"]), _nm(sp["line"]), _nm(sp["star"])
    s, t, deg, c = N["s"], N["t"], N["deg"], N["c"]; cols, rows = N["cols"], N["rows"]; bf = sum(x["bf_buy"] for x in plan["stock"])
    errors = [k for k in plan["checks"] if not k["ok"] and k["level"] != "warn"]; warns = [k for k in plan["checks"] if not k["ok"] and k["level"] == "warn"]
    size = f"{short(W)} × {short(Lb)} × {short(T)}"
    stamp = (f'<div class="stamp bad">✗ {len(errors)} check{"s" if len(errors) > 1 else ""} fail</div>' if errors else
             f'<div class="stamp">{TICK}{len(plan["checks"]) - len(warns)} of {len(plan["checks"])} checks pass</div>')
    def tb(no, title, by, meta):
        return f'<div class="tb"><div class="no mono">{no}</div><div><h2>{e(title)}</h2><div class="by">{by}</div></div><div class="meta">{meta}</div></div>'
    def fig(body, label, extra=""):
        return f'<figure><div class="ph">{body}</div><figcaption><span class="lbl">{e(label)}</span>{extra}</figcaption></figure>'
    ul = lambda xs: "<ul>" + "".join(f"<li>{x}</li>" for x in xs) + "</ul>"
    words = plan["name"].split(); h1 = e(" ".join(words[:-2])) + " <em>" + e(" ".join(words[-2:])) + "</em>" if len(words) > 2 else f"<em>{e(plan['name'])}</em>"
    desc = plan["description"]; lede = e(desc[0].upper() + desc[1:] + ". ") if desc else ""
    nglue = sum(1 for x in plan["steps"] if x.get("glue"))
    chain = "".join(f'<span><b>{n}</b>{e(x)}</span>' for n, x in enumerate(["three-ply blanks", f"{deg:g}° slabs", "square logs", "two planks", "star sticks", "rows", "board"], 1))
    stats = "".join(f'<div class="stat"><b class="mono">{b}</b><small>{e(x)}</small></div>' for b, x in (
        (e(size.replace('"', "")) + '"', "W × L × T, finished"), ("1", "log shape, used upright and on its side"), ("2", f"planks, each cut for {N['nA']} rows"),
        (str(rows), "rows, none of them turned"), (f"{bf:g}", "board feet to buy")))
    sheets = [("overview", "Overview", size), ("materials", "Material list", f"{bf:g} bd ft"), ("pattern", "The pattern", "1 tile"), ("slabs", "Blanks & slabs", f"{N['nslab']} slabs"),
              ("plank", "Planks & rows", f"2 planks · {rows} rows"), ("build", "Building it", f"{len(plan['steps'])} steps"), ("finish", "Flattening & options", "options"), ("sources", "Sources", "what is shown, what is mine")]
    index = "".join(f'<a href="#{i}"><span class="n">{n:02d}</span><span class="t">{e(x)}</span><span class="s">{e(y)}</span></a>' for n, (i, x, y) in enumerate(sheets, 1))
    index += (f'<a href="#checks"><span class="n">R</span><span class="t">Checks</span><span class="s" style="color:var(--{"weak" if errors else "good"})">'
              f'{"✗ " + str(len(errors)) + " fail" if errors else "all pass ✓" if not warns else str(len(plan["checks"]) - len(warns)) + " pass · " + str(len(warns)) + " note"}</span></a>')
    no = {i: f"{n:02d}" for n, (i, _, _) in enumerate(sheets, 1)}
    H = []

    # 01
    has_photo = bool(photo and os.path.exists(photo))
    if has_photo:
        mime = "image/png" if photo.lower().endswith(".png") else "image/jpeg"
        hero = fig(f'<img src="data:{mime};base64,{base64.b64encode(open(photo, "rb").read()).decode()}" alt="Render of the finished board">', "Render", "<span>made from the exact face with plan-to-photo; not a photo of a built board</span>")
    elif guide and os.path.exists(guide):
        from PIL import Image
        import io
        im = Image.open(guide).convert("RGB"); im.thumbnail((1500, 1500)); buf = io.BytesIO(); im.save(buf, "JPEG", quality=86)
        hero = fig(f'<img src="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}" alt="Model of the finished board">', "Model view", "<span>the exact face, colour coded by wood; not a photo</span>")
    else:
        hero = fig(svgs["face"], "Top face · finished size")
    how = [f"The whole board is one square tile, {short(s)} on a side: a {P} strip {short(t)} thick crossing a {G} square on a {deg:g} degree lean, with a corner of {O} at each end of the strip.",
           f"Upright, the strip is steep. On its side, the same tile has a shallow strip. Rows of upright tiles alternate with rows of tiles on their sides, and the steep and shallow zigzags close into six-sided cells, with a diamond of {O} at every corner where four strips meet.",
           f"What repeats: 1 slab shape and 1 log make everything. Plank A is {cols} logs upright, plank B is {cols} of the same logs on their sides; each plank is crosscut {N['nA']} times. No row is turned or flipped.",
           f"Nothing is assembled from small pieces. Blanks, slabs, logs and planks are all long, flat-sided and planed between glue-ups. The {O} diamonds are long square sticks glued into V-grooves in the planks, so each one is made of four triangles that are never handled as parts.",
           "The base board has no border, like the maker’s: the pattern runs to the edge."]
    glance = "".join(f"<dt>{e(k)}</dt><dd class='m'>{e(v)}</dd>" for k, v in (
        ("Blanks", f"{N['nblank']}, each {G} {short(N['Td'])}, {P} {short(t)}, {G} {short(N['Td'])}"), ("Slabs", f"{N['nslab']} + {N['spare_slabs']} spare, ripped at {deg:g}°, squared to {short(s)}"),
        ("Logs", f"{N['nlogs']} at {short(N['plank_len'])}, {N['per_stick']} from each stick"), ("Planks", f"2, each {short(cols * s)} × {short(s)} × {short(N['plank_len'])}"),
        ("Star sticks", f"{N['ngroove']} lengths, {fine(N['q'])} square"), ("Rows", f"{rows}, cut {short(N['cut'])} thick"), ("Glue-ups", f"{nglue}, every one with flat faces")))
    woods = "".join(f'<li><span class="sw" style="background:{sp[x["role"]]["end"]}"></span>{e(x["species"])}: {x["bf_buy"]:g} bd ft</li>' for x in plan["stock"])
    tools = [f"Table saw with a riving knife, digital angle gauge (one bevel setting: {deg:g}°), featherboard, push blocks", "Jointer and planer: every part before the final board is long grain and flat-sided",
             f"Router table with a 90° V-groove bit, {short(sh['vbit'])} or wider", "Bandsaw to resaw the thin ply", "Crosscut sled with a stop block and hold-down", "Calipers and a straightedge",
             "Flat cauls, bar clamps, Titebond III", "Router sled to flatten the board, random-orbit sander", "Mineral oil and board butter"]
    H.append(f'<article class="sheet" id="overview">{tb("01", "Overview", e(desc[0].upper() + desc[1:]) if desc else "", f"<div class=dims>{e(size)}</div>{stamp}")}'
             f'<div class="main"><div style="display:grid;gap:0;align-content:start">{hero}{fig(svgs["face"], "Top face · finished size")}</div><div class="notes" style="padding:0;display:grid;gap:0;align-content:start">{fig(svgs["tile"], "The tile")}'
             f'<div class="notes"><h3>How it goes together</h3>{ul([e(x) for x in how])}<h3>At a glance</h3><dl class="kv">{glance}</dl></div></div></div>'
             f'<div class="lower" style="grid-template-columns:1fr 1.65fr"><div class="notes"><h3>Wood to buy</h3><ul>{woods}</ul></div>'
             f'<div class="notes"><h3>Tools</h3><ul style="display:block;columns:2 30ch;column-gap:32px">{"".join(f"<li>{e(x)}</li>" for x in tools)}</ul></div></div></article>')

    # 02
    trs = ""
    for x in plan["stock"]:
        trs += (f'<tr class="grp"><td colspan="4"><span class="sw" style="background:{sp[x["role"]]["end"]}"></span>{e(x["species"])} · buy {x["bf_buy"]:g} bd ft</td></tr>'
                f'<tr><td class="m">{e(x["rough"])}</td><td class="q">{x["n"]}</td><td class="m">{e(x["size"])}</td><td class="m">{e(x["use"])}</td></tr>')
    trs += (f'<tr class="grp"><td colspan="4">Scrap, any wood</td></tr><tr><td class="m">offcuts</td><td class="q">4</td><td class="m">{short(N["scrap"])} x {short(s)} x {short(N["plank_len"])}</td><td class="m">sacrificial strips on the plank edges</td></tr>')
    wl = "".join(f'<li><span class="sw" style="background:{w["end"]}"></span><b>{e(w["name"])}</b>' + (f' · Janka {w["janka"]} · shrinkage {w["tan"]}%' if w["janka"] else "") + f'. {e(w["note"])}</li>' for w in plan["woods"])
    H.append(f'<article class="sheet" id="materials">{tb("02", "Material list", "Three woods; the ground wood is most of the cost", "<div class=dims>T × W × L</div>")}'
             f'<div class="lower full" style="border-top:0"><div class="panel"><div class="tbl"><table class="d"><tr><th>Rough stock</th><th style="text-align:right;padding-right:12px">Pieces</th><th>Milled size</th><th>Use</th></tr>{trs}</table></div>'
             f'<p class="small">Board feet include 25% for defects and milling. This build is hard on the {G}: about {round(N["yield"] * 100)}% of the {G} in the blanks ends up in logs. The rest is the triangle wasted by the first tilted cut, the {short(sh["blank_bearing"])} left to keep each blank flat on the saw, and the two sloping edges ripped off every slab. '
             f'That is the price of never handling a small or bevelled part. The offcuts from squaring are long three-ply strips, worth keeping for another board.</p></div></div>'
             f'<div class="lower full"><div class="notes"><h3>The woods</h3><ul>{wl}</ul>'
             f'<p class="small">The maker’s stills show wenge for the ground. The purple is almost certainly purpleheart and the orange looks like padauk; those two are my reading of the colours, not something the maker states where I could read it. '
             f'Wenge is hard and nearly black, which is what makes the purple show, but its splinters are nasty and its end grain is open-pored. Black walnut is the kinder and cheaper swap ("species": {{"ground": "walnut"}}); the purple will stand out less against it. '
             f'Purpleheart and padauk both dull with light over the years: purple toward brown, orange toward red-brown.</p></div></div></article>')

    # 03
    H.append(f'<article class="sheet" id="pattern">{tb("03", "The pattern", "Read from the maker’s cover photo, then simplified", f"<div class=dims>tile {short(s)} · strip {short(t)} · lean {deg:g}°</div>")}'
             f'<div class="main"><div style="display:grid;gap:0;align-content:start">{fig(svgs["tile"], "The tile, and four of them round one star")}{fig(svgs["face"], "This plan’s face, drawn from the tile")}</div><div class="panel"><h3>What the photos show</h3>{ul([
                 "Squared up, the maker’s cover photo shows the stars on a square grid, on every other grid corner like the black squares of a checkerboard. So the board is square tiles, not hexagons.",
                 "Purple strips join the stars in zigzags that run across the board. Rows of steep zigzags alternate with rows of shallow ones, the steep ones about 35 degrees off upright and the shallow ones about 35 degrees off level. A steep row and a shallow row together close the six-sided cells.",
                 "A steep tile and a shallow tile are the same tile a quarter turn apart. That is the whole trick, and it is why one log can make the board.",
                 "A still from the build shows a row of about eight dark blocks, each with one leaning purple strip, alternately leaning left and right, with small pale pieces where the strips meet."])}'
             f'<h3>Where this plan departs from the maker’s board</h3>{ul([
                 f"His stars are small hourglass shapes boxed in by short purple pieces. Mine are plain {O} diamonds, {short(2 * c)} across, that the strips run straight into. The lattice reads the same; the stars are simpler.",
                 f"His dark ground is pieced from more than one tone, in bars and stems that show in the photo. Mine is one wood.",
                 f"His board looks like about 12 tiles by 8. This plan is {cols} by {rows} at {short(s)} a tile."])}'
             f'<h3>Sizes</h3><dl class="kv"><dt>Tile</dt><dd class="m">{short(s)} square</dd><dt>Strip</dt><dd class="m">{short(t)} thick, leaning {deg:g}° from the log’s side</dd><dt>Star</dt><dd class="m">{short(2 * c)} corner to corner, from four {short(c)} corners</dd>'
             f'<dt>Board</dt><dd class="m">{cols} × {rows} tiles</dd></dl></div></div></article>')

    # 04
    H.append(f'<article class="sheet" id="slabs">{tb("04", "Blanks & slabs", "One blank, one saw tilt, one slab: every log comes from these", f"<div class=dims>{N["nblank"]} blanks · {N["nslab"]} slabs + {N["spare_slabs"]} spare</div>")}'
             f'<div class="jgrid" style="grid-template-columns:1fr">'
             f'<div class="joint"><div class="jh"><span class="jn">A</span><div><h4>The three-ply blank</h4><div class="jsub">{G} {short(N["Td"])}, {P} {short(t)}, {G} {short(N["Td"])}, glued face to face</div></div></div><div class="ph">{svgs["blank"]}</div></div>'
             f'<div class="joint"><div class="jh"><span class="jn">B</span><div><h4>Rip the slabs</h4><div class="jsub">blade {deg:g}° from upright, blank flat on the table against the fence</div></div></div><div class="ph">{svgs["rip"]}</div>'
             f'<p class="small">Seen from the infeed end. The blank stays between the blade and the fence and each slab falls away on the far side, under the lean of the blade, where nothing traps it. The {P} ply becomes the leaning strip in every slab.</p></div>'
             f'<div class="joint"><div class="jh"><span class="jn">C</span><div><h4>Plane, then rip each slab square</h4><div class="jsub">blade at 90°; two rips per slab</div></div></div><div class="ph">{svgs["slab"]}</div>'
             f'<p class="small">The slab is drawn lying on a sawn face. The sizes on the drawing are what to measure on the test slab. If the {G} beside the {P} measures long on the face that was up, move the fence toward the blade by the difference.</p></div></div></article>')

    # 05
    worth = "".join(f'<tr><td class="m" style="color:var(--accent-ink)">Plank {p["id"]}</td><td class="m">{p["logs"]} logs</td><td>{e(p["why"])}</td></tr>' for p in plan["planks"])
    rowtab = "".join(f'<tr><td class="m" style="color:var(--accent-ink)">R{r["n"]}</td><td class="m">plank {r["plank"]}, as cut</td></tr>' for r in sorted(plan["rows"], key=lambda r: r["n"]))
    H.append(f'<article class="sheet" id="plank">{tb("05", "Planks & rows", "End views: blue lines are glue, red marks are grooves, dashed strips are scrap", f"<div class=dims>{N["nlogs"]} logs · 2 planks · {rows} rows</div>")}'
             f'<div class="lower full" style="border-top:0">{fig(svgs["plankA"], "Plank A, end view, after the stars are in: this is also what an A row looks like from above")}</div>'
             f'<div class="lower full">{fig(svgs["plankB"], "Plank B, end view: the same logs on their sides")}</div>'
             f'<div class="lower" style="grid-template-columns:1.2fr 1fr"><div class="panel"><h3>Worth a plank?</h3><div class="tbl"><table class="d">{worth}</table></div>'
             f'{ul(["Both planks are the same log, so a spare log fits either.", "In each plank the grooves alternate faces from one glue line to the next. Where plank A has a groove on its lower face, plank B has one on its upper face, so the halves meet when the rows are stacked A over B.", "The scrap strips let the two edge grooves be cut and filled like the rest. Ripping them off leaves half a diamond on the edge of the board."])}</div>'
             f'{fig(svgs["groove"], "One groove, close up")}</div>'
             f'<div class="main" style="border-top:1px solid var(--rule)">{fig(svgs["rows"], "The board from above: red arrows are your pencil arrows, all pointing the same way")}<div class="panel"><h3>Rows</h3>'
             f'<div class="tbl"><table class="d">{rowtab}</table></div>{ul(["Rows alternate A, B from the top.", "Nothing is turned end for end and nothing is flipped."])}</div></div></article>')

    # 06
    def runin(x):
        m_ = re.match(r"^([A-Z][A-Za-z' -]{2,26})[:.] ", x)
        return f"<b>{e(m_.group(1))}.</b> {e(x[m_.end():][:1].upper() + x[m_.end():][1:])}" if m_ else e(x)
    body = ""; ng = 0
    for n, x in enumerate(plan["steps"], 1):
        kick = ""
        if x.get("glue"):
            ng += 1; kick = f'<span class="kick">GLUE-UP {ng}</span><br>'
        refs = [no[d] for d in x.get("see", []) if d in no]
        see = f'<div class="see">See sheet {", ".join(refs)}</div>' if refs else ""
        dont = f'<div class="dont"><b>DON\'T</b>{e(x["dont"])}</div>' if x.get("dont") else ""
        b = f'{kick}<h4>{e(x["title"])}</h4><ul>{"".join(f"<li>{runin(y)}</li>" for y in x["text"])}</ul>{see}'
        figs = [f for f in x.get("figs", []) if f in svgs]
        if figs: b = f'<div class="stepgrid"><div>{b}</div><div class="asm">{"".join(f"<figure{' class=wide' if f in ('rip', 'plankA', 'plankB', 'asm_cut', 'slab', 'rows') else ''}>{svgs[f]}</figure>" for f in figs)}</div></div>'
        body += f'<li><span class="sn">{n}</span><div>{b}</div>{dont}</li>'
    H.append(f'<article class="sheet" id="build">{tb("06", "Building it", "In order, with the reason where it isn\'t obvious", f"<div class=dims>{len(plan["steps"])} steps · {nglue} glue-ups</div>")}'
             f'<div class="stepbox"><ol class="steps">{body}</ol></div></article>')

    # 07
    H.append(f'<article class="sheet" id="finish">{tb("07", "Flattening & options", "Two ways to flatten without a drum sander, and what can be changed", "<div class=dims>options</div>")}'
             f'<div class="lower" style="border-top:0;grid-template-columns:1fr 1fr 1fr">'
             f'<div class="panel"><h3>Route 1 · router sled and sander</h3>{ul(["Board on a flat base, shimmed so it cannot rock, between two straight rails; a wide straight or bowl bit in a router on a bridge.", "Passes of 1/32 in. or less, the full face, then the other face.", "Sand out the router marks from 80 grit. This is the route the plan assumes and the one every source agrees on."])}</div>'
             f'<div class="panel"><h3>Route 2 · helical-head planer</h3>{ul(["Up to here the planer has done everything, because every part was long grain. The finished board is end grain, and a planer can tear the trailing edge out or throw the board.", "If you use it anyway, follow George Vondriska’s method (sheet 08): glue sacrificial long-grain rails to the leading and trailing edges or put a heavy chamfer on the trailing edge, take 1/64 in. or less a pass, sharp inserts, and stand out of line.", "This plan has not tested it and does not need it. Wenge end grain is brittle and chips at an unsupported edge, so the rails matter more here than on a maple board."])}</div>'
             f'<div class="panel"><h3>Options</h3>{ul([f"Ground wood: walnut in place of {G} is cheaper and kinder to work, with less contrast.", f"Scale: \"params\": {{\"tile\": 1.25}} makes a smaller board from thinner stock; the ply sizes and fence settings are recomputed and the checks say if a strip would miss its star.", "Border: the maker’s board has none and neither does this plan. If you want one, make it end grain like the field (blocks crosscut from a planed board and stood on end), never a long-grain frame, which cracks the board or itself as the field moves.", "Juice groove or handles: rout them after flattening; keep a groove clear of the stars at the edge."])}</div></div></article>')

    # 08
    src = "".join(f'<li><a href="{e(url)}">{e(x)}</a><br><span class="small">{e(n)}</span></li>' for x, url, n in SOURCES)
    H.append(f'<article class="sheet" id="sources">{tb("08", "Sources", "What the maker shows, and what in this plan is worked out rather than shown", "<div class=dims>read 2026-11-14</div>")}'
             f'<div class="lower" style="border-top:0;grid-template-columns:1fr 1fr">'
             f'<div class="panel"><h3>Shown by the maker</h3>{ul(["The finished face, in the cover photo of the full video.", "Wenge as the dark wood, ripped from a thick beam.", "Dark bars laminated with thin pale strips between them.", "A glue-up of a row of dark blocks, each with one leaning purple strip, alternately left and right, with small pale pieces at the points where strips meet. That row is a plank in all but name.", "Stripes of orange and purple running through the thickness at the board’s edges, so the stars are long sticks, not surface inlay."])}'
             f'<h3>Shown by other makers</h3>{ul(["Laminate, saw into strips at an angle, plane, re-glue, crosscut the plank into rows: MTM Wood and Bob Chambers.", "Rows crosscut from a glued plank: any checkerboard end-grain board."])}</div>'
             f'<div class="panel"><h3>Worked out for this plan, not shown</h3>{ul(["I could not play either video here, only read their titles and the still frames YouTube publishes for them. I do not know the order of the maker’s steps between those stills, and his own method is very likely different from mine in the details.",
                 "The pattern on sheet 03 is my simplified version of the maker’s face, not a copy of it: plain diamonds instead of his boxed hourglass stars, and a one-wood ground. I checked it against the photo by eye, not by measurement.",
                 f"The three-ply blank, its thicknesses, the {deg:g} degree slab and the two squaring rips are my reconstruction, carried over from the two-wood maze plan. The maker’s still suggests he glues leaning strips between separate dark bars instead.",
                 "Using one log upright for one plank and on its side for the other is my reading of the face. It works on paper for any strip that is the same after half a turn.",
                 "The stars as square sticks glued corner down into V-grooves routed along the planks’ glue lines, and the scrap strips for the edge grooves, are my method. I have not seen the maker or anyone else do this on a plank. Rout and fill one groove in an offcut first.",
                 "The helical-planer route for the finished board is Vondriska’s, untested on this board.", "Nobody has built this plan yet."])}</div></div>'
             f'<div class="lower full"><div class="notes"><h3>Links</h3><ul>{src}</ul></div></div></article>')

    chk = "".join(f'<tr><td>{e(k["what"])}' + (f'<span class="sub">{e(k["detail"])}</span>' if k["detail"] else "") + '</td>'
                  f'<td class="{"pass" if k["ok"] else k["level"] if k["level"] == "warn" else "fail"}">{"PASS" if k["ok"] else ("WARN" if k["level"] == "warn" else "FAIL")}</td></tr>' for k in plan["checks"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(plan["name"])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@112,600;112,700&family=IBM+Plex+Mono:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{CSS}</style></head><body><div class="wrap">
<header class="hero"><div class="eyebrow">End-grain cutting board · shop plan · after Stammherz</div>
<h1>{h1}</h1><p class="lede">{lede}</p><div class="chain" aria-label="Build order">{chain}</div><div class="stats">{stats}</div></header>
<nav class="index" aria-label="Sheets">{index}</nav>
<main>{"".join(H)}</main>
<article class="sheet" id="checks">{tb("R", "Checks", "Recomputed from the board's geometry every time the plan is built", stamp)}
<div class="lower full" style="border-top:0"><div class="panel"><table class="cost">{chk}</table></div></div></article>
<footer>Kerf {short(sh["kerf"])}; slabs ripped {short(sh["slab_over"])} over and planed to size; rows cut {short(N["cut"])}; {short(sh["end_trim"])} to square the first end of each plank and {short(sh["hold_end"])} held at the other. Change these under "shop" in design.json and rebuild.</footer>
</div></body></html>"""
