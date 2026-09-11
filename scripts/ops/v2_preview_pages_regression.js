/* 多页面回归：jsdom 加载关键页面，收集 JS 错误与渲染完成度。只读 dist。 */
const path = require('path');
const fs = require('fs');
function loadJsdom() {
  for (const c of ['jsdom', 'C:/Users/kenan/.workbuddy/binaries/node/workspace/node_modules/jsdom']) {
    try { return require(c); } catch (e) { /* next */ }
  }
  console.error('JSDOM_UNAVAILABLE'); process.exit(3);
}
const { JSDOM, VirtualConsole } = loadJsdom();
const DIST = process.argv[2];
const PAGES = ['events.html', 'countries.html', 'country.html', 'event.html', 'reports.html', 'disease-risk.html'];

(async function () {
  const results = [];
  for (const page of PAGES) {
    const file = path.join(DIST, page);
    if (!fs.existsSync(file)) { results.push({ page, missing: true }); continue; }
    const raw = fs.readFileSync(file, 'utf8');
    const errors = [];
    const vc = new VirtualConsole();
    vc.on('jsdomError', (e) => errors.push(String(e && e.message || e)));
    vc.on('error', (m) => errors.push('console.error: ' + m));
    const dom = new JSDOM(raw.replace(/<script[^>]*src=[^>]*>\s*<\/script>/g, ''), {
      url: 'http://127.0.0.1:8130/' + page, runScripts: 'dangerously',
      pretendToBeVisual: true, virtualConsole: vc,
    });
    const w = dom.window;
    w.fetch = function (u) {
      const rel = String(u).replace(/^.*\/data\//, 'data/');
      const p = path.join(DIST, rel);
      if (!fs.existsSync(p)) return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
      const t = fs.readFileSync(p, 'utf8');
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(JSON.parse(t)), text: () => Promise.resolve(t) });
    };
    const srcRe = /<script[^>]*\ssrc="([^"]+)"[^>]*>/g;
    let m;
    while ((m = srcRe.exec(raw))) {
      const src = m[1];
      if (/^https?:/.test(src)) continue;
      const p = path.join(DIST, src.replace(/^\//, ''));
      if (!fs.existsSync(p)) continue;
      try { w.eval(fs.readFileSync(p, 'utf8')); } catch (e) { errors.push(src + ': ' + e.message); }
    }
    await new Promise((r) => setTimeout(r, 1500));
    const body = w.document.body ? w.document.body.textContent.replace(/\s+/g, ' ') : '';
    results.push({
      page,
      js_errors: errors.slice(0, 5),
      loading_left: w.document.querySelectorAll('.loading, .v11-loading, [id$="Loading"]').length,
      body_chars: body.length,
      has_content: body.length > 500,
      cutoff_set: !!w.__ASIP_CUTOFF__,
    });
  }
  const outPath = process.argv[3];
  const out = { dist: DIST, pages: results,
    all_clean: results.every((r) => r.missing || ((r.js_errors || []).length === 0 && r.has_content)) };
  console.log(JSON.stringify(out, null, 1));
  if (outPath) fs.writeFileSync(outPath, JSON.stringify(out, null, 1) + '\n', 'utf8');
})();
