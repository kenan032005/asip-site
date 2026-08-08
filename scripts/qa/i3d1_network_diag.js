const http = require("http");
const WebSocket = require("ws");
const CDP_PORT = Number(process.env.CDP_PORT || 9228);
const BASE = process.env.PUBLIC_BASE || "http://127.0.0.1:4174/intelligence/africa";
const FOCUS = process.env.FOCUS || "actor-fu-aes";
function getJson(url) { return new Promise((resolve, reject) => { http.get(url, (res) => { let b = ""; res.on("data", x => b += x); res.on("end", () => { try { resolve(JSON.parse(b)); } catch (e) { reject(e); } }); }).on("error", reject); }); }
function wait(ms) { return new Promise(r => setTimeout(r, ms)); }
async function main() {
  const targets = await getJson(`http://127.0.0.1:${CDP_PORT}/json/list`);
  const target = targets.find(x => x.type === "page" && !x.url.startsWith("edge://") && !x.url.startsWith("chrome-extension://") && !x.url.startsWith("devtools://"));
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.once("open", resolve); ws.once("error", reject); });
  let id = 0; const pending = new Map(); const exceptions = []; const consoleErrors = [];
  ws.on("message", raw => { const m = JSON.parse(raw.toString()); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m); } if (m.method === "Runtime.exceptionThrown") exceptions.push(m.params.exceptionDetails || {}); if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") consoleErrors.push((m.params.args || []).map(a => a.value || a.description || "")); });
  const call = (method, params = {}) => new Promise((resolve, reject) => { const i = ++id; pending.set(i, { resolve, reject }); ws.send(JSON.stringify({ id: i, method, params })); });
  const evaluate = async expression => { const r = await call("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }); return r.result && r.result.result ? r.result.result.value : { __err: r.result && r.result.exceptionDetails && r.result.exceptionDetails.text }; };
  await call("Runtime.enable"); await call("Page.enable"); await call("Network.enable"); await call("Network.setCacheDisabled", { cacheDisabled: true });
  const url = `${BASE}/network/?focus=${FOCUS}`;
  await call("Page.navigate", { url }); await wait(2500);
  const state = await evaluate(`(() => ({
    url: location.href,
    focus_text: document.querySelector("#focusId") ? document.querySelector("#focusId").textContent.trim() : null,
    focus_name: document.querySelector("#focusName") ? document.querySelector("#focusName").textContent.trim() : null,
    graph_hint: document.querySelector("#graphHint") ? document.querySelector("#graphHint").textContent : null,
    node_count: document.querySelectorAll("g.graph-node[data-entity-id]").length,
    edge_count: document.querySelectorAll(".graph-edge").length,
    intel_error: document.querySelector("#intelError") ? { hidden: document.querySelector("#intelError").hidden, text: document.querySelector("#intelError").textContent } : null,
    relation_info_text: document.querySelector("#nodeInfo") ? document.querySelector("#nodeInfo").innerText.slice(0, 120) : null
  }))()`);
  console.log(JSON.stringify({ state, exceptions: exceptions.length, consoleErrors: consoleErrors.slice(0, 5) }, null, 2));
  ws.close();
}
main().catch(e => { console.error(e.stack || e); process.exit(1); });
