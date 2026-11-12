// 日中のカット：貯食・水浴び・昼の休息・屋上・ねぐら入り前の集合
import * as THREE from 'three';
import { perchedCrow } from './crow.js';
import {
  rng, clamp, lerp, smooth, easeOut, easeInOut, noise1, noise3, snapHead, canvasTex,
  buildCity, buildCanopy, buildLeafCloud, skyDome, beakMesh, wingPair, crowModel, featherTex, wire, asphaltTex, barkTex,
} from './lib.js';

const ASPECT = 720 / 1280;
function cam(fov = 72) {
  const c = new THREE.PerspectiveCamera(fov, ASPECT, 0.01, 16000);
  c.rotation.order = 'YXZ';
  return c;
}
const head = (c, h) => c.rotation.set(h.pitch, h.yaw, h.roll);
function jitter(c, t, a = 0.004) { c.rotation.x += noise1(t * 8, 11) * a; c.rotation.y += noise1(t * 8, 12) * a; }

function daylight(scene, { sunDir, sunColor = '#fff2e0', sunI = 2.6, hemiSky = '#c4d6ee', hemiGround = '#6a6458', hemiI = 1.5, box = 20, center = new THREE.Vector3(), sky, fog }) {
  scene.add(skyDome({ zenith: '#3f74c2', horizon: '#dde6ee', glow: '#fff3dc', glowSize: 40, exp: 0.5, sunDir, ...(sky || {}) }));
  scene.fog = new THREE.FogExp2(fog?.[0] || '#c8d4e0', fog?.[1] ?? 0.004);
  scene.add(new THREE.HemisphereLight(hemiSky, hemiGround, hemiI));
  const s = new THREE.DirectionalLight(sunColor, sunI);
  s.position.copy(center).addScaledVector(sunDir.clone().normalize(), 120);
  s.target.position.copy(center);
  s.castShadow = true; s.shadow.mapSize.set(2048, 2048);
  Object.assign(s.shadow.camera, { left: -box, right: box, top: box, bottom: -box, near: 1, far: 400 });
  s.shadow.bias = -0.0004; s.shadow.normalBias = 0.02;
  scene.add(s, s.target);
  return s;
}

function plane(w, h, mat, y = 0) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
  m.rotation.x = -Math.PI / 2; m.position.y = y; m.receiveShadow = true; return m;
}

const soilTex = (seed) => { const r = rng(seed); return canvasTex(512, 512, (g, w, h) => {
  g.fillStyle = '#4a3828'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 30000; i++) { const v = 40 + r() * 60; g.fillStyle = `rgba(${v},${v * 0.78},${v * 0.58},0.6)`; g.fillRect(r() * w, r() * h, 1 + r() * 3, 1 + r() * 3); }
  for (let i = 0; i < 260; i++) { const v = 70 + r() * 45; g.fillStyle = `rgb(${v},${v * 0.92},${v * 0.82})`; g.beginPath(); g.arc(r() * w, r() * h, 0.8 + r() * 1.6, 0, 7); g.fill(); }
}); };
const grassTex = (seed, base = [120, 140, 80]) => { const r = rng(seed); return canvasTex(512, 512, (g, w, h) => {
  g.fillStyle = `rgb(${base.join(',')})`; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 40000; i++) { const k = 0.6 + r() * 0.7; g.strokeStyle = `rgba(${base[0] * k | 0},${base[1] * k | 0},${base[2] * k | 0},0.7)`; g.lineWidth = 1; const x = r() * w, y = r() * h; g.beginPath(); g.moveTo(x, y); g.lineTo(x + (r() - 0.5) * 3, y - 3 - r() * 5); g.stroke(); }
  for (let i = 0; i < 40; i++) { g.fillStyle = `rgba(150,130,70,${0.15 + r() * 0.2})`; g.beginPath(); g.ellipse(r() * w, r() * h, 10 + r() * 40, 6 + r() * 20, r() * 3, 0, 7); g.fill(); }
}); };
const tileTex = () => canvasTex(512, 512, (g, w, h) => {
  const r = rng(5); const cols = ['#b9b2a6', '#a9a196', '#c4beb2', '#8f877d'];
  for (let y = 0; y < 16; y++) for (let x = 0; x < 8; x++) {
    g.fillStyle = cols[Math.floor(r() * 4)]; g.fillRect(x * 64 + (y % 2) * 32, y * 32, 62, 30);
    g.fillStyle = cols[Math.floor(r() * 4)]; g.fillRect(x * 64 + (y % 2) * 32 - 512, y * 32, 62, 30);
  }
  for (let i = 0; i < 8000; i++) { g.fillStyle = `rgba(0,0,0,${r() * 0.08})`; g.fillRect(r() * w, r() * h, 2, 2); }
});

// イチョウの落ち葉（扇形）
function ginkgoLeaves(seed, count, area, y) {
  const r = rng(seed);
  const tex = canvasTex(128, 128, (g) => {
    g.clearRect(0, 0, 128, 128);
    g.fillStyle = '#e8c23a'; g.beginPath(); g.moveTo(64, 120); g.lineTo(10, 30); g.quadraticCurveTo(64, -5, 118, 30); g.closePath(); g.fill();
    g.strokeStyle = 'rgba(160,120,20,0.6)'; for (let k = 0; k < 9; k++) { g.beginPath(); g.moveTo(64, 120); g.lineTo(14 + k * 12.5, 26); g.stroke(); }
    g.fillStyle = '#c9a02a'; g.fillRect(62, 100, 4, 28);
  }, { repeat: false });
  const geo = new THREE.PlaneGeometry(0.06, 0.06); geo.rotateX(-Math.PI / 2);
  const mesh = new THREE.InstancedMesh(geo, new THREE.MeshStandardMaterial({ map: tex, alphaTest: 0.5, side: THREE.DoubleSide, roughness: 0.8 }), count);
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), E = new THREE.Euler();
  for (let i = 0; i < count; i++) {
    E.set((r() - 0.5) * 0.4, r() * 6.28, (r() - 0.5) * 0.4); Q.setFromEuler(E);
    const s = 0.7 + r() * 0.6;
    M.compose(new THREE.Vector3(lerp(area[0], area[1], r()), y + r() * 0.01, lerp(area[2], area[3], r())), Q, new THREE.Vector3(s, s, s));
    mesh.setMatrixAt(i, M);
    const k = 0.75 + r() * 0.35; mesh.setColorAt(i, new THREE.Color(k, k * (0.85 + r() * 0.2), k * 0.8));
  }
  mesh.receiveShadow = true;
  return { mesh, tex };
}

