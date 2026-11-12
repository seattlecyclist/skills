#!/usr/bin/env node
/* Physics check for a build file.
 *
 *   node scripts/verify.js build.js [--samples 40] [--json]
 *
 * For every step it samples each move along its path and reports:
 *   collision      a moving part passes through a part already there
 *   floor, static  a moving part goes below the floor or through the assembly table or a light
 *   floating       at rest, a group of parts touches nothing that reaches the floor or a table
 *   no-contact     a placed part touches nothing at all
 *   unsupported    a loose part (or a whole sub-assembly) has nothing under it
 *   final-overlap  two parts share volume in the finished piece
 *   never-placed   a part that no step ever brings in
 * Exit code 1 when there is any issue. Repeats of the same issue are printed once.
 */
const { load } = require('./load.js');
const args = process.argv.slice(2);
const si = args.indexOf('--samples');
const file = args.find((a, i) => !a.startsWith('--') && !(si >= 0 && i === si + 1));
if (!file) { console.error('usage: verify.js build.js [--samples N] [--json]'); process.exit(2); }
const N = si >= 0 ? +args[si + 1] : 40;
const P = load(file);
const t0 = Date.now();
const r = P.verify({ samples: N });
if (args.includes('--json')) { console.log(JSON.stringify(r, null, 1)); process.exit(r.ok ? 0 : 1); }
console.log(`${P.meta.title}: ${P.LAST} steps, ${r.parts} parts in ${r.bodies} bodies, ${r.checks} checks in ${Date.now() - t0} ms`);
const seen = new Set();
r.issues.forEach(i => {
  const k = i.step + i.kind + i.a + (i.b || ''); if (seen.has(k)) return; seen.add(k);
  const s = P.STEPS[i.step];
  console.log(`  step ${i.step}${s ? ' "' + s.title + '"' : ''}: ${i.kind}: ${i.a}${i.b ? ' / ' + i.b : ''}${i.depth ? ' (' + i.depth + ' deep at t=' + i.t + 's)' : ''}`);
});
console.log(r.ok ? 'PASS' : `FAIL: ${seen.size} distinct issues`);
process.exit(r.ok ? 0 : 1);
