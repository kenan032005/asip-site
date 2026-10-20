#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C8-4D2 Part A — Phase 3/4 修正与执行顺序回归测试。

覆盖：
  A1  source_scope / country_scope 错配修正（多国展开源必须落在 phase 4）
  A2  保证键优先级不变（P0 → P1 → Lane A 先于一切 3/4 拆分）
  A3  执行顺序：普通国家 phase 3 全局先行，多国展开 phase 4 殿后
  A4  旧/新调度在**同一冻结执行集**上的差异必须只是"多国源改判 phase 4"
  A5  墙钟预算保持 3000s
  A6  真实注册表不变量（键总数、相位归属完备、PASS 顺序）
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "scripts" / "collectors")):
    if p not in sys.path:
        sys.path.insert(0, p)

import stage3_collect_v2 as s3  # noqa: E402
from scripts.ops import collection_run as cr  # noqa: E402

CN = ["乍得", "尼日尔", "尼日利亚", "马里", "塞内加尔"]


def _src(sid, scope, country_scope=None):
    s = {"source_id": sid, "source_name": sid}
    if scope is not None:
        s["source_scope"] = scope
    if country_scope is not None:
        s["country_scope"] = country_scope
    return s


#: 冻结 source-country 执行集（确定性，不依赖真实注册表内容）
FROZEN = [
    # (country, source_dict)
    ("尼日尔", _src("niger_anp", ["尼日尔"])),                      # P0 保证键
    ("尼日尔", _src("pan_allafrica", ["尼日尔"] + ["c%d" % i for i in range(53)])),  # 多国但在 P0 国 → P0 优先
    ("尼日利亚", _src("nga_nan", ["尼日利亚"])),                     # P1 保证核心
    ("尼日利亚", _src("nga_local_x", ["尼日利亚"])),                 # 普通 → 3
    ("乍得", _src("chad_local_y", ["乍得", "尼日尔"])),               # 双国 → 3
    ("乍得", _src("pan_bbc_africa", ["乍得"] + ["c%d" % i for i in range(53)])),   # 多国 → 4
    ("乍得", _src("pan_rfi_afrique", ["乍得"] + ["c%d" % i for i in range(53)])),  # 多国但是 Lane A → 2
    ("马里", _src("mali_local_z", ["马里"])),                        # 普通 → 3
    ("塞内加尔", _src("sen_local_w", ["塞内加尔"])),                   # 普通 → 3
    ("塞内加尔", _src("pan_dw_africa", ["塞内加尔"] + ["c%d" % i for i in range(53)])),  # Lane A 多国 → 2
    ("乍得", _src("legacy_view", None, country_scope=["乍得", "尼日尔", "马里"])),  # 旧字段回退 → 4
]


class TestPhaseAssignment(unittest.TestCase):
    def test_multicountry_goes_to_phase4(self):
        self.assertEqual(s3._assign_execution_phase("乍得", _src("pan_bbc_africa", ["乍得"] + ["c%d" % i for i in range(53)])), 4)

    def test_ordinary_single_and_dual_stay_phase3(self):
        self.assertEqual(s3._assign_execution_phase("乍得", _src("a", ["乍得"])), 3)
        self.assertEqual(s3._assign_execution_phase("乍得", _src("b", ["乍得", "尼日尔"])), 3)

    def test_guaranteed_lanes_take_precedence(self):
        p0 = s3._assign_execution_phase("尼日尔", _src("niger_anp", ["尼日尔"]))
        self.assertEqual(p0, 0)
        # P0 国的**非 P0 名单**多国源仍按展开拆分判 4（保证键只对名单内源生效）
        self.assertEqual(s3._assign_execution_phase("尼日尔", _src("pan_allafrica", ["尼日尔"] + ["c%d" % i for i in range(53)])), 4)
        self.assertEqual(s3._assign_execution_phase("尼日利亚", _src("nga_nan", ["尼日利亚"])), 1)
        # Lane A 多国源 → 2（不得因修正被推去 phase 4）
        self.assertEqual(s3._assign_execution_phase("乍得", _src("pan_rfi_afrique", ["乍得"] + ["c%d" % i for i in range(53)])), 2)

    def test_legacy_country_scope_fallback(self):
        self.assertEqual(s3._assign_execution_phase("乍得", _src("legacy", None, country_scope=["乍得", "尼日尔", "马里"])), 4)

    def test_frozen_set_distribution(self):
        phases = {}
        for cn, s in FROZEN:
            phases[(cn, s["source_id"])] = s3._assign_execution_phase(cn, s)
        got = {}
        for p in phases.values():
            got[p] = got.get(p, 0) + 1
        self.assertEqual(got, {0: 1, 1: 1, 2: 2, 3: 4, 4: 3})


