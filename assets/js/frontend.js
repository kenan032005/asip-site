/* ============================================================
   ASIP Stage 8A — Frontend Product Integration V1
   统一前端渲染引擎：消费 PUBLIC-SAFE FRONTEND VIEWS
   （API.get("site_overview") / "master_events" / ...）
   前端绝不读 data/runtime；绝不让 AI 打分/预测。
   ============================================================ */
(function () {
  "use strict";

  // ── 顶部导航（§三：全站统一 6 项；Mobile 折叠）──
  var NAV = [
    ["index.html", "首页", "home"],
    ["events.html", "态势事件", "events"],
    ["countries.html", "国家", "countries"],
    ["disease-risk.html", "疾病风险", "disease"],
    ["intelligence/africa/", "情报知识库", "intelligence"],
    ["reports.html", "报告", "reports"]
  ];

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/[&<>"']/g, function (c) {
        return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
      });
  }

  function dash(v) { return (v === null || v === undefined || v === "") ? "—" : v; }

  // 北京时间（§三十四）：统一 "YYYY-MM-DD HH:mm（北京时间）"
  function bj(s) {
    if (!s) return "—";
    s = String(s);
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s + "（北京时间）";
    var m = s.match(/(\d{4})-(\d{2})-(\d{2})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?/);
    if (!m) return s;
    var ms = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)) + 8 * 3600 * 1000;
    var d = new Date(ms);
    function p(n) { return (n < 10 ? "0" : "") + n; }
    return d.getUTCFullYear() + "-" + p(d.getUTCMonth() + 1) + "-" + p(d.getUTCDate()) +
      " " + p(d.getUTCHours()) + ":" + p(d.getUTCMinutes()) + "（北京时间）";
  }
  function bjShort(s) { return bj(s).replace("（北京时间）", ""); }

  // ── Verification Badge（§八/§三十三：与风险色区分，描边式）──
  var V_STYLE = {
    verified: ["已核实", "#15803d"], probable: ["较可信", "#2563eb"],
    partial: ["部分核实", "#6b7280"], single_source: ["单一来源", "#b45309"],
    conflicting: ["信息存在冲突", "#b91c1c"], pending: ["待进一步核实", "#6b7280"],
    unverified: ["未经证实", "#6b7280"]
  };
  function vBadge(v) {
    var s = V_STYLE[v] || [v || "—", "#6b7280"];
    return '<span class="fe-badge fe-verify" style="color:' + s[1] +
      ';border:1px solid ' + s[1] + '">' + esc(s[0]) + "</span>";
  }
  // ── Change Badge（§七）──
  var C_STYLE = {
    initial_report: ["NEW", "新报"], new_event: ["NEW", "新报"],
    casualty_increase: ["UPDATED", "伤亡更新"], injury_increase: ["UPDATED", "受伤更新"],
    official_confirmation: ["OFFICIAL", "官方确认"], actor_attribution_change: ["ATTRIB", "归因变化"],
    location_expansion: ["SPREAD", "地点扩展"], status_change: ["UPDATED", "状态变化"],
    correction: ["CORRECTED", "更正"], conflict_detected: ["CONFLICT", "信息冲突"],
    closed: ["CLOSED", "已结束"], new_outbreak: ["OUTBREAK", "新暴发"],
    case_increase: ["CASES", "病例增加"], mortality_increase: ["DEATHS", "死亡增加"],
    geographic_spread: ["SPREAD", "疫情扩散"], final_update: ["FINAL", "最终更新"]
  };
  function cBadge(c) {
    var s = C_STYLE[c] || (c ? [c.toUpperCase(), ""] : null);
    if (!s) return "";
    return '<span class="fe-badge fe-change" title="变化类型：' + esc(c) +
      '">' + esc(s[1] || s[0]) + "</span>";
  }

  // ── 统一 Empty/Error/Delayed（§三十六）──
  function emptyState(msg) {
    return '<div class="fe-empty">' + esc(msg || "当前无符合发布条件的内容。") + "</div>";
  }
  function errorState(msg) {
    return '<div class="fe-error">⚠ ' + esc(msg || "模块加载失败，请刷新重试。") + "</div>";
  }
  function delayedNote(msg) {
    return '<div class="fe-delayed">⏱ ' + esc(msg || "数据更新存在延迟，最近成功更新时间见页脚。") + "</div>";
  }

  // ── 加载器：__DB__ 优先，失败给空态 ──
  function load(name) {
    return API.get(name).then(function (d) { return { ok: true, data: d }; })
      .catch(function () { return { ok: false, data: null }; });
  }

  // ── 导航渲染（§三）──
  function renderNav(active) {
    var bar = document.getElementById("topbar");
    if (!bar) return;
    var links = NAV.map(function (n) {
      var cls = (n[2] === active) ? ' class="active"' : "";
      return '<a href="' + n[0] + '"' + cls + ">" + esc(n[1]) + "</a>";
    }).join("");
    bar.innerHTML =
      '<div class="top-row">' +
      '<div class="brand"><b>非洲地区社会安全信息平台</b><span>Africa Security Information Platform</span></div>' +
      '<div class="meta" id="topmeta">🕐 北京时间 <b id="clBJ">--:--:--</b>' +
      '<span class="muted" id="updLine">更新：<b id="hdrUpdated">--</b></span>' +
      '<button class="nav-toggle" id="navToggle" aria-label="菜单">☰</button></div>' +
      '</div>' +
      '<nav class="navbar" id="navbar">' + links + "</nav>";
    var toggle = document.getElementById("navToggle");
    var navbar = document.getElementById("navbar");
    if (toggle && navbar) {
      toggle.addEventListener("click", function () {
        navbar.classList.toggle("open");
      });
    }
    tickClock();
    if (!window.__clockTimer__) window.__clockTimer__ = setInterval(tickClock, 1000);
    API.getCached("status").then(function (st) {
      var t = (st && (st.last_update_bj || st.generated_at_bj)) || null;
      if (t) {
        var el = document.getElementById("hdrUpdated");
        if (el) el.textContent = t;
      }
    }).catch(function () {});
  }
  function tickClock() {
    var bj = document.getElementById("clBJ");
    if (!bj) return;
    bj.textContent = new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(11, 19);
  }

  // ── 首页（§四-§八）──
  function renderHome() {
    Promise.all([load("site_overview"), load("master_events"),
                 load("disease_outbreaks"), load("country_snapshots"),
                 load("report_index"), load("knowledge_summary"),
                 load("countries"), load("risk-levels"), load("status")])
      .then(function (R) {
        var ov = R[0], me = R[1], dis = R[2], cs = R[3], ri = R[4], ks = R[5];
        var countries = ((R[6].ok ? R[6].data : {}) || {}).countries || [];
        var risk = (R[7].ok ? R[7].data : {}) || {};
        var st = (R[8].ok ? R[8].data : {}) || {};

        // A. Situation Header
        var header = document.getElementById("feSituationHeader");
        if (header) {
          var ovd = ov.ok ? ov.data : null;
          var cutoff = (ovd && ovd.latest_data_time_bj) || st.last_update_bj || "--";
          var statusTxt = (ovd && ovd.data_status_text) || "数据正常";
          var statusCls = (ovd && ovd.data_status === "delayed") ? "delayed" :
            ((ovd && ovd.data_status === "degraded") ? "degraded" : "ok");
          header.innerHTML =
            '<div class="fe-sit-left"><h1>非洲地区社会安全信息平台</h1>' +
            '<p class="fe-sub">Africa Security Information Platform · 所有时间均为北京时间（UTC+8）</p>' +
            '<p class="fe-cutoff">数据更新时间：' + esc(bj(cutoff)) +
            '　<span class="fe-status ' + statusCls + '">当前态势：' + esc(statusTxt) + "</span></p>" +
            '<p class="fe-note">' + (ovd && ovd.data_status === "current"
              ? "最新正式研判见今日非洲日报（开发阶段为样例）。"
              : "数据更新存在延迟，最近成功更新时间见上。") + "</p></div>";
        }

        // B. KPI（§六：最多 6 个，确定性）
        var kpi = document.getElementById("feKpis");
        if (kpi && ov.ok) {
          var k = ov.data.kpis;
          var items = [
            ["24h 新增重大事件", dash(k.events_24h)],
            ["72h 持续关注", dash(k.events_72h_ongoing)],
            ["重点关注国家", dash(k.priority_country_count)],
            ["已核实 / 较可信事件", dash(k.verified_probable_count)],
            ["活跃疾病暴发", dash(k.active_outbreaks)],
            ["最新日报", (k.latest_daily && k.latest_daily.generated_at)
              ? "样例" : "待启用"]
          ];
          kpi.innerHTML = items.map(function (it) {
            return '<div class="fe-kpi"><div class="fe-kpi-v">' + esc(it[1]) +
              '</div><div class="fe-kpi-l">' + esc(it[0]) + "</div></div>";
          }).join("");
        }

        // C. Major Developments（§七：5-8 条 master，去重）
        var major = document.getElementById("feMajor");
        if (major) {
          var evs = (me.ok && me.data && me.data.events) || [];
          var list = evs.slice(0, 8);
          major.innerHTML = list.length ? list.map(masterCard).join("")
            : emptyState("当前无符合发布条件的事件。");
        }

        // D. Priority Countries（§十二）
        var pc = document.getElementById("fePriority");
        if (pc) {
          var snaps = (cs.ok && cs.data && cs.data.snapshots) || [];
          var prio = snaps.filter(function (s) { return (s.baseline_risk_level || 0) >= 3; }).slice(0, 6);
          pc.innerHTML = prio.length ? prio.map(function (s) {
            return '<a class="fe-country-chip" href="country.html?country=' +
              encodeURIComponent(s.country_cn) + '">' +
              '<span class="risk-' + (s.baseline_risk_level || 1) + '">' +
              esc(s.baseline_risk || "低") + "</span> " + esc(s.country_cn) +
              '<small>24h:' + dash(s.events_24h) + " · 7d:" + dash(s.events_7d) + "</small></a>";
          }).join("") : emptyState("暂无优先国家。");
        }

        // E. Disease Risk（§十五）
        var dr = document.getElementById("feDisease");
        if (dr) {
          var os = (dis.ok && dis.data && dis.data.outbreaks) || [];
          var active = os.filter(function (o) {
            return ["active", "developing", "increasing", "geographic_spread", "monitoring"]
              .indexOf(String(o.status || "").toLowerCase()) >= 0;
          }).slice(0, 5);
          dr.innerHTML = active.length
            ? '<div class="fe-outbreak-row">' + active.map(outbreakMini).join("") + "</div>" +
              '<p class="fe-more"><a href="disease-risk.html">查看全部疫情 →</a></p>'
            : emptyState("当前无符合发布条件的活跃疫情。");
        }

        // F. 7-Day Watch（§四 F：master 中 7 天内的持续关注）
        var watch = document.getElementById("feWatch");
        if (watch) {
          var watchEvs = (me.ok && me.data && me.data.events || []).filter(function (e) {
            return (e.update_count || 0) > 1;
          }).slice(0, 6);
          watch.innerHTML = watchEvs.length
            ? '<ul class="fe-watch">' + watchEvs.map(function (e) {
                return "<li><a href='event.html?id=" + encodeURIComponent(e.master_event_id) +
                  "'>" + esc(e.headline_zh) + "</a> " + cBadge(e.change_type) +
                  " <small>" + esc(e.country_cn || "") + " · 更新 " + (e.update_count || 0) + " 次</small></li>";
              }).join("") + "</ul>"
            : emptyState("暂无持续发展中的事件。");
        }

        // G. Latest Report（§十八：明确开发样例）
        var lr = document.getElementById("feLatestReport");
        if (lr) {
          var reps = (ri.ok && ri.data && ri.data.reports) || [];
          var daily = reps.filter(function (r) { return r.type === "africa_daily"; })[0];
          lr.innerHTML = daily
            ? '<p class="fe-report-line">' + esc(daily.title) +
              '　<span class="fe-badge fe-mock">MOCK / 开发样例 · 非正式情报报告</span>' +
              ' <a class="btn sm ghost" href="' + daily.path + '" target="_blank">查看样例</a>' +
              ' <a class="btn sm ghost" href="reports.html">报告中心</a></p>'
            : '<p class="fe-report-line">正式日报生成能力待 Production AI 启用。' +
              ' <a class="btn sm ghost" href="reports.html">报告中心</a></p>';
        }

        // H. Intelligence 入口（§二十三）
        var intel = document.getElementById("feIntelligence");
        if (intel && ks.ok) {
          var kd = ks.data;
          intel.innerHTML =
            '<p>已收录实体 <b>' + dash(kd.entity_count) + "</b> · 已收录关系 <b>" +
            dash(kd.relationship_count) + "</b> · 区域 <b>" + dash(kd.region_count) +
            "</b> · 国家 <b>" + dash(kd.country_count) + "</b></p>" +
            '<p><a class="btn sm" href="intelligence/africa/">进入情报知识库 →</a></p>' +
            '<p class="fe-note">实体与关系仅来自人工维护的知识库（manual update only）。</p>';
        }

        // I. Data / Verification Status（§三十七）
        var dv = document.getElementById("feDataStatus");
        if (dv) {
          var vs = (ov.ok && ov.data && ov.data.verification_summary) || {};
          var labels = { verified: "已核实", probable: "较可信", single_source: "单一来源",
                         conflicting: "冲突", partial: "部分核实", pending: "待核实" };
          var chips = Object.keys(vs).map(function (k) {
            return '<span class="fe-ver-chip">' + esc(labels[k] || k) + "：" + vs[k] + "</span>";
          }).join(" ");
          dv.innerHTML = (ov.ok && ov.data && ov.data.data_status === "current"
              ? '<p>数据状态：<b class="fe-status ok">正常</b></p>' : delayedNote(
              "数据更新存在延迟，最近成功更新时间：" +
              ((ov.ok && ov.data && ov.data.latest_data_time_bj) || "—") + "。")) +
            '<p>' + chips + "</p>";
        }
        renderFooterStatus(st);
      });
  }

  function renderFooterStatus(st) {
    var f = document.querySelector("footer.site");
    if (f) {
      var meta = document.getElementById("asip-build-meta");
      var s = (st && st.last_update_bj) ? "数据更新：" + st.last_update_bj : "";
      if (meta) meta.textContent = s;
    }
  }

  // ── Master Event Card（§七/§十）──
  function masterCard(e) {
    var time = bjShort(e.latest_update_at || e.event_time);
    return '<a class="fe-me-card" href="event.html?id=' + encodeURIComponent(e.master_event_id) + '">' +
      '<div class="fe-me-head">' +
      '<span class="fe-me-country">' + esc(e.country_cn || e.country_iso3 || "非洲") + "</span>" +
      cBadge(e.change_type) + vBadge(e.verification_status) + "</div>" +
      '<div class="fe-me-title">' + esc(e.headline_zh) + "</div>" +
      (e.headline_en ? '<div class="fe-me-en">' + esc(String(e.headline_en).slice(0, 110)) + "</div>" : "") +
      '<div class="fe-me-meta">' +
      (e.event_type_cn ? esc(e.event_type_cn) + " · " : "") +
      "来源 " + dash(e.source_count) + " 个 · 独立 " + dash(e.independent_source_count) + " 个 · " +
      time + "</div>" +
      '<div class="fe-me-fact">' + esc(e.fact_summary || "") + "</div>" +
      "</a>";
  }

  function outbreakMini(o) {
    var lc = o.latest_counts || {};
    return '<a class="fe-ob-mini" href="disease-risk.html#outbreak=' +
      encodeURIComponent(o.outbreak_id) + '">' +
      '<div class="fe-ob-name">' + esc(o.disease_name_cn || o.disease_id) +
      " <small>" + esc(o.country_cn || o.country_iso3 || "") + "</small></div>" +
      '<div class="fe-ob-status">' + esc(o.status_cn || o.status || "—") + "</div>" +
      '<div class="fe-ob-num">确诊 ' + dash(lc.confirmed_cases) + " · 死亡 " +
      dash(lc.deaths) + " · " + esc(bjShort(o.latest_report_at)) + "</div>" +
      "</a>";
  }

  // ── 事件列表页（§十：master-centric）──
  function renderEvents() {
    Promise.all([load("master_events"), load("site_overview")]).then(function (R) {
      var me = R[0], ov = R[1];
      var evs = (me.ok && me.data && me.data.events) || [];
      var host = document.getElementById("feEventsList");
      if (!host) return;
      if (!evs.length) { host.innerHTML = emptyState("当前无符合发布条件的事件。"); return; }
      var filter = document.getElementById("feEvFilter");
      if (filter) {
        filter.innerHTML = '<select id="feEvType">' +
          '<option value="">全部类型</option>' +
          Array.from(new Set(evs.map(function (e) { return e.event_type_cn; }).filter(Boolean)))
            .sort().map(function (t) { return '<option>' + esc(t) + "</option>"; }).join("") +
          "</select>" +
          '<select id="feEvCountry">' +
          '<option value="">全部国家</option>' +
          Array.from(new Set(evs.map(function (e) { return e.country_cn; }).filter(Boolean)))
            .sort().map(function (c) { return "<option>" + esc(c) + "</option>"; }).join("") +
          "</select>";
        filter.addEventListener("change", function () {
          var t = document.getElementById("feEvType").value;
          var c = document.getElementById("feEvCountry").value;
          var flt = evs.filter(function (e) {
            return (!t || e.event_type_cn === t) && (!c || e.country_cn === c);
          });
          host.innerHTML = flt.length ? flt.map(masterCard).join("")
            : emptyState("无匹配事件。");
        });
      }
      host.innerHTML = evs.slice(0, 30).map(masterCard).join("") ||
        emptyState("当前无符合发布条件的事件。");
      if (ov.ok && ov.data && ov.data.data_status !== "current") {
        var warn = document.getElementById("feDelayedWarn");
        if (warn) warn.innerHTML = delayedNote();
      }
    });
  }

  // ── 事件详情页（§九/§十一：Master Event + Timeline）──
  function renderEventDetail() {
    var id = new URLSearchParams(location.search).get("id");
    Promise.all([load("master_events"), load("event_timelines")]).then(function (R) {
      var me = R[0], tl = R[1];
      var evs = (me.ok && me.data && me.data.events) || [];
      var e = evs.find(function (x) { return x.master_event_id === id; });
      var host = document.getElementById("feEventDetail");
      if (!host) return;
      if (!e) {
        host.innerHTML = emptyState("未找到该事件（可能不在当前公开视图内）。");
        return;
      }
      var tls = (tl.ok && tl.data && tl.data.timelines) || {};
      var updates = tls[id] || [];
      var html = '<div class="fe-ev-head">' +
        '<h1>' + esc(e.headline_zh) + "</h1>" +
        (e.headline_en ? '<p class="fe-ev-en">' + esc(e.headline_en) + "</p>" : "") +
        '<p>' + vBadge(e.verification_status) + " " + cBadge(e.change_type) +
        " 来源 " + dash(e.source_count) + " 个 · 独立来源 " + dash(e.independent_source_count) +
        " 个</p></div>";
      // 基本信息
      html += '<div class="fe-ev-sec"><h2>事件信息</h2><table class="fe-tbl">' +
        row("国家 / 地区", esc(e.country_cn || "—") + (e.location ? " · " + esc(e.location) : "")) +
        row("事件类型", esc(e.event_type_cn || "—")) +
        row("首次报道", esc(bj(e.event_time))) +
        row("最近更新", esc(bj(e.latest_update_at))) +
        row("事件状态", esc(e.timeline_status || "—")) +
        "</table></div>";
      // 事实摘要
      html += '<div class="fe-ev-sec"><h2>事实摘要</h2><p class="fe-fact">' +
        esc(e.fact_summary || "—") + "</p></div>";
      // 最新状态
      html += '<div class="fe-ev-sec"><h2>最新状态</h2><p>' +
        esc((e.uncertainties && e.uncertainties.length)
          ? "存在不确定性：" + e.uncertainties.join("；")
          : "当前无已记录的不确定性项。") + "</p></div>";
      // Timeline（§十一：update_count > 1 才显示）
      if (updates.length > 1) {
        html += '<div class="fe-ev-sec"><h2>事件更新时间线</h2><div class="fe-timeline">' +
          updates.map(function (u, i) {
            var src = u.source_ref || {};
            return '<div class="fe-tl-item"><div class="fe-tl-time">' + esc(bj(u.time)) + "</div>" +
              '<div class="fe-tl-body"><b>' + esc(u.update_type_cn) + "</b>" +
              (u.fact_change ? " <small>(" + esc(u.fact_change) + ")</small>" : "") +
              "<div class='fe-tl-src'>来源：" + esc(src.source_name || src.source_id || "—") +
              (src.title ? " · " + esc(String(src.title).slice(0, 60)) : "") + "</div></div></div>";
          }).join("") + "</div></div>";
      } else if (updates.length === 1) {
        html += '<div class="fe-ev-sec"><h2>事件更新时间线</h2><p class="muted">该事件当前仅有首次报道，暂无更多结构化更新。</p></div>';
      }
      // 来源证据
      var srcs = [];
      updates.forEach(function (u) {
        var s = u.source_ref || {};
        if (s.url && srcs.indexOf(s.url) < 0) srcs.push(s);
      });
      html += '<div class="fe-ev-sec"><h2>来源证据</h2>' +
        (srcs.length ? '<ul class="fe-srcs">' + srcs.map(function (s) {
          return '<li><a href="' + esc(s.url) + '" target="_blank" rel="noopener noreferrer">' +
            esc(s.source_name || s.source_id || "来源") + "</a>" +
            (s.title ? " — " + esc(String(s.title).slice(0, 90)) : "") + "</li>";
        }).join("") + "</ul>"
          : '<p class="muted">来源链接信息见各更新条目。</p>') + "</div>";
      // 不确定性/冲突
      var conflicts = e.conflict_flags || [];
      html += '<div class="fe-ev-sec"><h2>不确定性 / 冲突</h2><p>' +
        (conflicts.length ? "来源冲突标记：" + esc(conflicts.join("；"))
          : (e.uncertainties && e.uncertainties.length
            ? esc(e.uncertainties.join("；")) : "无。")) + "</p></div>";
      // 相关
      html += '<div class="fe-ev-sec"><h2>相关</h2><p><a href="events.html">← 返回态势事件</a> · ' +
        '<a href="country.html?country=' + encodeURIComponent(e.country_cn || "") + '">国家页 →</a></p></div>';
      host.innerHTML = html;
    });
  }

  function row(k, v) {
    return "<tr><th>" + esc(k) + "</th><td>" + v + "</td></tr>";
  }

  // ── 国家总页（§十二）──
  function renderCountries() {
    Promise.all([load("country_snapshots"), load("countries"), load("risk-levels")])
      .then(function (R) {
        var cs = R[0], countries = ((R[1].ok ? R[1].data : {}) || {}).countries || [];
        var risk = (R[2].ok ? R[2].data : {}) || {};
        var host = document.getElementById("feCountries");
        if (!host) return;
        var snaps = (cs.ok && cs.data && cs.data.snapshots) || [];
        // 按风险分组
        var tiers = (risk.tiers || []).map(function (t) {
          var list = snaps.filter(function (s) {
            return countries.some(function (c) {
              return c.cn === s.country_cn && c.tier === t.tier;
            });
          }).map(countryCard).join("");
          return list ? '<div class="tier-block"><div class="tier-head"><span class="tier-name">' +
            esc(t.label) + '</span><span class="tier-count">' + snaps.filter(function (s) {
              return countries.some(function (c) {
                return c.cn === s.country_cn && c.tier === t.tier;
              });
            }).length + ' 国</span></div><div class="matrix">' + list + "</div></div>" : "";
        }).join("");
        host.innerHTML = tiers || emptyState("暂无国家快照。");
        // Priority Quick View（§十二）
        var pq = document.getElementById("fePriorityQuick");
        if (pq) {
          var prio = snaps.filter(function (s) { return (s.baseline_risk_level || 0) >= 3; });
          pq.innerHTML = prio.length ? prio.map(function (s) {
            return '<a class="fe-pq" href="country.html?country=' +
              encodeURIComponent(s.country_cn) + '">' +
              '<b>' + esc(s.country_cn) + "</b> " +
              '<span class="risk-' + (s.baseline_risk_level || 1) + '">' +
              esc(s.baseline_risk || "—") + "</span>" +
              "<small>24h " + dash(s.events_24h) + " · 7d " + dash(s.events_7d) +
              " · 疫情 " + dash(s.active_outbreaks) + "</small></a>";
          }).join("") : emptyState("暂无优先国家。");
        }
      });
  }

  function countryCard(s) {
    var l = s.latest_major_event || {};
    return '<a class="country-card fe-cc" style="border-left-color:var(--brand);" href="country.html?country=' +
      encodeURIComponent(s.country_cn) + '">' +
      '<div class="cn">' + esc(s.country_cn) + "</div>" +
      '<div class="en">' + esc(s.country_en || "") + "</div>" +
      '<div class="region">' + esc(s.region || "") + "</div>" +
      '<div class="meta-row"><span class="badge risk-' + (s.baseline_risk_level || 1) + '">' +
      esc(s.baseline_risk || "—") + '</span></div>' +
      '<div class="fe-cc-meta">24h ' + dash(s.events_24h) + " · 7d " + dash(s.events_7d) +
      " · 疫情 " + dash(s.active_outbreaks) + "</div>" +
      (l.title ? '<div class="fe-cc-last">最新：' + esc(String(l.title).slice(0, 40)) + "</div>" : "") +
      "</a>";
  }

  // ── 国家页（§十三/§十四：A-I + Graceful Empty）──
  function renderCountry() {
    var cn = new URLSearchParams(location.search).get("country") || "";
    Promise.all([load("country_snapshots"), load("master_events"),
                 load("disease_outbreaks"), load("report_index")]).then(function (R) {
      var cs = R[0], me = R[1], dis = R[2], ri = R[3];
      var snaps = (cs.ok && cs.data && cs.data.snapshots) || [];
      var s = snaps.find(function (x) { return x.country_cn === cn; });
      var host = document.getElementById("feCountry");
      if (!host) return;
      if (!s) {
        host.innerHTML = '<h1>' + esc(cn || "国家") + '</h1>' + emptyState(
          "该国家暂无公开快照数据。");
        return;
      }
      var iso = s.iso3 || "";
      // 该国 master 事件（按 iso 或 cn 匹配）
      var evs = ((me.ok && me.data && me.data.events) || []).filter(function (e) {
        return e.country_iso3 === iso || e.country_cn === cn;
      });
      var obs = ((dis.ok && dis.data && dis.data.outbreaks) || []).filter(function (o) {
        return o.country_iso3 === iso || o.country_cn === cn;
      });
      var wks = ((ri.ok && ri.data && ri.data.reports) || []).filter(function (r) {
        return r.country_iso3 === iso && r.type === "country_weekly";
      });
      var l = s.latest_major_event || {};
      var html = '<div class="fe-cy-head"><h1>' + esc(s.country_cn) + "</h1>" +
        '<p>' + esc(s.country_en || "") + (s.region ? " · " + esc(s.region) : "") +
        " · 基准风险 " + '<span class="badge risk-' + (s.baseline_risk_level || 1) + '">' +
        esc(s.baseline_risk || "—") + "</span>" + "</p></div>";
      // B. Current Situation（§十三 B：无正式周报 → 确定性/空态）
      html += '<div class="fe-ev-sec"><h2>当前态势</h2>' +
        (wks.length
          ? '<p>' + esc(wks[0].title) + "（" + esc(wks[0].status_cn) + "）<a href='" +
            wks[0].path + "' target='_blank'>查看样例</a></p>"
          : '<p class="muted">最新国家周报尚未生成（正式生成能力待 Production AI 启用）。</p>') +
        "</div>";
      // C. Key Metrics
      html += '<div class="fe-ev-sec"><h2>关键指标</h2><div class="fe-kpi-row">' +
        kpiSmall("24h 事件", dash(s.events_24h)) + kpiSmall("7d 事件", dash(s.events_7d)) +
        kpiSmall("活跃疫情", dash(s.active_outbreaks)) + kpiSmall("最近更新", bjShort(s.last_updated)) +
        "</div></div>";
      // D. Latest Major Events（§十三 D）
      html += '<div class="fe-ev-sec"><h2>主要事件</h2>' +
        (evs.length ? evs.slice(0, 10).map(masterCard).join("")
          : emptyState("该国家当前无符合发布条件的事件。")) + "</div>";
      // E. Event Timeline / Recent Changes
      html += '<div class="fe-ev-sec"><h2>事件时间线 / 近期变化</h2>' +
        (evs.filter(function (e) { return (e.update_count || 0) > 1; }).length
          ? evs.filter(function (e) { return (e.update_count || 0) > 1; }).slice(0, 5).map(function (e) {
              return "<p><a href='event.html?id=" + encodeURIComponent(e.master_event_id) + "'>" +
                esc(e.headline_zh) + "</a> " + cBadge(e.change_type) +
                " <small>更新 " + (e.update_count || 0) + " 次</small></p>";
            }).join("")
          : '<p class="muted">暂无多更新事件时间线。</p>') + "</div>";
      // F. Disease（§十三 F）
      html += '<div class="fe-ev-sec"><h2>公共卫生 / 疾病</h2>' +
        (obs.length ? obs.map(function (o) {
          var lc = o.latest_counts || {};
          return "<p><a href='disease-risk.html#outbreak=" + encodeURIComponent(o.outbreak_id) + "'>" +
            esc(o.disease_name_cn || o.disease_id) + "</a> " +
            '<span class="fe-ob-status">' + esc(o.status_cn || "—") + "</span>" +
            " 确诊 " + dash(lc.confirmed_cases) + " · 死亡 " + dash(lc.deaths) +
            " · " + esc(bjShort(o.latest_report_at)) + "</p>";
        }).join("")
          : '<p class="muted">当前无符合发布条件的活跃疫情。</p>') + "</div>";
      // G. Key Entities（§十三 G：知识库连接，approved only）
      html += '<div class="fe-ev-sec"><h2>关键实体</h2><p class="muted">' +
        '实体与事件互联需基于已核准的 entity reference；当前公开视图暂无已核准关联。' +
        ' 可前往 <a href="intelligence/africa/">情报知识库</a> 浏览。' + "</p></div>";
      // H. Latest Weekly Report（§十三 H）
      html += '<div class="fe-ev-sec"><h2>最新周报</h2>' +
        (wks.length
          ? '<p><a href="' + wks[0].path + '" target="_blank">' + esc(wks[0].title) +
            "</a>（开发样例，非正式情报报告）</p>"
          : '<p class="muted">最新国家周报尚未生成。</p>') + "</div>";
      // I. Sources / Verification Notes
      html += '<div class="fe-ev-sec"><h2>来源与核验说明</h2><p class="muted">' +
        "本页事件与疫情数字均来自确定性数据层；单一来源与冲突项已显式标注。" +
        "</p></div>";
      host.innerHTML = html;
    });
  }

  function kpiSmall(k, v) {
    return '<div class="fe-kpi-sm"><b>' + esc(v) + "</b><span>" + esc(k) + "</span></div>";
  }

  // ── 疾病风险 Dashboard（§十五/§十六）──
  function renderDisease() {
    Promise.all([load("disease_outbreaks"), load("master_events")]).then(function (R) {
      var dis = R[0];
      var os = (dis.ok && dis.data && dis.data.outbreaks) || [];
      var host = document.getElementById("feDiseaseList");
      if (!host) return;
      // filter
      var filter = document.getElementById("feDisFilter");
      if (filter) {
        filter.innerHTML =
          '<select id="feDisCountry"><option value="">全部国家</option>' +
          Array.from(new Set(os.map(function (o) { return o.country_cn; }).filter(Boolean)))
            .sort().map(function (c) { return "<option>" + esc(c) + "</option>"; }).join("") +
          "</select>" +
          '<select id="feDisDisease"><option value="">全部疾病</option>' +
          Array.from(new Set(os.map(function (o) { return o.disease_name_cn || o.disease_id; }).filter(Boolean)))
            .sort().map(function (d) { return "<option>" + esc(d) + "</option>"; }).join("") +
          "</select>" +
          '<select id="feDisStatus"><option value="">全部状态</option>' +
          Array.from(new Set(os.map(function (o) { return o.status_cn; }).filter(Boolean)))
            .sort().map(function (s) { return "<option>" + esc(s) + "</option>"; }).join("") +
          "</select>";
        filter.addEventListener("change", function () {
          var c = document.getElementById("feDisCountry").value;
          var d = document.getElementById("feDisDisease").value;
          var s = document.getElementById("feDisStatus").value;
          var flt = os.filter(function (o) {
            return (!c || o.country_cn === c) &&
                   (!d || (o.disease_name_cn || o.disease_id) === d) &&
                   (!s || o.status_cn === s);
          });
          host.innerHTML = flt.length ? flt.map(outbreakCard).join("")
            : emptyState("无匹配疫情。");
        });
      }
      // Active Outbreaks（§十五 顶部）
      var active = document.getElementById("feDisActive");
      if (active) {
        var act = os.filter(function (o) {
          return ["active", "developing", "increasing", "geographic_spread", "monitoring"]
            .indexOf(String(o.status || "").toLowerCase()) >= 0;
        });
        active.innerHTML = act.length
          ? '<div class="fe-outbreak-row">' + act.map(outbreakMini).join("") + "</div>"
          : emptyState("当前无符合发布条件的活跃疫情。");
      }
      host.innerHTML = os.length ? os.map(outbreakCard).join("")
        : emptyState("当前无符合发布条件的疫情数据。");
      // detail panel（§十六，hash: #outbreak=ID）
      applyOutbreakHash(os);
    });
  }

  function outbreakCard(o) {
    var lc = o.latest_counts || {};
    var dl = o.delta || {};
    return '<a class="fe-ob-card" href="#outbreak=' + encodeURIComponent(o.outbreak_id) + '">' +
      '<div class="fe-ob-card-h"><b>' + esc(o.disease_name_cn || o.disease_id) + "</b> " +
      '<span class="fe-ob-status">' + esc(o.status_cn || "—") + "</span></div>" +
      "<div>" + esc(o.country_cn || o.country_iso3 || "—") + "</div>" +
      '<div class="fe-ob-nums">确诊 <b>' + dash(lc.confirmed_cases) + "</b>" +
      (dl.confirmed_cases ? ' <small>(+' + dl.confirmed_cases + ")</small>" : "") +
      " · 疑似 <b>" + dash(lc.suspected_cases) + "</b> · 死亡 <b>" + dash(lc.deaths) + "</b>" +
      (dl.deaths ? ' <small>(+' + dl.deaths + ")</small>" : "") + "</div>" +
      '<div class="fe-ob-meta">统计截至 ' + esc(lc.as_of_date || "—") +
      " · " + esc(bjShort(o.latest_report_at)) + " · 来源 " + dash(o.source_count) + " 个" +
      " · " + esc(o.verification_status || "—") + "</div>" +
      "</a>";
  }

  function applyOutbreakHash(os) {
    var m = (location.hash || "").match(/outbreak=([^&]+)/);
    if (!m) return;
    var oid = decodeURIComponent(m[1]);
    var o = os.find(function (x) { return x.outbreak_id === oid; });
    var panel = document.getElementById("feOutbreakDetail");
    if (!panel) return;
    if (!o) { panel.innerHTML = emptyState("未找到该疫情。"); panel.hidden = false; return; }
    var lc = o.latest_counts || {};
    var html = '<div class="fe-ev-sec"><h2>' +
      esc(o.disease_name_cn || o.disease_id) + " · " + esc(o.country_cn || o.country_iso3 || "") +
      "</h2>" +
      '<p>' + vBadge(o.verification_status) + " " +
      '<span class="fe-ob-status">' + esc(o.status_cn || "—") + "</span></p>" +
      '<table class="fe-tbl">' +
      row("确诊 Confirmed", dash(lc.confirmed_cases)) +
      row("疑似 Probable", dash(lc.probable_cases)) +
      row("可疑 Suspected", dash(lc.suspected_cases)) +
      row("死亡 Deaths", dash(lc.deaths)) +
      row("统计截至", esc(lc.as_of_date || "—")) +
      row("最新报告", esc(bj(o.latest_report_at))) +
      row("来源", "来源 " + dash(o.source_count) + " 个 · 独立 " + dash(o.independent_source_count) + " 个") +
      (o.affected_admin1 && o.affected_admin1.length
        ? row("受影响地区", esc(o.affected_admin1.join("；"))) : "") +
      "</table>" +
      (o.uncertainties && o.uncertainties.length
        ? "<p class='muted'>不确定性：" + esc(o.uncertainties.join("；")) + "</p>" : "") +
      '<p><a href="disease-risk.html">← 返回疫情总览</a></p></div>';
    panel.innerHTML = html;
    panel.hidden = false;
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // ── 报告中心（§十七/§十八）──
  function renderReports() {
    Promise.all([load("report_index")]).then(function (R) {
      var ri = R[0];
      var reps = (ri.ok && ri.data && ri.data.reports) || [];
      var host = document.getElementById("feReports");
      if (!host) return;
      var daily = reps.filter(function (r) { return r.type === "africa_daily"; });
      var weekly = reps.filter(function (r) { return r.type === "country_weekly"; });
      var html = '<div class="fe-ev-sec"><h2>最新非洲日报</h2>' +
        (daily.length
          ? '<div class="fe-report-card"><b>' + esc(daily[0].title) + "</b>" +
            '<div class="fe-badge fe-mock">MOCK / 开发样例 · 非正式情报报告</div>' +
            "<div>" + esc(bj(daily[0].published_at)) + "</div>" +
            '<a class="btn sm" href="' + daily[0].path + '" target="_blank">查看样例 →</a>' +
            "</div>"
          : '<p class="muted">正式日报生成能力待 Production AI 启用。</p>') + "</div>";
      html += '<div class="fe-ev-sec"><h2>日报归档</h2>' +
        (daily.length
          ? daily.map(function (r) {
              return "<p><a href='" + r.path + "' target='_blank'>" + esc(r.title) +
                "</a> <small>" + esc(r.period_start + " ~ " + (r.period_end || "")) + "</small></p>";
            }).join("")
          : '<p class="muted">暂无日报归档。</p>') + "</div>";
      html += '<div class="fe-ev-sec"><h2>国家周报</h2>' +
        (weekly.length
          ? weekly.map(function (r) {
              return "<p><a href='" + r.path + "' target='_blank'>" + esc(r.title) +
                "</a> <span class='fe-badge fe-mock'>开发样例</span> <small>" +
                esc(r.country_iso3 || "") + " · " +
                esc(r.period_start + " ~ " + (r.period_end || "")) + "</small></p>";
            }).join("")
          : '<p class="muted">暂无周报。</p>') + "</div>";
      html += '<div class="fe-ev-sec"><h2>重大事件简报</h2>' +
        '<p class="muted">重大事件简报为条件触发类型（major_event_brief，Stage8 配置），当前无简报。</p></div>';
      host.innerHTML = html;
    });
  }

  // ── 报告展示页（§十九：mock 内容或明确空态）──
  function renderReport() {
    var id = new URLSearchParams(location.search).get("id") || "";
    Promise.all([load("report_index")]).then(function (R) {
      var ri = R[0];
      var reps = (ri.ok && ri.data && ri.data.reports) || [];
      var r = reps.find(function (x) { return x.report_id === id; });
      var host = document.getElementById("feReport");
      if (!host) return;
      if (!r || !r.path) {
        host.innerHTML = '<div class="fe-ev-sec"><h2>报告</h2>' +
          '<p class="muted">正式日报生成能力待 Production AI 启用。当前为开发样例。</p>' +
          '<p><a href="reports.html">← 返回报告中心</a></p></div>';
        return;
      }
      // 尝试取 mock 内容（预览构建内存在）；失败给明确状态
      fetch(r.path, { credentials: "same-origin" }).then(function (resp) {
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        return resp.json();
      }).then(function (rep) {
        host.innerHTML = renderReportBody(rep);
      }).catch(function () {
        host.innerHTML = '<div class="fe-ev-sec"><h2>报告（开发样例）</h2>' +
          '<p class="fe-badge fe-mock">MOCK / 开发样例 · 非正式情报报告</p>' +
          '<p class="muted">样例内容仅存在于开发预览环境。正式日报生成能力待 Production AI 启用。</p>' +
          '<p><a href="reports.html">← 返回报告中心</a></p></div>';
      });
    });
  }

  function renderReportBody(rep) {
    var html = '<div class="fe-ev-sec"><h2>' + esc(rep.title || "报告") + "</h2>" +
      '<div class="fe-badge fe-mock">MOCK / 开发样例 · 非正式情报报告</div>' +
      "<p>" + esc(rep.period_start || "") + " ~ " + esc(rep.period_end || "") +
      " · " + esc(bj(rep.generated_at)) + "</p></div>";
    var secs = [
      ["executive_summary", "核心摘要"], ["major_security_developments", "主要安全动态"],
      ["political_social_stability", "政治与社会稳定"], ["terrorism_armed_violence", "恐怖主义与武装暴力"],
      ["cross_border_regional_risks", "跨境与地区风险"], ["public_health_disease_risks", "公共卫生与疾病风险"],
      ["key_changes", "较上期主要变化"], ["watch_items", "关注事项"]
    ];
    secs.forEach(function (sc) {
      var items = rep[sc[0]] || [];
      if (!items.length) return;
      html += '<div class="fe-ev-sec"><h2>' + sc[1] + "</h2>" +
        items.map(function (it) {
          return '<div class="fe-ri"><b>' + esc(it.headline_zh || it.item_id || "") + "</b>" +
            '<div class="fe-fact">事实：' + esc(it.fact_summary || "") + "</div>" +
            (it.assessment ? '<div class="fe-assess">研判：' + esc(it.assessment) + "</div>" : "") +
            (it.outlook ? '<div class="fe-outlook">关注点：' + esc(it.outlook) + "</div>" : "") +
            "</div>";
        }).join("") + "</div>";
    });
    if (rep.overall_assessment) {
      html += '<div class="fe-ev-sec"><h2>整体评估</h2><p>' + esc(rep.overall_assessment) + "</p></div>";
    }
    return html;
  }

  // ── 页面分发 ──
  function init() {
    var page = document.body.getAttribute("data-page") || "";
    renderNav(page);
    if (page === "home") renderHome();
    else if (page === "events") renderEvents();
    else if (page === "event") renderEventDetail();
    else if (page === "countries") renderCountries();
    else if (page === "country") renderCountry();
    else if (page === "disease") renderDisease();
    else if (page === "reports") renderReports();
    else if (page === "report") renderReport();
  }

  window.FE = { init: init, nav: NAV };
  document.addEventListener("DOMContentLoaded", init);
})();
