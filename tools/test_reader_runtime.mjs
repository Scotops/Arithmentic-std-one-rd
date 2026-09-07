import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { createRequire } from 'node:module';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(.:)/, '$1')), '..');
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const pages = JSON.parse(fs.readFileSync(path.join(root, 'content/pages.json'), 'utf8'));
const texts = JSON.parse(fs.readFileSync(path.join(root, 'content/i18n/en-US/texts.json'), 'utf8'));
const audios = JSON.parse(fs.readFileSync(path.join(root, 'content/i18n/en-US/audios.json'), 'utf8'));
const videos = JSON.parse(fs.readFileSync(path.join(root, 'content/i18n/en-US/videos.json'), 'utf8'));

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.mp4': 'video/mp4' };
const server = http.createServer((request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
  const target = path.resolve(root, `.${pathname === '/' ? '/index.html' : pathname}`);
  if (!target.startsWith(`${root}${path.sep}`) || !fs.existsSync(target) || !fs.statSync(target).isFile()) {
    response.writeHead(404).end('Not found');
    return;
  }
  response.writeHead(200, { 'Content-Type': types[path.extname(target).toLowerCase()] || 'application/octet-stream' });
  fs.createReadStream(target).pipe(response);
});

await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const port = server.address().port;
const browser = await chromium.launch({ executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', headless: true });
const context = await browser.newContext({ viewport: { width: 1280, height: 1600 } });
const page = await context.newPage();
const pageErrors = [];
page.on('pageerror', (error) => {
  const detail = `${page.url()}: ${error.stack || error}`;
  pageErrors.push(detail);
  console.log(`PAGE ERROR ${detail}`);
});

if (process.argv.includes('--quiz-debug')) {
  const cdp = await context.newCDPSession(page);
  await cdp.send('Runtime.enable');
  cdp.on('Runtime.exceptionThrown', ({ exceptionDetails }) => {
    console.log(`CDP EXCEPTION ${JSON.stringify(exceptionDetails)}`);
  });
  await page.goto(`http://127.0.0.1:${port}/qz001.html`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
  console.log(`After quiz load: ${JSON.stringify(pageErrors)}`);
  await page.locator('input[type="radio"]').first().click({ force: true });
  await page.waitForTimeout(1000);
  console.log(`After quiz selection: ${JSON.stringify(pageErrors)}`);
  await browser.close();
  await new Promise((resolve) => server.close(resolve));
  process.exit(pageErrors.length ? 1 : 0);
}

let queueTargets = 0;
let imageOccurrences = 0;
for (let index = 0; index < pages.length; index += 1) {
  const entry = pages[index];
  const href = entry.href.split('#', 1)[0];
  if (index % 10 === 0) console.log(`Runtime page ${index + 1}/${pages.length}: ${href}`);
  const response = await page.goto(`http://127.0.0.1:${port}/${href}`, { waitUntil: 'domcontentloaded' });
  assert(response?.ok(), `${href}: navigation failed`);
  try {
    await page.waitForFunction(() => window.ADT_TTS_DEBUG?.queue && getComputedStyle(document.querySelector('#content')).opacity !== '0', null, { timeout: 10000 });
  } catch (error) {
    throw new Error(`${href}: runtime initialization timeout`, { cause: error });
  }
  const result = await page.evaluate(() => ({
    queue: window.ADT_TTS_DEBUG.queue(),
    missingImages: Array.from(document.images).filter((image) => !image.complete || image.naturalWidth === 0).map((image) => image.src),
    screenshotLayers: document.querySelectorAll('.pdf-page-facsimile, img[src*="pdf-pages"], img[src*="_page.png"]').length,
    folio: document.querySelector('.printed-folio')?.textContent.trim(),
    imageCount: document.querySelectorAll('#content img').length,
    mediaSync: Boolean(window.ADT_MEDIA_SYNC),
  }));
  const expectedFolio = String(entry.page_number);
  assert((result.folio || (index === 0 ? 'Cover' : '')) === expectedFolio, `${href}: folio mismatch`);
  assert(result.queue.length > 0, `${href}: empty narration queue`);
  assert(result.missingImages.length === 0, `${href}: missing images ${result.missingImages.join(', ')}`);
  assert(result.screenshotLayers === 0, `${href}: full-page screenshot layer found`);
  assert(result.mediaSync, `${href}: media synchronization adapter missing`);
  for (const item of result.queue) {
    assert(item.id && !item.id.includes('_ans_'), `${href}: hidden answer target in queue`);
    if (!item.id.startsWith('adt_question_label_')) {
      assert(item.id in texts, `${href}: queue text is unmapped: ${item.id}`);
      assert(item.id in audios, `${href}: queue audio is unmapped: ${item.id}`);
    }
  }
  if (href === 'pg054_sec001.html') {
    assert(result.queue.filter((item) => item.id === 'pg054_im010_seg004_v1_crop1').length === 7, 'page 54 must narrate all seven cars');
  }
  if (href === 'pg074_sec001.html') {
    assert(result.queue.filter((item) => item.id === 'pg074_im016').length >= 4, 'page 74 must narrate repeated sticks individually');
  }
  queueTargets += result.queue.length;
  imageOccurrences += result.imageCount;
}

for (let index = 0; index < pages.length; index += 1) {
  const filename = videos[`video-${index + 1}`];
  assert(filename, `Missing video mapping for physical page ${index + 1}`);
  assert(fs.existsSync(path.join(root, 'content/i18n/en-US/video', filename)), `Missing video file: ${filename}`);
}

await page.goto(`http://127.0.0.1:${port}/pg008_sec001.html`, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('input[type="radio"]');
const firstRadio = page.locator('input[type="radio"]').first();
await firstRadio.focus();
await page.keyboard.press('Space');
assert(await firstRadio.isChecked(), 'Keyboard selection failed on page 8');

await page.goto(`http://127.0.0.1:${port}/pg054_sec001.html`, { waitUntil: 'domcontentloaded' });
const answer = page.locator('input[type="text"]').first();
await answer.fill('10');
assert(await answer.inputValue() === '10', 'Fill-in exercise failed on page 54');

await page.goto(`http://127.0.0.1:${port}/qz001.html`, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('input[type="radio"]');
const quizOption = page.locator('input[type="radio"]').first();
await quizOption.click({ force: true });
assert(await quizOption.isChecked(), 'Quiz pointer selection failed');
assert(await page.locator('section[data-section-type="activity_quiz"]').count() === 1, 'Quiz activity structure is missing');

const syncResult = await page.evaluate(async () => {
  const video = document.querySelector('video') || document.body.appendChild(document.createElement('video'));
  video.pause();
  window.__syncPlay = 0;
  window.__syncPause = 0;
  let paused = true;
  Object.defineProperty(video, 'paused', { configurable: true, get: () => paused });
  video.play = () => { paused = false; window.__syncPlay += 1; return Promise.resolve(); };
  video.pause = () => { paused = true; window.__syncPause += 1; };
  const audio = document.body.appendChild(document.createElement('audio'));
  audio.dispatchEvent(new Event('play'));
  await new Promise((resolve) => setTimeout(resolve, 320));
  audio.dispatchEvent(new Event('pause'));
  await new Promise((resolve) => setTimeout(resolve, 120));
  return { play: window.__syncPlay, pause: window.__syncPause };
});
assert(syncResult.play > 0 && syncResult.pause > 0, `Audio/video synchronization failed: ${JSON.stringify(syncResult)}`);
assert(pageErrors.length === 0, `Browser errors: ${pageErrors.join(' | ')}`);

const summary = { physicalPages: pages.length, queueTargets, imageOccurrences, videos: Object.keys(videos).length, keyboardExercise: 'passed', pointerQuiz: 'passed', mediaSync: 'passed', pageErrors: 0 };
fs.writeFileSync(path.join(root, 'tmp/runtime-test-final.json'), `${JSON.stringify(summary, null, 2)}\n`);
console.log(JSON.stringify(summary, null, 2));

await browser.close();
await new Promise((resolve) => server.close(resolve));
