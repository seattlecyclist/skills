#!/usr/bin/env python3
"""Photo (+ optional scene) -> painted open-world crime-game loading-screen poster art.

  GEMINI_API_KEY=... python3 scripts/gta_render.py photo.jpg out.jpg [--scene "..."] [--preset miami-sunset]
                     [--takes 2] [--aspect auto] [--size 2K] [--model MODEL] [--compare]

Tries Google's Nano Banana Pro first, then the other Gemini image models, then OpenAI's image edit
model (OPENAI_API_KEY), and moves on when a model is missing, rate limited or returns no image.
Writes out.jpg, or out-1.jpg, out-2.jpg ... with --takes > 1, and prints which model made each.
--compare also writes out-compare.jpg: the photo and the poster side by side (needs Pillow).

The guardrails are part of the prompt and cannot be turned off from the command line: no logos,
titles or lettering, and no weapons, gang signs, drugs, money piles or crime scenes.
"""
import argparse, base64, io, json, mimetypes, os, sys, uuid, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

GEMINI_MODELS = ["gemini-3-pro-image", "gemini-3-pro-image-preview", "gemini-3.1-flash-image",
                 "gemini-3.1-flash-image-preview", "gemini-2.5-flash-image"]
OPENAI_MODELS = ["gpt-image-1"]
GEMINI_ASPECTS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]

PRESETS = {
    "miami-sunset": "a neon Miami-style beach city at dusk: hot pink, orange and violet sunset sky, tall palm "
                    "trees, glowing pastel art-deco hotels with neon trim, warm string lights, the ocean on one side",
    "neon-night": "a rain-slicked downtown street at night: magenta and cyan neon signs (no readable words), "
                  "reflections on wet pavement, palm trees silhouetted against a purple sky",
    "desert-highway": "a sun-baked desert highway at golden hour: long shadows, a dusty two-lane road, "
                      "mountains and a huge orange sun low behind them, heat haze",
    "beach-day": "a bright beach boardwalk at midday: turquoise water, white sand, lifeguard tower, "
                 "palm trees and a deep blue sky with a few big clouds",
    "hills-sunset": "a hillside overlook above a sprawling city at sunset: the city glowing gold below, "
                    "palm trees and a gradient sky from orange to deep blue",
    "keep": "the photo's own location, kept recognisable but repainted with the same bold palette and "
            "lighting, with the sky turned into a vivid sunset",
}

STYLE = """Repaint this photo as bold, hand-painted key art for a modern open-world crime-adventure video game: the kind of illustrated poster shown on a loading screen.

PEOPLE (most important): keep every person who is in the photo, in the same positions, poses, clothing, accessories and expressions. Keep each face clearly recognisable as that same person: the same face shape, skin tone, hair, facial hair, glasses, hats and build. Make everyone look confident, heroic and flattering, never caricatured, older, heavier, thinner or a different ethnicity. Do not add, remove or merge people.

ART STYLE: thick, confident illustrated outlines; painted cel-style shading with strong rim light and crisp highlights; saturated, high-contrast colour; slightly stylised but realistic proportions; cinematic poster composition with the group as the clear hero.

SETTING: {scene}

ABSOLUTE RULES: no logos, game titles, brand marks, lettering, captions or numbers anywhere; repaint any existing text on clothing, hats or signs as plain shapes or keep it unreadable. No weapons of any kind, no gang signs or gang tattoos, no drugs, money piles, police chases, fire or crime scenes. One single continuous illustration, no panels, borders, frames or split images."""


def closest_aspect(path):
    try:
        from PIL import Image
        w, h = Image.open(path).size
    except Exception:
        return "1:1"
    r = w / h
    return min(GEMINI_ASPECTS, key=lambda s: abs(eval(s.replace(":", "/")) - r))