export function people(N, seed, spec) {
  const r = rng(seed);
  const bodyG = new THREE.CapsuleGeometry(0.21, 1.0, 4, 10); bodyG.translate(0, 0.72, 0);
  const headG = new THREE.SphereGeometry(0.115, 12, 10); headG.translate(0, 1.55, 0);
  const bodies = new THREE.InstancedMesh(bodyG, new THREE.MeshStandardMaterial({ roughness: 0.85 }), N);
  const heads = new THREE.InstancedMesh(headG, new THREE.MeshStandardMaterial({ roughness: 0.7 }), N);
  bodies.castShadow = heads.castShadow = true;
  const coat = ['#141414', '#1d2433', '#3b3b3e', '#8a7a62', '#5a4a3a', '#c8c2b5', '#2e3a2e', '#6a2a2a', '#d9d4c8', '#3a5a7a'].map((c) => new THREE.Color(c));
  const hair = ['#0d0b0a', '#1a1410', '#3a2a1e', '#2a2a2a'].map((c) => new THREE.Color(c));
  const P = [];
  for (let i = 0; i < N; i++) { P.push(spec(r, i)); bodies.setColorAt(i, coat[Math.floor(r() * coat.length)]); heads.setColorAt(i, hair[Math.floor(r() * hair.length)]); }
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), up = new THREE.Vector3(0, 1, 0);
  const update = (t) => {
    P.forEach((p, i) => {
      const s = p.at(t);
      Q.setFromAxisAngle(up, s.ang);
      M.compose(s.pos, Q, new THREE.Vector3(1, s.sy ?? 1, 1));
      bodies.setMatrixAt(i, M); heads.setMatrixAt(i, M);
    });
    bodies.instanceMatrix.needsUpdate = heads.instanceMatrix.needsUpdate = true;
  };
  return { bodies, heads, update };
}

function cars(N, seed, lanes) {
  const r = rng(seed);
  const cols = [0xf0f0f0, 0x202020, 0x8a8f96, 0x2a3c5a, 0xd0d0cc, 0x5a1a1a, 0x1f5a3a, 0xe0c040];
  const g = new THREE.Group(); const list = [];
  for (let i = 0; i < N; i++) {
    const lane = lanes[i % lanes.length];
    const taxi = r() < 0.2;
    const body = new THREE.Mesh(new THREE.BoxGeometry(1.75, 0.8, 4.4), new THREE.MeshStandardMaterial({ color: taxi ? 0x1c2a4a : cols[Math.floor(r() * cols.length)], roughness: 0.25, metalness: 0.6 }));
    body.position.y = 0.6;
    const top = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.6, 2.3), new THREE.MeshStandardMaterial({ color: 0x1a1e22, roughness: 0.1, metalness: 0.7 }));
    top.position.set(0, 1.25, 0.2);
    const car = new THREE.Group(); car.add(body, top);
    car.traverse((o) => { if (o.isMesh) o.castShadow = true; });
    g.add(car); list.push({ car, lane, ph: r(), sp: 8 + r() * 5 });
  }
  const update = (t) => list.forEach(({ car, lane, ph, sp }) => {
    const L = lane.len; const s = ((ph * L + t * sp) % L);
    const p = lane.a.clone().add(lane.dir.clone().multiplyScalar(s));
    car.position.copy(p); car.rotation.y = Math.atan2(lane.dir.x, lane.dir.z);
  });
  return { group: g, update };
}
const lane = (a, dir, len) => ({ a: new THREE.Vector3(...a), dir: new THREE.Vector3(...dir).normalize(), len });

// 止まっているカラス（翼をたたんだ姿）
function perchedCrowOld(mat) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.SphereGeometry(1, 16, 12), mat); body.scale.set(0.085, 0.1, 0.2); body.rotation.x = -0.55; body.position.y = 0.13; g.add(body);
  const hd = new THREE.Group(); hd.position.set(0, 0.25, -0.1); g.add(hd);
  const h = new THREE.Mesh(new THREE.SphereGeometry(0.07, 14, 10), mat); h.scale.set(1, 1, 1.15); hd.add(h);
  const bk = new THREE.Mesh(new THREE.ConeGeometry(0.024, 0.09, 10), mat); bk.rotation.x = -Math.PI / 2 - 0.1; bk.position.set(0, -0.005, -0.1); hd.add(bk);
  const tail = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.015, 0.2), mat); tail.position.set(0, 0.0, 0.2); tail.rotation.x = 0.6; g.add(tail);
  const legs = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.06), mat); legs.position.y = 0.03; g.add(legs);
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  g.userData.head = hd;
  return g;
}

