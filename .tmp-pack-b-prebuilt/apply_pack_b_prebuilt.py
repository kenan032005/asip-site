#!/usr/bin/env python3
"""
Mechanical importer for ASIP Final Depth Consolidation Pack B prebuilt payload.

This script contains NO factual-content generation. It only imports user-provided
prebuilt JSON into the existing ASIP source-of-truth files.

Usage:
  python tools/apply_pack_b_prebuilt.py \
      --repo-root . \
      --package-dir /path/to/unzipped/package
"""
import argparse, json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def dump(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")

def norm_url(u):
    if not u:
        return ""
    p=urlsplit(u.strip())
    path=p.path.rstrip("/")
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, p.query, ""))

def merge_add_fields(target, patch, source_map=None):
    for k,v in patch.items():
        if k.endswith("_add"):
            base=k[:-4]
            cur=target.get(base, [])
            if not isinstance(cur, list):
                raise TypeError(f"{base} is not list on {target.get('entity_id')}")
            for item in v:
                # Mechanical source-id remap (dedup) applies to _add lists too.
                if source_map and base in ("source_refs", "source_ids"):
                    item = source_map.get(item, item)
                if item not in cur:
                    cur.append(item)
            target[base]=cur
        else:
            target[k]=v

def remap_source_refs(obj, source_map):
    if isinstance(obj, dict):
        for k,v in list(obj.items()):
            if k in ("source_id",):
                if isinstance(v,str) and v in source_map:
                    obj[k]=source_map[v]
            elif k in ("source_refs","source_ids"):
                if isinstance(v,list):
                    obj[k]=[source_map.get(x,x) for x in v]
            else:
                remap_source_refs(v, source_map)
    elif isinstance(obj, list):
        for x in obj:
            remap_source_refs(x, source_map)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--package-dir", required=True)
    args=ap.parse_args()
    root=Path(args.repo_root).resolve()
    pkg=Path(args.package_dir).resolve()
    data=root/"data/intelligence/africa"

    support=load(pkg/"ASIP-PACK-B-PREBUILT-SUPPORTING-DATA.json")
    profiles={}
    for n in (1,2,3):
        profiles.update(load(pkg/f"ASIP-PACK-B-PREBUILT-ENTITY-PROFILES-{n}.json")["profiles"])
    if len(profiles)!=11:
        raise SystemExit(f"Expected 11 profiles, got {len(profiles)}")

    entities_doc=load(data/"entities.json")
    entity_profiles_doc=load(data/"entity_profiles.json")
    sources_doc=load(data/"sources.json")
    evidence_doc=load(data/"evidence_records.json")
    rels_doc=load(data/"relationships.json")
    rel_profiles_doc=load(data/"relation_profiles.json")

    entities=entities_doc["entities"]
    by_eid={x["entity_id"]:x for x in entities}

    # Upsert sources, dedup mechanically by normalized URL (build source_map first
    # so entity-record _add source refs can be remapped during the merge below).
    existing_sources=sources_doc["sources"]
    by_url={norm_url(s.get("url")):s for s in existing_sources if s.get("url")}
    by_sid={s["source_id"]:s for s in existing_sources}
    source_map={}
    for s in support["source_additions"]:
        s=dict(s)
        s.setdefault("imported_by","final-depth-consolidation-pack-b")
        nu=norm_url(s.get("url"))
        if nu and nu in by_url:
            source_map[s["source_id"]]=by_url[nu]["source_id"]
            continue
        sid=s["source_id"]
        if sid in by_sid:
            # Same ID is safe only if URL normalizes identically.
            if norm_url(by_sid[sid].get("url")) != nu:
                raise ValueError(f"Source ID collision with different URL: {sid}")
            source_map[sid]=sid
            continue
        existing_sources.append(s)
        by_sid[sid]=s
        if nu: by_url[nu]=s
        source_map[sid]=sid

    # Merge entity-record field patches (with source remap available).
    for eid,patch in support["entity_record_patches"].items():
        if eid not in by_eid:
            raise KeyError(f"Missing entity {eid}")
        merge_add_fields(by_eid[eid], patch, source_map)

    # Remap all source references before storing.
    remap_source_refs(support, source_map)
    remap_source_refs(profiles, source_map)

    # Replace 11 profiles exactly.
    ep=entity_profiles_doc["profiles"]
    for eid,p in profiles.items():
        if eid not in by_eid:
            raise KeyError(f"Profile target missing entity {eid}")
        ep[eid]=p

    # Append evidence by evidence_id.
    evidence=evidence_doc["evidence"]
    by_ev={x["evidence_id"]:x for x in evidence}
    for e in support["evidence_additions"]:
        eid=e["evidence_id"]
        if eid in by_ev:
            raise ValueError(f"Evidence already exists: {eid}")
        evidence.append(e)
        by_ev[eid]=e
    for evid,patch in support.get("evidence_updates",{}).items():
        if evid not in by_ev:
            raise KeyError(f"Evidence update target missing: {evid}")
        merge_add_fields(by_ev[evid], patch)

    # Add only the supplied relationships.
    rels=rels_doc["relationships"]
    by_rel={x["relationship_id"]:x for x in rels}
    for r in support["relationship_additions"]:
        rid=r["relationship_id"]
        if rid in by_rel:
            raise ValueError(f"Relationship already exists: {rid}")
        rels.append(r)
        by_rel[rid]=r

    rp=rel_profiles_doc["profiles"]
    for rid,p in support["relation_profile_additions"].items():
        if rid in rp:
            raise ValueError(f"Relation profile already exists: {rid}")
        rp[rid]=p

    dump(data/"entities.json", entities_doc)
    dump(data/"entity_profiles.json", entity_profiles_doc)
    dump(data/"sources.json", sources_doc)
    dump(data/"evidence_records.json", evidence_doc)
    dump(data/"relationships.json", rels_doc)
    dump(data/"relation_profiles.json", rel_profiles_doc)

    print("PACK_B_PREBUILT_IMPORT_APPLIED")
    print("profiles=11")
    print(f"sources_requested={len(support['source_additions'])}")
    print(f"evidence_added={len(support['evidence_additions'])}")
    print(f"relationships_added={len(support['relationship_additions'])}")

if __name__=="__main__":
    main()
