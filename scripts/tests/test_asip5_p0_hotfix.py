#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0 稳定性热修 —— 预算闸门回归测试（全部离线、零付费、零网络）。

覆盖 2026-11-03 生产事故的直接机制与修复点：
  事故链：日额度耗尽 → BudgetExceeded 被当作故障 → 付费子进程崩溃 →
          orchestrator 退出码 1 → post Job 失败 → Commit state 被跳过 →
          预算/processed_hashes 回退到旧值 → 下一轮对**同一批输入**重复付费
          （实测 12 轮 × 3 次完全相同的输入 token 2813/2322/2175）。

本测试锁定：
  A. budget_remaining() 必须同时受**单轮**与**日累计**约束；
  B. charge_attempt() 必须在**真实 HTTP 之前**判定，越界不得自增（无 41/40 虚增）；
  C. 账本不可写 → fail-closed（不花钱）且按 deferred 处理（不炸 Job）；
  D. 预算跳过**绝不**记成 AI 成功 / 已富集（不写 processed_hashes）；
  E. 中途失败后重新唤醒：不重复付费。
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops import ai_ledger                      # noqa: E402
from scripts.ai.safety import manual_trial as mt       # noqa: E402
from scripts.ops import enrichment_run as er           # noqa: E402
from scripts.ops import production_state as ps         # noqa: E402


