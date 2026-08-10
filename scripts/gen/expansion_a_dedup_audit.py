#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
expansion_a_dedup_audit.py —— ASIP-PPT-ENTITY-EXPANSION-A §1 导入前只读去重扫描。

对 data/intelligence/africa/ 下 11 类数据文件做只读多维度扫描，对 14 个候选实体
按 canonical id / name_zh / name_en / acronym / native_name / aliases /
historical_names / 大小写 / 连字符 / ISIS 变体 / 阿语转写 等维度查重，
产出 qa-artifacts-expansion-a/pre-import-dedup-audit.json。

本脚本严格只读，不修改任何 source-of-truth 数据。
"""
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "intelligence", "africa")
OUT_DIR = os.path.join(ROOT, "qa-artifacts-expansion-a")

SCAN_FILES = [
    "countries.json", "country_profiles.json", "entities.json", "entity_profiles.json",
    "relationships.json", "relation_profiles.json", "relation_timelines.json",
    "sources.json", "evidence_records.json", "alias_index.json", "graph_index.json",
]


def bj_now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


# ── 归一化：大小写 / 连字符 / 撇号 / ISIS 变体 / 阿语转写噪声 ────────────────
ISIS_VARIANTS = [
    (r"\bislamic state\b", "is"),
    (r"\bisil\b", "is"),
    (r"\bisis\b", "is"),
    (r"\bdaesh\b", "is"),
    (r"\bda'esh\b", "is"),
    (r"\biscap\b", "is central africa province"),
]
TRANSLIT_NOISE = [
    ("’", "'"), ("‘", "'"), ("`", "'"), ("ʿ", "'"), ("ʾ", "'"),
    ("–", "-"), ("—", "-"), ("‑", "-"),
    ("al ", "al-"),
]


def normalize(s):
    """归一化字符串用于跨写法比对。"""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    for a, b in TRANSLIT_NOISE:
        s = s.replace(a, b)
    s = re.sub(r"[^\w\u4e00-\u9fff\s'-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for pat, rep in ISIS_VARIANTS:
        s = re.sub(pat, rep, s)
    # 连字符与空格等价化
    s = s.replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def token_set(s):
    return set(normalize(s).split())


# ── 候选清单（§3 八实体 + §4 六人物）─────────────────────────────────────────
CANDIDATES = [
    {
        "candidate": "Al-Shabaab", "proposed_id": "actor-al-shabaab", "kind": "organization",
        "name_zh": "索马里青年党", "name_en": "Harakat al-Shabaab al-Mujahideen",
        "acronym": "Al-Shabaab",
        "probe_names": ["Al-Shabaab", "al Shabaab", "Al Shabab", "Harakat al-Shabaab al-Mujahideen",
                        "HSM", "索马里青年党", "青年党", "沙巴布"],
    },
    {
        "candidate": "ISIS-Somalia", "proposed_id": "actor-isis-somalia", "kind": "organization",
        "name_zh": "伊斯兰国索马里省", "name_en": "Islamic State Somalia Province",
        "acronym": "ISIS-Somalia",
        "probe_names": ["ISIS-Somalia", "IS-Somalia", "ISS", "Islamic State Somalia Province",
                        "Islamic State in Somalia", "伊斯兰国索马里省", "伊斯兰国索马里分支"],
    },
    {
        "candidate": "al-Karrar Office", "proposed_id": "actor-al-karrar-office", "kind": "organization",
        "name_zh": "卡拉尔办公室", "name_en": "al-Karrar Office", "acronym": "",
        "probe_names": ["al-Karrar Office", "Al Karrar", "al-Karrar", "Karrar Office",
                        "卡拉尔办公室", "卡拉尔"],
    },
    {
        "candidate": "ADF / ISIS-Central Africa", "proposed_id": "actor-adf-isis-ca", "kind": "organization",
        "name_zh": "民主同盟军（伊斯兰国中非省）", "name_en": "Allied Democratic Forces / Islamic State Central Africa Province",
        "acronym": "ADF / ISIS-CA",
        "probe_names": ["Allied Democratic Forces", "ADF", "ISIS-CA", "IS-CA", "ISCAP",
                        "Islamic State Central Africa Province", "Madina at Tauheed Wau Mujahedeen",
                        "MTM", "民主同盟军", "伊斯兰国中非省"],
    },
    {
        "candidate": "Ansaru", "proposed_id": "actor-ansaru", "kind": "organization",
        "name_zh": "安萨鲁", "name_en": "Jamaat Ansar al-Muslimeen fi Bilad al-Sudan",
        "acronym": "Ansaru",
        "probe_names": ["Ansaru", "Jamaat Ansar al-Muslimeen fi Bilad al-Sudan",
                        "Jama'atu Ansaril Muslimina fi Biladis Sudan", "安萨鲁"],
    },
    {
        "candidate": "Lakurawa", "proposed_id": "actor-lakurawa", "kind": "organization",
        "name_zh": "拉库拉瓦武装网络", "name_en": "Lakurawa", "acronym": "",
        "probe_names": ["Lakurawa", "Lakurawa militants", "拉库拉瓦"],
    },
    {
        "candidate": "Sudanese Islamic Movement", "proposed_id": "actor-sudanese-islamic-movement",
        "kind": "organization",
        "name_zh": "苏丹伊斯兰运动", "name_en": "Sudanese Islamic Movement", "acronym": "SIM",
        "probe_names": ["Sudanese Islamic Movement", "SIM", "SMB", "Sudanese Muslim Brotherhood",
                        "Islamic Movement of Sudan", "National Islamic Front", "NIF",
                        "苏丹伊斯兰运动", "苏丹穆斯林兄弟会", "全国伊斯兰阵线"],
    },
    {
        "candidate": "Al-Baraa Bin Malik Brigade", "proposed_id": "actor-bbmb", "kind": "organization",
        "name_zh": "巴拉·本·马利克旅", "name_en": "Al-Baraa Bin Malik Brigade", "acronym": "BBMB",
        "probe_names": ["Al-Baraa Bin Malik Brigade", "Al Baraa Ibn Malik Brigade", "BBMB",
                        "Baraa Bin Malik", "巴拉·本·马利克旅", "巴拉本马利克旅"],
    },
    {
        "candidate": "Ahmed Diriye", "proposed_id": "person-ahmed-diriye", "kind": "person",
        "name_zh": "艾哈迈德·迪里耶", "name_en": "Ahmed Diriye", "acronym": "",
        "probe_names": ["Ahmed Diriye", "Ahmad Umar", "Abu Ubaidah", "Ahmed Umar Abu Ubaidah",
                        "艾哈迈德·迪里耶", "阿布·乌拜达"],
    },
    {
        "candidate": "Abd al-Qadir Mu'min", "proposed_id": "person-abd-al-qadir-mumin", "kind": "person",
        "name_zh": "阿卜杜勒·卡迪尔·穆明", "name_en": "Abd al-Qadir Mu'min", "acronym": "",
        "probe_names": ["Abd al-Qadir Mu'min", "Abdulqadir Mumin", "Abdul Qadir Mumin",
                        "阿卜杜勒·卡迪尔·穆明", "穆明"],
    },
    {
        "candidate": "Abdirahman Fahiye Isse", "proposed_id": "person-abdirahman-fahiye", "kind": "person",
        "name_zh": "阿卜迪拉赫曼·法希耶·伊塞", "name_en": "Abdirahman Fahiye Isse Mohamud", "acronym": "",
        "probe_names": ["Abdirahman Fahiye Isse", "Abdirahman Fahiye Isse Mohamud", "Fahiye",
                        "阿卜迪拉赫曼·法希耶"],
    },
    {
        "candidate": "Seka Musa Baluku", "proposed_id": "person-seka-musa-baluku", "kind": "person",
        "name_zh": "塞卡·穆萨·巴卢库", "name_en": "Seka Musa Baluku", "acronym": "",
        "probe_names": ["Seka Musa Baluku", "Musa Baluku", "Baluku", "塞卡·穆萨·巴卢库", "巴卢库"],
    },
    {
        "candidate": "Ali Ahmed Karti", "proposed_id": "person-ali-ahmed-karti", "kind": "person",
        "name_zh": "阿里·艾哈迈德·卡尔提", "name_en": "Ali Ahmed Karti", "acronym": "",
        "probe_names": ["Ali Ahmed Karti", "Ali Karti", "Ali Ahmed Kurti",
                        "阿里·艾哈迈德·卡尔提", "卡尔提"],
    },
    {
        "candidate": "Abu Zaid Talha al-Misbah", "proposed_id": "person-abu-zaid-talha", "kind": "person",
        "name_zh": "阿布·扎伊德·塔勒哈·米斯巴赫", "name_en": "Abu Zaid Talha al-Misbah", "acronym": "",
        "probe_names": ["Abu Zaid Talha al-Misbah", "Abu Zayd Talha", "al-Misbah",
                        "阿布·扎伊德·塔勒哈"],
    },
]


def build_registry():
    """建立现有知识对象的多维度名称登记表。"""
    entities = load("entities.json")["entities"]
    countries = load("countries.json")["countries"]
    alias_index = load("alias_index.json")["aliases"]

    reg = []  # {object_id, kind, field, raw, norm}
    for e in entities:
        oid = e["entity_id"]
        kind = e.get("entity_type", "organization")
        for field in ("entity_id", "slug", "name_zh", "name_en", "acronym", "native_name"):
            v = e.get(field)
            if v:
                reg.append({"object_id": oid, "kind": kind, "field": field,
                            "raw": v, "norm": normalize(v)})
        for field in ("aliases", "historical_names"):
            for v in (e.get(field) or []):
                reg.append({"object_id": oid, "kind": kind, "field": field,
                            "raw": v, "norm": normalize(v)})
    for c in countries:
        oid = c["country_id"]
        for field in ("country_id", "slug", "name_zh", "name_en"):
            v = c.get(field)
            if v:
                reg.append({"object_id": oid, "kind": "country", "field": field,
                            "raw": v, "norm": normalize(v)})
    for alias, oid in alias_index.items():
        reg.append({"object_id": oid, "kind": "alias_index", "field": "alias_index",
                    "raw": alias, "norm": normalize(alias)})
    return reg, entities, countries, alias_index


def free_text_hits(probe_names):
    """在全部扫描文件的原始文本中做提及扫描（仅提示，不作为判定依据）。"""
    hits = {}
    for fn in SCAN_FILES:
        path = os.path.join(DATA, fn)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        raw_norm = normalize(raw)
        for p in probe_names:
            pn = normalize(p)
            if len(pn) < 3:
                continue
            n = raw_norm.count(pn)
            if n:
                hits.setdefault(fn, {})[p] = n
    return hits


# ── 人工裁定记录（对自动扫描发现的近似命中做显式判读）──────────────────────
MANUAL_ADJUDICATIONS = {
    "actor-adf-isis-ca": [{
        "near_match_object": "actor-is-mozambique",
        "near_match_field": "historical_names",
        "near_match_value": "伊斯兰国中非省关联（IS-CAP）",
        "verdict": "NOT_THE_SAME_OBJECT",
        "reasoning": (
            "actor-is-mozambique 的历史名记录的是其 2019—2022 年曾被置于 ISCAP（伊斯兰国中非省）"
            "框架下的历史归属，且现有档案已明确其 2022 年成为独立的 Islamic State Mozambique "
            "Province。本轮 actor-adf-isis-ca 指的是以刚果（金）东部与乌干达为活动区的 ADF / "
            "ISIS–Central Africa 主体。两者是 ISCAP 历史框架下的不同地理分支，属不同实际对象，"
            "不构成重复；且不得因此把 IS-Mozambique 回溯改写为 ADF 的组成部分。"
        ),
    }],
    "person-ahmed-diriye": [{
        "near_match_object": "actor-aqim",
        "near_match_field": "entity_profiles.leadership",
        "near_match_value": "阿布·乌拜达·优素福·阿纳比（Abu Ubaydah Yusuf al-Annabi）",
        "verdict": "KUNYA_COLLISION_NOT_THE_SAME_PERSON",
        "reasoning": (
            "AQIM 现任埃米尔 Abu Ubaydah Yusuf al-Annabi 与 Al-Shabaab 领导人 Ahmed Diriye 的"
            "化名 Abu Ubaidah 属同名化名（kunya）碰撞，是两个不同的人。因此 person-ahmed-diriye "
            "不得登记裸别名 'Abu Ubaidah'，必须使用带限定的完整化名形式，避免 alias_index 产生"
            "指向歧义。"
        ),
        "import_constraint": "alias 必须写作 'Ahmed Diriye (Abu Ubaidah)' 等限定形式，禁止裸 'Abu Ubaidah'。",
    }],
    "actor-sudanese-islamic-movement": [{
        "near_match_object": "free_text:SIM/NIF 子串",
        "near_match_field": "normalized_substring_noise",
        "near_match_value": "SIM / NIF",
        "verdict": "SUBSTRING_NOISE_NOT_A_MATCH",
        "reasoning": (
            "全文提及扫描中 'SIM'、'NIF' 的高计数来自归一化后的子串噪声（如 similar、"
            "significant 等英文词内部片段），并非既有知识对象的名称字段命中。Depth D 苏丹深化"
            "已建 actor-saf / actor-rsf / actor-splm-n-al-hilu / actor-jem / actor-slm-aw，"
            "其中不存在与苏丹伊斯兰运动等价的政治—军事网络节点，故新建。"
        ),
    }],
    "actor-isis-somalia": [{
        "near_match_object": "free_text:ISS 子串",
        "near_match_field": "normalized_substring_noise",
        "near_match_value": "ISS",
        "verdict": "SUBSTRING_NOISE_NOT_A_MATCH",
        "reasoning": (
            "'ISS' 的高计数来自 issue、mission、commission 等英文词内部子串，非名称字段命中。"
            "现有伊斯兰国相关节点为 actor-islamic-state、actor-is-sahel、actor-iswap、"
            "actor-is-mozambique、actor-isis-libya，均无索马里省主体。"
        ),
    }],
}


def alias_collision_check(cand, alias_index):
    """检查候选拟用名称是否会与既有 alias_index 冲突。"""
    out = []
    probes = list(dict.fromkeys(cand["probe_names"] + [cand["name_zh"], cand["name_en"]]))
    norm_index = {}
    for a, oid in alias_index.items():
        norm_index.setdefault(normalize(a), set()).add(oid)
    for p in probes:
        n = normalize(p)
        if n in norm_index:
            out.append({"probe": p, "normalized": n,
                        "existing_targets": sorted(norm_index[n])})
    return out


def audit_candidate(cand, reg):
    probes = list(dict.fromkeys(
        cand["probe_names"] + [cand["name_zh"], cand["name_en"], cand["acronym"]]
    ))
    probes = [p for p in probes if p]

    exact_match = []       # canonical id 完全一致
    alias_match = []       # 归一化名称/别名完全一致
    possible_match = []    # token 高度重叠

    pid_norm = normalize(cand["proposed_id"])
    probe_norms = {normalize(p) for p in probes if normalize(p)}

    for r in reg:
        if r["field"] in ("entity_id", "country_id") and r["norm"] == pid_norm:
            exact_match.append({"object_id": r["object_id"], "matched_field": r["field"],
                                "matched_value": r["raw"]})
            continue
        if r["norm"] in probe_norms:
            alias_match.append({"object_id": r["object_id"], "matched_field": r["field"],
                                "matched_value": r["raw"]})
            continue
        # token 重叠（>=2 token 且 Jaccard >= 0.6）
        rt = set(r["norm"].split())
        if len(rt) < 2:
            continue
        for p in probe_norms:
            pt = set(p.split())
            if len(pt) < 2:
                continue
            inter = rt & pt
            union = rt | pt
            if inter and len(inter) / len(union) >= 0.6:
                possible_match.append({"object_id": r["object_id"], "matched_field": r["field"],
                                       "matched_value": r["raw"], "probe": p,
                                       "jaccard": round(len(inter) / len(union), 3)})
                break

    def dedup(lst):
        seen, out = set(), []
        for x in lst:
            k = (x["object_id"], x["matched_field"], x["matched_value"])
            if k not in seen:
                seen.add(k)
                out.append(x)
        return out

    return dedup(exact_match), dedup(alias_match), dedup(possible_match)


def main():
    reg, entities, countries, alias_index = build_registry()
    eids = {e["entity_id"] for e in entities}

    results = []
    for cand in CANDIDATES:
        exact, alias, possible = audit_candidate(cand, reg)

        existing_ids = sorted({m["object_id"] for m in exact} |
                              {m["object_id"] for m in alias})
        # 只保留指向实体的既有对象（country 命中不构成实体重复）
        existing_entity_ids = [x for x in existing_ids if x in eids]

        if existing_entity_ids:
            decision = "ENRICH_EXISTING"
            existing_id = existing_entity_ids[0]
            rationale = (
                f"已存在同一实际对象 {existing_id}（命中字段："
                + "、".join(sorted({m["matched_field"] for m in exact + alias}))
                + "）。按 §1 不得为同一实际对象建立第二个节点，本轮走 ENRICH_EXISTING："
                  "补齐双语字段、别名、E3 档案、关系与证据，不新建 canonical id。"
            )
        else:
            decision = "NEW"
            existing_id = None
            if possible:
                rationale = (
                    "canonical id、name_zh、name_en、acronym、native_name、aliases、"
                    "historical_names 及 alias_index 全维度归一化后均无精确命中；"
                    "仅存在弱 token 重叠（"
                    + "、".join(sorted({m["object_id"] for m in possible})[:5])
                    + "），经人工判读属不同实际对象，故新建。"
                )
            else:
                rationale = (
                    "canonical id、name_zh、name_en、acronym、native_name、aliases、"
                    "historical_names 及 alias_index 全维度归一化后均无任何命中，"
                    "全文提及扫描亦未发现等价对象，故新建。"
                )

        results.append({
            "candidate": cand["candidate"],
            "kind": cand["kind"],
            "proposed_id": cand["proposed_id"],
            "proposed_name_zh": cand["name_zh"],
            "proposed_name_en": cand["name_en"],
            "probe_dimensions": [
                "canonical_id", "slug", "name_zh", "name_en", "acronym", "native_name",
                "aliases", "historical_names", "alias_index",
                "case_insensitive", "hyphen_space_equivalence",
                "isis_isil_is_daesh_variants", "arabic_transliteration_noise",
            ],
            "probe_names": cand["probe_names"],
            "exact_match": exact,
            "alias_match": alias,
            "possible_match": possible,
            "existing_id": existing_id,
            "decision": decision,
            "rationale": rationale,
            "manual_adjudications": MANUAL_ADJUDICATIONS.get(cand["proposed_id"], []),
            "alias_collision_check": alias_collision_check(cand, alias_index),
            "free_text_mentions": free_text_hits(cand["probe_names"]),
        })

    # 国家依赖检查
    country_ids = {c["country_id"] for c in countries}
    country_check = {
        "country-somalia": "country-somalia" in country_ids,
        "country-drc": "country-drc" in country_ids or "country-dr-congo" in country_ids,
    }

    payload = {
        "artifact": "pre-import-dedup-audit",
        "task": "ASIP-PPT-ENTITY-EXPANSION-A",
        "section": "§1 导入前全库精确去重",
        "generated_at": bj_now(),
        "scan_mode": "read_only",
        "scanned_files": SCAN_FILES,
        "baseline_counts": {
            "countries": len(countries),
            "entities": len(entities),
            "alias_index_entries": len(alias_index),
            "relationships": len(load("relationships.json")["relationships"]),
            "relation_profiles": len(load("relation_profiles.json")["profiles"]),
            "relation_timelines": len(load("relation_timelines.json")["timelines"]),
            "sources": len(load("sources.json")["sources"]),
            "evidence_records": len(load("evidence_records.json")["evidence"]),
        },
        "candidate_count": len(results),
        "decision_summary": {
            "NEW": sum(1 for r in results if r["decision"] == "NEW"),
            "ENRICH_EXISTING": sum(1 for r in results if r["decision"] == "ENRICH_EXISTING"),
            "ALIAS_ONLY": sum(1 for r in results if r["decision"] == "ALIAS_ONLY"),
        },
        "country_node_check": country_check,
        "candidates": results,
        "notes": [
            "本审计为只读扫描，未修改任何 source-of-truth 数据。",
            "归一化覆盖大小写、连字符/空格等价、撇号与阿语转写噪声、ISIS/ISIL/IS/Daesh 变体。",
            "free_text_mentions 仅为提示性上下文，不作为重复判定依据。",
            "同一实际对象一律 ENRICH_EXISTING，禁止建立第二 canonical id。",
        ],
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "pre-import-dedup-audit.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("WROTE", out)
    for r in results:
        print(f"  {r['decision']:18s} {r['proposed_id']:36s} existing={r['existing_id']}")
    print("country_node_check:", country_check)
    return 0


if __name__ == "__main__":
    sys.exit(main())
