#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH G final closure gates: 16 tests covering count invariants, source
dedupe / un-jnim-2018 claim relevance, entity closure targets, AQIM al-Annabi
correction, ISWAP Barnawi/Bakura error removal, Katiba Hanifa E3, JNIM-IS
two-phase repair, core relation overrides, dynamic relation maturity coverage,
summary-only re-audit, stale temporal handling, evidence mapping, truthful
maturity downgrades, accepted evidence limitations, dangling reference zero,
and generator idempotency."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-g"

fails = []


def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    print(f"  [{tag}] {name}" + (f" | {detail}" if detail else ""))
    if not cond:
        fails.append(name)


def load(name, base=DATA):
    return json.load(open(base / name, encoding="utf-8"))


def qa(name):
    p = QA / name
    if not p.exists():
        return None
    return json.load(open(p, encoding="utf-8"))


countries = load("countries.json")["countries"]
entities = load("entities.json")["entities"]
rels = load("relationships.json")["relationships"]
ep = load("entity_profiles.json")["profiles"]
rp = load("relation_profiles.json")["profiles"]
sources = load("sources.json")["sources"]
evidence = load("evidence_records.json")["evidence"]
metrics = load("catalog_metrics.json")

rel_by_id = {r["relationship_id"]: r for r in rels}
ent_by_id = {e["entity_id"]: e for e in entities}
non_country = [e for e in entities if e["entity_type"] != "country"]
src_ids = {s.get("source_id") for s in sources}


def sections_text(eid):
    return json.dumps(ep.get(eid, {}).get("sections", {}), ensure_ascii=False)


print("== TEST 1: count invariants (no breadth expansion) ==")
check("countries=13", len(countries) == 13, f"got {len(countries)}")
check("entities=105", len(non_country) == 105, f"got {len(non_country)} (105 + 0 Consolidation A)")
check("relationships=201", len(rels) == 201, f"got {len(rels)} (201 + 0 Consolidation A)")
check("routes=333", metrics.get("route_count") == 333, f"got {metrics.get('route_count')} (333 + 0 Consolidation A)")
check("sources grew from 182", len(sources) >= 182, f"got {len(sources)}")
check("evidence grew from 297", len(evidence) >= 297, f"got {len(evidence)}")

print("== TEST 2: source dedupe ==")
by_url, by_key, dup_url, dup_key = {}, {}, [], []
for s in sources:
    u = (s.get("url") or "").strip().rstrip("/").lower()
    if u:
        if u in by_url:
            dup_url.append((by_url[u], s.get("source_id")))
        by_url[u] = s.get("source_id")
    k = ((s.get("title") or "").strip().lower(), (s.get("publisher") or "").strip().lower())
    if all(k):
        if k in by_key:
            dup_key.append((by_key[k], s.get("source_id")))
        by_key[k] = s.get("source_id")
check("no duplicate source URLs", not dup_url, str(dup_url[:3]))
check("no duplicate title+publisher", not dup_key, str(dup_key[:3]))
check("no duplicate source_ids", len(src_ids) == len(sources), f"{len(src_ids)} vs {len(sources)}")

print("== TEST 3: un-jnim-2018 claim relevance (not blanket deletion) ==")
audit = qa("source-relevance-audit.json")
check("audit artifact exists", audit is not None)
check("un-jnim-2018 still in catalog", "un-jnim-2018" in src_ids)
blob = json.dumps({"e": entities, "r": rels}, ensure_ascii=False)
check("un-jnim-2018 retained where relevant", blob.count("un-jnim-2018") > 0,
      f"remaining refs={blob.count('un-jnim-2018')}")
for eid in ("actor-tanzania-tpdf", "actor-rdf-mozambique"):
    check(f"{eid} un-jnim-2018 stripped",
          "un-jnim-2018" not in ent_by_id.get(eid, {}).get("source_refs", []))

print("== TEST 4: AQIM al-Annabi leadership correction ==")
aqim = sections_text("actor-aqim")
aqim_flat = aqim.replace(" ", "").replace("\u3000", "")
check("al-Annabi named", "Annabi" in aqim or "阿纳比" in aqim or "安纳比" in aqim)
check("Amir since 2020", "2020" in aqim and ("埃米尔" in aqim or "Amir" in aqim))
# Droukdel may only appear as a HISTORICAL amir; he must never read as incumbent.
if "Droukdel" in aqim or "德鲁克德尔" in aqim:
    check("Droukdel marked as killed/former",
          any(k in aqim_flat for k in ("被击毙", "击毙", "2020年6月", "历任")),
          "Droukdel present without death/former marker")
    check("al-Annabi is the incumbent amir",
          any(k in aqim_flat for k in ("现任埃米尔", "至今", "2020年11月至今")),
          "no incumbency statement for al-Annabi")
