// ASIP shared helpers + header/footer.
// 国家名单、风险等级均从 data/*.json 动态加载，避免多处硬编码。

// 风险等级：低(1)/中(2)/高(3)/极高(4) —— 名称与配色集中定义
const RISK_NAME = { 1: "低风险", 2: "中风险", 3: "高风险", 4: "极高风险" };
const RISK_SHORT = { 1: "低", 2: "中", 3: "高", 4: "极高" };

// 顶部导航：保留既有五项顺序，仅追加正式安全情报库入口
const NAV = [
  ["index.html", "首页"],
  ["events.html", "最新事件"],
  ["countries.html", "国家"],
  ["reports.html", "日报"],
  ["disease-risk.html", "非洲传染病风险"],
  ["/asip-site/intelligence/africa/", "安全情报库"],
];

// 事件类型 —— Stage-1: 英文枚举代码 → 中文显示（仅此唯一映射表）
// 数据层统一使用英文代码（如 public_health），前端统一通过此表显示中文。
// 未识别类型统一显示「其他安全事件」。
const EVENT_TYPE_CN = {
  "armed_conflict": "武装冲突",
  "terrorist_attack": "恐怖袭击",
  "military_operation": "军事行动",
  "political_crisis": "政治危机",
  "election_security": "选举安全",
  "protest": "抗议示威",
  "strike": "罢工",
  "civil_unrest": "社会动荡",
  "kidnapping": "绑架劫持",
  "serious_crime": "严重刑事犯罪",
  "communal_conflict": "社区及部族冲突",
  "border_security": "边境安全",
  "transport_disruption": "交通中断",
  "infrastructure_security": "基础设施安全",
  "natural_disaster": "自然灾害",
  "public_health": "传染病及公共卫生",
  "china_related": "涉华安全事件",
  "foreign_national_security": "外籍人员安全",
  "policy_security": "安全政策法规",
  "other_security": "其他安全事件",
};
// 中→英逆向映射（兼容旧数据中的中文类型）
const EVENT_TYPE_EN = {};
for (const [k, v] of Object.entries(EVENT_TYPE_CN)) { EVENT_TYPE_EN[v] = k; }

function eventTypeDisplay(raw) {
  // 输入可能是英文代码或旧中文 => 统一返回中文显示
  if (!raw) return "其他安全事件";
  if (EVENT_TYPE_CN[raw]) return EVENT_TYPE_CN[raw];   // 英文代码命中
  if (EVENT_TYPE_EN[raw]) return raw;                   // 旧中文命中
  // 模糊匹配
  for (const [en, cn] of Object.entries(EVENT_TYPE_CN)) {
    if (cn === raw || cn.indexOf(raw) >= 0 || raw.indexOf(cn) >= 0) return cn;
  }
  return "其他安全事件";
}

// 筛选/分组可用的中文标签列表（从映射表值去重生成）
const EVENT_TYPES = [...new Set(Object.values(EVENT_TYPE_CN))].sort();

// 可信度
const CONFIDENCE = { verified: "已核实", high: "较高可信", pending: "待进一步核实" };
const VERIFY_STATUS = { verified: "已核实", partial: "部分核实", pending: "待进一步核实", unverified: "未经证实" };