// ================================================================ D1 貯食（AM 8:20）
export function shotD1() {
  const scene = new THREE.Scene();
  const sunDir = new THREE.Vector3(0.9, 0.32, -0.3);
  daylight(scene, { sunDir, sunColor: '#ffe2bc', sunI: 2.4, hemiI: 1.3, box: 8, center: new THREE.Vector3(0, 0, -1.5), fog: ['#cbd6e2', 0.006] });
  const tt = tileTex(); tt.repeat.set(6, 6);
  scene.add(plane(30, 30, new THREE.MeshStandardMaterial({ map: tt, roughness: 0.9 }), 0));
  const asph = asphaltTex(3); asph.repeat.set(20, 3);
  const road = plane(200, 12, new THREE.MeshStandardMaterial({ map: asph, roughness: 0.9, color: 0x9a9a9a }), 0.005); road.position.z = -10; scene.add(road);
  // 植え込み（縁石＋土）
  const curbM = new THREE.MeshStandardMaterial({ color: 0xb0aca4, roughness: 0.75 });
  for (const [x, z, w, d] of [[0, 0.05, 3.2, 0.12], [0, -3.6, 3.2, 0.12], [-1.6, -1.8, 0.12, 3.8], [1.6, -1.8, 0.12, 3.8]]) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, 0.16, d), curbM); m.position.set(x, 0.08, z); m.castShadow = m.receiveShadow = true; scene.add(m);
  }
  const st = soilTex(4); st.repeat.set(3, 3);
  const soil = plane(3.1, 3.6, new THREE.MeshStandardMaterial({ map: st, roughness: 1 }), 0.12); soil.position.z = -1.8; scene.add(soil);
  // ツツジの植え込みとイチョウの幹
  scene.add(buildCanopy({ seed: 31, count: 26, x0: -1.4, x1: 1.4, z0: -3.4, z1: -2.3, yBase: -0.05, size: [0.35, 0.5], colors: ['#24461f', '#2c5226', '#1f3d1c'], shadows: true }));
  scene.add(buildCanopy({ seed: 32, count: 10, x0: -1.4, x1: -0.9, z0: -2.3, z1: -0.6, yBase: -0.05, size: [0.3, 0.45], colors: ['#24461f', '#2c5226'], shadows: true }));
  const bark = barkTex(8);
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.2, 7, 16), new THREE.MeshStandardMaterial({ map: bark, bumpMap: bark, bumpScale: 2, roughness: 0.95 }));
  trunk.position.set(0.85, 3.5, -1.6); trunk.castShadow = true; scene.add(trunk);
  scene.add(buildCanopy({ seed: 33, count: 14, x0: -0.5, x1: 2.2, z0: -3, z1: -0.3, yBase: 5.5, size: [1.0, 1.6], colors: ['#d4b23a', '#c9a530', '#b8962c'], shadows: true }));
  const leaves = ginkgoLeaves(34, 220, [-1.5, 1.5, -3.4, -0.1], 0.122); scene.add(leaves.mesh);
  scene.add(ginkgoLeaves(35, 300, [-6, 6, -0.2, 6], 0.003).mesh);
  // 道の向こうの建物と車
  scene.add(buildCity({ seed: 36, x0: -120, x1: 120, z0: -90, z1: -22, spacing: 18, hMin: 12, hMax: 45, lit: 0.04, emissive: 0.5, shadows: false, skip: 0.05 }));
  const C = cars(8, 37, [lane([-60, 0, -8], [1, 0, 0], 120), lane([60, 0, -12], [-1, 0, 0], 120)]); scene.add(C.group);
  // パン（くちばしにくわえている）と隠す葉
  const bread = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.028, 0.04), new THREE.MeshStandardMaterial({ color: 0xd8b07a, roughness: 0.9 }));
  bread.castShadow = true; scene.add(bread);
  const cover = new THREE.Mesh(new THREE.PlaneGeometry(0.07, 0.07).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ map: leaves.tex, alphaTest: 0.5, side: THREE.DoubleSide, roughness: 0.8 }));
  scene.add(cover);
  const c = cam(74); scene.add(c);
  const beak = beakMesh(); beak.position.set(0, -0.05, -0.05); c.add(beak);
  const spot = new THREE.Vector3(0.04, 0.12, -0.88);
  const leafStart = new THREE.Vector3(0.22, 0.123, -0.78);
  const keys = [
    { t: 0, yaw: 0.0, pitch: -0.15, roll: 0 }, { t: 1.4, yaw: 0.45, pitch: -0.05, roll: 0.05 }, { t: 1.95, yaw: -0.4, pitch: -0.05, roll: -0.05 },
    { t: 2.45, yaw: 0.0, pitch: -0.62, roll: 0 }, { t: 3.6, yaw: 0.1, pitch: -0.58, roll: 0.0 }, { t: 4.6, yaw: 0.02, pitch: -0.62, roll: 0 },
    { t: 5.2, yaw: 0.35, pitch: -0.05, roll: 0.06 },
  ];
  const tip = new THREE.Vector3(0, -0.058, -0.13);
  return {
    scene, camera: c,
    bloom: { strength: 0.3, radius: 0.4, threshold: 0.95 },
    grade: { sat: 1.02, contrast: 1.06, gain: [1.03, 1.0, 0.97], lift: [0.01, 0.01, 0.012], vignette: 0.35, grain: 0.035 },
    exposure: 0.95,
    update(t) {
      const hop = (h) => clamp((t - h) / 0.22);
      const k = (easeInOut(hop(0.3)) + easeInOut(hop(0.8))) / 2;
      const base = new THREE.Vector3(0, 0.32, 0.25).lerp(new THREE.Vector3(0.05, 0.32, -0.55), k);
      base.y += Math.sin(Math.PI * hop(0.3)) * 0.05 + Math.sin(Math.PI * hop(0.8)) * 0.05;
      const down = smooth(2.4, 2.8, t) * (1 - smooth(4.8, 5.2, t));
      const push = Math.max(0, Math.sin((t - 2.9) * Math.PI * 4)) * smooth(2.9, 3.0, t) * (1 - smooth(3.5, 3.6, t));
      base.y -= down * 0.1 + push * 0.04;
      c.position.copy(base);
      head(c, snapHead(keys, t)); jitter(c, t);
      // パン：くわえている → 土に押し込む
      c.updateMatrixWorld();
      if (t < 2.9) bread.position.copy(tip).applyMatrix4(c.matrixWorld), bread.rotation.copy(c.rotation);
      else { bread.position.copy(spot); bread.position.y = 0.13 - smooth(2.9, 3.6, t) * 0.018; bread.rotation.set(0, 0.4, 0); }
      // 葉をくわえて上にかぶせる
      if (t < 3.8) { cover.position.copy(leafStart); cover.rotation.set(0, 0.8, 0); }
      else if (t < 4.4) { const p = new THREE.Vector3().copy(tip).applyMatrix4(c.matrixWorld); cover.position.copy(leafStart.clone().lerp(p, smooth(3.8, 3.95, t))); cover.rotation.set(0.3, 0.8 + (t - 3.8), 0); }
      else { cover.position.copy(spot).add(new THREE.Vector3(0, 0.012 - smooth(4.4, 4.6, t) * 0.005, 0)); cover.rotation.set(0.05, 1.3, 0.02); }
      C.update(t);
    },
  };
}

