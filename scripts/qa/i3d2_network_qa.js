const http = require("http");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");
const PUBLIC = process.env.PUBLIC_BASE || "http://127.0.0.1:4175/intelligence/africa";
const CDP_PORT = Number(process.env.CDP_PORT || 9230);
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-i3d2", "network-density-qa.json");
const FOCI = ["actor-jnim", "actor-katiba-hanifa", "actor-dana-atem", "person-abou-ghosmane", "person-jafar-dicko", "actor-dozos-of-macina"];
function getJson(url) { return new Promise((resolve, reject) => { http.get(url, (res) => { let b = ""; res.on("data", x => b += x); res.on("end", () => { try { resolve(JSON.parse(b)); } catch (e) { reject(e); } }); }).on("error", reject); }); }
function wait(ms) { return new Promise(r => setTimeout(r, ms)); }
async function main() {
  const targets = await getJson(`http://127.0.0.1:${CDP_PORT}/json/list`);
  const target = targets.find(x => x.type === "page" && !x.url.startsWith("edge://") && !x.url.startsWith("chrome-extension://") && !x.url.startsWith("devtools://"));
  if (!target) throw new Error("CDP page target not found");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.once("open", resolve); ws.once("error", reject); });
  let id = 0; const pending = new Map(); const exceptions = []; const consoleErrors = []; const failed = []; const bad = []; const requestUrls = new Map();
  ws.on("message", raw => { const m = JSON.parse(raw.toString()); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m); } if (m.method === "Runtime.exceptionThrown") exceptions.push(m.params.exceptionDetails || {}); if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") consoleErrors.push(m.params); if (m.method === "Network.requestWillBeSent") requestUrls.set(m.params.requestId, m.params.request.url); if (m.method === "Network.responseReceived" && m.params.response && m.params.response.status >= 400 && !/favicon/.test(m.params.response.url)) bad.push({ url: m.params.response.url, status: m.params.response.status }); if (m.method === "Network.loadingFailed" && m.params.errorText !== "net::ERR_ABORTED") failed.push({ url: requestUrls.get(m.params.requestId) || null, error: m.params.errorText }); });
  const call = (method, params = {}) => new Promise((resolve, reject) => { const i = ++id; pending.set(i, { resolve, reject }); ws.send(JSON.stringify({ id: i, method, params })); });
  const evaluate = async expression => { const r = await call("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }); return r.result && r.result.result ? r.result.result.value : null; };
  await call("Runtime.enable"); await call("Page.enable"); await call("Network.enable"); await call("Log.enable"); await call("Network.setCacheDisabled", { cacheDisabled: true });
  const results = [];
  for (const focus of FOCI) {
    const url = `${PUBLIC}/network/?focus=${focus}`;
    await call("Emulation.setDeviceMetricsOverride", { width: 1366, height: 900, deviceScaleFactor: 1, mobile: false });
    await call("Page.navigate", { url }); await wait(1400);
    for (let i = 0; i < 40; i++) {
      const ready = await evaluate(`(() => document.readyState === "complete" && document.querySelectorAll("g.graph-node[data-entity-id]").length > 0 && !document.querySelector("#graphHint").textContent.includes("加载"))()`);
      if (ready) break;
      await wait(250);
    }
    const r = await evaluate(`(() => {
      const focusId = document.querySelector("#focusId")?.textContent.trim() || null;
      const nodes = [...document.querySelectorAll("g.graph-node[data-entity-id]")];
      const ids = nodes.map(n => n.getAttribute("data-entity-id"));
      const dup = ids.filter((x, i) => ids.indexOf(x) !== i);
      const edgeCountBefore = document.querySelectorAll(".graph-edge").length;
      const candidate = nodes.find(n => n.getAttribute("data-entity-id") !== focusId && !n.classList.contains("is-center"));
      let click = null;
      if (candidate) {
        candidate.scrollIntoView({ block: "center", inline: "center" });
        const rect = candidate.getBoundingClientRect();
        candidate.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 }));
        click = { clicked_id: candidate.getAttribute("data-entity-id"), after_focus: document.querySelector("#focusId")?.textContent.trim() || null };
      }
      return {
        focus_before: focusId,
        focus_name: document.querySelector("#focusName")?.textContent.trim() || null,
        node_count: nodes.length,
        edge_count: edgeCountBefore,
        duplicate_nodes: dup,
        candidate: click,
        graph_ready: document.querySelector("#graphHint")?.textContent || null
      };
    })()`);
    results.push({ focus, ...r });
  }
  const issues = [];
  for (const r of results) {
    if (r.duplicate_nodes.length) issues.push(`duplicate nodes at ${r.focus}: ${r.duplicate_nodes}`);
    if (r.node_count === 0) issues.push(`no nodes at ${r.focus}`);
    if (r.candidate && r.candidate.clicked_id !== r.candidate.after_focus) issues.push(`focus switch failed at ${r.focus}`);
  }
  const report = { artifact: "I3D2_NETWORK_DENSITY_QA", generated_at: new Date().toISOString(), public_base: PUBLIC, foci: FOCI, results, events: { runtime_exceptions: exceptions.length, console_errors: consoleErrors.length, failed_requests: failed.length, bad_responses: bad.length }, issues, gate: issues.length === 0 && exceptions.length === 0 && consoleErrors.length === 0 && failed.length === 0 && bad.length === 0 ? "PASS" : "OPEN" };
  fs.mkdirSync(path.dirname(OUT), { recursive: true }); fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ results: results.map(r => ({ focus: r.focus, nodes: r.node_count, edges: r.edge_count, dup: r.duplicate_nodes.length, click: r.candidate })), events: { runtime_exceptions: exceptions.length, console_errors: consoleErrors.length, failed_requests: failed.length, bad_responses: bad.length }, issues, gate: report.gate }, null, 2));
  ws.close();
}
main().catch(e => { console.error(e.stack || e); process.exit(1); });
