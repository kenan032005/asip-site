const fs = require('fs');
const http = require('http');
const { once } = require('events');
const base = process.env.QA_BASE || 'http://127.0.0.1:8782';
const outDir = process.env.QA_OUT || 'C:/Users/kenan/WorkBuddy/recovery/asip-intelligence-v02-clean/qa-artifacts-i1b';
const cdpPort = Number(process.env.CDP_PORT || 9223);
fs.mkdirSync(outDir, { recursive: true });
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
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
    if (m.method === 'Runtime.exceptionThrown') events.exceptions.push({ url: m.params.exceptionDetails?.url || '', text: m.params.exceptionDetails?.text || 'exception' });
    if (m.method === 'Network.loadingFailed') events.failedRequests.push({ error: m.params.errorText });
  };
  const call = (method, params = {}) => new Promise(resolve => { const mid = ++id; const timer = setTimeout(() => { pending.delete(mid); resolve({ error: true, timeout: method }); }, 30000); pending.set(mid, msg => { clearTimeout(timer); resolve(msg); }); ws.send(JSON.stringify({ id: mid, method, params })); });
  async function evaluate(expression) {
    const r = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (r.error) return null;
    if (r.result?.exceptionDetails) return null;
    return r.result?.result?.value;
  }
  async function navigate(url) {
    await call('Page.navigate', { url });
    await wait(800);
    const deadline = Date.now() + 10000;
    while (Date.now() < deadline) {
      const ready = await evaluate('document.readyState === "complete" && window.ASIP_INTEL && window.ASIP_INTEL.store && window.ASIP_INTEL.store.entities.length > 0 && document.querySelectorAll(".graph-node").length > 0');
      if (ready) break;
      await wait(250);
    }
    await wait(500);
  }
  async function state(label) {
    const s = await evaluate(`JSON.stringify((function(){const nodes=[...document.querySelectorAll('.graph-node')];const edgeGroups=[...document.querySelectorAll('.graph-edge-group')];const hits=[...document.querySelectorAll('.graph-edge-hit')];return {label:${JSON.stringify(label)},url:location.href,nodes:nodes.length,edges:document.querySelectorAll('.graph-edge').length,hits:hits.length,groups:edgeGroups.length,stats:document.querySelector('#importanceStats')?.textContent||null,bodyWidth:document.body.scrollWidth,innerWidth,error:document.querySelector('#intelError')?.hidden===false};})())`);
    return JSON.parse(s);
  }
  async function screenshot(name) { let r; for (let i = 0; i < 3; i++) { r = await call('Page.captureScreenshot', { format: 'png' }); if (r && r.result && r.result.data) break; await wait(800); } if (r && r.result && r.result.data) fs.writeFileSync(`${outDir}/${name}.png`, Buffer.from(r.result.data, 'base64')); }
  await call('Page.enable'); await call('Runtime.enable'); await call('Log.enable'); await call('Network.enable'); await call('Network.setCacheDisabled', { cacheDisabled: true });
  const report = { browser: (await request('/json/version')).Browser, layout: {}, click: {}, label: {}, viewports: {}, events };
  await navigate(`${base}/intelligence/demo/network/?focus=actor-jnim`);
  report.layout = await evaluate(`(function(){
    const nodes=[...document.querySelectorAll('.graph-node')];
    const pos={}; nodes.forEach(n=>{const t=n.getAttribute('transform');const m=/translate\\(([-0-9.]+),([-0-9.]+)\\)/.exec(t); if(m)pos[n.getAttribute('data-entity-id')]={x:+m[1],y:+m[2],ring:n.getAttribute('data-ring'),label:n.getAttribute('aria-label')};});
    const center=pos['actor-jnim']; const out={nodes:{},ringDist:{},sameRay:[]};
    Object.keys(pos).forEach(k=>{ if(k==='actor-jnim')return; const dx=pos[k].x-center.x, dy=pos[k].y-center.y; const r=Math.hypot(dx,dy); const ang=Math.atan2(dy,dx); out.nodes[k]={ring:pos[k].ring,r:Math.round(r),angle:+(ang*180/Math.PI).toFixed(1),label:pos[k].label}; (out.ringDist[pos[k].ring]=out.ringDist[pos[k].ring]||[]).push({id:k,angle:ang,r}); });
    const pairs=[]; const ids=Object.keys(pos); for(let i=0;i<ids.length;i++){for(let j=i+1;j<ids.length;j++){ if(ids[i]==='actor-jnim'||ids[j]==='actor-jnim')continue; const d=Math.hypot(pos[ids[i]].x-pos[ids[j]].x,pos[ids[i]].y-pos[ids[j]].y); pairs.push({a:ids[i],b:ids[j],d:Math.round(d)}); } }
    pairs.sort((x,y)=>x.d-y.d);
    out.minDistance=pairs.length?pairs[0]:null;
    out.closePairs=pairs.filter(p=>p.d<90);
    ['inner','middle','outer'].forEach(ring=>{ const arr=out.ringDist[ring]||[]; arr.sort((a,b)=>a.angle-b.angle); for(let i=1;i<arr.length;i++){ const deg=Math.abs(arr[i].angle-arr[i-1].angle)*180/Math.PI; if(deg<12) out.sameRay.push({ring,ids:[arr[i-1].id,arr[i].id],angleGap:Math.round(deg*10)/10}); } });
    return out;
  })()`);
  await screenshot('i1b-jnim-after');
  report.click = { measured: await evaluate(`(function(){
    const hit=document.querySelector('.graph-edge-hit');
    const line=document.querySelector('.graph-edge');
    if(!hit||!line)return {ok:false};
    const hb=hit.getBoundingClientRect(); const lb=line.getBoundingClientRect();
    if(hb.width<1||lb.width<1)return {ok:false};
    const hitLen=Math.hypot(hb.width,hb.height); const lineLen=Math.hypot(lb.width,lb.height);
    return {ok:true,hitLen:Math.round(hitLen),lineLen:Math.round(lineLen),clickableOutsideVisual:hitLen>lineLen,visualStroke:getComputedStyle(line).strokeWidth||'',hitStroke:getComputedStyle(hit).strokeWidth||''};
  })()`) };
  // offset click: click 6px perpendicular to the visual line, on the hit layer, should trigger relation info
  const offsetResult = await evaluate(`(function(){
    const hit=document.querySelector('.graph-edge-hit');
    if(!hit)return null;
    const x1=+hit.getAttribute('x1'),y1=+hit.getAttribute('y1'),x2=+hit.getAttribute('x2'),y2=+hit.getAttribute('y2');
    const mx=(x1+x2)/2,my=(y1+y2)/2; const dx=x2-x1,dy=y2-y1; const len=Math.max(Math.hypot(dx,dy),1);
    const svg=document.getElementById('graphSvg'); const pt=svg.createSVGPoint();
    const off=5; pt.x=mx-dy/len*off; pt.y=my+dx/len*off;
    const ctm=svg.getScreenCTM(); const sp=pt.matrixTransform(ctm);
    hit.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,clientX:sp.x,clientY:sp.y,view:window}));
    return {x:Math.round(sp.x),y:Math.round(sp.y)};
  })()`);
  await wait(400);
  const relInfo = await evaluate('document.querySelector("#relationInfo")?.innerText?.slice(0,60) || ""');
  report.click.offsetClick = { point: offsetResult || null, relationOpened: relInfo.includes('关系详情') && !relInfo.includes('点击关系线查看') };
  // label avoidance: distance from label bbox center to each edge segment, flag when < 8px (real overlap near the line)
  report.label = await evaluate(`(function(){
    function segDist(px,py,x1,y1,x2,y2){const dx=x2-x1,dy=y2-y1;const l2=dx*dx+dy*dy;let t=l2?((px-x1)*dx+(py-y1)*dy)/l2:0;t=Math.max(0,Math.min(1,t));const cx=x1+t*dx,cy=y1+t*dy;return Math.hypot(px-cx,py-cy);}
    const svg=document.getElementById('graphSvg');const ctm=svg.getScreenCTM();
    const labels=[...document.querySelectorAll('.graph-node .node-label')];
    const edges=[...document.querySelectorAll('.graph-edge')];
    let overlaps=0;const details=[];
    labels.forEach(l=>{const rb=l.getBoundingClientRect();if(rb.width<2||rb.height<2)return;const cx=(rb.left+rb.right)/2,cy=(rb.top+rb.bottom)/2;edges.forEach(e=>{const x1=+e.getAttribute('x1'),y1=+e.getAttribute('y1'),x2=+e.getAttribute('x2'),y2=+e.getAttribute('y2');const p1={x:ctm.a*x1+ctm.c*y1+ctm.e,y:ctm.b*x1+ctm.d*y1+ctm.f},p2={x:ctm.a*x2+ctm.c*y2+ctm.e,y:ctm.b*x2+ctm.d*y2+ctm.f};const d=segDist(cx,cy,p1.x,p1.y,p2.x,p2.y);if(d<10){overlaps++;if(details.length<8)details.push({label:l.textContent,d:Math.round(d*10)/10});}});});
    return {overlaps,details,labelCount:labels.length};
  })()`);
  // switch centers and re-measure min distance
  const focusStates = {};
  for (const id of ['actor-is-sahel', 'actor-al-qaida', 'person-iyad-ag-ghali', 'country-mali']) {
    await navigate(`${base}/intelligence/demo/network/?focus=${encodeURIComponent(id)}`);
    focusStates[id] = await evaluate(`(function(){const nodes=[...document.querySelectorAll('.graph-node')];const pos={};nodes.forEach(n=>{const m=/translate\\(([-0-9.]+),([-0-9.]+)\\)/.exec(n.getAttribute('transform'));if(m)pos[n.getAttribute('data-entity-id')]={x:+m[1],y:+m[2]};});const ids=Object.keys(pos);const pairs=[];for(let i=0;i<ids.length;i++){for(let j=i+1;j<ids.length;j++){if(ids[i]===${JSON.stringify(id)}||ids[j]===${JSON.stringify(id)})continue;const d=Math.hypot(pos[ids[i]].x-pos[ids[j]].x,pos[ids[i]].y-pos[ids[j]].y);pairs.push(d);}}pairs.sort((a,b)=>a-b);return {nodes:nodes.length,minDistance:pairs.length?Math.round(pairs[0]):null};})()`);
  }
  report.focusMinDistance = focusStates;
  await navigate(`${base}/intelligence/demo/network/?focus=actor-jnim`);
  await call('Emulation.setDeviceMetricsOverride', { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false }); await wait(400); report.viewports.desktop = await state('desktop'); await screenshot('i1b-desktop');
  await call('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true }); await wait(400); report.viewports.mobile = await state('mobile'); await screenshot('i1b-mobile');
  await call('Emulation.clearDeviceMetricsOverride');
  fs.writeFileSync(`${outDir}/browser-qa-results.json`, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ browser: report.browser, layout: { minDistance: report.layout?.minDistance, closePairs: (report.layout?.closePairs||[]).length, sameRay: report.layout?.sameRay, nodes: report.layout?.nodes }, click: report.click, label: report.label, focusMinDistance: report.focusMinDistance, viewports: report.viewports, consoleErrors: events.console.length, exceptions: events.exceptions.length, failedRequests: events.failedRequests.length }, null, 2));
  ws.close();
}
main().catch(e => { console.error(e.stack || e); process.exit(1); });
