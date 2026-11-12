// 共通ユーティリティ：乱数・ノイズ・手続き的テクスチャ・街／森／カラスの生成
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
export const easeOut = (t) => 1 - Math.pow(1 - clamp(t), 3);
export const easeInOut = (t) => { t = clamp(t); return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };

// 3D value noise
function hash3(x, y, z) {
  let h = (x * 374761393 + y * 668265263 + z * 2147483647) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
export function noise3(x, y, z) {
  const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z);
  const xf = x - xi, yf = y - yi, zf = z - zi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf), w = zf * zf * (3 - 2 * zf);
  const c = (i, j, k) => hash3(xi + i, yi + j, zi + k);
  const x00 = lerp(c(0, 0, 0), c(1, 0, 0), u), x10 = lerp(c(0, 1, 0), c(1, 1, 0), u);
  const x01 = lerp(c(0, 0, 1), c(1, 0, 1), u), x11 = lerp(c(0, 1, 1), c(1, 1, 1), u);
  return lerp(lerp(x00, x10, v), lerp(x01, x11, v), w) * 2 - 1;
}
export const noise1 = (t, seed = 0) => noise3(t, seed * 13.1, seed * 7.7);

// 首を「カクッ」と動かす鳥の頭の動き。keys: [{t, yaw, pitch, roll}]
export function snapHead(keys, t, snap = 0.11) {
  let i = 0;
  while (i + 1 < keys.length && keys[i + 1].t <= t) i++;
  const k = keys[i], p = keys[Math.max(0, i - 1)];
  const s = i === 0 ? 1 : easeOut((t - k.t) / snap);
  const o = {};
  for (const n of ['yaw', 'pitch', 'roll']) o[n] = lerp(p[n] || 0, k[n] || 0, s);
  return o;
}

// ---------- 手続き的テクスチャ ----------
export function canvasTex(w, h, draw, { srgb = true, repeat = true, aniso = 8 } = {}) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = c.getContext('2d');
  draw(g, w, h);
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; }
  t.anisotropy = aniso;
  return t;
}

function speckle(g, w, h, r, n, alpha, light = false) {
  for (let i = 0; i < n; i++) {
    const v = Math.floor(r() * 255);
    g.fillStyle = light ? `rgba(255,255,255,${alpha * r()})` : `rgba(${v},${v},${v},${alpha})`;
    const s = 1 + r() * 2.5;
    g.fillRect(r() * w, r() * h, s, s);
  }
}

// ビルの外壁。8x8セル = 1タイル。kind: 'glass' | 'concrete'
export function facadeTextures(seed, kind, lit, warm = 0.7) {
  const r = rng(seed);
  const S = 512, C = 64;
  const layout = [];
  for (let j = 0; j < 8; j++) for (let i = 0; i < 8; i++) {
    const on = r() < lit;
    const tone = r();
    const blind = r() < 0.4 ? 0.3 + r() * 0.6 : 1;
    layout.push({ on, tone, blind, warmPick: r() < warm, glass: r() });
  }
  const map = canvasTex(S, S, (g) => {
    g.fillStyle = kind === 'glass' ? '#7d858e' : '#9b968d';
    g.fillRect(0, 0, S, S);
    speckle(g, S, S, r, 6000, 0.08);
    layout.forEach((L, idx) => {
      const i = idx % 8, j = Math.floor(idx / 8);
      const x = i * C, y = j * C;
      if (kind === 'glass') {
        const gr = g.createLinearGradient(x, y, x, y + C);
        const b = 30 + L.glass * 26;
        gr.addColorStop(0, `rgb(${b + 20},${b + 30},${b + 42})`);
        gr.addColorStop(1, `rgb(${b},${b + 8},${b + 16})`);
        g.fillStyle = gr; g.fillRect(x + 3, y + 4, C - 6, C - 8);
      } else {
        const b = 26 + L.glass * 18;
        g.fillStyle = `rgb(${b},${b + 4},${b + 8})`;
        g.fillRect(x + 12, y + 14, C - 24, C - 30);
        g.fillStyle = 'rgba(60,58,54,0.9)';
        g.fillRect(x + 6, y + C - 14, C - 12, 3); // ベランダの手すり
        g.fillRect(x + 6, y + C - 8, C - 12, 2);
      }
    });
    g.fillStyle = 'rgba(0,0,0,0.12)'; // 汚れ
    for (let i = 0; i < 40; i++) g.fillRect(r() * S, r() * S, 1 + r() * 2, 20 + r() * 80);
  });
  const emissive = canvasTex(S, S, (g) => {
    g.fillStyle = '#000'; g.fillRect(0, 0, S, S);
    layout.forEach((L, idx) => {
      if (!L.on) return;
      const i = idx % 8, j = Math.floor(idx / 8);
      const x = i * C, y = j * C;
      const k = 0.55 + L.tone * 0.45;
      const col = L.warmPick ? [255 * k, 196 * k, 128 * k] : [200 * k, 225 * k, 255 * k];
      g.fillStyle = `rgb(${col.map(Math.floor).join(',')})`;
      if (kind === 'glass') {
        const hh = (C - 8) * L.blind;
        g.fillRect(x + 3, y + 4 + (C - 8 - hh), C - 6, hh);
      } else {
        const hh = (C - 30) * L.blind;
        g.fillRect(x + 12, y + 14 + (C - 30 - hh), C - 24, hh);
      }
    });
  });
  return { map, emissive };
}

