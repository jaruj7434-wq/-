// 使い方:
//   node ep01/render.js --stills 2,7,12,18,23,27,33 --out <dir>   静止画プレビュー
//   node ep01/render.js --from 0 --to 38 --out <file.mp4>           動画（音なし）を書き出し
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => (v.startsWith('--') ? a.concat([[v.slice(2), arr[i + 1]]]) : a), []));
const TL = JSON.parse(fs.readFileSync(path.join(__dirname, 'timeline.json'), 'utf8'));

const types = { '.js': 'text/javascript', '.html': 'text/html', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': types[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});

(async () => {
  await new Promise((r) => server.listen(0, r));
  const port = server.address().port;
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: TL.width, height: TL.height } });
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.error('[page]', m.text()); });
  page.on('pageerror', (e) => console.error('[pageerror]', e.message));
  await page.goto(`http://localhost:${port}/ep01/index.html`);
  await page.waitForFunction('window.ready === true', null, { timeout: 120000 });
  const grab = async (t) => Buffer.from((await page.evaluate((tt) => window.renderAt(tt), t)).split(',')[1], 'base64');

  if (args.stills) {
    fs.mkdirSync(args.out, { recursive: true });
    for (const s of args.stills.split(',').map(Number)) {
      const t0 = Date.now();
      fs.writeFileSync(path.join(args.out, `still_${String(s).replace('.', '_')}.jpg`), await grab(s));
      console.log(`still ${s}s  ${Date.now() - t0}ms`);
    }
  } else {
    const fps = TL.fps, from = Number(args.from ?? 0), to = Number(args.to ?? TL.duration);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
      '-vf', 'scale=1080:1920:flags=lanczos', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', args.out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const n0 = Math.round(from * fps), n1 = Math.round(to * fps);
    const t0 = Date.now();
    for (let n = n0; n < n1; n++) {
      const buf = await grab(n / fps);
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
      if ((n - n0) % 30 === 0) console.log(`frame ${n}/${n1}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
    ff.stdin.end();
    await new Promise((r) => ff.on('close', r));
  }
  await browser.close(); server.close();
})().catch((e) => { console.error(e); process.exit(1); });
