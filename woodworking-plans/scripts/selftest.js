#!/usr/bin/env node
/* Self-test: the castle bed passes clean, each deliberate break is caught, and the helpers,
 * validation, automatic explode and review worksheet behave.
 *   node scripts/selftest.js
 */
const path = require('path');
const { execFileSync } = require('child_process');
const C = require('./plan-core.js');
const J = require('./joints.js');
const X = require('./explode.js');
const { prepare } = require('./plan-load.js');
const { validate } = require('./validate.js');
const bed = require('../examples/castle-bed/plan.js');
const BED = path.join(__dirname, '../examples/castle-bed/plan.js');
const part = (p, id) => p.parts.find(x => x.id === id);
const params = f => { const P = JSON.parse(JSON.stringify(bed.PARAMS)); f(P); return P; };
const make = P => prepare(bed(P || bed.PARAMS, J));
const has = (R, code) => R.errors.concat(R.warnings).some(e => e.code === code);

// model check: each break must be caught by the code given
const cases = [
  ['clean plan', () => {}, R => !R.errors.length && !R.warnings.length],
  ['post slots removed', p => { part(p, '1').shape = part(p, '1').shape.slice(0, 1); }, R => has(R, 'interference')],
  ['cut list length wrong', p => { part(p, '3').l = 90; }, R => has(R, 'dims')],
  ['tenon breaks out of its rail', p => { const s = part(p, '11'); const t = s.shape.find(x => x.role === 'tenon'); t.box[2] -= 4.5; t.box[5] += 4.5; s.l += 4.5; }, R => has(R, 'tenon-seat') || has(R, 'dims')],
  ['joint not declared', p => { p.joints = p.joints.filter(j => j.id !== 'J8'); }, R => has(R, 'undeclared-contact')],
  ['headboard pulled off the rails', p => { ['8', '9', '10', '11'].forEach(id => part(p, id).instances.forEach(i => { i.at[1] += 1; })); p.bores = []; }, R => has(R, 'floating') && has(R, 'joint-no-contact')],
  ['castle towers too thin', p => Object.assign(p, make(params(P => { P.railT = 2.5; }))), R => has(R, 'castle-tower')],
  ['tenon too thick', p => { const s = part(p, '9'); s.shape.filter(x => x.role === 'tenon').forEach(t => { t.box[1] = 0.1; t.box[4] = 1.05; }); }, R => has(R, 'tenon-ratio')],
  ['quantity mismatch', p => { part(p, '7').qty = 13; }, R => has(R, 'qty')],
  ['title block size wrong', p => { p.meta.overall.w = 70; }, R => has(R, 'overall')],
  // the three problems the Rev C review found by hand, now caught by the check
  ['barrel nuts under the corner post (2" overhang)', p => { Object.assign(p, make(params(P => { P.ext = 2; }))); delete p.meta.overall; }, R => has(R, 'bore-blocked')],
  ['counterbore too small for the washer', p => { p.bores[0].counterbore.d = 0.625; }, R => has(R, 'counterbore')],
  ['castle slots listed for a dado stack', p => { part(p, '1').shape.forEach(s => { if (s.cut) s.tool = 'dado'; }); }, R => has(R, 'tool-depth')],
  ['cross-bolt too short for its nut', p => { p.bores[0].len = 7; }, R => has(R, 'bolt-short')],
  ['bolt line misses the nut', p => { p.bores[1].copies.forEach(c => { c.at[2] -= 1; }); }, R => has(R, 'bolt-misses-nut')],
  ['cleat screw too short', p => { p.bores[4].len = 1.5; }, R => has(R, 'screw-length')],
  ['slat screw comes through the cleat', p => { p.bores[5].len = 3; }, R => has(R, 'fastener-exits')],
  ['bit too short for the cross-bolt', p => { p.bores[0].bit = 6; }, R => has(R, 'bit-reach')]
];
let fail = 0;
const out = (ok, name, why) => { if (!ok) fail++; console.log((ok ? 'ok   ' : 'FAIL ') + name + (ok || !why ? '' : '  -> ' + why)); };
for (const [name, mut, ok] of cases) {
  const p = make(); mut(p);
  const R = C.check(p);
  out(ok(R), name, JSON.stringify(R.errors.concat(R.warnings).map(e => e.code)));
}

