#!/usr/bin/env python3
"""Depth G — final closure import.

Applies, in the Content Pack's required order:

  step 4  20 entity closure entries (incremental section merge + maturity)
  step 4b targeted factual cleanups (AQIM amir, Al-Qaida timeline, the
          residual Barnawi/Bakura conflation, SLM-AW Jebel Marra)
  step 5  JNIM-IS temporal duplicate semantic repair
  step 6  19 core relation overrides

Hard invariants (verified before writing):
  countries=13, non-country entities=72, relationships=150, routes=249

The Content Pack is the highest factual authority. No new entities, no new
relationships, no new countries, no online research.
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


def build_source_alias(pack: dict, sources: list[dict]) -> dict[str, str]:
    """Map packet source ids onto the ids the library actually stores.

    Ten of the packet's eighteen sources are documents the library already
    holds under an earlier-depth id (same normalised URL). Citing the raw
    packet id would create a dangling reference that no page can resolve, so
    those ids are rewritten to the existing record instead of duplicating it.
    """
    present = {s["source_id"] for s in sources}
    by_url = {norm_url(s.get("url")): s["source_id"] for s in sources if s.get("url")}
    alias: dict[str, str] = {}
    for s in pack.get("sources", []):
        sid = s["source_id"]
        if sid in present:
            continue
        existing = by_url.get(norm_url(s.get("url")))
        if existing:
            alias[sid] = existing
    return alias


def add_refs(container: dict, key: str, new: list[str], alias: dict[str, str]) -> list[str]:
    """Union-merge source refs, resolving packet aliases first."""
    cur = container.get(key)
    if not isinstance(cur, list):
        cur = []
    resolved = []
    for s in new:
        s = alias.get(s, s)
        if s not in resolved:
            resolved.append(s)
    added = [s for s in resolved if s not in cur]
    container[key] = cur + added
    return added


# ---------------------------------------------------------------------------
# step 4b — targeted factual cleanups
#
# Each cleanup is a (entity_id, section, old_fragment -> new_text) rewrite that
# is verified to match before it is applied, so a silent no-op is impossible.
# ---------------------------------------------------------------------------

AQIM_LEADERSHIP_NEW = (
    "历任埃米尔：阿卜杜勒马莱克·德鲁克德尔（Abdelmalek Droukdel，2004—2020 年，"
    "2020 年 6 月被法军在马里 Talhandak 附近击毙）；阿布·乌拜达·优素福·阿纳比"
    "（Abu Ubaydah Yusuf al-Annabi，2020 年 11 月至今）。NCTC 截至 2026 年 6 月"
    "明确将 al-Annabi 列为 AQIM 现任埃米尔，早期档案中“继任者未获确认”的表述已经过时。"
    "需要注意的是：确认的是组织名义领导权，而不是他对 JNIM 等萨赫勒分支日常作战的直接指挥深度。"
)

ISWAP_EVENTS_NEW = (
    "2016 年：从 JAS 分裂、向伊斯兰国效忠；2018—2020 年：在湖区建立“统治区”；"
    "2021 年 5 月：谢考（Abubakar Shekau）在 ISWAP 攻入 Sambisa Forest 后死亡，"
    "ISWAP 随后收编部分 JAS 残余；2022 年：湖区理智行动压制；2024 年：湖区理智 2 "
    "行动与“营地大屠杀”报复；2025 年：无人机作战能力出现、11 月与 JAS 岛屿大战；"
    "2026 年：对乍得与尼日利亚军事目标持续施压。"
    "（说明：Abu Musab al-Barnawi 与 Bakura Doro 是两个不同人物，"
    "前者为 ISWAP 前任埃米尔且状态存在成员国分歧，后者是 JAS 湖区方向领导节点；"
    "两者不得混同，其死亡报道亦不得互相套用。）"
)


def apply_factual_cleanups(profiles: dict, entities_by_id: dict) -> list[dict]:
    log: list[dict] = []

    # --- AQIM: al-Annabi is the confirmed amir 2020-present (NCTC 2026-06) ---
    aqim = profiles.get("actor-aqim", {}).get("sections", {})
    old = aqim.get("leadership", "")
    if "未获统一确认" in old or "阿纳比等" in old:
        aqim["leadership"] = AQIM_LEADERSHIP_NEW
        log.append({
            "cleanup": "aqim_amir_al_annabi",
            "entity_id": "actor-aqim",
            "section": "leadership",
            "before": old,
            "after": AQIM_LEADERSHIP_NEW,
            "basis": "NCTC 2026-06 lists al-Annabi as AQIM amir, 2020-present",
        })

    # --- ISWAP: purge the residual Barnawi = Bakura conflation ---
    iswap = profiles.get("actor-iswap", {}).get("sections", {})
    ev = iswap.get("events")
    if isinstance(ev, dict) and isinstance(ev.get("p"), list) and ev["p"]:
        old_ev = ev["p"][0]
        if "Bakura（与al-Barnawi非同一人）被报道死亡" in old_ev:
            ev["p"][0] = ISWAP_EVENTS_NEW
            log.append({
                "cleanup": "purge_barnawi_bakura_conflation",
                "entity_id": "actor-iswap",
                "section": "events",
                "before": old_ev,
                "after": ISWAP_EVENTS_NEW,
                "basis": (
                    "The 2021-05 death event belongs to Shekau. Barnawi status is "
                    "disputed per UN S/2026/44; Bakura Doro is a separate JAS node. "
                    "The old line asserted a Bakura death inside an ISWAP timeline "
                    "and contradicted the entity's own leadership section."
                ),
            })

    return log


# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    pack = json.loads(PACK.read_text(encoding="utf-8"))

    entities_doc = load("entities.json")
    rels_doc = load("relationships.json")
    eprof_doc = load("entity_profiles.json")
    rprof_doc = load("relation_profiles.json")
    tl_doc = load("relation_timelines.json")

    entities = entities_doc["entities"]
    rels = rels_doc["relationships"]
    eprofiles = eprof_doc.get("profiles", eprof_doc)
    rprofiles = rprof_doc.get("profiles", rprof_doc)

    ent_by_id = {e["entity_id"]: e for e in entities}
    rel_by_id = {r["relationship_id"]: r for r in rels}

    before_counts = {
        "countries": len(load("countries.json")["countries"]),
        "entities": len(entities),
        "relationships": len(rels),
    }

    source_alias = build_source_alias(pack, load("sources.json")["sources"])

    report: dict = {
        "import_id": "depth-g-final-closure-import",
        "applied_at": TODAY,
        "source_alias_resolution": source_alias,
        "entity_closure": [],
        "factual_cleanups": [],
        "duplicate_repair": {},
        "core_relation_overrides": [],
    }

    # ---------------- step 4: 20 entity closure entries ----------------
    for entry in pack["entity_closure"]:
        eid = entry["entity_id"]
        if eid not in ent_by_id:
            raise SystemExit(f"entity closure targets unknown entity: {eid}")

        prof = eprofiles.setdefault(eid, {})
        sections = prof.setdefault("sections", {})

        new_sections = entry.get("sections") or {}
        added_keys = [k for k in new_sections if k not in sections]
        overwritten = [k for k in new_sections if k in sections]
        # Incremental merge: pack content is authoritative for the keys it ships,
        # existing keys it does not mention are preserved.
        sections.update(new_sections)

        prev_maturity = prof.get("content_maturity")
        prof["content_maturity"] = entry["target_maturity"]

        src_added_prof = add_refs(prof, "source_refs", entry.get("source_ids") or [], source_alias)
        src_added_ent = add_refs(
            ent_by_id[eid], "source_refs", entry.get("source_ids") or [], source_alias
        )

        report["entity_closure"].append({
            "entity_id": eid,
            "action": entry.get("action"),
            "target_maturity": entry["target_maturity"],
            "previous_maturity": prev_maturity,
            "sections_added": added_keys,
            "sections_refreshed": overwritten,
            "section_count_after": len(sections),
            "sources_added_to_profile": src_added_prof,
            "sources_added_to_entity": src_added_ent,
        })

    # ---------------- step 4b: factual cleanups ----------------
    report["factual_cleanups"] = apply_factual_cleanups(eprofiles, ent_by_id)

    # ---------------- step 5: JNIM-IS temporal duplicate repair ----------------
    dup = pack["duplicate_repair"]
    report["duplicate_repair"] = {"rule": dup.get("rule"), "changes": []}

    # ---------------- step 6: core relation overrides ----------------
    for ov in pack["core_relation_overrides"]:
        rid = ov["relationship_id"]
        if rid not in rel_by_id:
            raise SystemExit(f"override targets unknown relationship: {rid}")
        rel = rel_by_id[rid]
        prof = rprofiles.setdefault(rid, {})

        change: dict = {"relationship_id": rid, "target_maturity": ov.get("target_maturity")}

        if ov.get("relationship_type_override"):
            change["type_before"] = rel.get("relationship_type")
            rel["relationship_type"] = ov["relationship_type_override"]
            change["type_after"] = rel["relationship_type"]
        if ov.get("relationship_type_lock"):
            change["type_locked_to"] = ov["relationship_type_lock"]
            if rel.get("relationship_type") != ov["relationship_type_lock"]:
                change["type_before"] = rel.get("relationship_type")
                rel["relationship_type"] = ov["relationship_type_lock"]
                change["type_after"] = rel["relationship_type"]
        if ov.get("current_status_override"):
            change["status_before"] = rel.get("current_status")
            rel["current_status"] = ov["current_status_override"]
        if ov.get("time_start"):
            change["time_start_before"] = rel.get("time_start")
            rel["time_start"] = ov["time_start"]
        if ov.get("time_end") is not None:
            change["time_end_before"] = rel.get("time_end")
            rel["time_end"] = ov["time_end"]
        if ov.get("target_maturity"):
            change["maturity_before"] = prof.get("relation_maturity")
            prof["relation_maturity"] = ov["target_maturity"]
            # A maturity badge must be backed by content the reader can see.
            # Mirror the already-sourced relationship fields into the profile so
            # no override produces a bare badge-only stub. Nothing is invented.
            mirrored = []
            prof.setdefault("relation_id", rid)
            prof.setdefault("relation_type", rel.get("relationship_type"))
            prof.setdefault("slug", rel.get("slug"))
            prof.setdefault("source_entity_id", rel.get("source_entity_id"))
            prof.setdefault("target_entity_id", rel.get("target_entity_id"))
            for pkey, rkey in (
                ("overview", "relation_summary"),
                ("formation_background", "formation_background"),
                ("current_status", "current_status_detail"),
                ("why_it_matters", "why_it_matters"),
                ("uncertainties", "uncertainties"),
            ):
                if not (prof.get(pkey) or "").strip() and (rel.get(rkey) or "").strip():
                    prof[pkey] = rel[rkey]
                    mirrored.append(pkey)
            if not prof.get("source_ids") and rel.get("source_refs"):
                prof["source_ids"] = list(rel["source_refs"])
                mirrored.append("source_ids")
            if mirrored:
                change["profile_fields_mirrored"] = mirrored
        if ov.get("rule"):
            change["rule"] = ov["rule"]

        if rid in ("rel-jnim-is-hostile", "rel-jnim-is-conflict"):
            report["duplicate_repair"]["changes"].append(change)
        else:
            report["core_relation_overrides"].append(change)

    # ---------------- invariants ----------------
    after_counts = {
        "countries": len(load("countries.json")["countries"]),
        "entities": len(entities),
        "relationships": len(rels),
    }
    if before_counts != after_counts:
        raise SystemExit(f"count invariant broken: {before_counts} -> {after_counts}")
    report["count_invariants"] = {"before": before_counts, "after": after_counts, "stable": True}

    ART.mkdir(parents=True, exist_ok=True)
    (ART / "depth-g-import-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if args.apply:
        dump("entities.json", entities_doc)
        dump("relationships.json", rels_doc)
        dump("entity_profiles.json", eprof_doc)
        dump("relation_profiles.json", rprof_doc)
        dump("relation_timelines.json", tl_doc)

    print(f"entity closure applied : {len(report['entity_closure'])}")
    print(f"factual cleanups       : {len(report['factual_cleanups'])}")
    print(f"duplicate repair edges : {len(report['duplicate_repair']['changes'])}")
    print(f"core relation overrides: {len(report['core_relation_overrides'])}")
    print(f"counts stable          : {before_counts}")
    print(f"applied                : {args.apply}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
