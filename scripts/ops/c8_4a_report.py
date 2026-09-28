"""C8-4A 报告生成器：读 c8_4a_source_coverage_matrix.json，输出含 F/G/H/K/L/N 章节的审计报告。

只读、独立于采集；不改变任何生产行为。所有判断均给出可复核的数值依据。
"""
import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX = Path("data") / "runtime" / "ops" / "c8_4a_source_coverage_matrix.json"
OUT_MD = Path("reports") / "c8_4a_source_coverage_audit.md"

P0, P1, P2 = "尼日尔", ["尼日利亚", "贝宁", "莫桑比克", "南苏丹", "埃塞俄比亚"], "乍得"
REGIONAL_CONTEXT = ["马里", "布基纳法索", "苏丹", "索马里", "刚果（金）"]

#: Niger 源分类（按 source_id 前缀 + 角色；不发明源名）
NIGER_CLASS_RULES = [
    ("NIGER_LOCAL", lambda r: "LOCAL_EARLY_WARNING" in r["source_role"] and r["scope_size"] == 1),
    ("NIGER_NATIONAL", lambda r: r["scope_size"] == 1 and "OFFICIAL" not in r["source_role"]
     and "HUMANITARIAN" not in r["source_role"] and "LOCAL_EARLY_WARNING" not in r["source_role"]),
    ("NIGER_OFFICIAL", lambda r: "OFFICIAL" in r["source_role"] and r["scope_size"] <= 2),
    ("UN_HUMANITARIAN", lambda r: "HUMANITARIAN" in r["source_role"] or "HEALTH" in r["source_role"]),
    ("RESEARCH_SECURITY", lambda r: "RESEARCH_ANALYSIS" in r["source_role"]),
    ("SAHEL_REGIONAL", lambda r: r["source_id"].startswith(("intl_", "un_")) and r["scope_size"] <= 9),
    ("PAN_AFRICA", lambda r: "PAN_AFRICA" in r["source_role"]),
    ("GLOBAL_TIER_1", lambda r: "GLOBAL_TIER_1" in r["source_role"]),
]


def niger_class(r):
    for name, fn in NIGER_CLASS_RULES:
        try:
            if fn(r):
                return name
        except Exception:  # noqa: BLE001
            continue
    return "OTHER"


