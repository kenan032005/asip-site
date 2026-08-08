const http = require("http");
const WebSocket = require("ws");
const CDP_PORT = Number(process.env.CDP_PORT || 9233);
const URL = "https://kenan032005.github.io/asip-site/intelligence/africa/entity/jnim/";
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
  // hard reload with bypass
  await call("Page.navigate", { url: URL });
  await wait(2500);
  const state = await evaluate(`(() => {
    const scripts = [...document.querySelectorAll("script[src]")].map(s => s.src);
    const links = [...document.querySelectorAll("link[rel=stylesheet]")].map(l => l.href);
    const analysis = document.querySelector(".intel-analysis-card");
    const hasNewCode = typeof maturityBadge !== "undefined";
    return { scripts, links, analysis_present: !!analysis, window_maturity: hasNewCode, body_has_analysis_text: document.body ? document.body.innerText.includes("ASIP Analysis") : false };
  })()`);
  console.log(JSON.stringify(state, null, 2));
  ws.close();
}
main().catch(e => { console.error(e.stack || e); process.exit(1); });
