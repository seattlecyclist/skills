// motion-video kit: everything a scene needs to be a pure function of time.
// Import it from a scene page next to three.js:
//   import * as THREE from "three";
//   import * as K from "./kit.js";
// Nothing here reads the clock or Math.random. Every function takes t (seconds) and returns state.

import * as THREE from "three";

// ---------------------------------------------------------------- time
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, k) => a + (b - a) * k;
/** 0 before t0, 1 after t1, linear between. */
export const ramp = (t, t0, t1) => clamp((t - t0) / (t1 - t0));
/** Smootherstep: zero speed and zero acceleration at both ends, so moves never snap. */
export const smooth = k => k * k * k * (k * (k * 6 - 15) + 10);
/** Overshoots a little and settles: for things that land. */
export const backOut = (k, s = 1.4) => { k -= 1; return k * k * ((s + 1) * k + s) + 1; };
/** In for `inDur`, hold, out for `outDur`: the opacity of anything that appears for a window. */
export const window01 = (t, t0, t1, inDur = 0.35, outDur = 0.3) => smooth(ramp(t, t0, t0 + inDur)) * (1 - smooth(ramp(t, t1 - outDur, t1)));
/** Deterministic random: same seed, same sequence, every frame and every render. */
export function seeded(seed) { return () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }; }

// ---------------------------------------------------------------- format
/** ?format=v gives a 9:16 vertical cut, ?format=s a 1:1 square, anything else 16:9. */
export function format(params = new URLSearchParams(location.search)) {
  const f = params.get("format");
  if (f === "v") return { name: "v", width: 1080, height: 1920, vertical: true };
  if (f === "s") return { name: "s", width: 1080, height: 1080, vertical: false };
  return { name: "h", width: 1920, height: 1080, vertical: false };
}

// ---------------------------------------------------------------- stage
/** A WebGL canvas with a 2D overlay canvas above it, both at exactly width x height. */
export function stage({ width, height, background = "#ECE7DF", fov = 32, exposure = 1.05, shadows = true }) {
  const root = document.getElementById("stage") || document.body.appendChild(Object.assign(document.createElement("div"), { id: "stage" }));
  Object.assign(root.style, { position: "relative", width: width + "px", height: height + "px" });
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1); renderer.setSize(width, height);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = exposure;
  renderer.shadowMap.enabled = shadows; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const overlay = document.createElement("canvas"); overlay.width = width; overlay.height = height;
  for (const c of [renderer.domElement, overlay]) Object.assign(c.style, { position: "absolute", inset: "0", width: width + "px", height: height + "px" });
  root.append(renderer.domElement, overlay);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(background);
  scene.fog = new THREE.Fog(background, 120, 260);
  const camera = new THREE.PerspectiveCamera(fov, width / height, 0.5, 600);
  return { renderer, scene, camera, overlay, g: overlay.getContext("2d"), width, height };
}

/** A warm key light with soft shadows, a sky fill and a cool rim: reads well on wood, paper and plastic. */
export function studioLights(scene, { shadowSize = 60 } = {}) {
  scene.add(new THREE.HemisphereLight(0xfff6ea, 0x8a7360, 1.25));
  const key = new THREE.DirectionalLight(0xffe6c8, 2.2);
  key.position.set(-30, 60, 35); key.castShadow = true; key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, { left: -shadowSize, right: shadowSize, top: shadowSize, bottom: -shadowSize, near: 1, far: 200 });
  key.shadow.bias = -0.0004; key.shadow.radius = 4;
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xdfe8ff, 0.45); rim.position.set(40, 25, -20); scene.add(rim);
  return key;
}

// ---------------------------------------------------------------- textures
/** A canvas texture you redraw each frame (call tex.needsUpdate = true after drawing). */
export function canvasTexture(w, h) {
  const canvas = document.createElement("canvas"); canvas.width = w; canvas.height = h;
  const tex = new THREE.CanvasTexture(canvas); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 16;
  return { canvas, g: canvas.getContext("2d"), tex };
}
export const loadImage = src => new Promise((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = () => no(new Error("missing image " + src)); i.src = src; });

