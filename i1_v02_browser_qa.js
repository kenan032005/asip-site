const fs = require('fs');
const http = require('http');
const { once } = require('events');

const base = process.env.QA_BASE || 'http://127.0.0.1:8782';
const outDir = process.env.QA_OUT || 'C:/Users/kenan/WorkBuddy/recovery/asip-intelligence-v02-clean/qa-artifacts-v02';
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
    if (message.method === 'Runtime.consoleAPICalled') events.console.push({ type: message.params.type, args: (message.params.args || []).map(arg => arg.value || arg.description || '') });
    if (message.method === 'Runtime.exceptionThrown') events.exceptions.push(message.params.exceptionDetails?.text || 'exception');
    if (message.method === 'Network.loadingFailed') events.failedRequests.push({ error: message.params.errorText });
  };
  const call = (method, params = {}) => new Promise(resolve => { const messageId = ++id; pending.set(messageId, resolve); ws.send(JSON.stringify({ id: messageId, method, params })); });
  async function evaluate(expression) {
    const result = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || 'Runtime.evaluate failed');
    return result.result?.result?.value;
  }
  async function navigate(url) {
    await call('Page.navigate', { url });
    await wait(700);
    for (let i = 0; i < 40; i++) {
      const ready = await evaluate('document.readyState === "complete" && (!document.querySelector("#graphSvg") || document.querySelectorAll(".graph-node").length > 0 || document.querySelector("#intelError")?.hidden === false)');
      if (ready) break; await wait(150);
    }
  }
  async function ensureFocus(entityId) {
    const current = await evaluate('document.querySelector("#focusId")?.textContent || null');
    if (current !== entityId) await navigate(`${base}/intelligence/demo/network/?focus=${encodeURIComponent(entityId)}`);
    return state(`ensure focus ${entityId}`);
  }
  async function state(label) {
    const encoded = await evaluate(`JSON.stringify((function(){const nodes=[...document.querySelectorAll('.graph-node')];return {label:${JSON.stringify(label)},url:location.href,title:document.title,focus:document.querySelector('#focusId')?.textContent||null,focusName:document.querySelector('#focusName')?.textContent||null,nodes:nodes.length,edges:document.querySelectorAll('.graph-edge').length,hint:document.querySelector('#graphHint')?.textContent||null,nodeInfo:document.querySelector('#nodeInfo')?.innerText||null,relationInfo:document.querySelector('#relationInfo')?.innerText||null,bodyWidth:document.body.scrollWidth,innerWidth,profileLevel:document.querySelector('.profile-level')?.textContent||null,heading:document.querySelector('h1')?.textContent||null,error:document.querySelector('#intelError')?.hidden===false,labels:nodes.map(node=>node.getAttribute('aria-label')),types:nodes.map(node=>node.getAttribute('data-entity-type'))};})())`);
    return JSON.parse(encoded);
  }
  async function screenshot(name) { const result = await call('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(`${outDir}/${name}.png`, Buffer.from(result.result.data, 'base64')); }
  async function clickNode(entityId) {
    const point = await evaluate(`(function(){const entity=window.ASIP_INTEL.entityById(${JSON.stringify(entityId)});const node=[...document.querySelectorAll('.graph-node')].find(item=>item.getAttribute('data-entity-id')===${JSON.stringify(entityId)} || item.getAttribute('aria-label')===entity?.name_zh);if(!node)return null;const rect=node.getBoundingClientRect();return {x:rect.left+rect.width/2,y:rect.top+rect.height/2};})()`);
    if (!point) return { label: `click ${entityId}`, unavailable: true, focus: await evaluate('document.querySelector("#focusId")?.textContent || null') };
    await call('Input.dispatchMouseEvent', { type: 'mouseMoved', x: point.x, y: point.y });
    await call('Input.dispatchMouseEvent', { type: 'mousePressed', x: point.x, y: point.y, button: 'left', clickCount: 1 });
    await call('Input.dispatchMouseEvent', { type: 'mouseReleased', x: point.x, y: point.y, button: 'left', clickCount: 1 });
    await wait(700);
    let focus = await evaluate('document.querySelector("#focusId")?.textContent || null');
    if (focus !== entityId) {
      await evaluate(`(function(){const node=document.querySelector('.graph-node[data-entity-id="${entityId}"]');if(node)node.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));})()`);
      await wait(700);
      focus = await evaluate('document.querySelector("#focusId")?.textContent || null');
    }
    const result = await state(`click ${entityId}`);
    result.inputFallback = focus === entityId && point ? (result.url.includes(`focus=${entityId}`) ? false : true) : false;
    return result;
  }
  async function clickRelation() {
    const result = await evaluate(`(function(){const line=document.querySelector('.graph-edge');if(!line)return null;line.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));return {type:line.getAttribute('data-relation-type'),group:line.getAttribute('data-display-group')};})()`);
    if (!result) return { label: 'relation line click', unavailable: true };
    await wait(250);
    const stateResult = await state('relation line click');
    stateResult.relationType = result.type;
    stateResult.relationGroup = result.group;
    stateResult.relationSelected = !stateResult.relationInfo.includes('点击关系线查看双方');
    return stateResult;
  }
  async function clickDom(selector, label) {
    const result = await evaluate(`(function(){const node=document.querySelector(${JSON.stringify(selector)});if(!node)return null;node.click();return {href:node.href||null};})()`);
    if (!result) return { label, unavailable: true };
    await wait(700);
    const stateResult = await state(label);
    stateResult.clickedHref = result.href;
    return stateResult;
  }
  async function clickSelector(selector, label) {
    const point = await evaluate(`(function(){const element=document.querySelector(${JSON.stringify(selector)});if(!element)return null;const rect=element.getBoundingClientRect();return {x:rect.left+rect.width/2,y:rect.top+rect.height/2};})()`);
    if (!point) throw new Error(`selector not found: ${selector}`);
    await call('Input.dispatchMouseEvent', { type: 'mousePressed', x: point.x, y: point.y, button: 'left', clickCount: 1 });
    await call('Input.dispatchMouseEvent', { type: 'mouseReleased', x: point.x, y: point.y, button: 'left', clickCount: 1 });
    await wait(250);
    return state(label);
  }
  await call('Page.enable'); await call('Runtime.enable'); await call('Log.enable'); await call('Network.enable');
  const report = { browser: (await request('/json/version')).Browser, entry: null, entityProfiles: [], graph: [], interactions: {}, viewports: {}, events };
  await navigate(`${base}/intelligence/demo/`); report.entry = await state('entry'); await screenshot('entry');
  for (const slug of ['jnim', 'is-sahel', 'aqim', 'iyad-ag-ghali', 'mali', 'al-qaida', 'ansar-eddine']) {
    await navigate(`${base}/intelligence/demo/entity/${slug}/`);
    const current = await state(`profile ${slug}`); report.entityProfiles.push(current); await screenshot(`entity-${cleanName(slug)}`);
  }
  await navigate(`${base}/intelligence/demo/network/?focus=actor-jnim`); report.graph.push(await state('graph JNIM')); await screenshot('network-jnim');
  report.graph.push(await clickRelation()); await screenshot('relation-line-detail');
  for (const id of ['actor-is-sahel', 'actor-al-qaida', 'person-iyad-ag-ghali']) { report.graph.push(await clickNode(id)); await screenshot(`network-${cleanName(id)}`); }
  report.interactions.browserBack = await evaluate(`(async function(){history.back();await new Promise(r=>setTimeout(r,700));return location.href;})()`); report.interactions.browserBackState = await state('browser back');
  report.interactions.browserForward = await evaluate(`(async function(){history.forward();await new Promise(r=>setTimeout(r,700));return location.href;})()`); report.interactions.browserForwardState = await state('browser forward');
  report.interactions.toolbarBack = await clickSelector('#backFocus', 'toolbar previous focus');
  report.graph.push(await ensureFocus('country-mali')); await screenshot('network-country-mali');
  report.graph.push(await ensureFocus('actor-jnim')); await screenshot('network-jnim-return');
  report.interactions.aliasSearch = await evaluate(`(function(){const input=document.querySelector('#entitySearch');if(!input)return null;input.focus();input.value='ISGS';input.dispatchEvent(new Event('input',{bubbles:true}));return {value:input.value,body:document.body.innerText.includes('伊斯兰国萨赫勒省')};})()`); await wait(500); report.interactions.aliasSearchState = await state('alias search');
  await evaluate(`(function(){const input=document.querySelector('#entitySearch');if(input){input.value='';input.dispatchEvent(new Event('input',{bubbles:true}));}})()`);
  report.interactions.personFilterOff = await clickSelector('[data-type-filter="person"]', 'person filter off');
  report.interactions.personFilterOn = await clickSelector('[data-type-filter="person"]', 'person filter on');
  report.interactions.countryFilterOff = await clickSelector('[data-type-filter="country"]', 'country filter off');
  report.interactions.countryFilterOn = await clickSelector('[data-type-filter="country"]', 'country filter on');
  report.interactions.hostileFilterOff = await clickSelector('[data-rel-filter="hostile_to"]', 'hostile filter off');
  report.interactions.hostileFilterOn = await clickSelector('[data-rel-filter="hostile_to"]', 'hostile filter on');
  report.interactions.zoomIn = await clickSelector('#zoomIn', 'zoom in');
  report.interactions.fit = await clickSelector('#fitGraph', 'fit graph');
  await navigate(`${base}/intelligence/demo/entity/jnim/`);
  report.interactions.entityToNetworkHref = await evaluate('document.querySelector("#graphLink")?.href || null');
  await navigate(`${base}/intelligence/demo/network/?focus=actor-jnim`);
  report.interactions.networkToEntity = await clickDom('#nodeInfo a[href*="/entity/"]', 'network to entity profile');
  await navigate(`${base}/intelligence/demo/entity/jnim/`);
  report.interactions.entityBackToNetwork = await clickDom('#graphLink', 'entity back to network');
  report.interactions.deepRefresh = await (async function(){ await navigate(`${base}/intelligence/demo/network/?focus=person-iyad-ag-ghali`); return state('deep network refresh'); })(); await screenshot('network-iyad-refresh');
  await call('Emulation.setDeviceMetricsOverride', { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false }); await wait(300); report.viewports.desktop = await state('viewport 1366x768'); await screenshot('viewport-1366x768');
  await call('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true }); await wait(300); report.viewports.mobile = await state('viewport 390x844'); await screenshot('viewport-390x844');
  await call('Emulation.clearDeviceMetricsOverride');
  fs.writeFileSync(`${outDir}/browser-qa-results.json`, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ browser: report.browser, profiles: report.entityProfiles.map(item => [item.label, item.profileLevel, item.error]), graphFocuses: report.graph.map(item => item.focus), interactions: Object.fromEntries(Object.entries(report.interactions).map(([key, value]) => [key, value?.focus || value?.label || value?.body || value])), viewports: report.viewports, events: report.events }, null, 2));
  ws.close();
}
main().catch(error => { console.error(error.stack || error); process.exit(1); });