def gemini(model, key, img, mime, prompt, aspect, size):
    cfg = {"aspectRatio": aspect}
    if "pro" in model: cfg["imageSize"] = size
    body = {"contents": [{"role": "user", "parts": [{"text": prompt},
                                                   {"inline_data": {"mime_type": mime, "data": base64.b64encode(img).decode()}}]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": cfg}}
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    r = json.load(urllib.request.urlopen(req, timeout=300))
    for c in r.get("candidates", []):
        for p in c.get("content", {}).get("parts", []):
            d = p.get("inlineData") or p.get("inline_data")
            if d and not p.get("thought"):
                return base64.b64decode(d["data"])
    reason = (r.get("candidates") or [{}])[0].get("finishReason") or r.get("promptFeedback", {}).get("blockReason")
    raise RuntimeError(f"no image ({reason})")


def openai(model, key, img, mime, prompt, aspect, size):
    w, h = map(int, aspect.split(":"))
    shape = "1024x1024" if abs(w / h - 1) < 0.15 else ("1536x1024" if w > h else "1024x1536")
    b = uuid.uuid4().hex
    fields = {"model": model, "prompt": prompt, "size": shape, "quality": "high", "input_fidelity": "high"}
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()]
    ext = mimetypes.guess_extension(mime) or ".png"
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="image"; filename="photo{ext}"\r\n'
                 f"Content-Type: {mime}\r\n\r\n".encode() + img + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    req = urllib.request.Request("https://api.openai.com/v1/images/edits", data=b"".join(parts),
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": f"multipart/form-data; boundary={b}"})
    r = json.load(urllib.request.urlopen(req, timeout=300))
    return base64.b64decode(r["data"][0]["b64_json"])


def save(data, out):
    """Write the bytes in the format the extension names (models return PNG or JPEG regardless)."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        fmt = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}.get(os.path.splitext(out)[1].lower())
        if fmt and im.format != fmt:
            (im.convert("RGB") if fmt == "JPEG" else im).save(out, fmt, quality=92); return
    except ImportError:
        pass
    open(out, "wb").write(data)


def chain(forced):
    g, o = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"), os.environ.get("OPENAI_API_KEY")
    out = []
    if g: out += [("gemini", m, g) for m in GEMINI_MODELS]
    if o: out += [("openai", m, o) for m in OPENAI_MODELS]
    if forced: out = [c for c in out if c[1] == forced] or [("gemini" if forced.startswith("gemini") else "openai", forced, g if forced.startswith("gemini") else o)]
    return [c for c in out if c[2]]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo"); ap.add_argument("out")
    ap.add_argument("--scene", default="", help="free-text scene setting; overrides or adds to --preset")
    ap.add_argument("--preset", default="miami-sunset", choices=sorted(PRESETS))
    ap.add_argument("--takes", type=int, default=2)
    ap.add_argument("--aspect", default="auto", help="auto (closest to the photo) or e.g. 9:16 for a phone wallpaper")
    ap.add_argument("--size", default="2K", help="Nano Banana Pro output size: 1K, 2K or 4K")
    ap.add_argument("--model", help="use only this model id")
    ap.add_argument("--compare", action="store_true")
    a = ap.parse_args()

    models = chain(a.model)
    if not models:
        sys.exit("No image model available: set GEMINI_API_KEY (Nano Banana) or OPENAI_API_KEY.")
    img = open(a.photo, "rb").read()
    mime = mimetypes.guess_type(a.photo)[0] or "image/jpeg"
    aspect = closest_aspect(a.photo) if a.aspect == "auto" else a.aspect
    scene = PRESETS[a.preset] if not a.scene else (a.scene if a.preset == "miami-sunset" else f"{PRESETS[a.preset]}; {a.scene}")
    prompt = STYLE.format(scene=scene)

    def take(i):
        out = a.out if a.takes == 1 else "{0}-{2}{1}".format(*os.path.splitext(a.out), i + 1)
        errors = []
        for provider, model, key in models:
            try:
                data = (gemini if provider == "gemini" else openai)(model, key, img, mime, prompt, aspect, a.size)
                save(data, out)
                return out, f"wrote {out} with {model}" + (f" (after: {'; '.join(errors)})" if errors else "")
            except urllib.error.HTTPError as e:
                errors.append(f"{model} HTTP {e.code}")
            except Exception as e:
                errors.append(f"{model} {e}")
        return None, f"{out}: every model failed: {'; '.join(errors)}"

    with ThreadPoolExecutor(min(a.takes, 4)) as ex:
        results = list(ex.map(take, range(a.takes)))
    for _, msg in results: print(msg)
    made = [p for p, _ in results if p]
    if a.compare and made:
        from PIL import Image
        src = Image.open(a.photo).convert("RGB")
        for p in made:
            dst = Image.open(p).convert("RGB")
            h = 1200; s = src.resize((round(src.width * h / src.height), h)); d = dst.resize((round(dst.width * h / dst.height), h))
            sheet = Image.new("RGB", (s.width + d.width + 24, h), (20, 14, 30))
            sheet.paste(s, (0, 0)); sheet.paste(d, (s.width + 24, 0))
            cp = "{0}-compare.jpg".format(os.path.splitext(p)[0]); sheet.save(cp, quality=90); print(f"wrote {cp}")
    sys.exit(0 if made else 1)


if __name__ == "__main__":
    main()
