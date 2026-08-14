// Post-Expansion Global Audit Phase 1 — browser + network QA (READ-ONLY).
// Verifies build output renders without console errors / overflow and the
// graph renders correctly for the 13 focus nodes. Emits JSON artifacts.
"use strict";
const WebSocket = require("ws");
const fs = require("fs");
const path = require("path");
const http = require("http");

const CDP_PORT = 9235;
const BASE = "http://127.0.0.1:4174/intelligence/africa";
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-post-expansion-global-audit-p1");
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
    const events = { console: [], exceptions: [], failed: [], logs: [] };
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
        events.console.push(m.params.args.map((a) => a.value || a.description || "").join(" "));
      } else if (m.method === "Runtime.exceptionThrown") {
        events.exceptions.push((m.params.exceptionDetails.exception && m.params.exceptionDetails.exception.description) || "exception");
      } else if (m.method === "Log.entryAdded" && m.params.entry.level === "error") {
        events.logs.push(m.params.entry.text);
      } else if (m.method === "Network.loadingFailed") {
        events.failed.push(m.params.errorText || "failed");
      }
    });
    s.on("open", () => res({ send, events }));
    s.on("error", rej);
  });
}

function withTimeout(p, ms, label) {
  return Promise.race([p, new Promise((_, j) => setTimeout(() => j(new Error("timeout " + label)), ms))]);
}

