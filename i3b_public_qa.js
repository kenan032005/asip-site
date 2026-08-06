// I3-B public-URL browser acceptance (round 3, clean session) against the
// verified public preview host.
const http = require("http");
const path = require("path");
const fs = require("fs");

const PUBLIC = process.env.PUBLIC_BASE || "https://e5f9aef1abbc4c938d3ce143c41811c4.gz1.agentos-app.net/intelligence/africa";
const CDP_PORT = process.env.CDP_PORT || "9224";
const OUT = path.join(__dirname, "qa-artifacts-i3b");
if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

const report = { pages: [], consoleErrors: 0, runtimeExceptions: 0, failedRequests: 0,
  unexpectedUnhandledRejections: 0, brokenAssets: 0, horizontalOverflow: 0 };
const events = { console: [], exceptions: [], failed: [] };
let currentUrl = "", ws = null, pending = new Map(), msgId = 0;

function getJson(url) { return new Promise((res, rej) => http.get(url, (r) => { let d = ""; r.on("data", (c) => (d += c)); r.on("end", () => { try { res(JSON.parse(d)); } catch (e) { rej(e); } }); }).on("error", rej)); }
function call(method, params = {}) { return new Promise((resolve) => { const id = ++msgId; pending.set(id, resolve); ws.send(JSON.stringify({ id, method, params })); }); }
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
    if (m.method === "Network.loadingFailed" && (m.params.errorText || "") !== "net::ERR_ABORTED")
      events.failed.push({ url: currentUrl, error: m.params.errorText });
  };
  await call("Runtime.enable"); await call("Page.enable"); await call("Network.enable");
  await call("Network.setCacheDisabled", { cacheDisabled: true });
}
function clearCounts() { events.console.length = 0; events.exceptions.length = 0; events.failed.length = 0; }
function flushCounts() {
  report.consoleErrors += events.console.length;
  report.runtimeExceptions += events.exceptions.length;
  report.failedRequests += events.failed.length;
  report.unexpectedUnhandledRejections += events.exceptions.length;
}
async function evaluate(expr) {
  const r = await call("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  return r.result && r.result.result ? r.result.result.value : null;
}
async function screenshot(name) {
  const r = await call("Page.captureScreenshot", { format: "png" });
  if (r.result && r.result.data) fs.writeFileSync(path.join(OUT, name + ".png"), Buffer.from(r.result.data, "base64"));
}
async function navigate(url, waitMs = 2600) {
  currentUrl = url;
  await call("Page.navigate", { url });
  await wait(waitMs);
}

async function main() {
  await connect();
  const checks = [
    ["public-home", "/index.html"],
    ["public-mali", "/country/mali/index.html"],
    ["public-burkina", "/country/burkina-faso/index.html"],
    ["public-ethiopia", "/country/ethiopia/index.html"],
    ["public-tanzania", "/country/tanzania/index.html"],
    ["public-jnim", "/entity/jnim/index.html"],
    ["public-graph", "/network/index.html?focus=country-mali"],
    ["public-relation", "/relation/endf-fano-conflict/index.html"],
  ];
  for (const [name, p] of checks) {
    clearCounts();
    await navigate(PUBLIC + p);
    const st = await evaluate(`(function(){
      const overflow = document.documentElement.scrollWidth > window.innerWidth + 2;
      const bodyChars = (document.querySelector('#countryBody,#entityBody,#relationBody') || {}).textContent ? document.querySelector('#countryBody,#entityBody,#relationBody').textContent.replace(/\\s+/g,'').length : 0;
      const banner = document.body.textContent.indexOf('非生产预览版') >= 0;
      const errorHidden = !document.querySelector('#intelError') || document.querySelector('#intelError').hidden;
      return { url: location.href, host: location.host, overflow, bodyChars, banner, errorHidden };
    })()`);
    flushCounts();
    if (st.overflow) report.horizontalOverflow++;
    report.pages.push({ name, ...st });
    await screenshot(name);
  }
  report.summary = { consoleErrors: report.consoleErrors, runtimeExceptions: report.runtimeExceptions,
    failedRequests: report.failedRequests, unexpectedUnhandledRejections: report.unexpectedUnhandledRejections,
    brokenAssets: report.brokenAssets, horizontalOverflow: report.horizontalOverflow, pagesChecked: report.pages.length };
  fs.writeFileSync(path.join(OUT, "public-preview-results.json"), JSON.stringify(report, null, 2));
  console.log("public QA done:", JSON.stringify(report.summary));
  process.exit(0);
}
main().catch((e) => { console.error("PUBLIC QA FAIL", e); process.exit(1); });
