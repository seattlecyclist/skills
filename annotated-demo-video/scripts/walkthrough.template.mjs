// Walkthrough runner — copy this, fill CONFIG, run with node. Drives a list of
// surfaces and captures either screenshots or a plain (optionally captioned)
// video. Used by the `screenshot-pages` and `record-video` skills.
//
//   cp $WT/scripts/walkthrough.template.mjs /tmp/run.mjs
//   # edit CONFIG, then (from a scratch dir that has playwright installed — see SKILL.md):
//   MODE=screenshots node /tmp/run.mjs
//   MODE=video CAPTIONS=1 node /tmp/run.mjs
//
// Env knobs (all optional):
//   MODE=screenshots|video   (default screenshots)
//   CAPTIONS=0               (disable the on-screen caption banner)
//   OUT=<dir>                (output dir; default .playwright-mcp)
//   LIB=<path to lib.mjs>    (default resolves next to this file)

import { fileURLToPath } from "node:url";
import path from "node:path";

const LIB = process.env.LIB || path.join(path.dirname(fileURLToPath(import.meta.url)), "lib.mjs");
const { createSession, finalize, login, gotoSafe, caption, tour, reveal, shot, slug, sleep } =
  await import(LIB);

const MODE = process.env.MODE || "screenshots"; // screenshots | video
const CAPTIONS = process.env.CAPTIONS !== "0";
const OUT = process.env.OUT || ".playwright-mcp";

// ── CONFIG — fill this in ─────────────────────────────────────────────────
const CONFIG = {
  base: "http://localhost:3000",
  // Omit `login` if the surfaces are public.
  login: {
    url: "http://localhost:3000/<login-path>",
    email: "admin@example.com",
    password: "<password>",
  },
  // Each surface: { path, caption?, reveal?, fullPage? }
  //   reveal: a selector or `text=...` to center-and-hold on (the changed thing).
  //           If omitted, falls back to a page-aware tour() that stops at bottom.
  surfaces: [
    { path: "/", caption: "Home", reveal: "h1" },
    // { path: "/orders/<id>", caption: "An order", reveal: "text=Order summary" },
  ],
};
// ──────────────────────────────────────────────────────────────────────────

(async () => {
  const session = await createSession({
    recordVideoDir: MODE === "video" ? `${OUT}/_video` : null,
  });
  const { page } = session;

  if (CONFIG.login) await login(page, CONFIG.login);

  for (const s of CONFIG.surfaces) {
    await gotoSafe(page, CONFIG.base + s.path);
    if (CAPTIONS && s.caption) await caption(page, s.caption);
    await sleep(400);
    if (s.reveal) {
      const ok = await reveal(page, s.reveal);
      if (!ok) await tour(page);
    } else {
      await tour(page);
    }
    if (MODE !== "video") {
      await shot(page, `${OUT}/${slug(s.path)}.png`, { fullPage: !!s.fullPage });
    }
    console.log(`SURFACE ${s.path} :: ${await page.title().catch(() => "")}`);
  }

  const video = await finalize(session);
  console.log("RESULT " + JSON.stringify({ mode: MODE, out: OUT, video }));
})();
