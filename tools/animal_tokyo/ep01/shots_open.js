// 外から撮るカット（O1 夜明けのカラス / O2 横顔の解説 / O3 夜のねぐら）と、X1 人の顔を見分けるカット
import * as THREE from 'three';
import { rng, clamp, lerp, smooth, easeOut, easeInOut, noise1, snapHead, buildCity, buildCanopy, buildLeafCloud, skyDome, barkTex, beakMesh } from './lib.js';
import { perchedCrow } from './crow.js';
import { streetWorld } from './shots.js';
import { people } from './shots_day.js';

const ASPECT = 720 / 1280;
const camT = (fov) => { const c = new THREE.PerspectiveCamera(fov, ASPECT, 0.02, 9000); return c; };

// 夜明け／夕暮れの森の枝。crowAt に主役のカラス
function branchWorld(o) {
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(o.fog, o.fogD);
  scene.add(skyDome(o.sky));
  scene.add(new THREE.HemisphereLight(o.hemi[0], o.hemi[1], o.hemi[2]));
  const key = new THREE.DirectionalLight(o.key[0], o.key[1]); key.position.set(-2, 3, -3); key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024); Object.assign(key.shadow.camera, { left: -1, right: 1, top: 1, bottom: -1, near: 0.1, far: 10 }); key.shadow.bias = -0.0005;
  scene.add(key);
  const rim = new THREE.DirectionalLight(o.rim[0], o.rim[1]); rim.position.set(0.6, 1.2, 4); scene.add(rim);
  const rim2 = new THREE.DirectionalLight(o.rim[0], o.rim[1] * 0.6); rim2.position.set(-1.5, 0.6, 3); scene.add(rim2);
  // 枝
  const bark = barkTex(5);
  const bm = new THREE.MeshStandardMaterial({ map: bark, bumpMap: bark, bumpScale: 3, roughness: 0.95, color: 0x9a948c });
  const br = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([
    new THREE.Vector3(-2.2, -0.3, 0.5), new THREE.Vector3(-0.8, -0.08, 0.15), new THREE.Vector3(0, -0.03, 0), new THREE.Vector3(0.9, -0.02, -0.25), new THREE.Vector3(1.8, 0.15, -0.3)]), 80, 0.03, 14), bm);
  br.castShadow = br.receiveShadow = true; scene.add(br);
  const tw = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([new THREE.Vector3(0.5, -0.02, -0.15), new THREE.Vector3(0.75, 0.25, -0.1), new THREE.Vector3(0.85, 0.5, 0.05)]), 24, 0.012, 8), bm);
  if (!o.noTwig) scene.add(tw);
  if (!o.noLeaves) scene.add(buildLeafCloud({ seed: o.seed, count: 450, center: new THREE.Vector3(0.6, 0.35, 0.3), rMin: 0.25, rMax: 1.6, forward: new THREE.Vector3(-1, -0.3, -0.8), gapDeg: 50, leafSize: 0.09 }));
  // 遠景：森と街（背景でぼける）
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(20000, 20000), new THREE.MeshStandardMaterial({ color: 0x0e1012, roughness: 1 })); ground.rotation.x = -Math.PI / 2; ground.position.y = -20; scene.add(ground);
  const cano = buildCanopy({ seed: o.seed + 1, count: 1500, x0: -300, x1: 300, z0: 6, z1: 260, yBase: -21, size: [4, 8], yJitter: 4 }); scene.add(cano);
  const city = buildCity({ seed: o.seed + 2, x0: -2500, x1: 2500, z0: 350, z1: 4000, spacing: 50, hMin: 15, hMax: 60, towers: [{ x: 300, z: 1300, r: 400, h: 230 }, { x: -700, z: 2000, r: 300, h: 170 }], lit: o.lit, emissive: o.emissive, skip: 0.15 });
  city.position.y = -20; scene.add(city);
  const crow = perchedCrow(); scene.add(crow);
  return { scene, crow, city };
}

