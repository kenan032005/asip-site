// UI HARD FIX A — online interaction QA (legend filters, node detail, TOC collapse, body links).
const path = require("path");
const http = require("http");
const fs = require("fs");
const ws = require("ws");
const CDP_PORT = 9232;
const BASE = "https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const withTimeout = (p, ms, label) => Promise.race([p, new Promise((_, j) => setTimeout(() => j(new Error("timeout " + label)), ms))]);

function getTarget() {
  return new Promise((res, rej) => {
    http.get(`http://127.0.0.1:${CDP_PORT}/json/list`, (r) => {
      let d = ""; r.on("data", (c) => (d += c));
      r.on("end", () => { const t = JSON.parse(d).find((x) => x.type === "page"); res(t ? t.webSocketDebuggerUrl : null); });
    }).on("error", rej);
  });
}
function connect(url) {
  return new Promise((res, rej) => {
    const s = new ws(url);
    let id = 0; const pending = {};
    const send = (method, params) => new Promise((r, j) => { const mid = ++id; pending[mid] = { r, j }; s.send(JSON.stringify({ id: mid, method, params: params || {} })); });
    s.on("message", (raw) => { const m = JSON.parse(raw); if (m.id && pending[m.id]) { if (m.error) pending[m.id].j(new Error(JSON.stringify(m.error))); else pending[m.id].r(m.result); delete pending[m.id]; } });
    s.on("open", () => res(send));
    s.on("error", rej);
  });
}

