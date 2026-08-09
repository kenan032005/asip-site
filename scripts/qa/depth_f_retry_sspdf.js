#!/usr/bin/env node
/* Retry SSPDF/SPLM-IO network focus on public with cache convergence */
const http = require("http");
const WebSocket = require("ws");
const PUBLIC = process.env.PUBLIC_BASE;
const CDP_PORT = 9243;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let d = "";
      res.on("data", (c) => (d += c));
      res.on("end", () => { try { resolve(JSON.parse(d)); } catch (e) { reject(e); } });
    }).on("error", reject);
  });
}
let msgId = 0;
function makeClient(ws) {
  const pending = new Map();
  ws.on("message", (raw) => {
    const msg = JSON.parse(raw.toString());
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  });
  return { send(m, p = {}) { return new Promise((res) => { const id = ++msgId; pending.set(id, res); ws.send(JSON.stringify({ id, method: m, params: p })); }); } };
}

async function main() {
  const targets = await getJson(`http://127.0.0.1:${CDP_PORT}/json/list`);
  const t = targets.find((x) => !x.url.startsWith("edge://") && !x.url.startsWith("chrome-extension://") && !x.url.startsWith("devtools://") && x.type === "page");
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise((r) => ws.on("open", r));
  const cdp = makeClient(ws);
  await cdp.send("Page.enable"); await cdp.send("Runtime.enable");
  for (const focus of ["actor-sspdf", "actor-splm-io"]) {
    for (let attempt = 0; attempt < 3; attempt++) {
      await cdp.send("Page.navigate", { url: PUBLIC + "/network/?focus=" + focus });
      for (let i = 0; i < 40; i++) {
        const r = await cdp.send("Runtime.evaluate", { expression: `document.readyState === "complete"`, returnByValue: true });
        if (r.result && r.result.result && r.result.result.value) break;
        await sleep(250);
      }
      await sleep(1500);
      const r = await cdp.send("Runtime.evaluate", {
        expression: `(() => ({ nodes: document.querySelectorAll("g.graph-node[data-entity-id]").length, edges: document.querySelectorAll(".graph-edge").length }))()`,
        returnByValue: true,
      });
      const v = r.result && r.result.result ? r.result.result.value : {};
      console.log(focus, "attempt", attempt, JSON.stringify(v));
      if (v.nodes > 0) break;
      await sleep(2000);
    }
  }
  ws.close();
}
main().catch((e) => { console.error(e); process.exit(2); });
