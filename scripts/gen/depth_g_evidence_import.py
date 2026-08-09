#!/usr/bin/env python3
"""Depth G — import the 18 packet sources and 15 packet evidence claims.

The packet expresses evidence with a `source_ids` list; the repository schema
uses a single `source_id` per evidence record. A packet claim citing N sources
is therefore materialised as N evidence records sharing one claim_id, which
preserves the existing schema instead of mutating it.

Sources already present (by id or by normalised URL) are not duplicated.

Writes qa-artifacts-depth-g/evidence-import-report.json.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
ART = ROOT / "qa-artifacts-depth-g"
PACK = pathlib.Path("C:/Users/kenan/Downloads/ASIP_Depth_G_Final_Closure_Content_Pack.json")

TODAY = "2026-08-09"


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def dump(name: str, obj) -> None:
    (DATA / name).write_text(
        json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def norm_url(u: str | None) -> str:
    u = (u or "").strip().lower().rstrip("/")
    for p in ("https://", "http://"):
        if u.startswith(p):
            u = u[len(p):]
    if u.startswith("www."):
        u = u[4:]
    return u


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    pack = json.loads(PACK.read_text(encoding="utf-8"))

    sources_doc = load("sources.json")
    sources = sources_doc["sources"]
    ev_doc = load("evidence_records.json")
    evidence = ev_doc["evidence"]

    ent_ids = {e["entity_id"] for e in load("entities.json")["entities"]}
    rel_ids = {r["relationship_id"] for r in load("relationships.json")["relationships"]}

    by_id = {s["source_id"] for s in sources}
    by_url = {norm_url(s.get("url")): s["source_id"] for s in sources if s.get("url")}

    added_sources: list[str] = []
    skipped_sources: list[dict] = []
    alias: dict[str, str] = {}

    for s in pack["sources"]:
        sid = s["source_id"]
        u = norm_url(s.get("url"))
        if sid in by_id:
            skipped_sources.append({"source_id": sid, "reason": "id already present"})
            continue
        if u and u in by_url:
            # Same document already in the library under another id: reuse it
            # rather than creating a duplicate record.
            alias[sid] = by_url[u]
            skipped_sources.append({
                "source_id": sid,
                "reason": "duplicate URL",
                "aliased_to": by_url[u],
            })
            continue
        rec = dict(s)
        rec.setdefault("accessed_at", TODAY)
        rec.setdefault("notes", "")
        rec["imported_by"] = "depth-g-final-closure"
        sources.append(rec)
        by_id.add(sid)
        if u:
            by_url[u] = sid
        added_sources.append(sid)

    # ---------------- evidence ----------------
    existing_claims = {e.get("claim_id") for e in evidence}
    existing_ev_ids = {e.get("evidence_id") for e in evidence}
    added_evidence: list[str] = []
    skipped_evidence: list[dict] = []
    unresolved: list[dict] = []

    for claim in pack["evidence"]:
        cid = claim["claim_id"]
        if cid in existing_claims:
            skipped_evidence.append({"claim_id": cid, "reason": "claim already present"})
            continue

        eids = [e for e in claim.get("entity_ids", []) if e in ent_ids]
        rids = [r for r in claim.get("relation_ids", []) if r in rel_ids]
        bad_e = [e for e in claim.get("entity_ids", []) if e not in ent_ids]
        bad_r = [r for r in claim.get("relation_ids", []) if r not in rel_ids]
        if bad_e or bad_r:
            unresolved.append({"claim_id": cid, "unknown_entities": bad_e, "unknown_relations": bad_r})

        src_list = [alias.get(s, s) for s in claim.get("source_ids", [])]
        src_list = [s for s in src_list if s in by_id]
        if not src_list:
            unresolved.append({"claim_id": cid, "reason": "no resolvable source"})
            continue

        for i, sid in enumerate(src_list, start=1):
            n = len(existing_ev_ids) + 1
            eid = f"ev-depthg-{cid.split('-')[-1]}-{i}"
            while eid in existing_ev_ids:
                n += 1
                eid = f"ev-depthg-{cid.split('-')[-1]}-{i}-{n}"
            src = next((s for s in sources if s["source_id"] == sid), {})
            rec = {
                "evidence_id": eid,
                "claim_id": cid,
                "claim_text_zh": claim["claim"],
                "claim_type": "fact",
                "entity_ids": eids,
                "relation_ids": rids,
                "country_ids": [],
                "region_ids": [],
                "source_id": sid,
                "source_locator": src.get("title", ""),
                "as_of_date": src.get("published_at") or TODAY,
                "confidence": "high" if src.get("reliability") == "authoritative" else "medium",
                "disputed": False,
                "verification_status": claim.get("verification_status", "verified"),
                "verified_at": TODAY,
                "record_created_at": TODAY,
                "record_updated_at": TODAY,
                "record_reviewed_at": TODAY,
                "source_published_at": src.get("published_at"),
                "source_accessed_at": src.get("accessed_at", TODAY),
                "claim_valid_as_of": src.get("published_at") or TODAY,
                "freshness_status": "current",
                "evidence_origin": "depth_g_final_closure",
                "verification_method": (
                    "Depth G Content Pack claim mapped to its cited source record; "
                    "the packet is the authoritative factual reference for this round."
                ),
            }
            evidence.append(rec)
            existing_ev_ids.add(eid)
            added_evidence.append(eid)
        existing_claims.add(cid)

    report = {
        "import_id": "depth-g-evidence-import",
        "applied_at": TODAY,
        "sources": {
            "packet_count": len(pack["sources"]),
            "added": added_sources,
            "skipped": skipped_sources,
            "aliases": alias,
            "total_after": len(sources),
        },
        "evidence": {
            "packet_claims": len(pack["evidence"]),
            "records_added": added_evidence,
            "skipped": skipped_evidence,
            "unresolved": unresolved,
            "total_after": len(evidence),
        },
    }

    ART.mkdir(parents=True, exist_ok=True)
    (ART / "evidence-import-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if args.apply:
        sources_doc["generated_at"] = TODAY
        ev_doc["generated_at"] = TODAY
        dump("sources.json", sources_doc)
        dump("evidence_records.json", ev_doc)

    print(f"sources  added {len(added_sources)} skipped {len(skipped_sources)} total {len(sources)}")
    print(f"evidence added {len(added_evidence)} skipped {len(skipped_evidence)} total {len(evidence)}")
    print(f"unresolved: {unresolved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
