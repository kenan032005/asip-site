const fs = require('fs');
const http = require('http');
const { once } = require('events');

const base = process.env.QA_BASE || 'http://127.0.0.1:8782';
const outDir = process.env.QA_OUT || 'C:/Users/kenan/WorkBuddy/recovery/asip-intelligence-v02-clean/qa-artifacts-i1a';
const cdpPort = Number(process.env.CDP_PORT || 9223);
fs.mkdirSync(outDir, { recursive: true });
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
function request(path) {
  return new Promise((resolve, reject) => {
    const req = http.get({ host: '127.0.0.1', port: cdpPort, path }, res => {
      let body = ''; res.on('data', chunk => body += chunk); res.on('end', () => { try { resolve(JSON.parse(body)); } catch (error) { reject(error); } });
    });
    req.on('error', reject);
  });
}
function cleanName(value) { return value.replace(/[^a-zA-Z0-9_-]+/g, '-').replace(/^-+|-+$/g, '').toLowerCase(); }
async function main() {
  let targets;
  for (let i = 0; i < 60; i++) { try { targets = await request('/json/list'); break; } catch (error) { await wait(250); } }
  if (!targets) throw new Error('Chrome DevTools endpoint unavailable');
  const page = targets.find(target => target.type === 'page');
  if (!page) throw new Error('Chrome page target unavailable');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await once(ws, 'open');
  let id = 0;
  const pending = new Map();
  const events = { console: [], exceptions: [], failedRequests: [] };
  ws.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) { pending.get(message.id)(message); pending.delete(message.id); }
    if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') events.console.push({ args: (message.params.args || []).map(arg => arg.value || arg.description || '') });
    if (message.method === 'Runtime.exceptionThrown') events.exceptions.push({ url: message.params.exceptionDetails?.url || '', text: message.params.exceptionDetails?.text || 'exception' });
    if (message.method === 'Network.loadingFailed') events.failedRequests.push({ error: message.params.errorText });
  };
  let currentUrl = '';
  const call = (method, params = {}) => new Promise(resolve => { const messageId = ++id; const timer = setTimeout(() => { pending.delete(messageId); resolve({ error: true, timeout: method }); }, 30000); pending.set(messageId, message => { clearTimeout(timer); resolve(message); }); ws.send(JSON.stringify({ id: messageId, method, params })); });
  async function evaluate(expression) {
    const result = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || 'Runtime.evaluate failed');
    return result.result?.result?.value;
  }
  async function navigate(url, viewport) {
    currentUrl = url;
    await call('Page.navigate', { url });
    await wait(900);
    const deadline = Date.now() + 12000;
    while (Date.now() < deadline) {
      let ready = false;
      try {
        ready = await evaluate('document.readyState === "complete" && (window.ASIP_INTEL && window.ASIP_INTEL.store && window.ASIP_INTEL.store.entities.length > 0) && (!document.querySelector("#graphSvg") || document.querySelectorAll(".graph-node").length > 0 || document.querySelector("#intelError")?.hidden === false)');
      } catch (error) { ready = false; }
      if (ready) break;
      await wait(250);
    }
    await wait(500);
  }
  async function state(label) {
    const encoded = await evaluate(`JSON.stringify((function(){const nodes=[...document.querySelectorAll('.graph-node')];return {label:${JSON.stringify(label)},url:location.href,title:document.title,focus:document.querySelector('#focusId')?.textContent||null,focusName:document.querySelector('#focusName')?.textContent||null,nodes:nodes.length,edges:document.querySelectorAll('.graph-edge').length,rings:nodes.map(n=>n.getAttribute('data-ring')),imps:nodes.map(n=>n.getAttribute('data-importance')),labels:nodes.map(n=>n.getAttribute('aria-label')),hint:document.querySelector('#graphHint')?.textContent||null,stats:document.querySelector('#importanceStats')?.textContent||null,nodeInfo:document.querySelector('#nodeInfo')?.innerText||null,relationInfo:document.querySelector('#relationInfo')?.innerText||null,profileLevel:document.querySelector('.profile-level')?.textContent||null,impBadge:document.querySelector('.intel-badge.imp-L1, .intel-badge.imp-L2, .intel-badge.imp-L3')?.textContent||null,heading:document.querySelector('h1')?.textContent||null,infobox:document.querySelector('#entityInfobox')?.innerText?.slice(0,600)||null,toc:document.querySelector('#entityToc')?.innerText?.slice(0,200)||null,timeline:document.querySelector('#relationTimeline')?.innerText?.slice(0,300)||null,parties:document.querySelector('#relationParties')?.innerText?.slice(0,200)||null,bodyWidth:document.body.scrollWidth,innerWidth,error:document.querySelector('#intelError')?.hidden===false};})())`);
    return JSON.parse(encoded);
  }
  async function screenshot(name) {
    let result;
    for (let attempt = 0; attempt < 3; attempt++) {
      result = await call('Page.captureScreenshot', { format: 'png' });
      if (result && result.result && result.result.data) break;
      await wait(1200);
    }
    if (!result || !result.result || !result.result.data) throw new Error('screenshot failed: ' + name);
    fs.writeFileSync(`${outDir}/${name}.png`, Buffer.from(result.result.data, 'base64'));
  }
  async function clickNode(entityId) {
    const point = await evaluate(`(function(){const node=[...document.querySelectorAll('.graph-node')].find(item=>item.getAttribute('data-entity-id')===${JSON.stringify(entityId)});if(!node)return null;const rect=node.getBoundingClientRect();if(rect.width<1||rect.height<1)return null;return {x:rect.left+rect.width/2,y:rect.top+rect.height/2};})()`);
    if (!point) {
      const fallback = await evaluate(`(function(){const node=document.querySelector('.graph-node[data-entity-id="${entityId}"]');if(node){node.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));return true;}return false;})()`);
      await wait(800);
      if (!fallback) {
        const s = await state(`click ${entityId} (not reachable, url fallback)`);
        if (s.focus !== entityId) await navigate(`${base}/intelligence/demo/network/?focus=${encodeURIComponent(entityId)}`);
        return state(`click ${entityId} (url fallback)`);
      }
      return state(`click ${entityId} (dom-fallback)`);
    }
    await call('Input.dispatchMouseEvent', { type: 'mouseMoved', x: point.x, y: point.y });
    await call('Input.dispatchMouseEvent', { type: 'mousePressed', x: point.x, y: point.y, button: 'left', clickCount: 1 });
    await call('Input.dispatchMouseEvent', { type: 'mouseReleased', x: point.x, y: point.y, button: 'left', clickCount: 1 });
    await wait(800);
    let focus = await evaluate('document.querySelector("#focusId")?.textContent || null');
    if (focus !== entityId) {
      await evaluate(`(function(){const node=document.querySelector('.graph-node[data-entity-id="${entityId}"]');if(node)node.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));})()`);
      await wait(800);
    }
    return state(`click ${entityId}`);
  }
  async function clickSelector(selector, label) {
    const point = await evaluate(`(function(){const element=document.querySelector(${JSON.stringify(selector)});if(!element)return null;const rect=element.getBoundingClientRect();return {x:rect.left+rect.width/2,y:rect.top+rect.height/2};})()`);
    if (!point) return { label, unavailable: true };
    await call('Input.dispatchMouseEvent', { type: 'mousePressed', x: point.x, y: point.y, button: 'left', clickCount: 1 });
    await call('Input.dispatchMouseEvent', { type: 'mouseReleased', x: point.x, y: point.y, button: 'left', clickCount: 1 });
    await wait(500);
    return state(label);
  }
  async function clickRelation() {
    const result = await evaluate(`(function(){const line=document.querySelector('.graph-edge[data-relation-type="hostile_to"]') || document.querySelector('.graph-edge');if(!line)return null;line.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));return {type:line.getAttribute('data-relation-type'),ring:line.getAttribute('data-display-ring')};})()`);
    if (!result) return { label: 'relation line click', unavailable: true };
    await wait(350);
    const s = await state('relation line click');
    s.relationType = result.type; s.relationRing = result.ring;
    s.relationSelected = !s.relationInfo.includes('点击关系线查看双方');
    return s;
  }
  await call('Page.enable'); await call('Runtime.enable'); await call('Log.enable'); await call('Network.enable');
  const report = { browser: (await request('/json/version')).Browser, entry: null, graph: [], importance: {}, relation: {}, entity: {}, viewports: {}, events };
  await navigate(`${base}/intelligence/demo/`); report.entry = await state('entry'); await screenshot('entry');
  await navigate(`${base}/intelligence/demo/network/?focus=actor-jnim`); report.graph.push(await state('graph JNIM')); await screenshot('network-jnim');
  report.graph.push(await clickRelation()); await screenshot('relation-card-hostile');
  const ringChecks = await evaluate(`(function(){const nodes=[...document.querySelectorAll('.graph-node')];const rings={};nodes.forEach(n=>{const r=n.getAttribute('data-ring');(rings[r]=rings[r]||[]).push(n.getAttribute('data-entity-id'));});return {rings,labelsUsed:[...document.querySelectorAll('.node-label')].map(n=>n.textContent)};})()`);
  report.ringLayout = ringChecks;
  for (const id of ['actor-is-sahel', 'actor-al-qaida', 'person-iyad-ag-ghali', 'country-mali']) { report.graph.push(await clickNode(id)); await screenshot(`network-${cleanName(id)}`); }
  await navigate(`${base}/intelligence/demo/network/?focus=actor-jnim`);
  report.importance.viewCore = await clickSelector('[data-view-filter="core"]', 'core view'); await screenshot('importance-core');
  report.importance.viewPriority = await clickSelector('[data-view-filter="priority"]', 'priority view'); await screenshot('importance-priority');
  report.importance.viewFull = await clickSelector('[data-view-filter="full"]', 'full view'); await screenshot('importance-full');
  report.importance.toggleL3Off = await clickSelector('[data-imp-filter="L3"]', 'L3 off'); await screenshot('importance-l3-off');
  report.importance.toggleL3On = await clickSelector('[data-imp-filter="L3"]', 'L3 on');
  await evaluate(`(function(){const input=document.querySelector('#entitySearch');if(input){input.focus();input.value='马西纳旅';input.dispatchEvent(new Event('input',{bubbles:true}));}})()`); await wait(600);
  report.importance.searchHiddenL3 = await state('search hidden L3'); await screenshot('search-hidden-l3');
  await evaluate(`(function(){const input=document.querySelector('#entitySearch');if(input){input.value='ISGS';input.dispatchEvent(new Event('input',{bubbles:true}));}})()`); await wait(600);
  report.importance.aliasSearch = await state('alias search ISGS');
  await navigate(`${base}/intelligence/demo/network/?focus=actor-jnim`);
  report.importance.combo = await clickSelector('[data-type-filter="person"]', 'type person off + imp combo'); await screenshot('combo-filter');
  await navigate(`${base}/intelligence/demo/relation/jnim-is-sahel-hostile/`); report.relation.jnimIs = await state('relation jnim-is-sahel'); await screenshot('relation-jnim-is-sahel');
  await navigate(`${base}/intelligence/demo/relation/jnim-is-sahel-conflict/`); report.relation.jnimIsConflict = await state('relation jnim-is-sahel-conflict');
  await navigate(`${base}/intelligence/demo/relation/jnim-alqaida-affiliate/`); report.relation.jnimAlqaida = await state('relation jnim-alqaida'); await screenshot('relation-jnim-alqaida');
  await navigate(`${base}/intelligence/demo/relation/jnim-mali-operates/`); report.relation.jnimMali = await state('relation jnim-mali');
  await navigate(`${base}/intelligence/demo/relation/jnim-iyad-ag-ghali-led/`); report.relation.iyadJnim = await state('relation iyad-jnim'); await screenshot('relation-iyad-jnim');
  await navigate(`${base}/intelligence/demo/entity/jnim/`); report.entity.jnim = await state('entity jnim'); await screenshot('entity-jnim');
  await navigate(`${base}/intelligence/demo/entity/is-sahel/`); report.entity.isSahel = await state('entity is-sahel'); await screenshot('entity-is-sahel');
  await navigate(`${base}/intelligence/demo/entity/aqim/`); report.entity.aqim = await state('entity aqim');
  await navigate(`${base}/intelligence/demo/entity/iyad-ag-ghali/`); report.entity.iyad = await state('entity iyad');
  await navigate(`${base}/intelligence/demo/entity/mali/`); report.entity.mali = await state('entity mali');
  await navigate(`${base}/intelligence/demo/entity/ansar-eddine/`); report.entity.ansar = await state('entity ansar');
  await navigate(`${base}/intelligence/demo/entity/jnim/`);
  await call('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false }); await wait(350); report.viewports.full = await state('1920x1080'); await screenshot('viewport-1920');
  await call('Emulation.setDeviceMetricsOverride', { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false }); await wait(350); report.viewports.desktop = await state('1366x768'); await screenshot('viewport-1366');
  await call('Emulation.setDeviceMetricsOverride', { width: 768, height: 1024, deviceScaleFactor: 1, mobile: false }); await wait(350); report.viewports.tablet = await state('768x1024'); await screenshot('viewport-768');
  await call('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true }); await wait(350); report.viewports.mobile = await state('390x844'); await screenshot('viewport-390');
  await call('Emulation.clearDeviceMetricsOverride');
  await navigate(`${base}/intelligence/demo/network/?focus=actor-is-sahel`); await call('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true }); await wait(400); report.viewports.mobileGraph = await state('390 graph is-sahel'); await screenshot('viewport-390-graph');
  await call('Emulation.clearDeviceMetricsOverride');
  fs.writeFileSync(`${outDir}/browser-qa-results.json`, JSON.stringify(report, null, 2));
  const staleExceptions = events.exceptions.filter(x => x.url && currentUrl && !currentUrl.startsWith(x.url));
  const currentExceptions = events.exceptions.filter(x => !x.url || !currentUrl || currentUrl.startsWith(x.url));
  console.log(JSON.stringify({
    browser: report.browser,
    graphFocuses: report.graph.map(x => x.focus),
    ringLayout: report.ringLayout,
    importance: Object.fromEntries(Object.entries(report.importance).map(([k, v]) => [k, { focus: v?.focus, nodes: v?.nodes, stats: v?.stats }])),
    relation: Object.fromEntries(Object.entries(report.relation).map(([k, v]) => [k, { title: v?.title, heading: v?.heading, timeline: !!v?.timeline, parties: !!v?.parties }])),
    entity: Object.fromEntries(Object.entries(report.entity).map(([k, v]) => [k, { heading: v?.heading, infobox: !!v?.infobox, toc: !!v?.toc }])),
    viewports: Object.fromEntries(Object.entries(report.viewports).map(([k, v]) => [k, { innerWidth: v?.innerWidth, bodyWidth: v?.bodyWidth, nodes: v?.nodes }])),
    consoleErrors: events.console.length,
    currentPageExceptions: currentExceptions.length,
    staleNavigationArtifacts: staleExceptions.length,
    failedRequests: events.failedRequests.length
  }, null, 2));
  ws.close();
}
main().catch(error => { console.error(error.stack || error); process.exit(1); });