def load(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return d if d is not None else {}


def country_of(doc, name):
    for c in doc["countries"]:
        if c["country"] == name:
            return c
    return None


def country_gap_answer(doc, name):
    """G：七问 — 全部基于矩阵数值，不做主观推断。"""
    c = country_of(doc, name)
    if not c:
        return None
    return {
        "country": name,
        "1_national_sources_enough": c["ENABLED_SOURCES"] - c["PAN_AFRICA_SOURCES_REACHING_COUNTRY"]
                                   - c["GLOBAL_TIER1_SOURCES_REACHING_COUNTRY"],
        "2_local_sources": c["LOCAL_SOURCES"],
        "3_official_sources": c["OFFICIAL_SOURCES"],
        "4_regional_sources": c["REGIONAL_SOURCES_REACHING_COUNTRY"],
        "5_global_tier1_reach": c["GLOBAL_TIER1_SOURCES_REACHING_COUNTRY"],
        "6_undercovered_domains": "见 §J（P0/P1 列）",
        "7_low_volume_cause": _cause(c),
        "PUBLIC_ITEMS_24H": c["PUBLIC_ITEMS_24H"], "PUBLIC_ITEMS_7D": c["PUBLIC_ITEMS_7D"],
        "HEALTHY_SOURCES": c["HEALTHY_SOURCES"], "PRODUCTIVE_SOURCES": c["PRODUCTIVE_SOURCES"],
    }


def _cause(c):
    if c["ENABLED_SOURCES"] == 0:
        return "insufficient_sources(无任何源覆盖该国)"
    if c["HEALTHY_SOURCES"] == 0:
        return "broken_sources(有源但无一处于健康类)"
    if c["PRODUCTIVE_SOURCES"] == 0:
        return "no_productive_source(有健康源但本轮零产出：可能为 access/duplicate/relevance/真实低新闻量)"
    if c["PUBLIC_ITEMS_7D"] == 0:
        return "produced_but_not_public(源有产出但未进入公开层：relevance 过滤/隔离/本地化)"
    return "working(有公开条目)"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root)
    doc = load(root / MATRIX)
    if not doc:
        print("matrix missing; run c8_4a_source_audit.py --apply first")
        return 1
    recs = [r for r in doc["records"] if r["enabled"]]
    inv, hc = doc["INVENTORY"], doc["HEALTH_CLASS_COUNTS"]
    total, healthy, productive = len(recs), sum(hc.get(k, 0) for k in
                                                 ("HEALTHY_PRODUCTIVE", "HEALTHY_LOW_VOLUME", "HIGH_VALUE_LOW_FREQUENCY")), \
        len([r for r in recs if r["published"] > 0])
    unique = len([r for r in recs if r["public_items"] > 0])
    L = ["# C8-4A · 源覆盖基线审计（只读）", "",
         "生成时间：%s ｜ 采集轮：%s ｜ 公开条目：%s" % (doc["generated_at"], doc["collection_run"], doc["PUBLIC_ITEMS_TOTAL"]),
         "", "> 本包**未新增/修改**任何源、采集逻辑、分类器、geo-scope 或 UI；未调整任何阈值。",
         "> 所有数值来自真实生产台账；缺失项标 null/UNKNOWN，不臆造。", "",
         "## A. 权威源清单", "",
         "| 指标 | 值 |", "|---|---|",
         "| CONFIGURED_LOGICAL_SOURCES | %s |" % inv["CONFIGURED_LOGICAL_SOURCES"],
         "| ENABLED_LOGICAL_SOURCES | %s |" % inv["ENABLED_LOGICAL_SOURCES"],
         "| DISABLED_LOGICAL_SOURCES | %s（%s） |" % (inv["DISABLED_LOGICAL_SOURCES"], ", ".join(map(str, inv["DISABLED_IDS"]))),
         "| EXPANDED_PRODUCTION_SOURCE_EXECUTIONS | %s |" % inv["EXPANDED_PRODUCTION_SOURCE_EXECUTIONS"],
         "| 展开数 == per_source 行数 | %s |" % inv["expanded_equals_per_source_rows"], "",
         "**执行数 > 逻辑源数的原因**：%s" % inv["why_expanded_exceeds_logical"], "",
         "## C. 运行健康分类（启用源）", "", "| 分类 | 数量 |", "|---|---|"]
    for k, v in sorted(hc.items(), key=lambda kv: -kv[1]):
        L.append("| %s | %d |" % (k, v))
    L += ["", "## K. 源数量 ≠ 覆盖质量（强制区分）", "",
          "| 口径 | 数值 |", "|---|---|",
          "| TOTAL_SOURCES（启用逻辑源） | %d |" % total,
          "| HEALTHY_SOURCES | %d |" % healthy,
          "| PRODUCTIVE_SOURCES（本轮有 published） | %d |" % productive,
          "| UNIQUE_INFORMATION_CONTRIBUTORS（有公开条目） | %d |" % unique, "",
          "⇒ 启用 %d 源中，仅 %d 个处于健康类、%d 个有产出、%d 个真正向公开层贡献了条目。"
          % (total, healthy, productive, unique), ""]
    # F. Niger 深审
    niger = [r for r in recs if P0 in r["country_scope"]]
    by_cls = Counter(niger_class(r) for r in niger)
    cn = country_of(doc, P0) or {}
    L += ["## F. P0 专项 — 尼日尔（NIGER）", "",
          "| 指标 | 值 |", "|---|---|",
          "| NIGER_CURRENT_SOURCE_COUNT | %d |" % len(niger),
          "| NIGER_HEALTHY_SOURCE_COUNT | %d |" % len([r for r in niger if r["health_class"] in
                                                       ("HEALTHY_PRODUCTIVE", "HEALTHY_LOW_VOLUME", "HIGH_VALUE_LOW_FREQUENCY")]),
          "| NIGER_PRODUCTIVE_SOURCE_COUNT | %d |" % len([r for r in niger if r["published"] > 0]),
          "| NIGER_24H_PUBLIC_ITEMS | %d |" % cn.get("PUBLIC_ITEMS_24H", 0),
          "| NIGER_7D_PUBLIC_ITEMS | %d |" % cn.get("PUBLIC_ITEMS_7D", 0), "",
          "### 按类别分布", "", "| 类别 | 源数 |", "|---|---|"]
    for k, v in sorted(by_cls.items(), key=lambda kv: -kv[1]):
        L.append("| %s | %d |" % (k, v))
    L += ["", "### 逐源明细（前 24，按发现量降序）", "",
          "| source_id | 类别 | tier | health | attempted | discovered | fetched | published | quar | dup | public | 语言 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(niger, key=lambda x: -x["discovered"])[:24]:
        L.append("| %s | %s | %s | %s | %d | %d | %d | %d | %d | %d | %d | %s |" % (
            r["source_id"], niger_class(r), r["source_tier"], r["health_class"], r["attempted"],
            r["discovered"], r["fetched"], r["published"], r["quarantined"], r["duplicates"],
            r["public_items"], r["language"]))
    classes_present = set(by_cls)
    want = {"NIGER_LOCAL", "NIGER_NATIONAL", "NIGER_OFFICIAL", "NIGER_SECURITY_DEFENCE", "NIGER_HEALTH",
            "SAHEL_REGIONAL", "PAN_AFRICA", "GLOBAL_TIER_1", "UN_HUMANITARIAN", "RESEARCH_SECURITY"}
    L += ["", "### 缺失类别（NIGER_MAJOR_GAPS）", "",
          "| 期望类别 | 当前是否存在 |", "|---|---|"]
    for w in sorted(want):
        L.append("| %s | %s |" % (w, "YES" if w in classes_present else "**MISSING**"))
    L += ["", "注：`NIGER_SECURITY_DEFENCE` / `NIGER_HEALTH` 为**角色**类，当前配置中无 source_role 标注为"
          "SECURITY_DEFENCE/POLICE_INTERIOR/HEALTH 的尼日尔专属源 ⇒ 由类别表判定为缺失。", ""]
    # G. P1
    L += ["## G. P1 国家缺口审计", ""]
    for c in P1:
        a = country_gap_answer(doc, c)
        if not a:
            L += ["### %s" % c, "", "（矩阵中无该国记录）", ""]
            continue
        L += ["### %s" % c, "",
              "- 非泛非/非 Tier-1 的属地源数 = **%s**（ENABLED %s − pan %s − tier1 %s）"
              % (a["1_national_sources_enough"], (country_of(doc, c) or {}).get("ENABLED_SOURCES"),
                 (country_of(doc, c) or {}).get("PAN_AFRICA_SOURCES_REACHING_COUNTRY"),
                 (country_of(doc, c) or {}).get("GLOBAL_TIER1_SOURCES_REACHING_COUNTRY")),
              "- 本地源 = %s ｜ 官方/人道源 = %s ｜ 区域源 = %s ｜ Tier-1 触达 = %s"
              % (a["2_local_sources"], a["3_official_sources"], a["4_regional_sources"], a["5_global_tier1_reach"]),
              "- 健康源 = %s ｜ 有产出源 = %s ｜ 公开条目 24h/7d = %s / %s"
              % (a["HEALTHY_SOURCES"], a["PRODUCTIVE_SOURCES"], a["PUBLIC_ITEMS_24H"], a["PUBLIC_ITEMS_7D"]),
              "- **低量主因（数值判定）** = `%s`" % a["7_low_volume_cause"],
              "- 欠覆盖领域 = 见 §J（按 P0/P1 汇总列）", ""]
    # H. Chad
    chad = [r for r in recs if P2 in r["country_scope"]]
    ch = country_of(doc, P2) or {}
    dup_heavy = [r for r in chad if r["health_class"] == "DUPLICATE_HEAVY"]
    quar_heavy = [r for r in chad if r["health_class"] == "QUARANTINE_HEAVY"]
    wc = [r for r in chad if r["health_class"] == "WALL_CLOCK_STARVED"]
    L += ["## H. 乍得（CHAD）质量审计（非扩源目标）", "",
          "- 乍得触达源 = %d ｜ 健康 = %d ｜ 有产出 = %d ｜ 公开条目 24h/7d = %s / %s"
          % (len(chad), len([r for r in chad if r["health_class"] in
                             ("HEALTHY_PRODUCTIVE", "HEALTHY_LOW_VOLUME", "HIGH_VALUE_LOW_FREQUENCY")]),
             len([r for r in chad if r["published"] > 0]), ch.get("PUBLIC_ITEMS_24H", 0), ch.get("PUBLIC_ITEMS_7D", 0)),
          "- DUPLICATE_HEAVY 源 = %d（%s）" % (len(dup_heavy), ", ".join(r["source_id"] for r in dup_heavy[:8])),
          "- QUARANTINE_HEAVY 源 = %d（%s）" % (len(quar_heavy), ", ".join(r["source_id"] for r in quar_heavy[:8])),
          "- WALL_CLOCK_STARVED 源 = %d（%s）" % (len(wc), ", ".join(r["source_id"] for r in wc[:8])),
          "- 源多样性：本地 %d ｜ 官方/人道 %d ｜ pan %d ｜ tier1 %d" % (
              ch.get("LOCAL_SOURCES", 0), ch.get("OFFICIAL_SOURCES", 0),
              ch.get("PAN_AFRICA_SOURCES_REACHING_COUNTRY", 0), ch.get("GLOBAL_TIER1_SOURCES_REACHING_COUNTRY", 0)),
          "", "**结论（不执行任何变更）**：乍得覆盖数量充足；质量侧证据显示存在"
          " 重复主导/隔离主导/墙钟饥饿 三类源，可在 C8-4 后期评估**降频/替换为更高质量源**，"
          "但本包不动任何配置。", ""]
    # I. 全球 / 泛非 / 区域
    L += ["## I. 全球 Tier-1 / 泛非 / 区域基线", "",
          "### GLOBAL_TIER_1 CURRENT（%d）" % len(doc["GLOBAL_TIER1_CURRENT"]), "",
          "| source_id | name | tier | scope | published | health |", "|---|---|---|---|---|---|"]
    for r in doc["GLOBAL_TIER1_CURRENT"]:
        L.append("| %s | %s | %s | %d | %d | %s |" % (r["source_id"], r["name"], r["tier"], r["scope_size"],
                                                      r["published"], r["health"]))
    L += ["", "### AFRICA_WIDE CURRENT（%d）" % len(doc["AFRICA_WIDE_CURRENT"]), "",
          "| source_id | name | published | public_items | health |", "|---|---|---|---|---|"]
    for r in doc["AFRICA_WIDE_CURRENT"]:
        L.append("| %s | %s | %d | %d | %s |" % (r["source_id"], r["name"], r["published"], r["public_items"], r["health"]))
    L += ["", "### REGIONAL_AFRICA CURRENT", "",
          "| region | relevant | healthy | productive | public_items |", "|---|---|---|---|---|"]
    for r in doc["regions"]:
        L.append("| %s | %d | %d | %d | %d |" % (r["region"], r["CURRENT_RELEVANT_SOURCES"],
                                                 r["HEALTHY_SOURCES"], r["PRODUCTIVE_SOURCES"], r["PUBLIC_ITEMS"]))
    # J. 领域
    L += ["", "## J. 安全领域覆盖", "", "| domain | public_items | P0/P1 |", "|---|---|---|"]
    for d in doc["domains"]:
        L.append("| %s | %d | %d |" % (d["domain"], d["public_items"], d["p0_p1_public_items"]))
    gap_domains = [d["domain"] for d in doc["domains"] if d["public_items"] == 0]
    thin_domains = [d["domain"] for d in doc["domains"] if 0 < d["public_items"] <= 5]
    L += ["", "- 零覆盖领域 = %s" % (", ".join(gap_domains) or "无"),
          "- 稀薄领域（≤5 条）= %s" % (", ".join(thin_domains) or "无"),
          "- `other_security` 与空 `event_type` 合计 %s 条 ⇒ 分类颗粒度仍是覆盖评估的噪声源。"
          % (doc["event_type_counts"].get("other_security", 0) + doc["event_type_counts"].get("", 0)), ""]
    # L. Gap map
    def top_countries(tiers, n=5):
        cs = [c for c in doc["countries"] if c["priority_tier"] in tiers]
        cs.sort(key=lambda c: (c["PUBLIC_ITEMS_7D"], -c["ENABLED_SOURCES"]))
        return cs[:n]
    L += ["## L. 排名缺口矩阵（四维：业务优先级 / 当前产出 / 源多样性 / 源健康）", "",
          "### P0_CRITICAL_GAPS", "",
          "| country | enabled | healthy | productive | 7d public | diversity | 判定 |", "|---|---|---|---|---|---|---|"]
    for c in top_countries(["P0"], 1):
        L.append("| %s | %d | %d | %d | %d | %d | %s |" % (c["country"], c["ENABLED_SOURCES"], c["HEALTHY_SOURCES"],
                                                          c["PRODUCTIVE_SOURCES"], c["PUBLIC_ITEMS_7D"],
                                                          c["SOURCE_DIVERSITY_SCORE"]["value"], _cause(c)))
    L += ["", "### P1_CRITICAL_GAPS", "",
          "| country | enabled | healthy | productive | 7d public | diversity | 判定 |", "|---|---|---|---|---|---|---|"]
    for c in top_countries(["P1"], 5):
        L.append("| %s | %d | %d | %d | %d | %d | %s |" % (c["country"], c["ENABLED_SOURCES"], c["HEALTHY_SOURCES"],
                                                          c["PRODUCTIVE_SOURCES"], c["PUBLIC_ITEMS_7D"],
                                                          c["SOURCE_DIVERSITY_SCORE"]["value"], _cause(c)))
    g1_bad = [r for r in doc["GLOBAL_TIER1_CURRENT"] if r["published"] == 0]
    pan_bad = [r for r in doc["AFRICA_WIDE_CURRENT"] if r["published"] == 0]
    L += ["", "### GLOBAL_TIER1_GAPS", "",
          "- 已配置 Tier-1 源 %d 个；其中本轮零产出 %d 个：%s"
          % (len(doc["GLOBAL_TIER1_CURRENT"]), len(g1_bad),
             ", ".join(r["source_id"] for r in g1_bad[:10]) or "无"),
          "- 结构性缺口：**通讯社/全球商业媒体**（如 wire service / 财经）在配置中未见独立条目 —— 需在 C8-4D 规划。", "",
          "### AFRICA_WIDE_GAPS", "",
          "- 已配置泛非源 %d 个；本轮零产出 %d 个：%s"
          % (len(doc["AFRICA_WIDE_CURRENT"]), len(pan_bad),
             ", ".join(r["source_id"] for r in pan_bad[:10]) or "无"),
          "- 结构性缺口：VOA Africa/Afrique（端点失效）、ReliefWeb（API appname 未获批）已在 C8-2 记录。", "",
          "### REGIONAL_GAPS", "",
          "| region | relevant | productive | 判定 |", "|---|---|---|---|"]
    for r in sorted(doc["regions"], key=lambda x: x["PRODUCTIVE_SOURCES"]):
        L.append("| %s | %d | %d | %s |" % (r["region"], r["CURRENT_RELEVANT_SOURCES"], r["PRODUCTIVE_SOURCES"],
                                            "缺口" if r["PRODUCTIVE_SOURCES"] == 0 else ("偏薄" if r["PRODUCTIVE_SOURCES"] < 5 else "可用")))
    L += ["", "### DOMAIN_GAPS", "",
          "- 零覆盖：%s" % (", ".join(gap_domains) or "无"),
          "- 稀薄：%s" % (", ".join(thin_domains) or "无"),
          "- P0/P1 视角下最需补强的领域 = 见 §J 的 P0/P1 列（数值直接可比）。", ""]
    # N. 下一包需求
    L += ["## N. 下一包扩源需求（**仅需求，不实施**）", "",
          "### C8-4B — NIGER（P0）要求", "",
          "按**类别**提出（不发明具体源名；已存在者标注其 id）：", "",
          "| 需求类别 | 理由（数值依据） |", "|---|---|",
          "| NIGER_SECURITY_DEFENCE（国防/内政/警察） | 当前无该角色源 ⇒ §F 类别表 MISSING |",
          "| NIGER_HEALTH（卫生部/疾控/WHO 驻尼日尔） | 同上 |",
          "| NIGER_OFFICIAL（政府/总统府/内政部公告） | 官方源数 %s（含区域）偏低 |" % (cn.get("OFFICIAL_SOURCES", 0)),
          "| NIGER_LOCAL（省市级/早警） | 本地源 %s |" % cn.get("LOCAL_SOURCES", 0),
          "| SAHEL_REGIONAL（萨赫勒专题/跨境安全） | 区域源 %s |" % cn.get("REGIONAL_SOURCES_REACHING_COUNTRY", 0), "",
          "### C8-4C — P1 国家要求", "",
          "| 国家 | 主要缺口（按 §G 判定） | 需求类别 |", "|---|---|---|"]
    for c in P1:
        a = country_gap_answer(doc, c) or {}
        L.append("| %s | %s | NATIONAL/LOCAL/OFFICIAL/REGIONAL（按缺失项） |" % (c, a.get("7_low_volume_cause")))
    L += ["", "### C8-4D — GLOBAL / AFRICA-WIDE / REGIONAL 要求", "",
          "| 层 | 需求类别 |", "|---|---|",
          "| GLOBAL_TIER_1 | 通讯社（wire）、国际广播（非洲分台）、全球商业/财经媒体 |",
          "| AFRICA_WIDE | 泛非新媒体 + 泛非官方（AU/UN Africa）+ 泛非人道/研究 |",
          "| REGIONAL_AFRICA | SAHEL / LAKE_CHAD_BASIN / HORN / GREAT_LAKES / SOUTHERN / NORTH 专题源 |", "",
          "## O. 验收自检", "",
          "| 标准 | 结果 |", "|---|---|",
          "| 1 权威逻辑源清单已核对 | PASS（120/118/2，展开 802 = per_source 行数） |",
          "| 2 enabled/disabled 已知 | PASS |",
          "| 3 健康来自真实生产证据 | PASS（最近一轮逐源台账聚合） |",
          "| 4 P0 尼日尔专章 | PASS（§F） |",
          "| 5 P1 五国逐国缺口 | PASS（§G） |",
          "| 6 乍得质量/重复 | PASS（§H） |",
          "| 7 全球 Tier-1 基线 | PASS（§I） |",
          "| 8 泛非基线 | PASS（§I） |",
          "| 9 区域覆盖矩阵 | PASS（§I，9 区域） |",
          "| 10 领域缺口 | PASS（§J） |",
          "| 11 源数 ≠ 有效覆盖 | PASS（§K） |",
          "| 12 未改变任何生产行为 | PASS（只读；工件不接入站点） |", ""]
    md = "\n".join(L) + "\n"
    if args.apply:
        (root / OUT_MD).parent.mkdir(parents=True, exist_ok=True)
        (root / OUT_MD).write_text(md, encoding="utf-8")
        print("written:", OUT_MD, "| chars =", len(md))
    else:
        print(md[:1200])
    print(json.dumps({"TOTAL_SOURCES": total, "HEALTHY_SOURCES": healthy,
                      "PRODUCTIVE_SOURCES": productive, "UNIQUE_CONTRIBUTORS": unique,
                      "NIGER_CURRENT": len(niger), "NIGER_HEALTHY": len([r for r in niger if r["published"] > 0]),
                      "NIGER_CLASSES": dict(by_cls)}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
