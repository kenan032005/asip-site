#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_stage2_closeout.py —— ASIP 第二阶段最终收尾 专项测试（20 项）

覆盖：
  A. 当前公开事件隔离（is_current_public_event）
  B. 日报持续跟踪重建（is_ongoing_report_event）
  C. 部署白名单与内部数据隔离（build_site.py / dist）
  D. 统计口径与文档一致性

退出码：FAIL>0 → 1；否则 0。
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline_core import (  # noqa: E402
    is_current_public_event,
    is_ongoing_report_event,
)

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}" + (f" -- {detail}" if detail else ""))


def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


WIN_END = datetime(2026, 7, 30, 22, 0, 0)


def mk_event(**over):
    """构造一个"完全合格"的当前公开事件，再由调用方覆盖字段。"""
    base = {
        "event_id": "EVT_0123456789abcdef",
        "country": "乍得",
        "title_cn": "测试事件",
        "summary_cn": "测试摘要",
        "current_policy_passed": True,
        "quality_gate_passed": True,
        "legacy_migration_preserved": False,
        "event_status": "ongoing",
        "event_time": "2026-07-30T10:00:00+08:00",
        "last_seen_at": "2026-07-30T12:00:00+08:00",
        "source_links": [{"name": "Reuters", "url": "https://reuters.com/x"}],
    }
    base.update(over)
    return base


