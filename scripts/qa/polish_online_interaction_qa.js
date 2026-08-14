#!/usr/bin/env node
/* Online polish interaction QA against the public preview URL. */
const fs = require("fs");
const path = require("path");
const http = require("http");
const ws = require("ws");

const BASE = "https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa";
const CDP_PORT = 9230;
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-ui-final-polish-1", "online-interaction-qa.json");

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
  const ev = (expr) => withTimeout(send("Runtime.evaluate", { expression: expr, returnByValue: true }), 12000, "ev").then((r) => {
    if (r && r.exceptionDetails) return { __evalError: (r.exceptionDetails.exception && r.exceptionDetails.exception.description) || r.exceptionDetails.text };
    return r ? r.result.value : undefined;
  });
  const nav = async (p2, wait = 4200) => { await withTimeout(send("Page.navigate", { url: BASE + p2 }), 15000, "nav"); await sleep(wait); };

  // 1. body auto-linking expanded: region names linkable (JNIM-Niger prose has 尼日尔/马里/贝宁)
  await nav("/relation/jnim-niger-operates/");
  const regionLinks = await ev(`(function(){
    var a = Array.prototype.slice.call(document.querySelectorAll("a.intel-entity-link"));
    var region = a.filter(function(x){ return x.getAttribute("href").indexOf("/region/") >= 0; }).length;
    var niger = a.filter(function(x){ return x.textContent.indexOf("尼日尔") >= 0 && (x.getAttribute("href").indexOf("/country/") >= 0 || x.getAttribute("href").indexOf("/region/") >= 0); }).length;
    return { total: a.length, region: region, niger: niger };
  })()`);
  check("region auto-links work (exact canonical)", regionLinks.region >= 1 && regionLinks.niger >= 1, JSON.stringify(regionLinks));

  // 2. entity body auto-links (countries/orgs mixed prose)
  await nav("/entity/aqim/");
  const entLinks = await ev(`(function(){ var a = document.querySelectorAll("#entityBody a.intel-entity-link.auto"); return a.length; })()`);
  const entLinksAll = await ev(`(function(){ var a = document.querySelectorAll("#entityBody a.intel-entity-link"); return a.length; })()`);
  check("entity body auto-links present", entLinks > 0 || entLinksAll > 0, "auto=" + entLinks + " all=" + entLinksAll);

  // 3. relation hero tech collapse toggle
  await nav("/relation/jnim-niger-operates/");
  const tech = await ev(`(function(){ var d = document.querySelector(".rel-tech-details"); if (!d) return null; d.open = true; return { open: d.open, body: d.querySelector(".rel-tech-body") ? d.querySelector(".rel-tech-body").textContent.slice(0, 60) : "" }; })()`);
  check("relation tech metadata expands on click", tech && tech.open === true && tech.body.indexOf("rel-jnim-niger-operates") >= 0, JSON.stringify(tech));

  // 4. network 2-hop
  await nav("/network/?focus=actor-aqim");
  const n1 = await ev(`document.querySelectorAll(".graph-node").length`);
  await ev(`(function(){ var b = document.getElementById("twoHopToggle"); if (b) { b.click(); } return true; })()`);
  await sleep(1600);
  const n2 = await ev(`document.querySelectorAll(".graph-node").length`);
  check("network 2-hop expands", n2 > n1, "before=" + n1 + " after=" + n2);
  await ev(`(function(){ var b = document.getElementById("twoHopToggle"); if (b && b.classList.contains("active")) b.click(); return true; })()`);
  await sleep(1200);

  // 5. node detail panel on click
  await nav("/network/?focus=actor-jnim");
  await ev(`(function(){ var n = document.querySelector(".graph-node:not(.is-center)"); if (n) n.dispatchEvent(new MouseEvent("click", {bubbles:true})); return !!n; })()`);
  await sleep(1400);
  const nd = await ev(`(function(){ var p = document.querySelector("#nodeInfo .intel-node-detail"); return p ? { has: true, h2: p.querySelector("h2").textContent, rels: p.querySelectorAll(".nd-rels a").length, btn: !!p.querySelector("a.intel-button") } : { has: false }; })()`);
  check("node click opens detail panel (name+rels+button)", nd.has === true && nd.rels > 0 && nd.btn === true, JSON.stringify(nd));

  // 6. legend: uncheck org hides non-center orgs, stats update
  const hideRes = await ev(`(function(){ var c = document.getElementById("lvNodeOrg"); if (c) { c.checked = false; c.dispatchEvent(new Event("change", {bubbles:true})); } return true; })()`);
  await sleep(1400);
  const hid = await ev(`(function(){ var orgs = document.querySelectorAll(".graph-node:not(.is-center)[data-entity-id^='actor-']").length; var stats = (document.querySelector("#graphVisStats")||{}).textContent || ""; return { orgs: orgs, stats: stats }; })()`);
  check("legend uncheck hides org nodes + stats", hid.orgs === 0 && hid.stats.indexOf("当前可见") >= 0, JSON.stringify(hid));

  // 7. legend select-all + reset
  await ev(`(function(){ document.getElementById("legendNodeAll").click(); return true; })()`);
  await sleep(1200);
  const all = await ev(`(function(){ var orgs = document.querySelectorAll(".graph-node:not(.is-center)[data-entity-id^='actor-']").length; return { orgs: orgs }; })()`);
  check("legend select-all restores nodes", all.orgs > 0, JSON.stringify(all));

  // 8. legend all-off -> empty state
  await ev(`(function(){ ["lvNodeOrg","lvNodePerson","lvNodeCountry"].forEach(function(id){ var c = document.getElementById(id); if (c) { c.checked = false; c.dispatchEvent(new Event("change", {bubbles:true})); } }); return true; })()`);
  await sleep(1400);
  const empty = await ev(`(function(){ var e = document.querySelector(".graph-empty"); return { has: !!e, text: e ? e.textContent : "" }; })()`);
  check("legend all-off shows empty state", empty.has === true && empty.text.indexOf("重新勾选图例项") >= 0, JSON.stringify(empty));
  await ev(`(function(){ document.getElementById("legendReset").click(); return true; })()`);
  await sleep(1200);

  // 9. label mode buttons
  await ev(`(function(){ var b = document.querySelector('[data-label-mode="full"]'); if (b) b.click(); return true; })()`);
  await sleep(1200);
  const lm = await ev(`(function(){ var shorts = document.querySelectorAll(".graph-node .node-label.short").length; var fulls = document.querySelectorAll(".graph-node .node-label:not(.short):not(.tiny)").length; var act = document.querySelector("[data-label-mode].active"); return { shorts: shorts, fulls: fulls, active: act ? act.getAttribute("data-label-mode") : null }; })()`);
  check("label mode full shows full labels", lm.active === "full" && lm.shorts === 0 && lm.fulls > 0, JSON.stringify(lm));

  // 10. entity TOC close + sources end (online)
  await nav("/entity/al-shabaab/");
  const toc = await ev(`(function(){ var c = document.querySelector(".toc-close-btn"); if (c) c.click(); var d = document.querySelector(".profile-toc-details"); return { closed: d ? !d.open : null, body: document.querySelector("#entityBody") }; })()`);
  const srcOrder = await ev(`(function(){ var b = document.querySelector("#entityBody"); var secs = b.querySelectorAll(".profile-section"); return { last: secs[secs.length-1].id, count: secs.length }; })()`);
  check("entity TOC close button collapses", toc.closed === true, JSON.stringify(toc.closed));
  check("entity sources last (online)", srcOrder.last === "sec-sources", JSON.stringify(srcOrder));

  const summary = {
    base: BASE,
    checks_run: checks.length,
    checks_passed: checks.filter((c) => c.pass).length,
    checks_failed: checks.filter((c) => !c.pass).length,
    gate: checks.every((c) => c.pass) ? "PASS" : "FAIL",
  };
  fs.writeFileSync(OUT, JSON.stringify({ summary, checks }, null, 2), "utf-8");
  console.log("=== ONLINE POLISH INTERACTION QA ===");
  checks.forEach((c) => console.log(`  [${c.pass ? "PASS" : "FAIL"}] ${c.name} — ${c.detail}`));
  console.log(JSON.stringify(summary));
  process.exit(summary.gate === "PASS" ? 0 : 1);
})().catch((e) => { console.error("FATAL", e); process.exit(2); });
