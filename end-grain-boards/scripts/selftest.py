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
expect("checkerboard: odd by odd, two strip panels taking turns, no slice turned, ends not trimmed",
       len(plan["logs"]) == 2 and {pk["flip"] for r in plan["rows"] for pk in r["pucks"]} == {False} and len(plan["rows"]) % 2 == 1
       and plan["face"][0]["role"] == plan["face"][-1]["role"] and plan["board"]["margins"][2] < 1e-6 and plan["board"]["margins"][3] < 1e-6)
d = json.load(open(os.path.join(EX, "tumbling-blocks", "design.json")))
plan, errs = run(d)
sw = [l for l in plan["logs"] if l["shape"] == "sandwich"]; bk = [l for l in plan["logs"] if l["shape"] == "sbar"]
expect("tumbling blocks build from rectangles by default: two three-layer sandwiches ripped at 30 degrees, two bar kinds, one plank, no triangle",
       not errs and plan["info"]["kind"] == "bars" and len(sw) == 2 and len(bk) == 2 and all(len(l["stack"]) == 3 and l["tilt"] == 30 for l in sw)
       and len(plan["planks"]) == 1 and all(l["kind"] == "rect" for l in plan["logs"]) and all(bt["kind"] == "board" for bt in plan["bar_types"]))
expect("the lid : face : lid sandwich is 1 : 2 : 1 before the allowance, and the bar is 0.866 x 1.5 diamond sides",
       abs(bk[0]["layers"][1][3] - bk[0]["layers"][1][2] - 1.5 * math.sqrt(3) / 2) < 1e-3 and abs(bk[0]["w"] - 1.5 * math.sqrt(3) / 2) < 1e-3 and abs(bk[0]["h"] - 2.25) < 1e-3
       and abs((bk[0]["layers"][1][3] - bk[0]["layers"][1][2]) / (bk[0]["layers"][0][3] - bk[0]["layers"][0][2]) - 2) < 1e-3)
expect("the face rebuilt from the sandwiches is checked against the pattern", any(c["ok"] and "rebuilt from the sandwiches" in c["what"] for c in plan["checks"]))
import bars as BR
wood = lambda r: plan["species"][r]["key"]
n0, tot0, bad0 = BR.verify(plan["rows"], plan["polygons"], wood, plan["board"]["trim"])
rows2 = copy.deepcopy(plan["rows"]); pk = rows2[3]["pucks"][4]; pk["cells"] = [("left" if r == "right" else "right" if r == "left" else r, q) for r, q in pk["cells"]]
expect("the proof passes on the real bars and catches one bar made from the wrong sandwich", bad0 < 1e-3 and BR.verify(rows2, plan["polygons"], wood, plan["board"]["trim"])[2] > 0.5)
d = dict(d, build="logs"); plan, _ = run(d)
expect("tumbling blocks, build logs: one hexagon log of three diamond bars, no triangle bar, half pucks on both long sides",
       len(plan["logs"]) == 1 and plan["logs"][0]["shape"] == "hex" and len(plan["bar_types"]) == 1 and "triangle" not in plan["bar_types"][0]["kind"]
       and {pk.get("half") for r in plan["rows"] for pk in r["pucks"]} == {None, "left", "right"})
t = copy.deepcopy(d); t["params"] = {"side": 1.0, "build": "triangle"}; plan, errs = run(t)
expect("tumbling blocks, build triangle: one triangle log, two bar shapes, no glue-up over four parts",
       not errs and len(plan["logs"]) == 1 and len(plan["bar_types"]) == 2 and max(len(s["parts"]) for s in plan["logs"][0]["stages"]) <= 4)
d["params"] = dict(d["params"], side=1.75); plan, errs = run(d)
expect("a log too tall for the saw is caught", errs and any("fits under the saw" in e for e in errs))
big = dict(d, build="bars"); plan, errs = run(big)
expect("a sandwich too thick for the tilted blade is never planned: larger cubes get shorter bars",
       not errs and plan["info"]["kind"] == "bars" and all(l["h"] <= 3.125 * math.cos(math.radians(30)) for l in plan["logs"] if l["shape"] == "sandwich"))
d = json.load(open(os.path.join(EX, "lemoyne-stars", "design.json")))
plan, _ = run(d)
expect("LeMoyne: bands, quarter, half and block logs plus a border bar; only the block and the border are sliced",
       [l["shape"] for l in plan["logs"]] == ["band", "band", "quarter", "half", "block", "border"] and [l["id"] for l in plan["logs"] if l["crosscut"]] == ["E", "F"])
expect("the trimmed board is inside the slices with waste on every edge", min(plan["board"]["margins"]) >= 0.12)
d = json.load(open(os.path.join(EX, "kagome-stars", "design.json")))
plan, _ = run(d)
expect("base designs carry no frame", all("frame" not in json.load(open(os.path.join(EX, n, "design.json"))) for n in os.listdir(EX)) and not plan["board"].get("frame"))
d["frame"] = {"width": 0.75, "species": "walnut", "liner": {"width": 0.375, "species": "cherry"}}; plan, errs = run(d)
expect("a frame is added when the design asks for one", plan is not None and bool(plan["board"].get("frame")))
plan, errs = run({"pattern": "rosettes", "params": {"side": 0.75}, "board": {"width": 12, "length": 16, "thickness": 1.5},
                  "species": {"hex": "purpleheart", "square": "maple", "tri": "walnut"}})
