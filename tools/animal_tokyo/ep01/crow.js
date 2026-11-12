// リアル寄りのハシブトガラス（全長約56cm）。前方は -z、足元が原点。
// perchedCrow(): 止まっている姿（首・くちばしが動く） / crowModel(): 飛んでいる姿（はばたき）
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

function rng(seed) {
  let a = seed >>> 0;
  return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const lerp = (a, b, t) => a + (b - a) * t;
function tex(w, h, draw, srgb = true, repeat = true) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8; return t;
}
// 高さマップ（キャンバス）→ 法線マップ
function normalFromHeight(hc, strength = 2.5) {
  const w = hc.width, h = hc.height, src = hc.getContext('2d').getImageData(0, 0, w, h).data;
  const H = (x, y) => src[(((y + h) % h) * w + ((x + w) % w)) * 4] / 255;
  return tex(w, h, (g) => {
    const img = g.createImageData(w, h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const dx = (H(x + 1, y) - H(x - 1, y)) * strength, dy = (H(x, y + 1) - H(x, y - 1)) * strength;
      const l = Math.hypot(dx, dy, 1), i = (y * w + x) * 4;
      img.data[i] = (-dx / l * 0.5 + 0.5) * 255; img.data[i + 1] = (dy / l * 0.5 + 0.5) * 255; img.data[i + 2] = (1 / l * 0.5 + 0.5) * 255; img.data[i + 3] = 255;
    }
    g.putImageData(img, 0, 0);
  }, false);
}

