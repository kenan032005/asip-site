const http = require("http");
const WebSocket = require("ws");
const CDP_PORT = Number(process.env.CDP_PORT || 9229);
const URL = "https://kenan032005.github.io/asip-site/intelligence/africa/entity/fla/";
function getJson(url) { return new Promise((resolve, reject) => { http.get(url, (res) => { let b = ""; res.on("data", x => b += x); res.on("end", () => { try { resolve(JSON.parse(b)); } catch (e) { reject(e); } }); }).on("error", reject); }); }
function wait(ms) { return new Promise(r => setTimeout(r, ms)); }
async function main() {
  const targets = await getJson(`http://127.0.0.1:${CDP_PORT}/json/list`);
  const target = targets.find(x => x.type === "page" && !x.url.startsWith("edge://") && !x.url.startsWith("chrome-extension://") && !x.url.startsWith("devtools://"));
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.once("open", resolve); ws.once("error", reject); });
  let id = 0; const pending = new Map();
  ws.on("message", raw => { const m = JSON.parse(raw.toString()); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m); } });
  const call = (method, params = {}) => new Promise((resolve, reject) => { const i = ++id; pending.set(i, { resolve, reject }); ws.send(JSON.stringify({ id: i, method, params })); });
  const evaluate = async expression => { const r = await call("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }); return r.result && r.result.result ? r.result.result.value : null; };
  await call("Runtime.enable"); await call("Page.enable"); await call("Network.enable"); await call("Network.setCacheDisabled", { cacheDisabled: true });
  await call("Emulation.setDeviceMetricsOverride", { width: 390, height: 900, deviceScaleFactor: 1, mobile: false });
  await call("Page.navigate", { url: URL }); await wait(1500);
  const state = await evaluate(`(() => {
    const iw = innerWidth;
    const offenders = [];
    document.querySelectorAll("*").forEach(function (el) {
      const r = el.getBoundingClientRect();
      if (r.right > iw + 2 || r.left < -2) {
        offenders.push({ tag: el.tagName, cls: (el.className || "").toString().slice(0, 60), text: (el.textContent || "").trim().slice(0, 40), right: Math.round(r.right), left: Math.round(r.left), w: Math.round(r.width) });
      }
    });
    return { inner_width: iw, scroll_width: document.documentElement.scrollWidth, offenders: offenders.slice(0, 12) };
  })()`);
  console.log(JSON.stringify(state, null, 2));
  ws.close();
}
main().catch(e => { console.error(e.stack || e); process.exit(1); });
