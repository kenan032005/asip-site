// UI HARD FIX A — online browser QA against the real public Preview URL.
const path = require("path");
const http = require("http");
const fs = require("fs");
const ws = require("ws");
const CDP_PORT = 9232;
const BASE = "https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2";
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-ui-hard-fix-a", "online-browser-qa.json");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const withTimeout = (p, ms, label) => Promise.race([p, new Promise((_, j) => setTimeout(() => j(new Error("timeout " + label)), ms))]);

const PAGES = [
  { key: "home", url: "/intelligence/africa/", type: "home" },
  { key: "network_al_shabaab", url: "/intelligence/africa/network/?focus=actor-al-shabaab", type: "network" },
  { key: "network_aqim", url: "/intelligence/africa/network/?focus=actor-aqim", type: "network" },
  { key: "network_jnim", url: "/intelligence/africa/network/?focus=actor-jnim", type: "network" },
  { key: "network_isis_somalia", url: "/intelligence/africa/network/?focus=actor-isis-somalia", type: "network" },
  { key: "network_lakurawa", url: "/intelligence/africa/network/?focus=actor-lakurawa", type: "network" },
  { key: "rel_jnim_niger", url: "/intelligence/africa/relation/jnim-niger-operates/", type: "relation" },
  { key: "rel_eij_alqaida", url: "/intelligence/africa/relation/expc-eij-alqaida-integration/", type: "relation" },
  { key: "rel_lakurawa_is_sahel", url: "/intelligence/africa/relation/d1-lakurawa-is-sahel-network/", type: "relation" },
  { key: "entity_al_shabaab", url: "/intelligence/africa/entity/al-shabaab/", type: "entity" },
  { key: "entity_aqim", url: "/intelligence/africa/entity/aqim/", type: "entity" },
  { key: "entity_eij", url: "/intelligence/africa/entity/egyptian-islamic-jihad/", type: "entity" },
  { key: "entity_gia", url: "/intelligence/africa/entity/gia/", type: "entity" },
  { key: "entity_lakurawa", url: "/intelligence/africa/entity/lakurawa/", type: "entity" },
];
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
];

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
const events = { console: [], exceptions: [], failed: [], logs: [] };
function connect(url) {
  return new Promise((res, rej) => {
    const s = new ws(url);
    let id = 0; const pending = {};
    const send = (method, params) => new Promise((r, j) => { const mid = ++id; pending[mid] = { r, j }; s.send(JSON.stringify({ id: mid, method, params: params || {} })); });
    s.on("message", (raw) => {
      const m = JSON.parse(raw);
      if (m.id && pending[m.id]) { if (m.error) pending[m.id].j(new Error(JSON.stringify(m.error))); else pending[m.id].r(m.result); delete pending[m.id]; return; }
      if (m.method === "Runtime.consoleAPICalled" && ["error", "assert"].indexOf(m.params.type) >= 0) events.console.push(m.params);
      if (m.method === "Runtime.exceptionThrown") events.exceptions.push(m.params);
      if (m.method === "Network.loadingFailed" && m.params.canceled !== true) events.failed.push(m.params);
      if (m.method === "Log.entryAdded" && m.params.entry.level === "error") events.logs.push(m.params.entry);
    });
    s.on("open", () => res(send));
    s.on("error", rej);
  });
}

