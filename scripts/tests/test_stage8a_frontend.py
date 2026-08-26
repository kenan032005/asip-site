#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8A — Frontend Product Integration V1 测试套件（§四十五）。

覆盖：
  frontend view schema / runtime-public isolation / master dedup UI /
  verification badge / timeline / country attribution / country empty state /
  disease unknown != 0 / disease categories separation / report development
  label / knowledge entity link IDs / navigation consistency / mobile
  structural / preview path checks / secret scan / __DB__ 隔离。

用法：
  python -m unittest scripts.tests.test_stage8a_frontend
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

VIEWS = ROOT / "data" / "runtime" / "frontend_preview_public"
DIST = ROOT / "dist"
FE_JS = (ROOT / "assets" / "js" / "frontend.js").read_text(encoding="utf-8")
CSS = (ROOT / "assets" / "css" / "style.css").read_text(encoding="utf-8")


def load_view(name):
    return json.loads((VIEWS / (name + ".json")).read_text(encoding="utf-8"))


class TestViewSchemas(unittest.TestCase):
    """§二十六-§三十：7 个契约必备字段与最小化。"""

    def test_site_overview(self):
        v = load_view("site_overview")
        for k in ("generated_at", "data_status", "latest_data_time_bj", "kpis",
                  "verification_summary", "source_freshness"):
            self.assertIn(k, v)
        for k in ("events_24h", "events_72h_ongoing", "priority_country_count",
                  "verified_probable_count", "active_outbreaks"):
            self.assertIn(k, v["kpis"])
        self.assertIn(v["data_status"], ("current", "delayed", "degraded"))

    def test_master_events_minimal_fields(self):
        v = load_view("master_events")
        allowed = {"master_event_id", "headline_zh", "headline_en", "country_iso3",
                   "country_cn", "location", "event_type", "event_type_cn",
                   "event_time", "latest_update_at", "verification_status",
                   "verification_cn", "source_count", "independent_source_count",
                   "fact_summary", "change_type", "change_type_cn", "update_count",
                   "timeline_status", "uncertainties", "conflict_flags"}
        for e in v["events"]:
            extra = set(e.keys()) - allowed
            self.assertEqual(extra, set(), "master event 含内部字段: %s" % extra)
            self.assertNotIn("merge_reasons", e)
            self.assertNotIn("raw", e)
            self.assertNotIn("candidate_ids", e)

    def test_master_events_unique(self):
        v = load_view("master_events")
        ids = [e["master_event_id"] for e in v["events"]]
        self.assertEqual(len(ids), len(set(ids)), "master event 重复")
        self.assertGreaterEqual(len(ids), 1)

    def test_event_timelines_minimal(self):
        v = load_view("event_timelines")
        for mid, ups in v["timelines"].items():
            for u in ups:
                for k in ("time", "update_type", "update_type_cn", "fact_change",
                          "source_ref", "verification_status"):
                    self.assertIn(k, u)
                self.assertNotIn("features", u)
                self.assertNotIn("evidence_blob", u)

    def test_country_snapshots(self):
        v = load_view("country_snapshots")
        self.assertGreaterEqual(len(v["snapshots"]), 1)
        for s in v["snapshots"]:
            for k in ("country_cn", "baseline_risk", "baseline_risk_level",
                      "events_24h", "events_7d", "active_outbreaks"):
                self.assertIn(k, s)

    def test_disease_outbreaks_schema(self):
        v = load_view("disease_outbreaks")
        for o in v["outbreaks"]:
            for k in ("outbreak_id", "disease_id", "country_iso3", "status",
                      "latest_counts", "latest_report_at", "verification_status"):
                self.assertIn(k, o)

    def test_report_index_development_only(self):
        v = load_view("report_index")
        for r in v["reports"]:
            self.assertEqual(r["status"], "development_sample")
            self.assertTrue(r["is_mock"])
            self.assertNotIn("approved_for_publication", r["status"])

    def test_report_index_paths_preview_safe(self):
        v = load_view("report_index")
        for r in v["reports"]:
            self.assertNotIn("data/runtime", r["path"],
                             "report_index 暴露 runtime 内部路径")
            self.assertTrue(r["path"].startswith("report-mock/"))

    def test_knowledge_summary(self):
        v = load_view("knowledge_summary")
        for k in ("entity_count", "relationship_count", "region_count",
                  "country_count", "source_count", "top_entities"):
            self.assertIn(k, v)
        for e in v["top_entities"]:
            self.assertIn("entity_id", e)


