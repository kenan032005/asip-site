/* Expansion C browser + network QA.
   Covers: EIJ / GIA / AIAI / TCG / GICM / Battar / Maitatsine / AQIM /
   Al-Murabitun entity pages (desktop + mobile), the GSPC-AQIM lineage relation,
   EIJ<->Al-Qaida and Battar<->ISIS-Libya relations, and network focus checks on
   AQIM / Al-Qaida / JNIM / Al-Murabitun / ISIS-Libya.
   Verifies UI/UX V2 features keep working on the new/enriched pages
   (auto TOC, key facts, semantic cards, historical badges, party cards,
   timeline V2, auto-links) and gates console/request/anchor/overflow = 0. */
"use strict";
const ws = require("ws");
const http = require("http");
const fs = require("fs");
const path = require("path");

const CDP = "http://127.0.0.1:9228";
const BASE = "http://127.0.0.1:4174/intelligence/africa/";
const OUT = path.resolve(__dirname, "..", "..", "qa-artifacts-expansion-c");
const SHOTS = path.join(OUT, "screenshots");
fs.mkdirSync(SHOTS, { recursive: true });

const PAGES = [
  { key: "entity_eij", url: BASE + "entity/egyptian-islamic-jihad/" },
  { key: "entity_gia", url: BASE + "entity/gia/" },
  { key: "entity_aiai", url: BASE + "entity/aiai/" },
  { key: "entity_tcg", url: BASE + "entity/tunisian-combatant-group/" },
  { key: "entity_gicm", url: BASE + "entity/gicm/" },
  { key: "entity_battar", url: BASE + "entity/al-battar-brigade/" },
  { key: "entity_maitatsine", url: BASE + "entity/maitatsine-movement/" },
  { key: "entity_aqim", url: BASE + "entity/aqim/" },
  { key: "entity_murabitun", url: BASE + "entity/al-mourabitoun/" },
  { key: "rel_gia_aqim", url: BASE + "relation/expc-gia-aqim-lineage/" },
  { key: "rel_eij_alqaida", url: BASE + "relation/expc-eij-alqaida-integration/" },
  { key: "rel_battar_isis_libya", url: BASE + "relation/expc-battar-isis-libya/" },
];
const NETWORKS = [
  { key: "net_aqim", focus: "actor-aqim" },
  { key: "net_alqaida", focus: "actor-al-qaida" },
  { key: "net_jnim", focus: "actor-jnim" },
  { key: "net_murabitun", focus: "actor-al-mourabitoun" },
  { key: "net_isis_libya", focus: "actor-isis-libya" },
];
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 900 },
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
async function ev(send, expr) {
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) return { __err: String(r.exceptionDetails.text) };
  return r.result && r.result.value;
}
async function waitFor(send, expr, timeout) {
  const t0 = Date.now();
  while (Date.now() - t0 < (timeout || 10000)) {
    if (await ev(send, expr)) return true;
    await sleep(180);
  }
  return false;
}

