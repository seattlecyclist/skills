#!/usr/bin/env python3
"""Plank builds: boards whose rows are crosscut from one long glued-up plank.

The first of them is `maze` (Stammherz's two-wood board): one square tile of two stepped bars, turned
a quarter turn in a checkerboard. Nothing is assembled from small pieces:

  two-ply blank (light on dark, face glued)  ->  slabs ripped off it with the blade at 45 degrees
  ->  slabs planed, ripped square, stacked four high into a square log (every other slab rolled over)
  ->  logs glued side by side into a plank (every other log a quarter turn)
  ->  the plank crosscut into rows  ->  rows glued into the board (every other row turned end for end).

cbplan.py hands a design with "pattern": "maze" to build() here; the outputs are the same files
(plan.html, plan.json, svg/, guide.png, spec.md, room.md, board.obj).
"""
import base64, html, json, math, os, sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import species as SP

R2 = math.sqrt(2)
SHOP = {"kerf": 0.125, "flatten_allowance": 0.125, "end_trim": 0.5, "hold_end": 2.0, "spare_rows": 1, "slab_over": 1 / 16,
        "ply_margin": 0.04, "blank_width": 9.25, "blank_bearing": 1.5, "max_bevel_depth": 2.125, "planer_width": 12.5,
        "edge_clean": 1 / 32, "true_skim": 1 / 64}
SOURCES = [
    ("Stammherz, “Another Cutting Board You’ve Never Seen!” (YouTube short)", "https://www.youtube.com/shorts/TrEm6C_xBT8",
     "The board this plan copies. Its stills show a walnut and light-wood stack being clamped face to face, and the finished board going into its border glue-up as square end-grain blocks."),
    ("Stammherz, “It Looks Impossible — But It’s Just 2 Woods” (the full build video)", "https://www.youtube.com/watch?v=rUjjSO708qE",
     "Stills show light boards and thin walnut strips laid out for laminating (build time 2 hours), a striped laminate being ripped on the table saw with the blade tilted, a stack of two-tone strips with bevelled edges on the planer (build time 11 hours), and the finished board square-on."),
    ("Stammherz shop and plans", "https://www.stammherz.de/diy-shop/", "The maker sells plans for other boards. No plan for this pattern was listed on 2026-11-14."),
    ("Andrei Muntian (MTM Wood), Making a 3D End Grain Cutting Board #1 and #3", "https://www.instructables.com/Making-a-3D-end-grain-cutting-board-1/",
     "The same family of method, shown step by step: laminate a blank, saw it into strips at an angle, plane, re-glue the strips, crosscut the plank into rows."),
    ("Bob Chambers, Building an Optical Illusion End Grain Cutting Board (after MTM Wood)", "https://www.brwoodworkers.com/optical-illusion-end-grain-cutting-board/",
     "A second builder following the laminate, re-saw, re-glue, crosscut sequence, with the planing between glue-ups."),
    ("George Vondriska (WWGOA), Running an End Grain Cutting Board Through a Planer", "https://wwgoa.com/video/running-end-grain-cutting-board-planer",
     "The source for the optional planer route on sheet 07."),
    ("Marc Spagnuolo, Why Did My Cutting Board Split?", "https://thewoodwhisperer.com/videos/why-did-my-cutting-board-split/",
     "Why the optional border is end grain like the field, never a long-grain frame."),
]


def frac(x, den=32):
    n = round(abs(x) * den); w, r = divmod(n, den); d = den
    while r and r % 2 == 0: r //= 2; d //= 2
    s = (f"{w}" if w else "") + (("-" if w else "") + f"{r}/{d}" if r else "")
    return ("-" if x < 0 else "") + (s or "0")


def short(x):
    return f'{frac(x)}"'


def fine(x):
    """A critical size: the 64th and the decimal."""
    return f'{frac(x, 64)}"' if abs(x - round(x * 64) / 64) < 5e-4 else f'{frac(x, 64)}" ({x:.3f})'


def _up(x, step=0.25):
    return math.ceil(x / step - 1e-9) * step


def nominal(t):
    for q, lim in ((4, 0.8125), (5, 1.0625), (6, 1.3125), (8, 1.75), (10, 2.25), (12, 2.75)):
        if t <= lim + 1e-9: return q
    return None


# ------------------------------------------------------------------------------------- the face
def tile(u):
    """The tile as it leaves the log, y up: four layers, each a light and a dark trapezoid meeting on a 45 degree line."""
    a, b = 1 + 1 / R2, 1 - 1 / R2; out = []
    for k in range(4):
        if k % 2 == 0:
            out.append(("light", k, [(0, k), (a, k), (a + 1, k + 1), (0, k + 1)]))
            out.append(("dark", k, [(a, k), (4, k), (4, k + 1), (a + 1, k + 1)]))
        else:
            out.append(("dark", k, [(0, k), (b + 1, k), (b + 2, k + 1), (0, k + 1)]))
            out.append(("light", k, [(b + 1, k), (4, k), (4, k + 1), (b + 2, k + 1)]))
    return [(r, k, [(x * u, y * u) for x, y in p]) for r, k, p in out]


def face_polys(cols, rows, u):
    s = 4 * u; out = []
    for j in range(rows):
        for i in range(cols):
            flat = (i + (rows - 1 - j)) % 2 == 0              # the top-left tile is a flat one, as in the maker’s board
            for r, k, p in tile(u):
                q = p if flat else [(s - y, x) for x, y in p]
                out.append({"pts": [(round(x + s * i, 6), round(y + s * j, 6)) for x, y in q], "role": r, "slice": f"r{j}", "unit": None,
                            "tile": (i, j), "flat": flat})
    return out


def generate(p, board):
    u = float(p.get("bar", 0.5)); s = 4 * u
    cols = int(p.get("cols") or max(2, 2 * round(board["width"] / s / 2)))
    rows = int(p.get("rows") or max(1, round(board["length"] / s)))
    return {"polygons": face_polys(cols, rows, u), "trim": [0, 0, cols * s, rows * s], "roles": ["light", "dark"],
            "cells": {"kind": "plank"}, "bar": u, "cols": cols, "rows": rows,
            "notes": [f"{rows} rows of {cols} tiles, each {short(s)} square with two stepped bars {short(u)} wide."]}