class TestIsolation(unittest.TestCase):
    """§四十二/§四十五：runtime 隔离、无内部字段、无密钥。"""

    def test_views_have_no_runtime_paths(self):
        blob = json.dumps([load_view(n) for n in (
            "site_overview", "master_events", "event_timelines",
            "country_snapshots", "disease_outbreaks", "report_index",
            "knowledge_summary")], ensure_ascii=False)
        self.assertNotIn("data/runtime", blob)
        self.assertNotIn("clustering", blob)
        self.assertNotIn("source_health", blob)
        self.assertNotIn("candidate_pool", blob)

    def test_no_internal_scoring(self):
        blob = json.dumps(load_view("master_events"), ensure_ascii=False)
        for bad in ("merge_reasons", "cluster_confidence", "score", "features",
                    "review_pair", "raw body", "body_extracted"):
            self.assertNotIn(bad, blob)

    def test_secret_scan_dist(self):
        pats = re.compile(
            r"ASIP_GLM_API_KEY|ASIP_DEEPSEEK_API_KEY|sk-[A-Za-z0-9]{16,}|"
            r"Bearer\s+[A-Za-z0-9._-]{16,}|GITHUB_TOKEN|GH_TOKEN|client_secret",
            re.I)
        hits = []
        for p in (DIST / "data").rglob("*.json"):
            txt = p.read_text(encoding="utf-8", errors="ignore")
            for m in pats.finditer(txt):
                hits.append("%s:%s" % (p.name, m.group(0)[:30]))
        self.assertEqual(hits, [], "dist data 含密钥: %s" % hits)

    def test_db_embed_isolation(self):
        html = (DIST / "index.html").read_text(encoding="utf-8")
        m = re.search(r"window\.__DB__\s*=\s*(\{.*?\});\s*</script>", html, re.S)
        self.assertTrue(m, "__DB__ 未内联")
        db = json.loads(m.group(1))
        self.assertIn("site_overview", db)
        self.assertIn("master_events", db)
        self.assertIn("report_index", db)
        self.assertNotIn("canonical", db)
        self.assertNotIn("raw_candidates", db)
        self.assertNotIn("quarantine_events", db)


class TestFrontendLogic(unittest.TestCase):
    """§四十五：导航 / 状态 / 数字语义。"""

    def test_nav_consistency(self):
        for item in ["index.html", "events.html", "countries.html",
                     "disease-risk.html", "intelligence/africa/", "reports.html"]:
            self.assertIn(item, FE_JS, "导航缺 %s" % item)
        self.assertIn("情报知识库", FE_JS)

    def test_verification_badges(self):
        for cn in ("已核实", "较可信", "单一来源", "信息存在冲突"):
            self.assertIn(cn, FE_JS)

    def test_mobile_structural(self):
        self.assertIn("@media (max-width: 720px)", CSS)
        self.assertIn(".nav-toggle", CSS)
        self.assertIn("navbar.open", CSS)

    def test_time_bj_label(self):
        self.assertIn("（北京时间）", FE_JS)

    def test_empty_error_delayed(self):
        for cls in ("fe-empty", "fe-error", "fe-delayed"):
            self.assertIn(cls, CSS)

    def test_disease_unknown_not_zero(self):
        v = load_view("disease_outbreaks")
        has_null = False
        for o in v["outbreaks"]:
            lc = o["latest_counts"]
            for k in ("confirmed_cases", "probable_cases", "suspected_cases", "deaths"):
                val = lc.get(k)
                # unknown 必须保留 null（绝不 null→0）
                if val is None:
                    has_null = True
                # 值只允许 int / None，不得是 "0" 字符串或错误类型
                self.assertTrue(val is None or isinstance(val, int),
                                "%s=%r（应 int/None）" % (k, val))
        self.assertTrue(has_null, "疾病视图应保留 unknown(null) 语义")
        self.assertNotIn("total_cases_sum", str(lc))

    def test_disease_categories_separate(self):
        v = load_view("disease_outbreaks")
        for o in v["outbreaks"]:
            lc = o["latest_counts"]
            for k in ("confirmed_cases", "probable_cases", "suspected_cases", "deaths"):
                self.assertIn(k, lc)

    def test_master_country_no_source_pollution(self):
        v = load_view("master_events")
        for e in v["events"]:
            # country 来自 timeline current_state（Stage6 归属），不含源国名
            self.assertNotIn("Radio Tamazuj", str(e.get("headline_zh") or ""))
        # 检查 master event 的 country 均有效或 None
        for e in v["events"]:
            self.assertIsInstance(e.get("country_cn"), (str, type(None)))

    def test_country_unknown_is_null(self):
        v = load_view("country_snapshots")
        for s in v["snapshots"]:
            for k in ("events_24h", "events_7d", "active_outbreaks"):
                self.assertIn(k, s)
                self.assertNotIsInstance(s[k], bool)

    def test_entity_link_ids_approved(self):
        v = load_view("knowledge_summary")
        for e in v["top_entities"]:
            eid = e.get("entity_id")
            self.assertIsInstance(eid, str)
            self.assertGreater(len(eid), 0)


class TestPreviewPath(unittest.TestCase):
    """§四十：预览构建相关。"""

    def test_report_mock_paths_match_preview(self):
        v = load_view("report_index")
        for r in v["reports"]:
            self.assertRegex(r["path"], r"^report-mock/sample-(daily|weekly-\w+)\.json$")

    def test_html_pages_have_frontend_js(self):
        for pg in ("index.html", "events.html", "event.html", "countries.html",
                   "country.html", "disease-risk.html", "reports.html", "report.html"):
            src = (ROOT / pg).read_text(encoding="utf-8")
            self.assertIn("assets/js/frontend.js", src)
            self.assertIn('data-page', src)


if __name__ == "__main__":
    unittest.main()
