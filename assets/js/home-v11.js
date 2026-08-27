/* ============================================================
   ASIP V1.1 — Homepage Dashboard Renderer
   数据均来自 PUBLIC-SAFE FRONTEND VIEWS + 白名单公开数据；
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

  // 风险等级名称（与 risk-levels.json 对齐）
  var RISK_NAME = { 5: "极高", 4: "极高", 3: "高", 2: "中", 1: "低", 0: "无数据" };
  var RISK_EN = { 5: "VERY HIGH", 4: "VERY HIGH", 3: "HIGH", 2: "ELEVATED", 1: "MODERATE", 0: "NO DATA" };
  function rl(level) { return { cls: "r" + (level || 0), cn: RISK_NAME[level] || "无数据", en: RISK_EN[level] || "NO DATA" }; }

  // 非洲 22 监测国近似坐标（SVG viewBox 0 0 560 620，示意地图，非 GIS）
  var MAP_XY = {
    "摩洛哥": [215, 70], "阿尔及利亚": [190, 125], "突尼斯": [285, 105], "利比亚": [335, 120],
    "埃及": [395, 140], "塞内加尔": [85, 200], "科特迪瓦": [120, 245], "加纳": [105, 265],
    "贝宁": [160, 265], "尼日利亚": [205, 245], "尼日尔": [265, 195], "马里": [165, 190],
    "布基纳法索": [150, 225], "乍得": [330, 205], "苏丹": [410, 215], "南苏丹": [400, 285],
    "埃塞俄比亚": [455, 265], "肯尼亚": [435, 340], "乌干达": [400, 315], "坦桑尼亚": [410, 380],
    "安哥拉": [245, 395], "刚果共和国（刚果布）": [280, 330], "加蓬": [255, 325],
    "莫桑比克": [390, 455], "南非": [330, 515], "马达加斯加": [480, 470]
  };

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

      renderKpis(countries, kpis, events, evs, updated);
      renderOutlook(kpis, events, snapshots);
      renderOverall(kpis, countries, riskCfg, updated);
      renderMap(countries, snapshots, kpis, updated);
      renderTopRisk(snapshots);
      renderKeyDev(events, countries);
      renderChina(evs, updated);
      renderIntel(reports);
      renderHealth(outbreaks);
      renderExplore(ks);
    });
  }

  // ── 1. KPI Strip ──
  function renderKpis(countries, kpis, events, evs, updated) {
    var set = function (id, v) {
      var el = document.getElementById(id);
      if (el) el.textContent = dash(v);
    };
    set("v11KpiCountries", countries.length || "—");
    set("v11KpiEvents24h", kpis.events_24h);
    set("v11KpiHighRisk", kpis.priority_country_count);
    var chinaN = (evs || []).filter(function (e) { return e.china_related; }).length;
    set("v11KpiChina", chinaN > 0 ? chinaN : "—");
    set("v11KpiDisease", kpis.active_outbreaks);
    set("v11KpiUpdated", updated ? bjShort(updated) + " BJT" : "—");
  }

  // ── 2. 今日30秒态势 ──
  function renderOutlook(kpis, events, snapshots) {
    var host = document.getElementById("v11Outlook");
    if (!host) return;
    var high = (kpis.priority_country_count || 0);
    var total = (high >= 3) ? "高风险" : (high >= 1 ? "中高风险" : "中等");
    var brief;
    if (high >= 3) {
      brief = "萨赫勒及周边地区安全压力维持高位，多个监测国处于高风险状态，需持续关注武装冲突、恐怖活动与跨境流窜风险。";
    } else if (high >= 1) {
      brief = "非洲整体安全形势处于中高水平，部分地区出现新的安全风险信号，建议关注重点国家动态。";
    } else {
      brief = "当前非洲整体安全形势总体平稳，未出现大面积风险升级信号。";
    }
    var pts = [];
    if (dash(kpis.events_24h) !== "—" && kpis.events_24h > 0) {
      pts.push("过去24小时新增重大安全事件 " + kpis.events_24h + " 起");
    }
    var focus = (kpis.priority_countries || []).slice(0, 3);
    if (focus.length) {
      pts.push(focus.length + " 个国家处于极高/高风险状态");
    }
    if (dash(kpis.active_outbreaks) !== "—" && kpis.active_outbreaks > 0) {
      pts.push("活跃传染病信号 " + kpis.active_outbreaks + " 个");
    }
    if (!pts.length) pts.push("暂无可靠的新增变化数据");
    var focusNames = focus.map(function (f) { return f.cn; }).join(" · ");
    host.innerHTML =
      '<div class="v11-outlook-total">今日态势：' + esc(total) + "</div>" +
      '<p class="v11-outlook-brief">' + esc(brief) + "</p>" +
      '<ul class="v11-outlook-list">' + pts.map(function (p) {
        return "<li>" + esc(p) + "</li>";
      }).join("") + "</ul>" +
      (focusNames ? '<p class="v11-outlook-focus">重点关注：<b>' + esc(focusNames) + "</b></p>" : "");
  }

  // ── 3. Overall Risk Signal ──
  function renderOverall(kpis, countries, riskCfg, updated) {
    var host = document.getElementById("v11OverallRisk");
    if (!host) return;
    var levels = countries.map(function (c) { return c.risk_level || 0; });
    var max = levels.length ? Math.max.apply(null, levels) : 0;
    var name = rl(max);
    var trend = "";
    var trendTxt = "总体稳定";
    var levelTxt = name.en;
    var cls = name.cls;
    host.innerHTML =
      '<div class="v11-overall">' +
      '<div class="v11-overall-level ' + cls + '">' + esc(levelTxt) + "</div>" +
      '<div class="v11-overall-trend">' + esc(trendTxt) + (trend ? " " + trend : "") + "</div>" +
      '<div class="v11-overall-basis">' + esc(riskCfg.note || "风险等级基于现行国家风险规则") + "</div>" +
      "</div>";
  }

  // ── 4. Africa Risk Map ──
  function renderMap(countries, snapshots, kpis, updated) {
    var host = document.getElementById("v11Map");
    if (!host) return;
    var snapByCn = {};
    (snapshots || []).forEach(function (s) { snapByCn[s.country_cn] = s; });
    var riskByCn = {};
    countries.forEach(function (c) { riskByCn[c.cn] = c.risk_level || 0; });

    var dots = countries.map(function (c) {
      var xy = MAP_XY[c.cn];
      if (!xy) return null;
      var snap = snapByCn[c.cn] || {};
      var lv = riskByCn[c.cn] || 0;
      var r = rl(lv);
      var tip =
        "<b>" + esc(c.cn) + " (" + esc(c.en || "") + ")</b>" +
        '<div class="tip-row"><span>Risk 风险等级</span><span>' + esc(r.en) + "</span></div>" +
        '<div class="tip-row"><span>24h Events</span><span>' + dash(snap.events_24h) + "</span></div>" +
        '<div class="tip-row"><span>7d Events</span><span>' + dash(snap.events_7d) + "</span></div>" +
        '<div class="tip-row"><span>Latest Update</span><span>' + (snap.last_updated ? bjShort(snap.last_updated) : "—") + "</span></div>" +
        '<div style="margin-top:6px;color:#bfdbfe">[查看国家] → ' + esc(c.cn) + "</div>";
      return { x: xy[0], y: xy[1], cn: c.cn, en: c.en, lv: lv, cls: r.cls, tip: tip };
    }).filter(Boolean);

    var land =
      '<path d="M210 55 L300 45 L350 70 L430 110 L470 165 L445 200 L470 235 L500 260 L520 330 L505 400 L455 470 L420 510 L380 545 L320 560 L255 545 L205 510 L175 470 L140 440 L95 380 L60 320 L70 255 L95 210 L140 170 L175 120 Z" fill="#e8edf4" stroke="#b8c4d4" stroke-width="1.5"/>';
    var dotsSvg = dots.map(function (d) {
      return '<a href="country.html?country=' + encodeURIComponent(d.cn) +
        '" aria-label="' + esc(d.cn) + '">' +
        '<circle cx="' + d.x + '" cy="' + d.y + '" r="11" class="v11-map-dot ' + d.cls + '" data-tip="' +
        esc(d.tip).replace(/"/g, "&quot;") + '" stroke="#fff" stroke-width="2"/></a>';
    }).join("");

    host.querySelector(".v11-loading").outerHTML =
      '<div class="v11-map-wrap" id="v11MapSvg">' +
      '<svg viewBox="0 0 560 620" role="img" aria-label="Africa Risk Map">' +
      land + dotsSvg + "</svg>" +
      '<div class="v11-map-tip" id="v11MapTip"></div></div>';
    var legend = document.getElementById("v11MapLegend");
    if (legend) {
      legend.innerHTML = [
        ["#8b0000", "Very High"], ["#c62828", "High"], ["#e65100", "Elevated"],
        ["#b8860b", "Moderate"], ["#1565c0", "Low"], ["#94a3b8", "No Data"]
      ].map(function (x) {
        return '<span><i style="background:' + x[0] + '"></i>' + x[1] + "</span>";
      }).join("");
    }
    bindMapTip();
  }

  function bindMapTip() {
    var tip = document.getElementById("v11MapTip");
    if (!tip) return;
    document.querySelectorAll(".v11-map-dot").forEach(function (dot) {
      dot.addEventListener("mousemove", function (ev) {
        tip.innerHTML = dot.getAttribute("data-tip");
        tip.style.opacity = 1;
        var wrap = document.getElementById("v11MapSvg");
        var rect = wrap.getBoundingClientRect();
        var x = ev.clientX - rect.left + 14;
        var y = ev.clientY - rect.top - 10;
        if (x + 180 > rect.width) x = ev.clientX - rect.left - 190;
        if (y + 120 > rect.height) y = ev.clientY - rect.top - 120;
        tip.style.left = x + "px";
        tip.style.top = y + "px";
      });
      dot.addEventListener("mouseleave", function () { tip.style.opacity = 0; });
    });
  }

  // ── 5. Top Risk Countries ──
  function renderTopRisk(snapshots) {
    var host = document.getElementById("v11TopRisk");
    if (!host) return;
    var list = snapshots.slice().sort(function (a, b) {
      return (b.baseline_risk_level || 0) - (a.baseline_risk_level || 0) ||
        (b.events_7d || 0) - (a.events_7d || 0);
    }).slice(0, 7);
    host.querySelector(".v11-loading").outerHTML = list.length
      ? '<ol class="v11-tr-list">' + list.map(function (s, i) {
          var r = rl(s.baseline_risk_level || 0);
          return '<li><a class="v11-tr-item" href="country.html?country=' +
            encodeURIComponent(s.country_cn) + '">' +
            '<span class="v11-tr-rank">' + String(i + 1).padStart(2, "0") + "</span>" +
            '<span class="v11-tr-name">' + esc(s.country_cn) + "</span>" +
            '<span class="v11-risk ' + r.cls + '">' + esc(r.cn) + "</span>" +
            '<span class="v11-tr-meta">24h:' + dash(s.events_24h) + " · 7d:" + dash(s.events_7d) +
            "</span></a></li>";
        }).join("") + "</ol>"
      : empty("暂无国家风险数据。");
  }

  // ── 6. Key Developments ──
  function renderKeyDev(events, countries) {
    var host = document.getElementById("v11KeyDev");
    if (!host) return;
    var riskByCn = {};
    countries.forEach(function (c) { riskByCn[c.cn] = c.risk_level || 0; });
    var list = (events || []).slice(0, 5);
    host.querySelector(".v11-loading").outerHTML = list.length
      ? '<div class="v11-kd-grid">' + list.map(function (e) {
          var cn = e.country_cn || "非洲";
          var r = rl(riskByCn[cn] || 0);
          return '<a class="v11-kd-card" href="event.html?id=' +
            encodeURIComponent(e.master_event_id) + '">' +
            '<div class="v11-kd-head"><span class="v11-risk ' + r.cls + '">' + esc(r.cn) + "</span>" +
            "<span>" + esc(cn) + "</span>" +
            (e.event_type_cn ? "<span>· " + esc(e.event_type_cn) + "</span>" : "") +
            (e.change_type_cn ? "<span>· " + esc(e.change_type_cn) + "</span>" : "") + "</div>" +
            '<div class="v11-kd-title">' + esc(e.headline_zh) + "</div>" +
            '<div class="v11-kd-fact">' + esc(e.fact_summary || "") + "</div>" +
            '<div class="v11-kd-meta">' +
            "<span>" + esc(bjShort(e.latest_update_at || e.event_time)) + "</span>" +
            (e.source_count ? "<span>来源 " + dash(e.source_count) + "</span>" : "") +
            (e.verification_cn ? "<span>" + esc(e.verification_cn) + "</span>" : "") +
            "</div></a>";
        }).join("") + "</div>"
      : empty("当前无符合发布条件的高风险事件。");
  }

  // ── 7. China Interest ──
  function renderChina(evs, updated) {
    var host = document.getElementById("v11China");
    if (!host) return;
    var china = (evs || []).filter(function (e) { return e.china_related; }).slice(0, 3);
    host.querySelector(".v11-loading").outerHTML = china.length
      ? '<div class="v11-kd-grid">' + china.map(function (e) {
          return '<a class="v11-kd-card" href="event.html?id=' + encodeURIComponent(e.event_id) + '">' +
            '<div class="v11-kd-title">' + esc(e.title_cn || e.title || e.headline_zh || "涉中安全事件") + "</div>" +
            '<div class="v11-kd-fact">' + esc(e.summary_cn || "") + "</div>" +
            '<div class="v11-kd-meta"><span>' + esc(e.country_cn || "") + "</span>" +
            "<span>" + esc(bjShort(e.event_time || "")) + "</span></div></a>";
        }).join("") + "</div>"
      : '<div class="v11-china-ok"><span class="v11-check">✓</span>' +
        "当前未发现已核实的重大涉中安全事件" +
        '<span class="v11-china-checked">Last checked: ' +
        esc(updated ? bjShort(updated) : "—") + " BJT</span></div>";
  }

  // ── 8. Latest Intelligence ──
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
            : (st === "LOW_DATA") ? "rb-low"
            : (st === "FALLBACK") ? "rb-fallback" : "";
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

  // ── 9. Public Health ──
  function renderHealth(outbreaks) {
    var host = document.getElementById("v11Health");
    if (!host) return;
    var active = (outbreaks || []).filter(function (o) {
      return ["active", "developing", "increasing", "geographic_spread", "monitoring"]
        .indexOf(String(o.status || "").toLowerCase()) >= 0;
    }).slice(0, 5);
    host.querySelector(".v11-loading").outerHTML = active.length
      ? '<ul class="v11-ob-list">' + active.map(function (o) {
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

  // ── 10. Explore ASIP ──
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
      ? '<div class="v11-explore-d">' + dash(ks.entity_count) + " 实体 · " + dash(ks.relationship_count) + " 关系</div>"
      : "";
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
