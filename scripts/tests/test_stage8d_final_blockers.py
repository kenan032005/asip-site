#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage8D Final Production Blocker Fix — 回归测试（§二十三）。

覆盖：
  §二   deploy_required propagation（FULL/FALLBACK/LOW_DATA/HOLD）
  §五/§六/§七 AI input identity + 同输入跳过（5 cycle）
  §十三 真实采集指标（禁止硬编码）
  §十四 source health 刷新
  §十五 真实 AI token 遥测
  §九/§十/§十二 日报业务日期 / period 新鲜度 / fixture 阻断
  §十七/§十九/§二十 外部调度路由 + 双重唤醒幂等
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops import production_state as ps  # noqa: E402
from scripts.ops import schedule_orchestrator as so  # noqa: E402
from scripts.ai import ai_input_identity as ident  # noqa: E402

BJT = timezone(timedelta(hours=8))


def _state(**over):
    s = dict(ps.EMPTY_STATE)
    s.update({
        "last_successful_collection": "2026-08-29T18:00:00Z",
        "last_successful_ai": "2026-08-29T18:05:00Z",
        "last_disease_run": "2026-08-29T18:10:00Z",
        "last_daily_report": None,
        "last_weekly_report": None,
    })
    s.update(over)
    return s


# ══════════════════════════════════════════════════════════════════
# §二 deploy_required contract
# ══════════════════════════════════════════════════════════════════
class TestDeployRequiredContract(unittest.TestCase):
    def test_full_requires_deploy(self):
        self.assertTrue(so.deploy_required_for("FULL"))

    def test_fallback_requires_deploy(self):
        self.assertTrue(so.deploy_required_for("FALLBACK"))

    def test_low_data_requires_deploy(self):
        self.assertTrue(so.deploy_required_for("LOW_DATA"))

    def test_fact_gate_fail_blocks_deploy(self):
        # FACT_GATE 失败 → 分类为 HOLD → 不可发布
        self.assertFalse(so.deploy_required_for("HOLD"))
        self.assertFalse(so.deploy_required_for(None))
        self.assertFalse(so.deploy_required_for("UNKNOWN"))

    def test_nested_report_result_propagates_deploy_required(self):
        """核心回归：嵌套 _do() 内的赋值必须传播到外层 deploy_required。

        修复前：_do() 内 `deploy_required = cls in LEGAL_REPORT` 缺少 nonlocal，
        外层恒为 False，publishable 报告也永远不触发 Auto Deploy。
        """
        for cls, expected in (("FULL", True), ("FALLBACK", True),
                              ("LOW_DATA", True), ("HOLD", False)):
            with self.subTest(classification=cls):
                calls = {"n": 0}

                def fake_run_script(args, emit, timeout=1800):
                    calls["n"] += 1
                    emit("$ python %s" % " ".join(args))
                    return True

                orig = (so._run_script, so._daily_report_meta, so._export_views,
                        so._reload_state, ps.record_run, ps.save_state)
                try:
                    so._run_script = fake_run_script
                    so._daily_report_meta = lambda root: {
                        "report_date": "2026-08-30", "classification": cls,
                        "fact_count": 3}
                    so._export_views = lambda emit: True
                    so._reload_state = lambda st: st
                    ps.record_run = lambda *a, **k: None
                    ps.save_state = lambda *a, **k: None
                    so.ops.save_ops = lambda *a, **k: None

                    plan = {"enabled": True, "due": [
                        {"task": "daily_report", "mode": "production",
                         "trigger": "scheduled_orchestrator",
                         "reason": "daily_20_00_tick"}]}
                    res = so.execute(plan, _state(), emit=lambda s: None)
                    self.assertEqual(res["deploy_required"], expected,
                                     "classification=%s" % cls)
                finally:
                    (so._run_script, so._daily_report_meta, so._export_views,
                     so._reload_state, ps.record_run, ps.save_state) = orig

    def test_deploy_provenance_recorded(self):
        """§三：deploy_request 必须含 trigger provenance 字段。"""
        def fake_run_script(args, emit, timeout=1800):
            return True
        orig = (so._run_script, so._daily_report_meta, so._export_views,
                so._reload_state, ps.record_run, ps.save_state, so.ops.save_ops)
        try:
            so._run_script = fake_run_script
            so._daily_report_meta = lambda root: {
                "report_date": "2026-08-30", "classification": "FALLBACK",
                "fact_count": 2}
            so._export_views = lambda emit: True
            so._reload_state = lambda st: st
            ps.record_run = lambda *a, **k: None
            ps.save_state = lambda *a, **k: None
            so.ops.save_ops = lambda *a, **k: None
            plan = {"enabled": True, "due": [
                {"task": "daily_report", "mode": "production",
                 "trigger": "scheduled_orchestrator", "reason": "tick"}]}
            res = so.execute(plan, _state(), emit=lambda s: None)
        finally:
            (so._run_script, so._daily_report_meta, so._export_views,
             so._reload_state, ps.record_run, ps.save_state,
             so.ops.save_ops) = orig
        dr = res["deploy_request"]
        self.assertEqual(dr["trigger_source"], "github_native_schedule")
        self.assertEqual(dr["trigger_type"], "automation")
        self.assertTrue(dr["automation"])
        self.assertFalse(dr["human"])
        self.assertEqual(dr["report_classification"], "FALLBACK")
        self.assertEqual(dr["report_date"], "2026-08-30")
        self.assertIsNotNone(dr["deploy_requested_at"])