check("stale 'successor unconfirmed' language retired",
      "继任者未获确认" not in aqim_flat or "已经过时" in aqim_flat)

print("== TEST 5: ISWAP Barnawi/Bakura error removed ==")
iswap = sections_text("actor-iswap")
check("no Bakura=Barnawi conflation",
      "Bakura（与al-Barnawi非同一人）被报道死亡" not in iswap)
check("Shekau 2021 death recorded", "Shekau" in iswap and "2021" in iswap)
check("Barnawi and Bakura distinguished",
      ("非同一人" in iswap or "不同" in iswap or "区分" in iswap)
      if ("Bakura" in iswap and "Barnawi" in iswap) else True)

print("== TEST 6: Katiba Hanifa E3 closure ==")
kh = ep.get("actor-katiba-hanifa", {})
check("Katiba Hanifa profile present", bool(kh))
check("Katiba Hanifa = E3", kh.get("content_maturity") == "E3_FULL_ENCYCLOPEDIA",
      str(kh.get("content_maturity")))
check("Katiba Hanifa has sections", len(kh.get("sections") or {}) >= 8,
      f"{len(kh.get('sections') or {})} sections")

print("== TEST 7: JNIM-IS two-phase repair ==")
hostile = rel_by_id.get("rel-jnim-is-hostile", {})
conflict = rel_by_id.get("rel-jnim-is-conflict", {})
check("hostile edge reclassified", hostile.get("relationship_type") == "historically_associated_with",
      str(hostile.get("relationship_type")))
check("hostile phase 2016-2019", hostile.get("time_start") == "2016" and hostile.get("time_end") == "2019",
      f"{hostile.get('time_start')}-{hostile.get('time_end')}")
check("hostile edge = R2", (rp.get("rel-jnim-is-hostile") or {}).get("relation_maturity")
      == "R2_DEVELOPED_RELATIONSHIP",
      str((rp.get("rel-jnim-is-hostile") or {}).get("relation_maturity")))
check("conflict edge hostile_to", conflict.get("relationship_type") == "hostile_to",
      str(conflict.get("relationship_type")))
check("conflict edge = R3", (rp.get("rel-jnim-is-conflict") or {}).get("relation_maturity")
      == "R3_FULL_RELATIONSHIP_INTELLIGENCE",
      str((rp.get("rel-jnim-is-conflict") or {}).get("relation_maturity")))
check("relationship count unchanged at 201", len(rels) == 201)

print("== TEST 8: core relation overrides applied ==")
imp = qa("depth-g-import-report.json")
check("import report exists", imp is not None)
pack_locked = [
    "rel-jnim-katiba-constituent", "rel-jnim-benin-forces-fought",
    "rel-cameroon-army-ambazonia", "rel-mali-army-jnim", "rel-burkina-army-jnim",
    "rel-d2-katiba-hanifa-jnim",
]
for rid in pack_locked:
    prof = rp.get(rid) or {}
    check(f"{rid} has maturity badge", bool(prof.get("relation_maturity")),
          str(prof.get("relation_maturity")))
    check(f"{rid} profile not badge-only stub", len(
        [k for k, v in prof.items() if isinstance(v, str) and len(v) > 20]) >= 1,
        f"fields={sorted(prof)[:6]}")

print("== TEST 9: dynamic relation maturity coverage ==")
missing = [r["relationship_id"] for r in rels
           if not (rp.get(r["relationship_id"]) or {}).get("relation_maturity")]
check("every relation has a maturity badge", not missing, f"missing={missing[:5]}")
tiers = {}
for r in rels:
    t = (rp.get(r["relationship_id"]) or {}).get("relation_maturity")
    tiers[t] = tiers.get(t, 0) + 1
check("all three tiers populated", len([k for k in tiers if k]) == 3, str(tiers))
check("tier totals sum to 201", sum(v for k, v in tiers.items() if k) == 201, str(tiers))

