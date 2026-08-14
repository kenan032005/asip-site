#!/usr/bin/env node
/* Online preview interaction QA: filters, TOC anchor, 2-hop, relation body auto-links. */
const fs = require("fs");
const path = require("path");
const http = require("http");
const ws = require("ws");

const BASE = "https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2";
const CDP_PORT = 9229;
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-online-preview", "online-interaction-qa.json");

function getTarget() {
  return new Promise((res, rej) => {
    http.get(`http://127.0.0.1:${CDP_PORT}/json/list`, (r) => {
      let d = "";
      r.on("data", (c) => (d += c));
      r.on("end", () => {
        const list = JSON.parse(d);
        const t = list.find((x) => x.type === "page" && !/^(edge|chrome-extension|devtools):/.test(x.url) && x.url !== "about:blank");
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
    const send = (m, p) => new Promise((r, j) => { const mid = ++id; pending[mid] = { r, j }; s.send(JSON.stringify({ id: mid, method: m, params: p || {} })); });
    s.on("message", (raw) => { const m = JSON.parse(raw); if (m.id && pending[m.id]) { m.error ? pending[m.id].j(new Error(JSON.stringify(m.error))) : pending[m.id].r(m.result); delete pending[m.id]; } });
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
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

  const checks = [];
  const check = (name, pass, detail) => checks.push({ name, pass: !!pass, detail: String(detail || "").slice(0, 200) });
  const ev = (expr) => withTimeout(send("Runtime.evaluate", { expression: expr, returnByValue: true }), 12000, "ev").then((r) => r.result.value);
  const nav = async (pathUrl, wait = 4000) => {
    await withTimeout(send("Page.navigate", { url: BASE + pathUrl }), 15000, "nav");
    await sleep(wait);
  };

  // 1. entity TOC anchors
  await nav("/intelligence/africa/entity/al-shabaab/");
  const toc = await ev(`(function(){ var toc = document.querySelectorAll("#entityToc a"); var ok = 0, total = toc.length;
    toc.forEach(function(a){ var id = a.getAttribute("href").split("#")[1]; if (id && document.getElementById(id)) ok++; });
    return { total: total, ok: ok, first: toc[0] ? toc[0].getAttribute("href") : null }; })()`);
  check("entity TOC links resolve to real sections", toc.ok === toc.total && toc.total > 15, JSON.stringify(toc));

  // deep-link anchor (take a real TOC-generated anchor, then verify it resolves)
  await nav("/intelligence/africa/entity/al-shabaab/");
  const realAnchor = await ev(`(function(){ var a = document.querySelector("#entityToc a"); return a ? a.getAttribute("href") : null; })()`);
  const anchorId = realAnchor ? realAnchor.replace("#", "") : null;
  const hasAnchor = await ev(`(function(){ var id = ${JSON.stringify(anchorId)}; return id ? !!document.getElementById(id) : false; })()`);
  check("entity TOC anchors exist as DOM ids", hasAnchor === true, "anchor=" + realAnchor);
  if (realAnchor) {
    await nav("/intelligence/africa/entity/al-shabaab/" + realAnchor);
    const deeplink = await ev(`(function(){ var h = location.hash; var el = h ? document.querySelector(h) : null; return { hash: h, found: !!el }; })()`);
    check("entity deep-link #sec- anchors work", deeplink.found, JSON.stringify(deeplink));
  } else {
    check("entity deep-link #sec- anchors work", false, "no TOC anchor found");
  }

  // 2. relation body auto-links
  await nav("/intelligence/africa/relation/expc-eij-alqaida-integration/");
  const autolink = await ev(`(function(){ var a = document.querySelectorAll(".relation-body a[href*='/entity/'], .intel-prose a[href*='/entity/'], .profile-section a[href*='/entity/']"); return { count: a.length }; })()`);
  check("relation body exact auto-links present", autolink.count > 0, JSON.stringify(autolink));

  // 3. entity list search + filter
  await nav("/intelligence/africa/entities/");
  const before = await ev(`document.querySelector("#entityCount") ? document.querySelector("#entityCount").textContent : "none"`);
  await ev(`(function(){ var s = document.getElementById("entityListSearch"); if (!s) return false; s.value = "shabaab"; s.dispatchEvent(new Event("input", {bubbles:true})); return true; })()`);
  await sleep(800);
  const after = await ev(`(function(){ var cnt = document.querySelector("#entityCount"); var cards = document.querySelectorAll("#allEntities .intel-card").length; var q = new URLSearchParams(location.search).get("entityQ"); return { cnt: cnt ? cnt.textContent : null, cards: cards, q: q }; })()`);
  check("entity search filters list + count updates", after.cards > 0 && after.cards < 30 && after.q === "shabaab", JSON.stringify({ before, after }));
  // clear search first so the type filter is tested on the full list
  await ev(`(function(){ var s = document.getElementById("entityListSearch"); if (!s) return false; s.value = ""; s.dispatchEvent(new Event("input", {bubbles:true})); return true; })()`);
  await sleep(800);
  await ev(`(function(){ var s = document.getElementById("entityTypeFilter"); if (!s) return false; s.value = "person"; s.dispatchEvent(new Event("change", {bubbles:true})); return true; })()`);
  await sleep(800);
  const typ = await ev(`(function(){ var cards = document.querySelectorAll("#allEntities .intel-card"); return { cards: cards.length, type: new URLSearchParams(location.search).get("entityType") }; })()`);
  check("entity type filter applies", typ.type === "person" && typ.cards > 0, JSON.stringify(typ));

  // 4. relation list filter
  await nav("/intelligence/africa/relations/");
  const relBefore = await ev(`(function(){ var c = document.querySelector("#relCount"); return c ? c.textContent : "none"; })()`);
  await ev(`(function(){ var s = document.getElementById("relListSearch"); if (!s) return false; s.value = "al-shabaab"; s.dispatchEvent(new Event("input", {bubbles:true})); return true; })()`);
  await sleep(800);
  const relAfter = await ev(`(function(){ var cards = document.querySelectorAll("#relationList .intel-rel-row").length; var q = new URLSearchParams(location.search).get("relQ"); return { cards: cards, q: q }; })()`);
  check("relation search filters list", relAfter.cards > 0 && relAfter.q === "al-shabaab", JSON.stringify({ relBefore, relAfter }));

  // 5. network focus + 2-hop
  await nav("/intelligence/africa/network/?focus=actor-aqim");
  const n1 = await ev(`document.querySelectorAll(".graph-node").length`);
  check("network 1-hop focus renders nodes", n1 > 0, "nodes=" + n1);
  const has2hop = await ev(`!!document.querySelector("#twoHopToggle")`);
  check("network 2-hop toggle present", has2hop === true, "btn=" + has2hop);
  await ev(`(function(){ var b = document.getElementById("twoHopToggle"); if (b) { b.checked = true; b.dispatchEvent(new Event("change", {bubbles:true})); } return true; })()`);
  await sleep(1500);
  const n2 = await ev(`document.querySelectorAll(".graph-node").length`);
  check("network 2-hop expands node set", n2 >= n1, "before=" + n1 + " after=" + n2);

  // 6. mobile relation hero + TOC collapse
  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await nav("/intelligence/africa/relation/expa-shabaab-isis-somalia-rivalry/");
  const mrel = await ev(`(function(){ var hero = getComputedStyle(document.querySelector(".relation-hero")); var party = document.querySelectorAll(".relation-party-card").length; return { grid: hero.gridTemplateColumns, party: party, overflow: document.documentElement.scrollWidth > window.innerWidth + 2 }; })()`);
  check("mobile relation hero stacks (single column)", !mrel.grid.includes(" ") && mrel.party === 2 && !mrel.overflow, JSON.stringify(mrel));
  await nav("/intelligence/africa/entity/lakurawa/");
  const mtoc = await ev(`(function(){ var d = document.querySelector(".profile-toc-details"); return { hasDetails: !!d, display: d ? getComputedStyle(d).display : null, open: d ? d.open : null }; })()`);
  check("mobile entity TOC uses collapsible details", mtoc.hasDetails === true, JSON.stringify(mtoc));

  const summary = {
    base: BASE,
    checks_run: checks.length,
    checks_passed: checks.filter((c) => c.pass).length,
    checks_failed: checks.filter((c) => !c.pass).length,
    gate: checks.every((c) => c.pass) ? "PASS" : "FAIL",
  };
  fs.writeFileSync(OUT, JSON.stringify({ summary, checks }, null, 2), "utf-8");
  console.log("=== ONLINE INTERACTION QA ===");
  checks.forEach((c) => console.log(`  [${c.pass ? "PASS" : "FAIL"}] ${c.name} — ${c.detail}`));
  console.log(JSON.stringify(summary));
  process.exit(summary.gate === "PASS" ? 0 : 1);
})().catch((e) => { console.error("FATAL", e); process.exit(2); });