// 体の羽：うろこ状に重なる小さな羽
let _M = null;
function materials() {
  if (_M) return _M;
  const r = rng(17);
  const S = 256;
  const hc = document.createElement('canvas'); hc.width = S; hc.height = S;
  const g = hc.getContext('2d');
  g.fillStyle = '#000'; g.fillRect(0, 0, S, S);
  const rows = 12, cols = 8;
  for (let j = rows + 1; j >= -1; j--) for (let i = -1; i <= cols; i++) {
    const x = (i + (j % 2) * 0.5) * S / cols + (r() - 0.5) * 6, y = j * S / rows + (r() - 0.5) * 4;
    const gr = g.createRadialGradient(x, y - 4, 1, x, y, S / cols * 0.75);
    gr.addColorStop(0, '#fff'); gr.addColorStop(0.7, '#888'); gr.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gr;
    for (const ox of [-S, 0, S]) for (const oy of [-S, 0, S]) { g.beginPath(); g.ellipse(x + ox, y + oy, S / cols * 0.62, S / rows * 1.1, 0, 0, Math.PI * 2); g.fill(); }
    g.strokeStyle = 'rgba(255,255,255,0.25)'; g.lineWidth = 0.6;
    for (let k = -3; k <= 3; k++) { g.beginPath(); g.moveTo(x, y - 6); g.lineTo(x + k * 3, y + 8); g.stroke(); }
  }
  const featherN = normalFromHeight(hc, 3);
  const rough = tex(S, S, (g2) => { g2.drawImage(hc, 0, 0); g2.globalCompositeOperation = 'difference'; g2.fillStyle = '#a0a0a0'; g2.fillRect(0, 0, S, S); }, false);
  const body = new THREE.MeshPhysicalMaterial({
    color: 0x0d0d11, roughness: 0.42, roughnessMap: rough, metalness: 0.0, normalMap: featherN, normalScale: new THREE.Vector2(0.35, 0.35),
    sheen: 0.5, sheenColor: new THREE.Color('#262a58'), sheenRoughness: 0.5,
    iridescence: 0.18, iridescenceIOR: 1.5, iridescenceThicknessRange: [250, 320],
    clearcoat: 0.25, clearcoatRoughness: 0.5, envMapIntensity: 1.2,
  });
  // 翼・尾羽：羽軸と羽枝が見える長い羽
  const wingH = document.createElement('canvas'); wingH.width = 512; wingH.height = 256;
  const wg = wingH.getContext('2d');
  wg.fillStyle = '#000'; wg.fillRect(0, 0, 512, 256);
  for (let k = 0; k < 14; k++) { // 雨覆（上側の短い羽）
    const x = k * 40; const gr = wg.createLinearGradient(x, 0, x + 40, 0); gr.addColorStop(0, '#bbb'); gr.addColorStop(1, '#333');
    wg.fillStyle = gr; wg.beginPath(); wg.ellipse(x + 20, 60, 26, 70, 0.2, 0, Math.PI * 2); wg.fill();
  }
  for (let k = 0; k < 12; k++) { // 風切羽（長い羽）
    const y = 110 + (k % 2) * 6; const x = k * 44;
    const gr = wg.createLinearGradient(x, 0, x + 44, 0); gr.addColorStop(0, '#fff'); gr.addColorStop(0.15, '#999'); gr.addColorStop(1, '#222');
    wg.fillStyle = gr; wg.fillRect(x, y, 46, 150);
    wg.strokeStyle = '#fff'; wg.lineWidth = 2; wg.beginPath(); wg.moveTo(x + 8, y); wg.lineTo(x + 8, 256); wg.stroke();
    wg.strokeStyle = 'rgba(255,255,255,0.18)'; wg.lineWidth = 0.7;
    for (let b = y; b < 256; b += 3) { wg.beginPath(); wg.moveTo(x + 8, b); wg.lineTo(x + 44, b + 10); wg.stroke(); }
  }
  const wingN = normalFromHeight(wingH, 4);
  const wingAlpha = tex(512, 256, (g2) => { // 羽先のギザギザ
    g2.fillStyle = '#fff'; g2.fillRect(0, 0, 512, 256);
    g2.fillStyle = '#000';
    for (let k = 0; k < 12; k++) { g2.beginPath(); g2.moveTo(k * 44 + 2, 256); g2.quadraticCurveTo(k * 44 + 30, 210 + (k % 3) * 8, k * 44 + 46, 256); g2.fill(); }
  }, false, false);
  const wing = new THREE.MeshPhysicalMaterial({
    color: 0x0c0c10, roughness: 0.4, normalMap: wingN, normalScale: new THREE.Vector2(0.3, 0.3), alphaMap: wingAlpha, alphaTest: 0.5, side: THREE.DoubleSide,
    sheen: 0.5, sheenColor: new THREE.Color('#2a2e60'), sheenRoughness: 0.45, iridescence: 0.2, iridescenceIOR: 1.5, iridescenceThicknessRange: [250, 320], envMapIntensity: 1.3,
  });
  const beak = new THREE.MeshPhysicalMaterial({ color: 0x111113, roughness: 0.3, clearcoat: 0.5, clearcoatRoughness: 0.35, envMapIntensity: 1.0 });
  const eyeT = tex(128, 128, (g2) => {
    g2.fillStyle = '#1a120c'; g2.fillRect(0, 0, 128, 128);
    const gr = g2.createRadialGradient(64, 64, 4, 64, 64, 60); gr.addColorStop(0, '#000'); gr.addColorStop(0.35, '#000'); gr.addColorStop(0.45, '#3a2414'); gr.addColorStop(0.9, '#20140c'); gr.addColorStop(1, '#0a0806');
    g2.fillStyle = gr; g2.beginPath(); g2.arc(64, 64, 62, 0, 7); g2.fill();
  }, true, false);
  const eye = new THREE.MeshPhysicalMaterial({ map: eyeT, roughness: 0.08, clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 0.7 });
  const leg = new THREE.MeshStandardMaterial({ color: 0x18181a, roughness: 0.6, normalMap: featherN, normalScale: new THREE.Vector2(0.4, 0.4) });
  _M = { body, wing, beak, eye, leg };
  return _M;
}

