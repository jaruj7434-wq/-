// 各カットの3Dシーン
import * as THREE from 'three';
import {
  rng, clamp, lerp, smooth, easeOut, easeInOut, noise1, snapHead,
  buildCity, buildCanopy, buildLeafCloud, skyDome, beakMesh, wingPair, crowModel,
  garbageBag, netTex, wire, asphaltTex, barkTex, facadeTextures, canvasTex,
} from './lib.js';

const ASPECT = 720 / 1280;
function cam(fov = 72) {
  const c = new THREE.PerspectiveCamera(fov, ASPECT, 0.01, 16000);
  c.rotation.order = 'YXZ';
  return c;
}
function applyHead(c, base, h) {
  c.rotation.set((base.pitch || 0) + h.pitch, (base.yaw || 0) + h.yaw, (base.roll || 0) + h.roll);
}

// ---------------------------------------------------------------- 明治神宮の森＋遠景の街
function forestWorld(opt) {
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(opt.fog, opt.fogDensity);
  const sky = skyDome(opt.sky);
  scene.add(sky);
  scene.add(new THREE.HemisphereLight(opt.hemiSky, opt.hemiGround, opt.hemiI));
  const dl = new THREE.DirectionalLight(opt.dirColor, opt.dirI);
  dl.position.copy(opt.sky.sunDir).multiplyScalar(500); scene.add(dl);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(30000, 30000), new THREE.MeshStandardMaterial({ color: 0x101214, roughness: 1 }));
  ground.rotation.x = -Math.PI / 2; scene.add(ground);
  // 森：z>-180 の範囲。カメラ付近は葉の雲で置き換えるので除外
  const exclude = (x, z) => Math.hypot(x - opt.camPos.x, z - opt.camPos.z) < 9;
  scene.add(buildCanopy({ seed: 11, count: 6000, x0: -700, x1: 700, z0: -180, z1: 900, yBase: 0, size: [5, 9], yJitter: 5, exclude }));
  // 森の縁の木を低めに（外がひらけて見える）
  scene.add(buildCanopy({ seed: 12, count: 600, x0: -500, x1: 500, z0: -260, z1: -180, yBase: -4, size: [4, 7], yJitter: 3 }));
  // 街：渋谷方向（-z）に高層ビル群
  const city = buildCity({
    seed: 21, x0: -3500, x1: 3500, z0: -5200, z1: -420, spacing: 46, hMin: 12, hMax: 55,
    towers: [{ x: 380, z: -1700, r: 380, h: 220 }, { x: -900, z: -2600, r: 300, h: 160 }, { x: 1600, z: -3200, r: 500, h: 190 }],
    lit: opt.lit, emissive: opt.emissive, skip: 0.18,
  });
  scene.add(city);
  return { scene, sky, city, dl };
}

const preDawnSky = (k) => ({
  zenith: new THREE.Color('#040a1c').lerp(new THREE.Color('#0d1d3e'), k),
  horizon: new THREE.Color('#2c3555').lerp(new THREE.Color('#6c6f93'), k),
  ground: '#141826',
  glow: new THREE.Color('#5a2f2a').lerp(new THREE.Color('#c27a5a'), k),
  sunDir: new THREE.Vector3(0.25, -0.06, -1),
  glowSize: 6, exp: 0.5,
});

export function shotC1() {
  const camPos = new THREE.Vector3(0, 21, 0);
  const W = forestWorld({
    fog: '#262f48', fogDensity: 0.00032, sky: preDawnSky(0.15), hemiSky: '#5a6ea6', hemiGround: '#141820', hemiI: 1.25,
    dirColor: '#8796c8', dirI: 0.45, lit: 0.32, emissive: 2.6, camPos,
  });
  const { scene } = W;
  const leaves = buildLeafCloud({ seed: 3, count: 2600, center: camPos, rMin: 0.35, rMax: 5.5, forward: new THREE.Vector3(0.12, -0.03, -1), gapDeg: 11, leafSize: 0.09 });
  scene.add(leaves);
  // 止まっている枝
  const bark = barkTex(4);
  const curve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-1.4, 20.7, 1.2), new THREE.Vector3(-0.3, 20.84, 0.25), new THREE.Vector3(0.15, 20.88, -0.35),
    new THREE.Vector3(0.6, 20.85, -1.0), new THREE.Vector3(1.0, 20.9, -1.7),
  ]);
  const branch = new THREE.Mesh(new THREE.TubeGeometry(curve, 64, 0.038, 12), new THREE.MeshStandardMaterial({ map: bark, bumpMap: bark, bumpScale: 2, roughness: 0.95, color: 0x8a8580 }));
  scene.add(branch);
  const twig = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.3, 20.87, -0.6), new THREE.Vector3(0.55, 21.05, -0.9), new THREE.Vector3(0.75, 21.3, -1.0)]), 24, 0.012, 8), branch.material);
  scene.add(twig);
  const c = cam(70); scene.add(c);
  const beak = beakMesh(); beak.position.set(0, -0.05, -0.05); c.add(beak);
  const keys = [
    { t: 0, yaw: 0.16, pitch: -0.03, roll: 0.02 }, { t: 0.95, yaw: -0.08, pitch: 0.0, roll: 0.06 },
    { t: 1.75, yaw: 0.22, pitch: -0.09, roll: -0.02 }, { t: 2.7, yaw: 0.03, pitch: 0.02, roll: 0.0 },
    { t: 3.7, yaw: -0.18, pitch: -0.05, roll: -0.05 }, { t: 4.5, yaw: 0.06, pitch: -0.02, roll: 0.03 },
  ];
  return {
    scene, camera: c,
    bloom: { strength: 0.75, radius: 0.55, threshold: 0.7 },
    grade: { sat: 0.85, contrast: 1.05, gain: [0.95, 1.0, 1.1], lift: [0.0, 0.01, 0.025], vignette: 0.45, grain: 0.06 },
    exposure: 1.25,
    update(t) {
      const sway = noise1(t * 0.6, 1) * 0.012;
      c.position.set(camPos.x + sway, camPos.y + noise1(t * 0.8, 2) * 0.006, camPos.z);
      applyHead(c, {}, snapHead(keys, t));
      c.rotation.x += noise1(t * 7, 3) * 0.003; c.rotation.y += noise1(t * 7, 4) * 0.003;
      leaves.rotation.y = noise1(t * 0.5, 5) * 0.004;
      W.city.userData.update(t);
    },
  };
}