print("== TEST 10: summary-only re-audit + staleness handling ==")
rc = qa("relation-closure-audit.json")
check("relation closure audit exists", rc is not None)
stale_marked = [r["relationship_id"] for r in rels if r.get("temporal_handling")]
check("stale relations carry temporal_handling", len(stale_marked) >= 20,
      f"got {len(stale_marked)}")
kinds = {r.get("temporal_handling") for r in rels if r.get("temporal_handling")}
check("temporal handling uses declared categories",
      kinds <= {"REFRESHED_BY_PACKET", "AGING_MONITORED", "HISTORICAL_CLOSED"}, str(kinds))
check("no relation both current and historical-closed",
      not [r for r in rels if r.get("temporal_handling") == "HISTORICAL_CLOSED"
           and r.get("freshness_status") == "current"])

print("== TEST 11: evidence mapping resolves ==")
ev_bad = [e for e in evidence if e.get("source_id") and e["source_id"] not in src_ids]
check("no evidence points at a missing source", not ev_bad,
      str([e.get("evidence_id") for e in ev_bad[:5]]))
ev_ids = [e.get("evidence_id") for e in evidence]
check("no duplicate evidence ids", len(set(ev_ids)) == len(ev_ids),
      f"{len(set(ev_ids))} vs {len(ev_ids)}")
evrep = qa("evidence-import-report.json")
check("evidence import unresolved=0",
      (evrep or {}).get("unresolved", 0) in (0, None), str((evrep or {}).get("unresolved")))

print("== TEST 12: zero dangling source references ==")
dangling = []
for e in entities:
    for s in e.get("source_refs", []) or []:
        if s not in src_ids:
            dangling.append(("entity", e["entity_id"], s))
for r in rels:
    for s in r.get("source_refs", []) or []:
        if s not in src_ids:
            dangling.append(("relation", r["relationship_id"], s))
for rid, prof in rp.items():
    for s in prof.get("source_ids", []) or []:
        if s not in src_ids:
            dangling.append(("relprofile", rid, s))
for eid, prof in ep.items():
    for s in prof.get("source_refs", []) or []:
        if s not in src_ids:
            dangling.append(("entprofile", eid, s))
check("DANGLING SOURCE REFS = 0", not dangling, str(dangling[:5]))

print("== TEST 13: truthful maturity downgrades applied ==")
led = qa("truthful-downgrade-ledger.json") or {"entities": {}, "relations": {}}
check("downgrade ledger exists", bool(led.get("entities") or led.get("relations")))
_EXP_A_ENTITY_DOWNSHIFT_EXEMPT = {
    # Consolidation A: Dozos of Macina was downshifted E3->E2 by Depth G for thin
    # content; the Final Depth Consolidation Pack A (§13) enriches it back to
    # encyclopedia_full, so the downshift is superseded.
    "actor-dozos-of-macina": "E3_FULL_ENCYCLOPEDIA",
}
for eid, mv in (led.get("entities") or {}).items():
    if eid in _EXP_A_ENTITY_DOWNSHIFT_EXEMPT:
        check(f"consolidation-a supersedes entity downshift {eid}",
              (ep.get(eid) or {}).get("content_maturity") == _EXP_A_ENTITY_DOWNSHIFT_EXEMPT[eid])
        continue
    check(f"entity downshift applied {eid}",
          (ep.get(eid) or {}).get("content_maturity") == mv["to"],
          f"want {mv['to']} got {(ep.get(eid) or {}).get('content_maturity')}")
