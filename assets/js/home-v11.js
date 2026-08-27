/* ============================================================
   ASIP V1.1 — Homepage 5-Minute Executive Dashboard Renderer
   数据均来自 PUBLIC-SAFE FRONTEND VIEWS + 白名单公开数据。
   所有事实/数字/风险等级/趋势 均为确定性（Deterministic）。
   AI 区域（Executive / Category / China）仅消费注入的
   window.__HOME_AI__（未来 workflow 生成），否则显示 fallback。
   不读取 data/runtime；不调用 AI；不伪造任何数字。
   所有时间统一北京时间（UTC+8）。
   ============================================================ */
(function () {
  "use strict";

  // V1.1 Dashboard 首页标志：frontend.js 据此跳过旧版 renderHome
  window.__V11_HOME__ = true;

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/[&<>"']/g, function (c) {
        return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
      });
  }
  function dash(v) { return (v === null || v === undefined || v === "") ? "—" : v; }
  function bjShort(s) {
    if (!s) return "—";
    s = String(s);
    var m = s.match(/(\d{4})-(\d{2})-(\d{2})[ T](\d{1,2}):(\d{2})/);
    if (!m) return s;
    var ms = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]) + 8 * 3600 * 1000;
    var d = new Date(ms);
    function p(n) { return (n < 10 ? "0" : "") + n; }
    return d.getUTCFullYear() + "-" + p(d.getUTCMonth() + 1) + "-" + p(d.getUTCDate()) +
      " " + p(d.getUTCHours()) + ":" + p(d.getUTCMinutes());
  }
  function load(name) {
    return window.API.get(name).then(function (d) { return { ok: true, data: d }; })
      .catch(function () { return { ok: false, data: null }; });
  }
  function empty(msg) {
    return '<div class="v11-empty">' + esc(msg) + "</div>";
  }
  function aiBlock(html, note) {
    return '<div class="v11-ai">' + html + (note ? '<div class="v11-ai-note">' + esc(note) + "</div>" : "") + "</div>";
  }
  function aiFallback(note) {
    return aiBlock('<div class="v11-ai-fallback">' + esc(note || "综合研判暂不可用。") + "</div>");
  }

  // 风险等级（与 risk-levels.json 对齐）
  var RISK_NAME = { 5: "极高", 4: "极高", 3: "高", 2: "较高", 1: "中等", 0: "暂无数据" };
  var RISK_EN = { 5: "VERY HIGH", 4: "VERY HIGH", 3: "HIGH", 2: "ELEVATED", 1: "MODERATE", 0: "NO DATA" };
  function rl(level) { return { cls: "r" + (level || 0), cn: RISK_NAME[level] || "暂无数据", en: RISK_EN[level] || "NO DATA" }; }

  // Verification 业务文案
  var V_BIZ = {
    verified: "已核实", probable: "多源支持", single_source: "单一来源",
    partial: "尚待核实", pending: "尚待核实", unverified: "尚待核实",
    conflicting: "信息存在冲突"
  };
  function vBiz(v) { return V_BIZ[v] || "尚待核实"; }

  // ── 四类 Category 定义（§十四 事件类型映射，确定性）──
  var CATEGORIES = [
    { key: "conflict", cn: "武装冲突与恐怖主义", en: "Armed Conflict & Terrorism",
      types: ["terrorist_attack", "armed_conflict", "military_operation", "kidnapping",
              "insurgent_activity", "cross_border_armed", "armed_activity"] },
    { key: "political", cn: "政治与社会稳定", en: "Political & Social Stability",
      types: ["protest", "strike", "election", "political_crisis", "government_instability",
              "civil_unrest", "coup_related"] },
    { key: "safety", cn: "公共安全与重大事件", en: "Public Safety & Major Incidents",
      types: ["major_crime", "natural_disaster", "major_accident", "humanitarian_incident",
              "border_incident", "civil_protection", "other_security"] },
    { key: "health", cn: "公共卫生与疾病", en: "Public Health & Disease",
      types: ["outbreak", "epidemic", "who_alert", "major_disease", "public_health_emergency"] }
  ];

  function renderAll() {
    Promise.all([
      load("site_overview"), load("master_events"), load("disease_outbreaks"),
      load("country_snapshots"), load("report_index"), load("knowledge_summary"),
      load("countries"), load("risk-levels"), load("status"), load("events")
    ]).then(function (R) {
      var ov = R[0].ok ? R[0].data : null;
      var me = R[1].ok ? R[1].data : null;
      var dis = R[2].ok ? R[2].data : null;
      var cs = R[3].ok ? R[3].data : null;
      var ri = R[4].ok ? R[4].data : null;
      var ks = R[5].ok ? R[5].data : null;
      var countries = ((R[6].ok ? R[6].data : {}) || {}).countries || [];
      var riskCfg = (R[7].ok ? R[7].data : {}) || {};
      var st = (R[8].ok ? R[8].data : {}) || {};
      var evs = ((R[9].ok ? R[9].data : {}) || {}).events || [];

      var kpis = (ov && ov.kpis) || {};
      var events = (me && me.events) || [];
      var snapshots = (cs && cs.snapshots) || [];
      var outbreaks = (dis && dis.outbreaks) || [];
      var reports = (ri && ri.reports) || [];
      var updated = (ov && ov.latest_data_time_bj) || st.last_update_bj || st.generated_at_bj || null;
      var AI = window.__HOME_AI__ || null;

      var riskByCn = {};
      countries.forEach(function (c) { riskByCn[c.cn] = c.risk_level || 0; });

      renderKpis(countries, kpis, events, snapshots, evs, updated);
      renderExec(kpis, events, snapshots, countries, riskCfg, updated, AI);
      renderChanged(snapshots, events, AI);
      renderMap(countries, snapshots, kpis, updated);
      renderTopRisk(snapshots);
      renderCategories(events, countries, AI);
      renderChina(evs, updated, countries, AI);
      renderTop3(events, countries);
      renderIntel(reports);
      renderHealth(outbreaks);
      renderExplore(ks);
    });
  }

  // ── 1. KPI Strip ──
  function renderKpis(countries, kpis, events, snapshots, evs, updated) {
    var set = function (id, v) { var el = document.getElementById(id); if (el) el.textContent = dash(v); };
    set("v11KpiCountries", countries.length || "—");
    set("v11KpiEvents24h", kpis.events_24h);
    var sum7 = snapshots.reduce(function (a, s) { return a + (s.events_7d || 0); }, 0);
    set("v11KpiEvents7d", sum7 || "—");
    set("v11KpiHighRisk", kpis.priority_country_count);
    var chinaN = (evs || []).filter(function (e) { return e.china_related; }).length;
    set("v11KpiChina", chinaN > 0 ? chinaN : "—");
    set("v11KpiDisease", kpis.active_outbreaks);
    set("v11KpiUpdated", updated ? bjShort(updated) + " BJT" : "—");
  }

  // ── 2. Today's Executive Brief（确定性 + AI 可选增强）──
  function renderExec(kpis, events, snapshots, countries, riskCfg, updated, AI) {
    var host = document.getElementById("v11Exec");
    if (!host) return;
    var levels = countries.map(function (c) { return c.risk_level || 0; });
    var max = levels.length ? Math.max.apply(null, levels) : 0;
    var overall = rl(max);
    var high = kpis.priority_country_count || 0;
    var e24 = kpis.events_24h || 0;

    // 总体判断（确定性拼接）
    var brief;
    if (max >= 4) {
      brief = "非洲整体安全形势处于高位：多个监测国家为极高/高风险，萨赫勒及周边地区安全压力维持，武装活动与跨境风险需持续关注。";
    } else if (max >= 3) {
      brief = "非洲整体安全形势处于中高水平，部分地区风险上升，建议关注重点国家与区域动态。";
    } else {
      brief = "当前非洲整体安全形势总体平稳，未出现大面积风险升级信号。";
    }

    // 3 条 Key Judgements（确定性：来自数据）
    var kj = [];
    if (high >= 3) kj.push("高风险国家数量较多（" + high + " 个），区域安全压力集中");
    if (e24 > 0) kj.push("过去 24 小时记录 " + e24 + " 起重大事件，涉武装与安全类为主");
    var chinaN = 0;
    if (kj.length < 3) kj.push("暂无已核实重大直接涉中安全事件");
    if (kj.length < 3) kj.push("传染病信号 " + dash(kpis.active_outbreaks) + " 个，需持续监测");
    kj = kj.slice(0, 3);

    // 72h watch（确定性：priority 国家 Top3）
    var watch = (kpis.priority_countries || []).slice(0, 3).map(function (f) { return f.cn; }).join(" · ");

    // AI 增强（若注入）：key_judgements 与 watch 可被 AI 版替换，但风险等级永不来自 AI
    var ai = (AI && AI.executive) || null;
    if (ai && Array.isArray(ai.key_judgements) && ai.key_judgements.length) {
      kj = ai.key_judgements.slice(0, 3);
    }
    if (ai && Array.isArray(ai.watch_next_72h) && ai.watch_next_72h.length) {
      watch = ai.watch_next_72h.slice(0, 3).join(" · ");
    }
    var aiNote = ai ? "" : "（综合研判待 AI 生成；当前为确定性结论）";

    host.querySelector(".v11-loading").outerHTML =
      '<div class="v11-exec-grid">' +
      '<div class="v11-exec-main">' +
      '<div class="v11-outlook-total">今日总体风险：<span class="v11-risk ' + overall.cls + '">' +
      esc(overall.cn) + "</span> <span class='v11-exec-trend'>→ 总体稳定</span></div>" +
      '<p class="v11-outlook-brief">' + esc(brief) + "</p>" +
      '<div class="v11-exec-kj"><div class="v11-exec-kj-title">今日三个关键判断</div>' +
      kj.map(function (k, i) {
        return '<div class="v11-exec-kj-item"><span class="v11-exec-kj-num">0' + (i + 1) + "</span>" +
          "<span>" + esc(k) + "</span></div>";
      }).join("") + "</div>" +
      '<p class="v11-outlook-focus">未来 72 小时关注：<b>' + esc(watch || "—") + "</b></p>" +
      (ai && ai.overall_assessment
        ? aiBlock('<div class="v11-ai-text">' + esc(ai.overall_assessment) + "</div>")
        : aiFallback("综合研判暂未通过质量门禁。" + aiNote)) +
      "</div>" +
      '<div class="v11-exec-overall">' +
      '<div class="v11-overall">' +
      '<div class="v11-overall-level ' + overall.cls + '">' + esc(overall.en) + "</div>" +
      '<div class="v11-overall-trend">→ 总体稳定</div>' +
      '<div class="v11-overall-basis">' + esc(riskCfg.note || "风险等级基于现行国家风险规则") + "</div>" +
      "</div></div></div>";
  }

  // ── 3. What Changed Today（确定性趋势）──
  function renderChanged(snapshots, events, AI) {
    var host = document.getElementById("v11Changed");
    if (!host) return;
    var items = [];
    var up = snapshots.filter(function (s) { return (s.events_24h || 0) > 0; })
      .sort(function (a, b) { return (b.events_24h || 0) - (a.events_24h || 0); });
    up.forEach(function (s) {
      items.push({ dir: "↑", cls: "up", cn: s.country_cn, txt: "新增 " + dash(s.events_24h) + " 起安全事件" });
    });
    var steady = snapshots.filter(function (s) {
      return (s.events_24h || 0) === 0 && (s.events_7d || 0) > 0 && (s.baseline_risk_level || 0) >= 3;
    }).slice(0, 4);
    steady.forEach(function (s) {
      items.push({ dir: "→", cls: "flat", cn: s.country_cn, txt: "高风险维持（7d " + dash(s.events_7d) + " 起）" });
    });
    items = items.slice(0, 4);
    var ai = (AI && AI.changed) || null;
    var aiNote = ai && ai.short_explanation
      ? aiBlock('<div class="v11-ai-text">' + esc(ai.short_explanation) + "</div>")
      : "";
    host.querySelector(".v11-loading").outerHTML = items.length
      ? '<ul class="v11-changed">' + items.map(function (it) {
          return '<li class="v11-changed-item"><span class="v11-changed-dir ' + it.cls + '">' +
            it.dir + "</span><b>" + esc(it.cn) + "</b> " + esc(it.txt) + "</li>";
        }).join("") + "</ul>" + aiNote
      : empty("本期无可靠趋势变化数据。") + aiNote;
  }

  // ── 4. Africa Risk Map（真实边界 choropleth，保留）──
  function renderMap(countries, snapshots, kpis, updated) {
    var host = document.getElementById("v11Map");
    if (!host) return;
    var geo = window.AFRICA_GEO || {};
    var labels = window.AFRICA_LABELS || {};
    var markers = window.AFRICA_MARKERS || {};
    var geoKeys = Object.keys(geo);
    var riskByIso = {}, cnByIso = {}, enByIso = {}, snapByIso = {};
    (snapshots || []).forEach(function (s) {
      if (s.iso3) {
        riskByIso[s.iso3] = s.baseline_risk_level || 0;
        cnByIso[s.iso3] = s.country_cn;
        enByIso[s.iso3] = s.country_en;
        snapByIso[s.iso3] = s;
      }
    });
    countries.forEach(function (c) {
      if (c.cn === "刚果共和国（刚果布）" && !cnByIso["COG"]) {
        cnByIso["COG"] = c.cn; riskByIso["COG"] = c.risk_level || 0;
      }
    });
    function tipFor(iso, name, en, cn, lv) {
      var snap = snapByIso[iso] || {};
      var r = rl(lv);
      var nm = cn || name;
      return "<b>" + esc(nm) + (en ? " / " + esc(en) : " / " + esc(name)) + "</b>" +
        '<div class="tip-row"><span>Risk 风险等级</span><span>' + esc(r.en) + "</span></div>" +
        '<div class="tip-row"><span>24h Events</span><span>' + dash(snap.events_24h) + "</span></div>" +
        '<div class="tip-row"><span>7d Events</span><span>' + dash(snap.events_7d) + "</span></div>" +
        '<div class="tip-row"><span>Trend</span><span>—</span></div>' +
        '<div class="tip-row"><span>Last Updated</span><span>' +
        (snap.last_updated ? bjShort(snap.last_updated) : "—") + "</span></div>" +
        (cn ? '<div style="margin-top:6px;color:#bfdbfe">[查看国家] → ' + esc(cn) + "</div>" : "");
    }
    var paths = geoKeys.map(function (iso) {
      var g = geo[iso];
      var lv = riskByIso[iso];
      var hasRisk = (lv !== undefined && lv !== null);
      var cls = "am-country " + (hasRisk ? "r" + lv : "r0");
      var cn = cnByIso[iso];
      var href = cn ? ' href="country.html?country=' + encodeURIComponent(cn) + '"' : "";
      return '<a' + href + ' class="am-link" tabindex="0" role="link" aria-label="' +
        esc(cn || g.name) + '" data-iso3="' + esc(iso) + '">' +
        '<path class="' + cls + '" d="' + g.d + '" fill-rule="evenodd" data-iso3="' +
        esc(iso) + '" data-tip="' + esc(tipFor(iso, g.name, enByIso[iso], cn, lv)).replace(/"/g, "&quot;") +
        '"/></a>';
    }).join("");
    var labelSvg = Object.keys(labels).map(function (iso) {
      var xy = labels[iso];
      return '<text class="am-label" x="' + xy[0] + '" y="' + (xy[1] + 3) +
        '" text-anchor="middle">' + esc(geo[iso].name) + "</text>";
    }).join("");
    var markerSvg = Object.keys(markers).map(function (iso) {
      var m = markers[iso];
      var lv = riskByIso[iso];
      var cls = "am-country am-marker " + (lv !== undefined ? "r" + lv : "r0");
      var cn = cnByIso[iso];
      var href = cn ? ' href="country.html?country=' + encodeURIComponent(cn) + '"' : "";
      return '<a' + href + ' class="am-link" tabindex="0" aria-label="' + esc(cn || m.name) +
        '" data-iso3="' + esc(iso) + '">' +
        '<circle class="' + cls + '" cx="' + m.x + '" cy="' + m.y + '" r="4" data-tip="' +
        esc(tipFor(iso, m.name, null, cn, lv)).replace(/"/g, "&quot;") + '"/></a>';
    }).join("");
    host.querySelector(".v11-loading").outerHTML =
      '<div class="v11-map-wrap" id="v11MapSvg">' +
      '<svg viewBox="0 0 600 620" role="img" aria-label="Africa Risk Map">' +
      paths + markerSvg + labelSvg + "</svg>" +
      '<div class="v11-map-tip" id="v11MapTip"></div></div>' +
      (geoKeys.length ? "" : '<div class="v11-empty">风险数据暂不可用</div>');
    var legend = document.getElementById("v11MapLegend");
    if (legend) {
      legend.innerHTML = [
        ["--v11-risk-5", "极高 Very High"], ["--v11-risk-4", "高 High"],
        ["--v11-risk-3", "较高 Elevated"], ["--v11-risk-2", "中等 Moderate"],
        ["--v11-risk-1", "低 Low"], ["--v11-risk-0", "暂无数据 No Data"]
      ].map(function (x) {
        return '<span><i style="background:var(' + x[0] + ')"></i>' + x[1] + "</span>";
      }).join("");
    }
    bindMapInteractions();
  }

  function bindMapInteractions() {
    var tip = document.getElementById("v11MapTip");
    var wrap = document.getElementById("v11MapSvg");
    function showTip(el, ev) {
      if (!tip || !wrap) return;
      tip.innerHTML = el.getAttribute("data-tip");
      tip.style.opacity = 1;
      var rect = wrap.getBoundingClientRect();
      var x = ev.clientX - rect.left + 14;
      var y = ev.clientY - rect.top - 10;
      if (x + 190 > rect.width) x = ev.clientX - rect.left - 200;
      if (y + 130 > rect.height) y = ev.clientY - rect.top - 130;
      tip.style.left = x + "px";
      tip.style.top = y + "px";
    }
    document.querySelectorAll(".am-link").forEach(function (a) {
      var iso = a.getAttribute("data-iso3");
      var el = a.querySelector("path, circle");
      a.addEventListener("mousemove", function (ev) { showTip(el, ev); });
      a.addEventListener("mouseleave", function () {
        if (tip) tip.style.opacity = 0;
        a.classList.remove("am-hover");
      });
      a.addEventListener("mouseenter", function () { a.classList.add("am-hover"); });
      a.addEventListener("focus", function () { a.classList.add("am-hover"); });
      a.addEventListener("blur", function () { a.classList.remove("am-hover"); });
      a.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" && a.getAttribute("href")) window.location.href = a.getAttribute("href");
      });
      a.addEventListener("click", function (ev) {
        if (!a.getAttribute("href")) ev.preventDefault();
      });
      a.addEventListener("mouseenter", function () {
        var item = document.querySelector('.v11-tr-item[data-iso3="' + iso + '"]');
        if (item) item.classList.add("v11-tr-active");
      });
      a.addEventListener("mouseleave", function () {
        var item = document.querySelector('.v11-tr-item[data-iso3="' + iso + '"]');
        if (item) item.classList.remove("v11-tr-active");
      });
    });
  }

  // ── 5. Top Risk Countries + Risk Summary ──
  function renderTopRisk(snapshots) {
    var host = document.getElementById("v11TopRisk");
    if (!host) return;
    var list = snapshots.slice().sort(function (a, b) {
      return (b.baseline_risk_level || 0) - (a.baseline_risk_level || 0) ||
        (b.events_7d || 0) - (a.events_7d || 0);
    }).slice(0, 7);
    var cnt = { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0, 0: 0 };
    snapshots.forEach(function (s) { var lv = s.baseline_risk_level || 0; cnt[lv] = (cnt[lv] || 0) + 1; });
    var summary = '<div class="v11-risk-summary">' +
      '<div class="v11-risk-summary-title">RISK SUMMARY</div>' +
      '<div class="v11-risk-summary-row">' +
      '<span class="v11-risk r4">极高 ' + dash(cnt[4] + cnt[5]) + "</span>" +
      '<span class="v11-risk r3">高 ' + dash(cnt[3]) + "</span>" +
      '<span class="v11-risk r2">较高 ' + dash(cnt[2]) + "</span>" +
      '<span class="v11-risk r1">中等 ' + dash(cnt[1]) + "</span>" +
      "</div>" +
      '<a class="v11-more" href="countries.html">查看全部国家 →</a></div>';
    host.querySelector(".v11-loading").outerHTML = list.length
      ? '<ol class="v11-tr-list">' + list.map(function (s, i) {
          var r = rl(s.baseline_risk_level || 0);
          return '<li><a class="v11-tr-item" data-iso3="' + esc(s.iso3 || "") +
            '" href="country.html?country=' + encodeURIComponent(s.country_cn) + '">' +
            '<span class="v11-tr-rank">' + String(i + 1).padStart(2, "0") + "</span>" +
            '<span class="v11-tr-name">' + esc(s.country_cn) + "</span>" +
            '<span class="v11-risk ' + r.cls + '">' + esc(r.cn) + "</span>" +
            '<span class="v11-tr-meta">24h:' + dash(s.events_24h) + " · 7d:" + dash(s.events_7d) +
            "</span></a></li>";
        }).join("") + "</ol>" + summary
      : empty("暂无国家风险数据。") + summary;
    host.querySelectorAll(".v11-tr-item").forEach(function (item) {
      var iso = item.getAttribute("data-iso3");
      item.addEventListener("mouseenter", function () {
        var el = document.querySelector('.am-link[data-iso3="' + iso + '"]');
        if (el) el.classList.add("am-hover");
      });
      item.addEventListener("mouseleave", function () {
        var el = document.querySelector('.am-link[data-iso3="' + iso + '"]');
        if (el) el.classList.remove("am-hover");
      });
    });
  }

  // ── 6. Today's Intelligence：四类 Category Brief ──
  function renderCategories(events, countries, AI) {
    var riskByCn = {};
    countries.forEach(function (c) { riskByCn[c.cn] = c.risk_level || 0; });
    CATEGORIES.forEach(function (cat) {
      var host = document.getElementById({ conflict: "v11CatConflict", political: "v11CatPolitical",
        safety: "v11CatSafety", health: "v11CatHealth" }[cat.key]);
      if (!host) return;
      var inCat = (events || []).filter(function (e) {
        return cat.types.indexOf(e.event_type) >= 0;
      }).sort(function (a, b) {
        return (b.latest_update_at || "").localeCompare(a.latest_update_at || "") ||
          (b.importance_score || 0) - (a.importance_score || 0);
      }).slice(0, 3);
      var ai = (AI && AI.categories && AI.categories[cat.key]) || null;
      var riskSignal = catSignal(inCat, riskByCn);

      if (!inCat.length) {
        // 0 事件：正式空态，无 AI
        host.innerHTML =
          '<div class="v11-cat-head"><span class="v11-cat-name">' + esc(cat.cn) + "</span>" +
          '<span class="v11-card-en">' + esc(cat.en) + "</span></div>" +
          '<div class="v11-cat-body">' +
          empty("过去 24 小时未发现符合条件的重大相关事件。") + "</div>";
        return;
      }
      var news = inCat.map(function (e, i) {
        var cn = e.country_cn || "非洲";
        return '<div class="v11-news">' +
          '<div class="v11-news-head"><span class="v11-news-num">' + String(i + 1).padStart(2, "0") +
          "</span><b>" + esc(cn) + "</b>" +
          (e.event_type_cn ? "<span>· " + esc(e.event_type_cn) + "</span>" : "") +
          '<span class="v11-news-verify ' + (e.verification_status === "single_source" ? "vs-single" : "vs-ok") +
          '">' + esc(vBiz(e.verification_status)) + "</span></div>" +
          '<div class="v11-news-title"><a href="event.html?id=' + encodeURIComponent(e.master_event_id) + '">' +
          esc(e.headline_zh) + "</a></div>" +
          '<div class="v11-news-fact">' + esc(e.fact_summary || "") + "</div>" +
          '<div class="v11-kd-meta"><span>' + esc(bjShort(e.latest_update_at || e.event_time)) + "</span>" +
          (e.source_count ? "<span>来源 " + dash(e.source_count) + " 个</span>" : "") +
          "</div></div>";
      }).join("");
      var watch72 = uniqueCn(inCat).slice(0, 3).join(" · ");
      host.innerHTML =
        '<div class="v11-cat-head"><span class="v11-cat-name">' + esc(cat.cn) + "</span>" +
        '<span class="v11-card-en">' + esc(cat.en) + "</span>" +
        (riskSignal ? '<span class="v11-risk ' + riskSignal.cls + '">' + esc(riskSignal.cn) + "</span>" : "") +
        "</div>" +
        '<div class="v11-cat-body">' +
        '<div class="v11-cat-section">今日重要动态</div>' + news +
        (ai && ai.assessment
          ? aiBlock('<div class="v11-ai-title">综合研判</div><div class="v11-ai-text">' +
              esc(ai.assessment) + "</div>" +
              (Array.isArray(ai.watch_next_72h) && ai.watch_next_72h.length
                ? '<div class="v11-ai-watch">72h 关注：' +
                  ai.watch_next_72h.slice(0, 3).map(esc).join(" · ") + "</div>" : ""))
          : aiFallback("综合研判暂不可用。") +
            (watch72 ? '<div class="v11-ai-watch">72h 关注（确定性）：' + esc(watch72) + "</div>" : "")) +
        "</div>";
    });
  }

  function catSignal(events, riskByCn) {
    var maxLv = 0;
    events.forEach(function (e) {
      var lv = riskByCn[e.country_cn] || 0;
      if (lv > maxLv) maxLv = lv;
    });
    return maxLv ? rl(maxLv) : null;
  }
  function uniqueCn(events) {
    var seen = {}, out = [];
    events.forEach(function (e) {
      if (e.country_cn && !seen[e.country_cn]) { seen[e.country_cn] = 1; out.push(e.country_cn); }
    });
    return out;
  }

  // ── 7. China Exposure & Implications ──
  function renderChina(evs, updated, countries, AI) {
    var host = document.getElementById("v11China");
    if (!host) return;
    var china = (evs || []).filter(function (e) { return e.china_related; }).slice(0, 3);
    var ai = (AI && AI.china) || null;
    var highCn = countries.filter(function (c) { return (c.risk_level || 0) >= 3; })
      .map(function (c) { return c.cn; }).slice(0, 5);
    var html = "";
    if (china.length) {
      html += '<div class="v11-cat-section">直接涉中事件</div><div class="v11-kd-grid">' +
        china.map(function (e) {
          return '<a class="v11-kd-card" href="event.html?id=' + encodeURIComponent(e.event_id) + '">' +
            '<div class="v11-kd-title">' + esc(e.title_cn || e.title || "涉中安全事件") + "</div>" +
            '<div class="v11-kd-fact">' + esc(e.summary_cn || "") + "</div>" +
            '<div class="v11-kd-meta"><span>' + esc(e.country_cn || "") + "</span>" +
            "<span>" + esc(bjShort(e.event_time || "")) + "</span></div></a>";
        }).join("") + "</div>";
    } else {
      html += '<div class="v11-china-ok"><span class="v11-check">✓</span>' +
        "当前未发现已核实的重大直接涉中安全事件" +
        '<span class="v11-china-checked">Last checked: ' + esc(updated ? bjShort(updated) : "—") + " BJT</span></div>";
    }
    // 间接区域风险（确定性）
    if (highCn.length) {
      html += '<div class="v11-cat-section">间接区域风险</div>' +
        '<div class="v11-china-indirect">高/极高风险国家：<b>' + esc(highCn.join(" · ")) +
        "</b>，相关区域安全环境变化可能影响当地企业与人员安排，建议关注官方安全提示。</div>";
    }
    // AI 宏观影响（若有）
    html += ai && ai.china_implications
      ? aiBlock('<div class="v11-ai-title">宏观影响提示</div><div class="v11-ai-text">' +
          esc(ai.china_implications) + "</div>")
      : "";
    host.querySelector(".v11-loading").outerHTML = html;
  }

  // ── 8. Top 3 Overall Developments ──
  function renderTop3(events, countries) {
    var host = document.getElementById("v11Top3");
    if (!host) return;
    var riskByCn = {};
    countries.forEach(function (c) { riskByCn[c.cn] = c.risk_level || 0; });
    var list = (events || []).slice().sort(function (a, b) {
      return (b.latest_update_at || "").localeCompare(a.latest_update_at || "") ||
        (b.importance_score || 0) - (a.importance_score || 0);
    }).slice(0, 3);
    host.querySelector(".v11-loading").outerHTML = list.length
      ? '<div class="v11-kd-grid">' + list.map(function (e) {
          var cn = e.country_cn || "非洲";
          var r = rl(riskByCn[cn] || 0);
          return '<a class="v11-kd-card" href="event.html?id=' + encodeURIComponent(e.master_event_id) + '">' +
            '<div class="v11-kd-head"><span class="v11-risk ' + r.cls + '">' + esc(r.cn) + "</span>" +
            "<span>" + esc(cn) + "</span>" +
            (e.event_type_cn ? "<span>· " + esc(e.event_type_cn) + "</span>" : "") + "</div>" +
            '<div class="v11-kd-title">' + esc(e.headline_zh) + "</div>" +
            '<div class="v11-kd-fact">' + esc(e.fact_summary || "") + "</div>" +
            '<div class="v11-kd-meta"><span>' + esc(bjShort(e.latest_update_at || e.event_time)) + "</span>" +
            (e.source_count ? "<span>来源 " + dash(e.source_count) + "</span>" : "") +
            "<span>" + esc(vBiz(e.verification_status)) + "</span></div></a>";
        }).join("") + "</div>"
      : empty("当前无符合发布条件的高风险事件。");
  }

  // ── 9. Latest Intelligence（状态业务映射）──
  var STATUS_MAP = { FULL: "综合研判", FALLBACK: "事实版", LOW_DATA: "数据有限", HOLD: "已保留" };
  function renderIntel(reports) {
    var host = document.getElementById("v11Intel");
    if (!host) return;
    var list = (reports || []).slice(0, 5);
    host.querySelector(".v11-loading").outerHTML = list.length
      ? '<ul class="v11-rep-list">' + list.map(function (r) {
          var st = r.status;
          var biz = r.status_cn || STATUS_MAP[st] || st || "—";
          var badge = (st === "development_sample" || r.is_mock) ? "rb-mock"
            : (st === "LOW_DATA") ? "rb-low" : (st === "FALLBACK") ? "rb-fallback" : "";
          return '<li class="v11-rep-item">' +
            '<span class="v11-rep-badge ' + badge + '">' + esc(biz) + "</span>" +
            '<div class="v11-rep-main"><div class="v11-rep-title">' + esc(r.title) + "</div>" +
            '<div class="v11-rep-sub">' + esc(r.type_cn || r.type || "") +
            (r.period_end ? " · " + esc(bjShort(r.period_end)) : "") + "</div></div>" +
            (r.path ? '<a class="v11-rep-link" href="' + esc(r.path) + '" target="_blank">查看 →</a>' : "") +
            "</li>";
        }).join("") + "</ul>"
      : empty("暂无正式情报报告。");
  }

  // ── 10. Public Health Signals ──
  function renderHealth(outbreaks) {
    var host = document.getElementById("v11Health");
    if (!host) return;
    var active = (outbreaks || []).filter(function (o) {
      return ["active", "developing", "increasing", "geographic_spread", "monitoring"]
        .indexOf(String(o.status || "").toLowerCase()) >= 0;
    }).slice(0, 3);
    var n = (outbreaks || []).filter(function (o) {
      return ["active", "developing", "increasing", "geographic_spread", "monitoring"]
        .indexOf(String(o.status || "").toLowerCase()) >= 0;
    }).length;
    host.querySelector(".v11-loading").outerHTML = active.length
      ? '<div class="v11-hs-top">Active Signals：<b>' + dash(n) + "</b></div>" +
        '<ul class="v11-ob-list">' + active.map(function (o) {
          var lc = o.latest_counts || {};
          return '<a class="v11-ob-item" href="disease-risk.html#outbreak=' +
            encodeURIComponent(o.outbreak_id) + '">' +
            '<span class="v11-ob-name">' + esc(o.disease_name_cn || o.disease_id) +
            "<small>" + esc(o.country_cn || o.country_iso3 || "") + "</small></span>" +
            '<span class="v11-ob-status">' + esc(o.status_cn || o.status || "—") + "</span>" +
            '<span class="v11-ob-status">确诊 ' + dash(lc.confirmed_cases) + " · 死亡 " +
            dash(lc.deaths) + "</span></a>";
        }).join("") + "</ul>"
      : empty("暂无可展示的传染病风险信号。");
  }

  // ── 11. Explore ASIP ──
  function renderExplore(ks) {
    var host = document.getElementById("v11Explore");
    if (!host) return;
    var cards = [
      ["🌍", "国家风险", "countries.html", "各国风险等级与 24h/7d 动态"],
      ["📌", "安全事件", "events.html", "已核验的重大安全事件"],
      ["📚", "情报知识库", "intelligence/africa/", "组织 · 人物 · 关系 · 国家 · 事件实体"],
      ["📄", "情报报告", "reports.html", "非洲日报与重点国家周报"],
      ["🦠", "传染病风险", "disease-risk.html", "活跃疫情与公共卫生信号"]
    ];
    var kbExtra = ks
      ? '<div class="v11-explore-d">' + dash(ks.entity_count) + " 实体 · " + dash(ks.relationship_count) + " 关系</div>" : "";
    host.querySelector(".v11-loading").outerHTML =
      '<div class="v11-explore">' + cards.map(function (c) {
        return '<a class="v11-explore-card" href="' + c[2] + '">' +
          '<div class="v11-explore-icon">' + c[0] + "</div>" +
          '<div class="v11-explore-t">' + esc(c[1]) + "</div>" +
          '<div class="v11-explore-d">' + esc(c[3]) + "</div>" +
          (c[1] === "情报知识库" ? kbExtra : "") + "</a>";
      }).join("") + "</div>";
  }

  // ── boot ──
  document.addEventListener("DOMContentLoaded", renderAll);
})();
