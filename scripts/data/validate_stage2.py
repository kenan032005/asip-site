#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_stage2.py —— ASIP Stage-2 规范数据层校验（25 项检查，零依赖）。

范围：canonical 数据完整性、Schema 合规、ID 规则、发布政策一致性、
来源分级与核实级别分离、遗留视图单向生成一致性、迁移状态与幂等证据。

用法：
  python scripts/data/validate_stage2.py

退出码：0=全部通过（或仅警告）；1=存在严重错误。
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
ROOT = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)

from data.schema_validator import load_schema, validate_instance  # noqa: E402
from data.publication_policy import PUBLISHABLE_LEVELS  # noqa: E402
from data.normalizers import (VERIFICATION_LEVEL_ENUMS,
                              PUBLICATION_STATUS_ENUMS)  # noqa: E402

DATA = os.path.join(ROOT, "data")
CANON = os.path.join(DATA, "canonical")
PUBLIC = os.path.join(DATA, "public")
SCHEMA_DIR = os.path.join(ROOT, "schemas")

results = []          # (check_id, ok, msg, critical)


def check(cid, ok_flag, msg, critical=True):
    results.append((cid, bool(ok_flag), msg, critical))
    mark = "✅" if ok_flag else ("🚫" if critical else "⚠")
    print(f"{mark} [{cid}] {msg}")


