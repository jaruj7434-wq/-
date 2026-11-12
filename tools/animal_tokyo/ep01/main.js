// レンダラー・ポストエフェクト・テロップ／字幕・地図カード
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { BokehPass } from 'three/addons/postprocessing/BokehPass.js';
import { shotO1, shotO2, shotO3, shotX1 } from './shots_open.js';
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

const builders = { o1: shotO1, o2: shotO2, o3: shotO3, x1: shotX1, c1: shotC1, c2: shotC2, c3: shotC3, c4: shotC4, c5: shotC5, d1: shotD1, d2: shotD2, d3: shotD3, d4: shotD4, d5: shotD5, c6: shotC6 };
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

// ---------------------------------------------------------------- 第7カット：地図と豆知識（模式図）
const paper = (() => {
  const c = document.createElement('canvas'); c.width = W; c.height = H; const g = c.getContext('2d');
  const gr = g.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, '#16181d'); gr.addColorStop(1, '#0d0e11'); g.fillStyle = gr; g.fillRect(0, 0, W, H);
  const r = rng(3);
  for (let i = 0; i < 30000; i++) { g.fillStyle = `rgba(255,255,255,${r() * 0.035})`; g.fillRect(r() * W, r() * H, 1, 1); }
  // 街路の格子（模式）
  g.strokeStyle = 'rgba(255,255,255,0.05)'; g.lineWidth = 2;
  for (let i = 0; i < 26; i++) { g.beginPath(); g.moveTo(-50 + i * 40 + r() * 20, 0); g.lineTo(-150 + i * 40 + r() * 40, H); g.stroke(); }
  for (let i = 0; i < 40; i++) { g.beginPath(); g.moveTo(0, i * 36 + r() * 20); g.lineTo(W, i * 36 + 60 + r() * 30); g.stroke(); }
  return c;
})();

function blob(cx, cy, rx, ry, seed) {
  const r = rng(seed); const p = new Path2D(); const n = 28;
  const pts = [];
  for (let i = 0; i < n; i++) { const a = i / n * Math.PI * 2; const k = 0.85 + r() * 0.25; pts.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]); }
  p.moveTo((pts[0][0] + pts[n - 1][0]) / 2, (pts[0][1] + pts[n - 1][1]) / 2);
  for (let i = 0; i < n; i++) { const a = pts[i], b = pts[(i + 1) % n]; p.quadraticCurveTo(a[0], a[1], (a[0] + b[0]) / 2, (a[1] + b[1]) / 2); }
  return p;
}
const meiji = blob(300, 360, 150, 190, 8), yoyogi = blob(205, 600, 95, 85, 9);
const route = [[300, 380], [360, 520], [430, 640], [500, 760], [540, 850]];
function routePoint(u) {
  const segs = route.length - 1; const f = clamp(u) * segs; const i = Math.min(segs - 1, Math.floor(f)); const k = f - i;
  return [route[i][0] + (route[i + 1][0] - route[i][0]) * k, route[i][1] + (route[i + 1][1] - route[i][1]) * k];
}

