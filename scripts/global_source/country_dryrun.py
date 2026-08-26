#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Country Source Layer — 真实 Dry-run（§十三/§十四/§二，Source Expansion B）。

- 5 国（TCD/NER/SSD/BEN/ETH）全部尝试；
- listing → candidate（country filter + topic classify + opinion 标记）→ dedup；
- detail extraction（每 source 2-3 篇）；
- stable source 计算（§十五）；
- 只写 data/runtime/ internal audit；不写 Canonical/Public。
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.global_source.registry import load_country_registry
from scripts.global_source.adapters import collect_source
from scripts.global_source.candidates import new_candidate, dedup_candidates
from scripts.global_source.africa_filter import country_hints
from scripts.global_source.topic_filter import classify_candidate
from scripts.global_source.detail import detail_extract
from scripts.global_source.health import record_health

AUDIT_PATH = ROOT / "data" / "runtime" / "country_discovery_audit.json"
DETAIL_PER_SOURCE = 3


def _iso2_of(iso3):
    return {"TCD": "TD", "NER": "NE", "SSD": "SS", "BEN": "BJ", "ETH": "ET"}.get(iso3)


def _country_filter_required(source):
    return bool(source.get("country_filter_required", False))


def _country_aliases(iso3):
    from scripts.global_source.africa_filter import AFRICA_COUNTRY_ALIASES
    iso2 = _iso2_of(iso3)
    return AFRICA_COUNTRY_ALIASES.get(iso2, [iso3.lower()])


def run_country_dryrun(max_items=25, detail_per_source=DETAIL_PER_SOURCE):
    sources, errors = load_country_registry()
    if errors:
        return None, {"registry_errors": errors}
    run_id = time.strftime("CRUN%Y%m%dT%H%M%S+0800")
    per_country = {}
    all_cands = []
    healths = []
    stable_map = {}
    detail_results = {}
    last_detail_success = {}

    for src in sources:
        sid = src["source_id"]
        iso3 = src.get("country_iso3")
        enabled = src.get("enabled", True)
        if enabled is False:
            continue
        per_country.setdefault(iso3, {"sources_attempted": 0, "listing_success": 0,
                                      "listing_failed": 0, "items": 0,
                                      "security": 0, "disease": 0,
                                      "duplicates": 0})
        pc = per_country[iso3]
        pc["sources_attempted"] += 1
        items, health = collect_source(src, max_items=max_items)
        health["country_iso3"] = iso3
        health["scope"] = "country"
        healths.append(health)
        if health["listing_status"] != "success":
            pc["listing_failed"] += 1
            stable_map[sid] = False
            continue

        cands = []
        for it in items:
            it["country_hints"] = country_hints(
                " ".join([str(it.get("title") or ""), str(it.get("url") or "")]))
            c = new_candidate(src, it)
            if not c:
                continue
            c["country_iso3"] = iso3
            c["role"] = src.get("role")
            c["topic_scope"] = src.get("topic_scope")
            # 栏目过滤（ActuNiger：排除 Sport/Culture 低价值栏目）
            if sid == "ner_actuniger":
                blob = " ".join([str(c.get("title") or ""),
                                 str(c.get("url") or "")]).lower()
                if any(kw in blob for kw in ("sport", "culture", "societe-culture")):
                    c["status"] = "filtered_low_value_section"
                    continue
            # country filter（仅标记源，如 Alwihda 泛非洲站）
            if _country_filter_required(src):
                blob = " ".join([str(c.get("title") or ""), str(c.get("url") or "")]).lower()
                if not any(a in blob for a in _country_aliases(iso3)):
                    c["status"] = "filtered_non_country"
                    continue
            c = classify_candidate(c)
            cands.append(c)
        cands, dup = dedup_candidates(cands)
        if health["listing_status"] == "success" and cands:
            pc["listing_success"] += 1
        else:
            pc["listing_failed"] += 1
        pc["items"] += len(cands)
        pc["duplicates"] += dup
        pc["security"] += sum(1 for c in cands if c.get("chain") == "social")
        pc["disease"] += sum(1 for c in cands if c.get("chain") == "disease")
        all_cands.extend(cands)

        # detail extraction（每 source 最多 N 篇）
        if cands:
            ok_detail, fail_detail = 0, []
            last_ok = None
            for c in cands[:detail_per_source]:
                d = detail_extract(c.get("url") or "", sid,
                                   language_hint=src.get("language", [""])[0])
                if d["detail_success"]:
                    ok_detail += 1
                    last_ok = d["canonical_url"] or c.get("url")
                else:
                    fail_detail.append((c.get("url"), d["failure_type"]))
            detail_results[sid] = {"success": ok_detail, "failed": len(fail_detail),
                                   "failures": fail_detail}
            if last_ok:
                last_detail_success[sid] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")

        # §十五 stable：listing_success + item + detail 成功（或明确 detail strategy）
        stable = (health["listing_status"] == "success" and bool(cands) and
                  (detail_results.get(sid, {}).get("success", 0) > 0 or
                   src.get("detail_strategy") not in (None, "none")))
        stable_map[sid] = stable

    record_health(healths, latest_items={
        sid: max([c.get("published_at") or "" for c in all_cands
                  if c["source_id"] == sid] or [None]) for sid in set(c["source_id"]
                                                                      for c in all_cands)
    }, scope="country", country_iso3=None, stable=stable_map,
        last_detail=last_detail_success)

    stats = {
        "run_id": run_id,
        "per_country": per_country,
        "total_sources": len(sources),
        "sources_attempted": sum(p["sources_attempted"] for p in per_country.values()),
        "listing_success": sum(p["listing_success"] for p in per_country.values()),
        "listing_failed": sum(p["listing_failed"] for p in per_country.values()),
        "items_discovered": len(all_cands),
        "security_candidates": sum(1 for c in all_cands if c.get("chain") == "social"),
        "disease_candidates": sum(1 for c in all_cands if c.get("chain") == "disease"),
        "opinion_tagged": sum(1 for c in all_cands if c.get("content_type")),
        "stable_sources": sum(1 for v in stable_map.values() if v),
        "stable_by_country": {},
        "detail": detail_results,
    }
    for src in sources:
        sid = src["source_id"]
        iso3 = src.get("country_iso3")
        if stable_map.get(sid):
            stats["stable_by_country"].setdefault(iso3, []).append(sid)

    audit = {"stats": stats, "candidates": all_cands}
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    return {"run_id": run_id, "stats": stats, "candidates": all_cands,
            "stable_map": stable_map, "healths": healths}, None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Country Source Layer dry-run")
    ap.add_argument("--max-items", type=int, default=25)
    ap.add_argument("--no-detail", action="store_true",
                    help="跳过 detail extraction（仅 listing 验证）")
    args = ap.parse_args(argv)

    res, err = run_country_dryrun(max_items=args.max_items,
                                  detail_per_source=0 if args.no_detail else DETAIL_PER_SOURCE)
    if err:
        print("errors:", err)
        return 2
    stats = res["stats"]
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print("audit written: %s" % AUDIT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
