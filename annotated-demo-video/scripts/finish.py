#!/usr/bin/env python3
"""finish.py: turns a recorded walkthrough into its deliverables.

    python3 finish.py ./walkthrough --name roster-move [--seconds 5.5] [--fade 0.6] [--wpm 200] [--crf 22]

Reads <dir>/manifest.json and <dir>/frames/*.png (written by record.cjs or an adapter) and writes:
    <dir>/<name>.mp4          H.264, one still per step with crossfades (needs ffmpeg)
    <dir>/<name>.html         self-contained player: frames inlined as JPEG, step rail, keyboard controls
    <dir>/sheet.png           contact sheet of every frame, to check the run at a glance
    <dir>/cropped/NN.png      the exact frames used

Each step is held for its reading time (base + words / wpm, clamped to min..max), so a two-word caption
stays snappy and a dense one gets long enough to read. --seconds sets one fixed hold for every step.

A frame taller than the viewport (a full-page screenshot) is cropped at its manifest offset first.
Only Pillow and ffmpeg are needed; output is the same for the same frames and options.
"""
import argparse, base64, html, io, json, math, pathlib, re, shutil, subprocess, sys

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent


def crop_frames(root, man):
    W, H = man["viewport"]["width"], man["viewport"]["height"]
    out = root / "cropped"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    paths = []
    for f in man["frames"]:
        im = Image.open(root / "frames" / f["file"]).convert("RGB")
        if im.size != (W, H):
            off = int(f.get("offset") or 0)
            im = im.crop((0, off, W, off + H))
        p = out / f["file"]
        im.save(p)
        paths.append(p)
    return paths


def contact_sheet(paths, dest, cols=4, w=480):
    h = round(w * Image.open(paths[0]).height / Image.open(paths[0]).width)
    rows = math.ceil(len(paths) / cols)
    sheet = Image.new("RGB", (cols * w, rows * h), "white")
    for i, p in enumerate(paths):
        sheet.paste(Image.open(p).resize((w, h), Image.LANCZOS), ((i % cols) * w, (i // cols) * h))
    sheet.save(dest)


def read_seconds(frame, wpm, base=1.2, lo=2.2, hi=9.0):
    words = len(re.sub(r"<[^>]+>", " ", f"{frame.get('title') or ''} {frame.get('body') or ''}").split())
    return round(min(hi, max(lo, base + words * 60 / wpm)), 2)


def video(paths, dest, holds, fade, crf, fps=30):
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found; skipping the MP4", file=sys.stderr)
        return False
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for p, hold in zip(paths, holds):
        cmd += ["-loop", "1", "-t", str(hold), "-framerate", str(fps), "-i", str(p)]
    if len(paths) == 1:
        graph, last = "[0:v]format=yuv420p[out]", None
    else:
        parts, prev, off = [], "[0:v]", holds[0] - fade
        for i in range(1, len(paths)):
            parts.append(f"{prev}[{i}:v]xfade=transition=fade:duration={fade}:offset={off:.3f}[v{i}]")
            prev, off = f"[v{i}]", off + holds[i] - fade
        parts.append(f"{prev}format=yuv420p[out]")
        graph = ";".join(parts)
    # Even dimensions keep libx264 happy whatever the viewport.
    graph = graph.replace("format=yuv420p[out]", "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p[out]")
    cmd += ["-filter_complex", graph, "-map", "[out]", "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-map_metadata", "-1", "-fflags", "+bitexact", str(dest)]
    subprocess.run(cmd, check=True)
    return True


def css_vars(d):
    return "".join(f"--{k.replace('_', '-')}:{v};" for k, v in d.items())


def player(paths, man, dest, holds, width, quality):
    theme = man["theme"]
    frames = []
    for p, f, hold in zip(paths, man["frames"], holds):
        im = Image.open(p).convert("RGB")
        im = im.resize((width, round(width * im.height / im.width)), Image.LANCZOS)
        b = io.BytesIO()
        im.save(b, "JPEG", quality=quality, optimize=True)
        frames.append({"src": "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode(),
                       "title": f["title"], "body": f.get("body", ""), "chapter": f.get("chapter"), "ms": int(hold * 1000)})
    vp = man["viewport"]
    steps = len(frames)
    note = man.get("note") or f"{steps} steps."
    fill = {
        "{{TITLE}}": html.escape(man.get("title") or "Walkthrough"),
        "{{EYEBROW}}": html.escape(man.get("kicker") or ""),
        "{{NOTE}}": html.escape(note),
        "{{FONT_CSS}}": html.escape(theme.get("font_css", "")),
        "{{DISPLAY_FONT}}": theme["display_font"], "{{BODY_FONT}}": theme["body_font"], "{{MONO_FONT}}": theme["mono_font"],
        "{{LIGHT}}": css_vars(theme["player"]["light"]), "{{DARK}}": css_vars(theme["player"]["dark"]),
        "{{ASPECT}}": f"{vp['width']}/{vp['height']}",
        "{{FRAMES}}": json.dumps(frames).replace("</", "<\\/"),
    }
    page = (HERE.parent / "assets" / "player.html").read_text()
    for k, v in fill.items():
        page = page.replace(k, v)
    dest.write_text(page)
    mb = dest.stat().st_size / 1e6
    if mb > 15:
        print(f"warning: {dest.name} is {mb:.1f} MB; rerun with a smaller --jpeg-width or --quality", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--name", default="walkthrough")
    ap.add_argument("--seconds", type=float, default=None, help="one fixed hold for every step (default: reading time)")
    ap.add_argument("--wpm", type=float, default=200, help="reading speed for the per-step hold")
    ap.add_argument("--crf", type=int, default=22, help="libx264 CRF; higher is smaller")
    ap.add_argument("--fade", type=float, default=0.6, help="crossfade between steps in the MP4")
    ap.add_argument("--jpeg-width", type=int, default=1200)
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("--no-video", action="store_true")
    a = ap.parse_args()

    root = pathlib.Path(a.dir).resolve()
    if not (root / "manifest.json").exists():
        sys.exit(f"no manifest.json in {root}; record first (record.cjs or the Capybara adapter)")
    man = json.loads((root / "manifest.json").read_text())
    if not man["frames"]:
        sys.exit("manifest has no frames")
    paths = crop_frames(root, man)
    holds = [a.seconds or read_seconds(f, a.wpm) for f in man["frames"]]
    contact_sheet(paths, root / "sheet.png")
    player(paths, man, root / f"{a.name}.html", holds, a.jpeg_width, a.quality)
    made = [root / "sheet.png", root / f"{a.name}.html"]
    if not a.no_video and video(paths, root / f"{a.name}.mp4", holds, a.fade, a.crf):
        made.append(root / f"{a.name}.mp4")
    for p in made:
        print(f"{p}  {p.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