expect("rosettes are refused with pinwheel offered", plan is None and "pinwheel" in errs)

plan, _ = run(dict(json.load(open(os.path.join(EX, "pinwheel-chevrons", "design.json"))), build="logs"))
expect("a repeating lattice is one plank, every row a crosscut of it", len(plan["planks"]) == 1 and plan["planks"][0]["rows_cut"] == len(plan["rows"])
       and all(r["plank"] == "P1" for r in plan["rows"]) and any("planks into rows" in s["title"] for s in plan["steps"]))
plan, _ = run(json.load(open(os.path.join(EX, "ziggurat", "design.json"))))
expect("mirrored rows share a plank, turned over", len(plan["planks"]) * 2 == len(plan["rows"]) and {r["op"] for r in plan["rows"]} == {"", "f"})
expect("a face no workable bar fits falls back to triangle logs and says why", plan["info"]["kind"] == "tri"
       and any(not c["ok"] and c["level"] == "warn" and "rectangles" in c["what"] for c in plan["checks"]))
plan, _ = run(dict(json.load(open(os.path.join(EX, "tumbling-blocks", "design.json"))), build="logs"))
expect("hexagon pucks are not planks", not plan["planks"])
d = dict(json.load(open(os.path.join(EX, "six-point-stars", "design.json"))), build="logs"); d7 = copy.deepcopy(d); d7["board"]["width"] = 13
plan, _ = run(d7)      # seven rows: an odd count has no mirror partner for most rows
expect("a plank cut for one row is called not worth it, and the check warns", any(not p["worth"] and "Not repeated" in p["why"] for p in plan["planks"])
       and any(not c["ok"] and "worth making" in c["what"] for c in plan["checks"]))
dm = json.load(open(os.path.join(EX, "two-wood-maze", "design.json")))
plan, errs = run(dm)
expect("maze: a plank build, one slab type, six rows from one plank", not errs and plan["method"] == "plank" and plan["N"]["nslab"] == 16 and len(plan["rows"]) == 6)
dm["params"]["cols"] = 7; plan, errs = run(dm)
expect("maze: an odd number of tiles across is caught", errs and any("even number" in e for e in errs))
dm["params"] = {"bar": 0.75, "cols": 6, "rows": 4}; plan, errs = run(dm)
expect("maze: a blank too thick for the tilted blade is caught", errs and any("45 degrees" in e for e in errs))

ds = json.load(open(os.path.join(EX, "star-lattice", "design.json")))
plan, errs = run(ds)
expect("star lattice: a plank build, one log, two planks each cut for half the rows", not errs and plan["method"] == "plank" and len(plan["planks"]) == 2
       and all(p["rows"] == 4 for p in plan["planks"]) and plan["repeats"]["log_types"] == 1)
ds["params"]["star"] = 0.25; plan, errs = run(ds)
expect("star lattice: a strip that would miss its star is caught", errs and any("land on a star" in e for e in errs))

plan, _ = run(d); rep = plan["repeats"]
expect("repeat math: the star field's rows pair up end for end about the middle of the board",
       rep["rows"] % 2 == 0 and rep["orbits"] * 2 == rep["rows"] and any(t["op"] == "r" and t["centre"] == rep["rows"] / 2 + 0.5 for t in rep["turns"]))
plan, _ = run(dict(json.load(open(os.path.join(EX, "pinwheel-chevrons", "design.json"))), build="logs"))
expect("repeat math: chevron rows repeat every row", plan["repeats"]["row_period"] == 1 and plan["repeats"]["orbits"] == 1)
import repeats as RP
vs = RP.variants(plan, plan["planks"][0])
expect("variants: one chevron plank makes 16 different faces, rolled rows carry every colour across the seams",
       len(vs) == 16 and vs[0]["row2"] == "f" and vs[0]["carry"] == 1.0 and [v["name"] for v in vs] == [v["name"] for v in RP.variants(plan, plan["planks"][0])])
plan, _ = run(json.load(open(os.path.join(EX, "six-point-stars", "design.json"))))
expect("six-point stars from rectangles: one sandwich makes every striped bar", plan["info"]["kind"] == "bars" and sum(1 for l in plan["logs"] if l["shape"] == "sandwich") == 1)
import hashlib, subprocess
def digest(seed):
    with tempfile.TemporaryDirectory() as out:
        subprocess.run([sys.executable, os.path.join(HERE, "cbplan.py"), os.path.join(EX, "faceted-gems", "design.json"), out],
                       env=dict(os.environ, PYTHONHASHSEED=seed), capture_output=True, check=True)
        return hashlib.md5(open(os.path.join(out, "plan.json"), "rb").read() + open(os.path.join(out, "plan.html"), "rb").read()).hexdigest()
expect("deterministic: the same design builds the same plan, byte for byte", digest("1") == digest("2"))

print("all good" if not fails else f"{fails} failed")
sys.exit(1 if fails else 0)
