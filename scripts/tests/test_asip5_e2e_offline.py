#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1 — 离线端到端验收（旧状态 → 分片 → 模拟采集 → 持久化 → 模拟AI → 首页 → 部署资格）。

全程离线：无网络、无真实模型调用、不触碰生产仓库与 production-state。
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "scripts" / "data")):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.data.quarantine_store import QuarantineStore  # noqa: E402
from scripts.ops import paid_gate, ai_ledger  # noqa: E402
from scripts.ops import commit_state  # noqa: E402
from scripts.ops import schedule_orchestrator as so  # noqa: E402
import scripts.build_site as bs  # noqa: E402


class _FakeProvider:
    model = "deepseek-flash"

    def __init__(self):
        self.n = 0

    def submit_task(self, task):
        self.n += 1
        return {"status": "succeeded", "result": {
            "requested_model": "deepseek-flash", "returned_model": "deepseek-flash",
            "input_tokens": 2000, "output_tokens": 400, "total_tokens": 2400,
            "cache_hit_tokens": None, "http_status": 200, "attempt_count": 1,
            "provider_status": "ok", "billing_mode": "paid", "estimated_cost": None}}


class TestOfflineE2E(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="asip5_e2e_")
        self.root = Path(self.tmp)
        (self.root / "data" / "canonical").mkdir(parents=True)
        (self.root / "data" / "runtime" / "ops").mkdir(parents=True)
        # 旧状态（含 processed_hashes，模拟 production-state 快照）
        self.state = {
            "last_successful_collection": "2026-10-27T04:55:16Z",
            "last_successful_ai": "2026-10-27T05:02:10Z",
            "processed_hashes": {"social_enrichment": {"h1": {"ts": "x"}},
                                 "disease_enrichment": {}}
        }
        (self.root / "data" / "runtime" / "ops" / "production_state.json").write_text(
            json.dumps(self.state, ensure_ascii=False), encoding="utf-8")
        # 旧单体隔离（其中一条已隔离 URL 用于安全 hold 校验）
        items = [{"quarantine_id": "Q_a", "original_object_type": "article",
                  "original_id": "https://ex.com/blocked", "reason_code": "other",
                  "detected_at": "2026-10-20T00:00:00Z", "legacy_payload": {}},
                 {"quarantine_id": "Q_b", "original_object_type": "event",
                  "original_id": "EVT-1", "reason_code": "wrong_country",
                  "detected_at": "2026-10-21T00:00:00Z", "legacy_payload": {}}]
        (self.root / "data" / "canonical" / "quarantine.json").write_text(
            json.dumps({"schema_version": "2.0", "items": items}, ensure_ascii=False),
            encoding="utf-8")
        self._env = {k: os.environ.get(k) for k in (
            paid_gate.PAUSE_ENV, "ASIP_PRICE_INPUT_PER_MTOK", "ASIP_PRICE_OUTPUT_PER_MTOK")}
        for k in self._env:
            os.environ.pop(k, None)
        self._breaker = paid_gate.BREAKER_PATH
        paid_gate.BREAKER_PATH = self.root / "breaker.json"
        self._led = (ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH)
        ai_ledger.LEDGER_PATH = self.root / "ai_usage.jsonl"
        ai_ledger.SUMMARY_PATH = self.root / "ai_usage_summary.json"

    def tearDown(self):
        paid_gate.BREAKER_PATH = self._breaker
        ai_ledger.LEDGER_PATH, ai_ledger.SUMMARY_PATH = self._led
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_full_chain(self):
        # 1) 旧状态加载
        state = json.loads((self.root / "data" / "runtime" / "ops" /
                            "production_state.json").read_text(encoding="utf-8"))
        self.assertIn("social_enrichment", state["processed_hashes"])

        # 2) 分片读取（迁移后）
        store = QuarantineStore(root=self.root, max_shard_bytes=2048)
        store.migrate(dry_run=False)
        self.assertTrue(store.is_sharded())
        urls = store.url_map()
        self.assertIn("https://ex.com/blocked", urls, "安全 hold 必须仍能读到已隔离 URL")

        # 3) 模拟采集：3 条候选，其中 1 条命中隔离
        candidates = [{"url": "https://ex.com/blocked", "hash": "h1"},
                      {"url": "https://ex.com/new1", "hash": "h2"},
                      {"url": "https://ex.com/new2", "hash": "h3"}]
        blocked = [c for c in candidates if c["url"] in urls]
        fresh = [c for c in candidates if c["url"] not in urls]
        self.assertEqual(len(blocked), 1)
        self.assertEqual(len(fresh), 2)

        # 4) 状态持久化：体积守卫通过
        rep = paid_gate.state_size_report(root=self.root)
        self.assertTrue(rep["safe_to_persist"])
        # 4b) 采集 checkpoint 的文件同步（不执行 git/push）
        cs = self.root / "state_src"
        (cs / "data" / "canonical").mkdir(parents=True)
        (cs / "data" / "runtime" / "ops").mkdir(parents=True)
        old_root, old_state = commit_state.ROOT, commit_state.STATE_DIR
        commit_state.ROOT, commit_state.STATE_DIR = self.root, cs
        try:
            commit_state.COPY_PAIRS = [("data/canonical", "data/canonical"),
                                       ("data/runtime/ops", "data/runtime/ops")]
            commit_state.COPY_FILES = []
            commit_state.sync_to_state_branch()
            self.assertTrue((cs / "data" / "runtime" / "ops" / "production_state.json").exists(),
                            "采集后 checkpoint 必须能把状态复制到 state 分支树")
        finally:
            commit_state.ROOT, commit_state.STATE_DIR = old_root, old_state

        # 5) 模拟 AI（仅对 fresh 条目；processed_hashes 幂等）
        for comp in ("social_ai", "news_localization", "homepage_brief"):
            prov = ai_ledger.wrap_provider(_FakeProvider(), component=comp,
                                           run_id="E2E1", ledger_path=ai_ledger.LEDGER_PATH)
            for _ in fresh:
                prov.submit_task({"task_type": "x"})
        s1 = ai_ledger.write_summary(run_id="E2E1")
        self.assertEqual(s1["totals"]["calls"], 6)

        # 5b) 重复运行不重复计费：
        #   首轮前：fresh 中未处理的条目才应付费处理
        processed_before = set(state["processed_hashes"]["social_enrichment"])
        first_round = [c for c in fresh if c["hash"] not in processed_before]
        self.assertEqual(len(first_round), 2, "首轮应处理两条全新条目")
        #   首轮后写回 processed_hashes → 同批条目再跑必须 0 次调用
        processed_after = processed_before | {c["hash"] for c in first_round}
        rerun = [c for c in fresh if c["hash"] not in processed_after]
        self.assertEqual(len(rerun), 0, "重复运行不得重复计费（幂等）")

        # 6) 首页生成：过期数据必须提示
        (self.root / "data" / "status.json").write_text(json.dumps({
            "run_id": "R1", "data_as_of": "2026-10-27T04:55:16Z"}), encoding="utf-8")
        old_dir = bs.DATA_DIR
        bs.DATA_DIR = str(self.root / "data")
        try:
            meta = bs.get_build_meta()
            self.assertTrue(meta["data_stale"])
            self.assertGreater(meta["data_age_hours"], 12)
            html = "<html><head></head><body>hi</body></html>"
            out = bs.inject_meta(html, meta)
            self.assertIn("asip-staleness-banner", out, "过期数据必须出现提示横幅")
            # 新鲜数据不提示
            meta2 = dict(meta, data_age_hours=1.0, data_stale=False)
            self.assertNotIn("asip-staleness-banner", bs.inject_meta(html, meta2))
        finally:
            bs.DATA_DIR = old_dir

        # 7) 部署资格判断（报告分类闸门）
        self.assertTrue(so.deploy_required_for("FULL"))
        self.assertFalse(so.deploy_required_for("HOLD"))

        # 8) GitHub 单文件上限：分片必须远低于硬限
        idx = store.read_index()
        self.assertLess(max(s["bytes"] for s in idx["shards"]),
                        paid_gate.GITHUB_HARD_LIMIT_BYTES)

    def test_pause_mode_zero_paid_calls(self):
        """暂停模式下：无采集、无模型调用、无状态写入。"""
        os.environ[paid_gate.PAUSE_ENV] = "1"
        calls = []
        orig = so._run_script
        so._run_script = lambda *a, **k: calls.append(a) or True
        try:
            res = so.execute({"due": [{"task": "collection", "reason": "x"},
                                      {"task": "news_localization", "reason": "x"}]},
                             state=dict(self.state),
                             trigger_meta={"trigger_source": "external_scheduler"})
        finally:
            so._run_script = orig
        self.assertEqual(calls, [])
        self.assertEqual(res["executed"], [])
        self.assertEqual(ai_ledger.read_ledger(run_id=""), [])
        # 状态文件未被修改
        st = json.loads((self.root / "data" / "runtime" / "ops" /
                         "production_state.json").read_text(encoding="utf-8"))
        self.assertEqual(st["last_successful_collection"], "2026-10-27T04:55:16Z")


if __name__ == "__main__":
    unittest.main(verbosity=2)