// 原文语言兜底映射：数据中偶有为英文（English/French…），统一显示为中文
const LANG_MAP = {
  "English": "英语", "english": "英语",
  "French": "法语", "french": "法语",
  "German": "德语", "german": "德语",
  "Spanish": "西班牙语", "spanish": "西班牙语",
  "Italian": "意大利语", "italian": "意大利语",
  "Portuguese": "葡萄牙文", "portuguese": "葡萄牙文",
  "Portuguese (Brazil)": "葡萄牙文",
  "Turkish": "土耳其语", "turkish": "土耳其语",
  "Arabic": "阿拉伯文", "arabic": "阿拉伯文",
  "Russian": "俄文", "russian": "俄文",
  "Chinese": "中文", "chinese": "中文",
};
function langCn(s) { return LANG_MAP[(s || "").trim()] || (s || "—"); }

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
  if (ev.event_type) tags.push(`<span class="ec-tag">${esc(eventTypeDisplay(ev.event_type))}</span>`);
  const china = (ev.china_related || ev.involves_china) ? `<span class="ec-tag" style="background:#ffe0e0;color:#b71c1c;">涉华</span>` : "";
  const timeStr = cardTime(ev.published_time || ev.event_time);
  const timeEl = timeStr ? `<span class="ec-time">${timeStr}</span>` : "";
  return `<a class="panel ecard" href="${url}">
    <div class="ec-title">${esc(ev.title_zh || ev.title_cn || ev.title_original)}</div>
    ${(ev.summary_zh || ev.summary_cn) ? `<div class="ec-summary">${esc(ev.summary_zh || ev.summary_cn).slice(0, 180)}</div>` : ""}
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
  if (f) f.innerHTML = '非洲地区社会安全信息平台 · Stage-1 主链路重建版 · 数据来源于公开信息，仅供参考，不构成行动或决策依据 · 所有时间均为北京时间（UTC+8）<div id="asip-build-meta" style="margin-top:4px;font-size:12px;color:#8899aa;"></div>';
  // 尝试加载 status 以显示 run_id
  if (window.ASIP && window.ASIP.renderFooterMeta) {
    window.ASIP.load('status').then(function(st) {
      window.ASIP.renderFooterMeta(st);
    }).catch(function() {});
  }
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

// ── Stage-2 前端隔离：当前公开事件统一准入（所有当前页面共用，禁止各处分别实现） ──
// 与后端 scripts/pipeline_core.py:is_current_public_event 保持语义一致。
function isCurrentPublicEvent(e) {
  if (!e || typeof e !== "object") return false;
  if (e.current_policy_passed !== true) return false;
  if (e.quality_gate_passed !== true) return false;
  const pub = e.publication_status;
  if (pub !== undefined && pub !== null && pub !== "published" && pub !== "publishable") return false;
  if (e.legacy_migration_preserved === true) return false;
  const eid = e.event_id || "";
  if (!/^EVT_[0-9a-f]{16}$/.test(eid)) return false;
  const country = e.country || e.country_cn || "";
  if (!country) return false;
  const st = e.status || e.event_status || "";
  if (["quarantined", "suppressed", "archived"].indexOf(st) >= 0) return false;
  if (e.quarantined === true) return false;
  return true;
}

// 统一数据访问层：明确区分当前公开事件与历史归档，禁止普通页面直接读 Legacy events.json。
// 所有“当前/最新/今日”模块必须经由下列函数，不得调用 API.get("events") 作为当前事件源。
async function loadCurrentPublishedEvents() {
  // 唯一数据源：Public 公开层（data/public/published_events.json）。
  // 硬性要求：Public 加载失败时宁可返回空数组（页面显示正常空状态），
  // 也绝不回退到 Legacy events.json（data/events.json）。历史迁移内容不得进入当前页面。
  try {
    const data = await API.get("public/published_events");
    const items = Array.isArray(data)
      ? data
      : (Array.isArray(data?.items) ? data.items : []);
    return items.filter(isCurrentPublicEvent);
  } catch (error) {
    console.error("Public 事件数据加载失败", error);
    return [];
  }
}
async function loadLegacyArchiveEvents() {
  // 仅供历史归档功能使用，不进入任何“当前”页面模块。
  try {
    const d = await API.get("public/legacy_archive_events");
    return (d && d.items) ? d.items : [];
  } catch (e) { return []; }
}
function loadLatestSummary() { return API.get("latest-summary"); }
function loadCurrentMetrics() { return API.get("public/current_metrics"); }

// 从当前公开事件列表派生首页三类当前模块（高/最新/涉华）。
function deriveHomeModules(cur) {
  const high = cur.filter(function (e) { return (Number(e.country_risk_level) || 0) >= 3; });
  const latest = cur.slice().sort(function (a, b) {
    return (b.published_time || "").localeCompare(a.published_time || "");
  }).slice(0, 15);
  const china = cur.filter(function (e) { return e.china_related || e.involves_china; });
  return { high: high, latest: latest, china: china };
}

document.addEventListener("DOMContentLoaded", function () { renderFooter(); showDemoBanner(); });
