#!/usr/bin/env node
/* Validate, check, review and build a plan page.
 *
 *   node build_plan.js plan.js --check              validate + model check, print the report
 *   node build_plan.js plan.js --validate           schema validation only
 *   node build_plan.js plan.js --review             review worksheet for the current rev's changes
 *        [--base old-plan.js] [--change C1] [--json] adds what moved since the base plan
 *   node build_plan.js plan.js out.html             full HTML document
 *   node build_plan.js plan.js out.html --artifact  page body only, for the Artifact tool
 *   node build_plan.js plan.js out.html --force     build even when the check has errors
 *
 * plan.js exports build(PARAMS, J) (J = scripts/joints.js) or the plan object; plan.json works too.
 * Exit code 1 when validation or the model check reports errors (unless --force).
 */
const fs = require('fs');
const path = require('path');
const core = require('./plan-core.js');
const { load } = require('./plan-load.js');
const { validate } = require('./validate.js');

const args = process.argv.slice(2);
const flags = new Set(args.filter(a => a.startsWith('--')));
const opt = k => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const valued = new Set([opt('--base'), opt('--change')].filter(Boolean));
const [src, out] = args.filter(a => !a.startsWith('--') && !valued.has(a));
if (!src) { console.error('usage: build_plan.js plan.js [out.html] [--check|--validate|--review [--base old.js] [--change id] [--json]] [--artifact] [--force]'); process.exit(2); }

const plan = load(src);
const V = validate(plan);
const vErr = V.filter(v => v.level === 'error');
const printV = () => { if (!V.length) console.log('Validation: ok'); else { console.log('Validation:'); V.forEach(v => console.log('  ' + (v.level === 'error' ? 'ERROR' : 'warn ') + ' ' + v.at + ': ' + v.msg)); } };
if (flags.has('--validate')) { printV(); process.exit(vErr.length ? 1 : 0); }
if (vErr.length && !flags.has('--force')) { printV(); console.error(vErr.length + ' validation errors: fix them first (the model check needs a well-formed plan).'); process.exit(1); }

const R = core.check(plan);
if (flags.has('--review')) { review(); process.exit(0); }

printV();
const line = (tag, m) => console.log(tag + ' ' + m.msg + (m.parts && m.parts.length ? '  [' + m.parts.join(', ') + ']' : ''));
console.log('Model check: ' + (plan.meta && plan.meta.title || src));
R.errors.forEach(e => line('  ERROR', e));
R.warnings.forEach(w => line('  CHECK', w));
R.passes.forEach(p => line('  pass ', p));
const o = R.stats.overall; if (o) console.log('  overall ' + o.map(v => core.fmt(v)).join(' x ') + ' (W x D x H)');
for (const l of R.stats.lumber || []) console.log('  lumber ' + core.fmt(l.t) + ' ' + l.material + ': ' + l.bf.toFixed(1) + ' bd ft net');
console.log(R.errors.length + ' errors, ' + R.warnings.length + ' checks to review');

if (flags.has('--check') || !out) process.exit(R.errors.length ? 1 : 0);
if (R.errors.length && !flags.has('--force')) { console.error('Not building: fix the errors above, or pass --force to build a draft that shows them.'); process.exit(1); }

const dir = path.join(__dirname, '..', 'assets');
let html = fs.readFileSync(path.join(dir, 'plan-template.html'), 'utf8');
const coreSrc = fs.readFileSync(path.join(__dirname, 'plan-core.js'), 'utf8');
const title = (plan.meta && plan.meta.title || 'Project plan').replace(/</g, '');
// JSON inside <script>: escape the sequences that could end the script element
const json = JSON.stringify(plan).replace(/</g, '\\u003c').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');
html = html.replace('__TITLE__', () => title).replace('/*__PLAN__*/null', () => json).replace('/*__CORE__*/', () => coreSrc.replace(/<\/script/gi, '<\\/script'));
if (flags.has('--artifact')) html = html.replace('<!--BODY-->\n', '');
else {
  const [head, body] = html.split('<!--BODY-->');
  html = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n' + head + '</head>\n<body>' + body + '</body>\n</html>\n';
}
fs.writeFileSync(out, html);
console.log('Wrote ' + out + ' (' + Math.round(html.length / 1024) + ' KB)');

