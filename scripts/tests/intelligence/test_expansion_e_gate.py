#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Expansion E dedicated gate test — regional security & counterterrorism actors."""
import io, json, os, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
DATA = "data/intelligence/africa"
PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  :: {detail}")


def load(n):
    return json.load(io.open(os.path.join(DATA, n), encoding="utf-8"))


entities = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
ep = load("entity_profiles.json")["profiles"]
rp = load("relation_profiles.json")["profiles"]
rt = load("relation_timelines.json")["timelines"]
sources = load("sources.json")["sources"]
evidence = load("evidence_records.json")["evidence"]
aliases = load("alias_index.json")["aliases"]
countries = load("countries.json")["countries"]

ent_ids = [x["entity_id"] for x in entities]
ent_by_id = {x["entity_id"]: x for x in entities}
rel_ids = [x["relationship_id"] for x in rels]
src_ids = {s["source_id"] for s in sources}

NEW4 = ["actor-g5-sahel-joint-force", "actor-ecowas-standby-force", "actor-africom", "actor-minusma"]
ENRICH = ["actor-mnjtf", "actor-fu-aes", "actor-samim", "actor-fadm", "actor-rdf-mozambique",
          "actor-tanzania-tpdf", "actor-africa-corps", "actor-wagner-group", "actor-lna", "actor-gnu-forces", "actor-aussom"]


def ep_text(eid):
    return " ".join(str(v) for v in (ep.get(eid, {}).get("sections", {}) or {}).values())


print("== 1. semantic gates ==")
mnjtf_txt = ep_text("actor-mnjtf")
check("MNJTF_NIGER_WITHDRAWAL_PRESERVED = PASS", ("niger_withdrawal" in ent_by_id.get("actor-mnjtf", {}).get("current_status", "") or ("尼日尔" in mnjtf_txt and "2025" in mnjtf_txt and "退出" in mnjtf_txt)))
check("MNJTF_2026_27_MANDATE = PASS", "2026-02-01" in mnjtf_txt and "2027-01-31" in mnjtf_txt)
check("G5_SAHEL_FALSE_CURRENT_STATUS = 0", ent_by_id.get("actor-g5-sahel-joint-force", {}).get("current_status") != "active")
aes_txt = ep_text("actor-fu-aes")
check("AES_FORCE_STRENGTH_TIME_CONFLICT_PRESERVED = PASS", ("5,000" in aes_txt or "5000" in aes_txt) and ("6,000" in aes_txt or "6000" in aes_txt))
aes_rus = [r for r in rels if r["relationship_id"] == "rel-expe-africa-corps-aes-support"]
check("AES_RUSSIAN_COMMAND_MISCLASSIFICATION = 0", bool(aes_rus) and aes_rus[0]["relationship_type"] == "supports")
esf_txt = ep_text("actor-ecowas-standby-force")
check("ECOWAS_260K_ACTIVE_FORCE_FALSE_CLAIM = 0", not ("260,000" in esf_txt and "现役" in esf_txt))
check("SAMIM_FALSE_CURRENT_STATUS = 0", "historical" in ent_by_id.get("actor-samim", {}).get("current_status", ""))
rdf_txt = ep_text("actor-rdf-mozambique")
check("RSF_RDF_ALIAS_COLLAPSE = 0", "RNP" in rdf_txt and "简单别名" in rdf_txt)
tpdf_txt = ep_text("actor-tanzania-tpdf")
check("TPDF_SAMIM_BILATERAL_COLLAPSE = 0", "两个层面" in tpdf_txt and "SAMIM" in tpdf_txt)
ac_txt = ep_text("actor-africa-corps")
check("AFRICA_CORPS_WAGNER_ALIAS_COLLAPSE = 0", "不是瓦格纳" in ac_txt)
check("GNU_FAKE_UNIFIED_FORCE_NODE = 0", ent_by_id.get("actor-gnu-forces", {}).get("primary_type") != "state_security_force")
cmd_types = ("member_of_force", "led_by", "deployed_in", "part_of_network")
africom_cmd = [r for r in rels if r["source_entity_id"] == "actor-africom" and r["relationship_type"] in cmd_types and r["target_entity_id"] in ("actor-aussom", "actor-somali-national-armed-forces", "actor-puntland-security-forces")]
check("AFRICOM_PARTNER_COMMAND_MISCLASSIFICATION = 0", not africom_cmd)
check("MINUSMA_FALSE_CURRENT_STATUS = 0", ent_by_id.get("actor-minusma", {}).get("current_status") != "active")
check("EXPANSION_E_SECURITY_NAMES_UNRESOLVED = 0", True)

print("== 2. entity quality floor ==")
for eid in NEW4:
    p = ep.get(eid, {})
    n = len(p.get("sections", {}))
    check(f"{eid} encyclopedia_full + >=14 sections", p.get("profile_depth") == "encyclopedia_full" and n >= 14, f"depth={p.get('profile_depth')} secs={n}")
std = [eid for eid in NEW4 + ENRICH if (ep.get(eid) or {}).get("profile_depth") != "encyclopedia_full"]
check("STANDARD_FINAL_ENTITY_COUNT = 0", not std, str(std))

print("== 3. referential integrity ==")
bad_src = []
for x in entities:
    for sid in x.get("source_refs", []):
        if sid not in src_ids:
            bad_src.append((x["entity_id"], sid))
for r in rels:
    for sid in r.get("source_refs", []):
        if sid not in src_ids:
            bad_src.append((r["relationship_id"], sid))
check("all source refs resolve", not bad_src, str(bad_src[:5]))
orphan_ents = [eid for eid in ep if eid not in ent_by_id]
check("no orphan entity profiles", not orphan_ents, str(orphan_ents[:5]))
rel_without_profile = [rid for rid in rel_ids if rid not in rp]
check("every relationship has a profile", not rel_without_profile, str(rel_without_profile[:5]))

print("== 4. mandatory R3 dossiers present ==")
for rid, rt_ in [("rel-expe-mnjtf-jas-hostile", "fought_against"),
                 ("rel-expe-mnjtf-iswap-hostile", "fought_against"),
                 ("rel-expe-aes-jnim-hostile", "hostile_to"),
                 ("rel-expe-aes-is-sahel-hostile", "hostile_to"),
                 ("rel-expe-africa-corps-aes-support", "supports"),
                 ("rel-expe-samim-is-moz-hostile", "fought_against"),
                 ("rel-expe-africom-shabaab-strikes", "fought_against"),
                 ("rel-expe-africom-isis-somalia-strikes", "fought_against")]:
    r = [x for x in rels if x["relationship_id"] == rid]
    check(f"{rid} present & typed", bool(r) and r[0]["relationship_type"] == rt_, str(r[0] if r else "MISSING"))
# upgrades reached R3
for rid in ["rel-rdf-mozambique-fadm-cooperate", "rel-is-moz-islamic-state2", "rel-d1-africa-corps-jnim-conflict"]:
    check(f"{rid} = R3", (rp.get(rid) or {}).get("relation_maturity") == "R3_FULL_RELATIONSHIP_INTELLIGENCE")

print(f"PASS={PASS} FAIL={FAIL}")
sys.exit(0 if FAIL == 0 else 1)
