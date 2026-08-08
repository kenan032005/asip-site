const http = require("http");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");
const PUBLIC = process.env.PUBLIC_BASE || "http://127.0.0.1:4174/intelligence/africa";
const CDP_PORT = Number(process.env.CDP_PORT || 9228);
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-i3d1", "candidate-browser-qa.json");
const routes = [
  ["Africa root", ""], ["Entities index", "entities/"], ["Relations index", "relations/"], ["Network", "network/"],
  ["Entity FLA", "entity/fla/"], ["Entity Africa Corps", "entity/africa-corps/"], ["Entity FU-AES", "entity/fu-aes/"],
  ["Entity Lakurawa", "entity/lakurawa/"], ["Entity Ansaru", "entity/ansaru/"], ["Entity Dan Na Ambassagou", "entity/dan-na-ambassagou/"],
  ["Entity Sadou Samahouna", "entity/sadou-samahouna/"], ["Entity Wagner", "entity/wagner-group/"],
  ["Relation FLA-JNIM", "relation/d1-fla-jnim-cooperation/"], ["Relation FAMa-Africa Corps", "relation/d1-africa-corps-fama-coop/"],
  ["Relation Wagner-Africa Corps", "relation/d1-africa-corps-wagner-history/"], ["Relation Ansarul-JNIM", "relation/d1-ansarul-jnim-constituent/"],
  ["Relation Sadou-IS Sahel", "relation/d1-sadou-is-sahel/"], ["Relation Lakurawa-IS Sahel", "relation/d1-lakurawa-is-sahel-network/"],
  ["Relation Ansaru-AQIM", "relation/d1-ansaru-aqim-allegiance/"], ["Relation FU-AES region", "relation/d1-fu-aes-region/"],
];
function getJson(url) { return new Promise((resolve, reject) => { http.get(url, (res) => { let b = ""; res.on("data", x => b += x); res.on("end", () => { try { resolve(JSON.parse(b)); } catch (e) { reject(e); } }); }).on("error", reject); }); }
function wait(ms) { return new Promise(r => setTimeout(r, ms)); }
async function main() {
  const targets = await getJson(`http://127.0.0.1:${CDP_PORT}/json/list`);
  const target = targets.find(x => x.type === "page" && !x.url.startsWith("edge://") && !x.url.startsWith("chrome-extension://") && !x.url.startsWith("devtools://"));
  if (!target) throw new Error("CDP page target not found");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.once("open", resolve); ws.once("error", reject); });
  let id = 0; const pending = new Map(); const events = { exceptions: [], console: [], failed: [], bad: [] }; const requestUrls = new Map(); let currentUrl = "";
  ws.on("message", raw => { const m = JSON.parse(raw.toString()); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m); } if (m.method === "Runtime.exceptionThrown") events.exceptions.push({ url: currentUrl, details: m.params.exceptionDetails }); if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") events.console.push({ url: currentUrl, args: (m.params.args || []).map(a => a.value || a.description || "") }); if (m.method === "Network.requestWillBeSent") requestUrls.set(m.params.requestId, m.params.request.url); if (m.method === "Network.responseReceived" && m.params.response && m.params.response.status >= 400) events.bad.push({ url: m.params.response.url, status: m.params.response.status }); if (m.method === "Network.loadingFailed" && m.params.errorText !== "net::ERR_ABORTED") events.failed.push({ url: requestUrls.get(m.params.requestId) || null, error: m.params.errorText }); });
  const call = (method, params = {}) => new Promise((resolve, reject) => { const i = ++id; pending.set(i, { resolve, reject }); ws.send(JSON.stringify({ id: i, method, params })); });
  const evaluate = async expression => { const r = await call("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }); return r.result && r.result.result ? r.result.result.value : null; };
  await call("Runtime.enable"); await call("Page.enable"); await call("Network.enable"); await call("Log.enable"); await call("Network.setCacheDisabled", { cacheDisabled: true });
  const pages = [];
  for (const [label, route] of routes) {
    await call("Emulation.setDeviceMetricsOverride", { width: 1366, height: 900, deviceScaleFactor: 1, mobile: false });
    currentUrl = `${PUBLIC}/${route}`; const before = { exceptions: events.exceptions.length, console: events.console.length, failed: events.failed.length, bad: events.bad.length };
    await call("Page.navigate", { url: currentUrl }); await wait(route.startsWith("network") || route.startsWith("relation") ? 1200 : 700);
    const state = await evaluate(`(() => { const err = document.querySelector("#intelError"); const top = document.querySelector("#topbar"); const h1 = document.querySelector("h1"); const relOv = document.querySelector("#relationOverview"); const tl = document.querySelector("#relationTimeline"); return { url: location.href, ready_state: document.readyState, h1: h1 ? h1.innerText.slice(0, 80) : null, body_chars: document.body ? document.body.innerText.replace(/\\s+/g, "").length : 0, error_hidden: !err || err.hidden, header_loaded: !!top && top.innerText.trim().length > 0, relation_overview_present: !!relOv && relOv.innerText.trim().length > 0, timeline_items: tl ? tl.querySelectorAll(".tl-item").length : -1, network_nodes: document.querySelectorAll("g.graph-node[data-entity-id]").length, overflow: document.documentElement.scrollWidth > innerWidth + 2 }; })()`);
    pages.push({ label, route, url: currentUrl, state, events: { runtime_exceptions: events.exceptions.length - before.exceptions, console_errors: events.console.length - before.console, failed_requests: events.failed.length - before.failed, bad_responses: events.bad.length - before.bad } });
  }
  const realBad = events.bad.filter(b => !/\/favicon\.ico$/.test(b.url));
  const allClean = pages.every(p => p.state.ready_state === "complete" && p.state.header_loaded && p.state.error_hidden && !p.state.overflow && Object.values(p.events).every(v => v === 0));
  const report = { artifact: "I3D1_CANDIDATE_BROWSER_QA", generated_at: new Date().toISOString(), public_base: PUBLIC, viewport: 1366, pages, events: { exceptions: events.exceptions, console: events.console, failed: events.failed, bad: events.bad, bad_excluding_favicon: realBad }, summary: { pagesChecked: pages.length, consoleErrors: events.console.length, runtimeExceptions: events.exceptions.length, failedRequests: events.failed.length, brokenAssets: realBad.length, horizontalOverflow: pages.filter(p => p.state.overflow).length, gate: allClean && realBad.length === 0 ? "PASS" : "OPEN" } };
  fs.mkdirSync(path.dirname(OUT), { recursive: true }); fs.writeFileSync(OUT, JSON.stringify(report, null, 2)); console.log(JSON.stringify(report.summary)); ws.close();
}
main().catch(e => { console.error(e.stack || e); process.exit(1); });