export function asphaltTex(seed) {
  const r = rng(seed);
  return canvasTex(512, 512, (g, w, h) => {
    g.fillStyle = '#3c3d3f'; g.fillRect(0, 0, w, h);
    speckle(g, w, h, r, 40000, 0.35);
    speckle(g, w, h, r, 3000, 0.25, true);
    for (let i = 0; i < 12; i++) { // ひび・補修跡
      g.strokeStyle = `rgba(20,20,22,${0.3 + r() * 0.3})`; g.lineWidth = 1 + r() * 2;
      g.beginPath(); let x = r() * w, y = r() * h; g.moveTo(x, y);
      for (let k = 0; k < 8; k++) { x += (r() - 0.5) * 60; y += (r() - 0.5) * 60; g.lineTo(x, y); }
      g.stroke();
    }
    for (let i = 0; i < 4; i++) { g.fillStyle = `rgba(30,30,32,0.35)`; g.fillRect(r() * w, r() * h, 60 + r() * 120, 40 + r() * 90); }
  });
}

export function barkTex(seed) {
  const r = rng(seed);
  return canvasTex(256, 512, (g, w, h) => {
    g.fillStyle = '#3a2f26'; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 260; i++) {
      const v = 30 + r() * 50;
      g.strokeStyle = `rgba(${v},${v * 0.82},${v * 0.66},0.7)`; g.lineWidth = 1 + r() * 4;
      const x = r() * w; g.beginPath(); g.moveTo(x, r() * h); g.lineTo(x + (r() - 0.5) * 10, r() * h); g.stroke();
    }
    speckle(g, w, h, r, 4000, 0.2);
    g.fillStyle = 'rgba(90,110,70,0.25)'; // 苔
    for (let i = 0; i < 30; i++) { g.beginPath(); g.arc(r() * w, r() * h, 4 + r() * 14, 0, 7); g.fill(); }
  });
}

export function leafTex() {
  return canvasTex(128, 256, (g, w, h) => {
    g.clearRect(0, 0, w, h);
    const path = new Path2D();
    path.moveTo(w / 2, 6);
    path.bezierCurveTo(w * 0.98, h * 0.3, w * 0.9, h * 0.75, w / 2, h - 18);
    path.bezierCurveTo(w * 0.1, h * 0.75, w * 0.02, h * 0.3, w / 2, 6);
    const gr = g.createLinearGradient(0, 0, w, h);
    gr.addColorStop(0, '#5f7f3e'); gr.addColorStop(1, '#2e4a22');
    g.fillStyle = gr; g.fill(path);
    g.strokeStyle = 'rgba(200,220,150,0.45)'; g.lineWidth = 3;
    g.beginPath(); g.moveTo(w / 2, 10); g.lineTo(w / 2, h - 4); g.stroke();
    g.lineWidth = 1.2;
    for (let k = 1; k < 7; k++) {
      const y = h * k / 8;
      g.beginPath(); g.moveTo(w / 2, y); g.quadraticCurveTo(w * 0.7, y - 10, w * 0.86, y - 26); g.stroke();
      g.beginPath(); g.moveTo(w / 2, y); g.quadraticCurveTo(w * 0.3, y - 10, w * 0.14, y - 26); g.stroke();
    }
  }, { repeat: false });
}