export function shotC2() {
  const camPos = new THREE.Vector3(0, 21, 0);
  const W = forestWorld({
    fog: '#3a4466', fogDensity: 0.00028, sky: preDawnSky(0.55), hemiSky: '#7084b8', hemiGround: '#161a22', hemiI: 1.3,
    dirColor: '#c09090', dirI: 0.35, lit: 0.27, emissive: 2.2, camPos,
  });
  const { scene } = W;
  const leaves = buildLeafCloud({ seed: 7, count: 2400, center: camPos, rMin: 0.35, rMax: 5.5, forward: new THREE.Vector3(0, 0.3, -1), gapDeg: 9, leafSize: 0.09 });
  scene.add(leaves);
  const c = cam(74); scene.add(c);
  const wings = wingPair(); c.add(wings);
  // 経路：かがむ → 飛び立つ → 森の上を滑空して街へ
  const path = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, 21, 0), new THREE.Vector3(0, 21.6, -1.5), new THREE.Vector3(0.5, 25, -7),
    new THREE.Vector3(1.5, 32, -20), new THREE.Vector3(3, 42, -48), new THREE.Vector3(6, 52, -80),
  ]);
  return {
    scene, camera: c,
    bloom: { strength: 0.7, radius: 0.55, threshold: 0.72 },
    grade: { sat: 0.9, contrast: 1.05, gain: [1.0, 1.0, 1.08], lift: [0.005, 0.01, 0.025], vignette: 0.4, grain: 0.055 },
    exposure: 1.05,
    update(t) {
      const crouch = smooth(0.0, 0.5, t) * (1 - smooth(0.55, 0.75, t)) * 0.06;
      const u = easeInOut(clamp((t - 0.6) / 4.4)) ;
      const s = Math.pow(u, 0.85);
      const p = path.getPointAt(clamp(s));
      p.y -= crouch;
      const flapping = t > 0.6 && t < 2.6;
      const flapA = flapping ? Math.sin((t - 0.6) * Math.PI * 2 * 5.2) : 0;
      p.y += flapA * 0.05 * smooth(0.6, 0.8, t);
      c.position.copy(p);
      const pitch = lerp(-0.02, 0.32, smooth(0.5, 0.9, t)) * (1 - smooth(1.4, 2.8, t)) + lerp(0, -0.12, smooth(2.0, 4.0, t));
      const roll = Math.sin(t * 0.9) * 0.06 * smooth(2.2, 3.5, t) + flapA * 0.01;
      c.rotation.set(pitch + flapA * 0.015, 0.03 * Math.sin(t * 0.7), roll);
      // 翼：はばたき中は大きく、滑空中は少し見える位置で止める
      const glide = smooth(2.4, 2.9, t);
      const fl = flapping ? (0.25 + 0.75 * (0.5 + 0.5 * Math.sin((t - 0.6) * Math.PI * 2 * 5.2))) : 0;
      wings.userData.set(lerp(fl * 1.1 - 0.35, 0.05 + Math.sin(t * 1.3) * 0.03, glide), lerp(0, 0.15, glide));
      wings.visible = t > 0.55;
      W.city.userData.update(t + 5);
    },
  };
}

