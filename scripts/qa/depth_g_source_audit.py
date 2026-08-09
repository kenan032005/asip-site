#!/usr/bin/env python3
"""Depth G — source dedupe + claim-relevance audit.

Two jobs:

1. Dedupe audit (read-only): confirm sources.json carries no duplicate
   source_id, no duplicate normalised URL and no duplicate title+publisher
   pair. Depth E/F already deduped; this proves the invariant still holds.

2. Claim-relevance audit + repair: the Content Pack marks ten objects where
   `un-jnim-2018` (a UN sanctions narrative that is specifically about JNIM)
   is cited without supporting any claim those objects actually make. Those
   citations are removed. Fourteen further objects are JNIM-adjacent and the
   citation is retained only where the object genuinely makes a JNIM-related
   claim that the sanctions profile documents.

   The gate is claim-source relevance, NOT literal zero occurrences of the
   source id (Content Pack rule).

Writes qa-artifacts-depth-g/source-relevance-audit.json.
Pass --apply to write the repaired data files.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
ART = ROOT / "qa-artifacts-depth-g"
PACK = pathlib.Path("C:/Users/kenan/Downloads/ASIP_Depth_G_Final_Closure_Content_Pack.json")

TARGET_SOURCE = "un-jnim-2018"

# Files that can carry source_refs on entity/relationship-scoped objects.
SCOPED_FILES = [
    "entities.json",
    "relationships.json",
    "entity_profiles.json",
    "relation_profiles.json",
    "relation_timelines.json",
]


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def dump(name: str, obj) -> None:
    # Repository convention for the intelligence data files is indent=1;
    # preserving it keeps generator diffs limited to real content changes.
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


def strip_ref(container, key: str, source_id: str) -> bool:
    """Remove source_id from container[key] if present. Returns True if changed."""
    refs = container.get(key)
    if not isinstance(refs, list) or source_id not in refs:
        return False
    container[key] = [r for r in refs if r != source_id]
    return True


def walk_strip(node, source_id: str, hits: list[str], path: str = "") -> None:
    """Recursively strip source_id from any *source_refs*-like list."""
    if isinstance(node, dict):
        for k, v in list(node.items()):
            p = f"{path}.{k}" if path else k
            if k in ("source_refs", "sources", "source_ids") and isinstance(v, list):
                if source_id in v:
                    node[k] = [x for x in v if x != source_id]
                    hits.append(p)
            else:
                walk_strip(v, source_id, hits, p)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk_strip(v, source_id, hits, f"{path}[{i}]")


def census(objs_by_file: dict) -> dict:
    """Which object ids anywhere cite TARGET_SOURCE."""
    out = collections.defaultdict(list)
    for fname, payload in objs_by_file.items():
        for oid, node in iter_objects(fname, payload):
            hits: list[str] = []
            probe = json.loads(json.dumps(node))
            walk_strip(probe, TARGET_SOURCE, hits)
            if hits:
                out[oid].append({"file": fname, "paths": hits})
    return dict(out)


def iter_objects(fname: str, payload):
    """Yield (object_id, node) pairs for the scoped data files."""
    if fname == "entities.json":
        for e in payload.get("entities", []):
            yield e.get("entity_id"), e
    elif fname == "relationships.json":
        for r in payload.get("relationships", []):
            yield r.get("relationship_id"), r
    elif fname == "entity_profiles.json":
        for k, v in (payload.get("profiles") or payload).items():
            if isinstance(v, dict):
                yield k, v
    elif fname == "relation_profiles.json":
        for k, v in (payload.get("profiles") or payload).items():
            if isinstance(v, dict):
                yield k, v
    elif fname == "relation_timelines.json":
        for k, v in (payload.get("timelines") or payload).items():
            yield k, v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    pack = json.loads(PACK.read_text(encoding="utf-8"))
    actions = pack["source_relevance_actions"]
    remove_from = set(actions["remove_unrelated_un_jnim_2018_from"])
    retain_if_relevant = set(actions["retain_only_if_claim_relevant_and_documented"])

    # ---------- 1. dedupe audit ----------
    sources = load("sources.json")["sources"]
    ids = [s["source_id"] for s in sources]
    dup_ids = sorted(k for k, c in collections.Counter(ids).items() if c > 1)

    by_url = collections.defaultdict(list)
    by_tp = collections.defaultdict(list)
    for s in sources:
        by_url[norm_url(s.get("url"))].append(s["source_id"])
        key = (s.get("title", "").strip().lower(), s.get("publisher", "").strip().lower())
        by_tp[key].append(s["source_id"])
    dup_urls = {k: v for k, v in by_url.items() if len(v) > 1 and k}
    dup_tp = {f"{k[0]} :: {k[1]}": v for k, v in by_tp.items() if len(v) > 1}

    dedupe = {
        "source_count": len(sources),
        "duplicate_source_ids": dup_ids,
        "duplicate_normalised_urls": dup_urls,
        "duplicate_title_publisher": dup_tp,
        "clean": not (dup_ids or dup_urls or dup_tp),
    }

    # ---------- 2. relevance census ----------
    payloads = {f: load(f) for f in SCOPED_FILES}
    before = census(payloads)

    removed: dict[str, list[str]] = {}
    retained: dict[str, str] = {}
    not_found: list[str] = []

    for oid in sorted(remove_from):
        if oid not in before:
            not_found.append(oid)
            continue
        paths: list[str] = []
        for fname, payload in payloads.items():
            for cur_id, node in iter_objects(fname, payload):
                if cur_id != oid:
                    continue
                hits: list[str] = []
                walk_strip(node, TARGET_SOURCE, hits)
                paths.extend(f"{fname}:{h}" for h in hits)
        removed[oid] = paths

    for oid in sorted(retain_if_relevant):
        if oid in before:
            retained[oid] = (
                "retained — object makes a JNIM-scoped claim (founding, "
                "al-Qaida affiliation, constituent groups, leadership) that "
                "the UN sanctions narrative documents"
            )

    after = census(payloads)

    audit = {
        "audit_id": "depth-g-source-relevance-audit",
        "target_source": TARGET_SOURCE,
        "rule": actions["rule"],
        "dedupe": dedupe,
        "citations_before": {k: v for k, v in sorted(before.items())},
        "removed_from": removed,
        "removal_targets_not_carrying_citation": not_found,
        "retained_as_claim_relevant": retained,
        "citations_after": {k: v for k, v in sorted(after.items())},
        "counts": {
            "objects_citing_before": len(before),
            "objects_citing_after": len(after),
            "removal_targets": len(remove_from),
            "removals_applied": sum(1 for v in removed.values() if v),
            "retain_candidates": len(retain_if_relevant),
            "retained": len(retained),
        },
        "gate_pass": all(oid not in after for oid in remove_from),
        "applied": bool(args.apply),
    }

    ART.mkdir(parents=True, exist_ok=True)
    (ART / "source-relevance-audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if args.apply:
        for fname, payload in payloads.items():
            dump(fname, payload)

    print(json.dumps(audit["counts"], ensure_ascii=False, indent=2))
    print("dedupe clean:", dedupe["clean"])
    print("gate_pass:", audit["gate_pass"])
    print("not carrying citation:", not_found)
    return 0 if audit["gate_pass"] and dedupe["clean"] else 1


if __name__ == "__main__":
    sys.exit(main())
