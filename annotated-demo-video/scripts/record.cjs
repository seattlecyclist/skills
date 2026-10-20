#!/usr/bin/env node
// record.cjs: drives a web app through a storyboard with Playwright and writes annotated frames.
//
//   node record.cjs storyboard.json --out ./walkthrough
//
// Writes <out>/frames/NN.png (already cropped to the viewport) and <out>/manifest.json, which
// finish.py turns into the MP4, the contact sheet and the HTML player. See SKILL.md for the
// storyboard format. Every run with the same storyboard and app state gives the same frames:
// fixed viewport and scale, animations and carets off, fonts awaited, clock optionally frozen.
const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

function loadPlaywright() {
  const roots = [process.cwd(), ...(process.env.NODE_PATH || "").split(path.delimiter).filter(Boolean),
    "/opt/node22/lib/node_modules", "/usr/local/lib/node_modules", "/usr/lib/node_modules"];
  for (const root of roots) {
    try { return createRequire(path.join(root, "noop.js"))("playwright"); } catch (_) {}
    try { return require(path.join(root, "playwright")); } catch (_) {}
  }
  throw new Error("Playwright not found. Install it (npm i -D playwright) or set NODE_PATH to a folder that has it.");
}

function args() {
  const a = process.argv.slice(2);
  const out = { storyboard: null, out: "walkthrough", headed: false };
  for (let i = 0; i < a.length; i++) {
    if (a[i] === "--out") out.out = a[++i];
    else if (a[i] === "--headed") out.headed = true;
    else if (!out.storyboard) out.storyboard = a[i];
  }
  if (!out.storyboard) { console.error("usage: node record.cjs storyboard.json [--out dir] [--headed]"); process.exit(2); }
  return out;
}

const STILL = `*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important;scroll-behavior:auto!important}`;

// A locator from a step: { selector }, { text }, { role, name }, { label } or { placeholder }.
function locate(page, s) {
  if (s.selector) return page.locator(s.selector).first();
  if (s.role) return page.getByRole(s.role, s.name ? { name: s.name, exact: !!s.exact } : {}).first();
  if (s.label) return page.getByLabel(s.label, { exact: !!s.exact }).first();
  if (s.placeholder) return page.getByPlaceholder(s.placeholder).first();
  if (s.text) return page.getByText(s.text, { exact: !!s.exact }).first();
  throw new Error(`step needs selector, text, role, label or placeholder: ${JSON.stringify(s)}`);
}

async function gotoSafe(page, url) {
  for (let i = 0; ; i++) {
    try { return await page.goto(url, { waitUntil: "networkidle" }); }
    catch (e) { if (i >= 3 || !/ERR_ABORTED|interrupted by another navigation/.test(e.message)) throw e; await page.waitForTimeout(300); }
  }
}

async function live(page, text) {
  if (!text || !text.includes("{{")) return text;
  const parts = [...text.matchAll(/\{\{\s*(.+?)\s*\}\}/g)];
  let out = text;
  for (const [whole, sel] of parts) {
    let value;
    try { value = await page.locator(sel).first().innerText({ timeout: 5000 }); }
    catch (e) { throw new Error(`live value {{ ${sel} }} not found on ${page.url()}: ${e.message.split("\n")[0]}`); }
    out = out.replace(whole, value.trim().replace(/\s+/g, " "));
  }
  return out;
}

async function act(page, step, base, dir) {
  const url = u => new URL(u, base).toString();
  switch (step.action) {
    case "goto": return gotoSafe(page, url(step.url));
    case "click": return locate(page, step).click();
    case "fill": return locate(page, step).fill(String(step.value));
    case "select": return locate(page, step).selectOption(step.value);
    case "check": return locate(page, step).check();
    case "press": return page.keyboard.press(step.key);
    case "hover": return locate(page, step).hover();
    case "upload": return locate(page, step).setInputFiles([].concat(step.files).map(f => path.resolve(dir, f)));
    case "wait_for": return (step.text ? page.getByText(step.text, { exact: !!step.exact }) : page.locator(step.selector)).first().waitFor({ timeout: step.timeout || 30000 });
    case "wait_url": return page.waitForURL(step.url.includes("*") ? step.url : url(step.url));
    case "wait_ms": return page.waitForTimeout(step.ms);
    case "eval": return page.evaluate(step.js);
    case "resize": return page.setViewportSize({ width: step.width, height: step.height });
    default: throw new Error(`unknown action ${step.action}`);
  }
}

