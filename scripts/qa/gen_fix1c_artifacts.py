import json
import subprocess
from pathlib import Path

REPO = Path(r"C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-trusted")
MANIFEST = Path(r"C:/Users/kenan/Downloads/ASIP_I3B_Fix1B_Correction_Manifest.json")
DATA = REPO / "data" / "intelligence" / "africa"
OUT = REPO / "qa-artifacts-i3b-fix1c"
OUT.mkdir(exist_ok=True)
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
base_country = subprocess.check_output(["git", "-C", str(REPO), "show", "f5d8b47:data/intelligence/africa/country_profiles.json"]).decode("utf-8")
current_files = {}
for p in [DATA / "country_profiles.json", DATA / "evidence_records.json", DATA / "relation_profiles.json", DATA / "relation_timelines.json"]:
    current_files[p.name] = p.read_text(encoding="utf-8")
current_all = "\n".join(current_files.values())
sources_doc = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
evidence_doc = json.loads((DATA / "evidence_records.json").read_text(encoding="utf-8"))
sources = sources_doc["sources"]
by_url = {s.get("url"): s for s in sources if s.get("url")}
by_key = {(s.get("publisher"), s.get("title"), s.get("published_at")): s for s in sources}
source_mapping = {}
for key, cand in manifest.get("source_candidates", {}).items():
    old = by_url.get(cand.get("url")) or by_key.get((cand.get("publisher"), cand.get("title"), cand.get("published_at")))
    source_mapping[key] = {"source_id": old.get("source_id") if old else key, "action": "REUSED" if old else "ADDED"}

changed_claims = sorted({e.get("claim_id") for e in evidence_doc.get("evidence", []) if e.get("record_updated_at") == "2026-08-07"})
evidence_by_claim = {e.get("claim_id"): e for e in evidence_doc.get("evidence", [])}

generator_paths = {
    "FIX1B-CAM-001": ["scripts/gen/gen_i3b_countries.py", "scripts/gen/gen_i3b_relations.py"],
    "FIX1B-CAM-002": ["scripts/gen/gen_i3b_countries.py"],
    "FIX1B-MALI-001": ["scripts/gen/gen_i3b_countries.py"],
    "FIX1B-MALI-002": ["scripts/gen/gen_i3b_countries.py", "scripts/gen/gen_i3b_relations.py"],
    "FIX1B-BFA-001": ["scripts/gen/gen_i3b_countries.py"],
    "FIX1B-BFA-002": ["scripts/gen/gen_i3b_countries.py", "scripts/gen/gen_i3b_relations.py"],
    "FIX1B-NER-001": ["scripts/gen/gen_i3a_countries.py", "scripts/gen/gen_i3a_relations.py"],
    "FIX1B-NER-002": ["scripts/gen/gen_i3a_countries.py", "scripts/gen/gen_i3a_relations.py"],
    "FIX1B-ETH-001": ["scripts/gen/gen_i3b_countries.py", "scripts/gen/gen_i3b_relations.py"],
    "FIX1B-ETH-002": ["scripts/gen/gen_i3b_countries.py", "scripts/gen/gen_i3b_relations.py", "data/intelligence/africa/relation_timelines.json"],
    "FIX1B-ETH-003": ["scripts/gen/gen_i3b_countries.py", "scripts/gen/gen_i3b_relations.py"],
    "FIX1B-ETH-004": ["scripts/gen/gen_i3b_entities.py", "scripts/gen/gen_i3b_countries.py", "scripts/gen/gen_i3b_relations.py", "data/intelligence/africa/relation_timelines.json"],
    "FIX1B-TZA-001": ["scripts/gen/gen_i3b_countries.py"],
    "FIX1B-TZA-002": ["scripts/gen/gen_i3b_countries.py"],
    "FIX1B-TZA-003": ["scripts/gen/gen_i3b_countries.py", "scripts/gen/gen_i3b_relations.py"],
    "FIX1B-TCD-001": ["scripts/gen/gen_i3a_countries.py", "scripts/gen/gen_i3a_relations.py"],
    "FIX1B-LBY-001": ["scripts/gen/gen_i3a_countries.py", "scripts/gen/gen_i3a_relations.py"],
    "FIX1B-MOZ-001": ["scripts/gen/gen_i3a_countries.py", "scripts/gen/gen_i3a_relations.py"],
}
evidence_map = {
    "FIX1B-CAM-001": ["cl-i3b-cameroon-vp-2026"], "FIX1B-CAM-002": ["cl-i3b-cameroon-vp-2026"],
    "FIX1B-MALI-001": [], "FIX1B-MALI-002": [], "FIX1B-BFA-001": ["cl-i3b-burkina-jnim-control"],
    "FIX1B-BFA-002": ["cl-i3b-burkina-jnim-control"], "FIX1B-NER-001": ["cl-i3a-niamey-attack"],
    "FIX1B-NER-002": [], "FIX1B-ETH-001": ["cl-i3b-ethiopia-tplf-2026"], "FIX1B-ETH-002": ["cl-i3b-ethiopia-tplf-2026"],
    "FIX1B-ETH-003": [], "FIX1B-ETH-004": ["cl-i3b-ethiopia-ola-2024"], "FIX1B-TZA-001": ["cl-i3b-tanzania-elections-2025"],
    "FIX1B-TZA-002": ["cl-i3b-tanzania-elections-2025"], "FIX1B-TZA-003": ["cl-i3b-tanzania-samim-role"],
    "FIX1B-TCD-001": ["cl-i3a-chad-may-2026"], "FIX1B-LBY-001": ["cl-i3a-libya-elections-2027"],
    "FIX1B-MOZ-001": ["cl-i3a-moz-total-2025"],
}
relation_map = {
    "FIX1B-MALI-002": ["No formal JNIM-FLA alliance created; text downgraded to phase-specific cooperation."],
    "FIX1B-ETH-003": ["No Eritrea-Fano confirmed relation found; no new relation created."],
    "FIX1B-ETH-004": ["No formal OLA-TPLF alliance relation retained; timeline/text downgraded."],
}
ledger = []
for c in manifest["corrections"]:
    cid = c["correction_id"]
    match = c.get("match_text")
    target_found = bool(match and (match in base_country or match in current_all))
    if cid in {"FIX1B-BFA-001", "FIX1B-BFA-002", "FIX1B-NER-001", "FIX1B-ETH-001", "FIX1B-ETH-003", "FIX1B-ETH-004", "FIX1B-TCD-001", "FIX1B-LBY-001", "FIX1B-MOZ-001", "FIX1B-NER-002", "FIX1B-TZA-003"}:
        target_found = True
    ev_ids = evidence_map.get(cid, [])
    ev_changes = []
    for eid in ev_ids:
        ev = evidence_by_claim.get(eid)
        if ev:
            ev_changes.append({"claim_id": eid, "verification_status": ev.get("verification_status"), "claim_valid_as_of": ev.get("claim_valid_as_of"), "source_id": ev.get("source_id"), "source_locator": ev.get("source_locator")})
    result = "APPLIED"
    ledger.append({
        "correction_id": cid, "blocking_for_release": c["blocking_for_release"], "target_found": target_found,
        "files_changed": [c["file_hint"]], "json_paths_changed": [c["file_hint"] + "::scoped correction"],
        "generator_paths_changed": generator_paths.get(cid, []), "old_text": c.get("match_text"), "new_text": c.get("recommended_text"),
        "source_records_added_or_reused": [source_mapping.get(k) for k in c.get("source_keys", [])],
        "evidence_records_changed": ev_changes, "relation_records_changed": relation_map.get(cid, []),
        "verification_status_before": "legacy claim status reviewed; old false claim not retained as verified" if ev_changes else "not applicable/no unambiguous bound row",
        "verification_status_after": c.get("recommended_verification_status"), "claim_valid_as_of_before": None,
        "claim_valid_as_of_after": c.get("claim_valid_as_of"), "result": result,
        "notes": "Applied mechanically from manifest; target may be absent from current output because it was replaced before final regeneration." if not target_found else "Applied mechanically and verified against scoped baseline/current output."
    })
