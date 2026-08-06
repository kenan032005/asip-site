// I3-Prep-A browser QA: 360-degree dispersion, relation visual encoding,
// legend, focus detail entry, non-regression of interactions.
const fs = require("fs");
const http = require("http");
const path = require("path");

const BASE = "http://127.0.0.1:8784";
const CDP_PORT = process.env.CDP_PORT || "9224";
const OUT = path.join(__dirname, "qa-artifacts-i3prepa");
if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => { let d = ""; res.on("data", (c) => (d += c)); res.on("end", () => { try { resolve(JSON.parse(d)); } catch (e) { reject(e); } }); }).on("error", reject);
  });
}

async function main() {
  const version = await getJson("http://127.0.0.1:" + CDP_PORT + "/json/version");
  const list = await getJson("http://127.0.0.1:" + CDP_PORT + "/json/list");
  const page = list.find((t) => t.type === "page");
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  const pending = new Map(); let id = 0;
  const events = { console: [], exceptions: [], failed: [] };
  let currentUrl = "";
  const call = (method, params = {}) => new Promise((resolve) => {
    const messageId = ++id;
    const timer = setTimeout(() => { pending.delete(messageId); resolve({ error: true }); }, 20000);
    pending.set(messageId, (m) => { clearTimeout(timer); resolve(m); });
    ws.send(JSON.stringify({ id: messageId, method, params }));
  });
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data.toString());
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
    if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") events.console.push({ url: currentUrl, a: (m.params.args || []).map((x) => x.value || x.description || "") });
    if (m.method === "Runtime.exceptionThrown") { const u = m.params.exceptionDetails?.url || currentUrl || ""; if (u.startsWith(BASE)) events.exceptions.push({ url: u, d: m.params.exceptionDetails?.exception?.description || m.params.exceptionDetails?.text }); }
    if (m.method === "Network.loadingFailed") events.failed.push({ error: m.params.errorText });
  };
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const evaluate = async (expr) => {
    const r = await call("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    return r.result && r.result.result ? r.result.result.value : null;
  };
  async function navigate(url, vp) {
    currentUrl = url;
    if (vp) await call("Emulation.setDeviceMetricsOverride", { width: vp.w, height: vp.h, deviceScaleFactor: 1, mobile: vp.mobile || false });
    await call("Network.setCacheDisabled", { cacheDisabled: true });
    await call("Page.navigate", { url });
    await wait(900);
    for (let i = 0; i < 60; i++) {
      const ready = await evaluate('document.readyState === "complete" && window.ASIP_AFRICA && window.ASIP_AFRICA.store.entities.length > 0');
      if (ready) break;
      await wait(200);
    }
    await wait(600);
  }
  async function shot(name) { const r = await call("Page.captureScreenshot", { format: "png" }); if (r.result && r.result.data) fs.writeFileSync(path.join(OUT, name + ".png"), Buffer.from(r.result.data, "base64")); }

  // spatial metrics for a focus center: quadrant distribution, angular coverage, centroid offset
  const spatialExpr = `(function(){
    const nodes = Array.from(document.querySelectorAll('.graph-node')).filter(function (n) { return !n.classList.contains('is-center'); });
    const cx = 450, cy = 315;
    const angles = [];
    nodes.forEach(function (n) {
      const m = n.transform.baseVal.consolidate().matrix; const x = m.e; const y = m.f;
      angles.push({ a: Math.atan2(y - cy, x - cx), r: Math.hypot(y - cy, x - cx) });
    });
    if (!angles.length) return null;
    // quadrant counts (0=right,1=bottom,2=left,3=top)
    const q = [0, 0, 0, 0];
    angles.forEach(function (p) { const idx = p.a >= -Math.PI / 4 && p.a < Math.PI / 4 ? 0 : p.a >= Math.PI / 4 && p.a < 3 * Math.PI / 4 ? 1 : p.a >= 3 * Math.PI / 4 || p.a < -3 * Math.PI / 4 ? 2 : 3; q[idx]++; });
    const sorted = angles.map(function (p) { return p.a; }).sort(function (a, b) { return a - b; });
    let maxGap = 0;
    for (let i = 0; i < sorted.length; i++) { const gap = (sorted[(i + 1) % sorted.length] - sorted[i] + 2 * Math.PI) % (2 * Math.PI); if (gap > maxGap) maxGap = gap; }
    // centroid
    let sx = 0, sy = 0;
    angles.forEach(function (p) { sx += cx + Math.cos(p.a) * p.r; sy += cy + Math.sin(p.a) * p.r; });
    const cdx = sx / angles.length - cx, cdy = sy / angles.length - cy;
    const avgR = angles.reduce(function (s, p) { return s + p.r; }, 0) / angles.length;
    return { count: angles.length, quadrants: q, maxQuadrantShare: Math.max.apply(null, q) / angles.length, maxGapDeg: Math.round(maxGap * 180 / Math.PI), centroidOffset: Math.round(Math.hypot(cdx, cdy)), avgRadius: Math.round(avgR), minRadius: Math.round(Math.min.apply(null, angles.map(function (p) { return p.r; }))), maxRadius: Math.round(Math.max.apply(null, angles.map(function (p) { return p.r; }))) };
  })()`;

  const report = { browser: version.Browser, base: BASE, layout: {}, encoding: {}, entry: {}, interactions: {}, viewports: {}, deep: {}, events: {} };

  await call("Page.enable"); await call("Runtime.enable"); await call("Network.enable");
  await call("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });

  // ---- layout dispersion across five centers ----
  for (const [name, focus] of [["chad", "country-chad"], ["jnim", "actor-jnim"], ["iswap", "actor-iswap"], ["sudan", "country-sudan"], ["mozambique", "country-mozambique"]]) {
    await navigate(BASE + "/intelligence/africa/network/?focus=" + focus);
    report.layout[name] = await evaluate(spatialExpr);
    await shot("layout-" + name);
  }

  // ---- relation visual encoding (aggregate across centers) ----
  const allGroups = {};
  const allStrokes = new Set();
  for (const [name, focus] of [["chad", "country-chad"], ["jnim", "actor-jnim"], ["iswap", "actor-iswap"], ["sudan", "country-sudan"], ["mozambique", "country-mozambique"]]) {
    await navigate(BASE + "/intelligence/africa/network/?focus=" + focus);
    const g = await evaluate(`(function(){
      const out = {};
      Array.from(document.querySelectorAll('.graph-edge')).forEach(function (l) {
        const cls = Array.from(l.classList).filter(function (c) { return c !== 'graph-edge'; })[0];
        if (!out[cls]) out[cls] = { count: 0, stroke: null, dash: null };
        out[cls].count++;
        const cs = getComputedStyle(l);
        out[cls].stroke = cs.stroke; out[cls].dash = cs.strokeDasharray;
      });
      return out;
    })()`);
    for (const k in g || {}) { allGroups[k] = g[k]; allStrokes.add(g[k].stroke); }
  }
  report.encoding = {
    groups: allGroups,
    distinctStrokes: allStrokes.size,
    legendText: await evaluate("(function(){var l=document.querySelector('.graph-legend'); return l?l.textContent.replace(/\\s+/g,' ').trim():null;})()"),
    focusLinkHref: await evaluate("(function(){var l=document.querySelector('#focusLink'); return l?l.getAttribute('href'):null;})()"),
    focusLinkText: await evaluate("(function(){var l=document.querySelector('#focusLink'); return l?l.textContent:null;})()"),
    nodeInfoButton: await evaluate("(function(){var n=document.querySelector('#nodeInfo'); var a=n?n.querySelector('a'):null; return a?a.getAttribute('href'):null;})()"),
    nodeInfoHasButton: await evaluate("(function(){var n=document.querySelector('#nodeInfo'); return !!n && !!n.querySelector('a');})()"),
    focusName: await evaluate("(function(){var n=document.querySelector('#focusName'); return n?n.textContent:null;})()")
  };
  await shot("encoding-jnim");

  // ---- center node click -> detail page (country) ----
  await navigate(BASE + "/intelligence/africa/network/?focus=country-chad");
  await evaluate(`(function(){const n=document.querySelector('.graph-node.is-center'); if(n) n.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));})()`);
  await wait(1800);
  const chadLoc = await evaluate("location.href");
  report.entry.countryCenterClick = { url: chadLoc, isCountryPage: (chadLoc || "").indexOf("/intelligence/africa/country/chad/") >= 0, isEntityPage: (chadLoc || "").indexOf("/intelligence/africa/entity/") >= 0 };
  await shot("entry-chad-click");

  // center node click -> detail page (entity)
  await navigate(BASE + "/intelligence/africa/network/?focus=actor-jnim");
  await evaluate(`(function(){const n=document.querySelector('.graph-node.is-center'); if(n) n.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));})()`);
  await wait(1800);
  const jnimLoc = await evaluate("location.href");
  report.entry.entityCenterClick = { url: jnimLoc, isEntityPage: (jnimLoc || "").indexOf("/intelligence/africa/entity/jnim/") >= 0 };
  await shot("entry-jnim-click");

  // peripheral node click still switches focus
  await navigate(BASE + "/intelligence/africa/network/?focus=country-chad");
  await evaluate(`(function(){const n=document.querySelector('.graph-node[data-entity-id="actor-mnjtf"]'); if(n) n.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));})()`);
  await wait(900);
  report.entry.peripheralSwitch = await evaluate(`(function(){return {focusName: document.querySelector('#focusName') ? document.querySelector('#focusName').textContent : null, focusId: document.querySelector('#focusId') ? document.querySelector('#focusId').textContent : null, url: location.href};})()`);
  await shot("entry-peripheral-switch");

  // ---- edge click still opens relation detail ----
  await navigate(BASE + "/intelligence/africa/network/?focus=actor-jnim");
  await evaluate(`(function(){const g=document.querySelector('.graph-edge-group'); if(g) g.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));})()`);
  await wait(500);
  report.interactions.edgeClick = await evaluate(`(function(){const i=document.querySelector('#relationInfo'); return i?i.textContent.replace(/\\s+/g,' ').trim().slice(0,120):null;})()`);
  await shot("edge-click");

  // ---- deep URL refresh ----
  for (const p of ["/intelligence/africa/network/?focus=country-chad", "/intelligence/africa/network/?focus=actor-iswap"]) {
    await navigate(BASE + p);
    report.deep[p] = await evaluate(`(function(){return {nodes: document.querySelectorAll('.graph-node').length, focusName: document.querySelector('#focusName') ? document.querySelector('#focusName').textContent : null};})()`);
  }

  // ---- viewports ----
  for (const [name, vp] of [["1366", { w: 1366, h: 768 }], ["390", { w: 390, h: 844, mobile: true }]]) {
    await navigate(BASE + "/intelligence/africa/network/?focus=country-chad", vp);
    report.viewports[name] = await evaluate(`(function(){return {innerWidth: window.innerWidth, bodyWidth: document.body.scrollWidth, overflow: document.body.scrollWidth > window.innerWidth + 4, nodes: document.querySelectorAll('.graph-node').length};})()`);
    await shot("viewport-" + name);
  }

  report.events = { console: events.console.length, exceptions: events.exceptions.length, failedNonAbort: events.failed.filter((f) => f.error !== "net::ERR_ABORTED").length };
  fs.writeFileSync(path.join(OUT, "browser-qa-results.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  ws.close();
  process.exit(0);
}
main().catch((e) => { console.error("QA ERROR", e); process.exit(1); });
