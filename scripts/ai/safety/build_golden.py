#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Run#15 artifact 提取 Stage8C Golden fixtures（真实 AI 输入/输出）。

只读运行：从 run15 case_results.json + canonical 数据提取 S3/S8/D1（FAIL 集）
与 S4/S6/S7/D4（PASS 回归集），写入 data/qualification/stage8c/golden/。
不调用任何 AI，不修改 Stage8B 数据。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

ART = Path(r"C:/Users/kenan/WorkBuddy/2026-07-31-09-46-56/.workbuddy/tmp/run15_art/data/runtime/ai_qualification/stage8b/case_results.json")
OUT_DIR = ROOT / "data" / "qualification" / "stage8c" / "golden"

# case_id -> (category, canonical source)
SEC_MAP = {
    "S3": ("direct_security", "EVT_15fee76f358f8d07"),
    "S4": ("economic_news", "EVT_b3861ba5c8d78187"),
    "S6": ("ordinary_security", "EVT_451cac52bc310619"),
    "S7": ("civil_unrest", "EVT_9a551301360773c7"),
    "S8": ("multi_country", "EVT_1c75828bd994ec7b"),
}
DIS_MAP = {
    "D1": ("disease_cholera", "DSEV_df9984f4005978cb"),
    "D4": ("disease_cholera_tcd", "DSEV_ac0ee92b04bc87c6"),
}


def main():
    cases = json.loads(ART.read_text(encoding="utf-8"))
    by_id = {c["case_id"]: c for c in cases}
    evs = json.loads((ROOT / "data/canonical/event_clusters.json").read_text(encoding="utf-8"))["items"]
    dis = json.loads((ROOT / "data/disease/canonical/outbreak_events.json").read_text(encoding="utf-8"))["items"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    for cid, (cat, eid) in list(SEC_MAP.items()) + list(DIS_MAP.items()):
        c = by_id.get(cid)
        if not c:
            print("MISSING case %s in artifact" % cid)
            continue
        parsed = c.get("parsed")
        if parsed is None:
            print("MISSING parsed for %s" % cid)
            continue
        # input payload 从 canonical 重建（S/D case 输入即 canonical 事件，确定性）
        if eid in {e["event_id"] for e in evs}:
            payload = next(e for e in evs if e["event_id"] == eid)
        elif eid in {e["disease_event_id"] for e in dis}:
            payload = next(e for e in dis if e["disease_event_id"] == eid)
        else:
            print("MISSING canonical payload for %s (%s)" % (cid, eid))
            continue
        g = {
            "case_id": cid,
            "category": cat,
            "task_type": c.get("task_type"),
            "semantic": c.get("semantic"),
            "run15_errors": c.get("errors") or [],
            "run15_attribution_loss": bool(c.get("errors")),
            "input_payload": payload,
            "original_ai_output": parsed,
            "expected_validator": "FAIL" if c.get("errors") else "PASS",
            "source": "Run#15 ACTIONS_RUN_ID=33018481998",
        }
        (OUT_DIR / ("%s.json" % cid)).write_text(
            json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
        print("WROTE %s  expected_validator=%s  errors=%s"
              % (cid, g["expected_validator"], bool(c.get("errors"))))
        n += 1
    print("TOTAL_GOLDEN=%d -> %s" % (n, OUT_DIR))


if __name__ == "__main__":
    main()
