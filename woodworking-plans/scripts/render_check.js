#!/usr/bin/env node
/* One command to look at a built plan: build it, open it in Chromium (Playwright), and report.
 *
 *   node scripts/render_check.js plan.js [--out dir] [--libs dir] [--pdf]
 *
 * Writes into --out (default: ./render-check): plan.html, desktop.png (whole page), viewer.png
 * (the 3D view), plate-<section>.png (each Material List exploded view), phone.png, and with --pdf,
 * plan.pdf from the page's own Printable PDF link. Prints one line per problem:
 *   page errors, NaN in drawings, balloons that overlap or leave the drawing, section views that
 *   did not render, sideways scrolling on a phone, parts that pass through each other at full
 *   explode, and PDF failures. Exit code 1 when there is a problem.
 * Also prints warnings that do not fail the check: balloon leaders that cross each other (the style
 * asks that they not, but allows it now and then; fix with a part's `callout` if it reads badly).
 *
 * --libs points at a node_modules folder holding three, html2canvas and jspdf, for machines that
 * cannot reach cdn.jsdelivr.net; requests for those packages are answered from it.
 */
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { load } = require('./plan-load.js');
const X = require('./explode.js');

const args = process.argv.slice(2);
const opt = k => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const src = args.find(a => !a.startsWith('--') && a !== opt('--out') && a !== opt('--libs'));
if (!src) { console.error('usage: render_check.js plan.js [--out dir] [--libs node_modules] [--pdf]'); process.exit(2); }
const outDir = path.resolve(opt('--out') || 'render-check');
const libs = opt('--libs') || process.env.WWP_LIBS;
fs.mkdirSync(outDir, { recursive: true });
const html = path.join(outDir, 'plan.html');
const problems = [], warnings = [];

try { execFileSync(process.execPath, [path.join(__dirname, 'build_plan.js'), src, html], { stdio: 'pipe' }); }
catch (e) { console.log(String(e.stdout || '') + String(e.stderr || '')); console.error('Build failed; fix the check first.'); process.exit(1); }
for (const c of X.collisions(load(src))) problems.push('explode: #' + c.a + ' passes through #' + c.b + ' at full explode (' + c.vol.toFixed(1) + ' cu in); change an explode vector');

let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { console.error('Playwright is not installed here; only the build and the explode check ran.'); report(); }

