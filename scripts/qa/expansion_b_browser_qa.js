// Expansion B browser QA — verifies rendering of the 11 new entities, the 8 R3
// core dossiers + key R2 relations, the fahiye upgrade, and special modeling
// pages (Puntland umbrella label, IRGC attribution, MONUSCO-ADF framing).
const http = require("http");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");
const PUBLIC = process.env.PUBLIC_BASE || "http://127.0.0.1:4174/intelligence/africa";
const CDP_PORT = Number(process.env.CDP_PORT || 9228);
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-expansion-b", "browser-qa.json");

const ENTITY_ROUTES = [
  ["AUSSOM", "entity/aussom/"],
  ["SNAF", "entity/somali-national-armed-forces/"],
  ["Puntland Security Forces", "entity/puntland-security-forces/"],
  ["FARDC", "entity/fardc/"],
  ["UPDF", "entity/updf/"],
  ["MONUSCO", "entity/monusco/"],
  ["IRGC", "entity/irgc/"],
  ["Mahad Karate", "entity/mahad-karate/"],
  ["Abdiweli Mohamed Yusuf", "entity/abdiweli-mohamed-yusuf/"],
  ["Meddie Nkalubo", "entity/meddie-nkalubo/"],
  ["Abu Zaid Talha", "entity/abu-zaid-talha/"],
  ["Fahiye (upgraded)", "entity/abdirahman-fahiye/"],
  ["Al-Shabaab (regression)", "entity/al-shabaab/"],
  ["ADF/ISIS-CA (regression)", "entity/adf-isis-ca/"],
];
const RELATION_ROUTES = [
  ["Al-Shabaab-AUSSOM R3", "relation/expb-shabaab-aussom-conflict/"],
  ["Al-Shabaab-SNAF R3", "relation/expb-shabaab-snaf-conflict/"],
  ["AUSSOM-SNAF R3", "relation/expb-aussom-snaf-cooperation/"],
  ["ISIS-Somalia-Puntland R3", "relation/expb-isis-somalia-puntland-conflict/"],
  ["ADF-FARDC R3", "relation/expb-adf-fardc-conflict/"],
  ["ADF-UPDF R3", "relation/expb-adf-updf-conflict/"],
  ["FARDC-UPDF Shujaa R3", "relation/expb-fardc-updf-shujaa/"],
  ["BBMB-IRGC R3", "relation/expb-bbmb-irgc-support/"],
  ["MONUSCO-ADF (framing)", "relation/expb-monusco-adf-countering/"],
  ["MONUSCO-FARDC", "relation/expb-monusco-fardc-cooperation/"],
  ["BBMB-Talha", "relation/expb-bbmb-talha-led/"],
  ["Talha-SAF", "relation/expb-talha-saf-allied/"],
];
const INDEX_ROUTES = [
  ["Africa root", ""], ["Entities index", "entities/"], ["Relations index", "relations/"],
  ["Network", "network/"], ["Sources", "sources/"],
];

