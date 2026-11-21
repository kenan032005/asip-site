/* ============================================================================
   ASIP V1.1-C1A — News / Signal Stream client  (news-stream-v1)

   Renders the ADDITIVE signal tier.  It never renders a signal as a verified
   event: every card carries its own provenance (single-source / unverified)
   and links out to the originating article.

   Consumes  data/views/news_stream.json  via API.get("views/news_stream").
   ========================================================================== */
(function () {
  "use strict";

  var VIEW = "views/news_stream";

  var state = {
    all: [], view: [], meta: null,
    recency: "", country: "", type: "", source: "", q: "",
    limit: 30, step: 30, loaded: false
  };

  /* ------------------------------------------------------------ helpers */
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function dash(v) { return (v === null || v === undefined || v === "") ? "—" : esc(v); }

  // Canonical path is data/views/news_stream.json.  api.js maps a
  // slash-containing name to a root-relative path, so we probe explicitly
  // and accept an embedded snapshot when the build inlines window.__DB__.
  var VIEW_PATHS = [
    "data/views/news_stream.json",
    "views/news_stream.json",
    "data/news_stream.json"
  ];

  function probe(paths, i) {
    return fetch(paths[i], { credentials: "same-origin" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).catch(function (e) {
      if (i + 1 < paths.length) return probe(paths, i + 1);
      throw e;
    });
  }

  function loadView() {
    if (window.__DB__ && window.__DB__[VIEW]) return Promise.resolve(window.__DB__[VIEW]);
    return probe(VIEW_PATHS, 0);
  }

  function relTime(item) {
    var h = item.age_hours;
    if (h == null) return "—";
    if (h < 1) return Math.max(1, Math.round(h * 60)) + " 分钟前";
    if (h < 24) return Math.round(h) + " 小时前";
    var d = h / 24;
    if (d < 30) return Math.round(d) + " 天前";
    return Math.round(d / 30) + " 个月前";
  }

  var RECENCY_CN = { fresh: "近 7 天", recent: "近 30 天", archive: "历史存档" };

  function recencyChips() {
    var c = (state.meta && state.meta.counts) || {};
    return [
      ["", "全部", c.total],
      ["h24", "24 小时", c.fresh_24h],
      ["h72", "72 小时", c.fresh_72h],
      ["h7d", "7 天", c.fresh_7d],
      ["h30d", "30 天", c.fresh_30d],
      ["archive", "历史存档", c.by_recency ? c.by_recency.archive : null]
    ];
  }

  function matchRecency(n) {
    var h = n.age_hours || 0;
    switch (state.recency) {
      case "h24": return h <= 24;
      case "h72": return h <= 72;
      case "h7d": return h <= 168;
      case "h30d": return h <= 720;
      case "archive": return h > 720;
      default: return true;
    }
  }

  function applyFilters() {
    var q = state.q.trim().toLowerCase();
    state.view = state.all.filter(function (n) {
      if (!matchRecency(n)) return false;
      if (state.country && n.country_cn !== state.country) return false;
      if (state.type && n.event_type_cn !== state.type) return false;
      if (state.source && n.source_name !== state.source) return false;
      if (q) {
        var hay = [n.title, n.title_cn, n.title_original, n.summary_cn,
                   n.source_name, n.country_cn].join(" ").toLowerCase();
        if (hay.indexOf(q) < 0) return false;
      }
      return true;
    });
  }

  /* ------------------------------------------------------------- badges */
  function provBadge(n) {
    if (n.is_verified_event) {
      return '<span class="ns-badge ns-badge-verified">多来源已核实</span>';
    }
    var cls = n.news_status === "held" ? "ns-badge-held" : "ns-badge-signal";
    var txt = n.news_status === "held" ? "待第二来源" : "单一来源 · 待核实";
    return '<span class="ns-badge ' + cls + '">' + txt + "</span>";
  }

  function recencyBadge(n) {
    var cls = n.recency === "fresh" ? "ns-r-fresh"
      : (n.recency === "recent" ? "ns-r-recent" : "ns-r-archive");
    return '<span class="ns-rec ' + cls + '">' + RECENCY_CN[n.recency] + "</span>";
  }

  /* --------------------------------------------------------------- card */
  function card(n) {
    var tcn = n.title_cn;
    var torig = n.title_original;
    var headline = tcn
      ? '<div class="ns-title">' + esc(tcn) + "</div>"
      : '<div class="ns-title ns-title-foreign" lang="' + esc(n.title_lang || "") + '">' + esc(torig) + "</div>";

    var origLine = (tcn && torig)
      ? '<div class="ns-title-orig" lang="' + esc(n.title_lang || "") + '">' + esc(torig) + "</div>"
      : "";

    var body = n.summary_cn
      ? '<div class="ns-sum">' + esc(n.summary_cn) + "</div>"
      : (n.summary_original
        ? '<div class="ns-sum ns-sum-foreign" lang="' + esc(n.title_lang || "") + '">' + esc(n.summary_original) + "</div>"
        : "");

    var bjTime = n.last_seen_bj
      ? '<span class="ns-bj">北京时间 ' + esc(n.last_seen_bj) + "</span>" : "";

    var meta = [];
    if (n.country_cn) meta.push('<span class="ns-chip">' + esc(n.country_cn) + (n.country_iso2 ? " · " + esc(n.country_iso2) : "") + "</span>");
    if (n.event_type_cn) meta.push('<span class="ns-chip">' + esc(n.event_type_cn) + "</span>");
    if (n.source_name) meta.push('<span class="ns-chip ns-chip-src">' + esc(n.source_name) + "</span>");
    meta.push('<span class="ns-chip">独立来源 ' + dash(n.independent_source_count) + "</span>");
    if (n.link_count = n.seen_count > 1) meta.push('<span class="ns-chip ns-chip-upd">关联 ' + n.seen_count + " 次</span>");

    var flags = [];
    // C3F §十四：只有**实际渲染使用原文标题**时才标注未翻译（状态字段与渲染字段必须一致）
    if (!n.title_cn && n.title_cn_missing) flags.push('<span class="ns-flag">未翻译 · 显示原文</span>');
    if (n.has_body) flags.push('<span class="ns-flag ns-flag-ok">正文已抓取</span>');
    if (n.fetch_http_status === 200) flags.push('<span class="ns-flag ns-flag-ok">HTTP 200</span>');
    if (n.china_related) flags.push('<span class="ns-flag ns-flag-cn">涉中</span>');
    if (n.linked_event_id) {
      flags.push('<a class="ns-flag ns-flag-link" href="event.html?id=' +
        encodeURIComponent(n.linked_event_id) + '">已关联事件簇</a>');
    }

    var url = n.source_url || "";
    var link = url
      ? '<a class="ns-src-link" href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">查看原文 ↗</a>'
      : '<span class="ns-src-link ns-src-none">无原文链接</span>';

    return '<article class="ns-card" data-news-id="' + esc(n.news_id) + '">' +
      '<div class="ns-card-h">' + provBadge(n) + recencyBadge(n) +
      '<span class="ns-age">' + esc(relTime(n)) + "</span></div>" +
      headline + origLine + body +
      '<div class="ns-meta">' + meta.join("") + "</div>" +
      (flags.length ? '<div class="ns-flags">' + flags.join("") + "</div>" : "") +
      '<div class="ns-card-f">' + link + bjTime + "</div>" +
      '<p class="ns-disclaimer">' + esc(n.disclaimer_cn || "") + "</p>" +
      "</article>";
  }

  /* ------------------------------------------------------------- render */
  function renderList(host) {
    if (!host) return;
    if (!state.view.length) { host.innerHTML = '<div class="ns-empty">当前筛选条件下无动态。</div>'; return; }
    var slice = state.view.slice(0, state.limit);
    var more = state.view.length - slice.length;
    host.innerHTML = slice.map(card).join("") +
      (more > 0
        ? '<div class="ns-more-wrap"><button class="ns-more" id="nsMore">加载更多（剩余 ' + more + " 条）</button></div>"
        : '<div class="ns-more-wrap ns-end">已显示全部 ' + state.view.length + " 条</div>");
    var b = document.getElementById("nsMore");
    if (b) b.addEventListener("click", function () {
      state.limit += state.step; renderList(host);
    });
  }

  function renderSummary(host) {
    if (!host) return;
    var c = (state.meta && state.meta.counts) || {};
    var g = (state.meta && state.meta.gate) || {};
    host.innerHTML =
      '<div class="ns-sum-grid">' +
      '<div class="ns-sum-k"><b>' + dash(c.total) + "</b><span>可展示动态</span></div>" +
      '<div class="ns-sum-k"><b>' + dash(c.fresh_24h) + "</b><span>近 24 小时</span></div>" +
      '<div class="ns-sum-k"><b>' + dash(c.fresh_7d) + "</b><span>近 7 天</span></div>" +
      '<div class="ns-sum-k ns-sum-warn"><b>' + dash(c.is_verified_event) + "</b><span>多来源已核实</span></div>" +
      '<div class="ns-sum-k"><b>' + dash(c.title_cn_missing) + "</b><span>未翻译条目</span></div>" +
      '<div class="ns-sum-k"><b>' + dash(g.rejected) + "</b><span>守门拦截</span></div>" +
      "</div>" +
      '<p class="ns-sum-note">' +
      "本页为 <b>情报信号流</b>：单一来源条目经收录后即可展示，用于尽早发现动向；" +
      "「已核实事件」需至少 2 个独立来源交叉印证，阈值未作任何下调。" +
      (c.is_verified_event === 0
        ? "当前语料中尚无满足多来源阈值的事件，因此信号流承担全部时效性展示。"
        : "") +
      "</p>";
  }

  function renderFilters(host) {
    if (!host) return;
    function opts(vals, cur, labelAll) {
      return '<option value="">' + labelAll + "</option>" + vals.map(function (v) {
        return '<option value="' + esc(v) + '"' + (v === cur ? " selected" : "") + ">" + esc(v) + "</option>";
      }).join("");
    }
    var countries = Object.keys(countUnique("country_cn"));
    var types = Object.keys(countUnique("event_type_cn"));
    var sources = Object.keys(countUnique("source_name"));

    host.innerHTML =
      '<div class="ns-filter-row">' +
      '<input id="nsQ" class="ns-input" type="search" placeholder="搜索标题 / 来源 / 国家…" value="' + esc(state.q) + '">' +
      '<select id="nsCountry" class="ns-select">' + opts(countries, state.country, "全部国家") + "</select>" +
      '<select id="nsType" class="ns-select">' + opts(types, state.type, "全部类型") + "</select>" +
      '<select id="nsSource" class="ns-select">' + opts(sources, state.source, "全部来源") + "</select>" +
      "</div>" +
      '<div class="ns-chips" id="nsChips">' + recencyChips().map(function (c) {
        return '<button class="ns-chip-btn' + (state.recency === c[0] ? " is-on" : "") +
          '" data-r="' + c[0] + '">' + esc(c[1]) +
          (c[2] != null ? '<em>' + c[2] + "</em>" : "") + "</button>";
      }).join("") + "</div>";

    var q = document.getElementById("nsQ");
    if (q) {
      var t = null;
      q.addEventListener("input", function () {
        clearTimeout(t);
        t = setTimeout(function () {
          state.q = q.value; state.limit = state.step;
          applyFilters(); renderList(host._listHost);
        }, 160);
      });
    }
    [["nsCountry", "country"], ["nsType", "type"], ["nsSource", "source"]].forEach(function (p) {
      var el = document.getElementById(p[0]);
      if (el) el.addEventListener("change", function () {
        state[p[1]] = el.value; state.limit = state.step;
        applyFilters(); renderList(host._listHost);
      });
    });
    var chips = document.getElementById("nsChips");
    if (chips) chips.addEventListener("click", function (e) {
      var b = e.target.closest ? e.target.closest(".ns-chip-btn") : null;
      if (!b) return;
      state.recency = b.getAttribute("data-r"); state.limit = state.step;
      applyFilters(); renderFilters(host); renderList(host._listHost);
    });
  }

  function countUnique(field) {
    var m = {};
    state.all.forEach(function (n) {
      var v = n[field];
      if (v) m[v] = (m[v] || 0) + 1;
    });
    return m;
  }

  /* ------------------------------------------------------------- events page */
  function setTab(tab) {
    var panes = { news: "c1aPaneNews", verified: "c1aPaneVerified" };
    Object.keys(panes).forEach(function (k) {
      var el = document.getElementById(panes[k]);
      if (el) el.style.display = (k === tab) ? "" : "none";
    });
    var btns = document.querySelectorAll("#c1aTabs .c1a-tab");
    for (var i = 0; i < btns.length; i++) {
      btns[i].classList.toggle("is-on", btns[i].getAttribute("data-tab") === tab);
    }
    try { location.hash = tab === "news" ? "#news" : "#verified"; } catch (e) {}
  }

  function initEventsPage() {
    var tabs = document.getElementById("c1aTabs");
    if (tabs) {
      tabs.addEventListener("click", function (e) {
        var b = e.target.closest ? e.target.closest(".c1a-tab") : null;
        if (!b) return;
        setTab(b.getAttribute("data-tab"));
      });
    }
    var sumHost = document.getElementById("nsSummary");
    var fHost = document.getElementById("nsFilters");
    var lHost = document.getElementById("nsList");
    if (!lHost) return;
    lHost.innerHTML = '<div class="ns-empty">加载中…</div>';

    loadView().then(function (d) {
      state.meta = d;
      state.all = (d && d.items) || [];
      state.loaded = true;
      state.limit = state.step;
      if (fHost) fHost._listHost = lHost;
      applyFilters();
      renderSummary(sumHost);
      renderFilters(fHost);
      renderList(lHost);
      var def = (location.hash === "#verified") ? "verified" : "news";
      setTab(def);
    }).catch(function () {
      lHost.innerHTML = '<div class="ns-empty">动态数据未能加载（data/views/news_stream.json）。</div>';
    });
  }

  /* --------------------------------------------------------------- home */
  function initHome() {
    var host = document.getElementById("v11News");
    if (!host) return;
    loadView().then(function (d) {
      var all = (d && d.items) || [];
      if (!all.length) { host.innerHTML = '<div class="ns-empty">暂无动态。</div>'; return; }
      var c = d.counts || {};
      var top = all.slice(0, 5);
      var html = '<div class="ns-home-list">' + top.map(function (n) {
        var t = n.title_cn || n.title_original;
        var foreign = n.title_cn ? "" : ' lang="' + esc(n.title_lang || "") + '"';
        return '<a class="ns-home-item" href="' + esc(n.source_url || "#") + '" target="_blank" rel="noopener noreferrer">' +
          '<span class="ns-home-dot ' + (n.recency === "fresh" ? "is-fresh" : "") + '"></span>' +
          '<span class="ns-home-t"' + foreign + ">" + esc(t) + "</span>" +
          '<span class="ns-home-m">' + esc(n.source_name || "") + " · " + esc(relTime(n)) + "</span>" +
          "</a>";
      }).join("") + "</div>" +
        '<div class="ns-home-f"><span>共 ' + dash(c.total) + " 条 · 近 24 小时 " + dash(c.fresh_24h) +
        " · 近 7 天 " + dash(c.fresh_7d) + "</span>" +
        '<span class="ns-home-warn">信号未核实 · 多来源已核实 ' + dash(c.is_verified_event) + "</span>" +
        '<a class="v11-more" href="events.html">查看全部动态 →</a></div>';
      host.innerHTML = html;
    }).catch(function () {
      host.innerHTML = '<div class="ns-empty">动态数据暂不可用。</div>';
    });
  }

  function init() {
    var page = document.body.getAttribute("data-page") || "";
    if (page === "events") initEventsPage();
    else if (page === "home") initHome();
  }

  window.NEWS = {
    init: init, state: state, setTab: setTab,
    applyFilters: applyFilters, renderList: renderList, card: card,
    _version: "c1a-1.0.0"
  };
  document.addEventListener("DOMContentLoaded", init);
})();
