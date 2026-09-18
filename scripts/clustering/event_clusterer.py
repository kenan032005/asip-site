#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""event_clusterer.py —— C1B §十七：确定性 event-level clustering（保守、非传递）。

背景（C1B §十三/§十四 审计）：
  生产采集路径 `stage3_collect_v2.build_event()` 对每篇文章直接生成
  `event_id = EVT_md5(article_url)[:16]`，并**硬编码**
  `independent_source_count = 1`，且完全不写 `article_ids` / `source_groups`。
  因此「一篇 = 一个事件」，同一现实事件被多家媒体报道时永远变成多个孤立事件，
  multi-source corroboration 在结构上不可能出现（不是计数错误，也不是完全没报道）。

本模块在**不改动任何 canonical 阈值**的前提下补上事件级聚类：
  * 阈值仍由 canonical 政策持有（independent_source_count >= 2 AND quality_gate_passed）；
    本模块只负责「正确地合并同一事件」与「正确地数独立来源」，绝不放宽下游阈值。
  * 保守优先：宁可少合并，不可过度合并（§十七 明令）。
  * 非传递：新成员只与 cluster anchor 比较，禁止 A-B-C 链式串并。
  * 冲突保留：伤亡数字/地点/时间不一致写入 conflict_flags，不静默覆盖。

聚类依据（与 §十七 允许项一一对应，全部确定性、无 LLM）：
  country + 时间邻近(≤72h) + category 兼容 + 具名地点 + 归一化实体 + 标题/内容相似度。
