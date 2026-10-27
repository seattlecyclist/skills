/* Modern eight-drawer dresser: two banks of four graduated drawers in a walnut plywood case on a
 * recessed plinth, with integrated finger pulls and every drawer box fully detailed.
 * Every number derives from PARAMS. Build:  node ../../scripts/build_plan.js plan.js out.html
 */
const PARAMS = {
  rev: 'A',
  w: 60, caseD: 19.25, caseH: 30.5,   // case outside; the fronts add their thickness to the depth
  ply: 0.75, back: 0.25,              // case plywood, back panel
  plinth: { h: 3.5, t: 0.75, front: 1.5, side: 1, rear: 0.5 },   // set back from the case faces
  fronts: [7.875, 7.25, 6.75],        // front heights, bottom row up; the top row takes the rest
  frontT: 0.75, seam: 0.125, rowGap: 0.75,   // vertical seam between banks, shadow gap between rows
  pull: { depth: 0.375, h: 0.875 },       // finger relief on the back of each front's bottom edge
  slide: { t: 33 / 64, h: 1.75, l: 18, setback: 0.125 },  // 18" full-extension slide; t: clearance per side, mid-window of 1/2" to 17/32"
  box: { t: 15 / 32, bottom: 0.25,   // t: 12 mm Baltic birch, modeled at its real 15/32"
          groove: 0.5, joint: 0.25, top: 0.25, floor: 0.25, step: 0.25 }
};