const dawn = { fog: '#2f3756', fogD: 0.00035, seed: 61, lit: 0.3, emissive: 3,
  sky: { zenith: '#0b1630', horizon: '#6a6a8e', ground: '#151a28', glow: '#d0866a', sunDir: new THREE.Vector3(0.15, -0.04, 1), glowSize: 6, exp: 0.5 },
  hemi: ['#7d8fc0', '#1a1c24', 0.9], key: ['#b8c6ee', 1.3], rim: ['#d8d0e8', 1.6] };

// ================================================================ O1 夜明けのカラス（タイトル）
export function shotO1() {
  const W = branchWorld(dawn);
  const { scene, crow } = W;
  crow.rotation.y = -0.5;
  const c = camT(30); scene.add(c);
  const target = new THREE.Vector3(0, 0.2, -0.04);
  const S = {
    scene, camera: c,
    dof: { focus: 1, aperture: 0.03, maxblur: 0.014 },
    bloom: { strength: 0.9, radius: 0.6, threshold: 0.6 },
    grade: { sat: 0.9, contrast: 1.06, gain: [1.0, 1.0, 1.06], lift: [0.005, 0.01, 0.025], vignette: 0.45, grain: 0.05 },
    exposure: 1.2,
    update(t) {
      const d = lerp(1.25, 0.82, easeInOut(t / 5));
      const ang = lerp(-0.55, -0.35, t / 5);
      c.position.set(Math.sin(ang) * d, 0.24 + t * 0.006, -Math.cos(ang) * d * 1.0);
      c.lookAt(target.clone().add(new THREE.Vector3(0, 0.03 * smooth(0, 5, t), 0)));
      S.dof.focus = c.position.distanceTo(new THREE.Vector3(0, 0.3, -0.1));
      // 首を回して鳴く（ハシブトの澄んだ「カァ」）
      const h = snapHead([{ t: 0, yaw: -0.3, pitch: 0 }, { t: 1.3, yaw: 0.45, pitch: -0.05 }, { t: 3.7, yaw: 0.1, pitch: 0.05 }, { t: 4.4, yaw: 0.5, pitch: 0 }], t, 0.14);
      let open = 0, bob = 0;
      for (const k of [2.0, 2.65]) { const u = (t - k) / 0.42; if (u > 0 && u < 1) { open = Math.max(open, Math.sin(Math.PI * u)); bob = Math.max(bob, Math.sin(Math.PI * u)); } }
      crow.userData.pose({ yaw: h.yaw, pitch: h.pitch - bob * 0.12, roll: 0, open, fluff: 0.15 + Math.sin(t * 2.4) * 0.03 });
      crow.position.y = Math.sin(t * 2.4) * 0.002;
      W.city.userData.update(t);
    },
  };
  return S;
}

