#!/usr/bin/env node
/* report_ui_contract.js — C4-B §十 renderer 坏值契约测试（node，无浏览器依赖）
 *
 * 直接执行 report-views.js 的 displayValue()（从源码中提取，保证测的是真实实现），
 * 覆盖：
 *   1. test_report_ui_does_not_stringify_object
 *   2. test_report_ui_hides_null_and_undefined
 *   3. test_weekly_nested_metrics_not_rendered_as_object_string
 *   4. test_report_scalar_formatter_handles_arrays_safely
 *   5. test_weekly_detail_contains_no_bad_value_sentinels
 *
 * 用法: node report_ui_contract.js <report-views.js 路径> [数据目录]
 */
const fs = require("fs");
const path = require("path");

const src = fs.readFileSync(process.argv[2], "utf8");
const dataDir = process.argv[3] || null;

/* 从 IIFE 源码中提取 OBJ_TEXT_KEYS 与 displayValue，保持被测实现**零改写** */
function extract(name) {
  const re = new RegExp("  var " + name + " = \\[[^\\]]*\\];");
  const m = src.match(re);
  if (!m) throw new Error("cannot extract " + name);
  return m[0];
}
function extractFn(name) {
  const start = src.indexOf("  function " + name + "(");
  if (start < 0) throw new Error("cannot extract fn " + name);
  let i = src.indexOf("{", start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}") { depth--; if (depth === 0) break; }
  }
  return src.slice(start, i + 1);
}
const displayValue = new Function(
  extract("OBJ_TEXT_KEYS") + "\n" + extractFn("displayValue") + "\n return displayValue;"
)();

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); console.log("  ok   " + name); pass++; }
  catch (e) { console.log("  FAIL " + name + " → " + e.message); fail++; }
}
function eq(a, b, m) { if (a !== b) throw new Error((m || "") + " expected " + JSON.stringify(b) + " got " + JSON.stringify(a)); }
const SENTINEL = /(\[object Object\]|undefined|(?<![A-Za-z])null(?![A-Za-z])|NaN)/;

t("test_report_ui_does_not_stringify_object", () => {
  eq(displayValue({}), "", "{}");
  eq(displayValue({ foo: 1, bar: 2 }), "", "no product key");
  eq(displayValue({ source_name: "libyaherald" }), "libyaherald");
  eq(displayValue([{ source_name: "anp" }, { source_id: "src_1" }]), "anp、src_1");
  if (SENTINEL.test(displayValue({ a: { b: 1 } }))) throw new Error("sentinel leaked");
});

t("test_report_ui_hides_null_and_undefined", () => {
  eq(displayValue(null), "");
  eq(displayValue(undefined), "");
  eq(displayValue([null, undefined, "x"]), "x");
  eq(displayValue({ source_name: null }), "");
  eq(displayValue(false), "", "boolean must not leak as text");
  eq(displayValue(Number.NaN), "", "NaN must not leak as text");
});

t("test_weekly_nested_metrics_not_rendered_as_object_string", () => {
  const metrics = { active_outbreak_count: 19, comparison: { active_outbreak_count: 18 } };
  const scalars = Object.keys(metrics).filter(k => {
    const ty = typeof metrics[k];
    return metrics[k] != null && (ty === "string" || ty === "number");
  });
  eq(scalars.join(","), "active_outbreak_count");
  const line = scalars.map(k => k + "=" + displayValue(metrics[k])).join(" · ");
  if (SENTINEL.test(line)) throw new Error("nested metrics leaked: " + line);
  eq(line, "active_outbreak_count=19");
});

t("test_report_scalar_formatter_handles_arrays_safely", () => {
  eq(displayValue(["a", "b"]), "a、b");
  eq(displayValue([[1, 2], "c"]), "1、2、c");
  eq(displayValue([]), "");
  eq(displayValue([{}, { source_name: "s" }]), "s");
  eq(displayValue(" z "), "z");
});

t("test_weekly_detail_contains_no_bad_value_sentinels", () => {
  if (!dataDir) { console.log("       (no data dir given; sentinel scan skipped)"); return; }
  const idxPath = path.join(dataDir, "views", "report_index.json");
  const idx = JSON.parse(fs.readFileSync(idxPath, "utf8"));
  const weeks = (idx.reports || []).filter(r => r.report_type === "africa_weekly");
  if (!weeks.length) throw new Error("no africa_weekly in index");
  /* 模拟 renderer 的取值边界：所有用户可见字段必须过 displayValue */
  let checked = 0;
  for (const w of weeks) {
    const rep = JSON.parse(fs.readFileSync(path.join(dataDir, "..", w.path), "utf8"));
    const facts = [];
    Object.keys(rep.sections || {}).forEach(k => (rep.sections[k] || []).forEach(it => facts.push(it)));
    for (const f of facts.slice(0, 20)) {
      const refs = displayValue(f.source_refs) || displayValue(f.source_evidence || []);
      if (SENTINEL.test(refs)) throw new Error("fact refs sentinel: " + refs);
      checked++;
    }
    for (const u of (rep.uncertainties || []).slice(0, 6)) {
      if (SENTINEL.test(displayValue(u))) throw new Error("uncertainty sentinel");
    }
    for (const c of (rep.coverage_notes || []).slice(0, 3)) {
      if (SENTINEL.test(displayValue(c))) throw new Error("coverage note sentinel");
    }
  }
  console.log("       (scanned " + checked + " fact rows across " + weeks.length + " weekly reports)");
});

console.log("");
console.log("renderer contract: " + pass + " passed, " + fail + " failed");
process.exit(fail ? 1 : 0);