// validation
const vcases = [
  ['bed validates clean', () => {}, V => !V.length],
  ['typo in a key', p => { part(p, '1').qyt = 4; }, V => V.some(v => v.level === 'warn' && /qyt/.test(v.at))],
  ['chip to a missing part', p => { p.steps[0].text += ' {#99}'; }, V => V.some(v => v.level === 'error' && /\{#99\}/.test(v.msg))],
  ['verdict that is not the worst line', p => { p.review[1].verdict = 'flag'; }, V => V.some(v => v.level === 'error' && /verdict/.test(v.at))],
  ['change with no review', p => { p.revisions[2].changes.push({ id: 'C7', summary: 'x', parts: ['1'] }); }, V => V.some(v => /C7 has no review/.test(v.msg))],
  ['review left as TODO', p => { p.review[0].checks[0].evidence = 'TODO'; }, V => V.some(v => /TODO/.test(v.msg))],
  ['step names a missing part', p => { p.steps[0].parts.push('42'); }, V => V.some(v => v.level === 'error' && /42/.test(v.msg))],
  ['crossing detail leaders warn, never fail', p => { (p.details = p.details || []).push({ title: 'X', items: [{ callout: [0, 0, '1'], to: [4, 4] }, { callout: [4, 0, '2'], to: [0, 4] }] }); }, V => V.some(v => v.level === 'warn' && /balloons 1 and 2 cross/.test(v.msg)) && !V.some(v => v.level === 'error')]
];
for (const [name, mut, ok] of vcases) { const p = make(); mut(p); const V = validate(p); out(ok(V), 'validate: ' + name, JSON.stringify(V)); }

// joint helpers on a small carcass: a shelf dadoed into two sides, an apron tenoned into two legs
{
  const side = x => ({ at: [x, 0, 0] });
  const sides = { id: '1', name: 'Sides', qty: 2, t: 0.75, w: 11.25, l: 30, stock: 'solid', shape: [{ box: [0, 0, 0, 0.75, 11.25, 30] }], instances: [side(0), { at: [24, 0, 0], mirror: 'x' }] };   // the right side mirrored, so its dado faces in
  const shelf = { id: '2', name: 'Shelf', qty: 1, t: 0.75, w: 11.25, l: 22.5, stock: 'solid', shape: [{ box: [0, 0, 0, 22.5, 11.25, 0.75] }], instances: [{ at: [0.75, 0, 12] }] };
  const legs = { id: '3', name: 'Legs', qty: 2, t: 1.75, w: 1.75, l: 29, stock: 'solid', shape: [{ box: [0, 0, 0, 1.75, 1.75, 29] }], instances: [{ at: [40, 0, 0] }, { at: [70, 0, 0] }] };
  const apron = { id: '4', name: 'Apron', qty: 1, t: 0.75, w: 4, stock: 'solid', shape: [{ box: [0, 0, 0, 28.25, 0.75, 4] }], instances: [{ at: [41.75, 0.5, 24] }] };
  const js = [J.dado({ host: sides, guest: shelf }), J.mortiseTenon({ rail: apron, hosts: [legs] })];
  out(shelf.l === 23 && sides.shape.filter(s => s.cut).length === 1, 'J.dado lengthens the shelf by both 1/4" dados (a third of the side) and cuts one dado per side', 'shelf.l ' + shelf.l);
  const tn = apron.shape.filter(s => s.role === 'tenon');
  out(tn.length === 4 && tn.every(t => t.box[4] === 0.25 && t.box[3] === 1.1875 && t.box[5] === 1.25) && apron.l === 30.625,
    'J.mortiseTenon: 1/4" tenons (a third of 3/4"), 1-3/16" long (2/3 of the leg), twinned (3" would be 12x), l updated', JSON.stringify(tn.map(t => t.box)) + ' l ' + apron.l);
  for (const [name, ps, j] of [['carcass', [sides, shelf], js[0]], ['leg and apron', [legs, apron], js[1]]]) {
    const R = C.check({ meta: { title: 't' }, parts: ps, joints: [j] });
    out(!R.errors.length && !R.warnings.length, 'helper-built ' + name + ' passes the model check', JSON.stringify(R.errors.concat(R.warnings).map(e => e.msg)));
  }
  let threw = false; try { const a = JSON.parse(JSON.stringify(sides)); delete a.instances[1].mirror; J.dado({ host: a, guest: JSON.parse(JSON.stringify(shelf)) }); } catch (e) { threw = /different cuts|must touch/.test(e.message); }
  out(threw, 'helpers refuse copies that would need different cuts');
}

// automatic explode: the bed with every vector removed explodes with nothing passing through anything
{
  const p = bed(bed.PARAMS, J);
  p.parts.forEach(q => q.instances.forEach(i => delete i.explode));
  prepare(p);
  const hit = X.collisions(p), lifted = p.parts.find(q => q.id === '7').instances.every(i => i.explode[2] > p.parts.find(q => q.id === '3').instances[0].explode[2]);
  out(!hit.length && lifted, 'auto explode: no collisions, slats above the side rails', JSON.stringify(hit));
  out(!X.collisions(make()).length, 'hand-set explode on the bed: no collisions');
}

// the dresser: a sheet-goods case with slides; it passes clean, and its fastener breaks are caught
{
  const dr = require('../examples/modern-dresser/plan.js');
  const mk = () => prepare(dr(dr.PARAMS, J));
  const p0 = mk(), R0 = C.check(p0);
  out(!R0.errors.length && !R0.warnings.length && !validate(p0).length, 'dresser: clean plan', JSON.stringify(R0.errors.concat(R0.warnings).map(e => e.msg)));
  const p1 = mk(); p1.bores.find(b => b.id === 'B2').copies.forEach(c => { if (c.dir === '-x' && c.at[0] > 30) c.at[1] -= 1; });
  out(has(C.check(p1), 'bore-cross'), 'dresser: slide screws from both faces of the divider meet');
  const p2 = mk(); delete p2.bores.find(b => b.id === 'B2').hardware;
  const R2 = C.check(p2), sl = R2.warnings.filter(w => w.code === 'screw-length');
  out(sl.length === 1 && /more copies/.test(sl[0].msg), 'dresser: slide screws without `hardware` warn once, grouped across copies', JSON.stringify(sl.map(w => w.msg)));
}

// review worksheet
{
  const r = execFileSync(process.execPath, [path.join(__dirname, 'build_plan.js'), BED, '--review', '--change', 'C1'], { encoding: 'utf8' });
  out(/Touches: #2 End Rails/.test(r) && /Mates: #1 Corner Posts/.test(r) && /step 5 "Bore for the bed bolts"/.test(r) && /evidence: "TODO"/.test(r), 'review worksheet lists touches, mates, paperwork and a record skeleton');
}
// shop paperwork: cut order, cut list, shopping list, tools, story sticks, metric, new-field validation
{
  const SK = require('../examples/skeleton/plan.js'), sk = prepare(SK(SK.PARAMS, J)), Msk = C.normalize(sk);
  const bd = { shelves: [{ y: 0, h: 20, used: 0 }, { y: 20.125, h: 10, used: 0 }], items: [{ pc: { w: 20, l: 50 }, x: 0, y: 0 }, { pc: { w: 18, l: 30 }, x: 50.125, y: 0 }, { pc: { w: 10, l: 96 }, x: 0, y: 20.125 }] };
  const cuts = C.cutOrder(bd, { w: 48, l: 96, kerf: 0.125 });
  out(cuts[0].kind === 'rip' && cuts[0].y1 === 20 && cuts.filter(c => c.kind === 'rip').length === 2 && cuts.some(c => c.kind === 'cross' && c.x1 === 50) && cuts.some(c => c.kind === 'trim' && c.y1 === 18) && !cuts.some(c => c.kind === 'cross' && c.x1 === 96),
    'sheet cut order: rips first, then crosscuts, then trims; no cut at the sheet edge', JSON.stringify(cuts));
  const cl = C.cutList(Msk).map(r => r.p.id);
  out(cl.join() === '1,4,2,3', 'shop cut list sorts by thickness, then width, then length', cl.join());
  const top = C.cutList(Msk).find(r => r.p.id === '4');
  out(top.rough.t === 1 && top.rough.w === 16.25 && top.rough.l === 21, 'rough size adds the milling allowance and rounds thickness up to 4/4', JSON.stringify(top.rough));
  const buy = C.buyList(Msk, sk), b44 = buy.find(b => /^4\/4 Cherry/.test(b.name));
  out(b44 && b44.glued && b44.glued.includes('4') && b44.drawn === 2 && b44.buy === 3, 'shopping list counts glue-up strips for a top wider than the board, plus a spare', JSON.stringify(buy));
  const dm = C.buyList(Msk, Object.assign({}, sk, { stock: { buy: 'dimensional' } }));
  out(dm.some(b => /^1x8 Cherry/.test(b.name)), 'stock.buy dimensional names boards 1x8');
  const tools = C.toolsFor(Msk, sk);
  out(tools.some(t => /Mortiser/.test(t)) && tools.some(t => /button groove/.test(t)), 'tools list follows the joints', tools.join(' | '));
  const st = C.storyMarks(Msk, { axis: 'z', parts: ['1', '2'] });
  out(st.len === 23.25 && st.marks.map(m => m.d).join() === '0,19.25,23.25', 'story stick merges edges along the axis', JSON.stringify(st.marks));
  globalThis.PlanUnits = 'mm'; const mmTxt = C.fmt(0.75); globalThis.PlanUnits = 'in';
  out(mmTxt === '19 mm' && C.fmt(0.75) === '3/4"', 'units toggle formats millimetres and back', mmTxt);
  out(!validate(sk).length, 'skeleton (every field, new paperwork included) validates clean', JSON.stringify(validate(sk)));
  const bad = JSON.parse(JSON.stringify(sk));
  bad.view.sections[0].cut = 'w'; bad.story_sticks[0].parts = ['99']; bad.jigs[0].items = []; bad.steps[2].wrong = 3;
  const v = validate(bad).filter(e => e.level === 'error').map(e => e.at);
  out(['view.sections[0].cut', 'story_sticks[0].parts', 'jigs[0].items', 'steps[2].wrong'].every(a => v.includes(a)), 'validation catches bad sections, sticks, jigs and "don\'t" panels', v.join(', '));
}
process.exit(fail ? 1 : 0);