# ------------------------------------------------------------------------------------- the plan
def build(design, out, photo=None):
    import cbplan as CB
    shop = dict(SHOP, **design.get("shop", {})); board = design["board"]; T = float(board.get("thickness", 1.5))
    frame = design.get("frame") or None; fw = float(frame.get("width", 1.25)) if frame else 0.0
    g = generate(design.get("params", {}), dict(board, width=board["width"] - 2 * fw, length=board["length"] - 2 * fw))
    u, cols, rows = g["bar"], g["cols"], g["rows"]; s = 4 * u; polys = g["polygons"]
    checks = []
    def check(ok, what, detail="", level="error"):
        checks.append({"ok": bool(ok), "what": what, "detail": detail, "level": level})
    smap = design.get("species", {}); smap = {"light": smap.get("light", "maple"), "dark": smap.get("dark", "walnut")}
    sp = {r: SP.get(smap[r]) for r in ("light", "dark")}
    if frame: sp["frame"] = SP.get(frame.get("species", smap["dark"]))
    woods = OrderedDict()
    for r in sp: woods.setdefault(sp[r]["key"], sp[r])
    jk = [w for w in woods.values() if w["janka"] and w["janka"] < 900]
    check(not jk, "Species hard enough for a cutting surface (Janka 900+)", ", ".join(f'{w["name"]} {w["janka"]}' for w in jk))
    tans = [w["tan"] for w in woods.values() if w["tan"]]; spread = max(tans) - min(tans) if tans else 0
    check(spread <= 4.0, "Species move alike (tangential shrinkage within 4 points)", f"{min(tans):.1f}% to {max(tans):.1f}%" if tans else "", "warn")

    # the face
    check(all(CB.convex(CB.ccw(p["pts"])) for p in polys), "Every piece of the face is convex")
    trim0 = [0, 0, cols * s, rows * s]
    no, op_, ng, gp = CB.coverage(polys, trim0, max(0.01, u / 12))
    check(no == 0, "Pieces do not overlap", f"overlap near {op_}" if no else "")
    check(ng == 0, "Pieces cover the whole board (no gaps)", f"gap near {gp}" if ng else "")
    # one slab makes every layer: layer k+1 is layer k rolled over (turned 180 degrees in the end view)
    tl = tile(u); lay = lambda k: sorted((r, tuple(sorted((round(x, 5), round(y - k * u, 5)) for x, y in p))) for r, kk, p in tl if kk == k)
    roll = lambda L: sorted((r, tuple(sorted((round(s - x, 5), round(u - y, 5)) for x, y in p))) for r, p in L)
    check(all(lay(k + 1) == roll(lay(k)) for k in range(3)), "All four layers of the log are the same slab, every other one rolled over")
    rowset = lambda j, turn: sorted((p["role"], tuple(sorted((round((cols * s - x) if turn else x, 4), round((s - (y - j * s)) if turn else (y - j * s), 4)) for x, y in p["pts"])))
                                    for p in polys if p["tile"][1] == j)
    check(all(rowset(j, False) == rowset(j + 1, True) for j in range(rows - 1)), "Every row is the same slice of the plank, every other one turned end for end")
    check(cols % 2 == 0, "An even number of tiles in a row, so turning a row end for end gives the next row", f"{cols} tiles")

    # plies, blank, slabs
    m = shop["ply_margin"]; over = shop["slab_over"]; kerf = shop["kerf"]
    Tl = _up(((1 + 1 / R2 + 1) * u + m) / R2, 1 / 16); Td = _up(((1 - 1 / R2 + 2) * u + m) / R2, 1 / 16)
    TB = Tl + Td; rough = u + over; stepx = (rough + kerf) * R2
    long_l, long_d = (2 + 1 / R2) * u, (3 - 1 / R2) * u            # the long face of each wood in the squared slab
    short_l, short_d = long_l - u, long_d - u
    spare_l, spare_d = Tl * R2 - long_l, Td * R2 - long_d
    check(min(spare_l, spare_d) >= 1 / 32 - 1e-6, "Plies thick enough to rip every slab square", f"{spare_l:.3f}\" spare at the light end, {spare_d:.3f}\" at the dark end")
    check(TB <= shop["max_bevel_depth"] + 1e-6, "The blank fits under the blade tilted to 45 degrees",
          f"blank {short(TB)} thick; a 10 in. saw cuts about {short(shop['max_bevel_depth'])} at 45 degrees" + ("" if TB <= shop["max_bevel_depth"] else ". Use narrower bars"))
    check(u >= 0.375 - 1e-9, "Bars at least 3/8\" wide", short(u), "warn")
    Wb = shop["blank_width"]; per_blank = int((Wb - TB - shop["blank_bearing"]) // stepx + 1e-9)
    check(per_blank >= 1, "The blank is wide enough to rip a slab from", f"{short(Wb)} wide")
    cut = T + shop["flatten_allowance"]; pitch = cut + kerf
    nrow = rows + shop["spare_rows"]; plank_len = _up(nrow * pitch + shop["end_trim"] + shop["hold_end"])
    nlong = math.ceil(cols / 2); log_len = _up(2 * plank_len + kerf + 0.25); slab_len = log_len + 0.25; blank_len = _up(slab_len + 0.5, 0.5)
    nslab = 4 * nlong; nblank = math.ceil((nslab + 1) / max(1, per_blank)); spare_slabs = nblank * per_blank - nslab
    groups = max(1, math.ceil(cols * s / shop["planer_width"] - 1e-9))
    while cols % groups: groups += 1
    per_group = cols // groups
    check(s <= 2.625, "The log passes under the saw and through the planer", f"{short(s)} square")
    check(T >= 1.0, "Board at least 1\" thick (end grain under 1\" can split)", f'{T}"')
    ec = shop["edge_clean"]; W = cols * s - 2 * ec; Lb = rows * s
    trim = [ec, 0, cols * s - ec, rows * s]
    face = [{"pts": c, "role": p["role"]} for p in polys for c in [CB.clip_rect(p["pts"], trim)] if c]
    frame_out = None
    if frame:
        t0, t1, t2, t3 = trim
        pcs = [[t0, t1 - fw, t2, t1], [t0, t3, t2, t3 + fw], [t0 - fw, t1 - fw, t0, t3 + fw], [t2, t1 - fw, t2 + fw, t3 + fw]]
        for a, b, c, d in pcs: face.append({"pts": [(a, b), (c, b), (c, d), (a, d)], "role": "frame"})
        frame_out = {"width": fw, "species": sp["frame"]["name"], "pieces": pcs, "outer": [t0 - fw, t1 - fw, t2 + fw, t3 + fw]}
        check(fw >= 0.375, "Frame at least 3/8\" wide", short(fw), "warn")
    Wt, Lt = W + 2 * fw, Lb + 2 * fw
    check(max(Wt, Lt) / T <= 18, "Board not too large for its thickness", f"{Wt:.1f} x {Lt:.1f} x {T}", "warn")

    stock = []
    for role, tk in (("light", Tl), ("dark", Td)):
        q = nominal(tk); bf = nblank * (q / 4) * (Wb + 0.5) * (blank_len + 1) / 144
        if frame and sp["frame"]["key"] == sp[role]["key"]:
            bf += (nominal(fw) or 8) / 4 * 6 * (2 * (Wt + Lt) / 5.0 * pitch + 6) / 144
        stock.append({"species": sp[role]["name"], "key": sp[role]["key"], "role": role, "rough": f"{q}/4", "mill_to": tk, "n": nblank,
                      "size": f'{short(tk)} x {short(Wb)} x {short(blank_len)}', "bf": bf, "bf_buy": math.ceil(bf * 1.25 * 2) / 2})
    N = {"u": u, "s": s, "cols": cols, "rows": rows, "Tl": Tl, "Td": Td, "TB": TB, "rough": rough, "stepx": stepx, "long_l": long_l, "long_d": long_d,
         "short_l": short_l, "short_d": short_d, "fenceA": long_l + Td * R2, "slab_w": TB * R2, "Wb": Wb, "per_blank": per_blank, "nblank": nblank,
         "nslab": nslab, "spare_slabs": spare_slabs, "blank_len": blank_len, "slab_len": slab_len, "log_len": log_len, "nlong": nlong, "plank_len": plank_len,
         "cut": cut, "pitch": pitch, "nrow": nrow, "groups": groups, "per_group": per_group, "blade_reach": TB * R2}
    plan = {"name": design.get("name", "Two-Wood Maze End-Grain Board"), "description": design.get("description", ""), "pattern": "maze",
            "board": {"width": Wt, "length": Lt, "thickness": T, "trim": frame_out["outer"] if frame else trim, "field": [W, Lb], "frame": frame_out, "field_trim": trim},
            "shop": shop, "species": sp, "woods": list(woods.values()), "notes": g["notes"], "options": design.get("options", {}), "face": face,
            "polygons": polys, "stock": stock, "checks": checks, "method": "plank", "N": N, "slice_cut": cut, "n_slices": rows,
            "rows": [{"n": rows - j, "turned": (rows - 1 - j) % 2 == 1} for j in range(rows)], "bars": [], "bar_types": [],
            "logs": [{"id": "A", "name": "Log A", "what": "square log of four slabs", "make": [(log_len, nlong)], "crosscut": False, "count": nlong}],
            "info": {"kind": "plank"}}
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
    json.dump({k: v for k, v in plan.items() if k != "polygons"}, open(os.path.join(out, "plan.json"), "w"), indent=1, default=str)
    return plan


# ------------------------------------------------------------------------------------- steps
def steps(plan):
    N = plan["N"]; sp = plan["species"]; T = plan["board"]["thickness"]; fr = plan["board"]["frame"]
    L, D = sp["light"]["name"].split()[-1].lower(), sp["dark"]["name"].split()[-1].lower()
    u, s = N["u"], N["s"]; W, Lb = plan["board"]["field"]
    half = N["groups"] > 1
    st = [
        {"title": "Mill the plies", "figs": ["blank"], "text": [
            f"Joint and plane {N['nblank']} {L} boards to {short(N['Tl'])} thick and {N['nblank']} {D} boards to {short(N['Td'])} thick, all {short(N['Wb'])} wide and {short(N['blank_len'])} long. Plane each wood in one session at one setting.",
            f"The two thicknesses set where the light and dark meet in every bar of the pattern, so measure them with calipers: within 0.005\" of each other board to board.",
            f"No {short(N['Wb'])} boards? Edge-glue narrower ones to that width first. A seam inside a ply never shows as a line in the pattern, only as an ordinary glue line in one wood."]},
        {"title": "Glue the two-ply blanks", "glue": True, "figs": ["asm_blank"], "text": [
            f"Glue one {L} board face to face on one {D} board: {N['nblank']} blanks, each {short(N['TB'])} thick. Roll the glue on one face, rub the boards together, and clamp between flat cauls with a clamp every 4 to 5 inches.",
            "Next day scrape the squeeze-out, joint one edge of each blank square to its faces and rip the other edge parallel. That jointed edge rides the fence in the next step."]},
        {"title": "Rip the slabs with the blade at 45 degrees", "figs": ["rip"], "text": [
            f"Tilt the blade to 45 degrees with a digital gauge, away from the fence, and raise it to cut through the {short(N['TB'])} blank (the blade is in {N['blade_reach']:.2f}\" of wood). Riving knife on, featherboard ahead of the blade, push blocks.",
            "The blank lies flat on the table with its jointed edge against the fence for every cut. The slab is the piece that comes off on the far side of the blade.",
            f"First cut: set the fence so the blade just takes the top corner off the far edge. That waste is a triangle.",
            f"Then move the fence {fine(N['stepx'])} toward the blade for each slab. Each slab comes off about {short(N['rough'])} thick with two bevelled edges. Check the first with calipers and adjust the move.",
            f"Take {N['per_blank']} slabs from each blank and stop: the last {short(plan['shop']['blank_bearing'])} of the blank is what holds it flat. {N['nblank'] * N['per_blank']} slabs in all; {N['nslab']} are needed, the rest are for setting up step 5."],
         "dont": "rip the last slab from a blank that no longer sits flat with its edge on the fence."},
        {"title": "Plane the slabs", "figs": [], "text": [
            f"A slab lies flat on its wide face, so it goes through the planer like any thin board. Plane every slab to exactly {short(u)}, taking the same from each face, all at the last setting in one session.",
            f"Check: four slabs stacked measure {short(s)}. The stack height is the size of the tile, and the next step rips the slabs to that same width."]},
        {"title": "Rip the slabs square, twice", "figs": ["slab"], "text": [
            "Blade back to 90 degrees. Each slab needs both bevelled edges ripped off square, at the right distance from its glue line.",
            f"Cut A squares the {L} edge. Lay the slab so the sharp corner of its {D} edge is down on the table and against the fence, and set the fence {fine(N['fenceA'])} from the blade. Test on a spare slab and measure the {L} from the new edge to the glue line: {fine(N['short_l'])} on the face that was up, {fine(N['long_l'])} on the face that was down. Nudge the fence until both are right, then run every slab.",
            f"Cut B squares the {D} edge. Turn the slab so the new square edge is against the fence and rip it to {short(s)} wide, or to the height of four stacked slabs if that measured a hair different. The log must come out square.",
            f"After both cuts every slab is {short(s)} x {short(u)} and shows {fine(N['long_l'])} of {L} and {fine(N['short_d'])} of {D} on one face, {fine(N['short_l'])} and {fine(N['long_d'])} on the other."]},
        {"title": "Glue the logs: four slabs each", "glue": True, "figs": ["log", "asm_log"], "text": [
            f"Stack four slabs, rolling every other one over along its length, so the {L} is on the left in slabs 1 and 3 and on the right in slabs 2 and 4. Looked at from the end, all four glue lines lean the same way and the {L} makes two bars that each step up once.",
            "Dry-stack first and look at the end against the drawing. If the bars do not join into two clean steps, a slab is end for end instead of rolled.",
            f"Glue on a flat base with the edges pushed against a straight, taped fence caul so the four stay flush. Clamp down through a caul every 4 inches, then lightly across. {N['nlong']} logs, {short(N['log_len'])} long."]},
        {"title": "True the logs and cut them in two", "figs": [], "text": [
            f"Scrape the glue, joint one side of each log, and plane the opposite side until the log is as wide as it is tall, within 0.005\". Take a skim only: every pass narrows the bars at that face.",
            f"Crosscut each log into two lengths of {short(N['plank_len'])}: {N['cols']} logs."]},
        {"title": ("Glue the plank in " + ("two halves" if N["groups"] == 2 else f"{N['groups']} parts")) if half else "Glue the plank", "glue": True, "figs": ["plank"], "text": [
            f"Lay the logs side by side and give every other one a quarter turn, so the ends read flat, upright, flat, upright. All the flat ones match each other and all the upright ones match each other; check the end view against the drawing before any glue.",
            (f"Glue {N['per_group']} logs at a time on flat cauls, so each part is {short(N['per_group'] * s)} wide and fits a {plan['shop']['planer_width']:g}\" planer. Plane both faces of each part with the lightest pass that cleans them, to the same thickness."
             if half else "Glue all the logs on flat cauls with cauls above, and plane both faces with the lightest pass that cleans them."),
            "These faces are the glue faces between rows later, so they need to be flat and clean, but each pass also thins the outer bars. Stop as soon as the face is clean."]
            + ([f"Then glue the parts together edge to edge on the same cauls, faces flush, into one plank {short(N['cols'] * s)} wide and {short(N['plank_len'])} long. Scrape the one new glue line flush."] if half else [])},
        {"title": "Crosscut the plank into rows", "figs": ["asm_cut"], "text": [
            f"On the crosscut sled with a stop block, square one end of the plank, then cut {N['nrow']} slices {short(N['cut'])} thick. Each slice is one whole row of the board. {N['rows']} are needed and one is a spare.",
            "Hold the plank down and against the sled fence for every cut and stop when the piece left is too short to hold safely. Number the slices in order and pencil an arrow on the same edge of each."]},
        {"title": "Lay out and glue the board", "glue": True, "figs": ["rows"], "text": [
            "Stand the slices on edge, end grain up, all with the same cut face up. Turn every other slice end for end, flat on the bench. Never flip one over: its other face is the mirror image.",
            "Each tile now sits beside tiles turned the other way, and the bars meet in pinwheels at the tile corners as in the drawing. To match the maker’s board, the flat tiles' bars step up to the right. If yours step down, flip every slice over.",
            f"Glue the rows with their ends flush against a stop, on taped cauls, clamps across the rows every 4 inches and cauls above to keep them level. These are long-grain faces: one coat of glue, normal pressure."]},
        {"title": "Flatten", "figs": [], "see": ["finish"], "text": [
            "Router sled first, then the random-orbit sander: 80 grit to remove the router marks, then 120, 180, 220. Raise the grain with a damp cloth before the last grit.",
            "A drum sander does the same job if you have one. For the planer route, read sheet 07 before trying it."]},
        {"title": "Trim, ease the edges, finish", "figs": [], "text": [
            f"Take {fine(plan['shop']['edge_clean'])} off each end of the rows on the crosscut sled with a backer, just enough to clean them. The other two edges are planed faces and need only sanding. Finished size {short(W)} x {short(Lb)} x {short(T)}.",
            f"{plan['options'].get('edge', '1/8 in. round-over')} on every edge. Flood with mineral oil until it stops soaking in, then board butter." + (" Add four rubber feet." if plan["options"].get("feet", True) else "")]},
    ]
    if fr:
        st.insert(-1, {"title": "Add the end-grain border", "glue": True, "figs": ["frame"], "see": ["finish"], "text": [
            f"Plane a {fr['species'].lower()} board to {short(fr['width'])} thick and crosscut it into blocks {short(N['cut'])} long. Stand the blocks on end so their end grain is up like the field.",
            "Glue blocks along the two long edges first, flush the ends, then across the two short edges. Flatten again lightly."]})
    return st


# ------------------------------------------------------------------------------------- drawings
GLUE = "#2f7fb5"; ORANGE = "#f39a1e"; RED = "#d62f2f"; MDF = "#d8d2c4"; MDF_E = "#8d8676"


def _arrow(S, a, b, raw=True, w=6, hw=13, hl=15):
    (ax, ay), (bx, by) = (a, b) if raw else (S.P(*a), S.P(*b))
    dx, dy = bx - ax, by - ay; d = math.hypot(dx, dy) or 1; ux, uy = dx / d, dy / d; nx, ny = -uy, ux
    pts = [(ax + nx * w, ay + ny * w), (bx - ux * hl + nx * w, by - uy * hl + ny * w), (bx - ux * hl + nx * hw, by - uy * hl + ny * hw), (bx, by),
           (bx - ux * hl - nx * hw, by - uy * hl - ny * hw), (bx - ux * hl - nx * w, by - uy * hl - ny * w), (ax - nx * w, ay - ny * w)]
    for p in pts: S._see(*p)
    S.raw('<polygon points="' + " ".join("%.1f,%.1f" % p for p in pts) + f'" fill="{ORANGE}" stroke="#b86a00" stroke-width="1"/>')


def _chip(S, xy, text, raw=False, r=11):
    x, y = xy if raw else S.P(*xy)
    S._see(x - r, y - r); S._see(x + r, y + r)
    S.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#fff" stroke="#1e2327" stroke-width="1.2"/>'
          f'<text x="{x:.1f}" y="{y + .5:.1f}" font-size="11.5" font-weight="bold" text-anchor="middle" dominant-baseline="middle">{html.escape(text)}</text>')


