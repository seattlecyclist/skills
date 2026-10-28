#!/usr/bin/env node
// Renders chosen moments of a scene to PNGs plus a contact sheet. Check these before a full render:
// a full render costs about a second per frame, a still costs one.
//
//   node stills.mjs scene.html --out stills/ [--times 1,3.5,8] [--count 8] [--format v] [--cols 4] [--root dir]
//
// Without --times, --count moments are spread evenly over the film (default 8).
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { openScene, arg } from "./lib.mjs";

const argv = process.argv.slice(2);
const sceneFile = argv[0];
if (!sceneFile || sceneFile.startsWith("--")) { console.error("usage: stills.mjs scene.html --out dir [--times a,b,c | --count n] [--format v]"); process.exit(2); }
const out = arg(argv, "--out", "stills");
const format = arg(argv, "--format", "");
const query = [format && `format=${format}`, arg(argv, "--query", "")].filter(Boolean).join("&");
fs.mkdirSync(out, { recursive: true });

const { page, scene, close } = await openScene(sceneFile, { root: arg(argv, "--root"), query, argv });
let times = arg(argv, "--times", "");
const count = Number(arg(argv, "--count", 8));
times = times ? times.split(",").map(Number)
  : Array.from({ length: count }, (_, i) => +(scene.duration * (i + 0.5) / count).toFixed(2));

const files = [];
for (const [i, t] of times.entries()) {
  await page.evaluate(t => window.renderAt(t), t);
  const file = path.join(out, `${String(i).padStart(2, "0")}-t${t}.png`);
  await page.screenshot({ path: file });
  files.push(file);
}
await close();

// Contact sheet: each still scaled to 480 px wide with its time burned in, tiled.
const cols = Number(arg(argv, "--cols", scene.width >= scene.height ? 4 : 6));
const rows = Math.ceil(files.length / cols);
const inputs = files.flatMap(f => ["-i", f]);
const w = 480, h = Math.round(w * scene.height / scene.width / 2) * 2;
const labelled = files.map((f, i) =>
  `[${i}]scale=${w}:${h},drawbox=x=0:y=0:w=110:h=34:color=black@0.6:t=fill,drawtext=text='${times[i]}s':x=10:y=8:fontsize=20:fontcolor=white[s${i}]`).join(";");
const pads = Array.from({ length: rows * cols - files.length }, (_, k) => `color=c=gray:s=${w}x${h}:d=1[p${k}]`).join(";");
const all = [...files.map((_, i) => `[s${i}]`), ...Array.from({ length: rows * cols - files.length }, (_, k) => `[p${k}]`)].join("");
const layout = Array.from({ length: rows * cols }, (_, i) => `${(i % cols) * w}_${Math.floor(i / cols) * h}`).join("|");
const graph = [labelled, pads, `${all}xstack=inputs=${rows * cols}:layout=${layout}[out]`].filter(Boolean).join(";");
const sheet = path.join(out, "sheet.png");
try {
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", ...inputs, "-filter_complex", graph, "-map", "[out]", "-frames:v", "1", sheet]);
} catch {
  // drawtext needs an ffmpeg built with freetype; fall back to an unlabelled sheet
  const plain = files.map((_, i) => `[${i}]scale=${w}:${h}[s${i}]`).join(";");
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", ...inputs, "-filter_complex", [plain, pads, `${all}xstack=inputs=${rows * cols}:layout=${layout}[out]`].filter(Boolean).join(";"), "-map", "[out]", "-frames:v", "1", sheet]);
}
console.log(files.join("\n"));
console.log(`sheet: ${sheet}`);