/** A flat plane showing an image at its own aspect ratio: a printed page, a screenshot, a photo. */
export function imagePlane(img, widthUnits, { flat = true } = {}) {
  const tex = new THREE.Texture(img); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 16; tex.needsUpdate = true;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(widthUnits, widthUnits * img.height / img.width), new THREE.MeshStandardMaterial({ map: tex, roughness: 0.9 }));
  if (flat) m.rotation.x = -Math.PI / 2;
  m.receiveShadow = true; m.castShadow = true;
  return m;
}

/** Procedural wood grain, for a bench, a floor or a tabletop. */
export function woodTexture({ base = "#B88B5E", line = "80,48,24", boards = 6, seed = 7, w = 2048, h = 1024 } = {}) {
  const { canvas, g, tex } = canvasTexture(w, h), rnd = seeded(seed);
  g.fillStyle = base; g.fillRect(0, 0, w, h);
  for (let b = 0; b < boards; b++) {
    const y0 = b * h / boards;
    g.fillStyle = `rgba(${90 + rnd() * 30},${55 + rnd() * 20},30,${0.08 + rnd() * 0.08})`; g.fillRect(0, y0, w, h / boards);
    for (let i = 0; i < 70; i++) {
      const y = y0 + rnd() * h / boards, amp = 2 + rnd() * 6, f = 0.002 + rnd() * 0.004;
      g.strokeStyle = `rgba(${line},${0.05 + rnd() * 0.12})`; g.lineWidth = 0.6 + rnd() * 1.6;
      g.beginPath(); for (let x = 0; x <= w; x += 16) g.lineTo(x, y + Math.sin(x * f + i) * amp); g.stroke();
    }
    g.fillStyle = "rgba(60,36,18,0.35)"; g.fillRect(0, y0, w, 2);
  }
  tex.needsUpdate = true; canvas.dataset.kind = "wood";
  return tex;
}

// ---------------------------------------------------------------- camera
/**
 * A shot list: [[t, [x,y,z] position, [x,y,z] target], ...]. Between keys the camera eases with
 * smootherstep, so every move starts and ends at rest. Two keys with the same pose make a hold;
 * a slightly different pose makes a slow drift. Give each beat one camera job.
 */
export function cameraAt(camera, shots, t) {
  let i = 0; while (i < shots.length - 2 && t >= shots[i + 1][0]) i++;
  const [t0, p0, q0] = shots[i], [t1, p1, q1] = shots[i + 1];
  const k = smooth(ramp(t, t0, t1));
  camera.position.set(lerp(p0[0], p1[0], k), lerp(p0[1], p1[1], k), lerp(p0[2], p1[2], k));
  camera.lookAt(lerp(q0[0], q1[0], k), lerp(q0[1], q1[1], k), lerp(q0[2], q1[2], k));
}

// ---------------------------------------------------------------- assembly
/**
 * Parts that fly in from an exploded offset and land at their place, one after another.
 * parts: [{ mesh, at: [x,y,z], from: [dx,dy,dz], land: seconds }]. Call update(t) each frame.
 */
export function assembly(parts, { fly = 0.75, spin = 1 } = {}) {
  return {
    parts,
    update(t) {
      for (const p of parts) {
        const k = ramp(t, p.land - fly, p.land), e = backOut(k);
        p.mesh.visible = k > 0;
        p.mesh.position.set(p.at[0] + p.from[0] * (1 - e), p.at[1] + p.from[1] * (1 - e), p.at[2] + p.from[2] * (1 - e));
        p.mesh.rotation.set((1 - e) * 0.5 * spin * Math.sign(p.from[2] || 1), (1 - e) * 0.7 * spin, (1 - e) * -0.35 * spin * Math.sign(p.from[0] || 1));
      }
    },
  };
}

