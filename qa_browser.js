const http = require('http');
const fs = require('fs');
const { spawn } = require('child_process');
const { once } = require('events');

const chrome = 'C:/Users/kenan/AppData/Local/Google/Chrome/Application/chrome.exe';
const userData = 'C:/Users/kenan/WorkBuddy/2026-08-05-19-13-54/.workbuddy/chrome-qa-profile-v01b';
const outDir = 'C:/Users/kenan/WorkBuddy/2026-07-20-22-01-23/asip-site-v01/qa-artifacts';
const base = 'http://127.0.0.1:8766';
const entry = base + '/intelligence/demo/';
const network = base + '/intelligence/demo/network/?focus=actor-jnim';
fs.mkdirSync(outDir, { recursive: true });

function wait(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
function request(path) {
  return new Promise((resolve, reject) => {
    const req = http.get({host: '127.0.0.1', port: 9223, path}, res => {
      let body = ''; res.on('data', x => body += x); res.on('end', () => { try { resolve(JSON.parse(body)); } catch (e) { reject(e); } });
    });
    req.on('error', reject);
  });
}
function cleanName(name) { return name.replace(/[^a-zA-Z0-9_-]+/g, '-').replace(/^-+|-+$/g, '').toLowerCase(); }

async function main() {
  let targets;
  for (let i = 0; i < 50; i++) { try { targets = await request('/json/list'); break; } catch (e) { await wait(250); } }
  if (!targets) throw new Error('Chrome DevTools endpoint unavailable');
  const page = targets.find(t => t.type === 'page');
  if (!page) throw new Error('Chrome page target unavailable');
  console.log('CDP_PAGE', page.url);
  const WebSocket = global.WebSocket;
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await once(ws, 'open');
  let id = 0; const pending = new Map(); const events = { console: [], exceptions: [], failedRequests: [] };
  ws.onmessage = e => {
    const msg = JSON.parse(e.data);
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
    if (msg.method === 'Runtime.consoleAPICalled') events.console.push({type: msg.params.type, args: (msg.params.args || []).map(a => a.value || a.description || '')});
    if (msg.method === 'Runtime.exceptionThrown') events.exceptions.push(msg.params.exceptionDetails && msg.params.exceptionDetails.text || 'exception');
    if (msg.method === 'Network.loadingFailed') events.failedRequests.push({url: msg.params.requestId, error: msg.params.errorText});
  };
  function call(method, params = {}) { return new Promise(resolve => { const i = ++id; pending.set(i, resolve); ws.send(JSON.stringify({id: i, method, params})); }); }
  async function evaluate(expression) {
    const result = await call('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || 'Runtime evaluate failed');
    return result.result && result.result.result ? result.result.result.value : undefined;
  }
  async function navigate(url) {
    await call('Page.navigate', {url});
    await wait(900);
    for (let i = 0; i < 20; i++) {
      const ready = await evaluate('document.readyState === "complete" && (!document.querySelector("#graphHint") || !document.querySelector("#graphHint").textContent.includes("加载共享"))');
      if (ready) break; await wait(150);
    }
  }
  async function screenshot(name) {
    const shot = await call('Page.captureScreenshot', {format: 'png'});
    fs.writeFileSync(outDir + '/' + name + '.png', Buffer.from(shot.result.data, 'base64'));
  }
  async function state(label) {
    const value = await evaluate(`JSON.stringify((function(){
      const nodes=[...document.querySelectorAll('.graph-node')];
      return {label:${JSON.stringify(label)},url:location.href,title:document.title,focus:document.querySelector('#focusId')?.textContent||null,
      focusName:document.querySelector('#focusName')?.textContent||null,nodes:nodes.length,edges:document.querySelectorAll('.graph-edge').length,
      hint:document.querySelector('#graphHint')?.textContent||null,nodeInfo:document.querySelector('#nodeInfo')?.innerText||null,
      relationInfo:document.querySelector('#relationInfo')?.innerText||null,bodyWidth:document.body.scrollWidth,innerWidth:innerWidth,
      visibleLabels:nodes.map(n=>n.getAttribute('aria-label'))};
    })())`);
    return JSON.parse(value);
  }
  async function clickNode(entityId) {
    const point = await evaluate(`(function(){const n=[...document.querySelectorAll('.graph-node')].find(x=>x.getAttribute('aria-label') && x.getAttribute('aria-label') === window.ASIP_INTEL.entityById(${JSON.stringify(entityId)})?.name_zh); if(!n)return null; const target=n.querySelector('.node-shape') || n; const r=target.getBoundingClientRect(); return {x:r.left+r.width/2,y:r.top+r.height/2,label:n.getAttribute('aria-label'),width:r.width,height:r.height};})()`);
    if (!point) return {label:'click ' + entityId, focus: await evaluate('document.querySelector("#focusId")?.textContent || null'), unavailable:true};
    await call('Input.dispatchMouseEvent', {type:'mouseMoved', x:point.x, y:point.y});
    await call('Input.dispatchMouseEvent', {type:'mousePressed', x:point.x, y:point.y, button:'left', clickCount:1});
    await call('Input.dispatchMouseEvent', {type:'mouseReleased', x:point.x, y:point.y, button:'left', clickCount:1});
    await wait(650);
    return state('click ' + entityId);
  }
  async function clickRelation(relId) {
    const point = await evaluate(`(function(){
      const rels=window.ASIP_INTEL.store.relationships.filter(r=>r.source_entity_id===document.querySelector('#focusId').textContent||r.target_entity_id===document.querySelector('#focusId').textContent);
      const rel=rels.find(r=>r.relationship_id===${JSON.stringify(relId)}); if(!rel)return null;
      const center=document.querySelector('#focusId').textContent;
      const other=rel.source_entity_id===center?rel.target_entity_id:rel.source_entity_id;
      const entity=window.ASIP_INTEL.entityById(other); const visible=[...document.querySelectorAll('.graph-node')].some(n=>n.getAttribute('aria-label')===entity.name_zh); if(!visible)return null;
      const idx=rels.filter(r=>{const o=r.source_entity_id===center?r.target_entity_id:r.source_entity_id; const e=window.ASIP_INTEL.entityById(o); return e && [...document.querySelectorAll('.graph-node')].some(n=>n.getAttribute('aria-label')===e.name_zh);}).findIndex(r=>r.relationship_id===${JSON.stringify(relId)});
      const line=document.querySelectorAll('.graph-edge')[idx]; if(!line)return null; const r=line.getBoundingClientRect(); return {x:r.left+r.width/2,y:r.top+r.height/2,idx};
    })()`);
    if (!point) throw new Error('relation line not found: ' + relId);
    await call('Input.dispatchMouseEvent', {type:'mouseMoved', x:point.x, y:point.y});
    await call('Input.dispatchMouseEvent', {type:'mousePressed', x:point.x, y:point.y, button:'left', clickCount:1});
    await call('Input.dispatchMouseEvent', {type:'mouseReleased', x:point.x, y:point.y, button:'left', clickCount:1});
    await wait(250);
    return state('relation ' + relId);
  }
  async function ensureFocus(entityId) {
    const current = await evaluate('document.querySelector("#focusId")?.textContent || null');
    if (current !== entityId) { await navigate(base + '/intelligence/demo/network/?focus=' + encodeURIComponent(entityId)); }
    return state('ensure focus ' + entityId);
  }
  async function inputSearch(term) {
    const point = await evaluate(`(function(){const e=document.querySelector('#entitySearch'); const r=e.getBoundingClientRect(); return {x:r.left+r.width/2,y:r.top+r.height/2};})()`);
    await call('Input.dispatchMouseEvent', {type:'mousePressed', x:point.x, y:point.y, button:'left', clickCount:1});
    await call('Input.dispatchMouseEvent', {type:'mouseReleased', x:point.x, y:point.y, button:'left', clickCount:1});
    await call('Input.insertText', {text:term}); await wait(650); return state('search ' + term);
  }
  async function clickSelector(selector, label) {
    const point = await evaluate(`(function(){const e=document.querySelector(${JSON.stringify(selector)}); if(!e)return null; const r=e.getBoundingClientRect(); return {x:r.left+r.width/2,y:r.top+r.height/2};})()`);
    if (!point) throw new Error('selector not found: ' + selector);
    await call('Input.dispatchMouseEvent', {type:'mousePressed', x:point.x, y:point.y, button:'left', clickCount:1});
    await call('Input.dispatchMouseEvent', {type:'mouseReleased', x:point.x, y:point.y, button:'left', clickCount:1});
    await wait(250); return state(label);
  }
  await call('Page.enable'); await call('Runtime.enable'); await call('Log.enable'); await call('Network.enable');
  await navigate(entry);
  const entryState = await state('entry'); await screenshot('entry');
  await evaluate(`document.querySelector('a[href*="entity/jnim"]')?.click()`); await wait(650);
  const entityState = await evaluate('JSON.stringify({url:location.href,title:document.title,heading:document.querySelector("h1")?.textContent,graphHref:document.querySelector("#graphLink")?.href,entityLinks:document.querySelectorAll(".intel-entity-link").length,bodyWidth:document.body.scrollWidth,innerWidth:innerWidth})');
  fs.writeFileSync(outDir + '/entity-jnim-state.json', entityState); await screenshot('entity-jnim');
  await evaluate(`document.querySelector('#graphLink')?.click()`); await wait(700);
  const initial = await state('network initial'); await screenshot('network-jnim');
  const sequence = ['actor-is-sahel','country-niger','actor-al-qaida','person-iyad-ag-ghali','actor-jnim'];
  const sequenceStates = [];
  for (const id of sequence) {
    const result = await clickNode(id);
    sequenceStates.push(result);
    if (result.unavailable) {
      result.urlFallback = base + '/intelligence/demo/network/?focus=' + encodeURIComponent(id);
      await navigate(result.urlFallback);
      result.deepFocus = await state('URL fallback ' + id);
    }
    await screenshot('network-' + cleanName(id));
  }
  const roundtrip = [];
  for (const id of ['actor-is-sahel','actor-jnim','actor-is-sahel','actor-jnim']) {
    const current = await state('roundtrip before ' + id);
    if (current.focus !== id) {
      const result = await clickNode(id);
      if (result.unavailable) { await navigate(base + '/intelligence/demo/network/?focus=' + encodeURIComponent(id)); }
      roundtrip.push(result);
    } else roundtrip.push(current);
  }
  await screenshot('network-roundtrip-jnim');
  const relations = [];
  for (const id of ['rel-jnim-is-conflict','rel-jnim-alqaida-affiliate','rel-jnim-mali-operates']) {
    if ((await state('relation precheck ' + id)).focus !== 'actor-jnim') await navigate(network);
    relations.push(await clickRelation(id)); await screenshot('relation-' + cleanName(id));
  }
  const iyadFocus = await ensureFocus('person-iyad-ag-ghali');
  relations.push(await clickRelation('rel-jnim-iyad-led')); await screenshot('relation-rel-iyad-jnim');
  const historyBefore = await state('before history');
  await clickNode('actor-jnim'); await clickNode('actor-is-sahel');
  await call('Page.goBack'); await wait(650); const back = await state('browser back');
  await call('Page.goForward'); await wait(650); const forward = await state('browser forward');
  await clickSelector('#backFocus','toolbar back focus'); const toolbarBack = await state('toolbar back focus');
  await clickSelector('#resetFocus','reset focus'); const reset = await state('reset focus');
  await inputSearch('ISGS'); const aliasSearch = await state('alias search');
  await evaluate('document.querySelector("#entitySearch").value=""; document.querySelector("#entitySearch").dispatchEvent(new Event("input",{bubbles:true}))'); await wait(200);
  await clickSelector('[data-type-filter="person"]','filter person off'); const personOff = await state('person filter off');
  await clickSelector('[data-type-filter="person"]','filter person on');
  await clickSelector('[data-type-filter="country"]','filter country off'); const countryOff = await state('country filter off');
  await clickSelector('[data-type-filter="country"]','filter country on');
  await clickSelector('[data-rel-filter="hostile_to"]','filter hostile off'); const hostileOff = await state('hostile filter off');
  await clickSelector('[data-rel-filter="hostile_to"]','filter hostile on');
  await clickSelector('#zoomIn','zoom in'); const zoomIn = await state('zoom in');
  await clickSelector('#fitGraph','fit graph'); const fit = await state('fit graph');
  await navigate(base + '/intelligence/demo/entity/is-sahel/'); const deepEntity = await evaluate('JSON.stringify({url:location.href,title:document.title,heading:document.querySelector("h1")?.textContent,bodyWidth:document.body.scrollWidth,innerWidth:innerWidth,error:document.querySelector("#intelError")?.hidden===false})'); await screenshot('entity-is-sahel');
  await navigate(base + '/intelligence/demo/network/?focus=person-iyad-ag-ghali'); const deepNetwork = await state('deep network refresh'); await screenshot('network-iyad-refresh');
  const widths = {};
  for (const width of [1920,1366,768,390]) {
    await call('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false}); await wait(400); widths[width] = await state('viewport ' + width); await screenshot('viewport-' + width);
  }
  await call('Emulation.clearDeviceMetricsOverride');
  const report = {browser:(await request('/json/version')).Browser,entry:entryState,entity:JSON.parse(entityState),initial,sequence:sequenceStates,roundtrip,relations,historyBefore,back,forward,toolbarBack,reset,aliasSearch,personOff,countryOff,hostileOff,zoomIn,fit,deepEntity:JSON.parse(deepEntity),deepNetwork,widths,events};
  fs.writeFileSync(outDir + '/browser-qa-results.json', JSON.stringify(report,null,2));
  console.log(JSON.stringify({entry:entryState,initial,sequence:sequenceStates.map(x=>x.focus),roundtrip:roundtrip.map(x=>x.focus),relations:relations.map(x=>x.relationInfo && x.relationInfo.split('\n').slice(0,3)),back:back.focus,forward:forward.focus,toolbarBack:toolbarBack.focus,reset:reset.focus,aliasSearch:aliasSearch.focus,deepNetwork:deepNetwork.focus,widths:Object.fromEntries(Object.entries(widths).map(([k,v])=>[k,{bodyWidth:v.bodyWidth,innerWidth:v.innerWidth,focus:v.focus}])),events},null,2));
  ws.close();
}
main().catch(e => { console.error(e.stack || e); process.exit(1); });
