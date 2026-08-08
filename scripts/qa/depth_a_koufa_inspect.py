#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect Koufa entity/relation current state + any death-phrasing variants."""
import json
from pathlib import Path

P = Path("C:/Users/kenan/WorkBuddy/clean/asip-intelligence-depth-a/data/intelligence/africa")
entities = {e["entity_id"]: e for e in json.load(open(P / "entities.json", encoding="utf-8"))["entities"]}
ep = json.load(open(P / "entity_profiles.json", encoding="utf-8"))["profiles"]
rels = {r["relationship_id"]: r for r in json.load(open(P / "relationships.json", encoding="utf-8"))["relationships"]}
rp = json.load(open(P / "relation_profiles.json", encoding="utf-8"))["profiles"]

k = entities["person-amadou-koufa"]
print("KOUFA entity:", {x: k.get(x) for x in ("current_status", "claim_valid_as_of", "freshness_status", "country_ids", "source_refs")})
pr = ep["person-amadou-koufa"]
secs = pr.get("sections", {})
for key in ("current_assessment", "current_situation", "history", "controversies_uncertainties"):
    if secs.get(key):
        print(f"--- {key} ---")
        print(str(secs[key])[:400])
print("profile_depth:", pr.get("profile_depth"), "| content_maturity:", pr.get("content_maturity"))

for rid in ("rel-koufa-jnim-senior", "rel-koufa-katiba-founder", "rel-koufa-iyad-network"):
    r = rels.get(rid)
    print("\nREL", rid, "::", r.get("relationship_type"), "|", r.get("current_status"), "|", r.get("claim_valid_as_of"))
    print("  summary:", r.get("relation_summary", "")[:200])
    print("  profile exists:", rid in rp, "| timeline:", len(json.load(open(P / "relation_timelines.json", encoding="utf-8"))["timelines"].get(rid, [])))

# death variants search
variants = ["死亡", "击毙", "阵亡", "deceased", "killed", "继任", "继任指挥官"]
blob = json.dumps({**ep["person-amadou-koufa"], **rels.get("rel-koufa-jnim-senior", {}), **rels.get("rel-koufa-katiba-founder", {}), **rels.get("rel-koufa-iyad-network", {})}, ensure_ascii=False)
print("\nKoufa death-variant hits:", [v for v in variants if v in blob])

# is-sahel / mourabitoun checks
iss = entities["actor-is-sahel"]
print("\nIS-Sahel current_status:", iss.get("current_status"), "| claim:", iss.get("claim_valid_as_of"))
print("IS-Sahel profile sections keys:", list(ep["actor-is-sahel"].get("sections", {}).keys()))
am = entities["actor-al-mourabitoun"]
print("Al-Mourabitoun current_status:", am.get("current_status"), "| claim:", am.get("claim_valid_as_of"))
print("Al-Mourabitoun profile sections keys:", list(ep["actor-al-mourabitoun"].get("sections", {}).keys()))
# iyad-al-mourabitoun relation
iyad_rel = [r for r in json.load(open(P / "relationships.json", encoding="utf-8"))["relationships"] if r["source_entity_id"] == "person-iyad-ag-ghali" and r["target_entity_id"] == "actor-al-mourabitoun"]
print("Iyad->Mourabitoun relations:", [(r["relationship_id"], r["relationship_type"]) for r in iyad_rel])