// ---------------------------------------------------------------- 渋谷の路地
export function streetWorld(opt) {
  const r = rng(opt.seed || 31);
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(opt.fog, opt.fogDensity);
  const sky = skyDome(opt.sky); scene.add(sky);
  scene.add(new THREE.HemisphereLight(opt.hemiSky, opt.hemiGround, opt.hemiI));
  const sun = new THREE.DirectionalLight(opt.sunColor, opt.sunI);
  sun.position.copy(opt.sky.sunDir).normalize().multiplyScalar(80);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -30, right: 30, top: 40, bottom: -40, near: 1, far: 200 });
  sun.shadow.bias = -0.0005; sun.shadow.normalBias = 0.02;
  scene.add(sun); scene.add(sun.target);
  // 路面
  const asph = asphaltTex(2); asph.repeat.set(3, 40);
  const road = new THREE.Mesh(new THREE.PlaneGeometry(6, 120), new THREE.MeshStandardMaterial({ map: asph, roughness: 0.92, color: 0xa8a8a8 }));
  road.rotation.x = -Math.PI / 2; road.position.z = -30; road.receiveShadow = true; scene.add(road);
  const lineM = new THREE.MeshStandardMaterial({ color: 0xd8d8d0, roughness: 0.8 });
  for (const x of [-2.3, 2.3]) {
    const l = new THREE.Mesh(new THREE.PlaneGeometry(0.12, 120), lineM); l.rotation.x = -Math.PI / 2; l.position.set(x, 0.003, -30); l.receiveShadow = true; scene.add(l);
  }
  // 両側の建物（3〜5階建て、間口いろいろ）
  const tex = [facadeTextures(41, 'concrete', opt.lit, 0.85), facadeTextures(42, 'concrete', opt.lit, 0.85), facadeTextures(43, 'glass', opt.lit * 0.6, 0.6)];
  const tints = [0xd8d0c4, 0xb8b4ae, 0xe6e0d6, 0x9ea4a8, 0xc9b9a6];
  for (const side of [-1, 1]) {
    let z = 20;
    while (z > -90) {
      const w = 5 + r() * 6, h = 8 + r() * 9, d = 10;
      const T = tex[Math.floor(r() * 3)];
      const geo = new THREE.BoxGeometry(d, h, w);
      // 外壁の UV を実寸に
      const uv = geo.attributes.uv;
      for (let i = 0; i < uv.count; i++) {
        const face = Math.floor(i / 4);
        let u = uv.getX(i), v = uv.getY(i);
        const fw = face < 2 ? w : d;
        if (face === 2 || face === 3) { u = 0.002; v = 0.002; } else { u = u * fw / 28.8 + Math.floor(r() * 8) / 8; v = v * h / 28 + 0.0; }
        uv.setXY(i, u, v);
      }
      const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ map: T.map, emissiveMap: T.emissive, emissive: 0xffffff, emissiveIntensity: opt.windowGlow, roughness: 0.8, color: tints[Math.floor(r() * tints.length)] }));
      m.position.set(side * (2.6 + d / 2 + r() * 0.3), h / 2, z - w / 2);
      m.castShadow = m.receiveShadow = true; scene.add(m);
      // 室外機・看板なしの箱
      const acM = new THREE.MeshStandardMaterial({ color: 0xcfcfca, roughness: 0.6 });
      for (let k = 0; k < 2; k++) {
        if (r() < 0.5) continue;
        const ac = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.55, 0.75), acM);
        ac.position.set(side * 2.75, 3 + Math.floor(r() * 3) * 3, z - 0.8 - r() * (w - 1.6));
        ac.castShadow = true; scene.add(ac);
      }
      // 1階のシャッター
      const sh = new THREE.Mesh(new THREE.PlaneGeometry(w * 0.7, 2.4), new THREE.MeshStandardMaterial({ color: 0x8c9296, roughness: 0.5, metalness: 0.6, map: canvasTex(64, 256, (g, W, H) => { for (let y = 0; y < H; y += 8) { g.fillStyle = y % 16 ? '#9aa0a4' : '#80868a'; g.fillRect(0, y, W, 8); } }) }));
      sh.rotation.y = -side * Math.PI / 2; sh.position.set(side * 2.59, 1.2, z - w / 2); sh.receiveShadow = true; scene.add(sh);
      z -= w + 0.15 + r() * 0.6;
    }
  }
  // 電柱と電線
  const poleM = new THREE.MeshStandardMaterial({ color: 0x9a9a94, roughness: 0.8 });
  const wireM = new THREE.MeshStandardMaterial({ color: 0x151515, roughness: 0.6 });
  const poles = [3, -27, -57];
  for (const pz of poles) {
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.2, 11, 12), poleM); pole.position.set(2.45, 5.5, pz); pole.castShadow = true; scene.add(pole);
    const arm = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.1, 0.1), poleM); arm.position.set(2.1, 8.3, pz); scene.add(arm);
    const tr = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 1.0, 12), new THREE.MeshStandardMaterial({ color: 0x7f8580, roughness: 0.6 })); tr.position.set(2.95, 7.6, pz); scene.add(tr);
  }
  for (let i = 0; i < poles.length - 1; i++) {
    for (const [x, y, sg] of [[1.5, 7.2, 0.5], [2.1, 8.25, 0.6], [2.7, 8.25, 0.6], [2.45, 6.4, 0.4], [1.75, 5.3, 0.15]]) {
      scene.add(wire(new THREE.Vector3(x, y, poles[i]), new THREE.Vector3(x, y, poles[i + 1]), sg, 0.011, wireM));
    }
  }
  // 道を横切る引き込み線
  scene.add(wire(new THREE.Vector3(2.45, 6.8, -4), new THREE.Vector3(-2.6, 6.1, -9), 0.3, 0.008, wireM));
  scene.add(wire(new THREE.Vector3(2.45, 6.6, 3), new THREE.Vector3(-2.6, 5.4, 6), 0.25, 0.008, wireM));
  // 街灯
  const lampLight = new THREE.PointLight(0xffd9a0, opt.lampI, 14, 2); lampLight.position.set(2.0, 4.6, -12); scene.add(lampLight);
  const lamp = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.12, 0.25), new THREE.MeshBasicMaterial({ color: new THREE.Color(4, 3.2, 2.2).multiplyScalar(opt.lampI > 0 ? 1 : 0.1) })); lamp.position.set(2.05, 4.7, -12); scene.add(lamp);
  // 自販機（ロゴなしの光る箱）
  const vm = new THREE.Group();
  const vb = new THREE.Mesh(new THREE.BoxGeometry(0.75, 1.85, 1.0), new THREE.MeshStandardMaterial({ color: 0x2a5aa0, roughness: 0.5 })); vb.position.y = 0.925; vm.add(vb);
  const vf = new THREE.Mesh(new THREE.PlaneGeometry(0.85, 1.1), new THREE.MeshBasicMaterial({ color: new THREE.Color(2.4, 2.6, 2.8) })); vf.rotation.y = Math.PI / 2; vf.position.set(0.38, 1.15, 0); vm.add(vf);
  vm.position.set(-2.15, 0, -7.5); vb.castShadow = true; scene.add(vm);
  const vl = new THREE.PointLight(0xdfefff, 1.2, 5, 2); vl.position.set(-1.6, 1.2, -7.5); scene.add(vl);
  // ゴミ集積所（右側の電柱の先）とネット
  const bags = [];
  const br = rng(77);
  const spots = [[1.75, -3.9], [2.05, -4.35], [1.6, -4.55], [2.1, -3.55], [1.85, -4.95], [2.15, -5.1], [1.45, -3.4]];
  spots.forEach(([x, z], i) => {
    const b = garbageBag(br, 0.95 + br() * 0.3);
    b.position.set(x, 0.17, z); b.rotation.y = br() * 6; scene.add(b); bags.push(b);
  });
  // はみ出した袋（C4 でつつく袋）
  const target = garbageBag(br, 1.05); target.position.set(1.25, 0.17, -3.05); target.rotation.set(0.15, 1.0, -0.12); scene.add(target);
  // ネット：袋の上にかぶせた形に変形した平面
  const nt = netTex(); nt.repeat.set(6, 6);
  const ng = new THREE.PlaneGeometry(1.6, 2.4, 40, 60); ng.rotateX(-Math.PI / 2);
  const np = ng.attributes.position;
  for (let i = 0; i < np.count; i++) {
    const x = np.getX(i) + 1.9, z = np.getZ(i) - 4.3;
    let y = 0.02;
    for (const b of bags) { const d = Math.hypot(x - b.position.x, z - b.position.z); y = Math.max(y, 0.62 * b.scale.x * Math.sqrt(Math.max(0, 1 - (d / (0.36 * b.scale.x)) ** 2))); }
    np.setY(i, y + 0.01);
  }
  ng.computeVertexNormals();
  const net = new THREE.Mesh(ng, new THREE.MeshStandardMaterial({ map: nt, alphaTest: 0.35, side: THREE.DoubleSide, roughness: 0.7, color: 0xffffff }));
  net.position.set(1.9, 0, -4.3); net.castShadow = true; scene.add(net);
  // 散らばった中身（つつかれた後に出す）
  const bits = new THREE.Group();
  const bitCols = [0xc8a060, 0x7a5030, 0xe8e0c8, 0x9a3020, 0x608040];
  for (let k = 0; k < 9; k++) {
    const m = new THREE.Mesh(new THREE.IcosahedronGeometry(0.012 + br() * 0.014, 1), new THREE.MeshStandardMaterial({ color: bitCols[k % 5], roughness: 0.7 }));
    m.position.set(1.0 + br() * 0.3, 0.015, -2.86 + br() * 0.14); m.castShadow = true; bits.add(m);
  }
  bits.visible = false; scene.add(bits);
  return { scene, sky, sun, target, bits, bags };
}

