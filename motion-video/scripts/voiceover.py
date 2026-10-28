#!/usr/bin/env python3
"""Voiceover for a motion video: synthesize lines, split a single take into lines, place lines on the film's timeline.

  voiceover.py keys                                   # which TTS keys this machine has
  voiceover.py tts lines.txt --out vo/ [--provider elevenlabs|openai] [--voice ID] [--model ID]
  voiceover.py split take.mp3 --lines 6 --out vo/ [--script lines.txt] [--cuts 1.6,5.0,...]  # one take -> line01.wav ...
  voiceover.py place timeline.json --duration 24.5 --out vo-track.wav

lines.txt holds one spoken line per line. `tts` and `split` both write line01.wav, line02.wav ... and
lines.json with each line's text and duration, which is what the scene's timeline is built from.

timeline.json for `place` is a list of {"at": seconds, "file": "vo/line01.wav"}.

Keys come from the environment: ELEVENLABS_API_KEY (optional ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL_ID)
or OPENAI_API_KEY (optional OPENAI_TTS_VOICE, OPENAI_TTS_MODEL). With neither, `tts` exits with
status 3 and says so; the film is then made without a voice. Only ffmpeg and the Python standard
library are needed.
"""
import argparse, json, os, re, subprocess, sys, urllib.request, urllib.error
from pathlib import Path

ELEVEN_DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"  # "George", a premade ElevenLabs narrator voice
ELEVEN_DEFAULT_MODEL = "eleven_multilingual_v2"
OPENAI_DEFAULT_MODEL, OPENAI_DEFAULT_VOICE = "gpt-4o-mini-tts", "alloy"


