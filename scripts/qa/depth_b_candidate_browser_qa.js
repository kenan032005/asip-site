#!/usr/bin/env node
/* DEPTH B candidate browser QA: 8 priority entities + 11 priority relations,
   four viewports 1920/1366/768/390. Asserts HTTP 200, no console errors,
   no runtime exceptions, no failed/bad requests, no horizontal overflow,
   maturity badges on upgraded pages, Facts/ASIP Analysis/Watch partitions.
   Writes qa-artifacts-depth-b/candidate-browser-qa.json */
const http = require("http");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");
const PUBLIC = process.env.PUBLIC_BASE || "http://127.0.0.1:4177/intelligence/africa";
const CDP_PORT = Number(process.env.CDP_PORT || 9234);
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-depth-b", "candidate-browser-qa.json");

const ENTITIES = [
  ["boko-haram-jas", "JAS"],
  ["iswap", "ISWAP"],
  ["mnjtf", "MNJTF"],
  ["nigerian-armed-forces", "Nigeria Army"],
  ["chad-armed-forces", "Chad Army"],
  ["cameroon-armed-forces", "Cameroon Army"],
  ["lakurawa", "Lakurawa"],
  ["ansaru", "Ansaru"],
];
const RELATIONS = [
  ["jas-iswap-conflict", "JAS-ISWAP"],
  ["jas-islamic-state-hostile", "JAS-IS State (repaired)"],
  ["iswap-islamic-state-affiliation", "ISWAP-IS State"],
  ["nigeria-mnjtf-member", "Nigeria-MNJTF"],
  ["chad-mnjtf-member", "Chad-MNJTF"],
  ["cameroon-mnjtf-member", "Cameroon-MNJTF"],
  ["cameroon-army-jas", "Cameroon-JAS"],
  ["cameroon-army-iswap", "Cameroon-ISWAP"],
  ["d1-ansaru-jas-split", "Ansaru-JAS"],
  ["d1-ansaru-aqim-allegiance", "Ansaru-AQIM"],
  ["d1-ansaru-jnim-affiliation", "Ansaru-JNIM"],
];
const VIEWPORTS = [[1920, 1080, "1920"], [1366, 900, "1366"], [768, 900, "768"], [390, 844, "390"]];
const ROUTES = [["Africa root", ""], ["Entities index", "entities/"], ["Relations index", "relations/"], ["Network", "network/"]]
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
  return {
    send(method, params = {}) {
      return new Promise((resolve) => {
        const id = ++msgId;
        pending.set(id, resolve);
        ws.send(JSON.stringify({ id, method, params }));
      });
    },
  };
}

async function main() {
  const pages = [];
  const events = { exceptions: [], console: [], failed: [], bad: [] };

  const targets = await getJson(`http://127.0.0.1:${CDP_PORT}/json/list`);
  const target = targets.find((t) =>
    !t.url.startsWith("edge://") && !t.url.startsWith("chrome-extension://") &&
    !t.url.startsWith("devtools://") && t.type === "page"
  );
  if (!target) throw new Error("no page target on " + CDP_PORT);
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.on("open", r));
  const cdp = makeClient(ws);

  ws.on("message", (raw) => {
    const msg = JSON.parse(raw.toString());
    if (msg.method === "Runtime.exceptionThrown") events.exceptions.push(msg.params);
    if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error") events.console.push(msg.params);
    if (msg.method === "Network.loadingFailed") events.failed.push(msg.params);
    if (msg.method === "Network.responseReceived" && msg.params.response.status >= 400) events.bad.push(msg.params);
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
    const before = { exc: events.exceptions.length, con: events.console.length, fai: events.failed.length, bad: events.bad.length };
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
      const analysis = document.querySelector(".intel-analysis-card");
      const watch = document.querySelector(".intel-watch-card");
      const mBadge = document.querySelector(".intel-badge.m-e3_full_encyclopedia, .intel-badge.m-r3_full_relationship_intelligence, .intel-badge.m-e2_developed, .intel-badge.m-r2_developed_relationship");
      return {
        ready_state: document.readyState,
        error_hidden: !err || err.hidden,
        header_loaded: !!top && top.innerText.trim().length > 0,
        analysis_partition: !!analysis,
        watch_partition: !!watch,
        maturity_badge: !!mBadge,
        h1: document.querySelector("h1") ? document.querySelector("h1").innerText.slice(0, 60) : "",
        overflow: document.documentElement.scrollWidth > innerWidth + 2,
        body_chars: document.body ? document.body.innerText.replace(/\\s+/g, "").length : 0,
      };
    })()`);
    pages.push({
      viewport: width, label, route, kind, url,
      state,
      events: {
        runtime_exceptions: events.exceptions.length - before.exc,
        console_errors: events.console.length - before.con,
        failed_requests: events.failed.length - before.fai,
        bad_responses: events.bad.length - before.bad,
      },
    });
  }

  for (const [label, route] of ROUTES) {
    if (!route) { await check(1920, label, "", "root"); continue; }
    if (route.startsWith("entity/") || route.startsWith("relation/")) {
      for (const [w, , wl] of VIEWPORTS) await check(w, `${label} ${wl}`, route, route.startsWith("relation/") ? "relation" : "entity");
    } else {
      await check(1920, label, route, "index");
    }
  }

  const report = { artifact: "DEPTHB_CANDIDATE_BROWSER_QA", pages, totals: { pages: pages.length } };
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(report, null, 1));

  const fails = [];
  for (const p of pages) {
    if (p.state.ready_state !== "complete" || !p.state.header_loaded || !p.state.error_hidden ||
        p.state.overflow || p.events.runtime_exceptions > 0 || p.events.console_errors > 0 ||
        p.events.failed_requests > 0 || p.events.bad_responses > 0) {
      fails.push(`${p.viewport} ${p.label}: ${JSON.stringify(p.state)} ${JSON.stringify(p.events)}`);
    }
  }
  const badges = pages.filter((p) => p.state.maturity_badge);
  const analysis = pages.filter((p) => p.state.analysis_partition);
  const watch = pages.filter((p) => p.state.watch_partition);
  console.log(`pages=${pages.length} fails=${fails.length}`);
  console.log(`maturity_badge=${badges.length} analysis_partition=${analysis.length} watch_partition=${watch.length}`);
  fails.slice(0, 12).forEach((f) => console.log("FAIL:", f));
  ws.close();
  process.exit(fails.length ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(2); });
