#!/usr/bin/env python3
"""Render an OBJ as a clean hidden-line drawing (white faces, black part and crease edges).

Needs only numpy and Pillow (no Blender), so it runs in any container. The drawing is the guide
image for scripts/nano_banana.py: the model is drawn exactly, from the camera you want the photo from.

  python3 scripts/line_drawing.py bed.obj bed-lines.jpg --cam=-1.35,-1.75,1.45 --target=0.85,1.05,0.42 --fov 50

Write negative coordinates as --cam=-1,2,3 (with =). The OBJ is in meters, Z up (what export_obj.js and build_model.js write). --fov is horizontal, in degrees.
"""
import argparse
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("obj"); ap.add_argument("out")
ap.add_argument("--cam", required=True, help="x,y,z of the camera, meters")
ap.add_argument("--target", required=True, help="x,y,z the camera looks at")
ap.add_argument("--fov", type=float, default=50)
ap.add_argument("--res", default="3000x2000")
a = ap.parse_args()
W, H = map(int, a.res.split("x"))
cam = np.array([float(t) for t in a.cam.split(",")]); tgt = np.array([float(t) for t in a.target.split(",")])

V, F, oid = [], [], -1
for l in open(a.obj):
    if l.startswith("o "): oid += 1
    elif l.startswith("v "): V.append([float(t) for t in l.split()[1:4]])
    elif l.startswith("f "):
        idx = [int(t.split("/")[0]) - 1 for t in l.split()[1:]]
        for k in range(1, len(idx) - 1): F.append(((idx[0], idx[k], idx[k + 1]), max(oid, 0)))
V = np.array(V)

fwd = tgt - cam; fwd /= np.linalg.norm(fwd)
right = np.cross(fwd, [0, 0, 1]); right /= np.linalg.norm(right); up = np.cross(right, fwd)
rel = V - cam; x, y, z = rel @ right, rel @ up, rel @ fwd
f = (W / 2) / np.tan(np.radians(a.fov / 2)); px = W / 2 + f * x / z; py = H / 2 - f * y / z

zb = np.full((H, W), np.inf); idb = np.full((H, W), -1); nb = np.zeros((H, W, 3)); shade = np.ones((H, W))
L = np.array([-0.4, -0.6, 0.7]); L /= np.linalg.norm(L)
for (i, j, k), o in F:
    if min(z[i], z[j], z[k]) <= 0.01: continue
    n = np.cross(V[j] - V[i], V[k] - V[i]); nn = np.linalg.norm(n)
    if nn == 0: continue
    n /= nn
    xs = np.array([px[i], px[j], px[k]]); ys = np.array([py[i], py[j], py[k]]); zs = np.array([z[i], z[j], z[k]])
    x0, x1 = int(max(0, np.floor(xs.min()))), int(min(W - 1, np.ceil(xs.max())))
    y0, y1 = int(max(0, np.floor(ys.min()))), int(min(H - 1, np.ceil(ys.max())))
    if x0 > x1 or y0 > y1: continue
    d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
    if abs(d) < 1e-9: continue
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
    w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
    w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
    w2 = 1 - w0 - w1
    m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
    zz = 1 / (w0 / zs[0] + w1 / zs[1] + w2 / zs[2])
    sub = zb[y0:y1 + 1, x0:x1 + 1]; m &= zz < sub
    sub[m] = zz[m]; idb[y0:y1 + 1, x0:x1 + 1][m] = o; nb[y0:y1 + 1, x0:x1 + 1][m] = n
    shade[y0:y1 + 1, x0:x1 + 1][m] = 0.80 + 0.20 * abs(n @ L)

# Edges: a change of part, a crease (normals differ), or a depth jump.
e = np.zeros((H, W), bool)
for dy, dx in [(0, 1), (1, 0), (1, 1)]:
    p = (slice(0, H - dy), slice(0, W - dx)); q = (slice(dy, H), slice(dx, W))
    both = (idb[p] >= 0) & (idb[q] >= 0)
    diff = (idb[p] != idb[q]) | (both & ((nb[p] * nb[q]).sum(-1) < 0.97))
    dz = np.zeros(both.shape); dz[both] = np.abs(zb[p][both] - zb[q][both])
    diff |= both & (dz > 0.03 * np.where(both, np.minimum(zb[p], zb[q]), 1))
    e[p] |= diff; e[q] |= diff
e2 = e.copy(); e2[1:] |= e[:-1]; e2[:, 1:] |= e[:, :-1]
img = np.where(np.isfinite(zb), shade * 255, 255).astype(np.uint8); img[e2] = 20
Image.fromarray(img).convert("RGB").save(a.out, quality=92)
print(f"wrote {a.out} ({W}x{H}, {len(F)} triangles)")