// 風切羽（翼の先）。黒に青紫のつや
export function featherTex() {
  return canvasTex(512, 256, (g, w, h) => {
    g.clearRect(0, 0, w, h);
    for (let i = 0; i < 9; i++) {
      const x0 = 30 + i * 52;
      const len = 150 + i * 10;
      g.save(); g.translate(x0, h - 10); g.rotate(-0.18 + i * 0.04);
      const gr = g.createLinearGradient(0, 0, 0, -len);
      gr.addColorStop(0, '#0b0b10'); gr.addColorStop(0.6, '#15162a'); gr.addColorStop(1, '#0a0a0e');
      g.fillStyle = gr;
      g.beginPath(); g.moveTo(-22, 0);
      g.quadraticCurveTo(-26, -len * 0.7, -6, -len); g.quadraticCurveTo(14, -len * 0.75, 22, 0); g.closePath(); g.fill();
      g.strokeStyle = 'rgba(70,70,90,0.6)'; g.lineWidth = 1.5;
      g.beginPath(); g.moveTo(0, 0); g.lineTo(-4, -len + 6); g.stroke();
      g.restore();
    }
    g.fillStyle = '#0b0b10'; g.fillRect(0, h - 40, w, 40);
  }, { repeat: false });
}

// ---------- 建物 ----------
function boxWithWorldUV(w, h, d, cellW = 3.6, cellH = 3.5, ox = 0, oy = 0) {
  const g = new THREE.BoxGeometry(w, h, d);
  const uv = g.attributes.uv;
  for (let i = 0; i < uv.count; i++) {
    const face = Math.floor(i / 4);
    let u = uv.getX(i), v = uv.getY(i);
    if (face === 2 || face === 3) { u = 0.002; v = 0.002; } // 屋上は枠の色
    else {
      const fw = face < 2 ? d : w;
      u = u * fw / (cellW * 8) + ox; v = v * h / (cellH * 8) + oy;
    }
    uv.setXY(i, u, v);
  }
  return g;
}

