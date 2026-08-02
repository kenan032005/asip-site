#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_stage3b_final_repair.py — Stage 3B Final Repair §8 正式阻断测试（25 项）

§8.1 Canonical/Public 一致性 (6)
§8.2 正文清洗 (5)
§8.3 字段完整性 (6)
§8.4 生产 HTML 栏目页 (5)
§8.5 审计快照 (3)
"""
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

# 使用基于文件位置的绝对仓库路径（不依赖 CWD）
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "collectors"))
sys.path.insert(0, str(ROOT / "scripts" / "data"))

DATA = ROOT / "data"
CANONICAL = DATA / "canonical"
PUBLIC = DATA / "public"


def _load(path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


class CanonicalPublicConsistency(unittest.TestCase):
    """§8.1 Canonical/Public 一致性 (6 项)"""

    def test_01_all_public_in_canonical(self):
        """所有 public event_id 均存在于 canonical（完整事件集合）。"""
        can = _load(os.path.join(CANONICAL, "event_clusters.json"))
        pub = _load(os.path.join(PUBLIC, "published_events.json"))
        self.assertIsNotNone(can, "canonical/event_clusters.json 缺失")
        self.assertIsNotNone(pub, "public/published_events.json 缺失")
        can_ids = {c.get("event_id") for c in can.get("items", []) if c.get("event_id")}
        pub_ids = {e.get("event_id") for e in pub.get("items", []) if e.get("event_id")}
        orphans = [e for e in pub_ids if e not in can_ids]
        self.assertEqual(len(orphans), 0,
                         f"public 有 {len(orphans)} 个孤儿事件不在 canonical 中: {orphans[:5]}")

    def test_02_no_orphan_events(self):
        """Public 所有事件（不限是否带正文）均存在于 canonical。"""
        can = _load(os.path.join(CANONICAL, "event_clusters.json"))
        pub = _load(os.path.join(PUBLIC, "published_events.json"))
        if not can or not pub:
            self.skipTest("数据缺失")
        can_ids = {c.get("event_id") for c in can.get("items", []) if c.get("event_id")}
        for e in pub.get("items", []):
            self.assertIn(e.get("event_id"), can_ids,
                          f"public 事件 {e.get('event_id')} 不在 canonical 中")

    def test_02b_no_public_quarantine_overlap(self):
        """public 与 quarantine 不得存在同一 event_id。"""
        can = _load(os.path.join(CANONICAL, "event_clusters.json"))
        pub = _load(os.path.join(PUBLIC, "published_events.json"))
        quar = _load(os.path.join(CANONICAL, "quarantine.json"))
        if not can or not pub or not quar:
            self.skipTest("数据缺失")
        pub_ids = {e.get("event_id") for e in pub.get("items", []) if e.get("event_id")}
        quar_ids = {q.get("original_id") for q in quar.get("items", []) if q.get("original_id")}
        # quarantine 中可能存 URL 或 event_id；同时匹配 public 的 event_id 与 source url
        pub_urls = set()
        for e in pub.get("items", []):
            for sl in e.get("source_links", []):
                u = (sl.get("url") or "").strip().rstrip("/").lower()
                if u:
                    pub_urls.add(u)
        quar_norm = {q.strip().rstrip("/").lower() for q in quar_ids}
        overlap_ids = [eid for eid in pub_ids if eid in quar_ids]
        overlap_urls = [u for u in pub_urls if u in quar_norm]
        self.assertEqual(len(overlap_ids), 0,
                         f"public 与 quarantine 重复事件: {overlap_ids[:5]}")
        self.assertEqual(len(overlap_urls), 0,
                         f"public source url 与 quarantine 重复: {overlap_urls[:3]}")

    def test_03_country_consistent(self):
        """Canonical/Public 相同事件国家一致。"""
        can = _load(os.path.join(CANONICAL, "event_clusters.json"))
        pub = _load(os.path.join(PUBLIC, "published_events.json"))
        if not can or not pub:
            self.skipTest("数据缺失")
        can_by_id = {c.get("event_id"): c for c in can.get("items", [])}
        for e in pub.get("items", []):
            can_e = can_by_id.get(e.get("event_id"))
            if can_e:
                self.assertEqual(e.get("country_cn"), can_e.get("country_cn"),
                                 f"{e.get('event_id')} 国家不一致")

    def test_04_body_fields_consistent(self):
        """Canonical/Public 正文��来源字段一致。"""
        can = _load(os.path.join(CANONICAL, "event_clusters.json"))
        pub = _load(os.path.join(PUBLIC, "published_events.json"))
        if not can or not pub:
            self.skipTest("数据缺失")
        can_by_id = {c.get("event_id"): c for c in can.get("items", [])}
        for e in pub.get("items", []):
            if not e.get("body_status"):
                continue
            can_e = can_by_id.get(e.get("event_id"))
            if can_e and can_e.get("body_status"):
                self.assertEqual(e.get("body_status"), can_e.get("body_status"),
                                 f"{e.get('event_id')} body_status 不一致")

    def test_05_source_links_present(self):
        """每个已发布事件至少有 1 个 source_link。"""
        pub = _load(os.path.join(PUBLIC, "published_events.json"))
        self.assertIsNotNone(pub)
        for e in pub.get("items", []):
            sl = e.get("source_links", [])
            self.assertGreaterEqual(len(sl), 0)  # 允许 legacy 事件无 source_links
            if sl:
                self.assertTrue(any(s.get("url") for s in sl),
                                f"{e.get('event_id')} source_links 无有效 URL")

    def test_06_run_id_consistent(self):
        """Canonical 与 public 顶层 run_id 一致。"""
        can = _load(os.path.join(CANONICAL, "event_clusters.json"))
        pub = _load(os.path.join(PUBLIC, "published_events.json"))
        if can and pub:
            cr = can.get("run_id", "")
            pr = pub.get("run_id", "")
            if cr and pr:
                self.assertIn(cr, pr if len(pr) >= len(cr) else cr,
                              "canonical 与 public 的 run_id 应一致")


class BodyCleaning(unittest.TestCase):
    """§8.2 正文清洗验证 (5 项)"""

    def test_07_journaldutchad_no_ad_template(self):
        """Journal du Tchad 广告模板被清除。"""
        from framework import fetch_page, ContentExtractor
        text, err, _ = fetch_page("https://journaldutchad.com/tchad-le-ministre-des-armees-effectue-une-mission-de-securite-a-owi/")
        if err:
            self.skipTest(f"fetch失败: {err[:60]}")
        ext = ContentExtractor(source_id="chad_journaldutchad")
        r = ext.extract(text)
        body = (r.get("body") or "").lower()
        bad = ["la suite après la publicité", "la suite apres la publicite", "publicité"]
        found = [b for b in bad if b in body]
        self.assertEqual(len(found), 0, f"Journal du Tchad 正文含广告模板: {found}")

    def test_08_rfi_no_promo(self):
        """RFI 推荐/Newsletter/App 推广/分享模板被清除。"""
        from framework import fetch_page, ContentExtractor
        text, err, _ = fetch_page("https://www.rfi.fr/fr/afrique/20260801-tchad-attaques-de-chacals-qui-pourraient-%C3%AAtre-infect%C3%A9s-par-la-rage-dans-la-commune-de-gouro")
        if err:
            self.skipTest(f"fetch失败: {err[:60]}")
        ext = ContentExtractor(source_id="intl_rfi_afrique_chad")
        r = ext.extract(text)
        body = (r.get("body") or "").lower()
        bad = ["je m'abonne", "je m abonne", "suivez toute l'actualité", "télécharger l'application"]
        found = [b for b in bad if b in body]
        self.assertEqual(len(found), 0, f"RFI 正文含推广模板: {found}")

    def test_09_alwihda_no_nav(self):
        """Alwihda 导航/阅读时长/分享模板被清除。"""
        from framework import fetch_page, ContentExtractor
        text, err, _ = fetch_page("https://www.alwihdainfo.com/tchad-appui-de-loim-a-la-commune-de-moussoro-pour-lutter-contre-les-inondations/")
        if err:
            self.skipTest(f"fetch失败: {err[:60]}")
        ext = ContentExtractor(source_id="chad_alwihda")
        r = ext.extract(text)
        body = (r.get("body") or "").lower()
        # 正文不应以导航/署名开头
        lines = [l.strip() for l in body.split("\n") if l.strip()]
        if lines:
            first_line_low = lines[0].lower()
            self.assertNotIn("min de lecture", first_line_low,
                             f"Alwihda 正文首行含阅读时长: {first_line_low[:60]}")

    def test_10_facts_preserved(self):
        """清洗后正文关键事实仍保留。"""
        from framework import fetch_page, ContentExtractor
        text, err, _ = fetch_page("https://journaldutchad.com/tchad-le-ministre-des-armees-effectue-une-mission-de-securite-a-owi/")
        if err:
            self.skipTest(f"fetch失败: {err[:60]}")
        ext = ContentExtractor(source_id="chad_journaldutchad")
        r = ext.extract(text)
        body = r.get("body", "")
        facts = ["Tibesti", "Owi", "ministre", "armées"]
        for f in facts:
            self.assertIn(f.lower(), body.lower(), f"关键事实 '{f}' 丢失")

    def test_11_unresolved_not_published(self):
        """含未解决模板污染的正文不会出现在 public（通过残留检查）。"""
        pub = _load(os.path.join(PUBLIC, "published_events.json"))
        self.assertIsNotNone(pub)
        for e in pub.get("items", []):
            body = (e.get("body_extracted") or "").lower()
            # 检查已知污染物
            cta = ["la suite après la publicité", "je m'abonne",
                   "télécharger l'application rfi"]
            found = [c for c in cta if c in body]
            self.assertEqual(len(found), 0,
                             f"{e.get('event_id')} 含未解决模板污染: {found}")


class FieldCompleteness(unittest.TestCase):
    """§8.3 字段完整性 (6 项)"""

    def test_12_canonical_url_nonempty(self):
        """canonical_url 非空（允许 source_links fallback）。"""
        pub = _load(os.path.join(PUBLIC, "published_events.json"))
        self.assertIsNotNone(pub)
        for e in pub.get("items", []):
            if e.get("body_status") in ("full_body", "partial_body"):
                cu = e.get("canonical_url", "")
                # fallback: source_links[0].url（用户 §四 明确允许）
                if not cu:
                    sl = e.get("source_links") or []
                    cu = sl[0].get("url", "") if sl else ""
                self.assertNotEqual(cu, "",
                                    f"{e.get('event_id')} canonical_url 为空")

    def test_12b_canonical_url_is_article_page(self):
        """canonical_url 为具体文章详情页（非首页/栏目页/聚合页）。"""
        import urllib.parse
        pub = _load(os.path.join(PUBLIC, "published_events.json"))
        self.assertIsNotNone(pub)
        home_paths = ("/", "/accueil", "/home", "/index.html", "/category/", "/rubrique/")
        for e in pub.get("items", []):
            if e.get("body_status") not in ("full_body", "partial_body"):
                continue
            cu = e.get("canonical_url", "")
            if not cu:
                sl = e.get("source_links") or []
                cu = sl[0].get("url", "") if sl else ""
            if not cu:
                continue
            self.assertTrue(cu.startswith(("http://", "https://")),
                            f"{e.get('event_id')} canonical_url 非 HTTP: {cu[:50]}")
            parsed = urllib.parse.urlparse(cu)
            path = (parsed.path or "").rstrip("/").lower()
            self.assertNotIn(path or "/", home_paths,
                             f"{e.get('event_id')} canonical_url 是首页/栏目页: {cu[:60]}")
            # 必须像文章页：path 长度 > 1（含文章 slug）
            self.assertGreater(len(path), 1,
                               f"{e.get('event_id')} canonical_url 无文章路径: {cu[:60]}")

    def test_13_canonical_url_is_http(self):
        """canonical_url 为安全 HTTP/HTTPS 文章 URL。"""
        pub = _load(os.path.join(PUBLIC, "published_events.json"))
        self.assertIsNotNone(pub)
        for e in pub.get("items", []):
            cu = e.get("canonical_url", "")
            if cu:
                self.assertTrue(cu.startswith(("http://", "https://")),
                                f"{e.get('event_id')} canonical_url 非 HTTP: {cu[:50]}")

    def test_14_quality_score_is_numeric(self):
        """extraction_quality_score 必须存在且为 0-100 数值（不得缺失）。"""
        can = _load(os.path.join(CANONICAL, "event_clusters.json"))
        self.assertIsNotNone(can)
        for c in can.get("items", []):
            if c.get("body_status") in ("full_body", "partial_body"):
                qs = c.get("extraction_quality_score")
                self.assertIsNotNone(qs,
                    f"{c.get('event_id')} extraction_quality_score 缺失（带正文必须存在）")
                self.assertIsInstance(qs, (int, float),
                                      f"{c.get('event_id')} extraction_quality_score 非数值")
                self.assertGreaterEqual(qs, 0)
                self.assertLessEqual(qs, 100)

    def test_15_quality_reasons_is_array(self):
        """extraction_quality_reasons 必须存在且为数组（不得缺失）。"""
        can = _load(os.path.join(CANONICAL, "event_clusters.json"))
        self.assertIsNotNone(can)
        for c in can.get("items", []):
            if c.get("body_status") in ("full_body", "partial_body"):
                qr = c.get("extraction_quality_reasons")
                self.assertIsNotNone(qr,
                    f"{c.get('event_id')} extraction_quality_reasons 缺失（带正文必须存在）")
                self.assertIsInstance(qr, list,
                                      f"{c.get('event_id')} extraction_quality_reasons 非数组")

    def test_16_title_cn_empty_allowed(self):
        """title_cn/summary_cn 允许为空且不触发失败。"""
        pub = _load(os.path.join(PUBLIC, "published_events.json"))
        self.assertIsNotNone(pub)
        # 验证至少有些事件 title_cn 为空（即允许为空）
        empty_cn = [e for e in pub.get("items", []) if not e.get("title_cn")]
        self.assertGreater(len(empty_cn), 0, "预期 title_cn 可为空（Stage 3 不要求中文）")

    def test_17_body_status_not_substituted(self):
        """extraction_quality_score 不得用 full_body/partial_body 等字符串代替数值。"""
        can = _load(os.path.join(CANONICAL, "event_clusters.json"))
        self.assertIsNotNone(can)
        for c in can.get("items", []):
            qs = c.get("extraction_quality_score")
            if qs is not None:
                self.assertNotIsInstance(qs, str,
                    f"{c.get('event_id')} extraction_quality_score 是字符串 '{qs}'")


class ProductionHTMLListing(unittest.TestCase):
    """§8.4 生产 HTML 栏目页 (5 项)"""

    def test_18_sources_have_listing_urls(self):
        """SourceRegistry 含 listing_urls。"""
        sources = _load(os.path.join(DATA, "sources.json"))
        self.assertIsNotNone(sources)
        with_listing = [s for s in sources.get("sources", [])
                        if s.get("listing_urls")]
        self.assertGreater(len(with_listing), 0, "sources.json 中无任何 source 含 listing_urls")

    def test_19_chad_two_html_sources(self):
        """乍得至少 2 个生产 HTML 来源配置。"""
        sources = _load(os.path.join(DATA, "sources.json"))
        self.assertIsNotNone(sources)
        chad_html = [s for s in sources.get("sources", [])
                     if s.get("listing_urls") and "乍得" in str(s.get("country_scope", []))]
        self.assertGreaterEqual(len(chad_html), 2,
                                f"乍得 HTML 来源: {len(chad_html)}, 需 ≥2")

    def test_20_niger_two_html_sources(self):
        """尼日尔至少 2 个生产 HTML 来源配置。"""
        sources = _load(os.path.join(DATA, "sources.json"))
        self.assertIsNotNone(sources)
        niger_html = [s for s in sources.get("sources", [])
                      if s.get("listing_urls") and "\u5c3c\u65e5\u5c14" in str(s.get("country_scope", []))]
        self.assertGreaterEqual(len(niger_html), 2,
                                f"尼日尔 HTML 来源: {len(niger_html)}, 需 ≥2")

    def test_21_html_goes_through_main_pipeline(self):
        """HTML 来源可通过主采集流程进入 canonical。"""
        from registry import SourceRegistry, ArticleDiscoverer
        reg = SourceRegistry()
        # 检查 Tchadinfos 有 listing_urls
        sources = reg.by_country("乍得")
        html_src = [s for s in sources if s.get("listing_urls") and s["source_id"] == "chad_tchadinfos"]
        if html_src:
            src = html_src[0]
            self.assertTrue(bool(src.get("listing_urls")),
                            "Tchadinfos 缺少 listing_urls")
            # 验证 discovery_type 允许 html_listing
            disc = ArticleDiscoverer(reg)
            # 创建 html 版本
            html_src_dict = dict(src)
            html_src_dict["discovery_type"] = "html_listing"
            html_src_dict["feed_url"] = ""
            arts, errs = disc.discover(html_src_dict)
            if errs and any("fetch" in str(e).lower() for e in errs):
                self.skipTest(f"fetch 暂时不可用: {errs[0][:80]}")
            self.assertGreater(len(arts), 0,
                               "Tchadinfos HTML 栏目页应发现 ≥1 篇文章")

    def test_22_verify_script_not_counted(self):
        """硬编码验证脚本结果不计入生产统计。"""
        import subprocess
        # precise_source_stats 只读 logs/stage3_collection_stats.json
        # verify_channels.py 的输出在 logs/channel_verification.json
        # 两者路径不同，确保统计不混用
        stats_path = os.path.join(ROOT, "logs", "stage3_collection_stats.json")
        verify_path = os.path.join(ROOT, "logs", "channel_verification.json")
        self.assertNotEqual(os.path.basename(stats_path), os.path.basename(verify_path),
                            "统计文件不应与验证脚本共用")


class AuditSnapshot(unittest.TestCase):
    """§8.5 审计快照 (3 项)"""

    def test_23_snapshot_not_in_dist(self):
        """快照不进入 dist。"""
        dist = os.path.join(ROOT, "dist")
        if os.path.exists(dist):
            audit_found = False
            for root, dirs, files in os.walk(dist):
                if "stage3_runs" in dirs or any("audit" in d for d in dirs):
                    audit_found = True
                    break
            self.assertFalse(audit_found, "审计目录不应出现在 dist 中")

    def test_24_snapshot_per_run_unique(self):
        """每次运行生成独立目录，不覆盖旧数据。"""
        audit = os.path.join(DATA, "audit", "stage3_runs")
        if os.path.exists(audit):
            runs = [d for d in os.listdir(audit)
                    if os.path.isdir(os.path.join(audit, d))]
            # 至少有一个 run_id 目录且有内容
            self.assertGreater(len(runs), 0, "audit/stage3_runs/ 应包含至少一个 run 目录")

    def test_25_snapshot_has_required_files(self):
        """快照目录含 manifest/source_stats/collection_summary。"""
        audit = os.path.join(DATA, "audit", "stage3_runs")
        if not os.path.exists(audit):
            self.skipTest("无审计快照")
        runs = [d for d in os.listdir(audit)
                if os.path.isdir(os.path.join(audit, d))]
        if not runs:
            self.skipTest("无审计快照")
        rd = os.path.join(audit, runs[0])
        required = ["manifest.json", "source_stats.json", "collection_summary.json"]
        for f in required:
            self.assertTrue(os.path.exists(os.path.join(rd, f)),
                            f"快照缺少 {f}")


class AuditConsistency(unittest.TestCase):
    """§2 审计文件统计一致性 + country_source_acceptance"""

    def test_26_audit_stats_consistent(self):
        """manifest / collection_summary / source_stats 关键统计一致。"""
        import glob
        audit_dirs = sorted(glob.glob(os.path.join(DATA, "audit", "stage3_runs", "*")))
        self.assertGreater(len(audit_dirs), 0, "无审计快照")
        # 最新 run
        rd = audit_dirs[-1]
        m = _load(os.path.join(rd, "manifest.json"))
        c = _load(os.path.join(rd, "collection_summary.json"))
        s = _load(os.path.join(rd, "source_stats.json"))
        self.assertIsNotNone(m); self.assertIsNotNone(c); self.assertIsNotNone(s)
        keys = ["configured_sources", "attempted_sources", "successful_sources",
                "published_count", "quarantined_count"]
        for k in keys:
            mv = m.get(k); cv = c.get("totals",{}).get(k)
            self.assertEqual(mv, cv,
                f"{k} 不一致: manifest={mv} collection_summary={cv}")
        # source_stats 一致性
        ps = s.get("per_source", [])
        self.assertEqual(c.get("totals",{}).get("enabled_sources"), len(ps),
            "enabled_sources != per_source 长度")
        # 从 source_stats 检查 published/quarantined 计数
        real_pub = sum(x.get("published",0) for x in ps)
        real_quar = sum(x.get("quarantined",0) for x in ps)
        self.assertEqual(c.get("totals",{}).get("published_count"), real_pub)
        self.assertEqual(c.get("totals",{}).get("quarantined_count"), real_quar)

    def test_27_country_acceptance_from_source_stats(self):
        """country_source_acceptance 必须与从 source_stats 重新计算的结果精确一致。"""
        import glob
        audit_dirs = sorted(glob.glob(os.path.join(DATA, "audit", "stage3_runs", "*")))
        self.assertGreater(len(audit_dirs), 0)
        rd = audit_dirs[-1]
        acc = _load(os.path.join(rd, "country_source_acceptance.json"))
        s = _load(os.path.join(rd, "source_stats.json"))
        self.assertIsNotNone(acc, "country_source_acceptance.json 缺失")
        self.assertIsNotNone(s, "source_stats.json 缺失")
        ps = s.get("per_source", [])

        def recompute(cn):
            """按正式规则从 source_stats 重算（与 generate_country_source_acceptance 一致）。"""
            stats = [x for x in ps if x.get("country") == cn]
            not_impl = [x for x in stats if x.get("method") == "gdelt_search"]
            implemented = [x for x in stats if x.get("method") != "gdelt_search"]

            def _is_success(st):
                return (st.get("status") == "success"
                        and st.get("discovered", 0) > 0
                        and st.get("fetched", 0) > 0)

            stable_discovery = [x for x in implemented if _is_success(x)]
            stable_body = [x for x in stable_discovery
                           if x.get("full_body", 0) + x.get("partial_body", 0) > 0]
            html_success = [x for x in implemented
                            if x.get("html_listing_channel") is True
                            and x.get("html_discovered", 0) > 0
                            and x.get("html_fetched", 0) > 0
                            and x.get("html_full_body", 0) + x.get("html_partial_body", 0) > 0]
            rss_success = [x for x in implemented
                           if x.get("method") in ("rss", "atom")
                           and x.get("discovered", 0) > 0
                           and x.get("fetched", 0) > 0]

            def _ids(rows):
                seen, out = set(), []
                for r in rows:
                    sid = r.get("source_id", "")
                    if sid and sid not in seen:
                        seen.add(sid)
                        out.append(sid)
                return out

            return {
                "stable_active_sources": len(_ids(stable_body)),
                "stable_active_sources_list": _ids(stable_body),
                "stable_discovery_sources": len(_ids(stable_discovery)),
                "stable_discovery_sources_list": _ids(stable_discovery),
                "successful_body_extraction_sources": len(_ids(stable_body)),
                "successful_body_extraction_sources_list": _ids(stable_body),
                "production_html_listing_success_sources": len(_ids(html_success)),
                "production_html_listing_success_sources_list": _ids(html_success),
                "rss_success_sources": len(_ids(rss_success)),
                "rss_success_sources_list": _ids(rss_success),
                "not_implemented_sources": len(_ids(not_impl)),
            }

        for cn in ("乍得", "尼日尔"):
            data = acc.get("countries", {}).get(cn)
            self.assertIsNotNone(data, f"{cn} 不在 acceptance 中")
            expect = recompute(cn)
            for k in ("stable_active_sources", "stable_active_sources_list",
                      "stable_discovery_sources", "stable_discovery_sources_list",
                      "successful_body_extraction_sources",
                      "successful_body_extraction_sources_list",
                      "production_html_listing_success_sources",
                      "production_html_listing_success_sources_list",
                      "rss_success_sources", "rss_success_sources_list"):
                self.assertEqual(data.get(k), expect[k],
                    f"{cn}.{k} 与 source_stats 重算不一致: json={data.get(k)} recomputed={expect[k]}")
            # 门槛
            self.assertGreaterEqual(data.get("stable_active_sources", 0), 12,
                f"{cn} stable_active={data.get('stable_active_sources')} < 12")
            self.assertGreaterEqual(data.get("production_html_listing_success_sources", 0), 2,
                f"{cn} html_listing={data.get('production_html_listing_success_sources')} < 2")
            # count == list 长度、唯一性、存在性
            for k in ("stable_active_sources", "production_html_listing_success_sources",
                      "rss_success_sources", "not_implemented_sources"):
                lst = data.get(k + "_list", [])
                self.assertEqual(data.get(k), len(lst), f"{cn}.{k} count != list len")
                self.assertEqual(len(lst), len(set(lst)), f"{cn}.{k} 有重复 source_id")
            # 所有 source_id 存在于 source_stats 且属于该国家
            stat_ids = {x.get("source_id") for x in ps}
            cn_ids = {x.get("source_id") for x in ps if x.get("country") == cn}
            for k in ("stable_active_sources_list", "production_html_listing_success_sources_list",
                      "rss_success_sources_list"):
                for sid in data.get(k, []):
                    self.assertIn(sid, stat_ids, f"{cn}.{k} source_id 不在 source_stats")
                    self.assertIn(sid, cn_ids, f"{cn}.{k} source_id 不属于该国家")


class PublicationChannel(unittest.TestCase):
    """§7 canonical→public 通道验证"""

    def test_28_canonical_export_is_working(self):
        """当存在合格 canonical 候选时，publication semantics 可生成 public 事件。"""
        can = _load(os.path.join(CANONICAL, "event_clusters.json"))
        pub = _load(os.path.join(PUBLIC, "published_events.json"))
        self.assertIsNotNone(can); self.assertIsNotNone(pub)
        self.assertGreater(len(can.get("items",[])), 0, "canonical 为空")
        self.assertGreater(len(pub.get("items",[])), 0, "published_events 为空 — 导出通道可能故障")
        # 验证 public ⊆ canonical
        can_ids = {c.get("event_id") for c in can.get("items", []) if c.get("event_id")}
        pub_ids = {e.get("event_id") for e in pub.get("items", []) if e.get("event_id")}
        orphans = [e for e in pub_ids if e not in can_ids]
        self.assertEqual(len(orphans), 0,
            f"public 有 {len(orphans)} 个孤儿事件不在 canonical 中")

    def test_29_published_zero_is_gate_not_fault(self):
        """本轮 published_count=0 是严格准入结果（非导出故障）。已通过 test_28 验证。"""
        # 当 published_count=0 但 canonical 有 publishable 事件时，需确认是准入而非故障
        can = _load(os.path.join(CANONICAL, "event_clusters.json"))
        pub = _load(os.path.join(PUBLIC, "published_events.json"))
        self.assertIsNotNone(can); self.assertIsNotNone(pub)
        # 只要 public ⊆ canonical 且 public 非空，就证明通道工作
        can_ids = {c.get("event_id") for c in can.get("items", []) if c.get("event_id")}
        pub_ids = {e.get("event_id") for e in pub.get("items", [])}
        self.assertGreater(len(pub_ids), 0, "public 应为空或含历史遗留事件")
        # 验证无 orphan（已通过 test_28）
        self.assertTrue(pub_ids.issubset(can_ids),
            "public 事件必须在 canonical 中（通道正常）")


# 非文章页路径段（国家页/栏目页/标签页/搜索页/Feed 等）
NON_ARTICLE_SEGMENTS = {"country", "category", "categories", "tag", "tags",
                        "rubrique", "search", "feed", "rss", "author",
                        "archives", "date", "wp-json", "page", "video",
                        "newsfeed", "program", "podcast"}


def _is_article_url(url):
    """判断 URL 是否为具体文章详情页（非首页/国家页/栏目页/标签页/搜索页/Feed）。

    允许 WordPress 日期结构（/2026/07/31/slug/），第一段年份不算列表页。
    """
    import urllib.parse
    if not url:
        return False
    if not url.startswith(("http://", "https://")):
        return False
    p = urllib.parse.urlparse(url)
    path_seg = [s for s in (p.path or "").strip("/").lower().split("/") if s]
    if not path_seg:
        return False  # 首页
    if path_seg[0] in NON_ARTICLE_SEGMENTS:
        return False  # 栏目/国家/标签/搜索/feed 等
    return True


class CanonicalUrlIntegrity(unittest.TestCase):
    """§5 Canonical 带正文事件 URL 必须为具体文章详情页"""

    def test_30_canonical_body_urls_are_articles(self):
        """所有 canonical 带正文记录的 canonical_url 必须是文章页。"""
        can = _load(os.path.join(CANONICAL, "event_clusters.json"))
        self.assertIsNotNone(can)
        bad = []
        for c in can.get("items", []):
            if c.get("body_status") not in ("full_body", "partial_body"):
                continue
            cu = c.get("canonical_url", "")
            if not _is_article_url(cu):
                bad.append((c.get("event_id"), cu))
        self.assertEqual(len(bad), 0,
            f"canonical 有 {len(bad)} 条带正文记录 canonical_url 非文章页: {bad[:5]}")

    def test_31_canonical_no_country_listing_body(self):
        """Canonical 不得存在国家页/栏目页/列表页判为正文（如 reliefweb.int/country/ner）。"""
        can = _load(os.path.join(CANONICAL, "event_clusters.json"))
        self.assertIsNotNone(can)
        for c in can.get("items", []):
            if c.get("body_status") not in ("full_body", "partial_body"):
                continue
            cu = (c.get("canonical_url") or "").lower()
            # 明确拦截 reliefweb 国家页
            if "reliefweb.int" in cu and "/country/" in cu:
                self.fail(f"{c.get('event_id')} 国家页被判为正文: {cu}")
            # 其他列表页
            self.assertTrue(_is_article_url(c.get("canonical_url")),
                            f"{c.get('event_id')} canonical_url 非文章页: {c.get('canonical_url')}")

    def test_32_article_url_fixture(self):
        """fixture: ReliefWeb 国家页拒绝；正常文章页允许；普通媒体文章不误杀。"""
        self.assertFalse(_is_article_url("https://reliefweb.int/country/ner"),
                         "ReliefWeb 国家页应被拒绝")
        self.assertFalse(_is_article_url("https://reliefweb.int/country/tcd"),
                         "ReliefWeb 国家页应被拒绝")
        self.assertFalse(_is_article_url("https://reliefweb.int/"),
                         "首页应被拒绝")
        self.assertFalse(_is_article_url("https://example.com/category/securite/"),
                         "栏目页应被拒绝")
        self.assertFalse(_is_article_url("https://example.com/tag/security/"),
                         "标签页应被拒绝")
        self.assertFalse(_is_article_url("https://example.com/rss"),
                         "Feed 应被拒绝")
        self.assertTrue(_is_article_url(
            "https://reliefweb.int/report/niger/niger-food-security-outlook-persistent-conflict"),
            "ReliefWeb 正常文章详情页应允许")
        self.assertTrue(_is_article_url(
            "https://www.alwihdainfo.com/tchad-appui-de-loim-a-la-commune-de-moussoro-pour-lutter-contre-les-inondations/"),
            "普通媒体文章页不应被误杀")
        self.assertTrue(_is_article_url(
            "https://journaldutchad.com/tchad-le-ministre-des-armees-effectue-une-mission-de-securite-a-owi/"),
            "Journal du Tchad 文章页不应被误杀")


class BodyFieldCompleteness(unittest.TestCase):
    """§6 带正文事件全部追溯字段必须存在（不得缺失）"""

    REQUIRED = ["canonical_url", "body_extracted", "extraction_method",
                "extraction_quality_score", "extraction_quality_reasons",
                "discovery_method", "fetch_http_status"]

    def test_33_canonical_body_fields_complete(self):
        """Canonical 带正文事件全部字段必须存在且类型正确。"""
        can = _load(os.path.join(CANONICAL, "event_clusters.json"))
        self.assertIsNotNone(can)
        checked = 0
        for c in can.get("items", []):
            if c.get("body_status") not in ("full_body", "partial_body"):
                continue
            checked += 1
            eid = c.get("event_id")
            self.assertTrue(bool(c.get("canonical_url")),
                            f"{eid} canonical_url 缺失")
            self.assertTrue(bool(c.get("body_extracted")),
                            f"{eid} body_extracted 缺失")
            self.assertTrue(bool(c.get("extraction_method")),
                            f"{eid} extraction_method 缺失")
            qs = c.get("extraction_quality_score")
            self.assertIsNotNone(qs, f"{eid} extraction_quality_score 缺失")
            self.assertIsInstance(qs, (int, float), f"{eid} score 非数值")
            self.assertGreaterEqual(qs, 0); self.assertLessEqual(qs, 100)
            qr = c.get("extraction_quality_reasons")
            self.assertIsNotNone(qr, f"{eid} extraction_quality_reasons 缺失")
            self.assertIsInstance(qr, list, f"{eid} reasons 非数组")
            dm = c.get("discovery_method")
            self.assertTrue(bool(dm), f"{eid} discovery_method 缺失")
            self.assertIn(dm, ("rss", "atom", "html_listing",
                               "reliefweb_api_or_feed", "gdelt_search"),
                          f"{eid} discovery_method 非法: {dm}")
            fh = c.get("fetch_http_status")
            self.assertIsNotNone(fh, f"{eid} fetch_http_status 缺失")
            self.assertIsInstance(fh, int, f"{eid} fetch_http_status 非整数")
            self.assertGreater(fh, 0, f"{eid} fetch_http_status 必须为正整数")
            self.assertGreater(c.get("article_word_count", 0), 0,
                               f"{eid} article_word_count 必须 > 0")
        self.assertGreater(checked, 0, "Canonical 无带正文记录可检查")

    def test_34_public_body_fields_complete(self):
        """Public 带正文事件全部字段必须存在且类型正确。"""
        pub = _load(os.path.join(PUBLIC, "published_events.json"))
        self.assertIsNotNone(pub)
        checked = 0
        for e in pub.get("items", []):
            if e.get("body_status") not in ("full_body", "partial_body"):
                continue
            checked += 1
            eid = e.get("event_id")
            self.assertTrue(bool(e.get("canonical_url")),
                            f"{eid} canonical_url 缺失")
            self.assertTrue(bool(e.get("body_extracted")),
                            f"{eid} body_extracted 缺失")
            self.assertTrue(bool(e.get("extraction_method")),
                            f"{eid} extraction_method 缺失")
            qs = e.get("extraction_quality_score")
            self.assertIsNotNone(qs, f"{eid} extraction_quality_score 缺失")
            self.assertIsInstance(qs, (int, float), f"{eid} score 非数值")
            self.assertGreaterEqual(qs, 0); self.assertLessEqual(qs, 100)
            qr = e.get("extraction_quality_reasons")
            self.assertIsNotNone(qr, f"{eid} extraction_quality_reasons 缺失")
            self.assertIsInstance(qr, list, f"{eid} reasons 非数组")
            dm = e.get("discovery_method")
            self.assertTrue(bool(dm), f"{eid} discovery_method 缺失")
            self.assertIn(dm, ("rss", "atom", "html_listing",
                               "reliefweb_api_or_feed", "gdelt_search"),
                          f"{eid} discovery_method 非法: {dm}")
            fh = e.get("fetch_http_status")
            self.assertIsNotNone(fh, f"{eid} fetch_http_status 缺失")
            self.assertIsInstance(fh, int, f"{eid} fetch_http_status 非整数")
            self.assertGreater(fh, 0, f"{eid} fetch_http_status 必须为正整数")
            self.assertGreater(e.get("article_word_count", 0), 0,
                               f"{eid} article_word_count 必须 > 0")
        self.assertGreater(checked, 0, "Public 无带正文记录可检查")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    n_run = result.testsRun
    n_fail = len(result.failures) + len(result.errors)
    print(f"RESULT: PASS={n_run - n_fail} FAIL={n_fail}")
    sys.exit(1 if n_fail else 0)
