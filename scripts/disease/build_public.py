#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 疾病公开快照（§十八）。

- data/public/disease_events.json：Public disease ⊆ Disease Canonical；
- 内部审计/原始抓取/runtime 不得进入 dist；
- 公开只包含展示需要字段与来源 URL（不含 data_quality_flags 内部细节）。
"""

import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "data" / "disease" / "canonical" / "outbreak_events.json"
PUBLIC = ROOT / "data" / "public" / "disease_events.json"

# 公开白名单字段（§十八：只含展示需要 + 来源 URL）
PUBLIC_FIELDS = (
    "disease_event_id", "disease_id", "disease_name_en", "disease_name_zh",
    "pathogen", "country_iso3", "admin1", "admin2", "location_raw",
    "report_date", "event_start_date", "event_end_date",
    "confirmed_cases", "probable_cases", "suspected_cases", "total_cases",
    "deaths", "recoveries", "case_count_type", "case_period_start", "case_period_end",
    "outbreak_status", "update_type", "cross_border", "affected_countries",
    "source_links", "primary_source", "source_tier",
    "verification_status", "verification_confidence",
    "previous_event_id", "supersedes_event_id",
    "created_at", "updated_at",
)


def _bj_now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def build_public(canonical_path=None, public_path=None, dry_run=True):
    """从 Disease Canonical 生成 Public 快照（Public ⊆ Canonical 校验）。

    返回 (count, orphans, status)。
    """
    cp = Path(canonical_path) if canonical_path else CANONICAL
    pp = Path(public_path) if public_path else PUBLIC
    doc = json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else {"items": []}
    items = doc.get("items", [])
    ids = {it.get("disease_event_id") for it in items}

    public_items = []
    for it in items:
        pub = {k: it.get(k) for k in PUBLIC_FIELDS if k in it}
        # 公开快照仅保留 source_links 的 url/source_name/source_tier（不含内部字段）
        links = []
        for l in (it.get("source_links") or []):
            links.append({k: l.get(k) for k in ("url", "source_id", "source_name", "source_tier") if k in l})
        pub["source_links"] = links
        public_items.append(pub)

    orphans = [eid for eid in ids if eid not in {p.get("disease_event_id") for p in public_items}]
    out = {
        "schema_version": "1.0.0",
        "pipeline_version": "disease-v1",
        "updated_at": _bj_now(),
        "source_canonical": str(cp.relative_to(ROOT)) if str(cp).startswith(str(ROOT)) else "disease canonical",
        "items": public_items,
    }
    if not dry_run:
        pp.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(pp.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
            os.replace(tmp, pp)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
    return len(public_items), orphans, "written" if not dry_run else "dry-run"
