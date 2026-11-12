// レンダラー・ポストエフェクト・テロップ／字幕・地図カード
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { BokehPass } from 'three/addons/postprocessing/BokehPass.js';
import { shotO1, shotO2, shotO3, shotX1, shotE1 } from './shots_open.js';
import { shotC1, shotC2, shotC3, shotC4, shotC5, shotC6 } from './shots.js';
import { shotD1, shotD2, shotD3, shotD4, shotD5 } from './shots_day.js';
import { clamp, smooth, easeOut, easeInOut, rng } from './lib.js';

const TL = await (await fetch('./timeline.json')).json();
const W = TL.width, H = TL.height;

const out = document.getElementById('out'); out.width = W; out.height = H;
const g2 = out.getContext('2d');

const GradeShader = {
  uniforms: {
    tDiffuse: { value: null }, uTime: { value: 0 }, uVignette: { value: 0.4 }, uGrain: { value: 0.05 }, uSat: { value: 1 }, uContrast: { value: 1 },
    uLift: { value: new THREE.Vector3() }, uGain: { value: new THREE.Vector3(1, 1, 1) }, uBlur: { value: 0 }, uFade: { value: 0 }, uCA: { value: 0.003 },
  },
  vertexShader: 'varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }',
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uTime,uVignette,uGrain,uSat,uContrast,uBlur,uFade,uCA; uniform vec3 uLift,uGain; varying vec2 vUv;
    float hash(vec2 p){ return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
    void main(){ vec2 uv=vUv; vec3 c;
      if(uBlur>0.001){ c=vec3(0.); for(int i=0;i<24;i++){ float o=(float(i)/23.-0.5)*uBlur; c+=texture2D(tDiffuse,uv+vec2(0.,o)).rgb; } c/=24.; }
      else { vec2 d=(uv-0.5)*uCA; c=vec3(texture2D(tDiffuse,uv+d).r, texture2D(tDiffuse,uv).g, texture2D(tDiffuse,uv-d).b); }
      c = c*uGain + uLift*(1.-c);
      float l=dot(c,vec3(0.299,0.587,0.114)); c=mix(vec3(l),c,uSat);
      c=(c-0.5)*uContrast+0.5;
      float v=smoothstep(0.95,0.25,length((uv-0.5)*vec2(1.0,1.35))); c*=mix(1.-uVignette,1.,v);
      float gr=hash(uv*vec2(720.,1280.)+fract(uTime*7.13)*91.7)-0.5; c+=gr*uGrain*(0.6+0.4*(1.-l));
      c*=1.-uFade;
      gl_FragColor=vec4(clamp(c,0.,1.),1.); }`,
};

// 描画パイプライン。通常は対数深度（遠景まで扱う）、外から撮るカットは被写界深度（背景ぼけ）用に通常深度
function makePipe(logDepth, dof) {
  const canvas = document.createElement('canvas'); canvas.width = W; canvas.height = H;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true, logarithmicDepthBuffer: logDepth });
  renderer.setPixelRatio(1); renderer.setSize(W, H, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const composer = new EffectComposer(renderer); composer.setPixelRatio(1); composer.setSize(W, H);
  const renderPass = new RenderPass(new THREE.Scene(), new THREE.PerspectiveCamera());
  composer.addPass(renderPass);
  let bokeh = null;
  if (dof) { bokeh = new BokehPass(new THREE.Scene(), new THREE.PerspectiveCamera(), { focus: 1, aperture: 0.002, maxblur: 0.01 }); composer.addPass(bokeh); }
  const bloom = new UnrealBloomPass(new THREE.Vector2(W / 2, H / 2), 0.6, 0.5, 0.85);
  const grade = new ShaderPass(GradeShader);
  composer.addPass(bloom); composer.addPass(new OutputPass()); composer.addPass(grade);
  return { canvas, renderer, composer, renderPass, bokeh, bloom, grade, pmrem: new THREE.PMREMGenerator(renderer) };
}
const PIPE = makePipe(true, false);
let PIPE_DOF = null;

const builders = { o1: shotO1, o2: shotO2, o3: shotO3, x1: shotX1, c1: shotC1, c2: shotC2, c3: shotC3, c4: shotC4, c5: shotC5, d1: shotD1, d2: shotD2, d3: shotD3, d4: shotD4, d5: shotD5, c6: shotC6, c7: shotE1 };
let current = null, currentId = null;
function getShot(id) {
  if (currentId === id) return current;
  if (current) current.scene.traverse((o) => { if (o.geometry) o.geometry.dispose(); });
  currentId = id;
  const dof = id.startsWith('o');
  if (dof && !PIPE_DOF) PIPE_DOF = makePipe(false, true);
  const P = dof ? PIPE_DOF : PIPE;
  current = builders[id](P.renderer);
  current.pipe = P;
  // 空から環境マップを作り、ガラス・水・羽に映り込ませる
  for (const sc of new Set([current.scene, ...(current.scenes || [])])) {
    if (sc.environment) continue;
    const sky = sc.children.find((o) => o.userData && o.userData.u);
    if (!sky) continue;
    const es = new THREE.Scene(); es.add(sky.clone());
    sc.environment = P.pmrem.fromScene(es, 0, 0.1, 10000).texture;
  }
  return current;
}

// ---------------------------------------------------------------- 文字
const FONT = '"IPAGothic", "IPAPGothic", sans-serif';
function strokeText(text, x, y, size, { align = 'center', fill = '#fff', stroke = 'rgba(0,0,0,0.85)', sw = 7, alpha = 1, bold = true } = {}) {
  g2.save(); g2.globalAlpha = alpha; g2.font = `${size}px ${FONT}`; g2.textAlign = align; g2.textBaseline = 'alphabetic';
  g2.lineJoin = 'round'; g2.strokeStyle = stroke; g2.lineWidth = sw; g2.strokeText(text, x, y);
  g2.fillStyle = fill; g2.fillText(text, x, y);
  if (bold) { g2.strokeStyle = fill; g2.lineWidth = 1.2; g2.strokeText(text, x, y); }
  g2.restore();
}

function drawTelop(shot, lt) {
  if (!shot.time) return;
  const a = smooth(0.15, 0.45, lt) * (1 - smooth(shot.dur - 0.25, shot.dur - 0.05, lt));
  const slide = (1 - easeOut((lt - 0.15) / 0.4)) * -30;
  g2.save(); g2.globalAlpha = a;
  g2.shadowColor = 'rgba(0,0,0,0.6)'; g2.shadowBlur = 10;
  g2.fillStyle = '#e8463c'; g2.fillRect(44 + slide, 92, 6, 82);
  g2.restore();
  strokeText(shot.time, 64 + slide, 146, 58, { align: 'left', sw: 6, alpha: a, stroke: 'rgba(0,0,0,0.55)' });
  strokeText(shot.place, 66 + slide, 178, 26, { align: 'left', sw: 5, alpha: a * 0.95, stroke: 'rgba(0,0,0,0.55)', bold: false });
}

function drawSubs(t) {
  for (const s of TL.subs) {
    if (t < s.start - 0.1 || t > s.end + 0.1) continue;
    const a = smooth(s.start - 0.1, s.start + 0.12, t) * (1 - smooth(s.end - 0.12, s.end + 0.1, t));
    const lines = s.text.split('\n');
    const base = 1000 - (lines.length - 1) * 30;
    lines.forEach((ln, i) => strokeText(ln, W / 2, base + i * 60, 42, { alpha: a, sw: 9 }));
  }
}

function drawTitle(t) {
  const T = TL.title; if (t > T.end + 0.3) return;
  const a = smooth(T.start, T.start + 0.4, t) * (1 - smooth(T.end - 0.3, T.end, t));
  const pop = 1 + (1 - easeOut((t - T.start) / 0.35)) * 0.15;
  g2.save(); g2.translate(W / 2, 400); g2.scale(pop, pop); g2.translate(-W / 2, -400);
  T.lines.forEach((ln, i) => strokeText(ln.text, W / 2, 360 + i * 90, ln.size, { alpha: a, sw: 11, fill: ln.color || '#fff' }));
  g2.restore();
}

// ---------------------------------------------------------------- 説明線（3D の位置に文字を付ける）
function drawLabels(S, lt) {
  for (const L of S.labels(lt)) {
    if (L.alpha <= 0) continue;
    const p = L.pos.clone().project(S.camera);
    const x = (p.x * 0.5 + 0.5) * W, y = (-p.y * 0.5 + 0.5) * H;
    if (L.to) { // 2点を結ぶ寸法線
      const q = L.to.clone().project(S.camera); const x2 = (q.x * 0.5 + 0.5) * W, y2 = (-q.y * 0.5 + 0.5) * H;
      g2.save(); g2.globalAlpha = L.alpha; g2.strokeStyle = '#ffd24a'; g2.lineWidth = 3; g2.setLineDash([]);
      const k = L.grow ?? 1;
      g2.beginPath(); g2.moveTo(x, y); g2.lineTo(x + (x2 - x) * k, y + (y2 - y) * k); g2.stroke();
      for (const [px, py] of [[x, y], [x + (x2 - x) * k, y + (y2 - y) * k]]) { g2.beginPath(); g2.arc(px, py, 5, 0, 7); g2.fillStyle = '#ffd24a'; g2.fill(); }
      g2.restore();
      strokeText(L.text, (x + x2) / 2 + (L.dx || 0), (y + y2) / 2 + (L.dy || 0), 32, { alpha: L.alpha * smooth(0.6, 1, k), sw: 7, fill: '#ffd24a' });
      continue;
    }
    if (L.box) { // 顔の枠
      const s = L.box / Math.max(0.1, p.z > 1 ? 1 : 1) ;
      g2.save(); g2.globalAlpha = L.alpha; g2.strokeStyle = L.color || '#7fe07f'; g2.lineWidth = 3;
      const b = L.size || 34;
      for (const [sx, sy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) { g2.beginPath(); g2.moveTo(x + sx * b, y + sy * b * 0.6); g2.lineTo(x + sx * b, y + sy * b); g2.lineTo(x + sx * b * 0.6, y + sy * b); g2.stroke(); }
      g2.restore();
      if (L.text) strokeText(L.text, x, y - b - 10, 24, { alpha: L.alpha, sw: 5, fill: L.color || '#7fe07f' });
      continue;
    }
    const lx = x + (L.dx || 120), ly = y + (L.dy || -80);
    g2.save(); g2.globalAlpha = L.alpha; g2.strokeStyle = '#fff'; g2.lineWidth = 2.5;
    g2.beginPath(); g2.arc(x, y, 6, 0, 7); g2.stroke();
    g2.beginPath(); g2.moveTo(x, y); g2.lineTo(lx, ly); g2.lineTo(lx + (L.dx > 0 ? 20 : -20), ly); g2.stroke(); g2.restore();
    strokeText(L.text, lx + (L.dx > 0 ? 26 : -26), ly + 11, 30, { align: L.dx > 0 ? 'left' : 'right', alpha: L.alpha, sw: 7 });
  }
}

// ---------------------------------------------------------------- 豆知識チップ
function roundRect(x, y, w, h, r) { g2.beginPath(); g2.moveTo(x + r, y); g2.arcTo(x + w, y, x + w, y + h, r); g2.arcTo(x + w, y + h, x, y + h, r); g2.arcTo(x, y + h, x, y, r); g2.arcTo(x, y, x + w, y, r); g2.closePath(); }
function drawTips(t) {
  for (const tp of TL.tips || []) {
    if (t < tp.start - 0.1 || t > tp.end + 0.1) continue;
    const a = smooth(tp.start, tp.start + 0.25, t) * (1 - smooth(tp.end - 0.25, tp.end, t));
    const slide = (1 - easeOut((t - tp.start) / 0.35)) * 40;
    const lines = tp.text.split('\n');
    const y0 = tp.y ?? 230, x0 = 40 + slide, w = W - 80, h = 64 + lines.length * 40 + (tp.src ? 26 : 0);
    g2.save(); g2.globalAlpha = a * 0.82; g2.fillStyle = '#101216'; roundRect(x0, y0, w, h, 18); g2.fill();
    g2.globalAlpha = a; g2.fillStyle = '#ffd24a'; roundRect(x0, y0, 150, 40, 14); g2.fill(); g2.restore();
    strokeText('豆知識', x0 + 75, y0 + 30, 26, { alpha: a, sw: 0, fill: '#101216', stroke: 'rgba(0,0,0,0)', bold: false });
    lines.forEach((ln, i) => strokeText(ln, x0 + 24, y0 + 84 + i * 40, 30, { align: 'left', alpha: a, sw: 4, bold: false }));
    if (tp.src) strokeText('出典：' + tp.src, x0 + 24, y0 + h - 14, 17, { align: 'left', alpha: a * 0.75, sw: 0, stroke: 'rgba(0,0,0,0)', bold: false, fill: '#bfc3c9' });
  }
}

// ---------------------------------------------------------------- 第7カット：エンディング（コメントのお願い）

// エンディング：視聴者にコメントをうながす
function drawCTA(lt) {
  const a = smooth(0.4, 0.9, lt);
  if (a <= 0) return;
  const grd = g2.createLinearGradient(0, 640, 0, H);
  grd.addColorStop(0, 'rgba(0,0,0,0)'); grd.addColorStop(0.35, `rgba(0,0,0,${0.55 * a})`); grd.addColorStop(1, `rgba(0,0,0,${0.75 * a})`);
  g2.fillStyle = grd; g2.fillRect(0, 640, W, H - 640);
  const pop = (t0) => { const u = clamp((lt - t0) / 0.35); return u <= 0 ? 0 : 1 + 0.18 * Math.sin(Math.PI * u) * (1 - u); };
  const q = pop(0.5);
  if (q > 0) {
    g2.save(); g2.translate(W / 2, 830); g2.scale(q, q);
    strokeText('次はどの動物の', 0, 0, 56, { sw: 9, alpha: a });
    strokeText('目線で見たい？', 0, 72, 56, { sw: 9, alpha: a, fill: '#ffd24a' });
    g2.restore();
  }
  const opts = ['ネコ', 'ハト', 'タヌキ', 'スズメ'];
  opts.forEach((txt, i) => {
    const s = pop(1.5 + i * 0.3); if (s <= 0) return;
    const x = 130 + (i % 2) * 230, y = 980 + Math.floor(i / 2) * 92;
    g2.save(); g2.translate(x + 100, y + 34); g2.scale(s, s); g2.translate(-(x + 100), -(y + 34));
    g2.globalAlpha = a * 0.92; g2.fillStyle = 'rgba(255,255,255,0.95)'; roundRect(x, y, 200, 68, 34); g2.fill();
    g2.globalAlpha = a; g2.fillStyle = '#16181d'; g2.font = `38px ${FONT}`; g2.textAlign = 'center'; g2.fillText(txt, x + 100, y + 48);
    g2.restore();
  });
  // コメント欄へうながす（吹き出し＋上下にゆれる矢印）
  const b = smooth(3.0, 3.4, lt);
  if (b > 0) {
    const yy = 1215 + Math.sin(lt * 5) * 6;
    g2.save(); g2.globalAlpha = b; g2.fillStyle = '#ffd24a';
    const bx = 150, by = yy - 44; roundRect(bx, by, 64, 46, 12); g2.fill();
    g2.beginPath(); g2.moveTo(bx + 14, by + 44); g2.lineTo(bx + 10, by + 60); g2.lineTo(bx + 30, by + 44); g2.fill();
    g2.fillStyle = '#16181d'; for (let k = 0; k < 3; k++) { g2.beginPath(); g2.arc(bx + 18 + k * 14, by + 23, 4.5, 0, 7); g2.fill(); }
    g2.restore();
    strokeText('コメントで教えてね！', 236, yy, 44, { align: 'left', sw: 8, alpha: b });
  }
}

// ---------------------------------------------------------------- 1コマ描画
window.renderAt = (t) => {
  const shot = TL.shots.find((s) => t >= s.start && t < s.start + s.dur) || TL.shots[TL.shots.length - 1];
  const lt = t - shot.start;
  {
    const S = getShot(shot.id);
    S.update(lt);
    const P = S.pipe;
    P.renderPass.scene = S.scene; P.renderPass.camera = S.camera;
    if (P.bokeh) {
      P.bokeh.scene = S.scene; P.bokeh.camera = S.camera;
      const D = S.dof || { focus: 1, aperture: 0, maxblur: 0 };
      P.bokeh.uniforms.focus.value = D.focus; P.bokeh.uniforms.aperture.value = D.aperture; P.bokeh.uniforms.maxblur.value = D.maxblur;
      P.bokeh.uniforms.nearClip.value = S.camera.near; P.bokeh.uniforms.farClip.value = S.camera.far; P.bokeh.uniforms.aspect.value = S.camera.aspect;
    }
    P.renderer.toneMappingExposure = S.exposure ?? 1;
    const B = S.bloom; P.bloom.strength = B.strength; P.bloom.radius = B.radius; P.bloom.threshold = B.threshold;
    const G = S.grade, u = P.grade.uniforms;
    u.uTime.value = t; u.uVignette.value = G.vignette; u.uGrain.value = G.grain; u.uSat.value = G.sat; u.uContrast.value = G.contrast;
    u.uLift.value.set(...G.lift); u.uGain.value.set(...G.gain); u.uBlur.value = G.blur || 0;
    // カット間は一瞬だけ暗くつなぐ（first は黒からフェードイン）
    const edge = Math.min(lt, shot.dur - lt);
    u.uFade.value = (shot === TL.shots[0] ? (1 - smooth(0, 0.5, lt)) : 0) + (shot.noFade ? 0 : clamp(1 - edge / 0.1) * 0.85);
    P.composer.render();
    g2.drawImage(P.canvas, 0, 0);
    if (shot.flashIn) { const f = 1 - smooth(0, 0.45, lt); if (f > 0) { g2.fillStyle = `rgba(255,255,255,${f})`; g2.fillRect(0, 0, W, H); } }
    if (S.flash) { const f = S.flash(lt); if (f > 0) { g2.fillStyle = `rgba(255,255,255,${f})`; g2.fillRect(0, 0, W, H); } }
    if (S.labels) drawLabels(S, lt);
    if (shot.id === 'c7') drawCTA(lt);
  }
  drawTelop(shot, lt);
  drawTitle(t);
  drawTips(t);
  drawSubs(t);
  if (t > TL.duration - 0.5) { g2.fillStyle = `rgba(0,0,0,${smooth(TL.duration - 0.5, TL.duration, t)})`; g2.fillRect(0, 0, W, H); }
  return out.toDataURL('image/jpeg', 0.93);
};

await document.fonts.load(`40px ${FONT}`);
window.ready = true;