// ---------- review worksheet ----------
// For each change: the parts it touches, the parts those mate with, what moved since the base
// plan, the paperwork that names them, the mechanical checks on them, and a record skeleton with
// one line per joint, bore group and paperwork item. The reviewer fills in evidence and results.
function review() {
  const M = R.model, F = v => core.fmt(v), byId = M.byId;
  const nm = id => '#' + id + ' ' + (byId[id] ? byId[id].name : '?');
  const meta = plan.meta || {};
  const want = opt('--change');
  const revs = plan.revisions || [];
  const changes = want ? revs.flatMap(r => (r.changes || []).map(c => Object.assign({ rev: r.rev }, c))).filter(c => c.id === want)
    : ((revs.find(r => r.rev === meta.rev) || revs[revs.length - 1] || {}).changes || []).map(c => Object.assign({ rev: meta.rev }, c));
  const joints = plan.joints || [];
  const bores = plan.bores || [];
  const steps = plan.steps || [];
  const chips = s => [...String(s || '').matchAll(/\{#([^}]+)\}/g)].map(m => m[1]);
  const diff = baseDiff();
  const res = [];
  for (const c of changes.length ? changes : [{ id: 'A1', rev: meta.rev, summary: 'Whole design (no revisions yet)', parts: M.parts.map(p => p.id) }]) {
    const touch = (c.parts || []).map(String);
    if (diff) for (const d of diff.parts) if (!touch.includes(d.id) && byId[d.id]) d.unlisted = true;
    const mates = new Map();
    for (const j of joints) if (j.parts.some(id => touch.includes(String(id)))) for (const id of j.parts.map(String)) if (!touch.includes(id)) mates.set(id, (mates.get(id) || []).concat(j.id));
    for (const k of R.contacts) for (const [a, b] of [[k.a, k.b], [k.b, k.a]]) if (touch.includes(a) && !touch.includes(b) && !mates.has(b)) mates.set(b, ['contact']);
    const scope = new Set(touch.concat([...mates.keys()]));
    const js = joints.filter(j => j.parts.some(id => touch.includes(String(id))));
    const bs = bores.filter(b => js.some(j => j.id === b.joint));
    const paper = [];
    steps.forEach((s, i) => { const ids = (s.parts || []).map(String).concat(chips(s.text)); const hit = ids.filter(id => scope.has(id)); if (hit.length) paper.push({ kind: 'step', ref: 'step ' + (i + 1) + ' "' + s.title + '"', ids: [...new Set(hit)] }); });
    (plan.hardware || []).forEach(h => { const ids = [h.part].filter(Boolean).map(String).concat(chips(h.note)); if (ids.some(id => scope.has(id))) paper.push({ kind: 'hardware', ref: 'hardware "' + h.item + '"', ids }); });
    if (bs.length || js.some(j => j.fasteners)) paper.push({ kind: 'hardware', ref: 'hardware list: sizes and counts of the fasteners in ' + js.filter(j => j.fasteners).map(j => j.id).join(', '), ids: [] });
    (plan.details || []).forEach(d => { const ids = (d.items || []).flatMap(it => [it.part, it.callout && it.callout[2]]).filter(Boolean).map(String); const hit = ids.filter(id => scope.has(id)); if (hit.length) paper.push({ kind: 'detail', ref: 'detail "' + d.title + '"', ids: [...new Set(hit)] }); });
    for (const g of core.layouts(M, plan)) { const ids = [...new Set(g.pieces.map(p => String(p.id)))]; if (ids.some(id => touch.includes(id))) paper.push({ kind: 'cutting', ref: 'cutting diagram ' + F(g.t) + ' ' + g.material, ids }); }
    if (touch.some(id => chips((meta.intro || []).join(' ')).includes(id)) || /\d/.test((meta.intro || []).join(' '))) paper.push({ kind: 'intro', ref: 'intro text (has numbers: re-read it)', ids: [] });
    const notes = M.parts.filter(p => scope.has(p.id) && p.note).map(p => ({ kind: 'note', ref: 'cut list note on ' + nm(p.id), ids: [p.id] }));
    const mech = R.errors.concat(R.warnings).filter(m => (m.parts || []).some(id => scope.has(String(id))) || bs.some(b => m.msg.includes('Bore ' + b.id)));
    const checks = [];
    checks.push({ check: 'Dimensions of ' + touch.map(id => '{#' + id + '}').join(' ') + ': cut list re-derived by hand from PARAMS', evidence: 'TODO', result: 'TODO' });
    for (const j of js) checks.push({ check: j.id + ' ' + (j.title || j.type) + ' ' + j.parts.map(id => '{#' + id + '}').join(' ') + ': engages, proportions (joinery.md), tools, assembly order, load path', evidence: 'TODO', result: 'TODO' });
    if (bs.length) checks.push({ check: 'Fasteners ' + bs.map(b => b.id).join(', ') + ': can be bored and fitted once assembled, length, nut engagement', evidence: 'TODO', result: 'TODO' });
    if (mates.size) checks.push({ check: 'Mates ' + [...mates.keys()].map(id => '{#' + id + '}').join(' ') + ': still fit, clearances to anything that moves', evidence: 'TODO', result: 'TODO' });
    checks.push({ check: 'Paperwork: ' + paper.map(p => p.ref).join('; '), evidence: 'TODO', result: 'TODO' });
    if (diff && diff.parts.some(d => d.unlisted)) checks.push({ check: 'Also moved, not listed in the change: ' + diff.parts.filter(d => d.unlisted).map(d => '{#' + d.id + '}').join(' '), evidence: 'TODO', result: 'TODO' });
    const existing = (plan.review || []).find(x => x.change === c.id);
    res.push({ change: c, touch, mates: [...mates].map(([id, via]) => ({ id, via })), joints: js.map(j => j.id), bores: bs.map(b => b.id), paper: paper.concat(notes), mech, existing: !!existing,
      record: { rev: c.rev, change: c.id, verdict: 'TODO', mates: [...mates.keys()], checks } });
  }
  if (flags.has('--json')) { console.log(JSON.stringify({ check: { errors: R.errors, warnings: R.warnings }, validation: V, diff, changes: res }, null, 2)); return; }
  const P = [];
  P.push('# Review worksheet: ' + (meta.title || src) + ', Rev ' + (meta.rev || '?'));
  P.push('Model check: ' + R.errors.length + ' errors, ' + R.warnings.length + ' warnings. Validation: ' + (V.length ? V.length + ' notes' : 'ok') + '.');
  if (R.errors.length) P.push('Fix the model check errors before reviewing: ' + R.errors.map(e => e.code).join(', '));
  if (diff) {
    P.push('', '## What changed since ' + opt('--base'));
    if (!diff.parts.length && !diff.other.length) P.push('Nothing in the model or hardware changed.');
    for (const d of diff.parts) P.push('- ' + nm(d.id) + ': ' + d.what.join('; ') + (d.unlisted ? '  ← not in any change\'s parts' : ''));
    for (const x of diff.other) P.push('- ' + x);
  }
  for (const r of res) {
    P.push('', '## ' + r.change.id + ': ' + (r.change.summary || ''));
    if (r.change.reason) P.push('Reason: ' + r.change.reason);
    P.push('Touches: ' + r.touch.map(nm).join(', '));
    P.push('Mates: ' + (r.mates.length ? r.mates.map(m => nm(m.id) + ' (' + m.via.join(', ') + ')').join(', ') : 'none'));
    P.push('Joints in scope: ' + (r.joints.join(', ') || 'none') + (r.bores.length ? '. Bores: ' + r.bores.join(', ') : ''));
    P.push('Mechanical checks on these parts: ' + (r.mech.length ? '' : 'all pass (interference, seating, contact, walls, bores, tools)'));
    for (const m of r.mech) P.push('  - ' + m.code + ': ' + m.msg);
    P.push('Paperwork to re-read:');
    for (const p of r.paper) P.push('  - ' + p.ref + (p.ids.length ? ' [' + p.ids.join(', ') + ']' : ''));
    P.push('Record ' + (r.existing ? '(this change already has a review entry; compare it with this one)' : 'skeleton (fill evidence with numbers and part numbers, set each result to pass, fixed, flag or fail, and the verdict to the worst line)') + ':');
    const rec = r.record, q = JSON.stringify;
    P.push('```js', '{ rev: ' + q(rec.rev) + ', change: ' + q(rec.change) + ', verdict: ' + q(rec.verdict) + ', mates: ' + q(rec.mates) + ',', '  checks: [');
    rec.checks.forEach((c, i) => P.push('    { check: ' + q(c.check) + ',', '      evidence: ' + q(c.evidence) + ', result: ' + q(c.result) + ' }' + (i < rec.checks.length - 1 ? ',' : '')));
    P.push('  ] }', '```');
  }
  P.push('', 'Attack every line with references/adversarial-review.md. A passing check is not a passing review.');
  console.log(P.join('\n'));
}
function baseDiff() {
  const b = opt('--base'); if (!b) return null;
  const B = load(b), F = v => core.fmt(v);
  const MB = core.normalize(B), MA = R.model;
  const parts = [], other = [];
  // compare positions about the model's center (x, y) and floor (z), so growing the piece from one
  // end does not report every part as moved
  const ref = x => { const w = core.check(x).stats.world; return [(w.min[0] + w.max[0]) / 2, (w.min[1] + w.max[1]) / 2, w.min[2]]; };
  const ra = ref(plan), rb = ref(B);
  const box = (I, o) => I.bbox ? I.bbox.min.concat(I.bbox.max).map((v, i) => (v - o[i % 3]).toFixed(4)).join(',') : '';
  for (const p of MA.parts) {
    const q = MB.byId[p.id];
    if (!q) { parts.push({ id: p.id, what: ['new part'] }); continue; }
    const what = [];
    for (const k of ['t', 'w', 'l']) if (p[k] != null && q[k] != null && Math.abs(p[k] - q[k]) > 1e-4) what.push(k.toUpperCase() + ' ' + F(q[k]) + ' → ' + F(p[k]));
    if (p.qty !== q.qty) what.push('qty ' + q.qty + ' → ' + p.qty);
    if (p.material !== q.material) what.push('material ' + q.material + ' → ' + p.material);
    const cutKey = x => x.local.cuts.concat(x.local.tenons).map(a => a.min.concat(a.max).map(v => v.toFixed(4)).join(',')).sort().join('|');
    if (cutKey(p) !== cutKey(q)) what.push('joinery cut differently');
    const moved = p.instances.filter((I, i) => q.instances[i] && box(I, ra) !== box(q.instances[i], rb));
    if (moved.length) {
      const I = moved[0], J0 = q.instances[I.index];
      const d = [0, 1, 2].map(a => (I.bbox.min[a] - ra[a]) - (J0.bbox.min[a] - rb[a]));
      what.push(moved.length + ' of ' + p.instances.length + ' copies moved' + (d.some(v => Math.abs(v) > 1e-4) ? ' (first by ' + d.map(v => F(v)).join(', ') + ' in x, y, z, about the center)' : ''));
    }
    if (what.length) parts.push({ id: p.id, what });
  }
  for (const q of MB.parts) if (!MA.byId[q.id]) parts.push({ id: q.id, what: ['removed'] });
  const ov = R.stats.overall, ob = core.check(B).stats.overall;
  if (ov && ob && ov.some((v, i) => Math.abs(v - ob[i]) > 1e-4)) other.push('Overall ' + ob.map(F).join(' × ') + ' → ' + ov.map(F).join(' × '));
  const hw = x => (x.hardware || []).map(h => h.qty + ' ' + h.item);
  const ha = hw(plan), hb = hw(B);
  for (const h of hb) if (!ha.includes(h)) other.push('Hardware removed or changed: ' + h);
  for (const h of ha) if (!hb.includes(h)) other.push('Hardware added or changed: ' + h);
  const bk = (x, o) => core.expandBores(x).map(b => b.key + ' ' + b.at.map((v, i) => (v - o[i]).toFixed(3)).join(',') + ' ' + b.len + ' ' + b.depth);
  const ba = bk(plan, ra), bb = bk(B, rb);
  const movedB = [...new Set(ba.filter(x => !bb.includes(x)).map(x => x.split(' ')[0].split('.')[0]))];
  if (movedB.length) other.push('Bores moved or resized: ' + movedB.join(', '));
  return { parts, other };
}
