const http = require('http');
const WebSocket = require('ws');
const port = Number(process.env.CDP_PORT || 9225);
const targetUrl = process.env.TARGET_URL || 'https://kenan032005.github.io/asip-site/intelligence/africa/network/';
const viewports = [1920, 1366, 768, 390];
const runs = Number(process.env.RUNS || 10);

function getJson(url) { return new Promise((resolve, reject) => { http.get(url, (res) => { let b = ''; res.on('data', x => b += x); res.on('end', () => { try { resolve(JSON.parse(b)); } catch (e) { reject(e); } }); }).on('error', reject); }); }
function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  const targets = await getJson(`http://127.0.0.1:${port}/json/list`);
  const target = targets.find(x => x.type === 'page' && x.url === targetUrl) || targets.find(x => x.type === 'page' && x.url !== 'about:blank');
  if (!target) throw new Error('CDP page target not found');
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.once('open', resolve); ws.once('error', reject); });
  let id = 0; const pending = new Map(); const exceptions = []; const consoleErrors = []; const failed = []; const badResponses = []; const requestUrls = new Map();
  ws.on('message', raw => {
    const m = JSON.parse(raw.toString());
    if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m); }
    if (m.method === 'Runtime.exceptionThrown') exceptions.push(m.params.exceptionDetails || {});
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') consoleErrors.push(m.params);
    if (m.method === 'Network.requestWillBeSent') requestUrls.set(m.params.requestId, m.params.request.url);
    if (m.method === 'Network.responseReceived' && m.params.response && m.params.response.status >= 400) badResponses.push({url:m.params.response.url,status:m.params.response.status});
    if (m.method === 'Network.loadingFailed' && m.params.errorText !== 'net::ERR_ABORTED') failed.push({url:requestUrls.get(m.params.requestId)||null,error:m.params.errorText});
  });
  function call(method, params={}) { return new Promise((resolve,reject) => { const i=++id; pending.set(i,{resolve,reject}); ws.send(JSON.stringify({id:i,method,params})); }); }
  async function evaluate(expression) { const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true}); if(r.result && r.result.exceptionDetails) throw new Error(r.result.exceptionDetails.text); return r.result && r.result.result ? r.result.result.value : null; }
  async function load(width) {
    exceptions.length=0; consoleErrors.length=0; failed.length=0; badResponses.length=0; requestUrls.clear();
    await call('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});
    await call('Page.navigate',{url:targetUrl}); await wait(1200);
    for(let i=0;i<40;i++) { const ready=await evaluate('document.readyState === "complete" && document.querySelectorAll("g.graph-node[data-entity-id]").length > 0 && document.querySelector("#graphHint") && !document.querySelector("#graphHint").textContent.includes("加载")'); if(ready) break; await wait(250); }
    return evaluate(`(() => {
      const focus=document.querySelector('#focusId')?.textContent.trim()||null;
      const nodes=[...document.querySelectorAll('g.graph-node[data-entity-id]')];
      const candidate=nodes.find(n=>n.getAttribute('data-entity-id')!==focus&&!n.classList.contains('is-center'));
      const before={focus_id:focus,focus_name:document.querySelector('#focusName')?.textContent.trim()||null,node_count:nodes.length,edge_count:document.querySelectorAll('.graph-edge').length,right_panel_entity_id:(document.querySelector('#nodeInfo')?.textContent.match(/(?:actor|country|person|entity)-[A-Za-z0-9_-]+/)||[null])[0],neighbor_ids:nodes.map(n=>n.getAttribute('data-entity-id')).filter(x=>x!==focus).sort(),url:location.href,ready_state:document.readyState,graph_ready_state:document.querySelector('#graphHint')?.textContent||null};
      if(!candidate) return {before,candidate:null,after:before,changed:false};
      candidate.scrollIntoView({block:'center',inline:'center'});
      const rect=candidate.getBoundingClientRect();
      candidate.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window,clientX:rect.left+rect.width/2,clientY:rect.top+rect.height/2}));
      const afterFocus=document.querySelector('#focusId')?.textContent.trim()||null;
      const afterNodes=[...document.querySelectorAll('g.graph-node[data-entity-id]')];
      const after={focus_id:afterFocus,focus_name:document.querySelector('#focusName')?.textContent.trim()||null,node_count:afterNodes.length,edge_count:document.querySelectorAll('.graph-edge').length,right_panel_entity_id:(document.querySelector('#nodeInfo')?.textContent.match(/(?:actor|country|person|entity)-[A-Za-z0-9_-]+/)||[null])[0],neighbor_ids:afterNodes.map(n=>n.getAttribute('data-entity-id')).filter(x=>x!==afterFocus).sort(),url:location.href,ready_state:document.readyState,graph_ready_state:document.querySelector('#graphHint')?.textContent||null};
      return {before,candidate:{entity_id:candidate.getAttribute('data-entity-id'),aria_label:candidate.getAttribute('aria-label')||null},after,changed:before.focus_id!==after.focus_id};
    })()`);
  }
  const results=[];
  for(const width of viewports) { const rounds=[]; for(let r=1;r<=runs;r++){ rounds.push(await load(width)); await wait(150); } results.push({viewport:width,rounds,events:{runtime_exceptions:exceptions.length,console_errors:consoleErrors.length,failed_requests:failed.length,bad_responses:badResponses.length}}); }
  console.log(JSON.stringify({viewports:results.map(x=>({viewport:x.viewport,rounds:x.rounds.length,all_focus_switches:x.rounds.every(r=>r.changed&&r.after.focus_id===r.candidate.entity_id),sample:x.rounds[0]})),events:{runtime_exceptions:exceptions.length,console_errors:consoleErrors.length,failed_requests:failed.length,bad_responses:badResponses.length}},null,2));
  ws.close();
}
main().catch(e=>{console.error(e.stack||e);process.exit(1);});
