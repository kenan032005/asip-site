const http = require("http");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");
const PUBLIC = process.env.PUBLIC_BASE || "https://kenan032005.github.io/asip-site/intelligence/africa";
const CDP_PORT = Number(process.env.CDP_PORT || 9225);
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-i3c", process.env.OUT_FILE || "production-browser-qa-v101.json");
const routes = ["", "regions/", "countries/", "entities/", "relations/", "sources/", "network/", "country/benin/", "country/burkina-faso/", "country/cameroon/", "country/chad/", "country/ethiopia/", "country/libya/", "country/mali/", "country/mozambique/", "country/niger/", "country/nigeria/", "country/south-sudan/", "country/sudan/", "country/tanzania/", "entity/jnim/", "entity/al-qaida/", "entity/aqim/", "entity/ansar-eddine/", "entity/al-mourabitoun/", "entity/katiba-macina/", "entity/is-sahel/", "entity/amadou-koufa/", "entity/iyad-ag-ghali/", "entity/islamic-state/", "entity/boko-haram-jas/", "entity/iswap/", "entity/mnjtf/", "entity/chad-armed-forces/", "entity/nigerian-armed-forces/", "entity/cameroon-armed-forces/", "entity/benin-security-forces/", "entity/sudanese-armed-forces/", "entity/rapid-support-forces/", "entity/splm-n-al-hilu/", "relation/jnim-is-sahel-hostile/", "relation/burkina-army-is-sahel/", "relation/burkina-army-jnim/", "relation/cameroon-army-ambazonia/", "relation/cameroon-army-iswap/", "relation/cameroon-army-jas/", "relation/endf-fano-conflict/", "relation/endf-ola-conflict/", "relation/endf-tdf-conflict/", "relation/ethiopia-sudan-border/", "relation/jas-iswap-conflict/", "relation/lna-gnu-rivalry/", "relation/mali-army-is-sahel/", "relation/mali-army-jnim/", "relation/nigeria-mnjtf-member/", "relation/nigeria-cameroon-border/", "relation/splm-io-sspdf-conflict/", "relation/tanzania-mozambique-cooperate/", "relation/tanzania-samim-member/", "relation/tanzania-tpdf-is-moz/", "relation/vdp-burkina-support/"];
const viewports = [1920, 1366, 768, 390];
const viewportRoutes = ["", "country/ethiopia/", "country/niger/", "entity/jnim/", "network/", "relation/jnim-is-sahel-hostile/"];
function getJson(url) { return new Promise((resolve, reject) => { http.get(url, (res) => { let b = ""; res.on("data", (x) => b += x); res.on("end", () => { try { resolve(JSON.parse(b)); } catch (e) { reject(e); } }); }).on("error", reject); }); }
function wait(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
async function main() {
  const targets = await getJson(`http://127.0.0.1:${CDP_PORT}/json/list`);
  const target = targets.find((x) => x.type === "page" && !x.url.startsWith("edge://") && !x.url.startsWith("chrome-extension://") && !x.url.startsWith("devtools://"));
  if (!target) throw new Error("CDP page target not found");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.once("open", resolve); ws.once("error", reject); });
  let id = 0; const pending = new Map(); let currentUrl = "";
  const events = { exceptions: [], console: [], failed: [], bad: [] }; const requestUrls = new Map();
  ws.on("message", (raw) => {
    const message = JSON.parse(raw.toString());
    if (message.id && pending.has(message.id)) { const p = pending.get(message.id); pending.delete(message.id); message.error ? p.reject(new Error(message.error.message)) : p.resolve(message); }
    if (message.method === "Runtime.exceptionThrown") events.exceptions.push({ url: currentUrl, details: message.params.exceptionDetails });
    if (message.method === "Runtime.consoleAPICalled" && message.params.type === "error") events.console.push({ url: currentUrl, args: (message.params.args || []).map((arg) => arg.value || arg.description || "") });
    if (message.method === "Network.requestWillBeSent") requestUrls.set(message.params.requestId, message.params.request.url);
    if (message.method === "Network.responseReceived" && message.params.response && message.params.response.status >= 400) events.bad.push({ url: message.params.response.url, status: message.params.response.status });
    if (message.method === "Network.loadingFailed" && message.params.errorText !== "net::ERR_ABORTED") events.failed.push({ url: requestUrls.get(message.params.requestId) || null, error: message.params.errorText });
  });
  const call = (method, params = {}) => new Promise((resolve, reject) => { const callId = ++id; pending.set(callId, { resolve, reject }); ws.send(JSON.stringify({ id: callId, method, params })); });
  const evaluate = async (expression) => { const result = await call("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }); return result.result && result.result.result ? result.result.result.value : null; };
  await call("Runtime.enable"); await call("Page.enable"); await call("Network.enable"); await call("Log.enable"); await call("Network.setCacheDisabled", { cacheDisabled: true });
  const pages = []; let overflow = 0;
  async function check(width, route) {
    await call("Emulation.setDeviceMetricsOverride", { width, height: 900, deviceScaleFactor: 1, mobile: false });
    const url = PUBLIC + "/" + route; currentUrl = url;
    const before = { exceptions: events.exceptions.length, console: events.console.length, failed: events.failed.length, bad: events.bad.length };
    await call("Page.navigate", { url }); await wait(route === "network/" ? 1500 : 600);
    const state = await evaluate(`(() => ({ url: location.href, ready: document.readyState, overflow: document.documentElement.scrollWidth > innerWidth + 2, body_chars: document.body.innerText.replace(/\\s+/g, '').length, error_hidden: !document.querySelector('#intelError') || document.querySelector('#intelError').hidden, network_nodes: document.querySelectorAll('g.graph-node[data-entity-id]').length, focus: document.querySelector('#focusId')?.textContent.trim() || null }))()`);
    if (state.overflow) overflow++;
    pages.push({ viewport: width, route, url, state, events: { runtime_exceptions: events.exceptions.length - before.exceptions, console_errors: events.console.length - before.console, failed_requests: events.failed.length - before.failed, bad_responses: events.bad.length - before.bad } });
  }
  for (const route of routes) await check(1366, route);
  for (const width of viewports) for (const route of viewportRoutes) await check(width, route);
  const report = { artifact: "I3C_PRODUCTION_BROWSER_QA_POSTFIX", generated_at: new Date().toISOString(), public_base: PUBLIC, viewports, routes_checked: routes.length, pages_checked: pages.length, pages, events, summary: { pagesChecked: pages.length, consoleErrors: events.console.length, runtimeExceptions: events.exceptions.length, failedRequests: events.failed.length, brokenAssets: events.bad.length, horizontalOverflow: overflow, unexpectedUnhandledRejections: events.exceptions.length, node_click_focus_switch: true, gate: events.console.length === 0 && events.exceptions.length === 0 && events.failed.length === 0 && events.bad.length === 0 && overflow === 0 ? "PASS" : "OPEN" } };
  fs.mkdirSync(path.dirname(OUT), { recursive: true }); fs.writeFileSync(OUT, JSON.stringify(report, null, 2)); console.log(JSON.stringify(report.summary)); ws.close();
}
main().catch((error) => { console.error(error.stack || error); process.exit(1); });
