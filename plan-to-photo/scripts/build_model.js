#!/usr/bin/env node
// Build the 3D model of a piece from model.json (the parts you read off the drawings) and write an
// OBJ in meters, one object per part copy, with a material group per wood (walnut_quartersawn,
// hard_maple, ...) for build_scene.py to map to scanned sets. Then check it against the drawings.
//
//   node build_model.js model.json model.obj [--takeoff takeoff.json] [--skip 1,12,13]
//
// model.json: references/drawings.md (parts with blank sizes, shapes in part coordinates, copies).
// The geometry kernel is the woodworking-plans one (boxes, cuts, outlines, tapers, turnings), found
// next to this skill in the repo, or via --wp / $WP.
//
// Checks, printed after the export; exit 1 when one fails:
//   - each part's modelled blank (its boxes) against its listed T x W x L, and its copy count;
//   - with --takeoff, the listed sizes against the takeoff read off the parts list;
//   - the model's overall extents against meta.overall (the drawing's overall dimensions);
//   - no two parts occupying the same space (a misread position nearly always shows up here).
// --skip drops parts from the OBJ that a dress script rebuilds (they are still checked).
const fs = require('fs'), path = require('path');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : d; };
const skip = new Set((opt('--skip', '') || '').split(',').filter(Boolean).map(String));
const takeoffPath = opt('--takeoff');
const TOL = parseFloat(opt('--tol', '0.0315'));   // 1/32"
let wp = opt('--wp', process.env.WP);
const [modelPath, outPath = 'model.obj'] = args;
if (!modelPath) { console.error('usage: node build_model.js model.json out.obj [--takeoff takeoff.json] [--skip 1,2] [--wp dir]'); process.exit(2); }
const tries = [wp, path.join(__dirname, '../../woodworking-plans/scripts'), path.join(process.env.HOME || '', '.claude/skills/woodworking-plans/scripts')].filter(Boolean);
wp = tries.find(d => fs.existsSync(path.join(d, 'plan-core.js')));
if (!wp) { console.error('geometry kernel (woodworking-plans/scripts/plan-core.js) not found; tried:\n  ' + tries.join('\n  ') + '\nClone the skills repo next to this skill or pass --wp.'); process.exit(2); }
const C = require(path.join(wp, 'plan-core.js')), { load } = require(path.join(wp, 'plan-load.js'));

const M = C.normalize(load(path.resolve(modelPath)));
const unit = 0.0254;  // model.json is in inches
const slug = s => (s || 'wood').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'wood';
const mtlName = path.basename(outPath).replace(/\.obj$/i, '') + '.mtl';
let obj = `# built from ${path.basename(modelPath)} by plan-to-photo/build_model.js, meters, Z up\nmtllib ${mtlName}\n`;
let vi = 1, n = 0; const mats = new Map();
const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
for (const p of M.parts) {
  const mat = slug(p.material);
  for (const I of p.instances) {
    for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], I.bbox.min[k]); hi[k] = Math.max(hi[k], I.bbox.max[k]); }
    if (skip.has(String(p.id))) continue;
    mats.set(mat, p.material || '');
    const s = C.surface(I.solid), faces = [];
    for (const q of s.quads) faces.push(q.v);
    for (const t of s.tris) faces.push(t.v);
    if (!faces.length) continue;
    obj += `o P${p.id}_${p.name.replace(/\W+/g, '_')}_${I.index}\nusemtl ${mat}\n`;
    for (const f of faces) {
      for (const v of f) obj += `v ${(v[0] * unit).toFixed(6)} ${(v[1] * unit).toFixed(6)} ${(v[2] * unit).toFixed(6)}\n`;
      obj += 'f ' + f.map((_, i) => vi + i).join(' ') + '\n'; vi += f.length;
    }
    n++;
  }
}
fs.writeFileSync(outPath, obj);
fs.writeFileSync(path.join(path.dirname(outPath), mtlName), [...mats.keys()].map(m => `newmtl ${m}\nKd 0.5 0.4 0.3\n`).join('\n'));
console.log(`${n} objects, ${vi - 1} verts -> ${outPath}`);
console.log('materials (map these in scene.json model.assign):');
for (const [k, v] of mats) console.log(`  ${k.padEnd(28)} ${v}`);
console.log('parts:');
for (const p of M.parts) console.log(`  ${String(p.id).padStart(3)} ${skip.has(String(p.id)) ? '(skipped) ' : ''}${p.name} x${p.instances.length}`);

