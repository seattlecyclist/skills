/* plan-core.js — shared geometry, formatting, packing and model checks for woodworking plans.
 * Runs in the browser (inlined into the plan page, exposes window.PlanCore) and in Node
 * (require('./plan-core.js')). One copy of the logic, so the page and the CLI never disagree.
 *
 * World axes: x = width (left to right), y = depth (front to back), z = height (up). Inches.
 */
(function (root) {
  'use strict';
  const EPS = 1e-6;

  // ---------- lengths and fractions ----------
  function parseLen(v) {
    if (v == null || v === '') return null;
    if (typeof v === 'number') return v;
    let s = String(v).trim().replace(/["”″]|in$/g, '').trim();
    if (/mm$/.test(s)) return parseFloat(s) / 25.4;
    if (/cm$/.test(s)) return parseFloat(s) / 2.54;
    let neg = s.startsWith('-') ? (s = s.slice(1), -1) : 1;
    const m = s.match(/^(\d+(?:\.\d+)?)?(?:[\s-]+)?(?:(\d+)\/(\d+))?$/);
    if (!m) { const f = parseFloat(s); if (isNaN(f)) throw new Error('Bad length: ' + v); return neg * f; }
    const whole = m[1] ? parseFloat(m[1]) : 0;
    const frac = m[2] ? parseInt(m[2], 10) / parseInt(m[3], 10) : 0;
    return neg * (whole + frac);
  }

  function gcd(a, b) { return b ? gcd(b, a % b) : a; }
  // -> {neg, whole, num, den} rounded to 1/denom
  function fracParts(x, denom) {
    denom = denom || 32;
    const neg = x < 0; x = Math.abs(x);
    let n = Math.round(x * denom), whole = Math.floor(n / denom), num = n - whole * denom, den = denom;
    if (num) { const g = gcd(num, den); num /= g; den /= g; }
    return { neg, whole, num, den, exact: Math.abs(n / denom - x) < 1e-4 };
  }
  // metric: the page sets PlanUnits = 'mm' (units toggle); checks and scripts always run in inches
  const metric = opts => opts.metric !== false && root.PlanUnits === 'mm';
  function mm(x) { const v = Math.round(x * 25.4 * 2) / 2; return (v % 1 ? v.toFixed(1) : String(v)); }
  // plain text: 23-3/4"
  function fmt(x, opts) {
    opts = opts || {};
    if (x == null) return '';
    if (metric(opts)) return mm(x) + (opts.unit === false ? '' : ' mm');
    const p = fracParts(x, opts.denom);
    let s = (p.neg ? '-' : '') + (p.whole || !p.num ? p.whole : '') + (p.num ? (p.whole ? '-' : '') + p.num + '/' + p.den : '');
    return s + (opts.unit === false ? '' : '"');
  }
  // html: 23<sup>3</sup>⁄<sub>4</sub>"  (magazine-style stacked fraction)
  function fmtHTML(x, opts) {
    opts = opts || {};
    if (x == null) return '';
    if (metric(opts)) return mm(x) + (opts.unit === false ? '' : '<span class="mmu"> mm</span>');
    const p = fracParts(x, opts.denom);
    let s = (p.neg ? '−' : '') + (p.whole || !p.num ? p.whole : '');
    if (p.num) s += '<span class="fr"><sup>' + p.num + '</sup>⁄<sub>' + p.den + '</sub></span>';
    return s + (opts.unit === false ? '' : '"');
  }

  // ---------- boxes ----------
  // box arrays are [x, y, z, dx, dy, dz]; aabb objects are {min:[3], max:[3]}
  const toAABB = b => ({ min: [b[0], b[1], b[2]], max: [b[0] + b[3], b[1] + b[4], b[2] + b[5]] });
  function rotPt(p, rot) {
    const r = ((rot || 0) % 360 + 360) % 360;
    const [x, y, z] = p;
    if (r === 0) return [x, y, z];
    if (r === 90) return [-y, x, z];
    if (r === 180) return [-x, -y, z];
    if (r === 270) return [y, -x, z];
    throw new Error('rot must be a multiple of 90, got ' + rot);
  }
  function xformAABB(a, inst) {
    const at = inst.at || [0, 0, 0];
    const xs = [], ys = [], zs = [];
    for (const cx of [a.min[0], a.max[0]]) for (const cy of [a.min[1], a.max[1]]) {
      let p = [cx, cy, 0];
      if (inst.mirror === 'x') p[0] = -p[0];
      if (inst.mirror === 'y') p[1] = -p[1];
      p = rotPt(p, inst.rot);
      xs.push(p[0]); ys.push(p[1]);
    }
    zs.push(a.min[2], a.max[2]);
    const r = v => Math.round(v * 1e6) / 1e6;
    return {
      min: [r(Math.min(...xs) + at[0]), r(Math.min(...ys) + at[1]), r(Math.min(...zs) + at[2])],
      max: [r(Math.max(...xs) + at[0]), r(Math.max(...ys) + at[1]), r(Math.max(...zs) + at[2])]
    };
  }
  // world axis that a local axis maps to under rot (mirror does not change axes)
  function axisAfterRot(localAxis, rot) {
    const r = ((rot || 0) % 360 + 360) % 360;
    if (localAxis === 2 || r === 0 || r === 180) return localAxis;
    return localAxis === 0 ? 1 : 0;
  }
  const vol = a => (a.max[0] - a.min[0]) * (a.max[1] - a.min[1]) * (a.max[2] - a.min[2]);
  function inter(a, b) {
    const min = [], max = [];
    for (let i = 0; i < 3; i++) {
      min[i] = Math.max(a.min[i], b.min[i]); max[i] = Math.min(a.max[i], b.max[i]);
      if (max[i] - min[i] <= EPS) return null;
    }
    return { min, max };
  }
  const inside = (p, a) => p[0] > a.min[0] && p[0] < a.max[0] && p[1] > a.min[1] && p[1] < a.max[1] && p[2] > a.min[2] && p[2] < a.max[2];
  function uniq(arr) {
    arr.sort((a, b) => a - b);
    const out = [];
    for (const v of arr) if (!out.length || v - out[out.length - 1] > 1e-5) out.push(v);
    return out;
  }

  // Decompose (union of adds) minus (union of cuts) into grid cells.
  // Returns {xs, ys, zs, occ(i,j,k) -> 0|1|2 (2 = tenon), cells:[{min,max,tenon}], bbox}
  function solid(adds, cuts, tenons) {
    cuts = cuts || []; tenons = tenons || [];
    const all = adds.concat(cuts);
    const xs = uniq(all.flatMap(a => [a.min[0], a.max[0]]));
    const ys = uniq(all.flatMap(a => [a.min[1], a.max[1]]));
    const zs = uniq(all.flatMap(a => [a.min[2], a.max[2]]));
    const nx = xs.length - 1, ny = ys.length - 1, nz = zs.length - 1;
    const grid = new Uint8Array(Math.max(0, nx * ny * nz));
    const cells = [];
    for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) for (let k = 0; k < nz; k++) {
      const c = [(xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2, (zs[k] + zs[k + 1]) / 2];
      if (!adds.some(a => inside(c, a)) || cuts.some(a => inside(c, a))) continue;
      const t = tenons.some(a => inside(c, a));
      grid[(i * ny + j) * nz + k] = t ? 2 : 1;
      cells.push({ min: [xs[i], ys[j], zs[k]], max: [xs[i + 1], ys[j + 1], zs[k + 1]], tenon: t });
    }
    const occ = (i, j, k) => (i < 0 || j < 0 || k < 0 || i >= nx || j >= ny || k >= nz) ? 0 : grid[(i * ny + j) * nz + k];
    let bbox = null;
    for (const c of cells) {
      if (!bbox) bbox = { min: c.min.slice(), max: c.max.slice() };
      else for (let a = 0; a < 3; a++) { bbox.min[a] = Math.min(bbox.min[a], c.min[a]); bbox.max[a] = Math.max(bbox.max[a], c.max[a]); }
    }
    return { xs, ys, zs, nx, ny, nz, occ, cells, bbox };
  }

  // Surface quads and crease edges for rendering. Quads: {n:[axis,sign], v:[4 pts]}. Edges: [[p,q],...]
  function surface(S) {
    const { xs, ys, zs, nx, ny, nz, occ } = S;
    const C = [xs, ys, zs];
    const quads = [];
    const filled = (i, j, k) => occ(i, j, k) > 0;
    for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) for (let k = 0; k < nz; k++) {
      if (!filled(i, j, k)) continue;
      const idx = [i, j, k];
      for (let a = 0; a < 3; a++) for (const s of [-1, 1]) {
        const nb = idx.slice(); nb[a] += s;
        if (filled(nb[0], nb[1], nb[2])) continue;
        const b = (a + 1) % 3, c = (a + 2) % 3;
        const pa = C[a][idx[a] + (s > 0 ? 1 : 0)];
        const b0 = C[b][idx[b]], b1 = C[b][idx[b] + 1], c0 = C[c][idx[c]], c1 = C[c][idx[c] + 1];
        const mk = (bv, cv) => { const p = [0, 0, 0]; p[a] = pa; p[b] = bv; p[c] = cv; return p; };
        const v = s > 0 ? [mk(b0, c0), mk(b1, c0), mk(b1, c1), mk(b0, c1)] : [mk(b0, c0), mk(b0, c1), mk(b1, c1), mk(b1, c0)];
        quads.push({ n: [a, s], v });
      }
    }
    // An edge segment along axis a at grid lines (b,c) is a crease when its 4 neighbouring cells
    // are filled in a pattern other than empty, full, or a flat pair.
    const edges = [];
    const N = [nx, ny, nz];
    for (let a = 0; a < 3; a++) {
      const b = (a + 1) % 3, c = (a + 2) % 3;
      for (let ia = 0; ia < N[a]; ia++) for (let ib = 0; ib <= N[b]; ib++) for (let ic = 0; ic <= N[c]; ic++) {
        const q = [];
        for (const [db, dc] of [[-1, -1], [0, -1], [0, 0], [-1, 0]]) {
          const id = [0, 0, 0]; id[a] = ia; id[b] = ib + db; id[c] = ic + dc;
          q.push(filled(id[0], id[1], id[2]) ? 1 : 0);
        }
        const n = q[0] + q[1] + q[2] + q[3];
        const crease = n === 1 || n === 3 || (n === 2 && q[0] === q[2]);
        if (!crease) continue;
        const p0 = [0, 0, 0], p1 = [0, 0, 0];
        p0[a] = C[a][ia]; p1[a] = C[a][ia + 1]; p0[b] = p1[b] = C[b][ib]; p0[c] = p1[c] = C[c][ic];
        edges.push([p0, p1]);
      }
    }
    // merge collinear consecutive segments
    const key = (e) => { const d = e[0].map((v, i) => e[1][i] - v); const a = d.findIndex(v => Math.abs(v) > EPS); return a + '|' + e[0].map((v, i) => i === a ? '' : v.toFixed(5)).join(','); };
    const groups = {};
    for (const e of edges) { const k = key(e); (groups[k] = groups[k] || []).push(e); }
    const merged = [];
    for (const k in groups) {
      const a = +k.split('|')[0];
      const g = groups[k].sort((p, q) => p[0][a] - q[0][a]);
      let cur = [g[0][0].slice(), g[0][1].slice()];
      for (let i = 1; i < g.length; i++) {
        if (Math.abs(g[i][0][a] - cur[1][a]) < EPS) cur[1] = g[i][1].slice();
        else { merged.push(cur); cur = [g[i][0].slice(), g[i][1].slice()]; }
      }
      merged.push(cur);
    }
    return { quads, edges: merged };
  }

  // ---------- model expansion ----------
  function num3(a) { return a ? a.map(parseLen) : [0, 0, 0]; }
  function normalize(plan) {
    const parts = (plan.parts || []).map((p, pi) => {
      const shape = p.shape || [];
      const loc = { adds: [], cuts: [], tenons: [] };
      for (const s of shape) {
        if (s.box) { const a = toAABB(s.box.map(parseLen)); loc.adds.push(a); if (s.role === 'tenon') loc.tenons.push(Object.assign(a, { through: !!s.through })); }
        if (s.cut) loc.cuts.push(Object.assign(toAABB(s.cut.map(parseLen)), s.tool ? { tool: s.tool } : {}));
      }
      const localSolid = solid(loc.adds, loc.cuts, loc.tenons);
      const instances = (p.instances && p.instances.length ? p.instances : [{ at: [0, 0, 0] }]).map((ins, ii) => {
        const inst = { at: num3(ins.at), rot: ins.rot || 0, mirror: ins.mirror, explode: num3(ins.explode), label: ins.label };
        const adds = loc.adds.map(a => xformAABB(a, inst));
        const cuts = loc.cuts.map(a => xformAABB(a, inst));
        const tenons = loc.tenons.map(a => Object.assign(xformAABB(a, inst), { through: a.through }));
        const S = solid(adds, cuts, tenons);
        return Object.assign(inst, { index: ii, adds, cuts, tenons, solid: S, bbox: S.bbox, key: p.id + '#' + ii });
      });
      return Object.assign({}, p, {
        index: pi,
        t: parseLen(p.t), w: parseLen(p.w), l: parseLen(p.l),
        qty: p.qty == null ? instances.length : p.qty,
        local: loc, localSolid, instances,
        isHardware: p.stock === 'hardware'
      });
    });
    const byId = {};
    for (const p of parts) byId[p.id] = p;
    return { plan, parts, byId };
  }

  // ---------- checks ----------
  function overlapVol(A, B, onlyTenonA) {
    if (!A.bbox || !B.bbox || !inter(A.bbox, B.bbox)) return 0;
    let v = 0;
    for (const a of A.cells) { if (onlyTenonA && !a.tenon) continue; for (const b of B.cells) { const x = inter(a, b); if (x) v += vol(x); } }
    return v;
  }
  function contactArea(A, B) {
    if (!A.bbox || !B.bbox) return 0;
    for (let i = 0; i < 3; i++) if (A.bbox.min[i] > B.bbox.max[i] + EPS || B.bbox.min[i] > A.bbox.max[i] + EPS) return 0;
    let area = 0;
    for (const a of A.cells) for (const b of B.cells) {
      for (let ax = 0; ax < 3; ax++) {
        if (Math.abs(a.max[ax] - b.min[ax]) > EPS && Math.abs(b.max[ax] - a.min[ax]) > EPS) continue;
        const o1 = (ax + 1) % 3, o2 = (ax + 2) % 3;
        const d1 = Math.min(a.max[o1], b.max[o1]) - Math.max(a.min[o1], b.min[o1]);
        const d2 = Math.min(a.max[o2], b.max[o2]) - Math.max(a.min[o2], b.min[o2]);
        if (d1 > EPS && d2 > EPS) area += d1 * d2;
      }
    }
    return area;
  }
  function gapBetween(A, B) {
    let d2 = 0;
    for (let i = 0; i < 3; i++) {
      const g = Math.max(0, A.bbox.min[i] - B.bbox.max[i], B.bbox.min[i] - A.bbox.max[i]);
      d2 += g * g;
    }
    return Math.sqrt(d2);
  }
  const fmtBox = a => '[' + a.min.map(v => fmt(v, { unit: false })).join(', ') + '] to [' + a.max.map(v => fmt(v, { unit: false })).join(', ') + ']';
  const AX = ['x', 'y', 'z'];

  function check(plan) {
    const M = normalize(plan);
    const out = { errors: [], warnings: [], passes: [], contacts: [], stats: {} };
    const said = new Set();
    const once = (list, code, msg, parts) => { if (said.has(code + msg)) return; said.add(code + msg); list.push({ code, msg, parts: parts || [] }); };
    const err = (code, msg, parts) => once(out.errors, code, msg, parts);
    const warn = (code, msg, parts) => once(out.warnings, code, msg, parts);
    const pass = (code, msg) => out.passes.push({ code, msg });
    const cfg = Object.assign({ min_wall: 0.25, tol: 1 / 64 }, (plan.meta && plan.meta.check) || {});
    const name = p => '#' + p.id + ' ' + p.name;

    // ids
    const seen = {};
    for (const p of M.parts) { if (seen[p.id]) err('dup-id', 'Part number ' + p.id + ' is used twice.', [p.id]); seen[p.id] = 1; }

    // 1. quantity and stock dimensions against the modeled geometry
    let dimsOK = 0;
    for (const p of M.parts) {
      if (!p.shape || !p.shape.length) { if (!p.isHardware) warn('no-geometry', name(p) + ' has no geometry, so nothing about its fit can be checked.', [p.id]); continue; }
      if (p.qty !== p.instances.length) err('qty', name(p) + ': cut list says ' + p.qty + ' but the model places ' + p.instances.length + '.', [p.id]);
      if (p.isHardware || p.t == null) continue;
      const b = p.localSolid.bbox; if (!b) { err('empty', name(p) + ' cuts remove all material.', [p.id]); continue; }
      const got = [0, 1, 2].map(i => b.max[i] - b.min[i]).sort((a, c) => a - c);
      const want = [p.t, p.w, p.l].sort((a, c) => a - c);
      const bad = got.some((g, i) => Math.abs(g - want[i]) > cfg.tol);
      if (bad) err('dims', name(p) + ': cut list says ' + [p.t, p.w, p.l].map(v => fmt(v)).join(' x ') + ' but the model measures ' + got.map(v => fmt(v)).join(' x ') + ' (sorted). One of them is wrong.', [p.id]);
      else dimsOK++;
    }
    pass('dims', dimsOK + ' parts: cut list T x W x L matches the modeled geometry.');

    // 2. thin walls left by cuts (slots, notches)
    for (const p of M.parts) {
      if (p.isHardware) continue;
      const min = p.min_wall != null ? parseLen(p.min_wall) : cfg.min_wall;
      for (const a of p.local.adds) for (const c of p.local.cuts) {
        if (!inter(a, c)) continue;
        for (let ax = 0; ax < 3; ax++) {
          const lo = c.min[ax] - a.min[ax], hi = a.max[ax] - c.max[ax];
          for (const w of [lo, hi]) if (w > EPS && w < min - EPS) warn('thin-wall', name(p) + ': a cut leaves a ' + fmt(w) + ' wall along ' + AX[ax] + ' (minimum ' + fmt(min) + ').', [p.id]);
        }
      }
    }

    // joint lookup
    const joints = (plan.joints || []).map((j, i) => Object.assign({ id: j.id || 'J' + (i + 1) }, j, { parts: (j.parts || []).map(String) }));
    const jointFor = (a, b) => joints.filter(j => j.parts.includes(a) && j.parts.includes(b));
    for (const j of joints) for (const id of j.parts) if (!M.byId[id]) err('joint-ref', 'Joint ' + j.id + ' names part ' + id + ', which does not exist.');

    // 3. interference, tenon seating, contacts
    const inst = [];
    for (const p of M.parts) if (p.shape && p.shape.length) for (const i of p.instances) inst.push({ p, i });
    const pairContact = {};
    const tenonSeated = new Map();
    let interf = 0;
    for (let x = 0; x < inst.length; x++) for (let y = x + 1; y < inst.length; y++) {
      const A = inst[x], B = inst[y];
      const SA = A.i.solid, SB = B.i.solid;
      if (!SA.bbox || !SB.bbox) continue;
      const ov = overlapVol(SA, SB);
      if (ov > 1e-5) {
        const tA = overlapVol(SA, SB, true), tB = overlapVol(SB, SA, true);
        const declared = A.p.id === B.p.id ? [] : jointFor(A.p.id, B.p.id);
        if ((tA + tB) > 1e-5 && !declared.length) err('tenon-undeclared', 'A tenon of ' + name(tA ? A.p : B.p) + ' enters ' + name(tA ? B.p : A.p) + ' but no joint between them is declared.', [A.p.id, B.p.id]);
        const resid = ov - tA - tB;
        if (resid > 1e-4) {
          interf++;
          const where = (() => { for (const a of SA.cells) for (const b of SB.cells) { const z = inter(a, b); if (z && !a.tenon && !b.tenon) return fmtBox(z); } return ''; })();
          err('interference', name(A.p) + ' (' + (A.i.index + 1) + ') and ' + name(B.p) + ' (' + (B.i.index + 1) + ') occupy the same ' + resid.toFixed(3) + ' cu in near ' + where + '. Two pieces of wood cannot be in one place: add a notch, a cut, or move one.', [A.p.id, B.p.id]);
        }
        // record tenon volume seated in other parts
        for (const [S, P, I, O] of [[SA, A.p, A.i, SB], [SB, B.p, B.i, SA]]) {
          for (let ti = 0; ti < I.tenons.length; ti++) {
            const T = I.tenons[ti];
            let v = 0; for (const c of S.cells) if (c.tenon && inside(c.min.map((m, k) => (m + c.max[k]) / 2), T)) for (const o of O.cells) { const z = inter(c, o); if (z) v += vol(z); }
            const k = I.key + '/' + ti; tenonSeated.set(k, (tenonSeated.get(k) || 0) + v);
            // mortise walls around the tenon in the mating part
            if (v > 0) for (const ob of (O === SB ? B.i : A.i).adds) {
              if (!inter(ob, T)) continue;
              for (let ax = 0; ax < 3; ax++) for (const w of [T.min[ax] - ob.min[ax], ob.max[ax] - T.max[ax]]) {
                if (w > EPS && w < 3 / 16 - EPS) warn('mortise-wall', 'The mortise for ' + name(P) + ' leaves a ' + fmt(w) + ' wall in ' + name(O === SB ? B.p : A.p) + ' along ' + AX[ax] + '.', [P.id]);
              }
            }
          }
        }
      }
      const area = contactArea(SA, SB);
      if (area > 1e-4 && A.p.id !== B.p.id) {
        const k = [A.p.id, B.p.id].sort().join('~');
        pairContact[k] = (pairContact[k] || 0) + area;
      }
    }
    if (!interf) pass('interference', 'No two parts occupy the same space (tenons excepted, inside declared joints).');

    // tenons fully seated
    for (const p of M.parts) for (const I of p.instances) I.tenons.forEach((T, ti) => {
      const S = I.solid;
      let tv = 0; for (const c of S.cells) if (c.tenon && inside(c.min.map((m, k) => (m + c.max[k]) / 2), T)) tv += vol(c);
      const seated = tenonSeated.get(I.key + '/' + ti) || 0;
      if (!T.through && seated < tv - 1e-4) err('tenon-seat', name(p) + ' (' + (I.index + 1) + '): ' + (tv - seated).toFixed(3) + ' of ' + tv.toFixed(3) + ' cu in of a tenon is outside any mating part. Either the tenon is too long, the mortise is in the wrong place, or the part is not where it should be.', [p.id]);
    });

    // 4. declared joints must touch (or bridge a declared hardware gap)
    const adj = {};
    const link = (a, b) => { (adj[a] = adj[a] || new Set()).add(b); (adj[b] = adj[b] || new Set()).add(a); };
    for (const k in pairContact) { const [a, b] = k.split('~'); link(a, b); out.contacts.push({ a, b, area: pairContact[k] }); }
    let jointsOK = 0;
    for (const j of joints) {
      const ps = j.parts.filter(id => M.byId[id] && M.byId[id].shape && M.byId[id].shape.length);
      if (j.gap != null) {
        const max = parseLen(j.gap);
        for (let a = 0; a < ps.length; a++) for (let b = a + 1; b < ps.length; b++) {
          let best = Infinity;
          for (const ia of M.byId[ps[a]].instances) for (const ib of M.byId[ps[b]].instances) best = Math.min(best, gapBetween(ia.solid, ib.solid));
          if (best > max + cfg.tol) err('joint-gap', 'Joint ' + j.id + ' (' + j.type + '): #' + ps[a] + ' and #' + ps[b] + ' are ' + fmt(best) + ' apart; the hardware bridges at most ' + fmt(max) + '.', [ps[a], ps[b]]);
          else link(ps[a], ps[b]);
        }
        jointsOK++;
        continue;
      }
      let ok = true;
      for (const id of ps) {
        const touches = ps.some(o => o !== id && pairContact[[id, o].sort().join('~')]);
        if (!touches && ps.length > 1) { ok = false; err('joint-no-contact', 'Joint ' + j.id + ' (' + j.type + ') says #' + id + ' ' + M.byId[id].name + ' joins ' + ps.filter(o => o !== id).map(o => '#' + o).join(', ') + ', but it touches none of them in the model.', [id]); }
      }
      if (ok) jointsOK++;
    }
    pass('joints', jointsOK + ' of ' + joints.length + ' declared joints have real contact (or a hardware gap within tolerance).');

    // 5. contacts nobody declared
    for (const c of out.contacts) {
      if (!jointFor(c.a, c.b).length) warn('undeclared-contact', '#' + c.a + ' ' + M.byId[c.a].name + ' touches #' + c.b + ' ' + M.byId[c.b].name + ' (' + c.area.toFixed(2) + ' sq in) but no joint says how they are held together.', [c.a, c.b]);
    }

    // 6. everything connects into one assembly
    const ids = M.parts.filter(p => p.shape && p.shape.length).map(p => p.id);
    const comp = []; const seenC = new Set();
    for (const id of ids) {
      if (seenC.has(id)) continue;
      const stack = [id], group = []; seenC.add(id);
      while (stack.length) { const c = stack.pop(); group.push(c); for (const n of (adj[c] || [])) if (!seenC.has(n)) { seenC.add(n); stack.push(n); } }
      comp.push(group);
    }
    if (comp.length > 1) {
      comp.sort((a, b) => b.length - a.length);
      for (const g of comp.slice(1)) err('floating', 'Not connected to the main assembly: ' + g.map(id => '#' + id + ' ' + M.byId[id].name).join(', ') + '.', g);
    } else if (ids.length) pass('connected', 'All ' + ids.length + ' modeled parts connect into one assembly.');

    // 7. parts with no joint at all
    for (const p of M.parts) if (!p.isHardware && p.shape && p.shape.length && !joints.some(j => j.parts.includes(p.id))) warn('no-joint', name(p) + ' is not part of any declared joint.', [p.id]);

    // 8. joint rules of thumb
    for (const j of joints) {
      if (j.type === 'mortise-tenon' || j.type === 'stub-tenon') {
        for (const id of j.parts) {
          const p = M.byId[id]; if (!p || !p.local.tenons.length || !p.t) continue;
          for (const T of p.local.tenons) {
            const d = [0, 1, 2].map(i => T.max[i] - T.min[i]).sort((a, b) => a - b);
            const r = d[0] / p.t;
            if (r < 0.25 || r > 0.55) warn('tenon-ratio', name(p) + ': tenon is ' + fmt(d[0]) + ' thick on ' + fmt(p.t) + ' stock (' + Math.round(r * 100) + '%). Aim for about a third to a half.', [id]);
          }
        }
      }
      if (j.type === 'castle') {
        for (const id of j.parts) {
          const p = M.byId[id]; if (!p || !p.local.cuts.length || p.local.cuts.length < 2) continue;
          const b = p.localSolid.bbox, wmin = Math.min(b.max[0] - b.min[0], b.max[1] - b.min[1]);
          for (const a of p.local.adds) for (const c of p.local.cuts) for (let ax = 0; ax < 2; ax++) {
            for (const w of [c.min[ax] - a.min[ax], a.max[ax] - c.max[ax]]) if (w > EPS && w < wmin / 4 - EPS) warn('castle-tower', name(p) + ': castle towers are ' + fmt(w) + ' on a ' + fmt(wmin) + ' post. Below a quarter of the post they snap off when a rail is dropped in.', [id]);
          }
        }
      }
    }

    // 9. cross-grain glue on wide solid parts
    for (const j of joints) {
      if (!j.glue) continue;
      const ps = j.parts.map(id => M.byId[id]).filter(Boolean);
      for (const p of ps) {
        if (p.stock !== 'solid' || !p.w || p.w < 6 || !p.instances.length) continue;
        const wAxis = localAxisOf(p, p.w), I = p.instances[0];
        if (wAxis < 0) continue;
        const wWorld = axisAfterRot(wAxis, I.rot);
        for (const q of ps) {
          if (q === p || q.stock !== 'solid' || !q.instances.length) continue;
          const lAxis = localAxisOf(q, q.l); if (lAxis < 0) continue;
          if (axisAfterRot(lAxis, q.instances[0].rot) === wWorld) warn('cross-grain', 'Joint ' + j.id + ' glues ' + name(q) + ' long grain across the ' + fmt(p.w) + ' width of ' + name(p) + '. Seasonal movement will split one of them; use a sliding joint, slotted screws, or glue only the middle.', [p.id, q.id]);
        }
      }
    }

    // 10. cut depth against the tool named for it (shape cut `tool`)
    const tools = Object.assign({}, TOOLS, (plan.meta && plan.meta.tools) || {});
    for (const p of M.parts) for (const c of p.local.cuts) {
      if (!c.tool) continue;
      const reach = tools[c.tool];
      if (reach == null) { warn('tool-unknown', name(p) + ': a cut names tool "' + c.tool + '", which has no depth limit. Add it to meta.tools as { "' + c.tool + '": depth }.', [p.id]); continue; }
      const d = cutDepth(p, c);
      if (d != null && d > parseLen(reach) + EPS) warn('tool-depth', name(p) + ': a ' + fmt(d) + ' deep cut is listed for the ' + c.tool + ', which reaches ' + fmt(parseLen(reach)) + '. Name a tool that can make it (bandsaw and chisel, router in passes) or make the cut shallower.', [p.id]);
    }

    // 11. bores and fasteners (plan.bores)
    boreChecks(M, plan, cfg, err, warn, pass);

    // 12. overall size
    const world = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
    for (const { i } of inst) if (i.bbox) for (let a = 0; a < 3; a++) { world.min[a] = Math.min(world.min[a], i.bbox.min[a]); world.max[a] = Math.max(world.max[a], i.bbox.max[a]); }
    const size = [0, 1, 2].map(a => world.max[a] - world.min[a]);
    out.stats.overall = size; out.stats.world = world;
    const ov = plan.meta && plan.meta.overall;
    if (ov && inst.length) {
      const want = [ov.w, ov.d, ov.h].map(parseLen);
      const labels = ['width', 'depth', 'height'];
      let ok = true;
      want.forEach((v, a) => { if (v != null && Math.abs(v - size[a]) > cfg.tol * 2) { ok = false; err('overall', 'Title block says overall ' + labels[a] + ' ' + fmt(v) + ' but the model measures ' + fmt(size[a]) + '.'); } });
      if (ok) pass('overall', 'Overall size in the title block matches the model: ' + size.map(v => fmt(v)).join(' W x ') .replace(/ W x ([^ ]+)$/, ' D x $1') + ' H.');
    }

    // 13. lumber stats
    out.stats.lumber = lumberStats(M);
    out.model = M;
    return out;
  }
  function localAxisOf(p, len) {
    const b = p.localSolid.bbox; if (!b) return -1;
    let best = -1, bd = Infinity;
    for (let a = 0; a < 3; a++) { const d = Math.abs(b.max[a] - b.min[a] - len); if (d < bd) { bd = d; best = a; } }
    return best;
  }

  // depth of a cut into the part: along the axes where it opens through exactly one face, the shortest
  function cutDepth(p, c) {
    const b = p.localSolid.bbox || p.local.adds[0]; if (!b) return null;
    let d = null;
    for (let a = 0; a < 3; a++) {
      const lo = c.min[a] <= b.min[a] + EPS, hi = c.max[a] >= b.max[a] - EPS;
      if (lo === hi) continue;
      const v = lo ? Math.min(c.max[a], b.max[a]) - b.min[a] : b.max[a] - Math.max(c.min[a], b.min[a]);
      d = d == null ? v : Math.min(d, v);
    }
    return d;
  }
  // tools a cut can name, with how deep each one cuts in one setup (override in meta.tools)
  const TOOLS = { 'dado': 2.5, 'tablesaw': 3, 'router': 1.5, 'router table': 1.5, 'mortiser': 4, 'bandsaw': Infinity, 'chisel': Infinity, 'handsaw': Infinity };

  // ---------- bores and fasteners ----------
  // plan.bores: [{ id, joint, kind: 'bolt'|'screw'|'cross-dowel'|'hole'|'peg', at, dir, d, depth, len,
  //   counterbore: {d, depth}, washer, nut, bit, access, through, copies: [{at, dir}] }]
  // `at` is the entry point on the surface, `dir` the drilling direction ('-z' or [0, 0, -1]).
  const DIRS = { '+x': [1, 0, 0], '-x': [-1, 0, 0], '+y': [0, 1, 0], '-y': [0, -1, 0], '+z': [0, 0, 1], '-z': [0, 0, -1] };
  function dirVec(d) {
    const v = typeof d === 'string' ? DIRS[d] : d;
    if (!v || v.filter(x => Math.abs(x) > EPS).length !== 1) throw new Error('Bore dir must be one of +x -x +y -y +z -z, got ' + JSON.stringify(d));
    return v.map(x => Math.sign(x));
  }
  function expandBores(plan) {
    const out = [];
    for (const b of plan.bores || []) {
      const copies = b.copies && b.copies.length ? b.copies : [{}];
      copies.forEach((c, i) => out.push(Object.assign({}, b, c, { copy: i, key: b.id + (copies.length > 1 ? '.' + (i + 1) : ''), at: num3(c.at || b.at), v: dirVec(c.dir || b.dir) })));
    }
    return out;
  }
  // which part copy holds point q (inside a box, not inside a cut)
  function holder(M, q) {
    for (const p of M.parts) {
      if (!p.shape || !p.shape.length) continue;
      for (const I of p.instances) {
        if (!I.bbox || !(q[0] > I.bbox.min[0] - EPS && q[0] < I.bbox.max[0] + EPS && q[1] > I.bbox.min[1] - EPS && q[1] < I.bbox.max[1] + EPS && q[2] > I.bbox.min[2] - EPS && q[2] < I.bbox.max[2] + EPS)) continue;
        if (I.adds.some(a => inside(q, a)) && !I.cuts.some(c => inside(q, c))) return { p, I };
      }
    }
    return null;
  }
  const along = (o, v, s) => [o[0] + v[0] * s, o[1] + v[1] * s, o[2] + v[2] * s];
  const perp = v => { const a = v.findIndex(x => x); return [0, 1, 2].filter(i => i !== a).flatMap(i => [-1, 1].map(sg => { const u = [0, 0, 0]; u[i] = sg; return u; })); };
  function boreChecks(M, plan, cfg, err0, warn0, pass) {
    const list = expandBores(plan);
    if (!list.length) return;
    // a problem repeated on many copies of one bore is reported once, with the count
    const seen = {}, order = [];
    let cur = null;
    const note = lvl => (code, msg, parts) => {
      const k = lvl + '|' + (cur ? cur.id : '') + '|' + code;
      if (!seen[k]) { seen[k] = { lvl, code, msg, parts: (parts || []).slice(), n: 0 }; order.push(k); }
      const s = seen[k]; s.n++;
      for (const q of parts || []) if (!s.parts.includes(q)) s.parts.push(q);
    };
    const err = note('err'), warn = note('warn');
    const step = 1 / 16, minWall = parseLen(cfg.bore_wall != null ? cfg.bore_wall : 1 / 8);
    const tools = Object.assign({}, TOOLS, (plan.meta && plan.meta.tools) || {});
    const tag = b => 'Bore ' + b.key + ' (' + (b.label || b.kind) + (b.joint ? ', ' + b.joint : '') + ')';
    let bad = 0;
    const path = {};
    for (const b of list) {
      cur = b;
      const d = parseLen(b.d), depth = parseLen(b.depth != null ? b.depth : b.len), r = d / 2;
      if (!(depth > 0)) { err('bore-depth', tag(b) + ' has no depth or len.'); bad++; continue; }
      // walk the bore and note which part holds each 1/16"
      const segs = [];
      for (let s = step / 2; s < depth; s += step) {
        const h = holder(M, along(b.at, b.v, s));
        const k = h ? h.I.key : null, last = segs[segs.length - 1];
        if (last && last.k === k) last.to = s + step / 2; else segs.push({ k, h, from: s - step / 2, to: s + step / 2 });
      }
      path[b.key] = segs;
      if (!segs[0].h) { err('bore-entry', tag(b) + ' starts in open air; `at` should be on the surface of the part it is drilled into.'); bad++; continue; }
      const wood = segs.filter(x => x.h);
      const air = segs.filter((x, i) => !x.h && i > 0);
      for (const a of air) {
        const end = a === segs[segs.length - 1];
        if (end && b.through) continue;
        if (a.to - a.from > 1 / 8 + EPS || end) { warn(end ? 'bore-exits' : 'bore-air', tag(b) + (end ? ' breaks out into open air ' + fmt(a.from) + ' from its entry.' : ' crosses ' + fmt(a.to - a.from) + ' of open air ' + fmt(a.from) + ' from its entry.'), wood.map(x => x.h.p.id)); bad++; }
      }
      // the entry must be reachable once the parts around it are assembled
      const access = b.access != null ? parseLen(b.access) : 1;
      const rr = Math.max(r, b.counterbore ? parseLen(b.counterbore.d) / 2 : 0);
      for (let s = step / 2; s < access; s += step) {
        const o = along(b.at, b.v, -s);
        const hit = [o].concat(perp(b.v).map(u => along(o, u, rr * 0.95))).map(q => holder(M, q)).find(Boolean);
        if (hit) { err('bore-blocked', tag(b) + ' is covered by #' + hit.p.id + ' ' + hit.p.name + ' ' + fmt(s) + ' outside its entry. The hole cannot be drilled, or the fastener fitted, once the parts are together.', [segs[0].h.p.id, hit.p.id]); bad++; break; }
      }
      // walls around the bore stay in the part
      for (const sg of wood) {
        let broke = false;
        for (let s = sg.from + step / 2; s < sg.to && !broke; s += step) {
          const o = along(b.at, b.v, s);
          for (const u of perp(b.v)) { const h = holder(M, along(o, u, r + minWall)); if (!h || h.I.key !== sg.k) { warn('bore-wall', tag(b) + ' leaves less than ' + fmt(minWall) + ' of wall in #' + sg.h.p.id + ' ' + sg.h.p.name + ' ' + fmt(s) + ' from its entry.', [sg.h.p.id]); bad++; broke = true; break; } }
        }
      }
      const bit = b.bit != null ? parseLen(b.bit) : (tools.drill != null ? parseLen(tools.drill) : null);
      if (bit != null && depth > bit + EPS) { warn('bit-reach', tag(b) + ' is ' + fmt(depth) + ' deep; the bit reaches ' + fmt(bit) + '. List a long-series bit.'); bad++; }
      if (b.counterbore && b.washer != null && parseLen(b.counterbore.d) < parseLen(b.washer) + 1 / 8 - EPS) { warn('counterbore', tag(b) + ': a ' + fmt(parseLen(b.counterbore.d)) + ' counterbore will not take a ' + fmt(parseLen(b.washer)) + ' washer and a socket (needs ' + fmt(parseLen(b.washer) + 1 / 8) + ').'); bad++; }
      if (b.kind === 'screw') {
        const len = parseLen(b.len), t1 = segs[0].to - segs[0].from;
        const woodLen = wood.reduce((v, x) => v + x.to - x.from, 0);
        if (len > woodLen + step) { err('fastener-exits', tag(b) + ': the ' + fmt(len) + ' screw has only ' + fmt(woodLen) + ' of wood; the tip comes through.', [segs[0].h.p.id]); bad++; }
        else if (!b.hardware && (len / t1 < 2 - 0.01 || len / t1 > 3.25)) { warn('screw-length', tag(b) + ': a ' + fmt(len) + ' screw through ' + fmt(t1) + ' of #' + segs[0].h.p.id + ' ' + segs[0].h.p.name + ' is ' + (len / t1).toFixed(1) + '× the part. Aim for 2× to 3×.', [segs[0].h.p.id]); bad++; }
      }
      if (b.kind === 'bolt' && b.len != null) {
        const seat = b.counterbore ? parseLen(b.counterbore.depth) : 0, tip = seat + parseLen(b.len);
        if (tip > depth + 1 / 32) { err('bore-shallow', tag(b) + ': the bolt reaches ' + fmt(tip) + ' from the entry but the hole is ' + fmt(depth) + ' deep.'); bad++; }
        if (b.nut) {
          const nuts = list.filter(n => n.id === b.nut);
          if (!nuts.length) { err('bore-ref', tag(b) + ' names nut ' + b.nut + ', which is not in plan.bores.'); bad++; continue; }
          // nearest nut copy: distance between the bolt axis and the nut axis
          let best = null;
          for (const n of nuts) {
            const a = b.v.findIndex(x => x), na = n.v.findIndex(x => x);
            const off = [0, 1, 2].filter(i => i !== a && i !== na).map(i => Math.abs(n.at[i] - b.at[i]));
            const miss = Math.hypot(...off);
            const sCenter = (n.at[a] - b.at[a]) * b.v[a];
            const nDepth = (b.at[na] - n.at[na]) * n.v[na];
            const nr = parseLen(n.d) / 2, nd = parseLen(n.depth);
            // how far the bolt axis is from lying inside this nut's hole
            const out = Math.max(0, miss - nr) + Math.max(0, -nDepth, nDepth - nd) + Math.max(0, -sCenter, sCenter - depth);
            if (!best || out < best.out - EPS) best = { n, miss, sCenter, nDepth, nr, nd, out };
          }
          if (best.out > EPS) { err('bolt-misses-nut', tag(b) + ' does not pass through its nut hole; the nearest, ' + best.n.key + ', ' + (best.miss > best.nr ? 'is ' + fmt(best.miss) + ' off the bolt line.' : best.nDepth > best.nd ? 'stops ' + fmt(best.nDepth - best.nd) + ' short of the bolt.' : 'is beyond the bolt hole.')); bad++; }
          else if (tip < best.sCenter + best.nr - EPS) { err('bolt-short', tag(b) + ': the bolt ends ' + fmt(best.sCenter + best.nr - tip) + ' short of the far side of nut ' + best.n.key + '. It needs to reach ' + fmt(best.sCenter + best.nr) + ' from the entry; it reaches ' + fmt(tip) + '.'); bad++; }
        }
      }
    }
    // two holes that meet: screws driven from opposite faces of a divider, a peg through a bolt
    cur = null;
    const span = b => {
      const a = b.v.findIndex(x => x), d = parseLen(b.depth != null ? b.depth : b.len);
      const rr = Math.max(parseLen(b.d), b.counterbore ? parseLen(b.counterbore.d) : 0) / 2;
      const end = along(b.at, b.v, d), min = [], max = [];
      for (let i = 0; i < 3; i++) { min[i] = Math.min(b.at[i], end[i]) - (i === a ? 0 : rr); max[i] = Math.max(b.at[i], end[i]) + (i === a ? 0 : rr); }
      return { min, max };
    };
    const spans = list.map(span), crossed = {};
    for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) {
      const A = list[i], Bb = list[j];
      if (A.nut === Bb.id || Bb.nut === A.id || (A.cross || []).includes(Bb.id) || (Bb.cross || []).includes(A.id)) continue;
      if (A.id === Bb.id && A.copy === Bb.copy) continue;
      const ov = inter(spans[i], spans[j]);
      if (!ov) continue;
      const k = [A.id, Bb.id].sort().join('|');
      crossed[k] = crossed[k] || { a: A, b: Bb, n: 0 };
      crossed[k].n++;
    }
    for (const k of Object.keys(crossed)) {
      const { a, b: c, n } = crossed[k];
      err0('bore-cross', tag(a) + ' runs into ' + tag(c) + (n > 1 ? ' at ' + n + ' places' : '') + '. Move one of them, or list the other in `cross` if they are meant to meet.', []);
      bad++;
    }
    for (const k of order) {
      const s = seen[k];
      (s.lvl === 'err' ? err0 : warn0)(s.code, s.msg + (s.n > 1 ? ' (and ' + (s.n - 1) + ' more cop' + (s.n > 2 ? 'ies' : 'y') + ' of this bore)' : ''), s.parts);
    }
    M.borePaths = path;
    if (!bad) pass('bores', list.length + ' bores: entries clear once assembled, walls intact, fasteners the right length, bolts reach their nuts.');
  }

  // ---------- lumber, board feet, cutting layouts ----------
  // rough lumber in quarters that mills to t (needs about 1/4" to flatten and plane)
  function nominal(t) {
    const q = [4, 5, 6, 8, 10, 12, 16].find(n => n / 4 >= t + 0.24);
    return q ? q + '/4' : 'glue-up';
  }
  const layerT = p => p.glueup ? p.t / p.glueup : (p.stock_t ? parseLen(p.stock_t) : p.t);
  function lumberStats(M) {
    const byT = {};
    for (const p of M.parts) {
      if (p.isHardware || p.t == null || p.stock === 'sheet') continue;
      const t = layerT(p), k = t.toFixed(4) + '|' + (p.material || '');
      const bf = p.t * p.w * p.l * p.qty / 144;
      byT[k] = byT[k] || { t, material: p.material || '', bf: 0, parts: [] };
      byT[k].bf += bf; byT[k].parts.push(p.id);
    }
    return Object.values(byT).sort((a, b) => a.t - b.t || (a.material > b.material ? 1 : -1));
  }
  // Shelf packing, grain along stock length. pieces: [{id, w, l, label}], stock {w, l, kerf}
  function pack(pieces, stock) {
    const kerf = stock.kerf != null ? stock.kerf : 0.125;
    const sorted = pieces.slice().sort((a, b) => b.w - a.w || b.l - a.l);
    const boards = [];
    const fail = [];
    for (const pc of sorted) {
      if (pc.w > stock.w + EPS || pc.l > stock.l + EPS) { fail.push(pc); continue; }
      let placed = false;
      for (const bd of boards) {
        for (const sh of bd.shelves) {
          if (pc.w <= sh.h + EPS && sh.used + pc.l <= stock.l + EPS) { bd.items.push({ pc, x: sh.used, y: sh.y }); sh.used += pc.l + kerf; placed = true; break; }
        }
        if (placed) break;
        const top = bd.shelves.length ? bd.shelves[bd.shelves.length - 1].y + bd.shelves[bd.shelves.length - 1].h + kerf : 0;
        if (top + pc.w <= stock.w + EPS) { bd.shelves.push({ y: top, h: pc.w, used: pc.l + kerf }); bd.items.push({ pc, x: 0, y: top }); placed = true; break; }
      }
      if (!placed) { boards.push({ shelves: [{ y: 0, h: pc.w, used: pc.l + kerf }], items: [{ pc, x: 0, y: 0 }] }); }
    }
    return { boards, fail, stock };
  }
  function layouts(M, plan) {
    const st = Object.assign({ sheet: { w: 48, l: 96, kerf: 0.125 }, board: { w: 7.25, l: 96, kerf: 0.125 } }, plan.stock || {});
    const groups = {};
    for (const p of M.parts) {
      if (p.isHardware || p.t == null) continue;
      const kind = p.stock === 'sheet' ? 'sheet' : 'board';
      const blank = p.blank || {};
      const allowW = parseLen(blank.w_extra || (kind === 'board' ? 0.25 : 0)), allowL = parseLen(blank.l_extra || (kind === 'board' ? 1 : 0));
      const t = layerT(p);
      const key = kind + '|' + t.toFixed(4) + '|' + (p.material || '');
      const g = groups[key] = groups[key] || { kind, t, material: p.material || '', pieces: [] };
      // a glue-up (glueup: n) is laid out as n face-glued layers of t/n each
      const layers = p.glueup || 1;
      for (let q = 0; q < p.qty; q++) for (let L = 0; L < layers; L++) g.pieces.push({ id: p.id, w: p.w + allowW, l: p.l + allowL, label: p.id, grain: hasGrain(p) });
    }
    return Object.values(groups).map(g => {
      const s = g.kind === 'sheet' ? Object.assign({}, st.sheet, (st.sheets || {})[g.material] || {}) : Object.assign({}, st.board, (st.boards || {})[fmt(g.t, { unit: false })] || {});
      const res = pack(g.pieces, { w: parseLen(s.w), l: parseLen(s.l), kerf: parseLen(s.kerf) });
      if (g.kind === 'sheet') res.boards.forEach(bd => { bd.cuts = cutOrder(bd, res.stock); });
      return Object.assign(g, res);
    }).sort((a, b) => (a.kind > b.kind ? -1 : 1) || a.t - b.t);
  }
  // MDF, hardboard, melamine and particleboard have no grain; a part can also say grain: false
  const hasGrain = p => p.grain === false ? false : !/\b(mdf|hdf|hardboard|melamine|particle ?board|masonite)\b/i.test(p.material || '');
  // Breakdown order for a packed sheet, the way it is cut on a table or track saw: rip the sheet into
  // its strips first (cut 1 is the "first cut"), then crosscut each strip, then trim any part narrower
  // than its strip. Coordinates as drawn: x along the sheet length, y across it.
  function cutOrder(bd, stock) {
    const E = 1e-6, kerf = stock.kerf != null ? stock.kerf : 0.125, cuts = [];
    const sh = bd.shelves.slice().sort((a, b) => a.y - b.y);
    for (const s of sh) if (s.y + s.h < stock.w - kerf - E) cuts.push({ kind: 'rip', x1: 0, y1: s.y + s.h, x2: stock.l, y2: s.y + s.h });
    for (const s of sh) {
      const its = bd.items.filter(it => Math.abs(it.y - s.y) < E).sort((a, b) => a.x - b.x);
      for (const it of its) if (it.x + it.pc.l < stock.l - kerf - E) cuts.push({ kind: 'cross', x1: it.x + it.pc.l, y1: s.y, x2: it.x + it.pc.l, y2: Math.min(stock.w, s.y + s.h) });
      for (const it of its) if (it.pc.w < s.h - E) cuts.push({ kind: 'trim', x1: it.x, y1: it.y + it.pc.w, x2: it.x + it.pc.l, y2: it.y + it.pc.w });
    }
    cuts.forEach((c, i) => { c.n = i + 1; });
    return cuts;
  }

  // ---------- shop paperwork: cut list, buy list, tools, story sticks ----------
  // The shop cut list, sorted the way Woodsmith lays out a cutting diagram: by stock (solid, then
  // sheet), thickness, then widest to narrowest, then longest to shortest. Rough sizes add the
  // milling allowance used by the cutting diagrams.
  function cutList(M) {
    const rows = [];
    for (const p of M.parts) {
      if (p.isHardware || p.t == null) continue;
      const sheet = p.stock === 'sheet', b = p.blank || {};
      const aw = parseLen(b.w_extra || (sheet ? 0 : 0.25)), al = parseLen(b.l_extra || (sheet ? 0 : 1));
      const t = layerT(p);
      rows.push({ p, stock: sheet ? 'sheet' : 'solid', t, rough: { t: sheet ? p.t : (p.stock_t ? parseLen(p.stock_t) : nominalT(t)), w: p.w + aw, l: p.l + al }, layers: p.glueup || 1, grain: hasGrain(p) });
    }
    return rows.sort((a, b) => (a.stock === b.stock ? 0 : a.stock === 'solid' ? -1 : 1) || b.t - a.t || ((a.p.material || '') > (b.p.material || '') ? 1 : (a.p.material || '') < (b.p.material || '') ? -1 : 0) || b.p.w - a.p.w || b.p.l - a.p.l);
  }
  const nominalT = t => { const n = nominal(t); return /\//.test(n) ? parseInt(n, 10) / 4 : t; };
  // dimensional lumber names for boards that match store sizes (1x8 = 3/4 x 7-1/4)
  const DIM_W = { 1.5: 2, 2.5: 3, 3.5: 4, 5.5: 6, 7.25: 8, 9.25: 10, 11.25: 12 }, DIM_T = { 0.75: '1', 1.5: '2', 3.5: '4' };
  function storeName(kind, t, w, l, material) {
    const ft = l / 12, len = (Math.abs(ft - Math.round(ft)) < 0.01 ? Math.round(ft) + "'" : fmt(l, { metric: false }));
    if (kind === 'sheet') return fmt(t) + ' ' + (material || 'plywood') + ', ' + fmt(w, { unit: false, metric: false }) + ' x ' + fmt(l, { unit: false, metric: false }) + ' sheet';
    // softwood construction lumber is bought by its dimensional name; hardwood rough, by the quarter
    const dt = DIM_T[+t.toFixed(3)], dw = DIM_W[+w.toFixed(3)];
    if (dt && dw && (dimensional || SOFT.test(material || ''))) return dt + 'x' + dw + ' ' + (material || '') + ' @ ' + len;
    return nominal(t) + ' ' + (material || '') + ', ' + fmt(w, { metric: false }) + ' wide @ ' + len;
  }
  const SOFT = /\b(pine|fir|spruce|hemlock|spf|cedar|construction|stud|lumber)\b/i;
  let dimensional = false;
  // What to buy, in store units, from the cutting diagrams: whole sheets as drawn (they are exact),
  // boards with a spare allowance for defects and grain matching (default 20%).
  function buyList(M, plan) {
    const spare = plan.stock && plan.stock.spare != null ? plan.stock.spare : 0.2;
    dimensional = !!(plan.stock && plan.stock.buy === 'dimensional');
    const by = new Map();
    for (const g of layouts(M, plan)) {
      if (!g.boards.length) continue;
      const name = storeName(g.kind, g.t, g.stock.w, g.stock.l, g.material);
      const r = by.get(name) || by.set(name, { kind: g.kind, t: g.t, material: g.material, drawn: 0, name, parts: [] }).get(name);
      r.drawn += g.boards.length; r.parts = [...new Set(r.parts.concat(g.pieces.map(p => p.id)))];
      // parts wider than the stock are edge-glued from strips: add the boards those strips take
      const lap = g.stock.kerf != null ? g.stock.kerf : 0.125;
      for (const pc of g.fail) {
        const strips = Math.ceil(pc.w / (g.stock.w - 0.25)), per = Math.max(1, Math.floor((g.stock.l + lap) / (pc.l + lap)));
        r.drawn += pc.l > g.stock.l ? strips : Math.ceil(strips / per); r.glued = (r.glued || []).concat(pc.id);
      }
    }
    dimensional = false;
    // sheets are bought as drawn (the layout is exact); boards get the spare, and at least one extra
    return [...by.values()].map(r => Object.assign(r, { buy: r.kind === 'sheet' ? r.drawn : Math.max(r.drawn + 1, Math.ceil(r.drawn * (1 + spare))) }));
  }
  // Tools the plan needs, worked out from its joints, cuts, bores and stock, so the list never forgets one.
  const JOINT_TOOLS = {
    'mortise-tenon': ['Mortiser, or drill and chisels, for the mortises', 'Tenoning jig or dado stack for the tenons'],
    'stub-tenon': ['Router table or dado stack for the stub tenons'],
    castle: ['Bandsaw and chisels for the castle slots'], 'half-lap': ['Dado stack or bandsaw for the laps'],
    bridle: ['Bandsaw or tenoning jig for the bridle slots'], dado: ['Dado stack or router with a straight bit'],
    groove: ['Table saw or router for the grooves'], rabbet: ['Rabbeting bit or dado stack'], dovetail: ['Dovetail saw and chisels, or a dovetail jig'],
    dowel: ['Doweling jig'], 'pocket-screw': ['Pocket-hole jig'], buttons: ['Router or table saw for the button groove'], biscuit: ['Biscuit joiner'], domino: ['Domino joiner']
  };
  function toolsFor(M, plan) {
    const out = new Set();
    const parts = M.parts.filter(p => !p.isHardware);
    if (parts.some(p => p.stock === 'sheet')) out.add('Track saw or circular saw and a straightedge to break down sheets');
    if (parts.some(p => p.stock === 'solid')) { out.add('Jointer and planer, or buy stock surfaced four sides'); out.add('Table saw'); out.add('Miter saw or crosscut sled'); }
    if (parts.some(p => p.glueup)) out.add('Clamps for the glue-ups');
    for (const j of plan.joints || []) for (const t of JOINT_TOOLS[j.type] || []) out.add(t);
    // a cut tool joins the list unless a joint already named it (the castle joint's bandsaw)
    for (const p of M.parts) for (const c of p.local.cuts) { const n = c.tool && TOOL_NAMES[c.tool]; if (n && ![...out].some(t => t.toLowerCase().includes(n.toLowerCase()))) out.add(n); }
    const bores = expandBores(plan);
    if (bores.some(b => b.kind === 'screw')) out.add('Drill/driver and countersink');
    const big = [...new Set(bores.filter(b => b.counterbore).map(b => fmt(parseLen(b.counterbore.d))))];
    if (big.length) out.add('Forstner bit' + (big.length > 1 ? 's' : '') + ' (' + big.join(', ') + ') for counterbores');
    const long = bores.filter(b => parseLen(b.depth || b.len || 0) > 4).map(b => fmt(parseLen(b.d)));
    if (long.length) out.add('Long-series bit' + ([...new Set(long)].length > 1 ? 's' : '') + ' (' + [...new Set(long)].join(', ') + ')');
    if (bores.some(b => b.kind !== 'screw')) out.add('Drill press or doweling guide for square holes');
    return [...out];
  }
  const TOOL_NAMES = { bandsaw: 'Bandsaw', router: 'Router', chisel: 'Chisels', mortiser: 'Hollow-chisel mortiser', jigsaw: 'Jigsaw', tablesaw: 'Table saw', dado: 'Dado stack' };
  // Story stick: every edge of the chosen parts along one axis, merged, measured from the stick's start.
  function storyMarks(M, st) {
    const ax = { x: 0, y: 1, z: 2 }[st.axis || 'z'];
    const want = st.parts ? new Set(st.parts.map(String)) : null;
    const marks = [];
    let lo = Infinity, hi = -Infinity;
    for (const p of M.parts) {
      if (want && !want.has(String(p.id))) continue;
      for (const I of p.instances) { const b = I.bbox; if (!b) continue; lo = Math.min(lo, b.min[ax]); hi = Math.max(hi, b.max[ax]); marks.push({ at: b.min[ax], id: p.id, end: 'min' }, { at: b.max[ax], id: p.id, end: 'max' }); }
    }
    const from = st.from != null ? parseLen(st.from) : (lo === Infinity ? 0 : lo), to = st.to != null ? parseLen(st.to) : hi;
    const merged = [];
    for (const m of marks.sort((a, b) => a.at - b.at)) {
      if (m.at < from - EPS || m.at > to + EPS) continue;
      const last = merged[merged.length - 1];
      if (last && Math.abs(last.at - m.at) < 1 / 64) { if (!last.ids.includes(m.id)) last.ids.push(m.id); continue; }
      merged.push({ at: m.at, ids: [m.id] });
    }
    for (const m of st.marks || []) merged.push({ at: parseLen(m.at), ids: [], label: m.label });
    merged.sort((a, b) => a.at - b.at);
    return { from, to, len: to - from, marks: merged.map(m => Object.assign(m, { d: m.at - from })) };
  }

  const api = { cutList, buyList, toolsFor, storyMarks, cutOrder, hasGrain, storeName, expandBores, cutDepth, TOOLS, nominal, parseLen, fmt, fmtHTML, fracParts, normalize, solid, surface, check, pack, layouts, lumberStats, toAABB, xformAABB, inter, vol };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.PlanCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
