#!/usr/bin/env python3
"""Depth G — dynamic relation maturity closure, summary-only re-audit, staleness.

Three jobs, all formalisation-only. No new factual claims are invented: every
field written is derived from material that already exists on the relationship
object (relation_summary, formation_background, current_status_detail,
why_it_matters, uncertainties, source_refs) or from packet-provided content.

  step 7  Assign relation_maturity to every relation still lacking one, using
          the Content Pack's type defaults, then verify the assignment against
          the actual evidence the object carries. An R2 default that cannot
          substantiate R2 is downshifted to R1 and recorded as an
          ACCEPTED_EVIDENCE_LIMITATION rather than padded with invention.

  step 8  Re-audit the 15 summary-only relations. Truthful downshift to R1 is
          the expected outcome unless already-sourced fields support R2.

  step 9  Temporal handling for the 29 stale relations. Historical/aging is not
          a failure; the failure mode is stale current-sensitive content with no
          explicit temporal handling. Each stale relation is classified as
          HISTORICAL_CLOSED, AGING_MONITORED or REFRESHED_BY_PACKET and gets an
          explicit temporal disclosure.

Writes qa-artifacts-depth-g/relation-closure-audit.json and
qa-artifacts-depth-g/accepted-evidence-limitations.json.
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

TODAY = "2026-08-09"
R1 = "R1_SIMPLE_SOURCED_RELATION"
R2 = "R2_DEVELOPED_RELATIONSHIP"
R3 = "R3_FULL_RELATIONSHIP_INTELLIGENCE"


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def dump(name: str, obj) -> None:
    (DATA / name).write_text(
        json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def txt(v) -> str:
    """Flatten a field to plain text for substance measurement."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        return " ".join(txt(x) for x in v)
    if isinstance(v, dict):
        return " ".join(txt(x) for x in v.values())
    return str(v)


def substantive(v, minimum: int = 12) -> bool:
    return len(txt(v)) >= minimum


def evidence_index(evidence_doc) -> dict:
    """relationship_id -> [claim_id]"""
    idx = collections.defaultdict(list)
    records = evidence_doc.get("evidence") or evidence_doc.get("records") or []
    for rec in records:
        cid = rec.get("claim_id") or rec.get("evidence_id")
        for rid in rec.get("relation_ids", []) or []:
            idx[rid].append(cid)
    return dict(idx)


def r2_capable(rel: dict, prof: dict) -> tuple[bool, list[str]]:
    """R2 = summary + context/history + current assessment + why/uncertainty + source."""
    gaps: list[str] = []
    has_summary = substantive(rel.get("relation_summary")) or substantive(prof.get("overview"))
    has_context = (
        substantive(rel.get("formation_background"))
        or substantive(prof.get("formation_background"))
        or substantive(prof.get("evolution_stages"))
        or substantive(prof.get("initial_relationship"))
    )
    has_current = (
        substantive(rel.get("current_status_detail"))
        or substantive(prof.get("current_status"))
    )
    has_why = (
        substantive(rel.get("why_it_matters"))
        or substantive(rel.get("uncertainties"))
        or substantive(prof.get("why_it_matters"))
        or substantive(prof.get("uncertainties"))
    )
    sourced = bool(rel.get("source_refs")) or bool(prof.get("source_ids"))

    if not has_summary:
        gaps.append("no relation summary")
    if not has_context:
        gaps.append("no context/history field")
    if not has_current:
        gaps.append("no current assessment field")
    if not has_why:
        gaps.append("no why-it-matters / uncertainty field")
    if not sourced:
        gaps.append("no resolvable source")
    return (not gaps), gaps