// 街。spec: {seed, x0,x1,z0,z1, spacing, hMin, hMax, towers:[{x,z,r,h}], lit, avoid(x,z)->bool}
export function buildCity(spec) {
  const r = rng(spec.seed);
  const glassT = facadeTextures(spec.seed + 1, 'glass', spec.lit, 0.5);
  const concT = facadeTextures(spec.seed + 2, 'concrete', spec.lit * 1.1, 0.8);
  const eI = spec.emissive ?? 2.2;
  const glassM = new THREE.MeshStandardMaterial({ map: glassT.map, emissiveMap: glassT.emissive, emissive: 0xffffff, emissiveIntensity: eI, roughness: 0.25, metalness: 0.6 });
  const concM = new THREE.MeshStandardMaterial({ map: concT.map, emissiveMap: concT.emissive, emissive: 0xffffff, emissiveIntensity: eI, roughness: 0.85, metalness: 0.0 });
  const roofM = new THREE.MeshStandardMaterial({ color: 0x6d6d6a, roughness: 0.9 });
  const gG = [], cG = [], rG = [];
  const beacons = [];
  const s = spec.spacing;
  for (let x = spec.x0; x < spec.x1; x += s) for (let z = spec.z0; z < spec.z1; z += s) {
    if (r() < (spec.skip ?? 0.12)) continue;
    const cx = x + (r() - 0.5) * s * 0.2, cz = z + (r() - 0.5) * s * 0.2;
    if (spec.avoid && spec.avoid(cx, cz)) continue;
    let h = lerp(spec.hMin, spec.hMax, Math.pow(r(), 2.2));
    for (const t of spec.towers || []) {
      const dd = Math.hypot(cx - t.x, cz - t.z);
      if (dd < t.r) h = Math.max(h, t.h * (0.45 + 0.55 * (1 - dd / t.r)) * (0.6 + r() * 0.5));
    }
    const w = s * (0.45 + r() * 0.4), d = s * (0.45 + r() * 0.4);
    const glass = h > 45 ? r() < 0.75 : r() < 0.15;
    const geo = boxWithWorldUV(w, h, d, 3.6, 3.5, Math.floor(r() * 8) / 8, Math.floor(r() * 8) / 8);
    geo.translate(cx, h / 2, cz);
    (glass ? gG : cG).push(geo);
    // 屋上設備
    const n = Math.floor(r() * 3);
    for (let k = 0; k < n; k++) {
      const uw = 1 + r() * w * 0.3, uh = 1 + r() * 3, ud = 1 + r() * d * 0.3;
      const ug = new THREE.BoxGeometry(uw, uh, ud);
      ug.translate(cx + (r() - 0.5) * (w - uw), h + uh / 2, cz + (r() - 0.5) * (d - ud));
      rG.push(ug);
    }
    if (h > 90) beacons.push(new THREE.Vector3(cx + w * 0.45, h + 0.6, cz + d * 0.45), new THREE.Vector3(cx - w * 0.45, h + 0.6, cz - d * 0.45));
  }
  const group = new THREE.Group();
  if (gG.length) group.add(new THREE.Mesh(mergeGeometries(gG), glassM));
  if (cG.length) group.add(new THREE.Mesh(mergeGeometries(cG), concM));
  if (rG.length) group.add(new THREE.Mesh(mergeGeometries(rG), roofM));
  group.children.forEach((m) => { m.castShadow = !!spec.shadows; m.receiveShadow = !!spec.shadows; });
  // 航空障害灯（赤く点滅）
  const beaconM = new THREE.MeshBasicMaterial({ color: new THREE.Color(6, 0.3, 0.2) });
  if (beacons.length) {
    const bm = new THREE.InstancedMesh(new THREE.SphereGeometry(0.9, 8, 6), beaconM, beacons.length);
    beacons.forEach((p, i) => bm.setMatrixAt(i, new THREE.Matrix4().makeTranslation(p.x, p.y, p.z)));
    group.add(bm);
  }
  group.userData.update = (t) => {
    const on = (t % 1.5) < 0.75 ? 1 : 0.08;
    beaconM.color.setRGB(6 * on, 0.3 * on, 0.2 * on);
  };
  group.userData.mats = { glassM, concM };
  return group;
}

// ---------- 森 ----------
function crownGeometry(seed) {
  const r = rng(seed);
  const parts = [];
  for (let k = 0; k < 5; k++) {
    const g = new THREE.IcosahedronGeometry(0.55 + r() * 0.35, 3);
    const off = new THREE.Vector3((r() - 0.5) * 0.9, (r() - 0.3) * 0.5, (r() - 0.5) * 0.9);
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const v = new THREE.Vector3().fromBufferAttribute(p, i);
      const n = noise3(v.x * 3 + k * 9, v.y * 3, v.z * 3) * 0.22 + noise3(v.x * 9, v.y * 9 + k, v.z * 9) * 0.08;
      v.multiplyScalar(1 + n).add(off);
      p.setXYZ(i, v.x, v.y, v.z);
    }
    g.computeVertexNormals();
    parts.push(g);
  }
  const m = mergeGeometries(parts);
  m.computeVertexNormals();
  return m;
}

// spec: {seed, count, x0,x1,z0,z1, yBase, size:[min,max], exclude(x,z)->bool, colors}
export function buildCanopy(spec) {
  const r = rng(spec.seed);
  const geo = crownGeometry(spec.seed + 5);
  const mat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.95, metalness: 0 });
  const mesh = new THREE.InstancedMesh(geo, mat, spec.count);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler();
  const cols = (spec.colors || ['#1c3519', '#24401e', '#2f4b24', '#1a2e1a', '#3b5428']).map((c) => new THREE.Color(c));
  const accent = [new THREE.Color('#8a7a2a'), new THREE.Color('#6e4a22')];
  let n = 0;
  for (let tries = 0; n < spec.count && tries < spec.count * 4; tries++) {
    const x = lerp(spec.x0, spec.x1, r()), z = lerp(spec.z0, spec.z1, r());
    if (spec.exclude && spec.exclude(x, z)) continue;
    const s = lerp(spec.size[0], spec.size[1], r());
    const y = (spec.yBase || 0) + s * (0.9 + r() * 0.7) + (spec.yJitter || 0) * r();
    e.set((r() - 0.5) * 0.3, r() * 6.28, (r() - 0.5) * 0.3); q.setFromEuler(e);
    m.compose(new THREE.Vector3(x, y, z), q, new THREE.Vector3(s, s * (0.7 + r() * 0.3), s));
    mesh.setMatrixAt(n, m);
    const c = r() < 0.04 ? accent[Math.floor(r() * 2)] : cols[Math.floor(r() * cols.length)];
    mesh.setColorAt(n, c.clone().multiplyScalar(0.8 + r() * 0.4));
    n++;
  }
  mesh.count = n;
  mesh.castShadow = mesh.receiveShadow = !!spec.shadows;
  return mesh;
}

