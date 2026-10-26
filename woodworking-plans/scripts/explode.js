/* explode.js — automatic explode vectors, from how each joint goes together.
 *
 * Parts are taken in build order (their order in plan.parts). Each copy moves away from the
 * earlier parts it joins, along the direction it would come out of the joint:
 *   - up out of a slot, notch or dado it sits in (the way the cut opens);
 *   - off a tenon, or pulling its own tenons out, along the tenon;
 *   - away from a face it is screwed to, rests on, or is bracketed to.
 * It moves far enough to clear the joint (the slot depth, the tenon length) plus a pad, and starts
 * from the furthest of the parts it joins, so layers stack: posts, lower rails, upper rails, slats.
 * A part held from both sides (a rail between two legs, a slat between two rails) instead pushes
 * those parts apart, when nothing else has been stacked on them yet; otherwise it lifts out.
 * The first part of each later section starts from its own offset, so assemblies stay together.
 *
 * Instances that already have `explode` keep it; set every explode by hand only to override.
 */
(function () {
  'use strict';
  const C = require('./plan-core.js');
  const EPS = 1e-6;

  function auto(plan) {
    const M = C.normalize(plan);
    const raw = (plan.parts || []).map(p => (p.instances || []).map(i => i.explode));
    const joints = (plan.joints || []).map(j => ({ parts: (j.parts || []).map(String), gap: j.gap != null ? C.parseLen(j.gap) : 0 }));
    const joined = (a, b) => joints.filter(j => j.parts.includes(a) && j.parts.includes(b));
    const all = [];
    for (const p of M.parts) if (p.shape && p.shape.length) for (const I of p.instances) if (I.bbox) all.push({ p, I, E: null, deps: new Set(), spread: new Set(), fixed: !!raw[p.index][I.index] });
    if (!all.length) return plan;
    const W = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
    for (const r of all) for (let a = 0; a < 3; a++) { W.min[a] = Math.min(W.min[a], r.I.bbox.min[a]); W.max[a] = Math.max(W.max[a], r.I.bbox.max[a]); }
    const size = Math.max(...[0, 1, 2].map(a => W.max[a] - W.min[a]));
    const pad = Math.round(Math.min(8, Math.max(2, size * 0.06)) * 4) / 4;
    const mid = [0, 1, 2].map(a => (W.min[a] + W.max[a]) / 2);
    const ctr = b => [0, 1, 2].map(a => (b.min[a] + b.max[a]) / 2);
    const body = (p, I) => { const bs = p.local.adds.filter(a => !p.local.tenons.includes(a)).map(a => C.xformAABB(a, I)); return bs.reduce((u, a) => ({ min: u.min.map((v, i) => Math.min(v, a.min[i])), max: u.max.map((v, i) => Math.max(v, a.max[i])) }), { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] }); };
    const unit = (a, s) => { const v = [0, 0, 0]; v[a] = s; return v; };
    // the way out of cut c in instance A: the axis where it opens through one face only (prefer up)
    function opening(A, c) {
      const b = A.bbox;
      for (const a of [2, 1, 0]) {
        const lo = c.min[a] <= b.min[a] + EPS, hi = c.max[a] >= b.max[a] - EPS;
        if (lo !== hi) return { a, s: hi ? 1 : -1 };
      }
      return null;
    }
    // how B comes off A: { v: unit vector B moves along, eng: travel to clear the joint }
    function relation(Ap, A, Bp, B, gap) {
      for (const [X, Y, Yp, sg] of [[A, B, Bp, 1], [B, A, Ap, -1]]) {
        // Y sits in a cut of X
        for (const c of X.cuts) {
          const ov = C.inter(Y.bbox, c); if (!ov) continue;
          const o = opening(X, c); if (!o) continue;
          return { v: unit(o.a, o.s * sg), eng: ov.max[o.a] - ov.min[o.a] };
        }
        // a tenon of Y inside X
        const yb = body(Yp, Y);
        for (const T of Y.tenons) {
          if (!C.inter(T, X.bbox)) continue;
          for (let a = 0; a < 3; a++) {
            if (T.max[a] <= yb.min[a] + EPS) return { v: unit(a, sg), eng: T.max[a] - T.min[a] };
            if (T.min[a] >= yb.max[a] - EPS) return { v: unit(a, -sg), eng: T.max[a] - T.min[a] };
          }
        }
      }
      // touching faces, or a hardware gap: move apart along the face normal
      let best = null;
      for (let a = 0; a < 3; a++) {
        const g = Math.max(A.bbox.min[a] - B.bbox.max[a], B.bbox.min[a] - A.bbox.max[a]);
        const others = [0, 1, 2].filter(i => i !== a).every(i => Math.min(A.bbox.max[i], B.bbox.max[i]) - Math.max(A.bbox.min[i], B.bbox.min[i]) > -EPS);
        if (g > -EPS && g <= gap + 1 / 64 && others && (!best || g < best.g)) best = { g, a };
      }
      if (!best) return null;
      const s = ctr(B.bbox)[best.a] > ctr(A.bbox)[best.a] ? 1 : -1;
      return { v: unit(best.a, s), eng: 0 };
    }
    const add = (u, v, k) => u.map((x, i) => x + v[i] * k);
    const firstSec = M.parts.length ? String(M.parts[0].section) : null;
    for (const r of all) {
      const rels = [];
      for (const q of all) {
        if (q === r) break;
        if (q.p === r.p) continue;
        const js = joined(q.p.id, r.p.id); if (!js.length) continue;
        const rel = relation(q.p, q.I, r.p, r.I, Math.max(...js.map(j => j.gap)));
        if (rel) rels.push(Object.assign(rel, { q }));
      }
      if (r.fixed) { r.E = r.I.explode.slice(); continue; }
      const out = [0, 1].map(a => { const d = ctr(r.I.bbox)[a] - mid[a]; return Math.abs(d) < 1 ? 0 : Math.sign(d); }).concat(0);
      const same = rels.filter(x => String(x.q.p.section) === String(r.p.section));
      if (!rels.length) { r.E = add([0, 0, 0], out, pad); continue; }
      if (!same.length && String(r.p.section) !== firstSec) {
        // first part of a later assembly: move the assembly off as a unit
        const s = rels.reduce((u, x) => add(u, x.v, 1), [0, 0, 0]);
        const a = [2, 1, 0].reduce((b, i) => Math.abs(s[i]) > Math.abs(s[b]) + EPS ? i : b, 2);
        r.E = add(add([0, 0, 0], out, pad), unit(a, Math.sign(s[a]) || 1), 2 * pad);
        continue;
      }
      const use = same.length ? same : rels;
      const s = use.reduce((u, x) => add(u, x.v, 1), [0, 0, 0]);
      const mean = use.reduce((u, x) => add(u, x.q.E, 1 / use.length), [0, 0, 0]);
      let a = [2, 1, 0].reduce((b, i) => Math.abs(s[i]) > Math.abs(s[b]) + EPS ? i : b, 2);
      if (Math.abs(s[a]) < EPS) {
        // held from both sides: spread those parts, unless something already stacks on them
        // (copies of one part count as one: the first copy spreads them, the rest reuse it)
        const free = use.every(x => !x.q.fixed && [...x.q.deps].every(id => id === r.p.id));
        const ax = use.find(x => x.v.some(Boolean)).v.findIndex(Boolean);
        if (free && ax === 2) {
          // held above and below (a slat between rails): rise off the lower parts, lift the upper ones clear
          const lo = use.filter(x => x.v[2] > 0), hi = use.filter(x => x.v[2] < 0);
          const z = Math.max(...lo.map(x => x.q.E[2] + x.eng)) + pad;
          r.E = lo.reduce((u, x) => add(u, x.q.E, 1 / lo.length), [0, 0, 0]); r.E[2] = z;
          for (const x of hi) if (!x.q.spread.has(r.p.id)) { x.q.E[2] = Math.max(x.q.E[2], z + x.eng + pad); x.q.spread.add(r.p.id); }
          for (const x of use) x.q.deps.add(r.p.id);
          continue;
        }
        if (free) {
          // held from both sides (a rail between legs): spread the legs apart
          for (const x of use) if (!x.q.spread.has(r.p.id)) { x.q.E = add(x.q.E, x.v, -(x.eng + pad)); x.q.spread.add(r.p.id); }
          r.E = use.reduce((u, x) => add(u, x.q.E, 1 / use.length), [0, 0, 0]);
          for (const x of use) x.q.deps.add(r.p.id);
          continue;
        }
        a = 2; s[2] = 1;
      }
      const dir = unit(a, Math.sign(s[a]));
      // clear every part it joins: the furthest one's travel plus that joint's engagement
      const from = Math.max(...use.map(x => x.q.E[a] * dir[a] + (x.v[a] === dir[a] ? x.eng : 0)));
      r.E = mean.slice(); r.E[a] = (from + pad) * dir[a];
      for (const x of use) x.q.deps.add(r.p.id);
    }
    const q = v => Math.sign(v) * Math.round(Math.abs(v) * 4) / 4;
    for (const r of all) {
      if (r.fixed) continue;
      const src = plan.parts[r.p.index];
      if (!src.instances || !src.instances.length) src.instances = [{ at: [0, 0, 0] }];
      src.instances[r.I.index].explode = r.E.map(v => q(v) || 0);
    }
    return plan;
  }
  // pairs of parts that still overlap at full explode (something passes through something)
  function collisions(plan) {
    const M = C.normalize(plan), out = [];
    const all = [];
    for (const p of M.parts) if (p.shape && p.shape.length) for (const I of p.instances) if (I.bbox) {
      const e = I.explode, sh = a => ({ min: a.min.map((v, i) => v + e[i]), max: a.max.map((v, i) => v + e[i]) });
      all.push({ p, I, bbox: sh(I.bbox), cells: I.solid.cells.map(sh) });
    }
    for (let i = 0; i < all.length; i++) for (let j = i + 1; j < all.length; j++) {
      const A = all[i], B = all[j];
      if (A.p === B.p || !C.inter(A.bbox, B.bbox)) continue;
      let v = 0;
      for (const a of A.cells) for (const b of B.cells) { const x = C.inter(a, b); if (x) v += C.vol(x); }
      if (v > 1e-3) out.push({ a: A.p.id + '#' + (A.I.index + 1), b: B.p.id + '#' + (B.I.index + 1), vol: v });
    }
    return out;
  }
  module.exports = { auto, collisions };
})();
