/* ASIP V1.1-C3 — AI 情报文本渲染（additive）。
 *
 * 契约（§十四/§十五/§三十二）：
 *   - 只在 artifact 状态合法时渲染：FULL → 正常展示；LOW_DATA → 诚实提示数据不足；
 *     FALLBACK / 缺失 → **完全不渲染**（页面继续显示确定性内容）。
 *   - 永不展示实现细节（模型名、prompt、schema、token、错误、pipeline 状态）。
 *   - 所有 KPI / 风险 / 日期 / 新闻计数仍由确定性层决定，本文件不改写任何数字。
 */
(function () {
  if (typeof window === "undefined") return;
  var URL_AI = "data/views/ai_intelligence.json";
  var CN_LOW = "当前数据不足以形成稳定研判";

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
    return '<div class="ai-intel">' +
      '<div class="ai-intel-h">' + esc(title) + "</div>" + rows.join("") + "</div>";
  }

  function inject(node, html) {
    if (!node || !html) return false;
    var d = document.createElement("div");
    d.innerHTML = html;
    node.appendChild(d.firstChild);
    return true;
  }

  fetch(URL_AI, { cache: "no-store" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (doc) {
      if (!doc) return;
      var home = doc.homepage;
      var host = document.getElementById("v11Exec");
      if (host && home && home.status === "FULL") {
        inject(host, block("当前态势研判 / 趋势判断 / 关注事项", home));
      }
      var cHost = document.getElementById("countryDetail") ||
                  document.querySelector("[data-country-detail]") ||
                  document.querySelector("main");
      if (cHost && doc.country_analysis) {
        var cn = (document.body.getAttribute("data-country") ||
                  new URLSearchParams(location.search).get("c") || "").trim();
        var c = cn ? doc.country_analysis[cn] : null;
        if (c && c.status === "FULL") {
          inject(cHost, block("当前态势研判 / 近期趋势 / 关注事项", c));
        } else if (c && c.status === "LOW_DATA") {
          inject(cHost, '<div class="ai-intel"><div class="ai-intel-h">当前态势研判</div>' +
            "<p class=\"ai-p\">" + esc(CN_LOW) + "</p></div>");
        }
      }
    })
    .catch(function () { /* 静默：AI 文本缺失绝不影响页面 */ });
})();