const morningStreet = (k) => ({
  fog: '#b4bfcc', fogDensity: 0.01,
  sky: { zenith: new THREE.Color('#4c6ea0').lerp(new THREE.Color('#5d86bf'), k), horizon: new THREE.Color('#d6c4bc').lerp(new THREE.Color('#e2d6cc'), k), glow: '#e0a070', sunDir: new THREE.Vector3(0.75, 0.06 + k * 0.08, -0.6), glowSize: 10, exp: 0.55 },
  hemiSky: '#b4c8e4', hemiGround: '#6a645c', hemiI: 1.7 + k * 0.5, sunColor: '#ffc690', sunI: 0.9 + k * 1.4, lit: 0.12, windowGlow: 1.0, lampI: k < 0.5 ? 3 : 0,
});

export function shotC3() {
  const W = streetWorld({ ...morningStreet(0), seed: 31 });
  const { scene } = W;
  const c = cam(68); scene.add(c);
  const beak = beakMesh(); beak.position.set(0, -0.05, -0.05); c.add(beak);
  const keys = [
    { t: 0, yaw: 0.12, pitch: -0.3, roll: 0 }, { t: 0.8, yaw: 0.02, pitch: -0.42, roll: 0.04 },
    { t: 1.55, yaw: 0.0, pitch: -0.86, roll: 0.0 }, { t: 2.3, yaw: 0.02, pitch: -0.9, roll: 0.18 },
    { t: 3.1, yaw: -0.03, pitch: -0.88, roll: -0.12 }, { t: 3.9, yaw: 0.0, pitch: -0.92, roll: 0.15 },
  ];
  return {
    scene, camera: c,
    bloom: { strength: 0.45, radius: 0.5, threshold: 0.9 },
    grade: { sat: 0.92, contrast: 1.06, gain: [1.0, 1.0, 1.04], lift: [0.01, 0.012, 0.02], vignette: 0.38, grain: 0.045 },
    exposure: 1.15,
    update(t) {
      const bounce = Math.sin(t * 2.1) * 0.01 + noise1(t * 1.5, 9) * 0.008; // 電線のゆれ
      c.position.set(1.75, 5.52 + bounce, -0.9);
      applyHead(c, {}, snapHead(keys, t));
      c.rotation.x += noise1(t * 8, 1) * 0.004; c.rotation.y += noise1(t * 8, 2) * 0.004;
    },
  };
}

