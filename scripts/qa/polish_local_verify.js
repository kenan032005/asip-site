#!/usr/bin/env node
/* Local validation of UI Final Polish Pack 1 changes (localhost dist). */
const fs = require("fs");
const path = require("path");
const http = require("http");
const ws = require("ws");

const BASE = "http://127.0.0.1:4174/intelligence/africa";
const CDP_PORT = 9230;
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-ui-final-polish-1", "local-polish-verify.json");

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

(async () => {
  const send = await connect(await getTarget());
  await send("Runtime.enable");
  await send("Network.enable");
  await send("Network.setCacheDisabled", { cacheDisabled: true });
  await send("Page.enable");
  await send("Log.enable");

  const checks = [];
  const check = (name, pass, detail) => checks.push({ name, pass: !!pass, detail: String(detail || "").slice(0, 220) });
  const ev = (expr) => withTimeout(send("Runtime.evaluate", { expression: expr, returnByValue: true }), 12000, "ev").then((r) => r.result.value);
  const nav = async (p2, wait = 4200) => { await withTimeout(send("Page.navigate", { url: BASE + p2 }), 15000, "nav"); await sleep(wait); };

  // 1. homepage section markers
  await nav("/");
  const home = await ev(`(function(){
    var spans = Array.prototype.map.call(document.querySelectorAll(".intel-section-title>span"), function(s){ return { t: s.textContent, fs: parseFloat(getComputedStyle(s).fontSize), bg: getComputedStyle(s).backgroundColor }; });
    var cards = document.querySelectorAll("#countryGrid .intel-card");
    var chips = document.querySelectorAll("#countryGrid .intel-region-chip").length;
    var chipLinks = Array.prototype.slice.call(document.querySelectorAll("#countryGrid a.intel-region-chip")).length;
    return { spans: spans.slice(0, 2), cardCount: cards.length, chips: chips, chipLinks: chipLinks, firstCardHTML: cards[0] ? cards[0].innerHTML.slice(0, 260) : "" };
  })()`);
  const homeBg = await ev(`(function(){ var s = document.querySelector(".intel-section-title>span"); return getComputedStyle(s).backgroundImage; })()`);
  check("homepage section markers enlarged (01/02 >= 18px + gradient bg)", home.spans.length >= 2 && home.spans.every((x) => x.fs >= 18) && homeBg.indexOf("gradient") >= 0, "fs=" + JSON.stringify(home.spans.map((x) => x.fs)) + " bg=" + homeBg.slice(0, 60));
  check("country card is integrated (chips present + no bare region text)", home.chips >= 3 && home.chips === home.chipLinks, "chips=" + home.chips + " links=" + home.chipLinks);
  const countrySummary = await ev(`(function(){ var el = document.querySelector("#countryGrid .intel-country-summary"); return el ? el.textContent.slice(0, 60) : ""; })()`);
  check("country card has code+risk+summary", home.firstCardHTML.indexOf("intel-code") >= 0 && home.firstCardHTML.indexOf("risk-") >= 0 && countrySummary.length > 0, "summary=" + countrySummary);

  // 2. relation hero simplified
  await nav("/relation/jnim-niger-operates/");
  const rel = await ev(`(function(){
    var head = document.querySelector("#relationHeading");
    var headingText = head ? head.textContent : "";
    var tech = document.querySelector(".rel-tech-details");
    var techOpen = tech ? tech.open : null;
    var h1 = (document.querySelector("#relationHeading h1") || {}).textContent || "";
    return { hasMachineIdInHeading: headingText.indexOf("rel-jnim-niger-operates") >= 0, techDetails: !!tech, techOpen: techOpen, h1: h1, heroSummary: document.querySelectorAll(".relation-hero-summary").length, partyCards: document.querySelectorAll(".relation-party-card").length, techBodyText: tech ? tech.textContent.slice(0, 80) : "" };
  })()`);
  check("relation hero hides machine id by default", rel.h1.indexOf("rel-") < 0 && rel.h1.indexOf("尼日尔") >= 0 && rel.techBodyText.indexOf("rel-jnim-niger-operates") >= 0, JSON.stringify(rel));
  check("relation hero tech metadata collapsed (holds machine id inside)", rel.techDetails === true && rel.techOpen === false && rel.techBodyText.indexOf("rel-jnim-niger-operates") >= 0, JSON.stringify(rel));
  check("relation hero keeps party cards + summary", rel.partyCards === 2 && rel.heroSummary === 1, JSON.stringify(rel));

  // 3. entity TOC + sources order
  await nav("/entity/al-shabaab/");
  const ent = await ev(`(function(){
    var toc = document.querySelector("#entityToc");
    var tocHeight = toc ? toc.getBoundingClientRect().height : 0;
    var closeBtn = !!document.querySelector("#entityToc .toc-close-btn");
    var body = document.querySelector("#entityBody");
    var secs = body ? Array.prototype.map.call(body.querySelectorAll(".profile-section"), function(x){ return x.id; }) : [];
    var sourceIdx = secs.indexOf("sec-sources");
    var last = secs[secs.length - 1];
    return { tocHeight: Math.round(tocHeight), closeBtn: closeBtn, sections: secs.length, sourceIdx: sourceIdx, last: last, lastIsSource: last === "sec-sources" || last === "sec-notes" };
  })()`);
  check("entity TOC has close button + bounded height", ent.closeBtn === true && ent.tocHeight <= 500, JSON.stringify(ent));
  check("entity sources moved to end", ent.sourceIdx >= 0 && (ent.lastIsSource || ent.sourceIdx === ent.sections - 1), JSON.stringify(ent));

  // 4. network: labels + legend + detail panel
  await nav("/network/?focus=actor-al-shabaab");
  const net = await ev(`(function(){
    var short = document.querySelectorAll(".graph-node .node-label.short").length;
    var center = document.querySelectorAll(".graph-node.is-center .center-label").length;
    var tooltip = document.querySelectorAll(".graph-node title").length;
    var legendChecks = document.querySelectorAll(".graph-legend input[type=checkbox]").length;
    var visStats = document.querySelector("#graphVisStats") ? document.querySelector("#graphVisStats").textContent : "";
    var labelModeBtns = document.querySelectorAll("[data-label-mode]").length;
    return { shortLabels: short, centerLabels: center, tooltips: tooltip, legendChecks: legendChecks, visStats: visStats, labelModeBtns: labelModeBtns };
  })()`);
  check("network short labels + center full label + tooltips", net.shortLabels > 0 && net.centerLabels === 1 && net.tooltips > 0, JSON.stringify(net));
  check("interactive legend checkboxes (8) + visible stats + label modes", net.legendChecks === 8 && net.visStats.indexOf("当前可见") >= 0 && net.labelModeBtns === 3, JSON.stringify(net));

  // 4b. click a node -> detail panel
  await ev(`(function(){ var n = document.querySelector(".graph-node:not(.is-center)"); if (n) n.dispatchEvent(new MouseEvent("click", {bubbles:true})); return !!n; })()`);
  await sleep(1200);
  const nd = await ev(`(function(){ var p = document.querySelector("#nodeInfo .intel-node-detail"); return p ? { has: true, text: p.textContent.slice(0, 140) } : { has: false }; })()`);
  check("node click opens detail panel", nd.has === true && nd.text.length > 40, JSON.stringify(nd));

  // 4c. legend visibility toggle hides nodes + edge relayout
  await ev(`(function(){ var c = document.getElementById("lvNodeOrg"); if (c) { c.checked = false; c.dispatchEvent(new Event("change", {bubbles:true})); } return true; })()`);
  await sleep(1200);
  const afterHide = await ev(`(function(){ var orgs = document.querySelectorAll(".graph-node:not(.is-center)[data-entity-id^='actor-']").length; var stats = document.querySelector("#graphVisStats").textContent; return { orgs: orgs, stats: stats }; })()`);
  check("legend uncheck hides org nodes + stats update", afterHide.orgs === 0 && afterHide.stats.indexOf("当前可见") >= 0, JSON.stringify(afterHide));

  // 4d. select-all restores
  await ev(`(function(){ var b = document.getElementById("legendNodeAll"); if (b) b.click(); return true; })()`);
  await sleep(1200);
  const afterAll = await ev(`(function(){ var orgs = document.querySelectorAll(".graph-node:not(.is-center)[data-entity-id^='actor-']").length; return { orgs: orgs }; })()`);
  check("legend select-all restores nodes", afterAll.orgs > 0, JSON.stringify(afterAll));

  // 4e. empty state
  await ev(`(function(){ ["lvNodeOrg","lvNodePerson","lvNodeCountry"].forEach(function(id){ var c = document.getElementById(id); if (c) { c.checked = false; c.dispatchEvent(new Event("change", {bubbles:true})); } }); return true; })()`);
  await sleep(1200);
  const empty = await ev(`(function(){ var e = document.querySelector(".graph-empty"); return { hasEmpty: !!e, text: e ? e.textContent : "" }; })()`);
  check("legend all-off shows empty state", empty.hasEmpty === true && empty.text.indexOf("重新勾选图例项") >= 0, JSON.stringify(empty));
  await ev(`(function(){ var b = document.getElementById("legendReset"); if (b) b.click(); return true; })()`);

  const summary = {
    base: BASE,
    checks_run: checks.length,
    checks_passed: checks.filter((c) => c.pass).length,
    checks_failed: checks.filter((c) => !c.pass).length,
    gate: checks.every((c) => c.pass) ? "PASS" : "FAIL",
  };
  fs.writeFileSync(OUT, JSON.stringify({ summary, checks }, null, 2), "utf-8");
  console.log("=== LOCAL POLISH VERIFY ===");
  checks.forEach((c) => console.log(`  [${c.pass ? "PASS" : "FAIL"}] ${c.name} — ${c.detail}`));
  console.log(JSON.stringify(summary));
  process.exit(summary.gate === "PASS" ? 0 : 1);
})().catch((e) => { console.error("FATAL", e); process.exit(2); });
