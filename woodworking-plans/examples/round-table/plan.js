/* Round side table: the shaped-part example. A turned round top with a round-over, legs tapered on
 * their two inside faces with chamfered feet, and aprons with an arched bottom edge, joined by
 * mortise and tenon. Every curve and angle is in the model, so the drawings, 3D view and patterns
 * show it true and the check fits it.
 *   node scripts/build_plan.js examples/round-table/plan.js --check
 */
const PARAMS = { rev: 'A', dia: 30, h: 26, base: 18, leg: 1.75, tip: 1, taperTop: 19, top: 0.75, apronH: 4.5, apronT: 0.75, inset: 0.25, rise: 1.25, ease: 0.25 };

module.exports = function build(P = PARAMS, J = require('../../scripts/joints.js')) {
  const legH = P.h - P.top, off = (P.dia - P.base) / 2, az = legH - P.apronH;
  // legs: modeled for the front-left corner (inside faces +x and +y), mirrored to the others
  const runOut = (P.leg - P.tip) / P.taperTop;           // taper per inch of height, carried 1" below the floor
  const taper = { cutout: [[P.tip - runOut, -1], [P.leg + 1, -1], [P.leg + 1, P.taperTop], [P.leg, P.taperTop]] };
  const leg = { id: '1', name: 'Legs', section: 'base', qty: 4, t: P.leg, w: P.leg, l: legH, material: 'Walnut', stock: 'solid',
    note: 'Taper the two inside faces from ' + P.tip + '" at the foot to full width ' + P.taperTop + '" up.',
    shape: [{ box: [0, 0, 0, P.leg, P.leg, legH] },
      Object.assign({ axis: 'y', tool: 'bandsaw' }, taper),
      { axis: 'x', tool: 'bandsaw', cutout: taper.cutout.map(([u, v]) => [u, v]) },
      { chamfer: 0.125, edges: 'bottom' }],
    instances: [
      { at: [off, off, 0] },
      { at: [off + P.base, off, 0], mirror: 'x' },
      { at: [off, off + P.base, 0], mirror: 'y' },
      { at: [off + P.base, off + P.base, 0], rot: 180 }] };
  const span = P.base - 2 * P.leg;
  // aprons shoulder to shoulder, with a shallow arch cut up into the bottom edge
  const arch = (len) => [[0, 0], [0, P.apronH], [len, P.apronH], [len, 0], { arc: [0, 0], rise: -P.rise }];
  const front = { id: '2', name: 'Front & Back Aprons', section: 'base', qty: 2, t: P.apronT, w: P.apronH, material: 'Walnut', stock: 'solid',
    shape: [{ box: [0, 0, 0, span, P.apronT, P.apronH] }, { outline: arch(span), axis: 'y', tool: 'bandsaw' }],
    instances: [P.inset, P.base - P.inset - P.apronT].map(y => ({ at: [off + P.leg, off + y, az] })) };
  const side = { id: '3', name: 'Side Aprons', section: 'base', qty: 2, t: P.apronT, w: P.apronH, material: 'Walnut', stock: 'solid',
    shape: [{ box: [0, 0, 0, P.apronT, span, P.apronH] }, { outline: arch(span), axis: 'x', tool: 'bandsaw' }],
    instances: [P.inset, P.base - P.inset - P.apronT].map(x => ({ at: [off + x, off + P.leg, az] })) };
  // the top: turned to a circle with a round-over on its upper edge (a lathe profile, radius by height)
  const R = P.dia / 2;
  const top = { id: '4', name: 'Top', section: 'top', qty: 1, t: P.top, w: P.dia, l: P.dia, material: 'Walnut', stock: 'solid', pattern: false,
    note: 'Glue up a ' + P.dia + '" square, cut the circle on a trammel, then round over the top edge.',
    shape: [{ box: [0, 0, 0, P.dia, P.dia, P.top] },
      { lathe: [[R, 0], [R, P.top - P.ease], { arc: [R - P.ease, P.top], center: [R - P.ease, P.top - P.ease] }], axis: 'z', tool: 'router' }],
    instances: [{ at: [0, 0, legH] }] };

  const joints = [
    J.mortiseTenon({ rail: front, hosts: [leg], length: 0.75, title: 'Front and back aprons to legs' }),
    J.mortiseTenon({ rail: side, hosts: [leg], length: 0.75, title: 'Side aprons to legs' }),
    J.joint('buttons', [top, front, side, leg], { title: 'Top to aprons', fasteners: 'Eight wood buttons in a 1/4" groove', note: 'Buttons let the top move across its grain.' })
  ];

  return {
    meta: { series: 'Shop Plan', plan_no: '015', rev: P.rev, date: 'Oct 2026', title: 'Round Side Table', subtitle: 'Tapered legs, arched aprons, round top',
      overall: { w: P.dia, d: P.dia, h: P.h }, wood: 'Walnut', skill: 'Intermediate', time: '2 weekends',
      intro: ['A small round table with a light, tapered base. The curves are cut on the bandsaw and cleaned up with a spokeshave; the top is cut round on a router trammel.'],
      needs: ['Bandsaw', 'Router with a 1/4" round-over bit and a trammel'] },
    materials: { wood: { color: '#e8c27a' } },
    sections: [{ id: 'base', title: 'Base' }, { id: 'top', title: 'Top' }],
    parts: [leg, front, side, top],
    joints,
    hardware: [{ item: '#8 × 1-1/4" screws', qty: 8, source: 'Hardware store', note: 'For the buttons.' }],
    steps: [
      { title: 'Mortise and taper the legs', text: 'Cut the mortises in the legs {#1}, then saw the tapers on the two inside faces and plane them smooth. Chamfer the feet.', parts: ['1'] },
      { title: 'Tenon and shape the aprons', text: 'Cut the tenons on the aprons {#2} {#3}, then lay out the arch with a bent batten, bandsaw it and fair it with a spokeshave.', parts: ['2', '3'] },
      { title: 'Make the top', text: 'Cut the top {#4} round on a trammel, round over the top edge and fasten it with buttons.', parts: ['4'] }
    ],
    revisions: [{ rev: 'A', date: 'Oct 27 2026', summary: 'First issue', changes: [{ id: 'A1', summary: 'Initial design', parts: ['1', '2', '3', '4'] }] }],
    review: [{ rev: 'A', change: 'A1', verdict: 'pass', mates: [],
      checks: [{ check: 'Apron tenons {#2} {#3} in {#1}', evidence: 'Tenons 3/4" long, clear of the tapers (they start 19" up, below the aprons at ' + az + '"). Model check clean.', result: 'pass' }] }]
  };
};
module.exports.PARAMS = PARAMS;