(async () => {
  const send = await connect(await getTarget());
  await send("Runtime.enable"); await send("Page.enable"); await send("Network.enable");
  await send("Network.setCacheDisabled", { cacheDisabled: true });
  try { await send("Network.clearBrowserCache"); } catch (e) {}
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  const ev = (expr, tmo) => withTimeout(send("Runtime.evaluate", { expression: expr, returnByValue: true }), tmo || 12000, "ev").then((r) => (r && r.result) ? r.result.value : undefined);
  const nav = (url) => withTimeout(send("Page.navigate", { url }), 15000, "nav");
  const wait = async (sel, tries) => { for (let i = 0; i < (tries || 24); i++) { if (await ev(`!!document.querySelector(${JSON.stringify(sel)})`) === true) return true; await sleep(500); } return false; };

  const checks = [];
  const check = (name, pass, detail) => { checks.push({ name, pass: !!pass, detail: detail || "" }); console.log((pass ? "PASS " : "FAIL ") + name + (detail ? " | " + detail : "")); };

  // 1. network legend: hide organization nodes -> nodes+edges update, stats update
  await nav(BASE + "/intelligence/africa/network/?focus=actor-jnim");
  await wait(".graph-node");
  await sleep(1200);
  const before = await ev(`(function(){ var nodes = document.querySelectorAll(".graph-node").length; var stats = (document.querySelector("#graphVisStats")||{}).textContent||""; var edges = document.querySelectorAll(".graph-edge").length; return { nodes: nodes, edges: edges, stats: stats }; })()`);
  await ev(`(function(){ var c = document.getElementById("lvNodeOrg"); c.checked = false; c.dispatchEvent(new Event("change", {bubbles:true})); return true; })()`);
  await sleep(1200);
  const afterHide = await ev(`(function(){ var nodes = document.querySelectorAll(".graph-node").length; var edges = document.querySelectorAll(".graph-edge").length; var stats = (document.querySelector("#graphVisStats")||{}).textContent||""; return { nodes: nodes, edges: edges, stats: stats }; })()`);
  check("legend uncheck org hides nodes", afterHide.nodes < before.nodes, `before=${before.nodes} after=${afterHide.nodes}`);
  check("legend hides edges too (no dangling)", afterHide.edges < before.edges, `edges ${before.edges}->${afterHide.edges}`);
  check("visible stats update", afterHide.stats.indexOf(before.nodes + "") < 0, afterHide.stats);

  // 2. select-all restores
  await ev(`(function(){ document.getElementById("legendNodeAll").click(); return true; })()`);
  await sleep(1000);
  const restored = await ev(`(function(){ return { nodes: document.querySelectorAll(".graph-node").length, orgChecked: document.getElementById("lvNodeOrg").checked }; })()`);
  check("legend select-all restores nodes", restored.nodes === before.nodes && restored.orgChecked === true, `nodes=${restored.nodes}`);

  // 3. click node -> detail panel + focus change
  await ev(`(function(){ var n = document.querySelector(".graph-node:not(.is-center)"); if (n) n.dispatchEvent(new MouseEvent("click", {bubbles:true})); return true; })()`);
  await sleep(1200);
  const detail = await ev(`(function(){ var ni = document.querySelector("#nodeInfo"); return ni ? ni.textContent.slice(0, 60) : ""; })()`);
  check("node click fills detail panel", detail.length > 10, detail);

  // 4. empty state: hide org+country+person (only center remains -> empty)
  await nav(BASE + "/intelligence/africa/network/?focus=actor-jnim");
  await wait(".graph-node"); await sleep(1000);
  await ev(`(function(){ ["lvNodeOrg","lvNodePerson","lvNodeCountry"].forEach(function(id){ var c=document.getElementById(id); c.checked=false; c.dispatchEvent(new Event("change",{bubbles:true})); }); return true; })()`);
  await sleep(1000);
  const empty = await ev(`(function(){ var e = document.querySelector(".graph-empty"); return e ? e.textContent.slice(0, 30) : ""; })()`);
  check("legend empty state shows message", empty.length > 0, empty);

  // 5. TOC auto-collapse on scroll
  await nav(BASE + "/intelligence/africa/entity/al-shabaab/");
  await wait("#entityToc .profile-toc-details"); await sleep(800);
  await ev(`(function(){ var d = document.querySelector("#entityToc .profile-toc-details"); d.open = true; d.dispatchEvent(new Event("toggle")); return d.open; })()`);
  await ev(`window.scrollTo(0, 500)`); await sleep(900);
  const tocAfterScroll = await ev(`(function(){ var d = document.querySelector("#entityToc .profile-toc-details"); return d ? d.open === false : null; })()`);
  check("TOC auto-collapses after scroll", tocAfterScroll === true, "open=" + tocAfterScroll);
  await ev(`window.scrollTo(0, 0)`); await sleep(900);
  const tocReopen = await ev(`(function(){ var d = document.querySelector("#entityToc .profile-toc-details"); return d ? d.open === true : null; })()`);
  check("TOC reopens near top", tocReopen === true, "open=" + tocReopen);

  // 6. relation hero machine-free (JNIM-Niger body links visible)
  await nav(BASE + "/intelligence/africa/relation/jnim-niger-operates/");
  await wait("#relationHeading h1"); await sleep(800);
  const rel2 = await ev(`(function(){ var h1 = document.querySelector("#relationHeading h1").textContent; var bodyLinks = Array.prototype.filter.call(document.querySelectorAll("#relationBody a"), function(a){ var t=a.textContent; return t.indexOf("尼日尔")>=0||t.indexOf("马里")>=0||t.indexOf("贝宁")>=0; }).length; var status = (document.querySelector("#relationParties .rh-row dd")||{}).textContent||""; return { h1: h1, bodyLinks: bodyLinks, status: status }; })()`);
  check("relation h1 no machine id", !/rel-|_/.test(rel2.h1), rel2.h1);
  check("relation body country links visible", rel2.bodyLinks > 0, "links=" + rel2.bodyLinks);
  check("relation parties status localized", /_/.test(rel2.status) === false, rel2.status);

  // 7. entity sources at very end + status localized
  await nav(BASE + "/intelligence/africa/entity/aqim/");
  await wait("#entityHeading h1"); await sleep(800);
  const ent = await ev(`(function(){ var main = document.querySelector(".intel-profile-main"); var panels = Array.prototype.map.call(main.querySelectorAll(":scope > .intel-panel"), function(x){ return x.id || (x.querySelector("h2")||{}).textContent || ""; }); var last = panels[panels.length-1]; var status = (document.querySelector("#entityHeading .intel-badge.status")||{}).textContent||""; return { panels: panels, last: last, status: status }; })()`);
  check("entity sources panel is last", ent.last === "entitySources", JSON.stringify(ent.panels));
  check("entity status localized", ent.status.length > 0 && !/_/.test(ent.status), ent.status);

  const fails = checks.filter((c) => !c.pass);
  const summary = { total: checks.length, passed: checks.length - fails.length, failed: fails.length, checks, base: BASE, run_at: new Date().toISOString() };
  fs.mkdirSync(path.join(__dirname, "..", "..", "qa-artifacts-ui-hard-fix-a"), { recursive: true });
  fs.writeFileSync(path.join(__dirname, "..", "..", "qa-artifacts-ui-hard-fix-a", "online-interaction-qa.json"), JSON.stringify(summary, null, 2));
  console.log("=== ONLINE HARD FIX INTERACTION QA:", (checks.length - fails.length) + "/" + checks.length, "===");
  process.exit(fails.length ? 1 : 0);
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
