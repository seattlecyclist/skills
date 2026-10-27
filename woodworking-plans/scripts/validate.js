/* validate.js — check a plan object against the schema in references/plan-schema.md.
 * Returns [{ level: 'error'|'warn', at: 'parts[3].shape[1]', msg }]. Errors stop the build;
 * warnings are typos and loose ends (unknown keys, chips that point nowhere, unreviewed changes).
 *   node scripts/build_plan.js plan.js --validate
 */
(function () {
  'use strict';
  const C = require('./plan-core.js');

  const KEYS = {
    plan: ['meta', 'materials', 'sections', 'parts', 'cutlist_notes', 'joints', 'bores', 'hardware', 'details', 'details_intro', 'view', 'stock', 'cutting_note', 'steps', 'revisions', 'review', 'jigs', 'story_sticks', 'finish', 'hardware_note'],
    meta: ['series', 'plan_no', 'rev', 'date', 'title', 'subtitle', 'overall', 'wood', 'skill', 'time', 'intro', 'needs', 'basis', 'changed', 'check', 'tools', 'toolkit'],
    basis: ['what', 'from', 'note'],
    changed: ['what', 'why'],
    part: ['id', 'name', 'section', 'qty', 't', 'w', 'l', 'material', 'stock', 'mat', 'glueup', 'stock_t', 'blank', 'size', 'note', 'shape', 'instances', 'stage', 'callout', 'drawing', 'min_wall', 'pattern', 'grain'],
    shape: ['box', 'cut', 'role', 'through', 'tool', 'outline', 'cutout', 'lathe', 'splay', 'roundover', 'chamfer', 'axis', 'span', 'center', 'edges', 'ease', 'section', 'top'],
    instance: ['at', 'rot', 'mirror', 'explode', 'label'],
    joint: ['id', 'type', 'title', 'parts', 'glue', 'fasteners', 'gap', 'note', 'at', 'radius', 'explode'],
    bore: ['id', 'joint', 'kind', 'label', 'at', 'dir', 'd', 'depth', 'len', 'counterbore', 'washer', 'nut', 'bit', 'access', 'through', 'hardware', 'cross', 'copies', 'qty'],
    hardware: ['item', 'qty', 'source', 'note', 'part', 'draw'],
    step: ['title', 'text', 'parts', 'wrong'],
    section: ['id', 'cut', 'at', 'keep', 'title', 'on', 'box'],
    jig: ['title', 'sub', 'purpose', 'use', 'for', 'parts', 'items', 'w', 'h', 'font', 'wide'],
    stick: ['title', 'axis', 'parts', 'from', 'to', 'marks', 'note', 'width'],
    finish: ['title', 'note', 'steps'],
    revision: ['rev', 'date', 'summary', 'changes'],
    change: ['id', 'summary', 'parts', 'reason'],
    review: ['rev', 'change', 'verdict', 'mates', 'checks'],
    check: ['check', 'evidence', 'result']
  };
  const FROM = ['you', 'reference', 'photo', 'choice'];
  const STOCK = ['solid', 'sheet', 'hardware'], RESULTS = ['pass', 'fixed', 'flag', 'fail'], KINDS = ['bolt', 'screw', 'cross-dowel', 'hole', 'peg'];
  const DIRS = ['+x', '-x', '+y', '-y', '+z', '-z'];

  function validate(plan) {
    const out = [];
    const E = (at, msg) => out.push({ level: 'error', at, msg });
    const W = (at, msg) => out.push({ level: 'warn', at, msg });
    const obj = v => v && typeof v === 'object' && !Array.isArray(v);
    const keys = (o, kind, at) => { if (!obj(o)) return E(at, 'should be an object'); for (const k of Object.keys(o)) if (!KEYS[kind].includes(k)) W(at + '.' + k, 'unknown key "' + k + '" (typo? allowed: ' + KEYS[kind].join(', ') + ')'); };
    const len = (v, at, opt) => { if (v == null) { if (!opt) E(at, 'missing'); return null; } try { const n = C.parseLen(v); if (!(n >= 0) && !(n < 0)) throw 0; return n; } catch (e) { E(at, 'not a length: ' + JSON.stringify(v)); return null; } };
    // curves, angles and turnings: a profile seen along an axis, or an edge treatment of the blank
    const shapeEntry = (s, sa, p) => {
      if (!(p.shape || []).some(x => x && x.box)) E(sa, 'a shape trims the part\'s blank: the part needs a box first');
      if (s.roundover != null || s.chamfer != null) {
        const r = len(s.roundover != null ? s.roundover : s.chamfer, sa + (s.roundover != null ? '.roundover' : '.chamfer'));
        if (r != null && !(r > 0)) E(sa, 'the size should be more than 0');
        for (const e of [].concat(s.edges == null ? [] : s.edges)) {
          const ws = String(e).toLowerCase().split(/[\s,+&-]+/).filter(Boolean);
          if (!(ws.length === 1 && ['all', 'long', 'top', 'bottom', 'front', 'back', 'left', 'right'].includes(ws[0])) && !(ws.length === 2 && ws.every(w => ['top', 'bottom', 'front', 'back', 'left', 'right'].includes(w))))
            E(sa + '.edges', '"' + e + '" is not an edge: use top, bottom, front, back, left, right, a pair like "top-front", "long" or "all"');
        }
        return;
      }
      if (s.splay != null) {
        // a leg splayed in two directions: [front-view degrees, side-view degrees], its section and top
        if (!Array.isArray(s.splay) || s.splay.length !== 2 || s.splay.some(d => typeof d !== 'number' || Math.abs(d) >= 45)) E(sa + '.splay', 'should be [front-view degrees, side-view degrees], each under 45');
        if (s.section != null) nums(s.section, 2, sa + '.section');
        if (s.top != null) nums(s.top, 2, sa + '.top');
        return;
      }
      if (s.ease != null) {
        if (!obj(s.ease) || (s.ease.roundover == null) === (s.ease.chamfer == null)) E(sa + '.ease', 'should be { roundover: r } or { chamfer: r }, with faces if not both');
        else { const r = len(s.ease.roundover != null ? s.ease.roundover : s.ease.chamfer, sa + '.ease'); if (r != null && !(r > 0)) E(sa + '.ease', 'the size should be more than 0'); }
        if (s.lathe) E(sa + '.ease', 'a turning takes its round-overs in its lathe profile');
        const want = { x: ['left', 'right'], y: ['front', 'back'], z: ['bottom', 'top'] }[s.axis] || [];
        for (const f of [].concat(s.ease && s.ease.faces != null ? s.ease.faces : [])) if (f !== 'both' && !want.includes(f)) E(sa + '.ease.faces', '"' + f + '" is not a face across a profile seen along ' + s.axis + ': use ' + want.concat('both').join(', '));
      }
      if (!['x', 'y', 'z'].includes(s.axis)) E(sa + '.axis', 'should be "x", "y" or "z": the axis the profile is seen along (the saw cuts through it along this axis)');
      if (s.span != null) nums(s.span, 2, sa + '.span');
      if (s.center != null) { if (!s.lathe) W(sa + '.center', 'only a lathe profile takes a center'); nums(s.center, 2, sa + '.center'); }
      if (s.tool && !C.TOOLS[s.tool] && !['lathe', 'spokeshave', 'jigsaw', 'coping saw', 'plane', 'sander', 'scroll saw'].includes(s.tool)) W(sa + '.tool', 'tool "' + s.tool + '" is not one the tools list knows');
      try {
        const P = C.profile(s.outline || s.cutout || s.lathe, !!s.lathe);
        if (P.pts.length < (s.lathe ? 2 : 3)) E(sa, 'the profile needs at least ' + (s.lathe ? 2 : 3) + ' points');
        if (s.lathe && P.pts.some(q => q[0] < -1e-9)) E(sa + '.lathe', 'lathe points are [radius, position along the axis]; a radius cannot be negative');
      } catch (e) { E(sa + '.' + (s.outline ? 'outline' : s.cutout ? 'cutout' : 'lathe'), e.message); }
    };
    const nums = (a, n, at) => { if (!Array.isArray(a) || a.length !== n) return E(at, 'should be ' + n + ' numbers'); a.forEach((v, i) => len(v, at + '[' + i + ']')); };
    const arr = (v, at) => { if (v == null) return []; if (!Array.isArray(v)) { E(at, 'should be an array'); return []; } return v; };

    if (!obj(plan)) { E('plan', 'plan.js must export a function returning the plan object, or the object'); return out; }
    keys(plan, 'plan', 'plan');
    const meta = plan.meta || {}; if (!plan.meta) E('meta', 'missing'); else keys(meta, 'meta', 'meta');
    if (!meta.title) E('meta.title', 'missing');
    if (meta.overall) for (const k of ['w', 'd', 'h']) len(meta.overall[k], 'meta.overall.' + k, true);
    arr(meta.basis, 'meta.basis').forEach((b, i) => {
      const at = 'meta.basis[' + i + ']'; keys(b, 'basis', at);
      if (!b.what) E(at + '.what', 'missing: say which size or feature');
      if (!FROM.includes(b.from)) E(at + '.from', 'must be one of ' + FROM.join(', ') + ' (got ' + JSON.stringify(b.from) + ')');
      if (b.from === 'photo' && !b.note) W(at + '.note', 'a size estimated from a photo should say what it was scaled from');
    });
    arr(meta.changed, 'meta.changed').forEach((c, i) => { const at = 'meta.changed[' + i + ']'; keys(c, 'changed', at); if (!c.what) E(at + '.what', 'missing'); });

    const secs = arr(plan.sections, 'sections').map(s => String(s.id));
    const parts = arr(plan.parts, 'parts');
    if (!parts.length) E('parts', 'no parts');
    const ids = new Set();
    parts.forEach((p, i) => {
      const at = 'parts[' + i + ']' + (p && p.id != null ? ' (#' + p.id + ')' : '');
      keys(p, 'part', at); if (!obj(p)) return;
      if (p.id == null || p.id === '') E(at + '.id', 'missing');
      else if (ids.has(String(p.id))) E(at + '.id', 'part number ' + p.id + ' is used twice'); else ids.add(String(p.id));
      if (!p.name) E(at + '.name', 'missing');
      if (!STOCK.includes(p.stock)) E(at + '.stock', 'should be one of ' + STOCK.join(', ') + (p.stock ? ', got "' + p.stock + '"' : ''));
      if (secs.length && p.section != null && !secs.includes(String(p.section))) E(at + '.section', 'section "' + p.section + '" is not in plan.sections');
      if (secs.length && p.section == null) W(at + '.section', 'no section: the part will not appear on any Material List exploded view');
      if (p.stock !== 'hardware') { len(p.t, at + '.t'); len(p.w, at + '.w'); len(p.l, at + '.l'); }
      if (p.qty != null && !(Number.isInteger(p.qty) && p.qty > 0)) E(at + '.qty', 'should be a whole number');
      if (p.mat && plan.materials && !plan.materials[p.mat]) E(at + '.mat', 'material "' + p.mat + '" is not in plan.materials');
      arr(p.shape, at + '.shape').forEach((s, k) => {
        const sa = at + '.shape[' + k + ']'; keys(s, 'shape', sa); if (!obj(s)) return;
        const kinds = ['box', 'cut', 'outline', 'cutout', 'lathe', 'splay', 'roundover', 'chamfer'].filter(x => s[x] != null);
        if (kinds.length !== 1) return E(sa, 'needs exactly one of box, cut, outline, cutout, lathe, splay, roundover or chamfer' + (kinds.length ? ' (has ' + kinds.join(' and ') + ')' : ''));
        if (C.isShape(s)) return shapeEntry(s, sa, p);
        nums(s.box || s.cut, 6, sa + (s.box ? '.box' : '.cut'));
        if (s.role && s.role !== 'tenon') E(sa + '.role', 'only "tenon" is supported');
        if (s.tool && !C.TOOLS[s.tool] && !(meta.tools && meta.tools[s.tool] != null)) W(sa + '.tool', 'tool "' + s.tool + '" has no depth limit; add it to meta.tools');
      });
      const ins = arr(p.instances, at + '.instances');
      if (p.shape && p.shape.length && !ins.length) W(at + '.instances', 'no instances: one copy is placed at the origin');
      if (p.qty != null && ins.length && p.qty !== ins.length) E(at + '.qty', 'qty ' + p.qty + ' but ' + ins.length + ' instances');
      ins.forEach((I, k) => {
        const ia = at + '.instances[' + k + ']'; keys(I, 'instance', ia); if (!obj(I)) return;
        nums(I.at || [0, 0, 0], 3, ia + '.at');
        if (I.explode) nums(I.explode, 3, ia + '.explode');
        if (I.rot && I.rot % 90) E(ia + '.rot', 'must be a multiple of 90');
        if (I.mirror && !['x', 'y'].includes(I.mirror)) E(ia + '.mirror', 'should be "x" or "y"');
      });
    });
    const has = id => ids.has(String(id));

    const jids = new Set();
    arr(plan.joints, 'joints').forEach((j, i) => {
      const at = 'joints[' + i + ']' + (j && j.id ? ' (' + j.id + ')' : ''); keys(j, 'joint', at); if (!obj(j)) return;
      if (j.id != null) { if (jids.has(j.id)) E(at + '.id', 'joint id used twice'); jids.add(j.id); } else jids.add('J' + (i + 1));
      if (!j.type) E(at + '.type', 'missing');
      const ps = arr(j.parts, at + '.parts');
      if (ps.length < 2) E(at + '.parts', 'a joint needs at least two parts');
      ps.forEach(id => { if (!has(id)) E(at + '.parts', 'part ' + id + ' does not exist'); });
    });

    const bids = new Set();
    arr(plan.bores, 'bores').forEach((b, i) => {
      const at = 'bores[' + i + ']' + (b && b.id ? ' (' + b.id + ')' : ''); keys(b, 'bore', at); if (!obj(b)) return;
      if (!b.id) E(at + '.id', 'missing'); else bids.add(b.id);
      if (!KINDS.includes(b.kind)) E(at + '.kind', 'should be one of ' + KINDS.join(', '));
      if (b.joint && !jids.has(b.joint)) E(at + '.joint', 'joint ' + b.joint + ' does not exist');
      len(b.d, at + '.d');
      if (b.depth == null && b.len == null) E(at + '.depth', 'needs depth (or len for a screw)');
      const copies = b.copies && b.copies.length ? b.copies : [b];
      copies.forEach((c, k) => {
        const ca = b.copies ? at + '.copies[' + k + ']' : at;
        nums(c.at || b.at, 3, ca + '.at');
        const d = c.dir || b.dir;
        if (!(DIRS.includes(d) || (Array.isArray(d) && d.filter(Boolean).length === 1))) E(ca + '.dir', 'should be one of ' + DIRS.join(' '));
      });
    });
    arr(plan.bores, 'bores').forEach((b, i) => { if (b && b.nut && !bids.has(b.nut)) E('bores[' + i + '].nut', 'nut ' + b.nut + ' is not a bore id'); });

    arr(plan.hardware, 'hardware').forEach((h, i) => { keys(h, 'hardware', 'hardware[' + i + ']'); if (h && h.part != null && !has(h.part)) E('hardware[' + i + '].part', 'part ' + h.part + ' does not exist'); });
    arr(plan.steps, 'steps').forEach((s, i) => {
      keys(s, 'step', 'steps[' + i + ']');
      arr(s && s.parts, 'steps[' + i + '].parts').forEach(id => { if (!has(id)) E('steps[' + i + '].parts', 'part ' + id + ' does not exist'); });
    });
    // every modeled part is added by some step
    if (plan.steps && plan.steps.length) {
      const added = new Set(plan.steps.flatMap(s => (s.parts || []).map(String)));
      parts.forEach(p => { if (p && p.shape && p.shape.length && !added.has(String(p.id))) W('steps', 'no step adds #' + p.id + ' ' + p.name + ', so assembly mode never shows it'); });
    }

    // {#id} chips anywhere in the text
    const walk = (v, at) => {
      if (typeof v === 'string') { for (const m of v.matchAll(/\{#([^}]+)\}/g)) if (!has(m[1])) E(at, 'chip {#' + m[1] + '} points to a part that does not exist'); }
      else if (Array.isArray(v)) v.forEach((x, i) => walk(x, at + '[' + i + ']'));
      else if (obj(v)) for (const k in v) if (k !== 'shape' && k !== 'instances') walk(v[k], at + '.' + k);
    };
    walk(plan, 'plan');

    // revisions and their review records
    const changes = new Map();
    arr(plan.revisions, 'revisions').forEach((r, i) => {
      keys(r, 'revision', 'revisions[' + i + ']');
      arr(r && r.changes, 'revisions[' + i + '].changes').forEach((c, k) => {
        const at = 'revisions[' + i + '].changes[' + k + ']'; keys(c, 'change', at);
        if (!c || !c.id) return E(at + '.id', 'missing');
        if (changes.has(c.id)) E(at + '.id', 'change id ' + c.id + ' used twice');
        changes.set(c.id, r.rev);
        arr(c.parts, at + '.parts').forEach(id => { if (!has(id)) E(at + '.parts', 'part ' + id + ' does not exist'); });
      });
    });
    if (meta.rev && plan.revisions && plan.revisions.length && !plan.revisions.some(r => r.rev === meta.rev)) E('meta.rev', 'rev ' + meta.rev + ' has no revisions entry');
    const reviewed = new Set();
    arr(plan.review, 'review').forEach((r, i) => {
      const at = 'review[' + i + ']' + (r && r.change ? ' (' + r.change + ')' : ''); keys(r, 'review', at); if (!obj(r)) return;
      if (!changes.has(r.change)) E(at + '.change', 'change ' + r.change + ' is not in revisions');
      else if (changes.get(r.change) !== r.rev) E(at + '.rev', 'change ' + r.change + ' belongs to rev ' + changes.get(r.change));
      reviewed.add(r.change);
      if (!RESULTS.includes(r.verdict)) E(at + '.verdict', 'should be one of ' + RESULTS.join(', ') + (r.verdict ? ', got "' + r.verdict + '"' : ''));
      arr(r.mates, at + '.mates').forEach(id => { if (!has(id)) E(at + '.mates', 'part ' + id + ' does not exist'); });
      const cs = arr(r.checks, at + '.checks');
      if (!cs.length) E(at + '.checks', 'a review needs at least one check');
      cs.forEach((c, k) => {
        const ca = at + '.checks[' + k + ']'; keys(c, 'check', ca); if (!obj(c)) return;
        if (!c.check) E(ca + '.check', 'missing');
        if (!c.evidence || /\bTODO\b/.test(c.evidence)) E(ca + '.evidence', 'missing or still TODO');
        if (!RESULTS.includes(c.result)) E(ca + '.result', 'should be one of ' + RESULTS.join(', ') + (c.result ? ', got "' + c.result + '"' : ''));
      });
      // the verdict is the worst line: fail, then flag, then fixed, then pass
      const worst = ['fail', 'flag', 'fixed', 'pass'].find(v => cs.some(c => c && c.result === v)) || 'pass';
      if (RESULTS.includes(r.verdict) && cs.length && r.verdict !== worst) E(at + '.verdict', 'verdict "' + r.verdict + '" but the worst check is "' + worst + '"; the verdict is the worst line (fail, flag, fixed, pass)');
      if (r.verdict === 'fail') E(at + '.verdict', 'a change that still fails must not ship; fix it or flag it for the user');
    });
    for (const [id] of changes) if (!reviewed.has(id)) E('review', 'change ' + id + ' has no review entry');

    // section views, shop aids, story sticks, finishing
    const views = ['front', 'side', 'top'], sids = new Set();
    arr(plan.view && plan.view.sections, 'view.sections').forEach((v, i) => {
      const at = 'view.sections[' + i + ']'; keys(v, 'section', at); if (!obj(v)) return;
      if (!v.id) E(at + '.id', 'missing (a letter: A, B …)'); else if (sids.has(v.id)) E(at + '.id', 'section ' + v.id + ' used twice'); else sids.add(v.id);
      if (!['x', 'y', 'z'].includes(v.cut)) E(at + '.cut', 'should be "x", "y" or "z" (the axis the cutting plane crosses)');
      len(v.at, at + '.at');
      if (v.keep != null && !['+', '-'].includes(v.keep)) E(at + '.keep', 'should be "+" or "-"');
      if (v.on != null && !views.includes(v.on)) E(at + '.on', 'should be one of ' + views.join(', '));
    });
    arr(plan.jigs, 'jigs').forEach((j, i) => {
      const at = 'jigs[' + i + ']'; keys(j, 'jig', at); if (!obj(j)) return;
      if (!j.title) E(at + '.title', 'missing');
      if (!arr(j.items, at + '.items').length) E(at + '.items', 'a shop aid needs a drawing');
      arr(j.for, at + '.for').forEach(id => { if (!has(id)) E(at + '.for', 'part ' + id + ' does not exist'); });
    });
    arr(plan.story_sticks, 'story_sticks').forEach((st, i) => {
      const at = 'story_sticks[' + i + ']'; keys(st, 'stick', at); if (!obj(st)) return;
      if (st.axis != null && !['x', 'y', 'z'].includes(st.axis)) E(at + '.axis', 'should be "x", "y" or "z"');
      arr(st.parts, at + '.parts').forEach(id => { if (!has(id)) E(at + '.parts', 'part ' + id + ' does not exist'); });
    });
    if (plan.finish != null) { keys(plan.finish, 'finish', 'finish'); arr(plan.finish.steps, 'finish.steps'); }
    arr(plan.steps, 'steps').forEach((s, i) => { if (s && s.wrong != null && typeof s.wrong !== 'string' && !(obj(s.wrong) && s.wrong.text)) E('steps[' + i + '].wrong', 'should be a sentence, or { text, items } with a drawing'); });
    // balloon leaders in a detail should not cross (a soft rule: warn, never fail)
    const X = (p1, p2, p3, p4) => { const d = (a, b, c) => (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0]); return d(p1, p2, p3) * d(p1, p2, p4) < 0 && d(p3, p4, p1) * d(p3, p4, p2) < 0; };
    arr(plan.details, 'details').forEach((d, i) => {
      const L = (d && Array.isArray(d.items) ? d.items : []).filter(t => t && Array.isArray(t.callout) && Array.isArray(t.to)).map(t => [t.callout.slice(0, 2).map(Number), t.to.map(Number), t.callout[2]]);
      L.forEach((l, a) => L.slice(a + 1).forEach(m => { if (X(l[0], l[1], m[0], m[1])) W('details[' + i + ']' + (d.title ? ' "' + d.title + '"' : ''), 'the leaders of balloons ' + l[2] + ' and ' + m[2] + ' cross; swap or move a balloon so they don\'t (allowed when there is no clean way)'); }));
    });
    arr(plan.details, 'details').forEach((d, i) => { if (d && d.pattern && !arr(d.items, 'details[' + i + '].items').length) E('details[' + i + ']', 'a full-size pattern needs items'); });
    return out;
  }
  module.exports = { validate, KEYS };
})();