/** A box with dark edge lines: the "technical drawing come to life" look. */
export function outlinedBox(size, { color = "#F2D3BC", edge = "#1E2327", roughness = 0.7 } = {}) {
  const geo = size.isBufferGeometry ? size : new THREE.BoxGeometry(...size);
  const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color, roughness }));
  m.castShadow = true; m.receiveShadow = true;
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geo), new THREE.LineBasicMaterial({ color: edge, transparent: true }));
  m.add(edges); m.userData.edges = edges;
  return m;
}

/** A sprite that always faces the camera and draws on top: labels, balloons, callouts. */
export function spriteFrom(drawFn, w, h, worldW) {
  const { canvas, g, tex } = canvasTexture(w, h);
  drawFn(g, w, h); tex.needsUpdate = true;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  s.scale.set(worldW, worldW * h / w, 1); s.renderOrder = 10;
  return s;
}

/**
 * A dimension line that draws itself out from its middle, with end ticks, and a label that pops in.
 * a, b: endpoints; tick: direction of the end ticks; t0: when it starts drawing.
 */
export function dimension(scene, { a, b, tick = [0, 1, 0], label, t0, draw = 0.55, color = "#1E2327", font = "600 64px monospace", chip = "#FAFAF8", labelOffset = 1.2 }) {
  const mat = new THREE.LineBasicMaterial({ color, transparent: true, depthTest: false });
  const line = new THREE.LineSegments(new THREE.BufferGeometry(), mat); line.renderOrder = 9; line.frustumCulled = false;
  scene.add(line);
  const sprite = spriteFrom((g, w, h) => {
    g.fillStyle = chip; roundRect(g, 10, 14, w - 20, h - 28, 10); g.fill();
    g.fillStyle = color; g.font = font; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(label, w / 2, h / 2 + 2);
  }, 320, 120, 2.9);
  scene.add(sprite);
  const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), M = A.clone().lerp(B, 0.5), T = new THREE.Vector3(...tick).multiplyScalar(0.45);
  sprite.position.copy(M).add(new THREE.Vector3(...tick).multiplyScalar(labelOffset));
  return {
    update(t, fade = 1) {
      const k = smooth(ramp(t, t0, t0 + draw));
      line.visible = k > 0 && fade > 0;
      if (line.visible) {
        const pts = [M.clone().lerp(A, k), M.clone().lerp(B, k)];
        if (k > 0.98) for (const P of [A, B]) pts.push(P.clone().add(T), P.clone().sub(T));
        line.geometry.setFromPoints(pts);
      }
      mat.opacity = fade;
      const la = smooth(ramp(t, t0 + draw * 0.8, t0 + draw + 0.2)) * fade;
      sprite.visible = la > 0; sprite.material.opacity = la;
    },
  };
}

// ---------------------------------------------------------------- 2D drawing
export function roundRect(g, x, y, w, h, r) {
  g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
}
/** A numbered or lettered balloon, as on an exploded-view drawing. */
export function balloon(g, x, y, r, label, { fill = "#fff", ring = "#1E2327", text = "#1E2327", font = "monospace" } = {}) {
  g.fillStyle = fill; g.strokeStyle = ring; g.lineWidth = r * 0.12;
  g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill(); g.stroke();
  g.fillStyle = text; g.font = `600 ${r * (String(label).length > 1 ? 0.95 : 1.15)}px ${font}`;
  g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(label, x, y + r * 0.06);
  g.textAlign = "left"; g.textBaseline = "alphabetic";
}
/** Types text out: the first n characters at time t, for a typing window [t0, t1]. */
export const typed = (text, t, t0, t1) => text.slice(0, Math.round(text.length * ramp(t, t0, t1)));

/** Wraps text into lines no wider than maxW at the current font. */
export function wrapLines(g, text, maxW) {
  const out = []; let line = "";
  for (const w of text.split(" ")) {
    const test = line ? line + " " + w : w;
    if (g.measureText(test).width > maxW && line) { out.push(line); line = w; } else line = test;
  }
  if (line) out.push(line);
  return out;
}

/**
 * A rubber stamp that slams down at t0 with a small settle wobble. Draw onto any 2D context
 * (a paper texture or the overlay).
 */
