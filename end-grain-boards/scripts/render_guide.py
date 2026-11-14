#!/usr/bin/env python3
"""Colour-coded perspective of the finished board: the guide image for plan-to-photo's nano_banana.py.

Top face: every bar's end in its species' end-grain colour with thin glue lines. Edges: the bars that
reach each edge as long-grain stripes, shaded darker. Pure Pillow, no Blender.

  python3 scripts/render_guide.py out/plan.json out/guide.png [--az 30 --el 38 --res 2400x1600]

cbplan.py calls render() itself; design.json "guide": {"az": .., "el": ..} changes the view.
"""
import json, math, sys
from PIL import Image, ImageDraw


def _hex(c, k=1.0):
    c = c.lstrip("#")
    return tuple(max(0, min(255, int(int(c[i:i + 2], 16) * k))) for i in (0, 2, 4))


def render(plan, out, az=-28, el=36, res="2400x1600", fov=32, ss=2):
    W, H = (int(v) for v in res.split("x"))
    Wi, Hi = W * ss, H * ss
    tr = plan["board"]["trim"]; T = plan["board"]["thickness"]
    cx, cy = (tr[0] + tr[2]) / 2, (tr[1] + tr[3]) / 2
    bw, bl = tr[2] - tr[0], tr[3] - tr[1]
    diag = math.sqrt(bw ** 2 + bl ** 2 + T ** 2)
    dist = diag / 2 / math.tan(math.radians(fov / 2)) * 1.12
    a, e = math.radians(az), math.radians(el)
    # camera in front (-y) of the board, turned by az, raised by el
    cam = (cx + dist * math.cos(e) * math.sin(a), cy - dist * math.cos(e) * math.cos(a), T / 2 + dist * math.sin(e))
    tgt = (cx, cy, T * 0.3)
    fwd = [t - c for t, c in zip(tgt, cam)]; n = math.sqrt(sum(v * v for v in fwd)); fwd = [v / n for v in fwd]
    right = [fwd[1], -fwd[0], 0]; n = math.hypot(*right[:2]); right = [v / n for v in right]
    up = [right[1] * fwd[2] - right[2] * fwd[1], right[2] * fwd[0] - right[0] * fwd[2], right[0] * fwd[1] - right[1] * fwd[0]]
    def raw(x, y, z):
        r = (x - cam[0], y - cam[1], z - cam[2])
        X = sum(p * q for p, q in zip(r, right)); Y = sum(p * q for p, q in zip(r, up)); Z = sum(p * q for p, q in zip(r, fwd))
        return (X / Z, Y / Z)

    # fit the board's projected corners to 84% of the frame, centred
    cs = [raw(x, y, z) for x in (tr[0], tr[2]) for y in (tr[1], tr[3]) for z in (0, T)]
    xs, ys = [c[0] for c in cs], [c[1] for c in cs]
    f = 0.84 * min(Wi / (max(xs) - min(xs)), Hi / (max(ys) - min(ys)))
    mx, my = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2

    def proj(x, y, z):
        X, Y = raw(x, y, z)
        return (Wi / 2 + f * (X - mx), Hi / 2 - f * (Y - my))

    img = Image.new("RGB", (Wi, Hi), (255, 255, 255)); d = ImageDraw.Draw(img)
    sp = plan["species"]
    # soft contact shadow
    sh = [proj(tr[0] - .15, tr[1] - .15, 0), proj(tr[2] + .15, tr[1] - .15, 0), proj(tr[2] + .15, tr[3] + .15, 0), proj(tr[0] - .15, tr[3] + .15, 0)]
    d.polygon(sh, fill=(225, 225, 225))
    # edges: segments of bars on the boundary, only the faces turned toward the camera
    sides = []
    for fc in plan["face"]:
        p = fc["pts"]
        for i in range(len(p)):
            (x0, y0), (x1, y1) = p[i - 1], p[i]
            for axis, val, normal in ((1, tr[1], (0, -1)), (1, tr[3], (0, 1)), (0, tr[0], (-1, 0)), (0, tr[2], (1, 0))):
                if abs((y0 if axis else x0) - val) < 1e-6 and abs((y1 if axis else x1) - val) < 1e-6:
                    mid = ((x0 + x1) / 2 + normal[0], (y0 + y1) / 2 + normal[1])
                    view = (cam[0] - (x0 + x1) / 2, cam[1] - (y0 + y1) / 2)
                    if view[0] * normal[0] + view[1] * normal[1] > 0:
                        k = 0.78 if normal[1] else 0.66
                        sides.append(([proj(x0, y0, 0), proj(x1, y1, 0), proj(x1, y1, T), proj(x0, y0, T)], _hex(sp[fc["role"]]["long"], k)))
    for q, c in sides: d.polygon(q, fill=c, outline=tuple(int(v * 0.8) for v in c))
    lw = max(1, ss)
    for fc in plan["face"]:
        pts = [proj(x, y, T) for x, y in fc["pts"]]
        d.polygon(pts, fill=_hex(sp[fc["role"]]["end"]))
    for fc in plan["face"]:
        pts = [proj(x, y, T) for x, y in fc["pts"]]
        d.line(pts + [pts[0]], fill=(40, 30, 20), width=lw)
    # crisp outline of the board
    top = [proj(tr[0], tr[1], T), proj(tr[2], tr[1], T), proj(tr[2], tr[3], T), proj(tr[0], tr[3], T)]
    d.line(top + [top[0]], fill=(20, 15, 10), width=lw * 2)
    img.resize((W, H), Image.LANCZOS).save(out)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("out")
    ap.add_argument("--az", type=float, default=-28); ap.add_argument("--el", type=float, default=36)
    ap.add_argument("--res", default="2400x1600"); ap.add_argument("--fov", type=float, default=32)
    a = ap.parse_args()
    render(json.load(open(a.plan)), a.out, a.az, a.el, a.res, a.fov)
    print("wrote", a.out)
