#!/usr/bin/env node
// Renders a scene frame by frame into an H.264 MP4, and its synthesized sound (if any) into a WAV.
//
//   node render.mjs scene.html --out film.mp4 [--fps 60] [--format v] [--query k=v&...]
//                   [--from 0 --to 5] [--crf 17] [--root dir] [--gpu]
//
// Writes film.mp4 (picture only) and film.sfx.wav when the scene defines window.renderAudio().
// Mix and mux with mix.py.
import { spawn } from "node:child_process";
import fs from "node:fs";
import { openScene, arg } from "./lib.mjs";

const argv = process.argv.slice(2);
const sceneFile = argv[0];
if (!sceneFile || sceneFile.startsWith("--")) {
  console.error("usage: render.mjs scene.html --out film.mp4 [--fps 60] [--format v] [--from s --to s] [--crf 17]");
  process.exit(2);
}
const out = arg(argv, "--out", "film.mp4");
const fps = Number(arg(argv, "--fps", 60));
const crf = arg(argv, "--crf", "17");
const format = arg(argv, "--format", "");
const query = [format && `format=${format}`, arg(argv, "--query", "")].filter(Boolean).join("&");

const { page, scene, close } = await openScene(sceneFile, { root: arg(argv, "--root"), query, argv });
const from = Number(arg(argv, "--from", 0)), to = Number(arg(argv, "--to", scene.duration));
const first = Math.round(from * fps), last = Math.round(to * fps); // frames [first, last)

if (from === 0 && to === scene.duration && await page.evaluate(() => typeof window.renderAudio === "function")) {
  const wav = out.replace(/\.mp4$/i, "") + ".sfx.wav";
  fs.writeFileSync(wav, Buffer.from(await page.evaluate(() => window.renderAudio()), "base64"));
  console.log(`sound: ${wav}`);
}

const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "png", "-i", "-",
  "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
  "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
  "-crf", String(crf), "-preset", "slow", "-movflags", "+faststart", out], { stdio: ["pipe", "inherit", "inherit"] });
const done = new Promise((ok, no) => ff.on("close", code => code === 0 ? ok() : no(new Error(`ffmpeg exited ${code}`))));

const t0 = Date.now();
for (let f = first; f < last; f++) {
  await page.evaluate(t => window.renderAt(t), f / fps);
  const png = await page.screenshot({ type: "png" });
  if (!ff.stdin.write(png)) await new Promise(r => ff.stdin.once("drain", r));
  const n = f - first + 1;
  if (n === 1 || n % fps === 0 || f === last - 1) {
    const per = (Date.now() - t0) / n / 1000;
    console.log(`frame ${n}/${last - first}  ${per.toFixed(2)} s/frame  ~${Math.round(per * (last - f - 1))} s left`);
  }
}
ff.stdin.end();
await done;
await close();
console.log(`video: ${out}  (${scene.width}x${scene.height}, ${fps} fps, ${((last - first) / fps).toFixed(2)} s)`);
