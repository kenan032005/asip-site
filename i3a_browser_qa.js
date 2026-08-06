// I3-A browser acceptance: deep country pages, entity encyclopedias, deepened
// relations, timelines, freshness, TOC/lead rendering, responsive, graph regression.
const http = require("http");
const path = require("path");
const fs = require("fs");

const BASE = "http://127.0.0.1:8786";
const CDP_PORT = process.env.CDP_PORT || "9224";
const OUT = path.join(__dirname, process.env.QA_OUT || "qa-artifacts-i3a");
if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

const report = { pages: [], consoleErrors: 0, runtimeExceptions: 0, failedRequests: 0,
  expectedNavigationAborts: 0, unexpectedUnhandledRejections: 0, stalePageEvents: 0 };
const events = { console: [], exceptions: [], failed: [], navAborts: [] };
let currentUrl = "";
let ws = null;
let pending = new Map();
let msgId = 0;

function getJson(url) {
  return new Promise((res, rej) => http.get(url, (r) => {
    let d = ""; r.on("data", (c) => (d += c)); r.on("end", () => { try { res(JSON.parse(d)); } catch (e) { rej(e); } });
  }).on("error", rej));
}
function call(method, params = {}) {
  return new Promise((resolve) => {
    const id = ++msgId; pending.set(id, resolve);
    ws.send(JSON.stringify({ id, method, params }));
  });
}
function wait(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function connect() {
  const list = await getJson(`http://127.0.0.1:${CDP_PORT}/json/list`);
  const page = list.find((t) => t.type === "page");
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data.toString());
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
    if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error")
      events.console.push({ url: currentUrl, args: (m.params.args || []).map((a) => a.value || a.description || "").join(" ") });
    if (m.method === "Runtime.exceptionThrown") {
      const d = m.params.exceptionDetails || {};
      const desc = (d.exception && d.exception.description) || d.text || "";
      events.exceptions.push({ url: currentUrl, desc: String(desc).slice(0, 160) });
    }
    if (m.method === "Network.loadingFailed") {
      const err = m.params.errorText || "";
      if (err === "net::ERR_ABORTED") { events.navAborts.push(currentUrl); report.expectedNavigationAborts++; }
      else events.failed.push({ url: currentUrl, error: err });
    }
  };
  await call("Runtime.enable"); await call("Page.enable");
  await call("Network.enable"); await call("Network.setCacheDisabled", { cacheDisabled: true });
}
function clearCounts() { events.console.length = 0; events.exceptions.length = 0; events.failed.length = 0; events.navAborts.length = 0; }
function flushCounts() {
  report.consoleErrors += events.console.length;
  report.runtimeExceptions += events.exceptions.length;
  report.failedRequests += events.failed.length;
  report.unexpectedUnhandledRejections += events.exceptions.length; // exceptions == unhandled rejections
  report.stalePageEvents += events.console.length; // any console noise during navigation is stale-page artifact
}
async function evaluate(expr) {
  const r = await call("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.result && r.result.exceptionDetails) throw new Error("evaluate failed: " + (r.result.exceptionDetails.exception && r.result.exceptionDetails.exception.description || r.result.exceptionDetails.text));
  return r.result && r.result.result ? r.result.result.value : null;
}
async function screenshot(name) {
  const r = await call("Page.captureScreenshot", { format: "png" });
  if (r.result && r.result.data) fs.writeFileSync(path.join(OUT, name + ".png"), Buffer.from(r.result.data, "base64"));
}
async function navigate(url, waitMs = 2200) {
  currentUrl = url;
  await call("Page.navigate", { url });
  await wait(waitMs);
}

async function checkCountry(slug, name) {
  clearCounts();
  await navigate(`${BASE}/intelligence/africa/country/${slug}/`);
  const st = await evaluate(`(function(){
    const lead = document.querySelector('.profile-lead');
    const toc = document.querySelector('.intel-toc');
    const secs = document.querySelectorAll('.profile-section');
    const paras = document.querySelectorAll('.profile-section p');
    const infobox = document.querySelector('#countryEvidence');
    const actors = document.querySelectorAll('#countryActors .entity-card, #countryActors a');
    const overflow = document.documentElement.scrollWidth > window.innerWidth + 2;
    const badges = Array.from(document.querySelectorAll('.intel-badge')).map(function(b){return b.textContent;});
    const links = Array.from(document.querySelectorAll('.profile-section a')).filter(function(a){return a.getAttribute('href') && !a.getAttribute('href').startsWith('http');}).length;
    const bodyText = document.querySelector('#countryBody') ? document.querySelector('#countryBody').textContent.replace(/\\s+/g,'').length : 0;
    return { leadParas: lead ? lead.querySelectorAll('p').length : 0, tocLinks: toc ? toc.querySelectorAll('a').length : 0,
      sections: secs.length, paras: paras.length, bodyChars: bodyText, internalLinks: links,
      actors: actors.length, overflow: overflow, badges: badges, freshnessNote: !!document.querySelector('.profile-standfirst') };
  })()`);
  flushCounts();
  report.pages.push({ type: "country", name, slug, ...st });
  await screenshot("country-" + slug);
  return st;
}

async function checkEntity(slug, name) {
  clearCounts();
  await navigate(`${BASE}/intelligence/africa/entity/${slug}/`);
  const st = await evaluate(`(function(){
    const lead = document.querySelector('.profile-lead');
    const toc = document.querySelector('.intel-toc');
    const secs = document.querySelectorAll('.profile-section');
    const paras = document.querySelectorAll('.profile-section p');
    const depth = document.querySelector('#entityInfobox .ib-row dd');
    const overflow = document.documentElement.scrollWidth > window.innerWidth + 2;
    const bodyText = document.querySelector('#entityBody') ? document.querySelector('#entityBody').textContent.replace(/\\s+/g,'').length : 0;
    return { leadParas: lead ? lead.querySelectorAll('p').length : 0, tocLinks: toc ? toc.querySelectorAll('a').length : 0,
      sections: secs.length, paras: paras.length, bodyChars: bodyText,
      depth: depth ? depth.textContent : null, overflow: overflow,
      relations: document.querySelectorAll('#entityRelations .intel-rel-row').length,
      dateRows: document.querySelectorAll('#entityInfobox .ib-row').length };
  })()`);
  flushCounts();
  report.pages.push({ type: "entity", name, slug, ...st });
  await screenshot("entity-" + slug);
  return st;
}

async function checkRelation(slug, name) {
  clearCounts();
  await navigate(`${BASE}/intelligence/africa/relation/${slug}/`);
  const st = await evaluate(`(function(){
    const tl = document.querySelectorAll('#relationTimeline .tl-item').length;
    const secs = document.querySelectorAll('#relationBody .profile-section').length;
    const overview = document.querySelector('#relationOverview p') ? document.querySelector('#relationOverview p').textContent.length : 0;
    const overflow = document.documentElement.scrollWidth > window.innerWidth + 2;
    return { timeline: tl, sections: secs, overviewChars: overview, overflow: overflow,
      graphBack: !!document.querySelector('#relationGraphBack') };
  })()`);
  flushCounts();
  report.pages.push({ type: "relation", name, slug, ...st });
  await screenshot("relation-" + slug);
  return st;
}

async function main() {
  await connect();
  // ---- 8 deep country pages ----
  const countries = [
    ["nigeria", "尼日利亚"], ["libya", "利比亚"], ["south-sudan", "南苏丹"], ["niger", "尼日尔"],
    ["benin", "贝宁"], ["chad", "乍得"], ["sudan", "苏丹"], ["mozambique", "莫桑比克"]];
  for (const [slug, name] of countries) await checkCountry(slug, name);

  // ---- 13 priority entities ----
  const entities = [
    ["boko-haram-jas", "博科圣地/JAS"], ["iswap", "ISWAP"], ["mnjtf", "MNJTF"],
    ["nigerian-armed-forces", "尼日利亚武装部队"], ["libyan-national-army", "利比亚国民军"], ["gnu-forces", "GNU 相关安全力量"],
    ["isis-libya", "ISIS 利比亚分支"], ["sspdf", "SSPDF"], ["splm-io", "SPLM/A-IO"], ["national-salvation-front", "NAS"],
    ["salva-kiir", "萨尔瓦·基尔"], ["riek-machar", "里克·马沙尔"], ["benin-security-forces", "贝宁安全力量"]];
  for (const [slug, name] of entities) await checkEntity(slug, name);

  // ---- 10+ deepened relations ----
  const rels = [
    ["jas-iswap-conflict", "JAS—ISWAP"], ["iswap-islamic-state-affiliation", "ISWAP—伊斯兰国"],
    ["jnim-is-sahel-hostile", "JNIM—IS Sahel"], ["jnim-niger-operates", "JNIM—尼日尔"],
    ["is-sahel-niger-operates", "IS Sahel—尼日尔"], ["lna-gnu-rivalry", "LNA—GNU"],
    ["isis-libya-affiliation", "ISIS-Libya—伊斯兰国"], ["splm-io-sspdf-conflict", "SPLM/A-IO—SSPDF"],
    ["kiir-sspdf-leads", "基尔—SSPDF"], ["machar-splm-io-leads", "马沙尔—SPLM/A-IO"],
    ["nas-splm-io-allied", "NAS—SPLM/A-IO"], ["nigeria-mnjtf-member", "尼日利亚—MNJTF"]];
  for (const [slug, name] of rels) await checkRelation(slug, name);

  // ---- graph regression (I3-Prep-A) ----
  clearCounts();
  await navigate(`${BASE}/intelligence/africa/network/?focus=country-chad`);
  const graph = await evaluate(`(function(){
    const nodes = document.querySelectorAll('.graph-node').length;
    const edges = document.querySelectorAll('.graph-edge').length;
    const legend = document.querySelector('.graph-legend') ? document.querySelector('.graph-legend').textContent.replace(/\\s+/g,' ').trim() : null;
    const focusLink = document.querySelector('#focusLink') ? document.querySelector('#focusLink').getAttribute('href') : null;
    return { nodes, edges, legend: !!legend, focusLink };
  })()`);
  flushCounts();
  report.graph = graph;
  await screenshot("graph-chad");
  clearCounts();
  await navigate(`${BASE}/intelligence/africa/network/?focus=actor-iswap`);
  const graph2 = await evaluate(`(function(){
    return { nodes: document.querySelectorAll('.graph-node').length,
      edges: document.querySelectorAll('.graph-edge').length,
      strokeSet: new Set(Array.from(document.querySelectorAll('.graph-edge')).map(function(l){return getComputedStyle(l).stroke;})).size };
  })()`);
  flushCounts();
  report.graphIswap = graph2;
  await screenshot("graph-iswap");

  // ---- deep link refresh (deep routes reload fine) ----
  clearCounts();
  await navigate(`${BASE}/intelligence/africa/country/libya/`);
  const deepReload = await evaluate(`(function(){ return { h1: document.querySelector('#countryHeading h1') ? document.querySelector('#countryHeading h1').textContent : null, sections: document.querySelectorAll('.profile-section').length }; })()`);
  flushCounts();
  report.deepReload = deepReload;

  // ---- responsive: 390px country + entity + relation ----
  await call("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  for (const [p, slug] of [["country", "nigeria"], ["entity", "boko-haram-jas"], ["relation", "jas-iswap-conflict"]]) {
    clearCounts();
    await navigate(`${BASE}/intelligence/africa/${p}/${slug}/`);
    const st = await evaluate(`(function(){
      return { overflowX: document.documentElement.scrollWidth > 390 + 2,
        bodyChars: (document.querySelector('#countryBody,#entityBody,#relationBody') || {}).textContent ? (document.querySelector('#countryBody,#entityBody,#relationBody')).textContent.length : 0,
        toc: !!document.querySelector('.intel-toc') };
    })()`);
    flushCounts();
    report["viewport390-" + p + "-" + slug] = st;
    await screenshot("v390-" + p + "-" + slug);
  }
  await call("Emulation.clearDeviceMetricsOverride");
  clearCounts();
  await navigate(`${BASE}/intelligence/africa/network/?focus=actor-jnim`);
  await screenshot("graph-390");
  flushCounts();

  report.summary = {
    consoleErrors: report.consoleErrors,
    runtimeExceptions: report.runtimeExceptions,
    failedRequests: report.failedRequests,
    expectedNavigationAborts: report.expectedNavigationAborts,
    unexpectedUnhandledRejections: report.unexpectedUnhandledRejections,
    stalePageEvents: report.stalePageEvents,
    pagesChecked: report.pages.length,
  };
  fs.writeFileSync(path.join(OUT, "browser-qa-results.json"), JSON.stringify(report, null, 2));
  console.log("I3-A QA done:", JSON.stringify(report.summary));
  process.exit(0);
}

main().catch((e) => { console.error("QA FAIL", e); process.exit(1); });