def drawings(plan):
    import cbplan as CB
    from assembly import Scene
    N = plan["N"]; sp = plan["species"]; u, s = N["u"], N["s"]; cols, rows = N["cols"], N["rows"]
    col = lambda r: sp[r]["end"]; lng = lambda r: sp[r]["long"]
    L, D = sp["light"]["name"].split()[-1].lower(), sp["dark"]["name"].split()[-1].lower()
    out = OrderedDict()
    ft = plan["board"]["field_trim"]; tr = plan["board"]["trim"]

    # face
    S = CB.Svg([tr[0], tr[1], tr[2], tr[3]], 620 / (tr[2] - tr[0]), pad=46, title="Top face")
    for f in plan["face"]: S.poly(f["pts"], fill=col(f["role"]), stroke="#3a2a1c", sw=0.5)
    S.poly([(tr[0], tr[1]), (tr[2], tr[1]), (tr[2], tr[3]), (tr[0], tr[3])], stroke="#1e2327", sw=1.6)
    S.dimx(tr[0], tr[2], tr[1], short(tr[2] - tr[0])); S.dimy(tr[1], tr[3], tr[0], short(tr[3] - tr[1]))
    out["face"] = S.svg()

    # tile
    S = CB.Svg([-0.2 * s, -0.25 * s, 3.2 * s, 1.2 * s], 150 / s * 1.2, pad=34, title="The tile")
    for r, k, p in tile(u): S.poly(p, fill=col(r), stroke="#3a2a1c", sw=0.7)
    for k in range(1, 4): S.line((0, k * u), (s, k * u), stroke=GLUE, sw=1.6)
    S.poly([(0, 0), (s, 0), (s, s), (0, s)], stroke="#1e2327", sw=1.6)
    S.dimx(0, s, 0, short(s)); S.dimy(0, u, 0, short(u))
    for k in range(4): S.text((s + 0.09 * s, (k + .5) * u), f"slab {k + 1}", 10.5, anchor="start")
    S.text((s / 2, s + 0.13 * s), "one tile = the end of a log", 11.5, weight="bold")
    ox = 1.75 * s; h = s * 0.5
    for j in range(2):
        for i in range(2):
            flat = (i + (1 - j)) % 2 == 0
            for r, k, p in tile(u):
                q = p if flat else [(s - y, x) for x, y in p]
                S.poly([(ox + (x + s * i) * 0.5, 0.0 * s + (y + s * j) * 0.5) for x, y in q], fill=col(r), stroke="#3a2a1c", sw=0.4)
            S.poly([(ox + i * h, j * h), (ox + (i + 1) * h, j * h), (ox + (i + 1) * h, (j + 1) * h), (ox + i * h, (j + 1) * h)], stroke="#1e2327", sw=1.2)
    S.text((ox + h, s + 0.13 * s), "every other tile a quarter turn", 11.5, weight="bold")
    out["tile"] = S.svg()

    # blank, end view
    Wb, TB, Tl, Td = N["Wb"], N["TB"], N["Tl"], N["Td"]
    S = CB.Svg([-0.6, -0.5, Wb + 0.6, TB + 0.6], 62, pad=40, title="Two-ply blank, end view")
    S.poly([(0, 0), (Wb, 0), (Wb, Td), (0, Td)], fill=col("dark"), stroke="#1e2327", sw=1)
    S.poly([(0, Td), (Wb, Td), (Wb, TB), (0, TB)], fill=col("light"), stroke="#1e2327", sw=1)
    S.line((0, Td), (Wb, Td), stroke=GLUE, sw=2.2)
    S.dimx(0, Wb, 0, short(Wb)); S.dimy(0, Td, 0, f"{D} {short(Td)}"); S.dimy(Td, TB, Wb, f"{L} {short(Tl)}", left=False)
    S.text((Wb / 2, TB + 0.3), f"two-ply blank, {short(TB)} thick, {short(N['blank_len'])} long: make {N['nblank']}", 11.5, weight="bold")
    out["blank"] = S.svg()

    # the bevel rip: saw from the infeed end, fence on the right
    S = CB.Svg([-1.4, -0.9, Wb + 1.6, TB + 1.5], 62, pad=40, title="Ripping slabs, blade at 45 degrees")
    S.poly([(-1.4, -0.35), (Wb + 1.6, -0.35), (Wb + 1.6, 0), (-1.4, 0)], fill="#c9ccd0", stroke="#5b6167", sw=0.8)
    S.poly([(Wb, 0), (Wb + 1.1, 0), (Wb + 1.1, 2.3), (Wb, 2.3)], fill=MDF, stroke=MDF_E, sw=1); S.text((Wb + 0.55, 1.15), "fence", 10.5, rot=-90)
    kx = N["shop_kerf"] * R2 if "shop_kerf" in N else plan["shop"]["kerf"] * R2
    x0 = TB; xs = [x0 + k * N["stepx"] for k in range(N["per_blank"] + 1)]
    def clipq(xa, xb, y0, y1):       # the part of the blank between two 45 degree planes (through (x, 0) leaning left), between heights y0 and y1
        return [(xa - y0, y0), (xb - y0, y0), (xb - y1, y1), (xa - y1, y1)]
    S.poly([(0, 0), (x0 - kx, 0), (0, Td)] if x0 - kx > Td else [(0, 0), (x0 - kx, 0), (x0 - kx - Td, Td), (0, Td)], fill=col("dark"), stroke="#3a2a1c", sw=0.6, op=0.35)
    S.poly([(0, Td), (x0 - kx - Td, Td), (0, x0 - kx)], fill=col("light"), stroke="#3a2a1c", sw=0.6, op=0.35)
    for k in range(1, N["per_blank"] + 1):
        xa, xb = xs[k - 1], xs[k] - kx
        S.poly(clipq(xa, xb, 0, Td), fill=col("dark"), stroke="#1e2327", sw=0.9); S.poly(clipq(xa, xb, Td, TB), fill=col("light"), stroke="#1e2327", sw=0.9)
        _chip(S, ((xa + xb) / 2 - TB / 2, TB / 2), str(k))
    xa = xs[-1]
    S.poly([(xa, 0), (Wb, 0), (Wb, Td), (xa - Td, Td)], fill=col("dark"), stroke="#1e2327", sw=0.9)
    S.poly([(xa - Td, Td), (Wb, Td), (Wb, TB), (xa - TB, TB)], fill=col("light"), stroke="#1e2327", sw=0.9)
    S.text(((xa + Wb) / 2, Td / 2), "left over", 10.5, fill="#fff", halo=False)
    bx = xs[1]                                                         # the blade drawn at the second cut
    S.poly([(bx + 0.35, -0.35), (bx - kx + 0.35, -0.35), (bx - kx - TB - 0.55, TB + 0.55), (bx - TB - 0.55, TB + 0.55)], fill="#8f969c", stroke="#444", sw=0.8, op=0.85)
    S.text((bx - TB - 0.75, TB + 0.9), "blade at 45°, leaning away from the fence", 11, anchor="middle")
    S.text((TB * 0.3, TB * 0.28), "waste", 10.5, fill="#444")
    S.dimx(xs[-2], xs[-1], 0, f"fence moves {frac(N['stepx'], 32)}\" per slab")
    S.text((Wb / 2, -0.75), f"blank flat on the table, jointed edge on the fence; slabs come off the far side, {N['per_blank']} per blank", 11)
    out["rip"] = S.svg()

    # the slab: as ripped and planed (parallelogram), and the two square rips
    e0 = N["short_l"] - Tl * R2; e1 = N["short_l"] + Td * R2          # the bevelled ends at the bottom face (x - y = e)
    S = CB.Svg([e0 - 0.5, -1.2, e1 + u + 0.6, u + 1.3], 150, pad=40, title="Squaring a slab")
    S.poly([(e0, 0), (N["short_l"], 0), (N["long_l"], u), (e0 + u, u)], fill=col("light"), stroke="#1e2327", sw=1)
    S.poly([(N["short_l"], 0), (e1, 0), (e1 + u, u), (N["long_l"], u)], fill=col("dark"), stroke="#1e2327", sw=1)
    S.poly([(e0, 0), (0, 0), (0, u), (e0 + u, u)], fill="#fff", stroke="none", op=0.55); S.poly([(s, 0), (e1, 0), (e1 + u, u), (s, u)], fill="#fff", stroke="none", op=0.55)
    S.line((N["short_l"], 0), (N["long_l"], u), stroke=GLUE, sw=2)
    for x, lab in ((0, "cut A"), (s, "cut B")):
        S.line((x, -0.28), (x, u + 0.28), stroke=RED, sw=1.8, dash="6 3"); S.text((x, u + 0.42), lab, 11.5, fill=RED, weight="bold")
    S.dimx(0, N["long_l"], u, f"{L} {frac(N['long_l'], 64)}\"", below=False); S.dimx(N["long_l"], s, u, f"{D} {frac(N['short_d'], 64)}\"", below=False)
    S.dimx(0, N["short_l"], 0, f"{L} {frac(N['short_l'], 64)}\""); S.dimx(N["short_l"], s, 0, f"{D} {frac(N['long_d'], 64)}\"")
    S.dimy(0, u, e0, short(u))
    S.text((s / 2, -0.42), f"finished slab {short(s)} wide; the blue glue line crosses it at 45°", 11.5, weight="bold")
    S.text((s / 2, -0.58), f"cut A: sharp {D} corner on the table against the fence, fence {frac(N['fenceA'], 64)}\" ({N['fenceA']:.3f}) from the blade", 10.5)
    out["slab"] = S.svg()

    # log: four slabs stacked against a fence caul
    S = CB.Svg([-1.3, -0.75, s + 1.5, s + 1.25], 120, pad=36, title="Log glue-up, end view")
    S.poly([(-1.3, -0.3), (s + 0.9, -0.3), (s + 0.9, 0), (-1.3, 0)], fill=MDF, stroke=MDF_E, sw=1)
    S.poly([(-0.55, 0), (0, 0), (0, s * 0.8), (-0.55, s * 0.8)], fill=MDF, stroke=MDF_E, sw=1); S.text((-0.28, s * 0.4), "fence caul", 10, rot=-90)
    S.poly([(-0.1, s), (s + 0.1, s), (s + 0.1, s + 0.28), (-0.1, s + 0.28)], fill=MDF, stroke=MDF_E, sw=1)
    for r, k, p in tile(u): S.poly(p, fill=col(r), stroke="#3a2a1c", sw=0.7)
    for k in range(1, 4): S.line((0, k * u), (s, k * u), stroke=GLUE, sw=2.4)
    for k in range(4):
        _chip(S, (s + 0.3, (k + .5) * u), str(k + 1))
        if k % 2: S.text((s + 0.5, (k + .5) * u), "rolled over", 10.5, anchor="start")
    ax, ay = S.P(s / 2, s + 0.28); _arrow(S, (ax, ay - 62), (ax, ay - 4))
    ax, ay = S.P(s, s * 0.5); _arrow(S, (ax + 150, ay + 70), (ax + 100, ay + 70), w=4, hw=9, hl=11)
    S.text((s / 2, -0.55), f"log {short(s)} square: light left, right, left, right", 11.5, weight="bold")
    out["log"] = S.svg()

    # plank, end view
    S = CB.Svg([-0.4, -1.1, cols * s + 0.4, s + 1.0], 640 / (cols * s), pad=34, title="Plank, end view")
    for i in range(cols):
        flat = i % 2 == 0
        for r, k, p in tile(u):
            q = p if flat else [(s - y, x) for x, y in p]
            S.poly([(x + s * i, y) for x, y in q], fill=col(r), stroke="#3a2a1c", sw=0.5)
        S.poly([(s * i, 0), (s * (i + 1), 0), (s * (i + 1), s), (s * i, s)], stroke="#1e2327", sw=1.3)
        S.text((s * (i + .5), s + 0.3), "flat" if flat else "¼ turn", 10.5)
    for i in range(1, cols):
        S.line((s * i, 0), (s * i, s), stroke=GLUE, sw=3.0 if i % N["per_group"] == 0 and N["groups"] > 1 else 1.8)
    S.dimx(0, cols * s, 0, short(cols * s)); S.dimy(0, s, 0, short(s))
    if N["groups"] > 1:
        for gk in range(N["groups"]):
            xa, xb = gk * N["per_group"] * s, (gk + 1) * N["per_group"] * s
            S.text(((xa + xb) / 2, s + 0.7), f"part {gk + 1}: glue and plane these {N['per_group']} first", 11, weight="bold")
    out["plank"] = S.svg()

    # rows
    S = CB.Svg([ft[0] - 1.6, ft[1], ft[2] + 1.9, ft[3]], 560 / (ft[2] - ft[0]), pad=40, title="Rows")
    for p in plan["polygons"]: S.poly(p["pts"], fill=col(p["role"]), stroke="#3a2a1c", sw=0.35)
    for j in range(rows + 1): S.line((0, j * s), (cols * s, j * s), stroke=GLUE if 0 < j < rows else "#1e2327", sw=2.4 if 0 < j < rows else 1.4)
    S.line((0, 0), (0, rows * s), stroke="#1e2327", sw=1.4); S.line((cols * s, 0), (cols * s, rows * s), stroke="#1e2327", sw=1.4)
    for j in range(rows):
        n = rows - j; turned = (rows - 1 - j) % 2 == 1
        S.text((-0.25, (j + .5) * s), f"R{n}", 12, anchor="end", weight="bold", fill="#6b4630")
        S.text((cols * s + 0.25, (j + .5) * s), "turned end for end" if turned else "as cut", 10.5, anchor="start")
        ax, ay = S.P(s * 0.5 if not turned else cols * s - s * 0.5, (j + .5) * s)
        S.raw(f'<path d="M{ax - 12:.1f},{ay:.1f} l24,0 m-8,-6 l8,6 l-8,6" fill="none" stroke="#fff" stroke-width="4" transform="rotate({180 if turned else 0} {ax:.1f} {ay:.1f})"/>'
              f'<path d="M{ax - 12:.1f},{ay:.1f} l24,0 m-8,-6 l8,6 l-8,6" fill="none" stroke="{RED}" stroke-width="2" transform="rotate({180 if turned else 0} {ax:.1f} {ay:.1f})"/>')
    ax, ay = S.P(cols * s / 2, rows * s); _arrow(S, (ax, ay - 60), (ax, ay - 6))
    ax, ay = S.P(cols * s / 2, 0); _arrow(S, (ax, ay + 60), (ax, ay + 6))
    S.text((cols * s / 2, -0.0), "", 1)
    out["rows"] = S.svg()

    if plan["board"]["frame"]:
        fr = plan["board"]["frame"]; o = fr["outer"]
        S = CB.Svg(o, 560 / (o[2] - o[0]), pad=40, title="Optional border")
        for f in plan["face"]: S.poly(f["pts"], fill=col(f["role"]), stroke="#3a2a1c", sw=0.4)
        for a, b, c, d in fr["pieces"]: S.poly([(a, b), (c, b), (c, d), (a, d)], stroke=GLUE, sw=2)
        S.dimx(o[0], o[2], o[1], short(o[2] - o[0])); S.dimy(o[1], o[3], o[0], short(o[3] - o[1]))
        out["frame"] = S.svg()

    # ------------------------------------------------------------------ 3D
    along = lambda ox=0.0, oy=0.0, oz=0.0: (lambda a, b, w: (ox + w, oy + a, oz + b))
    # blank: light ply above dark ply
    sc = Scene(az=40, el=28); Lg = 9.0; gap = 0.9
    sc.prism([(0, 0), (Wb, 0), (Wb, Td), (0, Td)], Lg, along(), col("dark"), lng("dark"), glue={2})
    sc.prism([(0, 0), (Wb, 0), (Wb, Tl), (0, Tl)], Lg, along(oz=Td + gap), col("light"), lng("light"))
    sc.mark("arrow", (Lg / 2, Wb / 2, Td + gap + Tl + 1.6), (Lg / 2, Wb / 2, Td + gap + Tl + 0.2))
    sc.mark("grain", (0.8, -1.0, 0), (Lg - 0.8, -1.0, 0))
    out["asm_blank"] = sc.svg(title="Two-ply blank")
    # log: four squared slabs
    sc = Scene(az=40, el=26); Lg = 6.0; gap = 0.55
    for r, k, p in tile(u):
        q = CB.ccw([(x, y + k * gap) for x, y in p])
        top = {i for i in range(len(q)) if k < 3 and abs(q[i][1] - ((k + 1) * u + k * gap)) < 1e-6 and abs(q[(i + 1) % len(q)][1] - ((k + 1) * u + k * gap)) < 1e-6}
        sc.prism(q, Lg, along(), col(r), lng(r), glue=top)
    for k in range(4): sc.mark("label", (Lg, s, (k + .5) * u + k * gap), str(k + 1), (40, 0))
    sc.mark("arrow", (Lg / 2, s / 2, 4 * u + 3 * gap + 1.4), (Lg / 2, s / 2, 4 * u + 3 * gap + 0.15))
    sc.mark("grain", (0.6, -0.9, 0), (Lg - 0.6, -0.9, 0))
    out["asm_log"] = sc.svg(title="Four slabs make a log")
    # crosscut
    sc = Scene(az=58, el=26); body = 5.0; cut = N["cut"]; gp = 0.6
    def plank_at(x0, ln):
        for i in range(cols):
            flat = i % 2 == 0
            for r, k, p in tile(u):
                q = p if flat else [(s - y, x) for x, y in p]
                sc.prism(CB.ccw([(x + s * i, y) for x, y in q]), ln, along(ox=x0), col(r), lng(r))
    plank_at(0, body)
    for k in range(2): plank_at(body + gp + k * (cut + gp), cut)
    sc.mark("line", (body + gp / 2, -0.6, 0), (body + gp / 2, cols * s + 0.6, 0), RED)
    sc.mark("text", (body + gp / 2, -0.6, 0), "red: the saw cut", (-40, 22))
    sc.mark("text", (body + gp + cut, 0, s + 0.5), f"each slice is one row, {short(cut)} thick", (-250, -34))
    out["asm_cut"] = sc.svg(width=820, title="Crosscutting the plank into rows")
    return out


