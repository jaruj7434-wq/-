// 「Bullet Alchemist」の投稿用メディア(スクリーンショット・カバー画像・紹介動画)を作る。
// 先に python3 tools/build_chougoushi.py でビルドしておくこと。
// 使い方:  node tools/capture_chougoushi.js
// 出力先:  dist/media/
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const GAME = 'file://' + path.join(ROOT, 'dist', 'bullet-alchemist', 'index.html') + '?capture';
const FONT = 'file://' + path.join(ROOT, 'dist', 'bullet-alchemist', 'fonts', 'DotGothic16-subset.woff2');
const OUT = path.join(ROOT, 'dist', 'media');
const TMP = path.join(OUT, 'tmp');
fs.mkdirSync(TMP, { recursive: true });

const MID = { split: 2, fork: 1, chain: 1, blast: 1 };
const BOSS = { split: 3, rapid: 2, heavy: 1, fork: 2, chain: 2, blast: 2, homing: 1 };
const wait = ms => new Promise(r => setTimeout(r, ms));

// 自機を中央付近で左右に揺らし続ける(撮影用の簡単な操縦)
let wiggleDir = 'ArrowLeft';
async function wiggle(page, ms) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    await page.keyboard.down(wiggleDir);
    await wait(450);
    await page.keyboard.up(wiggleDir);
    wiggleDir = wiggleDir === 'ArrowLeft' ? 'ArrowRight' : 'ArrowLeft';
  }
}