(async () => {
  const opt = args();
  const sbPath = path.resolve(opt.storyboard);
  const dir = path.dirname(sbPath);
  const sb = JSON.parse(fs.readFileSync(sbPath, "utf8"));
  const W = sb.viewport?.width || 1440, H = sb.viewport?.height || 900;
  const theme = Object.assign({}, JSON.parse(fs.readFileSync(path.join(__dirname, "../assets/theme.json"), "utf8")),
    sb.theme_file ? JSON.parse(fs.readFileSync(path.resolve(dir, sb.theme_file), "utf8")) : {}, sb.theme || {});
  const out = path.resolve(opt.out), frames = path.join(out, "frames");
  fs.rmSync(frames, { recursive: true, force: true });
  fs.mkdirSync(frames, { recursive: true });

  const { chromium } = loadPlaywright();
  const exe = process.env.CHROMIUM_PATH || (fs.existsSync("/opt/pw-browsers/chromium") && !process.env.PLAYWRIGHT_BROWSERS_PATH ? "/opt/pw-browsers/chromium" : undefined);
  const browser = await chromium.launch({ headless: !opt.headed, executablePath: exe });
  const context = await browser.newContext({
    viewport: { width: W, height: H }, deviceScaleFactor: 1, reducedMotion: "reduce",
    locale: sb.locale || "en-US", timezoneId: sb.timezone || "UTC", colorScheme: sb.color_scheme || "light"
  });
  const page = await context.newPage();
  if (sb.freeze_time) await page.clock.setFixedTime(new Date(sb.freeze_time));
  const annotate = fs.readFileSync(path.join(__dirname, "annotate.js"), "utf8");
  await page.addInitScript(`window.__wtTheme = ${JSON.stringify(theme)};`);
  await page.addInitScript(annotate);
  page.on("load", () => page.addStyleTag({ content: STILL }).catch(() => {}));

  const steps = sb.steps || [];
  const total = steps.filter(s => s.shot && s.shot.type !== "title").length;
  const manifest = { title: sb.title, kicker: sb.kicker || "", note: sb.note || "", viewport: { width: W, height: H }, theme, frames: [] };
  let n = 0, chapter = "";
  if (sb.base_url) await gotoSafe(page, sb.base_url);

  for (const [i, step] of steps.entries()) {
    try {
      for (const a of step.do || []) await act(page, a, sb.base_url || page.url(), dir);
      if (!step.shot) continue;
      const shot = { ...step.shot, title: await live(page, step.shot.title), body: await live(page, step.shot.body) };
      await page.addStyleTag({ content: STILL });
      await page.evaluate(keep => { window.scrollTo(0, 0); if (!keep) document.activeElement?.blur(); }, !!shot.keep_focus);
      let offset;
      if (shot.type === "title") {
        offset = await page.evaluate(o => __wt.titleCard(o), { kicker: shot.kicker ?? sb.kicker, title: shot.title, body: shot.body, height: H });
      } else {
        n += 1;
        if (shot.chapter) chapter = shot.chapter;
        const count = [sb.show_chapter !== false && chapter, sb.show_count !== false && `${n} / ${total}`].filter(Boolean).join("  ·  ");
        offset = await page.evaluate(o => __wt.frame(o), { selector: shot.selector, target: shot.target, title: shot.title, body: shot.body,
          count, height: H, side: shot.side || "right" });
      }
      await page.evaluate(() => __wt.ready());
      await page.waitForTimeout(150);
      const file = `${String(manifest.frames.length).padStart(2, "0")}.png`;
      await page.screenshot({ path: path.join(frames, file), fullPage: true, clip: { x: 0, y: offset, width: W, height: H }, animations: "disabled", caret: "hide" });
      await page.evaluate(() => __wt.clear());
      manifest.frames.push({ file, offset: 0, kind: shot.type === "title" ? "title" : "frame", title: shot.title, body: shot.body || "", chapter: shot.chapter || null });
      console.log(`${file}  ${shot.title}`);
    } catch (e) {
      await page.screenshot({ path: path.join(out, "failed-step.png"), fullPage: true }).catch(() => {});
      console.error(`step ${i + 1} failed: ${e.message}\n(see ${path.join(out, "failed-step.png")})`);
      await browser.close();
      process.exit(1);
    }
  }
  fs.writeFileSync(path.join(out, "manifest.json"), JSON.stringify(manifest, null, 2));
  await browser.close();
  console.log(`${manifest.frames.length} frames -> ${out}`);
})();
