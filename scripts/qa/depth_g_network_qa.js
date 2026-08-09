#!/usr/bin/env node
/* DEPTH G network density QA on Depth-G-relevant foci (JNIM, IS Sahel,
   Katiba Hanifa, Mali Army, Burkina Army, Benin Forces, Cameroon Army,
   Ambazonia, Ansaru, FAMa, Dozos). Asserts graph renders with node/edge
   counts > 0 and no runtime errors. Writes
   qa-artifacts-depth-g/network-density-qa.json */
const http = require("http");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");
const PUBLIC = process.env.PUBLIC_BASE || "http://127.0.0.1:4191/intelligence/africa";
const CDP_PORT = Number(process.env.CDP_PORT || 9252);
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-depth-g", "network-density-qa.json");

const FOCI = [
  "actor-jnim", "actor-is-sahel", "actor-katiba-hanifa", "actor-mali-army",
  "actor-burkina-army", "actor-benin-forces", "actor-cameroon-army",
  "actor-ambazonia-network", "actor-ansaru", "actor-dozos-of-macina",
];
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
  const results = [];
  const targets = await getJson(`http://127.0.0.1:${CDP_PORT}/json/list`);
  const target = targets.find((t) => t.type === "page"
    && !t.url.startsWith("edge://") && !t.url.startsWith("chrome-extension://")
    && !t.url.startsWith("devtools://"));
  if (!target) throw new Error("no page target");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.on("open", r));
  const cdp = makeClient(ws);
  let errs = [];
  ws.on("message", (raw) => {
    const msg = JSON.parse(raw.toString());
    if (msg.method === "Runtime.exceptionThrown") errs.push(msg.params);
  });
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await cdp.send("Network.enable");
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });

  async function evaluate(expression) {
    const r = await cdp.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    return r.result && r.result.result ? r.result.result.value : null;
  }

  for (const focus of FOCI) {
    const url = `${PUBLIC}/network/?focus=${focus}`;
    await cdp.send("Page.navigate", { url });
    for (let i = 0; i < 40; i++) {
      const done = await evaluate(`(() => document.readyState === "complete")()`);
      if (done) break;
      await sleep(250);
    }
    await sleep(600);
    const r = await cdp.send("Runtime.evaluate", {
      expression: `(() => {
        const nodes = document.querySelectorAll("g.graph-node[data-entity-id]").length;
        const edges = document.querySelectorAll("line.graph-edge, path.graph-edge, .graph-edge").length;
        const err = document.querySelector("#intelError");
        return { nodes, edges, error: err && !err.hidden ? err.innerText.slice(0, 80) : null };
      })()`, returnByValue: true,
    });
    const v = r.result && r.result.result ? r.result.result.value : {};
    results.push({ focus, ...v, runtime_errors: errs.length });
    console.log(`${focus}: nodes=${v.nodes} edges=${v.edges} error=${v.error || "none"} errors=${errs.length}`);
    errs.length = 0;
  }

  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify({ artifact: "DEPTHG_NETWORK_QA", results }, null, 1));
  const fails = results.filter((r) => r.nodes === 0 || r.edges === 0 || r.error || r.runtime_errors > 0);
  console.log(`network QA: ${results.length} foci, ${fails.length} fails`);
  ws.close();
  process.exit(fails.length ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(2); });
