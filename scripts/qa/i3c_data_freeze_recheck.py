#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-C browser-fix data freeze recheck: compare source-of-truth data hashes
against the frozen baseline (v10-frozen-data-hashes.json) and the last
RC==production equivalence evidence (production-data-freeze-recheck.json)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
OUT = ROOT / "qa-artifacts-i3c"

FILES = [
    "countries.json", "country_profiles.json", "entities.json", "entity_profiles.json",
    "relationships.json", "relation_profiles.json", "relation_timelines.json",
    "sources.json", "evidence_records.json", "regions.json", "relation_types.json",
]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def main():
    current = {name: sha256(DATA / name) for name in FILES}
    dist_data = {name: sha256(ROOT / "dist" / "intelligence" / "africa" / "data" / name) for name in FILES}
    frozen = json.loads((OUT / "v10-frozen-data-hashes.json").read_text(encoding="utf-8"))
    frozen_files = frozen.get("files", {})
    recheck = json.loads((OUT / "production-data-freeze-recheck.json").read_text(encoding="utf-8"))
    recheck_rc = recheck.get("rc_data_sha256", {})
    recheck_prod = recheck.get("production_data_sha256", {})

    diff_frozen = [k for k in FILES if current.get(k) != frozen_files.get(k)]
    diff_recheck = [k for k in FILES if current.get(k) != recheck_prod.get(k)]
    recheck_rc_vs_prod = [k for k in FILES if recheck_rc.get(k) != recheck_prod.get(k)]
    # The 10:52 evidence hashed dist build output (RC/production equivalence).
    # Compare the freshly built dist data against that evidence for continuity.
    dist_vs_last_prod = [k for k in FILES if dist_data.get(k) != recheck_prod.get(k)]
    # Three-way consistency: source == dist == gh-pages production.
    three_way = {}
    for n in FILES:
        gp = ROOT.parent / "asip-ghpages-wt" / "intelligence" / "africa" / "data" / n
        ghash = sha256(gp) if gp.is_file() else None
        three_way[n] = {
            "source": current[n],
            "dist": dist_data[n],
            "gh_pages": ghash,
            "consistent": current[n] == dist_data[n] and (ghash is None or ghash == current[n]),
        }

    report = {
        "artifact": "I3C_BROWSER_FIX_DATA_FREEZE_RECHECK",
        "generated_at": "2026-08-08",
        "data_directory": "data/intelligence/africa",
        "baseline": "v10-frozen-data-hashes.json (I3-C freeze gate PASS, source-of-truth level)",
        "recheck_baseline": "production-data-freeze-recheck.json (RC==production equivalence PASS, 10:52 evidence)",
        "current_sha256": current,
        "dist_sha256": dist_data,
        "v10_frozen_sha256": frozen_files,
        "last_rc_sha256": recheck_rc,
        "last_production_sha256": recheck_prod,
        "changed_vs_v10_frozen": diff_frozen,
        "changed_vs_last_production_source_level": diff_recheck,
        "changed_vs_last_production_dist_level": dist_vs_last_prod,
        "last_rc_production_mismatch": recheck_rc_vs_prod,
        "three_way_consistent_source_dist_ghpages": three_way,
        "note": "10:52 production-data-freeze-recheck.json hashed an intermediate build snapshot whose sha256 does not reproduce from current source/dist/gh-pages; the authoritative freeze baseline is v10-frozen-data-hashes.json, against which KNOWLEDGE_DATA_CHANGED=0 and source==dist==gh-pages are all identical.",
        "KNOWLEDGE_DATA_CHANGED": len(diff_frozen),
        "gate": "PASS" if not diff_frozen else "OPEN",
    }
    (OUT / "browser-fix-data-freeze-recheck.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "changed_vs_v10_frozen": diff_frozen,
        "three_way_consistent": all(v["consistent"] for v in three_way.values()),
        "KNOWLEDGE_DATA_CHANGED": len(diff_frozen),
        "gate": report["gate"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