// ================================================================ D2 水浴び（AM 10:30）
function waterNormal() {
  const S = 256;
  return canvasTex(S, S, (g) => {
    const img = g.createImageData(S, S);
    const H = new Float32Array(S * S);
    const waves = [[3, 1, 0.5], [1, 4, 0.4], [5, -3, 0.2], [-7, 2, 0.15], [9, 6, 0.08], [-4, -11, 0.06]];
    for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
      let h = 0; for (const [a, b, amp] of waves) h += Math.sin(2 * Math.PI * (a * x + b * y) / S) * amp; H[y * S + x] = h;
    }
    for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
      const dx = H[y * S + (x + 1) % S] - H[y * S + (x + S - 1) % S], dy = H[((y + 1) % S) * S + x] - H[((y + S - 1) % S) * S + x];
      const n = new THREE.Vector3(-dx * 3, -dy * 3, 1).normalize();
      const i = (y * S + x) * 4; img.data[i] = (n.x * 0.5 + 0.5) * 255; img.data[i + 1] = (n.y * 0.5 + 0.5) * 255; img.data[i + 2] = (n.z * 0.5 + 0.5) * 255; img.data[i + 3] = 255;
    }
    g.putImageData(img, 0, 0);
  }, { srgb: false });
}

export function shotD2(renderer) {
  const scene = new THREE.Scene();
  const sunDir = new THREE.Vector3(0.4, 0.55, -0.7);
  daylight(scene, { sunDir, sunI: 2.7, hemiI: 1.4, box: 15, center: new THREE.Vector3(0, 0, -6), fog: ['#cdd8e2', 0.006] });
  // 反射用の環境マップ（空だけ）
  const envScene = new THREE.Scene(); envScene.add(skyDome({ zenith: '#3f74c2', horizon: '#dde6ee', glow: '#fff3dc', glowSize: 40, exp: 0.5, sunDir }));
  const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(envScene, 0, 0.1, 10000).texture;
  const nrm = waterNormal(); nrm.repeat.set(10, 10);
  const nrm2 = nrm.clone(); nrm2.repeat.set(23, 23); nrm2.needsUpdate = true;
  const waterM = new THREE.MeshStandardMaterial({ color: 0x14302e, roughness: 0.04, metalness: 0.0, normalMap: nrm, normalScale: new THREE.Vector2(0.35, 0.35), envMapIntensity: 1.3, transparent: true, opacity: 0.94 });
  const water = plane(80, 60, waterM, 0); water.position.z = -20; scene.add(water);
  // 浅い底（手前だけ透けて見える）
  const sb = soilTex(9); sb.repeat.set(4, 4);
  const bed = plane(10, 6, new THREE.MeshStandardMaterial({ map: sb, roughness: 1, color: 0x9a8a70 }), -0.06); bed.position.z = 1; scene.add(bed);
  // 岸・石・芝
  const gt = grassTex(10, [110, 128, 72]); gt.repeat.set(20, 20);
  const bank = new THREE.Mesh(new THREE.RingGeometry(26, 120, 64, 1), new THREE.MeshStandardMaterial({ map: gt, roughness: 0.95 }));
  bank.rotation.x = -Math.PI / 2; bank.position.set(0, 0.25, -20); bank.receiveShadow = true; scene.add(bank);
  const r = rng(12);
  const stoneM = new THREE.MeshStandardMaterial({ color: 0x8a867c, roughness: 0.85 });
  for (let i = 0; i < 26; i++) {
    const g = new THREE.IcosahedronGeometry(0.25 + r() * 0.5, 2); const p = g.attributes.position;
    for (let k = 0; k < p.count; k++) { const v = new THREE.Vector3().fromBufferAttribute(p, k); v.multiplyScalar(1 + noise3(v.x * 3 + i, v.y * 3, v.z * 3) * 0.25); p.setXYZ(k, v.x, v.y * 0.6, v.z); }
    g.computeVertexNormals();
    const s = new THREE.Mesh(g, stoneM); const a = r() * Math.PI * 2;
    const R = i < 6 ? 1.2 + r() * 2 : 25 + r() * 2;
    s.position.set(i < 6 ? (r() - 0.5) * 3 + (r() < 0.5 ? -1.6 : 1.6) : Math.cos(a) * R, 0, i < 6 ? 0.6 + r() * 1.5 : -20 + Math.sin(a) * R);
    s.castShadow = s.receiveShadow = true; scene.add(s);
  }
  // ヨシ
  const reedM = new THREE.MeshStandardMaterial({ color: 0xb8a464, roughness: 0.8 });
  for (let i = 0; i < 160; i++) { const h = 0.8 + r() * 1.2; const m = new THREE.Mesh(new THREE.ConeGeometry(0.008, h, 4), reedM); const a = -0.6 - r() * 1.4; m.position.set(Math.cos(a) * 24 + (r() - 0.5) * 3, h / 2, -20 + Math.sin(a) * 24 + (r() - 0.5) * 2); m.rotation.z = (r() - 0.5) * 0.3; scene.add(m); }
  // 公園の木（紅葉まじり）と、木の上に見える高層ビル
  scene.add(buildCanopy({ seed: 13, count: 900, x0: -120, x1: 120, z0: -110, z1: -42, yBase: 0, size: [4, 7], yJitter: 3, colors: ['#3a5a2a', '#4a6a30', '#2e4a26', '#a8742c', '#c49a34', '#8a3a24'] }));
  scene.add(buildCity({ seed: 14, x0: -500, x1: 500, z0: -700, z1: -180, spacing: 40, hMin: 20, hMax: 60, towers: [{ x: 120, z: -400, r: 150, h: 180 }], lit: 0.03, emissive: 0.4, skip: 0.3 }));
  // しぶき・波紋
  const dips = [1.7, 2.35, 3.0, 3.6, 4.15];
  const ND = 360;
  const drops = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 8, 6), new THREE.MeshStandardMaterial({ color: 0xcfe4ea, roughness: 0.02, transparent: true, opacity: 0.45, envMapIntensity: 2.5 }), ND);
  drops.frustumCulled = false; scene.add(drops);
  const dr = rng(15);
  const D = Array.from({ length: ND }, (_, i) => ({ t0: dips[i % dips.length] + dr() * 0.08, v: new THREE.Vector3((dr() - 0.5) * 1.6, 0.8 + dr() * 2.2, -0.3 - dr() * 1.6), s: 0.0015 + dr() * 0.0045, x: (dr() - 0.5) * 0.25, z: -0.15 - dr() * 0.2 }));
  const rings = [];
  for (let i = 0; i < dips.length * 2; i++) {
    const m = new THREE.Mesh(new THREE.RingGeometry(0.96, 1, 64).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, depthWrite: false }));
    m.position.set(0, 0.004, -0.2); scene.add(m); rings.push([m, dips[i >> 1] + (i & 1) * 0.25]);
  }
  const c = cam(76); scene.add(c);
  const wings = wingPair(); c.add(wings);
  const keys = [{ t: 0, yaw: 0.2, pitch: -0.08, roll: 0 }, { t: 0.7, yaw: -0.25, pitch: -0.05, roll: 0.05 }, { t: 1.3, yaw: 0.0, pitch: -0.12, roll: 0 }];
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion();
  return {
    scene, camera: c,
    bloom: { strength: 0.45, radius: 0.4, threshold: 0.9 },
    grade: { sat: 1.05, contrast: 1.06, gain: [1.0, 1.0, 1.0], lift: [0.005, 0.01, 0.012], vignette: 0.35, grain: 0.035 },
    exposure: 0.9,
    update(t) {
      nrm.offset.set(t * 0.02, t * 0.013);
      let dip = 0;
      for (const d of dips) { const k = (t - d) / 0.4; if (k > 0 && k < 1) dip = Math.max(dip, Math.sin(Math.PI * k)); }
      const shake = smooth(4.7, 4.8, t) * (1 - smooth(5.5, 5.7, t));
      c.position.set(0, 0.16 - dip * 0.1, 0.6);
      const h = snapHead(keys, t);
      head(c, h);
      c.rotation.x += -dip * 0.35; c.rotation.z += dip * 0.25 * Math.sin(t * 40) + shake * 0.22 * Math.sin(t * 55);
      c.rotation.y += shake * 0.05 * Math.sin(t * 47);
      jitter(c, t);
      // 水をかぶるように翼をばたつかせる
      const bat = dip > 0.05 ? 0.5 + 0.5 * Math.sin(t * Math.PI * 2 * 9) : 0;
      wings.visible = dip > 0.05 || shake > 0.05;
      wings.userData.set(bat * 1.0 - 0.3 + shake * 0.4 * Math.sin(t * 60), 0.25);
      D.forEach((d, i) => {
        const dt = t - d.t0;
        let s = 0; const p = new THREE.Vector3();
        if (dt > 0 && dt < 1.2) { p.set(d.x + d.v.x * dt, d.v.y * dt - 4.9 * dt * dt, 0.6 + d.z + d.v.z * dt); if (p.y > 0) s = d.s; }
        M.compose(p, Q, new THREE.Vector3(s, s * 1.4, s)); drops.setMatrixAt(i, M);
      });
      drops.instanceMatrix.needsUpdate = true;
      for (const [m, t0] of rings) { const dt = t - t0; if (dt > 0 && dt < 2.2) { m.scale.setScalar(0.1 + dt * 0.9); m.material.opacity = 0.35 * (1 - dt / 2.2); } else m.material.opacity = 0; }
    },
  };
}

