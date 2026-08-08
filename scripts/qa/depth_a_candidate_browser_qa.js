const http = require("http");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");
const PUBLIC = process.env.PUBLIC_BASE || "http://127.0.0.1:4176/intelligence/africa";
const CDP_PORT = Number(process.env.CDP_PORT || 9232);
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-depth-a", "candidate-browser-qa.json");
const ENTITIES = ["jnim", "is-sahel", "amadou-koufa", "katiba-macina", "iyad-ag-ghali", "aqim", "al-mourabitoun", "ansarul-islam", "fla", "africa-corps", "wagner-group"];
const RELS = ["jnim-is-sahel-conflict", "jnim-alqaida-affiliate", "jnim-aqim-constituent", "jnim-katiba-constituent", "jnim-iyad-ag-ghali-led", "amadou-koufa-jnim-senior", "d1-ansarul-jnim-constituent", "d1-fla-jnim-cooperation", "d1-africa-corps-fama-coop", "d1-africa-corps-wagner-history", "amadou-koufa-katiba-founder"];
const routes = [["Africa root", ""], ["Entities index", "entities/"], ["Relations index", "relations/"], ["Network", "network/"]].concat(
  ENTITIES.map(s => ["entity " + s, "entity/" + s + "/"]),
  RELS.map(s => ["relation " + s, "relation/" + s + "/"])
);
const viewports = [1920, 1366, 768, 390];
const viewportRoutes = [["Africa root", ""], ["Network", "network/"], ["Entity JNIM", "entity/jnim/"], ["Entity Koufa", "entity/amadou-koufa/"], ["Relation JNIM-IS", "relation/jnim-is-sahel-conflict/"], ["Relation FLA-JNIM", "relation/d1-fla-jnim-cooperation/"]];
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
    for (let i = 0; i < 40; i++) {
      const done = await evaluate(`(() => document.readyState === "complete")()`);
      if (done) break;
      await wait(250);
    }
    await wait(route.startsWith("network") || route.startsWith("relation") ? 400 : 200);
    const state = await evaluate(`(() => { const err = document.querySelector("#intelError"); const top = document.querySelector("#topbar"); const h1 = document.querySelector("h1"); const analysis = document.querySelector(".intel-analysis-card"); const watch = document.querySelector(".intel-watch-card"); const mBadge = document.querySelector(".intel-badge.m-e3_full_encyclopedia, .intel-badge.m-r3_full_relationship_intelligence, .intel-badge.m-e2_developed, .intel-badge.m-r2_developed_relationship"); return { url: location.href, ready_state: document.readyState, h1: h1 ? h1.innerText.slice(0, 60) : null, error_hidden: !err || err.hidden, header_loaded: !!top && top.innerText.trim().length > 0, analysis_partition: !!analysis, watch_partition: !!watch, maturity_badge: !!mBadge, lead_first: !!document.querySelector(".profile-lead, .intel-lead"), network_nodes: document.querySelectorAll("g.graph-node[data-entity-id]").length, overflow: document.documentElement.scrollWidth > innerWidth + 2 }; })()`);
    pages.push({ viewport: width, label, route, url: currentUrl, state, events: { runtime_exceptions: events.exceptions.length - before.exceptions, console_errors: events.console.length - before.console, failed_requests: events.failed.length - before.failed, bad_responses: events.bad.length - before.bad } });
  }
  for (const [label, route] of routes) await check(1366, label, route);
  for (const width of viewports) for (const [label, route] of viewportRoutes) await check(width, label, route);
  const realBad = events.bad.filter(b => !/favicon/.test(b.url));
  const allClean = pages.every(p => p.state.ready_state === "complete" && p.state.header_loaded && p.state.error_hidden && !p.state.overflow && Object.values(p.events).every(v => v === 0));
  const upgraded_pages = pages.filter(p => p.label.startsWith("entity ") || p.label.startsWith("relation "));
  const separation_ok = upgraded_pages.every(p => p.state.maturity_badge);
  const report = { artifact: "DEPTHA_CANDIDATE_BROWSER_QA", generated_at: new Date().toISOString(), public_base: PUBLIC, viewports, routes_checked: routes.length, pages, events: { exceptions: events.exceptions, console: events.console, failed: events.failed, bad: events.bad }, summary: { pagesChecked: pages.length, consoleErrors: events.console.length, runtimeExceptions: events.exceptions.length, failedRequests: events.failed.length, brokenAssets: realBad.length, horizontalOverflow: pages.filter(p => p.state.overflow).length, upgradedPagesWithMaturityBadge: upgraded_pages.filter(p => p.state.maturity_badge).length + "/" + upgraded_pages.length, analysisPartitions: pages.filter(p => p.state.analysis_partition).length, watchPartitions: pages.filter(p => p.state.watch_partition).length, gate: allClean && realBad.length === 0 && separation_ok ? "PASS" : "OPEN" } };
  fs.mkdirSync(path.dirname(OUT), { recursive: true }); fs.writeFileSync(OUT, JSON.stringify(report, null, 2)); console.log(JSON.stringify(report.summary)); ws.close();
}
main().catch(e => { console.error(e.stack || e); process.exit(1); });
