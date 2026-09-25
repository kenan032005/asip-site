/* ============================================================
   ASIP C7-5 — MESIP 风格首页情报模块
   数据源：data/views/homepage_intelligence.json（homepage-intelligence-v1）
   层级铁律：news_signal（未核实）≠ verified_event（已核实）；tier 表示证据角色，不代表真假。
   回退：视图不可用 → 各板块显示诚实空态，绝不空白整页。
   ============================================================ */
(function () {
  "use strict";
  var VIEW = "data/views/homepage_intelligence.json";
  var CAND = ["data/views/homepage_intelligence.json", "views/homepage_intelligence.json"];

  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function shortTime(s) {
    var m = String(s || "").match(/(\d{4})-(\d{2})-(\d{2})[T ](\d{2}:\d{2})/);
    return m ? (m[2] + "-" + m[3] + " " + m[4]) : esc(s || "");
  }
  var LEVEL_CN = { high: "高", elevated: "偏高", moderate: "中等", low: "低", insufficient_data: "数据不足" };
  var DIR_CN = { improving: "趋于改善", stable: "总体平稳", worsening: "趋于恶化" };
  var TREND_ARROW = { up: "▲", flat: "▬", down: "▼" };
  var TREND_CN = { up: "上升", flat: "持平", down: "回落" };
  var CONF_CN = { high: "高", medium: "中", low: "低" };
  var TIER_CN = { A: "Tier A 主要/官方", B: "Tier B 区域/专业", C: "Tier C 地方信号" };

  function loadView() {
    var i = 0;
    function next() {
      if (i >= CAND.length) return Promise.reject(new Error("no view"));
      var u = CAND[i++];
      var viaApi = (u.indexOf("data/") === 0 && window.API) ? window.API.get(u.replace(/\.json$/, "")) : null;
      return (viaApi || fetch(u, { credentials: "same-origin" }).then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status); return r.json();
      })).catch(next);
    }
    return next();
  }

  var host = function (id) { return document.getElementById(id); };
  function busy(ids, msg) {
    ids.forEach(function (id) { var el = host(id); if (el) el.innerHTML = '<div class="hpi-empty">' + esc(msg) + "</div>"; });
  }

  /* ① 24 小时态势总览 */
  function renderOverview(d) {
    var el = host("hpiOverview"); if (!el) return;
    var o = d.overview || {}, m = d.metrics || {}, ai = d.ai || {};
    var kj = (o.key_judgments || []).map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("");
    var wt = (o.watch_24_72h || []).map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("");
    el.innerHTML =
      '<div class="hpi-assess">' + esc(o.summary_cn || "暂无足够公开信息形成稳定研判。") + "</div>" +
      '<div class="hpi-metrics">' +
        '<span class="hpi-metric"><b>' + (m.signals_24h || 0) + "</b>情报信号</span>" +
        '<span class="hpi-metric"><b>' + (m.verified_events_24h || 0) + "</b>已核实事件</span>" +
        '<span class="hpi-metric"><b>' + (m.countries_24h || 0) + "</b>活跃国家</span>" +
        '<span class="hpi-metric"><b>' + (m.high_attention || 0) + "</b>高关注</span>" +
        '<span class="hpi-metric"><b>' + (m.countries_7d || 0) + "</b>7日覆盖国家</span>" +
      "</div>" +
      '<div class="hpi-cols">' +
        '<div><h4>关键判断</h4><ul class="hpi-list">' + (kj || '<li class="hpi-muted">暂无</li>') + "</ul></div>" +
        '<div><h4>未来 24–72 小时关注</h4><ul class="hpi-list">' + (wt || '<li class="hpi-muted">暂无</li>') + "</ul></div>" +
      "</div>" +
      '<div class="hpi-meta"><span class="hpi-pill ' + (o.risk_direction === "worsening" ? "is-worse" : "") + '">风险方向：' +
        esc(DIR_CN[o.risk_direction] || "—") + '</span><span class="hpi-pill">置信度：' + esc(CONF_CN[o.confidence] || "—") + "</span>" +
        (o.ai_based ? '<span class="hpi-pill is-ai">AI 综合研判</span>' : '<span class="hpi-pill">确定性汇总（AI 简报不可用）</span>') +
        '<span class="hpi-upd">更新于 ' + esc(shortTime(ai.generated_time || d.generated_time)) + "</span></div>";
  }

  /* ② 五大安全领域 */
  function renderSectors(d) {
    var el = host("hpiSectors"); if (!el) return;
    var rows = d.sectors || [];
    el.innerHTML = rows.map(function (s) {
      var devs = (s.developments || []).map(function (x) {
        return '<li><span class="hpi-cc">' + esc(x.country) + "</span> " + esc(x.title) +
          ' <em class="hpi-t">' + esc(shortTime(x.time)) + "</em>" +
          (x.level === "verified_event" ? ' <i class="hpi-tag is-v">已核实</i>' : ' <i class="hpi-tag">情报信号</i>') + "</li>";
      }).join("");
      return '<div class="hpi-card hpi-sector">' +
        '<div class="hpi-card-h"><h3>' + esc(s.title_cn) + '</h3><span class="hpi-en">' + esc(s.title_en) + "</span>" +
        '<span class="hpi-trend ' + (s.trend === "up" ? "is-up" : s.trend === "down" ? "is-down" : "") + '">' +
        (TREND_ARROW[s.trend] || "▬") + esc(TREND_CN[s.trend] || "") + "</span></div>" +
        '<div class="hpi-sector-num"><b>' + (s.signals_24h || 0) + "</b> 24h 信号 · <b>" + (s.verified_events_24h || 0) + "</b> 已核实 · 置信度 " + esc(CONF_CN[s.confidence] || "低") + "</div>" +
        '<p class="hpi-sector-a' + (s.ai_based ? " is-ai" : "") + '">' + esc(s.assessment_cn || "过去24小时未发现足够高质量公开信息形成明确判断") + "</p>" +
        (s.countries && s.countries.length ? '<div class="hpi-ccs">' + s.countries.map(function (c) { return '<span class="hpi-cc">' + esc(c) + "</span>"; }).join("") + "</div>" : "") +
        (devs ? '<ul class="hpi-list hpi-devs">' + devs + "</ul>" : "") +
        "</div>";
    }).join("");
  }

  /* ③ 重点动态 + 解读 */
  function renderTop(d) {
    var el = host("hpiTop"); if (!el) return;
    var rows = d.top_developments || [];
    if (!rows.length) { el.innerHTML = '<div class="hpi-empty">近 24 小时暂无可展示的重点动态</div>'; return; }
    el.innerHTML = rows.map(function (t) {
      var href = t.event_id ? ("event.html?id=" + encodeURIComponent(t.event_id)) : "events.html";
      return '<div class="hpi-top">' +
        '<div class="hpi-top-h"><a class="hpi-cc" href="' + href + '">' + esc(t.country) + "</a>" +
        (t.level === "verified_event" ? '<i class="hpi-tag is-v">已核实事件</i>' : '<i class="hpi-tag">情报信号</i>') +
        '<i class="hpi-tag is-tier" title="' + esc(TIER_CN[t.source_tier] || "") + '">' + esc(t.source_tier || "C") + "</i>" +
        '<em class="hpi-t">' + esc(shortTime(t.time)) + "</em>" +
        '<span class="hpi-src">' + esc(t.source) + " · " + (t.source_count || 1) + " 源</span></div>" +
        '<a class="hpi-top-title" href="' + href + '">' + esc(t.title) + "</a>" +
        (t.summary ? '<p class="hpi-top-sum">' + esc(t.summary) + "</p>" : "") +
        '<div class="hpi-top-ai">' +
          (t.why_it_matters ? '<p><b>为什么重要：</b>' + esc(t.why_it_matters) + "</p>" : "") +
          (t.impact ? '<p><b>可能影响：</b>' + esc(t.impact) + "</p>" : "") +
          (t.watch_points ? '<p><b>后续关注：</b>' + esc(t.watch_points) + "</p>" : "") +
          (t.ai_based ? "" : '<p class="hpi-muted">AI 解读暂不可用（仅展示事实字段）</p>') +
        "</div></div>";
    }).join("");
  }

  /* ④ 中国企业与人员影响 */
  function renderChina(d) {
    var el = host("hpiChina"); if (!el) return;
    var c = d.china_impact || {};
    var items = (c.items || []).map(function (i) {
      return '<div class="hpi-china-item"><div class="hpi-top-h"><span class="hpi-cc">' + esc(i.country) + "</span>" +
        '<i class="hpi-tag">' + esc(i.sector || "") + "</i>" +
        '<i class="hpi-tag is-lv' + (i.impact_level === "high" ? " is-up" : "") + '">影响：' + esc(LEVEL_CN[i.impact_level] || i.impact_level || "") + "</i></div>" +
        '<p>' + esc(i.development || "") + "</p>" +
        (i.interpretation ? '<p class="hpi-ai"><b>影响判断：</b>' + esc(i.interpretation) + "</p>" : "") +
        (i.watch_point ? '<p class="hpi-muted"><b>关注：</b>' + esc(i.watch_point) + "</p>" : "") + "</div>";
    }).join("");
    var cands = (c.candidates || []).map(function (x) {
      return '<li><span class="hpi-cc">' + esc(x.country) + "</span> " + esc(x.title) +
        ' <em class="hpi-t">' + esc(shortTime(x.time)) + "</em></li>";
    }).join("");
    el.innerHTML =
      '<p class="hpi-china-sum' + (c.ai_based ? " is-ai" : "") + '">' +
        esc(c.summary_cn || "过去24小时未发现明确直接涉及中国企业或人员的重大公开安全事件。") + "</p>" +
      (items ? '<div class="hpi-china-list">' + items + "</div>" : "") +
      (cands ? '<div class="hpi-sub"><h4>需关注的区域性运营风险（含明确涉华指称的情报信号）</h4><ul class="hpi-list">' + cands + "</ul></div>" : "") +
      '<p class="hpi-note">仅基于公开来源；不推断未证实的中资存在或影响。</p>';
  }

  /* ⑤ 非洲安全风险与活动态势（SVG，使用既有 geo 资产） */
  function renderMap(d) {
    var el = host("hpiMap"); if (!el) return;
    var mp = d.map || {}, levels = mp.levels || [];
    var geo = window.AFRICA_GEO || null;
    var byIso3 = {};
    levels.forEach(function (l) { if (l.iso3) byIso3[l.iso3] = l; });
    var color = { high: "#c62828", elevated: "#e65100", moderate: "#b8860b", low: "#1565c0",
                  insufficient_data: "#94a3b8" };
    var paths = [], missing = 0;
    if (geo) {
      Object.keys(geo).forEach(function (iso3) {
        var l = byIso3[iso3];
        var lvl = l ? l.level : "insufficient_data";
        if (!l) missing++;
        paths.push('<path d="' + geo[iso3].d + '" fill="' + color[lvl] + '" fill-opacity="' +
          (lvl === "insufficient_data" ? ".35" : ".82") + '" stroke="#ffffff" stroke-width=".6">' +
          "<title>" + esc((l && l.country) || iso3) + "：" + esc(LEVEL_CN[lvl]) +
          (l ? (" · 24h " + l.sig24 + " 信号 / " + l.ev24 + " 已核实 / 7d " + l.sig7) : " · 无数据") + "</title></path>");
      });
    }
    var legend = (mp.legend || []).map(function (x) {
      return '<span class="hpi-lg"><i style="background:' + (color[x.level] || "#94a3b8") + '"></i>' + esc(x.label_cn) + "</span>";
    }).join("");
    var list = levels.slice(0, 14).map(function (l) {
      return '<div class="hpi-map-row"><span class="hpi-dot" style="background:' + (color[l.level] || "#94a3b8") + '"></span>' +
        '<a href="country.html?country=' + encodeURIComponent(l.country) + '">' + esc(l.country) + "</a>" +
        '<span class="hpi-map-n">24h ' + (l.sig24 || 0) + " · 7d " + (l.sig7 || 0) + " · 已核实 " + (l.ev24 || 0) + "</span>" +
        '<span class="hpi-map-lv">' + esc(LEVEL_CN[l.level]) + "</span></div>";
    }).join("");
    el.innerHTML = '<div class="hpi-map-wrap">' +
      (geo ? '<svg class="hpi-map-svg" viewBox="230 300 140 160" preserveAspectRatio="xMidYMid meet">' + paths.join("") + "</svg>"
           : '<div class="hpi-empty">地图数据不可用</div>') +
      '<div class="hpi-map-side"><div class="hpi-legend">' + legend + '</div><div class="hpi-map-list">' + list + "</div>" +
      '<p class="hpi-note">确定性口径：' + esc(mp.scoring || "") + "；“数据不足”与“低风险”严格区分。</p></div></div>";
  }

  /* ⑥ 公共卫生与传染病安全 */
  function renderHealth(d) {
    var el = host("hpiHealth"); if (!el) return;
    var h = d.health_security || {};
    var items = (h.items || []).map(function (x) {
      return '<li><span class="hpi-cc">' + esc(x.country_iso3 || "—") + "</span> " + esc(x.disease || "—") +
        ' <em class="hpi-t">' + esc(x.date || "") + "</em>" + (x.location ? " · " + esc(x.location) : "") + "</li>";
    }).join("");
    el.innerHTML =
      '<p class="hpi-sector-a' + (h.ai_based ? " is-ai" : "") + '">' +
        esc(h.summary_cn || (h.available ? "" : "公共卫生数据暂不可用或不足，不作推断。")) + "</p>" +
      (h.key_issues && h.key_issues.length ? '<ul class="hpi-list">' + h.key_issues.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul>" : "") +
      (h.impact_cn ? '<p><b>人员/运营影响：</b>' + esc(h.impact_cn) + "</p>" : "") +
      (items ? '<div class="hpi-sub"><h4>近期监测到的传染病事件</h4><ul class="hpi-list hpi-tight">' + items + "</ul></div>"
             : '<div class="hpi-empty">近期无可用传染病事件数据</div>') +
      '<p class="hpi-note">仅呈现既有监测数据，不作医学预测。置信度 ' + esc(CONF_CN[h.confidence] || "低") + "。</p>";
  }

  /* ⑦ 最新情报流（20–30 条 + 轻量过滤） */
  function renderFeed(d) {
    var el = host("hpiFeed"); if (!el) return;
    var rows = d.latest_intelligence || [];
    var tabs = [["all", "全部"], ["terrorism_conflict", "恐袭/冲突"], ["political_social", "政治社会"],
                ["crime_public_security", "治安犯罪"], ["military_border_maritime", "军事边境"],
                ["accident_disruption", "事故灾害"], ["health", "健康"]];
    el.innerHTML = '<div class="hpi-tabs">' + tabs.map(function (t, i) {
      return '<button class="hpi-tab' + (i === 0 ? " is-on" : "") + '" data-k="' + t[0] + '">' + t[1] + "</button>";
    }).join("") + '</div><div class="hpi-feed-list" id="hpiFeedList"></div>';
    var list = host("hpiFeedList");
    function draw(k) {
      var r = rows.filter(function (x) {
        if (k === "all") return true;
        if (k === "health") return /health|disease|cholera|epidemic/i.test(String(x.category_cn) + String(x.title));
        return x.sector === k;
      });
      list.innerHTML = r.length ? r.map(function (x) {
        return '<div class="hpi-feed-row"><span class="hpi-cc">' + esc(x.country) + "</span>" +
          '<span class="hpi-feed-main"><b>' + esc(x.title || "（无标题）") + "</b>" +
          (x.translated ? "" : '<i class="hpi-orig">原文</i>') +
          '<i class="hpi-feed-meta">' + esc(x.category_cn) + " ｜ " + esc(x.source) +
          ' ｜ <span title="' + esc(TIER_CN[x.source_tier] || "") + '">Tier ' + esc(x.source_tier || "C") + "</span>" +
          (x.importance === "high" ? ' ｜ <b class="hpi-imp">重要</b>' : "") + "</i></span>" +
          '<span class="hpi-feed-side"><em class="hpi-tag">情报信号</em><em class="hpi-t">' + esc(shortTime(x.time)) + "</em></span></div>";
      }).join("") : '<div class="hpi-empty">该分类近 24 小时暂无条目</div>';
    }
    draw("all");
    el.querySelectorAll(".hpi-tab").forEach(function (b) {
      b.addEventListener("click", function () {
        el.querySelectorAll(".hpi-tab").forEach(function (x) { x.classList.remove("is-on"); });
        b.classList.add("is-on"); draw(b.getAttribute("data-k"));
      });
    });
  }

  function init() {
    busy(["hpiOverview", "hpiSectors", "hpiTop", "hpiChina", "hpiMap", "hpiHealth", "hpiFeed"], "加载中…");
    loadView().then(function (d) {
      try { renderOverview(d); } catch (e) { busy(["hpiOverview"], "态势概览渲染失败"); }
      try { renderSectors(d); } catch (e) { busy(["hpiSectors"], "领域分析渲染失败"); }
      try { renderTop(d); } catch (e) { busy(["hpiTop"], "重点动态渲染失败"); }
      try { renderChina(d); } catch (e) { busy(["hpiChina"], "中国影响渲染失败"); }
      try { renderMap(d); } catch (e) { busy(["hpiMap"], "地图渲染失败"); }
      try { renderHealth(d); } catch (e) { busy(["hpiHealth"], "健康板块渲染失败"); }
      try { renderFeed(d); } catch (e) { busy(["hpiFeed"], "情报流渲染失败"); }
    }).catch(function (e) {
      if (window.console) console.warn("[homepage-intelligence]", e);
      busy(["hpiOverview", "hpiSectors", "hpiTop", "hpiChina", "hpiMap", "hpiHealth", "hpiFeed"],
           "首页情报数据暂不可用（其余模块不受影响）");
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