// 背骨カーブ＋断面の大きさから、なめらかな体を作る
function loft(curve, prof, s0, s1, rings = 48, segs = 28, uvRep = [6, 10]) {
  const pos = [], uv = [], idx = [];
  const up = new THREE.Vector3(0, 1, 0);
  for (let i = 0; i <= rings; i++) {
    const s = lerp(s0, s1, i / rings);
    const c = curve.getPointAt(s), T = curve.getTangentAt(s);
    const N = up.clone().addScaledVector(T, -up.dot(T)).normalize(), B = new THREE.Vector3().crossVectors(T, N).normalize();
    const p = prof(s);
    for (let j = 0; j <= segs; j++) {
      const a = (j / segs) * Math.PI * 2;
      const sn = Math.sin(a), cs = Math.cos(a);
      const v = c.clone().addScaledVector(B, cs * p.w).addScaledVector(N, sn * (sn > 0 ? p.top : p.bot) + (p.dy || 0));
      pos.push(v.x, v.y, v.z); uv.push(j / segs * uvRep[0], s * uvRep[1]);
    }
  }
  for (let i = 0; i < rings; i++) for (let j = 0; j < segs; j++) {
    const a = i * (segs + 1) + j, b = a + segs + 1;
    idx.push(a, b, a + 1, b, b + 1, a + 1);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
}
// 区分線形の断面テーブル
function table(rows) {
  return (s) => {
    let i = 0; while (i + 1 < rows.length && rows[i + 1][0] < s) i++;
    const a = rows[i], b = rows[Math.min(rows.length - 1, i + 1)];
    const t = b[0] === a[0] ? 0 : Math.min(1, Math.max(0, (s - a[0]) / (b[0] - a[0])));
    const e = t * t * (3 - 2 * t);
    return { w: lerp(a[1], b[1], e), top: lerp(a[2], b[2], e), bot: lerp(a[3], b[3], e) };
  };
}
const PROFILE = table([
  [0.0, 0.015, 0.014, 0.011], [0.035, 0.031, 0.041, 0.022], [0.09, 0.046, 0.049, 0.037], [0.16, 0.045, 0.043, 0.042],
  [0.25, 0.041, 0.038, 0.047], [0.37, 0.058, 0.054, 0.064], [0.54, 0.071, 0.061, 0.075], [0.72, 0.061, 0.051, 0.059],
  [0.88, 0.040, 0.033, 0.035], [1.0, 0.020, 0.015, 0.016],
]);

// くちばし（上下）
function beakGeos() {
  const up = new THREE.CatmullRomCurve3([new THREE.Vector3(0, 0.0, 0), new THREE.Vector3(0, 0.006, -0.028), new THREE.Vector3(0, 0.001, -0.053), new THREE.Vector3(0, -0.009, -0.068)]);
  const upper = loft(up, (s) => ({ w: 0.015 * Math.pow(1 - s, 0.75) + 0.0008, top: 0.016 * Math.pow(1 - s, 0.65) + 0.0008, bot: 0.006 * (1 - s) + 0.0008, dy: -0.002 }), 0, 1, 24, 18);
  const lo = new THREE.CatmullRomCurve3([new THREE.Vector3(0, -0.007, 0.002), new THREE.Vector3(0, -0.010, -0.03), new THREE.Vector3(0, -0.011, -0.06)]);
  const lower = loft(lo, (s) => ({ w: 0.013 * Math.pow(1 - s, 0.8) + 0.0006, top: 0.004 * (1 - s) + 0.0008, bot: 0.009 * Math.pow(1 - s, 0.9) + 0.0005 }), 0, 1, 20, 14);
  return { upper, lower };
}

let _G = null;
function geos() {
  if (_G) return _G;
  // 止まっている姿の背骨（頭 → 尾の付け根）
  const spine = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, 0.300, -0.140), new THREE.Vector3(0, 0.303, -0.098), new THREE.Vector3(0, 0.266, -0.060),
    new THREE.Vector3(0, 0.205, -0.036), new THREE.Vector3(0, 0.140, 0.004), new THREE.Vector3(0, 0.096, 0.055), new THREE.Vector3(0, 0.076, 0.105),
  ]);
  const neck = spine.getPointAt(0.22);
  const head = loft(spine, PROFILE, 0, 0.3, 40, 32, [10, 26]); head.translate(-neck.x, -neck.y, -neck.z);
  const body = loft(spine, PROFILE, 0.2, 1, 56, 32, [9, 16]);
  // 閉じた翼：体の側面にそわせた羽の面
  const wingFold = (side) => {
    const pos = [], uv = [], idx = []; const U = 28, V = 10;
    const tail = new THREE.Vector3(0, -0.55, 0.83);
    for (let i = 0; i <= U; i++) {
      const u = i / U; const s = lerp(0.34, 1.0, Math.min(1, u / 0.78));
      const ext = Math.max(0, (u - 0.78) / 0.22) * 0.13;
      const c = spine.getPointAt(s).addScaledVector(tail, ext), T = spine.getTangentAt(s);
      const N = new THREE.Vector3(0, 1, 0).addScaledVector(T, -T.y).normalize(), B = new THREE.Vector3().crossVectors(T, N).normalize();
      const p = PROFILE(s); const taper = 1 - Math.max(0, (u - 0.78) / 0.22) * 0.75;
      for (let j = 0; j <= V; j++) {
        const v = j / V; const a = lerp(1.3, -0.4, v);
        const off = 0.006 + 0.004 * Math.sin(Math.PI * v);
        const k = ext > 0 ? taper : 1;
        const v3 = c.clone().addScaledVector(B, -side * Math.cos(a) * (p.w + off) * k).addScaledVector(N, Math.sin(a) * ((Math.sin(a) > 0 ? p.top : p.bot) + off) * k);
        pos.push(v3.x, v3.y, v3.z); uv.push(v, 1 - u);
      }
    }
    for (let i = 0; i < U; i++) for (let j = 0; j < V; j++) { const a = i * (V + 1) + j, b = a + V + 1; idx.push(a, b, a + 1, b, b + 1, a + 1); }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals();
    return g;
  };
  // 尾羽（12枚を少しずつ扇状に）
  const tailCards = (base, dir, len) => {
    const parts = [];
    for (let k = 0; k < 12; k++) {
      const g = new THREE.PlaneGeometry(0.036, len, 1, 6); g.translate(0, -len / 2, 0);
      const p = g.attributes.position; for (let i = 0; i < p.count; i++) { const y = p.getY(i); p.setZ(i, 0.004 * Math.pow(y / len, 2) * 10); }
      const uvA = g.attributes.uv; for (let i = 0; i < uvA.count; i++) uvA.setXY(i, (k / 12) + uvA.getX(i) / 12, 0.45 + uvA.getY(i) * 0.55);
      g.rotateZ((k - 5.5) * 0.035); g.translate((k - 5.5) * 0.0025, 0, k * 0.0006);
      parts.push(g);
    }
    const m = mergeGeometries(parts);
    const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, -1, 0), dir.clone().normalize());
    m.applyQuaternion(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI / 2)); // 面を水平に
    m.applyQuaternion(q); m.translate(base.x, base.y, base.z);
    return m;
  };
  const tail = (() => {
    const parts = [];
    for (let k = 0; k < 12; k++) {
      const g = new THREE.PlaneGeometry(0.038, 0.21, 1, 6); g.rotateX(-Math.PI / 2); g.translate(0, 0, 0.105);
      const uvA = g.attributes.uv; for (let i = 0; i < uvA.count; i++) uvA.setXY(i, (k + uvA.getX(i)) / 12, 0.42 + uvA.getY(i) * 0.58);
      g.rotateY((k - 5.5) * 0.028); g.translate(0, k * 0.0005, 0); parts.push(g);
    }
    const m = mergeGeometries(parts); m.rotateX(0.62); m.translate(0, 0.08, 0.1); return m;
  })();
  // 鼻の上の剛毛
  const r = rng(3); const br = [];
  for (let k = 0; k < 46; k++) {
    const g = new THREE.ConeGeometry(0.0011, 0.02, 4); g.rotateX(-Math.PI / 2 - 0.15 - r() * 0.15); g.rotateY((r() - 0.5) * 0.7);
    g.translate((r() - 0.5) * 0.026, 0.304 + r() * 0.01 - neck.y, -0.132 - r() * 0.012 - neck.z); br.push(g);
  }
  const bristles = mergeGeometries(br);
  // 脚と指（枝をつかむ）
  const lg = [];
  for (const sx of [-1, 1]) {
    const t = new THREE.CylinderGeometry(0.0045, 0.0055, 0.07, 8); t.translate(sx * 0.022, 0.04, 0.004); lg.push(t);
    for (const [yaw, len] of [[-0.35, 0.034], [0, 0.04], [0.35, 0.032], [Math.PI, 0.03]]) {
      const pts = []; for (let k = 0; k <= 6; k++) { const a = k / 6 * 1.6; pts.push(new THREE.Vector3(0, 0.004 - (1 - Math.cos(a)) * len * 0.45, -Math.sin(a) * len * 0.75)); }
      const tg = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 8, 0.0028, 6); tg.rotateY(yaw); tg.translate(sx * 0.022, 0.004, 0.004); lg.push(tg);
    }
  }
  const legs = mergeGeometries(lg.map((g) => g.toNonIndexed()));
  // 飛んでいる姿：水平の背骨
  const fspine = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, 0.012, -0.185), new THREE.Vector3(0, 0.016, -0.15), new THREE.Vector3(0, 0.008, -0.11),
    new THREE.Vector3(0, 0.0, -0.06), new THREE.Vector3(0, -0.004, 0.0), new THREE.Vector3(0, -0.002, 0.06), new THREE.Vector3(0, 0.002, 0.11),
  ]);
  const fbody = loft(fspine, PROFILE, 0, 1, 64, 28, [6, 14]);
  const ftail = (() => {
    const parts = [];
    for (let k = 0; k < 12; k++) {
      const g = new THREE.PlaneGeometry(0.038, 0.2, 1, 4); g.rotateX(-Math.PI / 2); g.translate(0, 0, 0.1);
      const uvA = g.attributes.uv; for (let i = 0; i < uvA.count; i++) uvA.setXY(i, (k + uvA.getX(i)) / 12, 0.42 + uvA.getY(i) * 0.58);
      g.rotateY((k - 5.5) * 0.05); g.translate(0, k * 0.0004, 0); parts.push(g);
    }
    const m = mergeGeometries(parts); m.translate(0, 0, 0.1); return m;
  })();
  // 広げた翼：腕の部分＋手先（指のように分かれた初列風切）
  const wingArm = (() => {
    const s = new THREE.Shape(); s.moveTo(0, -0.06); s.lineTo(0.2, -0.045); s.lineTo(0.2, 0.11); s.quadraticCurveTo(0.1, 0.13, 0, 0.12);
    const g = new THREE.ShapeGeometry(s, 12); const p = g.attributes.position; const uvA = g.attributes.uv;
    for (let i = 0; i < p.count; i++) { const x = p.getX(i), y = p.getY(i); uvA.setXY(i, x / 0.2 * 0.5, (y + 0.06) / 0.19 * 0.9 + 0.05); p.setZ(i, -0.012 * Math.sin(Math.PI * (y + 0.06) / 0.19)); }
    g.rotateX(-Math.PI / 2); g.computeVertexNormals(); return g;
  })();
  const wingHand = (() => {
    const parts = [];
    const base = new THREE.Shape(); base.moveTo(0, -0.045); base.lineTo(0.12, -0.03); base.lineTo(0.12, 0.09); base.lineTo(0, 0.11);
    const bg = new THREE.ShapeGeometry(base, 6); const uvB = bg.attributes.uv; const pb = bg.attributes.position;
    for (let i = 0; i < pb.count; i++) uvB.setXY(i, 0.5 + pb.getX(i) / 0.12 * 0.3, (pb.getY(i) + 0.045) / 0.155 * 0.9 + 0.05);
    parts.push(bg);
    for (let k = 0; k < 7; k++) { // 指のような初列風切
      const len = 0.13 + Math.sin(k / 6 * Math.PI) * 0.03;
      const g = new THREE.PlaneGeometry(0.028, len, 1, 4); g.translate(0, len / 2, 0);
      const uvA = g.attributes.uv; for (let i = 0; i < uvA.count; i++) uvA.setXY(i, 0.8 + (k + uvA.getX(i)) / 7 * 0.2, 0.4 + (1 - uvA.getY(i)) * 0.6);
      g.rotateZ(-1.35 - k * 0.17); g.translate(0.1 + k * 0.002, 0.085 - k * 0.019, 0); parts.push(g);
    }
    const m = mergeGeometries(parts.map((g) => g.toNonIndexed())); m.rotateX(-Math.PI / 2); m.computeVertexNormals(); return m;
  })();
  const { upper, lower } = beakGeos();
  _G = { spine, neck, head, body, wingL: wingFold(-1), wingR: wingFold(1), tail, bristles, legs, upper, lower, fbody, ftail, wingArm, wingHand };
  return _G;
}

