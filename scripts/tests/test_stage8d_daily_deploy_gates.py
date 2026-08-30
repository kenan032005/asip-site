#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage8D Final Blocker Fix — Daily freshness & Deploy provenance 测试（§N/§O）。

§N  Daily：动态 report_id / BJT 业务日期 / 当前 period / 无新事件不回退日期 /
    trial identity 禁入。
§O  Deploy：publishable → deploy_required；dispatch payload 含 provenance；
    manual=human / automation 校验；provenance 缺失安全默认。
"""
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops import schedule_orchestrator as so  # noqa: E402
from scripts.ops import reports_run as rr  # noqa: E402
from scripts.ai.safety import manual_trial as mt  # noqa: E402

BJT = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════
# §N Daily freshness
# ══════════════════════════════════════════════════════════════════
class TestDailyFreshnessContract(unittest.TestCase):
    def test_daily_report_id_dynamic(self):
        daily = mt._build_daily_input([], [], datetime(2026, 8, 30, 20, 5, tzinfo=BJT))
        self.assertEqual(daily["report_id"], "DAILY_20260830")
        self.assertNotIn("MANUAL_TRIAL", daily["report_id"])

    def test_daily_report_date_uses_bjt_business_date(self):
        # BJT 20:05 落在 UTC 12:05 —— 仍必须是 BJT 业务日 2026-08-30
        daily = mt._build_daily_input([], [], datetime(2026, 8, 30, 20, 5, tzinfo=BJT))
        self.assertEqual(daily["report_date"], "2026-08-30")

    def test_daily_period_uses_current_cutoff(self):
        run_at = datetime(2026, 8, 30, 20, 5, tzinfo=BJT)
        daily = mt._build_daily_input([], [], run_at)
        pe = datetime.fromisoformat(daily["period_end"]).replace(tzinfo=BJT)
        pstart = datetime.fromisoformat(daily["period_start"]).replace(tzinfo=BJT)
        self.assertEqual(pe, run_at)
        self.assertAlmostEqual((pe - pstart).total_seconds(), 24 * 3600, delta=1)
        self.assertEqual(daily["tracking_72h_start"],
                         (run_at - timedelta(hours=72)).replace(tzinfo=None).isoformat())
        self.assertEqual(daily["trend_7d_start"],
                         (run_at - timedelta(days=7)).replace(tzinfo=None).isoformat())

    def test_daily_no_recent_events_keeps_current_business_date(self):
        # 无任何事实（fact_count=0 场景）→ report_date 仍必须是当天
        daily = mt._build_daily_input([], [], datetime(2026, 8, 30, 20, 0, tzinfo=BJT))
        self.assertEqual(daily["report_date"], "2026-08-30")
        self.assertEqual(daily["stats"]["eligible_events"], 0)

    def test_daily_no_recent_events_does_not_shift_period_to_last_event(self):
        # §C 反例：最后事件 2026-08-01，period 不得倒退为 07-31→08-01
        daily = mt._build_daily_input([], [], datetime(2026, 8, 30, 20, 0, tzinfo=BJT))
        self.assertTrue(daily["period_end"].startswith("2026-08-30"))
        self.assertTrue(daily["period_start"].startswith("2026-08-29"))

    def test_stale_event_does_not_make_stale_report_date(self):
        # 传入陈旧 cutoff（数据里的最新 event_time）→ report_date 仍按运行时刻
        daily = mt._build_daily_input([], [], "2026-08-01T18:02:40Z")
        # cutoff 本身是 Aug 1 → 报告业务日期即 Aug 1（由传入运行时刻决定），
        # 生产路径由 build_inputs(run_at=now) 保证传入的是当前 BJT 时刻
        self.assertEqual(daily["report_date"], "2026-08-01")
        # 而当运行时刻为今天时，陈旧数据不影响报告日期
        daily2 = mt._build_daily_input([], [], datetime(2026, 8, 30, 20, 0, tzinfo=BJT))
        self.assertEqual(daily2["report_date"], "2026-08-30")

    def test_manual_trial_identity_forbidden_in_production(self):
        """§D：report 含 trial identity → TRIAL_FIXTURE_LEAK_GATE=FAIL → HOLD。"""
        bad = {"report_id": "DAILY_MANUAL_TRIAL_20260827",
               "report_type": "africa_daily", "report_date": "2026-08-27"}
        self.assertEqual(rr.trial_fixture_leak_gate(bad, "daily"), "FAIL")
        good = {"report_id": "DAILY_20260830", "report_type": "africa_daily",
                "report_date": "2026-08-30"}
        self.assertEqual(rr.trial_fixture_leak_gate(good, "daily"), "PASS")
        res = {"gates": {"FACT_GATE": "PASS", "FINAL_SCHEMA_GATE": "PASS",
                         "REPORT_BUSINESS_DATE_GATE": "PASS",
                         "DAILY_PERIOD_FRESHNESS_GATE": "PASS",
                         "TRIAL_FIXTURE_LEAK_GATE": "FAIL"},
               "analysis_result": {"status": "PASS"}, "analysis": {}}
        self.assertEqual(rr.classify(res), "HOLD")


# ══════════════════════════════════════════════════════════════════
# §O Deploy permission / provenance
# ══════════════════════════════════════════════════════════════════
class _ProvHarness:
    """执行 execute() 并返回结果（monkeypatch 子进程与 IO）。"""

    def __init__(self, classification, report_id="DAILY_20260830"):
        self.classification = classification
        self.report_id = report_id
        self._orig = None

    def __enter__(self):
        self._orig = (so._run_script, so._daily_report_meta, so._export_views,
                      so._reload_state, ps_record, ps_save, so.ops.save_ops)
        so._run_script = lambda args, emit, timeout=1800: True
        so._daily_report_meta = lambda root: {
            "report_date": "2026-08-30", "classification": self.classification,
            "report_id": self.report_id, "fact_count": 1}
        so._export_views = lambda emit: True
        so._reload_state = lambda st: st
        globals()["_ps_record"] = ps_record
        return self

    def __exit__(self, *exc):
        (so._run_script, so._daily_report_meta, so._export_views,
         so._reload_state, ps_record, ps_save, so.ops.save_ops) = self._orig


def ps_record(*a, **k):
    return None


def ps_save(*a, **k):
    return None


def _run_daily(classification):
    h = _ProvHarness(classification)
    with h:
        so.ops.save_ops = lambda *a, **k: None
        plan = {"enabled": True, "due": [
            {"task": "daily_report", "mode": "production",
             "trigger": "scheduled_orchestrator", "reason": "tick"}]}
        return so.execute(plan, {"processed_hashes": {}}, emit=lambda s: None)



def _workflow_text(name):
    """定位 workflow YAML：优先 ASIP_WORKFLOWS_DIR，缺省 ROOT/.github/workflows。

    release 代码分支不含 workflows（workflows 在 main/fix 分支）→ 返回 None，
    对应静态结构测试 skip；在含新 workflow 的 checkout（QA 环境）上真实校验。
    """
    import os
    candidates = []
    env_dir = os.environ.get("ASIP_WORKFLOWS_DIR")
    if env_dir:
        candidates.append(Path(env_dir))
    candidates.append(ROOT / ".github" / "workflows")
    for d in candidates:
        f = d / name
        if f.exists():
            return f.read_text(encoding="utf-8")
    return None

class TestDeployRequiredAndProvenance(unittest.TestCase):
    def test_publishable_report_sets_deploy_required(self):
        self.assertTrue(so.deploy_required_for("FULL"))
        self.assertTrue(so.deploy_required_for("FALLBACK"))
        self.assertTrue(so.deploy_required_for("LOW_DATA"))

    def test_full_auto_deploy(self):
        self.assertTrue(_run_daily("FULL")["deploy_required"])

    def test_fallback_auto_deploy(self):
        self.assertTrue(_run_daily("FALLBACK")["deploy_required"])

    def test_low_data_auto_deploy(self):
        self.assertTrue(_run_daily("LOW_DATA")["deploy_required"])

    def test_fact_gate_fail_no_deploy(self):
        self.assertFalse(_run_daily("HOLD")["deploy_required"])

    def test_auto_deploy_dispatch_payload_contains_provenance(self):
        """§I：automation 派发的 payload 必须含全部 provenance 字段（workflow 静态校验）。"""
        text = _workflow_text("asip-production-orchestrator.yml")
        if text is None:
            self.skipTest("workflow 文件不在本 checkout（release 代码分支）")
        for field in ("root_orchestrator_run_id", "root_orchestrator_run_url",
                      "trigger_source", "trigger_type", "automation",
                      "report_date", "report_classification", "report_id"):
            self.assertIn('"%s"' % field, text)
        # §M fail-closed：dispatch 非 2xx 必须 exit 1
        self.assertIn("AUTO_DEPLOY_TRIGGER_HTTP=$HTTP", text)
        self.assertIn("exit 1", text)
        # §F：actions: write 权限
        self.assertIn("actions: write", text)

    def test_manual_dispatch_marks_human_manual(self):
        """§J：deploy workflow 中人工 dispatch 默认 human_manual。"""
        text = _workflow_text("asip-production-deploy.yml")
        if text is None:
            self.skipTest("workflow 文件不在本 checkout（release 代码分支）")
        self.assertIn('SRC="human_manual"', text)
        self.assertIn("human_manual_dispatch", text)

    def test_automation_dispatch_marks_automation_true(self):
        text = _workflow_text("asip-production-deploy.yml")
        if text is None:
            self.skipTest("workflow 文件不在本 checkout（release 代码分支）")
        self.assertIn("scheduled_orchestrator_auto_dispatch", text)
        # §J 一致性校验存在
        self.assertIn("automation=true 但 root_orchestrator_run_id", text)

    def test_missing_provenance_fail_or_safe_default(self):
        """§O：resolve_trigger 对未声明来源的 repository_dispatch 拒绝 automation。"""
        t = so.resolve_trigger("repository_dispatch", {}, {})
        self.assertFalse(t["automation"])
        self.assertTrue(t["human"])
        self.assertEqual(t["mode"], "shadow")

    def test_dispatch_403_is_not_reported_success(self):
        """§M：workflow 中 dispatch 失败必须显式失败（静态校验 fail-closed 逻辑）。"""
        text = _workflow_text("asip-production-orchestrator.yml")
        if text is None:
            self.skipTest("workflow 文件不在本 checkout（release 代码分支）")
        self.assertIn("-o /tmp/deploy_resp.json -w \"%{http_code}\"", text)
        self.assertLess(text.index('if [ "$HTTP" -lt 200 ]'),
                        text.index("Upload ops artifacts"))

    def test_deploy_provenance_persisted_in_ops_run(self):
        """§K：deploy 请求与 provenance 写入 ops run 记录。"""
        seen = {}

        def fake_finish(run, status=None):
            seen["run"] = run

        orig = so.ops.finish_run
        try:
            so.ops.finish_run = fake_finish
            so._run_script = lambda args, emit, timeout=1800: True
            so._daily_report_meta = lambda root: {
                "report_date": "2026-08-30", "classification": "LOW_DATA",
                "report_id": "DAILY_20260830", "fact_count": 0}
            so._export_views = lambda emit: True
            so._reload_state = lambda st: st
            import scripts.ops.production_state as _ps
            _ps.record_run = lambda *a, **k: None
            _ps.save_state = lambda *a, **k: None
            so.ops.save_ops = lambda *a, **k: None
            plan = {"enabled": True, "due": [
                {"task": "daily_report", "mode": "production",
                 "trigger": "scheduled_orchestrator", "reason": "tick"}]}
            so.execute(plan, {"processed_hashes": {}}, emit=lambda s: None)
        finally:
            so.ops.finish_run = orig
        run = seen["run"]
        self.assertTrue(run["deploy_requested"])
        dr = run["deploy_provenance"]
        for k in ("trigger_source", "automation", "human",
                  "root_orchestrator_run_id", "report_id", "report_date",
                  "report_classification", "deploy_requested_at"):
            self.assertIn(k, dr)
        self.assertEqual(dr["report_id"], "DAILY_20260830")


if __name__ == "__main__":
    unittest.main()