// カメラのまわりの葉（至近距離）。forward 方向の円錐 gapDeg には置かない
export function buildLeafCloud(spec) {
  const r = rng(spec.seed);
  const tex = leafTex();
  const mat = new THREE.MeshStandardMaterial({ map: tex, alphaTest: 0.5, side: THREE.DoubleSide, roughness: 0.85, metalness: 0 });
  const geo = new THREE.PlaneGeometry(spec.leafSize * 0.55, spec.leafSize);
  geo.translate(0, spec.leafSize / 2, 0);
  const mesh = new THREE.InstancedMesh(geo, mat, spec.count);
  const fwd = spec.forward.clone().normalize();
  const cosGap = Math.cos(THREE.MathUtils.degToRad(spec.gapDeg));
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler();
  let n = 0;
  const twigs = Math.ceil(spec.count / 14);
  for (let t = 0; t < twigs * 6 && n < spec.count; t++) {
    const dir = new THREE.Vector3(r() * 2 - 1, (r() * 2 - 1) * 0.8, r() * 2 - 1).normalize();
    if (dir.dot(fwd) > cosGap) continue;
    if (spec.minY !== undefined && dir.y < spec.minY) continue;
    const dist = lerp(spec.rMin, spec.rMax, Math.pow(r(), 0.7));
    const c = spec.center.clone().addScaledVector(dir, dist);
    for (let k = 0; k < 14 && n < spec.count; k++) {
      const p = c.clone().add(new THREE.Vector3((r() - 0.5) * 0.35, (r() - 0.5) * 0.25, (r() - 0.5) * 0.35));
      e.set(r() * 6.28, r() * 6.28, r() * 6.28); q.setFromEuler(e);
      const s = 0.75 + r() * 0.5;
      m.compose(p, q, new THREE.Vector3(s, s, s));
      mesh.setMatrixAt(n, m);
      const g = 0.4 + r() * 0.35;
      mesh.setColorAt(n, new THREE.Color(g, g * (0.95 + r() * 0.1), g * 0.85));
      n++;
    }
  }
  mesh.count = n;
  return mesh;
}

export function skyDome(opts) {
  const u = {
    zenith: { value: new THREE.Color(opts.zenith) },
    horizon: { value: new THREE.Color(opts.horizon) },
    ground: { value: new THREE.Color(opts.ground || opts.horizon) },
    glow: { value: new THREE.Color(opts.glow || '#000000') },
    sunDir: { value: opts.sunDir.clone().normalize() },
    glowSize: { value: opts.glowSize ?? 8 },
    sunDisk: { value: opts.sunDisk ?? 0 },
    exp: { value: opts.exp ?? 0.45 },
  };
  const mat = new THREE.ShaderMaterial({
    uniforms: u, side: THREE.BackSide, depthWrite: false, fog: false,
    vertexShader: `varying vec3 vDir; void main(){ vDir = position; vec4 p = modelViewMatrix*vec4(position,1.); gl_Position = projectionMatrix*p; gl_Position.z = gl_Position.w*0.9999; }`,
    fragmentShader: `uniform vec3 zenith, horizon, ground, glow; uniform vec3 sunDir; uniform float glowSize, sunDisk, exp; varying vec3 vDir;
      float h21(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233)))*43758.5453); }
      void main(){ vec3 d = normalize(vDir); float h = d.y;
        vec3 c = h > 0. ? mix(horizon, zenith, pow(clamp(h,0.,1.), exp)) : mix(horizon, ground, clamp(-h*6.,0.,1.));
        float s = max(dot(d, normalize(sunDir)), 0.);
        float band = exp2(-abs(h)*10.);
        c += glow * (pow(s, glowSize) * 1.2 + pow(s, glowSize*0.25) * 0.35 * band);
        c += glow * sunDisk * smoothstep(0.9994, 0.9998, s) * 8.;
        c += (h21(gl_FragCoord.xy) - 0.5) / 255.;
        gl_FragColor = vec4(c, 1.); }`,
  });
  const m = new THREE.Mesh(new THREE.SphereGeometry(9000, 48, 24), mat);
  m.frustumCulled = false; m.renderOrder = -10;
  m.userData.u = u;
  return m;
}