(async () => {
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const route = async page => {
    if (!libs) return;
    await page.route('https://cdn.jsdelivr.net/npm/**', r => {
      const u = new URL(r.request().url()).pathname.replace(/^\/npm\//, '');
      const m = u.match(/^(@?[^@/]+(?:\/[^@/]+)?)@[^/]+\/(.*)$/);
      const f = m && path.join(libs, m[1], m[2]);
      if (f && fs.existsSync(f)) r.fulfill({ path: f, contentType: 'application/javascript' }); else r.continue();
    });
  };
  const watch = (page, tag) => {
    page.on('pageerror', e => problems.push(tag + ': page error: ' + e.message));
    page.on('console', m => { if (m.type() === 'error') problems.push(tag + ': console error: ' + m.text()); if (m.type() === 'warning' && /not drawn/.test(m.text())) problems.push(tag + ': ' + m.text()); });
  };
  const ctx = await b.newContext({ acceptDownloads: true, viewport: { width: 1200, height: 900 } });
  const pg = await ctx.newPage(); watch(pg, 'desktop'); await route(pg);
  await pg.goto('file://' + html); await pg.waitForTimeout(4000);
  const audit = await pg.evaluate(() => {
    const out = [];
    for (const el of document.querySelectorAll('svg *')) for (const a of el.getAttributeNames()) if (/NaN|Infinity/.test(el.getAttribute(a))) { out.push('NaN in a drawing: <' + el.tagName + ' ' + a + '="' + el.getAttribute(a) + '">'); break; }
    document.querySelectorAll('figure.mlx').forEach(f => {
      const img = f.querySelector('img'), svg = f.querySelector('svg');
      if (f.hidden || !img || !img.src || img.src.length < 1000) { out.push('section view "' + f.dataset.sec + '" did not render'); return; }
      const vb = svg.viewBox.baseVal, c = [...svg.querySelectorAll('g > circle:not(.ltr)')].filter(x => +x.getAttribute('r') > 5).map(x => [+x.getAttribute('cx'), +x.getAttribute('cy'), +x.getAttribute('r')]);
      c.forEach((p, i) => {
        if (p[0] - p[2] < 0 || p[1] - p[2] < 0 || p[0] + p[2] > vb.width || p[1] + p[2] > vb.height) out.push('section view "' + f.dataset.sec + '": a balloon runs off the drawing');
        c.slice(i + 1).forEach(q => { if (Math.hypot(p[0] - q[0], p[1] - q[1]) < p[2] + q[2] - 1) out.push('section view "' + f.dataset.sec + '": two balloons overlap'); });
      });
    });
    const xs = [];
    document.querySelectorAll('figure.mlx svg').forEach(s => { if (+s.dataset.crossings) xs.push('section view "' + s.closest('figure').dataset.sec + '": ' + s.dataset.crossings + ' pair(s) of balloon leaders cross'); });
    const o3 = document.getElementById('ov'); if (o3 && +o3.dataset.crossings) xs.push('3D view: ' + o3.dataset.crossings + ' pair(s) of balloon leaders cross');
    const ov = document.getElementById('ov');
    if (ov) { const c = [...ov.querySelectorAll('g > circle:not(.ltr)')].filter(x => +x.getAttribute('r') > 5).map(x => [+x.getAttribute('cx'), +x.getAttribute('cy'), +x.getAttribute('r')]); c.forEach((p, i) => c.slice(i + 1).forEach(q => { if (Math.hypot(p[0] - q[0], p[1] - q[1]) < p[2] + q[2] - 1) out.push('3D view: two balloons overlap'); })); }
    return { out, warn: xs };
  });
  problems.push(...audit.out.map(a => 'desktop: ' + a));
  warnings.push(...audit.warn.map(a => 'desktop: ' + a));
  await pg.screenshot({ path: path.join(outDir, 'desktop.png'), fullPage: true });
  const v = await pg.$('#viewer'); if (v) await v.screenshot({ path: path.join(outDir, 'viewer.png') });
  for (const f of await pg.$$('figure.mlx')) { const sec = await f.getAttribute('data-sec'); await f.screenshot({ path: path.join(outDir, 'plate-' + (sec || 'all') + '.png') }); }
  if (args.includes('--pdf')) {
    try {
      const [dl] = await Promise.all([pg.waitForEvent('download', { timeout: 120000 }), pg.click('#pdf')]);
      const pdf = path.join(outDir, 'plan.pdf'); await dl.saveAs(pdf);
      const n = (fs.readFileSync(pdf, 'latin1').match(/\/Type\s*\/Page[^s]/g) || []).length;
      console.log('PDF: ' + n + ' pages, ' + Math.round(fs.statSync(pdf).size / 1024) + ' KB');
      if (!n) problems.push('pdf: the file has no pages');
    } catch (e) { problems.push('pdf: ' + e.message.split('\n')[0]); }
  }
  const ph = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 }); watch(ph, 'phone'); await route(ph);
  await ph.goto('file://' + html); await ph.waitForTimeout(3000);
  const sw = await ph.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  if (sw > 1) problems.push('phone: the page scrolls sideways by ' + sw + 'px at 390px wide');
  await ph.screenshot({ path: path.join(outDir, 'phone.png'), fullPage: true });
  await b.close();
  report();
})().catch(e => { problems.push('render check crashed: ' + e.message); report(); });

function report() {
  const uniq = [...new Set(problems)];
  console.log('Render check: ' + (uniq.length ? uniq.length + ' problems' : 'clean') + '. Screenshots in ' + outDir);
  uniq.forEach(p => console.log('  ' + p));
  [...new Set(warnings)].forEach(w => console.log('  warning: ' + w));
  process.exit(uniq.length ? 1 : 0);
}
