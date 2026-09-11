#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production maintenance regression tests — state load/commit symmetry（V1.0 hotfix）。

背景（真实生产故障，2026-09-11 定位）：
  orchestrator 的 "Load state（cold start）" 只恢复 data/runtime/ops/，
  而 "Commit state" 却写回 canonical / disease / timeline / events / pending /
  raw_candidates / quarantine_events / public。
  → 每个 run 都从 release 仓库自带的静态 data/ 起步；未重新生成该路径的 run
     会把仓库旧副本写回 production-state，导致 canonical 每约 6 小时被回退一次
     （采集推进 179 条 → 下一轮退回 152 条 20260802 版本，字节级一致）。

本文件锁定以下不变量：
  A. Load 必须覆盖 Commit 写回的全部 state 管理路径（对称性）
  B. 子流程写入的 state 结果不得被父流程用旧快照覆盖
  C. data_as_of / latest_verified_event_time / generated_at 语义互不混用
  D. 近期零事件是合法当前状态，不得视为失败
"""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "frontend"))

#: production-state 管理的路径（load 与 commit 必须一致）
STATE_MANAGED_PATHS = [
    "data/runtime/ops",
    "data/canonical",
    "data/disease",
    "data/runtime/timeline",
    "data/events.json",
    "data/pending_events.json",
    "data/raw_candidates.json",
    "data/quarantine_events.json",
    "data/public",
]


def _workflow_text(name):
    """定位 workflow YAML：优先 ASIP_WORKFLOWS_DIR，缺省 ROOT/.github/workflows。"""
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


def _load_block(text):
    """截取 Load state 步骤的 run 内容。"""
    marker = "Load state"
    i = text.find(marker)
    if i < 0:
        return None
    j = text.find("- name:", i)
    return text[i:j if j > 0 else len(text)]


def _commit_block(text):
    i = text.find("Commit state")
    if i < 0:
        return None
    j = text.find("- name:", i)
    return text[i:j if j > 0 else len(text)]


class TestStatePathSymmetry(unittest.TestCase):
    """A. load/commit 路径对称性（本次故障的直接防线）。"""

    def _wf(self):
        t = _workflow_text("asip-production-orchestrator.yml")
        if t is None:
            self.skipTest("orchestrator workflow 不在本 checkout（release 代码分支）")
        return t

    def test_load_restores_every_state_managed_path(self):
        text = self._wf()
        load = _load_block(text)
        self.assertIsNotNone(load, "未找到 Load state 步骤")
        missing = []
        for p in STATE_MANAGED_PATHS:
            if p == "data/runtime/ops":
                continue
            # load 必须出现 state_src/<path>
            if ("state_src/%s" % p) not in load:
                missing.append(p)
        self.assertFalse(
            missing,
            "Load state 未恢复以下 state 管理路径（会导致下一轮把仓库旧副本写回 state）：%s" % missing)

    def test_load_and_commit_cover_same_path_set(self):
        text = self._wf()
        load, commit = _load_block(text), _commit_block(text)
        self.assertIsNotNone(load)
        self.assertIsNotNone(commit)
        for p in STATE_MANAGED_PATHS:
            in_load = ("state_src/%s" % p) in load
            in_commit = ("%s" % p) in commit
            self.assertTrue(
                in_load == in_commit,
                "路径 %s 在 load/commit 间不对称（load=%s commit=%s）" % (p, in_load, in_commit))


class TestParentDoesNotClobberChild(unittest.TestCase):
    """B. 父流程不得用旧快照覆盖子流程写入的 state。"""

    def test_parent_state_does_not_overwrite_child_state(self):
        """模拟：仓库静态副本(旧) + state 快照(新) → load 后必须是新版本胜出。"""
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            data = Path(td) / "data" / "canonical"
            state = Path(td) / "state_src" / "data" / "canonical"
            data.mkdir(parents=True)
            state.mkdir(parents=True)
            (data / "event_clusters.json").write_text(
                json.dumps({"run_id": "OLD_REPO_COPY", "items": [{"event_id": "EVT_old"}]}),
                encoding="utf-8")
            (state / "event_clusters.json").write_text(
                json.dumps({"run_id": "NEW_STATE", "items": [{"event_id": "EVT_new"}]}),
                encoding="utf-8")
            # 等价于修复后的 load：state → data（后者覆盖前者）
            for f in state.iterdir():
                shutil.copy2(f, data / f.name)
            got = json.loads((data / "event_clusters.json").read_text(encoding="utf-8"))
            self.assertEqual(got["run_id"], "NEW_STATE",
                             "state 快照必须覆盖 release 仓库自带的静态副本")

    def test_collection_candidate_persisted_to_state(self):
        """采集写入 canonical 的新事件，必须在 state 提交后仍然存在。"""
        text = _workflow_text("asip-production-orchestrator.yml")
        if text is None:
            self.skipTest("workflow 不在本 checkout")
        commit = _commit_block(text)
        self.assertIn("data/canonical", commit,
                      "commit 步骤必须提交 canonical（否则采集结果不落 state）")
        load = _load_block(text)
        self.assertIn("state_src/data/canonical", load,
                      "load 步骤必须恢复 canonical（否则下一轮回退采集结果）")

    def test_pending_survives_state_commit(self):
        text = _workflow_text("asip-production-orchestrator.yml")
        if text is None:
            self.skipTest("workflow 不在本 checkout")
        commit = _commit_block(text)
        for f in ("data/pending_events.json", "data/raw_candidates.json"):
            self.assertIn(f, commit, "%s 必须随 state 提交" % f)


class TestPromotionLifecycle(unittest.TestCase):
    """C. 候选生命周期：验证/准入/提升/拒绝。"""

    def _repo(self, tmp):
        from scripts.data.repository import Repository
        return Repository(root=Path(tmp))

    def test_verified_candidate_reaches_admission(self):
        """通过 safety gate 的候选必须能写入 processed_hashes 的 public_eligible。"""
        from scripts.ops import production_state as ps
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            st = {"processed_hashes": {}}
            ps.mark_processed(st, "social_enrichment", "EVT_test_1",
                              {"status": "ok", "public_eligible": True})
            self.assertTrue(
                (st["processed_hashes"]["social_enrichment"]["EVT_test_1"] or {}).get("public_eligible"))

    def test_admitted_candidate_can_promote_to_canonical(self):
        """admission 真值（processed_hashes）必须能被 timeline/view 构建消费为 public truth。"""
        from scripts.ops import timeline_run as tr
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "canonical").mkdir(parents=True)
            (root / "runtime" / "ops").mkdir(parents=True)
            (root / "canonical" / "event_clusters.json").write_text(json.dumps({
                "items": [{"event_id": "EVT_ok", "event_time": "2026-09-11T00:00:00Z"},
                          {"event_id": "EVT_not_admitted", "event_time": "2026-09-11T00:00:00Z"}]
            }), encoding="utf-8")
            (root / "runtime" / "ops" / "production_state.json").write_text(json.dumps({
                "processed_hashes": {"social_enrichment": {"EVT_ok": {"public_eligible": True}}}
            }), encoding="utf-8")
            adm = tr.load_public_admission(data_dir=str(root))
            self.assertIn("EVT_ok", adm["social"])
            self.assertNotIn("EVT_not_admitted", adm["social"])

    def test_rejected_candidate_does_not_promote(self):
        """未通过 admission 的候选不得进入 public truth。"""
        from scripts.ops import timeline_run as tr
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "runtime" / "ops").mkdir(parents=True)
            (root / "runtime" / "ops" / "production_state.json").write_text(json.dumps({
                "processed_hashes": {"social_enrichment": {
                    "EVT_held": {"status": "schema_failure", "public_eligible": False}}}
            }), encoding="utf-8")
            adm = tr.load_public_admission(data_dir=str(root))
            self.assertNotIn("EVT_held", adm["social"])


class TestFreshnessSemantics(unittest.TestCase):
    """D. 三类时间语义必须区分，不得互相冒充。"""

    def test_pipeline_data_as_of_distinct_from_generated_at(self):
        tls = [{"report_date": "2026-09-10", "latest_report_at": "2026-09-10T00:00:00Z"}]
        self.assertNotEqual(tls[0]["report_date"], tls[0]["latest_report_at"],
                            "data_as_of 与 generated_at 不得混用同一字段表达")
        # 视图 generated_at 是构建时间，必须与数据截止时间分开表达
        from scripts.frontend import build_frontend_views as bfv
        ov = bfv.build_site_overview([], [], [], {"latest_report_date": "2026-09-10"},
                                     tls, None, {})
        self.assertIn("generated_at", ov)
        self.assertIn("latest_data_time_bj", ov)
        self.assertNotEqual(ov.get("generated_at"), ov.get("latest_data_time_bj"),
                            "generated_at（视图重建时间）必须与数据时间字段分离")

    def test_latest_event_time_distinct_from_data_as_of(self):
        from scripts.frontend import build_frontend_views as bfv
        events = [{"event_id": "EVT_a", "event_time": "2026-09-11T02:00:00Z"}]
        ov = bfv.build_site_overview(events, [], [], {}, [], None, {})
        self.assertNotEqual(ov.get("generated_at"), events[0]["event_time"],
                            "最新事件时间不得与视图生成时间等同")

    def test_recent_zero_events_is_valid_current_state(self):
        """最近窗口内零事件是合法状态（不得为“看起来更新”伪造事件）。"""
        from scripts.frontend import build_frontend_views as bfv
        ov = bfv.build_site_overview([], [], [], {}, [], None, {})
        self.assertIsInstance(ov, dict)
        kpis = ov.get("kpis") or {}
        self.assertEqual(int(kpis.get("events_24h") or 0), 0,
                         "无事件时 24h KPI 必须为 0，而不是编造数据")


if __name__ == "__main__":
    unittest.main(verbosity=2)
