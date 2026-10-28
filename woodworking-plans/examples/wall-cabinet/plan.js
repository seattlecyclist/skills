/* Two-door wall cabinet: a 3/4" plywood case joined with dados, rabbets and grooves, hung on a French
 * cleat that hides in a 3/4" cavity behind the recessed back, with overlay slab doors on 35 mm
 * concealed hinges and two adjustable shelves on 1/4" pins.
 * Every number derives from PARAMS. Build:  node ../../scripts/build_plan.js plan.js out.html
 */
const PARAMS = {
  rev: 'D',
  w: 30, h: 30, caseD: 11.25,          // case outside; the doors and pulls add to the depth
  ply: 0.75, back: 0.25,               // case plywood, back panel
  rab: 0.375,                          // dado, rabbet and groove depth in the 3/4" plywood
  inset: 0.5,                          // top and bottom dados stop this far in from the side ends (Rev A: rabbets at the ends)
  cavity: 0.75,                        // space behind the back for the French cleat (cleat thickness)
  cleat: { h: 3, wall: 28 },           // cleat height at mid-thickness (45° bevel); wall cleat length
  rail: 2.5,                           // bottom wall rail height
  door: { t: 0.75, reveal: 0.125, gap: 0.125, hingeIn: 3 },   // reveal at the case edges, gap between the pair, hinge centers from the door ends
  hinge: { cup: 35 / 25.4, depth: 0.5, edge: 5 / 25.4, plate: 37 / 25.4, w: 0.5, d: 2.25, h: 2 },
  shelf: { front: 0.25, back: 0.125, end: 1 / 16, strip: { t: 0.75, h: 1.5 } },
  pins: { d: 0.25, depth: 0.375, col: 1.5, z0: 6, step: 1.25, n: 15, proj: 0.375, rows: [3, 11] },
  pull: { c: 96 / 25.4, z: 2.5, in: 1.5, proj: 1.25 }
};