export function stamp(g, t, t0, { x, y, rotate = -0.12, w = 660, h = 300, color = "#2F6B4A", title = "APPROVED", sub = "", titleFont = "800 92px sans-serif", subFont = "600 36px monospace" }) {
  const s = ramp(t, t0 - 0.18, t0);
  if (s <= 0) return;
  const k = s < 1 ? 1 + (1 - s) * 1.4 : 1;
  const settle = t > t0 ? 1 + Math.sin((t - t0) * 30) * Math.exp(-(t - t0) * 14) * 0.04 : 1;
  g.save(); g.translate(x, y); g.rotate(rotate); g.scale(k * settle, k * settle);
  g.globalAlpha = s < 1 ? s * 0.7 : 0.93;
  g.strokeStyle = color; g.fillStyle = color; g.lineWidth = 12;
  roundRect(g, -w / 2, -h / 2, w, h, 22); g.stroke();
  g.lineWidth = 4; roundRect(g, -w / 2 + 24, -h / 2 + 24, w - 48, h - 48, 12); g.stroke();
  g.textAlign = "center"; g.font = titleFont; g.fillText(title, 0, sub ? -8 : 30);
  if (sub) { g.font = subFont; g.fillText(sub, 0, 70); }
  g.textAlign = "left"; g.restore();
}

/**
 * A caption card: kicker, headline, one line of support. Slides up and fades in for its window.
 * Layout follows the format: lower-left at 16:9, full-width near the bottom at 9:16.
 */
export function caption(g, t, c, { width, height, vertical, fonts, colors }) {
  const a = window01(t, c.t[0], c.t[1]);
  if (a <= 0) return;
  const slide = (1 - smooth(ramp(t, c.t[0], c.t[0] + 0.45))) * 24;
  g.save(); g.globalAlpha = a; g.translate(0, slide);
  const hs = vertical ? 72 : 76, ss = vertical ? 30 : 34;
  g.font = `800 ${hs}px ${fonts.display}`; const hw = g.measureText(c.head).width;
  g.font = `400 ${ss}px ${fonts.body}`; const sw = c.sub ? g.measureText(c.sub).width : 0;
  const bw = vertical ? width - 120 : Math.max(hw, sw) + 112, bx = vertical ? 60 : 88, bh = c.sub ? 214 : 170, by = vertical ? height - 420 : height - 290;
  g.fillStyle = colors.card; roundRect(g, bx, by, bw, bh, 6); g.fill();
  g.fillStyle = colors.accent; g.fillRect(bx, by, 8, bh);
  if (c.kicker) { g.font = `600 24px ${fonts.mono}`; g.fillStyle = colors.accent; g.fillText(c.kicker, bx + 52, by + 52); }
  g.font = `800 ${hs}px ${fonts.display}`; g.fillStyle = colors.ink; g.fillText(c.head, bx + 50, by + 128);
  if (c.sub) { g.font = `400 ${ss}px ${fonts.body}`; g.fillStyle = colors.muted; g.fillText(c.sub, bx + 52, by + 182); }
  g.restore();
}

/**
 * A screenshot shown in a plain browser window that fades in, pushes in slowly, then shrinks away.
 * Pass a canvas you have drawn the screenshot (and any typing or reveals) onto, and the part of it
 * to show. focusX moves the push toward one side (0..1 of the shown width).
 */
