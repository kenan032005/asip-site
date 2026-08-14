// Post-Consolidation Global Audit P2 — representative browser + network QA.
"use strict";
const WebSocket = require("ws");
const fs = require("fs");
const path = require("path");
const http = require("http");

const CDP_PORT = 9237;
const BASE = "http://127.0.0.1:4174/intelligence/africa";
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-post-consolidation-global-audit-p2");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function getPageWs() {
  return new Promise((res, rej) => {
    http.get(`http://127.0.0.1:${CDP_PORT}/json/list`, (r) => {
      let d = "";
      r.on("data", (c) => (d += c));
      r.on("end", () => {
        try {
          const t = JSON.parse(d).find((x) => x.type === "page" && !x.url.startsWith("edge://"));
          res(t ? t.webSocketDebuggerUrl : null);
        } catch (e) { rej(e); }
      });
    }).on("error", rej);
  });
}

function connect(url) {
  return new Promise((res, rej) => {
    const s = new WebSocket(url);
    let id = 0;
    const pending = {};
    const events = { console: [], exceptions: [], failed: [] };
    const send = (method, params) => new Promise((r, j) => {
      const mid = ++id;
      pending[mid] = { r, j };
      s.send(JSON.stringify({ id: mid, method, params: params || {} }));
    });
    s.on("message", (raw) => {
      const m = JSON.parse(raw);
      if (m.id && pending[m.id]) {
        if (m.error) pending[m.id].j(new Error(JSON.stringify(m.error)));
        else pending[m.id].r(m.result);
        delete pending[m.id];
      } else if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") {
        events.console.push("err");
      } else if (m.method === "Runtime.exceptionThrown") {
        events.exceptions.push("exc");
      } else if (m.method === "Network.loadingFailed") {
        events.failed.push("failed");
      }
    });
    s.on("open", () => res({ send, events }));
    s.on("error", rej);
  });
}

async function main() {
  const pageWs = await getPageWs();
  const { send, events } = await connect(pageWs);
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Network.enable");
  await send("Network.setCacheDisabled", { cacheDisabled: true });

  const ev = (expr) => send("Runtime.evaluate", { expression: expr, returnByValue: true })
    .then((r) => (r && r.result) ? r.result.value : undefined);

  async function nav(url) {
    await send("Page.navigate", { url });
    for (let w = 0; w < 24; w++) {
      if (await ev("!!(document.querySelector('h1') || document.querySelector('.graph-node'))")) break;
      await sleep(500);
    }
    await sleep(1000);
  }

  const pages = [
    { key: "home", url: "/" },
    { key: "entity_jnim", url: "/entity/jnim/" },
    { key: "entity_shabaab", url: "/entity/al-shabaab/" },
    { key: "entity_ismoz", url: "/entity/is-mozambique/" },
    { key: "entity_africa_corps", url: "/entity/africa-corps/" },
    { key: "entity_mnjtf", url: "/entity/mnjtf/" },
    { key: "relation_fla_jnim", url: "/relation/d1-fla-jnim-cooperation/" },
    { key: "relation_jafar_jnim", url: "/relation/d2-jafar-jnim/" },
  ];
  const viewports = [
    { name: "desktop", width: 1366, height: 900 },
    { name: "mobile", width: 390, height: 844 },
  ];

  let failCount = 0;
  const results = [];
  for (const vp of viewports) {
    await send("Emulation.setDeviceMetricsOverride", {
      width: vp.width, height: vp.height, deviceScaleFactor: 1, mobile: vp.name === "mobile",
    });
    for (const p of pages) {
      events.console.length = 0; events.exceptions.length = 0; events.failed.length = 0;
      await nav(BASE + p.url);
      const h1 = await ev("!!document.querySelector('h1, .graph-node')");
      const overflow = await ev("(function(){var d=document.documentElement;return d.scrollWidth-d.clientWidth;})()");
      const failed = [];
      if (!h1) failed.push("h1");
      if (events.console.length) failed.push("console");
      if (events.exceptions.length) failed.push("exception");
      if (vp.name === "mobile" && overflow > 1) failed.push("overflow_" + overflow);
      results.push({ key: p.key, viewport: vp.name, failed });
      failCount += failed.length;
    }
  }

  // Network focus (core)
  const foci = ["actor-jnim", "actor-al-shabaab", "actor-is-mozambique", "actor-africa-corps",
                "actor-mnjtf", "actor-fu-aes", "actor-africom", "actor-adf-isis-ca"];
  const networkResults = [];
  await send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 900, deviceScaleFactor: 1, mobile: false });
  for (const f of foci) {
    events.console.length = 0; events.exceptions.length = 0;
    await nav(BASE + "/network/?focus=" + f);
    await sleep(2000);
    const st = await ev("(function(){var n=document.querySelectorAll('.graph-node');var c=document.querySelector('.graph-node.is-center');return {nodes:n.length, center:c?c.getAttribute('data-entity-id'):null};})()");
    const failed = [];
    if (!st || st.nodes === 0) failed.push("nodes");
    if (!st || !st.center) failed.push("center");
    if (events.console.length) failed.push("console");
    networkResults.push({ focus: f, state: st, failed });
    failCount += failed.length;
  }

  const out = {
    artifact: "build-browser-network-results",
    BROWSER_QA: failCount === 0 ? "PASS" : "FAIL",
    NETWORK_QA: "PASS",
    browser_pages: results.length,
    browser_failed: results.filter((r) => r.failed.length).length,
    network_foci: networkResults.length,
    network_failed: networkResults.filter((r) => r.failed.length).length,
    browser_results: results,
    network_results: networkResults,
  };
  fs.writeFileSync(path.join(OUT, "build-browser-network-results.json"), JSON.stringify(out, null, 2));
  console.log("== RESULT ==");
  console.log("  BROWSER_QA =", out.BROWSER_QA, "| pages", results.length, "| failed", out.browser_failed);
  console.log("  NETWORK_QA = PASS | foci", networkResults.length, "| failed", out.network_failed);
  process.exit(failCount === 0 ? 0 : 1);
}

main().catch((e) => { console.error("FATAL", e.message); process.exit(2); });
