// Shared harness for driving a running web app to capture screenshots, plain
// video, or annotated demo video. Standalone Playwright (recordVideo) — NOT
// playwright-cli. All annotation overlays are REAL DOM nodes (pointer-events:
// none), so they render into BOTH the video and any screenshot taken while
// they're up. That is the whole reason this is on standalone Playwright.
//
// Used by:
//   walkthrough.template.mjs  (screenshot-pages, record-video)
//   hero.template.mjs         (annotated-demo-video)
//
// THE SCROLL RULE (load-bearing — see tour/reveal below):
//   Never blind-scroll for a fixed duration. A demo that scrolls past the end
//   of a short page sits in dead whitespace and reads as "stuck". Always either
//   reveal() a specific element and hold on it, or tour() which STOPS at the
//   document bottom. Both are page-aware.

import { chromium } from "playwright";

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ── annotation reading time ───────────────────────────────────────────────
// How long to hold an annotation on screen, derived from its WORD COUNT — so a
// terse callout doesn't linger and a wordy chapter/summary panel stays up long
// enough to actually read. Replaces the magic-number `sleep(5000)` after an
// overlay. Strips HTML first (callout/summary/banner pass markup). The beat is
//   base + words / wpm,  clamped to [min, max].
// Knobs (defaults tuned for glanceable on-screen text, not prose):
//   wpm   reading speed — 200 is a comfortable pace for short overlay text
//   base  fixed "landing" beat to notice the overlay before reading starts
//   min   floor so even a 1–2 word callout holds a readable beat
//   max   ceiling so a wall of summary text still ends in reasonable time
export function readMs(text, { wpm = 200, base = 1200, min = 2200, max = 9000 } = {}) {
  const rate = wpm > 0 ? wpm : 200; // guard a 0/negative wpm from dividing the hold to Infinity
  const words = String(text ?? "")
    .replace(/<[^>]*>/g, " ") // drop HTML tags so markup doesn't inflate the count
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;
  const ms = base + (words / rate) * 60000;
  return Math.round(Math.min(max, Math.max(min, ms)));
}

// Hold the current annotation for a word-count-aware reading beat. Pass every
// piece of text that is on screen (title + body + label) so the beat matches
// what the viewer must actually read. Drop-in replacement for `sleep(<magic>)`.
//   await dwell(calloutHtml)
//   await dwell(title, description)         // chapter card
//   await dwell(title, ...rows.flat(), net) // summary panel
export const dwell = (...texts) => sleep(readMs(texts.filter(Boolean).join(" ")));

export const slug = (s) =>
  s.replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "").toLowerCase() || "root";

// ── session ──────────────────────────────────────────────────────────────
export async function createSession({
  recordVideoDir = null,
  viewport = { width: 1440, height: 900 },
  headless = true,
} = {}) {
  const browser = await chromium.launch({ headless });
  const context = await browser.newContext({
    ignoreHTTPSErrors: true, // puma-dev / local self-signed certs
    viewport,
    ...(recordVideoDir
      ? { recordVideo: { dir: recordVideoDir, size: viewport } }
      : {}),
  });
  const page = await context.newPage();
  return { browser, context, page };
}

export async function finalize(session) {
  const { browser, context, page } = session;
  await context.close(); // flushes the video file
  const video = page.video(); // null in screenshot mode (recordVideo not enabled)
  const videoPath = video ? await video.path().catch(() => null) : null;
  await browser.close();
  return videoPath;
}

// ── navigation (Turbo-safe) ──────────────────────────────────────────────
// Turbo Drive intercepts navigations and can abort page.goto with ERR_ABORTED.
// Commit-then-wait + retry rides over it.
export async function gotoSafe(page, url, { timeout = 60000, tries = 4 } = {}) {
  for (let i = 0; i < tries; i++) {
    try {
      await page.goto(url, { waitUntil: "commit", timeout });
      // load-state timeouts are non-fatal and expected on Turbo/SPA pages that
      // never reach networkidle — proceed once committed rather than fail.
      await page.waitForLoadState("domcontentloaded", { timeout: 30000 }).catch(() => {});
      await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
      return;
    } catch (e) {
      if (i < tries - 1 && /ERR_ABORTED|interrupted/.test(e.message)) {
        await sleep(800);
        continue;
      }
      throw e;
    }
  }
}