function drawMap(lt) {
  g2.drawImage(paper, 0, 0);
  const a0 = smooth(0, 0.5, lt);
  g2.save(); g2.globalAlpha = a0;
  // 山手線（模式）
  g2.strokeStyle = '#8fbf3f'; g2.lineWidth = 7; g2.setLineDash([]);
  g2.beginPath(); g2.moveTo(500, 60); g2.bezierCurveTo(480, 300, 470, 520, 560, 880); g2.lineTo(600, 1200); g2.stroke();
  g2.fillStyle = '#26462a'; g2.fill(meiji); g2.strokeStyle = '#4f8a52'; g2.lineWidth = 3; g2.stroke(meiji);
  g2.fillStyle = '#22402a'; g2.fill(yoyogi); g2.strokeStyle = '#3f7044'; g2.stroke(yoyogi);
  // 駅
  for (const [x, y, name, dx] of [[478, 400, '原宿駅', 18], [560, 880, '渋谷駅', 18]]) {
    g2.fillStyle = '#fff'; g2.beginPath(); g2.arc(x, y, 10, 0, 7); g2.fill();
    g2.strokeStyle = '#8fbf3f'; g2.lineWidth = 4; g2.stroke();
    g2.restore(); strokeText(name, x + dx, y + 9, 26, { align: 'left', sw: 5, alpha: a0, bold: false }); g2.save(); g2.globalAlpha = a0;
  }
  g2.restore();
  strokeText('明治神宮', 300, 345, 34, { alpha: a0, sw: 6 });
  strokeText('（ねぐら）', 300, 385, 24, { alpha: a0, sw: 5, bold: false, fill: '#cfe8c8' });
  strokeText('代々木公園', 205, 610, 22, { alpha: a0 * 0.85, sw: 5, bold: false });
  // ルート
  const u = easeInOut((lt - 0.5) / 2.6);
  if (u > 0) {
    g2.save(); g2.strokeStyle = '#ffd24a'; g2.lineWidth = 6; g2.setLineDash([14, 12]); g2.lineDashOffset = -lt * 40;
    g2.beginPath(); g2.moveTo(route[0][0], route[0][1]);
    const N = 60; for (let i = 1; i <= N * u; i++) { const p = routePoint(i / N); g2.lineTo(p[0], p[1]); }
    g2.stroke(); g2.restore();
    const p = routePoint(u);
    // カラスのアイコン（シルエット）
    g2.save(); g2.translate(p[0], p[1]); g2.fillStyle = '#0a0a0c'; g2.strokeStyle = '#ffd24a'; g2.lineWidth = 3;
    const fl = Math.sin(lt * 18) * 8;
    g2.beginPath(); g2.moveTo(-34, -6 - fl); g2.quadraticCurveTo(-14, -4, 0, 6); g2.quadraticCurveTo(14, -4, 34, -6 - fl); g2.quadraticCurveTo(14, 4, 0, 14); g2.quadraticCurveTo(-14, 4, -34, -6 - fl); g2.fill(); g2.stroke();
    g2.restore();
  }
  const a2 = smooth(2.8, 3.3, lt);
  strokeText('エサ場（路地のごみ置き場）', 545, 805, 24, { alpha: a2, sw: 5, bold: false, fill: '#ffe08a' });
  strokeText('※ 位置関係は模式図です', 40, 1240, 20, { align: 'left', alpha: a0 * 0.7, sw: 4, bold: false });

  // 豆知識パネル
  const b = smooth(4.0, 4.5, lt);
  if (b > 0) {
    g2.save(); g2.globalAlpha = b * 0.92; g2.fillStyle = '#0b0c0f'; g2.fillRect(0, 0, W, H); g2.restore();
    const y0 = 360 + (1 - easeOut((lt - 4.0) / 0.6)) * 40;
    strokeText('都内のカラスの生息数', W / 2, y0, 36, { alpha: b, sw: 6 });
    const grow = easeOut((lt - 4.5) / 1.2);
    const maxH = 380, bw = 150, baseY = y0 + 480;
    const bars = [{ x: 210, h: maxH, label: '2001年度', val: '3万〜3.5万羽', col: '#8a8f99' }, { x: 510, h: maxH * 0.2 * grow + maxH * (1 - grow), label: '令和6年度まで', val: '約8割減', col: '#e8463c' }];
    for (const bar of bars) {
      g2.save(); g2.globalAlpha = b; g2.fillStyle = bar.col; g2.fillRect(bar.x - bw / 2, baseY - bar.h, bw, bar.h); g2.restore();
      strokeText(bar.label, bar.x, baseY + 44, 26, { alpha: b, sw: 5, bold: false });
      strokeText(bar.val, bar.x, baseY - bar.h - 18, 32, { alpha: b * (bar.col === '#e8463c' ? smooth(5.2, 5.6, lt) : 1), sw: 6 });
    }
    strokeText('出典：東京都環境局（日本野鳥の会東京支部等の調査をもとにした推計）', W / 2, 1150, 18, { alpha: b * 0.8, sw: 4, bold: false });
    strokeText('棒の高さはイメージです', W / 2, 1180, 18, { alpha: b * 0.6, sw: 4, bold: false });
  }
}

// ---------------------------------------------------------------- 1コマ描画
window.renderAt = (t) => {
  const shot = TL.shots.find((s) => t >= s.start && t < s.start + s.dur) || TL.shots[TL.shots.length - 1];
  const lt = t - shot.start;
  if (shot.id === 'c7') {
    drawMap(lt);
  } else {
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