def r1_capable(rel: dict, prof: dict) -> tuple[bool, list[str]]:
    """R1 = summary + temporal/current state + >=1 resolvable source."""
    gaps: list[str] = []
    if not (substantive(rel.get("relation_summary")) or substantive(prof.get("overview"))):
        gaps.append("no relation summary")
    if not (
        rel.get("time_start")
        or rel.get("start_year")
        or substantive(rel.get("current_status"))
        or substantive(rel.get("current_status_detail"))
    ):
        gaps.append("no temporal or current-state marker")
    if not (rel.get("source_refs") or prof.get("source_ids")):
        gaps.append("no resolvable source")
    return (not gaps), gaps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    pack = json.loads(PACK.read_text(encoding="utf-8"))
    rules = pack["dynamic_relation_maturity_rules"]
    r1_types = set(rules["R1_default_types"])
    r2_types = set(rules["R2_default_types"])

    rels_doc = load("relationships.json")
    rprof_doc = load("relation_profiles.json")
    rels = rels_doc["relationships"]
    rprofiles = rprof_doc.get("profiles", rprof_doc)
    try:
        ev_idx = evidence_index(load("evidence_records.json"))
    except FileNotFoundError:
        ev_idx = {}

    assignments: list[dict] = []
    limitations: list[dict] = []
    unknown_types: list[str] = []

    # ---------------- step 7: dynamic assignment ----------------
    for rel in rels:
        rid = rel["relationship_id"]
        prof = rprofiles.get(rid, {})
        if prof.get("relation_maturity"):
            continue  # core overrides / earlier depths already set this

        rtype = rel.get("relationship_type")
        if rtype in r1_types:
            default = R1
        elif rtype in r2_types:
            default = R2
        else:
            default = R1
            unknown_types.append(rtype)

        ok2, gaps2 = r2_capable(rel, prof)
        ok1, gaps1 = r1_capable(rel, prof)

        if default == R2 and ok2:
            final, reason = R2, "R2 default type with full R2 field coverage"
        elif default == R2 and not ok2:
            final = R1 if ok1 else R1
            reason = f"R2 default downshifted to R1 — {'; '.join(gaps2)}"
            limitations.append({
                "object_id": rid,
                "object_type": "relationship",
                "relationship_type": rtype,
                "default_maturity": R2,
                "assigned_maturity": R1,
                "limitation": "ACCEPTED_EVIDENCE_LIMITATION",
                "missing": gaps2,
                "rationale": (
                    "Content Pack rule: assign R1 and record the limitation rather "
                    "than fabricate the missing analytical material."
                ),
            })
        else:
            final = R1
            reason = "R1 default type — straightforward sourced relation"
            if not ok1:
                limitations.append({
                    "object_id": rid,
                    "object_type": "relationship",
                    "relationship_type": rtype,
                    "default_maturity": R1,
                    "assigned_maturity": R1,
                    "limitation": "ACCEPTED_EVIDENCE_LIMITATION",
                    "missing": gaps1,
                    "rationale": (
                        "Relation retained at R1; the missing element is a genuine "
                        "public-record gap and is disclosed rather than invented."
                    ),
                })

        target = rprofiles.setdefault(rid, {})
        target.setdefault("relation_id", rid)
        target.setdefault("relation_type", rtype)
        target.setdefault("slug", rel.get("slug"))
        target.setdefault("source_entity_id", rel.get("source_entity_id"))
        target.setdefault("target_entity_id", rel.get("target_entity_id"))
        # Mirror existing sourced material into the profile so the maturity badge
        # is backed by fields the reader can actually see. Nothing new is coined.
        if not target.get("overview") and rel.get("relation_summary"):
            target["overview"] = rel["relation_summary"]
        if not target.get("source_ids") and rel.get("source_refs"):
            target["source_ids"] = list(rel["source_refs"])
        if not target.get("why_it_matters") and rel.get("why_it_matters"):
            target["why_it_matters"] = rel["why_it_matters"]
        if not target.get("uncertainties") and rel.get("uncertainties"):
            target["uncertainties"] = rel["uncertainties"]
        if not target.get("current_status") and rel.get("current_status_detail"):
            target["current_status"] = rel["current_status_detail"]
        if not target.get("formation_background") and rel.get("formation_background"):
            target["formation_background"] = rel["formation_background"]
        target["relation_maturity"] = final
        target["maturity_basis"] = reason
        target["maturity_assessed_at"] = TODAY

        assignments.append({
            "relationship_id": rid,
            "relationship_type": rtype,
            "default_by_type": default,
            "assigned": final,
            "downshifted": default != final,
            "reason": reason,
            "evidence_items": len(ev_idx.get(rid, [])),
        })

    # ---------------- step 8: summary-only re-audit ----------------
    # Relations carrying an explicit Content Pack maturity target are exempt:
    # the packet is the highest factual authority and its targets are locked.
    # They are still inspected, and any thin profile is backfilled from the
    # relationship object so the badge is visibly substantiated.
    override_targets = {
        ov["relationship_id"]: ov.get("target_maturity")
        for ov in pack["core_relation_overrides"]
        if ov.get("target_maturity")
    }

    summary_only_audit: list[dict] = []
    for rid, prof in rprofiles.items():
        mat = prof.get("relation_maturity")
        if mat not in (R2, R3):
            continue
        if prof.get("asip_analysis") or prof.get("evolution_stages"):
            continue
        if len(txt(prof.get("overview"))) >= 60:
            continue
        rel = next((r for r in rels if r["relationship_id"] == rid), {})

        if rid in override_targets:
            # Backfill visible content from already-sourced relationship fields.
            backfilled = []
            for pkey, rkey in (
                ("overview", "relation_summary"),
                ("formation_background", "formation_background"),
                ("current_status", "current_status_detail"),
                ("why_it_matters", "why_it_matters"),
                ("uncertainties", "uncertainties"),
            ):
                if not substantive(prof.get(pkey)) and substantive(rel.get(rkey)):
                    prof[pkey] = rel[rkey]
                    backfilled.append(pkey)
            if not prof.get("source_ids") and rel.get("source_refs"):
                prof["source_ids"] = list(rel["source_refs"])
                backfilled.append("source_ids")
            summary_only_audit.append({
                "relationship_id": rid,
                "maturity_before": mat,
                "verdict": "retained_packet_locked",
                "note": (
                    "Content Pack explicitly targets "
                    f"{override_targets[rid]}; badge locked. Profile backfilled "
                    f"from existing sourced relationship fields: {backfilled or 'none needed'}"
                ),
            })
            continue

        ok2, gaps2 = r2_capable(rel, prof)
        before = mat
        if ok2 and mat == R2:
            verdict = "retained_R2"
            note = "thin overview but full R2 field coverage on the relationship object"
        else:
            prof["relation_maturity"] = R1
            prof["maturity_basis"] = f"summary-only re-audit downshift — {'; '.join(gaps2) or 'insufficient developed content'}"
            prof["maturity_assessed_at"] = TODAY
            verdict = "downshifted_to_R1"
            note = "; ".join(gaps2) or "summary-only content cannot substantiate a developed badge"
            limitations.append({
                "object_id": rid,
                "object_type": "relationship",
                "default_maturity": before,
                "assigned_maturity": R1,
                "limitation": "ACCEPTED_EVIDENCE_LIMITATION",
                "missing": gaps2 or ["developed analytical content"],
                "rationale": "Truthful downshift; badge must match content.",
            })
        summary_only_audit.append({
            "relationship_id": rid,
            "maturity_before": before,
            "verdict": verdict,
            "note": note,
        })

    # ---------------- step 9: staleness temporal handling ----------------
    packet_refreshed = {
        ov["relationship_id"] for ov in pack["core_relation_overrides"]
    }
    stale_handling: list[dict] = []
    for rel in rels:
        if rel.get("freshness_status") != "stale":
            continue
        rid = rel["relationship_id"]
        prof = rprofiles.setdefault(rid, {})
        closed = bool(rel.get("time_end"))
        sensitive = bool(rel.get("temporal_sensitive"))

        if rid in packet_refreshed:
            cls = "REFRESHED_BY_PACKET"
            disclosure = (
                f"本关系的当前状态已由 Depth G 内容包在 {TODAY} 重新核对并更新。"
            )
            rel["freshness_status"] = "current"
            rel["current_status_verified_at"] = TODAY
        elif closed:
            cls = "HISTORICAL_CLOSED"
            disclosure = (
                f"本关系是已封闭的历史阶段（{rel.get('time_start') or '?'}—{rel.get('time_end')}），"
                f"不描述当前状态；其内容按历史记录阅读，claim 有效期为 "
                f"{rel.get('claim_valid_as_of') or '见来源'}。"
            )
            rel["freshness_status"] = "historical"
        elif sensitive:
            cls = "AGING_MONITORED"
            disclosure = (
                f"本关系属时间敏感内容，最后一次可核实的 claim 有效期为 "
                f"{rel.get('claim_valid_as_of') or '未标注'}，此后未获新公开来源确认。"
                f"读者应将其视为“最后已知状态”，而不是 {TODAY} 的实时状态。"
            )
        else:
            cls = "AGING_MONITORED"
            disclosure = (
                f"本关系的结构性描述保持有效，但最后核实时间为 "
                f"{rel.get('claim_valid_as_of') or rel.get('last_verified_at') or '未标注'}，"
                f"细节可能已发生变化。"
            )

        rel["temporal_handling"] = cls
        rel["temporal_disclosure"] = disclosure
        prof["temporal_handling"] = cls
        prof["temporal_disclosure"] = disclosure
        stale_handling.append({
            "relationship_id": rid,
            "classification": cls,
            "time_start": rel.get("time_start"),
            "time_end": rel.get("time_end"),
            "claim_valid_as_of": rel.get("claim_valid_as_of"),
            "temporal_sensitive": sensitive,
        })

    # ---------------- reporting ----------------
    dist = collections.Counter(
        rprofiles[r["relationship_id"]].get("relation_maturity")
        for r in rels
        if r["relationship_id"] in rprofiles
    )
    unmatured = [
        r["relationship_id"]
        for r in rels
        if not rprofiles.get(r["relationship_id"], {}).get("relation_maturity")
    ]

    audit = {
        "audit_id": "depth-g-relation-closure",
        "assigned_at": TODAY,
        "dynamic_assignment": {
            "count": len(assignments),
            "downshifted": sum(1 for a in assignments if a["downshifted"]),
            "unknown_types_defaulted_to_R1": sorted(set(unknown_types)),
            "assignments": assignments,
        },
        "summary_only_reaudit": {
            "count": len(summary_only_audit),
            "downshifted": sum(1 for s in summary_only_audit if s["verdict"] == "downshifted_to_R1"),
            "entries": summary_only_audit,
        },
        "staleness_handling": {
            "count": len(stale_handling),
            "by_classification": dict(collections.Counter(s["classification"] for s in stale_handling)),
            "entries": stale_handling,
        },
        "final_distribution": {k: v for k, v in sorted(dist.items(), key=lambda x: str(x[0]))},
        "relations_total": len(rels),
        "relations_without_maturity": unmatured,
        "gate_pass": not unmatured and len(rels) == 150,
        "applied": bool(args.apply),
    }

    ART.mkdir(parents=True, exist_ok=True)
    (ART / "relation-closure-audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ART / "accepted-evidence-limitations.json").write_text(
        json.dumps(
            {
                "generated_at": TODAY,
                "policy": pack["closure_standard"]["source_count_rule"],
                "count": len(limitations),
                "limitations": limitations,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if args.apply:
        dump("relationships.json", rels_doc)
        dump("relation_profiles.json", rprof_doc)

    print(f"dynamic assignments : {len(assignments)} (downshifted {audit['dynamic_assignment']['downshifted']})")
    print(f"summary-only audited: {len(summary_only_audit)}")
    print(f"stale handled       : {len(stale_handling)} {audit['staleness_handling']['by_classification']}")
    print(f"accepted limitations: {len(limitations)}")
    print(f"final distribution  : {audit['final_distribution']}")
    print(f"without maturity    : {len(unmatured)}")
    print(f"gate_pass           : {audit['gate_pass']}")
    return 0 if audit["gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