export function shotC4() {
  const W = streetWorld({ ...morningStreet(0.25), seed: 31 });
  const { scene, target, bits } = W;
  const c = cam(74); scene.add(c);
  const beak = beakMesh(); c.add(beak);
  const start = new THREE.Vector3(0.55, 0.2, 0.3), end = new THREE.Vector3(0.95, 0.2, -2.25);
  const hopT = [0.25, 0.7, 1.15, 1.6, 2.05, 2.5, 2.9];
  const pecks = [3.35, 3.85, 4.3];
  const keys = [
    { t: 0, yaw: 0.0, pitch: 0.06, roll: 0 }, { t: 0.95, yaw: 0.25, pitch: 0.04, roll: 0.06 }, { t: 1.4, yaw: -0.18, pitch: 0.02, roll: -0.04 },
    { t: 2.25, yaw: -0.12, pitch: -0.02, roll: 0.03 }, { t: 3.05, yaw: -0.2, pitch: -0.18, roll: 0.0 },
  ];
  return {
    scene, camera: c,
    bloom: { strength: 0.4, radius: 0.5, threshold: 0.9 },
    grade: { sat: 0.95, contrast: 1.07, gain: [1.0, 1.0, 1.03], lift: [0.01, 0.012, 0.018], vignette: 0.42, grain: 0.045 },
    exposure: 1.2,
    update(t) {
      let hops = 0, hopY = 0, land = 0;
      for (const h of hopT) {
        if (t >= h) { const k = clamp((t - h) / 0.22); hops += easeInOut(k); hopY += Math.sin(Math.PI * k) * 0.06; if (t - h < 0.35) land += Math.exp(-(t - h - 0.22) * 25) * (t - h > 0.22 ? 1 : 0); }
      }
      const p = start.clone().lerp(end, hops / hopT.length);
      p.y += hopY;
      c.position.copy(p);
      const h = snapHead(keys, t);
      applyHead(c, {}, h);
      // 対象の袋の方へ向ける
      const yawTo = Math.atan2(-(target.position.x - p.x), -(target.position.z - p.z));
      c.rotation.y = lerp(h.yaw, yawTo, smooth(2.6, 3.1, t)) + (t < 2.6 ? 0 : 0);
      c.rotation.x += -land * 0.05 + noise1(t * 9, 4) * 0.005;
      // つつく
      let pk = 0;
      for (const q of pecks) { const k = (t - q) / 0.24; if (k > 0 && k < 1) pk = Math.max(pk, Math.sin(Math.PI * k)); }
      beak.position.set(0, -0.05 + pk * 0.012, -0.05 - pk * 0.05);
      c.position.addScaledVector(new THREE.Vector3(-Math.sin(c.rotation.y), -0.35, -Math.cos(c.rotation.y)), pk * 0.07);
      c.rotation.x -= pk * 0.18;
      // 袋がゆれる
      let hit = 0;
      for (const q of pecks) { const d = t - q - 0.12; if (d > 0) hit += Math.exp(-d * 6) * Math.sin(d * 30) * 0.06; }
      target.rotation.z = -0.12 + hit; target.scale.setScalar(1.05 * (1 - Math.abs(hit) * 0.3));
      bits.visible = t > pecks[1] + 0.15;
      bits.children.forEach((b, i) => { const k = clamp((t - pecks[1] - 0.15 - i * 0.03) / 0.3); b.position.y = 0.02 + (1 - k) * 0.12 * (k > 0 ? 1 : 0); });
    },
  };
}

// ---------------------------------------------------------------- 収集車 → スクランブル交差点
function truckModel() {
  const g = new THREE.Group();
  const white = new THREE.MeshStandardMaterial({ color: 0xe8e8e2, roughness: 0.4, metalness: 0.2 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x1a1f24, roughness: 0.15, metalness: 0.5 });
  const body = new THREE.Mesh(new THREE.BoxGeometry(1.95, 1.9, 3.3), white); body.position.set(0, 1.45, 0.9); g.add(body);
  const cab = new THREE.Mesh(new THREE.BoxGeometry(1.9, 1.75, 1.5), white); cab.position.set(0, 1.35, -1.55); g.add(cab);
  const ws = new THREE.Mesh(new THREE.PlaneGeometry(1.7, 0.75), dark); ws.position.set(0, 1.75, -2.31); ws.rotation.y = Math.PI; g.add(ws);
  const stripe = new THREE.Mesh(new THREE.BoxGeometry(1.97, 0.18, 3.32), new THREE.MeshStandardMaterial({ color: 0x2a7a4a, roughness: 0.5 })); stripe.position.set(0, 1.0, 0.9); g.add(stripe);
  const hl = new THREE.MeshBasicMaterial({ color: new THREE.Color(9, 8.5, 7) });
  for (const x of [-0.7, 0.7]) { const l = new THREE.Mesh(new THREE.CircleGeometry(0.11, 16), hl); l.position.set(x, 0.75, -2.31); l.rotation.y = Math.PI; g.add(l); }
  const tyre = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.9 });
  for (const [x, z] of [[-0.9, -1.5], [0.9, -1.5], [-0.9, 1.4], [0.9, 1.4]]) { const w = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 0.3, 20), tyre); w.rotation.z = Math.PI / 2; w.position.set(x, 0.42, z); g.add(w); }
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  return g;
}

