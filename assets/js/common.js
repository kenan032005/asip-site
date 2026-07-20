// ASIP shared helpers + header/footer.
// 国家名单、风险等级均从 data/*.json 动态加载，避免多处硬编码。

// 风险等级：低(1)/中(2)/高(3)/极高(4) —— 名称与配色集中定义
const RISK_NAME = { 1: "低风险", 2: "中风险", 3: "高风险", 4: "极高风险" };
const RISK_SHORT = { 1: "低", 2: "中", 3: "高", 4: "极高" };

// 顶部导航严格五项，顺序不可改变
const NAV = [
  ["index.html", "首页"],
  ["events.html", "最新事件"],
  ["countries.html", "国家"],
  ["reports.html", "日报"],
  ["disease-risk.html", "非洲传染病风险"],
];

// 事件类型（与 data/events.json 的 event_type 对齐）
const EVENT_TYPES = [
  "武装冲突", "恐怖袭击", "军事行动", "政变及政治危机",
  "选举及政治活动", "示威、罢工和社会骚乱", "绑架、抢劫和严重犯罪",
  "部族、族群和社区冲突", "边境关闭及跨境风险", "航空、道路、港口和交通中断",
  "油气、矿业、电力和重要基础设施", "自然灾害", "传染病及公共卫生",
  "涉中国企业和公民", "其他重大社会安全事件",
];

// 可信度
const CONFIDENCE = { verified: "已核实", high: "较高可信", pending: "待进一步核实" };
const VERIFY_STATUS = { verified: "已核实", partial: "部分核实", pending: "待进一步核实", unverified: "未经证实" };

