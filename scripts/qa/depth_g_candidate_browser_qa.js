#!/usr/bin/env node
/* DEPTH G candidate browser QA: closure-touched entities + relations + country
   and index routes, across FIVE viewports 1920/1440/1366/768/390.
   Asserts: no console errors, no runtime exceptions, no unhandled promise
   rejections, no failed/bad requests, no broken assets, no horizontal overflow,
   maturity badge rendering, and that downgraded objects render their NEW tier.
   Writes qa-artifacts-depth-g/candidate-browser-qa.json */
const http = require("http");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");
const PUBLIC = process.env.PUBLIC_BASE || "http://127.0.0.1:4191/intelligence/africa";
const CDP_PORT = Number(process.env.CDP_PORT || 9252);
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-depth-g", "candidate-browser-qa.json");

// entity closure targets + the three truthful downshifts
const ENTITIES = [
  ["katiba-hanifa", "Katiba Hanifa (E3 closure)"],
  ["aqim", "AQIM (al-Annabi fix)"],
  ["iswap", "ISWAP (Bakura fix)"],
  ["is-sahel", "IS-Sahel"],
  ["jnim", "JNIM"],
  ["ansaru", "Ansaru"],
  ["salva-kiir", "Salva Kiir (E3->E2)"],
  ["jafar-dicko", "Jafar Dicko (E3->E2)"],
  ["dozos-of-macina", "Dozos of Macina (E3->E2)"],
  ["slm-aw", "SLM-AW"],
];
// JNIM-IS two-phase repair + pack-locked overrides + truthful downshifts
const RELATIONS = [
  ["jnim-is-sahel-hostile", "JNIM-IS historical phase (R2)"],
  ["jnim-is-sahel-conflict", "JNIM-IS current conflict (R3)"],
  ["jnim-katiba-constituent", "JNIM-Katiba Macina"],
  ["jnim-benin-forces-fought", "JNIM-Benin Forces"],
  ["mali-army-jnim", "Mali Army-JNIM"],
  ["burkina-army-jnim", "Burkina Army-JNIM"],
  ["cameroon-army-ambazonia", "Cameroon Army-Ambazonia"],
  ["d2-katiba-hanifa-jnim", "Katiba Hanifa-JNIM"],
  ["d2-katiba-hanifa-benin-forces", "Katiba Hanifa-Benin"],
  ["is-moz-islamic-state2", "RDF-ISM (R3->R2)"],
  ["d1-ansaru-jas-split", "Ansaru-JAS split (R2->R1)"],
  ["d1-ansaru-aqim-allegiance", "Ansaru-AQIM (R2->R1)"],
  ["d1-ansaru-jnim-affiliation", "Ansaru-JNIM (R2->R1)"],
  ["d2-dana-fama-coop", "Dana Ambassagou-FAMa (R2->R1)"],
  ["d2-dozos-macina-amadou-led", "Dozos-Amadou (R2->R1)"],
  ["d1-fu-aes-region", "FU-AES region"],
];
const VIEWPORTS = [[1920, "1920"], [1440, "1440"], [1366, "1366"], [768, "768"], [390, "390"]];
const ROUTES = [
  ["Africa root", ""], ["Entities index", "entities/"], ["Relations index", "relations/"],
  ["Network", "network/"],
  ["Mali country", "country/mali/"], ["Burkina Faso country", "country/burkina-faso/"],
  ["Benin country", "country/benin/"], ["Nigeria country", "country/nigeria/"],
]
  .concat(ENTITIES.map(([s, l]) => ["entity " + l, "entity/" + s + "/"]))
  .concat(RELATIONS.map(([s, l]) => ["relation " + l, "relation/" + s + "/"]));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = "";
      res.on("data", (c) => (data += c));
      res.on("end", () => { try { resolve(JSON.parse(data)); } catch (e) { reject(e); } });
    }).on("error", reject);
  });
}