module.exports = function build(P = PARAMS, J = require('../../scripts/joints.js')) {
  const r = v => Math.round(v * 1e5) / 1e5;
  const F = v => { const s = v < 0 ? '-' : ''; v = Math.abs(v); const n = Math.round(v * 16), w = Math.floor(n / 16), f = n % 16; const g = (a, b) => b ? g(b, a % b) : a; return s + (f ? (w ? w + '-' : '') + (f / g(f, 16)) + '/' + (16 / g(f, 16)) : String(w)); };
  const T = P.ply, D = P.caseD, W = P.w, H = P.h, R = P.rab;
  const E = P.inset, inW = W - 2 * T, inH = H - 2 * (E + T);
  const yBack = D - P.cavity - P.back;          // front face of the back
  const yCav = D - P.cavity;                    // rear face of the back, front of the cleat cavity
  const zc = H - E - T - P.cleat.h;                 // where the two cleats meet (mid-thickness of the bevel)
  const DR = P.door, HG = P.hinge, S = P.shelf, PN = P.pins, PU = P.pull;
  const doorW = r((W - 2 * DR.reveal - DR.gap) / 2), doorH = r(H - 2 * DR.reveal);
  const dz0 = DR.reveal, dxL = DR.reveal, dxR = r(W - DR.reveal - doorW);
  const hz = [r(dz0 + DR.hingeIn), r(dz0 + doorH - DR.hingeIn)];
  const cupC = r(HG.edge + HG.cup / 2);         // cup center from the door's hinge edge
  const pinZ = Array.from({ length: PN.n }, (_, k) => r(PN.z0 + k * PN.step));
  const pinY = [PN.col, r(yBack - PN.col)];
  const shelfZ = PN.rows.map(k => r(pinZ[k] + PN.d / 2));   // shelf bottoms: on top of the pins
  const shelfL = r(inW - 2 * S.end), shelfY0 = r(S.front + S.strip.t), shelfY1 = r(yBack - S.back);
  const pullZ = [r(dz0 + PU.z), r(dz0 + PU.z + PU.c)];
  const pullX = [r(dxL + doorW - PU.in), r(dxR + PU.in)];

  // ---------- case ----------
  const side = { id: '1', name: 'Sides', section: 'case', qty: 2, t: T, w: D, l: H, material: 'Birch plywood', stock: 'sheet',
    note: 'Dados 3/8" deep, ' + F(E) + '" in from each end; a 3/8" × 1" rabbet down the back edge. Grain runs up.',
    shape: [{ box: [0, 0, 0, T, D, H] },
      // the back rabbet: 3/8" deep and 1" wide, so the back sits at its front shoulder and the cleats fill the rest
      { cut: [R, yBack, -1, T - R + 1, D - yBack + 1, H + 2], tool: 'router' }],
    instances: [{ at: [0, 0, 0] }, { at: [W, 0, 0], mirror: 'x' }] };
  const top = { id: '2', name: 'Top', section: 'case', qty: 1, t: T, w: D, l: inW, material: 'Birch plywood', stock: 'sheet',
    note: 'Groove underneath for the back; the hanging cleat bears on its back strip.',
    shape: [{ box: [0, 0, 0, inW, D, T] }], instances: [{ at: [T, 0, H - E - T] }] };
  const bottom = { id: '3', name: 'Bottom', section: 'case', qty: 1, t: T, w: D, l: inW, material: 'Birch plywood', stock: 'sheet',
    note: 'Groove on top for the back; the wall rail sits on its back strip.',
    shape: [{ box: [0, 0, 0, inW, D, T] }], instances: [{ at: [T, 0, E] }] };
  const back = { id: '4', name: 'Back', section: 'case', qty: 1, t: P.back, w: inH, l: inW, material: 'Plywood', stock: 'sheet',
    note: 'Glued into the side rabbets and the top and bottom grooves; it squares the case.',
    shape: [{ box: [0, 0, 0, inW, P.back, inH] }], instances: [{ at: [T, yBack, E + T] }] };
  const cleat = { id: '5', name: 'Hanging Cleat', section: 'case', qty: 1, t: P.cavity, w: P.cleat.h, l: inW, material: 'Birch plywood', stock: 'sheet',
    note: '45° bevel on the bottom edge, long face against the wall. Width is at mid-thickness: ' + F(P.cleat.h + P.cavity / 2) + '" on the wall face, ' + F(P.cleat.h - P.cavity / 2) + '" on the back face.',
    shape: [{ box: [0, 0, 0, inW, P.cavity, P.cleat.h] }], instances: [{ at: [T, yCav, zc], explode: [0, 10, 6] }] };   // by hand: out the back, so its balloon is not read on the top
  const rail = { id: '6', name: 'Bottom Wall Rail', section: 'case', qty: 1, t: P.cavity, w: P.rail, l: inW, material: 'Birch plywood', stock: 'sheet',
    note: 'Holds the bottom off the wall by the cavity depth and takes the two hold-down screws.',
    shape: [{ box: [0, 0, 0, inW, P.cavity, P.rail] }], instances: [{ at: [T, yCav, E + T], explode: [0, 10, -3] }] };
  const wallCleat = { id: '7', name: 'Wall Cleat', section: 'case', qty: 1, t: P.cavity, w: P.cleat.h, l: P.cleat.wall, material: 'Birch plywood', stock: 'sheet',
    note: '45° bevel on the top edge, high side away from the wall. Screws to the studs, never to drywall alone.',
    shape: [{ box: [0, 0, 0, P.cleat.wall, P.cavity, P.cleat.h] }], instances: [{ at: [r((W - P.cleat.wall) / 2), yCav, r(zc - P.cleat.h)], explode: [0, 20, 0] }] };

  // ---------- shelves ----------
  const shelf = { id: '8', name: 'Shelves', section: 'shelves', qty: 2, t: T, w: r(shelfY1 - shelfY0), l: shelfL, material: 'Birch plywood', stock: 'sheet',
    shape: [{ box: [0, 0, 0, shelfL, r(shelfY1 - shelfY0), T] }],
    instances: shelfZ.map(z => ({ at: [r(T + S.end), shelfY0, z] })) };
  const strip = { id: '9', name: 'Shelf Edge Strips', section: 'shelves', qty: 2, t: S.strip.t, w: S.strip.h, l: shelfL, material: 'Poplar', stock: 'solid', mat: 'poplar',
    note: 'Glued to the shelf front, top flush; it hangs ' + F(S.strip.h - T) + '" below and stiffens the ' + F(shelfL) + '" span.',
    shape: [{ box: [0, 0, 0, shelfL, S.strip.t, S.strip.h] }],
    instances: shelfZ.map(z => ({ at: [r(T + S.end), S.front, r(z + T - S.strip.h)] })) };
  const pins = { id: '10', name: 'Shelf Pins', section: 'shelves', qty: 0, t: PN.d, w: PN.d, l: PN.proj, material: 'Steel', stock: 'hardware', mat: 'hardware',
    size: '1/4" spoon shelf pin', shape: [{ box: [0, 0, 0, PN.proj, PN.d, PN.d] }], instances: [] };
  for (const k of PN.rows) for (const y of pinY) {
    pins.instances.push({ at: [T, r(y - PN.d / 2), r(pinZ[k] - PN.d / 2)] });
    pins.instances.push({ at: [r(W - T), r(y - PN.d / 2), r(pinZ[k] - PN.d / 2)], mirror: 'x' });
  }
  pins.qty = pins.instances.length;

  // ---------- doors ----------
  const door = { id: '11', name: 'Doors', section: 'doors', qty: 2, t: DR.t, w: doorW, l: doorH, material: 'Birch plywood', stock: 'sheet',
    note: 'Slab doors, banded on all four edges. Two 35 mm cup bores on the hinge edge, two pull holes on the meeting edge.',
    shape: [{ box: [0, 0, 0, doorW, DR.t, doorH] }],
    instances: [{ at: [dxL, -DR.t, dz0] }, { at: [r(dxR + doorW), -DR.t, dz0], mirror: 'x' }] };
  const hinge = { id: '12', name: 'Concealed Hinges', section: 'doors', qty: 4, t: HG.w, w: HG.d, l: HG.h, material: 'Steel', stock: 'hardware', mat: 'hardware',
    size: '35 mm full-overlay, 110°, soft-close, 0 mm clip plate',
    shape: [{ box: [0, 0, 0, HG.w, HG.d, HG.h] }],
    instances: hz.flatMap(z => [{ at: [T, 0, r(z - HG.h / 2)] }, { at: [r(W - T), 0, r(z - HG.h / 2)], mirror: 'x' }]) };
  const pull = { id: '13', name: 'Pulls', section: 'doors', qty: 2, t: 0.375, w: PU.proj, l: r(PU.c + 0.75), material: 'Steel', stock: 'hardware', mat: 'hardware',
    size: '96 mm (3-3/4") bar pull',
    shape: [{ box: [0, 0, 0, 0.375, PU.proj, r(PU.c + 0.75)] }],
    instances: pullX.map(x => ({ at: [r(x - 0.1875), r(-DR.t - PU.proj), r(pullZ[0] - 0.375)] })) };

  // ---------- joints ----------
  const joints = [
    J.dado({ host: side, guest: top, depth: R, title: 'Top in side dados', fasteners: 'Glue, 1-1/4" brads', tool: 'router', note: '3/8" deep, ' + F(E) + '" below the side tops, so the sides bear on the top and the top bears on the hanging cleat.' }),
    J.dado({ host: side, guest: bottom, depth: R, title: 'Bottom in side dados', fasteners: 'Glue, 1-1/4" brads', tool: 'router', note: '3/8" deep, ' + F(E) + '" above the side bottoms, so the bottom bears on the sides.' }),
    J.rabbet({ host: side, guest: back, depth: R, title: 'Back in side rabbets', fasteners: 'Glue', tool: 'router', note: '3/8" deep; the rabbet is 1" wide and the back sits against its front shoulder, leaving 3/4" behind it for the cleats.' }),
    J.groove({ host: top, guest: back, depth: R, title: 'Back in top groove', fasteners: 'Glue', tool: 'tablesaw' }),
    J.groove({ host: bottom, guest: back, depth: R, title: 'Back in bottom groove', fasteners: 'Glue', tool: 'tablesaw' }),
    J.rabbet({ host: side, guest: cleat, depth: R, title: 'Hanging cleat in side rabbets', fasteners: 'Glue, two #8 × 1" screws through each side', tool: 'router' }),
    J.rabbet({ host: side, guest: rail, depth: R, title: 'Wall rail in side rabbets', fasteners: 'Glue', tool: 'router' }),
    J.joint('screwed', [cleat, back, top], { title: 'Hanging cleat to back and top', glue: true, fasteners: 'Five #6 × 3/4" screws through the back, three #8 × 1-1/2" down through the top', note: 'The top bears on the cleat; glue over the full 3" face to the back.' }),
    J.joint('screwed', [rail, back, bottom], { title: 'Wall rail to back and bottom', glue: true, fasteners: 'Four #6 × 3/4" screws through the back' }),
    J.joint('french-cleat', [wallCleat, cleat, back], { title: 'French cleat', fasteners: 'Wall cleat: two #10 × 3" flat-head screws into each stud, countersunk', note: 'The beveled edges hook over each other; the cabinet lifts off only straight up. Two hold-down screws through the back and rail stop it lifting.' }),
    J.joint('shelf-pin', [pins, side], { title: 'Shelf pins', fasteners: '1/4" pins in 3/8" deep holes' }),
    J.joint('rests', [shelf, pins], { title: 'Shelves on pins', fasteners: 'None' }),
    J.joint('glued', [strip, shelf], { title: 'Edge strip to shelf', glue: true, fasteners: 'Glue, clamps', note: 'Long grain to the plywood edge.' }),
    J.joint('hinge', [hinge, side, door], { title: 'Concealed hinges', fasteners: '#6 × 5/8" into the side, #6 × 1/2" into the door', note: 'Cup bored 1/2" deep, ' + '5/32" (4 mm) from the door edge; plate screws 37 mm back from the front edge.' }),
    J.joint('rests', [door, side, top, bottom], { title: 'Doors close on the case edges', fasteners: 'Soft-close hinges hold them shut' }),
    J.joint('screwed', [pull, door], { title: 'Pulls', fasteners: '#8-32 × 1" machine screws from inside' })
  ];
  const hingeJoint = joints.find(j => j.title === 'Concealed hinges');
  hingeJoint.note = 'Cup bored 1/2" deep, 5 mm from the door edge (cup centre 22.5 mm in); plate screws 37 mm back from the front edge.';
  const jid = t => joints.find(j => j.title === t) && 'J' + (joints.findIndex(j => j.title === t) + 1);

  // ---------- bores ----------
  const bores = [];
  const hingeEdge = [[dxL, 1], [r(dxR + doorW), -1]];       // hinge edge x, and the direction into the door
  bores.push({ id: 'B1', joint: jid('Concealed hinges'), kind: 'hole', label: '35 mm hinge cup', d: HG.cup, depth: HG.depth, access: 0,
    copies: hingeEdge.flatMap(([x, s]) => hz.map(z => ({ at: [r(x + s * cupC), 0, z], dir: '-y' }))) });
  bores.push({ id: 'B2', joint: jid('Concealed hinges'), kind: 'screw', label: '#6 × 1/2" cup screw', d: 0.138, len: 0.5, access: 0, hardware: true,
    copies: hingeEdge.flatMap(([x, s]) => hz.flatMap(z => [-1, 1].map(u => ({ at: [r(x + s * (cupC + 9.5 / 25.4)), 0, r(z + u * 22.5 / 25.4)], dir: '-y' })))) });
  bores.push({ id: 'B3', joint: jid('Concealed hinges'), kind: 'screw', label: '#6 × 5/8" plate screw', d: 0.138, len: 0.625, access: 0, hardware: true,
    copies: [[T, '-x'], [W - T, '+x']].flatMap(([x, dir]) => hz.flatMap(z => [-1, 1].map(u => ({ at: [x, r(HG.plate), r(z + u * 16 / 25.4)], dir })))) });
  bores.push({ id: 'B4', joint: jid('Shelf pins'), kind: 'hole', label: '1/4" shelf-pin hole', d: PN.d, depth: PN.depth, access: 0,
    copies: [[T, '-x'], [W - T, '+x']].flatMap(([x, dir]) => pinY.flatMap(y => pinZ.map(z => ({ at: [x, y, z], dir })))) });
  bores.push({ id: 'B5', joint: jid('Pulls'), kind: 'hole', label: '3/16" pull screw hole', d: 0.1875, depth: DR.t, through: true,
    copies: pullX.flatMap(x => pullZ.map(z => ({ at: [x, 0, z], dir: '-y' }))) });
  const cj = jid('Hanging cleat to back and top');
  bores.push({ id: 'B6', joint: cj, kind: 'screw', label: '#8 × 1-1/2" screw', d: 0.164, len: 1.5,
    copies: [5, 15, 25].map(x => ({ at: [x, r(D - P.cavity / 2), H - E], dir: '-z' })) });
  bores.push({ id: 'B7', joint: jid('Hanging cleat in side rabbets'), kind: 'screw', label: '#8 × 1" screw', d: 0.164, len: 1,
    copies: [[0, '+x'], [W, '-x']].flatMap(([x, dir]) => [r(zc + 0.75), r(zc + 2.25)].map(z => ({ at: [x, r(D - P.cavity / 2), z], dir }))) });
  bores.push({ id: 'B8', joint: cj, kind: 'screw', label: '#6 × 3/4" screw', d: 0.138, len: 0.75,
    copies: [3, 9, 15, 21, 27].map(x => ({ at: [x, yBack, r(zc + P.cleat.h / 2)], dir: '+y' })) });
  bores.push({ id: 'B9', joint: jid('Wall rail to back and bottom'), kind: 'screw', label: '#6 × 3/4" screw', d: 0.138, len: 0.75,
    copies: [3, 11, 19, 27].map(x => ({ at: [x, yBack, r(E + T + P.rail / 2)], dir: '+y' })) });
  // wall screws: the wall and studs are not modeled, so these are the clearance holes; the screws run on into the studs
  const studs = [7, 23];
  bores.push({ id: 'B10', joint: jid('French cleat'), kind: 'hole', label: 'wall cleat screw hole, #10 × 3" flat-head, countersunk flush', d: 0.1875, depth: P.cavity, through: true, access: 0,
    copies: studs.flatMap(x => [r(zc - 0.875), r(zc - 2.125)].map(z => ({ at: [x, yCav, z], dir: '+y' }))) });
  bores.push({ id: 'B11', joint: jid('French cleat'), kind: 'hole', label: 'hold-down screw hole, #10 × 3" to stud', d: 0.1875, depth: r(P.back + P.cavity), through: true,
    copies: studs.map(x => ({ at: [x, yBack, r(E + T + P.rail / 2)], dir: '+y' })) });

  // ---------- paperwork ----------
  const allParts = [side, top, bottom, back, cleat, rail, wallCleat, shelf, strip, pins, door, hinge, pull];
  const lineZ = zc + P.cavity / 2;               // the wall cleat's high (front) edge above the cabinet bottom
  const circle = (cx, cy, rad, n = 28) => Array.from({ length: n }, (_, i) => [r(cx + rad * Math.cos(2 * Math.PI * i / n)), r(cy + rad * Math.sin(2 * Math.PI * i / n))]);

  // French cleat section: u is depth toward the wall (wall at u = 0.75 + 0.25 + ...), v is height above the cabinet bottom
  const cv = P.cavity, ch = P.cleat.h, u0 = 0;   // u: 0 = front of the back panel
  const uB = P.back, uW = P.back + cv;           // rear of the back, wall face
  const cleatDetail = {
    title: 'French Cleat Section', sub: 'through the cleats, wall on the right', w: 7, h: 9,
    items: [
      { rect: [-1.5, ch + 1.5, uW + 1.5, T], fill: 'wood', part: top.id },
      { rect: [u0, -2.5, uB, ch + 1.5 + R + 2.5], fill: 'end', part: back.id },
      { poly: [[uB, ch + 1.5], [uW, ch + 1.5], [uW, 1.5 - cv / 2], [uB, 1.5 + cv / 2]], fill: 'end', part: cleat.id },
      { poly: [[uB, 1.5 + cv / 2 - 0.0], [uW, 1.5 - cv / 2], [uW, 1.5 - ch], [uB, 1.5 - ch]].map(([a, b]) => [a, b]), fill: 'end', part: wallCleat.id },
      { line: [uW, -2, uW, ch + 3], dash: false },
      { text: [uW + 0.15, -2.4, 'wall'], size: 0.8, anchor: 'start' },
      { dim: [uB, ch + 1.5 + T + 0.2, uW, ch + 1.5 + T + 0.2], off: 0.6 },
      { dim: [uW, 1.5 - cv / 2, uW, ch + 1.5], off: -0.9, text: F(ch + cv / 2) + '"' },
      { dim: [uW, 1.5 - ch, uW, 1.5 - cv / 2], off: -0.9, text: F(ch - cv / 2) + '"' },
      { text: [uW + 0.15, 1.5, '45°'], size: 0.8, anchor: 'start' },
      { callout: [-1.6, ch, cleat.id], to: [uB + 0.2, ch] },
      { callout: [-1.6, -1, wallCleat.id], to: [uB + 0.2, -1] },
      { callout: [-1.6, 2.2, back.id], to: [0.05, 2.2] },
      { text: [-1.6, -3.4, 'lift 1" to hang'], size: 0.8, anchor: 'middle' }
    ]
  };
  // hinge cup layout on the back of the left door, near its hinge edge; u from the hinge edge, v from the door bottom
  const cupDetail = {
    title: 'Hinge Cup Layout', sub: 'back face of a door at the lower hinge', w: 6, h: 6,
    items: [
      { rect: [0, 0, 4, 5.5], fill: 'wood', part: door.id },
      { poly: circle(cupC, DR.hingeIn, HG.cup / 2), fill: 'none' },
      ...[-1, 1].map(u => ({ poly: circle(cupC + 9.5 / 25.4, DR.hingeIn + u * 22.5 / 25.4, 0.07, 10), fill: 'steel' })),
      { line: [cupC, DR.hingeIn - 1.2, cupC, DR.hingeIn + 1.2], dash: true },
      { dim: [0, DR.hingeIn + 1.6, r(HG.edge), DR.hingeIn + 1.6], off: 0.5, text: '5 mm' },
      { dim: [r(HG.edge), DR.hingeIn - 1.4, r(HG.edge + HG.cup), DR.hingeIn - 1.4], off: -0.5, text: '35 mm' },
      { dim: [0, 0, 0, DR.hingeIn], off: 0.6 },
      { dim: [cupC + 9.5 / 25.4, DR.hingeIn - 22.5 / 25.4, cupC + 9.5 / 25.4, DR.hingeIn + 22.5 / 25.4], off: -1.6, text: '45 mm' },
      { text: [0.2, 0.4, 'hinge edge'], size: 0.8, anchor: 'start' },
      { text: [2.2, DR.hingeIn + 2.2, 'cup 1/2" deep'], size: 0.8, anchor: 'start' }
    ]
  };

  // the door opening: between the case sides, from under the top to over the bottom; the side ends
  // run 1/2" past the top and bottom, so the case edge the doors overlay is 1-1/4" there
  const doors = [{ name: 'Doors', hinge: 'blum-clip-top-110', cabinet: 'frameless', style: 'full-overlay', hinged: 'pair',
    opening: { at: [T, 0, E + T], w: inW, h: inH }, frame: { left: T, right: T, top: r(E + T), bottom: r(E + T) },
    leaves: door.id, hinges: hinge.id, cup: 5, plate: 0, construction: { type: 'slab' },
    pull: { item: '96 mm (3-3/4") bar pull', cc: '96 mm', screw: '8-32 x 1"', at: F(PU.in) + '" from the meeting edge, bottom screw ' + F(PU.z) + '" up' },
    catch: 'Soft-close is built into the hinge cup; no catch needed.' }];

  return {
    meta: {
      series: 'Shop Plan', plan_no: '016', rev: P.rev, date: 'Oct 2026',
      title: 'Two-Door Wall Cabinet',
      subtitle: 'Plywood case on a hidden French cleat, overlay doors on concealed hinges',
      overall: { w: W, d: r(D + DR.t + PU.proj), h: H },
      wood: 'Birch plywood & poplar', skill: 'Beginner to intermediate', time: '2 weekends',
      intro: [
        'A ' + W + '" square wall cabinet for the shop or garage: a 3/4" plywood box with two adjustable shelves behind a pair of slab doors. The doors overlay the case edges with a ' + F(DR.reveal) + '" reveal all round and a ' + F(DR.gap) + '" gap between them, and hang on 35 mm concealed hinges, so nothing shows from the front but two bar pulls.',
        'The case goes together with dados, rabbets and grooves from a router and table saw. The sides run ' + F(E) + '" past the top and bottom, so the top hangs the sides in its dados and the bottom sits on theirs. The back is set ' + F(P.cavity) + '" forward in a 1"-wide rabbet, and that space hides the French cleat: one beveled strip glued into the case under the top, its twin screwed to the wall studs. Lift the cabinet an inch, push it to the wall, lower it, and it hooks on. Two screws through the bottom rail keep it from lifting off.'
      ],
      needs: ['Router with an edge guide and a 23/32" plywood bit', 'Table saw (a dado stack helps)', '35 mm Forstner bit with a drill guide or hinge-boring jig', '1/4" brad-point bit with a stop collar', 'Brad nailer and 1-1/4" brads', 'Iron-on birch edge banding, 3/4", 50 ft roll (about 25 ft used)', 'Stud finder and a 4 ft level'],
      check: { min_wall: 0.25 }
    },
    materials: { wood: { color: '#f2e38a' }, poplar: { color: '#f4ec9e' }, hardware: { color: '#c5c2be' } },
    sections: [{ id: 'case', title: 'Case & Cleats' }, { id: 'shelves', title: 'Shelves' }, { id: 'doors', title: 'Doors & Hardware' }],
    parts: allParts,
    cutlist_notes: [
      'Most 3/4" plywood is 23/32". Rout the dados, rabbets and grooves to the real thickness. The top, bottom, back, cleat and rail are ' + F(W) + '" less twice (real thickness − 3/8"): 29-5/16" for 23/32" plywood, not the 29-1/4" listed. Cut the shelves to the assembled case.',
      'Rip the two cleats from one 6-1/4" strip with the blade tilted to 45°, so the bevels match. Trim the wall half to ' + F(P.cleat.wall) + '".',
      'Doors: cut 1/32" under on each edge for the banding.'
    ],
    joints, bores, doors,
    hardware: [
      { item: 'Blum CLIP top BLUMOTION 110° full-overlay hinges (71B3550) with 0 mm CLIP mounting plates', qty: '2 pr.', source: 'Woodworking supplier', note: 'Overlay = 11 + cup distance − plate = 11 + 5 − 0 = 16 mm, the ' + F(T - DR.reveal) + '" the doors need; ±2 mm of side adjustment covers the rest. Salice, Grass or Hettich full-overlay hinges fit the same 35 mm cups but give a different overlay for the same bore: check the Door Breakout before you bore.', part: hinge.id },
      { item: '#6 × 5/8" flat-head screws', qty: 8, source: 'Usually with the hinges', note: 'Hinge plates, two per plate.' },
      { item: '#6 × 1/2" wafer-head screws', qty: 8, source: 'Usually with the hinges', note: 'Hinge cups, two per cup.' },
      { item: '96 mm (3-3/4") bar pulls with #8-32 × 1" screws', qty: 2, source: 'Hardware store', part: pull.id },
      { item: '1/4" spoon shelf pins', qty: 8, source: 'Hardware store', note: 'Buy a dozen; they go missing.', part: pins.id },
      { item: '#8 × 1-1/2" flat-head screws', qty: 3, source: 'Hardware store', note: 'Top into the hanging cleat.' },
      { item: '#8 × 1" flat-head screws', qty: 4, source: 'Hardware store', note: 'Sides into the hanging cleat ends.' },
      { item: '#6 × 3/4" flat-head screws', qty: 9, source: 'Hardware store', note: 'Back into the cleat and rail.' },
      { item: '#10 × 3" flat-head wood screws', qty: 4, source: 'Hardware store', note: 'Wall cleat to the studs, two per stud, countersunk flush: the back panel lies against the cleat face.', part: wallCleat.id, draw: { shape: 'screw', d: 0.19, len: 3 } },
      { item: '#10 × 3" cabinet screws (washer head)', qty: 2, source: 'Hardware store', note: 'Hold-down screws through the back and rail into the studs.', part: rail.id },
      { item: '18 ga brads, 1-1/4"', qty: '1 box', source: 'Hardware store', note: 'Top and bottom dados, to hold them while the glue cures.' }
    ],
    details_intro: 'The cleats are drawn square in the 3D view; this section shows the bevels. The hinge cup goes 5 mm from the door edge, 3" from each end.',
    details: [cleatDetail, cupDetail],
    view: {
      explode: 100, start: 'Front right',
      hint: 'Hover a part for its size. Click to select it everywhere on the plan.',
      dims: { B: [{ a: [0, D], b: [R, D], off: 0.8 }, { a: [R, yBack], b: [R, D], off: -0.8 }] },
      sections: [
        { id: 'A', cut: 'x', at: 7.5, title: 'through the left door, looking from the right' },
        { id: 'B', cut: 'z', at: r(zc - 1.5), keep: '-', box: [0, r(D - 3), r(zc - 3), 4, 3, 3], title: 'through the wall cleat at the left back corner, looking down' },
        { id: 'C', cut: 'z', at: hz[0], keep: '-', box: [0, -1, r(hz[0] - 1), 3.5, 3.5, 2], title: 'through the lower left hinge, looking down' }
      ]
    },
    stock: { sheet: { w: 48, l: 96, kerf: 0.125 }, sheets: { 'Plywood': { w: 48, l: 48 } }, board: { w: 1.5, l: 72, kerf: 0.125 }, buy: 'dimensional' },
    cutting_note: 'Everything but the back and the edge strips comes from one sheet of 3/4" birch plywood.',
    steps: [
      { title: 'Break down the plywood', text: 'Caliper the plywood. Rip and crosscut the sides {#1}, top {#2}, bottom {#3}, shelves {#8} and doors {#11}, with the face grain running up the sides and doors and across the top, bottom and shelves. Rip the cleat strip and bevel-rip it into the hanging cleat {#5} and wall cleat {#7}; cut the wall rail {#6}. Cut the back {#4} from 1/4" plywood.', parts: ['1', '2', '3', '4'] },
      { title: 'Dado and rabbet the sides, groove the top and bottom', text: 'With the router and edge guide, cut a ' + F(R) + '"-deep dado as wide as the plywood is thick across each side {#1} on the inside face, ' + F(E) + '" in from each end. Then cut a ' + F(R) + '"-deep, 1"-wide rabbet down the back edge of each inside face. Make a left and a right. On the table saw, cut a 1/4"-wide, ' + F(R) + '"-deep groove ' + F(P.cavity) + '" in from the back edge on the inside face of the top {#2} and bottom {#3}; fit it to the back.', parts: [] },
      { title: 'Drill the shelf-pin holes', text: 'Lay both sides inside face up. Draw the two hole lines ' + F(pinY[0]) + '" and ' + F(pinY[1]) + '" back from the front edge. Hook the jig\'s stop over the bottom end of each side, line its center on a line, and drill all ' + PN.n + ' holes ' + F(PN.depth) + '" deep with the stop collar. Do the four lines the same way.', parts: [],
        wrong: 'register the jig off the top end of one side and the bottom of the other. Unless every hole is measured from the same end, the shelves rock on three pins.' },
      { title: 'Assemble the case', text: 'Dry-fit first. Glue the top {#2} and bottom {#3} into the dados of one side and pin them with brads. Slide the back {#4} into the grooves from the open end until it seats in that side\'s rabbet, glued, then glue and brad on the second side. Clamp, check the diagonals, and let it cure.', parts: ['4'] },
      { title: 'Fit the cleat and rail', text: 'Glue the hanging cleat {#5} into the cavity behind the back, tight under the top, bevel down with the long face toward the wall. Drive five #6 × 3/4" screws through the back into it from inside, three #8 × 1-1/2" down through the top, and two #8 × 1" through each side. Glue the wall rail {#6} in at the bottom and screw it through the back. Band the front edges of the case.', parts: ['5', '6'] },
      { title: 'Make the shelves', text: 'Glue the poplar edge strips {#9} to the front edges of the shelves {#8}, tops flush, so they hang down. Check that each shelf drops between the sides with 1/16" to spare at each end.', parts: ['8', '9'] },
      { title: 'Make the doors', text: 'Measure the built case; the doors are ' + F(doorW) + '" × ' + F(doorH) + '" on a ' + F(W) + '" × ' + F(H) + '" case. Cut them, band all four edges, and trim the banding. Bore the 35 mm hinge cups ' + F(HG.depth) + '" deep, ' + F(DR.hingeIn) + '" from each end and 4 mm from the hinge edge (Hinge Cup Layout). Drill 3/16" pull holes ' + F(PU.in) + '" from the meeting edge, ' + F(PU.z) + '" and ' + F(PU.z + PU.c) + '" up from the bottom.', parts: ['11'] },
      { title: 'Finish', text: 'Sand and finish every part before the hardware goes on (Finishing Schedule). Keep finish off the cleat bevels so they seat.', parts: [] },
      { title: 'Hang the doors', text: 'Screw the hinge plates to the sides 37 mm back from the front edge, centered ' + F(hz[0]) + '" and ' + F(hz[1]) + '" up from the case bottom. Screw the hinges into the cups, clip each door onto its plates, and adjust for an even ' + F(DR.gap) + '" gap between the doors and ' + F(DR.reveal) + '" at the case edges. Fit the pulls {#13} from inside.', parts: ['12', '11', '13'] },
      { title: 'Hang the cabinet', text: 'Find two studs. Draw a level line ' + F(lineZ) + '" above where the cabinet bottom will be, and screw the wall cleat {#7} to both studs with its high edge on the line, the bevel facing up and sloping down toward the wall, two #10 × 3" flat-head screws per stud, countersunk flush (the back lies against the cleat face). Slide the cabinet sideways if needed so the cleat crosses two studs; leave about 1" to any side wall so the doors open fully. Lift the cabinet at least 1", push it to the wall, and lower it onto the cleat. Drill through the back and rail at the studs and drive two #10 × 3" washer-head hold-down screws. Set the shelf pins {#10} and shelves.', parts: ['7', '10', '8', '9'],
        wrong: 'hang it from drywall anchors or a cleat that misses the studs. A loaded cabinet pulls hard on the top screws; every wall screw goes into a stud.' }
    ],
    jigs: [{
      title: 'Shelf-Pin Drilling Jig', sub: 'Top View', w: 8, h: 26, for: ['1'],
      purpose: 'Puts all ' + PN.n * 4 + ' shelf-pin holes at the same heights in both sides, so every shelf sits flat on four pins.',
      use: 'Hook the stop over the bottom end of the side, line the hole centers up with a pencil line, clamp, and drill through the jig with a 1/4" brad-point bit. Set the stop collar for ' + F(PN.depth) + '" plus the jig thickness.',
      parts: [{ name: 'Strip', qty: 1, t: 0.5, w: 2, l: 25, material: 'Plywood' }, { name: 'Stop', qty: 1, t: 0.75, w: 0.75, l: 2, material: 'Hardwood' }],
      items: [
        { rect: [-1, -0.75, 2, 25], fill: 'wood' },
        { rect: [-1, -0.75, 2, 0.75], fill: 'end' },
        ...pinZ.map(z => ({ rect: [-0.125, z - 0.125, 0.25, 0.25], fill: 'none' })),
        { line: [0, -0.75, 0, 24.25], dash: true },
        { dim: [1, 0, 1, pinZ[0]], off: -1 },
        { dim: [1, pinZ[0], 1, pinZ[1]], off: -2.2 },
        { dim: [-1, 0, -1, pinZ[pinZ.length - 1]], off: 1 },
        { text: [-1.4, -0.4, 'stop'], size: 0.6, anchor: 'end' },
        { text: [1.4, 12, PN.n + ' holes, ' + F(PN.step) + '" apart'], size: 0.6, anchor: 'start' }
      ]
    }],
    story_sticks: [{
      title: 'Side Story Stick', axis: 'z', parts: ['1', '2', '3'],
      marks: pinZ.map(z => ({ at: z, label: 'pin' })).concat(hz.map(z => ({ at: z, label: 'hinge' }))),
      note: 'From the bottom end of a side: the dados, the shelf-pin rows and the hinge plate centers.'
    }],
    finish: {
      title: 'water-based polyurethane', note: 'Finish the parts before the hardware goes on. Keep finish out of the cup bores and off the cleat bevels.',
      steps: [
        { step: 'Sand', product: '120, then 180 grit', method: 'Random-orbit sander; ease the banded edges by hand', dry: '—' },
        { step: 'Seal', product: 'Dewaxed shellac, 1 lb cut', method: 'Wipe or brush one thin coat; it evens out the birch', dry: '1 h' },
        { step: 'Scuff', product: '220 grit', method: 'Light pass by hand, then wipe off the dust', dry: '—' },
        { step: 'Topcoat', product: 'Water-based polyurethane, satin', method: 'Two coats with a synthetic brush, 220 between', dry: '2 h between coats; 3 days before loading the shelves' }
      ]
    },
    revisions: [
      { rev: 'A', date: 'Oct 26 2026', summary: 'First issue',
        changes: [{ id: 'A1', summary: 'Initial design, full adversarial review', parts: allParts.map(p => p.id) }] },
      { rev: 'B', date: 'Oct 26 2026', summary: 'Fixes from the first review',
        changes: [
          { id: 'B1', summary: 'Top and bottom move from end rabbets into dados 1/2" in from the side ends', parts: ['1', '2', '3', '4', '5', '6', '7'], reason: 'In end rabbets the bottom and its load hung on glue and brads, and the sides hung off the top the same way. In dados every load bears on wood, and the brief asked for dados.' },
          { id: 'B2', summary: 'Hold-down screws #10 × 2-1/2" → #10 × 3"', parts: ['6'], reason: 'Through 1" of back and rail plus 1/2" of drywall, a 2-1/2" screw had only 1" in the stud.' },
          { id: 'B3', summary: 'Paperwork: story stick, cleat section, banding, real plywood lengths, two close-up sections', parts: ['1', '2', '3', '4', '5', '7', '12'], reason: 'The story stick marked the hinge bodies instead of the plate centers; the cleat section cut the back off short; 25 ft of banding was not enough; the cut list did not say what 23/32" plywood does to the lengths; the back rabbet and hinge were hidden in every view.' }
        ] },
      { rev: 'C', date: 'Oct 26 2026', summary: 'Fix from the second review',
        changes: [{ id: 'C1', summary: 'Wall cleat screws flat-head, countersunk flush', parts: ['7'], reason: 'The back panel lies against the wall cleat\'s front face; the washer heads of Rev B would stand about 1/8" proud and push the back or hold the cabinet off the wall.' },
          { id: 'C2', summary: 'Drawing fixes from the render check', parts: ['5', '6', '7'], reason: 'In the exploded views the hanging and wall cleat balloons landed on the top panel; the fastener labels ran into each other; Section B–B had no dimensions.' }] },
      { rev: 'D', date: 'Oct 28 2026', summary: 'Doors declared against their hinge; cups bored 5 mm from the edge',
        changes: [{ id: 'D1', summary: 'Door opening declared with its hinge (Blum CLIP top 110° full overlay), leaves, cup and plate; cup distance 4 mm → 5 mm', parts: [door.id, hinge.id], reason: 'The door check works the overlay from Blum\'s formula, 11 + cup distance − plate: a 4 mm bore on a 0 mm plate gives 15 mm, not the 16 mm (5/8") the doors overlay, leaving the hinge 0.9 mm into its 2 mm adjustment before the door is hung. At 5 mm it gives 16 mm exactly. No part sizes change.' }] }
    ],
    review: [
      { rev: 'D', change: 'D1', verdict: 'pass', mates: ['1', '2', '3'],
        checks: [
          { check: 'Doors against the Blum CLIP top 110° sheet {#11} {#12}', result: 'pass',
            evidence: 'Opening 28-1/2" between the sides; doors (30 − 2 × 1/8 − 1/8) ÷ 2 = 14-13/16" wide, 30 − 2 × 1/8 = 29-3/4" tall, overlaying the 3/4" sides by 5/8" (15.9 mm). Blum: 11 + 5 mm cup distance − 0 mm plate = 16 mm. Minimum reveal for a 19 mm door at 5 mm is 0.9 mm; nothing is hinged back to back, and the 1/8" edge reveals are 3.2 mm.' },
          { check: 'Hinge count and positions {#12}', result: 'pass', evidence: 'Each door is about 8 lb (14-13/16 × 29-3/4 × 3/4 at 42 lb/ft³) and 29-3/4" tall: two hinges (Salice chart: to 36" and 20 lb), 3" from each end.' },
          { check: 'Cup bore', result: 'pass', evidence: '35 mm, 1/2" (12.7 mm) deep against Blum\'s 13 mm, leaving 1/4" of door; the cup screws move 1 mm with the cup and stay 0.13" clear of it.' },
          { check: 'Paperwork', result: 'pass', evidence: 'Hardware list names the Blum 71B3550 and the 0 mm plate; step 7, the joint note, the cup layout and the Door Breakout say 5 mm.' }
        ] },
      { rev: 'C', change: 'C1', verdict: 'fixed', mates: ['4', '5'],
        checks: [
          { check: 'Wall cleat screw heads against the back {#7} {#4}', result: 'fixed',
            evidence: 'Found re-reviewing Rev B: the wall cleat face (y = ' + F(yCav) + '") is the plane the back\'s rear face sits on (model contact, J10), so any head proud of it bears on the 1/4" back. Washer heads stand about 1/8". The four wall screws are now #10 × 3" flat-head, countersunk flush; the two hold-down screws keep washer heads, which bear on the inside face of the back where nothing meets them.' },
          { check: 'Hardware and steps follow', result: 'pass',
            evidence: 'Hardware lists 4 flat-head and 2 washer-head #10 × 3" (B10: 4 holes, B11: 2). Step 10 says countersunk flush for the cleat and washer-head for the hold-downs. Model check: 0 errors, 0 warnings.' }
        ] },
      { rev: 'C', change: 'C2', verdict: 'fixed', mates: [],
        checks: [
          { check: 'Exploded views {#5} {#6} {#7}', result: 'fixed', evidence: 'With automatic explode the cleats sat behind the top and their balloons pointed at it. They are now set by hand to come out the back (cleat 10" back and 6" up, wall cleat 20" back, rail 10" back and 3" down); the viewer and Case & Cleats plates show each one clear. Render check: no collisions at full explode, no balloon problems.' },
          { check: 'Fasteners, Actual Size', result: 'fixed', evidence: 'The hinge screw labels overlapped, and the two hinge screw sizes were drawn twice (once from the bores, once from hardware lines). Labels shortened to "cup screw" and "plate screw"; the duplicate drawings removed. Counts unchanged: 8 and 8.' },
          { check: 'Section B–B dimensions', result: 'fixed', evidence: 'Added the 3/8" rabbet depth and the 1" rabbet width (1/4" back + 3/4" cavity) to the close-up.' }
        ] },
      { rev: 'A', change: 'A1', verdict: 'flag', mates: [],
        checks: [
          { check: 'Cut list re-derived from PARAMS {#1} {#2} {#3} {#4} {#5} {#6} {#7} {#8} {#9} {#11}', result: 'pass',
            evidence: 'Sides 3/4 × 11-1/4 × 30. Inside width 30 − 2 × 3/4 = 28-1/2, so the top, bottom, back width, hanging cleat and rail are 28-1/2 + 2 × 3/8 = 29-1/4. Wall cleat 28 (5/8" slack each end in the 29-1/4" cavity). Back front face at 11-1/4 − 3/4 − 1/4 = 10-1/4; shelves run from 1/4 + 3/4 strip = 1 to 10-1/4 − 1/8 = 10-1/8, so 9-1/8 deep, 28-1/2 − 2 × 1/16 = 28-3/8 long. Doors (30 − 2 × 1/8 − 1/8) ÷ 2 = 14-13/16 by 30 − 2 × 1/8 = 29-3/4. Model check: cut list matches, overall 30 × 13-1/4 × 30 (12" over the doors, 13-1/4" at the pulls).' },
          { check: 'Load path: top and bottom in end rabbets {#1} {#2} {#3}', result: 'fixed',
            evidence: 'The bottom sat in rabbets that open downward, so the bottom and everything on it hung on glue and brads in the 3/4" × 11-1/4" cheeks. The cleat holds the case up through the top, and the sides hung off the top the same way. Fixed in B1: dados 1/2" in from the ends put the bottom on a ledge of side and hang each side on the top.' },
          { check: 'Hold-down screw length {#6}', result: 'fixed',
            evidence: '#10 × 2-1/2" through 1/4" back + 3/4" rail + 1/2" drywall leaves 1" in the stud. Fixed in B2: 3", 1-1/2" in the stud.' },
          { check: 'Story stick and French cleat section', result: 'fixed',
            evidence: 'The stick listed part 12, which marks the hinge bodies 1" above and below each plate center, while its note promised the centers. The cleat section drew the back only from the cleat line up, not into the top groove. Both fixed in B3.' },
          { check: 'Edge banding', result: 'fixed',
            evidence: 'Doors 2 × 2 × (14-13/16 + 29-3/4) = 178", case front edges 2 × 30 + 2 × 29-1/4 = 118-1/2": 297", about 24.7 ft. A 25 ft roll leaves nothing for trimming. B3 lists a 50 ft roll.' },
          { check: 'Concealed hinges {#12} on {#1} {#11}', result: 'flag',
            evidence: 'Doors overlay the 3/4" sides by 3/4 − 1/8 = 5/8" (16 mm), so the hinge is a full-overlay 110° on a 0 mm plate. Cups 35 mm, 1/2" deep in 3/4" doors, leaving 1/4"; cup edge 4 mm from the door edge, center 0.846" in. Plate screws #6 × 5/8" into the side at 37 mm; cup screws #6 × 1/2". Two hinges per door: each door is about 3 sq ft of 3/4" plywood, roughly 7 lb, well inside two hinges at 29-3/4" tall. Hinges at 3" from each door end clear the case bottom and top inside faces by 7/8". Overlay for a given boring distance varies by maker: check your hinge chart gives 16 mm with a 0 mm plate, and use its side adjustment (±2 mm) for the rest.' },
          { check: 'Door swing, pair gap and side clearance {#11}', result: 'pass',
            evidence: 'The model check sees only the closed doors: no interference, 1/8" between the pair and 1/8" at each case edge. By hand, turning a door about its front hinge-side corner, the back corner of the meeting edge swings toward the other door by √(14-13/16² + 3/4²) − 14-13/16 = 0.02", so two doors opened together close the 1/8" gap by 0.04". Hinge makers\' minimum gaps for 3/4" doors are a few millimetres at most. At 90° the hinge edge stands about 5/8" past the case side, so step 10 leaves about 1" to any side wall.' },
          { check: 'Shelves clear the hinges and doors {#8} {#9} {#10} {#12}', result: 'pass',
            evidence: 'Pin rows run 6" to 23-1/2" every 1-1/4". The lowest possible shelf has its strip bottom at 6 + 1/8 − 3/4 = 5-3/8, above the lower hinge (top at 4-1/8); the highest shelf top is 23-1/2 + 1/8 + 3/4 = 24-3/8, below the upper hinge (25-7/8). Shelf front is 1/4" behind the door. Front pins at 1-1/2" sit 1/2" into the plywood behind the 3/4" strip; back pins at 8-3/4". Model check: shelves rest on the pins, no interference.' },
          { check: 'Shelf span {#8} {#9}', result: 'pass',
            evidence: 'The span between pins is 28-1/2", just over the 28" rule for 3/4" plywood under books. The 3/4" × 1-1/2" poplar strip glued under the front edge stiffens it as an L; long grain to the plywood edge, so no movement problem.' },
          { check: 'French cleat {#5} {#7} and hanging {#4}', result: 'pass',
            evidence: 'Both cleats are 3/4" plywood with 45° bevels that meet on a 1-1/16" face along 28". The cavity behind the back is 3/4" deep and 29-1/4" wide; the sides reach the wall. The cabinet lifts at least 3/4" (the bevel rise) to hook on; the cavity is open at the back and below the wall cleat down to the rail, so it goes on by lifting 1", pushing back and lowering. Four #10 × 3" screws (3/4 cleat + 1/2 drywall, 1-3/4" in the stud) carry it. A 28" cleat crosses two studs on 16" centers whenever a stud is within 12" of its end, so sliding the cabinet at most 4" sideways always finds two.' },
          { check: 'Case joints and racking {#1} {#2} {#3} {#4}', result: 'pass',
            evidence: 'Back rabbet 3/8" deep (half the side) and 1" wide; the back sits at its front shoulder. Top and bottom grooves 1/4 × 3/8, 3/4" in from the back edge. The back is glued on four edges and resists racking both ways; the cleat and rail, glued across the back, add to it.' },
          { check: 'Assembly order', result: 'pass',
            evidence: 'Top and bottom into one side; the back slides along the grooves from the open end into that side\'s rabbet (both the rabbet and the grooves open toward the second side); the second side goes on from the inside face. The cavity is open at the back, so the cleat and rail slide in last.' },
          { check: 'Fasteners B1–B11', result: 'pass',
            evidence: 'Model check: all 106 bores clear. Screw ratios: #8 × 1-1/2 through the 3/4" top (2×), #8 × 1 through the 3/8" side lip at the cavity (2.7×), #6 × 3/4 through the 1/4" back (3×). Pin holes 3/8" deep leave 3/8" of side. Pull holes 3/16" for #8-32 × 1" through the 3/4" door. Rail screws (x = 3, 11, 19, 27) stay 4" from the hold-down holes at the studs. Hinge cup and cup screws are 0.13" apart in height (screws at ±0.886", cup radius 0.689").' },
          { check: 'Wood movement', result: 'pass',
            evidence: 'All plywood except the 1-1/2"-wide poplar strips, glued long grain to long grain.' }
        ] },
      { rev: 'B', change: 'B1', verdict: 'pass', mates: ['8', '10', '11', '12'],
        checks: [
          { check: 'New heights re-derived {#2} {#3} {#4} {#5} {#6} {#7}', result: 'pass',
            evidence: 'Bottom 1/2" to 1-1/4", top 28-3/4" to 29-1/2"; inside height 30 − 2 × (1/2 + 3/4) = 27-1/2. Back 27-1/2 + 2 × 3/8 = 28-1/4 tall (worksheet: 29-1/4 → 28-1/4), still 29-1/4 wide. Hanging cleat 25-3/4" to 28-3/4", tight under the top; wall cleat 22-3/4" to 25-3/4"; rail 1-1/4" to 3-3/4". Lengths unchanged at 29-1/4 (dado depth equals the old rabbet depth).' },
          { check: 'Dados and load path {#1} {#2} {#3}', result: 'pass',
            evidence: 'Dados 3/8" deep in 3/4" sides (joinery.md: 1/4" to 3/8"), with 1/2" of side beyond each. The bottom now bears on a 3/8" × 11-1/4" ledge of side; each side bears on the top through the 1/2" above its dado; the top bears on the hanging cleat, which hooks the wall cleat. Every load ends in bearing on wood, then in four screws in studs. Model check: no thin walls (1/2" and 3/8").' },
          { check: 'Hinges, shelves and doors still clear {#11} {#12} {#8}', result: 'pass',
            evidence: 'Hinge bodies 2-1/8" to 4-1/8" and 25-7/8" to 27-7/8" now clear the bottom (1-1/4") and the top (28-3/4") by 7/8". Shelf openings 8-5/8, 9-1/4 and 8-1/8. Doors still cover the case: the side ends run to 0 and 30, doors 1/8" to 29-7/8".' },
          { check: 'Fastener positions moved with the parts', result: 'pass',
            evidence: 'Top screws now start at 29-1/2" and reach 28", 3/4" into the cleat; the 1/2" recess above the top is open, so the driver reaches them. Side screws at 26-1/2" and 28" stay in the cleat. Wall-cleat line in step 10 is now ' + F(lineZ) + '" (cleat line + 3/8"). Model check: 106 bores clear.' },
          { check: 'Paperwork', result: 'pass',
            evidence: 'Joint titles, side note, step 2 (dados 1/2" in from each end), step 4, the intro and the brad note now say dados.' }
        ] },
      { rev: 'B', change: 'B2', verdict: 'pass', mates: ['4', '7'],
        checks: [{ check: 'Hold-down screws {#6}', result: 'pass',
          evidence: '#10 × 3": 1/4 back + 3/4 rail + 1/2 drywall = 1-1/2", leaving 1-1/2" in the stud. One hardware line now covers all six #10 × 3" screws; step 10 says 3".' }] },
      { rev: 'B', change: 'B3', verdict: 'pass', mates: [],
        checks: [
          { check: 'Story stick', result: 'pass', evidence: 'Parts 1, 2, 3 (side ends and both dados) plus fifteen pin marks at 6" to 23-1/2" and hinge marks at 3-1/8" and 26-7/8", all from the side bottom.' },
          { check: 'French Cleat Section', result: 'pass', evidence: 'The back runs from below the wall cleat up into the top groove; the hanging cleat face reads 3-3/8" on the wall side, the wall cleat 2-5/8", meeting on the 45° line at the cleat line.' },
          { check: 'Real plywood note', result: 'pass', evidence: 'On 23/32" plywood the panels between the sides are 30 − 2 × (23/32 − 3/8) = 29-5/16", not 29-1/4"; the cut list note says so. Doors are sized from the outside of the case and do not change.' },
          { check: 'Sections B–B and C–C', result: 'pass', evidence: 'B–B cuts the left back corner through the wall cleat, showing the 3/8" × 1" rabbet, the back and the cavity; C–C cuts the lower left hinge, door and side.' }
        ] }
    ]
  };
};
module.exports.PARAMS = PARAMS;
