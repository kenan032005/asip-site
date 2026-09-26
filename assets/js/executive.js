/* ============================================================
   ASIP C7-2 — Executive Intelligence Dashboard（领导 30 秒视图）
   数据源：data/views/executive_summary.json（executive-summary-v1）
   ------------------------------------------------------------
   内容为**确定性事实汇总**（构建器 scripts/ops/executive_view.py，
   无 AI 生成）。文案保持中性："安全态势概览 / 近期重点动态 /
   最新情报流"。**不得标注为 AI 研判**——AI 研判留待 C7-3 引入
   正式每日评估后再使用该措辞。
   加载失败时降级为"态势摘要暂不可用"，不阻断首页其余模块。
   ============================================================ */
(function () {
  "use strict";

  var VIEW = "views/executive_summary";
  // 与 news-stream.js 相同的候选路径模式（canonical 路径优先）
  var CANDIDATES = [
    "data/views/executive_summary.json",
    "views/executive_summary.json",
    "data/executive_summary.json"
  ];

  var RISK_CN = { worsening: "趋于恶化", stable: "总体平稳", improving: "有所改善" };
  var RISK_CLS = { worsening: "is-worse", stable: "is-flat", improving: "is-better" };
  var CONF_CN = { high: "高", medium: "中", low: "低" };
  var DIR_ARROW = { up: "▲", flat: "▬", down: "▼" };
  var DIR_CLS = { up: "is-up", flat: "is-flat", down: "is-down" };
  var DIR_CN = { up: "活跃度上升", flat: "活跃度持平", down: "活跃度回落" };

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function shortTime(s) {
    var m = String(s || "").match(/(\d{4})-(\d{2})-(\d{2})[T ](\d{2}:\d{2})/);
    return m ? (m[2] + "-" + m[3] + " " + m[4]) : esc(s || "—");
  }

  function loadView() {
    var i = 0;
    function tryNext() {
      if (i >= CANDIDATES.length) return Promise.reject(new Error("executive_summary 不可用"));
      var name = CANDIDATES[i++];
      return window.API.get(name.replace(/\.json$/, "")).catch(function () {
        // API.get 的相对路径解析对子路径视图可能命中错误目录，逐个候选回退
        return fetch(CANDIDATES[i - 1], { credentials: "same-origin" }).then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        });
      }).catch(tryNext);
    }
    return tryNext();
  }

  function setBusy(host, msg) {
    var el = document.getElementById(host);
    if (el) el.innerHTML = '<div class="exec-busy">' + esc(msg || "加载中…") + "</div>";
  }

  /* ── 模块 1：安全态势概览 ─────────────────────────────── */
  function renderOverview(d) {
    var host = document.getElementById("execOverview");
    if (!host) return;
    var wrap = document.getElementById("execOverviewWrap");
    var a = d.assessment || {};
    var isAI = a.status === "ai" && String(a.overall_assessment || "").trim() !== "";
    var text = isAI ? a.overall_assessment
                    : (d.overall_assessment || "暂无足够的公开信息形成稳定研判。");
    var gen = shortTime(isAI ? (a.generated_time || d.generated_time) : d.generated_time);
    var risk = RISK_CN[(isAI ? a.risk_direction : d.risk_direction)] || "—";
    var conf = CONF_CN[(isAI ? a.confidence : d.confidence)] || "—";
    if (wrap) {  // 标签随内容来源切换：确定性内容绝不标注为 AI
      var h = wrap.querySelector(".exec-card-h h2");
      var en = wrap.querySelector(".exec-card-en");
      if (h) h.textContent = isAI ? "AI 安全态势研判" : "非洲安全态势概览";
      if (en) en.textContent = isAI ? "AI SECURITY ASSESSMENT"
                                    : "AFRICA SECURITY SITUATION OVERVIEW";
    }
    var p = d.period || {};
    host.innerHTML =
      '<div class="exec-assess">' + esc(text) + "</div>" +
      '<div class="exec-chips">' +
        '<span class="exec-chip"><b>' + Number(p.events_24h || 0) + "</b>24h 事件</span>" +
        '<span class="exec-chip"><b>' + Number(p.events_7d || 0) + "</b>7d 事件</span>" +
        '<span class="exec-chip"><b>' + Number(p.active_countries_24h || 0) + "</b>24h 活跃国家</span>" +
        '<span class="exec-chip"><b>' + Number(p.active_countries_7d || 0) + "</b>7d 活跃国家</span>" +
      "</div>" +
      '<div class="exec-meta">' +
        '<span class="exec-pill ' + (RISK_CLS[d.risk_direction] || "") + '">风险方向：' + esc(risk) + "</span>" +
        '<span class="exec-pill">数据置信度：' + esc(conf) + "</span>" +
        (isAI ? '<span class="exec-pill is-ai">基于' + esc(a.based_on || "过去24小时/7日公开信息") + "</span>" : "") +
        '<span class="exec-update">更新于 ' + esc(gen) + '</span>' +
      "</div>";
  }

  /* ── 模块 2：重点区域与热点 ───────────────────────────── */
  function renderRegions(d) {
    var host = document.getElementById("execRegions");
    if (!host) return;
    var rows = (d.key_regions || []).slice(0, 5);
    if (!rows.length) { host.innerHTML = '<div class="exec-empty">暂无区域热点数据</div>'; return; }
    host.innerHTML = rows.map(function (r) {
      var dir = DIR_ARROW[r.direction] || "▬";
      return '<div class="exec-region-row">' +
        '<span class="exec-dir ' + (DIR_CLS[r.direction] || "") + '" title="' + esc(DIR_CN[r.direction] || "") + '">' + dir + "</span>" +
        '<span class="exec-region-name">' + esc(r.country) + "</span>" +
        '<span class="exec-region-n"><b>' + Number(r.events_24h || 0) + "</b>24h · <b>" + Number(r.events_7d || 0) + "</b>7d</span>" +
        '<span class="exec-region-note">' + esc(r.note || "") + "</span>" +
      "</div>";
    }).join("");
  }

  /* ── 模块 3：近期重点动态（复用既有事件详情路由） ───────── */
  function renderTop(d) {
    var host = document.getElementById("execTop");
    if (!host) return;
    var rows = (d.top_events || []).slice(0, 5);
    if (!rows.length) { host.innerHTML = '<div class="exec-empty">近 7 日暂无公开事件记录；无记录不等于无风险</div>'; return; }
    host.innerHTML = rows.map(function (e) {
      var link = e.event_id ? "event.html?id=" + encodeURIComponent(e.event_id) : "events.html";
      var sev = String(e.severity || "").toLowerCase();
      return '<a class="exec-top-row sev-' + esc(sev || "na") + '" href="' + link + '">' +
        '<span class="exec-top-country">' + esc(e.country) + "</span>" +
        '<span class="exec-top-main"><b>' + esc(e.title || "（无标题）") + "</b>" +
          '<i>' + esc((e.summary || "").slice(0, 90) + ((e.summary || "").length > 90 ? "…" : "")) + "</i></span>" +
        '<span class="exec-top-meta"><em>' + esc(shortTime(e.time)) + "</em>" +
          '<u title="独立来源数">' + Number(e.source_count || 0) + " 源</u></span>" +
      "</a>";
    }).join("");
  }

  /* ── 模块 4：最新情报流（未翻译条目诚实标注原文） ───────── */
  function renderFeed(d) {
    var host = document.getElementById("execFeed");
    if (!host) return;
    var rows = (d.latest_intelligence || []).slice(0, 8);
    if (!rows.length) { host.innerHTML = '<div class="exec-empty">暂无新到情报条目</div>'; return; }
    host.innerHTML = rows.map(function (n) {
      var title = String(n.title || "").trim();
      var tr = n.translated === true
        ? ""
        : '<u class="exec-orig" title="该条目暂无中文译文，显示原文">原文 Original</u>';
      return '<div class="exec-feed-row">' +
        '<span class="exec-feed-main"><b>' + esc(title || "（无标题）") + "</b>" + tr +
          '<i>' + esc(n.security_category || "未分类") + " ｜ " + esc(n.source || "未知来源") + "</i></span>" +
        '<span class="exec-feed-side"><em>' + esc(n.country || "未识别") + "</em>" +
          "<em>" + esc(shortTime(n.time)) + "</em></span>" +
      "</div>";
    }).join("");
  }

  function renderAll(d) {
    renderOverview(d); renderRegions(d); renderTop(d); renderFeed(d);
  }

  function failAll() {
    ["execOverview", "execRegions", "execTop", "execFeed"].forEach(function (id) {
      setBusy(id, "态势摘要暂不可用");
    });
  }

  function init() {
    ["execOverview", "execRegions", "execTop", "execFeed"].forEach(function (id) {
      setBusy(id, "加载中…");
    });
    loadView().then(renderAll).catch(function (e) {
      if (window.console && console.warn) console.warn("[executive] 视图加载失败：", e);
      failAll();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