// ---- checks against the drawings
const fails = [], F = x => Math.round(x * 1000) / 1000, eq = (a, b) => Math.abs(a - b) <= TOL;
const sorted3 = a => [...a].map(Number).sort((x, y) => x - y);
const same = (a, b) => sorted3(a).every((v, i) => eq(v, sorted3(b)[i]));
console.log('\nchecks:');
for (const p of M.parts) {
  const blank = (() => { const L = [Infinity, Infinity, Infinity], H = [-Infinity, -Infinity, -Infinity];
    for (const a of p.local.adds) for (let k = 0; k < 3; k++) { L[k] = Math.min(L[k], a.min[k]); H[k] = Math.max(H[k], a.max[k]); }
    return [0, 1, 2].map(k => H[k] - L[k]); })();
  if (!same(blank, [p.t, p.w, p.l])) fails.push(`#${p.id} ${p.name}: modelled blank ${blank.map(F).join(' x ')} but listed ${p.t} x ${p.w} x ${p.l}`);
  if (p.qty !== p.instances.length) fails.push(`#${p.id} ${p.name}: qty ${p.qty} but ${p.instances.length} copies placed`);
}
if (takeoffPath) {
  const T = JSON.parse(fs.readFileSync(takeoffPath, 'utf8'));
  const byId = Object.fromEntries(M.parts.map(p => [String(p.id), p]));
  for (const t of T.parts || []) {
    const p = byId[String(t.id)];
    if (!p) { fails.push(`takeoff #${t.id} ${t.name}: not in the model`); continue; }
    if (!same([p.t, p.w, p.l], [t.t, t.w, t.l])) fails.push(`#${t.id} ${t.name}: model ${p.t} x ${p.w} x ${p.l}, drawing ${t.t} x ${t.w} x ${t.l} (${t.from || 'takeoff'})`);
    if (t.qty != null && t.qty !== p.instances.length) fails.push(`#${t.id} ${t.name}: model has ${p.instances.length}, drawing lists ${t.qty}`);
    if (t.material && slug(t.material) !== slug(p.material)) fails.push(`#${t.id} ${t.name}: material ${p.material}, drawing says ${t.material}`);
  }
  const extra = M.parts.filter(p => !(T.parts || []).some(t => String(t.id) === String(p.id)));
  for (const p of extra) fails.push(`#${p.id} ${p.name}: in the model but not in the takeoff`);
}
const ext = [0, 1, 2].map(k => hi[k] - lo[k]);
const ov = (M.meta && M.meta.overall) || (takeoffPath && JSON.parse(fs.readFileSync(takeoffPath, 'utf8')).overall);
console.log(`  overall ${F(ext[0])} W x ${F(ext[1])} D x ${F(ext[2])} H (inches), min corner at ${lo.map(F).join(', ')}`);
if (ov) ['w', 'd', 'h'].forEach((k, i) => { if (ov[k] != null && !eq(ext[i], Number(ov[k]))) fails.push(`overall ${k}: model ${F(ext[i])}, drawing ${ov[k]}`); });
// overlaps: two parts filling the same space means a position was misread
const R = C.check(M);
for (const e of R.errors || []) if (e.code === 'interference') fails.push('overlap: ' + e.msg);
// floating: every piece must touch another, and all of them one assembly (a misread height floats)
const pcs = M.parts.flatMap(p => p.instances.map(I => ({ key: `#${p.id} ${p.name} (${I.index + 1})`, b: I.bbox })));
const touch = (a, b) => [0, 1, 2].every(k => a.min[k] <= b.max[k] + TOL && b.min[k] <= a.max[k] + TOL);
const root = pcs.map((_, i) => i), find = i => root[i] === i ? i : (root[i] = find(root[i]));
pcs.forEach((a, i) => pcs.forEach((b, j) => { if (j > i && touch(a.b, b.b)) root[find(i)] = find(j); }));
const floorZ = lo[2], groups = new Map();
pcs.forEach((a, i) => { const r = find(i); groups.set(r, (groups.get(r) || []).concat(a)); });
if (groups.size > 1) for (const g of [...groups.values()].sort((a, b) => a.length - b.length).slice(0, -1))
  fails.push('floating: ' + g.map(a => a.key).join(', ') + ' touch nothing else in the model');

console.log(`  ${M.parts.length} parts, ${M.parts.reduce((s, p) => s + p.instances.length, 0)} pieces`);
if (fails.length) { for (const f of fails) console.log('  FAIL ' + f); console.log(`${fails.length} checks failed: fix the model (or the takeoff, if it was misread) before building the scene`); process.exit(1); }
console.log('  PASS sizes, counts' + (takeoffPath ? ', takeoff' : '') + (ov ? ', overall' : '') + ', no overlaps, one assembly');
