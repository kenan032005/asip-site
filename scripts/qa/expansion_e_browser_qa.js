// Expansion E — local browser QA against dist (127.0.0.1:4174).
const path = require("path");
const http = require("http");
const fs = require("fs");
const ws = require("ws");
const CDP_PORT = 9234;
const BASE = "http://127.0.0.1:4174";
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-expansion-e", "browser-qa-results.json");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const withTimeout = (p, ms, label) => Promise.race([p, new Promise((_, j) => setTimeout(() => j(new Error("timeout " + label)), ms))]);

const PAGES = [
  { key: "entity_mnjtf", url: "/intelligence/africa/entity/mnjtf/", type: "entity" },
  { key: "entity_aes", url: "/intelligence/africa/entity/fu-aes/", type: "entity" },
  { key: "entity_g5", url: "/intelligence/africa/entity/g5-sahel-joint-force/", type: "entity" },
  { key: "entity_samim", url: "/intelligence/africa/entity/samim/", type: "entity" },
  { key: "entity_fadm", url: "/intelligence/africa/entity/mozambique-defence-forces/", type: "entity" },
  { key: "entity_rdf", url: "/intelligence/africa/entity/rwanda-force-mozambique/", type: "entity" },
  { key: "entity_tpdf", url: "/intelligence/africa/entity/tpdf/", type: "entity" },
  { key: "entity_africa_corps", url: "/intelligence/africa/entity/africa-corps/", type: "entity" },
  { key: "entity_lna", url: "/intelligence/africa/entity/libyan-national-army/", type: "entity" },
  { key: "entity_africom", url: "/intelligence/africa/entity/africom/", type: "entity" },
  { key: "entity_minusma", url: "/intelligence/africa/entity/minusma/", type: "entity" },
  { key: "rel_mnjtf_iswap", url: "/intelligence/africa/relation/expe-mnjtf-iswap-hostile/", type: "relation" },
  { key: "rel_mnjtf_jas", url: "/intelligence/africa/relation/expe-mnjtf-jas-hostile/", type: "relation" },
  { key: "rel_aes_jnim", url: "/intelligence/africa/relation/expe-aes-jnim-hostile/", type: "relation" },
  { key: "rel_aes_is_sahel", url: "/intelligence/africa/relation/expe-aes-is-sahel-hostile/", type: "relation" },
  { key: "rel_africa_corps_wagner", url: "/intelligence/africa/relation/d1-africa-corps-wagner-history/", type: "relation" },
  { key: "rel_samim_is_moz", url: "/intelligence/africa/relation/expe-samim-is-moz-hostile/", type: "relation" },
  { key: "rel_fadm_is_moz", url: "/intelligence/africa/relation/fadm-is-moz-hostile/", type: "relation" },
  { key: "rel_rdf_is_moz", url: "/intelligence/africa/relation/is-moz-islamic-state2/", type: "relation" },
  { key: "rel_africom_shabaab", url: "/intelligence/africa/relation/expe-africom-shabaab-strikes/", type: "relation" },
  { key: "rel_africom_isis_somalia", url: "/intelligence/africa/relation/expe-africom-isis-somalia-strikes/", type: "relation" },
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
          return {
            h1: (document.querySelector("h1")||{}).textContent || "",
            overflow: document.documentElement.scrollWidth > window.innerWidth + 2,
            secs: document.querySelectorAll(".profile-section").length,
            ent_status: (document.querySelector("#entityHeading .intel-badge.status")||{}).textContent || "",
            rel_type: (document.querySelector("#relationHeading .intel-title-en")||{}).textContent || "",
            err: (document.querySelector("#intelError")||{hidden:true}).hidden === false ? (document.querySelector("#intelError").textContent||"") : ""
          };
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
        if (page.type === "entity") pass("entity_status_localized", state.ent_status.length > 0 && !/_/.test(state.ent_status));
        if (page.type === "relation") pass("rel_type_localized", state.rel_type.length > 0 && !/_/.test(state.rel_type));
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
  const allGates = results.flatMap((r) => r.gates || []);
  const total = allGates.length, passed = allGates.filter((g) => g.pass).length;
  const summary = { BROWSER_QA: (allGates.length && results.every((r) => !r.error && (r.gates || []).every((g) => g.pass))) ? "PASS" : "FAIL", total_gates: total, passed_gates: passed, pages: results.length, base: BASE, results };
  fs.writeFileSync(OUT, JSON.stringify(summary, null, 2));
  console.log(`=== EXPANSION E BROWSER QA: ${passed}/${total} ===`);
  process.exit(summary.BROWSER_QA === "PASS" ? 0 : 1);
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
