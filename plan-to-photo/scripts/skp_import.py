"""Clean a SketchUp export (from scripts/sketchup/export_for_p2p.rb) into the model the rest of
the skill uses.

  python3 scripts/skp_import.py export/ out/ [--drop REGEX] [--keep REGEX] [--all] [--scale S]

Reads export/model.obj, parts.json and scenes.json. Writes to out/:
  model.obj      meters, Z up, front-left-bottom corner at the origin, extras removed
  cameras.txt    line_drawing.py arguments for every saved scene, plus a default 3/4 view
  materials.md   the parts and SketchUp materials, a starting point for spec.md

Extras a plan file carries are dropped and printed so you can check them:
  - parts named like scale figures or annotations (people, dimensions, labels), plus --drop REGEX
  - every part outside the largest assembly: parts are grouped by touching bounding boxes, and an
    exploded view, a loose cut-list layout or a second copy falls apart into its own groups.
    --all keeps everything; --keep REGEX always keeps matching parts.
--scale multiplies coordinates (use 0.0254 for an OBJ exported from SketchUp Pro in inches).
Also takes a plain OBJ with no parts.json or scenes.json.
"""
import argparse, json, math, os, re, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frame_camera import frame, args_for  # noqa: E402

EXTRAS = (r"\b(person|people|figure|human|man|woman|scale ?fig|dimension|label|text|note|arrow|"
          r"susan|chris|derrick|lisanne|bryce|josh|sang|mila|aiden)\b")
GAP = 0.005  # meters: bounding boxes closer than this count as touching

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--drop", help="regex: also drop parts whose name or path matches")
ap.add_argument("--keep", help="regex: always keep parts whose name or path matches")
ap.add_argument("--all", action="store_true", help="keep every part (no assembly grouping)")
ap.add_argument("--scale", type=float, default=1.0)
a = ap.parse_args()

obj_path = a.src if a.src.endswith(".obj") else os.path.join(a.src, "model.obj")
src_dir = os.path.dirname(obj_path)
parts_info = {}
pj = os.path.join(src_dir, "parts.json")
if os.path.exists(pj):
    meta = json.load(open(pj))
    parts_info = {p["object"]: p for p in meta.get("parts", [])}
    materials = meta.get("materials", [])
else:
    meta, materials = {}, []

# Parse into objects, keeping each face's vertex and normal references.
V, VN, objs = [], [], []
cur = None
for l in open(obj_path):
    if l.startswith("o ") or l.startswith("g "):
        cur = {"name": l.split(None, 1)[1].strip(), "faces": [], "mtl": None, "mtls": {}}
        objs.append(cur)
    elif l.startswith("v "): V.append([float(t) for t in l.split()[1:4]])
    elif l.startswith("vn "): VN.append([float(t) for t in l.split()[1:4]])
    elif l.startswith("usemtl "):
        if cur is None: cur = {"name": "object", "faces": [], "mtl": None, "mtls": {}}; objs.append(cur)
        cur["mtl"] = l.split(None, 1)[1].strip()
    elif l.startswith("f "):
        if cur is None: cur = {"name": "object", "faces": [], "mtl": None, "mtls": {}}; objs.append(cur)
        f = []
        for t in l.split()[1:]:
            s = t.split("/")
            vi = int(s[0]); vi = vi - 1 if vi > 0 else len(V) + vi
            ni = None
            if len(s) > 2 and s[2]:
                ni = int(s[2]); ni = ni - 1 if ni > 0 else len(VN) + ni
            f.append((vi, ni))
        cur["faces"].append((cur["mtl"], f))
        cur["mtls"][cur["mtl"]] = cur["mtls"].get(cur["mtl"], 0) + 1
V = np.array(V) * a.scale; VN = np.array(VN) if VN else np.zeros((0, 3))
objs = [o for o in objs if o["faces"]]
if not objs: sys.exit("no faces in " + obj_path)
for o in objs:
    idx = sorted({vi for _, f in o["faces"] for vi, _ in f})
    o["lo"], o["hi"] = V[idx].min(0), V[idx].max(0)
    o["path"] = parts_info.get(o["name"], {}).get("path", o["name"])

size = V.max(0) - V.min(0)
if size.max() > 10 or size.max() < 0.05:
    print(f"warning: the whole export is {size.round(3)} m across; if that is not the plan's size, "
          f"pass --scale (0.0254 for inches)")

keep_re = re.compile(a.keep, re.I) if a.keep else None
drop_re = re.compile(a.drop, re.I) if a.drop else None
extra_re = re.compile(EXTRAS, re.I)
dropped = []


def kept_by_rule(o):
    return keep_re is not None and keep_re.search(o["path"])


live = []
for o in objs:
    txt = o["path"].replace("_", " ")
    if not kept_by_rule(o) and (extra_re.search(txt) or (drop_re and drop_re.search(o["path"]))):
        dropped.append((o["name"], "name looks like an extra" if extra_re.search(txt) else "--drop"))
    else:
        live.append(o)

