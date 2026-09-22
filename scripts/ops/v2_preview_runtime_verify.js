/* V2 Preview — jsdom 运行时验证（浏览器守护进程不可用时的等价 DOM 级取证）。
 * 只读取 preview_dist，不写任何文件。 */
const path = require('path');
const fs = require('fs');
function loadJsdom() {
  const candidates = [
    process.env.JSDOM_PATH,
    'jsdom',
    'C:/Users/kenan/.workbuddy/binaries/node/workspace/node_modules/jsdom',
  ].filter(Boolean);
  for (const c of candidates) {
    try { return require(c); } catch (e) { /* try next candidate */ }
  }
  console.error('JSDOM_UNAVAILABLE');
  process.exit(3);
}
const { JSDOM, VirtualConsole } = loadJsdom();

const DIST = process.argv[2];
const OUT = process.argv[3]; // 可选：写盘 JSON 证据（Gate 只读文件，不跨进程派生）
if (!DIST) { console.error('usage: node v2_preview_runtime_verify.js <dist> [out.json]'); process.exit(2); }

const vc = new VirtualConsole();
const pageErrors = [];
vc.on('jsdomError', (e) => pageErrors.push(String(e && e.message || e)));
vc.on('error', (m) => pageErrors.push('console.error: ' + m));

(async function () {
  // 移除外部 script 标签，改为手动按序 eval，避免 jsdom 与手动执行造成二次渲染
  const rawHtml = fs.readFileSync(path.join(DIST, 'index.html'), 'utf8');
  const html = rawHtml.replace(/<script[^>]*src=[^>]*>\s*<\/script>/g, '');
  const dom = new JSDOM(html, {
    url: 'http://127.0.0.1:8130/index.html',
    runScripts: 'dangerously',
    // 不加载外部资源（CSS/图片）：脚本手动按序 eval，样式与本验证无关
    pretendToBeVisual: true,
    virtualConsole: vc,
  });
  const w = dom.window;
  // jsdom 不实现 fetch：用本地文件兜底，保证前端 load() 能拿到同一份数据
  w.fetch = function (u) {
    const rel = String(u).replace(/^.*\/data\//, 'data/');
    const p = path.join(DIST, rel);
    if (!fs.existsSync(p)) return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
    const txt = fs.readFileSync(p, 'utf8');
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(JSON.parse(txt)), text: () => Promise.resolve(txt) });
  };
  // 按 index.html 原始顺序手动执行脚本
  const srcRe = /<script[^>]*\ssrc="([^"]+)"[^>]*>/g;
  const srcList = [];
  let mm;
  while ((mm = srcRe.exec(rawHtml))) srcList.push(mm[1]);
  const scripts = srcList.map((u) => ({ getAttribute: () => u }));
  for (const s of scripts) {
    const src = s.getAttribute('src');
    if (/^https?:/.test(src)) continue;
    const p = path.join(DIST, src.replace(/^\//, ''));
    if (!fs.existsSync(p)) continue;
    try { w.eval(fs.readFileSync(p, 'utf8')); } catch (e) { pageErrors.push(src + ': ' + e.message); }
  }
  await new Promise((r) => setTimeout(r, 2500));
  const d = w.document;
  const txt = (sel) => { const el = d.querySelector(sel); return el ? el.textContent.replace(/\s+/g, ' ').trim() : null; };
  const colored = Array.from(d.querySelectorAll('path.am-country')).filter((p) => !/\br0\b/.test(p.getAttribute('class') || ''));
  const noData = Array.from(d.querySelectorAll('path.am-country')).filter((p) => /\br0\b/.test(p.getAttribute('class') || ''));
  const out = {
    dist: DIST,
    title: d.title,
    cutoff: w.__ASIP_CUTOFF__ || null,
    map_audit: w.__ASIP_MAP_AUDIT__ || null,
    risk_audit: w.__ASIP_RISK_AUDIT__ || null,
    runtime_colored_countries: colored.length,
    runtime_nodata_countries: noData.length,
    runtime_colored_iso3: colored.map((p) => p.getAttribute('data-iso3')).sort(),
    kpis: {
      countries: txt('#v11KpiCountries'), e24: txt('#v11KpiEvents24h'), e7d: txt('#v11KpiEvents7d'),
      highRisk: txt('#v11KpiHighRisk'), china: txt('#v11KpiChina'), disease: txt('#v11KpiDisease'),
    },
    exec_overall: txt('.v11-outlook-total'),
    exec_overall_level: txt('.v11-overall-level'),
    exec_basis: txt('.v11-overall-basis'),
    changed_items: Array.from(d.querySelectorAll('.v11-changed-item')).map((li) => li.textContent.replace(/\s+/g, ' ').trim()),
    top3_title: txt('#v11Top3 .v11-card-en'),
    top3_window: (d.querySelector('#v11Top3 .v11-kd-grid') || {}).getAttribute
      ? d.querySelector('#v11Top3 .v11-kd-grid').getAttribute('data-time-window') : null,
    top3_dates: Array.from(d.querySelectorAll('#v11Top3 .v11-kd-meta span')).map((s) => s.textContent.trim()).filter((x) => /\d{4}-\d{2}-\d{2}/.test(x)),
    category_empty_states: Array.from(d.querySelectorAll('#v11CatConflict, #v11CatPolitical, #v11CatSafety, #v11CatHealth'))
      .map((h) => ({ id: h.id, text: h.textContent.replace(/\s+/g, ' ').trim().slice(0, 80),
                     hasEmptyState: /过去24小时暂无重大新增/.test(h.textContent) })),
    health_active_signals: txt('.v11-hs-top'),
    health_rows: Array.from(d.querySelectorAll('.v11-ob-item')).map((a) => a.textContent.replace(/\s+/g, ' ').trim().slice(0, 120)),
    home_ai_present: !!w.__HOME_AI__,
    render_errors: w.__ASIP_RENDER_ERRORS__ || [],
    ai_blocks: d.querySelectorAll('.v11-ai-text').length,
    ai_fallbacks: d.querySelectorAll('.v11-ai-fallback').length,
    loading_left: d.querySelectorAll('.v11-loading').length,
    page_errors: pageErrors.slice(0, 10),
  };
  console.log(JSON.stringify(out, null, 1));
  if (OUT) {
    fs.writeFileSync(OUT, JSON.stringify(out, null, 1) + '\n', 'utf8');
  }
})();
