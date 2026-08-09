#!/usr/bin/env node
/* Diagnose horizontal overflow on 390 viewport for SAF/RSF entity + JEM-SAF relation pages */
const http = require("http");
const WebSocket = require("ws");
const CDP_PORT = 9238;
const BASE = "http://127.0.0.1:4179/intelligence/africa";
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
  await cdp.send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: false });
  for (const route of ["entity/sudanese-armed-forces/", "relation/jem-saf-conflict/"]) {
    await cdp.send("Page.navigate", { url: BASE + "/" + route });
    for (let i = 0; i < 40; i++) {
      const r = await cdp.send("Runtime.evaluate", { expression: `document.readyState === "complete"`, returnByValue: true });
      if (r.result && r.result.result && r.result.result.value) break;
      await sleep(250);
    }
    await sleep(500);
    const r = await cdp.send("Runtime.evaluate", {
      expression: `(() => {
        const vw = innerWidth;
        const wide = [];
        document.querySelectorAll("*").forEach((el) => {
          const rect = el.getBoundingClientRect();
          if (rect.right > vw + 2 && rect.width > 0) {
            wide.push({ tag: el.tagName, cls: (el.className || "").toString().slice(0, 60), id: el.id, w: Math.round(rect.width), right: Math.round(rect.right), text: (el.innerText || "").slice(0, 40) });
          }
        });
        return { scrollW: document.documentElement.scrollWidth, vw, wide: wide.slice(0, 12) };
      })()`, returnByValue: true,
    });
    const v = r.result && r.result.result ? r.result.result.value : {};
    console.log("== " + route + " ==");
    console.log("scrollW:", v.scrollW, "vw:", v.vw);
    v.wide.forEach((w) => console.log("  ", w.tag, w.cls || w.id, "w=" + w.w, "right=" + w.right, "|", w.text));
  }
  ws.close();
}
main().catch((e) => { console.error(e); process.exit(2); });
