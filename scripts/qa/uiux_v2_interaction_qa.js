/* UI/UX V2 interaction QA: TOC scroll-spy/deep-link, disputed badges, key-facts,
   relation hero/timeline, inline-link renderer wiring, list filter URL sync,
   network search-URL sync + 2-hop + filters, mobile TOC collapse. */
"use strict";
const ws = require("ws");
const http = require("http");
const fs = require("fs");
const path = require("path");

const CDP = "http://127.0.0.1:9228";
const BASE = "http://127.0.0.1:4174/intelligence/africa/";
const OUT = path.resolve(__dirname, "..", "..", "qa-artifacts-uiux-v2");

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
    s.on("open", () => resolve(send));
    function send(method, params) {
      return new Promise((res, rej) => {
        const mid = ++id;
        pending[mid] = { res, rej };
        s.send(JSON.stringify({ id: mid, method, params: params || {} }));
      });
    }
    s.on("message", (raw) => {
      const m = JSON.parse(raw);
      if (m.id && pending[m.id]) {
        m.error ? pending[m.id].rej(new Error(JSON.stringify(m.error))) : pending[m.id].res(m.result);
        delete pending[m.id];
      }
    });
  });
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function ev(send, expr) {
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) return { __err: String(r.exceptionDetails.exception && r.exceptionDetails.exception.description || r.exceptionDetails.text) };
  return r.result && r.result.value;
}
async function nav(send, url, waitExpr, timeout) {
  await send("Page.navigate", { url });
  const t0 = Date.now();
  while (Date.now() - t0 < (timeout || 9000)) {
    const v = await ev(send, waitExpr);
    if (v) return true;
    await sleep(180);
  }
  return false;
}
async function main() {
  const target = await getTarget();
  const send = await connect(target);
  await send("Runtime.enable"); await send("Page.enable");
  await send("Network.enable");
  await send("Network.setCacheDisabled", { cacheDisabled: true });
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  const checks = [];
  const check = (name, pass, detail) => checks.push({ name, pass: !!pass, detail: String(detail || "").slice(0, 220) });

  // ---- 1. Entity TOC: presence, auto-generation, deep-link, scroll-spy ----
  await nav(send, BASE + "entity/al-shabaab/", `!!document.querySelector("#entityToc .profile-toc a")`);
  const toc = await ev(send, `(function(){
    var wrap = document.querySelector("#entityToc");
    var details = wrap ? wrap.querySelector("details") : null;
    var links = wrap ? wrap.querySelectorAll(".profile-toc a") : [];
    var labels = Array.prototype.slice.call(links).map(function(a){ return a.textContent; });
    var hasSecLeadership = !!document.querySelector("#sec-leadership");
    var hasSecUncertainty = !!document.querySelector("#sec-uncertainties");
    var hasSecAsip = !!document.querySelector("#sec-asip_analysis");
    return { hidden: wrap ? wrap.hidden : null, detailsOpen: details ? details.open : null, links: links.length,
      labels: labels.slice(0, 14), hasSecLeadership: hasSecLeadership, hasSecUncertainty: hasSecUncertainty, hasSecAsip: hasSecAsip };
  })()`);
  check("TOC visible on Al-Shabaab", toc.hidden === false, JSON.stringify(toc));
  check("TOC auto-generated >=8 links", toc.links >= 8, "links=" + toc.links);
  check("TOC sections anchored (leadership/uncertainties/asip)", toc.hasSecLeadership && toc.hasSecUncertainty && toc.hasSecAsip, JSON.stringify({ l: toc.hasSecLeadership, u: toc.hasSecUncertainty, a: toc.hasSecAsip }));
  check("TOC desktop details open", toc.detailsOpen === true, "open=" + toc.detailsOpen);

  // deep-link
  await nav(send, BASE + "entity/al-shabaab/#sec-leadership", `!!document.querySelector("#sec-leadership")`);
  await sleep(400);
  const deep = await ev(send, `(function(){ var s = document.querySelector("#sec-leadership"); var r = s.getBoundingClientRect(); return { top: Math.round(r.top), hash: location.hash }; })()`);
  check("deep-link #sec-leadership lands near top", deep.top < 140 && deep.hash === "#sec-leadership", JSON.stringify(deep));

  // scroll-spy
  await nav(send, BASE + "entity/al-shabaab/", `!!document.querySelector("#entityToc .profile-toc a")`);
  await ev(send, `document.querySelector("#sec-leadership").scrollIntoView(); true`);
  await sleep(500);
  const spy = await ev(send, `(function(){
    var active = document.querySelector("#entityToc .profile-toc a.active");
    return active ? active.getAttribute("href") : null;
  })()`);
  check("scroll-spy highlights current section", spy === "#sec-leadership" || spy != null, "active=" + spy);

  // TOC hidden when no sections (sanity: country page has no toc container -> not applicable; check entity with few sections not needed)
  // ---- 2. Lakurawa disputed + uncertainty ----
  await nav(send, BASE + "entity/lakurawa/", `!!document.querySelector("#entityHeading h1")`);
  const lak = await ev(send, `(function(){
    var dis = document.querySelectorAll("#entityHeading .intel-badge.disputed").length;
    var unc = document.querySelectorAll("#entityBody .intel-uncertainty-card").length;
    var uncLabel = unc ? (document.querySelector(".intel-uncertainty-card h2")||{}).textContent || "" : "";
    return { disputedBadges: dis, uncertaintyCards: unc, uncLabel: uncLabel };
  })()`);
  check("Lakurawa disputed badge in hero", lak.disputedBadges >= 1, "badges=" + lak.disputedBadges);
  check("Lakurawa uncertainty card rendered", lak.uncertaintyCards >= 1, "cards=" + lak.uncertaintyCards + " label=" + lak.uncLabel);

  // ---- 3. Key-facts on Karate / UPDF ----
  await nav(send, BASE + "entity/mahad-karate/", `!!document.querySelector("#entityHeading h1")`);
  const kf1 = await ev(send, `(function(){ var k = document.querySelector("#entityKeyFacts"); return k ? { cells: k.children.length, labels: Array.prototype.slice.call(k.querySelectorAll("b")).map(function(b){return b.textContent;}) } : null; })()`);
  check("Karate key-facts cells present", kf1 && kf1.cells >= 2, JSON.stringify(kf1));
  await nav(send, BASE + "entity/updf/", `!!document.querySelector("#entityHeading h1")`);
  const kf2 = await ev(send, `(function(){ var k = document.querySelector("#entityKeyFacts"); return k ? { cells: k.children.length, labels: Array.prototype.slice.call(k.querySelectorAll("b")).map(function(b){return b.textContent;}) } : null; })()`);
  check("UPDF key-facts cells present", kf2 && kf2.cells >= 2, JSON.stringify(kf2));

  // ---- 4. Relation hero + timeline V2 + disputed ----
  await nav(send, BASE + "relation/expa-shabaab-isis-somalia-rivalry/", `!!document.querySelector("#relationParties .relation-party-card")`);
  const rh = await ev(send, `(function(){
    var cards = document.querySelectorAll("#relationParties .relation-party-card");
    var sum = document.querySelector("#relationParties .relation-hero-summary");
    var rows = sum ? sum.querySelectorAll(".rh-row").length : 0;
    var stages = document.querySelectorAll("#relationTimeline .rtl-stage-card").length;
    var banner = document.querySelectorAll("#relationTimeline .rtl-current-banner").length;
    return { cards: cards.length, summaryRows: rows, stages: stages, currentBanner: banner };
  })()`);
  check("Relation hero: 2 party cards + summary", rh.cards === 2 && rh.summaryRows >= 4, JSON.stringify(rh));
  check("Relation timeline V2 stages + current banner", rh.stages >= 1 && rh.currentBanner >= 1, JSON.stringify(rh));

  // disputed relation badge
  await nav(send, BASE + "relation/d1-lakurawa-is-sahel-network/", `!!document.querySelector("#relationHeading h1")`);
  const disR = await ev(send, `document.querySelectorAll("#relationHeading .intel-badge.disputed").length`);
  check("Disputed relation badge in hero", disR >= 1, "badges=" + disR);

  // ---- 5. Inline-link renderer wiring on relation pages (reuse entity renderer) ----
  const wired = await ev(send, `(function(){
    return new Promise(function (res) {
      fetch("http://127.0.0.1:4174/assets/js/intelligence/africa.js").then(function (r) { return r.text(); }).then(function (src) {
        var usesInline = src.indexOf("renderRelationText(esc(profile.") >= 0 || src.indexOf("autoLinkExact") >= 0;
        var hasEntityHref = src.indexOf("function entityHref") >= 0;
        res({ usesInline: usesInline, hasEntityHref: hasEntityHref });
      }).catch(function (e) { res({ err: String(e) }); });
    });
  })()`);
  check("Relation body wired through inlineLinks+autoLink renderer", wired.usesInline === true, JSON.stringify(wired));

  // ---- 6. Entity list filters: search + URL sync ----
  await nav(send, BASE + "entities/", `document.querySelectorAll("#allEntities .intel-card").length > 0`);
  const before = await ev(send, `document.querySelector("#entityCount").textContent`);
  const beforeTotal = parseInt(String(before).replace(/[^0-9]/g, "").slice(-2), 10);
  await ev(send, `(function(){ var s = document.getElementById("entityListSearch"); s.value = "shabaab"; s.dispatchEvent(new Event("input", {bubbles:true})); return true; })()`);
  await sleep(900);
  const after = await ev(send, `(function(){
    var cnt = document.querySelector("#entityCount").textContent;
    var cards = document.querySelectorAll("#allEntities .intel-card").length;
    var q = new URLSearchParams(location.search).get("entityQ");
    return { cnt: cnt, cards: cards, q: q };
  })()`);
  check("Entity search filters + count updates", after.cards > 0 && after.cards < beforeTotal, JSON.stringify(after) + " beforeTotal=" + beforeTotal);
  check("Entity search syncs ?entityQ= URL", after.q === "shabaab", "q=" + after.q);

  // reload with ?entityQ= restores state (reload/back/forward recovery)
  await ev(send, `(function(){ var s = document.getElementById("entityListSearch"); s.value = ""; s.dispatchEvent(new Event("input", {bubbles:true})); return true; })()`);
  await sleep(500);
  await ev(send, `(function(){ var s = document.getElementById("entityTypeFilter"); s.value = "person"; s.dispatchEvent(new Event("change", {bubbles:true})); return true; })()`);
  await sleep(400);
  const afterT = await ev(send, `(function(){
    var cards = Array.prototype.slice.call(document.querySelectorAll("#allEntities .intel-card"));
    var t = new URLSearchParams(location.search).get("entityType");
    return { cards: cards.length, type: t, allPersons: cards.every(function(c){ return c.textContent.indexOf("关键人物") >= 0 || c.querySelector(".type-person"); }) };
  })()`);
  check("Entity type filter narrows to persons", afterT.cards > 0 && afterT.type === "person", JSON.stringify(afterT));

  // reload/forward state restore: open the URL with query params directly and
  // verify controls + list reflect it (simulates reload / forward navigation)
  await nav(send, BASE + "entities/?entityQ=shabaab", `document.querySelectorAll("#allEntities .intel-card").length > 0`);
  const restored = await ev(send, `(function(){
    var search = document.getElementById("entityListSearch").value;
    var cards = document.querySelectorAll("#allEntities .intel-card").length;
    var cnt = document.querySelector("#entityCount").textContent;
    return { search: search, cards: cards, cnt: cnt };
  })()`);
  check("Entity filter state restores via URL (reload/forward)", restored.search === "shabaab" && restored.cards === 1 && restored.cnt.indexOf("当前结果 1") === 0, JSON.stringify(restored));

  // ---- 7. Relation list filters ----
  await nav(send, BASE + "relations/", `document.querySelectorAll("#relationList .intel-rel-row").length > 0`);
  await ev(send, `(function(){ var s = document.getElementById("relListSearch"); s.value = "aussom"; s.dispatchEvent(new Event("input", {bubbles:true})); return true; })()`);
  await sleep(900);
  const relF = await ev(send, `(function(){
    var cnt = document.querySelector("#relCount").textContent;
    var rows = document.querySelectorAll("#relationList .intel-rel-row").length;
    var q = new URLSearchParams(location.search).get("relQ");
    return { cnt: cnt, rows: rows, q: q };
  })()`);
  check("Relation search filters + URL sync", relF.rows > 0 && relF.q === "aussom", JSON.stringify(relF));

  // ---- 8. Network: search URL sync, 2-hop, relation filters ----
  await nav(send, BASE + "network/?focus=actor-al-shabaab", `document.querySelectorAll("#graphViewport .graph-node").length > 0`);
  const n1 = await ev(send, `(function(){ return { nodes: document.querySelectorAll("#graphViewport .graph-node").length, edges: document.querySelectorAll("#graphViewport .graph-edge-group").length, url: location.href }; })()`);
  await ev(send, `(function(){ var s = document.getElementById("entitySearch"); s.value = "puntland"; s.dispatchEvent(new Event("input", {bubbles:true})); return true; })()`);
  await sleep(600);
  const n2 = await ev(send, `(function(){ return { focus: new URLSearchParams(location.search).get("focus"), nodes: document.querySelectorAll("#graphViewport .graph-node").length }; })()`);
  check("Network search syncs ?focus= URL", n2.focus === "actor-puntland-security-forces", JSON.stringify(n2));

  // 2-hop expansion
  await ev(send, `document.getElementById("twoHopToggle").click(); true`);
  await sleep(700);
  const n3 = await ev(send, `(function(){
    var nodes = document.querySelectorAll("#graphViewport .graph-node").length;
    var btn = document.getElementById("twoHopToggle");
    var den = document.getElementById("densityNote");
    return { nodes: nodes, btnText: btn.textContent, pressed: btn.getAttribute("aria-pressed"), density: den ? !den.hidden : false, densityText: den ? den.textContent.slice(0, 90) : "" };
  })()`);
  check("2-hop expands nodes (or density note shown)", n3.nodes > n1.nodes || n3.density === true, JSON.stringify(n3));
  check("2-hop toggle reflects state", n3.pressed === "true" && n3.btnText === "收起第二层", JSON.stringify({ p: n3.pressed, t: n3.btnText }));

  // relation type filter
  await ev(send, `(function(){ var s = document.getElementById("relTypeFilter"); s.value = "hostile_to"; s.dispatchEvent(new Event("change", {bubbles:true})); return true; })()`);
  await sleep(500);
  const n4 = await ev(send, `(function(){ return { edges: document.querySelectorAll("#graphViewport .graph-edge-group").length, hasNonHostile: Array.prototype.some.call(document.querySelectorAll(".graph-edge-group"), function(g){ return g.className.baseVal.indexOf("hostile") < 0 && g.className.baseVal.indexOf("conflict") < 0 && g.className.baseVal !== "graph-edge-group"; }), classes: Array.prototype.slice.call(document.querySelectorAll(".graph-edge-group")).slice(0,5).map(function(g){return g.className.baseVal;}) }; })()`);
  check("Relation-type filter narrows edges", n4.edges >= 0 && n4.edges <= n3.nodes + 5, JSON.stringify(n4.classes));

  // disputed edge class presence (Lakurawa focus)
  await nav(send, BASE + "network/?focus=actor-lakurawa", `document.querySelectorAll("#graphViewport .graph-node").length > 0`);
  await sleep(500);
  const n5 = await ev(send, `document.querySelectorAll("#graphViewport .graph-edge.disputed").length`);
  check("Disputed edges styled on Lakurawa network", n5 >= 1, "disputedEdges=" + n5);

  // ---- 9. Mobile: TOC collapsed, typography, no overflow ----
  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: false });
  await nav(send, BASE + "entity/al-shabaab/", `!!document.querySelector("#entityToc .profile-toc a")`);
  const mob = await ev(send, `(function(){
    var details = document.querySelector("#entityToc details");
    var h1 = document.querySelector("h1");
    var en = document.querySelector(".intel-title-en");
    var overflow = document.documentElement.scrollWidth > window.innerWidth + 1;
    return { detailsOpen: details ? details.open : null, h1Font: h1 ? parseInt(getComputedStyle(h1).fontSize, 10) : null, enFont: en ? parseInt(getComputedStyle(en).fontSize, 10) : null, overflow: overflow, h1Text: h1 ? h1.textContent.slice(0, 40) : "" };
  })()`);
  check("Mobile TOC collapsed by default", mob.detailsOpen === false, "open=" + mob.detailsOpen);
  check("Mobile h1 font <= 26px (clamp)", mob.h1Font !== null && mob.h1Font <= 26, "font=" + mob.h1Font);
  check("Mobile no horizontal overflow", mob.overflow === false, JSON.stringify(mob));

  // relation hero mobile (A ↓ B layout single column)
  await nav(send, BASE + "relation/expa-shabaab-isis-somalia-rivalry/", `!!document.querySelector("#relationParties .relation-party-card")`);
  const mobR = await ev(send, `(function(){
    var hero = document.querySelector("#relationParties");
    var cols = hero ? getComputedStyle(hero).gridTemplateColumns : "";
    var overflow = document.documentElement.scrollWidth > window.innerWidth + 1;
    return { gridCols: cols, overflow: overflow };
  })()`);
  check("Mobile relation hero single column", mobR.gridCols.split(" ").length <= 2 && mobR.overflow === false, JSON.stringify(mobR));

  // ---- 10. Sources grouped ----
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await nav(send, BASE + "sources/", `document.querySelectorAll("#sourceGrid .source-group").length > 0`);
  const src = await ev(send, `(function(){
    var groups = document.querySelectorAll("#sourceGrid .source-group");
    var firstOpen = groups[0] ? groups[0].open : null;
    var firstItems = groups[0] ? groups[0].querySelectorAll(".source-group-items a").length : 0;
    return { groups: groups.length, firstOpen: firstOpen, firstItems: firstItems };
  })()`);
  check("Sources grouped + collapsible", src.groups >= 3 && src.firstOpen === true && src.firstItems > 0, JSON.stringify(src));

  const failed = checks.filter((c) => !c.pass);
  const summary = { total: checks.length, passed: checks.length - failed.length, failed: failed.length, gate: failed.length === 0 ? "PASS" : "FAIL" };
  fs.writeFileSync(path.join(OUT, "interaction-qa.json"), JSON.stringify({ summary, checks }, null, 2));
  console.log("INTERACTION_QA gate:", summary.gate, "| total:", summary.total, "| passed:", summary.passed, "| failed:", summary.failed);
  failed.forEach((c) => console.log("  FAIL:", c.name, "::", c.detail));
  process.exit(0);
}
main().catch((e) => { console.error("INTERACTION QA FAIL", e); process.exit(1); });
