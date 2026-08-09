#!/usr/bin/env node
/* Diagnose Nigeria-MNJTF relation page render error */
const http = require("http");
const WebSocket = require("ws");
const CDP_PORT = Number(process.env.CDP_PORT || 9234);

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = "";
      res.on("data", (c) => (data += c));
      res.on("end", () => { try { resolve(JSON.parse(data)); } catch (e) { reject(e); } });
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
  const errs = [];
  ws.on("message", (raw) => {
    const msg = JSON.parse(raw.toString());
    if (msg.method === "Runtime.exceptionThrown") errs.push(JSON.stringify(msg.params.exceptionDetails));
    if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error") errs.push(JSON.stringify(msg.params.args || []));
  });
  await cdp.send("Page.enable"); await cdp.send("Runtime.enable"); await cdp.send("Network.enable");
  await cdp.send("Page.navigate", { url: "http://127.0.0.1:4177/intelligence/africa/relation/nigeria-mnjtf-member/" });
  await new Promise((r) => setTimeout(r, 2500));
  const r = await cdp.send("Runtime.evaluate", { expression: `(() => {
    const err = document.querySelector("#intelError");
    const body = document.querySelector("#relationBody");
    return { err_html: err ? err.outerHTML.slice(0, 600) : "no err el", body_html: body ? body.innerHTML.slice(0, 800) : "no body el", data_state: typeof window.__ASIP_DATA__ !== "undefined" ? "yes" : "no" };
  })()`, returnByValue: true });
  console.log(JSON.stringify(r.result && r.result.result ? r.result.result.value : r, null, 1));
  console.log("ERRORS:", errs.slice(0, 5));
  ws.close();
}

main().catch((e) => { console.error(e); process.exit(2); });