def load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def main():
    print("=" * 60)
    print("ASIP Stage-2 规范数据层校验（25 项）")
    print("=" * 60)

    # ── S01-S04 文件存在且 JSON 合法 ──
    arts_doc = load(os.path.join(CANON, "articles.json"))
    check("S01", arts_doc is not None, "canonical/articles.json 存在且 JSON 合法")
    cl_doc = load(os.path.join(CANON, "event_clusters.json"))
    check("S02", cl_doc is not None, "canonical/event_clusters.json 存在且 JSON 合法")
    q_doc = load(os.path.join(CANON, "quarantine.json"))
    check("S03", q_doc is not None, "canonical/quarantine.json 存在且 JSON 合法")
    pub_doc = load(os.path.join(PUBLIC, "published_events.json"))
    check("S04", pub_doc is not None, "public/published_events.json 存在且 JSON 合法")

    arts = (arts_doc or {}).get("items", [])
    clusters = (cl_doc or {}).get("items", [])
    quars = (q_doc or {}).get("items", [])
    pubs = (pub_doc or {}).get("items", [])

    # ── S05-S08 JSON Schema 校验 ──
    def schema_check(cid, name, items, id_field):
        try:
            sch = load_schema(name, SCHEMA_DIR)
        except Exception as e:
            check(cid, False, f"schema {name} 加载失败: {e}")
            return
        bad = []
        for it in items:
            errs = validate_instance(it, sch)
            if errs:
                bad.append((it.get(id_field, "?"), errs[:2]))
        check(cid, not bad,
              f"{name}: {len(items)} 条全部通过 Schema 校验" if not bad
              else f"{name}: {len(bad)} 条不合规，如 {bad[:2]}")

    schema_check("S05", "article.schema.json", arts, "article_id")
    schema_check("S06", "event_cluster.schema.json", clusters, "event_id")
    schema_check("S07", "quarantine_record.schema.json", quars, "quarantine_id")
    schema_check("S08", "published_event.schema.json", pubs, "event_id")

    # ── S09-S11 ID 规则与唯一性 ──
    aid_re = re.compile(r"^ART_[0-9a-f]{16}$")
    eid_re = re.compile(r"^EVT_[0-9a-f]{16}$")
    qid_re = re.compile(r"^Q_[0-9a-f]{16}$")
    aids = [a.get("article_id", "") for a in arts]
    check("S09", all(aid_re.match(x) for x in aids) and len(set(aids)) == len(aids),
          f"article_id 全部合规且唯一（{len(aids)} 条）")
    eids = [c.get("event_id", "") for c in clusters]
    check("S10", all(eid_re.match(x) for x in eids) and len(set(eids)) == len(eids),
          f"event_id 全部合规且唯一（{len(eids)} 条）")
    qids = [q.get("quarantine_id", "") for q in quars]
    check("S11", all(qid_re.match(x) for x in qids) and len(set(qids)) == len(qids),
          f"quarantine_id 全部合规且唯一（{len(qids)} 条）")

    # ── S12 版本标记 ──
    vers_ok = all(d.get("schema_version") == "2.0" and d.get("pipeline_version") == 2
                  for d in (arts_doc or {}, cl_doc or {}, q_doc or {}) if d)
    rec_ok = all(it.get("schema_version") == "2.0" and it.get("pipeline_version") == 2
                 for it in arts + clusters + quars)
    check("S12", vers_ok and rec_ok, "schema_version=2.0 且 pipeline_version=2（信封与全部记录）")

    # ── S13 关系完整性 ──
    aset = set(aids)
    dangling = [c.get("event_id") for c in clusters
                for x in c.get("article_ids", []) if x not in aset]
    check("S13", not dangling,
          "event_clusters.article_ids 全部指向存在的 article" if not dangling
          else f"{len(dangling)} 个 article_id 悬空，如 {dangling[:3]}")

    # ── S14 发布状态枚举与闸门 ──
    bad_ps = [c.get("event_id") for c in clusters
              if c.get("publication_status") not in PUBLICATION_STATUS_ENUMS]
    gate_bad = [c.get("event_id") for c in clusters
                if c.get("publication_status") in ("publishable", "published")
                and not c.get("quality_gate_passed")]
    check("S14", not bad_ps and not gate_bad,
          "publication_status 枚举合法，publishable/published 均通过质量闸门"
          if not bad_ps and not gate_bad
          else f"非法状态 {bad_ps[:3]} / 未过闸 {gate_bad[:3]}")

    # ── S15 verification_level 枚举合法 ──
    bad_vl = [c.get("event_id") for c in clusters
              if c.get("verification_level") not in VERIFICATION_LEVEL_ENUMS]
    check("S15", not bad_vl,
          "verification_level 枚举全部合法" if not bad_vl
          else f"{len(bad_vl)} 个非法核实级别，如 {bad_vl[:3]}")

    # ── S16 新发布事件必须达发布门槛（迁移保留的历史事件豁免）──
    bad_new = []
    for c in clusters:
        if c.get("publication_status") in ("publishable",) and \
           c.get("verification_level") not in PUBLISHABLE_LEVELS:
            bad_new.append(c.get("event_id"))
    check("S16", not bad_new,
          "publishable 事件全部达到发布门槛（cross_verified/direct_official_source）"
          if not bad_new else f"{len(bad_new)} 个 publishable 未达门槛，如 {bad_new[:3]}")

    # ── S17 Reuters 单源 ≠ 官方直接来源 ──
    bad_reuters = []
    for c in clusters:
        groups = [g.lower() for g in c.get("source_groups", [])]
        if any("reuters" in g for g in groups) and \
           int(c.get("independent_source_count") or 1) <= 1 and \
           c.get("verification_level") == "direct_official_source":
            bad_reuters.append(c.get("event_id"))
    check("S17", not bad_reuters,
          "Reuters 单一来源均未标记为 direct_official_source（转载≠官方）"
          if not bad_reuters else f"违规 {bad_reuters[:3]}")

    # ── S18 ReliefWeb 平台 ≠ 联合国官方直接来源 ──
    srcs_doc = load(os.path.join(DATA, "sources.json")) or {}
    srcs = srcs_doc.get("sources", [])
    bad_rw = [s.get("source_id") for s in srcs
              if "reliefweb" in (s.get("source_group", "") + s.get("source_id", "")).lower()
              and (s.get("is_direct_origin") or not s.get("is_republication_platform"))]
    check("S18", not bad_rw,
          "ReliefWeb 标记为转载平台且非直接来源（NGO 报告≠联合国官方）"
          if not bad_rw else f"违规 {bad_rw[:3]}")

    # ── S19-S21 遗留视图为单向生成 ──
    for cid, fname in (("S19", "events.json"), ("S20", "pending_events.json"),
                       ("S21", "raw_candidates.json")):
        d = load(os.path.join(DATA, fname)) or {}
        check(cid, d.get("generated_from_canonical") is True and d.get("do_not_edit_manually") is True,
              f"{fname} 带 generated_from_canonical/do_not_edit_manually 标记（单向生成）")

    # ── S22 legacy events 与 clusters 1:1 ──
    ev_doc = load(os.path.join(DATA, "events.json")) or {}
    legacy_ids = {e.get("event_id") for e in ev_doc.get("events", []) if e.get("event_id")}
    cluster_leids = {c.get("legacy_event_id") for c in clusters if c.get("legacy_event_id")}
    check("S22", legacy_ids == cluster_leids and len(legacy_ids) == len(clusters),
          f"legacy events（{len(legacy_ids)}）与 canonical clusters（{len(clusters)}）1:1 对应")

    # ── S23 published 数与达门槛 cluster 数一致，且隔离不进发布 ──
    pub_cnt = sum(1 for c in clusters
                  if c.get("publication_status") in ("publishable", "published"))
    pub_ids = {p.get("event_id") for p in pubs}
    quar_orig = {q.get("original_id") for q in quars if q.get("original_id")}
    quar_in_pub = pub_ids & {c.get("event_id") for c in clusters
                             if c.get("legacy_event_id") in quar_orig}
    check("S23", len(pubs) == pub_cnt and not quar_in_pub,
          f"published_events={len(pubs)} 与达门槛 clusters={pub_cnt} 一致，且无隔离事件混入")

    # ── S24 current_metrics 与实际计数一致 ──
    m = load(os.path.join(PUBLIC, "current_metrics.json")) or {}
    m_ok = (m.get("articles") == len(arts) and m.get("event_clusters") == len(clusters)
            and m.get("published_events") == len(pubs) and m.get("quarantine") == len(quars))
    check("S24", m_ok, f"current_metrics 计数一致 (articles={len(arts)} clusters={len(clusters)} "
                       f"published={len(pubs)} quarantine={len(quars)})")

    # ── S25 迁移状态与幂等证据 ──
    st = load(os.path.join(CANON, "migration_state.json")) or {}
    rep = load(os.path.join(CANON, "idempotency_report.json")) or {}
    check("S25", st.get("error_counts") == 0 and st.get("idempotent") is True
          and rep.get("identical") is True,
          "迁移无错误（error_counts=0）且幂等验证通过（idempotency_report.identical=true）")

    # ── 总结 ──
    n_fail = sum(1 for _, okf, _, crit in results if not okf and crit)
    n_warn = sum(1 for _, okf, _, crit in results if not okf and not crit)
    n_pass = sum(1 for _, okf, _, _ in results if okf)
    print("=" * 60)
    print(f"Stage-2 校验：PASS={n_pass}  FAIL={n_fail}  WARN={n_warn}  （共 {len(results)} 项）")
    print("=" * 60)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