export function browserWindow(g, t, src, { width, height, crop, scale, push = 0.12, focusX = 0.5, t0 = 0, t1, outDur = 0.7, address = "", fonts, colors }) {
  const out = smooth(ramp(t, t1 - outDur, t1)), inA = smooth(ramp(t, t0, t0 + 0.35));
  if (out >= 1 || t < t0) return;
  const k = smooth(ramp(t, t0 + 0.4, t1 - outDur));
  const s = scale * (1 + push * k) * (1 - 0.35 * out);
  const cw = crop.w * s, ch = crop.h * s;
  const fx = lerp(0.5, focusX, k);
  const x = width / 2 - (fx - 0.5) * cw - cw / 2, y = height / 2 - ch / 2 + 12;
  const bh = 34 * s / scale;
  g.save(); g.globalAlpha = inA * (1 - out);
  g.shadowColor = "rgba(30,35,39,0.28)"; g.shadowBlur = 50; g.shadowOffsetY = 18;
  g.fillStyle = colors.card; roundRect(g, x, y - bh, cw, ch + bh, 8); g.fill();
  g.shadowColor = "transparent";
  g.fillStyle = colors.chrome; roundRect(g, x, y - bh, cw, bh + 4, 8); g.fill();
  for (let i = 0; i < 3; i++) { g.fillStyle = colors.dots; g.beginPath(); g.arc(x + (22 + i * 20) * s / scale, y - bh / 2, 5.5 * s / scale, 0, Math.PI * 2); g.fill(); }
  if (address) { g.fillStyle = colors.muted; g.font = `500 ${15 * s / scale}px ${fonts.mono}`; g.textAlign = "center"; g.fillText(address, x + cw / 2, y - bh / 2 + 5 * s / scale); g.textAlign = "left"; }
  g.drawImage(src, crop.x, crop.y, crop.w, crop.h, x, y, cw, ch);
  g.restore();
}

/** A full-frame end card: name, tagline phrases that appear on cue, and a URL. */
export function endCard(g, t, { t0, width, height, vertical, name, phrases = [], cues = [], url = "", fonts, colors, nameSize = 150, underline = true }) {
  const e = smooth(ramp(t, t0, t0 + 0.6));
  if (e <= 0) return;
  g.save();
  g.fillStyle = colors.card; g.globalAlpha = e; g.fillRect(0, 0, width, height);
  const cy = vertical ? height * 0.43 : height * 0.44;
  g.font = `800 ${nameSize}px ${fonts.display}`; const nw = g.measureText(name).width;
  g.fillStyle = colors.ink; g.fillText(name, width / 2 - nw / 2, cy);
  if (underline) {
    const grow = smooth(ramp(t, cues[0] ?? t0, (cues[0] ?? t0) + 0.6)), mid = width / 2;
    g.strokeStyle = colors.accent; g.lineWidth = 6;
    g.beginPath(); g.moveTo(mid - nw / 2 * grow, cy + 52); g.lineTo(mid + nw / 2 * grow, cy + 52); g.stroke();
    if (grow > 0.98) { g.beginPath(); g.moveTo(mid - nw / 2, cy + 30); g.lineTo(mid - nw / 2, cy + 74); g.moveTo(mid + nw / 2, cy + 30); g.lineTo(mid + nw / 2, cy + 74); g.stroke(); }
  }
  g.font = `400 ${vertical ? 58 : 46}px ${fonts.body}`; g.fillStyle = colors.ink;
  const at = i => e * smooth(ramp(t, (cues[i + 1] ?? t0 + 0.5 + i * 0.6) - 0.1, (cues[i + 1] ?? t0 + 0.5 + i * 0.6) + 0.3));
  if (vertical) {
    g.textAlign = "center";
    phrases.forEach((p, i) => { g.globalAlpha = at(i); g.fillText(p, width / 2, cy + 190 + i * 80); });
  } else {
    const full = phrases.join(" "); let x = width / 2 - g.measureText(full).width / 2;
    phrases.forEach((p, i) => { g.globalAlpha = at(i); g.fillText(p, x, cy + 170); x += g.measureText(p + " ").width; });
  }
  if (url) {
    const last = cues[phrases.length] ?? t0 + 0.5 + phrases.length * 0.6;
    g.textAlign = "center"; g.font = `600 34px ${fonts.mono}`; g.fillStyle = colors.accent;
    g.globalAlpha = e * smooth(ramp(t, last + 0.4, last + 0.8));
    g.fillText(url, width / 2, vertical ? cy + 190 + phrases.length * 80 + 120 : cy + 260);
  }
  g.restore();
}

