// Expansion D — local browser QA against dist (127.0.0.1:4174).
const path = require("path");
const http = require("http");
const fs = require("fs");
const ws = require("ws");
const CDP_PORT = 9233;
const BASE = "http://127.0.0.1:4174";
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-expansion-d", "browser-qa-results.json");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const withTimeout = (p, ms, label) => Promise.race([p, new Promise((_, j) => setTimeout(() => j(new Error("timeout " + label)), ms))]);

const PAGES = [
  { key: "entity_isis_sinai", url: "/intelligence/africa/entity/isis-sinai/", type: "entity" },
  { key: "entity_ansaroul", url: "/intelligence/africa/entity/ansarul-islam/", type: "entity" },
  { key: "entity_katiba_hanifa", url: "/intelligence/africa/entity/katiba-hanifa/", type: "entity" },
  { key: "entity_fpl", url: "/intelligence/africa/entity/niger-fpl/", type: "entity" },
  { key: "entity_fla", url: "/intelligence/africa/entity/fla/", type: "entity" },
  { key: "rel_isis_sinai_isis", url: "/intelligence/africa/relation/expd-isis-sinai-isis/", type: "relation" },
  { key: "rel_ansaroul_jnim", url: "/intelligence/africa/relation/d1-ansarul-jnim-constituent/", type: "relation" },
  { key: "rel_katiba_hanifa_jnim", url: "/intelligence/africa/relation/d2-katiba-hanifa-jnim/", type: "relation" },
  { key: "rel_fla_jnim", url: "/intelligence/africa/relation/d1-fla-jnim-cooperation/", type: "relation" },
  { key: "rel_fpl_niger", url: "/intelligence/africa/relation/expd-fpl-niger-operates/", type: "relation" },
];
// excluded objects must NOT have a route
const ABSENT = [
  { key: "entity_abm_absent", url: "/intelligence/africa/entity/ansar-bayt-al-maqdis/" },
  { key: "entity_lions_absent", url: "/intelligence/africa/entity/lions-caliphate-maghreb-cell/" },
  { key: "entity_nasr_absent", url: "/intelligence/africa/entity/nasr-jihad/" },
  { key: "entity_yusuf_absent", url: "/intelligence/africa/entity/yusuf-ghazi-group/" },
];
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
];
const events = { console: [], exceptions: [], failed: [], logs: [] };

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
  const wait = async (sel, tries) => { for (let i = 0; i < (tries || 40); i++) { if (await ev(`!!document.querySelector(${JSON.stringify(sel)})`) === true) return true; await sleep(500); } return false; };

  const results = [];
  for (const page of PAGES) {
    for (const vp of VIEWPORTS) {
      events.console.length = 0; events.exceptions.length = 0; events.failed.length = 0; events.logs.length = 0;
      let entry = null;
      try {
        await send("Emulation.setDeviceMetricsOverride", { width: vp.width, height: vp.height, deviceScaleFactor: 1, mobile: vp.name === "mobile" });
        const url = BASE + page.url;
        await withTimeout(send("Page.navigate", { url }), 15000, "nav");
        await wait(page.type === "entity" ? "#entityHeading h1" : "#relationHeading h1");
        await sleep(vp.name === "mobile" ? 1500 : 1200);
        const state = await ev(`(function(){
          var out = {
            h1: (document.querySelector("h1")||{}).textContent || "",
            overflow: document.documentElement.scrollWidth > window.innerWidth + 2,
            secs: document.querySelectorAll(".profile-section").length,
            rel_type: (function(){ var te = document.querySelector("#relationHeading .intel-title-en"); return te ? te.textContent : ""; })(),
            ent_status: (document.querySelector("#entityHeading .intel-badge.status")||{}).textContent || "",
            src_panel: (function(){ var p = document.querySelector("#entitySources"); return p ? p.querySelectorAll(".profile-section").length : -1; })(),
            toc_btn: (document.querySelector("#entityToc .toc-btn")||{}).textContent || "",
            body_links: (function(){ return Array.prototype.filter.call(document.querySelectorAll(".intel-prose a, #relationBody a"), function(a){ return a.getAttribute("href") && a.getAttribute("href").indexOf("/entity/") >= 0; }).length; })(),
            err: (document.querySelector("#intelError")||{hidden:true}).hidden === false ? (document.querySelector("#intelError").textContent||"") : ""
          };
          return out;
        })()`);
        const gates = [];
        const pass = (n, c) => gates.push({ name: n, pass: !!c });
        pass("console=0", events.console.length === 0);
        pass("exceptions=0", events.exceptions.length === 0);
        pass("failed=0", events.failed.length === 0);
        pass("log=0", events.logs.length === 0);
        pass("overflow=0", state.overflow === false);
        pass("h1_present", state.h1.length > 0);
        pass("no_intel_error", state.err === "");
        if (page.type === "entity") {
          pass("entity_sources_at_end", state.src_panel > 0);
          pass("entity_status_localized", state.ent_status.length > 0 && !/_/.test(state.ent_status));
        }
        if (page.type === "relation") {
          pass("rel_type_localized", state.rel_type.length > 0 && !/_/.test(state.rel_type));
        }
        entry = { key: page.key, viewport: vp.name, url, state, gates, console_errors: events.console.length, exceptions: events.exceptions.length, failed_requests: events.failed.length };
        const failed = gates.filter((g) => !g.pass);
        console.log(`[done] ${page.key} @ ${vp.name} — ${gates.length - failed.length}/${gates.length} console=${events.console.length} exc=${events.exceptions.length}`);
      } catch (e) {
        entry = { key: page.key, viewport: vp.name, url: BASE + page.url, error: String(e && e.message || e), gates: [{ name: "no-crash", pass: false }], console_errors: 0, exceptions: 0, failed_requests: 0 };
        console.log(`[err] ${page.key} @ ${vp.name} — ${e.message}`);
      }
      results.push(entry);
    }
  }
  // excluded objects: HTTP 404
  const absentChecks = [];
  for (const a of ABSENT) {
    const code = await new Promise((res) => {
      http.get(BASE + a.url, (r) => { res(r.statusCode); }).on("error", () => res(0));
    });
    const ok = code === 404;
    absentChecks.push({ key: a.key, url: a.url, status: code, pass: ok });
    console.log(`[absent] ${a.key} status=${code} -> ${ok ? "OK-404" : "BAD"}`);
  }
  const allGates = results.flatMap((r) => r.gates || []);
  const total = allGates.length, passed = allGates.filter((g) => g.pass).length;
  const absentOk = absentChecks.every((a) => a.pass);
  const summary = {
    BROWSER_QA: (allGates.length && results.every((r) => !r.error && (r.gates || []).every((g) => g.pass)) && absentOk) ? "PASS" : "FAIL",
    total_gates: total, passed_gates: passed, pages: results.length, absent_checks: absentChecks,
    absent_all_404: absentOk, base: BASE, results,
  };
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(summary, null, 2));
  console.log(`=== EXPANSION D BROWSER QA: ${passed}/${total} gates, absent=${absentOk ? "OK" : "BAD"} ===`);
  process.exit(summary.BROWSER_QA === "PASS" ? 0 : 1);
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