function headParts(M, G, jawPivot) {
  const head = new THREE.Group();
  head.add(new THREE.Mesh(G.head, M.body));
  const bpos = new THREE.Vector3(0, 0.300 - G.neck.y, -0.136 - G.neck.z);
  const up = new THREE.Mesh(G.upper, M.beak); up.position.copy(bpos); head.add(up);
  const jaw = new THREE.Group(); jaw.position.copy(bpos).add(new THREE.Vector3(0, -0.004, 0.004)); head.add(jaw);
  const lo = new THREE.Mesh(G.lower, M.beak); jaw.add(lo);
  head.add(new THREE.Mesh(G.bristles, M.body));
  for (const sx of [-1, 1]) {
    const e = new THREE.Mesh(new THREE.SphereGeometry(0.0085, 20, 14), M.eye);
    e.position.set(sx * 0.031, 0.311 - G.neck.y, -0.113 - G.neck.z); e.rotation.y = sx * Math.PI / 2; head.add(e);
  }
  return { head, jaw };
}

export function perchedCrow() {
  const M = materials(), G = geos();
  const g = new THREE.Group();
  const body = new THREE.Mesh(G.body, M.body); g.add(body);
  g.add(new THREE.Mesh(G.wingL, M.wing), new THREE.Mesh(G.wingR, M.wing), new THREE.Mesh(G.tail, M.wing), new THREE.Mesh(G.legs, M.leg));
  const { head, jaw } = headParts(M, G);
  const hp = new THREE.Group(); hp.position.copy(G.neck); hp.add(head); g.add(hp);
  g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  g.userData.head = hp;
  g.userData.jaw = jaw;
  g.userData.pose = ({ yaw = 0, pitch = 0, roll = 0, open = 0, fluff = 0 } = {}) => {
    hp.rotation.set(pitch, yaw, roll); jaw.rotation.x = open * 0.45;
    body.scale.set(1 + fluff * 0.12, 1 + fluff * 0.08, 1 + fluff * 0.04);
  };
  return g;
}