// ---------------------------------------------------------------- sound
/**
 * Synthesizes the film's effects and music offline from an event list, so every sound is tied to a
 * picture event. Put each sound one frame after its event: it reads as caused by it.
 *
 * events: [[kind, t, arg], ...] with kinds tick, send, whoosh, knock, pencil, paper, thud, shimmer, chime.
 * music: { chords: [[t, [hz, hz, hz, hz]], ...], grid: 0.25, until, fadeFrom, rest: [t0, t1] } or null.
 * Returns a base64 16-bit stereo WAV, which render.mjs saves beside the video.
 */
export async function renderSound({ duration, events = [], music = null, seed = 3, sampleRate = 48000 }) {
  const SR = sampleRate, ctx = new OfflineAudioContext(2, Math.ceil(SR * duration), SR), rnd = seeded(seed);
  const master = ctx.createGain(); master.gain.value = 0.8; master.connect(ctx.destination);
  const nb = ctx.createBuffer(1, SR * 2, SR), nd = nb.getChannelData(0);
  for (let i = 0; i < nd.length; i++) nd[i] = rnd() * 2 - 1;
  const noise = (t, dur, type, freq, q, gain, attack = 0.002, out = master) => {
    const src = ctx.createBufferSource(); src.buffer = nb;
    const f = ctx.createBiquadFilter(); f.type = type; f.frequency.value = freq; f.Q.value = q;
    const g = ctx.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(gain, t + attack); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    src.connect(f).connect(g).connect(out); src.start(Math.max(0, t), rnd()); src.stop(t + dur + 0.05);
    return f;
  };
  const tone = (t, freq, dur, gain, type = "sine", attack = 0.004, pan = 0, out = master) => {
    const o = ctx.createOscillator(); o.type = type; o.frequency.value = freq;
    const g = ctx.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(gain, t + attack); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    const p = ctx.createStereoPanner(); p.pan.value = pan;
    o.connect(g).connect(p).connect(out); o.start(Math.max(0, t)); o.stop(t + dur + 0.05);
    return o;
  };
  const SOUNDS = {
    tick: (t, i = 0) => { noise(t, 0.025, "bandpass", 3200 + (i % 5) * 300, 4, 0.18); tone(t, 1900 + (i % 3) * 150, 0.02, 0.02); },
    send: t => { tone(t, 880, 0.12, 0.07); tone(t + 0.07, 1320, 0.18, 0.06); },
    whoosh: t => { const f = noise(t, 0.9, "bandpass", 400, 1.2, 0.2, 0.35); f.frequency.setValueAtTime(300, t); f.frequency.exponentialRampToValueAtTime(2600, t + 0.8); },
    knock: (t, i = 0) => {
      const base = [196, 208, 220, 233, 174, 185, 165, 247, 262, 147, 131][i % 11];
      const o = tone(t, base * 1.6, 0.22, 0.36, "sine", 0.002); o.frequency.exponentialRampToValueAtTime(base, t + 0.08);
      tone(t, base * 2.76, 0.09, 0.1, "triangle", 0.001); noise(t, 0.05, "bandpass", 1400, 2, 0.3, 0.001);
    },
    pencil: (t, dur = 0.55) => { for (let i = 0; i < 9; i++) noise(t + i * dur / 9, dur / 9 * 1.3, "bandpass", 4200 + rnd() * 1500, 3, 0.05 + rnd() * 0.04, 0.01); },
    paper: t => { noise(t - 0.35, 0.45, "bandpass", 2400, 0.8, 0.12, 0.2); noise(t, 0.12, "lowpass", 700, 0.7, 0.25, 0.002); },
    thud: t => { const o = tone(t, 140, 0.35, 0.85, "sine", 0.002); o.frequency.exponentialRampToValueAtTime(48, t + 0.25); noise(t, 0.12, "lowpass", 900, 0.7, 0.55, 0.001); noise(t, 0.06, "highpass", 2500, 0.7, 0.16, 0.001); },
    shimmer: t => [523.25, 659.25, 783.99, 1046.5].forEach((f, i) => tone(t + i * 0.09, f, 1.4, 0.04, "sine", 0.02, (i - 1.5) * 0.3)),
    chime: t => [[523.25, 0], [783.99, 0.12], [1046.5, 0.24], [1567.98, 0.36]].forEach(([f, d]) => { tone(t + d, f, 2.2, 0.09, "sine", 0.004); tone(t + d, f * 2.01, 0.9, 0.02, "sine", 0.004); }),
  };
  for (const [kind, t, arg] of events) {
    if (!SOUNDS[kind]) throw new Error(`unknown sound "${kind}"`);
    SOUNDS[kind](t, arg);
  }
  if (music) {
    // a soft plucked arpeggio on a grid, with a sustained root every two bars
    const bus = ctx.createGain(); bus.gain.value = music.gain ?? 0.55; bus.connect(master);
    const grid = music.grid ?? 0.25, until = music.until ?? duration - 0.5, fadeFrom = music.fadeFrom ?? until - 2;
    for (let t = grid; t < until; t += grid) {
      if (music.rest && t > music.rest[0] && t < music.rest[1]) continue;
      const ch = music.chords.filter(c => c[0] <= t).pop()[1], step = Math.round(t / grid);
      const fade = t > fadeFrom ? Math.max(0, 1 - (t - fadeFrom) / (until - fadeFrom)) : 1;
      tone(t, ch[[0, 2, 1, 3, 2, 1][step % 6]] * 2, 0.5, 0.05 * fade, "triangle", 0.005, ((step % 4) - 1.5) * 0.25, bus);
      if (step % 8 === 0) tone(t, ch[0], 2.2, 0.07 * fade, "sine", 0.05, 0, bus);
    }
  }
  return wavBase64(await ctx.startRendering());
}

