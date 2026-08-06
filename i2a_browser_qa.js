const fs = require('fs');
const http = require('http');
const { once } = require('events');
const base = 'http://127.0.0.1:8782';
const outDir = 'C:/Users/kenan/WorkBuddy/recovery/asip-intelligence-v02-clean/qa-artifacts-i2a';
const cdpPort = 9223;
fs.mkdirSync(outDir, { recursive: true });
const wait = ms => new Promise(r => setTimeout(r, ms));
function request(path) {
  return new Promise((resolve, reject) => {
    const req = http.get({ host: '127.0.0.1', port: cdpPort, path }, res => {
      let body = ''; res.on('data', c => body += c); res.on('end', () => { try { resolve(JSON.parse(body)); } catch (e) { reject(e); } });
    });
    req.on('error', reject);
  });
}
async function main() {
  const targets = await request('/json/list');
  const page = targets.find(t => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await once(ws, 'open');
  let id = 0; const pending = new Map();
  const events = { console: [], exceptions: [], failedRequests: [] };
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') events.console.push({ args: m.params.args.map(a => a.value || a.description || '') });
    if (m.method === 'Runtime.exceptionThrown') events.exceptions.push(m.params.exceptionDetails?.url || '');
    if (m.method === 'Network.loadingFailed') events.failedRequests.push({ error: m.params.errorText });
  };
  const call = (method, params = {}) => new Promise(resolve => { const mid = ++id; const timer = setTimeout(() => { pending.delete(mid); resolve({ error: true }); }, 30000); pending.set(mid, msg => { clearTimeout(timer); resolve(msg); }); ws.send(JSON.stringify({ id: mid, method, params })); });
  async function evaluate(expression) {
    const r = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (r.error || r.result?.exceptionDetails) return null;
    return r.result?.result?.value;
  }
  async function navigate(url) {
    await call('Page.navigate', { url });
    await wait(900);
    const deadline = Date.now() + 12000;
    while (Date.now() < deadline) {
      const ready = await evaluate('document.readyState === "complete" && window.ASIP_AFRICA && window.ASIP_AFRICA.store && window.ASIP_AFRICA.store.entities.length > 0');
      if (ready) break;
      await wait(250);
    }
    await wait(500);
  }
  async function state(label) {
    const s = await evaluate(`JSON.stringify((function(){return {label:${JSON.stringify(label)},url:location.href,title:document.title,heading:document.querySelector('h1')?.textContent||null,cards:document.querySelectorAll('.intel-card').length,nodes:document.querySelectorAll('.graph-node').length,edges:document.querySelectorAll('.graph-edge').length,relationRows:document.querySelectorAll('.intel-rel-row').length,stats:document.querySelector('#importanceStats')?.textContent||null,infobox:!!document.querySelector('#entityInfobox'),bodyWidth:document.body.scrollWidth,innerWidth,error:document.querySelector('#intelError')?.hidden===false};})())`);
    return JSON.parse(s);
  }
  async function screenshot(name) { let r; for (let i = 0; i < 3; i++) { r = await call('Page.captureScreenshot', { format: 'png' }); if (r && r.result && r.result.data) break; await wait(800); } if (r && r.result && r.result.data) fs.writeFileSync(`${outDir}/${name}.png`, Buffer.from(r.result.data, 'base64')); }
  async function setViewport(w, h, mobile) { await call('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: !!mobile }); await wait(400); }
  await call('Page.enable'); await call('Runtime.enable'); await call('Network.enable'); await call('Network.setCacheDisabled', { cacheDisabled: true });
  const report = { browser: (await request('/json/version')).Browser, pages: {}, network: {}, filters: {}, viewports: {}, events };
  await navigate(`${base}/intelligence/africa/`); report.pages.home = await state('home'); await screenshot('africa-home');
  await navigate(`${base}/intelligence/africa/regions/`); report.pages.regions = await state('regions'); await screenshot('africa-regions');
  await navigate(`${base}/intelligence/africa/region/central-sahel/`); report.pages.regionCentral = await state('region central-sahel'); await screenshot('africa-region-central-sahel');
  await navigate(`${base}/intelligence/africa/region/lake-chad-basin/`); report.pages.regionLakeChad = await state('region lake-chad'); await screenshot('africa-region-lake-chad');
  await navigate(`${base}/intelligence/africa/region/sudan-red-sea-horn/`); report.pages.regionSudan = await state('region sudan');
  await navigate(`${base}/intelligence/africa/region/southeast-africa-mozambique/`); report.pages.regionMoz = await state('region mozambique'); await screenshot('africa-region-mozambique');
  await navigate(`${base}/intelligence/africa/countries/`); report.pages.countries = await state('countries'); await screenshot('africa-countries');
  await navigate(`${base}/intelligence/africa/country/chad/`); report.pages.chad = await state('chad'); await screenshot('africa-chad');
  await navigate(`${base}/intelligence/africa/country/mozambique/`); report.pages.mozambique = await state('mozambique'); await screenshot('africa-mozambique');
  await navigate(`${base}/intelligence/africa/country/sudan/`); report.pages.sudan = await state('sudan'); await screenshot('africa-sudan');
  await navigate(`${base}/intelligence/africa/country/niger/`); report.pages.niger = await state('niger');
  await navigate(`${base}/intelligence/africa/entities/`); report.pages.entities = await state('entities'); await screenshot('africa-entities');
  await navigate(`${base}/intelligence/africa/relations/`); report.pages.relations = await state('relations'); await screenshot('africa-relations');
  await navigate(`${base}/intelligence/africa/entity/jnim/`); report.pages.entityJnim = await state('entity jnim'); await screenshot('africa-entity-jnim');
  await navigate(`${base}/intelligence/africa/entity/iswap/`); report.pages.entityIswap = await state('entity iswap');
  await navigate(`${base}/intelligence/africa/entity/is-mozambique/`); report.pages.entityIsMoz = await state('entity is-moz');
  await navigate(`${base}/intelligence/africa/entity/rapid-support-forces/`); report.pages.entityRsf = await state('entity rsf');
  await navigate(`${base}/intelligence/africa/relation/jas-iswap-conflict/`); report.pages.relJasIswap = await state('relation jas-iswap'); await screenshot('africa-relation-jas-iswap');
  await navigate(`${base}/intelligence/africa/relation/saf-rsf-war/`); report.pages.relSafRsf = await state('relation saf-rsf'); await screenshot('africa-relation-saf-rsf');
  await navigate(`${base}/intelligence/africa/sources/`); report.pages.sources = await state('sources');
  await navigate(`${base}/intelligence/africa/network/?focus=actor-jnim`); report.network.jnim = await state('network jnim'); await screenshot('africa-network-jnim');
  // filters
  const filterResult = await evaluate(`(async function(){
    const region = document.getElementById('regionFilter'); const country = document.getElementById('countryFilter'); const type = document.getElementById('typeFilter');
    const out = {};
    region.value = 'region-lake-chad-basin'; region.dispatchEvent(new Event('change', {bubbles:true})); await new Promise(r=>setTimeout(r,500)); out.lakeChadNodes = document.querySelectorAll('.graph-node').length;
    country.value = 'country-mozambique'; country.dispatchEvent(new Event('change', {bubbles:true})); await new Promise(r=>setTimeout(r,500)); out.mozambiqueNodes = document.querySelectorAll('.graph-node').length;
    type.value = 'state_security_force'; type.dispatchEvent(new Event('change', {bubbles:true})); await new Promise(r=>setTimeout(r,500)); out.securityForceNodes = document.querySelectorAll('.graph-node').length;
    return out;
  })()`);
  report.filters = filterResult; await screenshot('africa-network-filters');
  await navigate(`${base}/intelligence/africa/network/?focus=actor-jnim`);
  report.network.core = await (async function(){ const btn = await evaluate(`(function(){const b=[...document.querySelectorAll('[data-view-filter="core"]')][0]; if(b){b.click(); return true;} return false;})()`); await wait(500); return state('core view'); })(); await screenshot('africa-network-core');
  await navigate(`${base}/intelligence/africa/network/?focus=actor-jnim`);
  report.network.full = await (async function(){ await evaluate(`(function(){const b=[...document.querySelectorAll('[data-view-filter="full"]')][0]; if(b){b.click(); return true;} return false;})()`); await wait(500); return state('full view'); })(); await screenshot('africa-network-full');
  await navigate(`${base}/intelligence/africa/network/?focus=actor-iswap`);
  report.network.iswap = await state('network iswap'); await screenshot('africa-network-iswap');
  // search hidden entity
  await navigate(`${base}/intelligence/africa/network/?focus=actor-jnim`);
  report.network.search = await (async function(){ await evaluate(`(function(){const i=document.getElementById('entitySearch'); i.value='博科圣地'; i.dispatchEvent(new Event('input',{bubbles:true}));})()`); await wait(600); return state('search boko haram'); })(); await screenshot('africa-network-search');
  // deep refresh + viewports
  await navigate(`${base}/intelligence/africa/network/?focus=country-chad`); report.network.chadFocus = await state('chad focus network');
  await navigate(`${base}/intelligence/africa/country/chad/`);
  await setViewport(1920, 1080, false); report.viewports.full = await state('1920'); await screenshot('africa-1920');
  await setViewport(1366, 768, false); report.viewports.desktop = await state('1366'); await screenshot('africa-1366');
  await setViewport(768, 1024, false); report.viewports.tablet = await state('768'); await screenshot('africa-768');
  await setViewport(390, 844, true); report.viewports.mobile = await state('390'); await screenshot('africa-390');
  await call('Emulation.clearDeviceMetricsOverride');
  await navigate(`${base}/intelligence/africa/network/?focus=actor-jnim`);
  await setViewport(390, 844, true); report.viewports.mobileGraph = await state('390 graph'); await screenshot('africa-390-graph');
  await call('Emulation.clearDeviceMetricsOverride');
  await navigate(`${base}/intelligence/demo/network/?focus=actor-jnim`); report.pages.demoStillOk = await state('demo still ok');
  fs.writeFileSync(`${outDir}/browser-qa-results.json`, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ pages: Object.fromEntries(Object.entries(report.pages).map(([k, v]) => [k, { heading: v?.heading, cards: v?.cards, nodes: v?.nodes, error: v?.error }])), filters: report.filters, network: Object.fromEntries(Object.entries(report.network).map(([k, v]) => [k, { heading: v?.heading, nodes: v?.nodes, edges: v?.edges, stats: v?.stats }])), viewports: report.viewports, consoleErrors: events.console.length, exceptions: events.exceptions.length, failedRequests: events.failedRequests.length }, null, 2));
  ws.close();
}
main().catch(e => { console.error(e.stack || e); process.exit(1); });