class _BudgetBase(unittest.TestCase):
    """把共享预算状态指向临时文件，避免污染仓库 data/。"""

    ENV_KEYS = ("ASIP_AI_RUN_MAX_CALLS", "ASIP_AI_DAILY_MAX_CALLS",
                "ASIP_RUN_ID", "GITHUB_RUN_ID")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="asip5_hotfix_"))
        self._saved_path = ai_ledger.BUDGET_STATE_PATH
        self._saved_budget = dict(ai_ledger._BUDGET)
        ai_ledger.BUDGET_STATE_PATH = self.tmp / "ai_budget_state.json"
        self._env = {k: os.environ.get(k) for k in self.ENV_KEYS}
        for k in self.ENV_KEYS:
            os.environ.pop(k, None)
        os.environ["ASIP_AI_RUN_MAX_CALLS"] = "20"
        os.environ["ASIP_AI_DAILY_MAX_CALLS"] = "40"
        os.environ["ASIP_RUN_ID"] = "RUN_TEST_1"

    def tearDown(self):
        ai_ledger.BUDGET_STATE_PATH = self._saved_path
        ai_ledger._BUDGET.clear()
        ai_ledger._BUDGET.update(self._saved_budget)
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _seed(self, used=0, daily_used=37, daily_date=None, scope=None):
        doc = {"scope": scope or os.environ["ASIP_RUN_ID"], "used": used,
               "daily_date": daily_date or ai_ledger._daily_key(),
               "daily_used": daily_used, "cap": 20, "daily_cap": 40,
               "updated_at": "2026-11-03T00:00:00Z"}
        Path(ai_ledger.BUDGET_STATE_PATH).write_text(
            json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        return doc

    def _read(self):
        return json.loads(Path(ai_ledger.BUDGET_STATE_PATH).read_text(encoding="utf-8"))


class RemainingTests(_BudgetBase):
    """A：budget_remaining() 必须同时考虑单轮与日累计。"""

    def test_daily_37_of_40_remaining_is_3(self):
        """生产事故真实值：daily_used=37 / daily_cap=40 → 只剩 3 次。"""
        self._seed(used=0, daily_used=37)
        self.assertEqual(ai_ledger.budget_remaining(), 3)
        b = ai_ledger.budget_breakdown()
        self.assertEqual(b["run_remaining"], 20)
        self.assertEqual(b["daily_remaining"], 3)
        self.assertEqual(b["remaining"], 3)

    def test_daily_40_of_40_remaining_is_0(self):
        self._seed(used=0, daily_used=40)
        self.assertEqual(ai_ledger.budget_remaining(), 0)

    def test_daily_over_cap_remaining_is_0_not_negative(self):
        self._seed(used=0, daily_used=42)
        self.assertEqual(ai_ledger.budget_remaining(), 0)

    def test_run_quota_exhausted_remaining_is_0(self):
        self._seed(used=20, daily_used=10)
        self.assertEqual(ai_ledger.budget_remaining(), 0)

    def test_remaining_is_min_of_run_and_daily(self):
        # 单轮剩 1、日剩 10 → 1
        self._seed(used=19, daily_used=30)
        self.assertEqual(ai_ledger.budget_remaining(), 1)
        # 单轮剩 10、日剩 1 → 1
        self._seed(used=10, daily_used=39)
        self.assertEqual(ai_ledger.budget_remaining(), 1)

    def test_new_day_resets_daily_quota(self):
        self._seed(used=0, daily_used=40, daily_date="2026-01-01")
        self.assertEqual(ai_ledger.budget_remaining(), 20)

    def test_other_scope_resets_run_quota_only(self):
        self._seed(used=20, daily_used=30, scope="SOME_OTHER_RUN")
        b = ai_ledger.budget_breakdown()
        self.assertEqual(b["used"], 0)
        self.assertEqual(b["remaining"], 10)


class ChargeGateTests(_BudgetBase):
    """B：charge 必须在真实请求前判定，越界不得自增（无虚增记录）。"""

    def test_charge_blocked_before_increment_when_daily_exhausted(self):
        self._seed(used=0, daily_used=40)
        with self.assertRaises(ai_ledger.BudgetExceeded) as cm:
            ai_ledger.charge_attempt("daily_assessment")
        self.assertTrue(getattr(cm.exception, "deferred", False))
        self.assertEqual(cm.exception.deferred_reason, "deferred_budget_exhausted")
        doc = self._read()
        # 关键：不得出现 41/40、42/40 之类的"没花钱却记了一笔"
        self.assertEqual(doc["daily_used"], 40, "越界不得自增")
        self.assertEqual(doc.get("used", 0), 0)

    def test_charge_stops_exactly_at_daily_cap(self):
        """daily 37/40：连续 3 次成功，第 4 次被拦，且计数停在 40。"""
        self._seed(used=0, daily_used=37)
        for _ in range(3):
            ai_ledger.charge_attempt("stage4_event_enrichment")
        self.assertEqual(ai_ledger.budget_remaining(), 0)
        with self.assertRaises(ai_ledger.BudgetExceeded):
            ai_ledger.charge_attempt("stage4_event_enrichment")
        doc = self._read()
        self.assertEqual(doc["daily_used"], 40)
        self.assertEqual(doc["used"], 3)

    def test_charge_stops_exactly_at_run_cap(self):
        os.environ["ASIP_AI_RUN_MAX_CALLS"] = "2"
        self._seed(used=0, daily_used=0)
        ai_ledger.charge_attempt("a")
        ai_ledger.charge_attempt("b")
        with self.assertRaises(ai_ledger.BudgetExceeded):
            ai_ledger.charge_attempt("c")
        self.assertEqual(self._read()["used"], 2)

    def test_zero_run_cap_blocks_everything(self):
        os.environ["ASIP_AI_RUN_MAX_CALLS"] = "0"
        self._seed(used=0, daily_used=0)
        self.assertEqual(ai_ledger.budget_remaining(), 0)
        with self.assertRaises(ai_ledger.BudgetExceeded):
            ai_ledger.charge_attempt("any")


class LedgerFailClosedTests(_BudgetBase):
    """C：账本不可读/不可写 → fail-closed（不花钱），且按 deferred 处理。"""

    def test_unreadable_ledger_blocks_spending(self):
        p = Path(ai_ledger.BUDGET_STATE_PATH)
        p.write_text("{not-json", encoding="utf-8")
        with self.assertRaises(ai_ledger.BudgetStateUnavailable) as cm:
            ai_ledger.budget_remaining()
        self.assertTrue(getattr(cm.exception, "deferred", False))
        self.assertEqual(cm.exception.deferred_reason,
                         "deferred_budget_ledger_unavailable")
        with self.assertRaises(ai_ledger.BudgetStateUnavailable):
            ai_ledger.charge_attempt("social_ai")

    def test_unwritable_ledger_blocks_spending(self):
        blocker = self.tmp / "blocker"
        blocker.write_text("x", encoding="utf-8")
        # 父路径是文件 → 无法创建目录/写文件
        ai_ledger.BUDGET_STATE_PATH = blocker / "sub" / "ai_budget_state.json"
        with self.assertRaises(ai_ledger.BudgetStateUnavailable):
            ai_ledger.charge_attempt("social_ai")


class DeferredRecordTests(_BudgetBase):
    """D：预算跳过绝不记成成功/已富集。"""

    def test_enrich_and_safe_returns_deferred_without_counting_call(self):
        class _Prov:
            def submit_task(self, task):
                return {"task_id": task["task_id"],
                        "status": "deferred_budget_exhausted",
                        "deferred": True,
                        "deferred_reason": "deferred_budget_exhausted",
                        "result": {"input_tokens": None, "output_tokens": None}}

        telemetry = {}
        rec = mt.enrich_and_safe(_Prov(), "stage4_event_enrichment",
                                 {"event_id": "EVT_1", "title_cn": "x"}, "S1",
                                 telemetry, use_cache=False)
        self.assertTrue(rec.get("deferred"))
        self.assertEqual(rec["status"], "deferred_budget")
        self.assertNotEqual(rec["status"], "ok")
        self.assertEqual(telemetry["stage4_event_enrichment"]["calls"], 0,
                         "deferred 不得计入 calls（未付费）")

    def test_run_enrichment_breaks_on_deferred_and_never_marks_processed(self):
        data = self.tmp / "data"
        (data / "canonical").mkdir(parents=True)
        (data / "canonical" / "event_clusters.json").write_text(json.dumps({
            "items": [{"event_id": "EVT_A", "current_policy_passed": True,
                       "title_cn": "t", "event_time": "2026-11-03T00:00:00Z"},
                      {"event_id": "EVT_B", "current_policy_passed": True,
                       "title_cn": "t2", "event_time": "2026-11-03T00:00:00Z"}]}),
            encoding="utf-8")

        class _Prov:
            calls = 0

            def submit_task(self, task):
                _Prov.calls += 1
                return {"task_id": task["task_id"],
                        "status": "deferred_budget_exhausted", "deferred": True,
                        "deferred_reason": "deferred_budget_exhausted",
                        "result": {"input_tokens": None, "output_tokens": None}}

        saved = (er.DATA, er.ENRICH_OUT, ps.OPS_DIR)
        er.DATA = data
        er.ENRICH_OUT = self.tmp / "ops" / "enrichment"
        ps.OPS_DIR = self.tmp / "ops"
        try:
            state = {"processed_hashes": {}, "failed_held_records": [],
                     "ai_token_usage": {}}
            out = er.run_enrichment("social", provider=_Prov(), state=state,
                                    emit=lambda s: None, write_back=False,
                                    use_cache=False, data_dir=data)
        finally:
            er.DATA, er.ENRICH_OUT, ps.OPS_DIR = saved

        self.assertEqual(out["deferred_budget_exhausted"], 1)
        self.assertEqual(out["processed"], 0)
        self.assertEqual(out["ai_calls"], 0)
        self.assertEqual(out["held"], 0)
        self.assertEqual(_Prov.calls, 1, "命中 deferred 后必须停止，不得继续消费")
        self.assertEqual(state["processed_hashes"].get("social_enrichment", {}), {},
                         "deferred 绝不能写入 processed_hashes（否则被当成已富集）")


class NoDuplicateChargeTests(_BudgetBase):
    """E：失败/重试后不重复付费 —— 计数持久且不回退。"""

    def test_rejected_attempt_does_not_persist_increment(self):
        """被拦下的尝试不落盘 → 账号既不花也不虚增。"""
        self._seed(used=0, daily_used=40)
        before = self._read()
        for _ in range(3):
            with self.assertRaises(ai_ledger.BudgetExceeded):
                ai_ledger.charge_attempt("social_ai")
        after = self._read()
        self.assertEqual(before["daily_used"], after["daily_used"])
        self.assertEqual(before["used"], after["used"])

    def test_spend_survives_new_process_scope(self):
        """同一日内的新轮次（新 run_id）不得重置日累计（否则重复付费）。"""
        self._seed(used=0, daily_used=37)
        ai_ledger.charge_attempt("stage4_event_enrichment")
        os.environ["ASIP_RUN_ID"] = "RUN_TEST_2"      # 模拟重新唤醒/新进程
        doc = self._read()
        self.assertEqual(doc["daily_used"], 38, "已花的日额度必须跨轮保留")
        self.assertEqual(ai_ledger.budget_remaining(), 2)
        self.assertEqual(ai_ledger.budget_breakdown()["used"], 0,
                         "单轮计数按新 run 归零，但日累计不动")


class CommitBudgetOnlyTests(unittest.TestCase):
    """失败路径兜底提交入口存在且可被 CLI 识别。"""

    def test_cli_accepts_budget_only_flag(self):
        from scripts.ops import commit_state
        self.assertTrue(hasattr(commit_state, "commit_budget_only"))
        self.assertIn("data/runtime/ops/ai_budget_state.json",
                      commit_state.BUDGET_PATHS)
        src = Path(commit_state.__file__).read_text(encoding="utf-8")
        self.assertIn("--budget-only", src)


class OrchestratorBudgetGateTests(_BudgetBase):
    """编排器侧的付费闸门必须读同一个"有效余额"口径。"""

    def test_orchestrator_gate_false_when_daily_exhausted(self):
        from scripts.ops import schedule_orchestrator as so
        self._seed(used=0, daily_used=40)
        self.assertFalse(so._ai_budget_available(),
                         "日额度耗尽时编排器必须判定为无余额")

    def test_orchestrator_gate_true_when_remaining(self):
        from scripts.ops import schedule_orchestrator as so
        self._seed(used=0, daily_used=37)
        self.assertTrue(so._ai_budget_available())

    def test_orchestrator_gate_false_when_ledger_unreadable(self):
        from scripts.ops import schedule_orchestrator as so
        Path(ai_ledger.BUDGET_STATE_PATH).write_text("{bad", encoding="utf-8")
        self.assertFalse(so._ai_budget_available(), "账本不可验证 → fail-closed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
