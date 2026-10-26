/* Skeleton plan: a small side table, with every part of the schema used once. Copy this file to
 * start a new plan. Model parts as plain boxes where they sit; the J helpers cut the joinery.
 *   node scripts/build_plan.js examples/skeleton/plan.js --check
 */
const PARAMS = { rev: 'A', w: 20, d: 16, h: 24, leg: 1.75, top: 0.75, apronH: 4, apronT: 0.75, inset: 0.25, overhang: 1 };

module.exports = function build(P = PARAMS, J = require('../../scripts/joints.js')) {
  const legH = P.h - P.top, W = P.w - 2 * P.overhang, D = P.d - 2 * P.overhang;   // leg footprint
  const az = legH - P.apronH, ay = P.inset, ax = P.inset;                          // aprons sit flush with the leg tops
  const corner = [[0, 0], [W - P.leg, 0], [0, D - P.leg], [W - P.leg, D - P.leg]];
  const leg = { id: '1', name: 'Legs', section: 'table', qty: 4, t: P.leg, w: P.leg, l: legH, material: 'Cherry', stock: 'solid',
    shape: [{ box: [0, 0, 0, P.leg, P.leg, legH] }], instances: corner.map(([x, y]) => ({ at: [x + P.overhang, y + P.overhang, 0] })) };
  // aprons shoulder to shoulder between the legs; J.mortiseTenon adds the tenons and sets l
  const front = { id: '2', name: 'Front & Back Aprons', section: 'table', qty: 2, t: P.apronT, w: P.apronH, material: 'Cherry', stock: 'solid',
    shape: [{ box: [0, 0, 0, W - 2 * P.leg, P.apronT, P.apronH] }],
    instances: [ay, D - ay - P.apronT].map(y => ({ at: [P.overhang + P.leg, P.overhang + y, az] })) };
  const side = { id: '3', name: 'Side Aprons', section: 'table', qty: 2, t: P.apronT, w: P.apronH, material: 'Cherry', stock: 'solid',
    shape: [{ box: [0, 0, 0, P.apronT, D - 2 * P.leg, P.apronH] }],
    instances: [ax, W - ax - P.apronT].map(x => ({ at: [P.overhang + x, P.overhang + P.leg, az] })) };
  const top = { id: '4', name: 'Top', section: 'table', qty: 1, t: P.top, w: P.d, l: P.w, material: 'Cherry', stock: 'solid', glueup: 1,
    note: 'Glue up from three boards; attach with buttons so it can move.', shape: [{ box: [0, 0, 0, P.w, P.d, P.top] }], instances: [{ at: [0, 0, legH] }] };

  const joints = [
    J.mortiseTenon({ rail: front, hosts: [leg], length: 0.75, title: 'Front and back aprons to legs' }),   // 3/4" so the tenons miss each other in the leg
    J.mortiseTenon({ rail: side, hosts: [leg], length: 0.75, title: 'Side aprons to legs' }),
    J.joint('buttons', [top, front, side, leg], { title: 'Top to aprons', fasteners: 'Eight wood buttons in a 1/4" groove', note: 'Buttons let the 16" top move across its width.' })
  ];
  const bores = [
    // a 1/4" peg through each front leg face and the upper front tenon (x, z inside that tenon)
    { id: 'B1', joint: 'J1', kind: 'peg', label: '1/4" peg', d: 0.25, depth: 1.25,
      copies: [P.overhang + P.leg - 0.375, P.w - P.overhang - P.leg + 0.375].map(x => ({ at: [x, P.overhang, az + 3.125], dir: '+y' })) }
  ];

  return {
    meta: { series: 'Shop Plan', plan_no: '001', rev: P.rev, date: 'Oct 2026', title: 'Side Table', subtitle: 'Mortise and tenon base, buttoned top',
      overall: { w: P.w, d: P.d, h: P.h }, wood: 'Cherry', skill: 'Beginner', time: '1 weekend',
      intro: ['Four legs, four aprons and a top: the first table every woodworker should build.'], needs: ['Router or mortiser for the mortises'] },
    materials: { wood: { color: '#efcf78' } },
    sections: [{ id: 'table', title: 'Table' }],
    parts: [leg, front, side, top],
    joints, bores,
    hardware: [{ item: '#8 × 1-1/4" screws', qty: 8, source: 'Hardware store', note: 'For the buttons.', draw: { shape: 'screw', d: 0.164, len: 1.25 } }, { item: '1/4" cherry dowel, 12"', qty: 1, source: 'Woodworking supplier', note: 'Two pegs.' }],
    steps: [
      { title: 'Mill and mortise the legs', text: 'Mill the legs {#1} square and cut the mortises on the two inside faces.', parts: ['1'] },
      { title: 'Tenon the aprons', text: 'Cut the twin tenons on the aprons {#2} {#3} and fit each to its mortise. Glue the base and peg the front tenons.', parts: ['2', '3'] },
      { title: 'Attach the top', text: 'Fasten the top {#4} with buttons.', parts: ['4'],
        wrong: 'glue the top to the aprons or screw it tight through round holes; the 16" top moves about 1/8" across the grain each year.' }
    ],
    // the shop paperwork beyond the drawings: a section, a shop aid, a full-size pattern, a story stick, a finish
    view: { sections: [{ id: 'A', cut: 'y', at: P.d / 2, title: 'Through the side aprons, looking toward the back' }] },
    jigs: [{ title: 'Button Blank', sub: 'Shop Aid', w: 2, h: 1.5, for: ['4'],
      purpose: 'Make all eight buttons from one 3/4" x 1-1/4" strip: rabbet one end, then crosscut 1" buttons.',
      parts: [{ name: 'Button strip', qty: 1, t: 0.75, w: 1.25, l: 12, material: 'Cherry offcut' }],
      items: [{ rect: [0, 0, 1, 0.75] }, { rect: [1, 0.375, 0.375, 0.375], fill: 'none', dash: true }, { dim: [0, 0, 1, 0], off: -0.35 }, { dim: [1, 0.375, 1.375, 0.375], off: -0.35, text: '3/8"' }, { text: [0.5, 1.1, 'rabbet 3/8" x 3/8"'], size: 0.8 }] }],
    details: [{ title: 'Button', pattern: true, items: [{ poly: [[0, 0], [1, 0], [1, 0.375], [1.375, 0.375], [1.375, 0.75], [0, 0.75]] }, { dim: [0, 0, 1.375, 0], off: -0.4 }, { dim: [0, 0, 0, 0.75], off: 0.4 }, { grain: [0.15, 0.55, 0.85, 0.55] }] }],
    story_sticks: [{ title: 'Leg Story Stick', axis: 'z', parts: ['1', '2'] }],
    finish: { note: 'Cherry darkens fast in sunlight; finish all faces so the top moves evenly.', steps: [
      { step: 'Sand', product: '150 then 180 grit', method: 'Random-orbit sander', dry: '—' },
      { step: 'Oil', product: 'Boiled linseed oil', method: 'Wipe on, wipe off', dry: '24 h' },
      { step: 'Topcoat', product: 'Wipe-on poly, satin', method: 'Three thin coats, 320 between', dry: '4 h' }] },
    revisions: [{ rev: 'A', date: 'Oct 25 2026', summary: 'First issue', changes: [{ id: 'A1', summary: 'Initial design', parts: ['1', '2', '3', '4'] }] }],
    review: [{ rev: 'A', change: 'A1', verdict: 'pass', mates: [],
      checks: [{ check: 'Apron tenons {#2} {#3} in {#1}', evidence: '1/4" twin tenons on 3/4" aprons (33%), 3/4" long, so the front and side tenons stop 1/4" apart inside each 1-3/4" leg. Model check: all seated, no interference.', result: 'pass' }] }]
  };
};
module.exports.PARAMS = PARAMS;