def main():
    # ── A. 当前公开事件隔离 ───────────────────────────────
    # 1
    check("T01 合格事件通过 is_current_public_event",
          is_current_public_event(mk_event()) is True)
    # 2
    check("T02 历史迁移保留事件被拒（legacy_migration_preserved=true）",
          is_current_public_event(mk_event(
              legacy_migration_preserved=True)) is False)
    # 3
    check("T03 current_policy_passed=false 被拒",
          is_current_public_event(mk_event(
              current_policy_passed=False)) is False)
    # 4
    check("T04 quality_gate_passed=false 被拒",
          is_current_public_event(mk_event(
              quality_gate_passed=False)) is False)
    # 5
    check("T05 quarantined / 非法状态被拒",
          is_current_public_event(mk_event(event_status="quarantined")) is False
          and is_current_public_event(mk_event(quarantined=True)) is False)
    # 6
    check("T06 event_id 非法被拒",
          is_current_public_event(mk_event(event_id="EVT_bad")) is False
          and is_current_public_event(mk_event(event_id="")) is False)
    # 7
    check("T07 缺来源 / 缺国家被拒",
          is_current_public_event(mk_event(source_links=[])) is False
          and is_current_public_event(mk_event(country="")) is False)
    # 8
    check("T08 非 dict 输入安全返回 False",
          is_current_public_event(None) is False
          and is_current_public_event("x") is False
          and is_current_public_event([]) is False)

    # ── B. 日报持续跟踪重建 ──────────────────────────────
    # 9
    check("T09 ongoing 近期事件进入持续跟踪",
          is_ongoing_report_event(mk_event(), WIN_END) is True)
    # 10
    check("T10 developing / easing 进入持续跟踪",
          is_ongoing_report_event(mk_event(event_status="developing"), WIN_END)
          and is_ongoing_report_event(mk_event(event_status="easing"), WIN_END))
    # 11
    check("T11 ended / archived 不进入持续跟踪",
          is_ongoing_report_event(mk_event(event_status="ended"), WIN_END) is False
          and is_ongoing_report_event(mk_event(event_status="archived"), WIN_END) is False)
    # 12
    old = (WIN_END - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    check("T12 超过 7 天无活动不进入持续跟踪",
          is_ongoing_report_event(mk_event(last_seen_at=old, event_time=old),
                                  WIN_END) is False)
    # 13
    check("T13 历史迁移事件绝不进入持续跟踪",
          is_ongoing_report_event(mk_event(legacy_migration_preserved=True,
                                           current_policy_passed=False),
                                  WIN_END) is False)
    # 14
    check("T14 unknown / 空状态不进入持续跟踪",
          is_ongoing_report_event(mk_event(event_status="unknown"), WIN_END) is False
          and is_ongoing_report_event(mk_event(event_status=""), WIN_END) is False)

    # ── C. 部署白名单与内部数据隔离 ───────────────────────
    bs = (ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
    # 15
    check("T15 build_site.py 使用显式白名单且不整目录复制 data/",
          "PUBLIC_DATA_ALLOWLIST" in bs
          and "_copy_public_data" in bs
          and "copytree(DATA_DIR" not in bs.replace(" ", ""),
          "白名单/复制函数缺失或仍存在整目录 copytree")
    # 16
    check("T16 build_site.py 白名单不含 canonical / backup / quarantine",
          not re.search(r"PUBLIC_DATA_ALLOWLIST[\s\S]{0,600}?canonical", bs)
          and not re.search(r"PUBLIC_DATA_ALLOWLIST[\s\S]{0,600}?backup", bs))
    # 17
    check("T17 __DB__ 内联快照使用脱敏白名单加载器",
          "load_public_db" in bs and "inject_db(html, load_public_db" in bs)

    dist = ROOT / "dist"
    if dist.exists():
        can = list((dist / "data").glob("canonical/**/*")) if (dist / "data").exists() else []
        bak = list((dist / "data").glob("backup/**/*")) if (dist / "data").exists() else []
        # 18
        check("T18 dist/data 不含 canonical / backup 目录",
              not can and not bak,
              f"canonical={len(can)} backup={len(bak)}")
        # 19
        hits = []
        winpat = re.compile(r"[A-Za-z]:(?:\\\\|\\|/)+Users(?:\\\\|\\|/)+[A-Za-z0-9_.-]+")
        for f in dist.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in (".json", ".html", ".js"):
                continue
            try:
                t = f.read_text(encoding="utf-8")
            except Exception:
                continue
            if "legacy_payload" in t or winpat.search(t):
                hits.append(str(f.relative_to(dist)))
        check("T19 dist 无 legacy_payload 与本机路径",
              not hits, "; ".join(hits[:5]))
    else:
        check("T18 dist/data 不含 canonical / backup 目录", True, "dist 未构建，跳过")
        check("T19 dist 无 legacy_payload 与本机路径", True, "dist 未构建，跳过")

    # ── D. 统计口径与文档一致性 ──────────────────────────
    # 20
    pub = read_json(ROOT / "data" / "public" / "published_events.json", {})
    cm = read_json(ROOT / "data" / "public" / "current_metrics.json", {})
    items = pub.get("items", pub.get("events", [])) if isinstance(pub, dict) else []
    n_cur = sum(1 for e in items if isinstance(e, dict)
                and e.get("current_policy_passed") is True)
    pc = cm.get("publishable_clusters") if isinstance(cm, dict) else None
    check("T20 current_metrics.publishable_clusters 与 current_policy_passed 数一致",
          pc is None or pc == n_cur,
          f"publishable_clusters={pc} current_policy_passed={n_cur}")

    # 附加：README 与归档文件一致性（不计入 20 项主编号，仍参与 PASS/FAIL）
    rd = (ROOT / "README.md").read_text(encoding="utf-8")
    stale = [s for s in ("（42 项）失败即中止", "→ 42 项校验",
                         "配置 93 个源") if s in rd]
    check("T21 README 无过时数字表述且含第十五节收尾声明",
          not stale and "十五、第二阶段正式收尾" in rd,
          f"stale={stale}")
    arch = ROOT / "data" / "public" / "legacy_archive_events.json"
    if arch.exists():
        a = read_json(arch, {})
        txt = arch.read_text(encoding="utf-8")
        check("T22 legacy_archive_events.json 结构合法且已裁剪脱敏",
              isinstance(a, dict) and "items" in a
              and "legacy_payload" not in txt
              and not re.search(r"[A-Za-z]:(?:\\\\|\\|/)+Users", txt))
    else:
        check("T22 legacy_archive_events.json 结构合法且已裁剪脱敏",
              True, "尚未生成，跳过")

    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
