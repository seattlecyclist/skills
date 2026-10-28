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
  function boxSolid(adds, cuts, tenons) {
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
  function boxSurface(S) {
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

  // ---------- shaped parts: curves, angles and turnings ----------
  // A part is still its blank (boxes less box cuts), then shaped like the wood is: `outline` keeps
  // what lies inside a profile seen along one axis (an arched top, a round top, a taper, a splayed
  // leg), `cutout` removes what lies inside one (a mitre, a curved cutout, a cove), `lathe` keeps
  // what lies inside a turned profile, and `roundover` / `chamfer` ease the blank's edges. Tenons
  // are never trimmed. The drawings, 3D view and patterns get the exact shape (a mesh cut by BSP);
  // the checks see it as cells on a lattice that every part shares, so two mitred faces meet cell
  // for cell, and cells the curve passes through are counted as touching, not as interference.
  const CURVE_TOL = 0.006;   // chord error of a drawn curve, in inches
  const FACES = { left: [0, -1], right: [0, 1], front: [1, -1], back: [1, 1], bottom: [2, -1], top: [2, 1] };
  const AXN = { x: 0, y: 1, z: 2 };
  // the drawing axes (u, v) of a profile seen along axis a
  const plAxes = a => a === 0 ? [1, 2] : a === 1 ? [0, 2] : [0, 1];
  const isShape = s => !!(s && (s.outline || s.cutout || s.lathe || s.splay || s.roundover != null || s.chamfer != null));
  let SID = 0;   // surface ids: the facets of one curve share one, so no crease is drawn between them
  const JIT = [1.17e-7, 2.31e-7, 3.07e-7];

  const sub2 = (a, b) => [a[0] - b[0], a[1] - b[1]], len2 = a => Math.hypot(a[0], a[1]);
  const cross2 = (a, b) => a[0] * b[1] - a[1] * b[0];
  function arcSteps(r, sweep) {
    const st = Math.min(Math.PI / 16, 2 * Math.acos(Math.max(-1, 1 - CURVE_TOL / Math.max(r, 1e-6))));
    return 2 * Math.max(1, Math.ceil(Math.abs(sweep) / st / 2));   // even, so an arc's middle is a point
  }
  function circum(a, b, c) {
    const d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]));
    if (Math.abs(d) < 1e-12) return null;
    const A = a[0] * a[0] + a[1] * a[1], B = b[0] * b[0] + b[1] * b[1], Cc = c[0] * c[0] + c[1] * c[1];
    return [(A * (b[1] - c[1]) + B * (c[1] - a[1]) + Cc * (a[1] - b[1])) / d, (A * (c[0] - b[0]) + B * (a[0] - c[0]) + Cc * (b[0] - a[0])) / d];
  }
  // points along an arc about c from p0 (left out) to p1, counter-clockwise (dir 1) or clockwise (-1)
  function arcTo(p0, p1, c, dir) {
    const r = len2(sub2(p0, c));
    const a0 = Math.atan2(p0[1] - c[1], p0[0] - c[0]), a1 = Math.atan2(p1[1] - c[1], p1[0] - c[0]);
    let sw = a1 - a0;
    if (dir > 0) while (sw <= 1e-9) sw += 2 * Math.PI; else while (sw >= -1e-9) sw -= 2 * Math.PI;
    const n = arcSteps(r, sw), out = [];
    for (let i = 1; i < n; i++) { const t = a0 + sw * i / n; out.push([c[0] + r * Math.cos(t), c[1] + r * Math.sin(t)]); }
    out.push(p1.slice());
    return { pts: out, c, r, sweep: sw };
  }
  // centripetal Catmull-Rom through p0 and the listed points
  function curveTo(p0, list) {
    const P = [p0].concat(list), out = [];
    const ext = (a, b) => [2 * a[0] - b[0], 2 * a[1] - b[1]];
    for (let i = 0; i < P.length - 1; i++) {
      const a = i ? P[i - 1] : ext(P[0], P[1]), b = P[i], c = P[i + 1], d = i + 2 < P.length ? P[i + 2] : ext(P[i + 1], P[i]);
      const ta = 0, tb = ta + Math.sqrt(len2(sub2(b, a)) || 1e-9), tc = tb + Math.sqrt(len2(sub2(c, b)) || 1e-9), td = tc + Math.sqrt(len2(sub2(d, c)) || 1e-9);
      const n = Math.max(4, Math.min(48, Math.ceil(len2(sub2(c, b)) / 0.2)));
      const L = (p, q, t0, t1, t) => [(p[0] * (t1 - t) + q[0] * (t - t0)) / (t1 - t0), (p[1] * (t1 - t) + q[1] * (t - t0)) / (t1 - t0)];
      for (let k = 1; k <= n; k++) {
        const t = tb + (tc - tb) * k / n;
        const A1 = L(a, b, ta, tb, t), A2 = L(b, c, tb, tc, t), A3 = L(c, d, tc, td, t);
        const B1 = L(A1, A2, ta, tc, t), B2 = L(A2, A3, tb, td, t);
        out.push(k === n ? c.slice() : L(B1, B2, tb, tc, t));
      }
    }
    return out;
  }

  // A profile: points [u, v] (or [u, v, r] to round that corner), { arc: [u, v], through | center |
  // rise }, { curve: [[u, v], ...] }, { bezier: [[cu, cv], ([cu, cv],) [u, v]] }, or a whole
  // { circle: [cu, cv, r] } / { ellipse: [cu, cv, ru, rv] }.
  // -> { pts (counter-clockwise, closed), sid (surface id of the edge from pts[i] to pts[i+1]),
  //      nodes (the points as written, for dimensions), arcs ({ c, r, mid } for radius labels) }
  function profile(spec, open) {
    const L = parseLen, P2 = q => [L(q[0]), L(q[1])];
    const pts = [], sid = [], nodes = [], arcs = [], fil = [], curves = [];
    if (spec && !Array.isArray(spec) && (spec.circle || spec.ellipse)) {
      const e = (spec.circle || spec.ellipse).map(L), ru = e[2], rv = spec.circle ? e[2] : e[3];
      const n = 4 * Math.ceil(arcSteps(Math.max(ru, rv), 2 * Math.PI) / 4), id = ++SID;
      for (let i = 0; i < n; i++) { const t = 2 * Math.PI * i / n; pts.push([e[0] + ru * Math.cos(t), e[1] + rv * Math.sin(t)]); sid.push(id); }
      for (const t of [0, 1, 2, 3]) nodes.push([e[0] + ru * Math.cos(t * Math.PI / 2), e[1] + rv * Math.sin(t * Math.PI / 2)]);
      arcs.push({ c: [e[0], e[1]], r: ru, rv, mid: [e[0] + ru * Math.SQRT1_2, e[1] + rv * Math.SQRT1_2], circle: true });
      return { pts, sid, nodes, arcs, fil, curves };
    }
    if (!Array.isArray(spec) || !spec.length) throw new Error('A profile needs a list of points, or a circle or ellipse.');
    const add = (p, id) => { if (pts.length) sid[pts.length - 1] = id; pts.push(p); sid.push(null); };
    // which way is out: a positive rise bulges away from the inside of the profile (a lathe profile's
    // inside is toward its axis)
    const ends = spec.map(e => Array.isArray(e) ? P2(e) : e.arc ? P2(e.arc) : e.curve ? P2(e.curve[e.curve.length - 1]) : e.bezier ? P2(e.bezier[e.bezier.length - 1]) : null).filter(Boolean);
    if (open && ends.length) ends.push([0, ends[ends.length - 1][1]], [0, ends[0][1]]);
    const outward = area2(ends) >= 0 ? -1 : 1;   // counter-clockwise: the inside is on the left
    for (const e of spec) {
      if (Array.isArray(e)) {
        const p = P2(e); add(p, ++SID); nodes.push(p);
        if (e.length > 2 && L(e[2]) > 0) fil[pts.length - 1] = L(e[2]);
        continue;
      }
      if (!pts.length) throw new Error('A profile starts with a point.');
      const p0 = pts[pts.length - 1], id = ++SID;
      if (e.arc) {
        const p1 = P2(e.arc); let A;
        if (e.center) {
          const c = P2(e.center), cr = cross2(sub2(p0, c), sub2(p1, c));
          let dir = e.ccw != null ? (e.ccw ? 1 : -1) : (cr >= 0 ? 1 : -1);
          if (e.long && e.ccw == null) dir = -dir;
          A = arcTo(p0, p1, c, dir);
        } else {
          let m;
          if (e.through) m = P2(e.through);
          else if (e.rise != null) {
            const d = sub2(p1, p0), l = len2(d) || 1, rs = L(e.rise);
            m = [(p0[0] + p1[0]) / 2 - outward * d[1] / l * rs, (p0[1] + p1[1]) / 2 + outward * d[0] / l * rs];
          } else throw new Error('An arc needs through, center or rise.');
          const c = circum(p0, m, p1);
          if (!c) { add(p1, id); nodes.push(p1); continue; }   // a straight "arc" is a line
          A = arcTo(p0, p1, c, cross2(sub2(m, p0), sub2(p1, m)) > 0 ? 1 : -1);
        }
        for (const q of A.pts) add(q, id);
        nodes.push(p1);
        const ma = Math.atan2(p0[1] - A.c[1], p0[0] - A.c[0]) + A.sweep / 2;
        arcs.push({ c: A.c, r: A.r, mid: [A.c[0] + A.r * Math.cos(ma), A.c[1] + A.r * Math.sin(ma)], a: p0, b: p1, sweep: Math.abs(A.sweep) });
      } else if (e.curve) {
        const list = e.curve.map(P2);
        for (const q of curveTo(p0, list)) add(q, id);
        nodes.push(list[list.length - 1]);
        curves.push([p0].concat(list));
      } else if (e.bezier) {
        // a Bézier segment: [control, end] (quadratic) or [control, control, end] (cubic), as a
        // drawing program draws it; laid out in the shop through points marked along it
        const cs = e.bezier.map(P2);
        if (cs.length < 2 || cs.length > 3) throw new Error('A bezier is [control, end] or [control, control, end].');
        const ctl = [p0].concat(cs), at = t => { let q = ctl; while (q.length > 1) q = q.slice(1).map((b, k) => [q[k][0] + (b[0] - q[k][0]) * t, q[k][1] + (b[1] - q[k][1]) * t]); return q[0]; };
        const reach = ctl.slice(1).reduce((s2, q, k) => s2 + len2(sub2(q, ctl[k])), 0), n = Math.max(8, Math.min(96, Math.ceil(reach / 0.15)));
        for (let k = 1; k <= n; k++) add(k === n ? cs[cs.length - 1].slice() : at(k / n), id);
        nodes.push(cs[cs.length - 1]);
        curves.push([0, 0.25, 0.5, 0.75, 1].map(at));
      } else throw new Error('Unknown profile entry: ' + JSON.stringify(e));
    }
    // a closing entry that lands on the start point
    if (pts.length > 2 && len2(sub2(pts[0], pts[pts.length - 1])) < 1e-6) { const id = sid[pts.length - 2]; pts.pop(); sid.pop(); sid[pts.length - 1] = id; }
    if (!open) sid[pts.length - 1] = sid[pts.length - 1] || ++SID;
    return { pts, sid, nodes, arcs, fil, curves };
  }
  // round the corners that asked for it ([u, v, r]): only straight edges meet there
  function fillet(P) {
    if (!P.fil.length) return P;
    const n = P.pts.length, pts = [], sid = [];
    for (let i = 0; i < n; i++) {
      const p = P.pts[i], r = P.fil[i];
      if (!r) { pts.push(p); sid.push(P.sid[i]); continue; }
      const a = P.pts[(i - 1 + n) % n], b = P.pts[(i + 1) % n];
      const d1 = sub2(a, p), d2 = sub2(b, p), l1 = len2(d1), l2 = len2(d2);
      const u1 = [d1[0] / l1, d1[1] / l1], u2 = [d2[0] / l2, d2[1] / l2];
      const th = Math.acos(Math.max(-1, Math.min(1, u1[0] * u2[0] + u1[1] * u2[1])));
      if (th < 1e-3 || th > Math.PI - 1e-3) { pts.push(p); sid.push(P.sid[i]); continue; }
      const t = Math.min(r / Math.tan(th / 2), l1 * 0.999, l2 * 0.999), rr = t * Math.tan(th / 2);
      const bis = [u1[0] + u2[0], u1[1] + u2[1]], bl = len2(bis), h = rr / Math.sin(th / 2);
      const c = [p[0] + bis[0] / bl * h, p[1] + bis[1] / bl * h];
      const s = [p[0] + u1[0] * t, p[1] + u1[1] * t], e = [p[0] + u2[0] * t, p[1] + u2[1] * t];
      const A = arcTo(s, e, c, cross2(u1, u2) < 0 ? 1 : -1), id = ++SID;
      pts.push(s); sid.push(id);
      A.pts.forEach((q, k) => { pts.push(q); sid.push(k === A.pts.length - 1 ? P.sid[i] : id); });
      P.arcs.push({ c, r: rr, mid: [c[0] - bis[0] / bl * rr, c[1] - bis[1] / bl * rr], a: s, b: e, sweep: Math.PI - th, fillet: true });
    }
    return Object.assign({}, P, { pts, sid });
  }
  function area2(pts) { let s = 0; for (let i = 0; i < pts.length; i++) { const a = pts[i], b = pts[(i + 1) % pts.length]; s += a[0] * b[1] - b[0] * a[1]; } return s / 2; }
  function ccw(P) {
    if (area2(P.pts) >= 0) return P;
    const n = P.pts.length;
    return Object.assign({}, P, { pts: P.pts.slice().reverse(), sid: P.pts.map((_, k) => P.sid[((n - 2 - k) % n + n) % n]) });
  }
  function inPoly(q, pts) {
    let c = false;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      const a = pts[i], b = pts[j];
      if ((a[1] > q[1]) !== (b[1] > q[1]) && q[0] < (b[0] - a[0]) * (q[1] - a[1]) / (b[1] - a[1]) + a[0]) c = !c;
    }
    return c;
  }
  // ear clipping, for the end caps of a prism (a cap may be concave; BSP polygons must be convex)
  function triangulate(pts) {
    const idx = pts.map((_, i) => i), tris = [];
    let guard = 0;
    while (idx.length > 3 && guard++ < 10000) {
      let cut = false;
      for (let k = 0; k < idx.length; k++) {
        const i0 = idx[(k - 1 + idx.length) % idx.length], i1 = idx[k], i2 = idx[(k + 1) % idx.length];
        const a = pts[i0], b = pts[i1], c = pts[i2];
        if (cross2(sub2(b, a), sub2(c, b)) <= 1e-12) continue;
        let ear = true;
        for (const j of idx) {
          if (j === i0 || j === i1 || j === i2) continue;
          const p = pts[j];
          if (cross2(sub2(b, a), sub2(p, a)) > 1e-12 && cross2(sub2(c, b), sub2(p, b)) > 1e-12 && cross2(sub2(a, c), sub2(p, c)) > 1e-12) { ear = false; break; }
        }
        if (!ear) continue;
        tris.push([i0, i1, i2]); idx.splice(k, 1); cut = true; break;
      }
      if (!cut) { idx.splice(0, 1); }   // degenerate: drop a point rather than hang
    }
    if (idx.length === 3) tris.push(idx.slice());
    return tris;
  }

  // ---- BSP solids, after csg.js (Evan Wallace, MIT): polygons {v: [pts], n, w, s} ----
  const PEPS = 1e-5;
  const sub3 = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const dot3 = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const lerp3 = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
  function poly(v, s) {
    // Newell's normal: fine for the long thin facets curves make
    const n = [0, 0, 0];
    for (let i = 0; i < v.length; i++) { const a = v[i], b = v[(i + 1) % v.length]; n[0] += (a[1] - b[1]) * (a[2] + b[2]); n[1] += (a[2] - b[2]) * (a[0] + b[0]); n[2] += (a[0] - b[0]) * (a[1] + b[1]); }
    const l = Math.hypot(n[0], n[1], n[2]);
    if (l < 1e-12) return null;
    const nn = [n[0] / l, n[1] / l, n[2] / l];
    return { v, n: nn, w: dot3(nn, v[0]), s };
  }
  const flip = P => ({ v: P.v.slice().reverse(), n: P.n.map(x => -x), w: -P.w, s: P.s });
  const TY = new Uint8Array(4096);
  function split(pl, P, coF, coB, F, B) {
    let type = 0;
    const n = pl.n, V = P.v;
    for (let i = 0; i < V.length; i++) { const v = V[i], t = n[0] * v[0] + n[1] * v[1] + n[2] * v[2] - pl.w, ty = t < -PEPS ? 2 : t > PEPS ? 1 : 0; type |= ty; TY[i] = ty; }
    const types = type === 3 ? TY.slice(0, V.length) : null;
    if (type === 0) (dot3(pl.n, P.n) > 0 ? coF : coB).push(P);
    else if (type === 1) F.push(P);
    else if (type === 2) B.push(P);
    else {
      const f = [], b = [];
      for (let i = 0; i < P.v.length; i++) {
        const j = (i + 1) % P.v.length, ti = types[i], tj = types[j], vi = P.v[i], vj = P.v[j];
        if (ti !== 2) f.push(vi);
        if (ti !== 1) b.push(ti !== 2 ? vi.slice() : vi);
        if ((ti | tj) === 3) {
          const t = (pl.w - dot3(pl.n, vi)) / dot3(pl.n, sub3(vj, vi)), v = lerp3(vi, vj, t);
          f.push(v); b.push(v.slice());
        }
      }
      if (f.length >= 3) F.push({ v: f, n: P.n, w: P.w, s: P.s });
      if (b.length >= 3) B.push({ v: b, n: P.n, w: P.w, s: P.s });
    }
  }
  function bsp(polys) { const N = { plane: null, front: null, back: null, polys: [] }; if (polys && polys.length) build(N, polys); return N; }
  function build(N, polys) {
    if (!polys.length) return;
    if (!N.plane) N.plane = { n: polys[0].n, w: polys[0].w };
    const F = [], B = [];
    for (const P of polys) split(N.plane, P, N.polys, N.polys, F, B);
    if (F.length) { N.front = N.front || bsp(); build(N.front, F); }
    if (B.length) { N.back = N.back || bsp(); build(N.back, B); }
  }
  function invert(N) {
    N.polys = N.polys.map(flip);
    if (N.plane) N.plane = { n: N.plane.n.map(x => -x), w: -N.plane.w };
    if (N.front) invert(N.front); if (N.back) invert(N.back);
    const t = N.front; N.front = N.back; N.back = t;
  }
  function clipPolys(N, polys) {
    if (!N.plane) return polys.slice();
    let F = [], B = [];
    for (const P of polys) split(N.plane, P, F, B, F, B);
    if (N.front) F = clipPolys(N.front, F);
    B = N.back ? clipPolys(N.back, B) : [];
    return F.concat(B);
  }
  function clipTo(N, O) { N.polys = clipPolys(O, N.polys); if (N.front) clipTo(N.front, O); if (N.back) clipTo(N.back, O); }
  function allPolys(N) { let out = N.polys.slice(); if (N.front) out = out.concat(allPolys(N.front)); if (N.back) out = out.concat(allPolys(N.back)); return out; }
  function csgSubtract(a, b) {
    if (!a.length || !b.length) return a;
    const A = bsp(a), B = bsp(b);
    invert(A); clipTo(A, B); clipTo(B, A); invert(B); clipTo(B, A); invert(B); build(A, allPolys(B)); invert(A);
    return allPolys(A);
  }
  const bboxPolys = polys => { if (!polys.length) return null; const b = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] }; for (const P of polys) for (const v of P.v) for (let k = 0; k < 3; k++) { b.min[k] = Math.min(b.min[k], v[k]); b.max[k] = Math.max(b.max[k], v[k]); } return b; };
  function boxPolys(a, s) {
    const out = [];
    for (let ax = 0; ax < 3; ax++) for (const sg of [-1, 1]) {
      const b = (ax + 1) % 3, c = (ax + 2) % 3, pa = sg > 0 ? a.max[ax] : a.min[ax];
      const mk = (bv, cv) => { const p = [0, 0, 0]; p[ax] = pa; p[b] = bv; p[c] = cv; return p; };
      const v = sg > 0 ? [mk(a.min[b], a.min[c]), mk(a.max[b], a.min[c]), mk(a.max[b], a.max[c]), mk(a.min[b], a.max[c])]
        : [mk(a.min[b], a.min[c]), mk(a.min[b], a.max[c]), mk(a.max[b], a.max[c]), mk(a.max[b], a.min[c])];
      out.push(poly(v, s || null));
    }
    return out;
  }
  // a profile (counter-clockwise in u, v) pushed along axis a from s0 to s1
  function prismPolys(P, a, s0, s1) {
    const [ua, va] = plAxes(a), out = [];
    const at = (q, s) => { const p = [0, 0, 0]; p[ua] = q[0]; p[va] = q[1]; p[a] = s; return p; };
    const n = P.pts.length;
    const orient = (v, want, s) => { let Q = poly(v, s); if (!Q) return; if (dot3(Q.n, want) < 0) Q = flip(Q); out.push(Q); };
    for (let i = 0; i < n; i++) {
      const p = P.pts[i], q = P.pts[(i + 1) % n], d = sub2(q, p), w = [0, 0, 0];
      w[ua] = d[1]; w[va] = -d[0];   // outward, right of travel
      orient([at(p, s0), at(q, s0), at(q, s1), at(p, s1)], w, P.sid[i]);
    }
    for (const t of triangulate(P.pts)) for (const [s, sg] of [[s0, -1], [s1, 1]]) { const w = [0, 0, 0]; w[a] = sg; orient(t.map(k => at(P.pts[k], s)), w, null); }
    return out;
  }
  // a turned profile [r, along] revolved about axis a through (cu, cv)
  function lathePolys(P, a, c) {
    const [ua, va] = plAxes(a), out = [];
    const rmax = Math.max(...P.pts.map(q => q[0]));
    const N = Math.max(24, 4 * Math.ceil(arcSteps(rmax, 2 * Math.PI) / 4));
    const at = (r, s, k) => { const t = 2 * Math.PI * k / N, p = [0, 0, 0]; p[ua] = c[0] + r * Math.cos(t); p[va] = c[1] + r * Math.sin(t); p[a] = s; return p; };
    const n = P.pts.length;
    for (let i = 0; i < n; i++) {
      const p = P.pts[i], q = P.pts[(i + 1) % n];
      if (p[0] < 1e-9 && q[0] < 1e-9) continue;
      const out2 = [q[1] - p[1], -(q[0] - p[0])];   // outward in (r, along): right of travel
      for (let k = 0; k < N; k++) {
        const v = [at(p[0], p[1], k), at(q[0], q[1], k), at(q[0], q[1], k + 1), at(p[0], p[1], k + 1)].filter((x, j, arr) => j === 0 || len2(sub2([x[ua], x[va]], [arr[j - 1][ua], arr[j - 1][va]])) > 1e-9 || Math.abs(x[a] - arr[j - 1][a]) > 1e-9);
        if (v.length < 3) continue;
        let Q = poly(v, P.sid[i]); if (!Q) continue;
        const t = 2 * Math.PI * (k + 0.5) / N, w = [0, 0, 0]; w[ua] = out2[0] * Math.cos(t); w[va] = out2[0] * Math.sin(t); w[a] = out2[1];
        if (dot3(Q.n, w) < 0) Q = flip(Q);
        out.push(Q);
      }
    }
    return out;
  }

  // a profile offset into its own inside by d (outward when d < 0): each corner moves along its
  // bisector, as a router bearing's path does on a convex edge
  function offsetPts(pts, d) {
    if (!d) return pts.map(q => q.slice());
    const n = pts.length;
    return pts.map((p, i) => {
      const a = pts[(i - 1 + n) % n], b = pts[(i + 1) % n];
      const t1 = sub2(p, a), t2 = sub2(b, p), l1 = len2(t1) || 1, l2 = len2(t2) || 1;
      const n1 = [-t1[1] / l1, t1[0] / l1], n2 = [-t2[1] / l2, t2[0] / l2];   // left normals: inside, counter-clockwise
      const k = Math.max(0.25, 1 + n1[0] * n2[0] + n1[1] * n2[1]);
      return [p[0] + d * (n1[0] + n2[0]) / k, p[1] + d * (n1[1] + n2[1]) / k];
    });
  }
  // a solid lofted through rings of one profile: [{ s, d }] from one end to the other, each ring the
  // profile offset by d at s along axis a; edge i's band keeps one surface id per run of rings
  function loftPolys(P, a, rings, ids) {
    const [ua, va] = plAxes(a), out = [], n = P.pts.length;
    const at = (q, s2) => { const p = [0, 0, 0]; p[ua] = q[0]; p[va] = q[1]; p[a] = s2; return p; };
    const R = rings.map(r => offsetPts(P.pts, r.d));
    const orient = (v, want, sid) => { let Q = poly(v, sid); if (!Q) return; if (dot3(Q.n, want) < 0) Q = flip(Q); out.push(Q); };
    for (let j = 0; j + 1 < rings.length; j++) {
      if (Math.abs(rings[j + 1].s - rings[j].s) < 1e-9) continue;
      for (let i = 0; i < n; i++) {
        const p = P.pts[i], q = P.pts[(i + 1) % n], d = sub2(q, p), w = [0, 0, 0];
        w[ua] = d[1]; w[va] = -d[0];
        orient([at(R[j][i], rings[j].s), at(R[j][(i + 1) % n], rings[j].s), at(R[j + 1][(i + 1) % n], rings[j + 1].s), at(R[j + 1][i], rings[j + 1].s)], w, ids(i, j));
      }
    }
    const lo = rings[0].s < rings[rings.length - 1].s ? -1 : 1;
    for (const [k, sg] of [[0, lo], [rings.length - 1, -lo]]) for (const t of triangulate(R[k])) { const w = [0, 0, 0]; w[a] = sg; orient(t.map(m => at(R[k][m], rings[k].s)), w, null); }
    return out;
  }
  // a straight stick of section w x d along unit u from T, frame e1, e2: its eight corners as a solid
  function stickPolys(T, u, e1, e2, w, d, t0, t1) {
    const c = (sa, sb, t) => [0, 1, 2].map(k => T[k] + e1[k] * sa * w / 2 + e2[k] * sb * d / 2 + u[k] * t);
    const out = [], mid = c(0, 0, (t0 + t1) / 2);
    const face = v => { let Q = poly(v, null); if (!Q) return; const f = [0, 1, 2].map(k => v.reduce((s2, p) => s2 + p[k], 0) / v.length - mid[k]); if (dot3(Q.n, f) < 0) Q = flip(Q); out.push(Q); };
    for (const sa of [-1, 1]) face([c(sa, -1, t0), c(sa, 1, t0), c(sa, 1, t1), c(sa, -1, t1)]);
    for (const sb of [-1, 1]) face([c(-1, sb, t0), c(1, sb, t0), c(1, sb, t1), c(-1, sb, t1)]);
    for (const t of [t0, t1]) face([c(-1, -1, t), c(1, -1, t), c(1, 1, t), c(-1, 1, t)]);
    return out;
  }
  // distance from a point to the nearest edge of a closed polygon
  function edgeDist(q, pts) {
    let best = Infinity;
    for (let i = 0; i < pts.length; i++) {
      const a = pts[i], b = pts[(i + 1) % pts.length], ab = sub2(b, a), L = ab[0] * ab[0] + ab[1] * ab[1] || 1e-18;
      const t = Math.max(0, Math.min(1, ((q[0] - a[0]) * ab[0] + (q[1] - a[1]) * ab[1]) / L));
      best = Math.min(best, Math.hypot(q[0] - a[0] - ab[0] * t, q[1] - a[1] - ab[1] * t));
    }
    return best;
  }

  // ---- compiling a part's shapes (part coordinates) ----
  const grow3 = (b, d) => ({ min: b.min.map(v => v - d), max: b.max.map(v => v + d) });
  function unionBox(list) { let u = null; for (const a of list) u = u ? { min: u.min.map((v, k) => Math.min(v, a.min[k])), max: u.max.map((v, k) => Math.max(v, a.max[k])) } : { min: a.min.slice(), max: a.max.slice() }; return u; }
  // the box of a profile's boundary that lies inside the blank: where the shape changes the wood
  function boundaryBox(P, a, s0, s1, blank) {
    const [ua, va] = plAxes(a), b = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
    const n = P.pts.length;
    const hit = q => {
      if (q[0] < blank.min[ua] - EPS || q[0] > blank.max[ua] + EPS || q[1] < blank.min[va] - EPS || q[1] > blank.max[va] + EPS) return;
      b.min[ua] = Math.min(b.min[ua], q[0]); b.max[ua] = Math.max(b.max[ua], q[0]); b.min[va] = Math.min(b.min[va], q[1]); b.max[va] = Math.max(b.max[va], q[1]);
    };
    for (let i = 0; i < n; i++) {
      const p = P.pts[i], q = P.pts[(i + 1) % n], m = Math.max(1, Math.ceil(len2(sub2(q, p)) / 0.125));
      for (let k = 0; k <= m; k++) hit([p[0] + (q[0] - p[0]) * k / m, p[1] + (q[1] - p[1]) * k / m]);
    }
    if (b.min[ua] > b.max[ua]) return null;
    b.min[a] = Math.max(s0, blank.min[a]); b.max[a] = Math.min(s1, blank.max[a]);
    for (const k of [ua, va]) { b.min[k] = Math.max(blank.min[k], b.min[k] - 1 / 16); b.max[k] = Math.min(blank.max[k], b.max[k] + 1 / 16); }
    return b.max[a] > b.min[a] ? b : null;
  }
  function edgeList(spec, ext) {
    const all = [];
    for (const [fa, sa] of Object.values(FACES)) for (const [fb, sb] of Object.values(FACES)) if (fa < fb) all.push([[fa, sa], [fb, sb]]);
    const named = n => {
      n = String(n).toLowerCase().trim();
      if (n === 'all') return all;
      if (n === 'long') { const la = ext.indexOf(Math.max(...ext)); return all.filter(e => e[0][0] !== la && e[1][0] !== la); }
      const ws = n.split(/[\s,+&-]+/).filter(Boolean).map(w => FACES[w]);
      if (ws.some(w => !w)) throw new Error('Unknown edge "' + n + '": use top, bottom, front, back, left, right, a pair like top-front, long or all.');
      if (ws.length === 1) return all.filter(e => e.some(f => f[0] === ws[0][0] && f[1] === ws[0][1]));
      if (ws.length === 2 && ws[0][0] !== ws[1][0]) return all.filter(e => e.every(f => ws.some(w => w[0] === f[0] && w[1] === f[1])));
      throw new Error('Edge "' + n + '" does not name an edge.');
    };
    const out = [], seen = new Set();
    for (const n of [].concat(spec || 'all')) for (const e of named(n)) { const k = e.join(); if (!seen.has(k)) { seen.add(k); out.push(e); } }
    return out;
  }
  function compileShapes(p, loc) {
    const list = (p.shape || []).filter(isShape);
    if (!list.length) return [];
    const body = loc.adds.filter(a => !loc.tenons.includes(a));
    const blank = unionBox(body.length ? body : loc.adds);
    if (!blank) return [];
    const big = grow3(blank, 1), out = [];
    for (const s of list) {
      const tool = s.tool;
      if (s.outline || s.cutout) {
        const a = AXN[s.axis || 'y'], keep = !!s.outline;
        if (a == null) throw new Error('Part ' + p.id + ': a shape axis is x, y or z.');
        const P = ccw(fillet(profile(s.outline || s.cutout)));
        const sp = s.span ? s.span.map(parseLen).sort((x, y) => x - y) : [big.min[a], big.max[a]];
        const [ua, va] = plAxes(a);
        // ease: { roundover | chamfer: r, faces }: the profile's edges eased where they meet the faces
        // across the axis (both by default), following every curve and corner the profile has
        const E = s.ease ? { r: parseLen(s.ease.roundover != null ? s.ease.roundover : s.ease.chamfer), round: s.ease.roundover != null } : null;
        if (E) {
          const names = [].concat(s.ease.faces || 'both'), sides = new Set();
          for (const nm of names) {
            if (nm === 'both') { sides.add(-1); sides.add(1); continue; }
            const f = FACES[nm];
            if (!f || f[0] !== a) throw new Error('Part ' + p.id + ': ease faces for a profile seen along ' + 'xyz'[a] + ' are ' + Object.keys(FACES).filter(k => FACES[k][0] === a).join(' and ') + ', or both.');
            sides.add(f[1]);
          }
          E.planes = [...sides].map(sg => ({ sg, at: sg < 0 ? Math.max(sp[0], blank.min[a]) : Math.min(sp[1], blank.max[a]) }));
          E.inset = h => h >= E.r ? 0 : E.round ? E.r - Math.sqrt(Math.max(0, E.r * E.r - (E.r - h) * (E.r - h))) : E.r - h;
        }
        const eased = q => {
          if (!E) return false;
          for (const pl of E.planes) {
            const h = (q[a] - pl.at) * -pl.sg;   // depth in from that face
            if (h < 0 || h >= E.r) continue;
            if (edgeDist([q[ua], q[va]], P.pts) < E.inset(h)) return true;
          }
          return false;
        };
        let region = boundaryBox(P, a, sp[0], sp[1], blank);
        if (E && region) for (const k of [ua, va]) { region.min[k] = Math.max(blank.min[k], region.min[k] - E.r); region.max[k] = Math.min(blank.max[k], region.max[k] + E.r); }
        out.push({
          kind: keep ? 'outline' : 'cutout', keep, axis: a, span: sp, prof: P, tool, region, vary: E ? [0, 1, 2] : [ua, va], src: s, ease: E,
          removes: q => {
            const inSpan = q[a] > sp[0] && q[a] < sp[1], inside = inPoly([q[ua], q[va]], P.pts);
            if (inSpan && inside !== keep) return true;
            return eased(q);
          },
          cutter() {
            if (!E) {
              if (!keep) return prismPolys(P, a, sp[0], sp[1]);
              const slab = { min: big.min.slice(), max: big.max.slice() }; slab.min[a] = Math.max(sp[0], big.min[a]); slab.max[a] = Math.min(sp[1], big.max[a]);
              return csgSubtract(boxPolys(slab), prismPolys(P, a, slab.min[a] - 0.5, slab.max[a] + 0.5));
            }
            // rings from one end to the other: square ends run past the part, eased ends step in
            // (out, for a cutout) along the round-over's quarter circle or the chamfer's line
            const sgn = keep ? 1 : -1, steps = E.round ? 8 : 1;
            const end = (sg) => {
              const pl = E.planes.find(x => x.sg === sg), base = sg < 0 ? Math.max(sp[0], big.min[a]) : Math.min(sp[1], big.max[a]);
              if (!pl) return [{ s: base + sg * 0.5, d: 0 }];
              const rs = [];
              if (!keep) rs.push({ s: pl.at + sg * 0.5, d: -E.r });
              for (let k = 0; k <= steps; k++) { const h = E.r * k / steps; rs.push({ s: pl.at - sg * h, d: sgn * E.inset(h) }); }
              return rs;
            };
            const rings = end(-1).concat(end(1).reverse());
            const ids = {}, sid = (i, j) => { const key = P.sid[i] + '|' + (j < rings.length / 2 ? 0 : 1) + '|' + (Math.abs(rings[j].d) + Math.abs(rings[j + 1].d) > 0 ? 1 : 0); return ids[key] || (ids[key] = ++SID); };
            const body = loftPolys(P, a, rings, sid);
            if (!keep) return body;
            const slab = { min: big.min.slice(), max: big.max.slice() }; slab.min[a] = Math.max(sp[0], big.min[a]); slab.max[a] = Math.min(sp[1], big.max[a]);
            return csgSubtract(boxPolys(slab), body);
          }
        });
      } else if (s.splay) {
        // a leg splayed in two directions: a straight stick of section [w, d] hanging from `top`
        // ([x, y] on the blank's top face), its foot moved out by the two sight-line angles (as a
        // bevel gauge reads them in the front and side views), top and foot cut level
        const ang = [].concat(s.splay).map(Number), tx = Math.tan((ang[0] || 0) * Math.PI / 180), ty = Math.tan((ang[1] || 0) * Math.PI / 180);
        const sec = (s.section || [blank.max[0] - blank.min[0], blank.max[1] - blank.min[1]]).map(parseLen);
        const ul = Math.hypot(tx, ty, 1), u = [tx / ul, ty / ul, -1 / ul];
        const X = [1, 0, 0], ux = dot3(X, u), e1n = [1 - ux * u[0], -ux * u[1], -ux * u[2]], e1l = Math.hypot(...e1n), e1 = e1n.map(v => v / e1l);
        const e2 = [e1[1] * u[2] - e1[2] * u[1], e1[2] * u[0] - e1[0] * u[2], e1[0] * u[1] - e1[1] * u[0]];
        const hx = Math.abs(e1[0]) * sec[0] / 2 + Math.abs(e2[0]) * sec[1] / 2, hy = Math.abs(e1[1]) * sec[0] / 2 + Math.abs(e2[1]) * sec[1] / 2;
        const T = s.top ? [parseLen(s.top[0]), parseLen(s.top[1]), blank.max[2]] : [tx >= 0 ? blank.min[0] + hx : blank.max[0] - hx, ty >= 0 ? blank.min[1] + hy : blank.max[1] - hy, blank.max[2]];
        const H = blank.max[2] - blank.min[2], len = H / -u[2];
        out.push({
          kind: 'splay', keep: true, axis: 2, span: [blank.min[2], blank.max[2]], angles: [ang[0] || 0, ang[1] || 0], section: sec, top: T, dir: u, e1, e2, length: len,
          stock: len + (Math.abs(e1[2]) * sec[0] + Math.abs(e2[2]) * sec[1]) / -u[2], tool: tool || 'tablesaw', region: { min: blank.min.slice(), max: blank.max.slice() }, vary: [0, 1, 2], src: s,
          removes: q => { const r = sub3(q, T); return Math.abs(dot3(r, e1)) > sec[0] / 2 || Math.abs(dot3(r, e2)) > sec[1] / 2; },
          cutter: () => csgSubtract(boxPolys(big), stickPolys(T, u, e1, e2, sec[0], sec[1], -2 / -u[2], len + 2 / -u[2]))
        });
      } else if (s.lathe) {
        const a = AXN[s.axis || 'z'];
        if (a == null) throw new Error('Part ' + p.id + ': a lathe axis is x, y or z.');
        const [ua, va] = plAxes(a);
        const c = s.center ? s.center.map(parseLen) : [(blank.min[ua] + blank.max[ua]) / 2, (blank.min[va] + blank.max[va]) / 2];
        const raw = profile(s.lathe, true), first = raw.pts[0], last = raw.pts[raw.pts.length - 1];
        const lo = Math.min(first[1], last[1]), hi = Math.max(first[1], last[1]);
        // close along the axis, a little past each end so the cutter opens cleanly
        const dir = last[1] >= first[1] ? 1 : -1;
        const pts = [[0, first[1] - dir * 0.05], [first[0], first[1] - dir * 0.05]].concat(raw.pts, [[last[0], last[1] + dir * 0.05], [0, last[1] + dir * 0.05]]);
        const sid = [++SID, raw.sid[0] || ++SID].concat(raw.sid.slice(0, -1).map(x => x || ++SID), [++SID, ++SID, ++SID]);
        const P = ccw({ pts, sid, nodes: raw.nodes, arcs: raw.arcs, fil: [], curves: raw.curves });
        const region = { min: blank.min.slice(), max: blank.max.slice() }; region.min[a] = Math.max(lo, blank.min[a]); region.max[a] = Math.min(hi, blank.max[a]);
        out.push({
          kind: 'lathe', keep: true, axis: a, span: [lo, hi], prof: P, center: c, tool: tool || 'lathe', region, vary: [0, 1, 2], src: s,
          removes: q => {
            if (q[a] <= lo || q[a] >= hi) return false;
            return !inPoly([Math.hypot(q[ua] - c[0], q[va] - c[1]), q[a]], P.pts);
          },
          cutter() {
            const slab = { min: big.min.slice(), max: big.max.slice() }; slab.min[a] = lo; slab.max[a] = hi;
            return csgSubtract(boxPolys(slab), lathePolys(P, a, c));
          }
        });
      } else {
        // edge treatments: one small cutout along each edge of the blank
        const r = parseLen(s.roundover != null ? s.roundover : s.chamfer), round = s.roundover != null;
        const ext = [0, 1, 2].map(k => blank.max[k] - blank.min[k]);
        for (const [[fa, sa], [fb, sb]] of edgeList(s.edges, ext)) {
          const a = 3 - fa - fb, [ua, va] = plAxes(a);
          const fu = ua === fa ? sa : sb, fv = va === fa ? sa : sb;   // which side of u and v the edge is on
          const C = [fu > 0 ? blank.max[ua] : blank.min[ua], fv > 0 ? blank.max[va] : blank.min[va]];
          const iu = -fu, iv = -fv, o = 0.05;   // inward along u and v; o: past the face so the cut opens
          const A = [C[0] + iu * r, C[1]], B = [C[0], C[1] + iv * r];
          let spec;
          if (round) spec = [[A[0], C[1] - iv * o], [C[0] - iu * o, C[1] - iv * o], [C[0] - iu * o, B[1]], B, { arc: A, center: [C[0] + iu * r, C[1] + iv * r] }];
          else spec = [[A[0], C[1] - iv * o], [C[0] - iu * o, C[1] - iv * o], [C[0] - iu * o, B[1]], B, A];
          const P = ccw(profile(spec));
          const sp = [blank.min[a] - 1, blank.max[a] + 1];
          const region = { min: blank.min.slice(), max: blank.max.slice() };
          region.min[ua] = Math.max(blank.min[ua], Math.min(C[0], A[0])); region.max[ua] = Math.min(blank.max[ua], Math.max(C[0], A[0]));
          region.min[va] = Math.max(blank.min[va], Math.min(C[1], B[1])); region.max[va] = Math.min(blank.max[va], Math.max(C[1], B[1]));
          out.push({
            kind: round ? 'roundover' : 'chamfer', keep: false, axis: a, span: sp, prof: P, size: r, edge: [[fa, sa], [fb, sb]], tool: tool || (round ? 'router' : 'plane'), region, vary: [ua, va], src: s,
            removes: q => inPoly([q[ua], q[va]], P.pts),
            cutter: () => prismPolys(P, a, sp[0], sp[1])
          });
        }
      }
    }
    for (const sh of out) { const f = sh.cutter; let memo = null; sh.cutter = () => memo || (memo = f()); }
    return out;
  }

  // part coordinates <-> world, for one copy
  function toWorldPt(q, inst) {
    let p = q.slice();
    if (inst.mirror === 'x') p[0] = -p[0];
    if (inst.mirror === 'y') p[1] = -p[1];
    p = rotPt(p, inst.rot);
    const at = inst.at || [0, 0, 0];
    return [p[0] + at[0], p[1] + at[1], p[2] + at[2]];
  }
  function toLocalPt(q, inst) {
    const at = inst.at || [0, 0, 0];
    const p = rotPt([q[0] - at[0], q[1] - at[1], q[2] - at[2]], -(inst.rot || 0));
    if (inst.mirror === 'x') p[0] = -p[0];
    if (inst.mirror === 'y') p[1] = -p[1];
    return p;
  }
  function worldPolys(polys, inst) {
    const flipIt = inst.mirror === 'x' || inst.mirror === 'y';
    const out = [];
    for (const P of polys) { let v = P.v.map(q => toWorldPt(q, inst)); if (flipIt) v = v.reverse(); const Q = poly(v, P.s); if (Q) out.push(Q); }
    return out;
  }
  // does a copy's shaping remove the wood at world point q? (tenons are never trimmed)
  function shapedAway(shp, q, tenons) {
    if (!shp) return false;
    if (tenons && tenons.some(t => inside(q, t))) return false;
    const l = toLocalPt(q, shp.inst);
    return shp.list.some(sh => sh.removes(l));
  }

  // The lattice the checks use: the blank's own planes, plus planes every 1/16" (1/8", 1/4" ... on
  // long curves) through the part of the blank each shape changes, at the same world positions for
  // every part. A cell is wood when its centre is; a cell the shape's boundary crosses is an edge cell.
  function shapedCells(S) {
    const base = S.base, shp = S.shp, G = [base.xs.slice(), base.ys.slice(), base.zs.slice()];
    const regions = [];
    for (const sh of shp.list) {
      if (!sh.region) continue;
      const R = inter(xformAABB(sh.region, shp.inst), base.bbox); if (!R) continue;
      regions.push({ sh, R });
      for (const la of sh.vary) {
        const wa = axisAfterRot(la, shp.inst.rot), lo = R.min[wa], hi = R.max[wa];
        let h = 1 / 16; while ((hi - lo) / h > 96) h *= 2;
        G[wa].push(lo, hi);
        for (let k = Math.ceil(lo / h - 1e-9); k * h < hi - 1e-9; k++) G[wa].push(k * h);
      }
    }
    const C = G.map((g, a) => uniq(g).filter(v => v >= base.bbox.min[a] - EPS && v <= base.bbox.max[a] + EPS));
    const nx = C[0].length - 1, ny = C[1].length - 1, nz = C[2].length - 1;
    // which base cell each lattice step falls in
    const map = C.map((g, a) => { const bg = [base.xs, base.ys, base.zs][a], out = []; let j = 0; for (let i = 0; i < g.length - 1; i++) { const m = (g[i] + g[i + 1]) / 2; while (j < bg.length - 2 && bg[j + 1] <= m) j++; out.push(m > bg[0] && m < bg[bg.length - 1] ? j : -1); } return out; });
    const grid = new Uint8Array(Math.max(0, nx * ny * nz)), edge = new Uint8Array(grid.length);
    const tenons = S.tenons;
    for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) for (let k = 0; k < nz; k++) {
      const bi = map[0][i], bj = map[1][j], bk = map[2][k];
      if (bi < 0 || bj < 0 || bk < 0) continue;
      const o = base.occ(bi, bj, bk); if (!o) continue;
      const lo = [C[0][i], C[1][j], C[2][k]], hi = [C[0][i + 1], C[1][j + 1], C[2][k + 1]];
      const c = [0, 1, 2].map(a => (lo[a] + hi[a]) / 2 + JIT[a]);
      const g = (i * ny + j) * nz + k;
      if (!shapedAway(shp, c, tenons)) grid[g] = o;
      if (o === 2) continue;
      // an edge cell: some corner is on the other side of a shape's boundary
      const inR = regions.some(r => lo.every((v, a) => v < r.R.max[a] + EPS) && hi.every((v, a) => v > r.R.min[a] - EPS));
      if (!inR) continue;
      const here = !grid[g];
      for (let m = 0; m < 8 && !edge[g]; m++) {
        const q = [0, 1, 2].map(a => (m >> a) & 1 ? hi[a] - 1e-4 : lo[a] + 1e-4);
        if (shapedAway(shp, q, tenons) !== here) edge[g] = 1;
      }
    }
    const occ = (i, j, k) => (i < 0 || j < 0 || k < 0 || i >= nx || j >= ny || k >= nz) ? 0 : grid[(i * ny + j) * nz + k];
    // cells, merged along the most divided axis where they are plain wood
    const N = [nx, ny, nz], m = N.indexOf(Math.max(...N)), o1 = (m + 1) % 3, o2 = (m + 2) % 3, cells = [];
    const id = (q) => (q[0] * ny + q[1]) * nz + q[2];
    for (let i1 = 0; i1 < N[o1]; i1++) for (let i2 = 0; i2 < N[o2]; i2++) {
      let run = null;
      const flush = () => { if (run) cells.push(run); run = null; };
      for (let im = 0; im < N[m]; im++) {
        const q = [0, 0, 0]; q[m] = im; q[o1] = i1; q[o2] = i2;
        const g = id(q), v = grid[g];
        if (!v) { flush(); continue; }
        const lo = [C[0][q[0]], C[1][q[1]], C[2][q[2]]], hi = [C[0][q[0] + 1], C[1][q[1] + 1], C[2][q[2] + 1]];
        const e = !!edge[g], t = v === 2;
        if (run && !e && !run.edge && run.tenon === t) { run.max[m] = hi[m]; continue; }
        flush(); run = { min: lo, max: hi, tenon: t, edge: e };
        if (e) flush();
      }
      flush();
    }
    return { xs: C[0], ys: C[1], zs: C[2], nx, ny, nz, occ, cells };
  }

  // the exact surface: the blank's faces, less each shape's cutter, then its crease lines
  function shapedMesh(base, shp, tenons) {
    let polys = [];
    for (const q of boxSurface(base).quads) { const P = poly(q.v, null); if (P) polys.push(P); }
    for (const sh of shp.list) {
      if (!sh.region || !base.bbox) continue;
      let cut = worldPolys(sh.cutter(), shp.inst);
      if (!inter(bboxPolys(cut) || base.bbox, grow3(base.bbox, 1e-3))) continue;
      for (const t of tenons) cut = csgSubtract(cut, boxPolys(grow3(t, 1e-4)));
      polys = csgSubtract(polys, cut);
    }
    // snap, and drop slivers
    const sn = v => Math.round(v * 1e5) / 1e5;
    const out = [];
    for (const P of polys) {
      const v = [];
      for (const q of P.v) { const s = q.map(sn); if (!v.length || len3(sub3(s, v[v.length - 1])) > 1e-6) v.push(s); }
      while (v.length > 2 && len3(sub3(v[0], v[v.length - 1])) < 1e-6) v.pop();
      if (v.length < 3) continue;
      const Q = poly(v, P.s); if (!Q || polyArea(v) < 1e-8) continue;
      Q.n = P.n; Q.w = dot3(P.n, v[0]); out.push(Q);
    }
    return { polys: out, lines: meshLines(out) };
  }
  const len3 = a => Math.hypot(a[0], a[1], a[2]);
  function polyArea(v) { let n = [0, 0, 0]; for (let i = 1; i < v.length - 1; i++) { const a = sub3(v[i], v[0]), b = sub3(v[i + 1], v[0]); n = [n[0] + a[1] * b[2] - a[2] * b[1], n[1] + a[2] * b[0] - a[0] * b[2], n[2] + a[0] * b[1] - a[1] * b[0]]; } return len3(n) / 2; }
  // every polygon edge, gathered by the line it lies on and cut into spans, each with the polygons
  // on it. A span is a crease where two of them turn away from each other (not the facets of one curve).
  function meshLines(polys) {
    // lines are found by tolerance, not by an exact key: the short edges BSP splits off carry a
    // direction good to only a few decimals
    const buckets = new Map(), lines = [];
    const opts = (v, cell, tol) => { const f = v / cell, i = Math.floor(f), r = f - i, o = [i]; if (r < tol / cell) o.push(i - 1); if (r > 1 - tol / cell) o.push(i + 1); return o; };
    const keysOf = (vals, cells, tols) => { let ks = ['']; vals.forEach((v, k) => { const os = opts(v, cells[k], tols[k]); ks = ks.flatMap(x => os.map(o => x + o + ',')); }); return ks; };
    const distTo = (p, L) => { const d = sub3(p, L.o), t = dot3(d, L.u); return len3(sub3(d, L.u.map(x => x * t))); };
    const CELLS = [0.05, 0.05, 0.05, 0.1, 0.1, 0.1], TOLS = [0.01, 0.01, 0.01, 0.02, 0.02, 0.02];
    polys.forEach((P, pi) => {
      for (let i = 0; i < P.v.length; i++) {
        const a = P.v[i], b = P.v[(i + 1) % P.v.length], d = sub3(b, a), l = len3(d);
        if (l < 1e-6) continue;
        let u = d.map(x => x / l);
        const f = u.findIndex(x => Math.abs(x) > 1e-6); if (u[f] < 0) u = u.map(x => -x);
        const o = sub3(a, u.map(x => x * dot3(a, u))), vals = u.concat(o);
        let L = null;
        for (const k of keysOf(vals, CELLS, TOLS)) {
          for (const c of buckets.get(k) || []) if (Math.abs(dot3(c.u, u)) > 1 - 1e-5 && distTo(a, c) < 2e-4 && distTo(b, c) < 2e-4) { L = c; break; }
          if (L) break;
        }
        if (!L) {
          L = { u, o, segs: [] }; lines.push(L);
          const k = vals.map((v, j) => Math.floor(v / CELLS[j])).join(',') + ',';
          (buckets.get(k) || buckets.set(k, []).get(k)).push(L);
        }
        const ta = dot3(sub3(a, L.o), L.u), tb = dot3(sub3(b, L.o), L.u);
        L.segs.push({ t0: Math.min(ta, tb), t1: Math.max(ta, tb), p: pi });
      }
    });
    const spans = [];
    for (const L of lines) {
      const ts = uniq(L.segs.flatMap(s => [s.t0, s.t1]));
      for (let i = 0; i < ts.length - 1; i++) {
        const m = (ts[i] + ts[i + 1]) / 2, ps = [];
        for (const s of L.segs) if (s.t0 < m && s.t1 > m && !ps.includes(s.p)) ps.push(s.p);
        if (ps.length < 2) continue;
        let crease = false;
        for (let x = 0; x < ps.length && !crease; x++) for (let y = x + 1; y < ps.length; y++) {
          const A = polys[ps[x]], B = polys[ps[y]];
          if (A.s && A.s === B.s) continue;
          if (dot3(A.n, B.n) < 0.99995) { crease = true; break; }
        }
        spans.push({ a: L.o.map((v, k) => v + L.u[k] * ts[i]), b: L.o.map((v, k) => v + L.u[k] * ts[i + 1]), ps, crease, t0: ts[i], t1: ts[i + 1], key: L });
      }
    }
    return spans;
  }
  // like: the part's own solid, when this copy is just that solid placed (no mortises of its own yet)
  function shapedSolid(adds, cuts, tenons, shp, like) {
    const base = boxSolid(adds, cuts, tenons);
    const S = { shaped: true, base, shp, tenons };
    if (like && like.mesh && base.bbox) {
      const flipIt = shp.inst.mirror === 'x' || shp.inst.mirror === 'y';
      const polys = like.mesh.polys.map(P => { let v = P.v.map(q => toWorldPt(q, shp.inst)); if (flipIt) v.reverse(); const n = rotPt([shp.inst.mirror === 'x' ? -P.n[0] : P.n[0], shp.inst.mirror === 'y' ? -P.n[1] : P.n[1], P.n[2]], shp.inst.rot); return { v, n, w: dot3(n, v[0]), s: P.s }; });
      S.mesh = { polys, lines: like.mesh.lines.map(l => Object.assign({}, l, { a: toWorldPt(l.a, shp.inst), b: toWorldPt(l.b, shp.inst) })) };
    } else S.mesh = base.bbox ? shapedMesh(base, shp, tenons) : { polys: [], lines: [] };
    S.bbox = bboxPolys(S.mesh.polys);
    if (S.bbox) S.bbox = { min: S.bbox.min.map(v => Math.round(v * 1e6) / 1e6), max: S.bbox.max.map(v => Math.round(v * 1e6) / 1e6) };
    S.blank = base.bbox;
    let lat = null;
    const L = () => lat || (lat = S.bbox ? shapedCells(S) : { xs: [], ys: [], zs: [], nx: 0, ny: 0, nz: 0, occ: () => 0, cells: [] });
    for (const k of ['xs', 'ys', 'zs', 'nx', 'ny', 'nz', 'occ', 'cells']) Object.defineProperty(S, k, { get: () => L()[k], enumerable: false });
    return S;
  }
  function solid(adds, cuts, tenons, shp, like) {
    return shp && shp.list && shp.list.length ? shapedSolid(adds, cuts || [], tenons || [], shp, like) : boxSolid(adds, cuts, tenons);
  }
  // Surface for rendering. Box solids: quads {n: [axis, sign], v: [4 pts]}. Shaped solids: tris
  // {n: [x, y, z] unit normal, v: [3 pts], s: surface id}. Both: crease edges [[p, q], ...].
  function surface(S) {
    if (!S.shaped) { const r = boxSurface(S); r.tris = []; return r; }
    if (S._surf) return S._surf;
    const tris = [];
    for (const P of S.mesh.polys) for (let i = 1; i < P.v.length - 1; i++) tris.push({ n: P.n, v: [P.v[0], P.v[i], P.v[i + 1]], s: P.s });
    const edges = mergeSpans(S.mesh.lines.filter(l => l.crease));
    return (S._surf = { quads: [], tris, edges });
  }
  function mergeSpans(spans) {
    const by = new Map(), out = [];
    for (const s of spans) { const g = by.get(s.key) || []; g.push(s); by.set(s.key, g); }
    for (const g of by.values()) {
      g.sort((p, q) => p.t0 - q.t0);
      let cur = null;
      for (const s of g) { if (cur && Math.abs(s.t0 - cur.t1) < 1e-7) { cur.t1 = s.t1; cur.b = s.b; } else { if (cur) out.push([cur.a, cur.b]); cur = { t0: s.t0, t1: s.t1, a: s.a, b: s.b }; } }
      if (cur) out.push([cur.a, cur.b]);
    }
    return out;
  }
  // What a shaped solid shows a viewer looking along -d (d points at the viewer): its faces that turn
  // toward the viewer, grouped into flat faces and curved surfaces, each with its depth along d (larger
  // is nearer) and the lines drawn on it: creases, and the outline where the surface turns away.
  function faces(S, d) {
    const M = S.mesh, groups = new Map(), gOf = [];
    M.polys.forEach((P, i) => {
      const f = dot3(P.n, d);
      if (f <= 1e-6) { gOf[i] = null; return; }
      const key = P.s ? 's' + P.s : 'p' + P.n.map(x => x.toFixed(3)).join(',') + '|' + P.w.toFixed(4);
      let G = groups.get(key);
      if (!G) groups.set(key, G = { polys: [], norms: [], edges: [], depth: 0, area: 0, n: P.n, flat: !P.s, w: P.w });
      const c = P.v.reduce((s, v) => [s[0] + v[0], s[1] + v[1], s[2] + v[2]], [0, 0, 0]).map(x => x / P.v.length), ar = polyArea(P.v);
      G.depth += dot3(c, d) * ar; G.area += ar; G.polys.push(P.v); G.norms.push(P.n); gOf[i] = G;
    });
    for (const G of groups.values()) G.depth /= G.area || 1;
    for (const l of M.lines) {
      const facing = l.ps.filter(i => gOf[i]);
      if (!facing.length) continue;
      if (!l.crease && facing.length === l.ps.length) continue;
      // a line on a flat face seen edge-on adds nothing
      const g = facing.map(i => gOf[i]).sort((a, b) => b.depth - a.depth)[0];
      g.edges.push([l.a, l.b]);
    }
    return [...groups.values()];
  }

  // ---------- model expansion ----------
  function num3(a) { return a ? a.map(parseLen) : [0, 0, 0]; }
  // Sutherland-Hodgman: a polygon of { p, s } (s = the edge arriving at p) clipped to a rectangle;
  // edges along the rectangle get s = 'R'
  function clipRect(poly, lo, hi) {
    let out = poly;
    for (const [k, v, sg] of [[0, lo[0], 1], [0, hi[0], -1], [1, lo[1], 1], [1, hi[1], -1]]) {
      const inp = out; out = [];
      if (!inp.length) break;
      const ins = q => (q[k] - v) * sg >= -1e-9;
      for (let i = 0; i < inp.length; i++) {
        const c = inp[(i - 1 + inp.length) % inp.length], d = inp[i];
        const cut = () => { const t = (v - c.p[k]) / (d.p[k] - c.p[k]); return [c.p[0] + (d.p[0] - c.p[0]) * t, c.p[1] + (d.p[1] - c.p[1]) * t]; };
        if (ins(d.p)) { if (!ins(c.p)) out.push({ p: cut(), s: 'R' }); out.push(d); }
        else if (ins(c.p)) out.push({ p: cut(), s: d.s });
      }
    }
    return out.filter((q, i) => len2(sub2(q.p, out[(i - 1 + out.length) % out.length].p)) > 1e-7);
  }

  // Every angle and radius a shaped part needs written on its drawings and in its cut list, in part
  // coordinates. For each outline or cutout: the corners where two straight edges meet at anything
  // but a right angle, the angles its straight edges make where they leave the blank's edges (the
  // material's own angle, as the saw or plane sets it), each arc with its radius, rise over chord and
  // centre, and each free curve with the points it passes through. Turnings give their diameters,
  // edge treatments their sizes.
  //   -> { angles: [{ axis, at, deg, r1, r2, bend, ext (which ray carries an edge on past a bend), reach }], arcs: [{ axis, r, rv, circle, c, mid, a, b, rise, chord, sweep, fillet }],
  //        curves: [{ axis, pts }], turned: [{ axis, d, center, beads: [{ r, mid, rise, chord, cove }] }], eased: [{ kind, size, edges }], notes: [text] }
  // (2D points are in the shape's own [u, v], the plan axes other than `axis`; at3() lifts one.)
  function measures(p) {
    const out = { angles: [], arcs: [], curves: [], turned: [], eased: [], splay: [], notes: [] };
    const loc = p.local || {}, shapes = loc.shapes || [];
    if (!shapes.length) return out;
    const body = loc.adds.filter(a => !loc.tenons.includes(a)), blank = unionBox(body.length ? body : loc.adds);
    const DEG = 180 / Math.PI, square = d => Math.abs(d - 90) < 0.05 || d < 0.05;
    const seen = [];
    const addAngle = (A) => {
      if (square(A.deg)) return;
      if (seen.some(q => q.axis === A.axis && len2(sub2(q.at, A.at)) < 1e-3 && Math.abs(q.deg - A.deg) < 0.05)) return;
      seen.push(A); out.angles.push(A);
    };
    for (const sh of shapes) {
      if (sh.kind === 'roundover' || sh.kind === 'chamfer') {
        out.eased.push({ kind: sh.kind, size: sh.size, edges: [].concat(sh.src.edges || 'all') });
        continue;
      }
      if (sh.kind === 'splay') {
        // the sight-line angles, drawn where the stick leaves the top in the front and side views
        const [ax2, ay2] = sh.angles, H = sh.span[1] - sh.span[0];
        if (ax2) addAngle({ axis: 1, at: [sh.top[0], sh.top[2]], deg: Math.abs(ax2), r1: [0, -1], r2: [Math.tan(ax2 * Math.PI / 180), -1].map((v, k, q) => v / Math.hypot(...q)), bend: true, ext: 1, reach: H * 0.5, splay: true });
        if (ay2) addAngle({ axis: 0, at: [sh.top[1], sh.top[2]], deg: Math.abs(ay2), r1: [0, -1], r2: [Math.tan(ay2 * Math.PI / 180), -1].map((v, k, q) => v / Math.hypot(...q)), bend: true, ext: 1, reach: H * 0.5, splay: true });
        out.splay.push({ angles: sh.angles, section: sh.section, stock: sh.stock });
        continue;
      }
      const P = sh.prof, ax = sh.axis;
      if (sh.ease) out.eased.push({ kind: sh.ease.round ? 'roundover' : 'chamfer', size: sh.ease.r, edges: [sh.src.ease.faces ? [].concat(sh.src.ease.faces).join(' and ') + ' profile' : 'profile'] });
      if (sh.kind === 'lathe') {
        const ds = [...new Set(P.nodes.map(q => +(2 * q[0]).toFixed(4)))].sort((x, y) => y - x);
        // beads, coves and rounded ends: arcs in the [radius, along] profile
        const beads = P.arcs.filter(A => A.sweep != null).map(A => ({ r: A.r, mid: A.mid, rise: A.r * (1 - Math.cos(A.sweep / 2)), chord: 2 * A.r * Math.sin(Math.min(A.sweep, Math.PI) / 2), cove: A.mid[0] < (A.a[0] + A.b[0]) / 2 - 1e-6 }));
        out.turned.push({ axis: ax, d: ds, center: sh.center, beads });
        continue;
      }
      const unit = d => { const l = len2(d) || 1; return [d[0] / l, d[1] / l]; };
      const [ua, va] = plAxes(ax), lo = [blank.min[ua], blank.min[va]], hi = [blank.max[ua], blank.max[va]];
      const inRect = q => q[0] >= lo[0] - 1e-4 && q[0] <= hi[0] + 1e-4 && q[1] >= lo[1] - 1e-4 && q[1] <= hi[1] + 1e-4;
      const keep = sh.kind === 'outline', n = P.pts.length;
      const count = {}; for (let i = 0; i < n; i++) count[P.sid[i]] = (count[P.sid[i]] || 0) + 1;
      const straight = id => id === 'R' || (id != null && count[id] === 1);   // the blank's own edges, or a profile's lines
      // the corners of the part as it is cut, each angle measured in the material. The corners are
      // where the profile, clipped to the blank, turns; the material around each is found by
      // stepping a hair along every direction between the edges that meet there. A corner within
      // 15° of straight (where a taper starts) is given as its bend from straight, a notch as the
      // notch's own angle.
      const solidAt = q => q[0] > lo[0] && q[0] < hi[0] && q[1] > lo[1] && q[1] < hi[1] && inPoly(q, P.pts) === keep;
      const Q = clipRect(P.pts.map((q, i) => ({ p: q, s: P.sid[(i - 1 + n) % n] })), lo, hi), m = Q.length;
      for (let i = 0; i < m; i++) {
        const A = Q[(i - 1 + m) % m], V = Q[i], B = Q[(i + 1) % m];
        const rays = [{ d: unit(sub2(A.p, V.p)), ok: straight(V.s), l: len2(sub2(A.p, V.p)) }, { d: unit(sub2(B.p, V.p)), ok: straight(B.s), l: len2(sub2(B.p, V.p)) }];
        for (let k = 0; k < 2; k++) if (Math.abs(V.p[k] - lo[k]) < 1e-4 || Math.abs(V.p[k] - hi[k]) < 1e-4) for (const sg of [1, -1]) { const d = [0, 0], o = 1 - k; d[o] = sg; rays.push({ d, ok: true, side: true, l: sg > 0 ? hi[o] - V.p[o] : V.p[o] - lo[o] }); }
        for (const r of rays) r.t = Math.atan2(r.d[1], r.d[0]);
        rays.sort((x, y) => x.t - y.t);
        const R = rays.filter((r, k) => !k || r.t - rays[k - 1].t > 1e-6);
        if (R.length > 1 && R[0].t + 2 * Math.PI - R[R.length - 1].t < 1e-6) R.pop();
        // sectors between neighbouring rays, solid or not, merged where the solid runs on
        const sec = R.map((r, k) => { const nx = R[(k + 1) % R.length], t1 = nx.t + (k === R.length - 1 ? 2 * Math.PI : 0), tm = (r.t + t1) / 2; return { a: r, b: nx, sw: t1 - r.t, solid: solidAt([V.p[0] + 1e-3 * Math.cos(tm), V.p[1] + 1e-3 * Math.sin(tm)]) }; });
        if (!sec.some(x => x.solid) || sec.every(x => x.solid)) continue;
        const k0 = sec.findIndex((x, k) => x.solid && !sec[(k - 1 + sec.length) % sec.length].solid);
        for (let j = 0; j < sec.length; j++) {
          const k = (k0 + j) % sec.length; if (!sec[k].solid || (j && sec[(k - 1 + sec.length) % sec.length].solid)) continue;
          let sw = 0, e = k; while (sec[e % sec.length].solid && sw < 2 * Math.PI - 1e-9) { sw += sec[e % sec.length].sw; e++; }
          const ra = sec[k].a, rb = sec[(e - 1) % sec.length].b;
          if (!ra.ok || !rb.ok) continue;
          const mat = sw * DEG;
          let deg = mat > 180 ? 360 - mat : mat, r1 = ra.d, r2 = rb.d;
          const bend = deg > 165;
          let ext = 0;
          if (bend) { deg = 180 - deg; if (ra.side || (!rb.side && ra.l >= rb.l)) { r1 = [-ra.d[0], -ra.d[1]]; ext = 1; } else { r2 = [-rb.d[0], -rb.d[1]]; ext = 2; } }
          addAngle({ axis: ax, at: V.p, deg, r1, r2, bend, ext, reach: Math.min(ra.l, rb.l) });
        }
      }
      for (const A of P.arcs) {
        const e = { axis: ax, r: A.r, rv: A.rv, circle: !!A.circle, c: A.c, mid: A.mid, a: A.a, b: A.b, sweep: A.sweep, fillet: !!A.fillet };
        if (!A.circle && A.sweep != null) { e.chord = 2 * A.r * Math.sin(Math.min(A.sweep, Math.PI) / 2); e.rise = A.r * (1 - Math.cos(A.sweep / 2)); }
        if (A.circle || inRect(A.mid) || (A.a && inRect(A.a)) || (A.b && inRect(A.b))) out.arcs.push(e);
      }
      for (const c of P.curves || []) out.curves.push({ axis: ax, pts: c });
    }
    // what the cut list says about the shape, in shop words
    const F = x => fmt(x), D = d => (Math.round(d * 10) / 10) + '°';
    const radii = [...new Set(out.arcs.filter(a => !a.circle && !a.fillet).map(a => 'R ' + F(a.r) + (a.rise != null && a.r > 12 ? ' (rise ' + F(a.rise) + ' over ' + F(a.chord) + ')' : '')))];
    if (radii.length) out.notes.push((radii.length > 1 ? 'Arcs ' : 'Arc ') + radii.join(', '));
    const fil = [...new Set(out.arcs.filter(a => a.fillet).map(a => 'R ' + F(a.r)))];
    if (fil.length) out.notes.push('Rounded corners ' + fil.join(', '));
    const holes = [...new Set(out.arcs.filter(a => a.circle).map(a => a.rv && Math.abs(a.rv - a.r) > 1e-6 ? F(2 * a.r) + ' × ' + F(2 * a.rv) + ' oval' : '⌀' + F(2 * a.r)))];
    if (holes.length) out.notes.push('Round ' + holes.join(', '));
    for (const sp of out.splay) out.notes.push('Splayed ' + sp.angles.map((d, k) => D(Math.abs(d)) + ' ' + ['front view', 'side view'][k]).filter((_, k) => sp.angles[k]).join(', ') + '; cut from ' + F(sp.section[0]) + ' × ' + F(sp.section[1]) + ' stock ' + F(Math.ceil(sp.stock * 16) / 16) + ' long, ends cut level');
    const degs = [...new Set(out.angles.filter(a => !a.bend).map(a => D(a.deg)))], tapers = [...new Set(out.angles.filter(a => a.bend && !a.splay).map(a => D(a.deg)))];
    if (degs.length) out.notes.push((degs.length > 1 ? 'Angles ' : 'Angle ') + degs.join(', '));
    if (tapers.length) out.notes.push((tapers.length > 1 ? 'Tapers ' : 'Taper ') + tapers.join(', '));
    if (out.curves.length) out.notes.push(out.curves.length === 1 ? 'Fair curve through ' + out.curves[0].pts.length + ' marked points' : out.curves.length + ' fair curves through marked points');
    for (const t of out.turned) {
      out.notes.push('Turned, ⌀' + t.d.map(F).join(' / '));
      const bs = [...new Set(t.beads.map(b => (b.cove ? 'cove' : 'bead') + ' R ' + F(b.r)))];
      if (bs.length) out.notes.push(bs.join(', ').replace(/^./, c => c.toUpperCase()));
    }
    for (const e of out.eased) out.notes.push(F(e.size) + (e.kind === 'roundover' ? ' (R ' + F(e.size) + ') round-over' : ' × 45° chamfer') + ', ' + e.edges.join(' and ') + ' edges');
    out.notes = [...new Set(out.notes)];
    return out;
  }
  const at3 = (axis, q, w) => { const r = [w || 0, w || 0, w || 0], [ua, va] = plAxes(axis); r[ua] = q[0]; r[va] = q[1]; return r; };

  function normalize(plan) {
    const parts = (plan.parts || []).map((p, pi) => {
      const shape = p.shape || [];
      const loc = { adds: [], cuts: [], tenons: [] };
      for (const s of shape) {
        if (s.box) { const a = toAABB(s.box.map(parseLen)); loc.adds.push(a); if (s.role === 'tenon') loc.tenons.push(Object.assign(a, { through: !!s.through })); }
        if (s.cut) loc.cuts.push(Object.assign(toAABB(s.cut.map(parseLen)), s.tool ? { tool: s.tool } : {}));
      }
      // curves, angles and turnings (outline, cutout, lathe, roundover, chamfer), in part coordinates
      loc.shapes = compileShapes(p, loc);
      loc.shp = loc.shapes.length ? { list: loc.shapes, inst: { at: [0, 0, 0], rot: 0 } } : null;
      const localSolid = solid(loc.adds, loc.cuts, loc.tenons, loc.shp);
      const instances = (p.instances && p.instances.length ? p.instances : [{ at: [0, 0, 0] }]).map((ins, ii) => {
        const inst = { at: num3(ins.at), rot: ins.rot || 0, mirror: ins.mirror, explode: num3(ins.explode), label: ins.label };
        const adds = loc.adds.map(a => xformAABB(a, inst));
        const cuts = loc.cuts.map(a => xformAABB(a, inst));
        const tenons = loc.tenons.map(a => Object.assign(xformAABB(a, inst), { through: a.through }));
        const shp = loc.shp ? { list: loc.shapes, inst: { at: inst.at, rot: inst.rot, mirror: inst.mirror } } : null;
        const S = solid(adds, cuts, tenons, shp, localSolid);
        return Object.assign(inst, { index: ii, adds, cuts, tenons, shp, solid: S, bbox: S.bbox, key: p.id + '#' + ii });
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
    const mortises = cutMortises(plan, parts, byId);
    return { plan, parts, byId, mortises };
  }

  // world box -> part coordinates of instance I (the inverse of xformAABB)
  function toLocal(a, inst) {
    const xs = [], ys = [];
    for (const cx of [a.min[0], a.max[0]]) for (const cy of [a.min[1], a.max[1]]) {
      const p = rotPt([cx - inst.at[0], cy - inst.at[1], 0], -(inst.rot || 0));
      if (inst.mirror === 'x') p[0] = -p[0];
      if (inst.mirror === 'y') p[1] = -p[1];
      xs.push(p[0]); ys.push(p[1]);
    }
    const r = v => Math.round(v * 1e6) / 1e6;
    return { min: [r(Math.min(...xs)), r(Math.min(...ys)), r(a.min[2] - inst.at[2])], max: [r(Math.max(...xs)), r(Math.max(...ys)), r(a.max[2] - inst.at[2])] };
  }

  // Mortises: a tenon entering a part it is declared joined to is cut out of that part, so every
  // tenon has its mortise, sized to it, in the drawings, the 3D view and the sections. The plan only
  // models the tenon (J.mortiseTenon). Each copy gets its own mortises (corner legs differ); the
  // part's own drawing shows the first copy's. The check still looks at the wood before mortising
  // (I.pre), so a tenon must sit in solid wood of a joined part, and one that enters a part with no
  // joint declared stays an error.
  function cutMortises(plan, parts, byId) {
    const joined = new Set();
    for (const j of plan.joints || []) {
      const ids = (j.parts || []).map(String);
      for (const a of ids) for (const b of ids) if (a !== b) joined.add(a + '~' + b);
    }
    const out = [];
    const withTenons = parts.filter(p => p.local.tenons.length && p.shape && p.shape.length);
    for (const p of parts) {
      if (!p.shape || !p.shape.length || p.isHardware) { for (const I of p.instances) I.pre = I.solid; continue; }
      const body = p.local.adds.filter(a => !p.local.tenons.includes(a));
      for (const I of p.instances) {
        I.pre = I.solid;
        const bodyW = body.map(a => xformAABB(a, I)), mine = [];
        for (const q of withTenons) {
          if (q === p || !joined.has(q.id + '~' + p.id)) continue;
          for (const Q of q.instances) for (const T of Q.tenons) {
            if (!I.bbox || !inter(T, I.bbox)) continue;
            for (const a of bodyW) {
              const x = inter(T, a);
              if (!x || I.cuts.some(c => !c.mortise && x.min.every((v, k) => v >= c.min[k] - EPS && x.max[k] <= c.max[k] + EPS))) continue;
              const m = Object.assign(x, { mortise: true, tenon: q.id, through: !!T.through });
              mine.push(m); out.push({ host: p.id, inst: I.index, guest: q.id, guestInst: Q.index, box: x, tenon: T });
            }
          }
        }
        if (!mine.length) continue;
        I.cuts = I.cuts.concat(mine);
        I.solid = solid(I.adds, I.cuts, I.tenons, I.shp);
        I.bbox = I.solid.bbox;
        if (I.index === 0) {
          p.local.cuts = p.local.cuts.concat(mine.map(m => Object.assign(toLocal(m, I), { mortise: true, tenon: m.tenon, through: m.through })));
          p.localSolid = solid(p.local.adds, p.local.cuts, p.local.tenons, p.local.shp);
        }
      }
    }
    return out;
  }

  // ---------- checks ----------
  function overlapVol(A, B, onlyTenonA) {
    if (!A.bbox || !B.bbox || !inter(A.bbox, B.bbox)) return 0;
    let v = 0;
    for (const a of A.cells) { if (onlyTenonA && !a.tenon) continue; if (a.edge) continue; for (const b of B.cells) { if (b.edge) continue; const x = inter(a, b); if (x) v += vol(x); } }
    return v;
  }
  function overlapTenons(A, B) {
    if (!A.bbox || !B.bbox || !inter(A.bbox, B.bbox)) return 0;
    let v = 0;
    for (const a of A.cells) { if (!a.tenon || a.edge) continue; for (const b of B.cells) { if (!b.tenon || b.edge) continue; const x = inter(a, b); if (x) v += vol(x); } }
    return v;
  }
  function contactArea(A, B) {
    if (!A.bbox || !B.bbox) return 0;
    for (let i = 0; i < 3; i++) if (A.bbox.min[i] > B.bbox.max[i] + EPS || B.bbox.min[i] > A.bbox.max[i] + EPS) return 0;
    let area = 0;
    for (const a of A.cells) for (const b of B.cells) {
      // a curve or angle passes through one of them: overlap there is the lattice, so it counts as contact
      if (a.edge || b.edge) { const x = inter(a, b); if (x) { const e = [0, 1, 2].map(k => x.max[k] - x.min[k]); area += vol(x) / Math.max(Math.min(...e), 1e-6); continue; } }
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
      if (!p.localSolid.bbox) { err('empty', name(p) + ' cuts remove all material.', [p.id]); continue; }
      const sp = p.local.shapes.find(sh => sh.kind === 'splay');
      if (sp) {
        // a splayed leg is cut from its own stick: the section, and at least the length it runs
        const sec = sp.section.slice().sort((a, c) => a - c), tw = [p.t, p.w].sort((a, c) => a - c);
        if (sec.some((v, i) => Math.abs(v - tw[i]) > cfg.tol) || !(p.l >= sp.stock - cfg.tol))
          err('dims', name(p) + ': cut list says ' + [p.t, p.w, p.l].map(v => fmt(v)).join(' x ') + ' but the splayed leg is cut from ' + fmt(sp.section[0]) + ' x ' + fmt(sp.section[1]) + ' stock at least ' + fmt(Math.ceil(sp.stock * 16) / 16) + ' long.', [p.id]);
        else dimsOK++;
        continue;
      }
      const b = p.localSolid.blank || p.localSolid.bbox;   // shaped parts list the blank they are cut from
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
        if (c.mortise || !inter(a, c)) continue;
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
      const SA = A.i.pre, SB = B.i.pre;
      if (!SA.bbox || !SB.bbox) continue;
      const ov = overlapVol(SA, SB);
      if (ov > 1e-5) {
        const tA = overlapVol(SA, SB, true), tB = overlapVol(SB, SA, true);
        const declared = A.p.id === B.p.id ? [] : jointFor(A.p.id, B.p.id);
        if ((tA + tB) > 1e-5 && !declared.length) err('tenon-undeclared', 'A tenon of ' + name(tA ? A.p : B.p) + ' enters ' + name(tA ? B.p : A.p) + ' but no joint between them is declared.', [A.p.id, B.p.id]);
        const tt = overlapTenons(SA, SB);
        if (tt > 1e-5) err('tenon-clash', 'Tenons of ' + name(A.p) + ' (' + (A.i.index + 1) + ') and ' + name(B.p) + ' (' + (B.i.index + 1) + ') run into each other inside the part they share (' + tt.toFixed(3) + ' cu in). Shorten them or move one so each has its own mortise.', [A.p.id, B.p.id]);
        const resid = ov - tA - tB;
        if (resid > 1e-4) {
          interf++;
          const where = (() => { for (const a of SA.cells) for (const b of SB.cells) { const z = inter(a, b); if (z && !a.tenon && !b.tenon && !a.edge && !b.edge) return fmtBox(z); } return ''; })();
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
      const S = I.pre;
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
          const p = M.byId[id]; const cuts = p ? p.local.cuts.filter(c => !c.mortise) : []; if (cuts.length < 2) continue;
          const b = p.localSolid.bbox, wmin = Math.min(b.max[0] - b.min[0], b.max[1] - b.min[1]);
          for (const a of p.local.adds) for (const c of cuts) for (let ax = 0; ax < 2; ax++) {
            for (const w of [c.min[ax] - a.min[ax], a.max[ax] - c.max[ax]]) if (w > EPS && w < wmin / 4 - EPS) warn('castle-tower', name(p) + ': castle towers are ' + fmt(w) + ' on a ' + fmt(wmin) + ' post. Below a quarter of the post they snap off when a rail is dropped in.', [id]);
          }
        }
      }
    }

    // 8b. every joint has its mating half: a tenon joint has a tenon in a mortise, a housed joint a
    // cut in one part that another part of the joint fills, a dowel joint its bores
    const TENON = /tenon/, HOUSED = /^(dado|groove|rabbet|housed|housing|bridle|castle|half-lap|lap|notch|slot)$/;
    let paired = 0, pairedOf = 0;
    for (const j of joints) {
      const ps = j.parts.filter(id => M.byId[id] && M.byId[id].shape && M.byId[id].shape.length);
      if (ps.length < 2) continue;
      if (TENON.test(j.type)) {
        pairedOf++;
        if (M.mortises.some(m => ps.includes(m.host) && ps.includes(m.guest))) paired++;
        else err('joint-no-mortise', 'Joint ' + j.id + ' (' + j.type + ') joins ' + ps.map(id => '#' + id).join(', ') + ', but no tenon of one enters another, so there is no mortise to cut and the parts only butt together. Model the tenons with J.mortiseTenon, or call the joint what it is.', ps);
      } else if (HOUSED.test(j.type)) {
        pairedOf++;
        let found = false;
        for (const a of ps) for (const b of ps) {
          if (found || a === b) continue;
          for (const IA of M.byId[a].instances) for (const IB of M.byId[b].instances) {
            if (found) break;
            for (const c of IA.cuts) {
              if (c.mortise || !inter(c, IB.pre.bbox || c)) continue;
              if (IB.pre.cells.some(cell => inter(cell, c))) { found = true; break; }
            }
          }
        }
        if (found) paired++;
        else err('joint-no-housing', 'Joint ' + j.id + ' (' + j.type + ') joins ' + ps.map(id => '#' + id).join(', ') + ', but no part in it is cut to take another: the ' + j.type + ' is missing from the model. Cut it with the J helper (J.' + (j.type === 'half-lap' ? 'halfLap' : j.type) + ') or call the joint what it is.', ps);
      } else if (/dowel/.test(j.type)) {
        pairedOf++;
        if ((plan.bores || []).some(b => b.joint === j.id)) paired++;
        else warn('joint-no-bore', 'Joint ' + j.id + ' (' + j.type + ') has no bores in plan.bores, so the dowel holes in ' + ps.map(id => '#' + id).join(' and ') + ' are not drawn or checked to line up. Add a bore with joint: \'' + j.id + '\' through both parts.', ps);
      }
    }
    if (pairedOf && paired === pairedOf) pass('joint-pairs', paired + ' of ' + pairedOf + ' tenon, housed and dowel joints have both halves modeled: ' + M.mortises.length + ' mortises cut to their tenons, slots and dados filled by their mating part.');

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

    // 11b. drawers (plan.drawers): box, slide and front against the slide maker's numbers
    out.stats.drawers = drawerChecks(M, plan, err, warn, pass);

    // 11c. doors (plan.doors): leaves and hinges against the hinge maker's overlay and reveal tables
    out.stats.doors = doorChecks(M, plan, err, warn, pass);

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
        if (I.adds.some(a => inside(q, a)) && !I.cuts.some(c => inside(q, c)) && !shapedAway(I.shp, q, I.tenons)) return { p, I };
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

  // ---------- drawers: slide catalogue, sizing and checks (references/drawers.md) ----------
  // Inches. side: clearance per side [min, max]; under: k = opening − inside width, side thickness
  // range, h = opening − max box height, below/above = room under and over the box, recess = bottom
  // underside above the side's bottom edge, len(NL) = box length, depth(NL) = min inside depth.
  const MM = 1 / 25.4, EVEN = (a, b) => { const o = []; for (let v = a; v <= b; v += 2) o.push(v); return o; };
  const SLIDES = {
    'accuride-3832': { kind: 'side', name: 'Accuride 3832 full-extension ball-bearing slide', clear: [0.5, 0.531], height: 1.8, minH: 1.875, lengths: EVEN(10, 28), load: '100 lb', maxW: L => L, setback: 0.125, screws: '#8 pan-head or 6 mm Euro', source: 'Accuride 3832EC technical sheet' },
    'kv-8400': { kind: 'side', name: 'Knape & Vogt 8400 full-extension ball-bearing slide', clear: [0.5, 0.53], height: 1.79, minH: 2, lengths: EVEN(8, 28), load: '100 lb', maxW: () => 24, setback: 0.125, screws: '#7 × 1/2" pan-head', source: 'Knape & Vogt 8400 spec sheet' },
    'accuride-3640': { kind: 'side', name: 'Accuride 3640 over-travel ball-bearing slide', clear: [0.89, 0.92], height: 2.09, minH: 2.75, lengths: EVEN(12, 28), load: '200 lb', setback: 0.125, screws: '#10 flat-head or 6 mm Euro', source: 'Accuride 3640-A quick reference' },
    'accuride-9301': { kind: 'side', name: 'Accuride 9301 heavy-duty slide', clear: [0.75, 0.781], height: 3, minH: 3.5, lengths: EVEN(10, 36).concat([40, 42, 44, 48, 60]), load: 'to 500 lb', setback: 0.125, screws: '1/4" or #10', source: 'Accuride 9301 data sheet' },
    'fulterer-fr5400': { kind: 'side', name: 'Fulterer FR5400 heavy-duty slide', clear: [0.77, 0.79], height: 3, minH: 4, lengths: EVEN(12, 60), load: '450 lb', setback: 0.125, screws: 'every cabinet-member hole', source: 'Fulterer FR5400 specifications' },
    'generic-half': { kind: 'side', name: '1/2" ball-bearing slide (Accuride 3832 class)', clear: [0.5, 0.531], height: 1.8, minH: 1.875, lengths: EVEN(10, 28), load: '75–100 lb', setback: 0.125, screws: '#8 pan-head', source: 'typical; check your slide\'s sheet' },
    'blum-tandem-563h': { kind: 'under', name: 'Blum Tandem plus Blumotion 563H', k: 42 * MM, side: [12 * MM, 16 * MM], h: 21 * MM, below: 14 * MM, above: 7 * MM, recess: 13 * MM, notch: [35 * MM, 13 * MM], lengths: [9, 12, 15, 18, 21], len: L => L, depth: L => L + 0.9375, minIn: 170 * MM, load: '100 lb', setback: 0.125, source: 'Blum 563H specifications' },
    'blum-tandem-563f': { kind: 'under', name: 'Blum Tandem 563F (3/4" sides)', k: 49 * MM, side: [0.5, 0.75], h: 20 * MM, below: 14 * MM, above: 6 * MM, recess: 13 * MM, notch: [35 * MM, 13 * MM], lengths: [9, 12, 15, 18, 21], len: L => L, depth: L => L + 0.9375, minIn: 170 * MM, load: '100 lb', setback: 0.125, source: 'Blum Tandem 563F, Woodworker Express' },
    'blum-movento-760h': { kind: 'under', name: 'Blum Movento 760H', k: 42 * MM, side: [0.5, 0.625], h: 21 * MM, below: 14 * MM, above: 7 * MM, recess: 12 * MM, notch: [35 * MM, 13 * MM], lengths: null, len: L => L - 10 * MM, depth: null, minIn: 170 * MM, setback: 0.125, source: 'Blum, Building a Movento drawer' },
    'kv-muv-plus': { kind: 'under', name: 'Knape & Vogt MuV+ undermount', k: 42 * MM, side: [0.5, 0.625], h: 0.8125, below: 0.5625, above: 0.25, recess: 0.5, notch: [1.375, 0.5], lengths: [9, 10, 12, 14, 15, 16, 18, 20, 21, 22], len: L => L, depth: L => L + 2, load: '75 lb', maxW: (L, H) => Math.min(L + 10, H > 10 ? 21 : H > 8 ? 24 : H > 6 ? 28 : Infinity), setback: 0.125, source: 'Knape & Vogt MuV+ spec sheet' },
    'kv-muv-plus-34': { kind: 'under', name: 'Knape & Vogt MuV+34 undermount (3/4" sides)', k: 50 * MM, side: [0.625, 0.75], h: 0.8125, below: 0.5625, above: 0.25, recess: 0.5, notch: [1.375, 0.5], lengths: [9, 10, 12, 14, 15, 16, 18, 20, 21, 22], len: L => L, depth: L => L + 2, load: '75 lb', maxW: (L, H) => Math.min(L + 10, H > 10 ? 21 : H > 8 ? 24 : H > 6 ? 28 : Infinity), setback: 0.125, source: 'Knape & Vogt MuV+ spec sheet' },
    'hettich-quadro-iw21': { kind: 'under', name: 'Hettich Quadro, installation width 21', k: 42 * MM, side: [0.5, 0.63], h: 20 * MM, below: 14 * MM, above: 6 * MM, recess: 0.5, notch: [35 * MM, 13 * MM], lengths: [9, 12, 15, 18, 21], len: L => L, depth: L => ({ 15: 16.75, 18: 19.75, 21: 22.75 })[L] || L + 1.75, minIn: 165 * MM, setback: 0.125, source: 'Hettich Quadro FAQ' },
    'hettich-quadro-iw25': { kind: 'under', name: 'Hettich Quadro, installation width 25', k: 50 * MM, side: [0.7, 0.75], h: 20 * MM, below: 14 * MM, above: 6 * MM, recess: 0.5, notch: [35 * MM, 13 * MM], lengths: [9, 12, 15, 18, 21], len: L => L, depth: L => ({ 15: 16.75, 18: 19.75, 21: 22.75 })[L] || L + 1.75, minIn: 165 * MM, setback: 0.125, source: 'Hettich Quadro FAQ' },
    'accuride-1029': { kind: 'center', name: 'Accuride 1029 centre-mount slide, 3/4 extension', play: [0.0625, 0.25], below: 0.25, lengths: EVEN(13, 27).concat([14, 16, 18, 20, 22, 24, 26]).sort((a, b) => a - b), load: '35 lb', setback: 0.125, source: 'Accuride 1029 data sheet' },
    'wood-runners': { kind: 'wood', name: 'Wood runners and kickers (fitted drawer)', play: [1 / 64, 1 / 16], source: 'Fine Woodworking, fitted drawers' }
  };
  // a drawer's slide: a catalogue key, or an object (optionally { like: key, ...overrides })
  function slideSpec(s) {
    if (typeof s === 'string') return SLIDES[s] ? Object.assign({ key: s }, SLIDES[s]) : null;
    if (s && typeof s === 'object') {
      const base = s.like && SLIDES[s.like] ? SLIDES[s.like] : {};
      const o = Object.assign({ key: s.like || 'custom' }, base, s);
      for (const k of ['clear', 'side', 'play', 'notch']) if (Array.isArray(o[k])) o[k] = o[k].map(parseLen);
      for (const k of ['k', 'h', 'below', 'above', 'recess', 'height', 'minH', 'setback']) if (o[k] != null) o[k] = parseLen(o[k]);
      if (typeof o.len !== 'function') { const d = o.len != null ? parseLen(o.len) : 0; o.len = L => L - d; }
      if (o.depth != null && typeof o.depth !== 'function') { const d = parseLen(o.depth); o.depth = L => L + d; }
      return o;
    }
    return null;
  }
  // the size a box should be for an opening and slide: what the designer aims for
  function drawerSize(open, s, o) {
    o = o || {};
    const W = parseLen(open.w), H = parseLen(open.h), D = parseLen(open.d), ts = o.side != null ? parseLen(o.side) : 0.5;
    const r64 = v => Math.round(v * 64) / 64, f16 = v => Math.floor(v * 16 + 1e-6) / 16;
    const inset = o.inset != null ? parseLen(o.inset) : 0, set = s.setback != null ? s.setback : 0.125;
    const room = D - set - inset;
    const L = o.length != null ? parseLen(o.length) : (s.lengths || []).filter(l => (s.kind === 'under' ? (s.depth ? s.depth(l) <= D - inset : s.len(l) <= room) : l <= room - 0.25)).pop();
    if (s.kind === 'side') { const c = (s.clear[0] + s.clear[1]) / 2; return { w: r64(W - 2 * c), h: f16(H - 0.25 - 0.25), d: L, length: L, clear: c }; }
    if (s.kind === 'under') { const wi = W - s.k; return { w: r64(wi + 2 * ts), inside: r64(wi), h: f16(H - s.h), d: L != null ? r64(s.len(L)) : null, length: L }; }
    if (s.kind === 'center') return { w: r64(W - 0.125), h: f16(H - 0.5), d: L, length: L };
    return { w: r64(W - 1 / 32), h: f16(H - 0.125), d: f16(D - 0.375), length: null };
  }
  const ctr = b => [0, 1, 2].map(a => (b.min[a] + b.max[a]) / 2);
  const within = (q, lo, hi, pad) => q.every((v, a) => v >= lo[a] - pad[a] && v <= hi[a] + pad[a]);
  const union = list => list.reduce((u, b) => u ? { min: u.min.map((v, k) => Math.min(v, b.min[k])), max: u.max.map((v, k) => Math.max(v, b.max[k])) } : { min: b.min.slice(), max: b.max.slice() }, null);
  // measure every declared drawer opening from the model; one row per opening, checks along the way
  function drawerChecks(M, plan, err, warn, pass) {
    const rows = [];
    const ids = v => [].concat(v == null ? [] : v).map(String);
    const insts = (list, lo, hi, pad) => {
      const out = [];
      for (const id of list) { const p = M.byId[id]; if (!p) continue; for (const I of p.instances) if (I.bbox && within(ctr(I.bbox), lo, hi, pad)) out.push({ p, I, b: I.bbox }); }
      return out;
    };
    (plan.drawers || []).forEach((d, di) => {
      const nm = d.name || 'Drawer ' + (di + 1), s = slideSpec(d.slide);
      if (!s) { err('drawer-slide', nm + ': slide "' + (typeof d.slide === 'string' ? d.slide : '?') + '" is not in the catalogue (' + Object.keys(SLIDES).join(', ') + '). Name one, or give the maker\'s numbers as an object.'); return; }
      const op = d.opening || {}, W = parseLen(op.w), H = parseLen(op.h), D = parseLen(op.d);
      const ats = Array.isArray(op.at && op.at[0]) ? op.at : [op.at || [0, 0, 0]];
      const L = d.length != null ? parseLen(d.length) : null;
      const boxIds = ids(d.box), slideIds = ids(d.slides), front = d.front || {}, frontIds = ids(front.part);
      const style = front.style || 'overlay';
      // a drawer may accept a maker's recommendation it departs from, with the reason (never an error)
      const waived = new Set(), warn0 = warn;
      warn = (code, msg, parts) => { const why = d.waive && d.waive[code]; if (!why) return warn0(code, msg, parts); if (!waived.has(code)) { waived.add(code); pass(code, msg.replace(/^[^:]*\(\d+ of \d+\): /, nm + ': ') + ' Accepted: ' + why); } };
      ats.forEach((at0, k) => {
        const at = at0.map(parseLen), lo = at, hi = [at[0] + W, at[1] + D, at[2] + H];
        const tag = nm + (ats.length > 1 ? ' (' + (k + 1) + ' of ' + ats.length + ')' : '');
        const box = insts(boxIds, lo, hi, [0, 1.5, 0]);
        const row = { name: nm, index: k, count: ats.length, slide: s, length: L, style, opening: { at, w: W, h: H, d: D }, parts: boxIds };
        rows.push(row);
        if (!box.length) { err('drawer-no-box', tag + ': no box part (' + boxIds.map(i => '#' + i).join(', ') + ') sits in the opening at ' + at.map(v => fmt(v)).join(', ') + '.', boxIds); return; }
        const B = union(box.map(x => x.b)), bw = B.max[0] - B.min[0], bh = B.max[2] - B.min[2], bd = B.max[1] - B.min[1];
        const sides = box.filter(x => (x.b.max[0] - x.b.min[0]) < 1.25 && (x.b.max[1] - x.b.min[1]) > bd * 0.6 && (x.b.max[2] - x.b.min[2]) > 0.75);
        const ts = sides.length ? Math.min(...sides.map(x => x.b.max[0] - x.b.min[0])) : null;
        const flat = box.filter(x => (x.b.max[2] - x.b.min[2]) < 0.8 && (x.b.max[0] - x.b.min[0]) > bw * 0.6).sort((a, c) => a.b.min[2] - c.b.min[2])[0];
        const recess = flat ? flat.b.min[2] - B.min[2] : null;
        const cl = [B.min[0] - lo[0], hi[0] - B.max[0]], below = B.min[2] - lo[2], above = hi[2] - B.max[2], rear = hi[1] - B.max[1];
        Object.assign(row, { box: { w: bw, h: bh, d: bd, side: ts, inside: ts != null ? bw - 2 * ts : null, recess, at: B.min }, clear: { left: cl[0], right: cl[1], below, above, rear, front: B.min[1] - lo[1] } });
        const tol = 1 / 128, eq = (a, b, t) => Math.abs(a - b) <= (t || 1 / 64);
        const fm = v => fmt(v) + ' (' + String(Math.round(v * 25.4 * 2) / 2) + ' mm)';   // undermount makers work in mm
        if (s.kind === 'side') {
          const bad = cl.filter(c => c < s.clear[0] - tol || c > s.clear[1] + tol);
          if (bad.length) err('drawer-clearance', tag + ': the ' + s.name + ' needs ' + fmt(s.clear[0]) + '–' + fmt(s.clear[1]) + ' between the box and the opening on each side, but the model leaves ' + cl.map(v => fmt(v)).join(' and ') + '. Box width should be ' + fmt(W - s.clear[0] - s.clear[1]) + ' (opening ' + fmt(W) + ' − 2 × ' + fmt((s.clear[0] + s.clear[1]) / 2) + '), not ' + fmt(bw) + '.', boxIds);
          else if (!eq(cl[0], cl[1], 1 / 32)) warn('drawer-centred', tag + ': the box is off centre in its opening (' + fmt(cl[0]) + ' left, ' + fmt(cl[1]) + ' right); both slides need the same gap.', boxIds);
          if (s.minH && bh < s.minH - tol) err('drawer-height', tag + ': a ' + fmt(bh) + ' box is shorter than the ' + fmt(s.minH) + ' this slide needs.', boxIds);
        } else if (s.kind === 'under') {
          const want = W - s.k;
          if (ts != null && !eq(bw - 2 * ts, want, 1 / 32)) err('drawer-inside-width', tag + ': the ' + s.name + ' needs an inside width of opening − ' + fm(s.k) + ' = ' + fmt(want) + ', but the box is ' + fmt(bw - 2 * ts) + ' inside (' + fmt(bw) + ' outside with ' + fmt(ts) + ' sides). Box width should be ' + fmt(want + 2 * ts) + '.', boxIds);
          if (ts != null && (ts > s.side[1] + tol || ts < s.side[0] - tol)) err('drawer-side-thickness', tag + ': ' + fmt(ts) + ' box sides; the ' + s.name + ' takes ' + fm(s.side[0]) + ' to ' + fm(s.side[1]) + '.', boxIds);
          if (bh > H - s.h + tol) err('drawer-height', tag + ': a ' + fmt(bh) + ' box is too tall for a ' + fmt(H) + ' opening on this slide (at most opening − ' + fm(s.h) + ' = ' + fmt(H - s.h) + ').', boxIds);
          if (below < s.below - tol) err('drawer-under', tag + ': the box sits ' + fmt(below) + ' above the opening floor; the runner needs ' + fm(s.below) + ' under it.', boxIds);
          if (recess != null && s.recess && recess < s.recess - tol) err('drawer-recess', tag + ': the bottom is ' + fm(recess) + ' up from the bottom of the sides; this slide needs it at least ' + fm(s.recess) + ' up so the runner fits underneath.', boxIds);
          if (L != null && !eq(bd, s.len(L), 1 / 16)) err('drawer-length', tag + ': a ' + fmt(L) + ' ' + s.name + ' needs a box ' + fmt(s.len(L)) + ' long; the model\'s is ' + fmt(bd) + '.', boxIds);
          if (L != null && s.depth && D < s.depth(L) - tol) err('drawer-depth', tag + ': a ' + fmt(L) + ' runner needs at least ' + fmt(s.depth(L)) + ' inside the cabinet; the opening is ' + fmt(D) + ' deep. Use a shorter runner.', boxIds);
          if (s.minIn && ts != null && bw - 2 * ts < s.minIn) warn('drawer-narrow', tag + ': ' + fmt(bw - 2 * ts) + ' inside is narrower than the ' + fmt(s.minIn) + ' the locking devices need.', boxIds);
          if (s.notch) row.notch = s.notch;
        } else if (s.kind === 'center' || s.kind === 'wood') {
          const play = W - bw;
          if (play < s.play[0] - tol || play > s.play[1] + tol) warn('drawer-play', tag + ': ' + fmt(play) + ' of side play in total; a ' + (s.kind === 'wood' ? 'fitted drawer on wood runners' : 'centre-mount drawer') + ' wants ' + fmt(s.play[0]) + '–' + fmt(s.play[1]) + '.', boxIds);
        }
        if (s.kind !== 'under') {
          if (below < -tol || above < -tol) err('drawer-height', tag + ': the box runs outside its opening (' + fmt(below) + ' below, ' + fmt(above) + ' above).', boxIds);
          else if (s.kind !== 'wood' && (below < 0.125 - tol || above < 0.125 - tol)) warn('drawer-gap', tag + ': the box is ' + fmt(below) + ' over the surface below and ' + fmt(above) + ' under the one above; leave at least 1/8" (1/4" is usual) so it runs free.', boxIds);
        }
        // slides: the right number, the right length, inside the case
        if (s.kind !== 'wood') {
          const sl = insts(slideIds, lo, hi, [1, 1, 0.5]);
          const need = s.kind === 'center' ? 1 : 2;
          if (!slideIds.length) warn('drawer-no-slides', tag + ': no slide part is named, so the slides are not on the material list or in the model.', boxIds);
          else if (sl.length !== need) err('drawer-slides', tag + ': the model has ' + sl.length + ' slide' + (sl.length === 1 ? '' : 's') + ' in this opening; it needs ' + need + '.', slideIds);
          const sb = sl.length ? union(sl.map(x => x.b)) : null, slen = sb ? sb.max[1] - sb.min[1] : null;
          if (L != null && sb && !eq(slen, L, 1 / 8)) warn('drawer-slide-length', tag + ': the slide is modeled ' + fmt(slen) + ' long but the drawer names a ' + fmt(L) + ' slide.', slideIds);
          if (L != null && s.lengths && !s.lengths.some(l => eq(l, L))) warn('drawer-slide-length', tag + ': ' + s.name + ' does not come in ' + fmt(L) + '; it comes in ' + s.lengths.map(l => fmt(l, { unit: false })).join(', ') + '.', slideIds);
          if (s.kind === 'side' && L != null) {
            if (bd < L - 1 / 16) err('drawer-length', tag + ': the box is ' + fmt(bd) + ' long, shorter than its ' + fmt(L) + ' slide; the drawer member needs the full length of the box side.', boxIds);
            if (sb && sb.max[1] > hi[1] + tol) err('drawer-depth', tag + ': the slide runs ' + fmt(sb.max[1] - hi[1]) + ' past the back of the opening. Use a shorter slide.', slideIds);
            else if (!sb && (s.setback || 0) + L > D + tol) err('drawer-depth', tag + ': a ' + fmt(L) + ' slide set back ' + fmt(s.setback || 0) + ' does not fit a ' + fmt(D) + ' deep opening.', boxIds);
          }
          if (L != null && s.maxW && bw > s.maxW(L, bh) + tol) warn('drawer-wide', tag + ': a ' + fmt(bw) + ' wide box is wider than this slide is rated for (' + fmt(s.maxW(L, bh)) + ' with ' + fmt(L) + ' slides). Use a heavier slide or a narrower drawer.', boxIds);
          if (sb) row.slideAt = { centre: (sb.min[2] + sb.max[2]) / 2 - lo[2], setback: sb.min[1] - lo[1], bottom: sb.min[2] - lo[2] };
        }
        // the front: inset reveals or overlay
        if (frontIds.length) {
          const fr = insts(frontIds, lo, hi, [3, 3, 3]).filter(x => x.b.max[1] <= B.min[1] + 1.25).sort((a, c) => Math.hypot(ctr(a.b)[0] - (lo[0] + hi[0]) / 2, ctr(a.b)[2] - (lo[2] + hi[2]) / 2) - Math.hypot(ctr(c.b)[0] - (lo[0] + hi[0]) / 2, ctr(c.b)[2] - (lo[2] + hi[2]) / 2))[0];
          if (!fr) warn('drawer-front', tag + ': no front (' + frontIds.map(i => '#' + i).join(', ') + ') in front of this opening.', frontIds);
          else {
            const F = fr.b, fw = F.max[0] - F.min[0], fh = F.max[2] - F.min[2], ft = F.max[1] - F.min[1];
            const ed = { left: lo[0] - F.min[0], right: F.max[0] - hi[0], bottom: lo[2] - F.min[2], top: F.max[2] - hi[2] };   // + overlay, − reveal
            row.front = { id: fr.p.id, w: fw, h: fh, t: ft, edges: ed };
            if (style === 'inset') {
              const g = Object.values(ed).map(v => -v);
              if (g.some(v => v < 1 / 64 - tol)) err('drawer-front-fit', tag + ': the inset front is ' + fmt(fw) + ' × ' + fmt(fh) + ' in a ' + fmt(W) + ' × ' + fmt(H) + ' opening; it needs a gap all round (1/16"–1/8").', frontIds);
              else if (g.some(v => v > 0.1875 + tol)) warn('drawer-front-fit', tag + ': the inset front leaves ' + g.map(v => fmt(v)).join(', ') + ' gaps; more than 3/16" reads as a mistake.', frontIds);
              if (s.kind === 'side' && row.slideAt && row.slideAt.setback < ft - tol) err('drawer-setback', tag + ': with an inset front the slide must be set back the front\'s thickness plus 1/8" (' + fmt(ft + 0.125) + '); it is ' + fmt(row.slideAt.setback) + '.', slideIds);
            } else if (B.min[0] < F.min[0] - tol || B.max[0] > F.max[0] + tol || B.min[2] < F.min[2] - 0.5) warn('drawer-front-cover', tag + ': the box shows past its ' + style + ' front.', frontIds);
          }
        }
        // the pull screw: through everything it holds, plus about 1/4"
        const pl = d.pull;
        if (pl && pl.screw && row.front) {
          const m = String(pl.screw).match(/x\s*([0-9\-\/. ]+)"?\s*$/i) || String(pl.screw).match(/×\s*([0-9\-\/. ]+)"?\s*$/);
          const len = m ? (() => { try { return parseLen(m[1].trim()); } catch (e) { return null; } })() : null;
          const stack = row.front.t + (pl.through_box ? (box.filter(x => x.b.max[1] - x.b.min[1] < 1.25 && x.b.min[1] <= B.min[1] + 1e-3).map(x => x.b.max[1] - x.b.min[1])[0] || 0) : 0);
          row.pullStack = stack;
          if (len != null && (len < stack + 0.125 - tol || len > stack + 0.5 + tol)) warn('drawer-pull-screw', tag + ': a ' + fmt(len) + ' pull screw through ' + fmt(stack) + ' of wood; use about ' + fmt(stack + 0.25) + '.', frontIds);
        }
      });
      warn = warn0;
    });
    if (rows.some(r => r.box)) pass('drawers', rows.length + ' drawer opening' + (rows.length === 1 ? '' : 's') + ' measured against the slide maker\'s clearances.');
    return rows;
  }

  // ---------- doors: hinge catalogue, sizing and checks (references/doors.md) ----------
  // Millimetres, as the hinge makers publish them. overlay: the door's overlay on the face the hinge
  // mounts to = k + C − H (C = cup boring distance from the door edge, H = mounting plate height);
  // an inset door's reveal is −(k + C − H). adj = side adjustment either way after hanging. reveal =
  // the maker's minimum reveal at the hinge edge by door thickness (rows) and cup distance (cols).
  const BLUM_REVEAL = { C: [3, 4, 5, 6, 7], T: { 16: [0.5, 0.5, 0.5, 0.5, 0.5], 19: [1, 1, 0.9, 0.9, 0.9], 22: [1.8, 1.7, 1.7, 1.6, 1.6], 24: [2.7, 2.5, 2.4, 2.3, 2.2], 26: [4.3, 3.8, 3.4, 3.2, 3] } };
  const SALICE_REVEAL = { C: [3, 4, 5, 6], T: { 16: [0.5, 0.5, 0.5, 0.5], 17: [0.7, 0.7, 0.7, 0.7], 18: [0.9, 0.9, 0.9, 0.9], 19: [1.2, 1.2, 1.2, 1.2], 20: [1.5, 1.5, 1.5, 1.5], 21: [1.8, 1.8, 1.8, 1.8], 22: [2.4, 2.1, 2.1, 2.1], 23: [3.7, 2.7, 2.6, 2.5], 24: [5.1, 4.1, 3.1, 3], 25: [6.5, 5.5, 4.1, 3.5], 26: [7.8, 6.8, 5.4, 4.4] } };
  const GRASS_REVEAL = { C: [3, 4, 5, 6, 7], T: { 16: [0.6, 0.6, 0.6, 0.6, 0.6], 17: [0.6, 0.6, 0.6, 0.6, 0.6], 18: [0.7, 0.7, 0.7, 0.7, 0.7], 19: [0.9, 0.9, 0.9, 0.9, 0.9], 20: [1.1, 1.1, 1.1, 1.1, 1.1], 21: [1.4, 1.3, 1.3, 1.3, 1.3], 22: [1.6, 1.6, 1.6, 1.5, 1.5], 24: [2.4, 2.1, 2.1, 2.1, 2] } };
  const HETTICH_REVEAL = { C: [3, 4, 4.5, 5, 6, 7], T: { 15: [0.2, 0.2, 0.2, 0.2, 0.2, 0.2], 16: [0.3, 0.3, 0.3, 0.3, 0.3, 0.3], 17: [0.4, 0.4, 0.4, 0.4, 0.4, 0.4], 18: [0.6, 0.6, 0.6, 0.6, 0.6, 0.5], 19: [0.8, 0.8, 0.8, 0.8, 0.7, 0.7], 20: [1.1, 1, 1, 1, 1, 0.9], 21: [1.4, 1.3, 1.3, 1.3, 1.2, 1.2], 22: [2.2, 1.8, 1.7, 1.6, 1.6, 1.5], 23: [3, 2.6, 2.4, 2.2, 2, 1.9], 24: [3.9, 3.4, 3.2, 3, 2.6, 2.4] } };
  const blum = { cup: 35, depth: 13, C: [3, 7], adj: 2, plates: [0, 3, 6, 9], t: [16, 26], reveal: BLUM_REVEAL, angle: 110, pattern: '45/9.5', plateSet: 37, screws: '#6 × 5/8" pan-head (plate), #6 × 1/2" (cup)', source: 'Blum CLIP top BLUMOTION 110° planning sheet (Blum Inc. catalogue p. 12)' };
  const salice = { cup: 35, depth: 11.5, C: [3, 6], adj: 2, plates: [0, 1.5, 3, 5], t: [16, 26], reveal: SALICE_REVEAL, angle: 110, pattern: '45/9.5', plateSet: 37, screws: '#6 × 5/8" pan-head', source: 'Salice Concealed Hinges for the Cabinet, USA catalogue (overlay formulas p. 4, minimum reveal p. 70)' };
  const grass = { cup: 35, depth: 12.6, C: [3, 7], adj: 2, plates: [0, 2, 3], t: [16, 24], reveal: GRASS_REVEAL, angle: 110, pattern: '45/9.5', plateSet: 37, screws: '#6 × 5/8" pan-head', source: 'Grass Tiomos 110 catalogue pages (planning dimensions, minimum reveal)' };
  const hettich = { cup: 35, depth: 13, C: [3, 7], adj: 2, plates: [0, 1.5, 3, 5], t: [15, 24], reveal: HETTICH_REVEAL, angle: 110, pattern: 'TH 52/5.5', plateSet: 37, screws: '#6 × 5/8" pan-head or 5 mm Euro screws', source: 'Hettich Sensys brochure HUK 14987 (8645i planning tables)' };
  const HINGES = {
    'blum-clip-top-110': Object.assign({}, blum, { kind: 'overlay', name: 'Blum CLIP top BLUMOTION 110° full overlay (71B3550)', k: 11, cabinet: 'frameless' }),
    'blum-clip-top-110-half': Object.assign({}, blum, { kind: 'overlay', name: 'Blum CLIP top BLUMOTION 110° half overlay (71B3650)', k: 1.5, cabinet: 'frameless' }),
    'blum-clip-top-110-inset': Object.assign({}, blum, { kind: 'inset', name: 'Blum CLIP top BLUMOTION 110° inset (71B3750)', k: -7, cabinet: 'frameless' }),
    'blum-compact-39c': { kind: 'fixed', name: 'Blum COMPACT BLUMOTION 39C face-frame hinge', cabinet: 'face-frame', overlays: [1, 1.25, 1.3125, 1.375, 1.5, 1.5625], frameT: 0.75, cup: 35, depth: 13, C: [3, 3], t: [16, 26], reveal: BLUM_REVEAL, angle: 107, pattern: '45/9.5', screws: '#6 × 5/8" into the frame', source: 'Blum COMPACT BLUMOTION 39C programme (overlay = model suffix ÷ 16")' },
    'salice-110': Object.assign({}, salice, { kind: 'overlay', name: 'Salice 200 series 110° full overlay ("A" crank, C2P6A99)', k: 15, cabinet: 'frameless' }),
    'salice-110-half': Object.assign({}, salice, { kind: 'overlay', name: 'Salice 200 series 110° half overlay ("G" crank)', k: 6, cabinet: 'frameless' }),
    'salice-110-inset': Object.assign({}, salice, { kind: 'inset', name: 'Salice 200 series 110° inset ("P" crank)', k: -2, cabinet: 'frameless' }),
    'salice-110-face-frame': Object.assign({}, salice, { kind: 'overlay', name: 'Salice 110° 1/2" overlay face-frame hinge ("D" crank)', k: 10, cabinet: 'face-frame' }),
    'grass-tiomos-110': Object.assign({}, grass, { kind: 'overlay', name: 'Grass Tiomos 110 full overlay (crank 0, F028138519)', k: 15, cabinet: 'frameless' }),
    'grass-tiomos-110-k3': Object.assign({}, grass, { kind: 'overlay', name: 'Grass Tiomos 110 overlay (crank 3, F028138520)', k: 12, cabinet: 'frameless' }),
    'grass-tiomos-110-half': Object.assign({}, grass, { kind: 'overlay', name: 'Grass Tiomos 110 half overlay (crank 9.5, F028138521)', k: 5.5, cabinet: 'frameless' }),
    'hettich-sensys-110': Object.assign({}, hettich, { kind: 'overlay', name: 'Hettich Sensys 8645i 110° full overlay', k: 12.5, cabinet: 'frameless' }),
    'hettich-sensys-110-half': Object.assign({}, hettich, { kind: 'overlay', name: 'Hettich Sensys 8645i 110° half overlay', k: 3, cabinet: 'frameless' }),
    'hettich-sensys-110-inset': Object.assign({}, hettich, { kind: 'inset', name: 'Hettich Sensys 8645i 110° inset', k: -4, cabinet: 'frameless' }),
    'butt-hinge': { kind: 'butt', name: 'Butt hinges, mortised (inset doors)', cabinet: 'any', t: [0, 99], source: 'traditional; see doors.md' }
  };
  // a door's hinge: a catalogue key, or an object (optionally { like: key, ...overrides })
  function hingeSpec(h) {
    if (typeof h === 'string') return HINGES[h] ? Object.assign({ key: h }, HINGES[h]) : null;
    if (h && typeof h === 'object') return Object.assign({ key: h.like || 'custom' }, h.like && HINGES[h.like] ? HINGES[h.like] : {}, h);
    return null;
  }
  // the maker's minimum reveal (mm) for a door thickness and cup distance: interpolated between rows
  function hingeReveal(s, Tmm, Cmm) {
    const R = s && s.reveal; if (!R) return null;
    let ci = 0; R.C.forEach((c, i) => { if (c <= Cmm + 1e-6) ci = i; });
    const ts = Object.keys(R.T).map(Number).sort((a, b) => a - b);
    if (Tmm <= ts[0]) return R.T[ts[0]][ci];
    for (let i = 1; i < ts.length; i++) if (Tmm <= ts[i]) { const a = ts[i - 1], b = ts[i], u = (Tmm - a) / (b - a); return Math.round((R.T[a][ci] * (1 - u) + R.T[b][ci] * u) * 10) / 10; }
    return R.T[ts[ts.length - 1]][ci];
  }
  // the cup distance and plate that give an overlay (mm, negative = inset reveal): the plate that
  // leaves the cup distance nearest the middle of its range, so the adjustment is spent evenly
  function hingeSetup(s, overlayMM) {
    if (!s || s.kind === 'butt') return null;
    if (s.kind === 'fixed') { const o = s.overlays.map(v => v * 25.4).reduce((a, b) => Math.abs(b - overlayMM) < Math.abs(a - overlayMM) ? b : a); return { C: s.C[0], H: 0, overlay: o, fits: Math.abs(o - overlayMM) <= 1 }; }
    const mid = (s.C[0] + s.C[1]) / 2, opts = [];
    for (const H of s.plates || [0]) { const C = Math.round((overlayMM - s.k + H) * 2) / 2; if (C >= s.C[0] - 1e-6 && C <= s.C[1] + 1e-6) opts.push({ C, H, overlay: s.k + C - H }); }
    if (!opts.length) return { fits: false, C: null, H: null };
    opts.sort((a, b) => Math.abs(a.C - mid) - Math.abs(b.C - mid) || a.H - b.H);
    return Object.assign({ fits: true }, opts[0]);
  }
  // hinges a door needs: Salice's chart by height and weight; Blum adds one over 600 mm wide
  function hingeCount(h, lb, w) {
    const n = h <= 36 && lb <= 20 ? 2 : h <= 60 && lb <= 40 ? 3 : h <= 84 && lb <= 60 ? 4 : 5;
    return n + (w > 600 / 25.4 ? 1 : 0);
  }
  // pounds per cubic inch, for the hinge count: plywood ~42 pcf, MDF ~48, hardwood ~40, softwood ~28, glass 156
  function density(mat) {
    const m = String(mat || '').toLowerCase();
    return /mdf|hdf/.test(m) ? 48 / 1728 : /glass/.test(m) ? 156 / 1728 : /ply|birch|melamine|particle/.test(m) ? 42 / 1728 : /pine|fir|cedar|spruce|poplar/.test(m) ? 28 / 1728 : 40 / 1728;
  }
  const solidWood = mat => !/ply|mdf|hdf|melamine|particle|glass|steel|board/i.test(String(mat || ''));
  // door sizes for an opening: what the designer aims for. o: style, leaves (1|2), frame (the case
  // edge or frame member width around the opening, one number or {left,right,top,bottom}), reveal at
  // exposed edges, gap between leaves, overlay (face frame and partial overlay)
  function doorSize(open, o) {
    o = o || {};
    const W = parseLen(open.w), H = parseLen(open.h), n = o.leaves || 1, style = o.style || 'full-overlay';
    const fr = typeof o.frame === 'object' && o.frame ? o.frame : { left: o.frame, right: o.frame, top: o.frame, bottom: o.frame };
    const f = k => fr[k] != null ? parseLen(fr[k]) : 0.75;
    const rev = o.reveal != null ? parseLen(o.reveal) : style === 'inset' ? 0.09375 : 0.0625, gap = o.gap != null ? parseLen(o.gap) : style === 'inset' ? 0.09375 : 0.125;
    const r32 = v => Math.floor(v * 32 + 1e-6) / 32;
    let ov;
    if (style === 'inset') ov = { left: -rev, right: -rev, top: -rev, bottom: -rev };
    else if (style === 'full-overlay') ov = { left: f('left') - rev, right: f('right') - rev, top: f('top') - rev, bottom: f('bottom') - rev };
    else if (style === 'half-overlay') ov = { left: f('left') / 2 - gap / 2, right: f('right') / 2 - gap / 2, top: f('top') - rev, bottom: f('bottom') - rev };
    else { const v = o.overlay != null ? parseLen(o.overlay) : 0.5; ov = { left: v, right: v, top: v, bottom: v }; }
    const total = W + ov.left + ov.right, w = r32((total - (n - 1) * gap) / n), h = r32(H + ov.top + ov.bottom);
    return { w, h, leaves: n, overlay: ov, gap: n > 1 ? gap : null, reveal: rev, overlayMM: Math.round(ov.left * 25.4 * 10) / 10 };
  }
  function doorChecks(M, plan, err, warn, pass) {
    const rows = [], tol = 1 / 128, ids = v => [].concat(v == null ? [] : v).map(String), fm = v => fmt(v) + ' (' + (Math.round(v * 254) / 10) + ' mm)';
    const insts = (list, lo, hi, pad) => { const out = []; for (const id of list) { const p = M.byId[id]; if (!p) continue; for (const I of p.instances) if (I.bbox && within(ctr(I.bbox), lo, hi, pad)) out.push({ p, I, b: I.bbox }); } return out; };
    const cupBores = (plan.bores || []).filter(b => b.kind === 'hole' && /cup|hinge/i.test(b.label || '') && parseLen(b.d) > 1);
    (plan.doors || []).forEach((d, di) => {
      const nm = d.name || 'Door ' + (di + 1), s = hingeSpec(d.hinge);
      if (!s) { err('door-hinge', nm + ': hinge "' + (typeof d.hinge === 'string' ? d.hinge : '?') + '" is not in the catalogue (' + Object.keys(HINGES).join(', ') + '). Name one, or give the maker\'s numbers as an object.'); return; }
      const op = d.opening || {}, W = parseLen(op.w), H = parseLen(op.h), style = d.style || 'full-overlay', cab = d.cabinet || s.cabinet || 'frameless';
      const ats = Array.isArray(op.at && op.at[0]) ? op.at : [op.at || [0, 0, 0]];
      const fr0 = d.frame == null ? 0.75 : d.frame, fr = typeof fr0 === 'object' ? fr0 : { left: fr0, right: fr0, top: fr0, bottom: fr0 }, f = k => fr[k] != null ? parseLen(fr[k]) : 0.75;
      const leafIds = ids(d.leaves), hingeIds = ids(d.hinges);
      const waived = new Set(), warn0 = warn, err0 = err;
      warn = (code, msg, parts) => { const why = d.waive && d.waive[code]; if (!why) return warn0(code, msg, parts); if (!waived.has(code)) { waived.add(code); pass(code, msg + ' Accepted: ' + why); } };
      if (s.kind !== 'butt' && s.cabinet !== 'any' && s.cabinet !== cab) warn('door-hinge-type', nm + ': the ' + s.name + ' is made for ' + s.cabinet + ' cabinets; this one is ' + cab + '.', hingeIds);
      if (s.kind === 'inset' && style !== 'inset') err('door-hinge-type', nm + ': an inset hinge (' + s.name + ') cannot hang a ' + style + ' door.', hingeIds);
      if (s.kind === 'overlay' && style === 'inset') err('door-hinge-type', nm + ': an overlay hinge (' + s.name + ') cannot hang an inset door; use the maker\'s inset (full-crank) version.', hingeIds);
      ats.forEach((at0, k) => {
        const at = at0.map(parseLen), lo = [at[0], at[1], at[2]], hi = [at[0] + W, at[1], at[2] + H];
        const tag = nm + (ats.length > 1 ? ' (' + (k + 1) + ' of ' + ats.length + ')' : '');
        const row = { name: nm, index: k, count: ats.length, hinge: s, style, cabinet: cab, opening: { at, w: W, h: H }, frame: { left: f('left'), right: f('right'), top: f('top'), bottom: f('bottom') }, leaves: [] };
        rows.push(row);
        const lv = insts(leafIds, [lo[0] - 3, lo[1] - 3, lo[2] - 3], [hi[0] + 3, lo[1] + 2, hi[2] + 3], [0, 0, 0]).sort((a, c) => a.b.min[0] - c.b.min[0]);
        if (!lv.length) { err('door-no-leaf', tag + ': no door (' + leafIds.map(i => '#' + i).join(', ') + ') hangs in front of the opening at ' + at.map(v => fmt(v)).join(', ') + '.', leafIds); return; }
        const pair = lv.length > 1, hinged = d.hinged || (pair ? 'pair' : 'left');
        if (hinged === 'pair' && lv.length !== 2) err('door-leaves', tag + ': a pair of doors needs two leaves in the opening; the model has ' + lv.length + '.', leafIds);
        const Cmm = d.cup != null ? Number(d.cup) : null, Hmm = d.plate != null ? Number(d.plate) : 0;
        lv.forEach((x, li) => {
          const B = x.b, w = B.max[0] - B.min[0], h = B.max[2] - B.min[2], t = B.max[1] - B.min[1];
          const ed = { left: lo[0] - B.min[0], right: B.max[0] - hi[0], bottom: lo[2] - B.min[2], top: B.max[2] - hi[2] };   // + overlay, − reveal
          const side = hinged === 'pair' ? (li === 0 ? 'left' : 'right') : hinged;
          const lb = w * h * t * density(x.p.material), Tmm = t * 25.4;
          const L = { id: x.p.id, w, h, t, edges: ed, side, weight: lb, material: x.p.material };
          row.leaves.push(L);
          const ltag = tag + (lv.length > 1 ? ', ' + side + ' door' : '');
          // thickness against the hinge
          if (s.t && (Tmm > s.t[1] + 0.3)) err('door-thickness', ltag + ': a ' + fm(t) + ' door is thicker than the ' + s.name + ' takes (' + s.t[1] + ' mm).', [x.p.id]);
          else if (s.t && Tmm < s.t[0] - 0.3) warn('door-thickness', ltag + ': a ' + fm(t) + ' door is thinner than the ' + s.name + ' is made for (' + s.t[0] + ' mm); the cup leaves too little wood behind it.', [x.p.id]);
          // hinges along the hinge edge
          if (s.kind !== 'butt' || hingeIds.length) {
            const ex = side === 'left' ? B.min[0] : B.max[0];
            const hs = insts(hingeIds, [ex - 2.5, B.min[1] - 1, B.min[2]], [ex + 2.5, B.max[1] + 4, B.max[2]], [0, 0, 0]).map(q => ctr(q.b)[2] - B.min[2]).sort((a, c) => a - c);
            L.hinges = hs; L.need = hingeCount(h, lb, w);
            if (!hingeIds.length) warn('door-no-hinges', ltag + ': no hinge part is named, so the hinges are not on the material list or in the model.', [x.p.id]);
            else if (!hs.length) err('door-hinges', ltag + ': no hinge (' + hingeIds.map(i => '#' + i).join(', ') + ') sits on the ' + side + ' edge of this door.', hingeIds);
            else {
              if (hs.length < L.need) err('door-hinge-count', ltag + ': a ' + fmt(h) + ' tall, ' + fmt(w) + ' wide door weighing about ' + Math.round(lb) + ' lb needs ' + L.need + ' hinges (Salice: 2 to 36" and 20 lb, 3 to 60" and 40 lb, 4 to 84" and 60 lb; Blum: one more over 600 mm wide); the model has ' + hs.length + '.', hingeIds);
              const ends = [hs[0], h - hs[hs.length - 1]];
              if (ends.some(e => e < 2 - tol || e > 6 + tol)) warn('door-hinge-position', ltag + ': hinge centres ' + ends.map(e => fmt(e)).join(' and ') + ' from the door ends; set them about 3"–4" in (2" to 6").', hingeIds);
            }
          }
          // overlay or reveal at the hinge edge, from the hinge maker's formula
          const hov = ed[side];
          if (s.kind === 'overlay' || s.kind === 'inset') {
            const C = Cmm != null ? Cmm : (hingeSetup(s, hov * 25.4) || {}).C;
            const Hh = Cmm != null ? Hmm : ((hingeSetup(s, hov * 25.4) || {}).H || 0);
            L.cup = C; L.plate = Hh;
            if (C == null) err('door-overlay', ltag + ': the door ' + (hov >= 0 ? 'overlays the ' + side + ' edge by ' + fm(hov) : 'leaves a ' + fm(-hov) + ' reveal') + ', which no cup distance (' + s.C[0] + '–' + s.C[1] + ' mm) and plate (' + (s.plates || [0]).join(', ') + ' mm) on the ' + s.name + ' gives (overlay = ' + s.k + ' + cup distance − plate). Change the door size or the hinge.', [x.p.id]);
            else {
              if (C < s.C[0] - 1e-6 || C > s.C[1] + 1e-6) err('door-cup', ltag + ': a ' + C + ' mm cup distance is outside the ' + s.name + '\'s ' + s.C[0] + '–' + s.C[1] + ' mm range.', [x.p.id]);
              const give = s.k + C - Hh; L.hingeOverlay = give;
              if (Math.abs(hov * 25.4 - give) > (s.adj || 2) + 0.2) err('door-overlay', ltag + ': the ' + s.name + ' with a ' + C + ' mm cup distance on a ' + Hh + ' mm plate gives ' + (give >= 0 ? give + ' mm overlay' : -give + ' mm reveal') + ' (' + s.k + ' + ' + C + ' − ' + Hh + ', ±' + (s.adj || 2) + ' mm adjustment), but the door ' + (hov >= 0 ? 'overlays ' + fm(hov) : 'leaves a ' + fm(-hov) + ' reveal') + ' on its hinge edge.' + ((h => h && h.fits ? ' Bore the cup ' + h.C + ' mm from the edge and use the ' + h.H + ' mm plate.' : ' No cup distance and plate on this hinge reaches it (' + (s.k + s.C[0] - Math.max(...(s.plates || [0]))) + ' to ' + (s.k + s.C[1]) + ' mm): resize the door or choose another hinge.')(hingeSetup(s, hov * 25.4))), [x.p.id]);
            }
          } else if (s.kind === 'fixed') {
            L.cup = s.C[0]; L.plate = 0;
            const o = s.overlays.find(v => Math.abs(v - hov) <= 1 / 32 + tol);
            if (!o) err('door-overlay', ltag + ': the ' + s.name + ' comes in ' + s.overlays.map(v => fmt(v)).join(', ') + ' overlays; the door overlays ' + fmt(hov) + ' on its hinge edge.', [x.p.id]);
            else L.hingeOverlay = o * 25.4;
          }
          // the hinge-edge reveal must clear the swing (inset), and exposed reveals stay even
          const rv = hingeReveal(s, Tmm, L.cup != null ? L.cup : 3); L.minReveal = rv;
          if (style === 'inset') {
            const g = Object.values(ed).map(v => -v);
            if (g.some(v => v < 1 / 32 - tol)) err('door-fit', ltag + ': the inset door is ' + fmt(w) + ' × ' + fmt(h) + ' in a ' + fmt(W) + ' × ' + fmt(H) + ' opening; it needs a gap all round (1/16"–1/8").', [x.p.id]);
            else if (g.some(v => v > 0.1875 + tol)) warn('door-fit', ltag + ': the inset door leaves ' + g.map(v => fmt(v)).join(', ') + ' gaps; more than 3/16" reads as a mistake.', [x.p.id]);
            if (rv != null && -ed[side] * 25.4 < rv - 0.05) err('door-swing', ltag + ': a ' + fm(t) + ' inset door needs at least ' + rv + ' mm at its hinge edge to swing past the case (' + s.name + ', ' + (L.cup != null ? L.cup : 3) + ' mm cup distance); it has ' + fm(-ed[side]) + '. Widen the gap, ease the edge or bore the cup further in.', [x.p.id]);
          } else {
            for (const e of ['left', 'right', 'top', 'bottom']) {
              if (pair && ((e === 'right' && li === 0) || (e === 'left' && li === 1))) continue;
              const fe = style === 'half-overlay' && (e === 'left' || e === 'right') ? f(e) / 2 : f(e);
              if (cab === 'face-frame') { if (ed[e] > fe - 0.25 + tol) warn('door-frame-show', ltag + ': the door overlays the frame ' + fmt(ed[e]) + ' at the ' + e + ', leaving less than 1/4" of the ' + fmt(fe) + ' frame showing.', [x.p.id]); continue; }
              const rev = fe - ed[e];
              if (rev < -tol) warn('door-reveal', ltag + ': the door runs ' + fmt(-rev) + ' past the ' + e + ' edge of the case.', [x.p.id]);
              else if (rev < 1 / 32 - tol || rev > 0.1875 + tol) warn('door-reveal', ltag + ': ' + fmt(rev) + ' reveal at the ' + e + ' edge; frameless doors want 1/16"–1/8".', [x.p.id]);
            }
          }
          // pull screw: through the door, plus about 1/4"
          const pl = d.pull;
          if (pl && pl.screw) {
            const m = String(pl.screw).match(/[x×]\s*([0-9\-\/. ]+)"?\s*$/i);
            const len = m ? (() => { try { return parseLen(m[1].trim()); } catch (e) { return null; } })() : null;
            if (len != null && (len < t + 0.125 - tol || len > t + 0.5 + tol)) warn('door-pull-screw', ltag + ': a ' + fmt(len) + ' pull screw through a ' + fmt(t) + ' door; use about ' + fmt(t + 0.25) + '.', [x.p.id]);
          }
          // the cup bore: diameter and depth from the hinge sheet, inside the door
          if (s.cup) {
            const cb = cupBores.find(b => b.copies && b.copies.some(c => { const q = c.at.map(parseLen); return q[0] >= B.min[0] - 0.1 && q[0] <= B.max[0] + 0.1 && q[2] >= B.min[2] && q[2] <= B.max[2]; }));
            if (cb) {
              const bd = parseLen(cb.d) * 25.4, dp = parseLen(cb.depth) * 25.4; L.bore = { d: bd, depth: dp, id: cb.id };
              if (Math.abs(bd - s.cup) > 0.6) err('door-cup', ltag + ': the hinge cup is bored ' + Math.round(bd * 10) / 10 + ' mm; the ' + s.name + ' needs ' + s.cup + ' mm.', [x.p.id]);
              if (s.depth && (dp < s.depth - 0.6 || dp > Tmm - 2)) warn('door-cup', ltag + ': the cup is bored ' + Math.round(dp * 10) / 10 + ' mm deep; the hinge wants ' + s.depth + ' mm and at least 2 mm of door behind it.', [x.p.id]);
            }
          }
          // frame-and-panel: the panel sits in its grooves with room to move
          const cn = d.construction;
          if (cn && cn.type === 'frame-and-panel' && cn.panel != null) {
            const g = parseLen(cn.groove != null ? cn.groove : 0.375), pnl = insts(ids(cn.panel), B.min, B.max, [0.1, 0.5, 0.1])[0];
            const st = insts(ids(cn.stiles), B.min, B.max, [0.1, 0.5, 0.1]), rl = insts(ids(cn.rails), B.min, B.max, [0.1, 0.5, 0.1]);
            if (pnl && st.length >= 2 && rl.length >= 2) {
              const P2 = pnl.b, mid = ctr(B), sl = st.find(q => ctr(q.b)[0] < mid[0]), sr = st.find(q => ctr(q.b)[0] > mid[0]), rb = rl.find(q => ctr(q.b)[2] < mid[2]), rt = rl.find(q => ctr(q.b)[2] > mid[2]);
              const clearW = sl && sr ? sr.b.min[0] - sl.b.max[0] : 0, clearH = rb && rt ? rt.b.min[2] - rb.b.max[2] : 0;
              const eW = ((P2.max[0] - P2.min[0]) - clearW) / 2, eH = ((P2.max[2] - P2.min[2]) - clearH) / 2;
              L.panel = { w: P2.max[0] - P2.min[0], h: P2.max[2] - P2.min[2], engageW: eW, engageH: eH, groove: g, solid: solidWood(pnl.p.material) };
              if (eW > g + tol || eH > g + tol) err('door-panel', ltag + ': the panel runs ' + fmt(Math.max(eW, eH)) + ' into ' + fmt(g) + ' deep grooves; it cannot go in.', [pnl.p.id]);
              else if (L.panel.solid && g - eW < 1 / 16 - tol && L.panel.w > 6) warn('door-panel', ltag + ': a ' + fmt(L.panel.w) + ' wide solid panel has only ' + fmt(g - eW) + ' a side to swell; cut it to leave about 1/8" a side (less in a dry winter shop).', [pnl.p.id]);
              if (Math.min(eW, eH) < 0.25 - tol) warn('door-panel', ltag + ': the panel sits only ' + fmt(Math.min(eW, eH)) + ' in its groove and can pull out as it shrinks; aim for 1/4" or more.', [pnl.p.id]);
            }
          }
        });
        // the pair's meeting gap
        if (lv.length === 2) {
          const g = lv[1].b.min[0] - lv[0].b.max[0]; row.gap = g;
          const solid = lv.some(x => solidWood(x.p.material));
          if (g < 1 / 32 - tol) err('door-gap', tag + ': the two doors are ' + fmt(g) + ' apart; they bind. Leave 1/16"–1/8".', leafIds);
          else if (g > 0.1875 + tol || g < 1 / 16 - tol) warn('door-gap', tag + ': ' + fmt(g) + ' between the doors; 1/16"–1/8" reads as even.', leafIds);
          else if (solid && g < 5 / 32 - tol) warn('door-gap', tag + ': ' + fmt(g) + ' between solid-wood doors; they swell across their width, so shops leave about 4 mm (5/32").', leafIds);
        }
      });
      warn = warn0; err = err0;
    });
    // doors hinged back to back on one partition both open at once: twice the minimum reveal between them
    const edges = [];
    rows.forEach(r => r.leaves.forEach(L => { const x = r.opening.at[0] + (L.side === 'left' ? -L.edges.left : r.opening.w + L.edges.right); edges.push({ r, L, x }); }));
    for (let i = 0; i < edges.length; i++) for (let j = i + 1; j < edges.length; j++) {
      const a = edges[i], b = edges[j]; if (a.L.side === b.L.side) continue;
      const [lf, rt] = a.L.side === 'left' ? [a, b] : [b, a];   // a left-hinged door's edge to the right of a right-hinged one
      const g = lf.x - rt.x, za = [lf.r.opening.at[2] - lf.L.edges.bottom, lf.r.opening.at[2] + lf.r.opening.h + lf.L.edges.top], zb = [rt.r.opening.at[2] - rt.L.edges.bottom, rt.r.opening.at[2] + rt.r.opening.h + rt.L.edges.top];
      if (g < -tol || g > 2 || Math.min(za[1], zb[1]) - Math.max(za[0], zb[0]) < 1) continue;
      const need = ((lf.L.minReveal || 0) + (rt.L.minReveal || 0)) / 25.4;
      if (g < need - 0.002) err('door-swing', lf.r.name + ' and ' + rt.r.name + ': doors hinged back to back are ' + fmt(g) + ' apart; both open at once, so they need the two minimum reveals, ' + Math.round(need * 254) / 10 + ' mm. Use a thinner door, ease the edges or move the cups.', [lf.L.id, rt.L.id]);
    }
    if (rows.some(r => r.leaves.length)) pass('doors', rows.length + ' door opening' + (rows.length === 1 ? '' : 's') + ' measured against the hinge maker\'s overlay and reveal tables.');
    return rows;
  }

  const api = { HINGES, hingeSpec, hingeReveal, hingeSetup, hingeCount, doorSize, doorChecks, SLIDES, slideSpec, drawerSize, drawerChecks, measures, at3, plAxes, faces, profile, shapedAway, toLocalPt, toWorldPt, isShape, cutList, buyList, toolsFor, storyMarks, cutOrder, hasGrain, storeName, expandBores, cutDepth, TOOLS, nominal, parseLen, fmt, fmtHTML, fracParts, normalize, solid, surface, check, pack, layouts, lumberStats, toAABB, xformAABB, inter, vol };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.PlanCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
