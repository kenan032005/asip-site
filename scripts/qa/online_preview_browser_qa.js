#!/usr/bin/env node
/* Online preview browser QA against the real public HTTPS URL. */
const fs = require("fs");
const path = require("path");
const http = require("http");
const ws = require("ws");

const BASE = "https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2";
const CDP_PORT = 9229;
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-online-preview", "online-browser-qa.json");

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

async function newTab() {
  // Open a dedicated blank tab for QA via an existing browser-level connection.
  const list = await new Promise((res, rej) => {
    http.get(`http://127.0.0.1:${CDP_PORT}/json/new?about:blank`, (r) => {
      let d = "";
      r.on("data", (c) => (d += c));
      r.on("end", () => {
        try { res(JSON.parse(d)); } catch (e) { rej(e); }
      });
    }).on("error", rej);
  });
  return list.webSocketDebuggerUrl;
}

function connect(url) {
  return new Promise((res, rej) => {
    const s = new ws(url);
    let id = 0;
    const pending = {};
    let eventHandler = null;
    const send = (method, params) =>
      new Promise((r, j) => {
        const mid = ++id;
        pending[mid] = { r, j };
        s.send(JSON.stringify({ id: mid, method, params: params || {} }));
      });
    s.on("message", (raw) => {
      const m = JSON.parse(raw);
      if (m.id && pending[m.id]) {
        if (m.error) pending[m.id].j(new Error(JSON.stringify(m.error)));
        else pending[m.id].r(m.result);
        delete pending[m.id];
      } else if (m.method && eventHandler) {
        eventHandler(m);
      }
    });
    send.onEvent = (fn) => {
      eventHandler = fn;
    };
    s.on("open", () => res(send));
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const withTimeout = (p, ms, tag) =>
  Promise.race([p, sleep(ms).then(() => { throw new Error("TIMEOUT:" + tag); })]);

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
];

const PAGES = [
  // Entities (8)
  { key: "entity_al_shabaab", url: "/intelligence/africa/entity/al-shabaab/" },
  { key: "entity_lakurawa", url: "/intelligence/africa/entity/lakurawa/" },
  { key: "entity_aqim", url: "/intelligence/africa/entity/aqim/" },
  { key: "entity_eij", url: "/intelligence/africa/entity/egyptian-islamic-jihad/" },
  { key: "entity_gia", url: "/intelligence/africa/entity/gia/" },
  { key: "entity_aiai", url: "/intelligence/africa/entity/aiai/" },
  { key: "entity_updf", url: "/intelligence/africa/entity/updf/" },
  { key: "entity_maitatsine", url: "/intelligence/africa/entity/maitatsine-movement/" },
  // Relations (6)
  { key: "rel_shabaab_iss", url: "/intelligence/africa/relation/expa-shabaab-isis-somalia-rivalry/" },
  { key: "rel_lakurawa_is_sahel", url: "/intelligence/africa/relation/d1-lakurawa-is-sahel-network/" },
  { key: "rel_eij_alqaida", url: "/intelligence/africa/relation/expc-eij-alqaida-integration/" },
  { key: "rel_gia_aqim", url: "/intelligence/africa/relation/expc-gia-aqim-lineage/" },
  { key: "rel_battar_isis_libya", url: "/intelligence/africa/relation/expc-battar-isis-libya/" },
  { key: "rel_murabitoun_is_sahel", url: "/intelligence/africa/relation/is-sahel-mourabitoun-splinter/" },
  // Lists (3)
  { key: "entities_list", url: "/intelligence/africa/entities/" },
  { key: "relations_list", url: "/intelligence/africa/relations/" },
  { key: "sources_list", url: "/intelligence/africa/sources/" },
  // Network focus (5)
  { key: "network_al_shabaab", url: "/intelligence/africa/network/?focus=actor-al-shabaab" },
  { key: "network_aqim", url: "/intelligence/africa/network/?focus=actor-aqim" },
  { key: "network_jnim", url: "/intelligence/africa/network/?focus=actor-jnim" },
  { key: "network_isis_somalia", url: "/intelligence/africa/network/?focus=actor-isis-somalia" },
  { key: "network_adf", url: "/intelligence/africa/network/?focus=actor-adf-isis-ca" },
  // Landing
  { key: "landing", url: "/intelligence/africa/" },
];

(async () => {
  let send;
  try {
    send = await connect(await newTab());
  } catch (e) {
    console.error("tab open failed, falling back to existing page:", e.message);
    send = await connect(await getTarget());
  }
  await send("Runtime.enable");
  await send("Network.enable");
  await send("Network.setCacheDisabled", { cacheDisabled: true });
  await send("Page.enable");
  await send("Log.enable");

  // recreate the connection every N pages to avoid long-session CDP drift
  const RECONNECT_EVERY = 12;

  const results = [];
  let shots = 0;

  for (const page of PAGES) {
    for (const vp of VIEWPORTS) {
      const events = { console: [], exceptions: [], failed: [], logs: [] };
      send.onEvent((m) => {
        if (m.method === "Runtime.consoleAPICalled" && ["error", "assert"].includes(m.params.type)) {
          events.console.push(m.params);
        }
        if (m.method === "Runtime.exceptionThrown") events.exceptions.push(m.params);
        if (m.method === "Network.loadingFailed" && m.params.canceled !== true) events.failed.push(m.params);
        if (m.method === "Log.entryAdded" && m.params.entry.level === "error") events.logs.push(m.params.entry);
      });

      // periodic reconnect to avoid long-session CDP drift on slow public pages
      if (results.length > 0 && results.length % RECONNECT_EVERY === 0) {
        try { send.terminate && send.terminate(); } catch (e) {}
        try { send = await connect(await getTarget()); } catch (e) { console.error("reconnect failed", e.message); }
        await send("Runtime.enable");
        await send("Network.enable");
        await send("Network.setCacheDisabled", { cacheDisabled: true });
        await send("Page.enable");
        await send("Log.enable");
      }

      await withTimeout(send("Emulation.setDeviceMetricsOverride", { width: vp.width, height: vp.height, deviceScaleFactor: 1, mobile: vp.name === "mobile" }), 8000, "viewport");
      const url = BASE + page.url;
      let entry;
      try {
        await withTimeout(send("Page.navigate", { url }), 15000, "navigate");
        await sleep(vp.name === "mobile" ? 5000 : 4200);

        const state = await withTimeout(send("Runtime.evaluate", {
          expression: `(function () {
            var out = {
              h1: (document.querySelector("h1") || {}).textContent || "",
              title: document.title,
              sections: document.querySelectorAll(".profile-section").length,
              toc_links: document.querySelectorAll("#entityToc a, .profile-toc a").length,
              toc_open: !!document.querySelector("#entityToc[open], .profile-toc-details[open]"),
              keyfacts: document.querySelectorAll(".intel-keyfacts > div").length,
              uncertainty_cards: document.querySelectorAll(".intel-uncertainty-card").length,
              disputed_badges: document.querySelectorAll(".intel-sem-chip.disputed, .kf-disputed, .disputed-badge").length,
              party_cards: document.querySelectorAll(".relation-party-card").length,
              hero_summary: document.querySelectorAll(".relation-hero-summary").length,
              tl_stages: document.querySelectorAll(".rtl-stage-card").length,
              current_banner: document.querySelectorAll(".rtl-current-banner").length,
              source_groups: document.querySelectorAll(".source-group").length,
              entity_inline_links: document.querySelectorAll("#entityBody a[href*='/entity/']").length,
              relation_auto_links: document.querySelectorAll(".relation-body a[href*='/entity/'], .relation-hero a[href*='/entity/']").length,
              network_nodes: document.querySelectorAll(".graph-node").length,
              network_edges: document.querySelectorAll(".graph-edge").length,
              has_2hop_btn: !!document.querySelector("#twoHopToggle"),
              filter_controls: document.querySelectorAll(".list-controls select, .list-controls input").length,
              scroll_height: document.documentElement.scrollHeight,
              overflow: document.documentElement.scrollWidth > window.innerWidth + 2,
              viewport_w: window.innerWidth,
            };
            out.broken_anchors = Array.prototype.filter.call(document.querySelectorAll("a[href*='#']"), function (a) {
              var h = a.getAttribute("href");
              if (!h || h === "#") return false;
              var id = h.split("#")[1];
              return id && !document.getElementById(id);
            }).length;
            return out;
          })()`,
          returnByValue: true,
        }), 12000, "evaluate");

        const shot = path.join(__dirname, "..", "..", "qa-artifacts-online-preview", "screenshots",
          `${page.key}_${vp.name}.png`);
        fs.mkdirSync(path.dirname(shot), { recursive: true });
        const shotRes = await withTimeout(send("Page.captureScreenshot", { format: "png" }), 15000, "shot");
        fs.writeFileSync(shot, Buffer.from(shotRes.data, "base64"));
        shots++;

        entry = {
          key: page.key, viewport: vp.name, url,
          state: state.result.value,
          console_errors: events.console.length,
          exceptions: events.exceptions.length,
          failed_requests: events.failed.length,
          log_errors: events.logs.length,
        };
      } catch (err) {
        entry = {
          key: page.key, viewport: vp.name, url,
          state: { h1: "", error: String(err).slice(0, 200) },
          console_errors: events.console.length,
          exceptions: events.exceptions.length,
          failed_requests: events.failed.length,
          log_errors: events.logs.length,
          page_error: String(err).slice(0, 300),
        };
      }
      results.push(entry);
      console.log(`[done] ${page.key} @ ${vp.name} — console=${entry.console_errors} exc=${entry.exceptions} req=${entry.failed_requests}${entry.page_error ? " ERR=" + entry.page_error : ""} shots=${shots}`);
    }
  }

  const summary = {
    base: BASE,
    pages_checked: results.length,
    screenshots: shots,
    console_errors: results.reduce((a, r) => a + r.console_errors, 0),
    exceptions: results.reduce((a, r) => a + r.exceptions, 0),
    failed_requests: results.reduce((a, r) => a + r.failed_requests, 0),
    log_errors: results.reduce((a, r) => a + r.log_errors, 0),
    broken_anchors: results.reduce((a, r) => a + (r.state.broken_anchors || 0), 0),
    overflow_pages: results.filter((r) => r.state.overflow).map((r) => `${r.key}@${r.viewport}`),
    gate: results.every((r) => r.console_errors === 0 && r.exceptions === 0 && r.failed_requests === 0 && r.log_errors === 0 && !r.state.overflow) ? "PASS" : "FAIL",
  };
  fs.writeFileSync(OUT, JSON.stringify({ summary, results }, null, 2), "utf-8");
  console.log("\n=== ONLINE BROWSER QA SUMMARY ===");
  console.log(JSON.stringify(summary, null, 2));
  process.exit(summary.gate === "PASS" ? 0 : 1);
})().catch((e) => {
  console.error("FATAL", e);
  process.exit(2);
});