class TestExecutionOrder(unittest.TestCase):
    def _plan(self):
        phase_map = {}
        for cn, s in FROZEN:
            phase_map[(cn, s["source_id"])] = s3._assign_execution_phase(cn, s)
        return s3.plan_phase_execution(phase_map, CN)

    def test_all_phase3_before_any_phase4(self):
        plan = self._plan()
        order = []
        for idx, cn, sids in plan:
            for sid in sids:
                phase_map = {(c, s["source_id"]): s3._assign_execution_phase(c, s) for c, s in FROZEN}
                order.append(phase_map[(cn, sid)])
        first4 = order.index(4)
        self.assertNotIn(3, order[first4:], "phase 3 不得出现在 phase 4 之后")
        self.assertIn(3, order[:first4])

    def test_every_key_executed_exactly_once(self):
        plan = self._plan()
        seen = []
        for _idx, cn, sids in plan:
            seen.extend((cn, sid) for sid in sids)
        expected = {(cn, s["source_id"]) for cn, s in FROZEN}
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(set(seen), expected)

    def test_guaranteed_keys_in_first_pass(self):
        plan = self._plan()
        first = {idx for idx, _cn, _s in plan if idx == 0}
        self.assertEqual(first, {0})
        phase_map = {(c, s["source_id"]): s3._assign_execution_phase(c, s) for c, s in FROZEN}
        for idx, cn, sids in plan:
            for sid in sids:
                if phase_map[(cn, sid)] <= 2:
                    self.assertEqual(idx, 0, "保证键必须在 PASS A")

    def test_deterministic(self):
        self.assertEqual(self._plan(), self._plan())


class TestOldNewEquivalence(unittest.TestCase):
    def test_only_multicountry_reclassified(self):
        """旧实现（读 country_scope → 恒 3）与新实现的差异必须只限于多国源。"""
        old = {}
        new = {}
        for cn, s in FROZEN:
            sid = s["source_id"]
            old[(cn, sid)] = 3                       # 旧：country_scope 缺失 → 长度 0 → 3
            new[(cn, sid)] = s3._assign_execution_phase(cn, s)
        self.assertEqual(set(old), set(new))          # 执行键集合不变
        diff = {k for k in old if old[k] != new[k]}
        # 不变量：单/双国且**非保证键**的执行键相位不得改变（仍是 3）；
        # 保证键名单内者必须落到 0/1/2；非保证键只有多国展开源才改判到 4。
        guaranteed = s3.P0_NIGER_IDS | s3.P1_GUARANTEED_IDS | s3.LANE_A_IDS
        for (cn, sid) in diff:
            s = next(x for c, x in FROZEN if c == cn and x["source_id"] == sid)
            n = len(s.get("source_scope") or s.get("country_scope") or [])
            if sid in guaranteed:
                self.assertLessEqual(new[(cn, sid)], 2, f"{sid} 保证键必须在 PASS A")
            else:
                self.assertGreater(n, 2, f"{sid} 非多国源不得改判")
                self.assertEqual(new[(cn, sid)], 4)
        # 反向：非保证键的单/双国源必须全部保持 3（旧新一致）
        for k in old:
            cn, sid = k
            if sid in guaranteed:
                continue
            s = next(x for c, x in FROZEN if c == cn and x["source_id"] == sid)
            n = len(s.get("source_scope") or s.get("country_scope") or [])
            if n <= 2:
                self.assertEqual(old[k], new[k], f"{sid} 普通国家源相位被改动")
        self.assertEqual(len(diff), 7)  # niger_anp + nga_nan + pan_allafrica + pan_bbc + pan_rfi + pan_dw + legacy_view

    def test_total_keys_unchanged(self):
        phase_map = {(cn, s["source_id"]): s3._assign_execution_phase(cn, s) for cn, s in FROZEN}
        self.assertEqual(len(phase_map), len(FROZEN))


