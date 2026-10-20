// annotate.js: draws walkthrough overlays into any page. Inject it, then call:
//
//   __wt.setTheme(theme)                                    // optional, see assets/theme.json
//   __wt.titleCard({ kicker, title, body, height })         // full-viewport title slide, returns 0
//   __wt.frame({ selector, target, title, body, count,      // highlight + caption card,
//                height, side })                            //   returns the scroll offset to crop at
//   __wt.clear()                                            // removes every overlay
//   await __wt.ready()                                      // theme fonts loaded; call before each shot
//
// Overlays are absolutely positioned in document coordinates and the page is never scrolled, so a
// full-page screenshot cropped at [offset, offset + height] always shows the highlight and its card
// together. That is what keeps frames from coming out blank or misaligned after scrolling.
(function () {
  const DEFAULT = {
    accent: "#5B3FD6", card_bg: "#15132A", card_text: "#FFFFFF", card_body: "#E6E2FF", kicker: "#CFC3FF",
    dim: "rgba(21,19,42,.38)", title_bg: "linear-gradient(135deg,#15132A,#2A2152)",
    display_font: "Outfit, 'Helvetica Neue', system-ui, sans-serif",
    body_font: "'Hanken Grotesk', 'Helvetica Neue', system-ui, sans-serif",
    mono_font: "'Azeret Mono', ui-monospace, Menlo, monospace"
  };
  let T = Object.assign({}, DEFAULT, window.__wtTheme || {});

  function el(tag, css, text) {
    const e = document.createElement(tag);
    if (css) e.style.cssText = css;
    if (text != null) e.textContent = text;
    return e;
  }

  function clear() {
    document.querySelectorAll("[data-wt]").forEach(e => e.remove());
  }

  function viewportHeight(h) { return h || window.innerHeight; }

  function titleCard({ kicker = "", title, body = "", height } = {}) {
    clear();
    const H = viewportHeight(height);
    const box = el("div", `position:absolute;left:0;top:0;width:100%;height:${H}px;box-sizing:border-box;z-index:2147483646;` +
      `display:flex;flex-direction:column;justify-content:center;padding:0 120px;gap:18px;background:${T.title_bg};color:${T.card_text}`);
    box.dataset.wt = "";
    if (kicker) box.appendChild(el("div", `font:500 14px ${T.mono_font};letter-spacing:.14em;text-transform:uppercase;color:${T.kicker}`, kicker));
    box.appendChild(el("h2", `font:700 64px/1.05 ${T.display_font};letter-spacing:-.03em;margin:0;max-width:14em;color:${T.card_text}`, title));
    if (body) box.appendChild(el("p", `font:400 24px/1.4 ${T.body_font};margin:0;max-width:36em;color:${T.card_body}`, body));
    document.documentElement.appendChild(box);
    return 0;
  }

  function frame({ selector, target, title, body = "", count = "", height, side = "right" } = {}) {
    clear();
    const H = viewportHeight(height);
    const node = document.querySelector(target || selector);
    if (!node) throw new Error(`walkthrough: nothing matches ${target || selector}`);
    const sx = window.scrollX, sy = window.scrollY;
    const r = node.getBoundingClientRect();
    const top = r.top + sy, left = r.left + sx, bottom = top + r.height;
    const docH = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
    const offset = Math.round(Math.max(0, Math.min(top + r.height / 2 - H / 2, docH - H)));

    const ring = el("div", `position:absolute;left:${left - 8}px;top:${top - 8}px;width:${r.width + 16}px;height:${r.height + 16}px;` +
      `border:3px solid ${T.accent};border-radius:14px;box-shadow:0 0 0 99999px ${T.dim};z-index:2147483645;pointer-events:none;box-sizing:border-box`);
    ring.dataset.wt = "";

    const card = el("div", `position:absolute;${side}:28px;width:440px;z-index:2147483646;background:${T.card_bg};color:${T.card_text};` +
      `border-radius:16px;padding:18px 20px;box-shadow:0 18px 40px rgba(0,0,0,.35);display:flex;flex-direction:column;gap:6px;box-sizing:border-box`);
    card.dataset.wt = "";
    if (count) card.appendChild(el("div", `font:500 12px ${T.mono_font};letter-spacing:.12em;color:${T.kicker}`, count));
    card.appendChild(el("b", `font:700 22px/1.2 ${T.display_font};letter-spacing:-.02em`, title));
    if (body) card.appendChild(el("p", `font:400 16px/1.45 ${T.body_font};margin:0;color:${T.card_body}`, body));

    document.documentElement.appendChild(ring);
    document.documentElement.appendChild(card);
    // The card goes at the bottom of the cropped frame unless that would cover the highlight.
    const ch = card.getBoundingClientRect().height;
    const fitsBelow = (bottom - offset) + ch + 40 < H;
    card.style.top = (fitsBelow ? offset + H - ch - 24 : offset + 24) + "px";
    return offset;
  }

  function setTheme(theme) { T = Object.assign({}, DEFAULT, theme || {}); }

  // Loads the theme's font stylesheet once (it survives clear()), then waits until every font the
  // overlays use has loaded, so the first frame never shows fallback type.
  async function ready() {
    if (T.font_css && !document.querySelector("link[data-wt-font]")) {
      const link = document.createElement("link");
      link.rel = "stylesheet"; link.href = T.font_css; link.dataset.wtFont = "";
      const loaded = new Promise(r => { link.onload = link.onerror = r; });
      document.head.appendChild(link);
      await Promise.race([loaded, new Promise(r => setTimeout(r, 5000))]);
    }
    const fams = [`700 22px ${T.display_font}`, `400 16px ${T.body_font}`, `500 12px ${T.mono_font}`];
    await Promise.all(fams.map(f => document.fonts.load(f).catch(() => null)));
    document.documentElement.offsetHeight;
    await document.fonts.ready;
  }

  window.__wt = { titleCard, frame, clear, setTheme, ready };
})();
