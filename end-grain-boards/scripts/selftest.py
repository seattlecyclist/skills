#!/usr/bin/env python3
"""The checks must pass every example and catch known breaks.

  python3 scripts/selftest.py
"""
import copy, json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cbplan

EX = os.path.join(HERE, "..", "examples")
fails = 0


def run(design):
    with tempfile.TemporaryDirectory() as out:
        try:
            plan = cbplan.build(design, out)
        except SystemExit as e:
            return None, str(e)
        return plan, [c["what"] for c in plan["checks"] if not c["ok"] and c["level"] != "warn"]


def expect(name, ok):
    global fails
    print(("ok   " if ok else "FAIL ") + name)
    fails += not ok


for d in sorted(os.listdir(EX)):
    f = os.path.join(EX, d, "design.json")
    if os.path.exists(f):
        plan, errs = run(json.load(open(f)))
        expect(f"example {d} passes every check", plan is not None and not errs)

sq = lambda x, y, s=1: [[x, y], [x + s, y], [x + s, y + s], [x, y + s]]
base = {"pattern": "custom", "board": {"width": 2, "length": 1, "thickness": 1.5},
        "species": {"a": "maple", "b": "walnut"}, "trim": [0, 0, 2, 1],
        "polygons": [{"pts": sq(0, 0), "role": "a", "slice": "r0"}, {"pts": sq(1, 0), "role": "b", "slice": "r0"}]}
plan, errs = run(base)
expect("two squares pass", not errs)

d = copy.deepcopy(base); d["polygons"][1]["pts"] = sq(0.9, 0)
plan, errs = run(d); expect("overlap is caught", errs and any("overlap" in e for e in errs))

d = copy.deepcopy(base); d["polygons"][1]["pts"] = sq(1.1, 0, 0.9)
plan, errs = run(d); expect("gap is caught", errs and any("gaps" in e for e in errs))

d = copy.deepcopy(base)   # 30-degree rhombus needs a 60-degree tilt
import math
c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
d["polygons"] = [{"pts": [[0, 0], [1, 0], [1 + c, s], [c, s]], "role": "a", "slice": "r0"}]
d["trim"] = [c, 0, 1, s]
plan, errs = run(d); expect("bevel past 45 degrees is caught", errs and any("45" in e or "cut" in e for e in errs))

d = copy.deepcopy(base); d["polygons"][0]["pts"] = [[0, 0], [1, 0], [0.5, 0.3], [1, 1], [0, 1]]
plan, errs = run(d); expect("concave bar is caught", errs and any("convex" in e for e in errs))

d = copy.deepcopy(base); d["species"]["b"] = "red oak"
plan, errs = run(d); expect("red oak is refused", plan is None and "not a cutting-board species" in errs)

d = json.load(open(os.path.join(EX, "checkerboard", "design.json")))
plan, _ = run(d)
expect("checkerboard rows come from one log (every other row turned)",
       len(plan["logs"]) == 1 and {s["xf"] for s in plan["slices"]} == {"id", "r180"})
d = json.load(open(os.path.join(EX, "lemoyne-stars", "design.json")))
plan, _ = run(d)
expect("LeMoyne quarters are one unit type", len(plan["units"]) == 1 and len(plan["bar_types"]) == 3)

print("all good" if not fails else f"{fails} failed")
sys.exit(1 if fails else 0)
