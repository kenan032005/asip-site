#!/usr/bin/env node
/* Online polish QA against the real public preview URL (desktop + mobile). */
const fs = require("fs");
const path = require("path");
const http = require("http");
const ws = require("ws");

const BASE = "https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa";
const CDP_PORT = 9230;
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-ui-final-polish-1", "online-browser-qa.json");

function getTarget() {
  return new Promise((res, rej) => {
    http.get(`http://127.0.0.1:${CDP_PORT}/json/list`, (r) => {
      let d = "";
      r.on("data", (c) => (d += c));
      r.on("end", () => {
        const list = JSON.parse(d);
        const t = list.find((x) => x.type === "page" && !/^(edge|chrome-extension|devtools):/.test(x.url));
        res(t ? t.webSocketDebuggerUrl : null);
      });
    }).on("error", rej);
  });
}
function connect(url) {
  return new Promise((res, rej) => {
    const s = new ws(url);
    let id = 0;
    const pending = {};
    let eventHandler = null;
    const send = (m, p) => new Promise((r, j) => { const mid = ++id; pending[mid] = { r, j }; s.send(JSON.stringify({ id: mid, method: m, params: p || {} })); });
    s.on("message", (raw) => { const m = JSON.parse(raw); if (m.id && pending[m.id]) { m.error ? pending[m.id].j(new Error(JSON.stringify(m.error))) : pending[m.id].r(m.result); delete pending[m.id]; } else if (m.method && eventHandler) eventHandler(m); });
    send.onEvent = (fn) => { eventHandler = fn; };
    s.on("open", () => res(send));
  });
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const withTimeout = (p, ms, tag) => Promise.race([p, sleep(ms).then(() => { throw new Error("TIMEOUT:" + tag); })]);

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
];

const PAGES = [
  { key: "home", url: "/" },
  { key: "entity_al_shabaab", url: "/entity/al-shabaab/" },
  { key: "entity_aqim", url: "/entity/aqim/" },
  { key: "entity_eij", url: "/entity/egyptian-islamic-jihad/" },
  { key: "entity_gia", url: "/entity/gia/" },
  { key: "entity_lakurawa", url: "/entity/lakurawa/" },
  { key: "rel_jnim_niger", url: "/relation/jnim-niger-operates/" },
  { key: "rel_eij_alqaida", url: "/relation/expc-eij-alqaida-integration/" },
  { key: "rel_lakurawa_is_sahel", url: "/relation/d1-lakurawa-is-sahel-network/" },
  { key: "network_al_shabaab", url: "/network/?focus=actor-al-shabaab" },
  { key: "network_aqim", url: "/network/?focus=actor-aqim" },
  { key: "network_jnim", url: "/network/?focus=actor-jnim" },
  { key: "network_isis_somalia", url: "/network/?focus=actor-isis-somalia" },
  { key: "network_lakurawa", url: "/network/?focus=actor-lakurawa" },
];

const STATE_EXPR = `(function () {
  var out = {
    h1: (document.querySelector("h1") || {}).textContent || "",
    sections: document.querySelectorAll(".profile-section").length,
    toc_links: document.querySelectorAll("#entityToc a, .profile-toc a").length,
    toc_close: !!document.querySelector(".toc-close-btn"),
    source_last: (function(){ var b = document.querySelector("#entityBody"); if(!b) return null; var secs = b.querySelectorAll(".profile-section"); if(!secs.length) return null; return secs[secs.length-1].id; })(),
    section_markers: (function(){ var s = document.querySelectorAll(".intel-section-title>span"); return Array.prototype.map.call(s, function(x){ return parseFloat(getComputedStyle(x).fontSize); }); })(),
    country_chips: document.querySelectorAll("#countryGrid .intel-region-chip").length,
    country_summary: document.querySelectorAll("#countryGrid .intel-country-summary").length,
    rel_tech_details: !!document.querySelector(".rel-tech-details"),
    rel_tech_open: (function(){ var d = document.querySelector(".rel-tech-details"); return d ? d.open : null; })(),
    rel_party: document.querySelectorAll(".relation-party-card").length,
    rel_h1_has_machine: (function(){ var h = document.querySelector("#relationHeading h1"); return h ? h.textContent.indexOf("rel-") >= 0 : false; })(),
    net_short_labels: document.querySelectorAll(".graph-node .node-label.short").length,
    net_center: document.querySelectorAll(".graph-node.is-center .center-label").length,
    net_tooltips: document.querySelectorAll(".graph-node title").length,
    net_legend_checks: document.querySelectorAll(".graph-legend input[type=checkbox]").length,
    net_stats: document.querySelector("#graphVisStats") ? document.querySelector("#graphVisStats").textContent : "",
    net_label_modes: document.querySelectorAll("[data-label-mode]").length,
    overflow: document.documentElement.scrollWidth > window.innerWidth + 2,
    broken_anchors: (function(){ return Array.prototype.filter.call(document.querySelectorAll("a[href*='#']"), function (a) { var h = a.getAttribute("href"); if (!h || h === "#") return false; var id = h.split("#")[1]; return id && !document.getElementById(id); }).length; })(),
  };
  return out;
})()`;

