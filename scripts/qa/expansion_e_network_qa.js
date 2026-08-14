// Expansion E — network focus QA against local dist.
const path = require("path");
const http = require("http");
const fs = require("fs");
const ws = require("ws");
const CDP_PORT = 9234;
const BASE = "http://127.0.0.1:4174";
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-expansion-e", "network-qa-results.json");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const withTimeout = (p, ms, label) => Promise.race([p, new Promise((_, j) => setTimeout(() => j(new Error("timeout " + label)), ms))]);

const FOCI = [
  { key: "mnjtf", focus: "actor-mnjtf" },
  { key: "aes", focus: "actor-fu-aes" },
  { key: "fadm", focus: "actor-fadm" },
  { key: "rdf", focus: "actor-rdf-mozambique" },
  { key: "africa_corps", focus: "actor-africa-corps" },
  { key: "africom", focus: "actor-africom" },
  { key: "jnim", focus: "actor-jnim" },
  { key: "isis_mozambique", focus: "actor-is-mozambique" },
];
const events = { console: [], exceptions: [], failed: [] };
function getTarget() {
  return new Promise((res, rej) => {
    http.get(`http://127.0.0.1:${CDP_PORT}/json/list`, (r) => {
      let d = ""; r.on("data", (c) => (d += c));
      r.on("end", () => { const t = JSON.parse(d).find((x) => x.type === "page"); res(t ? t.webSocketDebuggerUrl : null); });
    }).on("error", rej);
  });
}
function connect(url) {
  return new Promise((res, rej) => {
    const s = new ws(url);
    let id = 0; const pending = {};
    const send = (method, params) => new Promise((r, j) => { const mid = ++id; pending[mid] = { r, j }; s.send(JSON.stringify({ id: mid, method, params: params || {} })); });
    s.on("message", (raw) => {
      const m = JSON.parse(raw);
      if (m.id && pending[m.id]) { if (m.error) pending[m.id].j(new Error(JSON.stringify(m.error))); else pending[m.id].r(m.result); delete pending[m.id]; return; }
      if (m.method === "Runtime.consoleAPICalled" && ["error", "assert"].indexOf(m.params.type) >= 0) events.console.push(m.params);
      if (m.method === "Runtime.exceptionThrown") events.exceptions.push(m.params);
      if (m.method === "Network.loadingFailed" && m.params.canceled !== true) events.failed.push(m.params);
    });
    s.on("open", () => res(send));
    s.on("error", rej);
  });
}
(async () => {
  const send = await connect(await getTarget());
  await send("Runtime.enable"); await send("Network.enable"); await send("Page.enable");
  await send("Network.setCacheDisabled", { cacheDisabled: true });
  try { await send("Network.clearBrowserCache"); } catch (e) {}
  const ev = (expr) => withTimeout(send("Runtime.evaluate", { expression: expr, returnByValue: true }), 12000, "ev").then((r) => (r && r.result) ? r.result.value : undefined);
  const wait = async (sel, tries) => { for (let i = 0; i < (tries || 40); i++) { if (await ev(`!!document.querySelector(${JSON.stringify(sel)})`) === true) return true; await sleep(500); } return false; };
  const results = [];
  for (const f of FOCI) {
    events.console.length = 0; events.exceptions.length = 0; events.failed.length = 0;
    await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await withTimeout(send("Page.navigate", { url: BASE + "/intelligence/africa/network/?focus=" + f.focus }), 15000, "nav");
    await wait(".graph-node");
    await sleep(1200);
    const state = await ev(`(function(){
      var nodes = document.querySelectorAll(".graph-node");
      var center = (document.querySelector(".graph-node.is-center .node-label")||{}).textContent || "";
      var stats = (document.querySelector("#graphVisStats")||{}).textContent || "";
      var orphan = Array.prototype.filter.call(document.querySelectorAll(".graph-edge"), function(e){ return !e.getAttribute("aria-label"); }).length;
      return { nodes: nodes.length, center: center, stats: stats };
    })()`);
    const gates = [];
    const pass = (n, c) => gates.push({ name: n, pass: !!c });
    pass("console=0", events.console.length === 0);
    pass("exceptions=0", events.exceptions.length === 0);
    pass("failed=0", events.failed.length === 0);
    pass("center_label_present", state.center.length > 0);
    pass("graph_rendered", state.nodes > 0);
    pass("stats_visible", state.stats.length > 0);
    results.push({ key: f.key, focus: f.focus, state, gates, console_errors: events.console.length, exceptions: events.exceptions.length, failed_requests: events.failed.length });
    const failed = gates.filter((g) => !g.pass);
    console.log(`[done] focus=${f.key} — ${gates.length - failed.length}/${gates.length} nodes=${state.nodes} center=${state.center.slice(0, 16)}`);
  }
  const allGates = results.flatMap((r) => r.gates || []);
  const total = allGates.length, passed = allGates.filter((g) => g.pass).length;
  const summary = { NETWORK_QA: (allGates.length && results.every((r) => (r.gates || []).every((g) => g.pass))) ? "PASS" : "FAIL", total_gates: total, passed_gates: passed, base: BASE, results };
  fs.writeFileSync(OUT, JSON.stringify(summary, null, 2));
  console.log(`=== EXPANSION E NETWORK QA: ${passed}/${total} ===`);
  process.exit(summary.NETWORK_QA === "PASS" ? 0 : 1);
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
