#!/usr/bin/env node
/* Build the walkthrough page from a build file.
 *
 *   node scripts/build.js build.js out.html [--standalone] [--no-verify]
 *
 * Runs the physics check first and refuses to build if it fails (--no-verify skips it, for a quick
 * look while you are still writing steps). Inlines assets/engine.js, the build file and assets/app.js
 * into assets/page.html and fills the title, About panel and links from PLAN.meta.
 *
 * The default output is the page body the Artifact tool expects (it adds the document skeleton).
 * --standalone writes a complete HTML document, for opening from disk or sending as a file.
 * The page loads three.js 0.160.0 from jsDelivr and fonts from Google Fonts; everything else is inline.
 */
const fs = require('fs');
const path = require('path');
const { load } = require('./load.js');
const args = process.argv.slice(2);
const [src, out] = args.filter(a => !a.startsWith('--'));
if (!src || !out) { console.error('usage: build.js build.js out.html [--standalone] [--no-verify]'); process.exit(2); }
const A = path.join(__dirname, '..', 'assets');

const P = load(src);
if (!args.includes('--no-verify')) {
  const r = P.verify({ samples: 24 });
  if (!r.ok) {
    console.error(`Physics check failed (${r.issues.length} issues). Run: node scripts/verify.js ${src}`);
    process.exit(1);
  }
  console.log(`physics check: PASS (${r.steps} steps, ${r.parts} parts, ${r.checks} checks)`);
}
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const m = P.meta;
const engine = fs.readFileSync(path.join(A, 'engine.js'), 'utf8');
const plan = fs.readFileSync(src, 'utf8');
const app = fs.readFileSync(path.join(A, 'app.js'), 'utf8');
for (const [n, t] of [['engine.js', engine], [src, plan], ['app.js', app]])
  if (/<\/script/i.test(t)) { console.error(n + ' contains "</script"; split the string so the page does not end early'); process.exit(1); }
const fill = {
  TITLE: esc(m.title),
  EYEBROW: esc(m.eyebrow),
  THING: esc(m.thing),
  INTRO: esc(m.intro || `Every part is modelled at its real size, in ${P.UNITS === 'mm' ? 'millimetres' : 'inches'}, so what you see here is what the cut list says.`),
  LOADING: esc(m.loading || `Cutting ${P.PARTS.filter(p => !p.decal && !P.BODY[p.body].temp).length} parts`),
  ABOUT: (m.about || []).map(([k, v]) => `      <dt>${esc(k)}</dt><dd>${esc(v)}</dd>\n`).join(''),
  LINKS: (m.links || []).map(([t, u]) => `    <p><a href="${esc(u)}" target="_blank" rel="noopener">${esc(t)}</a></p>\n`).join(''),
};
let html = fs.readFileSync(path.join(A, 'page.html'), 'utf8').replace(/\{\{(\w+)\}\}/g, (_, k) => {
  if (!(k in fill)) throw new Error('page.html has an unknown placeholder {{' + k + '}}');
  return fill[k];
});
// function replacers, so "$&" and friends in the sources are not treated as patterns
html = html.replace('/*PLAN_JS*/', () => engine + '\n' + plan).replace('/*APP_JS*/', () => app);
if (args.includes('--standalone')) html = standalone(html);
fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
fs.writeFileSync(out, html);
console.log(`wrote ${out} (${(html.length / 1024).toFixed(0)} KB)`);

function standalone(body) {
  return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
    + '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}[hidden]{display:none!important}</style></head><body>'
    + body + '</body></html>';
}
