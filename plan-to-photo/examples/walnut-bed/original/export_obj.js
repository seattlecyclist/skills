const C = require('./scripts/plan-core.js'), { load } = require('./scripts/plan-load.js'), fs = require('fs');
const M = C.normalize(load(process.argv[2]));
const k = 0.0254; let obj = 'mtllib bed.mtl\n', vi = 1, n = 0; const mats = new Set();
for (const p of M.parts) {
  const mat = /maple/i.test(p.material || '') ? 'maple' : /walnut/i.test(p.material||'') ? 'walnut' : 'hardware';
  mats.add(mat);
  for (const I of p.instances) {
    const s = C.surface(I.solid), faces = [];
    for (const q of s.quads) faces.push(q.v);
    for (const t of s.tris) faces.push(t.v);
    if (!faces.length) continue;
    obj += `o P${p.id}_${p.name.replace(/\W+/g,'_')}_${I.index}\nusemtl ${mat}\n`;
    for (const f of faces) { for (const v of f) obj += `v ${(v[0]*k).toFixed(6)} ${(v[1]*k).toFixed(6)} ${(v[2]*k).toFixed(6)}\n`; obj += 'f ' + f.map((_, i) => vi + i).join(' ') + '\n'; vi += f.length; }
    n++;
  }
}
fs.writeFileSync('bed.obj', obj);
fs.writeFileSync('bed.mtl', [...mats].map(m => `newmtl ${m}\nKd ${m==='maple'?'0.85 0.72 0.55':m==='walnut'?'0.30 0.18 0.11':'0.5 0.5 0.5'}\n`).join('\n'));
console.log(n, 'objects,', vi - 1, 'verts');