function getJson(url) { return new Promise((resolve, reject) => { http.get(url, (res) => { let b = ""; res.on("data", x => b += x); res.on("end", () => { try { resolve(JSON.parse(b)); } catch (e) { reject(e); } }); }).on("error", reject); }); }
function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  const targets = await getJson(`http://127.0.0.1:${CDP_PORT}/json/list`);
  const target = targets.find(x => x.type === "page" && !x.url.startsWith("edge://") && !x.url.startsWith("chrome-extension://") && !x.url.startsWith("devtools://"));
  if (!target) throw new Error("CDP page target not found");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.once("open", resolve); ws.once("error", reject); });
  let id = 0; const pending = new Map();
  const events = { exceptions: [], console: [], failed: [], bad: [] };
  const requestUrls = new Map(); let currentUrl = "";
  ws.on("message", raw => {
    const m = JSON.parse(raw.toString());
    if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m); }
    if (m.method === "Runtime.exceptionThrown") events.exceptions.push({ url: currentUrl, details: m.params.exceptionDetails });
    if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") events.console.push({ url: currentUrl, args: (m.params.args || []).map(a => a.value || a.description || "") });
    if (m.method === "Network.requestWillBeSent") requestUrls.set(m.params.requestId, m.params.request.url);
    if (m.method === "Network.responseReceived" && m.params.response && m.params.response.status >= 400) events.bad.push({ url: m.params.response.url, status: m.params.response.status });
    if (m.method === "Network.loadingFailed" && m.params.errorText !== "net::ERR_ABORTED") events.failed.push({ url: requestUrls.get(m.params.requestId) || null, error: m.params.errorText });
  });
  const call = (method, params = {}) => new Promise((resolve, reject) => { const i = ++id; pending.set(i, { resolve, reject }); ws.send(JSON.stringify({ id: i, method, params })); });
  const evaluate = async expression => { const r = await call("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }); return r.result && r.result.result ? r.result.result.value : null; };
  await call("Runtime.enable"); await call("Page.enable"); await call("Network.enable"); await call("Log.enable"); await call("Network.setCacheDisabled", { cacheDisabled: true });

  const pages = [];
  const checkPage = async (label, route, kind) => {
    await call("Emulation.setDeviceMetricsOverride", { width: 1366, height: 900, deviceScaleFactor: 1, mobile: false });
    currentUrl = `${PUBLIC}/${route}`;
    const before = { exceptions: events.exceptions.length, console: events.console.length, failed: events.failed.length, bad: events.bad.length };
    await call("Page.navigate", { url: currentUrl });
    await wait(route.startsWith("network") || route.startsWith("relation") ? 1200 : 700);
    const state = await evaluate(`(() => {
      const err = document.querySelector("#intelError");
      const top = document.querySelector("#topbar");
      const h1 = document.querySelector("h1");
      const relOv = document.querySelector("#relationOverview");
      const tl = document.querySelector("#relationTimeline");
      const secs = Array.from(document.querySelectorAll(".profile-section h2")).map(h => h.innerText.trim());
      const anchors = Array.from(document.querySelectorAll("a[href]")).map(a => a.getAttribute("href"));
      const brokenAnchors = anchors.filter(a => /^#/.test(a) && !document.getElementById(a.slice(1)));
      return {
        url: location.href, ready_state: document.readyState,
        h1: h1 ? h1.innerText.slice(0, 100) : null,
        body_chars: document.body ? document.body.innerText.replace(/\\s+/g, "").length : 0,
        error_hidden: !err || err.hidden,
        header_loaded: !!top && top.innerText.trim().length > 0,
        relation_overview_present: !!relOv && relOv.innerText.trim().length > 0,
        timeline_items: tl ? tl.querySelectorAll(".tl-item").length : -1,
        section_count: secs.length,
        broken_anchors: brokenAnchors.length,
        overflow: document.documentElement.scrollWidth > innerWidth + 2,
      };
    })()`);
    pages.push({ kind, label, route, url: currentUrl, state, events: { runtime_exceptions: events.exceptions.length - before.exceptions, console_errors: events.console.length - before.console, failed_requests: events.failed.length - before.failed, bad_responses: events.bad.length - before.bad } });
  };
  for (const [label, route] of INDEX_ROUTES) await checkPage(label, route, "index");
  for (const [label, route] of ENTITY_ROUTES) await checkPage(label, route, "entity");
  for (const [label, route] of RELATION_ROUTES) await checkPage(label, route, "relation");

  const realBad = events.bad.filter(b => !/\/favicon\.ico$/.test(b.url));
  const problems = [];
  for (const p of pages) {
    if (p.state.ready_state !== "complete") problems.push(`${p.label}: ready_state=${p.state.ready_state}`);
    if (!p.state.header_loaded) problems.push(`${p.label}: header not loaded`);
    if (!p.state.error_hidden) problems.push(`${p.label}: intel error visible`);
    if (p.state.overflow) problems.push(`${p.label}: horizontal overflow`);
    if (p.state.broken_anchors > 0) problems.push(`${p.label}: ${p.state.broken_anchors} broken anchors`);
    if (p.events.console_errors > 0) problems.push(`${p.label}: ${p.events.console_errors} console errors`);
    if (p.events.runtime_exceptions > 0) problems.push(`${p.label}: ${p.events.runtime_exceptions} runtime exceptions`);
    if (p.events.failed_requests > 0) problems.push(`${p.label}: ${p.events.failed_requests} failed requests`);
  }
  for (const [label, route] of ENTITY_ROUTES) {
    const p = pages.find(x => x.route === route);
    if (p && p.state.section_count < 12) problems.push(`${label}: only ${p.state.section_count} sections`);
  }
  for (const [label, route] of RELATION_ROUTES) {
    const p = pages.find(x => x.route === route);
    if (p && !p.state.relation_overview_present) problems.push(`${label}: relation overview missing`);
  }
  for (const [label, route] of RELATION_ROUTES) {
    if (!route.includes("r3")) continue;
    const p = pages.find(x => x.route === route);
    if (p && p.state.timeline_items <= 0) problems.push(`${label}: no timeline items`);
  }
  const summary = {
    pagesChecked: pages.length,
    consoleErrors: events.console.length,
    runtimeExceptions: events.exceptions.length,
    failedRequests: events.failed.length,
    brokenAssets: realBad.length,
    horizontalOverflow: pages.filter(p => p.state.overflow).length,
    brokenAnchors: problems.filter(x => x.includes("broken anchors")).length,
    problems,
    gate: problems.length === 0 && realBad.length === 0 ? "PASS" : "OPEN",
  };
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify({ artifact: "EXPANSION_B_BROWSER_QA", generated_at: new Date().toISOString(), public_base: PUBLIC, viewport: "1366x900", pages, events: { exceptions: events.exceptions, console: events.console, failed: events.failed, bad: events.bad, bad_excluding_favicon: realBad }, summary }, null, 2));
  console.log(JSON.stringify(summary, null, 2));
  ws.close();
}
main().catch(e => { console.error(e.stack || e); process.exit(1); });