"""
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone

#: 合并判定阈值（事件级；与 canonical 的 independent_source_count 阈值无关）
MERGE_AUTO_TITLE_JACCARD = 0.50
MERGE_AUTO_MIN_SHARED_TOKENS = 3
MERGE_AUTO_MIN_SHARED_ENTITIES = 2
MERGE_ENTITY_TIME_WINDOW_H = 24.0
MAX_TIME_DELTA_H = 72.0

#: category 兼容矩阵（宽口径；不兼容 → 不合并）
CATEGORY_COMPAT = {
    "armed_conflict": {"armed_conflict", "terrorism", "public_order", "security"},
    "terrorism": {"terrorism", "armed_conflict", "security"},
    "public_order": {"public_order", "armed_conflict", "security"},
    "security": {"security", "armed_conflict", "terrorism", "public_order"},
    "public_health": {"public_health", "humanitarian"},
    "humanitarian": {"humanitarian", "public_health", "natural_disaster"},
    "natural_disaster": {"natural_disaster", "humanitarian"},
}

#: 事件类型 → 宽 category（把采集器的细分类型收敛到可比较口径）
TYPE_TO_CATEGORY = {
    "armed_conflict": "armed_conflict",
    "terrorism": "terrorism",
    "public_order": "public_order",
    "public_health": "public_health",
    "humanitarian": "humanitarian",
    "natural_disaster": "natural_disaster",
    "security": "security",
}

_STOP = {
    # fr
    "les", "des", "une", "uns", "aux", "avec", "pour", "dans", "sur", "par",
    "est", "sont", "ont", "ete", "plus", "apres", "avant", "entre", "vers",
    "cette", "cet", "son", "ses", "leur", "leurs", "qui", "que", "quoi",
    "du", "de", "la", "le", "et", "en", "au", "il", "elle", "on", "ce",
    "aujourd", "hui", "selon", "face", "lors", "tout", "tous", "toute",
    # en
    "the", "and", "for", "with", "from", "that", "this", "these", "those",
    "has", "have", "had", "was", "were", "are", "will", "been", "into",
    "over", "after", "before", "between", "about", "says", "said", "new",
    "amid", "due", "its", "his", "her", "their", "they", "you", "our",
    # 通用
    "plus", "ans", "apres",
}
_TOKEN_RX = re.compile(r"[a-z0-9\u00c0-\u024f']{3,}")


def _strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def normalize_text(s):
    if not s:
        return ""
    s = _strip_accents(str(s).lower())
    return re.sub(r"\s+", " ", s).strip()


def distinctive_tokens(text):
    """标题中的判别性 token（去停用词、去纯数字、长度>=3）。"""
    t = normalize_text(text)
    return {w for w in _TOKEN_RX.findall(t)
            if w not in _STOP and not w.isdigit() and len(w) >= 4}


def named_entities(text):
    """简易确定性具名实体：原文中的首字母大写词组（长度>=3，非句首常见词）。"""
    if not text:
        return set()
    ents = set()
    for m in re.finditer(r"\b([A-ZÀ-Þ][\w'’\-]{2,}(?:\s+[A-ZÀ-Þ][\w'’\-]{2,})*)", str(text)):
        v = m.group(1).strip()
        if len(v) < 3:
            continue
        if normalize_text(v) in _STOP:
            continue
        ents.add(normalize_text(v))
    return ents


def numbers(text):
    return set(re.findall(r"\b\d{1,4}\b", str(text or "")))


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def _parse_ts(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(str(s)[:len(fmt) + 2], fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def hours_between(a, b):
    ta, tb = _parse_ts(a), _parse_ts(b)
    if not ta or not tb:
        return None
    return abs((ta - tb).total_seconds()) / 3600.0


def category_of(ev):
    t = (ev.get("event_type") or "").strip().lower()
    return TYPE_TO_CATEGORY.get(t, "security")


def _compatible(ev_a, ev_b):
    ca, cb = category_of(ev_a), category_of(ev_b)
    if ca == cb:
        return True
    return cb in CATEGORY_COMPAT.get(ca, set()) or ca in CATEGORY_COMPAT.get(cb, set())


def pair_evidence(anchor, cand):
    """返回 (mergeable, score, evidence, conflicts)。

    只有在**同一现实事件的强证据**成立时才 merge：
      E1 标题判别 token Jaccard ≥ 0.50 且共享 token ≥ 3；或
      E2 共享具名实体 ≥ 2 且时间差 ≤ 24h。
    国家/时间/category 为前置硬门槛，不满足直接不合并。
    """
    ev, conflicts = [], []
    if (anchor.get("country_code") or "") != (cand.get("country_code") or ""):
        return False, 0, ["R1_country_mismatch"], []
    dh = hours_between(anchor.get("event_time") or anchor.get("published_at_beijing"),
                       cand.get("event_time") or cand.get("published_at_beijing"))
    if dh is not None and dh > MAX_TIME_DELTA_H:
        return False, 0, ["R2_time_gt72h"], []
    if not _compatible(anchor, cand):
        return False, 0, ["R4_incompatible_category"], []
    la = normalize_text(anchor.get("location_name") or anchor.get("event_location_country") or "")
    lb = normalize_text(cand.get("location_name") or cand.get("event_location_country") or "")
    if la and lb and la != lb and la not in lb and lb not in la:
        return False, 0, ["R3_distinct_location"], []

    ta = distinctive_tokens(anchor.get("title_original") or "")
    tb = distinctive_tokens(cand.get("title_original") or "")
    jac = jaccard(ta, tb)
    shared_tok = ta & tb
    ea = named_entities(anchor.get("title_original") or "")
    eb = named_entities(cand.get("title_original") or "")
    shared_ent = ea & eb

    score = 0
    if jac >= MERGE_AUTO_TITLE_JACCARD and len(shared_tok) >= MERGE_AUTO_MIN_SHARED_TOKENS:
        score += 45
        ev.append("E1_title_jaccard=%.2f shared_tokens=%d" % (jac, len(shared_tok)))
    if len(shared_ent) >= MERGE_AUTO_MIN_SHARED_ENTITIES and dh is not None \
            and dh <= MERGE_ENTITY_TIME_WINDOW_H:
        score += 40
        ev.append("E2_shared_entities=%d dh=%.1f" % (len(shared_ent), dh))
    if dh is not None and dh <= 24:
        score += 10
        ev.append("time_within_24h")
    if numbers(anchor.get("title_original") or "") & numbers(cand.get("title_original") or ""):
        score += 5
        ev.append("shared_numeric_fact")

    # 冲突保留（不静默覆盖）
    na = numbers(anchor.get("title_original") or "")
    nb = numbers(cand.get("title_original") or "")
    if na and nb and not (na & nb):
        conflicts.append("numeric_difference:%s_vs_%s" % (sorted(na)[:3], sorted(nb)[:3]))
    if anchor.get("event_time") != cand.get("event_time"):
        conflicts.append("time_difference")

    mergeable = score >= 45 and any(e.startswith(("E1_", "E2_")) for e in ev)
    return mergeable, score, ev, conflicts


def apply_event_clustering(clusters_path, run_id, verbose=True):
    """把本次 run 产生的事件做事件级聚类后写回 canonical event_clusters.json。

    只处理 `run_id == run_id` 的条目（历史 cluster 原样保留，不改写、不重编号），
    按 country_code 分组后调用 cluster_events。返回统计。

    幂等：对同一批输入重复调用结果一致（cluster_id 由成员 canonical_url 决定）。
    """
    import os
    if not os.path.exists(clusters_path):
        return {"error": "clusters_path_missing", "path": clusters_path}
    with open(clusters_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    items = doc.get("items") or []
    mine = [c for c in items if c.get("run_id") == run_id]
    others = [c for c in items if c.get("run_id") != run_id]
    if not mine:
        return {"input_events": 0, "output_clusters": 0, "note": "no events for this run_id"}

    by_country = {}
    for c in mine:
        by_country.setdefault(c.get("country_code") or "", []).append(c)

    new_items, total = [], {"input_events": 0, "output_clusters": 0, "singletons": 0,
                            "multi_source_clusters": 0, "merged_pairs": 0,
                            "hard_rejects": 0, "max_independent_sources": 0}
    for cc, group in sorted(by_country.items()):
        clusters, st = cluster_events(group)
        new_items.extend(clusters)
        for k in ("input_events", "output_clusters", "singletons", "multi_source_clusters",
                  "merged_pairs", "hard_rejects"):
            total[k] += st.get(k, 0)
        total["max_independent_sources"] = max(total["max_independent_sources"],
                                               st.get("max_independent_sources", 0))

    doc["items"] = others + new_items
    doc["updated_at"] = _now_bj()
    tmp = clusters_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    os.replace(tmp, clusters_path)
    if verbose:
        print("[event-cluster] run=%s events %d -> clusters %d "
              "(singletons=%d multi_source=%d merged_pairs=%d max_indep=%d)"
              % (run_id, total["input_events"], total["output_clusters"],
                 total["singletons"], total["multi_source_clusters"],
                 total["merged_pairs"], total["max_independent_sources"]))
    return total


def _now_bj():
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(hours=8)).strftime(
        "%Y-%m-%dT%H:%M:%S+08:00")


def cluster_id(members):
    keys = sorted((m.get("canonical_url") or m.get("article_url") or m.get("event_id") or "")
                  for m in members)
    return "EVT_" + hashlib.sha1("|".join(keys).encode("utf-8")).hexdigest()[:16]


def cluster_events(events, identity_of=None):
    """对同一国家的 event 列表做保守事件聚类。

    events       : list[dict]，每项至少含 country_code / event_time / title_original /
                   event_type / independent_source_count / source_groups
    identity_of  : callable(event) -> source_identity dict（默认用 source_identity 模块）
    返回 (clusters, stats)：clusters 为合并后的 event 列表（保留 anchor 全部字段，
    并补齐 article_ids / source_groups / independent_source_count / cluster_status /
    member_event_ids / conflict_flags）；singleton 原样保留。
    """
    if identity_of is None:
        def identity_of(e):
            from data.source_identity import source_identity
            return source_identity(e)

    # block：(country_code, 日期)，相邻日期允许落入同一 block（±1 天）
    blocks = {}
    for e in events:
        cc = e.get("country_code") or ""
        dt = _parse_ts(e.get("event_time") or e.get("published_at_beijing"))
        day = dt.date().isoformat() if dt else "unknown"
        blocks.setdefault((cc, day), []).append(e)

    clusters, merged_pairs, hard_rejects = [], 0, 0
    for (cc, _day), members in sorted(blocks.items()):
        # 同 block 内（同日）非传递 anchor 聚类
        local = []          # list of {anchor: ev, members: [ev]}
        for e in members:
            placed = False
            for cl in local:
                ok, score, evid, conflicts = pair_evidence(cl["anchor"], e)
                if ok:
                    cl["members"].append(e)
                    cl["evidence"].extend(evid)
                    cl["conflicts"].extend(conflicts)
                    placed = True
                    merged_pairs += 1
                    break
                if evid and evid[0].startswith("R"):
                    hard_rejects += 1
            if not placed:
                local.append({"anchor": e, "members": [e], "evidence": [], "conflicts": []})

        for cl in local:
            ms = cl["members"]
            anchor = dict(cl["anchor"])
            if len(ms) == 1:
                anchor.setdefault("cluster_status", "singleton")
                anchor.setdefault("article_ids", [])
                anchor.setdefault("source_groups", [])
                anchor.setdefault("member_event_ids", [anchor.get("event_id")])
                anchor.setdefault("conflict_flags", [])
                clusters.append(anchor)
                continue
            # 独立来源计数：按 source identity（同媒体多国登记 / 转载 → 只算 1）
            idents = [identity_of(m) for m in ms]
            keys = []
            for i in idents:
                k = i["identity_key"]
                if i["independence_class"] == "aggregator":
                    k = "aggregator:" + k
                keys.append(k)
            uniq = sorted(set(keys))
            indep_keys = sorted({k for k, i in zip(keys, idents)
                                 if i["independence_class"] != "aggregator"})
            anchor.update({
                "event_id": cluster_id(ms),
                "cluster_status": "auto_clustered",
                "member_event_ids": [m.get("event_id") for m in ms],
                "member_count": len(ms),
                "article_ids": [m.get("article_id") for m in ms if m.get("article_id")],
                "source_groups": sorted({i.get("source_group") or "" for i in idents
                                         if i.get("source_group")}),
                "source_identity_ids": uniq,
                "independent_source_count": len(indep_keys),
                "source_count": len(ms),
                "merge_evidence": sorted(set(cl["evidence"])),
                "conflict_flags": sorted(set(cl["conflicts"])),
                "event_time_start": min(str(m.get("event_time") or "") for m in ms),
                "event_time_end": max(str(m.get("event_time") or "") for m in ms),
            })
            clusters.append(anchor)

    stats = {
        "input_events": len(events),
        "output_clusters": len(clusters),
        "singletons": sum(1 for c in clusters if c.get("cluster_status") == "singleton"),
        "multi_source_clusters": sum(1 for c in clusters
                                     if (c.get("independent_source_count") or 0) >= 2),
        "merged_pairs": merged_pairs,
        "hard_rejects": hard_rejects,
        "max_independent_sources": max([c.get("independent_source_count") or 0
                                        for c in clusters] or [0]),
    }
    return clusters, stats