function crossingWorld() {
  const r = rng(51);
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2('#c4cfdb', 0.0035);
  const sunDir = new THREE.Vector3(0.8, 0.42, -0.45);
  scene.add(skyDome({ zenith: '#4f7fc4', horizon: '#dfe6ec', glow: '#fff0d8', sunDir, glowSize: 30, exp: 0.5 }));
  scene.add(new THREE.HemisphereLight('#c4d6ee', '#7a746a', 1.9));
  const sun = new THREE.DirectionalLight('#fff0dc', 2.6);
  sun.position.copy(sunDir).multiplyScalar(150); sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -90, right: 90, top: 90, bottom: -90, near: 1, far: 400 }); sun.shadow.bias = -0.0006;
  scene.add(sun);
  const asph = asphaltTex(9); asph.repeat.set(30, 30);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(600, 600), new THREE.MeshStandardMaterial({ map: asph, roughness: 0.9, color: 0x9a9a9a }));
  ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);
  // 歩道（角）
  const walkM = new THREE.MeshStandardMaterial({ color: 0xa9a49a, roughness: 0.85 });
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    const s = new THREE.Mesh(new THREE.BoxGeometry(80, 0.18, 80), walkM); s.position.set(sx * (13 + 40), 0.09, sz * (14 + 40)); s.receiveShadow = true; scene.add(s);
  }
  // 横断歩道（スクランブル：4辺＋対角2本）
  const stripeM = new THREE.MeshStandardMaterial({ color: 0xe8e8e2, roughness: 0.7 });
  const stripes = [];
  const addCross = (cx, cz, ang, len, width) => {
    const n = Math.floor(len / 0.9);
    for (let i = 0; i < n; i++) {
      const g = new THREE.PlaneGeometry(0.45, width); g.rotateX(-Math.PI / 2);
      const off = -len / 2 + i * 0.9;
      g.rotateY(ang); g.translate(cx + Math.cos(ang) * off, 0.01, cz - Math.sin(ang) * off);
      stripes.push(g);
    }
  };
  addCross(0, -11.5, 0, 24, 5); addCross(0, 11.5, 0, 24, 5);
  addCross(-11, 0, Math.PI / 2, 22, 5); addCross(11, 0, Math.PI / 2, 22, 5);
  addCross(0, 0, Math.PI / 4.1, 26, 4); addCross(0, 0, -Math.PI / 4.1, 26, 4);
  for (const g of stripes) { const m = new THREE.Mesh(g, stripeM); m.receiveShadow = true; scene.add(m); }
  // 周りの建物＋大型ビジョン（文字なし・抽象的な色）
  const city = buildCity({ seed: 61, x0: -260, x1: 260, z0: -260, z1: 260, spacing: 24, hMin: 18, hMax: 70, towers: [{ x: 40, z: -60, r: 60, h: 180 }],
    lit: 0.05, emissive: 0.6, shadows: true, skip: 0.05, avoid: (x, z) => Math.abs(x) < 26 || Math.abs(z) < 26 });
  scene.add(city);
  const screenMat = new THREE.ShaderMaterial({ uniforms: { t: { value: 0 } }, fog: false,
    vertexShader: 'varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }',
    fragmentShader: 'uniform float t; varying vec2 vUv; void main(){ vec2 p=vUv*3.; float a=sin(p.x*2.+t*1.3)+sin(p.y*3.-t)+sin((p.x+p.y)*1.5+t*0.7); vec3 c=0.5+0.5*cos(a+vec3(0.,2.,4.)); gl_FragColor=vec4(c*1.6,1.); }' });
  for (const [x, z, ry, w, h, y] of [[-28, -27, Math.PI / 4, 14, 8, 22], [28, -30, -Math.PI / 4, 12, 9, 30], [-30, 28, Math.PI * 0.75, 12, 7, 18]]) {
    const s = new THREE.Mesh(new THREE.PlaneGeometry(w, h), screenMat); s.position.set(x, y, z); s.rotation.y = ry; scene.add(s);
    const back = new THREE.Mesh(new THREE.BoxGeometry(w + 1, h + 1, 0.8), new THREE.MeshStandardMaterial({ color: 0x222428 })); back.position.set(x, y, z); back.rotation.y = ry; back.translateZ(-0.45); scene.add(back);
  }
  // 停車中の車
  const carCols = [0xf0f0f0, 0x202020, 0x8a8f96, 0x2a3c5a, 0xd0d0cc, 0x5a1a1a];
  for (let i = 0; i < 12; i++) {
    const car = new THREE.Mesh(new THREE.BoxGeometry(1.75, 1.4, 4.3), new THREE.MeshStandardMaterial({ color: carCols[i % carCols.length], roughness: 0.3, metalness: 0.5 }));
    const lane = i % 4;
    const pos = [[-4 - (i % 2) * 3.4, 0.7, -20 - Math.floor(i / 4) * 6, 0], [4 + (i % 2) * 3.4, 0.7, 20 + Math.floor(i / 4) * 6, 0], [-21 - Math.floor(i / 4) * 6, 0.7, 4 + (i % 2) * 3.4, Math.PI / 2], [21 + Math.floor(i / 4) * 6, 0.7, -4 - (i % 2) * 3.4, Math.PI / 2]][lane];
    car.position.set(pos[0], pos[1], pos[2]); car.rotation.y = pos[3]; car.castShadow = true; scene.add(car);
  }
  // 人の流れ
  const N = 520;
  const bodyG = new THREE.CapsuleGeometry(0.22, 1.05, 4, 8); bodyG.translate(0, 0.75, 0);
  const headG = new THREE.SphereGeometry(0.12, 10, 8); headG.translate(0, 1.6, 0);
  const bodyM = new THREE.MeshStandardMaterial({ roughness: 0.85 }), headM = new THREE.MeshStandardMaterial({ roughness: 0.7 });
  const bodies = new THREE.InstancedMesh(bodyG, bodyM, N), heads = new THREE.InstancedMesh(headG, headM, N);
  bodies.castShadow = heads.castShadow = true;
  const coat = ['#141414', '#1d2433', '#3b3b3e', '#8a7a62', '#5a4a3a', '#c8c2b5', '#2e3a2e', '#6a2a2a', '#d9d4c8'].map((c) => new THREE.Color(c));
  const hair = ['#0d0b0a', '#1a1410', '#3a2a1e', '#2a2a2a', '#d8d0c0'].map((c) => new THREE.Color(c));
  const routes = [[[-14, -11.5], [14, -11.5]], [[14, 11.5], [-14, 11.5]], [[-11, 14], [-11, -14]], [[11, -14], [11, 14]], [[-13, -13], [13, 13]], [[13, -13], [-13, 13]], [[13, 13], [-13, -13]], [[-13, 13], [13, -13]]];
  const ppl = [];
  for (let i = 0; i < N; i++) {
    const route = routes[i % routes.length];
    const walking = r() < 0.8;
    ppl.push({ route, walking, ph: r(), sp: 1.1 + r() * 0.5, off: (r() - 0.5) * 3.6, cx: (r() - 0.5) * 8, cz: (r() - 0.5) * 8, corner: [[-16, -16], [16, -16], [-16, 16], [16, 16]][i % 4] });
    bodies.setColorAt(i, coat[Math.floor(r() * coat.length)]); heads.setColorAt(i, hair[Math.floor(r() * hair.length)]);
  }
  scene.add(bodies, heads);
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), S = new THREE.Vector3(1, 1, 1), up = new THREE.Vector3(0, 1, 0);
  function updatePeople(t) {
    ppl.forEach((p, i) => {
      let x, z, ang;
      if (p.walking) {
        const [a, b] = p.route;
        const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const s = ((p.ph * L + t * p.sp) % L) / L;
        const dx = (b[0] - a[0]) / L, dz = (b[1] - a[1]) / L;
        x = lerp(a[0], b[0], s) - dz * p.off; z = lerp(a[1], b[1], s) + dx * p.off;
        ang = Math.atan2(dx, dz);
      } else { x = p.corner[0] + p.cx; z = p.corner[1] + p.cz; ang = p.ph * 6.28; }
      const bob = p.walking ? Math.abs(Math.sin((t * p.sp * 2.2 + p.ph * 10) * Math.PI)) * 0.04 : 0;
      Q.setFromAxisAngle(up, ang);
      M.compose(new THREE.Vector3(x, (p.walking ? 0 : 0.18) + bob, z), Q, S);
      bodies.setMatrixAt(i, M); heads.setMatrixAt(i, M);
    });
    bodies.instanceMatrix.needsUpdate = heads.instanceMatrix.needsUpdate = true;
  }
  return { scene, updatePeople, screenMat, city };
}