// ハシブトガラスのくちばし（カメラの子にする）
export function beakMesh() {
  const g = new THREE.ConeGeometry(0.016, 0.085, 20, 6);
  g.rotateX(-Math.PI / 2);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const z = p.getZ(i), y = p.getY(i);
    const t = (z + 0.0425) / 0.085; // 0 = 先端, 1 = 根元
    p.setY(i, y * 1.25 + (y > 0 ? 0.004 : 0) - 0.012 * Math.pow(1 - t, 2));
    p.setX(i, p.getX(i) * 0.85);
  }
  g.computeVertexNormals();
  g.scale(0.8, 0.8, 0.8);
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0x0b0b0c, roughness: 0.7, metalness: 0.0 }));
  return m;
}

// カメラの左右に見え隠れする翼の先
export function wingPair() {
  const tex = featherTex();
  const mat = new THREE.MeshStandardMaterial({ map: tex, alphaTest: 0.4, side: THREE.DoubleSide, roughness: 0.45, metalness: 0.15, color: 0xffffff });
  const mk = (side) => {
    const pivot = new THREE.Group();
    const g = new THREE.PlaneGeometry(0.9, 0.45);
    g.translate(0.45, 0, 0);
    const mesh = new THREE.Mesh(g, mat);
    mesh.rotation.x = -Math.PI / 2 + 0.25;
    if (side < 0) { mesh.scale.x = -1; }
    pivot.add(mesh);
    pivot.position.set(side * 0.08, -0.06, 0.12);
    pivot.userData.side = side;
    return pivot;
  };
  const L = mk(-1), R = mk(1);
  const grp = new THREE.Group(); grp.add(L, R);
  grp.userData.set = (flap, sweep = 0) => {
    for (const w of [L, R]) {
      const s = w.userData.side;
      w.rotation.set(0, s * (-0.35 + sweep), s * flap);
    }
  };
  return grp;
}

// 群れ用のカラス
export function crowModel(mat) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.SphereGeometry(1, 16, 12), mat); body.scale.set(0.09, 0.085, 0.24); g.add(body);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.075, 14, 10), mat); head.position.set(0, 0.03, -0.24); g.add(head);
  const bk = new THREE.Mesh(new THREE.ConeGeometry(0.025, 0.09, 10), mat); bk.rotation.x = -Math.PI / 2; bk.position.set(0, 0.02, -0.34); g.add(bk);
  const tailS = new THREE.Shape(); tailS.moveTo(-0.03, 0); tailS.lineTo(-0.09, 0.2); tailS.lineTo(0.09, 0.2); tailS.lineTo(0.03, 0);
  const tail = new THREE.Mesh(new THREE.ShapeGeometry(tailS), mat); tail.rotation.x = Math.PI / 2; tail.position.set(0, 0.01, 0.18); g.add(tail);
  const wingShape = () => {
    const s = new THREE.Shape(); s.moveTo(0, -0.1); s.lineTo(0.25, -0.12); s.lineTo(0.5, -0.08);
    for (let k = 0; k < 5; k++) { s.lineTo(0.5 + 0.05 * k + 0.06, 0.02 + k * 0.035); s.lineTo(0.52 + 0.05 * k, 0.04 + k * 0.035); }
    s.lineTo(0.3, 0.14); s.lineTo(0, 0.1); return new THREE.ShapeGeometry(s);
  };
  const wings = [];
  for (const side of [-1, 1]) {
    const piv = new THREE.Group();
    const w = new THREE.Mesh(wingShape(), mat); w.rotation.x = Math.PI / 2; if (side < 0) w.scale.x = -1;
    piv.add(w); piv.position.set(side * 0.05, 0.03, -0.03); g.add(piv); wings.push([piv, side]);
  }
  g.userData.flap = (a) => { for (const [p, s] of wings) p.rotation.z = s * a; };
  return g;
}

