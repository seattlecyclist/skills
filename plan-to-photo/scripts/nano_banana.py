#!/usr/bin/env python3
"""Line drawing + piece spec + room brief -> photoreal photo, via Google's Nano Banana (Gemini image).

  GEMINI_API_KEY=... python3 scripts/nano_banana.py bed-lines.jpg spec.md room.md out.jpg [--takes 2]

The drawing (scripts/line_drawing.py) fixes the piece's shape and the camera. spec.md describes the
piece in words: the parts the model must not reinvent, the wood and finish, and how to dress it.
room.md is the setting. Writes out.jpg, or out-1.jpg, out-2.jpg ... with --takes > 1.

Only the drawing is sent, never the plan pages: with plan pages and no drawing the model redesigns
the piece (extra headboard posts, a third board, a flat top). Editing a finished Blender render
instead keeps the shape but barely adds realism.
"""
import argparse, base64, json, os, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

ap = argparse.ArgumentParser()
ap.add_argument("drawing"); ap.add_argument("spec"); ap.add_argument("room"); ap.add_argument("out")
ap.add_argument("--model", default="gemini-3-pro-image", help="Nano Banana Pro; list others with GET /v1beta/models")
ap.add_argument("--aspect", default="3:2"); ap.add_argument("--size", default="2K")
ap.add_argument("--takes", type=int, default=1)
a = ap.parse_args()
key = os.environ.get("GEMINI_API_KEY") or sys.exit("set GEMINI_API_KEY")

prompt = f"""Turn this line drawing into a beautiful, photorealistic interior photograph, the kind a professional interiors photographer shoots for a high-end furniture maker's catalogue on a full-frame camera.

THE PIECE IS FIXED. The drawing is the exact 3D model of a piece built from a shop plan. Keep its outline, proportions, position and perspective identical to the drawing, as if the drawing were traced over the photo. Do not add, remove or restyle any part.
{open(a.spec).read().strip()}

BUILD THE ROOM (make it beautiful and real):
{open(a.room).read().strip()}
Everything should have real-world texture, imperfection and believable light: contact shadows, light falloff, true photographic dynamic range and subtle grain.

Keep the same camera viewpoint and framing as the drawing. Do not include any drawing lines, text or people."""

mime = "image/png" if a.drawing.lower().endswith(".png") else "image/jpeg"
body = {"contents": [{"role": "user", "parts": [
            {"text": "LINE DRAWING (exact 3D model of the piece, rendered from the camera you must use):"},
            {"inline_data": {"mime_type": mime, "data": base64.b64encode(open(a.drawing, "rb").read()).decode()}},
            {"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"],
                             "imageConfig": {"aspectRatio": a.aspect, "imageSize": a.size}}}

def take(i):
    out = a.out if a.takes == 1 else "{0}-{2}{1}".format(*os.path.splitext(a.out), i + 1)
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{a.model}:generateContent",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        return f"{out}: HTTP {e.code} {e.read().decode()[:400]}"
    for c in r.get("candidates", []):
        for p in c.get("content", {}).get("parts", []):
            if "inlineData" in p and not p.get("thought"):
                open(out, "wb").write(base64.b64decode(p["inlineData"]["data"]))
                return f"wrote {out}"
    return f"{out}: no image ({r.get('candidates', [{}])[0].get('finishReason')})"

with ThreadPoolExecutor(a.takes) as ex:
    for msg in ex.map(take, range(a.takes)): print(msg)