export function shotC5() {
  const A = streetWorld({ ...morningStreet(1), seed: 31, lampI: 0 });
  A.target.visible = true;
  const truck = truckModel(); truck.rotation.y = Math.PI; A.scene.add(truck);
  const B = crossingWorld();
  const ca = cam(74); A.scene.add(ca);
  const beak = beakMesh(); beak.position.set(0, -0.05, -0.05); ca.add(beak);
  const wa = wingPair(); ca.add(wa);
  const cb = cam(70); B.scene.add(cb);
  const wb = wingPair(); cb.add(wb);
  const SWITCH = 2.22;
  const shot = {
    scene: A.scene, camera: ca, scenes: [A.scene, B.scene],
    bloom: { strength: 0.5, radius: 0.5, threshold: 0.88 },
    grade: { sat: 1.0, contrast: 1.06, gain: [1.02, 1.0, 0.98], lift: [0.01, 0.01, 0.015], vignette: 0.36, grain: 0.04, blur: 0 },
    exposure: 0.9,
    update(t) {
      shot.grade.blur = Math.exp(-Math.pow((t - SWITCH) / 0.09, 2)) * 0.22;
      if (t < SWITCH) {
        shot.scene = A.scene; shot.camera = ca; shot.exposure = 1.1;
        truck.position.set(-0.6, 0, lerp(-42, -9, t / SWITCH));
        const lift = smooth(1.55, 2.2, t);
        ca.position.set(0.9 + lift * 0.3, 0.22 + lift * lift * 3.5, -2.0 - lift * 1.2);
        const h = snapHead([{ t: 0, yaw: -0.05, pitch: 0.05, roll: 0 }, { t: 0.7, yaw: 0.12, pitch: 0.04, roll: 0.05 }, { t: 1.25, yaw: 0.0, pitch: 0.07, roll: -0.03 }], t);
        applyHead(ca, {}, h);
        ca.rotation.x += lift * 0.9;
        const fl = t > 1.55 ? 0.5 + 0.5 * Math.sin((t - 1.55) * Math.PI * 2 * 5.5) : 0;
        wa.visible = t > 1.55; wa.userData.set(fl * 1.2 - 0.3, 0);
        beak.visible = t < 1.7;
      } else {
        shot.scene = B.scene; shot.camera = cb; shot.exposure = 1.05;
        const k = t - SWITCH;
        cb.position.set(-26 + k * 9.5, 34 + Math.sin(k * 1.1) * 0.6, 30 - k * 9.5);
        cb.rotation.set(-0.72 + k * 0.03, -Math.PI / 4 + 0.05 * Math.sin(k * 0.8), 0.07 * Math.sin(k * 0.9));
        wb.userData.set(0.08 + Math.sin(k * 1.4) * 0.04, 0.2);
        B.updatePeople(t + 30);
        B.screenMat.uniforms.t.value = t;
      }
    },
  };
  return shot;
}

