// UI HARD FIX A — local smoke verification against dist (127.0.0.1:4174)
const path = require("path");
const http = require("http");
const fs = require("fs");
const ws = require("ws");
const CDP_PORT = 9232;
const BASE = "http://127.0.0.1:4174";
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-ui-hard-fix-a", "hardfix-local-probe.json");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function getTarget() {
  return new Promise((res, rej) => {
    http.get(`http://127.0.0.1:${CDP_PORT}/json/list`, (r) => {
      let d = ""; r.on("data", (c) => (d += c));
      r.on("end", () => {
        const list = JSON.parse(d);
        const t = list.find((x) => x.type === "page");
        res(t ? t.webSocketDebuggerUrl : null);
      });
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
const withTimeout = (p, ms, label) => Promise.race([p, new Promise((_, j) => setTimeout(() => j(new Error("timeout " + label)), ms))]);

(async () => {
  const send = await connect(await getTarget());
  await send("Runtime.enable"); await send("Page.enable"); await send("Network.enable");
  const ev = (expr, tmo) => withTimeout(send("Runtime.evaluate", { expression: expr, returnByValue: true }), tmo || 12000, "ev").then((r) => (r && r.exceptionDetails) ? { __error: (r.exceptionDetails.exception || {}).description || r.exceptionDetails.text } : (r && r.result) ? r.result.value : undefined);
  const waitNode = async (sel, tries) => {
    for (let i = 0; i < (tries || 20); i++) {
      const v = await ev(`!!document.querySelector(${JSON.stringify(sel)})`);
      if (v === true) return true;
      await sleep(500);
    }
    return false;
  };
  const nav = (url) => withTimeout(send("Page.navigate", { url }), 15000, "nav");

  const checks = [];
  const check = (name, pass, detail) => { checks.push({ name, pass: !!pass, detail: detail || "" }); console.log((pass ? "PASS " : "FAIL ") + name + (detail ? " | " + detail : "")); };

  // ---- relation hero: JNIM <-> Niger
  await nav(BASE + "/intelligence/africa/relation/jnim-niger-operates/");
  await sleep(4500);
  const rel = await ev(`(function(){
    var h1 = (document.querySelector("#relationHeading h1")||{}).textContent || "";
    var te = (document.querySelector("#relationHeading .intel-title-en")||{}).textContent || "";
    var tech = (document.querySelector(".rel-tech-details")||{});
    var partyRows = Array.prototype.map.call(document.querySelectorAll("#relationParties .rh-row"), function(x){ return x.textContent; });
    var ov = (document.querySelector("#relationOverview")||{textContent:""}).textContent || "";
    var nigerLinks = Array.prototype.filter.call(document.querySelectorAll("#relationBody a"), function(a){ return a.textContent.indexOf("尼日尔")>=0 || a.textContent.indexOf("马里")>=0 || a.textContent.indexOf("贝宁")>=0; }).length;
    return { h1: h1, te: te, techOpen: tech.open === true, techBody: (tech.textContent||"").indexOf("rel-jnim")>=0, partyRows: partyRows, ov: ov.slice(0,60), countryLinks: nigerLinks, h1HasMachine: /rel-|freshness|reported_activity|operates_in/.test(h1) };
  })()`);
  check("relation h1 no machine id", rel.h1HasMachine === false, JSON.stringify(rel.h1));
  check("relation status localized", /据报存在活动|reported_activity_presence/.test(rel.te) && rel.te.indexOf("reported_activity_presence") < 0, rel.te);
  check("relation tech details collapsed", rel.techOpen === false && rel.techBody === true, "open=" + rel.techOpen + " bodyHasRelId=" + rel.techBody);
  check("relation body country links visible", rel.countryLinks > 0, "links=" + rel.countryLinks);
  const partyStatusOk = rel.partyRows.some(function (x) { return x.indexOf("状态") >= 0 && x.indexOf("据报") >= 0; });
  check("relation parties status localized", partyStatusOk, JSON.stringify(rel.partyRows));

  // ---- entity: Al-Shabaab TOC + sources last
  await nav(BASE + "/intelligence/africa/entity/al-shabaab/");
  await sleep(5500);
  const ent = await ev(`(function(){
    var toc = document.querySelector("#entityToc .profile-toc-details");
    var tocOpen = toc ? toc.open === true : null;
    var tocBtn = (document.querySelector("#entityToc .toc-btn")||{}).textContent || "";
    var body = document.querySelector("#entityBody");
    var secs = body ? Array.prototype.map.call(body.querySelectorAll(".profile-section"), function(x){ return x.id; }) : [];
    var lastInBody = secs[secs.length-1] || "";
    var srcPanel = document.querySelector("#entitySources");
    var srcInBody = secs.indexOf("sec-sources") >= 0;
    var srcPanelLast = srcPanel ? srcPanel.querySelectorAll(".profile-section").length : 0;
    var srcId = (srcPanel ? (srcPanel.querySelector(".profile-section")||{}).id : "");
    // all sections in main column order
    var main = document.querySelector(".intel-profile-main");
    var panels = main ? Array.prototype.map.call(main.querySelectorAll(".intel-panel"), function(x){ return x.id || x.textContent.slice(0,6); }) : [];
    var relPanels = Array.prototype.map.call(document.querySelectorAll(".intel-profile-main > .intel-panel"), function(x){ return x.id || (x.querySelector("h2")||{}).textContent || ""; });
    return { tocOpen: tocOpen, tocBtn: tocBtn, lastInBody: lastInBody, srcInBody: srcInBody, srcPanelLast: srcPanelLast, srcId: srcId, panels: relPanels, status: (document.querySelector("#entityHeading .intel-badge.status")||{}).textContent || "" };
  })()`);
  check("entity sources NOT inside body", ent.srcInBody === false, "lastInBody=" + ent.lastInBody);
  check("entity sources panel at page end", ent.srcPanelLast > 0 && ent.panels[ent.panels.length-1] === "entitySources", JSON.stringify(ent.panels));
  check("entity TOC toggle button present", ent.tocBtn.length > 0, "btn=" + ent.tocBtn);
  check("entity status localized", ent.status.indexOf("_") < 0 && ent.status.length > 0, ent.status);

  // ---- network: JNIM default clean view
  await nav(BASE + "/intelligence/africa/network/?focus=actor-jnim");
  await waitNode(".graph-node");
  const net = await ev(`(function(){
    var nodes = document.querySelectorAll(".graph-node");
    var labels = Array.prototype.filter.call(document.querySelectorAll(".graph-node .node-label"), function(x){ return x.textContent.trim().length > 0; });
    var center = document.querySelector(".graph-node.is-center .node-label");
    var stats = (document.querySelector("#graphVisStats")||{}).textContent || "";
    return { total: nodes.length, labeled: labels.length, center: center ? center.textContent : "", stats: stats,
      l1labels: Array.prototype.filter.call(labels, function(x){ return !x.closest(".is-center") && (x.getAttribute("class")||"").indexOf("hidden-label") < 0; }).length };
  })()`);
  check("network default clean (few labels)", net.labeled >= 1 && net.labeled <= Math.max(8, Math.ceil(net.total / 3)), "nodes=" + net.total + " labeled=" + net.labeled);
  check("network center has full label", net.center.length > 0, net.center);

  // ---- network: Al-Shabaab focus
  await nav(BASE + "/intelligence/africa/network/?focus=actor-al-shabaab");
  await waitNode(".graph-node");
  const net2 = await ev(`(function(){
    var nodes = document.querySelectorAll(".graph-node");
    var labels = Array.prototype.filter.call(document.querySelectorAll(".graph-node .node-label"), function(x){ return x.textContent.trim().length > 0; });
    var center = (document.querySelector(".graph-node.is-center .node-label")||{}).textContent || "";
    var svg = document.getElementById("graphSvg");
    var viewBox = svg ? svg.getAttribute("viewBox") : "";
    return { total: nodes.length, labeled: labels.length, center: center };
  })()`);
  check("network al-shabaab clean", net2.labeled <= Math.max(8, Math.ceil(net2.total / 3)) && net2.center.length > 0, "nodes=" + net2.total + " labeled=" + net2.labeled + " center=" + net2.center.slice(0,20));

  const fails = checks.filter(function (c) { return !c.pass; });
  const summary = { total: checks.length, passed: checks.length - fails.length, failed: fails.length, checks: checks, run_at: new Date().toISOString(), base: BASE };
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(summary, null, 2));
  console.log("=== LOCAL HARD FIX PROBE:", (checks.length - fails.length) + "/" + checks.length, "===");
  process.exit(fails.length ? 1 : 0);
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
