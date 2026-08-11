/* UI/UX V2 browser QA: 19 representative pages x 3 viewports (57 real screenshots),
   console/exception/request/anchor/overflow gates, plus state extraction. */
"use strict";
const ws = require("ws");
const http = require("http");
const fs = require("fs");
const path = require("path");

const CDP = "http://127.0.0.1:9228";
const BASE = "http://127.0.0.1:4174/intelligence/africa/";
const OUT = path.resolve(__dirname, "..", "..", "qa-artifacts-uiux-v2");
const SHOTS = path.join(OUT, "screenshots");
fs.mkdirSync(SHOTS, { recursive: true });

const PAGES = [
  { key: "landing", url: BASE, label: "Landing" },
  { key: "entities", url: BASE + "entities/", label: "Entities list" },
  { key: "entity_al_shabaab", url: BASE + "entity/al-shabaab/", label: "Al-Shabaab" },
  { key: "entity_lakurawa", url: BASE + "entity/lakurawa/", label: "Lakurawa" },
  { key: "entity_updf", url: BASE + "entity/updf/", label: "UPDF" },
  { key: "entity_karate", url: BASE + "entity/mahad-karate/", label: "Mahad Karate" },
  { key: "relations", url: BASE + "relations/", label: "Relations list" },
  { key: "rel_shabaab_iss", url: BASE + "relation/expa-shabaab-isis-somalia-rivalry/", label: "Shabaab-ISIS-Somalia rivalry" },
  { key: "rel_lakurawa_is_sahel", url: BASE + "relation/d1-lakurawa-is-sahel-network/", label: "Lakurawa-IS-Sahel (disputed)" },
  { key: "rel_aussom_snaf", url: BASE + "relation/expb-aussom-snaf-cooperation/", label: "AUSSOM-SNAF" },
  { key: "network_al_shabaab", url: BASE + "network/?focus=actor-al-shabaab", label: "Network Al-Shabaab" },
  { key: "network_isis_somalia", url: BASE + "network/?focus=actor-isis-somalia", label: "Network ISIS-Somalia" },
  { key: "network_adf", url: BASE + "network/?focus=actor-adf-isis-ca", label: "Network ADF/ISIS-CA" },
  { key: "network_lakurawa", url: BASE + "network/?focus=actor-lakurawa", label: "Network Lakurawa" },
  { key: "sources", url: BASE + "sources/", label: "Sources" },
  { key: "regions", url: BASE + "regions/", label: "Regions list" },
  { key: "countries", url: BASE + "countries/", label: "Countries list" },
  { key: "region_central_sahel", url: BASE + "region/central-sahel/", label: "Region Central Sahel" },
  { key: "country_chad", url: BASE + "country/chad/", label: "Country Chad" },
];
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "laptop", width: 1280, height: 800 },
  { name: "mobile", width: 390, height: 844 },
];

function getTarget() {
  return new Promise((resolve, reject) => {
    http.get(CDP + "/json/list", (res) => {
      let d = "";
      res.on("data", (c) => (d += c));
      res.on("end", () => {
        const list = JSON.parse(d);
        const t = list.find((x) => x.type === "page" && !/^(edge|chrome-extension|devtools):/.test(x.url));
        resolve(t ? t.webSocketDebuggerUrl : null);
      });
    }).on("error", reject);
  });
}

