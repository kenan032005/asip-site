#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_stage2.py —— ASIP Stage-2 规范数据层校验（48 项检查，零依赖）。

范围：canonical 数据完整性、Schema 合规、ID 规则、发布政策一致性、
来源分级与核实级别分离、遗留视图单向生成一致性、迁移状态与幂等证据；
第二阶段收尾新增（S26-S42）：仓库层强制校验、双向关联、canonical-first
管线链路、发布语义、风险统一、路径卫生、run_id 一致性等 17 项。

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
    print("ASIP Stage-2 规范数据层校验（48 项）")
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
    # 历史迁移保留事件（legacy_migration_preserved）按第七节语义豁免质量闸门
    gate_bad = [c.get("event_id") for c in clusters
                if c.get("publication_status") in ("publishable", "published")
                and not c.get("quality_gate_passed")
                and not c.get("legacy_migration_preserved")]
    check("S14", not bad_ps and not gate_bad,
          "publication_status 枚举合法，publishable/published 均通过质量闸门（历史保留豁免）"
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

    # ════════ 第二阶段收尾新增检查 S26-S42 ════════

    def read_text(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    WIN_PATH = re.compile(r"[A-Za-z]:(?:\\\\|\\|/)+Users(?:\\\\|\\|/)+[A-Za-z0-9_.-]+")
    POSIX_PATH = re.compile(r"/(?:home|Users)/[A-Za-z0-9_.-]+/")

    def has_local_path(text):
        return bool(WIN_PATH.search(text) or POSIX_PATH.search(text))

    # ── S26 Repository 保存路径强制 Schema 校验（源码静态检查）──
    repo_src = read_text(os.path.join(SCRIPTS, "data", "repository.py"))
    check("S26", "SCHEMA_FOR" in repo_src and "_revalidate" in repo_src
          and "validate_instance" in repo_src and "RepositorySchemaError" in repo_src,
          "repository.py 保存前强制调用 Schema 校验（SCHEMA_FOR/_revalidate/validate_instance）")

    # ── S27 article↔cluster 双向关联一致 ──
    cl_by_id = {c.get("event_id"): c for c in clusters}
    bad_link = []
    for a in arts:
        le = a.get("linked_event_id")
        if le:
            c = cl_by_id.get(le)
            if not c or a.get("article_id") not in c.get("article_ids", []):
                bad_link.append(a.get("article_id"))
    for c in clusters:
        for x in c.get("article_ids", []):
            aa = next((a for a in arts if a.get("article_id") == x), None)
            if aa is not None and aa.get("linked_event_id") not in (None, "", c.get("event_id")):
                bad_link.append(x)
    check("S27", not bad_link,
          "article.linked_event_id 与 cluster.article_ids 双向一致" if not bad_link
          else f"{len(bad_link)} 处双向关联不一致，如 {bad_link[:3]}")

    # ── S28 public 仅由 canonical 生成（event_id 全部来自 clusters）──
    eid_set = {c.get("event_id") for c in clusters}
    orphan_pub = [p.get("event_id") for p in pubs if p.get("event_id") not in eid_set]
    check("S28", not orphan_pub,
          "public/published_events 每条均来自 canonical clusters" if not orphan_pub
          else f"{len(orphan_pub)} 条 public 事件不在 canonical 中，如 {orphan_pub[:3]}")

    # ── S29 legacy 三文件与 public 同批导出（run_id 一致）──
    pub_rid = (pub_doc or {}).get("run_id")
    legacy_rids = {}
    for fname in ("events.json", "pending_events.json", "raw_candidates.json"):
        legacy_rids[fname] = (load(os.path.join(DATA, fname)) or {}).get("run_id")
    same_batch = pub_rid and all(v == pub_rid for v in legacy_rids.values())
    check("S29", same_batch,
          f"legacy 三文件与 public 同批导出（run_id={pub_rid}）" if same_batch
          else f"run_id 不一致: public={pub_rid} legacy={legacy_rids}")

    # ── S30 当前统计只计 current_policy_passed=true ──
    st_doc = load(os.path.join(DATA, "status.json")) or {}
    n_cur = sum(1 for p in pubs if p.get("current_policy_passed") is True)
    stats_ok = (st_doc.get("current_event_count", -1) <= n_cur
                and st_doc.get("events_24h", -1) <= n_cur
                and st_doc.get("events_7d", -1) <= n_cur)
    check("S30", stats_ok,
          f"status 统计口径 ≤ 当前政策通过事件数（current_policy_passed={n_cur}，"
          f"current_event_count={st_doc.get('current_event_count')}）")

    # ── S31 历史保留事件不得标记质量闸门/当前政策通过 ──
    bad_hist = [p.get("event_id") for p in pubs
                if p.get("legacy_migration_preserved") is True
                and (p.get("quality_gate_passed") is True
                     or p.get("current_policy_passed") is True)]
    bad_hist += [c.get("event_id") for c in clusters
                 if c.get("legacy_migration_preserved") is True
                 and c.get("current_policy_passed") is True]
    check("S31", not bad_hist,
          "历史迁移保留事件均未标记 quality_gate_passed/current_policy_passed"
          if not bad_hist else f"违规 {bad_hist[:3]}")

    # ── S32 22 国风险等级/标签与 countries.json 一致 ──
    RISK_LABEL = {4: "极高", 3: "高", 2: "中", 1: "低"}
    countries = (load(os.path.join(DATA, "countries.json")) or {}).get("countries", [])
    risk_map = {c.get("cn"): int(c.get("risk_level") or 0)
                for c in countries if c.get("cn")}
    bad_risk = []
    for p in pubs:
        cn = p.get("country_cn")
        lv = risk_map.get(cn)
        if lv:
            if p.get("country_risk_level") != lv or \
               p.get("country_risk_label") != RISK_LABEL.get(lv, ""):
                bad_risk.append((p.get("event_id"), cn))
    check("S32", risk_map and not bad_risk,
          f"public 事件风险等级/标签与 countries.json 全部一致（{len(risk_map)} 国映射）"
          if risk_map and not bad_risk else f"{len(bad_risk)} 条不一致，如 {bad_risk[:3]}")

    # ── S33 Reuters/Xinhua/ReliefWeb 业务属性合规（source_rules）──
    try:
        from data.source_rules import validate_source_business_rules
        src_errs = []
        for s in srcs:
            src_errs.extend(validate_source_business_rules(s))
        check("S33", not src_errs,
              "sources.json 全部通过来源业务规则（Reuters/Xinhua/ReliefWeb）"
              if not src_errs else f"{len(src_errs)} 处违规，如 {src_errs[:2]}")
    except Exception as e:
        check("S33", False, f"source_rules 导入/执行失败: {e}")

    # ── S34 public 不含 legacy_payload ──
    has_lp = [p.get("event_id") for p in pubs if "legacy_payload" in p]
    check("S34", not has_lp,
          "public/published_events 不含 legacy_payload（内部字段不外泄）"
          if not has_lp else f"{len(has_lp)} 条含 legacy_payload，如 {has_lp[:3]}")

    # ── S35 public 目录无本地机器路径 ──
    pub_dirty = []
    if os.path.isdir(PUBLIC):
        for fn in os.listdir(PUBLIC):
            if fn.endswith(".json") and has_local_path(read_text(os.path.join(PUBLIC, fn))):
                pub_dirty.append(fn)
    check("S35", not pub_dirty,
          "data/public/ 无本地机器路径" if not pub_dirty else f"含路径: {pub_dirty}")

    # ── S36 migration_state.json 无本地机器路径 ──
    check("S36", not has_local_path(read_text(os.path.join(CANON, "migration_state.json"))),
          "canonical/migration_state.json 无本地机器路径")

    # ── S37 build_summary 不再读取遗留 events.json ──
    bs_src = read_text(os.path.join(SCRIPTS, "build_summary.py"))
    check("S37", "published_events.json" in bs_src
          and "load_events" not in bs_src
          and 'os.path.join(DATA_DIR, "events.json")' not in bs_src,
          "build_summary.py 从 public/published_events.json 读取（不读遗留 events.json）")

    # ── S38 generate_reports 不再读取遗留 events.json ──
    gr_src = read_text(os.path.join(SCRIPTS, "generate_reports.py"))
    check("S38", "published_events.json" in gr_src
          and 'os.path.join(DATA_DIR, "events.json")' not in gr_src
          and '"events.json"' not in gr_src,
          "generate_reports.py 从 public/published_events.json 读取（不读遗留 events.json）")

    # ── S39 pipeline_runner 编排中调用 validate_stage2 ──
    pr_src = read_text(os.path.join(SCRIPTS, "pipeline_runner.py"))
    check("S39", "validate_stage2" in pr_src,
          "pipeline_runner.py 调用 validate_stage2（第二阶段校验入链）")

    # ── S40 pull 失败即中止（不允许"以本地为准"继续）──
    check("S40", "PULL_FAILURE_BLOCKS = True" in pr_src and "以本地为准" not in pr_src,
          "pipeline_runner.py git pull 失败即中止（PULL_FAILURE_BLOCKS）")

    # ── S41 提交/日志信息使用 Stage-2 标记 ──
    check("S41", "Stage-2 run_id=" in pr_src and "Stage-1 run_id=" not in pr_src,
          "pipeline_runner.py 提交信息为 Stage-2 run_id=（无 Stage-1 残留）")

    # ── S42 main/dist/public run_id 一致 ──
    main_rid = st_doc.get("run_id")
    dist_st = load(os.path.join(ROOT, "dist", "data", "status.json"))
    dist_rid = (dist_st or {}).get("run_id") if dist_st else main_rid
    m_doc = load(os.path.join(PUBLIC, "current_metrics.json")) or {}
    pub_rid2 = m_doc.get("run_id")
    rid_ok = main_rid and dist_rid == main_rid and pub_rid2 == main_rid and pub_rid == main_rid
    check("S42", rid_ok,
          f"main/dist/public run_id 一致（{main_rid}）" if rid_ok
          else f"run_id 不一致: main={main_rid} dist={dist_rid} "
               f"metrics={pub_rid2} published={pub_rid}")

    # ════════ Stage-2 收尾新增检查 S43-S48（首页隔离 / 日报 / 部署边界）══

    # ── S43 首页当前模块仅含 current_policy_passed 事件 ──
    summary_doc = load(os.path.join(DATA, "latest-summary.json")) or {}
    n_cur = sum(1 for p in pubs if p.get("current_policy_passed") is True)
    homepage_violation = []
    for grp in ("high_risk_events", "latest_events", "china_related"):
        for e in summary_doc.get(grp, []) or []:
            if not isinstance(e, dict):
                continue
            if e.get("current_policy_passed") is not True:
                homepage_violation.append((grp, e.get("event_id", "?")))
    # 当前政策通过事件为 0 时，首页当前模块必须为空
    if n_cur == 0:
        for grp in ("high_risk_events", "latest_events", "china_related"):
            if summary_doc.get(grp):
                homepage_violation.append((grp, "non-empty-while-zero-current"))
    check("S43", not homepage_violation,
          "首页当前模块（high_risk/latest/china）仅含 current_policy_passed 事件"
          + ("" if not homepage_violation else f"；违规 {homepage_violation[:5]}"))

    # ── S44/S45/S46 日报持续跟踪校验 ──
    reports_dir = os.path.join(ROOT, "reports")
    v_policy, v_count, v_legacy = [], [], []
    if os.path.isdir(reports_dir):
        for dc in sorted(os.listdir(reports_dir)):
            rdir = os.path.join(reports_dir, dc)
            if not os.path.isdir(rdir):
                continue
            for fn in sorted(os.listdir(rdir)):
                if not fn.endswith(".json") or fn == "index.json":
                    continue
                rep = load(os.path.join(rdir, fn))
                if not isinstance(rep, dict) or rep.get("pipeline_version") != 2:
                    continue
                # 仅校验收尾后新格式日报（含 new_events/ongoing_events 数组）；
                # 旧格式历史日报为不可变归档，无这两个字段，不参与数量一致性校验
                if "new_events" not in rep or "ongoing_events" not in rep:
                    continue
                ne = rep.get("new_events", []) or []
                oe = rep.get("ongoing_events", []) or []
                for e in ne + oe:
                    if e.get("current_policy_passed") is not True:
                        v_policy.append(f"{dc}/{fn}:{e.get('event_id','?')}")
                    if e.get("legacy_migration_preserved") is True:
                        v_legacy.append(f"{dc}/{fn}:{e.get('event_id','?')}")
                for e in oe:
                    if e.get("event_status") not in ("ongoing", "developing", "easing"):
                        v_policy.append(f"{dc}/{fn}:status={e.get('event_status')}")
                if rep.get("new_event_count") != len(ne):
                    v_count.append(f"{dc}/{fn}:new {rep.get('new_event_count')}!={len(ne)}")
                if rep.get("ongoing_event_count") != len(oe):
                    v_count.append(f"{dc}/{fn}:ongoing {rep.get('ongoing_event_count')}!={len(oe)}")
                if (rep.get("ongoing_event_count") or 0) == 0 and not rep.get("ongoing_note"):
                    v_count.append(f"{dc}/{fn}:ongoing=0 无 note")
    check("S44", not v_policy,
          "日报 new/ongoing 均为 current_policy_passed 且 ongoing 状态合法"
          + ("" if not v_policy else f"；{v_policy[:4]}"))
    check("S45", not v_count,
          "日报数量与数组一致，无持续跟踪时给出说明"
          + ("" if not v_count else f"；{v_count[:4]}"))
    check("S46", not v_legacy,
          "日报 new/ongoing 不含历史迁移保留事件"
          + ("" if not v_legacy else f"；{v_legacy[:4]}"))

    # ── S47 dist 不含内部数据（canonical/backup/legacy_payload）──
    dist_data = os.path.join(ROOT, "dist", "data")
    dist_leak = []
    if os.path.isdir(dist_data):
        for bad in ("canonical", "backup", ".trash"):
            if os.path.exists(os.path.join(dist_data, bad)):
                dist_leak.append(bad)
        for root, _, files in os.walk(dist_data):
            for f in files:
                if not f.endswith(".json"):
                    continue
                p = os.path.join(root, f)
                try:
                    txt = open(p, "r", encoding="utf-8").read()
                except Exception:
                    continue
                if '"legacy_payload"' in txt:
                    dist_leak.append("legacy_payload@" + os.path.relpath(p, dist_data))
                    break
    check("S47", not dist_leak,
          "dist/data 不含 canonical/backup 及 legacy_payload"
          + ("" if not dist_leak else f"；发现 {dist_leak[:4]}"))

    # ── S48 current_metrics.publishable_clusters 语义 ──
    m2 = load(os.path.join(PUBLIC, "current_metrics.json")) or {}
    pc = m2.get("publishable_clusters")
    cp = m2.get("current_policy_passed_events")
    check("S48", pc == cp,
          f"current_metrics.publishable_clusters({pc}) == current_policy_passed_events({cp})"
          if pc == cp else
          f"publishable_clusters={pc} 与 current_policy_passed_events={cp} 不一致（不得统计历史迁移）")

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
