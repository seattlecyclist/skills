#!/usr/bin/env node
/* Prove the physics check would catch a bad move in THIS build, not just in general.
 *
 *   node scripts/mutate.js build.js [--count 8]
 *
 * Picks moves spread across the sequence and breaks each one on a fresh copy of the build:
 *   push   shove the part 1/4" (6 mm) into a neighbour it touches at rest  -> must be caught
 *   float  lift a loose part 1/8" (3 mm) off whatever it sits on          -> must be caught
 * Run it once the build passes verify.js. Exit code 1 if any break goes unnoticed: that means
 * a part is not modelled where it really sits, or the check has a blind spot for this build.
 */
const { load } = require('./load.js');
const args = process.argv.slice(2);
const ci = args.indexOf('--count');
const file = args.find((a, i) => !a.startsWith('--') && !(ci >= 0 && i === ci + 1));
if (!file) { console.error('usage: mutate.js build.js [--count N]'); process.exit(2); }
const COUNT = ci >= 0 ? +args[ci + 1] : 8;

const base = load(file);
const base_r = base.verify({ samples: 12 });
if (!base_r.ok) { console.error('The build does not pass verify.js yet; fix that first.'); process.exit(1); }
const U = base.U;

// candidate moves: the body's last move that leaves it in place (not removed), one per body, spread over the steps
const cands = [];
base.BODIES.forEach(b => {
  if (b.virtual) return;
  const ev = b.events.filter(e => !e.remove);
  if (!ev.length) return;
  const e = ev[ev.length - 1];
  if (b.events.some(x => x.remove && x.step >= e.step)) return;
  cands.push({ id: b.id, ei: b.events.indexOf(e), step: e.step, loose: b.loose });
});
const picks = [];
const bySteps = [...new Set(cands.map(c => c.step))].sort((a, b) => a - b);
for (let i = 0; picks.length < COUNT && i < COUNT * 4; i++) {
  const s = bySteps[Math.floor((i % COUNT) / COUNT * bySteps.length + i / COUNT) % bySteps.length];
  const c = cands.find(c => c.step === s && !picks.includes(c));
  if (c) picks.push(c);
}

let missed = 0;
function attempt(name, c, mutateFn) {
  const P = load(file);
  const ev = P.BODY[c.id].events[c.ei];
  const last = ev.path[ev.path.length - 1];
  const off = last.off.slice();
  mutateFn(off, P);
  ev.path[ev.path.length - 1] = Object.assign({}, last, { off });
  const r = P.verify({ samples: 12 });
  const kinds = {}; r.issues.forEach(i => kinds[i.kind] = (kinds[i.kind] || 0) + 1);
  if (r.ok) missed++;
  console.log(`${r.ok ? 'MISSED' : 'caught'}  ${name}: ${P.label(c.id)} (step ${c.step})  ${r.ok ? '' : JSON.stringify(kinds)}`);
}
picks.forEach(c => {
  const touching = base.contacts(c.step, c.id);
  // push toward the neighbour it rests on or against; prefer one below it, then any other
  const t = touching.find(t => t.axis === 2 && t.dir === -1) || touching[0];
  if (t) attempt('push ' + 'xyz'[t.axis] + (t.dir > 0 ? '+' : '-') + ' into ' + base.label(t.other), c, off => { off[t.axis] += t.dir * 0.25 * U; });
  if (c.loose) attempt('float 1/8 up', c, off => { off[2] += 0.125 * U; });
});
console.log(missed ? `FAIL: ${missed} broken moves were not caught` : 'PASS: every broken move was caught');
process.exit(missed ? 1 : 0);