async function openGame(browser, opts) {
  const page = await browser.newPage(opts);
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  // 外部への通信が一切ないことを確かめる(投稿サイトでの動作を想定)
  await page.route(/^https?:\/\//, route => { errors.push('external request: ' + route.request().url()); route.abort(); });
  await page.goto(GAME);
  await page.evaluate(() => document.fonts.ready);
  await wait(800);
  await page.evaluate(() => window.__capture.setLang('en'));
  return { page, errors };
}

async function screenshots(browser) {
  const { page, errors } = await openGame(browser, { viewport: { width: 360, height: 640 }, deviceScaleFactor: 3 });
  const shot = name => page.locator('#stage').screenshot({ path: path.join(OUT, name) });
  await shot('screenshot-1-title.png');
  await page.evaluate(r => window.__capture.draft(r, 2), { split: 1, fork: 1 });
  await wait(300);
  await shot('screenshot-2-pick-parts.png');
  // 敵や弾が画面ににぎやかに映っている瞬間を待って撮る
  const busy = async (cond, maxMs) => {
    const end = Date.now() + maxMs;
    while (Date.now() < end) {
      await wiggle(page, 400);
      const c = await page.evaluate(() => window.__capture.counts());
      if (cond(c)) return;
    }
  };
  await page.addStyleTag({ content: '.ctl { display: none !important; }' });   // 撮影では右上のボタンを隠す
  await page.evaluate(r => window.__capture.run(r, 5), MID);
  await wiggle(page, 3000);
  await busy(c => c.en >= 6 && c.eb >= 6, 40000);
  await shot('screenshot-3-gameplay.png');
  await page.evaluate(r => window.__capture.run(r, 6), BOSS);
  await busy(c => c.boss && c.eb >= 25, 20000);
  await shot('screenshot-4-boss.png');
  await page.close();
  return errors;
}

async function covers(browser) {
  const img = n => 'file://' + path.join(OUT, n);
  const base = `
    <style>
      @font-face { font-family: DG; src: url("${FONT}") format("woff2"); }
      * { margin: 0; box-sizing: border-box; }
      body { background: #0a0b1e; color: #eceeff; font-family: DG, monospace; overflow: hidden; }
      .t1 { color: #b78cff; letter-spacing: 0.12em; }
      .t2 { color: #5ef2d6; line-height: 1; }
      .shot { display: block; border: 2px solid rgba(94, 242, 214, 0.35); box-shadow: 0 0 60px rgba(183, 140, 255, 0.25); }
      .chips { display: flex; flex-wrap: wrap; gap: 10px; }
      .chips span { background: #161a42; border-left: 4px solid var(--c); padding: 6px 12px; }
    </style>`;
  const chips = `<div class="chips"><span style="--c:#5ef2d6">Split</span><span style="--c:#8fd3ff">Chain</span><span style="--c:#ff8a4c">Blast</span><span style="--c:#5ef2d6">Fork</span><span style="--c:#b78cff">Homing</span></div>`;
  const pages = {
    'cover-landscape-1920x1080.png': [1920, 1080, `
      <div style="display:flex;align-items:center;height:1080px;padding:0 100px 0 110px;gap:56px">
        <div style="flex:1">
          <div class="t1" style="font-size:60px">BULLET</div>
          <div class="t2" style="font-size:132px">ALCHEMIST</div>
          <div style="font-size:38px;margin:40px 0 36px;opacity:.9">Brew your own bullets.<br>Pick 1 of 3 parts every wave.</div>
          <div style="font-size:30px">${chips}</div>
        </div>
        <img class="shot" src="${img('screenshot-3-gameplay.png')}" style="height:900px">
        <img class="shot" src="${img('screenshot-4-boss.png')}" style="height:760px;opacity:.92">
      </div>`],
    'cover-portrait-800x1200.png': [800, 1200, `
      <img src="${img('screenshot-3-gameplay.png')}" style="position:absolute;inset:0;width:800px;height:1200px;object-fit:cover;object-position:center 60%">
      <div style="position:absolute;inset:0 0 auto;height:520px;background:linear-gradient(#0a0b1e 45%, rgba(10,11,30,0))"></div>
      <div style="position:absolute;top:70px;width:100%;text-align:center">
        <div class="t1" style="font-size:48px">BULLET</div>
        <div class="t2" style="font-size:104px">ALCHEMIST</div>
        <div style="font-size:30px;margin-top:22px">Brew your own bullets.</div>
      </div>`],
    'cover-square-800x800.png': [800, 800, `
      <img src="${img('screenshot-3-gameplay.png')}" style="position:absolute;inset:0;width:800px;height:800px;object-fit:cover;object-position:center 70%">
      <div style="position:absolute;inset:0 0 auto;height:400px;background:linear-gradient(#0a0b1e 50%, rgba(10,11,30,0))"></div>
      <div style="position:absolute;top:60px;width:100%;text-align:center">
        <div class="t1" style="font-size:44px">BULLET</div>
        <div class="t2" style="font-size:100px">ALCHEMIST</div>
      </div>`],
    'cover-itch-630x500.png': [630, 500, `
      <div style="display:flex;align-items:center;height:500px;padding:0 36px;gap:28px">
        <div style="flex:1">
          <div class="t1" style="font-size:26px">BULLET</div>
          <div class="t2" style="font-size:52px">ALCHEMIST</div>
          <div style="font-size:18px;margin:18px 0;opacity:.9">Brew your own bullets.</div>
          <div style="font-size:14px">${chips}</div>
        </div>
        <img class="shot" src="${img('screenshot-3-gameplay.png')}" style="height:440px">
      </div>`],
  };
  for (const [name, [w, h, body]] of Object.entries(pages)) {
    // file:// の画像とフォントを読めるよう、いったんファイルに書き出して開く
    const htmlPath = path.join(TMP, name + '.html');
    fs.writeFileSync(htmlPath, `<!doctype html><html><head><meta charset="utf-8">${base}</head><body style="width:${w}px;height:${h}px;position:relative">${body}</body></html>`);
    const page = await browser.newPage({ viewport: { width: w, height: h } });
    await page.goto('file://' + htmlPath);
    await page.waitForLoadState('load');
    await page.evaluate(() => document.fonts.ready);
    await wait(300);
    await page.screenshot({ path: path.join(OUT, name) });
    await page.close();
  }
}

async function video(browser) {
  const ctx = await browser.newContext({ viewport: { width: 540, height: 960 }, recordVideo: { dir: TMP, size: { width: 540, height: 960 } } });
  const page = await ctx.newPage();
  const t0 = Date.now();
  await page.route(/^https?:\/\//, route => route.abort());
  await page.goto(GAME);
  await page.evaluate(() => document.fonts.ready);
  await wait(800);
  await page.evaluate(() => window.__capture.setLang('en'));
  await page.evaluate(r => window.__capture.draft(r, 3), { split: 2, rapid: 1, fork: 1, chain: 1, blast: 1 });
  await page.addStyleTag({ content: '.ctl { display: none !important; }' });
  const start = (Date.now() - t0) / 1000;
  await wait(2500);
  await page.keyboard.press('Digit1');
  await wiggle(page, 18000);
  const vpath = await page.video().path();
  await ctx.close();

  const portrait = path.join(OUT, 'preview-portrait-1080x1920.mp4');
  const landscape = path.join(OUT, 'preview-landscape-1920x1080.mp4');
  const common = ['-y', '-ss', start.toFixed(2), '-t', '20', '-i', vpath, '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', '30', '-crf', '20', '-movflags', '+faststart'];
  execFileSync('ffmpeg', [...common.slice(0, 7), '-vf', 'scale=1080:1920:flags=lanczos', ...common.slice(7), portrait], { stdio: 'ignore' });
  execFileSync('ffmpeg', [...common.slice(0, 7), '-filter_complex',
    '[0:v]scale=1920:3413,crop=1920:1080,boxblur=30:3,eq=brightness=-0.25[bg];[0:v]scale=-2:1080:flags=lanczos[fg];[bg][fg]overlay=(W-w)/2:0',
    ...common.slice(7), landscape], { stdio: 'ignore' });
}

(async () => {
  const browser = await chromium.launch();
  const errors = await screenshots(browser);
  await covers(browser);
  await video(browser);
  await browser.close();
  fs.rmSync(TMP, { recursive: true, force: true });
  for (const f of fs.readdirSync(OUT)) console.log(f, (fs.statSync(path.join(OUT, f)).size / 1024).toFixed(0) + ' KB');
  console.log('errors:', errors);
})();
