#!/usr/bin/env node
// Export a woodworking-plans plan.js to an OBJ in meters, one object per part instance, with a
// material group per part material (walnut_rift, hard_maple, ...) for build_scene.py to map to
// scanned sets. Exact geometry: joinery, tapers and bores as the plan models them.
//
//   node export_obj.js plan.js out.obj [--skip 1,12,13] [--wp path/to/woodworking-plans/scripts]
//
// --skip drops parts you will rebuild by hand in Blender (true curves, radiused legs).
// The woodworking-plans scripts are found next to this skill in the repo, or via --wp / $WP.
const fs = require('fs'), path = require('path');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : d; };
const skip = new Set((opt('--skip', '') || '').split(',').filter(Boolean).map(String));
let wp = opt('--wp', process.env.WP);
const [planPath, outPath = 'model.obj'] = args;
if (!planPath) { console.error('usage: node export_obj.js plan.js out.obj [--skip 1,2] [--wp dir]'); process.exit(2); }
const tries = [wp, path.join(__dirname, '../../woodworking-plans/scripts'), path.join(process.env.HOME || '', '.claude/skills/woodworking-plans/scripts'), path.join(path.dirname(path.resolve(planPath)), 'scripts')].filter(Boolean);
wp = tries.find(d => fs.existsSync(path.join(d, 'plan-core.js')));
if (!wp) { console.error('woodworking-plans scripts not found; tried:\n  ' + tries.join('\n  ') + '\nInstall that skill or pass --wp.'); process.exit(2); }
const C = require(path.join(wp, 'plan-core.js')), { load } = require(path.join(wp, 'plan-load.js'));

const M = C.normalize(load(path.resolve(planPath)));
const unit = 0.0254;  // plan.js geometry is always inches (the page's mm toggle is display only)
const slug = s => (s || 'wood').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'wood';
const mtlName = path.basename(outPath).replace(/\.obj$/i, '') + '.mtl';
let obj = `# exported from ${path.basename(planPath)} by plan-to-photo/export_obj.js, meters, Z up\nmtllib ${mtlName}\n`;
let vi = 1, n = 0; const mats = new Map();
for (const p of M.parts) {
  if (skip.has(String(p.id))) continue;
  const mat = slug(p.material);
  mats.set(mat, p.material || '');
  for (const I of p.instances) {
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
