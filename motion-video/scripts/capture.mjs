#!/usr/bin/env node
// Screenshots a real page to use as footage (a texture or an overlay in the scene), and records where
// named elements sit so the scene can animate over them (type into a field, ring a value, wipe in a reply).
//
//   node capture.mjs URL out.png [--width 1600 --height 1000] [--scale 2] [--full]
//                    [--wait 1500] [--boxes "#entry,.total"] [--scroll "#messages:top"]
//                    [--cookies cookies.json] [--goto-first URL]
//
// --boxes writes out.json: { "#entry": {x, y, w, h}, ... } in screenshot pixels (already times --scale).
// --goto-first visits a URL first in the same browser (a one-time sign-in link, for example).
import fs from "node:fs";
import { loadPlaywright, arg } from "./lib.mjs";

const argv = process.argv.slice(2);
const [url, out] = argv;
if (!url || !out) { console.error("usage: capture.mjs URL out.png [--width --height --scale --full --wait --boxes sel,sel --goto-first URL]"); process.exit(2); }
const { chromium } = loadPlaywright();
const scale = Number(arg(argv, "--scale", 2));
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: Number(arg(argv, "--width", 1600)), height: Number(arg(argv, "--height", 1000)) },
  deviceScaleFactor: scale, reducedMotion: "reduce",
});
const cookies = arg(argv, "--cookies");
if (cookies) await context.addCookies(JSON.parse(fs.readFileSync(cookies, "utf8")));
const page = await context.newPage();
const first = arg(argv, "--goto-first");
if (first) await page.goto(first);
await page.goto(url);
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(Number(arg(argv, "--wait", 1000)));
// Hide carets and focus rings so the still is clean.
await page.addStyleTag({ content: "*{caret-color:transparent!important} *:focus{outline:none!important}" });

for (const spec of (arg(argv, "--scroll", "") || "").split(",").filter(Boolean)) {
  const [sel, where] = spec.split(":");
  await page.$eval(sel, (el, where) => { el.scrollTop = where === "bottom" ? el.scrollHeight : 0; }, where);
}
await page.screenshot({ path: out, fullPage: argv.includes("--full") });

const boxes = (arg(argv, "--boxes", "") || "").split(",").filter(Boolean);
if (boxes.length) {
  const found = {};
  for (const sel of boxes) {
    const b = await page.$eval(sel, el => { const r = el.getBoundingClientRect(); return { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height }; }).catch(() => null);
    found[sel] = b && Object.fromEntries(Object.entries(b).map(([k, v]) => [k, Math.round(v * scale)]));
  }
  fs.writeFileSync(out.replace(/\.(png|jpe?g)$/i, "") + ".json", JSON.stringify(found, null, 2));
}
await browser.close();
console.log(out);