function $(sel, root) { return (root || document).querySelector(sel); }
function $all(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

function esc(s) {
  if (s === null || s === undefined) return "";
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function riskBadge(level) {
  const r = Number(level) || 1;
  return `<span class="badge risk-${r}">${RISK_NAME[r] || "低风险"}</span>`;
}
function riskShortBadge(level) {
  const r = Number(level) || 1;
  return `<span class="badge risk-${r}">${RISK_SHORT[r] || "低"}</span>`;
}
function confidenceBadge(c) {
  const key = (c === "已核实") ? "verified" : (c === "较高可信") ? "high" : "pending";
  return `<span class="badge" style="background:#eef2f6;color:#5a6b7b;">可信度：${CONFIDENCE[key]}</span>`;
}
function chinaBadge(ev) {
  if (ev && (ev.china_related || ev.involves_china)) return `<span class="badge" style="background:#ffe0e0;color:#b71c1c;">涉华</span>`;
  return "";
}

// 北京时间换算：底层存储为 UTC，统一 +8 显示为北京时间（UTC+8）
function fmtTimeBJ(s) {
  if (!s) return "";
  s = String(s).trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s; // 纯日期不转换
  const m = s.match(/(\d{4})-(\d{2})-(\d{2})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?/);
  if (!m) return String(s).replace("T", " ").replace("Z", "").slice(0, 16);
  const Y = +m[1], Mo = +m[2] - 1, D = +m[3], h = +m[4], mi = +m[5], se = +(m[6] || 0);
  const ms = Date.UTC(Y, Mo, D, h, mi, se) + 8 * 3600 * 1000;
  return new Date(ms).toISOString().slice(0, 19).replace("T", " ");
}
// 卡片时间：转北京时间后只显示 月-日 时:分
function cardTime(s) {
  if (!s) return "";
  const bj = fmtTimeBJ(s);
  if (/^\d{4}-\d{2}-\d{2}$/.test(bj)) return bj.slice(5);
  const m = bj.match(/(\d{4})-(\d{2})-(\d{2})[ T](\d{1,2}):(\d{2})/);
  return m ? (m[2] + "-" + m[3] + " " + m[4] + ":" + m[5]) : "";
}
function fmtDateTimeBJ(s) {
  const bj = fmtTimeBJ(s);
  return bj ? (bj.slice(5) + "（北京时间）") : "—";
}

// 事件卡片（列表用）
function eventCard(ev, opts) {
  opts = opts || {};
  const url = "event.html?id=" + encodeURIComponent(ev.event_id || ev.id || "");
  const risk = Number(ev.country_risk_level) || Number(ev.risk_level) || 0;
  const riskLabel = `<span class="ec-risk ec-risk-${risk}">${RISK_NAME[risk] || "低风险"}</span>`;
  const tags = [];
  if (ev.country) tags.push(`<span class="ec-tag">${esc(ev.country)}</span>`);
  if (ev.location && ev.location !== ev.country) tags.push(`<span class="ec-tag">${esc(ev.location)}</span>`);
  if (ev.event_type) tags.push(`<span class="ec-tag">${esc(ev.event_type)}</span>`);
  const china = (ev.china_related || ev.involves_china) ? `<span class="ec-tag" style="background:#ffe0e0;color:#b71c1c;">涉华</span>` : "";
  const timeStr = cardTime(ev.published_time || ev.event_time);
  const timeEl = timeStr ? `<span class="ec-time">${timeStr}</span>` : "";
  return `<a class="panel ecard" href="${url}">
    <div class="ec-title">${esc(ev.title_cn || ev.title_original)}</div>
    ${ev.summary_cn ? `<div class="ec-summary">${esc(ev.summary_cn).slice(0, 180)}</div>` : ""}
    <div class="ec-tags">${riskLabel}${tags.join("")}${china}${timeEl}</div>
  </a>`;
}

// ---- 顶部导航 + 页脚 ----
function renderHeader(active) {
  const links = NAV.map(([u, t]) => `<a href="${u}" class="${u === active ? "active" : ""}">${t}</a>`).join("");
  const bar = $("#topbar");
  if (bar) {
    bar.innerHTML = `<div class="top-row">
      <div class="brand"><b>非洲地区社会安全信息平台</b><span>Africa Security Information Platform</span></div>
      <div class="meta" id="topmeta">
        🕐 北京时间 <b id="clBJ">--:--:--</b>
        <span class="muted" id="updLine">更新（北京时间）：<b id="hdrUpdated">--</b></span>
      </div>
    </div>
    <nav class="navbar">${links}</nav>`;
  }
  tickClock();
  if (!window.__clockTimer__) window.__clockTimer__ = setInterval(tickClock, 1000);
  // 载入状态栏（更新时间等）
  API.getCached("status").then(function (st) {
    if (st && st.last_update_bj) setUpdated(st.last_update_bj);
    else if (st && st.generated_at_bj) setUpdated(st.generated_at_bj);
  }).catch(function () {});
}
function tickClock() {
  const bj = $("#clBJ");
  if (!bj) return;
  bj.textContent = new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(11, 19);
}
function setUpdated(s) {
  const m = $("#hdrUpdated");
  if (m && s) m.textContent = s;
}
function renderFooter() {
  const f = document.querySelector("footer.site");
  if (f) f.innerHTML = '非洲地区社会安全信息平台 · 第一阶段框架版 · 数据来源于公开信息，仅供参考，不构成行动或决策依据 · 所有时间均为北京时间（UTC+8）';
}
function showDemoBanner() {
  API.get("status").then(function (st) {
    if (st && st.demo_mode) {
      let b = document.getElementById("demoBanner");
      if (!b) {
        b = document.createElement("div");
        b.id = "demoBanner";
        b.className = "demo-banner";
        b.textContent = "⚠️ 演示模式：当前展示为占位/演示数据，非真实安全事件。正式运行前将替换为经核实的公开信息。";
        const main = document.querySelector(".container") || document.body;
        main.insertBefore(b, main.firstChild);
      }
    }
  }).catch(function () {});
}
function showDbError() {
  const b = document.getElementById("dbError");
  if (b) b.style.display = "block";
}
function getQS(name) { return new URLSearchParams(location.search).get(name); }

document.addEventListener("DOMContentLoaded", function () { renderFooter(); showDemoBanner(); });
