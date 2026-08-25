#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 传染病数据链 CLI（§十四 手动 dry-run）。

用法：
  python scripts/disease/cli.py --ingest docs/stage5-disease-candidates.json [--apply]

- --ingest：读取手动采集的候选通报（真实公开数据）→ normalize → 质量 Gate
  → 写 Disease Canonical（默认 dry-run 不写盘，--apply 才写）；
- 不恢复 schedule；不调用 AI；不写 Public（Public 由 build_public 单独生成）。
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.disease.normalizer import build_disease_event
from scripts.disease.gate import run_gate
from scripts.disease.canonical import upsert, load_canonical, make_event_id
from scripts.disease.build_public import build_public
from scripts.disease.diseases import load_diseases
from scripts.disease.constants import RULES_VERSION


def main(argv=None):
    ap = argparse.ArgumentParser(description="ASIP Stage 5 传染病数据链 CLI（手动 dry-run）")
    ap.add_argument("--ingest", help="候选通报 JSON 路径（真实公开数据，手动采集）")
    ap.add_argument("--apply", action="store_true", help="写盘 Canonical/Public（默认 dry-run）")
    args = ap.parse_args(argv)

    if not args.ingest:
        ap.print_help()
        return 0

    cand = json.loads(Path(args.ingest).read_text(encoding="utf-8"))
    # 按 report_date 升序处理（先早后晚），保证 previous/supersede 时间方向正确
    items = sorted(cand.get("items", []), key=lambda r: (r.get("report_date") or ""))
    print("candidates=%d rules_version=%s" % (len(items), RULES_VERSION))
    print()

    diseases = load_diseases()
    ok, fail = 0, 0
    fail_reasons = {}
    stats = {"diseases": set(), "countries": set(), "statuses": set()}
    new_items = []

    for i, raw in enumerate(items):
        seed = raw.get("seed") or "%s|%s|%s" % (
            raw.get("disease_raw"), raw.get("country_iso3"), raw.get("report_date"))
        eid = make_event_id(seed)
        fields = build_disease_event(eid, raw)
        passed, errors = run_gate(fields)

        if not passed:
            fail += 1
            fail_reasons.setdefault(errors[0], 0)
            fail_reasons[errors[0]] += 1
            print("FAIL %-22s disease=%s %s | %s" % (
                eid[:10], fields["disease_id"], fields["country_iso3"], errors[0]))
            continue

        ok += 1
        stats["diseases"].add(fields["disease_id"])
        stats["countries"].add(fields["country_iso3"])
        stats["statuses"].add(fields["verification_status"])
        new_items.append(fields)
        print(" OK  %-22s disease=%-14s country=%-4s status=%s conf=%d total=%s deaths=%s" % (
            eid[:10], fields["disease_id"], fields["country_iso3"],
            fields["verification_status"], fields["verification_confidence"],
            fields.get("total_cases"), fields.get("deaths")))

    print()
    print("normalized: ok=%d fail=%d" % (ok, fail))
    print("diseases covered: %d -> %s" % (len(stats["diseases"]), sorted(stats["diseases"])))
    print("countries covered: %d -> %s" % (len(stats["countries"]), sorted(stats["countries"])))
    print("verification statuses: %s" % sorted(stats["statuses"]))
    if fail_reasons:
        print("fail reasons: %s" % fail_reasons)

    if args.apply:
        for f in new_items:
            upsert(f)
        count, orphans, st = build_public(dry_run=False)
        print()
        print("canonical=%d public=%d orphans=%d public_status=%s" % (
            len(load_canonical()["items"]), count, len(orphans), st))
    else:
        print("dry-run：未写盘（加 --apply 生效）")
    return 0 if fail == 0 else 0  # 允许部分失败（个别来源不可解析不阻断）

if __name__ == "__main__":
    sys.exit(main())
