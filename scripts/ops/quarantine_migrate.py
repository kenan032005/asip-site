#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1B — quarantine 迁移/校验/回滚 CLI（运维入口）。

用法（在 state_src 或代码工作树，指向仓库根）：
  python scripts/ops/quarantine_migrate.py --root . --dry-run
  python scripts/ops/quarantine_migrate.py --root . --apply
  python scripts/ops/quarantine_migrate.py --root . --verify [--expect 20461]
  python scripts/ops/quarantine_migrate.py --root . --rollback [--expect 20461]

约定：
  * --apply 只在声明目录写入分片/index/ids/manifest，**不删除任何条目**；
  * --rollback 先合并全部分片（含迁移后新增）写回单体并校验，再清理分片（零丢失）；
  * --verify 做 sha256 + 计数 + index/ids/manifest 一致性校验。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.data.quarantine_store import QuarantineStore, QuarantineCorrupt  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    ap.add_argument("--retire", action="store_true", help="迁移后退役旧单体（写墓碑）")
    ap.add_argument("--backup-dir", default=None, help="旧单体离线备份目录（不进入仓库）")
    ap.add_argument("--tree", action="store_true", help="输出迁移后预期的 Git 树")
    ap.add_argument("--allow-remigrate", action="store_true")
    ap.add_argument("--expect", type=int, default=None, help="期望条目数（例如 20461）")
    ap.add_argument("--max-shard-mb", type=float, default=20.0)
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    store = QuarantineStore(root=root, max_shard_bytes=int(a.max_shard_mb * 1024 * 1024))
    try:
        if a.dry_run or a.apply:
            rep = store.migrate(dry_run=not a.apply, allow_remigrate=a.allow_remigrate)
            print(json.dumps(rep, ensure_ascii=False, indent=1))
            if rep.get("refused"):
                return 9          # 已迁移：拒绝覆盖（非零，防误用）
            if a.apply:
                print(json.dumps(store.verify_consistency(), ensure_ascii=False, indent=1))
            return 0
        if a.retire:
            rep = store.retire_monolith(backup_dir=a.backup_dir, expect_items=a.expect)
            print(json.dumps(rep, ensure_ascii=False, indent=1))
            print(json.dumps(store.expected_tree(), ensure_ascii=False, indent=1))
            return 0
        if a.tree:
            print(json.dumps(store.expected_tree(), ensure_ascii=False, indent=1))
            return 0
        if a.verify:
            rep = store.verify(expect_items=a.expect)
            rep["consistency"] = store.verify_consistency() if store.is_sharded() else None
            print(json.dumps(rep, ensure_ascii=False, indent=1))
            ok = (rep.get("count_match", True) and rep.get("duplicate_ids") == 0)
            return 0 if ok else 1
        if a.rollback:
            rep = store.rollback_to_monolith(expect_items=a.expect)
            print(json.dumps(rep, ensure_ascii=False, indent=1))
            return 0 if rep.get("ok") else 1
        print(json.dumps({"error": "specify --dry-run|--apply|--verify|--rollback"},
                         ensure_ascii=False))
        return 2
    except QuarantineCorrupt as e:
        print(json.dumps({"ok": False, "error": "QuarantineCorrupt: %s" % e}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