(async () => {
  const send = await connect(await getTarget());
  await send("Runtime.enable");
  await send("Network.enable");
  await send("Network.setCacheDisabled", { cacheDisabled: true });
  await send("Page.enable");
  await send("Log.enable");

  const results = [];
  let shots = 0;
  for (const page of PAGES) {
    for (const vp of VIEWPORTS) {
      const events = { console: [], exceptions: [], failed: [], logs: [] };
      send.onEvent((m) => {
        if (m.method === "Runtime.consoleAPICalled" && ["error", "assert"].includes(m.params.type)) events.console.push(m.params);
        if (m.method === "Runtime.exceptionThrown") events.exceptions.push(m.params);
        if (m.method === "Network.loadingFailed" && m.params.canceled !== true) events.failed.push(m.params);
        if (m.method === "Log.entryAdded" && m.params.entry.level === "error") events.logs.push(m.params.entry);
      });
      await withTimeout(send("Emulation.setDeviceMetricsOverride", { width: vp.width, height: vp.height, deviceScaleFactor: 1, mobile: vp.name === "mobile" }), 8000, "viewport");
      const url = BASE + page.url;
      let entry;
      try {
        await withTimeout(send("Page.navigate", { url }), 15000, "nav");
        await sleep(vp.name === "mobile" ? 5200 : 4500);
        // wait until the page heading actually renders (up to 8s)
        for (let w = 0; w < 16; w++) {
          const done = await withTimeout(send("Runtime.evaluate", { expression: "!!(document.querySelector('#entityHeading h1') || document.querySelector('#relationHeading h1') || document.querySelector('.graph-node'))", returnByValue: true }), 6000, "w");
          if (done && done.result && done.result.value) break;
          await sleep(500);
        }
        const state = await withTimeout(send("Runtime.evaluate", { expression: STATE_EXPR, returnByValue: true }), 12000, "eval");
        const shot = path.join(__dirname, "..", "..", "qa-artifacts-ui-final-polish-1", "screenshots", `${page.key}_${vp.name}.png`);
        fs.mkdirSync(path.dirname(shot), { recursive: true });
        const shotRes = await withTimeout(send("Page.captureScreenshot", { format: "png" }), 15000, "shot");
        fs.writeFileSync(shot, Buffer.from(shotRes.data, "base64"));
        shots++;
        entry = { key: page.key, viewport: vp.name, url, state: state.result.value, console_errors: events.console.length, exceptions: events.exceptions.length, failed_requests: events.failed.length, log_errors: events.logs.length };
      } catch (err) {
        entry = { key: page.key, viewport: vp.name, url, state: { h1: "", error: String(err).slice(0, 150) }, console_errors: events.console.length, exceptions: events.exceptions.length, failed_requests: events.failed.length, log_errors: events.logs.length, page_error: String(err).slice(0, 200) };
      }
      results.push(entry);
      console.log(`[done] ${page.key} @ ${vp.name} — c=${entry.console_errors} e=${entry.exceptions} r=${entry.failed_requests}${entry.page_error ? " ERR" : ""} shots=${shots}`);
    }
  }

  // derive feature gates
  const summary = {
    base: BASE,
    pages_checked: results.length,
    screenshots: shots,
    console_errors: results.reduce((a, r) => a + r.console_errors, 0),
    exceptions: results.reduce((a, r) => a + r.exceptions, 0),
    failed_requests: results.reduce((a, r) => a + r.failed_requests, 0),
    log_errors: results.reduce((a, r) => a + r.log_errors, 0),
    broken_anchors: results.reduce((a, r) => a + (r.state.broken_anchors || 0), 0),
    overflow_pages: results.filter((r) => r.state.overflow).map((r) => `${r.key}@${r.viewport}`),
    gates: {
      HOMEPAGE_SECTION_UI: results.some((r) => r.key === "home" && (r.state.section_markers || []).length >= 2 && r.state.section_markers.every((x) => x >= 18)),
      COUNTRY_ENTRY_REDESIGN: results.some((r) => r.key === "home" && r.state.country_chips >= 3 && r.state.country_summary >= 3),
      RELATION_HERO_SIMPLIFIED: results.some((r) => r.key === "rel_jnim_niger" && r.state.rel_tech_details && r.state.rel_tech_open === false && r.state.rel_h1_has_machine === false),
      ENTITY_TOC_BEHAVIOR: results.some((r) => r.key === "entity_al_shabaab" && r.state.toc_close === true),
      ENTITY_SOURCE_ORDER: results.some((r) => r.key === "entity_al_shabaab" && r.state.source_last === "sec-sources"),
      NETWORK_REDESIGN: results.some((r) => r.key.startsWith("network_") && r.state.net_center === 1 && r.state.net_short_labels > 0 && r.state.net_tooltips > 0),
      LEGEND_VISIBILITY_FILTER: results.some((r) => r.key.startsWith("network_") && r.state.net_legend_checks === 8 && r.state.net_stats.indexOf("当前可见") >= 0 && r.state.net_label_modes === 3),
    },
    gate: (() => {
      const g = {};
      const ok = results.every((r) => r.console_errors === 0 && r.exceptions === 0 && r.failed_requests === 0 && r.log_errors === 0 && !r.state.overflow);
      return ok && Object.values(summary2gate(results)).every(Boolean);
    })(),
  };
  function summary2gate(results2) {
    return {
      HOMEPAGE_SECTION_UI: results2.some((r) => r.key === "home" && (r.state.section_markers || []).length >= 2 && r.state.section_markers.every((x) => x >= 18)),
      COUNTRY_ENTRY_REDESIGN: results2.some((r) => r.key === "home" && r.state.country_chips >= 3 && r.state.country_summary >= 3),
      RELATION_HERO_SIMPLIFIED: results2.some((r) => r.key === "rel_jnim_niger" && r.state.rel_tech_details && r.state.rel_tech_open === false && r.state.rel_h1_has_machine === false),
      ENTITY_TOC_BEHAVIOR: results2.some((r) => r.key === "entity_al_shabaab" && r.state.toc_close === true),
      ENTITY_SOURCE_ORDER: results2.some((r) => r.key === "entity_al_shabaab" && r.state.source_last === "sec-sources"),
      NETWORK_REDESIGN: results2.some((r) => r.key.startsWith("network_") && r.state.net_center === 1 && r.state.net_short_labels > 0 && r.state.net_tooltips > 0),
      LEGEND_VISIBILITY_FILTER: results2.some((r) => r.key.startsWith("network_") && r.state.net_legend_checks === 8 && r.state.net_stats.indexOf("当前可见") >= 0 && r.state.net_label_modes === 3),
    };
  }
  summary.gates = summary2gate(results);
  summary.gate = results.every((r) => r.console_errors === 0 && r.exceptions === 0 && r.failed_requests === 0 && r.log_errors === 0 && !r.state.overflow) && Object.values(summary.gates).every(Boolean);
  fs.writeFileSync(OUT, JSON.stringify({ summary, results }, null, 2), "utf-8");
  console.log("\n=== ONLINE POLISH BROWSER QA ===");
  console.log(JSON.stringify({ gate: summary.gate, gates: summary.gates, console: summary.console_errors, exc: summary.exceptions, req: summary.failed_requests, overflow: summary.overflow_pages }, null, 2));
  process.exit(summary.gate ? 0 : 1);
})().catch((e) => { console.error("FATAL", e); process.exit(2); });
