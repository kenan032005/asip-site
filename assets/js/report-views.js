/* ASIP V1.1-C4-B — 报告视图（真实 report index / artifact，additive，不重设计全站 UI）
 *
 * 数据契约（只读真实数据）：
 *   index  : data/views/report_index.json   （real-only；mock 永不出现）
 *   detail : index[].path → data/reports/{daily|weekly|country_weekly}/<report_id>.json
 *
 * 规则：
 *   * 状态语义：FULL=完整 / FALLBACK=确定性版 / LOW_DATA=数据有限。**不得**把 LOW_DATA 写成
 *     FAIL / ERROR / "AI 不可用"。
 *   * 页面不显示 model / prompt / input_hash / fact_pack_hash / cache / pipeline 等实现细节。
 *   * FACTS 与 ANALYSIS 视觉分区；无 AI 时分析区显示确定性内容，不留空白。
 */
(function () {
  if (typeof window === "undefined") return;

  // 站点发布路径为 data/report_index.json（build_frontend_views 白名单），
  // 开发/仓库内为 data/views/report_index.json；依次探测，取第一个可用。
  var IDX_CANDIDATES = ["data/report_index.json", "data/views/report_index.json"];
  var TYPE_CN = { africa_daily: "非洲日报", africa_weekly: "非洲周报",
                  country_weekly: "国家周报", major_event_brief: "重大事件简报" };
  var STATUS_CN = { FULL: "完整", FALLBACK: "确定性版", LOW_DATA: "数据有限" };
  var LOW_CN = "本报告周期内可追溯且满足筛选条件的安全信息有限，当前证据不足以形成稳定趋势判断。";

  /* ---------- Display Value Contract ----------
   * 所有"值→用户文本"的边界都必须经过 displayValue()：
   *   string → 原样（trim）        number → 仅有限数
   *   boolean → ""（由产品文案决定，不隐式输出 true/false）
   *   array  → 逐个 displayValue 后 join
   *   object → 显式取产品允许字段（绝不 String(object) → "[object Object]"）
   *   null/undefined → ""（该字段不渲染）
   */
  var OBJ_TEXT_KEYS = ["source_name", "name", "title", "title_cn", "label",
                       "source_id", "id", "event_id", "fact", "summary", "detail"];
  function displayValue(v) {
    if (v == null) return "";
    var t = typeof v;
    if (t === "string") return v.trim();
    if (t === "number") return isFinite(v) ? String(v) : "";
    if (t === "boolean") return "";
    if (Array.isArray(v)) {
      return v.map(displayValue).filter(Boolean).join("、");
    }
    if (t === "object") {
      for (var i = 0; i < OBJ_TEXT_KEYS.length; i++) {
        var k = OBJ_TEXT_KEYS[i];
        if (v[k] != null) {
          var s = displayValue(v[k]);
          if (s) return s;
        }
      }
      return "";           // 显式跳过：不猜、不串化
    }
    return "";
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }
  function jgetFirst(urls) {
    return new Promise(function (res) {
      var i = 0;
      (function step() {
        if (i >= urls.length) return res(null);
        jget(urls[i++]).then(function (d) {
          if (d && d.reports) return res(d);
          step();
        });
      })();
    });
  }

  function jget(url) {
    return fetch(url, { cache: "no-store" }).then(function (r) {
      return r.ok ? r.json() : null;
    }).catch(function () { return null; });
  }
  function q(name) {
    try { return (new URLSearchParams(location.search).get(name) || "").trim(); }
    catch (e) { return ""; }
  }
  function statusBadge(st) {
    var cn = STATUS_CN[st] || st || "";
    var cls = st === "LOW_DATA" ? "fe-badge" : (st === "FULL" ? "fe-badge" : "fe-badge fe-mock");
    return '<span class="' + cls + '">' + esc(cn) + "</span>";
  }
  function periodOf(r) {
    var a = displayValue(r.period_start).slice(0, 16).replace("T", " ");
    var b = displayValue(r.period_end).slice(0, 16).replace("T", " ");
    return a && b ? a + " → " + b : (r.period_end || r.period_start || "");
  }
  function one(r) {
    return '<div class="fe-report-card">' +
      '<b>' + esc(displayValue(r.title_cn) || displayValue(r.title) || displayValue(r.report_id)) + "</b> " + statusBadge(r.status) +
      '<div><small>' + esc(TYPE_CN[r.report_type] || r.report_type || "") +
      " · " + esc(periodOf(r)) + "</small></div>" +
      (displayValue(r.headline) ? "<div>" + esc(displayValue(r.headline).slice(0, 150)) + "</div>" : "") +
      '<div><small>数据截至 ' + esc(displayValue(r.data_as_of).slice(0, 16).replace("T", " ")) + "</small></div>" +
      '<a class="btn sm" href="report.html?id=' + encodeURIComponent(r.report_id) + '">查看 →</a>' +
      "</div>";
  }

  /* ---------- Reports 索引页 ---------- */
  function reportsIndex() {
    var host = document.getElementById("feReports");
    if (!host) return;
    jgetFirst(IDX_CANDIDATES).then(function (doc) {
      var rows = (doc && doc.reports) || [];
      if (!rows.length) return;
      var tab = sessionStorage.getItem("repTab") || "all";
      function view() {
        var list = rows.filter(function (r) { return tab === "all" || r.report_type === tab; });
        var tabs = [["all", "全部"]].concat(Object.keys(TYPE_CN).filter(function (t) {
          return rows.some(function (r) { return r.report_type === t; });
        }).map(function (t) { return [t, TYPE_CN[t]]; }));
        var html = '<div class="fe-evs-filter">' + tabs.map(function (t) {
          return '<a class="btn sm' + (t[0] === tab ? "" : " ghost") + '" data-rep-tab="' + t[0] + '">' +
            esc(t[1]) + "（" + rows.filter(function (r) {
              return t[0] === "all" || r.report_type === t[0];
            }).length + "）</a>";
        }).join(" ") + "</div>";
        html += list.length ? list.map(one).join("")
                            : '<p class="muted">该分类暂无正式报告。</p>';
        host.innerHTML = html;
        Array.prototype.forEach.call(host.querySelectorAll("[data-rep-tab]"), function (a) {
          a.addEventListener("click", function () {
            tab = a.getAttribute("data-rep-tab");
            sessionStorage.setItem("repTab", tab);
            view();
          });
        });
      }
      view();
    });
  }

  /* ---------- Report 详情页 ---------- */
  function reportDetail() {
    var host = document.getElementById("feReport");
    if (!host) return;
    var rid = q("id");
    if (!rid) {
      host.innerHTML = '<p class="muted">缺少报告编号。</p>';
      return;
    }
    jgetFirst(IDX_CANDIDATES).then(function (doc) {
      var row = ((doc && doc.reports) || []).filter(function (r) {
        return r.report_id === rid;
      })[0];
      if (!row || !row.path) {
        host.innerHTML = '<p class="muted">未找到该报告。</p>';
        return;
      }
      return jget(row.path).then(function (rep) {
        if (!rep) { host.innerHTML = '<p class="muted">报告内容暂不可读取。</p>'; return; }
        var h = '<div class="fe-ev-head"><h1>' +
          esc(displayValue(rep.title_cn) || displayValue(rep.title) || displayValue(rep.report_id)) + "</h1>" +
          "<p>" + statusBadge(rep.status) + " " +
          '<span class="fe-badge">' + esc(TYPE_CN[rep.report_type] || rep.report_type || "") + "</span> " +
          "<small>" + esc(periodOf(rep)) + "</small></p>" +
          '<p><small>数据截至 ' + esc(displayValue(rep.data_as_of).slice(0, 16).replace("T", " ")) +
          (rep.country_iso3 ? " · " + esc(rep.country_iso3) : "") +
          " · 事实 " + esc(rep.fact_count == null ? "—" : rep.fact_count) +
          " 条 · 来源 " + esc(rep.source_count == null ? "—" : rep.source_count) + " 个</small></p></div>";

        /* FACTS */
        h += '<div class="fe-ev-sec"><h2>事实依据</h2>';
        var facts = [];
        var secs = rep.sections || {};
        Object.keys(secs).forEach(function (k) {
          (secs[k] || []).forEach(function (it) { facts.push(it); });
        });
        ["major_events", "political_social_stability", "terrorism_armed_violence",
         "disease_public_health"].forEach(function (k) {
          (rep[k] || []).forEach(function (it) { facts.push(it); });
        });
        if (facts.length) {
          h += '<div class="fe-tbl">' + facts.slice(0, 20).map(function (f) {
            var ev = f.source_evidence || [];
            var refs = displayValue(f.source_refs) || displayValue(ev);
            var title = displayValue(f.title_zh) || displayValue(f.headline_zh) ||
                        displayValue(f.fact) || displayValue(f.event_id);
            return '<div class="fe-fact"><div>' + esc(title) + "</div>" +
              (refs ? '<div><small>来源：' + esc(refs) + "</small></div>" : "") + "</div>";
          }).join("") + "</div>";
        } else {
          h += "<p>" + esc(LOW_CN) + "</p>";
        }
        if (rep.metrics && Object.keys(rep.metrics).length) {
          // 只取标量指标；嵌套结构（如 comparison）不得串化成 "[object Object]"
          var scalars = Object.keys(rep.metrics).filter(function (k) {
            var t = typeof rep.metrics[k];
            return rep.metrics[k] != null && (t === "string" || t === "number");
          }).slice(0, 6);
          if (scalars.length) {
            h += "<p><small>本周指标：" + esc(scalars.map(function (k) {
              return k + "=" + rep.metrics[k];
            }).join(" · ")) + "</small></p>";
          }
        }
        h += "</div>";

        /* ANALYSIS（确定性版也必须有内容，不留空白） */
        var an = rep.analysis || {};
        h += '<div class="fe-ev-sec"><h2>态势研判</h2>';
        var blocks = [
          ["执行摘要", rep.overall_assessment || rep.executive_assessment || an.executive_assessment],
          ["趋势判断", rep.security_trend || an.trend_analysis],
          ["关注事项", (rep.next_week_watch_items || an.watch_points || [])[0] ||
                      (rep.key_changes || [])[0] ||
                      (rep.outlook || an.outlook)]
        ];
        var any = false;
        // 只渲染文本：对象/嵌套结构一律跳过（否则 String({}) 会渲染成 "[object Object]"）
        function asText(v) {
          if (v == null) return "";
          if (typeof v === "string") return v.trim();
          if (typeof v === "number" || typeof v === "boolean") return String(v);
          if (Array.isArray(v)) {
            return v.map(asText).filter(Boolean).join("；");
          }
          return "";
        }
        h += blocks.map(function (b) {
          var v = asText(b[1]);
          if (!v) return "";
          any = true;
          return "<p><b>" + esc(b[0]) + "</b>：" + esc(v) + "</p>";
        }).join("");
        if (!any) {
          h += "<p>" + esc(LOW_CN) + "</p>";
        }
        h += "</div>";

        /* 来源 */
        var refs = rep.source_refs || [];
        if (refs.length) {
          h += '<div class="fe-ev-sec"><h2>来源</h2>' + refs.slice(0, 12).map(function (s) {
            if (typeof s === "string") {
              return "<p>" + (s.indexOf("http") === 0
                ? '<a href="' + esc(s) + '" target="_blank" rel="noopener noreferrer">' + esc(s) + " ↗</a>"
                : esc(s)) + "</p>";
            }
            var nm = displayValue(s && (s.source_name || s.name || s.source_id));
            var url = s && typeof s.url === "string" ? s.url : "";
            var ver = displayValue(s && s.verification);
            if (!nm && !url) return "";
            return "<p>" + (url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">' + esc(nm || url) + " ↗</a>" : esc(nm)) +
              (ver ? " <small>" + esc(ver) + "</small>" : "") + "</p>";
          }).join("") + "</div>";
        }

        /* 不确定性 / 数据质量 */
        var unc = rep.uncertainties || [];
        var cov = rep.coverage_notes || [];
        if (unc.length || cov.length) {
          h += '<div class="fe-ev-sec"><h2>不确定性与数据说明</h2>' +
            unc.slice(0, 6).map(function (u) {
              var t = displayValue(u); return t ? "<p>" + esc(t) + "</p>" : "";
            }).join("") +
            cov.slice(0, 3).map(function (c) {
              var t = displayValue(c); return t ? '<p><small>' + esc(t) + "</small></p>" : "";
            }).join("") +
            "</div>";
        }
        host.innerHTML = h;
      });
    });
  }

  /* ---------- 首页「最新情报报告」 ---------- */
  function homepageIntel() {
    var host = document.getElementById("v11Intel");
    if (!host) return;
    jgetFirst(IDX_CANDIDATES).then(function (doc) {
      var rows = (doc && doc.reports) || [];
      if (!rows.length) return;
      function latest(t) { return rows.filter(function (r) { return r.report_type === t; })[0]; }
      var picks = [latest("africa_daily"), latest("africa_weekly"), latest("country_weekly")]
        .filter(Boolean);
      if (!picks.length) return;
      var head = host.querySelector(".v11-card-h");
      var body = picks.map(function (r) {
        return '<div class="fe-report-line">' +
          '<a href="report.html?id=' + encodeURIComponent(r.report_id) + '">' +
          esc(displayValue(r.title_cn) || displayValue(r.title) || displayValue(r.report_id)) + "</a> " + statusBadge(r.status) +
          ' <small>' + esc(periodOf(r)) + "</small></div>";
      }).join("");
      var keep = host.querySelector(".v11-card-h");
      host.innerHTML = "";
      if (keep) host.appendChild(keep);
      var d = document.createElement("div");
      d.innerHTML = body;
      host.appendChild(d);
    });
  }

  function boot() {
    try {
      if (document.getElementById("feReports")) reportsIndex();
      else if (document.getElementById("feReport")) reportDetail();
      else if (document.getElementById("v11Intel")) homepageIntel();
    } catch (e) { /* 静默：报告视图失败不影响页面其它部分 */ }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { setTimeout(boot, 900); });
  } else {
    setTimeout(boot, 900);
  }
})();