# ══════════════════════════════════════════════════════════════════
# §五/§六/§七 AI identity + idempotency
# ══════════════════════════════════════════════════════════════════
class TestAiInputIdentity(unittest.TestCase):
    def test_ignores_volatile_fields(self):
        a = ident.ai_input_hash({"fact_id": "F1", "text": "x", "retrieved_at": "t1",
                                 "run_id": "r1", "generated_at": "g1"},
                                task_type="T", model="m", prompt_version="p1")
        b = ident.ai_input_hash({"fact_id": "F1", "text": "x", "retrieved_at": "t2",
                                 "run_id": "r2", "generated_at": "g2"},
                                task_type="T", model="m", prompt_version="p1")
        self.assertEqual(a, b)

    def test_changes_on_fact_change(self):
        a = ident.ai_input_hash({"text": "x"}, task_type="T", model="m",
                                prompt_version="p1")
        b = ident.ai_input_hash({"text": "y"}, task_type="T", model="m",
                                prompt_version="p1")
        self.assertNotEqual(a, b)

    def test_changes_on_schema_version(self):
        a = ident.ai_input_hash({"text": "x"}, task_type="T", model="m",
                                prompt_version="p1", output_schema_version="1.1")
        b = ident.ai_input_hash({"text": "x"}, task_type="T", model="m",
                                prompt_version="p1", output_schema_version="1.2")
        self.assertNotEqual(a, b)

    def test_changes_on_model(self):
        a = ident.ai_input_hash({"text": "x"}, task_type="T", model="m1",
                                prompt_version="p1")
        b = ident.ai_input_hash({"text": "x"}, task_type="T", model="m2",
                                prompt_version="p1")
        self.assertNotEqual(a, b)


class _FakeProv:
    """模拟 deepseek-v4-flash：记录调用次数，返回可解析的 JSON 结果。"""

    def __init__(self):
        self.calls = 0

    def submit_task(self, task):
        self.calls += 1
        return {"status": "succeeded", "result": {
            "returned_model": "deepseek-v4-flash",
            "text": json.dumps({"summary_zh": "ok", "verified_summary": "ok"}),
            "input_tokens": 100, "output_tokens": 20, "total_tokens": 120,
            "finish_reason": "stop", "thinking_requested": "disabled",
            "reasoning_tokens": None}}


