const http = require('http');
const fs = require('fs');
const { once } = require('events');
const chrome = 'C:/Users/kenan/AppData/Local/Google/Chrome/Application/chrome.exe';
const base = 'http://127.0.0.1:8776';
const outDir = 'C:/Users/kenan/WorkBuddy/recovery/asip-site-v01-i0c-clean/i0c-browser-artifacts';
fs.mkdirSync(outDir, { recursive: true });
function wait(ms) { return new Promise(r => setTimeout(r, ms)); }
function request(path) { return new Promise((resolve, reject) => { const req = http.get({host:'127.0.0.1',port:9223,path}, res => { let b=''; res.on('data',x=>b+=x); res.on('end',()=>{try{resolve(JSON.parse(b));}catch(e){reject(e);}}); }); req.on('error', reject); }); }
async function main(){
  const targets=await request('/json/list'); const page=targets.find(t=>t.type==='page'); if(!page) throw Error('page target unavailable');
  const ws=new WebSocket(page.webSocketDebuggerUrl); await once(ws,'open'); let id=0; const pending=new Map(); const events={console:[],exceptions:[],failedRequests:[]};
  ws.onmessage=e=>{const m=JSON.parse(e.data); if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);} if(m.method==='Runtime.consoleAPICalled')events.console.push(m.params.type); if(m.method==='Runtime.exceptionThrown')events.exceptions.push(m.params.exceptionDetails?.text||'exception'); if(m.method==='Network.loadingFailed')events.failedRequests.push(m.params.errorText||'failed');};
  const call=(method,params={})=>new Promise(resolve=>{const i=++id;pending.set(i,resolve);ws.send(JSON.stringify({id:i,method,params}));});
  async function ev(x){const r=await call('Runtime.evaluate',{expression:x,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text);return r.result?.result?.value;}
  async function nav(u){await call('Page.navigate',{url:u});await wait(700);for(let i=0;i<40;i++){const ready=await ev('document.readyState==="complete" && (!document.querySelector("#graphSvg") || document.querySelectorAll(".graph-node").length>0 || document.querySelector("#graphHint")?.textContent.includes("加载失败"))');if(ready)break;await wait(150);}}
  async function shot(name){const r=await call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(outDir+'/'+name+'.png',Buffer.from(r.result.data,'base64'));}
  async function state(label){return JSON.parse(await ev(`JSON.stringify({label:${JSON.stringify(label)},url:location.href,title:document.title,focus:document.querySelector('#focusId')?.textContent||null,nodes:document.querySelectorAll('.graph-node').length,edges:document.querySelectorAll('.graph-edge').length,nodeInfo:document.querySelector('#nodeInfo')?.innerText||null,relationInfo:document.querySelector('#relationInfo')?.innerText||null,bodyWidth:document.body.scrollWidth,innerWidth})`));}
  const results={browser:undefined,checks:[],events};
  await call('Page.enable'); await call('Runtime.enable'); await call('Log.enable'); await call('Network.enable');
  results.browser=await ev('navigator.userAgent');
  await nav(base+'/intelligence/demo/'); results.checks.push(await state('entry')); await shot('entry');
  await nav(base+'/intelligence/demo/entity/jnim/'); results.checks.push(await state('entity-jnim')); await shot('entity-jnim');
  await nav(base+'/intelligence/demo/network/?focus=actor-jnim'); results.checks.push(await state('network-jnim')); await shot('network-jnim');
  const node=async(id)=>{const p=await ev(`(()=>{const e=window.ASIP_INTEL.entityById(${JSON.stringify(id)});const n=[...document.querySelectorAll('.graph-node')].find(x=>x.getAttribute('aria-label')===e?.name_zh);if(!n)return false; n.dispatchEvent(new MouseEvent('click',{bubbles:true})); return true;})()`); await wait(650); const s=await state('click-'+id); results.checks.push(s); return p;};
  await node('actor-is-sahel'); await shot('network-is-sahel'); await node('actor-jnim'); await shot('network-jnim-return');
  const relation=await ev(`(()=>{const l=document.querySelector('.graph-edge');if(!l)return false;l.dispatchEvent(new MouseEvent('click',{bubbles:true}));return true;})()`); await wait(250); results.checks.push(await state('relation-first')); await shot('relation-first');
  await nav(base+'/intelligence/demo/network/?focus=person-iyad-ag-ghali'); results.checks.push(await state('deep-refresh')); await shot('deep-refresh');
  await nav(base+'/intelligence/demo/network/?focus=actor-jnim'); await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true}); results.checks.push(await state('viewport-390')); await shot('viewport-390'); await call('Emulation.clearDeviceMetricsOverride');
  fs.writeFileSync(outDir+'/browser-qa-results.json',JSON.stringify(results,null,2)); console.log(JSON.stringify(results,null,2)); ws.close();
}
main().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