function wavBase64(buf) {
  const n = buf.length, L = buf.getChannelData(0), R = buf.numberOfChannels > 1 ? buf.getChannelData(1) : L, SR = buf.sampleRate;
  const ab = new ArrayBuffer(44 + n * 4), dv = new DataView(ab);
  const ws = (o, s) => [...s].forEach((c, i) => dv.setUint8(o + i, c.charCodeAt(0)));
  ws(0, "RIFF"); dv.setUint32(4, 36 + n * 4, true); ws(8, "WAVEfmt "); dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 2, true);
  dv.setUint32(24, SR, true); dv.setUint32(28, SR * 4, true); dv.setUint16(32, 4, true); dv.setUint16(34, 16, true); ws(36, "data"); dv.setUint32(40, n * 4, true);
  for (let i = 0; i < n; i++) { dv.setInt16(44 + i * 4, clamp(L[i], -1, 1) * 32767, true); dv.setInt16(46 + i * 4, clamp(R[i], -1, 1) * 32767, true); }
  let bin = ""; const u8 = new Uint8Array(ab);
  for (let i = 0; i < u8.length; i += 0x8000) bin += String.fromCharCode(...u8.subarray(i, i + 0x8000));
  return btoa(bin);
}

// ---------------------------------------------------------------- boot
/** Waits for fonts, e.g. ["800 40px Inter"]. Call it before drawing any sprite or texture with text. */
export async function loadFonts(list = []) {
  for (const f of list) await document.fonts.load(f);
  await document.fonts.ready;
}

/**
 * Finishes a scene: waits for fonts, publishes the render contract and, when opened in a normal
 * browser, plays it on a loop. ?t=3.2 freezes one moment for inspection.
 *   window.scene = { width, height, duration }   window.renderAt(t)   window.renderAudio()   window.ready
 */
export async function boot({ width, height, duration, renderAt, renderAudio, fonts = [] }) {
  await loadFonts(fonts);
  window.scene = { width, height, duration };
  window.renderAt = renderAt;
  if (renderAudio) window.renderAudio = renderAudio;
  const q = new URLSearchParams(location.search).get("t");
  if (q !== null) renderAt(parseFloat(q));
  else if (!navigator.webdriver) {
    const t0 = performance.now();
    const loop = () => { renderAt(((performance.now() - t0) / 1000) % duration); requestAnimationFrame(loop); };
    loop();
  } else renderAt(0);
  window.ready = true;
}