// ================================================================ D3 昼の休息（PM 0:40）
export function shotD3() {
  const scene = new THREE.Scene();
  const sunDir = new THREE.Vector3(-0.15, 0.62, -0.75);
  const camPos = new THREE.Vector3(0, 11, 0);
  daylight(scene, { sunDir, sunI: 2.8, hemiI: 1.5, box: 40, center: new THREE.Vector3(0, 0, -20), fog: ['#cfdae4', 0.004] });
  const gt = grassTex(20, [128, 140, 78]); gt.repeat.set(40, 40);
  scene.add(plane(400, 400, new THREE.MeshStandardMaterial({ map: gt, roughness: 0.95 }), 0));
  // 周りの木
  scene.add(buildCanopy({ seed: 21, count: 500, x0: -150, x1: 150, z0: -160, z1: -70, yBase: 0, size: [4, 7], yJitter: 3, colors: ['#3a5a2a', '#4a6a30', '#2e4a26', '#a8742c', '#c49a34'], shadows: true }));
  scene.add(buildCanopy({ seed: 22, count: 120, x0: -60, x1: 60, z0: -8, z1: 30, yBase: 0, size: [4, 6.5], yJitter: 2, exclude: (x, z) => Math.hypot(x, z) < 15 || z < 0, colors: ['#2e4a26', '#3a5a2a'], shadows: true }));
  scene.add(buildCity({ seed: 23, x0: -700, x1: 700, z0: -900, z1: -230, spacing: 40, hMin: 20, hMax: 60, towers: [{ x: 200, z: -500, r: 200, h: 190 }], lit: 0.03, emissive: 0.4, skip: 0.3 }));
  const leaves = buildLeafCloud({ seed: 24, count: 2400, center: camPos, rMin: 0.4, rMax: 4.5, forward: new THREE.Vector3(0, -0.45, -1), gapDeg: 14, leafSize: 0.09 });
  scene.add(leaves);
  const bark = barkTex(25);
  const branch = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([new THREE.Vector3(-1.2, 10.75, 1.0), new THREE.Vector3(0, 10.86, 0.1), new THREE.Vector3(0.4, 10.84, -0.8)]), 32, 0.045, 10), new THREE.MeshStandardMaterial({ map: bark, bumpMap: bark, bumpScale: 2, roughness: 0.95 }));
  scene.add(branch);
  // 芝生でくつろぐ人（座っている人・シート・歩く人）
  const sheetCols = [0x3a6aa8, 0xc84a3a, 0xe8d24a, 0x4aa86a, 0xe8e8e0];
  const sr = rng(26);
  const sheets = [];
  for (let i = 0; i < 14; i++) {
    const s = new THREE.Mesh(new THREE.PlaneGeometry(1.8, 1.8).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ color: sheetCols[i % 5], roughness: 0.8 }));
    s.position.set((sr() - 0.5) * 50, 0.01, -14 - sr() * 40); s.rotation.y = sr() * 3; s.receiveShadow = true; scene.add(s); sheets.push(s.position.clone());
  }
  const P = people(60, 27, (r, i) => {
    if (i < 40) {
      const sp = sheets[i % sheets.length]; const o = new THREE.Vector3((r() - 0.5) * 1.2, 0, (r() - 0.5) * 1.2); const a = r() * 6.28;
      return { at: () => ({ pos: sp.clone().add(o), ang: a, sy: 0.6 }) };
    }
    const a0 = new THREE.Vector3((r() - 0.5) * 80, 0, -12 - r() * 45); const dir = new THREE.Vector3(r() - 0.5, 0, r() - 0.5).normalize(); const sp = 0.9 + r() * 0.5;
    return { at: (t) => ({ pos: a0.clone().addScaledVector(dir, t * sp), ang: Math.atan2(dir.x, dir.z) }) };
  });
  scene.add(P.bodies, P.heads);
  // 羽づくろいの時に映る自分の羽
  const fm = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.45), new THREE.MeshStandardMaterial({ map: featherTex(), alphaTest: 0.4, side: THREE.DoubleSide, roughness: 0.45, metalness: 0.15 }));
  const c = cam(70); scene.add(c); c.add(fm);
  const beak = beakMesh(); beak.position.set(0, -0.05, -0.05); c.add(beak);
  const keys = [
    { t: 0, yaw: 0.05, pitch: -0.42, roll: 0 }, { t: 1.2, yaw: -0.15, pitch: -0.38, roll: 0.12 },
    { t: 2.5, yaw: 0.9, pitch: -0.75, roll: 0.35 }, { t: 4.2, yaw: 0.1, pitch: -0.45, roll: -0.05 }, { t: 5.3, yaw: -0.08, pitch: -0.4, roll: 0.0 },
  ];
  return {
    scene, camera: c,
    bloom: { strength: 0.35, radius: 0.45, threshold: 0.92 },
    grade: { sat: 1.04, contrast: 1.05, gain: [1.02, 1.0, 0.97], lift: [0.01, 0.012, 0.012], vignette: 0.38, grain: 0.035 },
    exposure: 0.92,
    update(t) {
      c.position.set(camPos.x + noise1(t * 0.5, 1) * 0.01, camPos.y + noise1(t * 0.6, 2) * 0.006, camPos.z);
      const h = snapHead(keys, t, 0.2); head(c, h);
      const preen = smooth(2.5, 2.7, t) * (1 - smooth(4.1, 4.3, t));
      c.rotation.x += preen * Math.max(0, Math.sin(t * 22)) * 0.05;
      jitter(c, t, 0.003);
      fm.visible = false;
      fm.position.set(0.12, -0.14 + (1 - preen) * -0.15, -0.2); fm.rotation.set(-0.7, 0.5, 0.5 + Math.sin(t * 22) * 0.03 * preen);
      leaves.rotation.y = noise1(t * 0.6, 5) * 0.006;
      P.update(t);
    },
  };
}