module.exports = function build(P = PARAMS, J = require('../../scripts/joints.js')) {
  const C = require('../../scripts/plan-core.js');
  const F = v => C.fmt(v, { unit: false });
  const r = v => Math.round(v * 1e6) / 1e6;
  const T = P.ply, Z0 = P.plinth.h, B = P.box, S = P.slide;
  const xDiv = P.w / 2 - T / 2, bankW = xDiv - T, backY = P.caseD - P.back;
  const banks = [T, xDiv + T];                         // inside left edge of each bank
  const boxW = bankW - 2 * S.t, boxD = S.l;
  const zInTop = P.caseH - T;                          // underside of the case top, from the case bottom

  // fronts tile the case height: rows bottom up, the top row takes what is left
  const fh = P.fronts.slice();
  fh.push(r(P.caseH - fh.reduce((a, b) => a + b, 0) - (fh.length) * P.rowGap));
  const rows = [];
  let z = 0;
  fh.forEach((h, i) => {
    const bot = z, top = z + h;
    const boxBot = Math.max(bot + P.pull.h, T + B.floor);   // above the finger relief, and 1/4" over the case bottom
    const limit = Math.min(top, zInTop - B.top);
    const bh = Math.floor((limit - boxBot) / B.step + 1e-6) * B.step;
    rows.push({ i, bot, top, h, boxBot, bh, slideC: r(boxBot + bh / 2) });
    z = top + P.rowGap;
  });
  const NAMES = ['Bottom', 'Third', 'Second', 'Top'];
  const fw = (P.w - P.seam) / 2;
  // explode by hand: drawers come out the front, the case opens around them
  const OUT = { box: -22, side: 2, end: 2, front: -46, lift: 3 };   // lift: extra rise per row, so the rows separate

  // ---------- case ----------
  const side = { id: '1', name: 'Case Sides', section: 'case', qty: 2, t: T, w: P.caseD, l: P.caseH, material: 'Walnut plywood', stock: 'sheet',
    note: 'Iron-on walnut banding on the top edges. Grain runs up.',
    shape: [{ box: [0, 0, 0, T, P.caseD, P.caseH] }],
    instances: [{ at: [0, 0, Z0], explode: [-10, 0, 0] }, { at: [P.w, 0, Z0], mirror: 'x', explode: [10, 0, 0] }] };
  const top = { id: '2', name: 'Case Top', section: 'case', qty: 1, t: T, w: P.caseD, l: P.w - 2 * T, material: 'Walnut plywood', stock: 'sheet',
    note: 'Band the front and back edges. Grain runs side to side.',
    shape: [{ box: [0, 0, 0, P.w - 2 * T, P.caseD, T] }], instances: [{ at: [T, 0, Z0 + P.caseH - T], explode: [0, 0, 10] }] };
  const bottom = { id: '3', name: 'Case Bottom', section: 'case', qty: 1, t: T, w: P.caseD, l: P.w - 2 * T, material: 'Walnut plywood', stock: 'sheet',
    shape: [{ box: [0, 0, 0, P.w - 2 * T, P.caseD, T] }], instances: [{ at: [T, 0, Z0], explode: [0, 0, -4] }] };
  const divider = { id: '4', name: 'Divider', section: 'case', qty: 1, t: T, w: backY, l: P.caseH - 2 * T, material: 'Walnut plywood', stock: 'sheet',
    note: 'Slides mount on both faces; stagger the screws (see Divider Slide Screws).',
    shape: [{ box: [0, 0, 0, T, backY, P.caseH - 2 * T] }], instances: [{ at: [xDiv, 0, Z0 + T], explode: [0, 0, 3] }] };
  const back = { id: '5', name: 'Back', section: 'case', qty: 1, t: P.back, w: P.caseH - 2 * T, l: P.w - 2 * T, material: 'Walnut plywood', stock: 'sheet',
    note: 'Glued into the rabbets; it squares the case.',
    shape: [{ box: [0, 0, 0, P.w - 2 * T, P.back, P.caseH - 2 * T] }], instances: [{ at: [T, backY, Z0 + T], explode: [0, 14, 3] }] };

  // ---------- plinth ----------
  const PL = P.plinth, plX0 = PL.side, plX1 = P.w - PL.side, plY0 = PL.front, plY1 = P.caseD - PL.rear;
  const rail = { id: '6', name: 'Plinth Front & Back', section: 'base', qty: 2, t: PL.t, w: PL.h, l: plX1 - plX0, material: 'Poplar', stock: 'solid', mat: 'paint',
    note: 'Paint black so the case floats over a shadow.',
    shape: [{ box: [0, 0, 0, plX1 - plX0, PL.t, PL.h] }],
    instances: [{ at: [plX0, plY0, 0], explode: [0, -3, -12] }, { at: [plX0, plY1, 0], mirror: 'y', explode: [0, 3, -12] }] };
  const endL = plY1 - plY0 - 2 * PL.t;
  const plEnd = { id: '7', name: 'Plinth Ends', section: 'base', qty: 2, t: PL.t, w: PL.h, material: 'Poplar', stock: 'solid', mat: 'paint',
    shape: [{ box: [0, 0, 0, PL.t, endL, PL.h] }],
    instances: [{ at: [plX0, plY0 + PL.t, 0], explode: [-3, 0, -12] }, { at: [plX1, plY0 + PL.t, 0], mirror: 'x', explode: [3, 0, -12] }] };
  const stretch = { id: '8', name: 'Plinth Stretcher', section: 'base', qty: 1, t: PL.t, w: PL.h, material: 'Poplar', stock: 'solid', mat: 'paint',
    note: 'Sits under the divider.',
    shape: [{ box: [0, 0, 0, PL.t, endL, PL.h] }], instances: [{ at: [xDiv, plY0 + PL.t, 0], explode: [0, 0, -12] }] };

  // ---------- slides and drawer boxes ----------
  const slides = { id: '9', name: 'Drawer Slides', section: 'boxes', qty: 0, t: S.t, w: S.h, l: S.l, material: 'Steel', stock: 'hardware', mat: 'hardware',
    size: S.l + '" full-extension ball bearing, 1/2" side', shape: [{ box: [0, 0, 0, S.t, S.l, S.h] }], instances: [] };
  for (const R of rows) for (const bx of banks) for (const [x, sx] of [[bx, -1], [bx + S.t + boxW, 1]])
    slides.instances.push({ at: [r(x), S.setback, r(Z0 + R.slideC - S.h / 2)], explode: [sx * 2.75, OUT.box, R.i * OUT.lift] });
  slides.qty = slides.instances.length;

  // drawer parts top row first, so part numbers follow the build (top drawers are built first)
  let id = 10;
  const drawer = [];
  for (const R of rows.slice().reverse()) {
    const nm = NAMES[R.i], zb = Z0 + R.boxBot, h = R.bh, sec = 'boxes', up = R.i * OUT.lift;
    const sides = { id: String(id++), name: nm + ' Box Sides', section: sec, qty: 4, t: B.t, w: h, l: boxD, material: 'Baltic birch', stock: 'sheet',
      shape: [{ box: [0, 0, 0, B.t, boxD, h] }],
      instances: banks.flatMap(bx => [{ at: [r(bx + S.t), 0, zb], explode: [-OUT.side, OUT.box, up] }, { at: [r(bx + S.t + boxW), 0, zb], mirror: 'x', explode: [OUT.side, OUT.box, up] }]) };
    const fb = { id: String(id++), name: nm + ' Box Fronts & Backs', section: sec, qty: 4, t: B.t, w: h, material: 'Baltic birch', stock: 'sheet',
      shape: [{ box: [0, 0, 0, boxW - 2 * B.t, B.t, h] }],
      instances: banks.flatMap(bx => [{ at: [r(bx + S.t + B.t), 0, zb], explode: [0, OUT.box - OUT.end, up] }, { at: [r(bx + S.t + B.t), boxD, zb], mirror: 'y', explode: [0, OUT.box + OUT.end, up] }]) };
    const bot = { id: String(id++), name: nm + ' Box Bottoms', section: sec, qty: 2, t: B.bottom, w: boxD - 2 * B.t, l: boxW - 2 * B.t, material: 'Baltic birch', stock: 'sheet',
      shape: [{ box: [0, 0, 0, boxW - 2 * B.t, boxD - 2 * B.t, B.bottom] }],
      instances: banks.map(bx => ({ at: [r(bx + S.t + B.t), B.t, zb + B.groove], explode: [0, OUT.box, up - 1.25] })) };
    drawer.push({ R, sides, fb, bot });
  }
  const fronts = [];
  for (const R of rows.slice().reverse()) {
    const f = { id: String(id++), name: NAMES[R.i] + ' Drawer Fronts', section: 'fronts', qty: 2, t: P.frontT, w: R.h, l: fw, material: 'Walnut plywood, fronts sheet', stock: 'sheet',
      note: 'Cut in sequence from one sheet so the grain runs on across the bank.',
      shape: [{ box: [0, 0, 0, fw, P.frontT, R.h] },
        { cut: [-1, P.frontT - P.pull.depth, -1, fw + 2, P.pull.depth + 1, P.pull.h + 1], tool: 'router table' }],
      instances: [{ at: [0, -P.frontT, Z0 + R.bot], explode: [0, OUT.front, R.i * OUT.lift] }, { at: [r(fw + P.seam), -P.frontT, Z0 + R.bot], explode: [0, OUT.front, R.i * OUT.lift] }] };
    fronts.push({ R, f });
  }

  // ---------- joints ----------
  const joints = [
    J.rabbet({ host: side, guest: top, depth: T / 2, title: 'Top in side rabbets', fasteners: 'Glue, clamps', tool: 'router' }),
    J.rabbet({ host: side, guest: bottom, depth: T / 2, title: 'Bottom in side rabbets', fasteners: 'Glue, clamps', tool: 'router' }),
    J.dado({ host: top, guest: divider, depth: 0.25, title: 'Divider in top', fasteners: 'Glue', tool: 'router' }),
    J.dado({ host: bottom, guest: divider, depth: 0.25, title: 'Divider in bottom', fasteners: 'Glue', tool: 'router' }),
    J.rabbet({ host: side, guest: back, depth: T / 2, title: 'Back in side rabbets', fasteners: 'Glue, 5/8" brads', tool: 'router' }),
    J.rabbet({ host: top, guest: back, depth: T / 2, title: 'Back in top rabbet', fasteners: 'Glue, 5/8" brads', tool: 'router' }),
    J.rabbet({ host: bottom, guest: back, depth: T / 2, title: 'Back in bottom rabbet', fasteners: 'Glue, 5/8" brads', tool: 'router' }),
    J.joint('screwed', [back, divider], { title: 'Back to divider', fasteners: 'Five #6 × 5/8" screws', note: 'Ties the divider to the back so it stays straight and the slides stay parallel.' }),
    J.rabbet({ host: rail, guest: plEnd, depth: PL.t / 2, title: 'Plinth corners', glue: true, fasteners: 'Glue, 1-1/4" brads', tool: 'tablesaw' }),
    J.dado({ host: rail, guest: stretch, depth: 0.25, title: 'Plinth stretcher', fasteners: 'Glue', tool: 'tablesaw' }),
    J.joint('screwed', [bottom, rail, plEnd, stretch], { title: 'Case to plinth', fasteners: 'Twelve #8 × 1-1/2" screws down through the case bottom', note: 'Countersink flush; the bottom drawers run 1/4" above the heads. The stretcher is not screwed; it carries the divider.' }),
    J.joint('screwed', [slides, side, divider].concat(drawer.map(d => d.sides)), { title: 'Drawer slides', fasteners: '#6 × 5/8" into the case, #6 × 3/8" into the boxes', note: 'Both members set 1/8" back from the case and box fronts, so the slide never touches the drawer front.' })
  ];
  for (const d of drawer) {
    joints.push(J.rabbet({ host: d.sides, guest: d.fb, depth: B.joint, title: NAMES[d.R.i] + ' box corners', fasteners: 'Glue, 1" brads', tool: 'tablesaw' }));
    joints.push(J.groove({ host: d.sides, guest: d.bot, depth: 0.25, title: NAMES[d.R.i] + ' box bottom in sides', glue: false, fasteners: 'None; captured', tool: 'tablesaw' }));
    joints.push(J.groove({ host: d.fb, guest: d.bot, depth: 0.25, title: NAMES[d.R.i] + ' box bottom in front and back', glue: false, fasteners: 'None; captured', tool: 'tablesaw' }));
  }
  for (const { R, f } of fronts) {
    const d = drawer.find(x => x.R === R);
    R.jid = 'J' + (joints.length + 1);
    joints.push(J.joint('screwed', [f, d.fb, d.sides], { title: NAMES[R.i] + ' fronts to boxes', fasteners: 'Four #8 × 1" screws from inside the box', note: 'Clearance holes in the box front let you shift the front 1/16" before the last screws go in.' }));
  }
  joints.push(J.joint('rests', fronts.map(x => x.f).concat([side, top, bottom, divider]), { title: 'Fronts close on the case', fasteners: 'Bumper dots, two per front', note: 'The fronts are the drawer stops; the slides stop them at full extension.' }));

  // ---------- bores ----------
  const bores = [];
  // case to plinth: down through the bottom into the plinth edges
  const plScrews = [8, 20, 40, 52].flatMap(x => [[x, plY0 + PL.t / 2], [x, plY1 - PL.t / 2]]).concat([plX0 + PL.t / 2, plX1 - PL.t / 2].flatMap(x => [[x, 6], [x, 14]]));
  bores.push({ id: 'B1', joint: 'J11', kind: 'screw', label: '#8 × 1-1/2" screw', d: 0.164, len: 1.5, access: 0.25,
    copies: plScrews.map(([x, y]) => ({ at: [x, y, Z0 + T], dir: '-z' })) });
  // slide cabinet members: case sides and both faces of the divider; the two faces use holes 1" apart
  const slideCase = [];
  for (const R of rows) {
    const zc = r(Z0 + R.slideC);
    for (const y of [2, 9, 16]) { slideCase.push({ at: [T, y, zc], dir: '-x' }); slideCase.push({ at: [xDiv, y, zc], dir: '+x' }); }
    for (const y of [3, 10, 17]) { slideCase.push({ at: [xDiv + T, y, zc], dir: '-x' }); slideCase.push({ at: [P.w - T, y, zc], dir: '+x' }); }
  }
  bores.push({ id: 'B2', joint: 'J12', kind: 'screw', label: '#6 × 5/8" slide screw', d: 0.138, len: 0.625, access: 0, hardware: true, copies: slideCase });
  const slideBox = [];
  for (const R of rows) for (const bx of banks) for (const y of [2, 9, 16]) {
    const zc = r(Z0 + R.slideC);
    slideBox.push({ at: [r(bx + S.t), y, zc], dir: '+x' }, { at: [r(bx + S.t + boxW), y, zc], dir: '-x' });
  }
  bores.push({ id: 'B3', joint: 'J12', kind: 'screw', label: '#6 × 3/8" slide screw', d: 0.138, len: 0.375, access: 0, hardware: true, copies: slideBox });
  // fronts to boxes, from inside each box front
  rows.slice().reverse().forEach((R, k) => {
    const copies = [];
    for (const bx of banks) for (const x of [bx + S.t + 3, bx + S.t + boxW - 3]) for (const zz of [R.boxBot + 1.5, R.boxBot + R.bh - 1])
      copies.push({ at: [r(x), B.t, r(Z0 + zz)], dir: '-y' });
    bores.push({ id: 'B' + (6 + k), joint: R.jid, kind: 'screw', label: '#8 × 1" washer-head screw', d: 0.164, len: 1, copies });
  });
  bores.push({ id: 'B5', joint: 'J8', kind: 'screw', label: '#6 × 5/8" screw', d: 0.138, len: 0.625,
    copies: [3, 9, 15, 21, 26].map(zz => ({ at: [P.w / 2, P.caseD, Z0 + zz], dir: '-y' })) });

  // ---------- paperwork ----------
  const allParts = [side, top, bottom, divider, back, rail, plEnd, stretch, slides].concat(drawer.flatMap(d => [d.sides, d.fb, d.bot]), fronts.map(x => x.f));
  const byRowTop = rows.slice().reverse();
  const sl = byRowTop.map(R => NAMES[R.i].toLowerCase() + ' ' + F(R.slideC - T) + '"').join(', ');
  const boxList = byRowTop.map(R => F(R.bh) + '"').join(', ');
  const frontList = byRowTop.map(R => F(R.h) + '"').join(', ');
  const fid = n => fronts.find(x => NAMES[x.R.i] === n).f.id;
  const did = (n, k) => drawer.find(x => NAMES[x.R.i] === n)[k].id;
  const boxIds = drawer.flatMap(d => [d.sides.id, d.fb.id, d.bot.id]);
  const frontIds = fronts.map(x => x.f.id);
  const top4 = rows[3];
  // finger pull section: lower front top, the gap, upper front with its relief; y is depth (front face at 0), v is height
  const lo = rows[1], up = rows[2], fT = P.frontT, pd = P.pull.depth;
  const v0 = lo.top - 2.5;
  const pullDetail = {
    title: 'Finger Pull Section', sub: 'through the gap between the second and third rows', w: 8, h: 7,
    items: [
      { rect: [0, lo.top - 2.5 - v0, fT, 2.5], fill: 'end', part: fid(NAMES[lo.i]) },
      { poly: [[0, up.bot - v0], [fT - pd, up.bot - v0], [fT - pd, up.bot + P.pull.h - v0], [fT, up.bot + P.pull.h - v0], [fT, up.bot + 3 - v0], [0, up.bot + 3 - v0]], fill: 'end', part: fid(NAMES[up.i]) },
      { rect: [fT, up.boxBot - v0, B.t, 2.4], fill: 'end', part: did(NAMES[up.i], 'fb') },
      { rect: [fT, lo.boxBot + lo.bh - 1.8 - v0, B.t, 1.8], fill: 'end', part: did(NAMES[lo.i], 'fb') },
      { rect: [fT + B.t - 0.25, up.boxBot + B.groove - v0, 2.75, B.bottom], fill: 'wood', part: did(NAMES[up.i], 'bot') },
      { line: [fT, up.bot - 0.6 - v0, fT, up.bot + P.pull.h + 0.6 - v0], dash: true },
      { dim: [fT + B.t, lo.top - v0, fT + B.t, up.bot - v0], off: -0.9, text: F(P.rowGap) + '" gap' },
      { dim: [0, up.bot - v0, 0, up.bot + P.pull.h - v0], off: 0.9 },
      { dim: [fT - pd, up.bot + 3 - v0, fT, up.bot + 3 - v0], off: 0.6 },
      { dim: [0, up.bot + 3 - v0, fT, up.bot + 3 - v0], off: 1.3 },
      { text: [fT + 0.2, up.bot + 0.35 - v0, 'finger relief'], size: 0.5, anchor: 'start' },
      { text: [-0.25, up.bot - 0.45 - v0, 'fingers in'], size: 0.5, anchor: 'end' },
      { callout: [-1.6, lo.top - 1.6 - v0, fid(NAMES[lo.i])], to: [0.2, lo.top - 1.6 - v0] },
      { callout: [-1.6, up.bot + 2.4 - v0, fid(NAMES[up.i])], to: [0.2, up.bot + 2.4 - v0] },
      { callout: [4, up.boxBot + 1.6 - v0, did(NAMES[up.i], 'fb')], to: [fT + B.t - 0.1, up.boxBot + 1.6 - v0] }
    ]
  };
  // box corner: plan section at the front of a box, x across, y back
  const cornerDetail = {
    title: 'Box Corner & Slide', sub: 'plan section at a front corner, any drawer', w: 7.5, h: 6.5,
    items: [
      { rect: [-S.t - T, -fT, 5.75, fT], fill: 'wood', part: fid('Top') },
      { rect: [-S.t - T, 0, T, 4.5], fill: 'wood', part: side.id },
      { rect: [-S.t, S.setback, S.t, 4.375], fill: 'steel', part: slides.id },
      { poly: [[0, 0], [B.t - B.joint, 0], [B.t - B.joint, B.t], [B.t, B.t], [B.t, 4.5], [0, 4.5]], fill: 'end', part: did('Top', 'sides') },
      { rect: [B.t - B.joint, 0, 4.5 - (B.t - B.joint), B.t], fill: 'wood', part: did('Top', 'fb') },
      { dim: [-S.t, 4.5, 0, 4.5], off: 0.6, text: '1/2" to 17/32"' },
      { dim: [0, -fT, B.t - B.joint, -fT], off: -0.7 },
      { dim: [4.5, 0, 4.5, B.t], off: -0.6 },
      { dim: [4.5, -fT, 4.5, 0], off: -1.4 },
      { text: [-S.t / 2, 5.9, 'slide'], size: 0.5 },
      { text: [B.t + 0.3, 2.6, 'glue + 1" brads'], size: 0.5, anchor: 'start' },
      { callout: [-2.8, 2.5, side.id], to: [-S.t - T + 0.2, 2.5] },
      { callout: [3, 1.6, did('Top', 'fb')], to: [3, B.t - 0.1] },
      { callout: [1.6, 3.6, did('Top', 'sides')], to: [B.t - 0.1, 3.6] },
      { callout: [2, -1.9, fid('Top')], to: [2, -fT + 0.15] }
    ]
  };
  const divDetail = {
    title: 'Divider Slide Screws', sub: 'side view of the divider at one slide height', w: 21, h: 6, wide: true,
    items: [
      { rect: [0, 0, 19, 2.4], fill: 'wood', part: divider.id },
      ...[2, 9, 16].map(y => ({ rect: [y - 0.12, 1.08, 0.24, 0.24], fill: 'steel' })),
      ...[3, 10, 17].map(y => ({ rect: [y - 0.12, 1.08, 0.24, 0.24], fill: 'none' })),
      { dim: [0, 2.4, 2, 2.4], off: 0.5 },
      { dim: [2, 2.4, 3, 2.4], off: 0.5 },
      { dim: [2, 2.4, 9, 2.4], off: 1.2 },
      { text: [9.5, -0.9, 'solid: left bank, driven from the left face'], size: 0.7 },
      { text: [9.5, -1.9, 'open: right bank, driven from the right face'], size: 0.7 }
    ]
  };

  // drawer openings: each row of each bank, between the case side and the divider; with no rails,
  // a row's opening runs from its front's bottom edge to the next front up (case top for the top row)
  const drawers = byRowTop.map(R => {
    const d = drawer.find(x => x.R === R), f = fronts.find(x => x.R === R).f;
    const z0 = Math.max(T, R.bot), z1 = Math.min(zInTop, R.top + P.rowGap);
    return { name: NAMES[R.i] + ' drawers', slide: 'accuride-3832', length: S.l,
      opening: { at: banks.map(bx => [bx, 0, r(Z0 + z0)]), w: bankW, h: r(z1 - z0), d: backY },
      box: [d.sides.id, d.fb.id, d.bot.id], slides: slides.id, front: { part: f.id, style: 'full-overlay' },
      waive: { 'drawer-wide': 'clothes weigh far less than the 100 lb rating, and the rabbeted, glued boxes stay square. For tools or files, use a slide rated for wide drawers (Accuride 3640 is rated on a 42" drawer).' } };
  });

  return {
    meta: {
      series: 'Shop Plan', plan_no: '015', rev: P.rev, date: 'Oct 2026',
      title: 'Modern Eight-Drawer Dresser',
      subtitle: 'Walnut case, graduated drawers, integrated finger pulls',
      overall: { w: P.w, d: P.caseD + P.frontT, h: Z0 + P.caseH },
      wood: 'Walnut plywood, Baltic birch & poplar', skill: 'Intermediate', time: '3 weekends',
      intro: [
        'A long, low case with two banks of four drawers that step down in height from bottom to top. The fronts are slabs of walnut plywood cut in sequence from one sheet, so the grain runs unbroken across each row and down each bank. There are no pulls: a ' + F(P.rowGap) + '" shadow gap between rows lets your fingers reach the ' + F(P.pull.depth) + '" relief routed into the back of every front\'s bottom edge. The case floats on a black plinth set back ' + F(PL.front) + '" from the front.',
        'The case is frameless 3/4" plywood, rabbeted and dadoed, with a center divider that carries the slides for both banks. Each drawer is a Baltic birch box with rabbeted corners and a captured bottom, hung on ' + S.l + '" full-extension ball-bearing slides. Fronts screw on from inside the box, so you can align them after the boxes run.'
      ],
      needs: ['Router, edge guide, and straight bits sized to the real plywood (23/32" for most 3/4" walnut ply) and 1/4"', 'Table saw with a dado stack', 'Router table for the finger reliefs', 'Brad nailer, 5/8" to 1-1/4" brads', 'Iron-on walnut edge banding, 3/4", about 75 ft', 'Slide jig or a 32 mm drilling guide'],
      check: { min_wall: 0.1875 }
    },
    materials: { wood: { color: '#e6c578' }, birch: { color: '#f4ec9e' }, paint: { color: '#8c8270' }, hardware: { color: '#c5c2be' } },
    sections: [{ id: 'case', title: 'Case' }, { id: 'base', title: 'Plinth' }, { id: 'boxes', title: 'Drawer Boxes & Slides' }, { id: 'fronts', title: 'Drawer Fronts' }],
    parts: allParts.map(p => (p.material === 'Baltic birch' ? Object.assign(p, { mat: 'birch' }) : p)),
    cutlist_notes: [
      'Baltic birch sold as 1/2" is 12 mm (0.47"). Cut the box fronts and backs from the actual stock so every box is ' + F(boxW) + '" wide, ± 1/32": the slides need between 1/2" and 17/32" each side. Measure each opening first.',
      'Cut the eight fronts from one sheet in order, top row to bottom, and mark each one. Band the edges after the reliefs are cut.',
      'Bottoms are 6 mm Baltic birch; cut them 1/16" under the listed size so they drop into the grooves.'
    ],
    joints, bores, drawers,
    hardware: [
      { item: S.l + '" full-extension ball-bearing slides, 100 lb (Accuride 3832 class)', qty: (slides.qty / 2) + ' pr.', source: 'Woodworking supplier', note: '1/2" clearance per side, 45 mm tall.', part: slides.id },
      { item: '#6 × 5/8" pan-head screws', qty: 53, source: 'Usually with the slides', note: 'Slide cabinet members, three per slide; back to divider.' },
      { item: '#6 × 3/8" pan-head screws', qty: 48, source: 'Hardware store', note: 'Slide drawer members. The 1/2" screws packed with most slides go through a 12 mm box side.' },
      { item: '#8 × 1" washer-head screws', qty: 32, source: 'Hardware store', note: 'Fronts to boxes, four per drawer; the wide head covers the 1/4" adjusting hole.', part: fid('Top') },
      { item: '#8 × 1-1/2" flat-head screws', qty: 12, source: 'Hardware store', note: 'Case to plinth.', part: rail.id },
      { item: 'Brads, 18 ga: 5/8", 1", 1-1/4"', qty: '1 box each', source: 'Hardware store', note: 'Back, box corners, plinth corners.' },
      { item: 'Clear bumper dots, 1/4" × 1/16"', qty: 16, source: 'Hardware store', note: 'Two per front: one on the case side edge, one on the 5/16" of divider edge it covers.' },
      { item: 'Anti-tip furniture strap kit, with #8 × 1-1/4" screws', qty: 1, source: 'Hardware store', note: 'Through the back into the divider\'s rear edge, and into a wall stud. A loaded dresser with open drawers will tip.', part: divider.id }
    ],
    details_intro: 'The pull is the gap: fingers go in under a front, up into the relief, and pull. Box corners are a single rabbet; the bottom floats in a 1/4" groove on all four sides.',
    details: [pullDetail, cornerDetail, divDetail],
    view: {
      explode: 100, start: 'Front right',
      hint: 'Hover a part for its size. Click to select it everywhere on the plan.',
      dims: { front: rows.map(R => ({ a: [P.w, Z0 + R.bot], b: [P.w, Z0 + R.top], off: -3 })) }
    },
    stock: { sheet: { w: 48, l: 96, kerf: 0.125 }, sheets: { 'Baltic birch': { w: 60, l: 60 } }, board: { w: 7.25, l: 96, kerf: 0.125 } },
    cutting_note: 'Case and fronts come from three sheets of 3/4" walnut plywood; keep the fronts to their own sheet.',
    steps: [
      { title: 'Break down the sheets', text: 'Cut the case sides {#1}, top {#2}, bottom {#3} and divider {#4} with the grain as listed. Cut the back {#5}. Set the fronts sheet aside for now.', parts: ['1', '2', '3', '4', '5'] },
      { title: 'Rabbet and dado the case', text: 'Caliper the plywood first; every rabbet and dado below follows its real thickness, not 3/4". Rout rabbets half the sheet thickness deep and one thickness wide across the top and bottom inside edges of each side {#1}, and 3/8" × 1/4" rabbets along their back edges and the back edges of the top {#2} and bottom {#3}. Rout a 1/4"-deep, 3/4" dado across the center of the top and bottom for the divider {#4}, fitting the bit to the actual plywood.', parts: ['1', '2', '3'] },
      { title: 'Assemble the case', text: 'Glue the top, bottom and divider into the sides. Check the diagonals, glue and brad the back {#5} into its rabbets, and drive five screws through the back into the divider. Then band the front edges of the sides, divider, top and bottom, the back edge of the top, and the top ends of the sides (the gaps between the fronts show them), trimming the banding flush. Measure the case: the fronts are sized from it.', parts: ['4', '5'] },
      { title: 'Build the plinth', text: 'Rabbet the ends of the plinth front and back {#6} and dado them for the stretcher {#8}. Glue and brad the ends {#7} and stretcher in, paint the frame black, and screw the case to it with countersunk screws through the case bottom, ' + F(PL.front) + '" back from the front and ' + F(PL.side) + '" in from each side.', parts: ['6', '7', '8'] },
      { title: 'Mount the cabinet slide members', text: 'Draw slide centerlines on the sides and divider, measured up from the top of the case bottom: ' + sl + '. Screw the cabinet members 1/8" back from the front edge. On the divider, use different holes in the slides on the two faces, at least 3/4" apart along the slide, so no two screws meet (see Divider Slide Screws).', parts: ['9'] },
      { title: 'Build the boxes', text: 'Mill the box parts to ' + boxList + ' tall (top to bottom). Cut 1/4"-deep rabbets as wide as the actual stock at both ends of every box side, then a 1/4" × 1/4" groove ' + F(B.groove) + '" up from the bottom edge on all four parts. Glue and brad the fronts and backs into the side rabbets around the bottom, leaving the bottom dry. Square each box and check that it is ' + F(boxW) + '" wide, ± 1/32". Drill two 1/4" holes in each box front for the front screws, ' + F(1.5) + '" up from the box bottom edge and 1" down from its top, 3" from each end.', parts: boxIds },
      { title: 'Hang the boxes', text: 'Screw the drawer members 1/8" back from the box front, on the slide centerline, with 3/8" screws. Slide each box in and check that it runs.', parts: [] },
      { title: 'Make the fronts', text: 'Check the built case against 60" × 30-1/2" and adjust the front width and the top row by the difference. Cut the eight fronts {#' + frontIds.join('} {#') + '} in order from one sheet: ' + frontList + ' tall (top to bottom), ' + F(fw) + '" wide, less the banding. Rout a ' + F(P.pull.depth) + '" × ' + F(P.pull.h) + '" rabbet on the back of each bottom edge, then band all four edges and finish.', parts: frontIds },
      { title: 'Hang the fronts', text: 'Start with the bottom row, flush with the bottom of the case and its outer side. Use ' + F(P.rowGap) + '" spacers between rows and a ' + F(P.seam) + '" spacer at the center seam. Stick each front to its box with double-sided tape, open the drawer, and drive two screws through the 1/4" holes from inside; the holes let you shift the front 1/16". Check the gaps, then add the other two.', parts: [] },
      { title: 'Secure it', text: 'Stick a bumper dot on the case side edge and on the divider edge behind each front. Screw the anti-tip bracket through the back {#5} into the rear edge of the divider {#4}, 2" below the top, never into the 1/4" back alone, and strap it to a wall stud before filling the drawers.', parts: [] }
    ],
    revisions: [{ rev: 'A', date: 'Oct 25 2026', summary: 'First issue',
      changes: [{ id: 'A1', summary: 'Initial design, full adversarial review', parts: allParts.map(p => p.id) }] }],
    review: [{ rev: 'A', change: 'A1', verdict: 'flag', mates: [],
      checks: [
        { check: 'Cut list re-derived from PARAMS', result: 'pass',
          evidence: 'Case: sides 30-1/2 × 19-1/4, top and bottom 58-1/2 + 2 × 3/8 rabbet = 59-1/4, divider 29 + 2 × 1/4 dado = 29-1/2 × 19 (stops at the back), back 59-1/4 × 29-3/4. Fronts (60 − 1/8) ÷ 2 = 29-15/16 wide; 7-7/8 + 7-1/4 + 6-3/4 + 3 × 3/4 gaps = 24-1/8, so the top row is 6-3/8. Plinth 58, 16-1/2, 16-1/4. A fresh reviewer re-derived all 25 parts independently and agreed. Model check: cut list matches the model, overall 60 × 20 × 34.' },
        { check: 'Box width with real 12 mm Baltic birch {#11} {#14} {#17} {#20}', result: 'fixed',
          evidence: 'Found by the fresh reviewer. The first draft modeled the boxes at a nominal 1/2", so the fronts and backs came out 27-11/32. Built from 12 mm (0.47") sides with 1/4" rabbets, that box is 27.79" wide and leaves 0.54" a side, over the slide\'s 17/32" limit. The boxes are now modeled at 15/32": fronts, backs and bottoms are 27-13/32, the box is 27-27/32 (17/32 − 1/64 a side, the middle of the window), and step 6 cuts the rabbets to the actual stock width.' },
        { check: 'Slide clearance and depth {#9}', result: 'fixed',
          evidence: 'The first draft sized the box to exactly 1/2" per side, the bottom of the 1/2"–17/32" window, so a case a hair narrow would bind. Cross-checked against shop-drawer-planner (0.516 a side), now 33/64. Slides are 18" with a 1/8" setback, ending at 18-1/8 in a 19" inside depth. The 1-3/4" slide fits the shortest box (4-1/2").' },
        { check: 'Bottom drawer clear of the case bottom {#19} {#3}', result: 'fixed',
          evidence: 'Shrinking the finger relief to 7/8" dropped the bottom boxes to 1/8" over the case bottom, and the model check failed: the plinth screws\' heads lay under the box sides. Boxes now start at the higher of the relief top and 1/4" over the case bottom.' },
        { check: 'Finger pull works {#22} {#23} {#24} {#25}', result: 'flag',
          evidence: 'The first draft used 5/8" gaps between rows, tight for a fingertip that has to go in and then curl up. Fixed at 3/4", with a 3/8" × 7/8" relief behind a 3/8" lip. Every box starts at or above the relief top, so nothing blocks it. On the bottom row the case bottom edge sits right behind the relief, so the grip is only the 3/8" lip. Rout one scrap front and try it before cutting all eight.' },
        { check: 'Clearances between moving parts', result: 'pass',
          evidence: 'Box heights 4-1/2, 5-3/4, 6-1/4, 6-3/4 leave 1-3/4" between boxes in each bank. The top box is 1/4" below the case top; each box top is 1/8" below its front top. Fronts have a 1/8" seam and 3/4" row gaps. Model check: no interference anywhere.' },
        { check: 'Case joints {#1} {#2} {#3} {#4} {#5}', result: 'pass',
          evidence: 'Top and bottom sit in rabbets half the sheet deep, and the sides bear on the bottom at the rabbet shoulder. The divider sits in 1/4" dados in 3/4" ply (1/3, within joinery.md). The back, glued into rabbets on four edges and screwed to the divider, resists racking both ways.' },
        { check: 'Load path, loaded open drawer to floor', result: 'pass',
          evidence: 'Box, then slide, then the side or divider (three #6 screws into face grain). The sides bear on the bottom rabbet shoulder, which has a 5/8" cantilever to the plinth ends at x = 1. The divider bears in the bottom dado directly over the stretcher {#8}. The top spans 28-7/8 between the sides and divider, just over the 28" shelf rule, but its back edge is in a rabbet and it only carries what goes on a dresser.' },
        { check: 'Slide screws meet in the divider {#4}', result: 'fixed',
          evidence: 'Both banks hang at the same heights, so the screws from the two faces of the 3/4" divider would line up: two 5/8" screws overlap by 1/2". The model check had no test for this; one was added (bore-cross). The faces now use positions 1" apart (B2), and the check passes.' },
        { check: 'Slide hole pattern on the divider', result: 'flag',
          evidence: 'The 1" stagger is drawn for clarity. Use whichever holes in your slide model put the screws on the two faces at least 3/4" apart along the slide. Check the maker\'s sheet for the hole spacing and the clearance window before you size the boxes.' },
        { check: 'Fastener lengths, real stock', result: 'pass',
          evidence: 'Slide to box: #6 × 3/8", about 5/16" into 15/32". Slide to case: #6 × 5/8", about 9/16" into 23/32" ply. Front screws: #8 × 1" through 15/32" (2.1×), about 1/2" into the front and clear of the relief (the lowest screw is 1-1/2" above the box bottom). Plinth: #8 × 1-1/2" (2× the bottom). Back: #6 × 5/8" (2.5×).' },
        { check: 'Front adjustment holes', result: 'fixed',
          evidence: 'Found by the fresh reviewer. The joint note relied on oversize holes in the box fronts, but no step drilled them. Step 6 now drills 1/4" holes and step 9 uses them. The screws are washer-head so they cover the hole. B6 to B9 are now tied to their joints, so later reviews see them.' },
        { check: 'Case built from real 23/32" plywood', result: 'flag',
          evidence: 'Found by the fresh reviewer. On 0.71" ply the case comes out about 59-15/16" wide, and the fronts would overhang a little. Step 2 now sizes every rabbet and dado to the caliper, step 3 measures the built case, and step 8 cuts the fronts to it, less the banding. Expect the fronts to change by up to 1/16".' },
        { check: 'Tipping', result: 'pass',
          evidence: 'The dresser pivots on the plinth front, 2-1/4" behind the drawer faces. Open, loaded 18" drawers, or a child climbing them, will tip it. The anti-tip strap is listed and step 10 fastens it through the back into the divider edge. The back screws (B5) were moved so the top one is 2-1/2" below the strap screw, which keeps the divider edge from splitting. The fresh reviewer raised the spacing.' },
        { check: 'Paperwork', result: 'fixed',
          evidence: 'The case drawer-front stops were changed to 1/4" bumper dots: a 3/8" bumper does not fit on the 5/16" of divider edge that each front covers. The anti-tip strap moved off the 1/4" back alone. Banding now goes on after glue-up so it does not cover the dado mouths (fresh reviewer). Brads were added to the hardware list. Screw counts were re-counted: 53 #6 × 5/8, 48 #6 × 3/8, 32 #8 × 1, 12 #8 × 1-1/2. Edge banding is about 75 ft. The Finger Pull Section first labeled the two fronts the wrong way round; it is fixed. Sheets: three 3/4" walnut (one for the fronts), one 1/4" walnut, two 5 × 5 of 12 mm Baltic birch, two of 6 mm.' },
        { check: 'Wood movement', result: 'pass',
          evidence: 'Everything is plywood except the 3-1/2" poplar plinth, whose movement across its height is unrestrained, because the case is screwed to its top edge.' }
      ] }]
  };
};
module.exports.PARAMS = PARAMS;
