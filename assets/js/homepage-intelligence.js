/* ============================================================
   ASIP C7-6 — 首页情报模块（MESIP 风格，信息优先）
   数据源：data/views/homepage_intelligence.json（homepage-intelligence-view-v2）
   铁律：
     · 层级：已核实事件（多源独立核实）≠ 情报信号（尚未独立核实）；标签按平台真实核实级别
     · 每条公开条目都带 detail_url（中心化）→ 点开即到该条详情页，绝不指向泛列表页
     · 五大领域基于 7 日窗口，前 6–8 条 + 展开全部
     · 地图板块使用旧版「非洲风险地图」组件（不在本模块内）
   回退：视图不可用 → 各板块诚实空态，不空白整页。
   ============================================================ */
(function () {
  "use strict";
  var CAND = ["data/views/homepage_intelligence.json", "views/homepage_intelligence.json"];
  var LEVEL_CN = { high: "高", elevated: "偏高", moderate: "中等", low: "低" };
  var DIR_CN = { improving: "趋于改善", stable: "总体平稳", worsening: "趋于恶化" };
  var TREND_ARROW = { up: "▲", flat: "▬", down: "▼" };
  var TREND_CN = { up: "上升", flat: "持平", down: "回落" };
  var CONF_CN = { high: "高", medium: "中", low: "低" };
  var TIER_CN = { A: "主要/官方信源", B: "区域/专业信源", C: "地方信号" };
  var HEALTH_TREND_CN = { worsening: "恶化", stable: "稳定", improving: "改善", unclear: "尚不明朗" };
  var VERIFIED_CN = "已核实事件";
  var SIGNAL_CN = "情报信号";
  var WINDOW = 8;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function shortTime(s) {
    var m = String(s || "").match(/(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/);
    return m ? (m[2] + "-" + m[3] + " " + m[4] + ":" + m[5]) : String(s || "—").slice(0, 16);
  }
  function href(d) { return d && d.detail_url ? d.detail_url : "events.html"; }
  function isVerified(d) { return d && d.kind === "verified_event"; }
  function statusTag(d) {
    return isVerified(d)
      ? '<i class="hpi-tag is-v">' + VERIFIED_CN + "</i>"
      : '<i class="hpi-tag">' + esc(d.verification_label || SIGNAL_CN) + "</i>";
  }
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

  /* ① 过去24小时非洲安全态势 */
  function renderOverview(d) {
    var el = host("hpiOverview"); if (!el) return;
    var o = d.overview || {}, m = d.metrics || {}, ai = d.ai || {};
    var kj = (o.key_judgments || []).map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("");
    var wt = (o.watch_24_72h || []).map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("");
    el.innerHTML =
      '<div class="hpi-assess hpi-prose">' + esc(o.summary_cn || "暂无足够公开信息形成稳定研判。") + "</div>" +
      '<div class="hpi-metrics">' +
        '<span class="hpi-metric"><b>' + (m.signals_24h || 0) + "</b>情报信号（24h）</span>" +
        '<span class="hpi-metric"><b>' + (m.verified_events_24h || 0) + "</b>已核实事件（24h）</span>" +
        '<span class="hpi-metric"><b>' + (m.countries_24h || 0) + "</b>活跃国家</span>" +
        '<span class="hpi-metric"><b>' + (m.high_attention || 0) + "</b>高关注</span>" +
        '<span class="hpi-metric"><b>' + (m.countries_7d || 0) + "</b>7日覆盖国家</span>" +
      "</div>" +
      '<div class="hpi-cols">' +
        '<div><h4>关键判断</h4><ul class="hpi-list">' + (kj || '<li class="hpi-muted">暂无</li>') + "</ul></div>" +
        '<div><h4>未来 24–72 小时关注</h4><ul class="hpi-list">' + (wt || '<li class="hpi-muted">暂无</li>') + "</ul></div>" +
      "</div>" +
      (d.dedup ? '<div class="hpi-meta"><span class="hpi-pill">去重：原始 ' + d.dedup.raw_items +
        " 条 → 发展项 " + d.dedup.deduped_developments + " 条（合并 " + d.dedup.collapsed_duplicates +
        " 条重复）</span></div>" : "") +
      '<div class="hpi-meta"><span class="hpi-pill ' + (o.risk_direction === "worsening" ? "is-worse" : "") + '">风险方向：' +
        esc(DIR_CN[o.risk_direction] || "—") + '</span><span class="hpi-pill">置信度：' + esc(CONF_CN[o.confidence] || "—") + "</span>" +
        (o.ai_based ? '<span class="hpi-pill is-ai">AI 综合研判</span>' : '<span class="hpi-pill">确定性汇总</span>') +
        '<span class="hpi-upd">更新于 ' + esc(shortTime(ai.generated_time || d.generated_time)) + "</span></div>";
  }

  /* ② 五大安全领域（7 日窗口） */
  function renderSectors(d) {
    var el = host("hpiSectors"); if (!el) return;
    var rows = d.sectors || [];
    el.innerHTML = rows.map(function (s) {
      var devs = (s.developments || []);
      function li(x) {
        return '<li><a class="hpi-cc" href="' + esc(href(x)) + '">' + esc(x.country) + "</a> " +
          esc(x.title_cn || "") +
          ' <em class="hpi-t">' + esc(shortTime(x.time)) + "</em>" + statusTag(x) +
          '<i class="hpi-tag is-tier" title="' + esc(TIER_CN[x.tier] || "") + '">' + esc(x.tier || "C") + "</i></li>";
      }
      var head = devs.slice(0, WINDOW).map(li).join("");
      var rest = devs.slice(WINDOW).map(li).join("");
      var more = devs.length > WINDOW
        ? '<button class="hpi-more" data-k="' + esc(s.key) + '">展开全部（' + devs.length + "）</button>"
        : "";
      return '<div class="hpi-card hpi-sector">' +
        '<div class="hpi-card-h"><h3>' + esc(s.title_cn) + '</h3><span class="hpi-en">' + esc(s.title_en) + "</span>" +
        '<span class="hpi-trend ' + (s.trend === "up" ? "is-up" : s.trend === "down" ? "is-down" : "") + '">' +
        (TREND_ARROW[s.trend] || "▬") + esc(TREND_CN[s.trend] || "") + "</span></div>" +
        '<div class="hpi-sector-num">近 7 日：<b>' + (s.verified_events_7d || 0) + "</b> 已核实 · <b>" +
        (s.signals_7d || 0) + "</b> 情报信号 · 置信度 " + esc(CONF_CN[s.confidence] || "低") + "</div>" +
        '<p class="hpi-sector-a hpi-prose' + (s.ai_based ? " is-ai" : "") + '">' +
        esc(s.assessment_cn || "过去24小时未发现足够高质量公开信息形成明确判断") + "</p>" +
        (s.changes_cn ? '<p class="hpi-muted"><b>显著变化：</b>' + esc(s.changes_cn) + "</p>" : "") +
        (s.watch_cn ? '<p class="hpi-muted"><b>前瞻关注：</b>' + esc(s.watch_cn) + "</p>" : "") +
        (s.countries && s.countries.length ? '<div class="hpi-ccs">' + s.countries.map(function (c) {
          return '<span class="hpi-cc">' + esc(c) + "</span>"; }).join("") + "</div>" : "") +
        (head ? '<ul class="hpi-list hpi-devs">' + head + "</ul>" : "") +
        (rest ? '<ul class="hpi-list hpi-devs hpi-more-list" data-k="' + esc(s.key) + '" hidden>' + rest + "</ul>" : "") +
        more +
        "</div>";
    }).join("");
    el.querySelectorAll(".hpi-more").forEach(function (b) {
      b.addEventListener("click", function () {
        var k = b.getAttribute("data-k");
        var ul = el.querySelector('.hpi-more-list[data-k="' + k + '"]');
        if (ul) { ul.hidden = !ul.hidden; b.textContent = ul.hidden ? ("展开全部（" + ul.children.length + "）") : "收起"; }
      });
    });
  }

  /* ③ 今日重点信息与事件解读 */
  function renderTop(d) {
    var el = host("hpiTop"); if (!el) return;
    var rows = d.top_developments || [];
    if (!rows.length) { el.innerHTML = '<div class="hpi-empty">近 24 小时暂无可展示的重点动态</div>'; return; }
    el.innerHTML = rows.map(function (t) {
      var h = href(t), blocks = "";
      if (t.why_it_matters) blocks += '<p class="hpi-why"><b>为什么重要：</b>' + esc(t.why_it_matters) + "</p>";
      if (t.ai_analysis) blocks += '<p class="hpi-ai"><b>AI 解读：</b>' + esc(t.ai_analysis) + "</p>";
      if (t.ai_impact) blocks += "<p><b>可能影响：</b>" + esc(t.ai_impact) + "</p>";
      if (t.ai_watch) blocks += '<p class="hpi-muted"><b>后续关注：</b>' + esc(t.ai_watch) + "</p>";
      return '<div class="hpi-top">' +
        '<div class="hpi-top-h"><a class="hpi-cc" href="' + esc(h) + '">' + esc(t.country) + "</a>" +
        statusTag(t) +
        '<i class="hpi-tag is-tier" title="' + esc(TIER_CN[t.tier] || "") + '">' + esc(t.tier || "C") + "</i>" +
        '<em class="hpi-t">' + esc(shortTime(t.time)) + "</em>" +
        '<span class="hpi-src">' + esc(t.source) + " · " + (t.source_count || 1) + " 个来源</span></div>" +
        '<a class="hpi-top-title" href="' + esc(h) + '">' + esc(t.title_cn || "（无标题）") + "</a>" +
        (t.summary_cn ? '<p class="hpi-top-sum">' + esc(t.summary_cn) + "</p>" : "") +
        blocks +
        '<div class="hpi-top-f"><a class="hpi-cc" href="' + esc(h) + '">查看详情 →</a> ' +
        (t.original_url ? '<a class="hpi-cc" href="' + esc(t.original_url) + '" target="_blank" rel="noopener noreferrer">查看原文 ↗</a>' : "") +
        "</div></div>";
    }).join("");
  }

  /* ④ 对中国企业及人员影响 */
  function renderChina(d) {
    var el = host("hpiChina"); if (!el) return;
    var c = d.china_impact || {};
    var items = (c.items || []).map(function (i) {
      return '<div class="hpi-china-item"><div class="hpi-top-h"><a class="hpi-cc" href="' + esc(href(i)) + '">' +
        esc(i.country) + "</a>" + (i.sector_cn ? '<i class="hpi-tag">' + esc(i.sector_cn) + "</i>" : "") +
        '<i class="hpi-tag is-lv' + (i.impact_level === "high" ? " is-up" : "") + '">影响：' +
        esc(LEVEL_CN[i.impact_level] || i.impact_level || "") + "</i></div>" +
        '<a href="' + esc(href(i)) + '">' + esc(i.title_cn) + "</a>" +
        (i.impact_note ? '<p class="hpi-ai"><b>影响判断：</b>' + esc(i.impact_note) + "</p>" : "") + "</div>";
    }).join("");
    function list(arr) {
      return (arr || []).map(function (x) {
        return '<li><a class="hpi-cc" href="' + esc(href(x)) + '">' + esc(x.country) + "</a> " +
          esc(x.title_cn) + ' <em class="hpi-t">' + esc(shortTime(x.time)) + "</em>" +
          (x.source_count > 1 ? ' <i class="hpi-tag">多源</i>' : "") + "</li>";
      }).join("");
    }
    el.innerHTML =
      '<div class="hpi-part"><h4>总体影响研判</h4>' +
      '<p class="hpi-prose' + (c.ai_based ? " is-ai" : "") + '">' +
      esc(c.analysis_cn || c.summary_cn || "过去24小时未发现明确直接涉及中国企业或人员的重大公开安全事件。") + "</p></div>" +
      '<div class="hpi-part"><h4>直接涉华事件</h4>' +
      (c.direct_items && c.direct_items.length
        ? '<ul class="hpi-list">' + list(c.direct_items) + "</ul>"
        : '<p class="hpi-muted">过去 24 小时未发现明确直接涉及中国企业或人员的重大公开安全事件。</p>') +
      (items ? '<div class="hpi-china-list">' + items + "</div>" : "") + "</div>" +
      '<div class="hpi-part"><h4>需关注的区域性运营风险</h4>' +
      (c.regional_items && c.regional_items.length
        ? '<ul class="hpi-list">' + list(c.regional_items) + "</ul>"
        : '<p class="hpi-muted">暂无可支撑的区域性运营风险评估。</p>') + "</div>" +
      '<p class="hpi-note">仅基于公开来源；不推断未证实的中资存在或影响。直接涉华与区域性风险严格分列。</p>';
  }

  /* ⑥ 公共卫生与传染病安全 */
  function renderHealth(d) {
    var el = host("hpiHealth"); if (!el) return;
    var h = d.health_security || {};
    var issues = (h.issues && h.issues.length) ? h.issues : (h.key_issues || []).map(function (x) { return { what: x }; });
    var issueRows = issues.map(function (x) {
      return "<li><b>" + esc(x.what || x.disease || "—") + "</b>" +
        (x.where ? " · " + esc(x.where) : "") +
        (x.when ? " · 起始：" + esc(x.when) : "") +
        (x.severity_cn ? " · 严重程度：" + esc(x.severity_cn) : "") +
        (x.trend ? " · 趋势：" + esc(HEALTH_TREND_CN[x.trend] || x.trend) : "") +
        (x.impact_cn ? '<br><span class="hpi-muted">' + esc(x.impact_cn) + "</span>" : "") + "</li>";
    }).join("");
    var rows = (h.items || []).slice(0, 10).map(function (x) {
      return '<li><span class="hpi-cc">' + esc(x.country_iso3 || "—") + "</span> " + esc(x.disease || "—") +
        ' <em class="hpi-t">' + esc(x.as_of || x.date || "") + "</em>" +
        (x.location ? " · " + esc(x.location) : "") +
        (x.start_known === false ? " · 起始时间待确认" : "") + "</li>";
    }).join("");
    el.innerHTML =
      '<p class="hpi-sector-a hpi-prose' + (h.ai_based ? " is-ai" : "") + '">' +
      esc(h.summary_cn || (h.available ? "" : "公共卫生数据暂不可用或不足，不作推断。")) + "</p>" +
      (issueRows ? '<div class="hpi-sub"><h4>重点卫生议题</h4><ul class="hpi-list">' + issueRows + "</ul></div>" : "") +
      (h.impact_cn ? "<p><b>人员/运营影响：</b>" + esc(h.impact_cn) + "</p>" : "") +
      (rows ? '<div class="hpi-sub"><h4>近期监测到的传染病事件</h4><ul class="hpi-list hpi-tight">' + rows + "</ul></div>"
            : '<div class="hpi-empty">近期无可用传染病事件数据</div>') +
      '<p class="hpi-note">仅呈现既有监测数据，不作医学预测。趋势 ' + esc(HEALTH_TREND_CN[h.trend] || "尚不明朗") +
      "；置信度 " + esc(CONF_CN[h.confidence] || "低") + "。</p>";
  }

  /* ⑦ 最新情报流 */
  function renderFeed(d) {
    var el = host("hpiFeed"); if (!el) return;
    var rows = d.latest_intelligence || [];
    var tabs = [["all", "全部"], ["terrorism_conflict", "恐袭/冲突"], ["political_social", "政治社会"],
                ["crime_public_security", "治安犯罪"], ["military_border_maritime", "军事边境"],
                ["accident_disruption", "事故灾害"]];
    el.innerHTML = '<div class="hpi-tabs">' + tabs.map(function (t, i) {
      return '<button class="hpi-tab' + (i === 0 ? " is-on" : "") + '" data-k="' + t[0] + '">' + t[1] + "</button>";
    }).join("") + '</div><div class="hpi-feed-list" id="hpiFeedList"></div>';
    var list = host("hpiFeedList");
    function draw(k) {
      var r = rows.filter(function (x) { return k === "all" || x.sector === k; });
      list.innerHTML = r.length ? r.map(function (x) {
        return '<div class="hpi-feed-row"><a class="hpi-cc" href="' + esc(href(x)) + '">' + esc(x.country) + "</a>" +
          '<span class="hpi-feed-main"><a class="hpi-feed-t" href="' + esc(href(x)) + '"><b>' + esc(x.title_cn) + "</b></a>" +
          (x.localized ? "" : '<i class="hpi-orig">原文</i>') +
          '<i class="hpi-feed-meta">' + esc(x.category_cn) + " ｜ " + esc(x.source) +
          " ｜ <span title=\"" + esc(TIER_CN[x.tier] || "") + "\">" + esc(x.tier || "C") + "</span>" +
          (x.source_count > 1 ? " ｜ " + x.source_count + " 个来源" : "") +
          (x.importance === "high" ? ' ｜ <b class="hpi-imp">重要</b>' : "") + "</i></span>" +
          '<span class="hpi-feed-side">' + statusTag(x) + '<em class="hpi-t">' + esc(shortTime(x.time)) + "</em></span></div>";
      }).join("") : '<div class="hpi-empty">该分类近 7 日暂无条目</div>';
    }
    draw("all");
    el.querySelectorAll(".hpi-tab").forEach(function (b) {
      b.addEventListener("click", function () {
        el.querySelectorAll(".hpi-tab").forEach(function (x) { x.classList.remove("is-on"); });
        b.classList.add("is-on"); draw(b.getAttribute("data-k"));
      });
    });
  }

  /* ⑧ 日报与周报（直达当期报告） */
  function renderReports(d) {
    var el = host("hpiReports"); if (!el) return;
    var r = d.reports || {};
    function card(cn, en, id, title, period, hrefv) {
      if (!id) return '<div class="hpi-rep hpi-empty">当期' + cn + "尚未生成</div>";
      return '<a class="hpi-rep" href="' + esc(hrefv) + '"><span class="hpi-rep-k">' + cn +
        '<i class="hpi-en">' + en + "</i></span><b>" + esc(title || id) + "</b>" +
        (period ? "<em>" + esc(period) + "</em>" : "") + '<span class="hpi-cc">打开报告 →</span></a>';
    }
    el.innerHTML = '<div class="hpi-reps">' +
      card("非洲日报", "DAILY BRIEF", r.daily_id, r.daily_title, r.daily_period, r.daily_href) +
      card("非洲周报", "WEEKLY BRIEF", r.weekly_id, r.weekly_title, r.weekly_period, r.weekly_href) +
      '<a class="hpi-rep is-all" href="reports.html"><span class="hpi-rep-k">全部报告<i class="hpi-en">ALL REPORTS</i></span>' +
      "<b>报告中心</b><span class=\"hpi-cc\">查看全部 →</span></a></div>";
  }

  function init() {
    busy(["hpiOverview", "hpiSectors", "hpiTop", "hpiChina", "hpiHealth", "hpiFeed"], "加载中…");
    loadView().then(function (d) {
      try { renderOverview(d); } catch (e) { busy(["hpiOverview"], "态势概览渲染失败"); }
      try { renderSectors(d); } catch (e) { busy(["hpiSectors"], "领域分析渲染失败"); }
      try { renderTop(d); } catch (e) { busy(["hpiTop"], "重点动态渲染失败"); }
      try { renderChina(d); } catch (e) { busy(["hpiChina"], "涉华影响渲染失败"); }
      try { renderHealth(d); } catch (e) { busy(["hpiHealth"], "健康板块渲染失败"); }
      try { renderFeed(d); } catch (e) { busy(["hpiFeed"], "情报流渲染失败"); }
      try { renderReports(d); } catch (e) { busy(["hpiReports"], "报告板块渲染失败"); }
    }).catch(function () {
      busy(["hpiOverview", "hpiSectors", "hpiTop", "hpiChina", "hpiHealth", "hpiFeed"],
           "情报视图暂不可用，请稍后重试");
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
