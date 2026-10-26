/* Castle-joint platform bed with slatted headboard (queen).
 * Parametric: every dimension below derives from PARAMS, so a change (say, thicker rails)
 * moves every mating part with it. Build:  node ../../scripts/build_plan.js plan.js out.html
 */
const PARAMS = {
  rev: 'D',
  mattress: { w: 60, l: 80 },   // queen
  clear: 3 / 8,                 // mattress clearance per side, measured to the post faces (the tightest point)
  post: 3.5,                    // corner and headboard posts, square
  railT: 1.5,                   // rail thickness (Rev A: 1-1/4)
  railH: 6.5,                   // rail height; the castle half-lap takes half of it at each post
  railTop: 14,                  // floor to top of rails and posts
  ext: 3,                       // rail ends run past the post faces (Rev A/B: 2; the head end needs room for barrel nuts)
  pocket: 3,                    // mattress sinks this far below the rail tops
  slat: { t: 0.75, w: 3.5, n: 14 },
  cleat: { t: 1, h: 1.5 },     // Rev A/B: 3/4
  spine: { t: 1.5, h: 3.5 },
  hb: { h: 48, topT: 1.25, topH: 5, botH: 4, botZ: 15, slatN: 9, slatW: 4.5, slatT: 0.75, tenon: 0.75 }
};