// ================================================================ O2 横顔：ハシブトガラスの見分け方
export function shotO2() {
  const W = branchWorld({ ...dawn, noTwig: true, noLeaves: true, sky: { ...dawn.sky, zenith: '#13244a', horizon: '#8a7f98', glow: '#e09a70' }, hemi: ['#8a9cc8', '#1a1c24', 1.5], key: ['#c8d4f6', 1.5] });
  const { scene, crow } = W;
  crow.rotation.y = 0;
  const c = camT(30); scene.add(c);
  const eye = new THREE.Vector3(0.031, 0.311, -0.113);
  const look = new THREE.Vector3(0, 0.27, 0.03);
  const S = {
    scene, camera: c,
    dof: { focus: 1.7, aperture: 0.02, maxblur: 0.012 },
    bloom: { strength: 0.8, radius: 0.6, threshold: 0.6 },
    grade: { sat: 0.9, contrast: 1.06, gain: [1.0, 1.0, 1.05], lift: [0.005, 0.01, 0.022], vignette: 0.42, grain: 0.045 },
    exposure: 1.3,
    update(t) {
      // 横から全身 → 最後に目へ寄ってカラス目線へ
      const pushU = easeInOut(clamp((t - 3.9) / 1.1));
      const far = new THREE.Vector3(1.45, 0.19, 0.03);
      const near = eye.clone().add(new THREE.Vector3(0.035, 0.0, 0.0));
      c.position.copy(far.clone().lerp(near, Math.pow(pushU, 0.6)));
      c.position.z += Math.sin(t * 0.5) * 0.02 * (1 - pushU);
      c.lookAt(look.clone().lerp(eye, smooth(3.9, 4.5, t)));
      c.fov = lerp(30, 40, pushU); c.updateProjectionMatrix();
      S.dof.focus = c.position.distanceTo(look.clone().lerp(eye, pushU));
      const h = snapHead([{ t: 0, yaw: 0, pitch: 0 }, { t: 2.4, yaw: 0.08, pitch: -0.04 }, { t: 3.3, yaw: 0.0, pitch: 0.02 }], t, 0.14);
      crow.userData.pose({ yaw: h.yaw, pitch: h.pitch, open: 0, fluff: 0.12 + Math.sin(t * 2.4) * 0.03 });
      W.city.userData.update(t);
    },
    flash: (t) => smooth(4.55, 5.0, t),
    labels(t) {
      const out = smooth(3.7, 3.9, t);
      return [
        { pos: new THREE.Vector3(0, 0.29, -0.19), text: '太いくちばし', dx: -150, dy: 120, alpha: smooth(0.4, 0.7, t) * (1 - out) },
        { pos: new THREE.Vector3(0, 0.35, -0.12), text: '出っぱった おでこ', dx: -170, dy: -40, alpha: smooth(1.0, 1.3, t) * (1 - out) },
        { pos: new THREE.Vector3(0, 0.285, -0.205), to: new THREE.Vector3(0, -0.035, 0.27), text: '全長 約56cm', dx: 110, dy: 30, grow: easeOut((t - 1.7) / 0.8), alpha: smooth(1.7, 1.9, t) * (1 - out) },
      ];
    },
  };
  return S;
}

// ================================================================ O3 夜のねぐら（PM 5:00）
export function shotO3() {
  const dusk = { ...dawn, fog: '#1a2036', fogD: 0.0004, seed: 71, lit: 0.42, emissive: 3.2,
    sky: { zenith: '#070c1e', horizon: '#3a3f66', ground: '#10141f', glow: '#a0583e', sunDir: new THREE.Vector3(-0.3, -0.06, 1), glowSize: 5, exp: 0.5 },
    hemi: ['#5a6890', '#0e1016', 0.8], key: ['#8a9cd0', 0.9], rim: ['#9aa8d8', 1.1] };
  const W = branchWorld(dusk);
  const { scene, crow } = W;
  crow.rotation.y = 0.3;
  // まわりの枝で休む仲間
  const r = rng(4); const mates = [];
  for (let i = 0; i < 6; i++) {
    const m = perchedCrow(); const a = i / 6 * Math.PI * 1.4 - 0.4;
    m.position.set(Math.cos(a) * (1.5 + r() * 1.5), 0.2 + r() * 1.2, 1.5 + Math.sin(a) * 1.2 + r() * 2);
    m.rotation.y = r() * 6; m.userData.ph = r() * 10; scene.add(m); mates.push(m);
    const b = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.03, 1.4, 8), new THREE.MeshStandardMaterial({ color: 0x2a2420, roughness: 1 }));
    b.rotation.z = Math.PI / 2 + (r() - 0.5) * 0.3; b.rotation.y = r() * 3; b.position.copy(m.position).add(new THREE.Vector3(0, -0.03, 0)); scene.add(b);
  }
  const c = camT(32); scene.add(c);
  const S = {
    scene, camera: c,
    dof: { focus: 1, aperture: 0.025, maxblur: 0.013 },
    bloom: { strength: 0.65, radius: 0.55, threshold: 0.78 },
    grade: { sat: 0.85, contrast: 1.1, gain: [0.95, 0.98, 1.08], lift: [0.0, 0.005, 0.02], vignette: 0.5, grain: 0.06 },
    exposure: 1.05,
    update(t) {
      const d = lerp(1.35, 1.1, easeInOut(t / 6));
      c.position.set(-0.75 * d, 0.3, -0.66 * d);
      c.lookAt(0, 0.2, 0);
      S.dof.focus = c.position.distanceTo(new THREE.Vector3(0, 0.25, -0.05));
      // 羽をふくらませ、首を背中にうずめて眠る
      const tuck = easeInOut(clamp((t - 2.6) / 1.2));
      const h = snapHead([{ t: 0, yaw: 0.3, pitch: 0 }, { t: 1.0, yaw: -0.3, pitch: 0.05 }, { t: 1.8, yaw: 0.1, pitch: 0 }], t, 0.14);
      crow.userData.pose({ yaw: lerp(h.yaw, 2.5, tuck), pitch: lerp(h.pitch, 0.35, tuck), roll: lerp(0, 0.3, tuck), fluff: smooth(1.8, 2.8, t) * 0.9 + 0.1 });
      for (const m of mates) m.userData.pose({ yaw: Math.sin(Math.floor(t * 0.8 + m.userData.ph) * 2.3) * 0.6, fluff: 0.6 });
      W.city.userData.update(t);
    },
  };
  return S;
}