export function crowModel() {
  const M = materials(), G = geos();
  const g = new THREE.Group();
  g.add(new THREE.Mesh(G.fbody, M.body), new THREE.Mesh(G.ftail, M.wing));
  const bp = new THREE.Mesh(G.upper, M.beak); bp.position.set(0, 0.014, -0.18); g.add(bp);
  const bl = new THREE.Mesh(G.lower, M.beak); bl.position.set(0, 0.01, -0.176); g.add(bl);
  const wings = [];
  for (const side of [-1, 1]) {
    const sh = new THREE.Group(); sh.position.set(side * 0.035, 0.02, -0.06); g.add(sh);
    const arm = new THREE.Mesh(G.wingArm, M.wing); arm.scale.x = side; sh.add(arm);
    const el = new THREE.Group(); el.position.set(side * 0.2, 0, 0); sh.add(el);
    const hand = new THREE.Mesh(G.wingHand, M.wing); hand.scale.x = side; el.add(hand);
    wings.push({ sh, el, side });
  }
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  // a: 肩の角度（+で上）。打ち上げの時は手先を少したたむ
  g.userData.flap = (a) => {
    for (const { sh, el, side } of wings) {
      sh.rotation.z = side * a;
      el.rotation.z = side * (a > 0 ? a * 0.35 : a * 0.25);
      el.rotation.y = side * (a > 0.3 ? -(a - 0.3) * 0.5 : 0);
    }
  };
  return g;
}