module.exports = function build(P = PARAMS, J = require('../../scripts/joints.js')) {
  const half = P.post / 2, t = P.railT, h = P.railH, Zb = P.railTop - P.railH;
  const inW = P.mattress.w + 2 * P.clear, inL = P.mattress.l + 2 * P.clear;
  // Rails run through the post centers, so the inner half of each post stands inside the rail line.
  // The mattress opening is therefore measured between post faces, not rail faces.
  const xcL = P.ext + half, xcR = xcL + inW + P.post;
  const ycF = P.ext + half, ycH = ycF + inL + P.post;
  const Lend = xcR + half + P.ext, Lside = ycH + half + P.ext;
  const footIn = ycF + t / 2, headIn = ycH - t / 2;          // end rail inner faces
  const postIn = ycF + half;                                 // foot post inner faces
  const slatTop = P.railTop - P.pocket, slatBot = slatTop - P.slat.t;
  const hbY = Lside, hbYc = hbY + half;                      // headboard posts sit against the side rail ends
  const HB = P.hb;
  const span = (xcR - half) - (xcL + half);                  // between headboard posts
  const hbSlatH = (HB.h - HB.topH) - (HB.botZ + HB.botH);
  const r = v => Math.round(v * 1e5) / 1e5;
  const F = v => { const n = Math.round(v * 16), w = Math.floor(n / 16), f = n % 16; const g = (a, b) => b ? g(b, a % b) : a; return f ? (w ? w + '-' : '') + (f / g(f, 16)) + '/' + (16 / g(f, 16)) : String(w); };
  const sx = [-1, 1];

  // Parts are plain boxes where they sit; the joint helpers at the bottom cut the castle slots,
  // half-laps and bridle slots and add the tenons.
  const post = {
    id: '1', name: 'Corner Posts', section: 'frame', qty: 4, t: P.post, w: P.post, l: P.railTop, glueup: 2,
    material: 'White oak', stock: 'solid',
    note: 'Face-glue two 8/4 blanks, then cut the castle slots.',
    pattern: true,                                              // full-size slot layout, to mark all four posts from
    shape: [{ box: [0, 0, 0, P.post, P.post, P.railTop] }],
    instances: [[xcL, ycF, -1, -1], [xcR, ycF, 1, -1], [xcL, ycH, -1, 1], [xcR, ycH, 1, 1]].map(([x, y, a, b]) => ({ at: [r(x - half), r(y - half), 0], explode: [a * 6, b * 6, -6] })),
    callout: { inst: 1 }
  };
  // end rails are the lower member of the castle lap, side rails the upper
  const endRail = {
    id: '2', name: 'End Rails', section: 'frame', qty: 2, t, w: h, l: Lend, material: 'White oak', stock: 'solid',
    shape: [{ box: [0, 0, 0, Lend, t, h] }],
    instances: [ycF, ycH].map((y, i) => ({ at: [0, r(y - t / 2), Zb], explode: [0, i ? 6 : -6, 9] })),
    callout: { inst: 0 }
  };
  const sideRail = {
    id: '3', name: 'Side Rails', section: 'frame', qty: 2, t, w: h, l: Lside, material: 'White oak', stock: 'solid',
    note: 'Two barrel-nut holes in the head end, see Headboard Bolts.',
    shape: [{ box: [0, 0, 0, t, Lside, h] }],
    instances: [xcL, xcR].map((x, i) => ({ at: [r(x - t / 2), 0, Zb], explode: [sx[i] * 9, 0, 19] })),
    callout: { inst: 1 }
  };
  const cleatL = inL - 0.25;                                  // runs between the posts, 1/8" clear each end
  const cleat = {
    id: '4', name: 'Slat Cleats', section: 'frame', qty: 2, t: P.cleat.t, w: P.cleat.h, l: cleatL, material: 'Poplar', stock: 'solid', mat: 'poplar',
    shape: [{ box: [0, 0, 0, P.cleat.t, cleatL, P.cleat.h] }],
    instances: [
      { at: [r(xcL + t / 2), r(postIn + 0.125), r(slatBot - P.cleat.h)], explode: [-2, 0, 15] },
      { at: [r(xcR - t / 2 - P.cleat.t), r(postIn + 0.125), r(slatBot - P.cleat.h)], explode: [2, 0, 15] }
    ]
  };
  const spineL = (headIn - footIn) - 0.25;                    // between end rails, 1/8" bracket gap each end
  const spine = {
    id: '5', name: 'Center Spine', section: 'frame', qty: 1, t: P.spine.t, w: P.spine.h, l: spineL, material: 'Poplar', stock: 'solid', mat: 'poplar',
    note: 'Hangs on hook-in brackets at each end rail.',
    shape: [{ box: [0, 0, 0, P.spine.t, spineL, P.spine.h] }],
    instances: [{ at: [r((xcL + xcR) / 2 - P.spine.t / 2), r(footIn + 0.125), r(slatBot - P.spine.h)], explode: [0, 0, 24] }]
  };
  const legH = slatBot - P.spine.h;
  const legs = {
    id: '6', name: 'Center Support Legs', section: 'frame', qty: 2, size: 'Adjustable steel, set to ' + F(legH) + '"', material: 'Steel', stock: 'hardware', mat: 'hardware',
    shape: [{ box: [0, 0, 0, 1.5, 1.5, legH] }],
    instances: [1 / 3, 2 / 3].map(f => ({ at: [r((xcL + xcR) / 2 - 0.75), r(footIn + 0.125 + spineL * f - 0.75), 0], explode: [0, 0, 13] }))
  };
  const slatL = (xcR - xcL - t) - 0.25;                      // between side rail faces, 1/8" clear each end
  const gap = (inL - P.slat.n * P.slat.w) / (P.slat.n + 1);
  const slats = {
    id: '7', name: 'Slats', section: 'frame', qty: P.slat.n, t: P.slat.t, w: P.slat.w, l: slatL, material: 'Poplar', stock: 'solid', mat: 'poplar',
    note: 'Spaced ' + F(gap) + '" apart; one screw into each cleat keeps the spacing.',
    shape: [{ box: [0, 0, 0, slatL, P.slat.w, P.slat.t] }],
    instances: Array.from({ length: P.slat.n }, (_, i) => ({ at: [r(xcL + t / 2 + 0.125), r(postIn + gap + i * (P.slat.w + gap)), r(slatBot)], explode: [0, 0, 34] })),
    callout: { inst: 6 }
  };

  // headboard
  const hbPost = {
    id: '8', name: 'Headboard Posts', section: 'head', qty: 2, t: P.post, w: P.post, l: HB.h, glueup: 2, material: 'White oak', stock: 'solid',
    note: 'Open slot at the top for the cap rail; mortise for the bottom rail.',
    shape: [{ box: [0, 0, 0, P.post, P.post, HB.h] }],
    instances: [xcL, xcR].map((x, i) => ({ at: [r(x - half), r(hbY), 0], explode: [sx[i] * 6, 20, 0] }))
  };
  const botRail = {
    id: '9', name: 'Headboard Bottom Rail', section: 'head', qty: 1, t: HB.topT, w: HB.botH, material: 'White oak', stock: 'solid',
    shape: [{ box: [0, 0, 0, span, HB.topT, HB.botH] }],          // shoulder to shoulder; J.mortiseTenon adds the tenons and sets l
    instances: [{ at: [r(xcL + half), r(hbYc - HB.topT / 2), HB.botZ], explode: [0, 20, 0] }]
  };
  const topRail = {
    id: '10', name: 'Headboard Cap Rail', section: 'head', qty: 1, t: HB.topT, w: HB.topH, l: Lend, material: 'White oak', stock: 'solid',
    note: 'Ends run past the posts to match the end rails below.',
    shape: [{ box: [0, 0, 0, Lend, HB.topT, HB.topH] }],
    instances: [{ at: [0, r(hbYc - HB.topT / 2), HB.h - HB.topH], explode: [0, 20, 13] }]
  };
  const hbGap = (span - HB.slatN * HB.slatW) / (HB.slatN + 1);
  const ttk = 0.375, twinW = 1.5;                           // twin tenons: each no wider than 4x its thickness
  const hbSlat = {
    id: '11', name: 'Headboard Slats', section: 'head', qty: HB.slatN, t: HB.slatT, w: HB.slatW, material: 'White oak', stock: 'solid',
    note: 'Twin stub tenons both ends, ' + ttk * 8 + '/8" × ' + F(twinW) + '".',
    shape: [{ box: [0, 0, 0, HB.slatW, HB.slatT, hbSlatH] }],
    instances: Array.from({ length: HB.slatN }, (_, i) => ({ at: [r(xcL + half + hbGap + i * (HB.slatW + hbGap)), r(hbYc - HB.slatT / 2), HB.botZ + HB.botH], explode: [0, 20, 6.5] })),
    callout: { inst: 4 }
  };

  // joints, in build order; the helpers cut and size the joinery from the parts above
  const joints = [
    J.castle({ post, lower: endRail, upper: sideRail, title: 'Castle joint, four corners', fasteners: 'One 5/16" cross-bolt through the lap', explode: 55 }),
    J.joint('screwed', [cleat, sideRail], { title: 'Cleats to side rails', glue: true, fasteners: '#8 × 2" screws, 8" apart', note: 'Long grain to long grain, so glue is safe here.' }),
    J.joint('rests', [slats, cleat], { title: 'Slats on cleats', fasteners: 'One #8 × 1-1/2" screw each end, piloted', note: 'Center the screw on the 7/8" of bearing and drill a pilot hole so the cleat edge does not split.' }),
    J.joint('rests', [slats, spine], { title: 'Slats on spine', fasteners: 'None' }),
    J.joint('bracket', [spine, endRail], { title: 'Spine to end rails', gap: 0.125, fasteners: 'Hook-in center rail brackets', note: 'Brackets take the 1/8" gap at each end.' }),
    J.joint('screwed', [legs, spine], { title: 'Legs under spine', fasteners: 'Leg plate screws' }),
    J.mortiseTenon({ rail: botRail, hosts: [hbPost], thick: 0.5, length: 1.5, shoulder: 0.5, twin: false, title: 'Bottom rail to headboard posts' }),
    J.bridle({ post: hbPost, rail: topRail, title: 'Cap rail in post tops', fasteners: 'Glue + two 3/8" pegs per post', note: 'An open slot in each post top, the headboard echo of the castle corners below.' }),
    J.mortiseTenon({ rail: hbSlat, hosts: [botRail, topRail], thick: ttk, length: HB.tenon, shoulder: 0.25, twin: twinW, title: 'Headboard slats' }),
    J.joint('bed-bolt', [sideRail, hbPost], { title: 'Headboard to side rails', fasteners: 'Two 3/8" × 6" bed bolts per side', note: 'Bolts at ' + F(Zb + 1.5) + '" and ' + F(P.railTop - 1.5) + '" from the floor, so the headboard cannot hinge on a single bolt line.' })
  ];

  // bores and fasteners, modeled so the check can prove they can be drilled and reach their nuts
  const corners = [[xcL, ycF, 1], [xcR, ycF, -1], [xcL, ycH, 1], [xcR, ycH, -1]];  // 1: inside face is +x
  const dowel = 10 / 25.4, nutZ = Zb - 1.5, bedZ = [Zb + 1.5, P.railTop - 1.5];
  const slat0 = slats.instances[0].at;
  const bores = [
    { id: 'B1', joint: 'J1', kind: 'bolt', label: 'cross-bolt', d: 5 / 16, depth: h + 2.125, len: 8, counterbore: { d: 1, depth: 0.625 }, washer: 0.875, nut: 'B2', bit: 12,
      copies: corners.map(([x, y]) => ({ at: [x, y, P.railTop], dir: '-z' })) },
    { id: 'B2', joint: 'J1', kind: 'cross-dowel', label: 'cross dowel', d: dowel, depth: half + 0.375,
      copies: corners.map(([x, y, s]) => ({ at: [x + s * half, y, nutZ], dir: s > 0 ? '-x' : '+x' })) },
    { id: 'B3', joint: 'J10', kind: 'bolt', label: 'bed bolt', d: 3 / 8, depth: 6, len: 6, nut: 'B4',
      copies: [xcL, xcR].flatMap(x => bedZ.map(z => ({ at: [x, Lside + P.post, z], dir: '-y' }))) },
    { id: 'B4', joint: 'J10', kind: 'cross-dowel', label: 'bed-bolt barrel nut', d: dowel, depth: t / 2 + 0.375,
      copies: [[xcL, 1], [xcR, -1]].flatMap(([x, s]) => bedZ.map(z => ({ at: [x + s * t / 2, Lside - 2.25, z], dir: s > 0 ? '-x' : '+x' }))) },
    { id: 'B5', joint: 'J2', kind: 'screw', label: '#8 × 2" screw', d: 0.164, len: 2, qty: 24,
      copies: [[xcL + t / 2 + P.cleat.t, '-x'], [xcR - t / 2 - P.cleat.t, '+x']].map(([x, dir]) => ({ at: [x, (ycF + ycH) / 2, slatBot - P.cleat.h / 2], dir })) },
    { id: 'B6', joint: 'J3', kind: 'screw', label: '#8 × 1-1/2" screw', d: 0.164, len: 1.5, qty: 2 * P.slat.n,
      at: [slat0[0] + 0.4375, slat0[1] + P.slat.w / 2, slatTop], dir: '-z' }
  ];

  return {
    meta: {
      series: 'Shop Plan', plan_no: '014', rev: P.rev, date: 'Oct 2026',
      title: 'Castle Joint Bed',
      subtitle: 'Queen platform frame with slatted headboard',
      overall: { w: r(Lend), d: r(Lside + P.post), h: HB.h },
      wood: 'White oak & poplar', skill: 'Intermediate', time: '3 weekends',
      intro: [
        'Four posts, four rails, and no bed-rail brackets at the corners. Each corner is a castle joint: two slots cross in the top of the post, the end rail drops in notch-up, and the side rail drops over it notch-down. The half-laps lock the rails to each other and the post walls lock them sideways, so gravity and a single cross-bolt per corner do the rest.',
        'The rails run ' + P.ext + '" past every post, and the headboard cap rail repeats the overhang, which gives the bed its long, low line. The mattress sits ' + P.pocket + '" down inside the rails on ' + P.slat.n + ' poplar slats, and the whole frame comes apart with a wrench for moving.'
      ],
      needs: ['A tall fence for the castle slots (drawn under Shop Aids)', 'Hardware from the Hard-to-Find Hardware box'],
      check: { min_wall: 0.25 }
    },
    materials: { wood: { color: '#efcf78' }, poplar: { color: '#f4ec9e' }, hardware: { color: '#c5c2be' } },
    sections: [{ id: 'frame', title: 'Bed Frame' }, { id: 'head', title: 'Headboard' }],
    parts: [post, endRail, sideRail, cleat, spine, legs, slats, hbPost, botRail, topRail, hbSlat],
    cutlist_notes: ['Posts are listed at finished size; each is two face-glued layers.', 'Rails and posts: mill the rail stock first, then saw the castle slots to the actual rail thickness.'],
    joints,
    bores,
    hardware: [
      { item: '5/16"-18 × 8" hex bolts, washers', qty: 4, source: 'Hardware store', note: 'Cross-bolt down through each castle lap.' },
      { item: '5/16"-18 cross dowels (barrel nuts), 10 mm', qty: 4, source: 'Woodworking supplier', note: 'In the post, 1-1/2" below the slot bottom.' },
      { item: '1" walnut face plugs', qty: 4, source: 'Woodworking supplier', note: 'Friction-fit caps in the 1" × 5/8" counterbore over each bolt head and washer.' },
      { item: '3/8" × 6" bed bolts with barrel nuts', qty: 4, source: 'Woodworking supplier', note: 'Headboard to side rail ends; nuts 2-1/4" from the rail end, outside the corner post.', part: '3' },
      { item: '3/8" white oak dowel, 12"', qty: 1, source: 'Woodworking supplier', note: 'Four pegs for the cap rail bridles.' },
      { item: 'Hook-in center rail brackets', qty: '2 pr.', source: 'Woodworking supplier', part: '5' },
      { item: 'Adjustable center support legs', qty: 2, source: 'Woodworking supplier', part: '6' },
      { item: '#8 × 2" flat-head screws', qty: 24, source: 'Hardware store', note: 'Cleats to rails.' },
      { item: '#8 × 1-1/2" flat-head screws', qty: 36, source: 'Hardware store', note: 'Slats, leg plates.' }
    ],
    details: [
      {
        title: 'Castle Joint Section', sub: 'cut through the post center, along the side rail', w: 11, h: 16,
        items: [
          { rect: [0, 0, P.post, Zb], fill: 'wood', part: '1' },
          { poly: [[-3, Zb], [half - t / 2, Zb], [half - t / 2, Zb + h / 2], [half + t / 2, Zb + h / 2], [half + t / 2, Zb], [P.post + 3, Zb], [P.post + 3, P.railTop], [-3, P.railTop]], fill: 'wood' },
          { rect: [half - t / 2, Zb, t, h / 2], fill: 'end', part: '2' },
          { rect: [half - 0.5, P.railTop - 0.625, 1, 0.625], fill: 'none' },
          { line: [half, P.railTop - 0.625, half, P.railTop - 0.625 - 8], dash: true },
          { rect: [half - 0.2, Zb - 1.7, 0.4, 0.4], fill: 'steel' },
          { line: [-3, Zb - 0.4, -3, P.railTop + 0.4], dash: true },
          { line: [P.post + 3, Zb - 0.4, P.post + 3, P.railTop + 0.4], dash: true },
          { dim: [P.post + 3, Zb, P.post + 3, Zb + h / 2], off: -0.8 },
          { dim: [P.post + 3, Zb + h / 2, P.post + 3, P.railTop], off: -0.8 },
          { dim: [P.post, 0, P.post, Zb], off: -0.8 },
          { dim: [half - t / 2, P.railTop, half + t / 2, P.railTop], off: 1.7 },
          { dim: [0, 0, P.post, 0], off: -0.9 },
          { dim: [0, Zb - 1.5, 0, Zb], off: 0.9 },
          { callout: [-1.6, 3, '1'], to: [0.5, 3] },
          { callout: [half, Zb - 3.8, '2'], to: [half - 0.2, Zb + 0.6] },
          { callout: [-4.6, P.railTop - 1.5, '3'], to: [-2.6, P.railTop - 1.5] },
          { text: [P.post + 1.2, Zb - 1.45, 'cross-bolt and barrel nut'], size: 0.62, anchor: 'start' },
          { text: [half - 0.6, P.railTop + 0.35, 'plug'], size: 0.62, anchor: 'end' }
        ]
      },
      {
        title: 'Headboard Bolts', sub: 'side view at the head end', w: 9, h: 9,
        items: [
          { rect: [-5, Zb, 5, h], fill: 'wood', part: '3' },
          { line: [-(P.ext + half - t / 2), Zb, -(P.ext + half - t / 2), Zb + h / 2], dash: true },
          { rect: [0, 0, P.post, 17], fill: 'wood', part: '8' },
          { line: [-P.ext, Zb - 1, -P.ext, P.railTop + 1], dash: true },
          { text: [-P.ext - 0.15, P.railTop + 1.3, 'corner post face'], size: 0.62, anchor: 'end' },
          { line: [P.post, Zb + 1.5, -2.5, Zb + 1.5], dash: true },
          { line: [P.post, P.railTop - 1.5, -2.5, P.railTop - 1.5], dash: true },
          { rect: [-2.45, Zb + 1.3, 0.4, 0.4], fill: 'steel' },
          { rect: [-2.45, P.railTop - 1.7, 0.4, 0.4], fill: 'steel' },
          { dim: [P.post, 0, P.post, Zb + 1.5], off: -0.8 },
          { dim: [P.post, Zb + 1.5, P.post, P.railTop - 1.5], off: -0.8 },
          { dim: [-2.25, P.railTop, 0, P.railTop], off: 0.8 },
          { dim: [-(P.ext + half - t / 2), Zb, 0, Zb], off: -0.8, text: 'lap starts ' + F(P.ext + half - t / 2) + '"' },
          { callout: [-6.4, Zb + h / 2, '3'], to: [-4.6, Zb + h / 2] },
          { callout: [P.post + 1.4, 16, '8'], to: [P.post - 0.4, 16] },
          { text: [-1.2, -1.4, 'two bed bolts per side'], size: 0.85 }
        ]
      }
    ],
    view: {
      explode: 100, start: 'Front right',
      hint: 'Hover a part for its size. Click to select it everywhere on the plan.',
      sections: [
        // close-ups: A through a slat at mid-length shows the pocket; B through a foot post shows the castle lap
        { id: 'A', cut: 'y', at: r(slats.instances[6].at[1] + P.slat.w / 2), keep: '+', box: [0, r(slats.instances[6].at[1]), 0, r(xcL + half + 12), 8, r(P.railTop + 0.5)],
          title: 'through a slat, left side, looking toward the head' },
        { id: 'B', cut: 'x', at: r(xcL), keep: '+', box: [0, 0, 0, r(Lend), r(ycF + half + 12), r(P.railTop + 0.5)],
          title: 'through the left foot post, looking in from the left' }
      ],
      dims: {
        A: [{ a: [r(xcL + t / 2 + P.cleat.t + 3), slatTop], b: [r(xcL + t / 2 + P.cleat.t + 3), P.railTop], off: -1 },
            { a: [r(xcL - t / 2), Zb], b: [r(xcL - t / 2), P.railTop], off: 1.2 },
            { a: [r(xcL + t / 2), slatBot - P.cleat.h], b: [r(xcL + t / 2 + P.cleat.t), slatBot - P.cleat.h], off: -1 }],
        B: [{ a: [0, Zb], b: [0, r(Zb + h / 2)], off: -1.2 }, { a: [0, r(Zb + h / 2)], b: [0, P.railTop], off: -1.2 }, { a: [0, 0], b: [0, Zb], off: -1.2 },
            { a: [r(-(ycF + half)), 0], b: [r(-(ycF - half)), 0], off: -1.2 }]
      }
    },
    steps: [
      { title: 'Glue up the posts', text: 'Face-glue pairs of 8/4 oak for the four corner posts {#1} and the two headboard posts {#8}. Joint and plane them square to ' + F(P.post) + '" after the glue cures.', parts: ['1', '8'] },
      { title: 'Cut the castle slots', text: 'Mill all four rails first and cut the slots to fit them. Lay out both slots ' + F(t) + '" wide and ' + F(h) + '" deep on each corner post {#1}. Saw the cheeks on the bandsaw against the tall fence (Shop Aids), then chop out the waste with a mortise chisel or rout it with a pattern bit. Pare the slot bottoms flat; the rails bear on them.', parts: ['1'] },
      { title: 'Notch the rails', text: 'Lay out the half-laps from the assembled post positions, not from the cut list: end rails {#2} notch from the top, side rails {#3} from the bottom. Sneak up on the fit so each rail drops in with hand pressure.', parts: ['2', '3'] },
      { title: 'Bore for the cross-bolts', text: 'Dry-assemble each corner. Counterbore 1" × 5/8" deep in the top of the side rail, then drill 5/16" straight down through both laps and 2-1/8" into the post with a long-series bit. Bore the 10 mm cross-dowel hole into the inside face of the post, ' + F(1.5) + '" below the slot bottom.', parts: ['2', '3'] },
      { title: 'Bore for the bed bolts', text: 'Clamp a headboard post {#8} to each side rail end. Drill 3/8" through the post and 2-1/2" into the rail end at ' + F(Zb + 1.5) + '" and ' + F(P.railTop - 1.5) + '" from the floor. Bore the barrel-nut holes into the inside face of the rail 2-1/4" from its end, clear of the corner post.', parts: ['3'] },
      { title: 'Cleats, spine and legs', text: 'Glue and screw the cleats {#4} to the side rails with their top edge ' + F(P.pocket + P.slat.t) + '" below the rail top. Hang the spine {#5} on its brackets and set the legs {#6} to just touch the floor.', parts: ['4', '5', '6'] },
      { title: 'Lay the slats', text: 'Space the slats {#7} ' + F(gap) + '" apart and drive one screw at each end.', parts: ['7'] },
      { title: 'Build the headboard', text: 'Mortise the posts {#8} and rails for the bottom rail {#9} and slats {#11}. Glue the bottom rail and slats into the posts, then drop the cap rail {#10} into the open slots and peg it.', parts: ['9', '11', '10'] },
      { title: 'Assemble the frame', text: 'Finish every part first: ease each edge 1/16" and apply hardwax oil. Stand the posts {#1}, drop in the end rails {#2}, then the side rails {#3}, and drive and tighten the four cross-bolts. Tap in the plugs. Expect the rail tops to sit up to 1/16" proud of the posts or below them as the seasons change; that is the rails moving across their height.', parts: ['1', '2', '3'],
        wrong: 'glue the castle laps. The bed has to come apart to move; the laps and cross-bolts hold it, and glue would also lock the rails against their seasonal movement.' },
      { title: 'Bolt on the headboard', text: 'Set the headboard against the side rail ends and drive two bed bolts per side into the barrel nuts.', parts: ['8'] }
    ],
    jigs: [{
      title: 'Tall Bandsaw Fence', sub: 'End View', w: 6, h: 8, for: ['1'],
      purpose: 'Holds each 3-1/2" corner post square to the table while you saw the castle slot cheeks. The base and braces sit behind the face, so the work side stays flat. Because every slot is centred in its post, one fence setting saws all sixteen cheeks.',
      use: 'Clamp the base to the table with the face parallel to the blade and ' + F(half - t / 2) + '" from the fence side of the blade. Saw a cheek, turn the post 180° against the fence, and saw the opposite cheek: both kerfs land in the waste and the slot comes out ' + F(t) + '" wide. Test on an offcut against a milled rail first. Stop each cut at the ' + F(h) + '" layout line.',
      parts: [{ name: 'Face', t: 0.75, w: 8, l: 24, material: 'Baltic birch' }, { name: 'Base', t: 0.75, w: 4, l: 24, material: 'Baltic birch' }, { name: 'Braces', qty: 3, t: 0.75, w: 3, l: 3, material: 'Baltic birch' }],
      items: [
        { line: [-4.5, 0, 5.5, 0] }, { text: [-4.4, -0.55, 'bandsaw table'], size: 0.6, anchor: 'start' },
        { rect: [0, 0, 0.75, 8] }, { rect: [0.75, 0, 4, 0.75] },
        { poly: [[0.75, 0.75], [3.75, 0.75], [0.75, 3.75]], fill: 'end' },
        { rect: [-P.post, 0, P.post, P.post], fill: 'none', dash: true },
        { text: [-half, half - 0.15, 'post'], size: 0.7 },
        { dim: [0, 0, 4.75, 0], off: -1.1 }, { dim: [0.75, 0, 0.75, 8], off: -4.8 },
        { text: [2.9, 3.3, 'braces: screw and glue'], size: 0.6, anchor: 'start' }
      ]
    }],
    story_sticks: [{
      title: 'Headboard Post Story Stick', axis: 'z', parts: ['2', '3', '8', '9', '10', '11'],
      marks: bedZ.map(z => ({ at: z, label: 'bed bolt' })),
      note: 'From the floor. Mark the two headboard posts {#8} together from this stick: rail lap, bed bolts, bottom rail, slat shoulders and the cap rail slot.'.replace('{#8}', '#8')
    }],
    finish: {
      title: 'hardwax oil', note: 'Finish every part before assembly so the joints never trap a dry face. Keep oil out of the castle slots and the mortises that get glue.',
      steps: [
        { step: 'Ease and sand', product: '120, then 150 grit', method: 'Ease every edge 1/16" with a block; sand with the grain', dry: '—' },
        { step: 'Raise the grain', product: 'Water', method: 'Wipe damp, let dry, knock down with 180 grit', dry: '1 h' },
        { step: 'First coat', product: 'Hardwax oil (natural)', method: 'Thin coat with a pad, wipe off all excess after 15 min', dry: '24 h' },
        { step: 'Second coat', product: 'Hardwax oil', method: 'Same, on the faces you see; buff with a white pad', dry: '24 h, full cure 2 weeks' }
      ]
    },
    revisions: [
      { rev: 'A', date: 'Oct 25 2026', summary: 'First issue',
        changes: [{ id: 'A1', summary: 'Initial design, full adversarial review of every joint', parts: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'] }] },
      { rev: 'B', date: 'Oct 25 2026', summary: 'Stiffer side rails',
        changes: [{ id: 'B1', summary: 'Rails thickened from 1-1/4" to 1-1/2"', parts: ['2', '3'], reason: 'The side rails carry the slat ends across 84-1/4" between post centers. Going to 1-1/2" (8/4 stock) adds 20% stiffness at the same height and matches the spine stock.' }] },
      { rev: 'C', date: 'Oct 25 2026', summary: 'Fixes from an independent review',
        changes: [
          { id: 'C1', summary: 'Rail overhang 2" → 3"', parts: ['2', '3', '8', '9', '10', '11'], reason: 'At a 2" overhang the head-end barrel nuts landed 1/4" inside the corner post, where the post tower covers the bore. Caught by an independent reviewer; the Rev A and B reviews had checked the nut against the lap but not against the post.' },
          { id: 'C2', summary: 'Castle slots cut with bandsaw and chisel', parts: ['1'], reason: 'A dado stack cannot cut a 6-1/2" deep slot.' },
          { id: 'C3', summary: 'Cross-bolt counterbore 1" × 5/8"', parts: ['3'], reason: 'The 5/8" counterbore could not take the washer or a socket.' },
          { id: 'C4', summary: 'Headboard slats get twin tenons', parts: ['11'], reason: 'A single 4"-wide, 3/8"-thick tenon is over 10 times its thickness.' },
          { id: 'C5', summary: 'Cleats 1" thick, longer screws', parts: ['4'], reason: 'More slat bearing and screws that reach 2× the part thickness.' },
          { id: 'C6', summary: 'Steps, hardware and intro completed', parts: ['3', '8', '10'], reason: 'No step bored the bed bolts or assembled the frame; the cap-rail pegs and long drill bit were not listed; the intro said there was no metal at the corners.' }
        ] },
      { rev: 'D', date: 'Oct 26 2026', summary: 'Shop paperwork from the plan-layout research',
        changes: [
          { id: 'D1', summary: 'Sections A–A and B–B, post pattern, headboard story stick', parts: ['1', '2', '3', '4', '7', '8', '9', '10', '11'], reason: 'The slat pocket and the castle laps are hidden in the outside views; the posts and headboard are marked out from full-size layouts instead of a tape.' },
          { id: 'D2', summary: 'Tall bandsaw fence drawn as a shop aid', parts: ['1'], reason: 'Step 2 relied on a tall fence the plan never showed.' },
          { id: 'D3', summary: 'Finishing schedule and a "Don\'t" at assembly', parts: ['1', '2', '3'], reason: 'The finish was one clause in step 9; gluing the castle laps is the mistake that ruins a knock-down bed.' }
        ] }
    ],
    review: [
      { rev: 'D', change: 'D1', verdict: 'fixed', mates: ['5'],
        checks: [
          { check: 'Model unchanged', evidence: 'The review worksheet against Rev C reports no change to any part, joint, bore or hardware line; the model check is 0 errors, 0 warnings. Rev D is paperwork only.', result: 'pass' },
          { check: 'Section A–A {#3} {#4} {#7}', evidence: 'Cut through the seventh slat, left side, 8" deep window. Hatched: side rail 1-1/2" × 6-1/2", cleat 1" × 1-1/2", slat 3/4". Pocket dimension reads 3" (rail top 14" − slat top 11"), matching PARAMS.pocket. The first draft showed the whole bed width with the head end rail and headboard behind it, which buried the pocket; it is now a close-up.', result: 'fixed' },
          { check: 'Section B–B {#1} {#2} {#3}', evidence: 'Cut on the left post centre line (x = 4-3/4"). The side rail is hatched full length with its lower half notched over the end rail, whose 1-1/2" cross-section fills the notch; the post shows only below the slot, because the plane runs down the side-rail slot. Laps 3-1/4" + 3-1/4" = rail height 6-1/2"; rail bottom 7-1/2" off the floor; post 3-1/2". All re-derived from PARAMS.', result: 'pass' },
          { check: 'Corner post pattern {#1}', evidence: 'Face view at 1:1: 14" long, slot 6-1/2" deep and 1-1/2" wide with 1" walls each side (1 + 1-1/2 + 1 = 3-1/2"). The second slot is the same size on the adjacent faces, so one pattern marks both. 3 letter pages.', result: 'pass' },
          { check: 'Headboard story stick {#2} {#3} {#8} {#9} {#10} {#11}', evidence: 'Marks from the floor: 7-1/2" and 14" rail lap, 9" and 12-1/2" bed bolts (Zb + 1-1/2, rail top − 1-1/2), 15" and 19" bottom rail, 18-1/4" and 43-3/4" slat tenon ends (3/4" tenons), 43" and 48" cap rail. Every mark matches the model and the Headboard Bolts detail.', result: 'pass' },
          { check: 'Cut list note on the castle slots', evidence: 'The Material List note still said to set the slot width "on the dado stack", contradicting C2 (a dado stack cannot reach 6-1/2"). Now: saw the slots to the actual rail thickness.', result: 'fixed' }
        ] },
      { rev: 'D', change: 'D2', verdict: 'fixed',
        checks: [
          { check: 'Fence works with the post on the table {#1}', evidence: 'First drawing put the braces and base on the work side, under the post. Redrawn with the base and braces behind the 8" face, so the 3-1/2" post bears on the table and a flat face.', result: 'fixed' },
          { check: 'Fence setting gives a 1-1/2" slot', evidence: 'The first text said to move the fence by the rail thickness plus the kerf, which makes the slot one kerf too wide (the offset should be thickness minus kerf). Because the slots are centred, the fence now sits 1" from the blade and the post is turned 180° for the second cheek: kerfs at 1" from each face, slot 3-1/2 − 2 = 1-1/2", kerfs in the waste.', result: 'fixed' }
        ] },
      { rev: 'D', change: 'D3', verdict: 'pass', mates: ['8'],
        checks: [
          { check: 'Finishing schedule matches the steps', evidence: 'Step 9 already finishes every part with hardwax oil before assembly; the schedule spells out ease and sand, raise the grain, two coats and the 2-week cure, and keeps oil out of the slots and glued mortises (J7, J8, J9 are glued).', result: 'pass' },
          { check: '"Don\'t" at assembly {#1} {#2} {#3}', evidence: 'J1 is listed with glue: false and a cross-bolt; the bed knocks down for moving and the rails must move across their height (C6). The panel says not to glue the laps.', result: 'pass' }
        ] },
      { rev: 'A', change: 'A1', verdict: 'fixed', mates: ['1', '2', '3', '4', '7', '8'],
        checks: [
          { check: 'Castle corner {#1} {#2} {#3}: rails fit the slots', evidence: 'Slot width and notch width both come from the rail thickness; each rail gives up half its height at the crossing. Model check: no interference, contact on all three parts at all four corners.', result: 'pass' },
          { check: 'Castle towers strong enough', evidence: 'Towers are (3-1/2 − 1-1/4) ÷ 2 = 1-1/8" square. Rule of thumb is at least a quarter of the post (7/8"). They are long grain and get captured by the rails once assembled.', result: 'pass' },
          { check: 'Load path at the post', evidence: 'Side rail bears on the end rail lap, which bears on the slot bottom, which is solid post below. No load hangs on a tower.', result: 'pass' },
          { check: 'Posts intrude on the mattress {#1} {#4}', evidence: 'The model check failed the first draft: both cleats ran 1-1/8" into the posts at every corner. The cause is the castle geometry itself. The rails pass through the post centers, so the inner quarter of every post stands inside the rail line, and a mattress sized to the rail faces would hit four posts. Fixed by measuring the 60-3/4" × 80-3/4" opening between post faces and running the cleats between the posts.', result: 'fixed' },
          { check: 'Mattress side gap', evidence: 'With the opening set by the posts, the side rails stand 1-1/2" off the mattress at mid-length. The mattress sits 3" below the rail tops, so the gap is hidden, and the posts still locate it at the corners.', result: 'pass' },
          { check: 'Headboard to side rails {#8} {#3}', evidence: 'The first draft had one bed bolt per side, both at the same height. Two bolts on one horizontal line act as a hinge, and only a 2" strip of the post bears on the rail end below it. Changed to two bolts per side, 3-1/2" apart.', result: 'fixed' },
          { check: 'Bed bolts stay in full-height wood', evidence: 'The side rail is half height through the lap, which starts 3-1/8" from the rail end. Bolts run 2-1/2" in and the barrel nuts sit 2-1/4" in.', result: 'pass' },
          { check: 'Slats bear on cleats {#7} {#4}', evidence: 'Slats are 1/4" shorter than the space between side rails, leaving 5/8" of bearing on each 3/4" cleat. The first and last slats start 2-1/8" past the post faces, so none of them hits a post. The spine carries the middle at the same height (model check: contact).', result: 'pass' },
          { check: 'Headboard tenons {#9} {#11}', evidence: 'Bottom rail tenons are 1/2" on 1-1/4" stock (40%), 1-1/2" deep in a 3-1/2" post. Slat tenons are 3/8" on 3/4" stock (50%), leaving 7/16" mortise walls. Model check: every tenon fully seated.', result: 'pass' },
          { check: 'Wood movement', evidence: 'No glued cross-grain joint wider than 6". The headboard slats sit in separate mortises with gaps between them, so the panel never acts as one wide board.', result: 'pass' }
        ] },
      { rev: 'B', change: 'B1', verdict: 'pass', mates: ['1', '4', '5', '7', '8'],
        checks: [
          { check: 'Post slots {#1} follow the rail', evidence: 'Slot width is the rail thickness, so both slots went to 1-1/2". Towers are now (3-1/2 − 1-1/2) ÷ 2 = 1" square, still above the 7/8" minimum. The model check raised no castle-tower warning.', result: 'pass' },
          { check: 'Half-lap notches {#2} {#3}', evidence: 'Notch width follows the mating rail (1-1/2"); depth stays 3-1/4". Model check: no interference and full contact at all four corners.', result: 'pass' },
          { check: 'Rail lengths and overall size', evidence: 'Post centers do not move, because the opening is set by the post faces. End rails stay 71-3/4" and side rails 91-3/4"; overall stays 71-3/4" W × 95-1/4" D × 48" H, and the title block agrees with the model.', result: 'pass' },
          { check: 'Slats {#7}', evidence: 'Each rail face moved 1/8" inward, so the slats get 1/4" shorter, to 62-1/2". Bearing on the cleats stays 5/8".', result: 'pass' },
          { check: 'Cleats {#4}', evidence: 'Cleats moved 1/8" inward with the rail faces and keep their length (80-1/2"). Model check: still in contact with the side rails, still clear of the posts.', result: 'pass' },
          { check: 'Spine {#5}', evidence: 'End rail faces moved 1/8" inward at each end, so the spine gets 1/4" shorter, to 82-1/2", keeping the 1/8" bracket gap. Model check: the gap is within what the brackets bridge.', result: 'pass' },
          { check: 'Headboard bolts {#8} {#3}', evidence: 'The lap now starts 3" from the rail end instead of 3-1/8". The barrel nuts at 2-1/4" still sit 3/4" clear of it.', result: 'pass' },
          { check: 'Cross-bolt length', evidence: 'The bolt passes 3-1/4" + 3-1/4" of lap and 1-1/2" into the post, so the 8" bolt is still right.', result: 'pass' },
          { check: 'Stock', evidence: 'Rails now come from 8/4 stock instead of 6/4. The cutting diagrams and board-foot table regroup from the model.', result: 'pass' }
        ] },
      { rev: 'C', change: 'C1', verdict: 'flag', mates: ['1', '4', '5', '7'],
        checks: [
          { check: 'Barrel nuts clear the corner post {#3} {#1}', evidence: 'The corner post\'s back face is now 3" from the rail end. The nuts sit 2-1/4" in, which leaves about 9/16" of rail face between a 10 mm bore and the post, and the lap starts 4" in.', result: 'fixed' },
          { check: 'Rail and cap rail lengths {#2} {#3} {#10}', evidence: 'End rails and cap rail 73-3/4", side rails 93-3/4". The side rail blank (94-3/4" with milling allowance) still fits an 8\' board.', result: 'pass' },
          { check: 'Mattress opening, slats, cleats, spine {#7} {#4} {#5}', evidence: 'Post centers moved 1" outward together, so the distance between posts is unchanged and none of these parts changed size.', result: 'pass' },
          { check: 'Headboard {#8} {#9} {#11}', evidence: 'The headboard moved 1" back with the side rail ends. The bottom rail and slats keep their sizes; the bed bolts still run 2-1/2" into full-height rail.', result: 'pass' },
          { check: 'Overall size', evidence: 'Now 73-3/4" W × 97-1/4" D × 48" H. The title block agrees with the model.', result: 'pass' },
          { check: 'Gap between mattress and headboard', evidence: 'The mattress stops 3/8" short of the head posts, and the headboard face is 3-1/2" + 3" behind that, so there is a 6-7/8" gap at the head (5-7/8" at Rev B). Pillows can drop into it. Options: accept it, add a ledge shelf on the headboard, or redesign the head end. This is a design choice for you.', result: 'flag' }
        ] },
      { rev: 'C', change: 'C2', verdict: 'fixed',
        checks: [{ check: 'Slots can be cut with the listed tools {#1}', evidence: 'A dado stack reaches about 2-1/2"; the slots are 6-1/2" deep. Step 2 now saws the cheeks on the bandsaw and chops or routs the waste, and the tool list says so.', result: 'fixed' }] },
      { rev: 'C', change: 'C3', verdict: 'fixed',
        checks: [{ check: 'Counterbore and bolt length', evidence: 'A 1" × 5/8" counterbore takes a 5/16" washer (up to 7/8") and a socket. From the counterbore bottom at 13-3/8" the 8" bolt reaches 5-3/8", which is 5/8" past the cross-dowel center at 6". Step 4 and the hardware list now give the counterbore size.', result: 'fixed' }] },
      { rev: 'C', change: 'C4', verdict: 'fixed', mates: ['9', '10'],
        checks: [{ check: 'Twin tenons {#11} in {#9} {#10}', evidence: 'Two 3/8" × 1-1/2" × 3/4" tenons per end (4× their thickness), with 1" between them. Model check: all seated, mortise walls 7/16".', result: 'fixed' }] },
      { rev: 'C', change: 'C5', verdict: 'fixed', mates: ['3', '7'],
        checks: [
          { check: 'Slat bearing {#7} on {#4}', evidence: 'Cleats are now 1" thick, so each slat end bears on 7/8" instead of 5/8". Model check: the cleats still touch the rails and still clear the posts.', result: 'fixed' },
          { check: 'Screw lengths', evidence: 'Cleat screws are #8 × 2": through 1" of cleat and 1" into the 1-1/2" rail. Slat screws are #8 × 1-1/2" (2× the slat), piloted to protect the cleat edge.', result: 'fixed' }
        ] },
      { rev: 'C', change: 'C6', verdict: 'flag',
        checks: [
          { check: 'Every operation has a step', evidence: 'Added steps for boring the bed bolts and for assembling the frame (cross-bolts, plugs). The long-series bit and cap-rail pegs are now in the tool and hardware lists.', result: 'fixed' },
          { check: 'Intro matches the hardware', evidence: 'Changed to "no bed-rail brackets at the corners", since each corner has a cross-bolt.', result: 'fixed' },
          { check: 'Seasonal movement at the castle stack', evidence: 'Two stacked 3-1/4" rail halves cross a post whose height does not move, so the rail tops can sit about 1/16" proud or low with the seasons. The assembly step now says so.', result: 'pass' },
          { check: 'Spine brackets {#5}', evidence: 'The plan assumes a 1/8" hook-in gap and about 2-3/4" of overlap between the spine and end rail faces. Check this against the brackets you buy before cutting the spine to length.', result: 'flag' }
        ] }
    ]
  };
};
module.exports.PARAMS = PARAMS;
