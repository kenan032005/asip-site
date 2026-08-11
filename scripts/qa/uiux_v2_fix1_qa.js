/* UI/UX V2 Fix-1 QA: relation body exact auto-linking.
   Verifies REAL clickable links on 5 key relation pages (not just renderer wiring):
   - body_auto_links_count per page
   - every auto link: canonical resolve, route exists, no wrong target,
     no nested anchor, no broken route
   - autoLinkExact boundary/denylist/URL/ID unit samples
   Outputs: FALSE_POSITIVE_AUTO_LINKS = 0, BROKEN_AUTO_LINKS = 0, RELATION_BODY_REAL_LINKS = PASS */
"use strict";
const ws = require("ws");
const http = require("http");
const fs = require("fs");
const path = require("path");

const CDP = "http://127.0.0.1:9228";
const BASE = "http://127.0.0.1:4174/intelligence/africa/";
const OUT = path.resolve(__dirname, "..", "..", "qa-artifacts-uiux-v2");
const DIST = path.resolve(__dirname, "..", "..", "dist");

const RELATIONS = [
  { key: "shabaab_iss", url: BASE + "relation/expa-shabaab-isis-somalia-rivalry/", label: "Al-Shabaab ↔ ISIS-Somalia" },
  { key: "lakurawa_is_sahel", url: BASE + "relation/d1-lakurawa-is-sahel-network/", label: "Lakurawa ↔ ISIS-Sahel" },
  { key: "aussom_snaf", url: BASE + "relation/expb-aussom-snaf-cooperation/", label: "AUSSOM ↔ SNAF" },
  { key: "adf_updf", url: BASE + "relation/expb-adf-updf-conflict/", label: "ADF/ISIS-CA ↔ UPDF" },
  { key: "sim_bbmb", url: BASE + "relation/expa-sim-bbmb-linked/", label: "SIM ↔ BBMB" },
];

function getTarget() {
  return new Promise((resolve, reject) => {
    http.get(CDP + "/json/list", (res) => {
      let d = "";
      res.on("data", (c) => (d += c));
      res.on("end", () => {
        const list = JSON.parse(d);
        const t = list.find((x) => x.type === "page" && !/^(edge|chrome-extension|devtools):/.test(x.url));
        resolve(t ? t.webSocketDebuggerUrl : null);
      });
    }).on("error", reject);
  });
}
function connect(url) {
  return new Promise((resolve, reject) => {
    const s = new ws(url);
    let id = 0;
    const pending = {};
    s.on("open", () => resolve(send));
    function send(method, params) {
      return new Promise((res, rej) => {
        const mid = ++id;
        pending[mid] = { res, rej };
        s.send(JSON.stringify({ id: mid, method, params: params || {} }));
      });
    }
    s.on("message", (raw) => {
      const m = JSON.parse(raw);
      if (m.id && pending[m.id]) {
        m.error ? pending[m.id].rej(new Error(JSON.stringify(m.error))) : pending[m.id].res(m.result);
        delete pending[m.id];
      }
    });
  });
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function ev(send, expr) {
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) return { __err: String(r.exceptionDetails.exception && r.exceptionDetails.exception.description || r.exceptionDetails.text) };
  return r.result && r.result.value;
}
async function nav(send, url, waitExpr, timeout) {
  await send("Page.navigate", { url });
  const t0 = Date.now();
  while (Date.now() - t0 < (timeout || 10000)) {
    const v = await ev(send, waitExpr);
    if (v) return true;
    await sleep(180);
  }
  return false;
}

function routeExists(href) {
  // href like /intelligence/africa/entity/<slug>/
  const m = href.match(/\/entity\/([^/]+)\/$/);
  if (!m) return { ok: false, reason: "non-entity href: " + href };
  const fp = path.join(DIST, "intelligence", "africa", "entity", m[1], "index.html");
  return { ok: fs.existsSync(fp), reason: "route missing: " + m[1] };
}