let msgId = 0;
function makeClient(ws) {
  const pending = new Map();
  ws.on("message", (raw) => {
    const msg = JSON.parse(raw.toString());
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  });
  return { send(m, p = {}) { return new Promise((res) => { const id = ++msgId; pending.set(id, res); ws.send(JSON.stringify({ id, method: m, params: p })); }); } };
}

async function main() {
  const pages = [];
  const events = { exceptions: [], console: [], failed: [], bad: [], rejections: [] };
  const targets = await getJson(`http://127.0.0.1:${CDP_PORT}/json/list`);
  // NOTE: Edge injects edge:// / extension / devtools targets even with
  // --disable-extensions; filter them or navigation lands on an internal page.
  const target = targets.find((t) => t.type === "page"
    && !t.url.startsWith("edge://") && !t.url.startsWith("chrome-extension://")
    && !t.url.startsWith("devtools://"));
  if (!target) throw new Error("no usable page target on " + CDP_PORT);
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.on("open", r));
  const cdp = makeClient(ws);
  ws.on("message", (raw) => {
    const msg = JSON.parse(raw.toString());
    if (msg.method === "Runtime.exceptionThrown") {
      const d = msg.params.exceptionDetails || {};
      const text = JSON.stringify(d);
      if (/unhandledrejection|Uncaught \(in promise\)/i.test(text)) events.rejections.push(d);
      else events.exceptions.push(d);
    }
    if (msg.method === "Runtime.consoleAPICalled" &&
        (msg.params.type === "error" || msg.params.type === "warning")) events.console.push(msg.params);
    if (msg.method === "Network.loadingFailed") events.failed.push(msg.params);
    if (msg.method === "Network.responseReceived" && msg.params.response.status >= 400
        && !/favicon/i.test(msg.params.response.url)) events.bad.push(msg.params);
  });
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await cdp.send("Network.enable");
  await cdp.send("Log.enable");
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });

  async function evaluate(expression) {
    const r = await cdp.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    return r.result && r.result.result ? r.result.result.value : null;
  }

  async function check(width, label, route, kind) {
    await cdp.send("Emulation.setDeviceMetricsOverride", { width, height: 900, deviceScaleFactor: 1, mobile: false });
    const url = `${PUBLIC}/${route}`;
    const before = { exc: events.exceptions.length, con: events.console.length,
                     fai: events.failed.length, bad: events.bad.length, rej: events.rejections.length };
    await cdp.send("Page.navigate", { url });
    for (let i = 0; i < 40; i++) {
      const done = await evaluate(`(() => document.readyState === "complete")()`);
      if (done) break;
      await sleep(250);
    }
    await sleep(kind === "relation" ? 350 : 200);
    const state = await evaluate(`(() => {
      const err = document.querySelector("#intelError");
      const top = document.querySelector("#topbar");
      const badge = document.querySelector(".intel-badge[class*='m-']");
      const brokenImgs = Array.from(document.images).filter(i => i.complete && i.naturalWidth === 0).length;
      return {
        ready_state: document.readyState,
        error_hidden: !err || err.hidden,
        header_loaded: !!top && top.innerText.trim().length > 0,
        maturity_badge: badge ? badge.className : "",
        badge_text: badge ? badge.innerText.trim().slice(0, 40) : "",
        analysis_partition: !!document.querySelector(".intel-analysis-card"),
        watch_partition: !!document.querySelector(".intel-watch-card"),
        h1: document.querySelector("h1") ? document.querySelector("h1").innerText.slice(0, 60) : "",
        overflow: document.documentElement.scrollWidth > innerWidth + 2,
        broken_images: brokenImgs,
        body_chars: document.body ? document.body.innerText.replace(/\\s+/g, "").length : 0,
      };
    })()`);
    pages.push({
      viewport: width, label, route, kind, url, state,
      events: {
        runtime_exceptions: events.exceptions.length - before.exc,
        console_errors: events.console.length - before.con,
        failed_requests: events.failed.length - before.fai,
        bad_responses: events.bad.length - before.bad,
        unhandled_rejections: events.rejections.length - before.rej,
      },
    });
  }

  for (const [label, route] of ROUTES) {
    if (!route) { await check(1920, label, "", "root"); continue; }
    if (route.startsWith("entity/") || route.startsWith("relation/")) {
      for (const [w, wl] of VIEWPORTS) {
        await check(w, `${label} ${wl}`, route, route.startsWith("relation/") ? "relation" : "entity");
      }
    } else {
      await check(1920, label, route, "index");
    }
  }

  const fails = [];
  for (const p of pages) {
    const e = p.events;
    if (p.state.ready_state !== "complete" || !p.state.header_loaded || !p.state.error_hidden ||
        p.state.overflow || p.state.broken_images > 0 || e.runtime_exceptions > 0 ||
        e.console_errors > 0 || e.failed_requests > 0 || e.bad_responses > 0 ||
        e.unhandled_rejections > 0) {
      fails.push(`${p.viewport} ${p.label}: ${JSON.stringify(p.state)} ${JSON.stringify(e)}`);
    }
  }

  // verify downgraded objects render their NEW (lower) tier, never the old one
  const EXPECT = {
    "entity/salva-kiir/": "e2_developed",
    "entity/jafar-dicko/": "e2_developed",
    "entity/dozos-of-macina/": "e2_developed",
    "relation/is-moz-islamic-state2/": "r2_developed_relationship",
    "relation/d1-ansaru-jas-split/": "r1_simple_sourced_relation",
    "relation/d1-ansaru-aqim-allegiance/": "r1_simple_sourced_relation",
    "relation/d1-ansaru-jnim-affiliation/": "r1_simple_sourced_relation",
    "relation/d2-dana-fama-coop/": "r1_simple_sourced_relation",
    "relation/d2-dozos-macina-amadou-led/": "r1_simple_sourced_relation",
    "relation/jnim-is-sahel-hostile/": "r2_developed_relationship",
    "relation/jnim-is-sahel-conflict/": "r3_full_relationship_intelligence",
    "entity/katiba-hanifa/": "e3_full_encyclopedia",
  };
  const badgeChecks = [];
  for (const [route, want] of Object.entries(EXPECT)) {
    const p = pages.find((x) => x.route === route && x.viewport === 1920);
    const got = p ? p.state.maturity_badge : "(page not visited)";
    const ok = !!p && got.includes("m-" + want);
    badgeChecks.push({ route, expect: want, got, ok });
    if (!ok) fails.push(`badge tier mismatch ${route}: want m-${want} got ${got}`);
  }

  const report = {
    artifact: "DEPTHG_CANDIDATE_BROWSER_QA",
    viewports: VIEWPORTS.map((v) => v[0]),
    totals: {
      pages: pages.length,
      fails: fails.length,
      console_errors: pages.reduce((a, p) => a + p.events.console_errors, 0),
      runtime_exceptions: pages.reduce((a, p) => a + p.events.runtime_exceptions, 0),
      failed_requests: pages.reduce((a, p) => a + p.events.failed_requests, 0),
      bad_responses: pages.reduce((a, p) => a + p.events.bad_responses, 0),
      unhandled_rejections: pages.reduce((a, p) => a + p.events.unhandled_rejections, 0),
      broken_images: pages.reduce((a, p) => a + p.state.broken_images, 0),
      overflow_pages: pages.filter((p) => p.state.overflow).length,
    },
    badge_tier_checks: badgeChecks,
    fails,
    pages,
  };
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(report, null, 1));

  console.log(`pages=${pages.length} fails=${fails.length}`);
  console.log("totals:", JSON.stringify(report.totals));
  console.log(`badge tier checks: ${badgeChecks.filter((b) => b.ok).length}/${badgeChecks.length} ok`);
  fails.slice(0, 12).forEach((f) => console.log("FAIL:", f));
  ws.close();
  process.exit(fails.length ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(2); });
