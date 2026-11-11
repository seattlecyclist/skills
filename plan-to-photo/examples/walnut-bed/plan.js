/* Queen castle-leg bed in quartersawn walnut, with a split curved headboard.
 * Mike Porter's design. Every driving number is in PARAMS.
 *   node scripts/build_plan.js plan.js --check
 */
const PARAMS = {
  rev: 'A',
  mattress: { w: 60, l: 80 },        // queen; the opening between the leg faces is exactly this
  leg: 3, legH: 13, foot: 2.25, taperTop: 8, legR: 0.75,   // legs; two inside faces taper to `foot` below taperTop
  railT: 1, railH: 4,                 // castle rails; rail tops flush with the leg tops
  cleat: 1,                           // 1" x 1" cleats outside the rails, flush with the tops
  support: 1, slatTop: 11.5,          // slat supports inside the side rails; slat top height
  slat: { t: 0.75, w: 2, n: 16, clear: 1 / 16 },
  center: { t: 0.75, w: 2, bracketW: 4, bracketH: 1.75, post: 2, posts: 3 },
  hb: { t: 1, top: 44, rise: 1.5, gapZ: 30, gap: 0.25, braceT: 1.25, braceW: 3, braceIn: 3, braceTop: 42, segs: 20 }
};

module.exports = function build(P = PARAMS, J = require('./scripts/joints.js')) {
  const r = v => Math.round(v * 1e5) / 1e5;
  const F = v => { const n = Math.round(v * 16), w = Math.floor(n / 16), f = n % 16; const g = (a, b) => b ? g(b, a % b) : a; return f ? (w ? w + '-' : '') + (f / g(f, 16)) + '/' + (16 / g(f, 16)) : String(w); };
  const L = P.leg, t = P.railT, H = P.railH, zb = P.legH - H;            // rail bottom
  const W = P.mattress.w + 2 * L, D = P.mattress.l + 2 * L;              // 66 x 86, outside of the legs
  const rc = L / 2;                                                      // rail centre line, 1-1/2" in from the outside
  const inX0 = rc + t / 2, inX1 = W - rc - t / 2;                        // side rail inner faces (2, 64)
  const inY0 = rc + t / 2, inY1 = D - rc - t / 2;                        // end rail inner faces (2, 84)
  const slatBot = P.slatTop - P.slat.t;
  const CT = P.center;
  const cx = W / 2;
  const HB = P.hb, hbY = D;                                             // headboard front face against the head legs

  // ---- frame ----
  const leg = { id: '1', name: 'Legs', section: 'frame', qty: 4, t: L, w: L, l: P.legH, material: 'Walnut, rift', stock: 'solid', glueup: 2,
    note: 'Two 1-5/8" rift layers, glue line parallel to one slot. ' + F(P.legR) + '" radius on the outside corner; two inside faces taper to ' + F(P.foot) + '" at the floor (see Leg pattern).',
    shape: [{ box: [0, 0, 0, L, L, P.legH] }],
    instances: [[0, 0], [W - L, 0], [0, D - L], [W - L, D - L]].map(([x, y]) => ({ at: [x, y, 0] })) };
  const sideRail = { id: '2', name: 'Side Rails', section: 'frame', qty: 2, t, w: H, l: D, material: 'Walnut, quartersawn', stock: 'solid',
    note: 'Lower member of the castle lap: notched from the top.',
    shape: [{ box: [0, 0, 0, t, D, H] }],
    instances: [rc - t / 2, W - rc - t / 2].map(x => ({ at: [x, 0, zb] })) };
  const endRail = { id: '3', name: 'End Rails', section: 'frame', qty: 2, t, w: H, l: W, material: 'Walnut, quartersawn', stock: 'solid',
    note: 'Upper member of the castle lap: notched from the bottom. Head rail gets six cap-nut seats.',
    shape: [{ box: [0, 0, 0, W, t, H] }],
    instances: [rc - t / 2, D - rc - t / 2].map(y => ({ at: [0, y, zb] })) };
  const sideCleat = { id: '4', name: 'Side Cleats', section: 'frame', qty: 2, t: P.cleat, w: P.cleat, l: D - 2 * L, material: 'Walnut, quartersawn', stock: 'solid',
    note: 'Outside the side rails, flush with the rail top and the leg faces.',
    shape: [{ box: [0, 0, 0, P.cleat, D - 2 * L, P.cleat] }],
    instances: [0, W - P.cleat].map(x => ({ at: [x, L, P.legH - P.cleat] })) };
  const endCleat = { id: '5', name: 'End Cleats', section: 'frame', qty: 2, t: P.cleat, w: P.cleat, l: W - 2 * L, material: 'Walnut, quartersawn', stock: 'solid',
    note: 'Outside the end rails, flush with the rail top and the leg faces.',
    shape: [{ box: [0, 0, 0, W - 2 * L, P.cleat, P.cleat] }],
    instances: [0, D - P.cleat].map(y => ({ at: [L, y, P.legH - P.cleat] })) };
  const support = { id: '6', name: 'Slat Supports', section: 'frame', qty: 2, t: P.support, w: P.support, l: D - 2 * L, material: 'Hard maple', stock: 'solid', mat: 'maple',
    shape: [{ box: [0, 0, 0, P.support, D - 2 * L, P.support] }],
    instances: [inX0, inX1 - P.support].map(x => ({ at: [x, L, slatBot - P.support] })) };
  const bracket = { id: '7', name: 'U Brackets', section: 'frame', qty: 2, t: 1, w: CT.bracketH, l: CT.bracketW, material: 'Hard maple', stock: 'solid', mat: 'maple',
    note: F(CT.w) + '" × ' + F(CT.t) + '" notch centred in the top edge.',
    shape: [{ box: [0, 0, 0, CT.bracketW, 1, CT.bracketH] }, { cut: [(CT.bracketW - CT.w) / 2, -1, CT.bracketH - CT.t, CT.w, 3, 1] }],
    instances: [inY0, inY1 - 1].map(y => ({ at: [cx - CT.bracketW / 2, y, zb] })) };
  const crL = inY1 - inY0 - 0.125;
  const centerRail = { id: '8', name: 'Center Rail', section: 'frame', qty: 1, t: CT.t, w: CT.w, l: crL, material: 'Hard maple', stock: 'solid', mat: 'maple',
    note: 'Lies flat in the U brackets, 1/16" short of each end rail.',
    shape: [{ box: [0, 0, 0, CT.w, crL, CT.t] }],
    instances: [{ at: [cx - CT.w / 2, inY0 + 0.0625, slatBot - CT.t] }] };
  const postH = slatBot - CT.t;
  const postY = [1, 2, 3].map(i => r(L + (D - 2 * L) * i / 4 - CT.post / 2));
  const cpost = { id: '9', name: 'Center Posts', section: 'frame', qty: CT.posts, t: CT.post, w: CT.post, l: postH, material: 'Walnut', stock: 'solid',
    note: 'A 3/8" dowel glued into each top locates the rail; nothing is screwed into the end grain.',
    shape: [{ box: [0, 0, 0, CT.post, CT.post, postH] }],
    instances: postY.map(y => ({ at: [cx - CT.post / 2, y, 0] })) };
  const slatL = r(inX1 - inX0 - 2 * P.slat.clear);
  const gap = (D - 2 * L - P.slat.n * P.slat.w) / (P.slat.n + 1);
  const slats = { id: '10', name: 'Slats', section: 'frame', qty: P.slat.n, t: P.slat.t, w: P.slat.w, l: slatL, material: 'Hard maple', stock: 'solid', mat: 'maple',
    note: 'Spaced ' + F(gap) + '" apart; one screw into each support.',
    shape: [{ box: [0, 0, 0, slatL, P.slat.w, P.slat.t] }],
    instances: Array.from({ length: P.slat.n }, (_, i) => ({ at: [inX0 + P.slat.clear, r(L + gap + i * (P.slat.w + gap)), slatBot] })) };

  // ---- headboard ----
  const par = x => 1 - Math.pow((x - W / 2) / (W / 2), 2);
  const yt = x => HB.top - HB.rise * par(x), yb = x => HB.gapZ + HB.rise * par(x), yl = x => yb(x) - HB.gap;
  const segX = Array.from({ length: HB.segs + 1 }, (_, i) => r(W * i / HB.segs));
  const extreme = (f, a, b, mode) => { const v = [f(a), f(b), f(Math.min(Math.max(W / 2, a), b))]; return mode === 'max' ? Math.max(...v) : Math.min(...v); };
  // curved boards modeled as narrow upright boxes that follow the curve (the true curve is on the Full-Size Patterns sheet)
  const topShape = segX.slice(0, -1).map((a, i) => { const b = segX[i + 1], z0 = extreme(yb, a, b, 'max'), z1 = extreme(yt, a, b, 'max');
    return { box: [a, 0, r(z0 - HB.gapZ), r(b - a), HB.t, r(z1 - z0)] }; });
  const lowShape = segX.slice(0, -1).map((a, i) => { const b = segX[i + 1], z1 = extreme(yl, a, b, 'min');
    return { box: [a, 0, 0, r(b - a), HB.t, r(z1 - zb)] }; });
  // slivers carry the true extremes, so the cut list gives the full blank: top board ends to 30", lower board crown to the center
  topShape.push({ box: [0, 0, 0, 0.0625, HB.t, HB.top - HB.gapZ] }, { box: [W - 0.0625, 0, 0, 0.0625, HB.t, HB.top - HB.gapZ] });
  lowShape.push({ box: [W / 2 - 0.03125, 0, 0, 0.0625, HB.t, r(yl(W / 2) - zb)] });
  const lowH = r(yl(W / 2) - zb), topH = r(HB.top - HB.gapZ);
  const spacer = { id: '11', name: 'Spacer Blocks', section: 'head', qty: 2, t: P.cleat, w: H - P.cleat, l: HB.braceW, material: 'Walnut', stock: 'solid',
    note: 'Grain runs side to side, parallel to the rail. Glued to the back of the head rail under the cleat.',
    shape: [{ box: [0, 0, 0, HB.braceW, P.cleat, H - P.cleat] }],
    instances: [HB.braceIn, W - HB.braceIn - HB.braceW].map(x => ({ at: [x, D - P.cleat, zb] })) };
  const lower = { id: '12', name: 'Headboard Lower Board', section: 'head', qty: 1, t: HB.t, w: lowH, l: W, material: 'Walnut, quartersawn', stock: 'solid', glueup: 1,
    note: 'Three boards edge-glued. Top edge on the template curve, ' + F(yl(0)) + '" at the ends rising to ' + F(yl(W / 2)) + '".',
    shape: lowShape, instances: [{ at: [0, hbY, zb] }] };
  const top = { id: '13', name: 'Headboard Top Board', section: 'head', qty: 1, t: HB.t, w: topH, l: W, material: 'Walnut, quartersawn', stock: 'solid', glueup: 1,
    note: 'Two boards edge-glued. Top edge dips ' + F(HB.rise) + '", bottom edge rises ' + F(HB.rise) + '"; ' + F(P.legR) + '" radius top corners.',
    shape: topShape, instances: [{ at: [0, hbY, HB.gapZ] }] };
  const braceH = HB.braceTop - zb;
  const brace = { id: '14', name: 'Headboard Braces', section: 'head', qty: 2, t: HB.braceT, w: HB.braceW, l: braceH, material: 'Walnut', stock: 'solid',
    note: 'Round screw holes next to the gap, slots elsewhere; two bolts at the bottom.',
    shape: [{ box: [0, 0, 0, HB.braceW, HB.braceT, braceH] }],
    instances: [HB.braceIn, W - HB.braceIn - HB.braceW].map(x => ({ at: [x, hbY + HB.t, zb] })) };

  const joints = [
    J.castle({ post: leg, lower: sideRail, upper: endRail, tool: 'bandsaw', title: 'Castle joint, four corners', glue: false, fasteners: 'None; gravity and the laps', note: 'Dry, so the frame comes apart. Wax the laps if a corner ever creaks.' }),
    J.joint('domino', [sideCleat, sideRail], { title: 'Side cleats to rails', glue: true, fasteners: '5 × 30 mm Dominos about every 8"', note: 'Long grain to long grain, parallel.' }),
    J.joint('domino', [endCleat, endRail], { title: 'End cleats to rails', glue: true, fasteners: '5 × 30 mm Dominos about every 8"; skip any within 1" of a headboard bolt' }),
    J.joint('butt', [sideCleat, endCleat, support, leg], { title: 'Cleat and support ends at the legs', glue: false, note: 'Cut to fit tight between the legs; not glued to them.' }),
    J.joint('screwed', [support, sideRail], { title: 'Slat supports to side rails', glue: true, fasteners: '#8 × 1-1/2" screws, eight per support' }),
    J.joint('screwed', [bracket, endRail], { title: 'U brackets to end rails', glue: true, fasteners: 'Two #8 × 1-1/2" screws each' }),
    J.joint('rests', [centerRail, bracket], { title: 'Center rail in the brackets', fasteners: 'None' }),
    J.joint('dowel', [cpost, centerRail], { title: 'Center posts under the rail', fasteners: '3/8" dowel glued in each post top, loose in the rail' }),
    J.joint('rests', [slats, support, centerRail], { title: 'Slats on supports and center rail', fasteners: 'One #8 × 1-1/2" screw each end' }),
    J.joint('glued', [spacer, endRail, endCleat], { title: 'Spacer blocks to head rail', glue: true, note: 'Grain parallel to the rail.' }),
    J.joint('bolted', [lower, brace, spacer, endCleat, endRail, sideRail, leg], { title: 'Headboard to frame', fasteners: 'Six 1/4-20 connector bolts into cap nuts', note: 'Two bolts per brace through brace, lower board, spacer or cleat and rail; two more at the center. Lower-board holes slotted 1/2" tall.' }),
    J.joint('screwed', [brace, top, lower], { title: 'Braces to boards', fasteners: '#10 × 2" pan-head screws with washers', note: 'Round holes beside the gap, slots elsewhere, so the 1/4" gap never changes.' })
  ];

  const braceX = [HB.braceIn + HB.braceW / 2, W - HB.braceIn - HB.braceW / 2];
  const back = hbY + HB.t + HB.braceT;
  const bores = [
    { id: 'B1', joint: 'J11', kind: 'bolt', label: '1/4-20 × 3-1/2" connector bolt', d: 9 / 32, depth: back - inY1, len: 3.5, counterbore: { d: 0.75, depth: 0.5 }, through: true, access: 0,
      copies: braceX.flatMap(x => [10.25, 12.5].map(z => ({ at: [x, back, z], dir: '-y' }))) },
    { id: 'B2', joint: 'J11', kind: 'hole', label: 'cap-nut seat', d: 0.375, depth: 0.625, cross: ['B1'],
      copies: braceX.flatMap(x => [10.25, 12.5].map(z => ({ at: [x, inY1, z], dir: '+y' }))) },
    { id: 'B3', joint: 'J11', kind: 'bolt', label: '1/4-20 × 2-3/4" connector bolt', d: 9 / 32, depth: hbY + HB.t - inY1, len: 2.75, through: true, access: 0,
      copies: [22, 44].map(x => ({ at: [x, hbY + HB.t, 12.5], dir: '-y' })) },
    { id: 'B4', joint: 'J11', kind: 'hole', label: 'cap-nut seat', d: 0.375, depth: 0.625, cross: ['B3'],
      copies: [22, 44].map(x => ({ at: [x, inY1, 12.5], dir: '+y' })) },
    { id: 'B5', joint: 'J12', kind: 'screw', label: '#10 × 2" pan-head', d: 0.19, len: 2, access: 0,
      copies: braceX.flatMap(x => [41, 31.9, 28.6, 20].map(z => ({ at: [x, back, z], dir: '-y' }))) },
    { id: 'B6', joint: 'J5', kind: 'screw', label: '#8 × 1-1/2" flat-head', d: 0.164, len: 1.5, qty: 16,
      copies: [[inX0 + P.support, '-x'], [inX1 - P.support, '+x']].map(([x, dir]) => ({ at: [x, D / 2, slatBot - P.support / 2], dir })) },
    { id: 'B7', joint: 'J9', kind: 'screw', label: '#8 × 1-1/2" flat-head', d: 0.164, len: 1.5, qty: 2 * P.slat.n,
      at: [inX0 + P.slat.clear + P.support / 2, slats.instances[3].at[1] + P.slat.w / 2, P.slatTop], dir: '-z' },
    { id: 'B8', joint: 'J8', kind: 'peg', label: '3/8" dowel', d: 0.375, depth: CT.t + 1,
      copies: postY.map(y => ({ at: [cx, y + CT.post / 2, slatBot], dir: '-z' })) }
  ];

  const half = W / 2, pts = Array.from({ length: 12 }, (_, i) => [r(i * half / 11), r(HB.rise * par(i * half / 11))]);
  return {
    meta: {
      series: 'Shop Plan', plan_no: 'MP-01', rev: P.rev, date: 'Oct 2026',
      title: 'Castle Leg Bed',
      subtitle: 'Queen platform frame in quartersawn walnut, split curved headboard',
      overall: { w: W, d: r(back), h: HB.top },
      wood: 'Quartersawn walnut & hard maple', skill: 'Intermediate', time: '4 weekends',
      intro: [
        'Four 3" legs carry the frame. Two slots cross in each leg top, the side rail {#2} drops in notch-up and the end rail {#3} drops over it notch-down, so the laps lock both rails and gravity does the rest. Nothing is bolted or glued at the corners; the frame lifts apart for moving. Walnut cleats {#4} {#5} fill the step outside each rail, so the frame reads as one flat band flush with the legs all the way around.',
        'The slats sit ' + F(P.legH - P.slatTop) + '" below the rail tops on maple supports and a center rail carried by three walnut posts. The headboard is two quartersawn boards in one plane, split by a 1/4" gap on a ' + F(HB.rise) + '"-rise curve, held by two braces that never reach the floor and bolted through the head rail.'
      ],
      needs: ['Domino DF 500 with a 5 mm cutter', 'A 1/2"-shank pattern or flush-trim bit, 1-1/4" cutting length', 'Hardware from the Hard-to-Find Hardware box'],
      toolkit: ['Spokeshave', 'Thin batten for laying out the curve'],
      check: { min_wall: 0.25 }
    },
    materials: { wood: { color: '#e2b768' }, maple: { color: '#f2e38a' }, hardware: { color: '#c5c2be' } },
    sections: [{ id: 'frame', title: 'Bed Frame' }, { id: 'head', title: 'Headboard', view: 'Rear' }],
    parts: [leg, sideRail, endRail, sideCleat, endCleat, support, bracket, centerRail, cpost, slats, spacer, lower, top, brace],
    cutlist_notes: ['Legs are listed at finished size before the taper and radius; lay those out from the Leg pattern.', 'Headboard boards are listed as rectangular blanks; cut the curves from the template.', 'Saw the castle slots to the actual milled rail thickness.'],
    joints, bores,
    hardware: [
      { item: 'Festool Domino 5 × 30 mm beech, 300-pack (494938)', qty: 36, source: 'thepowertoolstore.com, Festool dealers', note: 'Cleats to rails.' },
      { item: '1/4-20 × 3-1/2" black-oxide connector bolts (Rockler 49153)', qty: 4, source: 'rockler.com', note: 'Brace bolts.', draw: { shape: 'bolt', d: 0.25, len: 3.5 } },
      { item: '1/4-20 × 2-3/4" black-oxide connector bolts (Rockler 47428)', qty: 2, source: 'rockler.com', note: 'Center bolts.' },
      { item: '1/4-20 cap nuts, black (Rockler 45467)', qty: 6, source: 'rockler.com or woodcraft.com', note: 'In a 3/8" seat in the inside face of the head rail, over a washer.' },
      { item: '1/4" fender washers, 1" OD, black', qty: 2, source: 'Hardware store', note: 'Under the center bolt heads.' },
      { item: '3/8" SAE flat washers, 13/16" OD, black', qty: 6, source: 'Hardware store', note: 'Under each cap nut, on the inside face of the head rail, to spread the load.' },
      { item: '#10 × 2" pan-head wood screws and washers', qty: 8, source: 'Hardware store', note: 'Braces to boards.', draw: { shape: 'screw', d: 0.19, len: 2 } },
      { item: '#8 × 1-1/2" flat-head wood screws', qty: 52, source: 'Hardware store', note: 'Supports, brackets, slats.', draw: { shape: 'screw', d: 0.164, len: 1.5 } },
      { item: '3/8" walnut or maple dowel, 12"', qty: 1, source: 'Woodworking supplier', note: 'Three center-post pins.' },
      { item: 'Felt or UHMW glides, 1-1/2"', qty: 7, source: 'Hardware store', note: 'Legs and center posts.' }
    ],
    details: [
      { title: 'Headboard Curve Template', sub: 'half template, full size; flip it end for end for the other half', pattern: true, w: half + 1, h: 4,
        items: [
          { poly: [[0, 0]].concat(pts).concat([[half, 0]]), fill: 'wood' },
          { line: [0, 0, half, 0], dash: true },
          ...[0, 6, 12, 18, 24, 30].map(d => ({ line: [half - d, 0, half - d, r(HB.rise * par(half - d))] })),
          { text: [half - 2, 2.2, 'center: ' + F(HB.rise) + '" rise'], size: 0.5, anchor: 'end' },
          { text: [1, 2.2, 'end of board'], size: 0.5, anchor: 'start' },
          { dim: [0, 0, half, 0], off: -0.8 }
        ] },
      { title: 'Leg Pattern', sub: 'inside face and top view, full size', pattern: true, w: 9, h: 14,
        items: [
          { poly: [[0, 0], [P.foot, 0], [L, P.taperTop], [L, P.legH], [0, P.legH]], fill: 'wood', part: '1' },
          { rect: [(L - t) / 2, zb, t, H], fill: 'none', dash: true },
          { dim: [0, 0, P.foot, 0], off: -0.6 }, { dim: [L, 0, L, P.taperTop], off: -0.8 }, { dim: [L, zb, L, P.legH], off: -0.8 }, { dim: [0, P.legH, L, P.legH], off: 0.7 },
          { text: [L + 0.3, P.taperTop + 0.3, 'taper starts'], size: 0.45, anchor: 'start' },
          { poly: [[5, 9.5], [5, 9.5 + L - P.legR], [5 + P.legR * 0.29, 9.5 + L - P.legR * 0.29], [5 + P.legR, 9.5 + L], [5 + L, 9.5 + L], [5 + L, 9.5]], fill: 'end' },
          { text: [5 + L / 2, 9.0, 'top: ' + F(P.legR) + '" R outside corner'], size: 0.45 }
        ] }
    ],
    view: {
      explode: 100, start: 'Front right',
      sections: [
        { id: 'A', cut: 'x', at: braceX[0], keep: '+', box: [0, D - 6, 0, W, 9, HB.top + 1], title: 'through the left brace and its bolts' },
        { id: 'B', cut: 'y', at: r(slats.instances[7].at[1] + P.slat.w / 2), keep: '+', box: [0, slats.instances[7].at[1], 0, 10, 4, P.legH + 0.5], title: 'through a slat, left side' }
      ]
    },
    steps: [
      { title: 'Laminate and mill the legs', text: 'Glue two 1-5/8" rift layers for each leg {#1}, then mill to ' + F(L) + '" square. Rout the ' + F(P.legR) + '" radius on the one outside corner while the leg is solid, so the outer tower gets it too.', parts: ['1'] },
      { title: 'Cut the castle slots', text: 'Mill the rails {#2} {#3} first. Saw both slots ' + F(t) + '" wide and ' + F(H) + '" deep on the bandsaw, clear the waste and pare the floors flat; the rails bear on them.', parts: ['1'] },
      { title: 'Notch the rails', text: 'Side rails {#2} notch ' + F(H / 2) + '" from the top, end rails {#3} ' + F(H / 2) + '" from the bottom, each 1" wide and 1" from the end. Knife the walls from a leg, not a tape.', parts: ['2', '3'] },
      { title: 'Taper the legs', text: 'Taper the two inside faces of each leg {#1} from ' + F(P.taperTop) + '" off the floor to ' + F(P.foot) + '" at the bottom. Drill the cap-nut and bolt holes later, from the frame.', parts: ['1'] },
      { title: 'Cleats', text: 'Dry-fit the frame. Fit the cleats {#4} {#5} tight between the legs, cut 5 mm Dominos about every 8" (skip any within 1" of 4-1/2", 22", 44" or 61-1/2" on the head cleat), and glue them flush with the rail tops and the leg faces.', parts: ['4', '5'],
        wrong: 'glue the cleats or rails to the legs. Only cleat to rail is glued; the corners must lift apart.' },
      { title: 'Supports and center', text: 'Glue and screw the slat supports {#6} to the side rails with their bottoms 3/4" above the rail bottom, and the U brackets {#7} to the end rails flush with the rail bottom. Glue a 3/8" dowel into each center post {#9}, drill the center rail {#8} to drop over them, and set it in the brackets.', parts: ['6', '7', '8', '9'] },
      { title: 'Slats', text: 'Space the slats {#10} ' + F(gap) + '" apart and screw each end to its support.', parts: ['10'] },
      { title: 'Headboard boards', text: 'Glue up the lower {#12} and top {#13} boards. Cut all three curved edges from one template (Shop Aids) with a 1/2"-shank bit, routing downhill from the ends toward the center. Check the 1/4" gap with spacers before anything else.', parts: ['12', '13'] },
      { title: 'Braces', text: 'With 1/4" spacers in the gap, screw the braces {#14} to both boards: round holes for the screw beside the gap in each board, 1/4" slots for the others.', parts: ['14'],
        wrong: 'use round holes for every brace screw. Each board must grow away from the gap, or the gap closes in summer.' },
      { title: 'Bolt to the frame', text: 'Glue the spacer blocks {#11} behind the head rail. Clamp the headboard on, drill the six bolt holes, slot the lower board holes 1/2" tall, and set a 3/8" washer under each cap nut on the inside face of the rail.', parts: ['11'] },
      { title: 'Finish and assemble', text: 'Finish every part. Stand the legs, drop in the side rails, then the end rails, set the center rail and posts, lay the slats, and bolt on the headboard.', parts: ['1', '2', '3'] }
    ],
    jigs: [{ title: 'Curve Template', sub: 'Router Template', w: 12, h: 4, for: ['12', '13'],
      purpose: 'One 72" template cuts the top edge of the top board, its bottom edge, and the top edge of the lower board, so the gap stays an even 1/4".',
      use: 'Lay out the curve with a thin batten through the offsets on the Full-Size Patterns sheet, fair it with a spokeshave, and flip the template end for end for the second half. Bandsaw 1/8" outside the line and flush-trim.',
      parts: [{ name: 'Template, 1/2" MDF', qty: 1, t: 0.5, w: 6, l: 72, material: 'MDF' }, { name: 'Batten', qty: 1, t: 0.25, w: 0.75, l: 80, material: 'Straight-grained fir or ash' }],
      items: [{ poly: [[0, 0], [12, 0], [12, 3], [6, 2.4], [0, 3]], fill: 'wood' }, { text: [6, 1.2, '72" long, 1/2" MDF'], size: 0.5 }] }],
    story_sticks: [{ title: 'Headboard Story Stick', axis: 'z', parts: ['3', '11', '12', '13', '14'],
      marks: [{ at: 10.25, label: 'brace bolt' }, { at: 12.5, label: 'bolt' }, { at: 20, label: 'slot' }, { at: 28.6, label: 'round' }, { at: 31.9, label: 'round' }, { at: 41, label: 'slot' }],
      note: 'From the floor, at the ends of the headboard.' }],
    finish: { title: 'hardwax oil', note: 'Finish every part before assembly; keep oil off Domino mortises and the spacer glue faces.',
      steps: [
        { step: 'Sand', product: '150 then 180 grit; end grain to 320', method: 'With the grain', dry: 'none' },
        { step: 'Raise the grain', product: 'Water', method: 'Wipe damp, dry, knock down with 220', dry: '1 h' },
        { step: 'Oil', product: 'Rubio Monocoat Oil Plus 2C, Pure', method: 'Thin coat, wipe off all excess within 15 min', dry: '24 h, full cure 7 days' }] },
    revisions: [{ rev: 'A', date: 'Oct 26 2026', summary: 'First issue in the woodworking-plans format',
      changes: [{ id: 'A1', summary: 'Whole design, full adversarial review', parts: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14'] }] }],
    review: [{ rev: 'A', change: 'A1', verdict: 'flag', mates: [],
      checks: [
        { check: 'Dimensions {#1} to {#14} re-derived from PARAMS', evidence: 'Outside 60 + 2 × 3 = 66\" × 80 + 6 = 86\". Rails 1 × 4 × 86 and 66. Cleats and supports 86 − 6 = 80, end cleats 60. Center rail (84 − 2) − 1/8 = 81-7/8\". Posts 10-3/4 − 3/4 = 10\". Slats (64 − 2) − 1/8 = 61-7/8\", gaps (80 − 32) ÷ 17 = 2-13/16\". Lower board 31-1/4 − 9 = 22-1/4\" blank, top board 44 − 30 = 14\", braces 42 − 9 = 33\". All match the cut list and the model.', result: 'pass' },
        { check: 'J1 castle {#1} {#2} {#3}: proportions, tools, load path', evidence: 'Slots 1\" × 4\" in a 3\" leg leave 1\" towers, a third of the leg (rule: a quarter, 3/4\" minimum). Laps 2\" + 2\" = rail height. Slots on the bandsaw (4\" deep); rail notches 2\" deep, inside a dado stack\'s 2-1/2\". Side rail bears on the slot floor, end rail on the side-rail lap: wood on wood to the floor.', result: 'pass' },
        { check: 'Leg corner radius on a 1\" tower {#1}', evidence: 'A 3/4\" radius removes 0.56 × (1 − π/4) = 0.12 sq in of the 1 sq in outer tower, 12%. The tower is long grain and captured by both rails once assembled. My earlier note called it fragile; the numbers do not support that.', result: 'pass' },
        { check: 'Side rail size {#2}', evidence: 'joinery.md asks for 1-1/4\" × 6\" minimum on a queen side rail; these are 1\" × 4\". With slats continuous over the center rail, each side rail carries about 3/16 of the load: 112 lb of a 600 lb design load over 80\" gives 420 psi bending stress (walnut breaks near 14,600) and 0.08\" sag. A 250 lb person sitting mid-rail gives about 0.22\" of flex, counting the glued cleat (I 7.2 in⁴). Strong enough; it will flex a little when sat on. Going to 1\" × 5\" would cut that flex by half. Your call.', result: 'flag' },
        { check: 'J2 J3 Dominos {#4} {#5} {#2} {#3}', evidence: '5 mm Dominos 15 mm deep into 25 mm parts leave 10 mm walls. Cleat and rail grain run the same way, so a full glue line is safe. Glued cleats sit between the legs, so each rail still drops straight down into its slots.', result: 'pass' },
        { check: 'J5 J6 supports and brackets {#6} {#7}', evidence: 'Glued long grain to the rails, with screws as clamps. The model check warns that a 1-1/2\" screw is 1.5× the 1\" support; a 2\" screw would come through the 1\" rail, so 1-1/2\" (1/2\" into the rail) is the longest that fits. The glue line carries the load.', result: 'pass' },
        { check: 'J8 center posts {#9} {#8}', evidence: 'The old page screwed the center rail down into the end grain of each post. Now a 3/8\" dowel glued 1\" into each post top passes up through a hole in the 3/4\" rail. The load is the rail bearing on the post end grain; nothing hangs on a screw.', result: 'fixed' },
        { check: 'J9 slats {#10} on {#6} {#8}', evidence: 'Slats end 1/16\" from the rail faces, so each bears on 15/16\" of the 1\" support. Slat screws were #8 × 1-1/4\" (1.7× the slat, 1/2\" into the support); now #8 × 1-1/2\": 2× the slat and 3/4\" into the support. The middle screw into the 3/4\" center rail is dropped; a 1-1/2\" screw would come through it. First slat starts at 5-13/16\", clear of the U brackets (2\" to 3\").', result: 'fixed' },
        { check: 'J10 spacer blocks {#11}', evidence: 'The old cut sheet gave no grain direction for a 3\" × 3\" block glued to the rail. Now grain runs side to side, parallel to the rail, so the glue line is long grain to long grain.', result: 'fixed' },
        { check: 'J11 headboard bolts {#12} {#14} {#11} {#5} {#3}: reach and clearance', evidence: 'Brace bolt stack 1-1/4 + 1 + 1 + 1 = 4-1/4\"; less the 1/2\" counterbore leaves 3-3/4\", so the 3-1/2\" bolt stops 1/4\" short of the rail face, 3/8\" (7 threads) into the 5/8\" cap nut. Center stack 3\", 2-3/4\" bolt, same 3/8\" engagement. Cap nuts at 4-1/2\" sit 1-1/2\" from the leg face; the center nuts at 22\" and 44\" clear the U brackets at 31\" to 35\". Two bolts per brace, 2-1/4\" apart, so the headboard cannot hinge.', result: 'pass' },
        { check: 'J11 headboard bolts: bearing under the cap nuts', evidence: 'A 100 lb lean at 34\" pivots the headboard on the frame at 9\": 2,500 in-lb, about 170 lb on each upper bolt. The cap nut flange alone bears on about 0.14 sq in of walnut, 1,200 psi, above walnut\'s roughly 1,000 psi crushing strength across the grain: it would dent in over time. Added a 3/8\" SAE washer (13/16\" OD) under each cap nut: 0.40 sq in, 420 psi. The washer top stays 3/32\" below the rail top. Pushing the bed against the wall takes most of this load anyway.', result: 'fixed' },
        { check: 'J12 braces {#14} {#13} {#12}: movement', evidence: 'Quartersawn walnut moves about 0.0019 per inch per 1% moisture; over a 4% swing the lower board moves 0.17\" and the top board 0.11\". Each board is pinned only by the screw beside the gap (31.9\" and 28.6\"), so the gap stays 1/4\". Farthest slotted screw is 9.1\" from its pin: 0.07\" of travel in a 1/4\" slot. The bolts are 18.4\" below the lower pin: 0.14\" in a 1/2\" slot. The model check warns a 2\" screw is 1.6× the 1-1/4\" brace; the board is only 1\" thick, and 2\" already leaves just 1/4\" of wood in front of the tip.', result: 'pass' },
        { check: 'Mattress fit', evidence: 'Leg faces are exactly 60\" × 80\" apart; the rails stand 1\" farther out on each side. A standard queen touches only at the four inside leg corners. Measure yours; an oversize mattress needs the legs moved.', result: 'pass' },
        { check: 'Paperwork', evidence: 'Every bore has a step: B1 to B4 in step 10, B5 in 9, B6 and B8 in 6, B7 in 7. #8 × 1-1/2\" count: 16 supports + 4 brackets + 32 slats = 52. Dominos: 10 per side cleat and 8 per end cleat, less any skipped beside the bolts at 4-1/2\", 22\", 44\", 61-1/2\": 36 or fewer. Intro: slats 1-1/2\" below the rail tops (13 − 11-1/2).', result: 'pass' }
      ] }]
  };
};
module.exports.PARAMS = PARAMS;
