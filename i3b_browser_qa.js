// I3-B browser acceptance: 13 countries, 20 core entities, 15 deepened
// relations, graph regression (7 focuses), 4 viewports, console/net zero.
const http = require("http");
const path = require("path");
const fs = require("fs");

const BASE = process.env.QA_BASE || "http://127.0.0.1:8786";
const CDP_PORT = process.env.CDP_PORT || "9224";
const OUT = path.join(__dirname, process.env.QA_OUT || "qa-artifacts-i3b");
if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

const report = { pages: [], consoleErrors: 0, runtimeExceptions: 0, failedRequests: 0,
  expectedNavigationAborts: 0, unexpectedUnhandledRejections: 0, brokenAssets: 0, horizontalOverflow: 0 };
const events = { console: [], exceptions: [], failed: [], aborts: [] };
let currentUrl = "";
let ws = null, pending = new Map(), msgId = 0;

function getJson(url) {
  return new Promise((res, rej) => http.get(url, (r) => {
    let d = ""; r.on("data", (c) => (d += c)); r.on("end", () => { try { res(JSON.parse(d)); } catch (e) { rej(e); } });
  }).on("error", rej));
}
function call(method, params = {}) {
  return new Promise((resolve) => { const id = ++msgId; pending.set(id, resolve); ws.send(JSON.stringify({ id, method, params })); });
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
      events.exceptions.push({ url: currentUrl, desc: String((d.exception && d.exception.description) || d.text || "").slice(0, 160) });
    }
    if (m.method === "Network.loadingFailed") {
      const err = m.params.errorText || "";
      if (err === "net::ERR_ABORTED") { events.aborts.push(currentUrl); report.expectedNavigationAborts++; }
      else events.failed.push({ url: currentUrl, error: err, type: m.params.type || "" });
    }
  };
  await call("Runtime.enable"); await call("Page.enable");
  await call("Network.enable"); await call("Network.setCacheDisabled", { cacheDisabled: true });
}
function clearCounts() { events.console.length = 0; events.exceptions.length = 0; events.failed.length = 0; events.aborts.length = 0; }
function flushCounts() {
  report.consoleErrors += events.console.length;
  report.runtimeExceptions += events.exceptions.length;
  report.failedRequests += events.failed.length;
  report.unexpectedUnhandledRejections += events.exceptions.length;
}
async function evaluate(expr) {
  const r = await call("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.result && r.result.exceptionDetails) throw new Error("eval failed");
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

async function checkPage(type, slug, name) {
  clearCounts();
  await navigate(`${BASE}/intelligence/africa/${type}/${slug}/`);
  const st = await evaluate(`(function(){
    const lead = document.querySelector('.profile-lead');
    const toc = document.querySelector('.intel-toc');
    const secs = document.querySelectorAll('.profile-section');
    const paras = document.querySelectorAll('.profile-section p');
    const overflow = document.documentElement.scrollWidth > window.innerWidth + 2;
    const bodyEl = document.querySelector('#countryBody,#entityBody,#relationBody');
    const bodyChars = bodyEl ? bodyEl.textContent.replace(/\\s+/g,'').length : 0;
    const tl = document.querySelectorAll('#relationTimeline .tl-item').length;
    const relations = document.querySelectorAll('#entityRelations .intel-rel-row, #countryRelations .intel-rel-row').length;
    const errorHidden = !document.querySelector('#intelError') || document.querySelector('#intelError').hidden;
    return { lead: lead ? lead.querySelectorAll('p').length : 0, toc: toc ? toc.querySelectorAll('a').length : 0,
      sections: secs.length, paras: paras.length, bodyChars, timeline: tl, relations,
      overflow, errorHidden };
  })()`);
  flushCounts();
  if (st.overflow) report.horizontalOverflow++;
  report.pages.push({ type, name, slug, ...st });
  await screenshot(`${type}-${slug}`);
  return st;
}

async function checkGraph(focus, name) {
  clearCounts();
  await navigate(`${BASE}/intelligence/africa/network/?focus=${focus}`);
  const g = await evaluate(`(function(){
    const nodes = document.querySelectorAll('.graph-node').length;
    const edges = document.querySelectorAll('.graph-edge').length;
    const legend = !!document.querySelector('.graph-legend');
    const strokeSet = new Set(Array.from(document.querySelectorAll('.graph-edge')).map(function(l){return getComputedStyle(l).stroke;})).size;
    const focusLink = document.querySelector('#focusLink') ? document.querySelector('#focusLink').getAttribute('href') : null;
    const overflow = document.documentElement.scrollWidth > window.innerWidth + 2;
    return { nodes, edges, legend, strokeSet, focusLink, overflow };
  })()`);
  flushCounts();
  if (g.overflow) report.horizontalOverflow++;
  report.pages.push({ type: "graph", name, focus, ...g });
  await screenshot("graph-" + focus);
  return g;
}

async function main() {
  await connect();
  const countries = [
    ["chad", "乍得"], ["niger", "尼日尔"], ["benin", "贝宁"], ["south-sudan", "南苏丹"],
    ["sudan", "苏丹"], ["mozambique", "莫桑比克"], ["nigeria", "尼日利亚"], ["libya", "利比亚"],
    ["mali", "马里"], ["burkina-faso", "布基纳法索"], ["cameroon", "喀麦隆"],
    ["ethiopia", "埃塞俄比亚"], ["tanzania", "坦桑尼亚"]];
  for (const [slug, name] of countries) await checkPage("country", slug, name);

  const entities = [
    ["al-qaida", "基地组织"], ["ansar-eddine", "安萨尔埃丁"], ["al-mourabitoun", "穆拉比通"],
    ["katiba-macina", "马西纳旅"], ["jnim", "JNIM"], ["is-sahel", "IS Sahel"], ["aqim", "AQIM"],
    ["mali-armed-forces", "马里武装部队"], ["burkina-armed-forces", "布基纳法索武装部队"], ["vdp", "VDP"],
    ["cameroon-armed-forces", "喀麦隆武装部队"], ["bir", "BIR"], ["endf", "ENDF"], ["fano", "Fano"],
    ["ola", "OLA"], ["tpdf", "TPDF"], ["boko-haram-jas", "JAS"], ["iswap", "ISWAP"],
    ["mnjtf", "MNJTF"], ["is-mozambique", "IS-Mozambique"]];
  for (const [slug, name] of entities) await checkPage("entity", slug, name);

  const relations = [
    ["mali-army-jnim", "马里军队—JNIM"], ["burkina-army-jnim", "布基纳军队—JNIM"],
    ["cameroon-army-jas", "喀麦隆军队—JAS"], ["cameroon-army-ambazonia", "喀麦隆军队—安巴佐尼亚"],
    ["endf-fano-conflict", "ENDF—Fano"], ["endf-ola-conflict", "ENDF—OLA"],
    ["endf-tdf-conflict", "ENDF—TDF"], ["tanzania-tpdf-is-moz", "TPDF—IS-Mozambique"],
    ["tanzania-mozambique-cooperate", "坦桑尼亚—莫桑比克合作"], ["vdp-burkina-support", "VDP—布基纳军队"],
    ["jas-iswap-conflict", "JAS—ISWAP"], ["jnim-is-sahel-hostile", "JNIM—IS Sahel"],
    ["splm-io-sspdf-conflict", "SPLM/A-IO—SSPDF"], ["lna-gnu-rivalry", "LNA—GNU"],
    ["nigeria-mnjtf-member", "尼日利亚—MNJTF"]];
  for (const [slug, name] of relations) await checkPage("relation", slug, name);

  const focuses = [["country-chad", "乍得"], ["actor-jnim", "JNIM"], ["actor-iswap", "ISWAP"],
    ["country-mali", "马里"], ["country-burkina-faso", "布基纳法索"],
    ["country-ethiopia", "埃塞俄比亚"], ["actor-is-sahel", "IS Sahel"]];
  for (const [focus, name] of focuses) await checkGraph(focus, name);

  // deep link refresh
  clearCounts();
  await navigate(`${BASE}/intelligence/africa/country/ethiopia/`);
  const deep = await evaluate(`(function(){ return { h1: document.querySelector('#countryHeading h1') ? document.querySelector('#countryHeading h1').textContent : null, sections: document.querySelectorAll('.profile-section').length }; })()`);
  flushCounts();
  report.deepReload = deep;

  // viewports: 1920/1366/768/390 on mali + entity + relation
  for (const [w, h, label] of [[1920, 1080, "1920"], [1366, 768, "1366"], [768, 1024, "768"], [390, 844, "390"]]) {
    await call("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: w < 500 });
    clearCounts();
    await navigate(`${BASE}/intelligence/africa/country/mali/`);
    const st = await evaluate(`(function(){ return { overflowX: document.documentElement.scrollWidth > ${w} + 2 }; })()`);
    flushCounts();
    if (st.overflowX) report.horizontalOverflow++;
    report["viewport-" + label] = st;
    await screenshot("v" + label + "-mali");
  }
  await call("Emulation.clearDeviceMetricsOverride");
  clearCounts();
  await navigate(`${BASE}/intelligence/africa/network/?focus=country-mali`);
  await screenshot("graph-390-mali");
  flushCounts();

  report.summary = {
    consoleErrors: report.consoleErrors, runtimeExceptions: report.runtimeExceptions,
    failedRequests: report.failedRequests, expectedNavigationAborts: report.expectedNavigationAborts,
    unexpectedUnhandledRejections: report.unexpectedUnhandledRejections,
    brokenAssets: report.brokenAssets, horizontalOverflow: report.horizontalOverflow,
    pagesChecked: report.pages.length,
  };
  fs.writeFileSync(path.join(OUT, "browser-qa-results.json"), JSON.stringify(report, null, 2));
  console.log("I3-B QA done:", JSON.stringify(report.summary));
  process.exit(0);
}
main().catch((e) => { console.error("QA FAIL", e); process.exit(1); });