// ================================================================ X1 人の顔を見分ける（PM 1:30）
export function shotX1() {
  const sky = { zenith: '#4c7ec4', horizon: '#dde6ee', glow: '#fff0d8', sunDir: new THREE.Vector3(-0.4, 0.7, -0.5), glowSize: 30, exp: 0.5 };
  const Wd = streetWorld({ seed: 31, fog: '#c8d4e0', fogDensity: 0.008, sky, hemiSky: '#c4d6ee', hemiGround: '#7a7268', hemiI: 1.8, sunColor: '#fff2e0', sunI: 2.4, lit: 0.04, windowGlow: 0.4, lampI: 0 });
  const { scene } = Wd;
  Wd.bags.forEach((b) => (b.visible = false)); Wd.target.visible = false; Wd.bits.visible = false;
  scene.traverse((o) => { if (o.isMesh && o.material && o.material.map && o.material.alphaTest > 0.3 && o.position.x > 1.5 && o.position.z < -3) o.visible = false; });
  // 通りを歩く人。i=0 が「前に追い払った人」
  const list = [];
  const P = people(26, 81, (r, i) => {
    const x = i === 0 ? 0.4 : (r() - 0.5) * 3.6; const dir = i === 0 ? 1 : (r() < 0.5 ? 1 : -1);
    const z0 = i === 0 ? -16 : -30 + r() * 30; const sp = i === 0 ? 1.15 : 0.9 + r() * 0.5;
    const o = { at: (t) => ({ pos: new THREE.Vector3(x, 0, dir > 0 ? z0 + sp * t : z0 - sp * t + 20), ang: dir > 0 ? 0 : Math.PI }) };
    list.push(o); return o;
  });
  scene.add(P.bodies, P.heads);
  const c = new THREE.PerspectiveCamera(68, ASPECT, 0.01, 16000); c.rotation.order = 'YXZ'; scene.add(c);
  const beak = beakMesh(); beak.position.set(0, -0.05, -0.05); c.add(beak);
  const S = {
    scene, camera: c,
    bloom: { strength: 0.35, radius: 0.45, threshold: 0.92 },
    grade: { sat: 1.0, contrast: 1.06, gain: [1.02, 1.0, 0.98], lift: [0.01, 0.012, 0.014], vignette: 0.38, grain: 0.035 },
    exposure: 1.0,
    update(t) {
      P.update(t);
      c.position.set(1.75, 5.52 + Math.sin(t * 2.1) * 0.01, -0.9);
      // 気になる顔を目で追う
      const tp = list[0].at(t).pos.clone().add(new THREE.Vector3(0, 1.6, 0));
      const d = tp.clone().sub(c.position);
      const yawT = Math.atan2(-d.x, -d.z), pitchT = Math.atan2(d.y, Math.hypot(d.x, d.z));
      const h = snapHead([{ t: 0, yaw: 0.1, pitch: -0.75, roll: 0 }, { t: 0.9, yaw: -0.15, pitch: -0.8, roll: 0.1 }], t);
      const k = smooth(1.6, 1.8, t);
      c.rotation.set(lerp(h.pitch, pitchT + 0.2, k), lerp(h.yaw, yawT, k), lerp(h.roll, 0.15 * Math.sin(t * 3), k));
      c.rotation.x += noise1(t * 8, 1) * 0.004;
    },
    labels(t) {
      const L = [];
      list.slice(0, 9).forEach((o, i) => {
        const p = o.at(t).pos.clone().add(new THREE.Vector3(0, 1.6, 0));
        const v = p.clone().project(c);
        if (v.z > 1 || Math.abs(v.x) > 0.9 || Math.abs(v.y) > 0.9) return;
        const a = smooth(0.4 + i * 0.08, 0.6 + i * 0.08, t);
        if (i === 0) {
          const hit = smooth(1.7, 1.9, t); const pulse = 1 + Math.sin(t * 12) * 0.08 * hit;
          L.push({ pos: p, box: true, size: 40 * pulse, alpha: a, color: hit > 0.5 ? '#ff5a4a' : '#7fe07f', text: hit > 0.5 ? '前にこわいことをした人！' : '' });
        } else L.push({ pos: p, box: true, size: 28, alpha: a * 0.8, color: '#7fe07f', text: '' });
      });
      return L;
    },
  };
  return S;
}