# Group parts into assemblies by touching bounding boxes; keep the one with the most parts.
if not a.all and len(live) > 1:
    n = len(live); parent = list(range(n))

    def root(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i in range(n):
        for j in range(i + 1, n):
            if np.all(live[i]["lo"] - GAP <= live[j]["hi"]) and np.all(live[j]["lo"] - GAP <= live[i]["hi"]):
                parent[root(i)] = root(j)
    groups = {}
    for i in range(n): groups.setdefault(root(i), []).append(i)
    vol = lambda g: np.prod(np.max([live[i]["hi"] for i in g], 0) - np.min([live[i]["lo"] for i in g], 0))
    best = max(groups.values(), key=lambda g: (len(g), vol(g)))
    if len(groups) > 1:
        print(f"{len(groups)} separate groups of parts; keeping the largest assembly ({len(best)} parts)")
    keep = set(best)
    for i, o in enumerate(live):
        if i not in keep and not kept_by_rule(o):
            dropped.append((o["name"], "outside the main assembly"))
    live = [o for i, o in enumerate(live) if i in keep or kept_by_rule(o)]

for name, why in dropped: print(f"  dropped {name}: {why}")

# Move the front-left-bottom corner to the origin; cameras move with it.
used = sorted({vi for o in live for _, f in o["faces"] for vi, _ in f})
shift = -V[used].min(0)
os.makedirs(a.out, exist_ok=True)
lines = [f"# plan-to-photo model from {os.path.basename(obj_path)}, meters, Z up"]
vmap, nmap = {}, {}
for o in live:
    lines.append(f"o {o['name']}")
    cur = object()
    for mtl, f in o["faces"]:
        if mtl != cur and mtl: lines.append(f"usemtl {mtl}")
        cur = mtl
        refs = []
        for vi, ni in f:
            if vi not in vmap:
                vmap[vi] = len(vmap) + 1; p = V[vi] + shift
                lines.append(f"v {p[0]:.5f} {p[1]:.5f} {p[2]:.5f}")
            if ni is not None and ni not in nmap:
                nmap[ni] = len(nmap) + 1; q = VN[ni]
                lines.append(f"vn {q[0]:.4f} {q[1]:.4f} {q[2]:.4f}")
            refs.append(f"{vmap[vi]}//{nmap[ni]}" if ni is not None else f"{vmap[vi]}")
        lines.append("f " + " ".join(refs))
open(os.path.join(a.out, "model.obj"), "w").write("\n".join(lines) + "\n")
Vk = V[used] + shift
dims = Vk.max(0)
print(f"wrote {a.out}/model.obj: {len(live)} parts, {dims[0]:.3f} x {dims[1]:.3f} x {dims[2]:.3f} m "
      f"({dims[0] / 0.0254:.2f} x {dims[1] / 0.0254:.2f} x {dims[2] / 0.0254:.2f} in, W x D x H)")

# Cameras: every saved perspective scene, then a default 3/4 view.
cams = []
sj = os.path.join(src_dir, "scenes.json")
if os.path.exists(sj):
    for c in json.load(open(sj)):
        if not c.get("perspective", True):
            cams.append(f"# {c['name']}: parallel projection, skipped (line_drawing.py is perspective only)")
            continue
        eye = np.array(c["eye"]) * a.scale + shift; tgt = np.array(c["target"]) * a.scale + shift
        note = ""
        if abs(c.get("up", [0, 0, 1])[2]) < 0.9: note = "  # camera is rolled or looking straight down; the drawing keeps Z up"
        cams.append(f"# {c['name']}{note}\n{args_for(eye, tgt, round(c['hfov_3x2'], 1))}")
cam, tgt = frame(Vk)
cams.append(f"# default 3/4 view from the front left (scripts/frame_camera.py)\n{args_for(cam, tgt, 40)}")
open(os.path.join(a.out, "cameras.txt"), "w").write("\n".join(cams) + "\n")
print(f"wrote {a.out}/cameras.txt: {sum(1 for c in cams if c.startswith('# ') and '--cam' in c)} cameras")

# Materials and parts, for spec.md.
nice = lambda m: re.sub(r"[_\s]+", " ", re.sub(r"^\[|\]$", "", m or "no material")).strip()
by_mat = {}
for o in live:
    m = parts_info.get(o["name"], {}).get("material") or max(o["mtls"], key=lambda k: o["mtls"][k]) or None
    by_mat.setdefault(nice(m), []).append(o)
md = [f"# Parts and materials from {meta.get('source', os.path.basename(obj_path))}", "",
      "SketchUp material names are often defaults (\"Wood Cherry Original\" on a walnut plan). Check each "
      "against the plan's cut list and say the real wood and finish in spec.md.", ""]
for m, os_ in sorted(by_mat.items(), key=lambda kv: -len(kv[1])):
    col = next((x for x in materials if nice(x.get("name")) == m), None)
    extra = f" (colour rgb{tuple(col['color'])}{', texture ' + col['texture'] if col.get('texture') else ''})" if col else ""
    md.append(f"## {m}{extra}: {len(os_)} parts")
    for o in os_:
        s = parts_info.get(o["name"], {}).get("size_in") or list(((o["hi"] - o["lo"]) / 0.0254).round(3))
        md.append(f"- {o['path']}: {' x '.join(f'{x:g}' for x in s)} in (W x D x H as placed)")
    md.append("")
open(os.path.join(a.out, "materials.md"), "w").write("\n".join(md))
print(f"wrote {a.out}/materials.md: {len(by_mat)} materials")
