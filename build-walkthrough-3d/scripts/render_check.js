#!/usr/bin/env node
/* Look at a walkthrough the way a viewer will: build it, open it in headless Chromium, step through
 * every step, and write a contact sheet to read before showing anyone.
 *
 *   node scripts/render_check.js build.js [--out dir] [--libs node_modules] [--steps 0,3,7]
 *
 * Writes into --out (default ./render-check): walkthrough.html (standalone), step-NN.jpg for each
 * step, sheet.png (every step on one labelled sheet), phone.png (a step at 390×844).
 * Prints one line per problem: page errors, a WebGL failure, the in-page physics check failing,
 * steps that render blank, and sideways scrolling on a phone. Exit code 1 when there is a problem.
 *
 * --libs points at a node_modules folder holding three@0.160.0 for machines that cannot reach
 * cdn.jsdelivr.net (npm i three@0.160.0); requests for it are answered from there.
 */
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const args = process.argv.slice(2);
const opt = k => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const vals = new Set(['--out', '--libs', '--steps'].map(opt));
const src = args.find(a => !a.startsWith('--') && !vals.has(a));
if (!src) { console.error('usage: render_check.js build.js [--out dir] [--libs node_modules] [--steps 0,3,7]'); process.exit(2); }
const outDir = path.resolve(opt('--out') || 'render-check');
const libs = opt('--libs') || process.env.WALKTHROUGH_LIBS;
fs.mkdirSync(outDir, { recursive: true });
const html = path.join(outDir, 'walkthrough.html');
try { execFileSync(process.execPath, [path.join(__dirname, 'build.js'), src, html, '--standalone'], { stdio: 'inherit' }); }
catch (e) { console.error('Build failed; fix the physics check first.'); process.exit(1); }

const problems = [];
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { console.error('Playwright is not installed here; only the build and physics check ran.'); process.exit(0); }

(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const open = async (viewport, tag) => {
    const page = await b.newPage({ viewport });
    if (libs) await page.route('https://cdn.jsdelivr.net/npm/**', r => {
      const u = new URL(r.request().url()).pathname.replace(/^\/npm\//, '');
      const m = u.match(/^(@?[^@/]+(?:\/[^@/]+)?)@[^/]+\/(.*)$/);
      const f = m && path.join(libs, m[1], m[2]);
      if (f && fs.existsSync(f)) r.fulfill({ path: f, contentType: 'application/javascript' }); else r.continue();
    });
    // fonts are optional; a blocked font host must not fail the check
    await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
    page.on('pageerror', e => problems.push(`${tag}: page error: ${e.message}`));
    page.on('console', m => { if (m.type() === 'error' && !/fonts\.g|ERR_FAILED|net::/.test(m.text() + (m.location().url || ''))) problems.push(`${tag}: console error: ${m.text()}`); });
    await page.goto('file://' + html);
    try { await page.waitForFunction(() => window.__view && window.__view.ready, null, { timeout: 30000 }); }
    catch (e) { problems.push(`${tag}: the viewer never started (three.js not loaded? try --libs)`); }
    return page;
  };
  const page = await open({ width: 1280, height: 800 }, 'desktop');
  const n = await page.evaluate(() => window.PLAN && window.__view ? window.PLAN.LAST : -1);
  await page.waitForTimeout(1200);   // let the loading cover fade
  if (n < 0) { report(); return b.close(); }
  const titles = await page.evaluate(() => window.PLAN.STEPS.map(s => s.title));
  const want = opt('--steps') ? opt('--steps').split(',').map(Number) : [...Array(n + 1).keys()];
  const shots = [];
  for (const i of want) {
    await page.evaluate(i => { window.__view.go(i, { instant: true }); window.__view.settle(); }, i);
    await page.waitForTimeout(350);
    const buf = await page.screenshot({ type: 'jpeg', quality: 72 });
    fs.writeFileSync(path.join(outDir, `step-${String(i).padStart(2, '0')}.jpg`), buf);
    shots.push({ i, title: titles[i], data: buf.toString('base64') });
  }
  // the page re-runs the physics check itself about a second after load
  await page.waitForFunction(() => /ok|bad/.test(document.getElementById('iCheck').className), null, { timeout: 20000 }).catch(() => {});
  const chk = await page.evaluate(() => { const e = document.getElementById('iCheck'); return { cls: e.className, text: e.textContent }; });
  if (!/\bok\b/.test(chk.cls)) problems.push('in-page physics check: ' + chk.text);

  const phone = await open({ width: 390, height: 844 }, 'phone');
  await phone.evaluate(i => { window.__view.go(i, { instant: true }); window.__view.settle(); }, Math.min(n, 3));
  await phone.waitForTimeout(1400);
  await phone.screenshot({ path: path.join(outDir, 'phone.png') });
  const sw = await phone.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  if (sw > 1) problems.push(`phone: the page scrolls sideways by ${sw}px`);

  // contact sheet
  const cols = 4, tw = 400, th = 250, rows = Math.ceil(shots.length / cols);
  const sheet = await b.newPage({ viewport: { width: cols * tw, height: rows * (th + 26) } });
  await sheet.setContent(`<body style="margin:0;background:#111;font:13px system-ui;color:#eee;display:grid;grid-template-columns:repeat(${cols},${tw}px)">` +
    shots.map(s => `<figure style="margin:0;height:${th + 26}px"><img src="data:image/jpeg;base64,${s.data}" style="width:${tw}px;height:${th}px;object-fit:cover;display:block"><figcaption style="padding:4px 8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${s.i ? 'Step ' + s.i : 'Overview'} · ${s.title.replace(/</g, '&lt;')}</figcaption></figure>`).join('') + '</body>');
  // blank check: count distinct colours in the upper middle of each shot, where the scene shows and the UI does not
  const variety = await sheet.evaluate(() => [...document.images].map(img => {
    const g = document.createElement('canvas'); g.width = 64; g.height = 32; const x = g.getContext('2d');
    x.drawImage(img, img.naturalWidth * 0.3, img.naturalHeight * 0.15, img.naturalWidth * 0.4, img.naturalHeight * 0.35, 0, 0, 64, 32);
    const d = x.getImageData(0, 0, 64, 32).data, set = new Set();
    for (let k = 0; k < d.length; k += 4) set.add((d[k] >> 4) + ',' + (d[k + 1] >> 4) + ',' + (d[k + 2] >> 4)); return set.size;
  }));
  variety.forEach((v, k) => { if (v < 10) problems.push(`step ${shots[k].i}: the 3D view looks blank`); });
  await sheet.screenshot({ path: path.join(outDir, 'sheet.png'), fullPage: true });
  await b.close();
  report();
})().catch(e => { console.error(e); process.exit(1); });

function report() {
  const seen = [...new Set(problems)];
  seen.forEach(p => console.log('PROBLEM ' + p));
  console.log(seen.length ? `FAIL: ${seen.length} problems` : `PASS: wrote ${outDir}/sheet.png, phone.png and one image per step`);
  process.exitCode = seen.length ? 1 : 0;
}
