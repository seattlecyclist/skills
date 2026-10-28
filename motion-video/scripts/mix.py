#!/usr/bin/env python3
"""Mixes a film's sound and muxes it onto the picture.

  mix.py film.mp4 --out final.mp4 [--sfx film.sfx.wav] [--vo vo-track.wav]
         [--lufs -14] [--tp -2] [--bed 0.8] [--voice 1.25] [--no-duck]

The effects-and-music bed ducks under the voice (sidechain compression), the two are summed, and the
mix is normalized in two passes (measure, then one gain and a limiter) to the target integrated loudness and true peak (-14 LUFS and -2 dBTP
suit web and social). Prints the measured result. Needs ffmpeg only.
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path


def ff(*args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-y", *args], capture_output=True, text=True, check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video"); p.add_argument("--out", required=True)
    p.add_argument("--sfx"); p.add_argument("--vo")
    p.add_argument("--lufs", type=float, default=-14); p.add_argument("--tp", type=float, default=-2)
    p.add_argument("--bed", type=float, default=0.8, help="bed gain when a voice is present")
    p.add_argument("--voice", type=float, default=1.25, help="voice gain")
    p.add_argument("--no-duck", action="store_true")
    a = p.parse_args()
    if not a.sfx and not a.vo:
        sys.exit("Give --sfx and/or --vo.")

    tmp = Path(tempfile.mkdtemp())
    raw = tmp / "mix-raw.wav"
    if a.sfx and a.vo:
        duck = "[0][sc]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=300[bed];" if not a.no_duck else "[0]anull[bed];[sc]anullsink;"
        graph = f"[1]asplit[vo][sc];{duck}[bed][vo]amix=inputs=2:weights='{a.bed} {a.voice}':normalize=0[m]"
        ff("-i", a.sfx, "-i", a.vo, "-filter_complex", graph, "-map", "[m]", "-ar", "48000", str(raw))
    else:
        ff("-i", a.sfx or a.vo, "-ar", "48000", str(raw))

    # pass 1: measure
    target = f"I={a.lufs}:TP={a.tp}:LRA=11"
    log = ff("-i", str(raw), "-af", f"loudnorm={target}:print_format=json", "-f", "null", "-").stderr
    m = json.loads(log[log.rindex("{"):log.rindex("}") + 1])
    # pass 2: a linear gain to the target, then a true-peak-safe limiter for the transients (knocks,
    # thuds) the gain pushes over the ceiling. Limiting lowers loudness, so re-measure and top up the
    # gain until within 0.3 LU. Half a dB of headroom covers the AAC encode.
    gain = a.lufs - float(m["input_i"])
    ceiling = 10 ** ((a.tp - 0.5) / 20)
    mix = tmp / "mix.wav"
    for _ in range(5):
        ff("-i", str(raw), "-af", f"volume={gain:.2f}dB,alimiter=limit={ceiling:.4f}:attack=1:release=60:level=disabled:asc=1",
           "-ar", "48000", str(mix))
        got = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", ff("-i", str(mix), "-af", "ebur128", "-f", "null", "-").stderr)[-1])
        if abs(got - a.lufs) < 0.3: break
        gain += a.lufs - got

    ff("-i", a.video, "-i", str(mix), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", "-shortest", a.out)
    report = ff("-i", a.out, "-af", "ebur128=peak=true", "-f", "null", "-").stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", report)[-1]
    peak = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", report)[-1]
    print(f"final: {a.out}  integrated {i} LUFS, true peak {peak} dBTP")


if __name__ == "__main__":
    main()