// ================================================================ E1 エンディング：翌朝、カメラの方を向いて首をかしげる
export function shotE1() {
  const morning = { ...dawn, seed: 83, lit: 0.18, emissive: 2.4,
    sky: { zenith: '#24406e', horizon: '#8a8aa6', ground: '#1e2028', glow: '#e8a070', sunDir: new THREE.Vector3(0.6, 0.03, 1), glowSize: 5, exp: 0.55 },
    hemi: ['#8ea0c8', '#221f1c', 1.0], key: ['#ffe2c0', 2.2], rim: ['#e0dcf0', 1.2] };
  const W = branchWorld(morning);
  const { scene, crow } = W;
  crow.rotation.y = -0.5;
  const c = camT(30); scene.add(c);
  const S = {
    scene, camera: c,
    dof: { focus: 1, aperture: 0.03, maxblur: 0.014 },
    bloom: { strength: 0.5, radius: 0.55, threshold: 0.82 },
    grade: { sat: 0.95, contrast: 1.07, gain: [1.03, 1.0, 0.98], lift: [0.0, 0.005, 0.015], vignette: 0.45, grain: 0.05 },
    exposure: 1.0,
    update(t) {
      const d = lerp(1.75, 1.55, easeInOut(t / 8));
      const ang = -0.3;
      c.position.set(Math.sin(ang) * d, 0.28, -Math.cos(ang) * d);
      c.lookAt(0, 0.02, -0.04);
      S.dof.focus = c.position.distanceTo(new THREE.Vector3(0, 0.3, -0.1));
      // こちらを見て、首をかしげる（「次はだれ？」）
      const h = snapHead([{ t: 0, yaw: -0.4, pitch: 0 }, { t: 0.7, yaw: 0.3, pitch: 0.02 }, { t: 2.4, yaw: 0.3, pitch: -0.04 }, { t: 4.6, yaw: 0.25, pitch: 0.02 }], t, 0.14);
      const roll = 0.42 * (smooth(2.4, 2.6, t) - smooth(3.9, 4.1, t)) - 0.38 * (smooth(4.6, 4.8, t) - smooth(6.3, 6.5, t));
      let open = 0, bob = 0;
      for (const k of [1.1]) { const u = (t - k) / 0.42; if (u > 0 && u < 1) { open = Math.sin(Math.PI * u); bob = open; } }
      crow.userData.pose({ yaw: h.yaw, pitch: h.pitch - bob * 0.12, roll, open, fluff: 0.15 + Math.sin(t * 2.4) * 0.03 });
      crow.position.y = Math.sin(t * 2.4) * 0.002;
      W.city.userData.update(t);
    },
  };
  return S;
}
