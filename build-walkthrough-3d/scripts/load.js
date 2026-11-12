/* Load a build file in Node: the engine first (it defines globalThis.Walkthrough), then the build,
   which sets globalThis.PLAN. Each call loads fresh copies, so mutations never leak between runs. */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ENGINE = path.join(__dirname, '..', 'assets', 'engine.js');
function load(file) {
  const ctx = { console, Math, JSON, Object, Array, Set, Map, Number, String, Error, Infinity };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(ENGINE, 'utf8'), ctx, { filename: ENGINE });
  const src = path.resolve(file);
  vm.runInContext(fs.readFileSync(src, 'utf8'), ctx, { filename: src });
  if (!ctx.PLAN) throw new Error(file + ' did not set PLAN (end it with root.PLAN = K.finish({...}))');
  return ctx.PLAN;
}
module.exports = { load };