// ---------------------------------------------------------------- 夕方：群れで森へ帰る
export function shotC6() {
  const scene = new THREE.Scene();
  const sunDir = new THREE.Vector3(-0.35, 0.02, -1);
  scene.fog = new THREE.FogExp2('#8a5a5a', 0.00042);
  scene.add(skyDome({ zenith: '#1b2050', horizon: '#ff8d4e', ground: '#3a2430', glow: '#ffb062', sunDir, glowSize: 14, sunDisk: 1, exp: 0.42 }));
  scene.add(new THREE.HemisphereLight('#6a5a8a', '#1a1010', 0.45));
  const dl = new THREE.DirectionalLight('#ff9a5a', 1.4); dl.position.copy(sunDir).multiplyScalar(500); scene.add(dl);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(30000, 30000), new THREE.MeshStandardMaterial({ color: 0x15100f, roughness: 1 }));
  ground.rotation.x = -Math.PI / 2; scene.add(ground);
  // 前方に森、左右と後ろに街
  scene.add(buildCanopy({ seed: 81, count: 7000, x0: -700, x1: 600, z0: -1500, z1: -380, yBase: 0, size: [5, 10], yJitter: 5, colors: ['#162a18', '#1c3319', '#203a1e'] }));
  const city = buildCity({ seed: 91, x0: -4000, x1: 4000, z0: -6000, z1: 1500, spacing: 50, hMin: 12, hMax: 60,
    towers: [{ x: 900, z: -400, r: 400, h: 200 }, { x: -1500, z: -2600, r: 500, h: 210 }, { x: 1800, z: -3600, r: 600, h: 180 }],
    lit: 0.2, emissive: 1.4, skip: 0.15, avoid: (x, z) => x > -800 && x < 700 && z > -1600 && z < -300 });
  scene.add(city);
  const crowMat = new THREE.MeshStandardMaterial({ color: 0x070709, roughness: 0.5, metalness: 0.1, side: THREE.DoubleSide });
  const r = rng(5);
  const flock = [];
  for (let i = 0; i < 34; i++) {
    const m = crowModel(crowMat); m.scale.setScalar(1.25); scene.add(m);
    flock.push({ m, off: new THREE.Vector3((r() - 0.5) * 34, (r() - 0.5) * 12, -3 - Math.pow(r(), 0.8) * 70), ph: r() * 10, f: 3.6 + r() * 1.4, glide: r() });
  }
  const c = cam(70); scene.add(c);
  const wings = wingPair(); c.add(wings);
  return {
    scene, camera: c,
    bloom: { strength: 0.85, radius: 0.6, threshold: 0.75 },
    grade: { sat: 1.08, contrast: 1.08, gain: [1.06, 0.98, 0.92], lift: [0.02, 0.005, 0.02], vignette: 0.5, grain: 0.05 },
    exposure: 0.95,
    update(t) {
      const pos = new THREE.Vector3(60 - t * 4, 75 - t * 1.2, 120 - t * 15);
      c.position.copy(pos);
      c.rotation.set(-0.06 + Math.sin(t * 0.6) * 0.02, -0.12 + Math.sin(t * 0.5) * 0.04, Math.sin(t * 0.8) * 0.05);
      const fl = Math.sin(t * Math.PI * 2 * 4.2);
      const flapping = (t % 2.4) < 1.0;
      wings.userData.set(flapping ? (0.3 + 0.6 * (0.5 + 0.5 * fl)) - 0.3 : 0.06, flapping ? 0 : 0.2);
      c.position.y += flapping ? fl * 0.04 : 0;
      for (const b of flock) {
        const drift = new THREE.Vector3(Math.sin(t * 0.7 + b.ph) * 1.5, Math.sin(t * 0.9 + b.ph * 2) * 0.8, Math.sin(t * 0.4 + b.ph) * 1.2);
        const p = pos.clone().add(new THREE.Vector3(b.off.x, b.off.y, b.off.z).applyAxisAngle(new THREE.Vector3(0, 1, 0), -0.12)).add(drift);
        b.m.position.copy(p);
        b.m.rotation.set(0.05, -0.12 + Math.sin(t + b.ph) * 0.1, Math.sin(t * 1.3 + b.ph) * 0.15);
        const gl = ((t + b.ph) % 3) < (1 + b.glide);
        b.m.userData.flap(gl ? Math.sin((t + b.ph) * Math.PI * 2 * b.f) * 0.75 : 0.05);
      }
      city.userData.update(t);
    },
  };
}