async function main() {
  const target = await getTarget();
  const send = await connect(target);
  await send("Runtime.enable"); await send("Page.enable"); await send("Network.enable");
  await send("Network.setCacheDisabled", { cacheDisabled: true });
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

  const pages = [];
  for (const rel of RELATIONS) {
    await nav(send, rel.url, `!!document.querySelector("#relationBody") && !!document.querySelector("#relationParties .relation-party-card")`);
    await sleep(400);
    const data = await ev(send, `(function () {
      var scopes = ["#relationBody", "#relationOverview", "#relationTimeline"];
      var links = [];
      scopes.forEach(function (sel) {
        Array.prototype.forEach.call(document.querySelectorAll(sel + " a.intel-entity-link.auto"), function (a) {
          links.push({ text: a.textContent, href: a.getAttribute("href"), nested: !!a.querySelector("a"), scope: sel });
        });
      });
      var total = links.length;
      var byScope = {};
      scopes.forEach(function (sel) { byScope[sel] = document.querySelectorAll(sel + " a.intel-entity-link.auto").length; });
      // validate against store: canonical resolve + no-wrong-target
      var store = window.ASIP_AFRICA.store;
      var problems = [];
      links.forEach(function (l) {
        var m = l.href.match(/\\/entity\\/([^/]+)\\/$/);
        if (!m) { problems.push({ href: l.href, issue: "non-entity href" }); return; }
        var e = store.byEntitySlug[m[1]] || store.byEntityId[m[1]];
        if (!e) { problems.push({ href: l.href, issue: "unresolved entity" }); return; }
        var names = [e.name_zh, e.name_en, e.acronym || "", e.native_name || ""].concat(e.aliases || []).map(function (x) { return String(x || "").toLowerCase(); });
        if (names.indexOf(l.text.toLowerCase()) < 0) problems.push({ href: l.href, text: l.text, entity: e.entity_id, issue: "wrong target" });
        if (l.nested) problems.push({ href: l.href, text: l.text, issue: "nested anchor" });
      });
      return { total: total, byScope: byScope, problems: problems };
    })()`);
    // node-side route existence check
    const links = await ev(send, `(function () {
      var out = [];
      ["#relationBody", "#relationOverview", "#relationTimeline"].forEach(function (sel) {
        Array.prototype.forEach.call(document.querySelectorAll(sel + " a.intel-entity-link.auto"), function (a) { out.push(a.getAttribute("href")); });
      });
      return out;
    })()`);
    const broken = [];
    links.forEach((h) => { const r = routeExists(h); if (!r.ok) broken.push(r.reason); });
    pages.push({
      key: rel.key, label: rel.label,
      body_auto_links_count: data.total,
      byScope: data.byScope,
      in_page_problems: data.problems,
      broken_routes: broken,
    });
    console.log(rel.label, "-> auto_links:", data.total, "| byScope:", JSON.stringify(data.byScope), "| problems:", data.problems.length, "| broken:", broken.length);
  }

  // ---- unit samples for autoLinkExact (boundary / longest-first / URL / ID / denylist) ----
  const unit = await ev(send, `(function () {
    var A = window.ASIP_AFRICA.autoLinkExact;
    var out = {};
    out.longestFirst = A("ISIS-Somalia 与 ISIS 的关系");
    out.urlProtect = A("UPDF 与 FARDC 联合行动，来源 https://www.updf.go.ug 与 updf.go.ug 官网");
    out.idProtect = A("实体 actor-al-shabaab 与关系 rel-d1-lakurawa-jnim-cooperation");
    out.denyList = A("the 与 in 与 of 不链接");
    out.zhLongest = A("青年党与索马里青年党是同一组织");
    out.aliasLink = A("塞卡·穆萨·巴卢库领导 ADF，而 SIM 在苏丹");
    out.none = A("普通一句话没有任何实体名");
    return out;
  })()`);

  const checks = [];
  const check = (name, pass, detail) => checks.push({ name, pass: !!pass, detail: String(detail || "").slice(0, 200) });

  // per-page real links + no problems
  pages.forEach((p) => {
    check("REAL_LINKS " + p.key, p.body_auto_links_count > 0, "count=" + p.body_auto_links_count);
    check("NO_FALSE_POSITIVE " + p.key, p.in_page_problems.length === 0, JSON.stringify(p.in_page_problems));
    check("NO_BROKEN_ROUTE " + p.key, p.broken_routes.length === 0, JSON.stringify(p.broken_routes));
  });
  // unit assertions
  check("unit longest-first (ISIS-Somalia whole token wins, no ISIS truncation)", unit.longestFirst.indexOf(">ISIS-Somalia</a>") >= 0 && unit.longestFirst.indexOf(">ISIS</a>-Somalia") < 0 && unit.longestFirst.indexOf("entity/isis-somalia") >= 0, unit.longestFirst.slice(0, 170));
  check("unit URL/domain never linked (UPDF entity still links)", unit.urlProtect.indexOf(">UPDF</a>") >= 0 && unit.urlProtect.indexOf(">updf</a>") < 0 && unit.urlProtect.indexOf("updf.go.ug") >= 0 && unit.urlProtect.indexOf(">updf.go.ug</a>") < 0, unit.urlProtect.slice(0, 200));
  check("unit machine ids fully protected (incl. hyphenated)", unit.idProtect.indexOf("actor-al-shabaab") >= 0 && unit.idProtect.indexOf("rel-d1-lakurawa-jnim-cooperation") >= 0 && unit.idProtect.indexOf(">al-shabaab</a>") < 0 && unit.idProtect.indexOf(">lakurawa</a>") < 0, unit.idProtect.slice(0, 200));
  check("unit denylist words not linked", unit.denyList.indexOf("<a ") < 0, unit.denyList);
  check("unit zh longest-first", unit.zhLongest.indexOf(">索马里青年党</a>") >= 0 && unit.zhLongest.indexOf(">青年党</a>") >= 0, unit.zhLongest.slice(0, 120));
  check("unit aliases + acronyms link", unit.aliasLink.indexOf(">ADF</a>") >= 0 && unit.aliasLink.indexOf(">SIM</a>") >= 0 && unit.aliasLink.indexOf(">塞卡·穆萨·巴卢库</a>") >= 0, unit.aliasLink.slice(0, 170));
  check("unit no-name text stays plain", unit.none.indexOf("<a ") < 0, unit.none);

  const failed = checks.filter((c) => !c.pass);
  const totalAuto = pages.reduce((n, p) => n + p.body_auto_links_count, 0);
  const falsePos = pages.reduce((n, p) => n + p.in_page_problems.length, 0);
  const broken = pages.reduce((n, p) => n + p.broken_routes.length, 0);
  const summary = {
    pages: pages.map((p) => ({ key: p.key, label: p.label, body_auto_links_count: p.body_auto_links_count })),
    total_auto_links: totalAuto,
    FALSE_POSITIVE_AUTO_LINKS: falsePos,
    BROKEN_AUTO_LINKS: broken,
    unit_checks_pass: checks.filter((c) => c.pass).length,
    unit_checks_total: checks.length,
    gate: failed.length === 0 && totalAuto > 0 && falsePos === 0 && broken === 0 ? "PASS" : "FAIL",
  };
  fs.writeFileSync(path.join(OUT, "relation-auto-link-fix1-qa.json"), JSON.stringify({ summary, pages, unit, checks }, null, 2));
  console.log("RELATION_BODY_REAL_LINKS gate:", summary.gate, "| total_auto_links:", totalAuto, "| FALSE_POSITIVE:", falsePos, "| BROKEN:", broken, "| checks:", checks.length - failed.length + "/" + checks.length);
  failed.forEach((c) => console.log("  FAIL:", c.name, "::", c.detail));
  process.exit(0);
}
main().catch((e) => { console.error("FIX1 QA FAIL", e); process.exit(1); });