function connect(url) {
  return new Promise((resolve, reject) => {
    const s = new ws(url);
    let id = 0;
    const pending = {};
    const events = { console: [], exceptions: [], failed: [], logs: [] };
    s.on("open", () => resolve({ s, pending, events, send }));
    s.on("error", reject);
    function send(method, params) {
      return new Promise((res, rej) => {
        const mid = ++id;
        pending[mid] = { res, rej };
        s.send(JSON.stringify({ id: mid, method, params: params || {} }));
      });
    }
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const target = await getTarget();
  if (!target) { console.log("NO_CDP_TARGET"); process.exit(1); }
  const { s, pending, events, send } = await connect(target);
  s.on("message", (raw) => {
    const m = JSON.parse(raw);
    if (m.id && pending[m.id]) {
      if (m.error) pending[m.id].rej(new Error(JSON.stringify(m.error)));
      else pending[m.id].res(m.result);
      delete pending[m.id];
      return;
    }
    if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") events.console.push(m.params);
    if (m.method === "Runtime.exceptionThrown") events.exceptions.push(m.params);
    if (m.method === "Network.loadingFailed") events.failed.push(m.params);
    if (m.method === "Log.entryAdded" && m.params.entry.level === "error") events.logs.push({ text: m.params.entry.text, source: m.params.entry.source, url: m.params.entry.url });
  });
  await send("Runtime.enable");
  await send("Network.enable");
  await send("Log.enable");
  await send("Page.enable");
  await send("Emulation.setDefaultBackgroundColorOverride", { color: { r: 255, g: 255, b: 255, a: 1 } });

  const results = [];
  const manifest = [];

  async function evaluate(expr) {
    const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) return { __err: String(r.exceptionDetails.exception && r.exceptionDetails.exception.description || r.exceptionDetails.text) };
    return r.result && r.result.value;
  }

  async function waitFor(expr, timeoutMs) {
    const t0 = Date.now();
    while (Date.now() - t0 < timeoutMs) {
      const v = await evaluate(expr);
      if (v) return true;
      await sleep(180);
    }
    return false;
  }

  for (const page of PAGES) {
    for (const vp of VIEWPORTS) {
      events.console.length = 0; events.exceptions.length = 0; events.failed.length = 0; events.logs.length = 0;
      await send("Emulation.setDeviceMetricsOverride", { width: vp.width, height: vp.height, deviceScaleFactor: 1, mobile: false });
      await send("Page.navigate", { url: page.url });
      const readyExpr = `new Promise(function (res) {
        function ok() {
          var err = document.querySelector("#intelError");
          if (err && !err.hidden) return res(true);
          if (!document.querySelector("h1")) return false;
          var body = document.body.getAttribute("data-africa-page");
          if (body === "entity") return !!document.querySelector("#entityBody .profile-section, #entityBody p");
          if (body === "relation") return !!document.querySelector("#relationBody") && (document.querySelector("#relationParties .relation-party-card") || document.querySelector("#relationOverview p"));
          if (body === "entities") return document.querySelectorAll("#allEntities .intel-card").length > 0;
          if (body === "relations") return document.querySelectorAll("#relationList .intel-rel-row").length > 0;
          if (body === "sources") return document.querySelectorAll("#sourceGrid .source-group").length > 0;
          if (body === "network") return document.querySelectorAll("#graphViewport .graph-node").length > 0;
          if (body === "region" || body === "country") return !!document.querySelector("#regionBody, #countryBody");
          if (body === "home") return !!document.querySelector("#entityGrid .intel-card");
          return document.querySelector("#intelError") ? true : false;
        }
        var t0 = Date.now();
        (function tick() { if (ok()) res(true); else if (Date.now() - t0 > 9000) res(false); else setTimeout(tick, 150); })();
      })`;
      const loaded = await waitFor(readyExpr, 10000);
      await sleep(450); // let scroll-spy / lazy paint settle
      const state = await evaluate(`(function () {
        var h1 = document.querySelector("h1");
        var toc = document.querySelector("#entityToc");
        var kf = document.querySelector("#entityKeyFacts");
        var secs = document.querySelectorAll("#entityBody .profile-section");
        var anchors = Array.prototype.slice.call(document.querySelectorAll("a[href^='#']"));
        var brokenAnchors = 0;
        anchors.forEach(function (a) { var t = document.querySelector(a.getAttribute("href")); if (!t) brokenAnchors++; });
        var overflow = document.documentElement.scrollWidth > window.innerWidth + 1;
        var zh = 0, en = 0;
        if (h1) { zh = parseInt(getComputedStyle(h1).fontSize, 10); }
        var enEl = document.querySelector(".intel-title-en"); if (enEl) en = parseInt(getComputedStyle(enEl).fontSize, 10);
        return {
          title: document.title,
          h1: h1 ? h1.textContent.slice(0, 90) : "",
          h1_font: zh,
          en_font: en,
          sections: secs.length,
          toc_links: toc ? toc.querySelectorAll(".profile-toc a").length : -1,
          toc_hidden: toc ? toc.hidden : -1,
          toc_details_open: toc ? (toc.querySelector("details") ? toc.querySelector("details").open : null) : null,
          keyfacts: kf ? kf.children.length : -1,
          party_cards: document.querySelectorAll("#relationParties .relation-party-card").length,
          hero_summary: document.querySelectorAll("#relationParties .relation-hero-summary").length,
          tl_stages: document.querySelectorAll(".rtl-stage-card").length,
          current_banner: document.querySelectorAll(".rtl-current-banner").length,
          disputed_badges: document.querySelectorAll(".intel-badge.disputed").length,
          uncertainty_cards: document.querySelectorAll(".intel-uncertainty-card").length,
          source_groups: document.querySelectorAll("#sourceGrid .source-group").length,
          entity_inline_links: document.querySelectorAll("#entityBody a[href*='/entity/'], #entityBody a[href*='/country/']").length,
          rel_inline_links: document.querySelectorAll("#relationBody a[href*='/entity/'], #relationBody a[href*='/country/'], #relationOverview a[href*='/entity/']").length,
          list_count: (function () { var e = document.querySelector("#entityCount") || document.querySelector("#relCount"); return e ? e.textContent : ""; })(),
          broken_anchors: brokenAnchors,
          h_overflow: overflow,
          scroll_height: document.documentElement.scrollHeight,
          nodes: document.querySelectorAll("#graphViewport .graph-node").length,
          edges: document.querySelectorAll("#graphViewport .graph-edge-group").length,
          density_note_visible: (function () { var d = document.querySelector("#densityNote"); return d ? !d.hidden : false; })(),
          loaded: ${JSON.stringify(loaded)}
        };
      })()`);
      const shotName = page.key + "_" + vp.name + ".png";
      const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      fs.writeFileSync(path.join(SHOTS, shotName), Buffer.from(shot.data, "base64"));
      manifest.push({ file: shotName, page: page.key, viewport: vp.name, width: vp.width, height: vp.height });
      results.push({
        key: page.key, label: page.label, viewport: vp.name,
        url: page.url,
        state: state,
        console_errors: events.console.length,
        exceptions: events.exceptions.length,
        failed_requests: events.failed.length,
        log_errors: events.logs.length,
        log_details: events.logs.slice(0, 5),
      });
      console.log("shot", shotName, "| h1:", state.h1 ? state.h1.slice(0, 34) : "-", "| toc:", state.toc_links, "| kf:", state.keyfacts, "| ovf:", state.h_overflow);
    }
  }

  // ---- gates ----
  const consoleErrors = results.reduce((n, r) => n + r.console_errors + r.exceptions + r.log_errors, 0);
  const failedRequests = results.reduce((n, r) => n + r.failed_requests, 0);
  const brokenAnchors = results.reduce((n, r) => n + (r.state.broken_anchors || 0), 0);
  const horizontalOverflow = results.filter((r) => r.state.h_overflow).map((r) => r.key + ":" + r.viewport);
  const summary = {
    pagesChecked: results.length,
    screenshots: manifest.length,
    consoleErrors,
    runtimeExceptions: results.reduce((n, r) => n + r.exceptions, 0),
    failedRequests,
    brokenAnchors,
    horizontalOverflow,
    overflowPages: horizontalOverflow,
    gate: consoleErrors === 0 && failedRequests === 0 && brokenAnchors === 0 && horizontalOverflow.length === 0 ? "PASS" : "FAIL",
  };
  fs.writeFileSync(path.join(OUT, "browser-qa.json"), JSON.stringify({ summary, results }, null, 2));
  fs.writeFileSync(path.join(OUT, "screenshot-manifest.json"), JSON.stringify({ summary: { count: manifest.length }, screenshots: manifest }, null, 2));
  console.log("BROWSER_QA gate:", summary.gate, "| pages:", summary.pagesChecked, "| shots:", summary.screenshots, "| console:", summary.consoleErrors, "| req:", summary.failedRequests, "| anchors:", summary.brokenAnchors, "| overflow:", summary.horizontalOverflow);
  process.exit(0);
}

main().catch((e) => { console.error("QA FAIL", e); process.exit(1); });
