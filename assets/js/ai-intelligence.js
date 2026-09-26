/* ASIP V1.1-C3F — AI 情报文本接线（真实 DOM/URL 契约，additive）。
 *
 * 契约（审计自真实 HTML/JS，非猜测）：
 *   HOMEPAGE_AI_HOST  = #v11Exec        通过 window.__HOME_AI_SET__ 注入（home-v11.js 既有 AI 槽位）
 *   COUNTRY_AI_HOST   = #feCountry      （country.html:21 / frontend.js:524）
 *   COUNTRY_URL_PARAM = ?country=<中文显示名>（frontend.js:518）→ 经 ISO3 索引关联 artifact
 *   EVENT_AI_HOST     = #feEventDetail  （event.html:21 / frontend.js:382）
 *   EVENT_ID          = master_events[].master_event_id（= EVT_<16hex>，与 event_analysis 键同源）
 *
 * 渲染规则：
 *   * 只有 status=FULL 才渲染；LOW_DATA 显示正式低数据文案；FALLBACK/缺失一律不渲染。
 *   * 首页额外要求 fact_pack_hash 与当前确定性 fact pack 一致，否则视为 STALE → 保留确定性摘要。
 *   * 永不展示 model / prompt / schema / token / cache / hash / pipeline 状态等实现细节。
 *   * 不修改 KPI、风险等级、新闻数量、verification、来源与日期。
 */
(function () {
  if (typeof window === "undefined") return;
  var URL_AI = "data/views/ai_intelligence.json";
  var LOW_DATA_CN = "当前数据不足以形成稳定研判";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function block(title, o) {
    var rows = [];
    if (o.executive_assessment) rows.push('<p class="ai-p">' + esc(o.executive_assessment) + "</p>");
    if (o.trend_analysis) rows.push('<p class="ai-p">' + esc(o.trend_analysis) + "</p>");
    if (o.outlook) rows.push('<p class="ai-p">' + esc(o.outlook) + "</p>");
    if (o.watch_points && o.watch_points.length) {
      rows.push('<ul class="ai-watch">' + o.watch_points.map(function (w) {
        return "<li>" + esc(w) + "</li>";
      }).join("") + "</ul>");
    }
    if (!rows.length) return "";
    return '<div class="ai-intel"><div class="ai-intel-h">' + esc(title) + "</div>" +
      rows.join("") + "</div>";
  }

  function insertOnce(host, marker, html) {
    if (!host || !html) return true;
    if (host.querySelector(marker)) return true;
    var d = document.createElement("div");
    d.innerHTML = html;
    host.appendChild(d.firstChild);
    return true;
  }

  function q(name) {
    try { return (new URLSearchParams(location.search).get(name) || "").trim(); }
    catch (e) { return ""; }
  }

  /* frontend.js 是异步渲染，必须等宿主真正有内容再插入 */
  function whenReady(fn, tries) {
    var n = (tries === undefined ? 30 : tries);
    (function step() {
      if (fn() === true || n-- <= 0) return;
      setTimeout(step, 240);
    })();
  }

  fetch(URL_AI, { cache: "no-store" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (doc) {
      if (!doc) return;

      /* ---------- 首页 ---------- */
      var hp = doc.homepage || null;
      var fresh = !!(hp && hp.status === "FULL" && hp.fact_pack_hash &&
                     doc.homepage_fact_pack_hash &&
                     hp.fact_pack_hash === doc.homepage_fact_pack_hash);
      if (fresh && typeof window.__HOME_AI_SET__ === "function") {
        window.__HOME_AI_SET__({
          executive: {
            overall_assessment: [hp.executive_assessment, hp.trend_analysis, hp.outlook]
              .filter(Boolean).join(" ")
          }
        }, true);
      }

      /* ---------- 国家页 ---------- */
      var cn = q("country");
      var iso = cn && (doc.country_name_to_iso3 || {})[cn];
      var cd = iso && (doc.country_index || {})[iso];
      if (cd) {
        whenReady(function () {
          var host = document.getElementById("feCountry");
          if (!host || !host.children.length) return false;
          if (cd.status === "FULL") {
            return insertOnce(host, ".ai-intel",
              block("当前态势研判 / 近期趋势 / 关注事项", cd));
          }
          if (cd.status === "LOW_DATA") {
            return insertOnce(host, ".ai-intel",
              '<div class="ai-intel"><div class="ai-intel-h">当前态势研判</div>' +
              '<p class="ai-p">' + esc(LOW_DATA_CN) + "</p></div>");
          }
          return true;
        });
      }

      /* ---------- 事件详情页 ---------- */
      var eid = q("id");
      var ev = eid && (doc.event_analysis || {})[eid];
      if (ev && ev.status === "FULL") {
        whenReady(function () {
          var host = document.getElementById("feEventDetail");
          if (!host || !host.children.length) return false;
          var rows = [];
          if (ev.summary_cn) rows.push('<p class="ai-p">' + esc(ev.summary_cn) + "</p>");
          if (ev.significance) rows.push('<p class="ai-p">' + esc(ev.significance) + "</p>");
          if (ev.trend_signal) rows.push('<p class="ai-p">' + esc(ev.trend_signal) + "</p>");
          if (ev.watch_points && ev.watch_points.length) {
            rows.push('<ul class="ai-watch">' + ev.watch_points.map(function (w) {
              return "<li>" + esc(w) + "</li>";
            }).join("") + "</ul>");
          }
          if (!rows.length) return true;
          return insertOnce(host, ".ai-intel",
            '<div class="ai-intel"><div class="ai-intel-h">事件研判（分析，非原始事实）</div>' +
            rows.join("") + "</div>");
        });
      }
    })
    .catch(function () { /* 静默：AI 文本缺失绝不影响页面 */ });
})();
