// ゆびさき工房サイトの画像(作品サムネイルと SNS シェア用画像)を、実際のゲーム画面から作る。
// 先に python3 tools/build_site.py を実行しておくこと。
// 使い方:  node tools/capture_site_thumbs.js
// 出力:    site/img/<slug>.jpg(3:4)、site/img/og.jpg(1200x630)
//
// three.js の読み込みに CDN が使えない環境では、環境変数 THREE_DIR に
// npm の three パッケージのフォルダを指定すると、そこから読み込む。
const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SITE = path.join(ROOT, 'site');
const FONTS = path.join(ROOT, 'assets', 'source', 'fonts');
const THREE_DIR = process.env.THREE_DIR || '';
const wait = ms => new Promise(r => setTimeout(r, ms));

const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'application/javascript', '.jpg': 'image/jpeg', '.png': 'image/png', '.svg': 'image/svg+xml', '.woff2': 'font/woff2' };
function serve() {
  const srv = http.createServer((req, res) => {
    const p = path.join(SITE, decodeURIComponent(req.url.split('?')[0]));
    if (!p.startsWith(SITE) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
    fs.createReadStream(p).pipe(res);
  });
  return new Promise(r => srv.listen(0, '127.0.0.1', () => r(srv)));
}

// フォントと three.js を手元のファイルで差し替える(ネットに出られない環境用)
async function localRoutes(page) {
  const faces = [['Dela Gothic One', 'DelaGothicOne-Regular.ttf', 400], ['Zen Maru Gothic', 'ZenMaruGothic-Bold.ttf', 700], ['Zen Maru Gothic', 'ZenMaruGothic-Bold.ttf', 500], ['DotGothic16', 'DotGothic16-Regular.ttf', 400]];
  await page.route(/fonts\.googleapis\.com\/css2/, route => route.fulfill({ contentType: 'text/css', body: faces.filter(f => fs.existsSync(path.join(FONTS, f[1]))).map(([fam, file, w]) => `@font-face{font-family:"${fam}";font-weight:${w};src:url(https://fonts.gstatic.com/local/${file}) format("truetype");}`).join('\n') }));
  await page.route(/fonts\.gstatic\.com\/local\//, route => { const f = path.join(FONTS, route.request().url().split('/local/')[1]); fs.existsSync(f) ? route.fulfill({ contentType: 'font/ttf', body: fs.readFileSync(f) }) : route.abort(); });
  if (THREE_DIR) await page.route(/cdn\.jsdelivr\.net\/npm\/three@0\.160\.0\//, route => { const f = path.join(THREE_DIR, route.request().url().split('three@0.160.0/')[1]); fs.existsSync(f) ? route.fulfill({ contentType: 'application/javascript', body: fs.readFileSync(f) }) : route.abort(); });
}

(async () => {
  const srv = await serve();
  const base = `http://127.0.0.1:${srv.address().port}`;
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--ignore-gpu-blocklist'] });
  const errors = [];
  const open = async (url, vp) => {
    const p = await browser.newPage({ viewport: vp || { width: 360, height: 640 }, deviceScaleFactor: 2 });
    p.on('pageerror', e => errors.push(String(e)));
    await localRoutes(p);
    await p.goto(base + url);
    await p.evaluate(() => document.fonts.ready);
    await wait(2500);
    return p;
  };

  // たこ焼き返し:焼いている途中の鉄板
  {
    const p = await open('/play/takoyaki/index.html?capture');
    await p.addStyleTag({ content: '.mini, .yk-home, #stepUi { display: none !important; }' });
    await p.evaluate(() => window.__capture.skip('cook'));
    await wait(3000);
    const t0 = Date.now();
    while (Date.now() - t0 < 240000) {
      const balls = await p.evaluate(() => window.__capture.balls());
      for (const [i, b] of balls.entries()) if (b.st === 'side1' && b.c >= 0.72 && i % 3 !== 2) await p.mouse.click(b.x, b.y);
      if (balls.filter(b => b.st === 'side2').length >= 6 && balls.some(b => b.st === 'side2' && b.c > 0.3)) break;
      await wait(80);
    }
    await wait(1600);   // 「きつね色!」などの表示が消えるのを待つ
    await p.screenshot({ path: path.join(SITE, 'img', 'takoyaki.jpg'), type: 'jpeg', quality: 85, clip: { x: 36, y: 128, width: 288, height: 384 } });
    await p.close();
  }
  // 弾丸の調合師:敵と弾でにぎやかな瞬間
  {
    const p = await open('/play/bullet-alchemist/index.html?capture');
    await p.addStyleTag({ content: '.ctl, .yk-home { display: none !important; }' });
    await p.evaluate(() => window.__capture.setLang('ja'));
    await p.evaluate(() => window.__capture.run({ split: 2, fork: 1, chain: 1, blast: 1 }, 5));
    let dir = 'ArrowLeft';
    for (let i = 0; i < 120; i++) {
      await p.keyboard.down(dir); await wait(400); await p.keyboard.up(dir); dir = dir === 'ArrowLeft' ? 'ArrowRight' : 'ArrowLeft';
      const c = await p.evaluate(() => window.__capture.counts());
      if (c.en >= 6 && c.eb >= 6) break;
    }
    await p.locator('#stage').screenshot({ path: path.join(ROOT, 'dist', 'tmp_ba.png') });
    const box = await p.locator('#stage').boundingBox();
    await p.screenshot({ path: path.join(SITE, 'img', 'bullet-alchemist.jpg'), type: 'jpeg', quality: 85, clip: { x: box.x, y: box.y + box.height * 0.12, width: box.width, height: box.width * 4 / 3 } });
    await p.close();
  }
  // ソフトクリーム巻き:自動で巻いて、できあがる直前
  {
    const p = await open('/play/softcream/index.html?capture');
    await p.addStyleTag({ content: '.mini, .yk-home, #doneUi { display: none !important; } #cv { opacity: 0; }' });
    await p.evaluate(() => window.__capture.play(true));
    const t0 = Date.now();
    while (Date.now() - t0 < 400000) {
      const info = await p.evaluate(() => window.__capture.info());
      if (info.H >= info.order.cm - 0.6) break;
      await wait(300);
    }
    await p.screenshot({ path: path.join(SITE, 'img', 'softcream.jpg'), type: 'jpeg', quality: 85, clip: { x: 0, y: 110, width: 360, height: 480 } });
    await p.close();
  }
  // SNS シェア用(1200x630)
  {
    const p = await browser.newPage({ viewport: { width: 1200, height: 630 } });
    await localRoutes(p);
    await p.goto(base + '/index.html');
    await p.setContent(`<!doctype html><html><head><meta charset="utf-8"><base href="${base}/">
      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Zen+Maru+Gothic:wght@700&display=swap">
      <style>body{margin:0;width:1200px;height:630px;background:#121318;color:#f1ece2;font-family:"Zen Maru Gothic";display:flex;align-items:center;gap:56px;padding:0 70px;box-sizing:border-box;overflow:hidden;
      background:radial-gradient(ellipse 60% 70% at 85% 30%,rgba(242,181,68,.16),transparent 70%),#121318}
      .t{flex:1}.mark{width:84px;height:84px;color:#f2b544}.b{font:400 78px/1.1 "Dela Gothic One";margin:18px 0 0;white-space:nowrap}.s{font-size:30px;margin-top:22px;color:#cfc9bd}
      .imgs{display:flex;gap:22px;align-items:center}.imgs img{width:230px;height:307px;object-fit:cover;border-radius:16px;border:2px solid rgba(255,255,255,.12)}.imgs img:first-child{transform:rotate(-3deg)}.imgs img:last-child{transform:rotate(3deg) translateY(20px)}</style></head>
      <body><div class="t"><svg class="mark" viewBox="0 0 40 40"><circle cx="20" cy="20" r="6" fill="currentColor"/><circle cx="20" cy="20" r="12" fill="none" stroke="currentColor" stroke-width="2.5" opacity=".55"/><circle cx="20" cy="20" r="18" fill="none" stroke="currentColor" stroke-width="2" opacity=".25"/></svg>
      <div class="b">ゆびさき工房</div><div class="s">指先ひとつで遊べる、<br>ちいさな手しごとのゲーム。</div></div>
      <div class="imgs"><img src="img/softcream.jpg"><img src="img/takoyaki.jpg"></div></body></html>`);
    await p.evaluate(() => document.fonts.ready);
    await wait(800);
    await p.screenshot({ path: path.join(SITE, 'img', 'og.jpg'), type: 'jpeg', quality: 85 });
    await p.close();
  }
  await browser.close();
  srv.close();
  fs.rmSync(path.join(ROOT, 'dist', 'tmp_ba.png'), { force: true });
  console.log('done', fs.readdirSync(path.join(SITE, 'img')).join(' '), 'errors:', errors);
})();
