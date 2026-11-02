#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1D — quarantine 备份/迁移/退役/回滚 CLI（运维入口）。

命令：
  --backup            离线备份（必须在 Git 工作树之外）+ 写备份清单（sha256/bytes/items）
  --dry-run           只计算迁移计划
  --apply             迁移（**必须**提供有效备份清单，清单哈希须与当前单体一致）
  --verify            内容级校验（id 集合/月份归属/ids 映射/分片 sha/index/manifest）
  --retire            迁移后退役旧单体（写 <4KB 墓碑）
  --tree              输出预期 Git 树（path → bytes）
  --rollback          回滚：合并全部分片（含迁移后新增）→ 写单体 → 校验 → 清理分片

安全约束：
  * 备份目录**不得**位于 Git 工作树内（防止 >100MB 单体被误提交）；
  * `--apply` / `--retire` 必须带 `--expect N`，并在迁移后再次校验；
  * 备份失败 / 清单不匹配 → 拒绝迁移（非零退出）。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.data.quarantine_store import QuarantineStore, QuarantineCorrupt  # noqa: E402

EXIT_OK = 0
EXIT_VERIFY = 1
EXIT_REFUSED = 9
EXIT_BACKUP = 10


def _git_toplevel(path):
    try:
        r = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:  # noqa: BLE001
        return ""


def _inside_worktree(dest, root):
    """dest 是否位于 root 的 Git 工作树内（含子目录）。"""
    top = _git_toplevel(root)
    if not top:
        return False
    d = Path(dest).resolve()
    try:
        d.relative_to(Path(top).resolve())
        return True
    except ValueError:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--backup", action="store_true")
    ap.add_argument("--backup-dir", default=None)
    ap.add_argument("--backup-manifest", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    ap.add_argument("--retire", action="store_true")
    ap.add_argument("--tree", action="store_true")
    ap.add_argument("--expect", type=int, default=None)
    ap.add_argument("--max-shard-mb", type=float, default=20.0)
    ap.add_argument("--allow-remigrate", action="store_true")
    a = ap.parse_args(argv)

    root = Path(a.root).resolve()
    store = QuarantineStore(root=root, max_shard_bytes=int(a.max_shard_mb * 1024 * 1024))
    try:
        # ── 备份 ────────────────────────────────────────────────
        if a.backup:
            if not a.backup_dir:
                print(json.dumps({"ok": False, "error": "--backup requires --backup-dir"},
                                 ensure_ascii=False))
                return EXIT_BACKUP
            dest = Path(a.backup_dir).resolve()
            if _inside_worktree(dest, root):
                print(json.dumps({"ok": False,
                                  "error": "backup dir must be OUTSIDE the git worktree: %s" % dest},
                                 ensure_ascii=False))
                return EXIT_BACKUP
            rep = store.write_backup_manifest(dest, expect_items=a.expect)
            print(json.dumps(rep, ensure_ascii=False, indent=1))
            ok = (a.expect is None or rep["items"] == a.expect)
            return EXIT_OK if ok else EXIT_BACKUP

        # ── 迁移 ────────────────────────────────────────────────
        if a.dry_run or a.apply:
            if a.apply:
                if a.expect is None:
                    print(json.dumps({"ok": False, "error": "--apply requires --expect N"},
                                     ensure_ascii=False))
                    return EXIT_REFUSED
                mp = a.backup_manifest
                if not mp and a.backup_dir:
                    cand = Path(a.backup_dir) / "quarantine.backup.json"
                    mp = str(cand) if cand.exists() else None
                if not mp:
                    print(json.dumps({"ok": False,
                                      "error": "migration requires a valid backup manifest "
                                               "(--backup-manifest or --backup-dir)"},
                                     ensure_ascii=False))
                    return EXIT_REFUSED
                pre = store.assert_backup_matches(mp)
                print(json.dumps({"backup_preflight": pre}, ensure_ascii=False, indent=1))
            rep = store.migrate(dry_run=not a.apply, allow_remigrate=a.allow_remigrate,
                                expect_items=a.expect)
            print(json.dumps(rep, ensure_ascii=False, indent=1))
            if rep.get("refused"):
                return EXIT_REFUSED
            if a.apply:
                cons = store.verify_consistency()
                print(json.dumps(cons, ensure_ascii=False, indent=1))
                if a.expect is not None and cons["on_disk"] != a.expect:
                    return EXIT_VERIFY
            return EXIT_OK

        # ── 校验 ────────────────────────────────────────────────
        if a.verify:
            rep = store.verify(expect_items=a.expect)
            rep["consistency"] = store.verify_consistency() if store.is_sharded() else None
            print(json.dumps(rep, ensure_ascii=False, indent=1))
            ok = rep.get("count_match", True) and rep.get("duplicate_ids") == 0
            return EXIT_OK if ok else EXIT_VERIFY

        # ── 退役 ────────────────────────────────────────────────
        if a.retire:
            rep = store.retire_monolith(backup_dir=a.backup_dir, expect_items=a.expect)
            print(json.dumps(rep, ensure_ascii=False, indent=1))
            cons = store.verify_consistency()
            tree = store.expected_tree()
            print(json.dumps({"consistency": cons, "tree": tree}, ensure_ascii=False, indent=1))
            ok = (cons["consistent"] and tree["all_below_hard_limit"]
                  and (a.expect is None or cons["on_disk"] == a.expect))
            return EXIT_OK if ok else EXIT_VERIFY

        if a.tree:
            print(json.dumps(store.expected_tree(), ensure_ascii=False, indent=1))
            return EXIT_OK

        # ── 回滚 ────────────────────────────────────────────────
        if a.rollback:
            rep = store.rollback_to_monolith(expect_items=a.expect)
            print(json.dumps(rep, ensure_ascii=False, indent=1))
            return EXIT_OK if rep.get("ok") else EXIT_VERIFY

        print(json.dumps({"error": "specify --backup|--dry-run|--apply|--verify|--retire|"
                                   "--tree|--rollback"}, ensure_ascii=False))
        return 2
    except QuarantineCorrupt as e:
        print(json.dumps({"ok": False, "error": "QuarantineCorrupt: %s" % e}, ensure_ascii=False))
        return EXIT_VERIFY


if __name__ == "__main__":
    sys.exit(main())
