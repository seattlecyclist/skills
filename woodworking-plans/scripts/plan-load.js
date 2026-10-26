/* plan-load.js — load a plan file the same way everywhere (build, review, selftest, render check).
 *   const { load, prepare } = require('./plan-load.js');
 *   const plan = load('plan.js');               // or load('plan.js', { ...PARAMS, railT: 2 })
 * A plan.js exports build(PARAMS, J) (J = joints.js) or the plan object; plan.json works too.
 * prepare() numbers unnamed joints J1, J2 … in order and fills in missing explode vectors.
 */
const fs = require('fs');
const path = require('path');
const J = require('./joints.js');
const X = require('./explode.js');

function prepare(plan) {
  (plan.joints || []).forEach((j, i) => { if (j.id == null) j.id = 'J' + (i + 1); });
  X.auto(plan);
  return plan;
}
function load(file, params) {
  const abs = path.resolve(file);
  let plan;
  if (/\.(c?js)$/.test(abs)) {
    delete require.cache[abs];
    const m = require(abs);
    plan = typeof m === 'function' ? m(params || m.PARAMS, J) : (m.plan || m);
  } else plan = JSON.parse(fs.readFileSync(abs, 'utf8'));
  return prepare(plan);
}
module.exports = { load, prepare, J };