// ================================================================ D4 屋上から街を見る（PM 2:30）
export function shotD4() {
  const scene = new THREE.Scene();
  const sunDir = new THREE.Vector3(-0.6, 0.4, 0.55);
  const ROOF = 34;
  daylight(scene, { sunDir, sunColor: '#fff0d8', sunI: 2.6, hemiI: 1.6, box: 60, center: new THREE.Vector3(0, 0, -25), fog: ['#cad6e2', 0.0035] });
  const asph = asphaltTex(41); asph.repeat.set(40, 40);
  scene.add(plane(600, 600, new THREE.MeshStandardMaterial({ map: asph, roughness: 0.9, color: 0x9a9a9a }), 0));
  const walkM = new THREE.MeshStandardMaterial({ color: 0xaaa59b, roughness: 0.85 });
  for (const z of [-17.5, -32.5]) { const s = new THREE.Mesh(new THREE.BoxGeometry(400, 0.15, 4), walkM); s.position.set(0, 0.075, z); s.receiveShadow = true; scene.add(s); }
  const lineM = new THREE.MeshStandardMaterial({ color: 0xe8e8e2, roughness: 0.7 });
  for (let x = -200; x < 200; x += 6) { const l = plane(3, 0.15, lineM, 0.01); l.position.set(x, 0.01, -25); scene.add(l); }
  // 自分のいるビル
  const own = new THREE.Mesh(new THREE.BoxGeometry(20, ROOF, 14), new THREE.MeshStandardMaterial({ color: 0xbab4aa, roughness: 0.8 })); own.position.set(0, ROOF / 2, 7.2); own.castShadow = own.receiveShadow = true; scene.add(own);
  const para = new THREE.Mesh(new THREE.BoxGeometry(20, 0.9, 0.25), new THREE.MeshStandardMaterial({ color: 0xc8c2b8, roughness: 0.75 })); para.position.set(0, ROOF + 0.45, 0.25); para.castShadow = true; scene.add(para);
  const mastM = new THREE.MeshStandardMaterial({ color: 0x8a8a8a, roughness: 0.4, metalness: 0.7 });
  const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 4), mastM); mast.position.set(-2.2, ROOF + 2, 1.2); scene.add(mast);
  for (let k = 0; k < 4; k++) { const e = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 1.2 - k * 0.2), mastM); e.rotation.z = Math.PI / 2; e.position.set(-2.2, ROOF + 2.6 + k * 0.35, 1.2); scene.add(e); }
  scene.add(buildCity({ seed: 42, x0: -400, x1: 400, z0: -400, z1: 300, spacing: 26, hMin: 15, hMax: 60, towers: [{ x: 90, z: -320, r: 120, h: 200 }, { x: -160, z: -380, r: 100, h: 160 }],
    lit: 0.03, emissive: 0.4, shadows: true, skip: 0.06, avoid: (x, z) => (z > -36 && z < -14) || (x > -14 && x < 14 && z > -4 && z < 20) || (Math.abs(x - 40) < 7) }));
  const C = cars(18, 43, [lane([-200, 0, -21.5], [1, 0, 0], 400), lane([200, 0, -28.5], [-1, 0, 0], 400), lane([-200, 0, -24.5], [1, 0, 0], 400), lane([40, 0, 150], [0, 0, -1], 400)]);
  scene.add(C.group);
  const P = people(90, 44, (r, i) => {
    const z = (i % 2 ? -17.5 : -32.5) + (r() - 0.5) * 2.5; const dir = r() < 0.5 ? 1 : -1; const x0 = (r() - 0.5) * 160; const sp = 1.1 + r() * 0.4;
    return { at: (t) => ({ pos: new THREE.Vector3(x0 + dir * sp * t, 0.15, z), ang: dir > 0 ? Math.PI / 2 : -Math.PI / 2 }) };
  });
  scene.add(P.bodies, P.heads);
  // 隣に降りてくる仲間
  const crowMat = new THREE.MeshStandardMaterial({ color: 0x08080a, roughness: 0.45, metalness: 0.1, side: THREE.DoubleSide });
  const flyer = crowModel(crowMat); scene.add(flyer);
  const sitter = perchedCrow(crowMat); scene.add(sitter);
  const landAt = new THREE.Vector3(1.1, ROOF + 0.9, 0.2);
  const c = cam(70); scene.add(c);
  const beak = beakMesh(); beak.position.set(0, -0.05, -0.05); c.add(beak);
  const keys = [
    { t: 0, yaw: 0.1, pitch: -0.92, roll: 0 }, { t: 1.0, yaw: 0.35, pitch: -1.0, roll: 0.15 }, { t: 1.9, yaw: -0.2, pitch: -0.9, roll: -0.1 },
    { t: 2.7, yaw: -0.55, pitch: -0.15, roll: 0 }, { t: 3.6, yaw: -0.6, pitch: -0.2, roll: 0.08 }, { t: 4.6, yaw: 0.05, pitch: -0.95, roll: 0 },
  ];
  const flyPath = new THREE.CatmullRomCurve3([new THREE.Vector3(14, ROOF + 6, -10), new THREE.Vector3(7, ROOF + 3.5, -5), new THREE.Vector3(3, ROOF + 1.8, -1.5), landAt.clone().add(new THREE.Vector3(0, 0.1, 0)), landAt]);
  return {
    scene, camera: c,
    bloom: { strength: 0.3, radius: 0.4, threshold: 0.95 },
    grade: { sat: 1.0, contrast: 1.07, gain: [1.02, 1.0, 0.98], lift: [0.01, 0.01, 0.014], vignette: 0.36, grain: 0.035 },
    exposure: 0.95,
    update(t) {
      c.position.set(0, ROOF + 1.12, 0.25);
      head(c, snapHead(keys, t)); jitter(c, t);
      C.update(t + 10); P.update(t);
      const u = clamp((t - 2.3) / 1.4);
      flyer.visible = u < 1; sitter.visible = u >= 1;
      if (u < 1) {
        const p = flyPath.getPointAt(easeOut(u)); const q = flyPath.getTangentAt(Math.min(0.999, easeOut(u)));
        flyer.position.copy(p); flyer.rotation.set(-Math.asin(q.y) + (u > 0.7 ? -0.8 * (u - 0.7) / 0.3 : 0), Math.atan2(-q.x, -q.z), 0);
        flyer.userData.flap(Math.sin(t * Math.PI * 2 * (u > 0.7 ? 7 : 4)) * 0.8);
      } else {
        sitter.position.copy(landAt).add(new THREE.Vector3(0, -0.02, 0)); sitter.rotation.y = 0.9;
        sitter.userData.head.rotation.y = snapHead([{ t: 0, yaw: 0 }, { t: 4.2, yaw: 0.6 }, { t: 5.0, yaw: -0.3 }], t).yaw;
      }
    },
  };
}