# ------------------------------------------------------------------------------------- page
def page(plan, svgs, photo, guide=None):
    from plan_page import CSS, TICK
    e = html.escape; N = plan["N"]; sp = plan["species"]; sh = plan["shop"]
    W, Lb, T = plan["board"]["width"], plan["board"]["length"], plan["board"]["thickness"]
    L, D = sp["light"]["name"].split()[-1].lower(), sp["dark"]["name"].split()[-1].lower()
    u, s = N["u"], N["s"]; bf = sum(x["bf_buy"] for x in plan["stock"])
    errors = [c for c in plan["checks"] if not c["ok"] and c["level"] != "warn"]; warns = [c for c in plan["checks"] if not c["ok"] and c["level"] == "warn"]
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
    chain = "".join(f'<span><b>{n}</b>{e(x)}</span>' for n, x in enumerate(["two-ply blanks", "45° slabs", "square logs", "one plank", "rows", "board"], 1))
    stats = "".join(f'<div class="stat"><b class="mono">{b}</b><small>{e(t)}</small></div>' for b, t in (
        (e(size.replace('"', "")) + '"', "W × L × T, finished"), ("1", "tile, turned a quarter turn in a checkerboard"), (str(N["nslab"]), f"slabs, all the same, from {N['nblank']} blanks"),
        (str(N["rows"]), "rows, crosscut from one plank"), (f"{bf:g}", "board feet to buy")))
    sheets = [("overview", "Overview", size), ("materials", "Material list", f"{bf:g} bd ft"), ("pattern", "The pattern", "1 tile"), ("slabs", "Blanks & slabs", f"{N['nslab']} slabs"),
              ("plank", "Logs, plank & rows", f"{N['rows']} rows"), ("build", "Building it", f"{len(plan['steps'])} steps"), ("finish", "Flattening & border", "options"), ("sources", "Sources", "what is shown, what is mine")]
    index = "".join(f'<a href="#{i}"><span class="n">{n:02d}</span><span class="t">{e(t)}</span><span class="s">{e(x)}</span></a>' for n, (i, t, x) in enumerate(sheets, 1))
    index += (f'<a href="#checks"><span class="n">R</span><span class="t">Checks</span><span class="s" style="color:var(--{"weak" if errors else "good"})">'
              f'{"✗ " + str(len(errors)) + " fail" if errors else "all pass ✓" if not warns else str(len(plan["checks"]) - len(warns)) + " pass · " + str(len(warns)) + " note"}</span></a>')
    no = {i: f"{n:02d}" for n, (i, _, _) in enumerate(sheets, 1)}
    H = []

    # 01
    if photo and os.path.exists(photo):
        mime = "image/png" if photo.lower().endswith(".png") else "image/jpeg"
        hero = fig(f'<img src="data:{mime};base64,{base64.b64encode(open(photo, "rb").read()).decode()}" alt="Render of the finished board">', "Render", "<span>made from the exact face with plan-to-photo</span>")
    elif guide and os.path.exists(guide):
        from PIL import Image
        import io
        im = Image.open(guide).convert("RGB"); im.thumbnail((1500, 1500)); buf = io.BytesIO(); im.save(buf, "JPEG", quality=86)
        hero = fig(f'<img src="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}" alt="Model of the finished board">', "Model view", "<span>the exact face, colour coded by wood; not a photo</span>")
        photo = guide
    else:
        hero = fig(svgs["face"], "Top face · finished size")
    how = [f"The whole board is one square tile, {short(s)} on a side: two {L} bars {short(u)} wide in a {D} ground, each stepping up one bar width through a 45 degree jog. Every other tile is turned a quarter turn. The maze, and the look of bars passing over and under, come from that alone.",
           f"The tile is the end of a log made of four identical slabs. A slab is {short(u)} thick with the {L} and {D} meeting on a 45 degree line, and it is ripped off a two-ply blank with the blade tilted to 45 degrees.",
           "Nothing is assembled from small pieces. Blanks, slabs, logs and the plank are all long, flat-sided and planed between glue-ups; the rows are crosscut from the finished plank.",
           "The base board has no border: the pattern runs to the edge. The dark border on the maker’s board is an option on sheet 07."]
    glance = "".join(f"<dt>{e(k)}</dt><dd class='m'>{e(v)}</dd>" for k, v in (
        ("Blanks", f"{N['nblank']}, each {L} {short(N['Tl'])} on {D} {short(N['Td'])}"), ("Slabs", f"{N['nslab']} + {N['spare_slabs']} spare, {short(s)} × {short(u)} after squaring"),
        ("Logs", f"{N['nlong']} at {short(N['log_len'])}, cut into {N['cols']} at {short(N['plank_len'])}"), ("Plank", f"{short(N['cols'] * s)} × {short(s)} × {short(N['plank_len'])}"),
        ("Rows", f"{N['rows']} + {sh['spare_rows']} spare, cut {short(N['cut'])} thick"), ("Glue-ups", f"{nglue}, every one with flat faces and square edges")))
    woods = "".join(f'<li><span class="sw" style="background:{sp[x["role"]]["end"]}"></span>{e(x["species"])}: {x["bf_buy"]:g} bd ft</li>' for x in plan["stock"])
    tools = ["Table saw with a riving knife, digital angle gauge (one bevel setting: 45°), featherboard, push blocks", "Jointer and planer: every part before the final board is long grain and flat-sided",
             "Crosscut sled with a stop block and hold-down", "Calipers and a straightedge", "Flat cauls, a straight fence caul, bar clamps, Titebond III",
             "Router sled to flatten the board, random-orbit sander", "Mineral oil and board butter"]
    H.append(f'<article class="sheet" id="overview">{tb("01", "Overview", e(desc[0].upper() + desc[1:]) if desc else "", f"<div class=dims>{e(size)}</div>{stamp}")}'
             f'<div class="main">{hero}<div class="notes" style="padding:0;display:grid;gap:0;align-content:start">{fig(svgs["face"], "Top face · finished size") if photo and os.path.exists(photo) else fig(svgs["tile"], "The tile")}'
             f'<div class="notes"><h3>How it goes together</h3>{ul(how)}<h3>At a glance</h3><dl class="kv">{glance}</dl></div></div></div>'
             f'<div class="lower" style="grid-template-columns:1fr 1.65fr"><div class="notes"><h3>Wood to buy</h3><ul>{woods}</ul></div>'
             f'<div class="notes"><h3>Tools</h3><ul style="display:block;columns:2 30ch;column-gap:32px">{"".join(f"<li>{e(t)}</li>" for t in tools)}</ul></div></div></article>')

    # 02
    trs = ""
    for x in plan["stock"]:
        trs += (f'<tr class="grp"><td colspan="4"><span class="sw" style="background:{sp[x["role"]]["end"]}"></span>{e(x["species"])} · buy {x["bf_buy"]:g} bd ft</td></tr>'
                f'<tr><td class="m">{e(x["rough"])}</td><td class="q">{x["n"]}</td><td class="m">{e(x["size"])}</td><td class="m">one ply of each blank</td></tr>')
    wl = "".join(f'<li><span class="sw" style="background:{w["end"]}"></span><b>{e(w["name"])}</b>' + (f' · Janka {w["janka"]} · shrinkage {w["tan"]}%' if w["janka"] else "") + f'. {e(w["note"])}</li>' for w in plan["woods"])
    H.append(f'<article class="sheet" id="materials">{tb("02", "Material list", "Two woods, one board of each per blank", "<div class=dims>T × W × L</div>")}'
             f'<div class="lower full" style="border-top:0"><div class="panel"><div class="tbl"><table class="d"><tr><th>Rough stock</th><th style="text-align:right;padding-right:12px">Boards</th><th>Milled size</th><th>Use</th></tr>{trs}</table></div>'
             f'<p class="small">Board feet include 25% for defects and milling. Each blank gives {N["per_blank"]} slabs; the first cut wastes a triangle and the last {short(sh["blank_bearing"])} is left to keep the blank flat on the saw, so about half of each blank ends up in the board. '
             f'{short(N["Td"])} from 4/4 stock needs boards that arrive a full inch thick and flat; otherwise buy 5/4. Narrower boards can be edge-glued to {short(N["Wb"])} first.</p></div></div>'
             f'<div class="lower full"><div class="notes"><h3>The woods</h3><ul>{wl}</ul>'
             f'<p class="small">The maker says only that the board is two woods. From the photos the dark one is walnut and the light one looks like ash (strong ring lines); that is my reading, not the maker’s statement. Ash end grain has open pores, so this plan uses hard maple by default. With ash the bars show more of the light and shade seen in the video.</p></div></div></article>')

    # 03
    H.append(f'<article class="sheet" id="pattern">{tb("03", "The pattern", "Worked out from the maker’s photos, then checked against them", f"<div class=dims>tile {short(s)} · bar {short(u)}</div>")}'
             f'<div class="main">{fig(svgs["tile"], "The tile and how it repeats")}<div class="panel"><h3>What the photos show</h3>{ul([
                 "Bars run only along the two edges of the board and step sideways on 45 degree jogs. (At phone resolution the jogs read as 60 degrees; in the full-size stills they measure 45.)",
                 "Glue lines every four bar widths, both ways, mark square tiles. Every tile holds the same two stepped bars; every other tile is turned a quarter turn.",
                 f"The maker’s field is 8 tiles by 4 inside a dark border. This plan keeps the 8 tiles across and uses {N['rows']} rows to make a {short(N['cols'] * s)} × {short(N['rows'] * s)} board with no border.",
                 "Check: the model on this sheet, drawn 8 × 4 and laid over a squared-up still of the finished board, agrees with it on 90% of pixels; the rest is along bar edges, from lens distortion and wood figure.",
                 "The depth in the video comes from end-grain figure: turning a tile a quarter turn turns its growth rings too, so neighbouring bars catch the light differently."])}'
             f'<h3>Sizes</h3><dl class="kv"><dt>Bar</dt><dd class="m">{short(u)} wide, straight and in the jog</dd><dt>Step</dt><dd class="m">one bar width, over a 45° jog</dd><dt>Tile</dt><dd class="m">{short(s)} square, four slabs of {short(u)}</dd>'
             f'<dt>Board</dt><dd class="m">{N["cols"]} × {N["rows"]} tiles</dd></dl></div></div></article>')

    # 04
    H.append(f'<article class="sheet" id="slabs">{tb("04", "Blanks & slabs", "One blank, one saw tilt, one slab: every piece of the pattern comes from these", f"<div class=dims>{N["nblank"]} blanks · {N["nslab"]} slabs + {N["spare_slabs"]} spare</div>")}'
             f'<div class="jgrid" style="grid-template-columns:1fr">'
             f'<div class="joint"><div class="jh"><span class="jn">A</span><div><h4>The two-ply blank</h4><div class="jsub">{L} {short(N["Tl"])} glued face to face on {D} {short(N["Td"])}</div></div></div><div class="ph">{svgs["blank"]}</div></div>'
             f'<div class="joint"><div class="jh"><span class="jn">B</span><div><h4>Rip the slabs</h4><div class="jsub">blade 45° from vertical, blank flat on the table against the fence</div></div></div><div class="ph">{svgs["rip"]}</div>'
             f'<p class="small">Seen from the infeed end. The blank stays between the blade and the fence and each slab falls away on the far side, under the lean of the blade, where nothing traps it. The glue line of the blank becomes the 45 degree line in every slab.</p></div>'
             f'<div class="joint"><div class="jh"><span class="jn">C</span><div><h4>Plane, then rip each slab square</h4><div class="jsub">blade at 90°; two rips per slab</div></div></div><div class="ph">{svgs["slab"]}</div>'
             f'<p class="small">The pale ends are the bevels that come off. The four sizes on the drawing are what to measure on the test slab: if the {L} measures long on both faces, move the fence toward the blade by the difference.</p></div></div></article>')

    # 05
    rowtab = "".join(f'<tr><td class="m" style="color:var(--accent-ink)">R{r["n"]}</td><td class="m">{"turned end for end" if r["turned"] else "as cut"}</td></tr>' for r in sorted(plan["rows"], key=lambda r: r["n"]))
    H.append(f'<article class="sheet" id="plank">{tb("05", "Logs, plank & rows", "End views: blue lines are glue, orange is clamp pressure", f"<div class=dims>{N["cols"]} logs · 1 plank · {N["rows"]} rows</div>")}'
             f'<div class="main">{fig(svgs["log"], "The log: four slabs on a flat base against a fence caul")}<div class="panel"><h3>The log</h3>{ul([
                 f"Slabs 2 and 4 are rolled over along their length, so the {L} swaps sides and the glue lines still lean the same way.",
                 f"Make {N['nlong']} logs {short(N['log_len'])} long, true them square, and cut each in two: {N['cols']} logs of {short(N['plank_len'])}."])}</div></div>'
             f'<div class="lower full">{fig(svgs["plank"], "The plank, end view: this is also what one row looks like from above")}</div>'
             f'<div class="main" style="border-top:1px solid var(--rule)">{fig(svgs["rows"], "The board from above: rows crosscut from the plank, red arrows are your pencil arrows")}<div class="panel"><h3>Rows</h3>'
             f'<div class="tbl"><table class="d">{rowtab}</table></div>{ul(["Every row is the same slice of the plank.", "Turned means end for end, flat on the bench, same face up. Never flipped over."])}</div></div></article>')

    # 06
    import re
    def runin(t):
        m_ = re.match(r"^([A-Z][A-Za-z' -]{2,26}): ", t)
        return f"<b>{e(m_.group(1))}.</b> {e(t[m_.end():][:1].upper() + t[m_.end():][1:])}" if m_ else e(t)
    body = ""; ng = 0
    for n, x in enumerate(plan["steps"], 1):
        kick = ""
        if x.get("glue"):
            ng += 1; kick = f'<span class="kick">GLUE-UP {ng}</span><br>'
        refs = [no[d] for d in x.get("see", []) if d in no]
        see = f'<div class="see">See sheet {", ".join(refs)}</div>' if refs else ""
        dont = f'<div class="dont"><b>DON\'T</b>{e(x["dont"])}</div>' if x.get("dont") else ""
        b = f'{kick}<h4>{e(x["title"])}</h4><ul>{"".join(f"<li>{runin(t)}</li>" for t in x["text"])}</ul>{see}'
        figs = [f for f in x.get("figs", []) if f in svgs]
        if figs: b = f'<div class="stepgrid"><div>{b}</div><div class="asm">{"".join(f"<figure{' class=wide' if f in ('rip', 'plank', 'asm_plank', 'asm_cut', 'slab') else ''}>{svgs[f]}</figure>" for f in figs)}</div></div>'
        body += f'<li><span class="sn">{n}</span><div>{b}</div>{dont}</li>'
    H.append(f'<article class="sheet" id="build">{tb("06", "Building it", "In order, with the reason where it isn\'t obvious", f"<div class=dims>{len(plan["steps"])} steps · {nglue} glue-ups</div>")}'
             f'<div class="stepbox"><ol class="steps">{body}</ol></div></article>')

    # 07
    fwid = 2.5 * u; fo = (W + 2 * fwid, Lb + 2 * fwid) if not plan["board"]["frame"] else (W, Lb)
    H.append(f'<article class="sheet" id="finish">{tb("07", "Flattening & border", "Two ways to flatten without a drum sander, and the maker\'s dark border as an add-on", "<div class=dims>options</div>")}'
             f'<div class="lower" style="border-top:0;grid-template-columns:1fr 1fr 1fr">'
             f'<div class="panel"><h3>Route 1 · router sled and sander</h3>{ul(["Board on a flat base, shimmed so it cannot rock, between two straight rails; a wide straight or bowl bit in a router on a bridge.", "Passes of 1/32 in. or less, the full face, then the other face.", "Sand out the router marks from 80 grit. This is the route the plan assumes and the one every source agrees on."])}</div>'
             f'<div class="panel"><h3>Route 2 · helical-head planer</h3>{ul(["Up to here the planer has done everything, because every part was long grain. The finished board is end grain, and a planer can tear the trailing edge out or throw the board.", "If you use it anyway, follow George Vondriska's method (sheet 08): glue sacrificial long-grain rails to the leading and trailing edges or put a heavy chamfer on the trailing edge, take 1/64 in. or less a pass, sharp inserts, and stand out of line.", "This plan has not tested it and does not need it. With the optional border on, the border is the sacrificial edge: plane before the final trim."])}</div>'
             f'<div class="panel"><h3>Optional · the dark border</h3>{ul([f"The maker’s board has a plain {D} border about two and a half bar widths wide: {short(fwid)} here, for a finished board of {short(fo[0])} × {short(fo[1])}.", f"Make it end grain like the field: a {D} board planed to {short(fwid)}, crosscut into blocks {short(N['cut'])} long, stood on end and glued along the long edges first, then the ends.", "Never a long-grain frame: the field moves across its width with the seasons and a long-grain frame does not, so one of them cracks.", "To add it to this plan, put \"frame\": {\"width\": " + f"{fwid:g}" + ", \"species\": \"" + sp["dark"]["key"] + "\"} in design.json and rebuild."])}</div></div>'
             + (f'<div class="lower full">{fig(svgs["frame"], "With the border")}</div>' if "frame" in svgs else "") + '</article>')

    # 08
    src = "".join(f'<li><a href="{e(url)}">{e(t)}</a><br><span class="small">{e(n)}</span></li>' for t, url, n in SOURCES)
    H.append(f'<article class="sheet" id="sources">{tb("08", "Sources", "What the maker shows, and what in this plan is worked out rather than shown", "<div class=dims>read 2026-11-14</div>")}'
             f'<div class="lower" style="border-top:0;grid-template-columns:1fr 1fr">'
             f'<div class="panel"><h3>Shown by the maker</h3>{ul(["The finished face: taken from the maker’s stills and matched by the model on sheet 03.", "Two woods only.", "Boards and strips laminated face to face into a thick blank.", "A laminated blank ripped on the table saw with the blade tilted.", "Two-tone strips with bevelled edges going through the planer.", "A final glue-up of square end-grain blocks with a border of dark blocks round them."])}'
             f'<h3>Shown by other makers</h3>{ul(["Laminate, saw into strips at an angle, plane, re-glue, crosscut the plank into rows: MTM Wood and Bob Chambers.", "Rows crosscut from a glued plank and every other row turned: any checkerboard end-grain board."])}</div>'
             f'<div class="panel"><h3>Worked out for this plan, not shown</h3>{ul(["I could not play either video here, only read their titles and the still frames YouTube publishes for them. The order of the maker’s steps between those stills is not known to me.",
                 f"The two-ply blank and its thicknesses ({short(N['Tl'])} and {short(N['Td'])}), the 45 degree slab, and the four-slab log are my reconstruction. They reproduce the face exactly on paper and use the operations the maker’s stills show, but the maker’s own laminate may have more layers or a different order.",
                 "Squaring each slab with its sharp corner against the fence (step 5) is my method. Prove the fence setting on the spare slabs before cutting the rest.",
                 "Gluing whole logs into one plank and crosscutting rows from it is the standard plank method, applied here; in the last still the maker appears to glue loose blocks instead.",
                 "The helical-planer route for the finished board is Vondriska's, untested on this board.", "Nobody has built this plan yet."])}</div></div>'
             f'<div class="lower full"><div class="notes"><h3>Links</h3><ul>{src}</ul></div></div></article>')

    chk = "".join(f'<tr><td>{e(c["what"])}' + (f'<span class="sub">{e(c["detail"])}</span>' if c["detail"] else "") + '</td>'
                  f'<td class="{"pass" if c["ok"] else c["level"] if c["level"] == "warn" else "fail"}">{"PASS" if c["ok"] else ("WARN" if c["level"] == "warn" else "FAIL")}</td></tr>' for c in plan["checks"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(plan["name"])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@112,600;112,700&family=IBM+Plex+Mono:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{CSS}</style></head><body><div class="wrap">
<header class="hero"><div class="eyebrow">End-grain cutting board · shop plan</div>
<h1>{h1}</h1><p class="lede">{lede}</p><div class="chain" aria-label="Build order">{chain}</div><div class="stats">{stats}</div></header>
<nav class="index" aria-label="Sheets">{index}</nav>
<main>{"".join(H)}</main>
<article class="sheet" id="checks">{tb("R", "Checks", "Recomputed from the board's geometry every time the plan is built", stamp)}
<div class="lower full" style="border-top:0"><div class="panel"><table class="cost">{chk}</table></div></div></article>
<footer>Kerf {short(sh["kerf"])}; slabs ripped {short(sh["slab_over"])} over and planed to size; rows cut {short(N["cut"])}; {short(sh["end_trim"])} to square the first end of the plank and {short(sh["hold_end"])} held at the other. Change these under "shop" in design.json and rebuild.</footer>
</div></body></html>"""