async function main() {
  const pageWs = await getPageWs();
  if (!pageWs) throw new Error("no page target on CDP");
  const { send, events } = await connect(pageWs);
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Network.enable");
  await send("Log.enable");
  await send("Network.setCacheDisabled", { cacheDisabled: true });

  const ev = (expr, tmo) => withTimeout(
    send("Runtime.evaluate", { expression: expr, returnByValue: true }),
    tmo || 12000, "ev").then((r) => (r && r.result) ? r.result.value : undefined);

  async function nav(url) {
    await withTimeout(send("Page.navigate", { url }), 15000, "nav");
    for (let w = 0; w < 24; w++) {
      const done = await withTimeout(ev("!!(document.querySelector('h1') || document.querySelector('.graph-node'))"), 6000, "w");
      if (done) break;
      await sleep(500);
    }
    await sleep(1200);
  }

  const results = [];
  let pageId = 0;
  const check = (name, pass, detail) => ({ name, pass, detail });

  async function pageGate(page, viewport, checks) {
    events.console.length = 0; events.exceptions.length = 0; events.failed.length = 0; events.logs.length = 0;
    await send("Emulation.setDeviceMetricsOverride", {
      width: viewport.width, height: viewport.height, deviceScaleFactor: 1,
      mobile: viewport.name === "mobile",
    });
    await nav(BASE + page.url);
    const gates = [];
    for (const c of checks) {
      const r = await ev(c.expr, 8000);
      gates.push(check(c.name, !!r, r === undefined ? "undefined" : JSON.stringify(r).slice(0, 120)));
    }
    const overflow = await ev("(function(){ var d=document.documentElement; return d.scrollWidth - d.clientWidth; })()");
    gates.push(check("no_horizontal_overflow", overflow <= 1, "overflow_px=" + overflow));
    gates.push(check("no_console_error", events.console.length === 0, "count=" + events.console.length));
    gates.push(check("no_exception", events.exceptions.length === 0, "count=" + events.exceptions.length));
    const failed = gates.filter((g) => !g.pass);
    results.push({
      key: page.key, viewport: viewport.name, url: page.url,
      state: { overflow, console: events.console.length, exc: events.exceptions.length, failed_req: events.failed.length },
      gates, failed: failed.map((g) => g.name),
    });
    pageId++;
    if (pageId % 8 === 0) console.log("  ...progress", pageId, "pages done");
    return failed.length;
  }

  // ---- Browser QA pages (entity + relation) ----
  const entityPages = [
    { key: "entity_mnjtf", url: "/entity/mnjtf/" },
    { key: "entity_fu_aes", url: "/entity/fu-aes/" },
    { key: "entity_g5", url: "/entity/g5-sahel-joint-force/" },
    { key: "entity_samim", url: "/entity/samim/" },
    { key: "entity_fadm", url: "/entity/mozambique-defence-forces/" },
    { key: "entity_rdf", url: "/entity/rwanda-force-mozambique/" },
    { key: "entity_tpdf", url: "/entity/tpdf/" },
    { key: "entity_africa_corps", url: "/entity/africa-corps/" },
    { key: "entity_lna", url: "/entity/libyan-national-army/" },
    { key: "entity_africom", url: "/entity/africom/" },
    { key: "entity_minusma", url: "/entity/minusma/" },
    { key: "entity_jnim", url: "/entity/jnim/" },
  ];
  const relationPages = [
    { key: "rel_mnjtf_iswap", url: "/relation/expe-mnjtf-iswap-hostile/" },
    { key: "rel_aes_jnim", url: "/relation/expe-aes-jnim-hostile/" },
    { key: "rel_africa_corps_wagner", url: "/relation/d1-africa-corps-wagner-history/" },
    { key: "rel_africom_shabaab", url: "/relation/expe-africom-shabaab-strikes/" },
    { key: "rel_fadm_ismoz", url: "/relation/fadm-is-moz-hostile/" },
    { key: "rel_fla_jnim", url: "/relation/d1-fla-jnim-cooperation/" },
  ];
  const viewports = [
    { name: "desktop", width: 1366, height: 900 },
    { name: "mobile", width: 390, height: 844 },
  ];

  console.log("== Browser QA (entity + relation pages) ==");
  let failCount = 0;
  for (const vp of viewports) {
    for (const p of entityPages) {
      failCount += await pageGate(p, vp, [
        { name: "h1", expr: "!!document.querySelector('h1')" },
        { name: "entity_heading", expr: "!!document.querySelector('#entityHeading h1, .entity-hero h1')" },
      ]);
    }
    for (const p of relationPages) {
      failCount += await pageGate(p, vp, [
        { name: "h1", expr: "!!document.querySelector('h1')" },
        { name: "relation_heading", expr: "!!document.querySelector('#relationHeading h1, .relation-hero h1')" },
      ]);
    }
  }

  // ---- Network QA (13 foci) ----
  console.log("== Network QA (13 foci) ==");
  const foci = ["actor-jnim", "actor-aqim", "actor-al-shabaab", "actor-isis-somalia",
    "actor-adf-isis-ca", "actor-is-mozambique", "actor-iswap", "actor-jas",
    "actor-africa-corps", "actor-mnjtf", "actor-fu-aes", "actor-africom", "actor-lna"];
  const networkResults = [];
  await send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 900, deviceScaleFactor: 1, mobile: false });
  for (const f of foci) {
    events.console.length = 0; events.exceptions.length = 0;
    await nav(BASE + "/network/?focus=" + f);
    await sleep(2500);
    const st = await ev("(function(){ " +
      "var nodes = document.querySelectorAll('.graph-node'); " +
      "var edges = document.querySelectorAll('.graph-edge, .graph-link, line.edge'); " +
      "var center = document.querySelector('.graph-node.is-center'); " +
      "return { nodes: nodes.length, edges: edges.length, center: center ? center.getAttribute('data-entity-id') : null }; })()");
    const gates = [
      check("nodes_rendered", st && st.nodes > 0, JSON.stringify(st)),
      check("center_present", st && !!st.center, JSON.stringify(st)),
      check("no_console_error", events.console.length === 0, "count=" + events.console.length),
    ];
    const failed = gates.filter((g) => !g.pass);
    networkResults.push({ focus: f, state: st, gates, failed: failed.map((g) => g.name) });
    if (failed.length) failCount += failed.length;
    console.log("  ", f, "nodes=" + (st && st.nodes), "edges=" + (st && st.edges), "center=" + (st && st.center), failed.length ? "FAIL" : "ok");
  }

  const browserGates = results.reduce((n, r) => n + r.failed.length, 0);
  const netGates = networkResults.reduce((n, r) => n + r.failed.length, 0);
  const totalPages = results.length;
  const totalGates = results.reduce((n, r) => n + r.gates.length, 0);

  const out = {
    artifact: "ui-route-regression-audit + network-qa",
    browser_pages: totalPages,
    browser_gates_total: totalGates,
    browser_gates_failed: browserGates,
    BROWSER_QA: browserGates === 0 ? "PASS" : "FAIL",
    network_foci: networkResults.length,
    network_gates_failed: netGates,
    NETWORK_QA: netGates === 0 ? "PASS" : "FAIL",
    browser_results: results,
    network_results: networkResults,
  };
  fs.writeFileSync(path.join(OUT, "browser-qa-results.json"), JSON.stringify(out, null, 2));
  fs.writeFileSync(path.join(OUT, "network-qa-results.json"), JSON.stringify({ network_results: networkResults, NETWORK_QA: out.NETWORK_QA }, null, 2));
  console.log("\n== RESULT ==");
  console.log("  BROWSER_QA =", out.BROWSER_QA, "| pages", totalPages, "| gates", totalGates, "| failed", browserGates);
  console.log("  NETWORK_QA =", out.NETWORK_QA, "| foci", networkResults.length, "| failed", netGates);
  process.exit(failCount === 0 ? 0 : 1);
}

main().catch((e) => { console.error("FATAL", e.message); process.exit(2); });