(async () => {
  const send = await connect(await getTarget());
  await send("Runtime.enable"); await send("Network.enable"); await send("Log.enable"); await send("Page.enable");
  await send("Network.setCacheDisabled", { cacheDisabled: true });
  try { await send("Network.clearBrowserCache"); } catch (e) {}
  const ev = (expr, tmo) => withTimeout(send("Runtime.evaluate", { expression: expr, returnByValue: true }), tmo || 12000, "ev").then((r) => (r && r.result) ? r.result.value : undefined);

  const results = [];
  let shots = 0;
  for (const page of PAGES) {
    for (const vp of VIEWPORTS) {
      events.console.length = 0; events.exceptions.length = 0; events.failed.length = 0; events.logs.length = 0;
      let entry = null;
      try {
        await send("Emulation.setDeviceMetricsOverride", { width: vp.width, height: vp.height, deviceScaleFactor: 1, mobile: vp.name === "mobile" });
        const url = BASE + page.url;
        await withTimeout(send("Page.navigate", { url }), 15000, "nav");
        // wait for the page's primary render; network pages need data to finish loading
        for (let w = 0; w < 40; w++) {
          const done = await withTimeout(send("Runtime.evaluate", { expression: "!!(document.querySelector('#entityHeading h1') || document.querySelector('#relationHeading h1') || document.querySelector('.graph-node') || document.querySelector('h1'))", returnByValue: true }), 6000, "w");
          if (done && done.result && done.result.value) break;
          await sleep(500);
        }
        await sleep(vp.name === "mobile" ? 2000 : 1600);
        const state = await ev(`(function () {
          var out = {
            h1: (document.querySelector("h1") || {}).textContent || "",
            overflow: document.documentElement.scrollWidth > window.innerWidth + 2,
            broken_anchors: Array.prototype.filter.call(document.querySelectorAll("a[href*='#']"), function (a) { var h = a.getAttribute("href"); if (!h || h === "#") return false; var id = h.split("#")[1]; return id && !document.getElementById(id); }).length,
            secs: document.querySelectorAll(".profile-section").length,
            source_last: (function () { var body = document.querySelector("#entityBody"); if (!body) return null; var s = body.querySelectorAll(".profile-section"); return s.length ? s[s.length - 1].id : null; })(),
            src_panel: (function () { var p = document.querySelector("#entitySources"); return p ? p.querySelectorAll(".profile-section").length : -1; })(),
            toc_btn: (document.querySelector("#entityToc .toc-btn") || {}).textContent || "",
            toc_open: (function () { var t = document.querySelector("#entityToc .profile-toc-details"); return t ? t.open === true : null; })(),
            net_nodes: document.querySelectorAll(".graph-node").length,
            net_labeled: (function () { return Array.prototype.filter.call(document.querySelectorAll(".graph-node .node-label"), function (x) { return x.textContent.trim().length > 0; }).length; })(),
            net_center: (document.querySelector(".graph-node.is-center .node-label") || {}).textContent || "",
            net_stats: (document.querySelector("#graphVisStats") || {}).textContent || "",
            rel_h1: (function () { var h = document.querySelector("#relationHeading h1"); return h ? h.textContent : ""; })(),
            rel_status: (function () { var te = document.querySelector("#relationHeading .intel-title-en"); return te ? te.textContent : ""; })(),
            rel_tech_open: (function () { var t = document.querySelector(".rel-tech-details"); return t ? t.open === true : null; })(),
            rel_body_links: (function () { return Array.prototype.filter.call(document.querySelectorAll("#relationBody a"), function (a) { var t = a.textContent; return t.indexOf("尼日尔") >= 0 || t.indexOf("马里") >= 0 || t.indexOf("贝宁") >= 0; }).length; })(),
            ent_status: (document.querySelector("#entityHeading .intel-badge.status") || {}).textContent || "",
            page_type: document.body.getAttribute("data-africa-page")
          };
          return out;
        })()`);
        const shot = path.join(__dirname, "..", "..", "qa-artifacts-ui-hard-fix-a", "screenshots", `${page.key}_${vp.name}.png`);
        fs.mkdirSync(path.dirname(shot), { recursive: true });
        const shotRes = await send("Page.captureScreenshot", { format: "png" });
        fs.writeFileSync(shot, Buffer.from(shotRes.data, "base64")); shots++;
        // build gates
        let gates = [];
        const pass = (n, c) => gates.push({ name: n, pass: !!c });
        pass("console_errors=0", events.console.length === 0);
        pass("exceptions=0", events.exceptions.length === 0);
        pass("failed_requests=0", events.failed.length === 0);
        pass("log_errors=0", events.logs.length === 0);
        pass("overflow=0", state.overflow === false);
        pass("broken_anchors=0", state.broken_anchors === 0);
        if (page.type === "network") {
          pass("net_clean_default", state.net_labeled >= 1 && state.net_labeled <= Math.max(8, Math.ceil(state.net_nodes / 3)));
          pass("net_center_label", state.net_center.length > 0);
          pass("net_stats_visible", state.net_stats.length > 0);
          pass("net_no_machine_label", !/rel-|reported_activity|freshness=/.test(state.net_center + state.net_stats));
        }
        if (page.type === "relation") {
          pass("rel_h1_no_machine", !/rel-|reported_activity_presence|freshness=|operates_in/.test(state.rel_h1));
          pass("rel_status_localized", /_/.test(state.rel_status) === false && state.rel_status.length > 0);
          pass("rel_tech_collapsed", state.rel_tech_open === false);
          if (page.key === "rel_jnim_niger") pass("rel_country_links_visible", state.rel_body_links > 0);
        }
        if (page.type === "entity") {
          pass("ent_sources_not_in_body", state.source_last !== "sec-sources" && state.source_last !== "sec-notes");
          pass("ent_sources_at_end", state.src_panel > 0);
          pass("ent_toc_toggle", state.toc_btn.length > 0);
          pass("ent_status_localized", state.ent_status.length > 0 && !/_/.test(state.ent_status));
        }
        entry = { key: page.key, viewport: vp.name, url, state, gates, console_errors: events.console.length, exceptions: events.exceptions.length, failed_requests: events.failed.length, log_errors: events.logs.length };
        const failed = gates.filter((g) => !g.pass);
        // retry once when a network graph failed to render (CDN latency race)
        if (failed.length && page.type === "network" && (!state.net_nodes || state.net_nodes === 0)) {
          await sleep(1500);
          await withTimeout(send("Page.navigate", { url }), 15000, "retry-nav");
          for (let w = 0; w < 40; w++) {
            const done = await withTimeout(send("Runtime.evaluate", { expression: "!!document.querySelector('.graph-node')", returnByValue: true }), 6000, "rw");
            if (done && done.result && done.result.value) break;
            await sleep(500);
          }
          await sleep(1200);
          const st2 = await ev(`(function(){ return { net_nodes: document.querySelectorAll(".graph-node").length, net_labeled: Array.prototype.filter.call(document.querySelectorAll(".graph-node .node-label"), function (x) { return x.textContent.trim().length > 0; }).length, net_center: (document.querySelector(".graph-node.is-center .node-label")||{}).textContent || "", net_stats: (document.querySelector("#graphVisStats")||{}).textContent || "" }; })()`);
          if (st2 && st2.net_nodes > 0) {
            const g2 = entry.gates.map((g) => {
              if (g.name === "net_clean_default") return { name: g.name, pass: st2.net_labeled >= 1 && st2.net_labeled <= Math.max(8, Math.ceil(st2.net_nodes / 3)) };
              if (g.name === "net_center_label") return { name: g.name, pass: st2.net_center.length > 0 };
              if (g.name === "net_stats_visible") return { name: g.name, pass: st2.net_stats.length > 0 };
              if (g.name === "net_no_machine_label") return { name: g.name, pass: !/rel-|reported_activity|freshness=/.test(st2.net_center + st2.net_stats) };
              return g;
            });
            entry.gates = g2; entry.state = Object.assign({}, entry.state, st2); entry.retried = true;
          }
        }
        console.log(`[done] ${page.key} @ ${vp.name} — gates ${gates.length - failed.length}/${gates.length} console=${events.console.length} exc=${events.exceptions.length} shots=${shots}`);
      } catch (e) {
        entry = { key: page.key, viewport: vp.name, url: BASE + page.url, error: String(e && e.message || e), gates: [{ name: "no-crash", pass: false }], console_errors: 0, exceptions: 0, failed_requests: 0, log_errors: 0 };
        console.log(`[err] ${page.key} @ ${vp.name} — ${e.message}`);
      }
      results.push(entry);
    }
  }
  const allGates = results.flatMap((r) => (r.gates || []).map((g) => g.name));
  const total = allGates.length, passed = allGates.filter((g, i) => results.flatMap((r) => r.gates || []).map((x) => x.pass)[i]).length;
  const gateSummary = {};
  results.flatMap((r) => r.gates || []).forEach((g) => { gateSummary[g.name] = gateSummary[g.name] || { total: 0, pass: 0 }; gateSummary[g.name].total++; if (g.pass) gateSummary[g.name].pass++; });
  const summary = {
    ONLINE_BROWSER_QA: allGates.length && results.every((r) => !r.error && (r.gates || []).every((g) => g.pass)) ? "PASS" : "FAIL",
    total_gates: total, passed_gates: allGates.filter((g, i) => results.flatMap((r) => r.gates || []).map((x) => x.pass)[i]).length,
    pages: results.length, screenshots: shots, base: BASE, run_at: new Date().toISOString(), gate_summary: gateSummary, results,
  };
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(summary, null, 2));
  console.log("=== ONLINE HARD FIX BROWSER QA:", summary.passed_gates + "/" + total, "===");
  process.exit(summary.ONLINE_BROWSER_QA === "PASS" ? 0 : 1);
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
