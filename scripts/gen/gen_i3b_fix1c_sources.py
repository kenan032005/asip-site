# -*- coding: utf-8 -*-
"""I3-B-Fix-1C mechanical source/evidence application.
Uses only the user-approved correction manifest; no network research.
"""
import json
import sys
from pathlib import Path

REPO = Path(sys.argv[1])
MANIFEST = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(r"C:/Users/kenan/Downloads/ASIP_I3B_Fix1B_Correction_Manifest.json")
DATA = REPO / "data" / "intelligence" / "africa"
REVIEWED = "2026-08-07"

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
sources_doc = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
evidence_doc = json.loads((DATA / "evidence_records.json").read_text(encoding="utf-8"))

sources = sources_doc["sources"]
by_url = {s.get("url"): s for s in sources if s.get("url")}
by_title = {(s.get("publisher"), s.get("title"), s.get("published_at")): s for s in sources}
source_map = {}
for key, candidate in manifest["source_candidates"].items():
    existing = by_url.get(candidate["url"]) or by_title.get((candidate["publisher"], candidate["title"], candidate["published_at"]))
    if existing:
        source_map[key] = existing["source_id"]
        continue
    record = {
        "source_id": key,
        "title": candidate["title"],
        "publisher": candidate["publisher"],
        "source_type": "manifest_candidate",
        "url": candidate["url"],
        "published_at": candidate["published_at"],
        "accessed_at": REVIEWED,
        "notes": "I3-B-Fix-1C mechanical manifest source candidate; no independent research performed.",
    }
    sources.append(record)
    by_url[record["url"]] = record
    by_title[(record["publisher"], record["title"], record["published_at"])] = record
    source_map[key] = key

# Exact evidence claim replacements. Empty entries intentionally mean the
# correction is profile/generator scoped and has no unambiguous evidence row.
evidence_updates = {
    "cl-i3b-cameroon-vp-2026": ("2026年4月，喀麦隆通过宪法修正重新设置副总统职位，由总统任免并承担法定继任功能。截至2026年7月22日，该职位仍未填补；网络流传的任命文件已被事实核查认定为伪造。", "verified", "2026-07-22"),
    "cl-i3a-niamey-attack": ("2026年1月29日尼亚美机场及空军基地101遭袭；公开报道对武器使用说法不一致，可能涉及迫击炮、火箭推进榴弹或装载爆炸物的无人机。", "partially_verified", "2026-01-30"),
    "cl-i3a-chad-may-2026": ("2026年5月4日Barka Tolorom基地遭袭，公开报道军方死亡约23至24人；5月6日另一支湖区巡逻力量遭伏击，两名将军死亡。两起事件应分开记录。", "verified", "2026-05-07"),
    "cl-i3a-libya-elections-2027": ("2026年6月UNSMIL结构化对话完成最终建议，目标是创造举行全国性选举的条件；现有公开材料没有形成确定的2027年全国总统和议会选举时间表。", "verified", "2026-07-06"),
    "cl-i3a-moz-total-2025": ("Mozambique LNG联合体于2025年11月7日决定解除2021年宣布的不可抗力；TotalEnergies于2026年1月29日与莫桑比克政府宣布项目陆上和海上活动全面重启。", "verified", "2026-01-29"),
    "cl-i3b-burkina-jnim-control": ("不同来源对布基纳法索领土控制与争夺范围的估计差异显著，不能将争夺区或国家力量无法自由行动区直接等同于JNIM单独控制区。", "partially_verified", "2025-08-26"),
    "cl-i3b-ethiopia-ola-2024": ("2024年12月OLA分裂派与政府签署有限和平协议，主流派拒绝协议并继续武装行动；公开资料仅支持不同力量之间可能存在接触或战术协调，不足以确认OLA与TPLF已形成稳定、正式的联盟关系。", "partially_verified", "2026-08-07"),
}
changed = []
for ev in evidence_doc["evidence"]:
    claim_id = ev.get("claim_id")
    if claim_id not in evidence_updates:
        continue
    text, status, asof = evidence_updates[claim_id]
    ev["claim_text_zh"] = text
    ev["verification_status"] = status
    ev["claim_valid_as_of"] = asof
    ev["as_of_date"] = asof
    ev["source_accessed_at"] = REVIEWED
    ev["record_updated_at"] = REVIEWED
    if status == "verified":
        ev["verified_at"] = REVIEWED
    else:
        ev["verified_at"] = None
    changed.append(claim_id)

sources_doc["generated_at"] = REVIEWED
evidence_doc["generated_at"] = REVIEWED
(DATA / "sources.json").write_text(json.dumps(sources_doc, ensure_ascii=False, indent=1), encoding="utf-8")
(DATA / "evidence_records.json").write_text(json.dumps(evidence_doc, ensure_ascii=False, indent=1), encoding="utf-8")
print("manifest source candidates:", len(manifest["source_candidates"]))
print("sources added/reused:", len(source_map), "added:", len(sources) - (len(sources) - sum(1 for s in sources if s.get("source_id") in manifest["source_candidates"])))
print("evidence rows changed:", len(changed), changed)
