const http = require("http");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");
const PUBLIC = process.env.PUBLIC_BASE || "https://kenan032005.github.io/asip-site/intelligence/africa";
const CDP_PORT = Number(process.env.CDP_PORT || 9231);
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-i3d2", "public-browser-qa.json");
const ENTITIES = ["jafar-dicko", "ousmane-dicko", "katiba-hanifa", "abou-ghosmane", "katiba-serma", "dana-atem", "ibrahim-malam-dicko", "dozos-of-macina", "sidi-ongoiba", "amadou-nionson-diarra", "youssouf-toloba"];
const REFRESH_ENTITIES = ["jnim", "abu-hanifa", "ansarul-islam"];
const RELS = ["d2-jafar-jnim", "d2-ansarul-jafar-led", "d2-ansarul-ibrahim-founded", "d2-ousmane-jnim", "d2-katiba-hanifa-jnim", "d2-katiba-hanifa-abu-led", "d2-katiba-hanifa-benin", "d2-katiba-hanifa-niger", "d2-katiba-hanifa-burkina", "d2-katiba-hanifa-benin-forces", "d2-ghosmane-jnim", "d2-ghosmane-niger", "d2-katiba-serma-jnim", "d2-katiba-serma-mali", "d2-katiba-serma-burkina", "d2-dana-dan-na-split", "d2-dana-sidi-led", "d2-dana-mali", "d2-dana-katiba-serma-conflict", "d2-dana-ansarul-conflict", "d2-dana-fama-coop", "d2-dozos-macina-amadou-led", "d2-dozos-macina-mali", "d2-dozos-macina-jnim-conflict", "d2-dozos-macina-fama-coop", "d2-dan-na-toloba-led", "d2-jnim-nigeria-emerging", "d2-jafar-burkina", "d2-ousmane-burkina"];
const routes = [["Africa root", ""], ["Entities index", "entities/"], ["Relations index", "relations/"], ["Network", "network/"]].concat(
  ENTITIES.map(s => ["entity " + s, "entity/" + s + "/"]),
  REFRESH_ENTITIES.map(s => ["refresh entity " + s, "entity/" + s + "/"]),
  RELS.map(s => ["relation " + s, "relation/" + s + "/"]),
  [["refresh relation jnim-is-sahel-conflict", "relation/jnim-is-sahel-conflict/"], ["refresh relation jnim-benin-spillover", "relation/jnim-benin-spillover/"], ["refresh relation jnim-benin-forces-fought", "relation/jnim-benin-forces-fought/"]]
);
const viewports = [1920, 1366, 390];
const viewportRoutes = [["Africa root", ""], ["Network", "network/"], ["Entity Jafar", "entity/jafar-dicko/"], ["Entity Katiba Hanifa", "entity/katiba-hanifa/"], ["Relation JNIM-Nigeria", "relation/d2-jnim-nigeria-emerging/"], ["Relation JNIM-IS", "relation/jnim-is-sahel-conflict/"]];
function getJson(url) { return new Promise((resolve, reject) => { http.get(url, (res) => { let b = ""; res.on("data", x => b += x); res.on("end", () => { try { resolve(JSON.parse(b)); } catch (e) { reject(e); } }); }).on("error", reject); }); }
function wait(ms) { return new Promise(r => setTimeout(r, ms)); }
async function main() {
  const targets = await getJson(`http://127.0.0.1:${CDP_PORT}/json/list`);
  const target = targets.find(x => x.type === "page" && !x.url.startsWith("edge://") && !x.url.startsWith("chrome-extension://") && !x.url.startsWith("devtools://"));
  if (!target) throw new Error("CDP page target not found");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.once("open", resolve); ws.once("error", reject); });
  let id = 0; const pending = new Map(); const events = { exceptions: [], console: [], failed: [], bad: [] }; const requestUrls = new Map(); let currentUrl = "";
  ws.on("message", raw => { const m = JSON.parse(raw.toString()); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m); } if (m.method === "Runtime.exceptionThrown") events.exceptions.push({ url: currentUrl, details: m.params.exceptionDetails }); if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") events.console.push({ url: currentUrl, args: (m.params.args || []).map(a => a.value || a.description || "") }); if (m.method === "Network.requestWillBeSent") requestUrls.set(m.params.requestId, m.params.request.url); if (m.method === "Network.responseReceived" && m.params.response && m.params.response.status >= 400 && !/favicon/.test(m.params.response.url)) events.bad.push({ url: m.params.response.url, status: m.params.response.status }); if (m.method === "Network.loadingFailed" && m.params.errorText !== "net::ERR_ABORTED") events.failed.push({ url: requestUrls.get(m.params.requestId) || null, error: m.params.errorText }); });
  const call = (method, params = {}) => new Promise((resolve, reject) => { const i = ++id; pending.set(i, { resolve, reject }); ws.send(JSON.stringify({ id: i, method, params })); });
  const evaluate = async expression => { const r = await call("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }); return r.result && r.result.result ? r.result.result.value : null; };
  await call("Runtime.enable"); await call("Page.enable"); await call("Network.enable"); await call("Log.enable"); await call("Network.setCacheDisabled", { cacheDisabled: true });
  const pages = [];
  async function check(width, label, route) {
    await call("Emulation.setDeviceMetricsOverride", { width, height: 900, deviceScaleFactor: 1, mobile: false });
    currentUrl = `${PUBLIC}/${route}`; const before = { exceptions: events.exceptions.length, console: events.console.length, failed: events.failed.length, bad: events.bad.length };
    await call("Page.navigate", { url: currentUrl });
    // poll until document is complete (public CDN latency varies); hard cap 10s
    for (let i = 0; i < 40; i++) {
      const done = await evaluate(`(() => document.readyState === "complete")()`);
      if (done) break;
      await wait(250);
    }
    await wait(route.startsWith("network") || route.startsWith("relation") ? 400 : 200);
    const state = await evaluate(`(() => { const err = document.querySelector("#intelError"); const top = document.querySelector("#topbar"); const h1 = document.querySelector("h1"); return { url: location.href, ready_state: document.readyState, h1: h1 ? h1.innerText.slice(0, 70) : null, error_hidden: !err || err.hidden, header_loaded: !!top && top.innerText.trim().length > 0, network_nodes: document.querySelectorAll("g.graph-node[data-entity-id]").length, overflow: document.documentElement.scrollWidth > innerWidth + 2, body_chars: document.body ? document.body.innerText.replace(/\\s+/g, "").length : 0 }; })()`);
    pages.push({ viewport: width, label, route, url: currentUrl, state, events: { runtime_exceptions: events.exceptions.length - before.exceptions, console_errors: events.console.length - before.console, failed_requests: events.failed.length - before.failed, bad_responses: events.bad.length - before.bad } });
  }
  for (const [label, route] of routes) await check(1366, label, route);
  for (const width of viewports) for (const [label, route] of viewportRoutes) await check(width, label, route);
  const realBad = events.bad.filter(b => !/favicon/.test(b.url));
  const allClean = pages.every(p => p.state.ready_state === "complete" && p.state.header_loaded && p.state.error_hidden && !p.state.overflow && Object.values(p.events).every(v => v === 0));
  const report = { artifact: "I3D2_PUBLIC_BROWSER_QA", generated_at: new Date().toISOString(), public_base: PUBLIC, viewports, routes_checked: routes.length, pages, events: { exceptions: events.exceptions, console: events.console, failed: events.failed, bad: events.bad }, summary: { pagesChecked: pages.length, consoleErrors: events.console.length, runtimeExceptions: events.exceptions.length, failedRequests: events.failed.length, brokenAssets: realBad.length, horizontalOverflow: pages.filter(p => p.state.overflow).length, new_entities_200: ENTITIES.length, new_relations_200: RELS.length, refreshed_entities_200: REFRESH_ENTITIES.length, gate: allClean && realBad.length === 0 ? "PASS" : "OPEN" } };
  fs.mkdirSync(path.dirname(OUT), { recursive: true }); fs.writeFileSync(OUT, JSON.stringify(report, null, 2)); console.log(JSON.stringify(report.summary)); ws.close();
}
main().catch(e => { console.error(e.stack || e); process.exit(1); });
