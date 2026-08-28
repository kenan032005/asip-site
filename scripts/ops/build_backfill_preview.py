# -*- coding: utf-8 -*-
"""Backfill → V1.1 Preview 构建（临时合并工作树数据 → timelines → build_site → 恢复）。
只影响本地 preview 构建；结束后 git checkout 恢复 tracked 数据文件。"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

PY = r"C:/Users/kenan/.workbuddy/binaries/python/versions/3.13.12/python.exe"
ROOT = Path("C:/Users/kenan/WorkBuddy/clean/asip-v11-homepage")
BK = ROOT / ".workbuddy_tmp" / "backup_data"
PV = ROOT / "data/runtime/backfill_preview"

TRACKED = [
    ROOT / "data/canonical/event_clusters.json",
    ROOT / "data/disease/canonical/outbreak_events.json",
    ROOT / "data/events.json",
]

# 1) 备份 tracked 数据
BK.mkdir(parents=True, exist_ok=True)
for p in TRACKED:
    dst = BK / p.name
    if not dst.exists():
        shutil.copy2(p, dst)
        print("backup:", p.name)

# 2) 合并回填数据
bf = json.loads((PV / "canonical/event_clusters.json").read_text(encoding="utf-8"))
cur = json.loads((ROOT / "data/canonical/event_clusters.json").read_text(encoding="utf-8"))
cur_items = cur.get("items", [])
bf_ids = {e["event_id"] for e in bf.get("items", [])}
cur_ids = {e.get("event_id") for e in cur_items}
print("existing canonical:", len(cur_items), "| backfill:", len(bf["items"]), "| overlap:", len(cur_ids & bf_ids))
merged = cur_items + [e for e in bf["items"] if e["event_id"] not in cur_ids]
(ROOT / "data/canonical/event_clusters.json").write_text(
    json.dumps({"items": merged, "meta": cur.get("meta", {})}, ensure_ascii=False, indent=1) + "\n",
    encoding="utf-8")
print("merged canonical:", len(merged))

bdf = json.loads((PV / "disease/canonical/outbreak_events.json").read_text(encoding="utf-8"))
cd = json.loads((ROOT / "data/disease/canonical/outbreak_events.json").read_text(encoding="utf-8"))
cd_items = cd.get("items", [])
dbf_ids = {d["disease_event_id"] for d in bdf.get("items", [])}
dcur_ids = {d.get("disease_event_id") for d in cd_items}
merged_d = cd_items + [d for d in bdf["items"] if d["disease_event_id"] not in dcur_ids]
(ROOT / "data/disease/canonical/outbreak_events.json").write_text(
    json.dumps({"items": merged_d, "meta": cd.get("meta", {})}, ensure_ascii=False, indent=1) + "\n",
    encoding="utf-8")
print("merged disease:", len(merged_d))

# 2b) events.json（静态白名单文件）合并回填事件（build 后恢复）
evp = ROOT / "data/events.json"
ev = json.loads(evp.read_text(encoding="utf-8"))
ev_ids = {e["event_id"] for e in ev.get("events", [])}
added_ev = 0
for it in bf["items"]:
    if it["event_id"] in ev_ids:
        continue
    ev["events"].append({
        "event_id": it["event_id"], "title_cn": it.get("title_cn"),
        "title_original": it.get("title_original"), "summary_cn": it.get("summary_cn"),
        "country": it.get("country_cn"), "country_cn": it.get("country_cn"),
        "country_iso3": it.get("country_iso3"), "event_type": it.get("event_type"),
        "event_severity": it.get("event_severity"), "event_time": it.get("event_time"),
        "published_time": it.get("event_time"),
        "china_related": bool(it.get("china_related")), "china_interest": it.get("china_interest"),
        "verification_status": it.get("verification_level"),
        "verification_label_cn": it.get("verification_label_cn"),
        "independent_source_count": it.get("independent_source_count"),
        "source_url": (it.get("source_urls") or [None])[0],
        "source_name": (it.get("source_groups") or [None])[0],
        "location": it.get("location_name"), "importance_score": it.get("importance_score"),
        "current_policy_passed": True, "quality_gate_passed": True, "is_demo": False,
        "created_at": it.get("created_at"), "updated_at": it.get("updated_at"),
        "ingestion_mode": "historical_backfill",
        "backfill_batch_id": "asip-backfill-20260818-20260827",
    })
    added_ev += 1
ev["note"] = (ev.get("note") or "") + " [backfill preview: +%d events]" % added_ev
evp.write_text(json.dumps(ev, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("events.json merged: +%d (total %d)" % (added_ev, len(ev["events"])))

# 3) timelines
import sys as _sys
_sys.path.insert(0, str(ROOT))
from scripts.ops import timeline_run as tr  # noqa: E402
r = tr.build_timelines(data_dir=str(ROOT / "data"))
print("timelines:", r)

# 4) build_site
out = subprocess.run([PY, "scripts/build_site.py"], cwd=str(ROOT), capture_output=True, text=True)
print(out.stdout.strip().splitlines()[-3:])
if out.returncode != 0:
    print("BUILD_STDERR:", out.stderr[-1500:])
    sys.exit(1)

# 5) 恢复 tracked 文件
for p in TRACKED:
    subprocess.run(["git", "checkout", "--", str(p.relative_to(ROOT))], cwd=str(ROOT), check=True)
    print("restored:", p.name)

# 6) 生成 preview 副本
pv_dist = ROOT / "preview_dist_backfill"
shutil.rmtree(pv_dist, ignore_errors=True)
shutil.copytree(ROOT / ".dist_new", pv_dist)
print("PREVIEW_DIST:", pv_dist)