def run(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def duration(path):
    return float(run("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)).stdout.strip())


def to_wav(src, dst, start=None, end=None):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src)]
    if start is not None: cmd += ["-ss", f"{start:.3f}"]
    if end is not None: cmd += ["-to", f"{end:.3f}"]
    run(*cmd, "-ar", "48000", "-ac", "2", str(dst))


def available():
    if os.environ.get("ELEVENLABS_API_KEY"): return "elevenlabs"
    if os.environ.get("OPENAI_API_KEY"): return "openai"
    return None


def post(url, headers, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"TTS request failed: HTTP {e.code} {e.read()[:300]!r}")


def synth(provider, text, voice, model, prev=None, nxt=None):
    if provider == "elevenlabs":
        voice = voice or os.environ.get("ELEVENLABS_VOICE_ID") or ELEVEN_DEFAULT_VOICE
        body = {"text": text, "model_id": model or os.environ.get("ELEVENLABS_MODEL_ID") or ELEVEN_DEFAULT_MODEL}
        # neighbouring lines keep the delivery continuous across separately generated lines
        if prev: body["previous_text"] = prev
        if nxt: body["next_text"] = nxt
        return post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
                    {"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "accept": "audio/mpeg"}, body), "mp3"
    body = {"model": model or os.environ.get("OPENAI_TTS_MODEL") or OPENAI_DEFAULT_MODEL,
            "voice": voice or os.environ.get("OPENAI_TTS_VOICE") or OPENAI_DEFAULT_VOICE,
            "input": text, "response_format": "wav"}
    if os.environ.get("OPENAI_TTS_INSTRUCTIONS"): body["instructions"] = os.environ["OPENAI_TTS_INSTRUCTIONS"]
    return post("https://api.openai.com/v1/audio/speech", {"authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}, body), "wav"


def write_index(out, lines, files):
    index = [{"line": i + 1, "text": t, "file": str(f), "duration": round(duration(f), 3)} for i, (t, f) in enumerate(zip(lines, files))]
    (out / "lines.json").write_text(json.dumps(index, indent=2))
    for row in index: print(f"line{row['line']:02d}  {row['duration']:6.2f} s  {row['text']}")
    print(f"index: {out / 'lines.json'}")


def cmd_keys(_):
    p = available()
    print(p or "none")
    sys.exit(0 if p else 3)


def cmd_tts(a):
    provider = a.provider or available()
    if not provider:
        print("No TTS key found (ELEVENLABS_API_KEY or OPENAI_API_KEY). Make the film without a voiceover, or supply a recorded take and use `split`.", file=sys.stderr)
        sys.exit(3)
    lines = [l.strip() for l in Path(a.script).read_text().splitlines() if l.strip()]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    files = []
    for i, text in enumerate(lines):
        audio, ext = synth(provider, text, a.voice, a.model, lines[i - 1] if i else None, lines[i + 1] if i + 1 < len(lines) else None)
        raw = out / f"line{i + 1:02d}.raw.{ext}"
        raw.write_bytes(audio)
        dst = out / f"line{i + 1:02d}.wav"
        to_wav(raw, dst); raw.unlink()
        files.append(dst)
    print(f"provider: {provider}")
    write_index(out, lines, files)


def silences(path, noise, min_gap):
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", f"silencedetect=noise={noise}dB:d={min_gap}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    return list(zip(starts, ends))


def cmd_split(a):
    total = duration(a.take)
    gaps = [g for g in silences(a.take, a.noise, a.min_gap) if 0.05 < g[0] and g[1] < total - 0.05]
    print("pauses: " + "  ".join(f"{(s + e) / 2:.2f}s ({e - s:.2f})" for s, e in gaps))
    if a.cuts:
        mids = [float(x) for x in a.cuts.split(",")]
        if len(mids) != a.lines - 1: sys.exit(f"--cuts needs {a.lines - 1} times")
    else:
        if len(gaps) < a.lines - 1:
            sys.exit(f"Found {len(gaps)} pauses, need {a.lines - 1}. Lower --min-gap or raise --noise (now {a.min_gap} s, {a.noise} dB).")
        # the longest pauses are the line breaks; shorter ones are pauses inside a line. When a pause
        # inside a line is as long as a break, check the printed pauses and pass --cuts instead.
        mids = [(s + e) / 2 for s, e in sorted(sorted(gaps, key=lambda g: g[1] - g[0], reverse=True)[:a.lines - 1])]
    bounds = [0.0] + mids + [total]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    texts = [l.strip() for l in Path(a.script).read_text().splitlines() if l.strip()] if a.script else [""] * a.lines
    files = []
    for i in range(a.lines):
        dst = out / f"line{i + 1:02d}.wav"
        to_wav(a.take, dst, bounds[i], bounds[i + 1]); files.append(dst)
    write_index(out, texts, files)


def cmd_place(a):
    items = json.loads(Path(a.timeline).read_text())
    inputs, chains = [], []
    for i, it in enumerate(items):
        inputs += ["-i", it["file"]]
        ms = int(round(float(it["at"]) * 1000))
        chains.append(f"[{i}]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{i}]")
    graph = ";".join(chains) + ";" + "".join(f"[a{i}]" for i in range(len(items))) + \
        f"amix=inputs={len(items)}:normalize=0,apad=whole_dur={a.duration},atrim=0:{a.duration}[out]"
    run("ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-map", "[out]", "-ar", "48000", a.out)
    for it in items:
        print(f"{float(it['at']):6.2f} s  {it['file']}  ends {float(it['at']) + duration(it['file']):.2f} s")
    print(f"track: {a.out}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("keys").set_defaults(fn=cmd_keys)
    t = sub.add_parser("tts"); t.add_argument("script"); t.add_argument("--out", required=True)
    t.add_argument("--provider", choices=["elevenlabs", "openai"]); t.add_argument("--voice"); t.add_argument("--model"); t.set_defaults(fn=cmd_tts)
    s = sub.add_parser("split"); s.add_argument("take"); s.add_argument("--lines", type=int, required=True); s.add_argument("--out", required=True)
    s.add_argument("--script", help="lines.txt, to label the pieces"); s.add_argument("--cuts", help="explicit cut times, e.g. 1.6,5.04,9.12"); s.add_argument("--noise", type=float, default=-38); s.add_argument("--min-gap", type=float, default=0.25)
    s.set_defaults(fn=cmd_split)
    pl = sub.add_parser("place"); pl.add_argument("timeline"); pl.add_argument("--duration", type=float, required=True); pl.add_argument("--out", required=True)
    pl.set_defaults(fn=cmd_place)
    a = p.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
