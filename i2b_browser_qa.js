// I2-B browser QA: trust, evidence semantics, freshness display, relation
// ontology, fast-navigation noise separation, responsive, deep routes.
// Uses Edge/Chrome CDP. Event stats are separated:
//   consoleErrors / runtimeExceptions / failedRequests /
//   expectedNavigationAborts / unexpectedUnhandledRejections / stalePageEvents
const fs = require("fs");
const http = require("http");
const path = require("path");

const BASE = "http://127.0.0.1:8784";
const CDP_PORT = process.env.CDP_PORT || "9223";
const OUT = path.join(__dirname, process.env.QA_OUT || "qa-artifacts-i2b");
if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let d = "";
      res.on("data", (c) => (d += c));
      res.on("end", () => { try { resolve(JSON.parse(d)); } catch (e) { reject(e); } });
    }).on("error", reject);
  });
}

async function main() {
  const version = await getJson("http://127.0.0.1:" + CDP_PORT + "/json/version");
  const list = await getJson("http://127.0.0.1:" + CDP_PORT + "/json/list");
  let page = list.find((t) => t.type === "page");
  if (!page) throw new Error("no page target");
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

  const pending = new Map();
  let id = 0;
  const events = { console: [], exceptions: [], failedRequests: [], pageUrl: "" };
  let currentUrl = "";

  const call = (method, params = {}) => new Promise((resolve) => {
    const messageId = ++id;
    const timer = setTimeout(() => { pending.delete(messageId); resolve({ error: true, timeout: method }); }, 20000);
    pending.set(messageId, (m) => { clearTimeout(timer); resolve(m); });
    ws.send(JSON.stringify({ id: messageId, method, params }));
  });

  ws.onmessage = (event) => {
    const m = JSON.parse(event.data.toString());
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
    if (m.method === "Runtime.consoleAPICalled") {
      const level = m.params.type;
      if (level === "error") events.console.push({ url: currentUrl, args: (m.params.args || []).map((a) => a.value || a.description || "") });
    }
    if (m.method === "Runtime.exceptionThrown") {
      const url = m.params.exceptionDetails?.url || currentUrl || "";
      events.exceptions.push({ url: url, text: m.params.exceptionDetails?.text || "exception", desc: m.params.exceptionDetails?.exception?.description || "" });
    }
    if (m.method === "Network.loadingFailed") events.failedRequests.push({ url: currentUrl, error: m.params.errorText });
    if (m.method === "Network.responseReceived" && m.params.response && m.params.response.status >= 400) {
      events.httpErrors = events.httpErrors || [];
      events.httpErrors.push({ url: m.params.response.url, status: m.params.response.status });
    }
  };

  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const evaluate = async (expr) => {
    const r = await call("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.result && r.result.result && r.result.result.value !== undefined) return r.result.result.value;
    if (r.result && r.result.exceptionDetails) return { __err: r.result.exceptionDetails.text };
    return null;
  };

  async function navigate(url, viewport) {
    currentUrl = url;
    if (viewport) await call("Emulation.setDeviceMetricsOverride", { width: viewport.w, height: viewport.h, deviceScaleFactor: 1, mobile: viewport.mobile || false });
    await call("Network.setCacheDisabled", { cacheDisabled: true });
    await call("Page.navigate", { url });
    await wait(900);
    for (let i = 0; i < 60; i++) {
      const ready = await evaluate('document.readyState === "complete" && (!document.querySelector("#intelError") || document.querySelector("#intelError").hidden === true) && window.ASIP_AFRICA && window.ASIP_AFRICA.store && window.ASIP_AFRICA.store.entities.length > 0');
      if (ready) break;
      await wait(200);
    }
    await wait(500);
  }

  async function screenshot(name) {
    const r = await call("Page.captureScreenshot", { format: "png" });
    if (r.result && r.result.data) fs.writeFileSync(`${OUT}/${name}.png`, Buffer.from(r.result.data, "base64"));
  }

  async function pageState(label, extraExpr) {
    const base = await evaluate(`(function(){
      const h = document.querySelector("h1");
      const err = document.querySelector("#intelError");
      return {
        title: document.title,
        heading: h ? h.textContent : null,
        error: (err && !err.hidden) ? err.textContent : null,
        cards: document.querySelectorAll(".intel-card").length,
        rows: document.querySelectorAll(".intel-rel-row").length,
        nodes: document.querySelectorAll(".graph-node").length,
        edges: document.querySelectorAll(".graph-edge-group").length,
        badges: Array.from(document.querySelectorAll(".intel-badge")).map(function (b) { return b.textContent; }).slice(0, 12)
      };
    })()`);
    let extra = null;
    if (extraExpr) extra = await evaluate(extraExpr);
    return { label, ...(base || {}), extra };
  }

  const report = { browser: version.Browser, base: BASE, pages: {}, graph: {}, evidence: {}, fastnav: {}, viewports: {}, events: {}, git: {} };

  // ---- Git preconditions (read-only, from the repo) ----
  const execSync = require("child_process").execSync;
  function git(args) { try { return execSync(`git -C "${__dirname}" ${args}`, { encoding: "utf-8" }).trim(); } catch (e) { return "ERR " + e.message; } }
  report.git.branch = git("rev-parse --abbrev-ref HEAD");
  report.git.head = git("rev-parse HEAD");
  report.git.health = execSync(`"${process.env.PY || "C:/Users/kenan/.workbuddy/binaries/python/versions/3.13.12/python.exe"}" "${__dirname}/scripts/tools/check_git_health.py" "${__dirname}"`, { encoding: "utf-8" }).trim().split("\n").slice(-2).join(" | ");

  await call("Page.enable"); await call("Runtime.enable"); await call("Log.enable"); await call("Network.enable");
  await call("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });

  // ---- core pages ----
  const pages = [
    ["home", "/intelligence/africa/", "(function(){const n=document.querySelector('#metricNote');return n?n.textContent:null;})()"],
    ["regions", "/intelligence/africa/regions/", null],
    ["countries", "/intelligence/africa/countries/", null],
    ["entities", "/intelligence/africa/entities/", null],
    ["relations", "/intelligence/africa/relations/", null],
    ["sources", "/intelligence/africa/sources/", null],
    ["countryChad", "/intelligence/africa/country/chad/", "(function(){const b=document.querySelectorAll('.intel-badge');return Array.from(b).map(function(x){return x.textContent;});})()"],
    ["countrySudan", "/intelligence/africa/country/sudan/", null],
    ["countryMozambique", "/intelligence/africa/country/mozambique/", null],
    ["entityJas", "/intelligence/africa/entity/boko-haram-jas/", "(function(){const b=document.querySelectorAll('.intel-badge');return Array.from(b).map(function(x){return x.textContent;});})()"],
    ["entityIswap", "/intelligence/africa/entity/iswap/", null],
    ["entitySaf", "/intelligence/africa/entity/sudanese-armed-forces/", null],
    ["entityRsf", "/intelligence/africa/entity/rapid-support-forces/", null],
    ["entityIsMoz", "/intelligence/africa/entity/is-mozambique/", null],
    ["entityMnjtf", "/intelligence/africa/entity/mnjtf/", null],
    ["relJasIswap", "/intelligence/africa/relation/jas-iswap-conflict/", null],
    ["relSafRsf", "/intelligence/africa/relation/saf-rsf-war/", null],
    ["relIsMozIs", "/intelligence/africa/relation/is-moz-islamic-state/", null],
    ["relRdfMoz", "/intelligence/africa/relation/rdf-mozambique-fadm-cooperate/", null],
  ];
  for (const [key, path, extra] of pages) {
    await navigate(BASE + path);
    report.pages[key] = await pageState(key, extra);
    await screenshot("page-" + key);
  }

  // ---- evidence / time semantics checks (entity page) ----
  await navigate(BASE + "/intelligence/africa/entity/boko-haram-jas/");
  report.evidence.entityJas = await evaluate(`(function(){
    const badges = Array.from(document.querySelectorAll(".intel-badge")).map(function (b) { return b.textContent; });
    const note = document.querySelector(".profile-standfirst-label");
    const ib = document.querySelector("#entityInfobox");
    const rows = ib ? Array.from(ib.querySelectorAll(".ib-row")).map(function (r) { return r.textContent.replace(/\\s+/g, " ").trim(); }) : [];
    return { badges: badges, freshnessNote: note ? note.textContent : null, infoboxRows: rows };
  })()`);
  await screenshot("evidence-jas");
  await navigate(BASE + "/intelligence/africa/country/sudan/");
  report.evidence.countrySudan = await evaluate(`(function(){
    const badges = Array.from(document.querySelectorAll(".intel-badge")).map(function (b) { return b.textContent; });
    const rows = Array.from(document.querySelectorAll("#countryEvidence .ib-row")).map(function (r) { return r.textContent.replace(/\\s+/g, " ").trim(); });
    return { badges: badges, evidenceRows: rows };
  })()`);
  await screenshot("evidence-sudan");

  // ---- network: pledge label, filters, center switching ----
  await navigate(BASE + "/intelligence/africa/network/?focus=actor-jnim");
  report.graph.jnim = await pageState("graph jnim", "(function(){return {hint:document.querySelector('#graphHint')?.textContent,pledgeEdges:Array.from(document.querySelectorAll('.graph-edge-group')).filter(function(g){return g.textContent.includes('宣誓效忠')||g.getAttribute('aria-label')?.includes('宣誓效忠');}).length};})()");
  await screenshot("network-jnim");

  // click a node (ISWAP via DOM event to avoid coordinates)
  await evaluate(`(function(){const n=document.querySelector('.graph-node[data-entity-id="actor-iswap"]'); if(n) n.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));})()`);
  await wait(900);
  report.graph.iswapCenter = await pageState("graph iswap center");
  await screenshot("network-iswap");

  // L1 core view
  await evaluate(`(function(){const v=document.querySelector('[data-view-filter="core"]'); if(v) v.click();})()`);
  await wait(800);
  report.graph.coreView = await pageState("core view", "(function(){return document.querySelector('#importanceStats')?.textContent;})()");
  await screenshot("network-core");

  // full view
  await evaluate(`(function(){const v=document.querySelector('[data-view-filter="full"]'); if(v) v.click();})()`);
  await wait(800);
  report.graph.fullView = await pageState("full view", "(function(){return document.querySelector('#importanceStats')?.textContent;})()");
  await screenshot("network-full");

  // edge click → relation detail with freshness badge
  const edgeClick = await evaluate(`(function(){
    const g = document.querySelector('.graph-edge-group');
    if (!g) return null;
    g.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
    return true;
  })()`);
  await wait(500);
  report.graph.edgeClick = await evaluate(`(function(){
    const info = document.querySelector('#relationInfo');
    return info ? info.textContent.replace(/\\s+/g, " ").trim().slice(0, 260) : null;
  })()`);
  await screenshot("network-edge-click");

  // ---- fast navigation test (10 rapid navigations) ----
  const clearCounts = () => { events.console.length = 0; events.exceptions.length = 0; events.failedRequests.length = 0; };
  clearCounts();
  const navStart = Date.now();
  const rapid = ["/intelligence/africa/", "/intelligence/africa/region/central-sahel/", "/intelligence/africa/country/chad/", "/intelligence/africa/entity/boko-haram-jas/", "/intelligence/africa/relation/jas-iswap-conflict/", "/intelligence/africa/network/?focus=actor-iswap", "/intelligence/africa/country/sudan/", "/intelligence/africa/entity/rapid-support-forces/", "/intelligence/africa/relation/saf-rsf-war/", "/intelligence/africa/"];
  for (const p of rapid) {
    await call("Page.navigate", { url: BASE + p });
    await wait(260);
  }
  await wait(2500);
  const navAborts = events.failedRequests.filter((f) => f.error === "net::ERR_ABORTED").length;
  const realFailures = events.failedRequests.filter((f) => f.error !== "net::ERR_ABORTED");
  const classify = (ex) => {
    if (ex.url && ex.url.startsWith("chrome-extension://")) return "browserExtension";
    if (ex.url && ex.url.startsWith(BASE)) return "pageEvent";
    return "other";
  };
  const extNoise = events.exceptions.filter((e) => classify(e) === "browserExtension").length;
  const pageEvents = events.exceptions.filter((e) => classify(e) === "pageEvent");
  report.fastnav = {
    durationMs: Date.now() - navStart,
    expectedNavigationAborts: navAborts,
    unexpectedFailedRequests: realFailures.length,
    consoleErrors: events.console.length,
    runtimeExceptions: events.exceptions.length,
    unexpectedUnhandledRejections: pageEvents.length,
    browserExtensionExceptions: extNoise,
    otherExceptions: events.exceptions.length - extNoise - pageEvents.length,
    realFailureSamples: realFailures.slice(0, 5),
    consoleSamples: events.console.slice(0, 5),
    exceptionUrls: [...new Set(pageEvents.map((e) => e.url))],
    exceptionSamples: pageEvents.slice(0, 5).map((e) => e.desc || e.text),
  };

  // single page stable load must be clean
  clearCounts();
  await navigate(BASE + "/intelligence/africa/entity/iswap/");
  await wait(2000);
  const stablePageEvents = events.exceptions.filter((e) => classify(e) === "pageEvent");
  report.fastnav.singlePageStable = {
    consoleErrors: events.console.length,
    runtimeExceptions: events.exceptions.length,
    unexpectedUnhandledRejections: stablePageEvents.length,
    browserExtensionExceptions: events.exceptions.filter((e) => classify(e) === "browserExtension").length,
    failedRequests: events.failedRequests.filter((f) => f.error !== "net::ERR_ABORTED").length,
  };
  await screenshot("stable-iswap");

  // ---- viewports ----
  for (const [name, vp] of [["1920", { w: 1920, h: 1080 }], ["1366", { w: 1366, h: 768 }], ["768", { w: 768, h: 1024, mobile: true }], ["390", { w: 390, h: 844, mobile: true }]]) {
    await navigate(BASE + "/intelligence/africa/country/chad/", vp);
    const v = await evaluate(`(function(){return {innerWidth: window.innerWidth, bodyWidth: document.body.scrollWidth, overflow: document.body.scrollWidth > window.innerWidth + 4};})()`);
    report.viewports[name] = v;
    await screenshot("viewport-" + name);
  }

  // deep routes direct refresh
  const deep = ["/intelligence/africa/relation/jas-iswap-conflict/", "/intelligence/africa/entity/boko-haram-jas/", "/intelligence/africa/network/?focus=actor-jnim"];
  report.deepRoutes = {};
  for (const p of deep) {
    await navigate(BASE + p);
    report.deepRoutes[p] = await pageState("deep " + p);
  }

  report.events = events;

  fs.writeFileSync(`${OUT}/browser-qa-results.json`, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({
    browser: report.browser, git: report.git,
    pages: Object.fromEntries(Object.entries(report.pages).map(([k, v]) => [k, { heading: v?.heading, error: v?.error, cards: v?.cards, rows: v?.rows, nodes: v?.nodes }])),
    evidence: report.evidence, graph: report.graph, fastnav: report.fastnav,
    viewports: report.viewports, deepRoutes: Object.keys(report.deepRoutes), events: report.events
  }, null, 2));
  ws.close();
  process.exit(0);
}

main().catch((e) => { console.error("QA ERROR", e); process.exit(1); });
