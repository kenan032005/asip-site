const http = require("http");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");
const PUBLIC = process.env.PUBLIC_BASE || "http://127.0.0.1:4173/intelligence/africa";
const CDP_PORT = Number(process.env.CDP_PORT || 9226);
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-i3c", "representative-browser-qa.json");
const routes = [
  ["Africa root", ""], ["Network", "network/"], ["Countries index", "countries/"], ["Country detail", "country/ethiopia/"],
  ["Entities index", "entities/"], ["Entity detail", "entity/jnim/"], ["Regions index", "regions/"], ["Region detail", "region/central-sahel/"],
  ["Relations index", "relations/"], ["Relation detail", "relation/jnim-is-sahel-hostile/"], ["Sources", "sources/"]
];
function getJson(url) { return new Promise((resolve, reject) => { http.get(url, (res) => { let b = ""; res.on("data", x => b += x); res.on("end", () => { try { resolve(JSON.parse(b)); } catch (e) { reject(e); } }); }).on("error", reject); }); }
function wait(ms) { return new Promise(r => setTimeout(r, ms)); }
async function main() {
  const targets = await getJson(`http://127.0.0.1:${CDP_PORT}/json/list`);
  const target = targets.find(x => x.type === "page" && x.url !== "about:blank");
  if (!target) throw new Error("CDP page target not found");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.once("open", resolve); ws.once("error", reject); });
  let id = 0; const pending = new Map(); const events = { exceptions: [], console: [], failed: [], bad: [], rejections: [] }; const requestUrls = new Map(); let currentUrl = "";
  ws.on("message", raw => { const m = JSON.parse(raw.toString()); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m); } if (m.method === "Runtime.exceptionThrown") events.exceptions.push({ url: currentUrl, details: m.params.exceptionDetails }); if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") events.console.push({ url: currentUrl, args: (m.params.args || []).map(a => a.value || a.description || "") }); if (m.method === "Network.requestWillBeSent") requestUrls.set(m.params.requestId, m.params.request.url); if (m.method === "Network.responseReceived" && m.params.response && m.params.response.status >= 400) events.bad.push({ url: m.params.response.url, status: m.params.response.status }); if (m.method === "Network.loadingFailed" && m.params.errorText !== "net::ERR_ABORTED") events.failed.push({ url: requestUrls.get(m.params.requestId) || null, error: m.params.errorText }); });
  const call = (method, params = {}) => new Promise((resolve, reject) => { const i = ++id; pending.set(i, { resolve, reject }); ws.send(JSON.stringify({ id: i, method, params })); });
  const evaluate = async expression => { const r = await call("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }); return r.result && r.result.result ? r.result.result.value : null; };
  await call("Runtime.enable"); await call("Page.enable"); await call("Network.enable"); await call("Log.enable"); await call("Network.setCacheDisabled", { cacheDisabled: true });
  const pages = [];
  for (const [label, route] of routes) {
    await call("Emulation.setDeviceMetricsOverride", { width: 1366, height: 900, deviceScaleFactor: 1, mobile: false });
    currentUrl = `${PUBLIC}/${route}`; const before = { exceptions: events.exceptions.length, console: events.console.length, failed: events.failed.length, bad: events.bad.length };
    await call("Page.navigate", { url: currentUrl }); await wait(route === "network/" ? 1400 : 700);
    const state = await evaluate(`(() => { const top = document.querySelector("#topbar"); const footer = document.querySelector("footer.site"); const err = document.querySelector("#intelError"); const hint = document.querySelector("#graphHint"); const body = document.body ? document.body.innerText.replace(/\\s+/g, "").length : 0; return { url: location.href, ready_state: document.readyState, topbar_present: !!top, topbar_text_length: top ? top.innerText.trim().length : 0, equivalent_public_header_loaded: !!top && top.innerText.trim().length > 0, footer_present: !!footer, body_chars: body, error_hidden: !err || err.hidden, graph_ready: hint ? hint.textContent : null, network_nodes: document.querySelectorAll("g.graph-node[data-entity-id]").length, overflow: document.documentElement.scrollWidth > innerWidth + 2 }; })()`);
    const rejection = await evaluate("window.__ASIP_QA_REJECTIONS || []");
    pages.push({ label, route, url: currentUrl, state, events: { runtime_exceptions: events.exceptions.length - before.exceptions, console_errors: events.console.length - before.console, failed_requests: events.failed.length - before.failed, bad_responses: events.bad.length - before.bad, unhandled_rejections: rejection.length } });
  }
  const checks = pages.every(p => p.state.ready_state === "complete" && p.state.equivalent_public_header_loaded && p.state.error_hidden && !p.state.overflow && Object.values(p.events).every(v => v === 0));
  const report = { artifact: "I3C_REPRESENTATIVE_BROWSER_QA", generated_at: new Date().toISOString(), public_base: PUBLIC, viewport: 1366, pages, summary: { pagesChecked: pages.length, consoleErrors: events.console.length, runtimeExceptions: events.exceptions.length, failedRequests: events.failed.length, brokenAssets: events.bad.length, horizontalOverflow: pages.filter(p => p.state.overflow).length, unexpectedUnhandledRejections: pages.reduce((n,p) => n + p.events.unhandled_rejections, 0), equivalent_public_header_all_pass: pages.every(p => p.state.equivalent_public_header_loaded), gate: checks ? "PASS" : "OPEN" } };
  fs.mkdirSync(path.dirname(OUT), { recursive: true }); fs.writeFileSync(OUT, JSON.stringify(report, null, 2)); console.log(JSON.stringify(report.summary)); ws.close();
}
main().catch(e => { console.error(e.stack || e); process.exit(1); });
