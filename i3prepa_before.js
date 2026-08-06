// Capture before-fix screenshots from the I2-B baseline server (8785).
const http = require("http");
const fs = require("fs");
const path = require("path");
const getJson = (url) => new Promise((res, rej) => http.get(url, (r) => { let d = ""; r.on("data", (c) => (d += c)); r.on("end", () => { try { res(JSON.parse(d)); } catch (e) { rej(e); } }); }).on("error", rej));
const OUT = path.join(__dirname, "qa-artifacts-i3prepa");
async function main() {
  const list = await getJson("http://127.0.0.1:9224/json/list");
  const page = list.find((t) => t.type === "page");
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0; const pending = new Map();
  const call = (method, params = {}) => new Promise((resolve) => { const mid = ++id; pending.set(mid, resolve); ws.send(JSON.stringify({ id: mid, method, params })); });
  ws.onmessage = (ev) => { const m = JSON.parse(ev.data.toString()); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const evaluate = async (expr) => { const r = await call("Runtime.evaluate", { expression: expr, returnByValue: true }); return r.result && r.result.result ? r.result.result.value : null; };
  await call("Page.enable"); await call("Runtime.enable"); await call("Network.setCacheDisabled", { cacheDisabled: true });
  await call("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
  const spatial = await evaluate("0"); // warm up
  for (const [name, focus] of [["chad", "country-chad"], ["jnim", "actor-jnim"]]) {
    const url = "http://127.0.0.1:8785/intelligence/africa/network/?focus=" + focus;
    await call("Page.navigate", { url });
    await wait(3500);
    const r = await call("Page.captureScreenshot", { format: "png" });
    if (r.result && r.result.data) fs.writeFileSync(path.join(OUT, "before-" + name + ".png"), Buffer.from(r.result.data, "base64"));
    console.log("before shot:", name);
  }
  // also quantify the before layout (same spatial metric)
  await call("Page.navigate", { url: "http://127.0.0.1:8785/intelligence/africa/network/?focus=actor-jnim" });
  await wait(3500);
  const beforeJnim = await evaluate(`(function(){
    const nodes = Array.from(document.querySelectorAll('.graph-node')).filter(function (n) { return !n.classList.contains('is-center'); });
    const cx = 450, cy = 315; const angles = [];
    nodes.forEach(function (n) { const m = n.transform.baseVal.consolidate().matrix; angles.push(Math.atan2(m.f - cy, m.e - cx)); });
    const sorted = angles.slice().sort(function (a, b) { return a - b; });
    let maxGap = 0;
    for (let i = 0; i < sorted.length; i++) { const gap = (sorted[(i + 1) % sorted.length] - sorted[i] + 2 * Math.PI) % (2 * Math.PI); if (gap > maxGap) maxGap = gap; }
    const q = [0, 0, 0, 0];
    angles.forEach(function (a) { const idx = a >= -Math.PI / 4 && a < Math.PI / 4 ? 0 : a >= Math.PI / 4 && a < 3 * Math.PI / 4 ? 1 : a >= 3 * Math.PI / 4 || a < -3 * Math.PI / 4 ? 2 : 3; q[idx]++; });
    return { count: angles.length, quadrants: q, maxShare: Math.max.apply(null, q) / angles.length, maxGapDeg: Math.round(maxGap * 180 / Math.PI) };
  })()`);
  console.log("before jnim layout:", JSON.stringify(beforeJnim));
  fs.writeFileSync(path.join(OUT, "before-layout-metrics.json"), JSON.stringify(beforeJnim, null, 1));
  process.exit(0);
}
main().catch((e) => { console.error("ERR", e); process.exit(1); });
