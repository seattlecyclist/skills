/* joints.js — joint helpers for plan.js generators.
 *
 * Model each part as one plain box per piece, placed where it sits in the assembly (instances with
 * `at`, `rot`). Then call one helper per connection. The helper cuts the slots, notches and
 * housings, adds the tenons, updates the part's length when tenons change it, and returns the
 * joint record for `plan.joints`, sized by references/joinery.md unless you pass a size.
 *
 *   module.exports = function build(P = PARAMS, J) {      // build_plan.js passes J
 *     ...parts as plain boxes...
 *     const joints = [
 *       J.castle({ post, lower: endRail, upper: sideRail, fasteners: 'One 5/16" cross-bolt' }),
 *       J.mortiseTenon({ rail: apron, hosts: [leg] }),
 *       J.dado({ host: side, guest: shelf }),
 *       J.joint('screwed', [cleat, rail], { fasteners: '#8 x 2" screws' })
 *     ];
 *
 * Every helper takes the part objects themselves, not ids. Helpers change parts in place, so call
 * each once, after every part has its base box and instances. Helpers throw when the copies of one
 * part would need different cuts; split those copies into separate parts.
 */
(function () {
  'use strict';
  const C = require('./plan-core.js');
  const L = C.parseLen, EPS = 1e-6;
  const r5 = v => Math.round(v * 1e5) / 1e5;

  // ---- geometry ----
  const boxes = p => (p.shape || []).filter(s => s.box && s.role !== 'tenon').map(s => C.toAABB(s.box.map(L)));
  function union(list) {
    if (!list.length) return null;
    const u = { min: list[0].min.slice(), max: list[0].max.slice() };
    for (const a of list) for (let i = 0; i < 3; i++) { u.min[i] = Math.min(u.min[i], a.min[i]); u.max[i] = Math.max(u.max[i], a.max[i]); }
    return u;
  }
  function base(p) {
    const b = union(boxes(p));
    if (!b) throw new Error('joints.js: part #' + p.id + ' needs a { box } in its shape before a joint helper is called.');
    return b;
  }
  const insts = p => (p.instances && p.instances.length ? p.instances : [{ at: [0, 0, 0] }]).map(i => ({ at: (i.at || [0, 0, 0]).map(L), rot: i.rot || 0, mirror: i.mirror }));
  const world = (p, I) => C.xformAABB(base(p), I);
  function rot(pt, deg) {
    const d = ((deg % 360) + 360) % 360, [x, y, z] = pt;
    return d === 0 ? [x, y, z] : d === 90 ? [-y, x, z] : d === 180 ? [-x, -y, z] : [y, -x, z];
  }
  // world box -> part coordinates of instance I (inverse of plan-core's mirror, rot, then at)
  function toLocal(a, I) {
    const xs = [], ys = [];
    for (const x of [a.min[0], a.max[0]]) for (const y of [a.min[1], a.max[1]]) {
      let p = rot([x - I.at[0], y - I.at[1], 0], -(I.rot || 0));
      if (I.mirror === 'x') p[0] = -p[0];
      if (I.mirror === 'y') p[1] = -p[1];
      xs.push(p[0]); ys.push(p[1]);
    }
    return { min: [Math.min(...xs), Math.min(...ys), a.min[2] - I.at[2]], max: [Math.max(...xs), Math.max(...ys), a.max[2] - I.at[2]] };
  }
  // local axis that world axis a maps to under rot
  const localAxis = (a, I) => (a === 2 || ((I.rot || 0) % 180 === 0)) ? a : 1 - a;
  const inter = C.inter;
  // a cut that reaches a face of the part runs 1" past it, so the slot opens cleanly
  function open(host, c, pad) {
    const out = [];
    for (let i = 0; i < 3; i++) {
      const lo = c.min[i] <= host.min[i] + EPS ? host.min[i] - pad : c.min[i];
      const hi = c.max[i] >= host.max[i] - EPS ? host.max[i] + pad : c.max[i];
      out.push([lo, hi]);
    }
    return [out[0][0], out[1][0], out[2][0], out[0][1] - out[0][0], out[1][1] - out[1][0], out[2][1] - out[2][0]].map(r5);
  }
  const key = b => b.map(v => v.toFixed(4)).join(',');
  // add cuts to a part; every copy of the part must want the same set
  function addCuts(p, perInst, extra) {
    const sets = perInst.map(list => [...new Set(list.map(key))].sort().join('|'));
    if (sets.some(s => s !== sets[0])) throw new Error('joints.js: the copies of #' + p.id + ' ' + p.name + ' would need different cuts. Give the copies that face the other way `mirror: \'x\'` (or \'y\'), so the cut lands on the same face of every copy, or split them into separate parts.');
    const have = new Set((p.shape || []).filter(s => s.cut).map(s => key(s.cut.map(L))));
    const added = [];
    for (const c of perInst[0] || []) {
      if (have.has(key(c))) continue;
      have.add(key(c));
      const s = Object.assign({ cut: c }, extra || {});
      p.shape.push(s); added.push(s);
    }
    return added;
  }
  // pairs of overlapping copies: [{hi, gi, H, G, ov}]
  function crossings(host, guest) {
    const out = [];
    insts(host).forEach((H, hi) => insts(guest).forEach((G, gi) => {
      const ov = inter(world(host, H), world(guest, G));
      if (ov) out.push({ hi, gi, H, G, ov });
    }));
    return out;
  }
  // faces where two copies touch: [{H, G, axis, sign}] sign = +1 when the guest is on the host's + side
  function touches(host, guest) {
    const out = [];
    insts(host).forEach(H => insts(guest).forEach(G => {
      const a = world(host, H), b = world(guest, G);
      for (let ax = 0; ax < 3; ax++) {
        const o1 = (ax + 1) % 3, o2 = (ax + 2) % 3;
        const over = (i) => Math.min(a.max[i], b.max[i]) - Math.max(a.min[i], b.min[i]) > EPS;
        if (!over(o1) || !over(o2)) continue;
        if (Math.abs(a.max[ax] - b.min[ax]) < 1e-4) out.push({ H, G, a, b, axis: ax, sign: 1 });
        else if (Math.abs(b.max[ax] - a.min[ax]) < 1e-4) out.push({ H, G, a, b, axis: ax, sign: -1 });
      }
    }));
    return out;
  }
  const fmt = v => C.fmt(v);
  const sz = b => [0, 1, 2].map(i => b.max[i] - b.min[i]);
  // nearest common chisel or bit size, in inches
  const CHISEL = [1 / 4, 5 / 16, 3 / 8, 7 / 16, 1 / 2, 5 / 8, 3 / 4, 7 / 8, 1];
  const nearest = (v, list) => list.reduce((b, x) => Math.abs(x - v) < Math.abs(b - v) - 1e-9 ? x : b, list[0]);
  const snap16 = v => Math.round(v * 16) / 16;

  // ---- joint record ----
  function joint(type, parts, o) {
    o = o || {};
    const rec = { id: o.id, type, title: o.title || (type[0].toUpperCase() + type.slice(1)), parts: parts.map(p => String(p.id != null ? p.id : p)) };
    for (const k of ['glue', 'fasteners', 'gap', 'note', 'at', 'radius', 'explode']) if (o[k] !== undefined) rec[k] = o[k];
    if (rec.glue === undefined) rec.glue = false;
    if (rec.id === undefined) delete rec.id;
    return rec;
  }

  // ---- housings: a slot, dado or notch the size of the part that sits in it ----
  function housing(host, guest, o) {
    o = o || {};
    const X = crossings(host, guest);
    if (!X.length) throw new Error('joints.js: #' + guest.id + ' does not overlap #' + host.id + ', so there is nothing to cut. Place the guest where it sits in the finished joint.');
    const hb = base(host), per = insts(host).map(() => []);
    for (const x of X) per[x.hi].push(open(hb, toLocal(x.ov, x.H), 1));
    return addCuts(host, per, o.tool ? { tool: o.tool } : null);
  }

  // ---- half-lap at every crossing: `lower` keeps its bottom half, `upper` its top half ----
  function lapCuts(lower, upper, axis) {
    const X = crossings(lower, upper);
    if (!X.length) throw new Error('joints.js: #' + lower.id + ' and #' + upper.id + ' do not cross.');
    const lb = base(lower), ub = base(upper);
    const pl = insts(lower).map(() => []), pu = insts(upper).map(() => []);
    for (const x of X) {
      const mid = (x.ov.min[axis] + x.ov.max[axis]) / 2;
      const top = { min: x.ov.min.slice(), max: x.ov.max.slice() }, bot = { min: x.ov.min.slice(), max: x.ov.max.slice() };
      top.min[axis] = mid; bot.max[axis] = mid;
      pl[x.hi].push(open(lb, toLocal(top, x.H), 1));
      const UG = insts(upper)[x.gi];
      pu[x.gi].push(open(ub, toLocal(bot, UG), 1));
    }
    addCuts(lower, pl); addCuts(upper, pu);
    return X;
  }
  function halfLap(o) {
    const X = lapCuts(o.lower, o.upper, o.axis != null ? o.axis : 2);
    const d = sz(X[0].ov)[o.axis != null ? o.axis : 2] / 2;
    return joint('half-lap', [o.lower, o.upper], Object.assign({ title: 'Half-lap', note: 'Each part cut ' + fmt(d) + ' deep at the crossing.' }, o));
  }

  // ---- castle: two crossing slots in a post top, rails half-lapped inside it ----
  function castle(o) {
    const { post, lower, upper } = o;
    const X = lapCuts(lower, upper, 2);
    housing(post, lower, { tool: o.tool || 'bandsaw' });
    housing(post, upper, { tool: o.tool || 'bandsaw' });
    const s = sz(X[0].ov), lt = Math.min(...sz(base(lower))), ut = Math.min(...sz(base(upper)));
    const note = 'Slots ' + (Math.abs(lt - ut) < EPS ? fmt(lt) : fmt(lt) + ' and ' + fmt(ut)) + ' wide by ' + fmt(s[2]) + ' deep in the post. ' +
      'The lower rail is notched ' + fmt(s[2] / 2) + ' from the top, the upper rail ' + fmt(s[2] / 2) + ' from the bottom, so the rail tops finish flush.';
    return joint('castle', [post, lower, upper], Object.assign({ title: 'Castle joint', note }, o));
  }

  // ---- bridle: an open slot in a post end that a rail drops into ----
  function bridle(o) {
    const cuts = housing(o.post, o.rail, { tool: o.tool });
    const c = cuts[0] && cuts[0].cut;
    return joint('bridle', [o.rail, o.post], Object.assign({ title: 'Bridle', glue: true, note: c ? 'Open slot ' + fmt(Math.min(c[3], c[4])) + ' wide.' : undefined }, o));
  }

  // ---- dado, groove or rabbet: the guest runs `depth` into the host, which is cut to take it ----
  // Model the guest touching the host's face (shoulder to shoulder); the helper lengthens it.
  function inset(type, o) {
    const { host, guest } = o;
    const T = touches(host, guest);
    if (!T.length) throw new Error('joints.js: ' + type + ': #' + guest.id + ' must touch a face of #' + host.id + '.');
    const ht = Math.min(...sz(base(host)));
    const depth = o.depth != null ? L(o.depth) : type === 'rabbet' ? snap16(ht / 2) : host.stock === 'sheet' ? (ht >= 0.7 ? 0.375 : snap16(ht / 3)) : snap16(ht / 3);
    // grow the guest's base box into the host at each touching end (same ends for every copy)
    const ends = new Set();
    for (const t of T) { const la = localAxis(t.axis, t.G); const lb = toLocal(t.b, t.G), lh = toLocal(t.a, t.G); ends.add(la + (lh.max[la] <= lb.min[la] + 1e-4 ? '-' : '+')); }
    const gb = guest.shape.find(s => s.box && s.role !== 'tenon');
    const before = sz(base(guest)), la = lenAxis(guest);
    const b = gb.box.map(L);
    for (const e of ends) { const a = +e[0]; if (e[1] === '-') b[a] -= depth; b[a + 3] += depth; }
    gb.box = b.map(r5);
    // the cut-list field of each grown axis follows the model: length, or width for a panel in a groove
    const after = sz(base(guest));
    for (const a of new Set([...ends].map(e => +e[0]))) {
      if (a === la) guest.l = r5(after[a]);
      else if (guest.w != null && Math.abs(L(guest.w) - before[a]) < 1e-4) guest.w = r5(after[a]);
    }
    housing(host, guest, { tool: o.tool });
    return joint(type, [guest, host], Object.assign({ title: type[0].toUpperCase() + type.slice(1), glue: true, note: fmt(depth) + ' deep.' }, o));
  }
  // local axis of the part's length: the axis whose base extent best matches p.l (longest if unset)
  function lenAxis(p, b) {
    const s = sz(b || base(p)), l = p.l != null ? L(p.l) : Math.max(...s);
    let best = 0; for (let a = 1; a < 3; a++) if (Math.abs(s[a] - l) < Math.abs(s[best] - l) - 1e-9) best = a;
    return best;
  }

  // ---- mortise and tenon: tenons on the rail ends that touch each host ----
  // Model the rail shoulder to shoulder, touching the hosts. Defaults follow joinery.md: thickness
  // about a third of the stock (nearest chisel), length 1-1/2" or 2/3 of the host, edge shoulders
  // 1/2" on rails 3" and wider (1/4" below), twin tenons when one would be over 5x its thickness.
  function mortiseTenon(o) {
    const rail = o.rail, hosts = o.hosts || [o.host];
    const rb = base(rail), rs = sz(rb), la = lenAxis(rail, rb);
    const cross = [0, 1, 2].filter(a => a !== la);
    const thAx = o.thickAxis != null ? o.thickAxis : (rs[cross[0]] <= rs[cross[1]] ? cross[0] : cross[1]);
    const wAx = cross.find(a => a !== thAx);
    const T = rs[thAx], W = rs[wAx];
    const th = o.thick != null ? L(o.thick) : nearest(T / 3, CHISEL);
    const edge = o.shoulder != null ? L(o.shoulder) : (W >= 3 ? 0.5 : 0.25);
    const ends = {};
    for (const h of hosts) for (const t of touches(h, rail)) {
      const a = localAxis(t.axis, t.G);
      if (a !== la) continue;
      const lh = toLocal(t.a, t.G);
      const side = lh.max[a] <= rb.min[a] + 1e-4 ? '-' : '+';
      const depth = sz(t.a)[t.axis];
      ends[side] = ends[side] || { host: h, depth };
      ends[side].depth = Math.min(ends[side].depth, depth);
    }
    const sides = Object.keys(ends).sort();
    if (!sides.length) throw new Error('joints.js: mortiseTenon: #' + rail.id + ' must touch ' + hosts.map(h => '#' + h.id).join(' or ') + ' end-on. Model the rail shoulder to shoulder.');
    const tw = W - 2 * edge;
    const twin = o.twin === false ? null : o.twin != null ? L(o.twin) : (tw > 5 * th + EPS ? r5((tw - Math.max(2 * th, 0.5)) / 2) : null);
    const spans = twin ? [[rb.min[wAx] + edge, twin], [rb.max[wAx] - edge - twin, twin]] : [[rb.min[wAx] + edge, tw]];
    const off = o.offset != null ? L(o.offset) : (T - th) / 2;
    let lenUsed = 0;
    for (const side of sides) {
      const len = o.length != null ? L(o.length) : Math.max(0.75, Math.min(1.5, snap16(ends[side].depth * 2 / 3)));
      lenUsed = Math.max(lenUsed, len);
      for (const [w0, ww] of spans) {
        const b = [0, 0, 0, 0, 0, 0];
        b[la] = side === '-' ? rb.min[la] - len : rb.max[la]; b[la + 3] = len;
        b[thAx] = rb.min[thAx] + off; b[thAx + 3] = th;
        b[wAx] = w0; b[wAx + 3] = ww;
        rail.shape.push({ box: b.map(r5), role: 'tenon' });
      }
    }
    const all = union(rail.shape.filter(s => s.box).map(s => C.toAABB(s.box.map(L))));
    rail.l = r5(sz(all)[la]);
    const desc = (twin ? 'Twin ' : '') + fmt(th) + ' × ' + fmt(twin || tw) + ' × ' + fmt(lenUsed) + ' tenon' + (twin ? 's at each end' : sides.length > 1 ? 's' : '');
    return joint(o.type || 'mortise-tenon', [rail].concat(hosts), Object.assign({ title: 'Mortise and tenon', glue: true, fasteners: 'Glue', note: desc + '.' }, o));
  }

  const api = {
    joint, castle, halfLap, bridle, mortiseTenon, housing: (o) => { housing(o.host, o.guest, o); return joint(o.type || 'housed', [o.guest, o.host], o); },
    dado: o => inset('dado', o), groove: o => inset('groove', o), rabbet: o => inset('rabbet', o),
    screwed: (parts, o) => joint('screwed', parts, o), rests: (parts, o) => joint('rests', parts, o),
    // geometry helpers for plan code
    world: (p, i) => world(p, insts(p)[i || 0]), base
  };
  module.exports = api;
})();