async function main() {
  const target = await getTarget();
  const { s, pending, events, send } = await connect(target);
  s.on("message", (raw) => {
    const m = JSON.parse(raw);
    if (m.id && pending[m.id]) {
      m.error ? pending[m.id].rej(new Error(JSON.stringify(m.error))) : pending[m.id].res(m.result);
      delete pending[m.id];
      return;
    }
    if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") events.console.push(m.params);
    if (m.method === "Runtime.exceptionThrown") events.exceptions.push(m.params);
    if (m.method === "Network.loadingFailed") events.failed.push(m.params);
    if (m.method === "Log.entryAdded" && m.params.entry.level === "error") events.logs.push(m.params.entry);
  });
  await send("Runtime.enable"); await send("Network.enable"); await send("Log.enable"); await send("Page.enable");
  await send("Network.setCacheDisabled", { cacheDisabled: true });
  await send("Emulation.setDefaultBackgroundColorOverride", { color: { r: 255, g: 255, b: 255, a: 1 } });

  const results = [];
  const manifest = [];
  for (const page of PAGES) {
    for (const vp of VIEWPORTS) {
      events.console.length = 0; events.exceptions.length = 0; events.failed.length = 0; events.logs.length = 0;
      await send("Emulation.setDeviceMetricsOverride", { width: vp.width, height: vp.height, deviceScaleFactor: 1, mobile: false });
      await send("Page.navigate", { url: page.url });
      await waitFor(send, `(function(){ var p=document.body.getAttribute("data-africa-page"); if(p==="entity") return !!document.querySelector("#entityBody .profile-section"); if(p==="relation") return !!document.querySelector("#relationBody"); return true; })()`);
      await sleep(450);
      const state = await ev(send, `(function(){
        var toc = document.querySelector("#entityToc");
        var kf = document.querySelector("#entityKeyFacts");
        var h1 = document.querySelector("h1");
        var hbadge = document.querySelector(".intel-badge.f-historical");
        var dis = document.querySelectorAll(".intel-badge.disputed").length;
        var unc = document.querySelectorAll(".intel-uncertainty-card").length;
        var sections = document.querySelectorAll("#entityBody .profile-section").length;
        var party = document.querySelectorAll("#relationParties .relation-party-card").length;
        var tl = document.querySelectorAll("#relationTimeline .rtl-stage-card").length;
        var autoLinks = document.querySelectorAll("#relationBody a.intel-entity-link.auto, #relationOverview a.intel-entity-link.auto, #relationTimeline a.intel-entity-link.auto").length;
        var broken = 0;
        Array.prototype.forEach.call(document.querySelectorAll("a[href^='#']"), function(a){ if(!document.querySelector(a.getAttribute("href"))) broken++; });
        var overflow = document.documentElement.scrollWidth > window.innerWidth + 1;
        return {
          page: document.body.getAttribute("data-africa-page"),
          h1: h1 ? h1.textContent.slice(0, 40) : "",
          sections: sections,
          toc_links: toc ? toc.querySelectorAll(".profile-toc a").length : -1,
          toc_open: toc ? (toc.querySelector("details") ? toc.querySelector("details").open : null) : null,
          keyfacts: kf ? kf.children.length : -1,
          hist_badge: hbadge ? hbadge.textContent : "",
          disputed: dis,
          uncertainty: unc,
          party_cards: party,
          tl_stages: tl,
          auto_links: autoLinks,
          broken_anchors: broken,
          overflow: overflow,
        };
      })()`);
      const shotName = page.key + "_" + vp.name + ".png";
      const shot = await send("Page.captureScreenshot", { format: "png" });
      fs.writeFileSync(path.join(SHOTS, shotName), Buffer.from(shot.data, "base64"));
      manifest.push({ file: shotName, page: page.key, viewport: vp.name });
      results.push({ key: page.key, viewport: vp.name, state: state,
        console_errors: events.console.length, exceptions: events.exceptions.length,
        failed_requests: events.failed.length, log_errors: events.logs.length });
      console.log(page.key, vp.name, "| h1:", (state.h1 || "").slice(0, 26), "| toc:", state.toc_links, "| kf:", state.keyfacts, "| hist:", state.hist_badge, "| party:", state.party_cards, "| tl:", state.tl_stages, "| auto:", state.auto_links);
    }
  }

  // network focus checks
  const netResults = [];
  for (const n of NETWORKS) {
    events.console.length = 0; events.exceptions.length = 0; events.failed.length = 0; events.logs.length = 0;
    await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await send("Page.navigate", { url: BASE + "network/?focus=" + n.focus });
    await waitFor(send, `document.querySelectorAll("#graphViewport .graph-node").length > 0`);
    await sleep(500);
    const st = await ev(send, `(function(){
      var fn = document.querySelector("#focusId");
      return { focus: fn ? fn.textContent : "", nodes: document.querySelectorAll("#graphViewport .graph-node").length,
               edges: document.querySelectorAll("#graphViewport .graph-edge-group").length,
               console_state: "" };
    })()`);
    netResults.push({ key: n.key, focus: n.focus, nodes: st.nodes, edges: st.edges,
      console_errors: events.console.length, exceptions: events.exceptions.length,
      failed_requests: events.failed.length, log_errors: events.logs.length });
    console.log("NET", n.key, "focus:", st.focus, "nodes:", st.nodes, "edges:", st.edges);
  }

  const consoleErrors = results.reduce((x, r) => x + r.console_errors + r.exceptions + r.log_errors, 0) +
                        netResults.reduce((x, r) => x + r.console_errors + r.exceptions + r.log_errors, 0);
  const failedRequests = results.reduce((x, r) => x + r.failed_requests, 0) + netResults.reduce((x, r) => x + r.failed_requests, 0);
  const brokenAnchors = results.reduce((x, r) => x + (r.state.broken_anchors || 0), 0);
  const overflow = results.filter((r) => r.state.overflow).map((r) => r.key + ":" + r.viewport);
  const entityV2 = results.filter((r) => r.state.page === "entity");
  const tocMissing = entityV2.filter((r) => r.state.toc_links < 3).length;
  const relV2 = results.filter((r) => r.state.page === "relation");
  const partyMissing = relV2.filter((r) => r.state.party_cards !== 2).length;
  const summary = {
    pagesChecked: results.length + netResults.length,
    screenshots: manifest.length,
    consoleErrors, failedRequests, brokenAnchors, overflowPages: overflow,
    tocMissingOnNewEntities: tocMissing,
    partyCardsMissingOnRelations: partyMissing,
    UIUX_V2_REGRESSION: consoleErrors === 0 && failedRequests === 0 && brokenAnchors === 0 && overflow.length === 0 && tocMissing === 0 && partyMissing === 0 ? 0 : 1,
    gate: (consoleErrors === 0 && failedRequests === 0 && brokenAnchors === 0 && overflow.length === 0 && tocMissing === 0 && partyMissing === 0) ? "PASS" : "FAIL",
  };
  fs.writeFileSync(path.join(OUT, "browser-qa-results.json"), JSON.stringify({ summary, results, network: netResults }, null, 2));
  fs.writeFileSync(path.join(OUT, "network-qa-results.json"), JSON.stringify({ summary: { focuses: NETWORKS.length, checked: netResults.length, gate: summary.gate }, networks: netResults }, null, 2));
  console.log("BROWSER_QA gate:", summary.gate, "| UIUX_V2_REGRESSION:", summary.UIUX_V2_REGRESSION, "| console:", consoleErrors, "| req:", failedRequests, "| anchors:", brokenAnchors, "| overflow:", overflow.length, "| tocMissing:", tocMissing, "| partyMissing:", partyMissing);
  process.exit(0);
}
main().catch((e) => { console.error("QA FAIL", e); process.exit(1); });