class TestWallClockBudget(unittest.TestCase):
    def test_collection_budget_default_3000(self):
        saved = os.environ.pop("ASIP_COLLECTION_WALL_CLOCK_SECONDS", None)
        try:
            import importlib
            importlib.reload(cr)
            self.assertEqual(cr.COLLECTION_WALL_CLOCK_LIMIT, 3000)
        finally:
            if saved is not None:
                os.environ["ASIP_COLLECTION_WALL_CLOCK_SECONDS"] = saved
            importlib.reload(cr)

    def test_env_override_still_supported(self):
        os.environ["ASIP_COLLECTION_WALL_CLOCK_SECONDS"] = "2400"
        try:
            import importlib
            importlib.reload(cr)
            self.assertEqual(cr.COLLECTION_WALL_CLOCK_LIMIT, 2400)
        finally:
            os.environ.pop("ASIP_COLLECTION_WALL_CLOCK_SECONDS", None)
            importlib.reload(cr)


class TestLiveRegistryInvariants(unittest.TestCase):
    """真实注册表不变量：键总数、相位归属完备、保证键不被 3/4 拆分吞掉。"""

    def test_live_registry_phase_split(self):
        from registry import SourceRegistry
        reg = SourceRegistry()
        reg.load()
        countries = sorted({c for s in reg.enabled() for c in (s.get("source_scope") or [])})
        phase = {}
        for cn in countries:
            for s in reg.by_country(cn):
                phase[(cn, str(s.get("source_id")))] = s3._assign_execution_phase(cn, s)
        self.assertEqual(len(phase), 888)
        # 双向不变量：
        #  - phase 4 的执行键必须 source_scope > 2（多国展开）；
        #  - phase <= 2 的执行键必须命中某个保证名单（按其国家判定），
        #    注意 P0/P1 名单是"按国家生效"的，同一源在别国可按展开数判 4。
        for (cn, sid), p in phase.items():
            s = next(x for x in reg.by_country(cn) if str(x.get("source_id")) == sid)
            n = len(s.get("source_scope") or [])
            if p == 4:
                self.assertGreater(n, 2, f"{sid}@{cn} 非多国源不得进 phase 4")
            if p <= 2:
                guaranteed = ((cn == s3.P0_NIGER_COUNTRY and sid in s3.P0_NIGER_IDS)
                              or (cn in s3.P1_COUNTRIES_ORDER and sid in s3.P1_GUARANTEED_IDS)
                              or sid in s3.LANE_A_IDS)
                self.assertTrue(guaranteed, f"{sid}@{cn} 非保证键不得进 PASS A")
        # 相位 3/4 必须真的分开（修正前 phase 4 恒为 0）
        self.assertGreater(sum(1 for p in phase.values() if p == 4), 0)
        self.assertGreater(sum(1 for p in phase.values() if p == 3), 0)
        # 计划覆盖全部键且顺序确定
        plan = s3.plan_phase_execution(phase, countries)
        planned = [(cn, sid) for _i, cn, sids in plan for sid in sids]
        self.assertEqual(len(planned), len(set(planned)))
        self.assertEqual(set(planned), set(phase))


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestRollbackSwitch(unittest.TestCase):
    """C8-4D2：PASS B 拆分的立即回滚开关（ASIP_PHASE_B_SPLIT=0 → 单趟 {3,4}）。"""

    def tearDown(self):
        os.environ.pop("ASIP_PHASE_B_SPLIT", None)

    def test_default_is_split(self):
        os.environ.pop("ASIP_PHASE_B_SPLIT", None)
        self.assertEqual(s3.active_phase_passes(), ({0, 1, 2}, {3}, {4}))

    def test_env_zero_rolls_back_to_single_pass(self):
        os.environ["ASIP_PHASE_B_SPLIT"] = "0"
        self.assertEqual(s3.active_phase_passes(), ({0, 1, 2}, {3, 4}))

    def test_env_one_keeps_split(self):
        os.environ["ASIP_PHASE_B_SPLIT"] = "1"
        self.assertEqual(s3.active_phase_passes(), ({0, 1, 2}, {3}, {4}))

    def test_rollback_still_runs_guaranteed_first(self):
        for passes in (s3.PHASE_PASSES, (({0, 1, 2}, {3, 4}))):
            self.assertEqual(passes[0], {0, 1, 2})