# EXPANSION A: the three ansaru relations were downshifted by Depth G because
# they lacked context/history fields. The Expansion A content pack (section 16,
# dossier C) authorizes full R3/R2 dossiers for them, which fills exactly those
# gaps, so the depth-g downshift is superseded and they are exempted.
_EXP_A_REL_DOWNSHIFT_EXEMPT = {
    "rel-d1-ansaru-jas-split": "R3_FULL_RELATIONSHIP_INTELLIGENCE",
    "rel-d1-ansaru-aqim-allegiance": "R2_DEVELOPED_RELATIONSHIP",
    "rel-d1-ansaru-jnim-affiliation": "R2_DEVELOPED_RELATIONSHIP",
    # EXPANSION E: RDF/RSF ↔ ISIS-Mozambique was downshifted R3→R2 for lacking
    # evolution_stages / <2 timeline events; Expansion E (§7 mandatory R3) fills
    # exactly those gaps, so the downshift is superseded.
    "rel-is-moz-islamic-state2": "R3_FULL_RELATIONSHIP_INTELLIGENCE",
    # Consolidation A: this person-only led_by edge was removed during
    # de-formalization of person-amadou-nionson-diarra (leadership fact moved
    # into actor-dozos-of-macina narrative), so the depth-g downshift no longer applies.
    "rel-d2-dozos-macina-amadou-led": "__REMOVED__",
}
for rid, mv in (led.get("relations") or {}).items():
    if rid in _EXP_A_REL_DOWNSHIFT_EXEMPT:
        if _EXP_A_REL_DOWNSHIFT_EXEMPT[rid] == "__REMOVED__":
            check(f"consolidation-a removed relation {rid}", rid not in rp)
        else:
            check(f"expansion-a supersedes downshift {rid}",
                  (rp.get(rid) or {}).get("relation_maturity") == _EXP_A_REL_DOWNSHIFT_EXEMPT[rid],
                  f"want {_EXP_A_REL_DOWNSHIFT_EXEMPT[rid]} got {(rp.get(rid) or {}).get('relation_maturity')}")
        continue
    check(f"relation downshift applied {rid}",
          (rp.get(rid) or {}).get("relation_maturity") == mv["to"],
          f"want {mv['to']} got {(rp.get(rid) or {}).get('relation_maturity')}")

print("== TEST 14: no inflated badge outside declared limitations ==")
after = qa("maturity-recalibration-after.json")
check("after snapshot exists", after is not None)
if after:
    lim = qa("accepted-evidence-limitations.json") or {}
    ceil = (lim.get("maturity_ceiling_limitations") or {})
    locked = {x["relationship_id"] for x in (ceil.get("relations") or [])}
    locked_e = {x["entity_id"] for x in (ceil.get("entities") or [])}
    r_infl = {k for k, v in after["relations"].items() if (v.get("delta") or 0) > 0}
    e_infl = {k for k, v in after["entities"].items() if (v.get("delta") or 0) > 0}
    check("entity inflated outside limitations = 0", not (e_infl - locked_e),
          str(sorted(e_infl - locked_e)))
    check("relation inflated outside limitations = 0", not (r_infl - locked),
          str(sorted(r_infl - locked)))
    check("every declared limitation is real", not (locked - r_infl),
          str(sorted(locked - r_infl)))
    viol = [k for k, v in after["entities"].items() if not v.get("truthful_meets_floor")]
    check("importance floor violations = 0", not viol, str(viol[:5]))

print("== TEST 15: accepted evidence limitations are declared, not silent ==")
lim = qa("accepted-evidence-limitations.json")
check("limitations artifact exists", lim is not None)
if lim:
    ceil = lim.get("maturity_ceiling_limitations") or {}
    recs = (ceil.get("relations") or []) + (ceil.get("entities") or [])
    check("every limitation states scored tier",
          all(r.get("scored_maturity") for r in recs), f"n={len(recs)}")
    check("every limitation states a basis",
          all(r.get("basis") for r in recs))
    check("every limitation states gaps",
          all(r.get("gaps") is not None for r in recs))

print("== TEST 16: generator idempotency + no fabricated objects ==")
regen = qa("regen-diff.json")
check("regen diff artifact exists", regen is not None)
if regen:
    c = regen["checks"]
    check("byte idempotent", c["byte_idempotent"]["pass"],
          str(c["byte_idempotent"]["files_changed_on_rerun"]))
    check("counts frozen", c["counts"]["pass"], str(c["counts"]["actual"]))
    check("no entities added", not c["id_sets"].get("entities_added"),
          str(c["id_sets"].get("entities_added")))
    check("no relations added", not c["id_sets"].get("relations_added"),
          str(c["id_sets"].get("relations_added")))
    check("no entities removed", not c["id_sets"].get("entities_removed"),
          str(c["id_sets"].get("entities_removed")))
    check("no relations removed", not c["id_sets"].get("relations_removed"),
          str(c["id_sets"].get("relations_removed")))
    check("no unexpected maturity moves",
          c["maturity_movements"]["pass"],
          f"E={c['maturity_movements']['entity_unexpected']} "
          f"R={c['maturity_movements']['relation_unexpected']}")

print()
if fails:
    print(f"FAIL_TOTAL={len(fails)}: {fails}")
    sys.exit(1)
print("ALL DEPTH G TESTS PASS")
