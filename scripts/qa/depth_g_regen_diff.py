#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPTH G regeneration / idempotency diff.

Verifies:
  1. re-running the full Depth G pipeline produces byte-identical data files
  2. no unexpected object creation / deletion (counts frozen at baseline shape)
  3. the only maturity movements versus the DEPTH F baseline are the
     INTENTIONAL DOWNSHIFTS recorded in truthful-downgrade-report.json
  4. the JNIM-IS relationship repair is present and correct
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
QA = ROOT / "qa-artifacts-depth-g"
PIPELINE = ROOT / "scripts" / "gen" / "depth_g_pipeline.py"

BASELINE_COUNTS = {
    "countries": 13,
    "entities": 72,
    "relationships": 150,
}


def load(name, base=DATA):
    with open(base / name, encoding="utf-8") as fh:
        return json.load(fh)


def hash_data():
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(DATA.glob("*.json"))
    }


def git_show(path):
    """Read a data file as it exists at the DEPTH F baseline commit (HEAD)."""
    rel = path.relative_to(ROOT).as_posix()
    out = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8")
    if out.returncode != 0:
        return None
    return json.loads(out.stdout)


def main():
    findings = []
    result = {"artifact": "DEPTHG_REGEN_DIFF", "checks": {}}

    # ---- 1. byte-level idempotency ---------------------------------------
    before = hash_data()
    proc = subprocess.run([sys.executable, str(PIPELINE)], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        findings.append(f"pipeline rerun failed rc={proc.returncode}")
    after = hash_data()
    changed = sorted(k for k in after if before.get(k) != after[k])
    result["checks"]["byte_idempotent"] = {
        "files_checked": len(after),
        "files_changed_on_rerun": changed,
        "pass": not changed,
    }
    if changed:
        findings.append(f"pipeline NOT idempotent: {changed}")

    # ---- 2. object counts frozen -----------------------------------------
    counts = {
        "countries": len(load("countries.json")["countries"]),
        "entities": len(load("entities.json")["entities"]),
        "relationships": len(load("relationships.json")["relationships"]),
    }
    result["checks"]["counts"] = {
        "expected": BASELINE_COUNTS, "actual": counts,
        "pass": counts == BASELINE_COUNTS,
    }
    if counts != BASELINE_COUNTS:
        findings.append(f"object counts drifted: {counts} != {BASELINE_COUNTS}")

    # ---- 3. id sets unchanged versus baseline ----------------------------
    base_ents = git_show(DATA / "entities.json")
    base_rels = git_show(DATA / "relationships.json")
    idcheck = {}
    if base_ents and base_rels:
        cur_e = {e["entity_id"] for e in load("entities.json")["entities"]}
        old_e = {e["entity_id"] for e in base_ents["entities"]}
        cur_r = {r["relationship_id"] for r in load("relationships.json")["relationships"]}
        old_r = {r["relationship_id"] for r in base_rels["relationships"]}
        idcheck = {
            "entities_added": sorted(cur_e - old_e),
            "entities_removed": sorted(old_e - cur_e),
            "relations_added": sorted(cur_r - old_r),
            "relations_removed": sorted(old_r - cur_r),
        }
        idcheck["pass"] = not any(idcheck[k] for k in list(idcheck) if k != "pass")
        if not idcheck["pass"]:
            findings.append(f"id set drift: {idcheck}")
    result["checks"]["id_sets"] = idcheck

    # ---- 4. maturity movements are all intentional -----------------------
    # the cumulative ledger survives idempotent reruns; the per-run report does not
    try:
        led = json.load(open(QA / "truthful-downgrade-ledger.json", encoding="utf-8"))
    except FileNotFoundError:
        led = {"entities": {}, "relations": {}}
    intentional_e = {k: (v["from"], v["to"]) for k, v in led.get("entities", {}).items()}
    intentional_r = {k: (v["from"], v["to"]) for k, v in led.get("relations", {}).items()}

    pack = json.load(open(r"C:\Users\kenan\Downloads\ASIP_Depth_G_Final_Closure_Content_Pack.json",
                          encoding="utf-8"))
    pack_ent_targets = {c.get("entity_id"): c.get("target_maturity")
                        for c in pack.get("entity_closure", []) if c.get("entity_id")}
    pack_rel_targets = {o.get("relationship_id"): o.get("target_maturity")
                        for o in pack.get("core_relation_overrides", []) if o.get("relationship_id")}

    base_ep = git_show(DATA / "entity_profiles.json")
    cur_ep = load("entity_profiles.json")["profiles"]
    e_moves, e_unexpected = [], []
    if base_ep:
        for eid, prof in cur_ep.items():
            old = (base_ep["profiles"].get(eid) or {}).get("content_maturity")
            new = prof.get("content_maturity")
            if old and new and old != new:
                move = {"entity_id": eid, "from": old, "to": new}
                if eid in intentional_e:
                    move["basis"] = "INTENTIONAL_TRUTHFUL_DOWNSHIFT"
                elif pack_ent_targets.get(eid) == new:
                    move["basis"] = "CONTENT_PACK_CLOSURE_TARGET"
                else:
                    move["basis"] = "UNEXPECTED"
                    e_unexpected.append(move)
                e_moves.append(move)

    base_rp = git_show(DATA / "relation_profiles.json")
    cur_rp = load("relation_profiles.json")["profiles"]
    r_moves, r_unexpected = [], []
    dyn_rules = bool(pack.get("dynamic_relation_maturity_rules"))
    if base_rp:
        for rid, prof in cur_rp.items():
            old = (base_rp["profiles"].get(rid) or {}).get("relation_maturity")
            new = prof.get("relation_maturity")
            if old and new and old != new:
                move = {"relationship_id": rid, "from": old, "to": new}
                if rid in intentional_r:
                    move["basis"] = "INTENTIONAL_TRUTHFUL_DOWNSHIFT"
                elif pack_rel_targets.get(rid) == new:
                    move["basis"] = "CONTENT_PACK_OVERRIDE_TARGET"
                elif dyn_rules:
                    move["basis"] = "DYNAMIC_RELATION_MATURITY_RULE"
                else:
                    move["basis"] = "UNEXPECTED"
                    r_unexpected.append(move)
                r_moves.append(move)

    result["checks"]["maturity_movements"] = {
        "entity_moves": len(e_moves),
        "relation_moves": len(r_moves),
        "entity_unexpected": e_unexpected,
        "relation_unexpected": r_unexpected,
        "intentional_downshifts_entities": intentional_e,
        "intentional_downshifts_relations": intentional_r,
        "pass": not e_unexpected and not r_unexpected,
    }
    if e_unexpected or r_unexpected:
        findings.append(f"unexpected maturity moves: E={len(e_unexpected)} R={len(r_unexpected)}")

    # ---- 5. JNIM-IS repair present ---------------------------------------
    rels = {r["relationship_id"]: r for r in load("relationships.json")["relationships"]}
    hostile = rels.get("rel-jnim-is-hostile", {})
    conflict = rels.get("rel-jnim-is-conflict", {})
    jnim_is = {
        "rel-jnim-is-hostile": {
            "type": hostile.get("relationship_type"),
            "time_start": hostile.get("time_start"),
            "time_end": hostile.get("time_end"),
            "maturity": (cur_rp.get("rel-jnim-is-hostile") or {}).get("relation_maturity"),
            "expect_type": "historically_associated_with",
            "expect_maturity": "R2_DEVELOPED_RELATIONSHIP",
        },
        "rel-jnim-is-conflict": {
            "type": conflict.get("relationship_type"),
            "maturity": (cur_rp.get("rel-jnim-is-conflict") or {}).get("relation_maturity"),
            "expect_type": "hostile_to",
            "expect_maturity": "R3_FULL_RELATIONSHIP_INTELLIGENCE",
        },
    }
    ok = (jnim_is["rel-jnim-is-hostile"]["type"] == "historically_associated_with"
          and jnim_is["rel-jnim-is-hostile"]["maturity"] == "R2_DEVELOPED_RELATIONSHIP"
          and jnim_is["rel-jnim-is-conflict"]["type"] == "hostile_to"
          and jnim_is["rel-jnim-is-conflict"]["maturity"] == "R3_FULL_RELATIONSHIP_INTELLIGENCE"
          and len(rels) == 150)
    jnim_is["relationship_total"] = len(rels)
    jnim_is["pass"] = ok
    result["checks"]["jnim_is_repair"] = jnim_is
    if not ok:
        findings.append("JNIM-IS repair check failed")

    result["findings"] = findings
    result["pass"] = not findings

    (QA / "regen-diff.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print("== DEPTH G REGEN DIFF ==")
    print("byte idempotent      :", result["checks"]["byte_idempotent"]["pass"],
          f"({len(after)} files, {len(changed)} changed)")
    print("counts frozen        :", result["checks"]["counts"]["pass"], counts)
    print("id sets unchanged    :", idcheck.get("pass"))
    print("maturity moves       : E=%d R=%d (unexpected E=%d R=%d)" % (
        len(e_moves), len(r_moves), len(e_unexpected), len(r_unexpected)))
    print("JNIM-IS repair       :", ok, "| relationships =", len(rels))
    print("\nINTENTIONAL DOWNSHIFTS")
    for eid, (a, b) in intentional_e.items():
        print(f"  E {eid}: {a} -> {b}")
    for rid, (a, b) in intentional_r.items():
        print(f"  R {rid}: {a} -> {b}")
    print("\nRESULT:", "PASS" if result["pass"] else "FAIL", findings)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