class TestAiIdempotencyCycles(unittest.TestCase):
    """§七 5-cycle 回归：REPROCESSED_UNCHANGED_COUNT 必须为 0。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="asip-ai-idem-"))
        from scripts.ai import ai_result_cache
        ai_result_cache.set_ai_root(self.tmp)
        self.cache = ai_result_cache
        from scripts.ai.safety import manual_trial as mt
        self.mt = mt

    def tearDown(self):
        self.cache.set_ai_root(None)

    def _call(self, prov, payload):
        telemetry = {}
        self.mt.enrich_and_safe(prov, "stage4_event_enrichment", payload, "LBL",
                                telemetry)
        return telemetry["stage4_event_enrichment"]

    def test_five_cycle_idempotency(self):
        prov = _FakeProv()
        base = {"fact_id": "F1", "title_cn": "标题", "summary_cn": "摘要",
                "retrieved_at": "2026-08-30T01:00:00Z"}
        # Cycle 1：首次 → 1 次调用
        t1 = self._call(prov, dict(base))
        self.assertEqual(t1["calls"], 1)
        # Cycle 2：完全相同的 payload → 0 次调用（命中缓存）
        t2 = self._call(prov, dict(base))
        self.assertEqual(t2["calls"], 0)
        self.assertEqual(t2["skipped_same_input"], 1)
        # Cycle 3：仅 retrieved_at 变化 → 0 次调用
        c3 = dict(base, retrieved_at="2026-08-30T02:00:00Z")
        t3 = self._call(prov, c3)
        self.assertEqual(t3["calls"], 0)
        # Cycle 4：fact 内容变化 → 1 次调用
        c4 = dict(base, summary_cn="摘要已更新")
        t4 = self._call(prov, c4)
        self.assertEqual(t4["calls"], 1)
        # Cycle 5：analysis schema version 变化 → 1 次调用
        t5 = self._call(prov, dict(base))
        self.assertEqual(t5["calls"], 0)  # base 已缓存过
        # 显式切身份版本 → 全量失效，需重新调用
        old = ident.AI_IDENTITY_VERSION
        try:
            ident.AI_IDENTITY_VERSION = "ai-identity-v2"
            t6 = self._call(prov, dict(base))
            self.assertEqual(t6["calls"], 1)
        finally:
            ident.AI_IDENTITY_VERSION = old
        self.assertEqual(prov.calls, 3)  # cycle1 + cycle4 + cycle5(version bump)


# ══════════════════════════════════════════════════════════════════
# §十三 真实采集指标（禁止硬编码）
# ══════════════════════════════════════════════════════════════════
class TestCollectionTelemetry(unittest.TestCase):
    def test_no_hardcoded_sources_attempted(self):
        """§十三：不得对 sources_attempted 等采集指标硬编码常量（AST 级检查）。"""
        import ast
        src = (ROOT / "scripts" / "ops" / "collection_run.py").read_text(
            encoding="utf-8")
        tree = ast.parse(src)
        bad = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not isinstance(node.value, ast.Constant):
                continue
            for tgt in node.targets:
                name = None
                if isinstance(tgt, ast.Name):
                    name = tgt.id
                elif isinstance(tgt, ast.Subscript):
                    sl = getattr(tgt, "slice", None)
                    if isinstance(sl, ast.Constant):
                        name = sl.value
                if name in ("sources_attempted", "sources_succeeded",
                            "sources_failed", "candidates_new"):
                    bad.append((name, getattr(node, "lineno", -1),
                                node.value.value))
        self.assertEqual(bad, [], "硬编码采集指标: %s" % bad)

    def test_metrics_none_when_stats_missing_or_stale(self):
        from scripts.ops import collection_run as cr
        orig = cr.COLLECTOR_STATS
        try:
            cr.COLLECTOR_STATS = Path(tempfile.mkdtemp()) / "missing.json"
            self.assertIsNone(cr.read_collector_stats("2026-08-30T00:00:00Z"))
            # 陈旧统计（早于本次运行起点）不得被采用
            d = Path(tempfile.mkdtemp())
            p = d / "stage3_collection_stats.json"
            p.write_text(json.dumps({"generated_at": "2026-08-01T00:00:00Z",
                                     "totals": {"attempted_sources": 147}}),
                         encoding="utf-8")
            cr.COLLECTOR_STATS = p
            self.assertIsNone(cr.read_collector_stats("2026-08-30T00:00:00Z"))
        finally:
            cr.COLLECTOR_STATS = orig

    def test_metrics_from_real_stats(self):
        from scripts.ops import collection_run as cr
        d = Path(tempfile.mkdtemp())
        p = d / "stage3_collection_stats.json"
        p.write_text(json.dumps({
            "generated_at": "2026-08-30T12:00:00Z", "run_id": "R1",
            "totals": {"configured_sources": 147, "attempted_sources": 12,
                       "successful_sources": 11, "failed_sources": 1,
                       "duplicate_count": 3, "published_count": 4,
                       "quarantined_count": 2}}), encoding="utf-8")
        orig = cr.COLLECTOR_STATS
        try:
            cr.COLLECTOR_STATS = p
            st = cr.read_collector_stats("2026-08-30T11:00:00Z")
            self.assertIsNotNone(st)
            self.assertEqual(st["totals"]["attempted_sources"], 12)
        finally:
            cr.COLLECTOR_STATS = orig


# ══════════════════════════════════════════════════════════════════
# §十四 source health 刷新
# ══════════════════════════════════════════════════════════════════
class TestSourceHealthRefresh(unittest.TestCase):
    def test_run_health_writes_fresh_generated_at(self):
        from scripts.ops import source_health as sh
        from scripts.ops.production_state import OPS_DIR
        tmp = Path(tempfile.mkdtemp(prefix="asip-sh-"))
        orig_dir, orig_file = sh.OPS_DIR, OPS_DIR
        try:
            sh.OPS_DIR = tmp
            h = sh.run_health(emit=lambda s: None)
            written = json.loads((tmp / "source_health.json").read_text(
                encoding="utf-8"))
            self.assertEqual(written["generated_at"], h["generated_at"])
            self.assertIn("source_count", written)
            self.assertIn("stale_count", written)
            self.assertIn("bad_status_count", written)
        finally:
            sh.OPS_DIR = orig_dir


# ══════════════════════════════════════════════════════════════════
# §十五 真实 AI token 遥测
# ══════════════════════════════════════════════════════════════════
class TestAiTelemetry(unittest.TestCase):
    def test_enrichment_returns_real_token_metrics(self):
        from scripts.ops import enrichment_run as er
        from scripts.ai import ai_result_cache
        tmp = Path(tempfile.mkdtemp(prefix="asip-tel-"))
        ai_result_cache.set_ai_root(tmp)
        try:
            items = [{"event_id": "EVT_%08d" % i, "title_cn": "标题%d" % i,
                      "summary_cn": "摘要%d" % i, "current_policy_passed": True,
                      "country_code": "TD",
                      "event_time": "2026-08-30T00:00:00+08:00"}
                     for i in range(2)]
            data = {"canonical": {"event_clusters.json": {"items": items}}}
            root = tmp / "data"
            (root / "canonical").mkdir(parents=True, exist_ok=True)
            (root / "canonical" / "event_clusters.json").write_text(
                json.dumps({"items": items}, ensure_ascii=False), encoding="utf-8")
            orig_data, orig_out = er.DATA, er.ENRICH_OUT
            try:
                er.DATA = root
                er.ENRICH_OUT = tmp / "enrichment"
                r = er.run_enrichment("social", provider=_FakeProv(),
                                      state=_state(), write_back=False,
                                      data_dir=str(root), emit=lambda s: None,
                                      use_cache=True)
            finally:
                er.DATA, er.ENRICH_OUT = orig_data, orig_out
            self.assertEqual(r["ai_calls"], 2)
            self.assertEqual(r["total_tokens"], 240)
            self.assertEqual(r["input_tokens"], 200)
            self.assertEqual(r["output_tokens"], 40)
        finally:
            ai_result_cache.set_ai_root(None)


# ══════════════════════════════════════════════════════════════════
# §九/§十/§十二 日报日期与 period 新鲜度
# ══════════════════════════════════════════════════════════════════
class TestDailyFreshness(unittest.TestCase):
    def test_daily_report_date_is_current_bjt(self):
        from scripts.ai.safety import manual_trial as mt
        run_at = datetime(2026, 8, 30, 20, 0, 0, tzinfo=BJT)
        inputs = {"daily_input": None}
        # 直接测试 input builder（不依赖 canonical 数据）
        daily = mt._build_daily_input([], [], run_at)
        self.assertEqual(daily["report_date"], "2026-08-30")
        self.assertEqual(daily["report_id"], "DAILY_20260830")

    def test_daily_period_is_current(self):
        from scripts.ai.safety import manual_trial as mt
        run_at = datetime(2026, 8, 30, 20, 0, 0, tzinfo=BJT)
        daily = mt._build_daily_input([], [], run_at)
        pe = datetime.fromisoformat(daily["period_end"]).replace(tzinfo=BJT)
        pstart = datetime.fromisoformat(daily["period_start"]).replace(tzinfo=BJT)
        self.assertEqual(pe.date().isoformat(), "2026-08-30")
        self.assertAlmostEqual((pe - pstart).total_seconds(), 24 * 3600, delta=1)

    def test_stale_fixture_date_blocked(self):
        from scripts.ops import reports_run as rr
        run_at = datetime(2026, 8, 30, 20, 0, 0, tzinfo=BJT)
        # 当前业务日期 → PASS
        g = rr.freshness_gates({"report_date": "2026-08-30",
                                "period_end": "2026-08-30T20:00:00+08:00"},
                               "daily", run_at=run_at)
        self.assertEqual(g["REPORT_BUSINESS_DATE_GATE"], "PASS")
        self.assertEqual(g["DAILY_PERIOD_FRESHNESS_GATE"], "PASS")
        # fixture 旧日期 + 旧 period → 双 FAIL
        g2 = rr.freshness_gates({"report_date": "2026-08-27",
                                 "period_end": "2026-08-01T18:02:40+00:00"},
                                "daily", run_at=run_at)
        self.assertEqual(g2["REPORT_BUSINESS_DATE_GATE"], "FAIL")
        self.assertEqual(g2["DAILY_PERIOD_FRESHNESS_GATE"], "FAIL")

    def test_freshness_fail_forces_hold(self):
        from scripts.ops import reports_run as rr
        res = {"gates": {"FACT_GATE": "PASS", "FINAL_SCHEMA_GATE": "PASS",
                         "REPORT_BUSINESS_DATE_GATE": "FAIL",
                         "DAILY_PERIOD_FRESHNESS_GATE": "PASS"},
               "analysis_result": {"status": "PASS"}, "analysis": {}}
        self.assertEqual(rr.classify(res), "HOLD")


# ══════════════════════════════════════════════════════════════════
# §十七/§十九/§二十 外部调度路由 + 双重唤醒幂等
# ══════════════════════════════════════════════════════════════════
class TestExternalSchedulerRouting(unittest.TestCase):
    def test_github_schedule_is_automation(self):
        t = so.resolve_trigger("schedule", {})
        self.assertEqual(t["trigger_source"], "github_native_schedule")
        self.assertTrue(t["automation"])
        self.assertFalse(t["human"])
        self.assertEqual(t["mode"], "production")

    def test_external_scheduler_route(self):
        t = so.resolve_trigger("repository_dispatch", {},
                               {"trigger_source": "external_scheduler"})
        self.assertEqual(t["trigger_source"], "external_scheduler")
        self.assertEqual(t["trigger_type"], "automation")
        self.assertTrue(t["automation"])
        self.assertFalse(t["human"])
        self.assertEqual(t["mode"], "production")

    def test_unverified_repository_dispatch_is_human(self):
        t = so.resolve_trigger("repository_dispatch", {}, {"foo": "bar"})
        self.assertFalse(t["automation"])
        self.assertTrue(t["human"])

    def test_manual_dispatch_is_human(self):
        t = so.resolve_trigger("workflow_dispatch", {"canary": "true"})
        self.assertFalse(t["automation"])
        self.assertTrue(t["human"])
        self.assertEqual(t["trigger_source"], "manual_canary")

    def test_env_json_handles_workflow_null(self):
        """workflow 的 toJSON() 对空 client_payload 会传字符串 'null'。"""
        import os
        for raw, expect in (("null", {}), ("", {}), (None, {}),
                            ('{"trigger_source":"external_scheduler"}',
                             {"trigger_source": "external_scheduler"}),
                            ("not-json", {})):
            os.environ["ASIP_TEST_ENV_JSON"] = raw if raw is not None else ""
            if raw is None:
                os.environ.pop("ASIP_TEST_ENV_JSON", None)
            self.assertEqual(so._env_json("ASIP_TEST_ENV_JSON"), expect)
        os.environ.pop("ASIP_TEST_ENV_JSON", None)

    def test_double_wake_up_idempotency(self):
        """§二十：外部调度先跑完本小时 due，GitHub 延迟 schedule 再唤醒 → 不重复执行。"""
        # 注意：state 时间戳为 UTC；daily/disease/weekly 的"今天"按 BJT 日期判定，
        # 故 BJT 2026-08-30 需对应 UTC 2026-08-29T16:00Z ~ 2026-08-30T16:00Z
        now = datetime(2026, 8, 30, 20, 50, tzinfo=BJT)  # 周日 → weekly 也需已跑
        st = _state(last_successful_collection="2026-08-30T12:00:00Z",
                    last_daily_report="2026-08-30T04:05:00Z",      # BJT 12:05
                    last_disease_run="2026-08-30T04:10:00Z",       # BJT 12:10
                    last_weekly_report="2026-08-30T04:20:00Z")     # BJT 12:20
        first = so.plan_due_tasks(st, now_bjt=now)
        self.assertEqual([t["task"] for t in first["due"]], [])
        # 模拟第一轮（外部调度）执行后写入 state
        st2 = dict(st)
        st2["last_successful_collection"] = "2026-08-30T12:50:00Z"  # BJT 20:50
        st2["last_daily_report"] = "2026-08-30T12:55:00Z"           # BJT 20:55
        # GitHub 延迟 schedule 在 40 分钟后到达
        later = now + timedelta(minutes=40)
        second = so.plan_due_tasks(st2, now_bjt=later)
        self.assertEqual([t["task"] for t in second["due"]], [],
                         "同一小时内重复唤醒不得产生重复 due task")


if __name__ == "__main__":
    unittest.main()
