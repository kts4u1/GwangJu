// 장면 렌더러
//   node render.js stills 10 30.5 ...   → build/stills/*.jpg (지정한 초의 정지 화면)
//   node render.js video [workers]      → build/video.mp4 (무음, 1920x1080 30fps)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const { once } = require('events');
const path = require('path'), fs = require('fs');

const FPS = 30;
const BUILD = path.join(__dirname, 'build');
const timeline = JSON.parse(fs.readFileSync(path.join(BUILD, 'timeline.json'), 'utf8'));

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => m.type() === 'error' && errors.push(m.text()));
  await page.goto('file://' + path.join(__dirname, 'scene.html'));
  const text = await page.evaluate(tl => window.init(tl), timeline);
  await page.evaluate(async text => {
    for (const w of [400, 500, 600, 700, 800, 900]) await document.fonts.load(`${w} 40px P`, text);
    await document.fonts.ready;
  }, text);
  return { page, errors };
}

async function frame(page, t) {
  await page.evaluate(t => window.renderAt(t), t);
  return page.screenshot({ type: 'jpeg', quality: 95 });
}

async function renderRange(browser, from, to, out, label) {
  const { page, errors } = await openPage(browser);
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', String(FPS), out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = from; i < to; i++) {
    const buf = await frame(page, i / FPS);
    if (!ff.stdin.write(buf)) await once(ff.stdin, 'drain');
    if ((i - from) % 300 === 0) console.log(`${label}: ${i - from}/${to - from}`);
  }
  ff.stdin.end();
  const [code] = await once(ff, 'close');
  if (code !== 0) throw new Error('ffmpeg failed for ' + out);
  await page.close();
  return errors;
}

(async () => {
  const mode = process.argv[2] || 'stills';
  const browser = await chromium.launch();
  let errors = [];
  if (mode === 'stills') {
    const dir = path.join(BUILD, 'stills');
    fs.mkdirSync(dir, { recursive: true });
    const { page, errors: e } = await openPage(browser);
    for (const a of process.argv.slice(3)) {
      fs.writeFileSync(path.join(dir, `t${String(a).padStart(6, '0')}.jpg`), await frame(page, parseFloat(a)));
    }
    errors = e;
  } else {
    const workers = parseInt(process.argv[3] || '3', 10);
    const n = Math.round(timeline.total * FPS), per = Math.ceil(n / workers);
    const segs = [];
    const jobs = [];
    for (let w = 0; w < workers; w++) {
      const out = path.join(BUILD, `seg${w}.mp4`);
      segs.push(out);
      jobs.push(renderRange(browser, w * per, Math.min(n, (w + 1) * per), out, `worker ${w}`));
    }
    errors = (await Promise.all(jobs)).flat();
    const list = path.join(BUILD, 'segs.txt');
    fs.writeFileSync(list, segs.map(s => `file '${s}'`).join('\n'));
    await once(spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', path.join(BUILD, 'video.mp4')], { stdio: 'inherit' }), 'close');
    segs.forEach(s => fs.unlinkSync(s));
    console.log(`video: ${n} frames`);
  }
  console.log(errors.length ? 'PAGE ERRORS:\n' + [...new Set(errors)].join('\n') : 'no page errors');
  await browser.close();
})();
