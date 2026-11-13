"""Pick a camera for line_drawing.py from an OBJ's bounding box.

  python3 scripts/frame_camera.py model.obj [--az 35] [--el 18] [--fov 40] [--fill 0.62]

--az is degrees around the piece: 0 looks straight at the front (from -Y), positive swings the
camera to the viewer's left. --el is degrees above level. --fill is how much of the frame the
piece's bounding sphere fills (raise it for a small piece that looks lost). Prints the
--cam= --target= --fov arguments for line_drawing.py.
"""
import argparse, math
import numpy as np


def frame(V, az=35.0, el=18.0, fov=40.0, fill=0.62):
    lo, hi = V.min(0), V.max(0)
    c = (lo + hi) / 2; c[2] = lo[2] + (hi[2] - lo[2]) * 0.45
    r = np.linalg.norm(hi - lo) / 2
    d = r / math.tan(math.radians(fov / 2)) / fill
    a, e = math.radians(az), math.radians(el)
    cam = c + d * np.array([-math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])
    return cam, c


def args_for(cam, tgt, fov):
    f = lambda p: ",".join(f"{x:.3f}" for x in p)
    return f"--cam={f(cam)} --target={f(tgt)} --fov {fov:g}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("obj")
    ap.add_argument("--az", type=float, default=35); ap.add_argument("--el", type=float, default=18)
    ap.add_argument("--fov", type=float, default=40); ap.add_argument("--fill", type=float, default=0.62)
    a = ap.parse_args()
    V = np.array([[float(t) for t in l.split()[1:4]] for l in open(a.obj) if l.startswith("v ")])
    cam, tgt = frame(V, a.az, a.el, a.fov, a.fill)
    print(args_for(cam, tgt, a.fov))
