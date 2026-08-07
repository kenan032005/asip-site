const fs = require('fs');
const path = require('path');
const http = require('http');
const WebSocket = globalThis.WebSocket;
if (!WebSocket) throw new Error('Node WebSocket unavailable');
const OUT = 'C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-trusted/qa-artifacts-i3b-fix1a/round-3-browser';
const BASE = 'https://kenan032005.github.io/asip-site/previews/asip-intelligence-v1.0-rc1/intelligence/africa/';
const PAGES = [
  {name:'africa-home', url: BASE + '?gate_round=3&fresh=1'},
  {name:'country-mali', url: BASE + 'country/mali/?gate_round=3&fresh=1'},
  {name:'country-cameroon', url: BASE + 'country/cameroon/?gate_round=3&fresh=1'},
  {name:'entity-jnim', url: BASE + 'entity/jnim/?gate_round=3&fresh=1'},
  {name:'network-focus-jnim', url: BASE + 'network/?focus=actor-jnim&gate_round=3&fresh=1'},
  {name:'catalog-metrics', url: BASE + 'data/catalog_metrics.json?gate_round=3&fresh=1'}
];
function getJson(url) { return new Promise((resolve,reject)=>http.get(url,r=>{let s='';r.on('data',d=>s+=d);r.on('end',()=>{try{resolve(JSON.parse(s))}catch(e){reject(e)}})}).on('error',reject)); }
function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
async function main(){
  const targets = await getJson('http://127.0.0.1:9226/json/list');
  const target = targets.find(x=>x.type==='page' && x.url==='about:blank') || targets.find(x=>x.type==='page');
  if(!target) throw new Error('no page target');
  const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j});
  let id=0, pending=new Map(), current='';
  const events={consoleErrors:[],runtimeExceptions:[],unexpectedUnhandledRejections:[],unexpectedFailedRequests:[],brokenAssets:[]};
  ws.onmessage=e=>{const m=JSON.parse(e.data); if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id)}
    if(m.method==='Runtime.consoleAPICalled' && m.params.type==='error') events.consoleErrors.push({url:current,args:(m.params.args||[]).map(a=>a.value??a.description??'').join(' ')});
    if(m.method==='Runtime.exceptionThrown'){const d=m.params.exceptionDetails||{};events.runtimeExceptions.push({url:current,text:d.text||'',description:d.exception?.description||''});}
    if(m.method==='Network.loadingFailed' && m.params.errorText!=='net::ERR_ABORTED') events.unexpectedFailedRequests.push({url:current,requestId:m.params.requestId,error:m.params.errorText||'',type:m.params.type||''});
  };
  function call(method,params={}){return new Promise(resolve=>{const n=++id;pending.set(n,resolve);ws.send(JSON.stringify({id:n,method,params}))})}
  await call('Runtime.enable'); await call('Page.enable'); await call('Network.enable'); await call('Network.setCacheDisabled',{cacheDisabled:true});
  await call('Page.addScriptToEvaluateOnNewDocument',{source:`window.__qaUnhandled=[];window.addEventListener('unhandledrejection',e=>window.__qaUnhandled.push(String(e.reason&&e.reason.stack||e.reason||'unhandled rejection')));`});
  const report={schema:'asip-i3b-fix1a-browser-round-3-v1',round:3,cacheDisabled:true,extensionsDisabled:true,profile:'fresh-user-data-dir',browserTarget:target.url,verifiedAtUtc:new Date().toISOString(),pages:[],summary:{consoleErrors:0,runtimeExceptions:0,unexpectedUnhandledRejections:0,unexpectedFailedRequests:0,brokenAssets:0,horizontalOverflow:0}};
  for(const p of PAGES){
    current=p.url; const before={ce:events.consoleErrors.length,re:events.runtimeExceptions.length,uf:events.unexpectedFailedRequests.length};
    await call('Page.navigate',{url:p.url}); await sleep(2500);
    const evalRes=await call('Runtime.evaluate',{expression:`(async()=>{const isJson=location.pathname.endsWith('.json');const resources=[...performance.getEntriesByType('resource')].map(x=>({name:x.name,initiatorType:x.initiatorType}));const links=[...document.querySelectorAll('link[rel=stylesheet]')].map(x=>x.href);const scripts=[...document.scripts].map(x=>x.src).filter(Boolean);const bad=[...document.querySelectorAll('img,script,link[rel=stylesheet]')].filter(x=>x.tagName==='IMG'?!x.complete:x.tagName==='LINK'?!x.sheet:!x.src).map(x=>x.src||x.href);let jsonOk=true;if(isJson){try{JSON.parse(document.body.innerText)}catch(e){jsonOk=false}};return {finalUrl:location.href,title:document.title,isJson,htmlOk:isJson||!!document.querySelector('html'),jsonOk,cssCount:links.length,jsCount:scripts.length,resources,brokenAssets:bad,scrollWidth:document.documentElement.scrollWidth,innerWidth:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth+2,unhandled:window.__qaUnhandled||[]}})()`,returnByValue:true,awaitPromise:true});
    const st=evalRes.result?.result?.value||{}; events.unexpectedUnhandledRejections.push(...(st.unhandled||[]).map(x=>({url:current,text:x}))); events.brokenAssets.push(...(st.brokenAssets||[]).map(x=>({url:current,asset:x})));
    const page={name:p.name,requestedUrl:p.url,finalUrl:st.finalUrl||null,statusAssumption:'CDP Page.navigate completed; HTTP status cross-checked by round-2 HTTP evidence',htmlOk:!!st.htmlOk,jsonOk:!!st.jsonOk,cssCount:st.cssCount||0,jsCount:st.jsCount||0,resources:st.resources||[],brokenAssets:st.brokenAssets||[],consoleErrors:events.consoleErrors.slice(before.ce),runtimeExceptions:events.runtimeExceptions.slice(before.re),unexpectedUnhandledRejections:st.unhandled||[],unexpectedFailedRequests:events.unexpectedFailedRequests.slice(before.uf),horizontalOverflow:!!st.overflow,scrollWidth:st.scrollWidth,innerWidth:st.innerWidth,deepRefresh:true,queryParameterChecked:p.url.includes('focus=actor-jnim')?String(st.finalUrl||'').includes('focus=actor-jnim'):true};
    report.pages.push(page); if(page.horizontalOverflow)report.summary.horizontalOverflow++; report.summary.consoleErrors+=page.consoleErrors.length;report.summary.runtimeExceptions+=page.runtimeExceptions.length;report.summary.unexpectedUnhandledRejections+=page.unexpectedUnhandledRejections.length;report.summary.unexpectedFailedRequests+=page.unexpectedFailedRequests.length;report.summary.brokenAssets+=page.brokenAssets.length;
    const shot=await call('Page.captureScreenshot',{format:'png'});if(shot.result?.data)fs.writeFileSync(path.join(OUT,p.name+'.png'),Buffer.from(shot.result.data,'base64'));
  }
  fs.writeFileSync(path.join(OUT,'browser-qa-round-3.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify({summary:report.summary,pages:report.pages.map(x=>({name:x.name,finalUrl:x.finalUrl,htmlOk:x.htmlOk,jsonOk:x.jsonOk,cssCount:x.cssCount,jsCount:x.jsCount,consoleErrors:x.consoleErrors.length,runtimeExceptions:x.runtimeExceptions.length,unexpectedUnhandledRejections:x.unexpectedUnhandledRejections.length,unexpectedFailedRequests:x.unexpectedFailedRequests.length,brokenAssets:x.brokenAssets.length,horizontalOverflow:x.horizontalOverflow}))},null,2));
  ws.close();
}
main().catch(e=>{console.error(e);process.exit(1)});
