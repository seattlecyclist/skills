// Shared helpers for the motion-video scripts: find Playwright, serve a folder, open a scene.
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);

// Playwright from the current project, then from the global npm root.
export function loadPlaywright() {
  for (const from of [process.cwd() + "/", import.meta.url]) {
    try { return createRequire(from)("playwright"); } catch {}
  }
  try {
    const root = execSync("npm root -g", { encoding: "utf8" }).trim();
    return require(path.join(root, "playwright"));
  } catch {}
  throw new Error("Playwright not found. Run `npm i playwright` (and `npx playwright install chromium` outside cloud containers).");
}

const TYPES = {
  ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json",
  ".css": "text/css", ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf",
  ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".svg": "image/svg+xml", ".webp": "image/webp",
  ".glb": "model/gltf-binary", ".gltf": "model/gltf+json", ".wav": "audio/wav", ".mp3": "audio/mpeg",
};

// A static server on a free port, rooted at `root`. Scenes load fonts, textures and modules from it.
export function serve(root) {
  const server = http.createServer((req, res) => {
    const rel = decodeURIComponent(req.url.split("?")[0]);
    const file = path.join(root, rel);
    if (!file.startsWith(path.resolve(root))) { res.writeHead(403); return res.end(); }
    fs.readFile(file, (err, data) => {
      if (err) { res.writeHead(404); return res.end(); }
      res.writeHead(200, { "content-type": TYPES[path.extname(file).toLowerCase()] || "application/octet-stream" });
      res.end(data);
    });
  });
  return new Promise(ok => server.listen(0, () => ok({ server, port: server.address().port })));
}

// SwiftShader WebGL works everywhere, GPU or not. Pass --gpu to use the machine's GPU instead.
export function launchArgs(argv) {
  return argv.includes("--gpu") ? ["--ignore-gpu-blocklist", "--enable-gpu-rasterization"]
    : ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"];
}

// Opens a scene and waits for its contract: window.scene {width, height, duration}, window.renderAt(t),
// window.ready. Query params (format=v and anything else) pass straight through to the page.
export async function openScene(sceneFile, { root, query = "", argv = [] } = {}) {
  const { chromium } = loadPlaywright();
  const abs = path.resolve(sceneFile);
  root = path.resolve(root || path.dirname(abs));
  const rel = path.relative(root, abs).split(path.sep).join("/");
  if (rel.startsWith("..")) throw new Error(`--root ${root} must contain the scene ${abs}`);
  const { server, port } = await serve(root);
  const browser = await chromium.launch({ args: launchArgs(argv) });
  // Read the size first on a throwaway page, then open the real page at exactly that viewport.
  const probe = await browser.newPage();
  const url = `http://localhost:${port}/${rel}${query ? "?" + query : ""}`;
  const errors = [];
  probe.on("pageerror", e => errors.push(e.message));
  await probe.goto(url);
  await probe.waitForFunction(() => window.ready === true, null, { timeout: 120000 }).catch(() => {
    throw new Error(`Scene never set window.ready. Page errors: ${errors.join(" | ") || "none"}`);
  });
  const scene = await probe.evaluate(() => ({ ...window.scene }));
  await probe.close();
  if (!scene.width || !scene.height || !scene.duration) throw new Error("window.scene needs width, height and duration");
  const page = await browser.newPage({ viewport: { width: scene.width, height: scene.height } });
  page.on("pageerror", e => console.error("page error:", e.message));
  await page.goto(url);
  await page.waitForFunction(() => window.ready === true, null, { timeout: 120000 });
  return { page, scene, close: async () => { await browser.close(); server.close(); } };
}

export function arg(argv, name, fallback) {
  const i = argv.indexOf(name);
  return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : fallback;
}