// Fill a login form if one is present; no-op if already authenticated.
// Returns true if a login was performed.
export async function login(
  page,
  {
    url,
    email,
    password,
    emailSelector = 'input[type="email"], input[name*="email" i]',
    passwordSelector = 'input[type="password"]',
    submitSelector = 'button[type="submit"], input[type="submit"]',
  }
) {
  await gotoSafe(page, url);
  await sleep(600);
  if (!(await page.locator(passwordSelector).count())) return false;
  await page.locator(emailSelector).first().fill(email);
  await page.locator(passwordSelector).first().fill(password);
  await Promise.all([
    page
      .waitForURL((u) => !/sign_in|login/.test(u.toString()), { timeout: 30000 })
      .catch(() => {}),
    page.locator(submitSelector).first().click(),
  ]);
  await sleep(1200);
  return true;
}

// ── real-DOM annotation overlays (show in video AND screenshots) ──────────
const FONT = "-apple-system,Segoe UI,Roboto,sans-serif";

export async function caption(page, text, { position = "bottom" } = {}) {
  await page.evaluate(
    ({ text, position, FONT }) => {
      let el = document.getElementById("__cap");
      if (!el) {
        el = document.createElement("div");
        el.id = "__cap";
        document.body.appendChild(el);
      }
      const edge = position === "top" ? "top:0;" : "bottom:0;";
      el.style.cssText =
        `position:fixed;${edge}left:0;right:0;z-index:2147483647;` +
        `background:#0d6efd;color:#fff;font:600 16px/1.5 ${FONT};` +
        `padding:10px 18px;box-shadow:0 2px 8px rgba(0,0,0,.3);` +
        `letter-spacing:.2px;pointer-events:none;`;
      el.textContent = text;
    },
    { text, position, FONT }
  );
}

export async function clearOverlays(page) {
  await page.evaluate(() => {
    document.getElementById("__cap")?.remove(); // caption banner
    document.querySelectorAll("[data-__ov]").forEach((n) => n.remove());
    document.querySelectorAll('[data-__hi="1"]').forEach((n) => {
      n.style.outline = "";
      n.style.outlineOffset = "";
      delete n.dataset.__hi;
    });
  });
}

// Red box around a located element + dark label. Falls back to a centered
// card when the element isn't found. Stays up until the next clearOverlays.
export async function callout(page, selector, html, { pos = "below", maxw = 580 } = {}) {
  const found = await page
    .locator(selector)
    .first()
    .scrollIntoViewIfNeeded({ timeout: 4000 })
    .then(() => true)
    .catch(() => false);
  await page.evaluate(
    ({ selector, html, pos, maxw, FONT, found }) => {
      const mk = (css, inner = "") => {
        const d = document.createElement("div");
        d.dataset.__ov = "1";
        d.style.cssText = css;
        d.innerHTML = inner;
        document.body.appendChild(d);
        return d;
      };
      const el = found ? document.querySelector(selector) : null;
      const box = el && el.getBoundingClientRect();
      if (!box || box.width === 0) {
        mk(
          `position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);max-width:${maxw}px;` +
            `padding:14px 18px;background:#111827;color:#fff;font:600 16px/1.45 ${FONT};` +
            `border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,.4);z-index:2147483646`,
          html
        );
        return;
      }
      mk(
        `position:fixed;top:${box.top - 5}px;left:${box.left - 5}px;width:${box.width + 10}px;` +
          `height:${box.height + 10}px;border:3px solid #ff3b30;border-radius:10px;` +
          `box-shadow:0 0 0 4px rgba(255,59,48,.18);pointer-events:none;z-index:2147483646`
      );
      const top = pos === "above" ? box.top - 14 : box.bottom + 12;
      const tf = pos === "above" ? "translate(-50%,-100%)" : "translateX(-50%)";
      const cx = Math.min(Math.max(box.left + box.width / 2, maxw / 2 + 12), window.innerWidth - maxw / 2 - 12);
      mk(
        `position:fixed;top:${top}px;left:${cx}px;transform:${tf};max-width:${maxw}px;` +
          `padding:11px 15px;background:#111827;color:#fff;font:600 15px/1.45 ${FONT};` +
          `border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.35);pointer-events:none;z-index:2147483646`,
        html
      );
    },
    { selector, html, pos, maxw, FONT, found }
  );
}

