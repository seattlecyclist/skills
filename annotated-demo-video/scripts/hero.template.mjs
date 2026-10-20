// Annotated demo / bug-repro runner — copy this, fill the SCENE, run with node.
// Records a narrated video with real-DOM chapter cards, callouts, and a closing
// summary panel (all show in stills too). Used by the `annotated-demo-video` skill.
//
//   cp $WT/scripts/hero.template.mjs /tmp/<id>_hero.mjs
//   # edit CONFIG + SCENE, then (from a scratch dir with playwright installed):
//   node /tmp/<id>_hero.mjs
//   # then: bash $WT/scripts/verify.sh tmp/demos/_video <id>   (contact sheet + mp4)

import { fileURLToPath } from "node:url";
import path from "node:path";

const LIB = process.env.LIB || path.join(path.dirname(fileURLToPath(import.meta.url)), "lib.mjs");
const lib = await import(LIB);
const { createSession, finalize, login, gotoSafe, caption, callout, banner, summary, reveal, clearOverlays, sleep, readMs, dwell } = lib;

const OUT = process.env.OUT || "/tmp/demos";

const CONFIG = {
  id: "<ID>",
  base: "http://localhost:3000",
  login: {
    url: "http://localhost:3000/<login-path>",
    email: "admin@example.com",
    password: "<password>",
  },
};

// A real-DOM "chapter card": full-screen title + description. Held for a
// word-count-aware reading beat by default (pass `ms` to force a fixed hold).
async function chapter(page, title, description, ms = readMs(`${title} ${description}`)) {
  await page.evaluate(
    ({ title, description }) => {
      const d = document.createElement("div");
      d.dataset.__ov = "1";
      d.style.cssText =
        "position:fixed;inset:0;z-index:2147483647;background:#0b1220;color:#fff;" +
        "display:flex;flex-direction:column;align-items:center;justify-content:center;" +
        "font:600 16px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;text-align:center;padding:0 12%";
      d.innerHTML =
        `<div style="font:800 30px/1.25 inherit;margin-bottom:14px">${title}</div>` +
        `<div style="max-width:760px;color:#cbd5e1">${description}</div>`;
      document.body.appendChild(d);
    },
    { title, description }
  );
  await sleep(ms);
  await clearOverlays(page);
}

(async () => {
  const session = await createSession({ recordVideoDir: `${OUT}/_video` });
  const { page } = session;
  await login(page, CONFIG.login);

  // ── SCENE ────────────────────────────────────────────────────────────────
  // 1. Thesis chapter card
  await chapter(page, `${CONFIG.id} · <one-line thesis>`, "<2 sentences of plain-English context>");

  // 2. Setup
  await gotoSafe(page, `${CONFIG.base}/<setup-page>`);
  const setupText = "Setup: <who / plan / amount / state>.";
  await banner(page, setupText);
  await dwell(setupText); // hold ∝ word count — never a magic-number sleep
  await clearOverlays(page);

  // 3. Action → live-read the wrong value into the callout (never hardcode it)
  await gotoSafe(page, `${CONFIG.base}/<action-page>`);
  const shown =
    (await page.evaluate(() => (document.querySelector("<result-selector>")?.textContent || "").trim())) ||
    "<fallback>";
  const calloutText = `The app shows <b>${shown}</b> — should be <b><expected></b>.`;
  await callout(page, "<result-region-selector>", calloutText, { pos: "above" });
  await dwell(calloutText); // longer label → longer hold, automatically
  await clearOverlays(page);

  // 4. Why + summary
  await chapter(page, "Why", "<root cause in one line>"); // chapter auto-holds for reading time
  const sumTitle = `${CONFIG.id} — what actually happened`;
  const sumRows = [
    ["✗", "<cause 1, naming the method/file>"],
    ["✗", "<cause 2>"],
    ["✗", "<consequence>"],
  ];
  const sumNet = "Net: <one-line impact>.";
  await summary(page, sumTitle, sumRows, sumNet);
  await dwell(sumTitle, ...sumRows.flat(), sumNet); // dense panel → near the max hold
  // ──────────────────────────────────────────────────────────────────────────

  const video = await finalize(session);
  console.log("VIDEO " + video + "  (run verify.sh to extract frames + mp4)");
})();
