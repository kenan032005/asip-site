#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_build_site_report_publication.py — §6 C4 build output 契约测试。

锁定「一次正式 build 之后 dist/data/reports 精确反映本次构建」：
  * 发布（source → dist_new → dist）
  * 新增 / 修改 / **删除** 同步
  * report_index ↔ artifact 双向一致
  * 不依赖任何手工同步

module 级会**真实跑一次 build**（除非 ASIP_SKIP_BUILD_TEST=1），
并在构建前向 dist 注入一个陈旧 artifact 以验证删除语义。
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "scripts")):
    sys.path.insert(0, p)

from scripts import build_site as BS          # noqa: E402

DIST = ROOT / "dist"
SRC_REPORTS = ROOT / "data" / "reports"
STALE_NAME = "DAILY_19990101.json"
STALE_REL = "data/reports/daily/" + STALE_NAME
_BUILD = {"ran": False, "ok": False, "log": ""}


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _rel_json(root):
    out = {}
    root = Path(root)
    if not root.is_dir():
        return out
    for f in root.rglob("*.json"):
        out[str(f.relative_to(root)).replace("\\", "/")] = f
    return out


def _status_run_id():
    """C6-R2.6：构建必须沿用 data/status.json 的 run_id。

    禁止在测试里生成「新的 run_id」——那会把 legacy 视图
    （events.json / pending_events.json / raw_candidates.json）的 run_id
    改写成测试值，导致后续 S29（public ↔ legacy run_id 一致）在 runner 内失败。
    """
    try:
        with io.open(ROOT / "data" / "status.json", encoding="utf-8") as f:
            rid = (json.load(f) or {}).get("run_id")
        if rid:
            return rid
    except Exception:  # noqa: BLE001
        pass
    return "20260921T140000+0800_buildtest"


def setUpModule():
    """构建前注入陈旧 artifact，然后真实构建一次（验证删除语义 + 发布一致性）。"""
    if os.environ.get("ASIP_SKIP_BUILD_TEST") == "1":
        return
    stale = DIST / STALE_REL
    if DIST.is_dir():
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text(json.dumps({"report_id": "DAILY_19990101", "status": "FALLBACK"}),
                         encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "scripts.build_site",
                        "--run-id", _status_run_id()],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=900)
    _BUILD["ran"] = True
    _BUILD["ok"] = r.returncode == 0
    _BUILD["log"] = (r.stdout or "") + (r.stderr or "")


class ReportPublicationTest(unittest.TestCase):

    def test_01_build_site_publishes_report_artifacts(self):
        """§7：一次构建必须把全部 report artifact 发布到 dist。"""
        if _BUILD["ran"] and not _BUILD["ok"]:
            self.fail("build_site 构建失败（见日志尾部）：\n" + _BUILD["log"][-1500:])
        src, dst = _rel_json(SRC_REPORTS), _rel_json(DIST / "data" / "reports")
        self.assertEqual(len(src), 22, "source report artifact 应为 22")
        self.assertEqual(set(src), set(dst), "dist 的 artifact 集合必须与 source 完全一致")
        for rel in src:
            self.assertEqual(_sha(src[rel]), _sha(dst[rel]), "%s 内容不一致" % rel)

    def test_02_dist_reports_match_dist_new_reports(self):
        """§2：构建完成后 dist 必须等于本次构建产物（.dist_new 已被交换掉）。"""
        dist_new = ROOT / ".dist_new"
        self.assertFalse(dist_new.exists(),
                         ".dist_new 残留 = 本次构建未完成交换（dist 可能被占用）")
        res = BS.verify_report_publication(str(DIST), str(ROOT / "data"))
        self.assertEqual(res["REPORT_ARTIFACT_PUBLICATION"], "PASS")
        self.assertEqual(res["SOURCE_REPORT_COUNT"], res["DIST_REPORT_COUNT"])
        self.assertEqual(res["MISMATCHED_REPORT_ARTIFACTS"], 0)

    def test_03_stale_report_removed_from_dist(self):
        """§4：source 里不存在的 artifact 必须从 dist 消失（不能只增不减）。"""
        self.assertFalse((DIST / STALE_REL).exists(),
                         "陈旧 artifact 仍残留在 dist：构建只做了「加文件」")
        # 反向：dist 里不得存在 index 之外的正式 artifact
        dst = _rel_json(DIST / "data" / "reports")
        src = _rel_json(SRC_REPORTS)
        self.assertEqual(sorted(set(dst) - set(src)), [],
                         "dist 出现 source 之外的 artifact（陈旧残留）")

    def test_04_report_index_paths_exist_in_dist(self):
        """§5：index 引用的每个 artifact 都必须存在，且反向不留孤儿。"""
        idx_path = None
        for rel in BS.REPORT_INDEX_CANDIDATES:
            if (DIST / rel).exists():
                idx_path = DIST / rel
                break
        self.assertIsNotNone(idx_path, "dist 中找不到 report_index.json")
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
        rows = idx.get("reports") or []
        self.assertEqual(idx.get("count"), 22)
        self.assertEqual(len(rows), 22)
        missing = [r.get("path") for r in rows
                   if not (DIST / str(r.get("path") or "")).exists()]
        self.assertEqual(missing, [], "index 引用了 dist 中不存在的 artifact")
        indexed = {str(r.get("path")).replace("\\", "/") for r in rows}
        # 统一基准：index 的 path 相对 dist 根（data/reports/...）
        on_disk = {"data/reports/" + k for k in _rel_json(DIST / "data" / "reports")}
        orphan = sorted(on_disk - indexed)
        self.assertEqual(orphan, [], "dist 存在 index 之外的孤儿 artifact")
        self.assertEqual(sum(1 for r in rows if r.get("is_mock")), 0)

    def test_05_build_does_not_depend_on_manual_report_sync(self):
        """§2/§9：发布不得依赖人工 copy；且构建脚本必须保留硬校验。"""
        src = (ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
        self.assertIn("verify_report_publication(DIST)", src,
                      "构建流程必须调用发布后校验，否则失败会静默")
        self.assertIn("_copy_report_artifacts(DIST_NEW)", src,
                      "报告 artifact 必须在 .dist_new 阶段就发布（沿用既有 build 模式）")
        # 校验函数本身要能识别不一致（用临时目录构造反例）
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "dist"
            (d / "data" / "reports" / "daily").mkdir(parents=True)
            (d / "data" / "report_index.json").write_text(
                json.dumps({"count": 1, "reports": [
                    {"report_id": "X", "path": "data/reports/daily/X.json",
                     "is_mock": False}]}), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                BS.verify_report_publication(str(d), str(ROOT / "data"))

    def test_06_copy_report_artifacts_covers_all_types(self):
        """发布函数本身：三类报告目录都必须被复制，且内容逐字节一致。"""
        with tempfile.TemporaryDirectory() as t:
            n = BS._copy_report_artifacts(t)
            self.assertEqual(n, 22)
            for sub in ("daily", "weekly", "country_weekly"):
                got = list((Path(t) / "data" / "reports" / sub).glob("*.json"))
                want = list((SRC_REPORTS / sub).glob("*.json"))
                self.assertEqual(len(got), len(want), sub)
                for f in want:
                    self.assertEqual(_sha(f), _sha(Path(t) / "data" / "reports" / sub / f.name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
