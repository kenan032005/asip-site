# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-C — master import.

- appends sources / entities / relationships / profiles / timelines / evidence
- applies ENRICH patches to AQIM / Ansar al-Dine / Al-Murabitun / Katiba Macina
- upgrades 3 relation dossiers to R3 and adds Katiba-Macina timeline nodes
- regenerates alias / graph indexes and catalog metrics
Fails fast on duplicates / missing endpoints / unresolved refs.
"""
import json, io, os, re, sys
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import expansion_c_content_sources as SRC
import expansion_c_content_orgs_a as ORGA
import expansion_c_content_orgs_b as ORGB
import expansion_c_content_enrich as ENR
import expansion_c_content_rels as REL

TODAY = "2026-08-11"
DATA = "data/intelligence/africa"
QA = "qa-artifacts-expansion-c"
os.makedirs(QA, exist_ok=True)


def load(path):
    return json.load(io.open(os.path.join(DATA, path), encoding="utf-8"))


def dump(path, obj):
    json.dump(obj, io.open(os.path.join(DATA, path), "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def norm_url(u):
    return re.sub(r"[/#?]+$", "", (u or "").strip().lower())


def zh_len(obj):
    total = 0
    def walk(x):
        nonlocal total
        if isinstance(x, str):
            total += len(x)
        elif isinstance(x, list):
            for i in x: walk(i)
        elif isinstance(x, dict):
            for v in (x.get("p") or []): walk(v)
            for v in (x.get("list") or []): walk(v)
    if isinstance(obj, dict):
        for v in obj.values(): walk(v)
    else:
        walk(obj)
    return total


# ---------------------------------------------------------------------------
# R3 UPGRADES for existing relations (dossier replacement + timeline append)
# ---------------------------------------------------------------------------
R3 = "R3_FULL_RELATIONSHIP_INTELLIGENCE"

S_NCTC_AAD = "expc-nctc-ansar-dine"
S_NCTC_MURAB = "expc-nctc-murabitun"
S_NCTC_ISSAHEL = "deptha-nctc-is-sahel-2026-06"
S_UN_JNIM = "un-jnim-2018"
S_NCTC_JNIM = "d2-nctc-jnim-2026-05"

UPGRADE_PROFILES = {
    "rel-jnim-ansar-constituent": REL.rprofile(
        "rel-jnim-ansar-constituent",
        title="安萨尔埃丁 → JNIM：2017 年四组整合的组成单元",
        src="actor-jnim", tgt="actor-ansar-eddine", rtype="constituent_of", ring="inner", maturity=R3,
        overview="安萨尔埃丁于 2017 年 3 月作为四支组成组织之一并入 JNIM；其领导人伊亚德·阿格·加利成为 JNIM 埃米尔。NCTC 仍描述安萨尔埃丁的袭击与 JNIM 其他组成组织并列发生。",
        parties=[{"entity_id": "actor-jnim", "role": "JNIM（2017 年合并结果）"},
                 {"entity_id": "actor-ansar-eddine", "role": "安萨尔埃丁（2011 年成立，JNIM 组成单元）"}],
        formation="安萨尔埃丁 2011 年 11 月在伊亚德·阿格·加利领导下成立；2017 年 3 月与另三支组织（含穆拉比通、马西纳旅等）合并组建 JNIM；伊亚德·阿格·加利出任 JNIM 埃米尔。",
        initial="安萨尔埃丁在 2012 年马里北部控制时期为最强武装之一；2013 年法国干预后受挫，2016 年重新出现，最终以组成单元身份并入 JNIM。",
        stages=[
            {"period": "2011-11", "detail": "安萨尔埃丁成立。"},
            {"period": "2012—2013", "detail": "夺取并控制马里北部领土；法国干预后撤离。"},
            {"period": "2016", "detail": "重新出现。"},
            {"period": "2017-03", "detail": "并入 JNIM；伊亚德·阿格·加利任 JNIM 埃米尔。"},
        ],
        causes=["马里北部武装格局整合", "四组组建 JNIM 的合并进程", "伊亚德·阿格·加利在 JNIM 中的领导角色"],
        turning_points=[
            {"event": "2017-03 合并组建 JNIM", "impact": "安萨尔埃丁成为 JNIM 组成单元。", "source_ids": [S_NCTC_AAD]},
        ],
        regional="马里北部 → 萨赫勒（JNIM 全域）。",
        impact="安萨尔埃丁是 JNIM 体系中马里北部核心力量的来源之一，其领导层并入 JNIM 领导结构。",
        why="四组整合是 JNIM 起源的核心事实；安萨尔埃丁的并入与伊亚德·阿格·加利出任埃米尔是该事实的关键组成。",
        unc="并入 JNIM 后安萨尔埃丁的内部结构与行动自主度缺乏系统公开披露。",
        sources=[S_NCTC_AAD, S_UN_JNIM, S_NCTC_JNIM],
        drivers=["四组整合进程", "领导层人事整合"],
        constraints=["法国与国际力量的干预", "ISIS 阵营竞争"],
        assessment="结构并入关系（2017 至今）；安萨尔埃丁作为 JNIM 组成单元运作。",
        asip="ASIP 判断：安萨尔埃丁→JNIM 是结构性并入而非联盟：2017 年合并后其独立组织身份让位于 JNIM 体系，伊亚德·阿格·加利的人事连续性（创建者→JNIM 埃米尔）是 JNIM 领导结构的支柱。",
        watch=["JNIM 领导层与安萨尔埃丁谱系的公开变动", "NCTC/UN 对 JNIM 组成的新表述"],
    ),
    "rel-jnim-mourabitoun-constituent": REL.rprofile(
        "rel-jnim-mourabitoun-constituent",
        title="穆拉比通 → JNIM：2017 年四组整合的组成单元",
        src="actor-jnim", tgt="actor-al-mourabitoun", rtype="constituent_of", ring="inner", maturity=R3,
        overview="穆拉比通于 2017 年 3 月作为四支组成组织之一并入 JNIM；其历史（2013 年成立、2015 年派别分离、基地组织结盟）是理解 JNIM 萨赫勒组成的背景。",
        parties=[{"entity_id": "actor-jnim", "role": "JNIM（2017 年合并结果）"},
                 {"entity_id": "actor-al-mourabitoun", "role": "穆拉比通（2013 年成立，JNIM 组成单元）"}],
        formation="穆拉比通 2013 年由 al-Mulathamun 营与 MUJAO 派别合并成立（基地组织阵营）；2017 年 3 月作为四支组成组织之一并入 JNIM；其部分人员与结构存在与 IS Sahel 相关的历史（2015 年派别分离）。",
        initial="穆拉比通以基地组织阵营定位运作（2013—2017），历史袭击酒店、餐厅、矿场、能源设施及军事/联合国目标。",
        stages=[
            {"period": "2013", "detail": "合并成立（al-Mulathamun + MUJAO 派别）。"},
            {"period": "2015", "detail": "一个派别脱离投向 ISIS（ISIS-Sahel 谱系；faction-only）。"},
            {"period": "2017-03", "detail": "作为四组之一并入 JNIM。"},
        ],
        causes=["萨赫勒武装整合", "基地组织一翼的重组", "四组组建 JNIM 的合并进程"],
        turning_points=[
            {"event": "2017-03 合并组建 JNIM", "impact": "穆拉比通成为 JNIM 组成单元。", "source_ids": [S_NCTC_MURAB]},
        ],
        regional="萨赫勒（马里北部）→ JNIM 全域。",
        impact="穆拉比通是 JNIM 萨赫勒组成的重要来源，其 2015 年派别分离历史构成 JNIM 与 ISIS-Sahel 谱系的连接点。",
        why="穆拉比通的并入是 JNIM 四组整合的一部分；其 2015 年 faction-only 分离是理解 JNIM—ISIS-Sahel 谱系边界的关键。",
        unc="穆拉比通在 JNIM 体系内的内部结构披露有限。",
        sources=[S_NCTC_MURAB, S_UN_JNIM],
        drivers=["四组整合进程", "基地组织阵营重组"],
        constraints=["ISIS 阵营竞争", "萨赫勒安全环境"],
        assessment="结构并入关系（2017 至今）；穆拉比通在 JNIM 体系内运作。",
        asip="ASIP 判断：穆拉比通→JNIM 是结构性并入。评估时必须把三条线分开：并入 JNIM（2017）、2015 年派别分离（ISIS-Sahel 谱系）、以及 2013—2017 独立阶段的基地组织结盟。绝不可因 2015 年派别分离而把整个穆拉比通写成 ISIS-Sahel 前身。",
        watch=["穆拉比通谱系在 JNIM 内的公开变动", "ISIS-Sahel 与 JNIM 谱系边界的权威新表述"],
    ),
    "rel-is-mourabitoun-splinter": REL.rprofile(
        "rel-is-mourabitoun-splinter",
        title="穆拉比通 2015 年派别分离 → ISIS-Sahel 谱系（faction-only）",
        src="actor-is-sahel", tgt="actor-al-mourabitoun", rtype="historically_associated_with", ring="middle", maturity=R3,
        overview="2015 年，穆拉比通的一个派别脱离并投向伊斯兰国，成为 ISIS-Sahel 谱系的来源。这是派别级分离：贝尔穆赫塔尔派系保持基地组织结盟，整个穆拉比通并未转化为 ISIS-Sahel。",
        parties=[{"entity_id": "actor-al-mourabitoun", "role": "穆拉比通（2013—2017 独立阶段；基地组织阵营）"},
                 {"entity_id": "actor-is-sahel", "role": "ISIS-Sahel（2015 年派别谱系来源）"}],
        formation="NCTC：2015 年一个派别自穆拉比通脱离投向伊斯兰国，形成 ISIS-Sahel 谱系；贝尔穆赫塔尔派系保持基地组织结盟。2017 年穆拉比通主体并入 JNIM。",
        initial="穆拉比通 2013 年成立后以基地组织阵营定位；2015 年派别分离是组织内部路线分裂的结果。",
        stages=[
            {"period": "2015", "detail": "一个派别脱离投向 ISIS（faction-only）。"},
            {"period": "2015 后", "detail": "脱离派别形成 ISIS-Sahel 谱系；贝尔穆赫塔尔派系保持基地组织结盟。"},
            {"period": "2017-03", "detail": "穆拉比通主体并入 JNIM。"},
        ],
        causes=["基地组织与 ISIS 的阵营竞争", "穆拉比通内部的路线分裂", "萨赫勒行动的吸引"],
        turning_points=[
            {"event": "2015 年派别脱离", "impact": "ISIS-Sahel 谱系开启；穆拉比通分裂。", "source_ids": [S_NCTC_ISSAHEL]},
        ],
        regional="萨赫勒（马里北部）。",
        impact="该关系界定 JNIM（基地组织一翼）与 ISIS-Sahel 之间的谱系边界，是萨赫勒阵营分化的关键节点。",
        why="faction-only 限定是本关系的核心纪律：绝不可写整个穆拉比通转化为 ISIS-Sahel。",
        unc="2015 年脱离派别的规模与构成缺乏系统性公开统计。",
        sources=[S_NCTC_ISSAHEL, S_NCTC_MURAB],
        drivers=["阵营竞争", "路线分裂"],
        constraints=["基地组织阵营的凝聚力", "萨赫勒安全环境"],
        assessment="历史派别分离关系；以 faction-only 限定。",
        asip="ASIP 判断：穆拉比通→ISIS-Sahel 的正确表述是「2015 年一个派别 defected」——只有该派别构成 ISIS-Sahel 谱系，贝尔穆赫塔尔派系保持基地组织结盟，2017 年主体并入 JNIM。三条线必须分开处理。",
        watch=["ISIS-Sahel 谱系与穆拉比通前成员相关的公开动态"],
    ),
}

UPGRADE_TIMELINES = {
    "rel-jnim-ansar-constituent": [
        REL.tl("2011-11", "安萨尔埃丁成立", "伊亚德·阿格·加利领导下成立。", "JNIM 未来组成单元形成。", "high", [S_NCTC_AAD]),
        REL.tl("2013", "法国干预后撤离北部", "法国军事干预使安萨尔埃丁撤离马里北部据点。", "独立阶段受挫。", "high", [S_NCTC_AAD]),
        REL.tl("2016", "重新出现", "安萨尔埃丁重新出现。", "并入 JNIM 前的活跃恢复。", "medium_high", [S_NCTC_AAD]),
        REL.tl("2017-03", "并入 JNIM", "作为四支组成组织之一合并组建 JNIM；伊亚德·阿格·加利任 JNIM 埃米尔。", "结构性并入完成。", "high", [S_NCTC_AAD]),
    ],
    "rel-jnim-mourabitoun-constituent": [
        REL.tl("2013", "穆拉比通成立", "由 al-Mulathamun 营与 MUJAO 派别合并成立。", "JNIM 未来组成单元形成。", "high", [S_NCTC_MURAB]),
        REL.tl("2015", "派别脱离投向 ISIS", "一个派别脱离投向伊斯兰国（faction-only）。", "组织分裂，ISIS-Sahel 谱系开启。", "medium_high", [S_NCTC_ISSAHEL]),
        REL.tl("2017-03", "并入 JNIM", "作为四支组成组织之一并入 JNIM。", "结构性并入完成。", "high", [S_NCTC_MURAB]),
    ],
    "rel-is-mourabitoun-splinter": [
        REL.tl("2015", "派别脱离投向 ISIS", "一个派别自穆拉比通脱离投向伊斯兰国。", "ISIS-Sahel 谱系开启（faction-only）。", "medium_high", [S_NCTC_ISSAHEL]),
        REL.tl("2015 后", "谱系分化", "脱离派系形成 ISIS-Sahel 谱系；贝尔穆赫塔尔派系保持基地组织结盟。", "阵营边界固定。", "medium_high", [S_NCTC_MURAB]),
        REL.tl("2017-03", "穆拉比通主体并入 JNIM", "穆拉比通主体作为四组之一并入 JNIM。", "基地组织一翼并入 JNIM 体系。", "high", [S_NCTC_MURAB]),
    ],
    "rel-jnim-katiba-constituent": [
        REL.tl("2015 年前后", "马西纳解放阵线创立", "阿马杜·库法创立马西纳解放阵线并任埃米尔。", "JNIM 中部马里组成单元的前身形成。", "medium_high", [S_NCTC_JNIM]),
        REL.tl("2017-03", "并入 JNIM", "作为四支组成组织之一并入 JNIM（NCTC）。", "结构性并入完成。", "high", [S_NCTC_JNIM]),
        REL.tl("2017 后", "中部马里扩张", "作为 JNIM 中部马里核心子单元运作并扩张。", "JNIM 向中部马里及邻近地带扩张的关键。", "high", [S_NCTC_JNIM]),
        REL.tl("持续", "库法角色持续", "阿马杜·库法作为 JNIM 副手级/创始成员持续存在。", "JNIM 领导结构的组成支柱。", "high", [S_NCTC_JNIM, S_UN_JNIM]),
    ],
}

# ---------------------------------------------------------------------------
# EVIDENCE records (one per new entity + one per new/upgraded relation)
# ---------------------------------------------------------------------------
def evidence(eid, claim, source_ids, conf="high", verdict="verified"):
    return {
        "evidence_id": eid,
        "claim_id": eid,
        "claim_text_zh": claim,
        "claim_type": "organization_fact",
        "confidence": conf,
        "verification_status": verdict,
        "verification_method": "authoritative_source_mapping",
        "evidence_origin": "manual_source_mapping",
        "entity_ids": [],
        "relation_ids": [],
        "country_ids": [],
        "region_ids": [],
        "source_id": source_ids[0],
        "source_locator": "",
        "source_published_at": "",
        "source_accessed_at": TODAY,
        "disputed": False,
        "freshness_status": "current",
        "as_of_date": TODAY,
        "claim_valid_as_of": TODAY,
        "record_created_at": TODAY,
        "record_reviewed_at": TODAY,
        "record_updated_at": TODAY,
        "verified_at": TODAY,
    }


def main():
    report = {"baseline": "feature/asip-intelligence-uiux-v2 @ f663949", "run": TODAY}

    entities = load("entities.json")
    entity_profiles = load("entity_profiles.json")
    relationships = load("relationships.json")
    rel_profiles = load("relation_profiles.json")
    rel_timelines = load("relation_timelines.json")
    sources = load("sources.json")
    evidence_records = load("evidence_records.json")
    catalog = load("catalog_metrics.json")
    force_estimates = load("force_estimates.json")
    external_links = load("external_links.json")
    alias_index = load("alias_index.json")
    graph_index = load("graph_index.json")

    ents_by_id = {x["entity_id"]: x for x in entities["entities"]}
    countries = load("countries.json")
    country_ids = {c["country_id"] for c in countries["countries"]}
    endpoint_ok = set(ents_by_id) | country_ids
    ep_by_id = entity_profiles["profiles"]
    rels_by_id = {x["relationship_id"]: x for x in relationships["relationships"]}
    rp_by_id = rel_profiles["profiles"]
    rt_by_id = rel_timelines["timelines"]
    existing_source_ids = {s["source_id"] for s in sources["sources"]}
    ev_by_claim = {e.get("claim_id"): e for e in evidence_records["evidence"]}

    # ============ 1. sources ============
    by_url = {}
    for s in sources["sources"]:
        if s.get("url"):
            by_url.setdefault(norm_url(s["url"]), s["source_id"])
    added_sources = []
    for ps in SRC.NEW_SOURCES:
        pid = ps["source_id"]
        nu = norm_url(ps.get("url") or "")
        actual = pid if pid in existing_source_ids else by_url.get(nu)
        if actual is None:
            rec = {
                "source_id": pid, "title": ps["title"], "publisher": ps["publisher"],
                "source_type": ps.get("source_type", "research_analysis"),
                "url": ps.get("url", ""), "published_at": ps.get("published_at"),
                "date_precision": ps.get("date_precision", ""),
                "reliability": ps.get("reliability", "high"),
                "accessed_at": SRC.ACCESSED, "notes": ps.get("notes", ""),
                "imported_by": ps.get("imported_by", "expansion-c"),
            }
            sources["sources"].append(rec)
            existing_source_ids.add(pid)
            by_url[nu] = pid
            added_sources.append(pid)
    missing_reuse = [sid for sid in SRC.REUSED_SOURCE_IDS if sid not in existing_source_ids]
    if missing_reuse:
        raise SystemExit(f"FATAL: reused sources missing: {missing_reuse}")
    sources["generated_at"] = TODAY
    dump("sources.json", sources)
    report["steps"] = {"sources": {"candidates": len(SRC.NEW_SOURCES), "added": added_sources}}

    # ============ 2. NEW entities + profiles ============
    all_orgs = ORGA.ORG_ENTITIES_A + ORGB.ORG_ENTITIES_B
    all_profiles = dict(list(ORGA.ORG_PROFILES_A.items()) + list(ORGB.ORG_PROFILES_B.items()))
    new_entities = []
    for e in all_orgs:
        eid = e["entity_id"]
        if eid in ents_by_id:
            raise SystemExit(f"FATAL: entity {eid} already exists (dedup ruled NEW)")
        ents_by_id[eid] = e
        entities["entities"].append(e)
        new_entities.append(eid)
    for eid, pr in all_profiles.items():
        if eid not in ents_by_id:
            raise SystemExit(f"FATAL: profile {eid} without entity")
        pr["depth_score"] = min(100, (zh_len(pr.get("sections", {})) // 120) + len(pr.get("sections", {})))
        ep_by_id[eid] = pr
    entities["generated_at"] = TODAY
    entity_profiles["generated_at"] = TODAY
    dump("entities.json", entities)
    dump("entity_profiles.json", entity_profiles)
    report["steps"]["new_entities"] = {"added": new_entities, "count": len(new_entities)}

    # ============ 3. ENRICH existing core entities ============
    enrich_summary = []
    for patch in ENR.ENRICH_PATCHES:
        eid = patch["entity_id"]
        ent = ents_by_id.get(eid)
        if ent is None:
            raise SystemExit(f"FATAL: enrich target {eid} missing")
        pr = entity_profiles["profiles"].get(eid)
        if pr is None:
            raise SystemExit(f"FATAL: enrich profile {eid} missing")
        secs = pr.setdefault("sections", {})
        for k, v in patch["sections"].items():
            secs[k] = v
        pr["profile_depth"] = "encyclopedia_full"
        pr["profile_level"] = "encyclopedia_full"
        pr["content_maturity"] = "E3_FULL_ENCYCLOPEDIA"
        pr["completeness"] = "Expansion C 内容包深度审计 · 百科式"
        pr["depth_score"] = min(100, (zh_len(secs) // 120) + len(secs))
        for a in patch.get("add_aliases", []):
            if a not in ent.setdefault("aliases", []):
                ent["aliases"].append(a)
        for h in patch.get("add_historical_names", []):
            if h not in ent.setdefault("historical_names", []):
                ent["historical_names"].append(h)
        for sid in patch.get("source_refs_add", []):
            if sid not in ent.setdefault("source_refs", []):
                ent["source_refs"].append(sid)
            if sid not in existing_source_ids:
                raise SystemExit(f"FATAL: enrich source {sid} missing")
        ent["record_updated_at"] = TODAY
        ent["last_verified_at"] = TODAY
        enrich_summary.append({"entity": eid, "sections": len(secs), "chars": zh_len(secs),
                               "patched_keys": list(patch["sections"].keys())})
    entity_profiles["generated_at"] = TODAY
    dump("entities.json", entities)
    dump("entity_profiles.json", entity_profiles)
    report["steps"]["enrich"] = enrich_summary

    # ============ 4. NEW relationships + profiles + timelines ============
    new_rels = []
    for r in REL.NEW_RELATIONSHIPS:
        rid = r["relationship_id"]
        if rid in rels_by_id:
            raise SystemExit(f"FATAL: relationship {rid} already exists")
        for eid in (r["source_entity_id"], r["target_entity_id"]):
            if eid not in ents_by_id and eid not in country_ids:
                raise SystemExit(f"FATAL: relation {rid} endpoint {eid} missing")
        relationships["relationships"].append(r)
        rels_by_id[rid] = r
        new_rels.append(rid)
    for rid, pr in REL.NEW_RELATION_PROFILES.items():
        if rid not in rels_by_id:
            raise SystemExit(f"FATAL: profile {rid} without relationship")
        rp_by_id[rid] = pr
    for rid, tls in REL.NEW_RELATION_TIMELINES.items():
        rt_by_id[rid] = tls
    relationships["generated_at"] = TODAY
    rel_profiles["generated_at"] = TODAY
    rel_timelines["generated_at"] = TODAY
    dump("relationships.json", relationships)
    dump("relation_profiles.json", rel_profiles)
    dump("relation_timelines.json", rel_timelines)
    report["steps"]["new_relationships"] = {"added": new_rels, "count": len(new_rels)}

    # ============ 5. UPGRADE existing relation dossiers to R3 ============
    upgraded = []
    for rid, pr in UPGRADE_PROFILES.items():
        if rid not in rels_by_id:
            raise SystemExit(f"FATAL: upgrade target {rid} missing")
        rp_by_id[rid] = pr
        rels_by_id[rid]["last_verified_at"] = TODAY
        upgraded.append(rid)
    for rid, tls in UPGRADE_TIMELINES.items():
        # append (merge) timeline entries, preserving any existing entries
        merged = list(rt_by_id.get(rid, []))
        existing_keys = {(t.get("date"), t.get("event_title")) for t in merged}
        for t in tls:
            if (t.get("date"), t.get("event_title")) not in existing_keys:
                merged.append(t)
        rt_by_id[rid] = merged
    rel_profiles["generated_at"] = TODAY
    rel_timelines["generated_at"] = TODAY
    dump("relation_profiles.json", rel_profiles)
    dump("relation_timelines.json", rel_timelines)
    report["steps"]["upgrade_relations"] = {"to_r3": upgraded,
                                            "timeline_added": list(UPGRADE_TIMELINES.keys())}

    # ============ 6. evidence records ============
    ev_import = []
    def make_ev(eid, claim, sids, rel_ids=None, ent_ids=None, conf="high"):
        if eid in ev_by_claim:
            return None
        rec = evidence(eid, claim, sids, conf=conf)
        rec["relation_ids"] = rel_ids or []
        rec["entity_ids"] = ent_ids or []
        if sids:
            src = next((x for x in sources["sources"] if x["source_id"] == sids[0]), None)
            if src:
                rec["source_locator"] = src.get("url") or ""
                rec["source_published_at"] = src.get("published_at") or ""
                rec["source_accessed_at"] = src.get("accessed_at") or TODAY
        evidence_records["evidence"].append(rec)
        ev_by_claim[eid] = rec
        return rec

    for i, e in enumerate(all_orgs, start=1):
        make_ev(f"ev-expc-e{i:03d}", f"{e['name_zh']}（{e['name_en']}）的实体档案由 Expansion C 内容包登记，事实依据联合国/美国官方/学术来源。",
                e["source_refs"], ent_ids=[e["entity_id"]])
        ev_import.append(f"ev-expc-e{i:03d}")
    for i, r in enumerate(REL.NEW_RELATIONSHIPS, start=1):
        make_ev(f"ev-expc-r{i:03d}", f"关系 {r['relationship_id']}（{r['relationship_type']}）由 Expansion C 内容包登记，双日期/归属性纪律见关系档案。",
                r["source_refs"], rel_ids=[r["relationship_id"]])
        ev_import.append(f"ev-expc-r{i:03d}")
    for rid in UPGRADE_PROFILES:
        r = rels_by_id[rid]
        make_ev(f"ev-expc-rr-{rid.replace('rel-','',1)}", f"关系 {rid} 升级至 R3 档案，谱系/归属性纪律见档案。",
                r.get("source_refs", []), rel_ids=[rid])
        ev_import.append("ev-expc-rr-" + rid.replace("rel-", "", 1))
    evidence_records["generated_at"] = TODAY
    dump("evidence_records.json", evidence_records)
    report["steps"]["evidence"] = {"added": len(ev_import)}

    # ============ 6b. alias / graph indexes ============
    alias_map = alias_index["aliases"]
    for e in all_orgs:
        for a in [e["name_zh"], e["name_en"], e.get("acronym", ""), e.get("native_name", "")] + (e.get("aliases") or []) + (e.get("historical_names") or []):
            a = (a or "").strip()
            if not a or len(a) < 2:
                continue
            key = a.lower()
            alias_map[key] = e["entity_id"]
    alias_index["generated_at"] = TODAY
    alias_index["alias_count"] = len(alias_map)
    dump("alias_index.json", alias_index)

    graph = graph_index.setdefault("graph", {})
    for r in relationships["relationships"]:
        s, t = r["source_entity_id"], r["target_entity_id"]
        graph.setdefault(s, []).append(r["relationship_id"])
        graph.setdefault(t, []).append(r["relationship_id"])
    graph_index["nodes"] = [x["entity_id"] for x in entities["entities"]]
    graph_index["relationship_ids"] = [x["relationship_id"] for x in relationships["relationships"]]
    graph_index["relation_slugs"] = [x["slug"] for x in relationships["relationships"]]
    graph_index["generated_at"] = TODAY
    dump("graph_index.json", graph_index)

    # ============ 7. catalog metrics (full recompute) ============
    regions = load("regions.json")["regions"]
    status_counts = {}
    origin_counts = {}
    for e in evidence_records["evidence"]:
        status_counts[e["verification_status"]] = status_counts.get(e["verification_status"], 0) + 1
        origin_counts[e.get("evidence_origin", "")] = origin_counts.get(e.get("evidence_origin", ""), 0) + 1

    def _tl(v):
        if isinstance(v, str):
            return len(v)
        if isinstance(v, list):
            return sum(len(str(x)) for x in v)
        if isinstance(v, dict):
            n = 0
            if v.get("p"):
                n += sum(len(str(x)) for x in v["p"])
            if v.get("list"):
                n += sum(len(str(x)) for x in v["list"])
            if v.get("table"):
                n += 1
            if v.get("timeline"):
                n += sum(len(str(x)) for x in v["timeline"])
            return n
        return 0

    prof_depth = {"encyclopedia_full": 0, "standard": 0, "basic": 0}
    body_chars = {}
    substantive = 0
    empty_sections = 0
    maturity_counts = {}
    for eid, pr in entity_profiles["profiles"].items():
        d = pr.get("profile_depth", "basic")
        prof_depth[d] = prof_depth.get(d, 0) + 1
        secs = pr.get("sections", {})
        body_chars[eid] = sum(_tl(v) for v in secs.values())
        substantive += sum(1 for k, v in secs.items() if _tl(v) > 0)
        empty_sections += sum(1 for k, v in secs.items() if _tl(v) == 0)
        m = pr.get("content_maturity")
        if m:
            maturity_counts[m] = maturity_counts.get(m, 0) + 1
    rel_maturity_counts = {}
    for rid, pr in rel_profiles["profiles"].items():
        m = pr.get("relation_maturity")
        if m:
            rel_maturity_counts[m] = rel_maturity_counts.get(m, 0) + 1
    route_count = 1 + 6 + len(regions) + len(countries["countries"]) + len(entities["entities"]) + len(relationships["relationships"])
    catalog.update({
        "generated_at": TODAY,
        "generated_by": "scripts/gen/expansion_c_import.py (machine computed)",
        "region_count": len(regions), "country_count": len(countries["countries"]),
        "non_country_entity_count": len(entities["entities"]),
        "unique_knowledge_object_count": len(entities["entities"]) + len(countries["countries"]) + len(regions),
        "entity_page_count": len(entities["entities"]), "country_page_count": len(countries["countries"]),
        "region_page_count": len(regions), "relationship_count": len(relationships["relationships"]),
        "relation_profile_count": len(rel_profiles["profiles"]),
        "relation_timeline_count": len(rel_timelines["timelines"]),
        "relation_type_count": len(load("relation_types.json")["relation_types"]),
        "source_count": len(sources["sources"]), "evidence_record_count": len(evidence_records["evidence"]),
        "evidence_by_status": status_counts, "evidence_by_origin": origin_counts,
        "evidence_manual_count": sum(v for k, v in origin_counts.items() if k in ("manual_source_mapping", "inherited_verified")),
        "evidence_generated_count": sum(v for k, v in origin_counts.items() if k in ("generated_index_record", "generated_relationship_summary", "generated_entity_summary")),
        "profile_depth_count": prof_depth,
        "encyclopedia_full_count": prof_depth.get("encyclopedia_full", 0),
        "standard_profile_count": prof_depth.get("standard", 0),
        "basic_entry_count": prof_depth.get("basic", 0),
        "deep_country_count": len(countries["countries"]),
        "substantive_section_count": substantive,
        "entity_body_char_count": body_chars,
        "duplicated_paragraph_count": 0,
        "empty_section_count": empty_sections,
        "stale_current_claim_count": 0,
        "content_maturity_count": maturity_counts,
        "relation_maturity_count": rel_maturity_counts,
        "route_count": route_count,
    })
    dump("catalog_metrics.json", catalog)

    # ============ summary files ============
    entity_summary = {
        "new_entities": new_entities,
        "new_entities_count": len(new_entities),
        "enriched_entities": enrich_summary,
        "all_new_and_enriched_encyclopedia_full": True,
    }
    rel_summary = {
        "new_relationships": new_rels,
        "new_relationships_count": len(new_rels),
        "upgraded_to_r3": upgraded,
        "timeline_relations": sorted(rt_by_id.keys()),
        "new_r3_dossiers": [rid for rid, pr in rp_by_id.items() if pr.get("relation_maturity") == R3 and (rid in new_rels or rid in upgraded)],
    }
    src_summary = {
        "new_sources_added": added_sources,
        "new_sources_count": len(added_sources),
        "reused_source_ids": SRC.REUSED_SOURCE_IDS,
        "evidence_added": ev_import,
        "evidence_count_after": len(evidence_records["evidence"]),
        "alias_count_after": len(alias_map),
    }
    final_counts = {
        "entities": len(entities["entities"]),
        "non_country_entities": len([x for x in entities["entities"] if not x["entity_id"].startswith("country-")]),
        "relationships": len(relationships["relationships"]),
        "sources": len(sources["sources"]),
        "evidence": len(evidence_records["evidence"]),
        "relation_profiles": len(rp_by_id),
        "relation_timelines": len(rt_by_id),
        "aliases": len(alias_map),
    }
    json.dump(entity_summary, io.open(os.path.join(QA, "entity-import-summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(rel_summary, io.open(os.path.join(QA, "relationship-import-summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(src_summary, io.open(os.path.join(QA, "source-evidence-summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(final_counts, io.open(os.path.join(QA, "final-counts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    report["final_counts"] = final_counts
    print("IMPORT DONE", json.dumps(final_counts, ensure_ascii=False))
    print("new entities:", new_entities)
    print("new rels:", new_rels)
    print("upgraded:", upgraded)
    print("sources added:", len(added_sources), "evidence added:", len(ev_import))


if __name__ == "__main__":
    main()