// ゴミ袋（半透明の袋に中身が透ける）
export function garbageBag(r, scale = 1) {
  const grp = new THREE.Group();
  const g = new THREE.SphereGeometry(0.28, 28, 20);
  const p = g.attributes.position;
  const sd = r() * 100;
  for (let i = 0; i < p.count; i++) {
    const v = new THREE.Vector3().fromBufferAttribute(p, i);
    const n = noise3(v.x * 9 + sd, v.y * 9, v.z * 9) * 0.08 + noise3(v.x * 25 + sd, v.y * 25, v.z * 25) * 0.035 + Math.abs(noise3(v.x * 60 + sd, v.y * 60, v.z * 60)) * 0.02;
    v.multiplyScalar(1 + n);
    if (v.y < -0.12) v.y = -0.12 - (v.y + 0.12) * 0.25; // 底がつぶれる
    v.y *= 1.15;
    p.setXYZ(i, v.x, v.y, v.z);
  }
  g.computeVertexNormals();
  const bagM = new THREE.MeshPhysicalMaterial({ color: 0xf2f4f0, roughness: 0.28, metalness: 0, transparent: true, opacity: 0.88, clearcoat: 1.0, clearcoatRoughness: 0.15, bumpMap: crinkleTex(), bumpScale: 3, side: THREE.DoubleSide, depthWrite: false });
  const bag = new THREE.Mesh(g, bagM);
  bag.castShadow = true; bag.receiveShadow = true; bag.renderOrder = 2;
  grp.add(bag);
  // 中身
  const colors = [0x7a5a3a, 0xc8b070, 0x5a7a3a, 0xa04030, 0xdcdcd0, 0x3a3a40, 0xe0a040];
  for (let k = 0; k < 9; k++) {
    const s = 0.035 + r() * 0.045;
    const geo = r() < 0.5 ? new THREE.BoxGeometry(s * 1.6, s * 0.5, s) : new THREE.IcosahedronGeometry(s * 0.7, 0);
    const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: colors[Math.floor(r() * colors.length)], roughness: 0.7 }));
    m.position.set((r() - 0.5) * 0.24, -0.1 + r() * 0.14, (r() - 0.5) * 0.24); m.rotation.set(r() * 3, r() * 3, r() * 3);
    grp.add(m);
  }
  const knot = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.12, 10), bagM);
  knot.position.y = 0.33; grp.add(knot);
  grp.scale.setScalar(scale);
  grp.userData.bag = bag;
  return grp;
}

let _crinkle = null;
export function crinkleTex() {
  if (_crinkle) return _crinkle;
  const r = rng(99);
  _crinkle = canvasTex(512, 512, (g, w, h) => {
    g.fillStyle = '#808080'; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 420; i++) {
      const v = r() < 0.5 ? 40 : 220;
      g.strokeStyle = `rgba(${v},${v},${v},${0.25 + r() * 0.4})`; g.lineWidth = 0.6 + r() * 2.2;
      g.beginPath(); let x = r() * w, y = r() * h; g.moveTo(x, y);
      for (let k = 0; k < 3; k++) { x += (r() - 0.5) * 90; y += (r() - 0.5) * 90; g.lineTo(x, y); }
      g.stroke();
    }
  }, { srgb: false });
  return _crinkle;
}

export function netTex() {
  return canvasTex(256, 256, (g, w, h) => {
    g.clearRect(0, 0, w, h);
    g.strokeStyle = '#2f8a4a'; g.lineWidth = 5;
    for (let i = 0; i <= 8; i++) {
      g.beginPath(); g.moveTo(i * 32, 0); g.lineTo(i * 32, h); g.stroke();
      g.beginPath(); g.moveTo(0, i * 32); g.lineTo(w, i * 32); g.stroke();
    }
  });
}

// 電線（たるみのある細い円柱）
export function wire(a, b, sag, radius, mat) {
  const pts = [];
  for (let i = 0; i <= 24; i++) {
    const t = i / 24;
    const p = a.clone().lerp(b, t); p.y -= sag * 4 * t * (1 - t);
    pts.push(p);
  }
  return new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 48, radius, 6), mat);
}