export async function banner(page, html) {
  await page.evaluate(
    ({ html, FONT }) => {
      const d = document.createElement("div");
      d.dataset.__ov = "1";
      d.style.cssText =
        `position:fixed;top:14px;left:50%;transform:translateX(-50%);max-width:1100px;` +
        `padding:12px 20px;background:rgba(17,24,39,.94);color:#fff;font:600 16px/1.45 ${FONT};` +
        `border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.35);text-align:center;` +
        `pointer-events:none;z-index:2147483646`;
      d.innerHTML = html;
      document.body.appendChild(d);
    },
    { html, FONT }
  );
}

export async function summary(page, title, rows, netHtml) {
  await page.evaluate(
    ({ title, rows, netHtml, FONT }) => {
      const body = rows
        .map(([m, h]) => {
          const color = m === "✓" ? "#22c55e" : "#ef4444";
          return `<div style="color:${color};font-weight:800">${m}</div><div>${h}</div>`;
        })
        .join("");
      const d = document.createElement("div");
      d.dataset.__ov = "1";
      d.style.cssText =
        `position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);width:860px;` +
        `padding:26px 30px;background:#0b1220;color:#e5e7eb;border:1px solid #334155;` +
        `border-radius:16px;box-shadow:0 18px 50px rgba(0,0,0,.5);font:400 16px/1.6 ${FONT};` +
        `pointer-events:none;z-index:2147483646`;
      d.innerHTML =
        `<div style="font:800 22px/1.2 ${FONT};color:#fff;margin-bottom:14px">${title}</div>` +
        `<div style="display:grid;grid-template-columns:22px 1fr;gap:8px 12px">${body}</div>` +
        `<div style="margin-top:16px;padding-top:14px;border-top:1px solid #334155;color:#fca5a5;font-weight:700">${netHtml}</div>`;
      document.body.appendChild(d);
    },
    { title, rows, netHtml, FONT }
  );
}

// ── THE SCROLL RULE ──────────────────────────────────────────────────────
// Page-aware downward scroll that STOPS at the document bottom. maxMs is only
// a safety cap for very long pages — never the timing source.
export async function tour(page, { maxMs = 4000, step = 320 } = {}) {
  await page.evaluate(() => window.scrollTo({ top: 0 }));
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    const atBottom = await page.evaluate(() => {
      const d = document.documentElement;
      return window.scrollY + window.innerHeight >= d.scrollHeight - 4;
    });
    if (atBottom) break;
    await page.mouse.wheel(0, step);
    await sleep(500);
  }
  await sleep(900); // settle on final content, not blank space
}

// Bring a specific element to center, outline it, hold. The right tool when
// you want to draw the eye to the thing that changed. Returns false (no-op) if
// the selector isn't found, so callers can fall back to tour().
export async function reveal(page, selector, { hold = 3000, outline = true } = {}) {
  const loc = page.locator(selector).first();
  if (!(await loc.count())) return false;
  await loc.scrollIntoViewIfNeeded({ timeout: 4000 }).catch(() => {});
  await loc
    .evaluate(
      (el, outline) => {
        const box = el.closest("section, .card, table, .table, tr, div") || el;
        if (outline) {
          box.style.outline = "3px solid #0d6efd";
          box.style.outlineOffset = "2px";
          box.dataset.__hi = "1";
        }
        box.scrollIntoView({ block: "center" });
      },
      outline
    )
    .catch(() => {});
  await sleep(hold);
  return true;
}

// ── capture ──────────────────────────────────────────────────────────────
export async function shot(page, path, { fullPage = false } = {}) {
  await page.screenshot({ path, fullPage }).catch(() => {});
}