// ================================================================ D5 ねぐら入り前の集合（PM 3:50）
export function shotD5() {
  const scene = new THREE.Scene();
  const sunDir = new THREE.Vector3(-0.85, 0.14, -0.35);
  daylight(scene, { sunDir, sunColor: '#ffb070', sunI: 2.2, hemiSky: '#a4b4d0', hemiGround: '#5a4a40', hemiI: 1.2, box: 40, center: new THREE.Vector3(0, 0, -20),
    sky: { zenith: '#4a6aa6', horizon: '#f0c8a0', glow: '#ffc890', glowSize: 12 }, fog: ['#d6c8bc', 0.004] });
  const asph = asphaltTex(51); asph.repeat.set(10, 60);
  scene.add(plane(400, 400, new THREE.MeshStandardMaterial({ map: asph, roughness: 0.9, color: 0x9a9a9a }), 0));
  scene.add(buildCity({ seed: 52, x0: -300, x1: 300, z0: -400, z1: 100, spacing: 22, hMin: 10, hMax: 40, lit: 0.06, emissive: 0.6, shadows: true, skip: 0.08, avoid: (x) => Math.abs(x) < 16 }));
  scene.add(buildCanopy({ seed: 53, count: 18, x0: 7, x1: 9.5, z0: -80, z1: 5, yBase: 3, size: [2.5, 3.5], colors: ['#2e4a26', '#3a5a2a', '#9a7a2a'], shadows: true }));
  const C = cars(14, 54, [lane([-3, 0, 100], [0, 0, -1], 300), lane([3, 0, -200], [0, 0, 1], 300)]); scene.add(C.group);
  const poleM = new THREE.MeshStandardMaterial({ color: 0x9a9a94, roughness: 0.8 });
  const wireM = new THREE.MeshStandardMaterial({ color: 0x151515, roughness: 0.6 });
  const poles = [10, -20, -50, -80, -110];
  for (const pz of poles) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.22, 12, 12), poleM); p.position.set(-7, 6, pz); p.castShadow = true; scene.add(p); const a = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.1, 0.1), poleM); a.position.set(-6.3, 9.3, pz); scene.add(a); }
  const lines = [[-7.3, 9.25, 0.45], [-6.3, 9.25, 0.45], [-5.4, 9.25, 0.45], [-7, 7.6, 0.35]];
  for (let i = 0; i < poles.length - 1; i++) for (const [x, y, sg] of lines) scene.add(wire(new THREE.Vector3(x, y, poles[i]), new THREE.Vector3(x, y, poles[i + 1]), sg, 0.012, wireM));
  const wireY = (y, sg, z) => { const i = Math.max(0, poles.findIndex((p) => p < z) - 1); const a = poles[i], b = poles[i + 1]; const u = (a - z) / (a - b); return y - sg * 4 * u * (1 - u); };
  // 電線に並ぶカラス
  const crowMat = new THREE.MeshStandardMaterial({ color: 0x08080a, roughness: 0.45, metalness: 0.1, side: THREE.DoubleSide });
  const r = rng(55);
  const sitters = [];
  for (let i = 0; i < 48; i++) {
    const [x, y, sg] = lines[i % 3]; const z = 8 - i * 1.6 - r() * 1.2;
    const b = perchedCrow(crowMat); b.position.set(x, wireY(y, sg, z) + 0.02, z); b.rotation.y = r() < 0.5 ? 0.3 : Math.PI - 0.3 + (r() - 0.5);
    b.userData.ph = r() * 10; scene.add(b); sitters.push(b);
  }
  // 次々に飛んでくる仲間
  const flyers = [];
  for (let i = 0; i < 9; i++) {
    const f = crowModel(crowMat); scene.add(f);
    const [x, y, sg] = lines[i % 3]; const z = -3 - i * 4.5;
    const end = new THREE.Vector3(x + 0.2, wireY(y, sg, z) + 0.12, z);
    const start = end.clone().add(new THREE.Vector3(18 + r() * 10, 9 + r() * 6, -10 - r() * 20));
    const sit = perchedCrow(crowMat); sit.position.copy(end).add(new THREE.Vector3(-0.2, -0.1, 0)); sit.rotation.y = 0.3; sit.visible = false; scene.add(sit);
    flyers.push({ f, sit, path: new THREE.CatmullRomCurve3([start, start.clone().lerp(end, 0.6).add(new THREE.Vector3(0, 2, 0)), end]), t0: 0.2 + i * 0.6 + r() * 0.3 });
  }
  const c = cam(70); scene.add(c);
  const beak = beakMesh(); beak.position.set(0, -0.05, -0.05); c.add(beak);
  const keys = [{ t: 0, yaw: 0.05, pitch: -0.08, roll: 0 }, { t: 1.2, yaw: -0.55, pitch: 0.12, roll: 0.05 }, { t: 2.4, yaw: -0.2, pitch: -0.05, roll: -0.05 }, { t: 3.6, yaw: -0.7, pitch: 0.18, roll: 0 }, { t: 4.7, yaw: 0.0, pitch: -0.1, roll: 0.05 }];
  const camZ = 10.2;
  return {
    scene, camera: c,
    bloom: { strength: 0.55, radius: 0.5, threshold: 0.85 },
    grade: { sat: 1.06, contrast: 1.07, gain: [1.06, 1.0, 0.92], lift: [0.015, 0.008, 0.012], vignette: 0.42, grain: 0.04 },
    exposure: 0.9,
    update(t) {
      c.position.set(-6.3, wireY(9.25, 0.45, camZ) + 0.2 + Math.sin(t * 2.3) * 0.01, camZ);
      head(c, snapHead(keys, t)); jitter(c, t);
      C.update(t);
      for (const b of sitters) b.userData.head.rotation.y = Math.sin(Math.floor(t * 1.3 + b.userData.ph) * 2.1) * 0.7;
      for (const { f, sit, path, t0 } of flyers) {
        const u = clamp((t - t0) / 1.6);
        f.visible = t > t0 && u < 1; sit.visible = u >= 1;
        const p = path.getPointAt(easeOut(u)); const q = path.getTangentAt(Math.min(0.999, easeOut(u)));
        f.position.copy(p); f.rotation.set(-Math.asin(q.y) - (u > 0.8 ? 0.7 : 0), Math.atan2(-q.x, -q.z), 0);
        f.userData.flap(u < 1 ? Math.sin(t * Math.PI * 2 * (u > 0.75 ? 7 : 4.5) + t0) * 0.85 : 1.35);
      }
    },
  };
}