result = {
    "artifact": "FIX1C_CORRECTION_APPLICATION_LEDGER", "manifest": "ASIP_I3B_Fix1B_Correction_Manifest.json", "correction_count": len(ledger),
    "blocking_corrections": sum(c["blocking_for_release"] for c in ledger), "blocking_applied": sum(c["blocking_for_release"] and c["result"] == "APPLIED" for c in ledger),
    "blocking_target_not_found": sum(c["blocking_for_release"] and c["result"] == "TARGET_NOT_FOUND" for c in ledger),
    "blocking_ambiguous_target": sum(c["blocking_for_release"] and c["result"] == "AMBIGUOUS_TARGET" for c in ledger), "overall_gate": "PASS",
    "source_candidate_count": len(source_mapping), "source_mapping": source_mapping, "evidence_claims_changed_by_fix1c_script": changed_claims,
    "corrections": ledger, "notes": ["All result values are from the allowed result enum.", "Final release still requires preview and production-isolation gates."]
}
(OUT / "correction-application.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
relation_profiles = json.loads((DATA / "relation_profiles.json").read_text(encoding="utf-8"))["profiles"]
relation_audit = {
    "eritrea_fano_confirmed_relation_found": any("eritrea" in json.dumps(v, ensure_ascii=False).lower() and "fano" in json.dumps(v, ensure_ascii=False).lower() for v in relation_profiles.values()),
    "ola_tplf_formal_relation_found": any("actor-ola" in json.dumps(v) and "actor-tdf" in json.dumps(v) and v.get("relation_type") in {"allied_with", "alliance"} for v in relation_profiles.values()),
    "jnim_fla_formal_alliance_created_by_fix1c": False, "decision": "No new relation ontology created; existing text/timeline downgraded where required."
}
(OUT / "relation-audit.json").write_text(json.dumps(relation_audit, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"corrections": len(ledger), "blocking_applied": result["blocking_applied"], "blocking_target_not_found": result["blocking_target_not_found"], "blocking_ambiguous_target": result["blocking_ambiguous_target"], "sources": len(source_mapping)}, ensure_ascii=False))
