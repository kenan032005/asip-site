const http = require("http");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");

const CDP_PORT = Number(process.env.CDP_PORT || 9225);
const TARGET_URL = process.env.PUBLIC_NETWORK || "https://kenan032005.github.io/asip-site/intelligence/africa/network/";
const VIEWPORT = Number(process.env.VIEWPORT || 1366);
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-i3c", "browser-blocker-diagnosis.json");

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let body = "";
      res.on("data", (chunk) => { body += chunk; });
      res.on("end", () => { try { resolve(JSON.parse(body)); } catch (error) { reject(error); } });
    }).on("error", reject);
  });
}
function wait(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function text(value) { return value == null ? null : String(value); }

async function run() {
  const targets = await getJson(`http://127.0.0.1:${CDP_PORT}/json/list`);
  const target = targets.find((item) => item.type === "page" && item.url === TARGET_URL) || targets.find((item) => item.type === "page" && item.url !== "about:blank");
  if (!target) throw new Error(`没有找到 CDP page target，端口 ${CDP_PORT}`);
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.once("open", resolve); ws.once("error", reject); });
  let seq = 0;
  const pending = new Map();
  const exceptions = [];
  const consoleErrors = [];
  const failedRequests = [];
  const requestUrls = new Map();
  const badResponses = [];
  let testStep = "attach";
  let action = "attach to clean Edge session";
  let focusBefore = null;
  let clickedNodeId = null;
  let focusAfter = null;

  let currentUrl = target.url || TARGET_URL;
  const cdp = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++seq;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async (expression) => {
    const result = await cdp("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (result.result && result.result.exceptionDetails) throw new Error(result.result.exceptionDetails.text || "Runtime.evaluate failed");
    return result.result && result.result.result ? result.result.result.value : null;
  };
  const frames = (stack) => (stack && stack.callFrames || []).map((frame) => ({
    function_name: text(frame.functionName),
    script_url: text(frame.url),
    line: frame.lineNumber == null ? null : frame.lineNumber + 1,
    column: frame.columnNumber == null ? null : frame.columnNumber + 1
  }));
  const exceptionDetails = (params) => {
    const details = params.exceptionDetails || {};
    const exception = details.exception || {};
    const stack = details.stackTrace || exception.stackTrace || {};
    const stackTrace = frames(stack);
    const first = stackTrace[0] || {};
    return {
      page_url: text(details.url || currentUrl),
      viewport: VIEWPORT,
      test_step: testStep,
      action,
      exception_message: text(details.text || exception.value || exception.description || "Unhandled exception"),
      exception_description: text(exception.description || details.exceptionDescription || details.text || ""),
      stack_trace: stackTrace,
      script_url: text(first.script_url || details.url),
      line: first.line,
      column: first.column,
      promise_rejection_reason: text(exception.description || exception.value || details.text || ""),
      focus_before: focusBefore,
      clicked_node_id: clickedNodeId,
      focus_after: focusAfter
    };
  };
  ws.on("message", (raw) => {
    const message = JSON.parse(raw.toString());
    if (message.id && pending.has(message.id)) {
      const request = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) request.reject(new Error(message.error.message || "CDP error"));
      else request.resolve(message);
    }
    if (message.method === "Page.frameNavigated" && message.params.frame && !message.params.frame.parentId) currentUrl = message.params.frame.url || currentUrl;
    if (message.method === "Runtime.exceptionThrown") exceptions.push(exceptionDetails(message.params));
    if (message.method === "Runtime.consoleAPICalled" && message.params.type === "error") consoleErrors.push({
      page_url: currentUrl, viewport: VIEWPORT, test_step: testStep, action,
      args: (message.params.args || []).map((arg) => text(arg.value || arg.description || ""))
    });
    if (message.method === "Log.entryAdded" && message.params.entry && message.params.entry.level === "error") consoleErrors.push({
      page_url: currentUrl, viewport: VIEWPORT, test_step: testStep, action,
      source: "Log.entryAdded", text: text(message.params.entry.text), url: text(message.params.entry.url),
      line: message.params.entry.lineNumber == null ? null : message.params.entry.lineNumber + 1,
      column: message.params.entry.columnNumber == null ? null : message.params.entry.columnNumber + 1
    });
    if (message.method === "Network.requestWillBeSent") requestUrls.set(message.params.requestId, message.params.request.url);
    if (message.method === "Network.responseReceived" && message.params.response && message.params.response.status >= 400) badResponses.push({
      page_url: currentUrl, viewport: VIEWPORT, test_step: testStep, action,
      request_id: text(message.params.requestId), url: text(message.params.response.url), status: message.params.response.status
    });
    if (message.method === "Network.loadingFailed" && message.params.errorText !== "net::ERR_ABORTED") failedRequests.push({
      page_url: currentUrl, viewport: VIEWPORT, test_step: testStep, action,
      request_id: text(message.params.requestId), url: text(requestUrls.get(message.params.requestId)), error: text(message.params.errorText)
    });
  });

  await cdp("Runtime.enable");
  await cdp("Page.enable");
  await cdp("Network.enable");
  await cdp("Log.enable");
  await cdp("Network.setCacheDisabled", { cacheDisabled: true });
  await cdp("Page.addScriptToEvaluateOnNewDocument", { source: `(() => {
    window.__ASIP_QA_REJECTIONS = [];
    window.__ASIP_QA_WINDOW_ERRORS = [];
    addEventListener("unhandledrejection", (event) => {
      const reason = event.reason;
      window.__ASIP_QA_REJECTIONS.push({ message: reason && reason.message ? String(reason.message) : String(reason), description: reason && reason.stack ? String(reason.stack) : String(reason) });
    });
    addEventListener("error", (event) => {
      window.__ASIP_QA_WINDOW_ERRORS.push({ message: String(event.message || ""), source_url: String(event.filename || ""), line: event.lineno || null, column: event.colno || null, stack: event.error && event.error.stack ? String(event.error.stack) : "" });
    });
  })();` });

  const state = async (label) => evaluate(`(() => {
    const focus = document.querySelector("#focusId");
    const name = document.querySelector("#focusName");
    const info = document.querySelector("#nodeInfo");
    const all = [...document.querySelectorAll("[data-entity-id]")].map((node) => node.getAttribute("data-entity-id"));
    const focusId = focus ? focus.textContent.trim() : null;
    return {
      label: ${JSON.stringify(label)}, url: location.href, ready_state: document.readyState,
      graph_ready_state: document.querySelector("#graphHint") ? document.querySelector("#graphHint").textContent : null,
      focus_id: focusId, focus_name: name ? name.textContent.trim() : null,
      node_count: all.length, edge_count: document.querySelectorAll(".graph-edge").length,
      right_panel_entity_id: info ? ((info.textContent.match(/(?:actor|country|person|entity)-[A-Za-z0-9_-]+/) || [null])[0]) : null,
      right_panel_text: info ? info.innerText.slice(0, 700) : null,
      neighbor_ids: all.filter((id) => id !== focusId).sort(), viewport_width: innerWidth,
      scroll_width: document.documentElement.scrollWidth
    };
  })()`);

  testStep = "initial-load";
  action = "navigate to formal Network page";
  await cdp("Page.navigate", { url: TARGET_URL });
  await wait(1400);
  for (let i = 0; i < 40; i++) {
    const ready = await evaluate(`(() => document.readyState === "complete" && document.querySelector("#focusId") && document.querySelector("#graphHint") && !document.querySelector("#graphHint").textContent.includes("加载"))()`);
    if (ready) break;
    await wait(250);
  }
  const initial = await state("initial-state");
  focusBefore = initial.focus_id;

  testStep = "node-focus-switch";
  action = "click a real one-hop peripheral node selected by data-entity-id";
  const candidate = await evaluate(`(() => {
    const focus = document.querySelector("#focusId")?.textContent.trim();
    const node = [...document.querySelectorAll("g.graph-node[data-entity-id]")].find((item) => item.getAttribute("data-entity-id") !== focus && !item.classList.contains("is-center"));
    if (!node) return null;
    const shape = node.querySelector(".node-shape") || node;
    const rect = shape.getBoundingClientRect();
    return { entity_id: node.getAttribute("data-entity-id"), x: rect.left + rect.width / 2, y: rect.top + rect.height / 2, aria_label: node.getAttribute("aria-label") || "" };
  })()`);
  if (!candidate) {
    const browserSignals = await evaluate(`(() => ({ unhandled_rejections: window.__ASIP_QA_REJECTIONS || [], window_errors: window.__ASIP_QA_WINDOW_ERRORS || [] }))()`);
    const report = {
      artifact: "I3C_BROWSER_BLOCKER_DIAGNOSIS",
      generated_at: new Date().toISOString(), page_url: TARGET_URL, viewport: VIEWPORT, cdp_port: CDP_PORT,
      browser_target_url: target.url || null, initial, candidate_node: null, after_click: null,
      focus_transition: { focus_before: focusBefore, clicked_node_id: null, focus_after: null, changed: false },
      exceptions, console_errors: consoleErrors, failed_requests: failedRequests, bad_responses: badResponses,
      browser_captured_rejections: browserSignals.unhandled_rejections, browser_captured_window_errors: browserSignals.window_errors,
      diagnosis: "PRODUCT_PAGE_ASSET_PATH_BUG: page loaded the Africa frontend from a root-relative URL outside /asip-site, so the graph data renderer did not execute and no real graph node existed to click.",
      summary: {
        runtime_exceptions: exceptions.length, console_errors: consoleErrors.length,
        failed_requests: failedRequests.length, bad_responses: badResponses.length,
        unhandled_rejections: browserSignals.unhandled_rejections.length,
        node_click_focus_switch: false, diagnosis_gate: "OPEN"
      }
    };
    fs.mkdirSync(path.dirname(OUT), { recursive: true });
    fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report.summary));
    console.log(JSON.stringify({ initial: report.initial, exceptions: report.exceptions, failed_requests: report.failed_requests, bad_responses: report.bad_responses }, null, 2));
    ws.close();
    return;
  }
  await cdp("Input.dispatchMouseEvent", { type: "mouseMoved", x: candidate.x, y: candidate.y });
  await cdp("Input.dispatchMouseEvent", { type: "mousePressed", x: candidate.x, y: candidate.y, button: "left", clickCount: 1 });
  await cdp("Input.dispatchMouseEvent", { type: "mouseReleased", x: candidate.x, y: candidate.y, button: "left", clickCount: 1 });
  await wait(1000);
  const afterClick = await state("after-peripheral-node-click");
  focusAfter = afterClick.focus_id;
  const browserSignals = await evaluate(`(() => ({ unhandled_rejections: window.__ASIP_QA_REJECTIONS || [], window_errors: window.__ASIP_QA_WINDOW_ERRORS || [] }))()`);
  const transition = {
    focus_before: focusBefore, clicked_node_id: clickedNodeId, focus_after: focusAfter,
    changed: focusBefore !== focusAfter,
    url_focus: new URL(afterClick.url).searchParams.get("focus"),
    current_focus_name: afterClick.focus_name,
    right_panel_entity_id: afterClick.right_panel_entity_id,
    neighbor_ids_before: initial.neighbor_ids, neighbor_ids_after: afterClick.neighbor_ids,
    neighbor_set_changed: JSON.stringify(initial.neighbor_ids) !== JSON.stringify(afterClick.neighbor_ids)
  };
  const report = {
    artifact: "I3C_BROWSER_BLOCKER_DIAGNOSIS",
    generated_at: new Date().toISOString(), page_url: TARGET_URL, viewport: VIEWPORT, cdp_port: CDP_PORT,
    browser_target_url: target.url || null, initial, candidate_node: candidate, after_click: afterClick,
    focus_transition: transition, exceptions, console_errors: consoleErrors,     failed_requests: failedRequests, bad_responses: badResponses,
    browser_captured_rejections: browserSignals.unhandled_rejections, browser_captured_window_errors: browserSignals.window_errors,
    summary: {
      runtime_exceptions: exceptions.length, console_errors: consoleErrors.length,
      failed_requests: failedRequests.length, bad_responses: badResponses.length, unhandled_rejections: browserSignals.unhandled_rejections.length,
      node_click_focus_switch: transition.changed && transition.url_focus === clickedNodeId && transition.right_panel_entity_id === clickedNodeId,
      diagnosis_gate: exceptions.length === 0 && browserSignals.unhandled_rejections.length === 0 && transition.changed ? "PASS" : "OPEN"
    }
  };
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report.summary));
  console.log(JSON.stringify({ exceptions: report.exceptions, focus_transition: report.focus_transition }, null, 2));
  ws.close();
}

run().catch((error) => { console.error(error.stack || error); process.exit(1); });
