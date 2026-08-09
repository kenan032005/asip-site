#!/usr/bin/env node
/* Diagnose 4xx responses on Africa root page (local) */
const http = require("http");
const WebSocket = require("ws");
const CDP_PORT = Number(process.env.CDP_PORT || 9236);

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
  const target = targets.find((t) => !t.url.startsWith("edge://") && !t.url.startsWith("chrome-extension://") && !t.url.startsWith("devtools://") && t.type === "page");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.on("open", r));
  const cdp = makeClient(ws);
  const bad = [];
  ws.on("message", (raw) => {
    const msg = JSON.parse(raw.toString());
    if (msg.method === "Network.responseReceived" && msg.params.response.status >= 400) {
      bad.push({ url: msg.params.response.url, status: msg.params.response.status });
    }
  });
  await cdp.send("Page.enable"); await cdp.send("Network.enable");
  await cdp.send("Page.navigate", { url: "http://127.0.0.1:4178/intelligence/africa/" });
  await new Promise((r) => setTimeout(r, 2500));
  console.log("bad responses:", JSON.stringify(bad, null, 1));
  ws.close();
}
main().catch((e) => { console.error(e); process.exit(2); });
