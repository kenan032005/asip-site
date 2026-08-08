const http = require("http");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");
const PUBLIC = process.env.PUBLIC_BASE || "https://kenan032005.github.io/asip-site/intelligence/africa";
const CDP_PORT = Number(process.env.CDP_PORT || 9229);
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-i3d1", "public-browser-qa.json");
const ENTITIES = ["fla", "africa-corps", "wagner-group", "ansarul-islam", "hcua", "mnla", "maa-cma", "gatia", "dan-na-ambassagou", "fu-aes", "niger-armed-forces", "abu-hanifa", "sadou-samahouna", "lakurawa", "ansaru"];
const RELS = ["d1-abu-hanifa-jnim-affiliation", "d1-abu-hanifa-niger", "d1-africa-corps-fama-coop", "d1-africa-corps-jnim-conflict", "d1-africa-corps-mali-deployed", "d1-africa-corps-wagner-history", "d1-ansaru-aqim-allegiance", "d1-ansaru-jas-split", "d1-ansaru-jnim-affiliation", "d1-ansaru-nigeria-operates", "d1-ansarul-burkina-operates", "d1-ansarul-jnim-constituent", "d1-burkina-army-fu-aes-member", "d1-dan-na-fama-coop", "d1-dan-na-jnim-conflict", "d1-dan-na-mali-operates", "d1-fama-fu-aes-member", "d1-fla-africa-corps-conflict", "d1-fla-fama-conflict", "d1-fla-gatia-merged", "d1-fla-hcua-merged", "d1-fla-jnim-cooperation", "d1-fla-maa-merged", "d1-fla-mali-operates", "d1-fla-mnla-merged", "d1-fu-aes-region", "d1-gatia-mali", "d1-hcua-mali", "d1-lakurawa-is-sahel-network", "d1-lakurawa-jas-cooperation", "d1-lakurawa-jnim-cooperation", "d1-lakurawa-niger-operates", "d1-lakurawa-nigeria-operates", "d1-maa-mali", "d1-mnla-mali", "d1-niger-army-fu-aes-member", "d1-niger-army-niger", "d1-sadou-burkina-history", "d1-sadou-is-sahel", "d1-sadou-jnim-history", "d1-wagner-fama-coop", "d1-wagner-jnim-conflict", "d1-wagner-mali-deployed"];
const routes = [["Africa root", ""], ["Entities index", "entities/"], ["Relations index", "relations/"], ["Network", "network/"]].concat(
  ENTITIES.map(s => ["entity " + s, "entity/" + s + "/"]),
  RELS.map(s => ["relation " + s, "relation/" + s + "/"])
);
const viewports = [1920, 1366, 390];
const viewportRoutes = [["Africa root", ""], ["Network", "network/"], ["Entity FLA", "entity/fla/"], ["Entity FU-AES", "entity/fu-aes/"], ["Relation FLA-JNIM", "relation/d1-fla-jnim-cooperation/"], ["Relation Lakurawa-IS Sahel", "relation/d1-lakurawa-is-sahel-network/"]];
function getJson(url) { return new Promise((resolve, reject) => { http.get(url, (res) => { let b = ""; res.on("data", x => b += x); res.on("end", () => { try { resolve(JSON.parse(b)); } catch (e) { reject(e); } }); }).on("error", reject); }); }
function wait(ms) { return new Promise(r => setTimeout(r, ms)); }
async function main() {
  const targets = await getJson(`http://127.0.0.1:${CDP_PORT}/json/list`);
  const target = targets.find(x => x.type === "page" && !x.url.startsWith("edge://") && !x.url.startsWith("chrome-extension://") && !x.url.startsWith("devtools://"));
  if (!target) throw new Error("CDP page target not found");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.once("open", resolve); ws.once("error", reject); });
  let id = 0; const pending = new Map(); const events = { exceptions: [], console: [], failed: [], bad: [], rejections: [] }; const requestUrls = new Map(); let currentUrl = "";
  ws.on("message", raw => { const m = JSON.parse(raw.toString()); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m); } if (m.method === "Runtime.exceptionThrown") events.exceptions.push({ url: currentUrl, details: m.params.exceptionDetails }); if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") events.console.push({ url: currentUrl, args: (m.params.args || []).map(a => a.value || a.description || "") }); if (m.method === "Network.requestWillBeSent") requestUrls.set(m.params.requestId, m.params.request.url); if (m.method === "Network.responseReceived" && m.params.response && m.params.response.status >= 400 && !/favicon/.test(m.params.response.url)) events.bad.push({ url: m.params.response.url, status: m.params.response.status }); if (m.method === "Network.loadingFailed" && m.params.errorText !== "net::ERR_ABORTED") events.failed.push({ url: requestUrls.get(m.params.requestId) || null, error: m.params.errorText }); });
  const call = (method, params = {}) => new Promise((resolve, reject) => { const i = ++id; pending.set(i, { resolve, reject }); ws.send(JSON.stringify({ id: i, method, params })); });
  const evaluate = async expression => { const r = await call("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }); return r.result && r.result.result ? r.result.result.value : null; };
  await call("Runtime.enable"); await call("Page.enable"); await call("Network.enable"); await call("Log.enable"); await call("Network.setCacheDisabled", { cacheDisabled: true });
  const pages = [];
  async function check(width, label, route) {
    await call("Emulation.setDeviceMetricsOverride", { width, height: 900, deviceScaleFactor: 1, mobile: false });
    currentUrl = `${PUBLIC}/${route}`; const before = { exceptions: events.exceptions.length, console: events.console.length, failed: events.failed.length, bad: events.bad.length };
    await call("Page.navigate", { url: currentUrl }); await wait(route.startsWith("network") || route.startsWith("relation") ? 1300 : 750);
    const state = await evaluate(`(() => { const err = document.querySelector("#intelError"); const top = document.querySelector("#topbar"); const h1 = document.querySelector("h1"); return { url: location.href, ready_state: document.readyState, h1: h1 ? h1.innerText.slice(0, 70) : null, body_chars: document.body ? document.body.innerText.replace(/\\s+/g, "").length : 0, error_hidden: !err || err.hidden, header_loaded: !!top && top.innerText.trim().length > 0, network_nodes: document.querySelectorAll("g.graph-node[data-entity-id]").length, overflow: document.documentElement.scrollWidth > innerWidth + 2 }; })()`);
    const rejection = await evaluate("window.__ASIP_QA_REJECTIONS || []");
    pages.push({ viewport: width, label, route, url: currentUrl, state, events: { runtime_exceptions: events.exceptions.length - before.exceptions, console_errors: events.console.length - before.console, failed_requests: events.failed.length - before.failed, bad_responses: events.bad.length - before.bad, unhandled_rejections: rejection.length } });
  }
  for (const [label, route] of routes) await check(1366, label, route);
  for (const width of viewports) for (const [label, route] of viewportRoutes) await check(width, label, route);
  const allClean = pages.every(p => p.state.ready_state === "complete" && p.state.header_loaded && p.state.error_hidden && !p.state.overflow && Object.values(p.events).every(v => v === 0));
  const report = { artifact: "I3D1_PUBLIC_BROWSER_QA", generated_at: new Date().toISOString(), public_base: PUBLIC, viewports, routes_checked: routes.length, pages, events: { exceptions: events.exceptions, console: events.console, failed: events.failed, bad: events.bad }, summary: { pagesChecked: pages.length, consoleErrors: events.console.length, runtimeExceptions: events.exceptions.length, failedRequests: events.failed.length, brokenAssets: events.bad.length, horizontalOverflow: pages.filter(p => p.state.overflow).length, unexpectedUnhandledRejections: pages.reduce((n, p) => n + p.events.unhandled_rejections, 0), new_entities_200: ENTITIES.length, new_relations_200: RELS.length, gate: allClean && events.bad.length === 0 ? "PASS" : "OPEN" } };
  fs.mkdirSync(path.dirname(OUT), { recursive: true }); fs.writeFileSync(OUT, JSON.stringify(report, null, 2)); console.log(JSON.stringify(report.summary)); ws.close();
}
main().catch(e => { console.error(e.stack || e); process.exit(1); });
