#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I2-B: relation type ontology registry + 3-region intelligence audit records.

Adds:
  data/intelligence/africa/relation_types.json   (ontology registry)
  data/intelligence/africa/audit_records.json    (>=36 audit records, sourced)
  new audit sources appended to sources.json
Applies source-supported data corrections from the audit (SAMIM end date,
Sudan/Mozambique/Chad current-status notes, evidence claim upgrades).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
AUDIT_DATE = "2026-08-06"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def save(name, obj):
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


RELATION_TYPES = [
    {"relation_type": "affiliated_with", "label_zh": "存在关联", "label_en": "Affiliated with",
     "definition": "实体之间存在组织或网络层面的关联，但未构成正式隶属、效忠或组成部分关系。",
     "direction": "undirected", "reciprocal": True, "time_sensitive": False,
     "evidence_requirement": "至少一个可定位来源说明关联存在",
     "graph_style": "实线", "common_confusion": "常与 pledged_allegiance_to / constituent_of 混淆",
     "example": "JNIM 与萨赫勒其他武装组织的一般性关联"},
    {"relation_type": "pledged_allegiance_to", "label_zh": "宣誓效忠于", "label_en": "Pledged allegiance to",
     "definition": "实体公开宣誓效忠（bay'ah）某网络或领导人，构成正式效忠关系；属高时间敏感性语义，与一般关联、组成、结盟均不同。",
     "direction": "directed", "reciprocal": False, "time_sensitive": True,
     "evidence_requirement": "公开宣誓声明或权威来源对效忠关系的确认",
     "graph_style": "实线箭头（效忠方向）", "common_confusion": "不得映射为 affiliated_with；效忠≠普通网络关联",
     "example": "JNIM 于 2017 年向基地组织宣誓效忠；ISWAP 于 2016 年向伊斯兰国宣誓效忠"},
    {"relation_type": "constituent_of", "label_zh": "组成部分", "label_en": "Constituent of",
     "definition": "实体是另一实体的组成部分（如并入联盟、合并后的一部分）。",
     "direction": "directed", "reciprocal": False, "time_sensitive": True,
     "evidence_requirement": "成立/合并声明或权威来源",
     "graph_style": "实线箭头", "common_confusion": "与 part_of_network 的区别：组成是结构性并入",
     "example": "Ansar Dine、穆拉比通等并入 JNIM"},
    {"relation_type": "part_of_network", "label_zh": "属于某网络", "label_en": "Part of network",
     "definition": "实体属于某一跨国网络体系（如基地组织网络、伊斯兰国网络）的组成部分。",
     "direction": "directed", "reciprocal": False, "time_sensitive": True,
     "evidence_requirement": "权威来源对网络归属的描述",
     "graph_style": "实线箭头", "common_confusion": "网络归属≠正式宣誓效忠",
     "example": "JNIM 属于基地组织网络体系"},
    {"relation_type": "split_from", "label_zh": "分裂自", "label_en": "Split from",
     "definition": "实体从另一实体中分裂出来（通常伴随内部冲突或派别决裂）。",
     "direction": "directed", "reciprocal": False, "time_sensitive": True,
     "evidence_requirement": "分裂声明或权威来源",
     "graph_style": "实线箭头", "common_confusion": "与 merged_from 相反",
     "example": "ISWAP 2016 年从博科圣地分裂"},
    {"relation_type": "merged_from", "label_zh": "由……合并而来", "label_en": "Merged from",
     "definition": "实体由多个既有实体合并或整合而成。",
     "direction": "directed", "reciprocal": False, "time_sensitive": True,
     "evidence_requirement": "合并声明或权威来源",
     "graph_style": "实线箭头", "common_confusion": "",
     "example": "JNIM 2017 年由多支武装整合成立"},
    {"relation_type": "led_by", "label_zh": "领导", "label_en": "Led by",
     "definition": "人物领导某实体（当前或历史）。",
     "direction": "directed", "reciprocal": False, "time_sensitive": True,
     "evidence_requirement": "权威来源对领导关系的确认（注意现任领导变化）",
     "graph_style": "实线箭头", "common_confusion": "与 founded_by 区分现任/创立",
     "example": "伊亚德·阿格·加利领导 JNIM"},
    {"relation_type": "founded_by", "label_zh": "创立者", "label_en": "Founded by",
     "definition": "人物创立某实体（历史事实，不随现任领导变化）。",
     "direction": "directed", "reciprocal": False, "time_sensitive": False,
     "evidence_requirement": "成立史料或权威来源",
     "graph_style": "实线箭头", "common_confusion": "",
     "example": "阿马杜·库法创立马西纳旅"},
    {"relation_type": "operates_in", "label_zh": "活动于", "label_en": "Operates in",
     "definition": "实体在国家/地区有活动存在。注意：活动不等于控制。",
     "direction": "directed", "reciprocal": False, "time_sensitive": True,
     "evidence_requirement": "活动记录或权威来源；不得以活动推断控制",
     "graph_style": "轻虚线", "common_confusion": "活动≠存在≠影响≠控制",
     "example": "JNIM 在马里、布基纳法索、尼日尔活动"},
    {"relation_type": "active_in_region", "label_zh": "在区域活动", "label_en": "Active in region",
     "definition": "实体在某一区域层面有活动（不绑定单一国家）。",
     "direction": "directed", "reciprocal": False, "time_sensitive": True,
     "evidence_requirement": "活动记录",
     "graph_style": "轻虚线", "common_confusion": "",
     "example": "ISWAP 在乍得湖盆地活动"},
    {"relation_type": "allied_with", "label_zh": "结盟", "label_en": "Allied with",
     "definition": "实体之间形成正式或事实上的联盟。",
     "direction": "undirected", "reciprocal": True, "time_sensitive": True,
     "evidence_requirement": "结盟声明或权威来源",
     "graph_style": "实线", "common_confusion": "与 cooperates_with 程度不同",
     "example": "南苏丹 NAS 与 SPLM-IO 结盟"},
    {"relation_type": "cooperates_with", "label_zh": "合作", "label_en": "Cooperates with",
     "definition": "实体之间存在合作行动（战术、情报、后勤等）。",
     "direction": "undirected", "reciprocal": True, "time_sensitive": True,
     "evidence_requirement": "合作记录",
     "graph_style": "实线", "common_confusion": "",
     "example": "SAMIM 与 FADM 合作"},
    {"relation_type": "supported_by", "label_zh": "受到支持", "label_en": "Supported by",
     "definition": "实体受到另一实体（国家、组织、网络）的支持（资金、武器、训练等）。",
     "direction": "directed", "reciprocal": False, "time_sensitive": True,
     "evidence_requirement": "权威来源对支持关系的确认",
     "graph_style": "实线箭头", "common_confusion": "与 alleged_support 区别：已确认 vs 据称",
     "example": "RSF 据称受到外部支持（有争议）"},
    {"relation_type": "supports", "label_zh": "支持", "label_en": "Supports",
     "definition": "实体向另一实体提供支持。",
     "direction": "directed", "reciprocal": False, "time_sensitive": True,
     "evidence_requirement": "支持记录",
     "graph_style": "实线箭头", "common_confusion": "",
     "example": ""},
    {"relation_type": "hostile_to", "label_zh": "敌对", "label_en": "Hostile to",
     "definition": "实体之间处于敌对或冲突状态（武装冲突、政治对立等）。",
     "direction": "undirected", "reciprocal": True, "time_sensitive": True,
     "evidence_requirement": "冲突记录或权威来源；不得简单归因于意识形态",
     "graph_style": "醒目冲突线（双箭头样式）", "common_confusion": "需区分全面/局部/历史敌对",
     "example": "JNIM 与 IS Sahel 敌对；SAF 与 RSF 交战"},
    {"relation_type": "competes_with", "label_zh": "竞争", "label_en": "Competes with",
     "definition": "实体之间存在竞争（地盘、招募、资源、影响力）。",
     "direction": "undirected", "reciprocal": True, "time_sensitive": True,
     "evidence_requirement": "竞争记录",
     "graph_style": "虚线", "common_confusion": "竞争可能升级为敌对",
     "example": "JAS 与 ISWAP 争夺水道走私收入"},
    {"relation_type": "fought_against", "label_zh": "交战中", "label_en": "Fought against",
     "definition": "实体之间发生过实际武装交火（历史或当前）。",
     "direction": "undirected", "reciprocal": True, "time_sensitive": True,
     "evidence_requirement": "交火记录",
     "graph_style": "冲突线", "common_confusion": "",
     "example": "FADM 与 IS-Mozambique 交战"},
    {"relation_type": "historically_associated_with", "label_zh": "历史关联", "label_en": "Historically associated with",
     "definition": "实体之间存在历史性关联（前史、渊源），当前未必活跃。",
     "direction": "undirected", "reciprocal": True, "time_sensitive": False,
     "evidence_requirement": "历史资料",
     "graph_style": "灰色虚线", "common_confusion": "",
     "example": "IS-Mozambique 与伊斯兰国非洲省网络的历史关联"},
    {"relation_type": "deployed_in", "label_zh": "部署于", "label_en": "Deployed in",
     "definition": "部队/任务在特定国家或地区部署。",
     "direction": "directed", "reciprocal": False, "time_sensitive": True,
     "evidence_requirement": "部署记录",
     "graph_style": "实线箭头", "common_confusion": "",
     "example": "卢旺达部队部署于德尔加杜角"},
    {"relation_type": "member_of_force", "label_zh": "部队成员", "label_en": "Member of force",
     "definition": "国家武装力量为多国部队/任务的成员。",
     "direction": "directed", "reciprocal": False, "time_sensitive": True,
     "evidence_requirement": "部队组成文件",
     "graph_style": "实线箭头", "common_confusion": "",
     "example": "乍得为 MNJTF 成员"},
    {"relation_type": "political_affiliation", "label_zh": "政治归属", "label_en": "Political affiliation",
     "definition": "实体与政治运动、政府或政治派别的归属关系。",
     "direction": "undirected", "reciprocal": True, "time_sensitive": True,
     "evidence_requirement": "政治声明",
     "graph_style": "虚线", "common_confusion": "",
     "example": ""},
    {"relation_type": "alleged_support", "label_zh": "据称受到支持", "label_en": "Alleged support",
     "definition": "实体据称受到支持但未经证实或有争议。",
     "direction": "directed", "reciprocal": False, "time_sensitive": True,
     "evidence_requirement": "指控记录 + 争议标注",
     "graph_style": "虚线加提示标识", "common_confusion": "不得写成已确认支持",
     "example": "关于外部国家对 RSF 提供武器的指控"},
    {"relation_type": "cross_border_link", "label_zh": "跨境关联", "label_en": "Cross-border link",
     "definition": "实体与邻国/跨境网络存在安全关联（人员、武器、走私路线等）。",
     "direction": "undirected", "reciprocal": True, "time_sensitive": True,
     "evidence_requirement": "跨境活动记录",
     "graph_style": "虚线", "common_confusion": "",
     "example": "IS-Mozambique 与坦桑尼亚边境关联"},
    {"relation_type": "criminal_link", "label_zh": "犯罪关联", "label_en": "Criminal link",
     "definition": "实体与跨境犯罪网络存在关联（走私、勒索、绑架等）。",
     "direction": "undirected", "reciprocal": True, "time_sensitive": True,
     "evidence_requirement": "犯罪活动记录",
     "graph_style": "虚线", "common_confusion": "",
     "example": "萨赫勒武装与走私网络的关联"},
]


NEW_SOURCES = [
    {"source_id": "au-psc-mnjtf-2025-12", "title": "Consideration of the Report of the Commission on the MNJTF Mandate (AU PSC 1318th session)",
     "publisher": "Amani Africa (AU PSC session brief)", "source_type": "regional_org", "reliability": "high",
     "url": "http://amaniafrica-et.org/consideration-of-the-report-of-the-commission-on-the-mnjtf-mandate",
     "published_at": "2025-12-14", "accessed_at": AUDIT_DATE,
     "notes": "I2-B 审计来源：MNJTF 授权审议，含 ACSS 伤亡数据与成员国动态。"},
    {"source_id": "au-psc-lakechad-2025-11", "title": "Update on the Situation in the Lake Chad Basin Area (AU PSC 1313th session)",
     "publisher": "Amani Africa (AU PSC session brief)", "source_type": "regional_org", "reliability": "high",
     "url": "http://amaniafrica-et.org/update-on-the-situation-in-the-lake-chad-basin-area/",
     "published_at": "2025-11-18", "accessed_at": AUDIT_DATE,
     "notes": "I2-B 审计来源：2025-11-05~08 JAS 对 ISWAP 岛屿攻势、MNJTF 能力缺口。"},
    {"source_id": "asa-lakechad-2026-06", "title": "Monthly Forecast: Central Africa and the Lake Chad Basin (June 2026)",
     "publisher": "African Security Analysis", "source_type": "research_institute", "reliability": "medium",
     "url": "https://www.africansecurityanalysis.com/reports/monthly-forecast-central-africa-and-the-lake-chad-basin-unoca-mnjtf-fragmentation-and-the-deepening-insurgent-adaptation-crisis",
     "published_at": "2026-06-01", "accessed_at": AUDIT_DATE,
     "notes": "I2-B 审计来源：MNJTF 自 2024-07 无大规模行动、尼日尔退出、乍得可能缩减参与、ISWAP 无人机能力。"},
    {"source_id": "asa-cabo-delgado-2025", "title": "Cabo Delgado Crisis (2025)",
     "publisher": "African Security Analysis", "source_type": "research_institute", "reliability": "medium",
     "url": "https://www.africansecurityanalysis.com/reports/cabo-delgado-crisis",
     "published_at": "2025-06-01", "accessed_at": AUDIT_DATE,
     "notes": "I2-B 审计来源：2025-05 起德尔加杜角暴力升级、SAMIM 撤出、流离失所数据。"},
    {"source_id": "govuk-sudan-cpin-2026-07", "title": "Country Policy and Information Note: Security situation, Sudan (July 2026)",
     "publisher": "UK Home Office", "source_type": "government", "reliability": "high",
     "url": "https://www.gov.uk/government/publications/sudan-country-policy-and-information-notes/country-policy-and-information-note-security-situation-sudan-july-2026-accessible",
     "published_at": "2026-07-01", "accessed_at": AUDIT_DATE,
     "notes": "I2-B 审计来源：2026-06 控制格局（SAF/RSF/SPLM-N/SLA-AW）、ACLED 数据。"},
    {"source_id": "aj-sudan-2026-04", "title": "After three years of war, what is the situation like in Sudan?",
     "publisher": "Al Jazeera", "source_type": "news_media", "reliability": "medium",
     "url": "https://www.aljazeera.com/news/2026/4/14/after-three-years-of-war-what-is-the-situation-like-in-sudan",
     "published_at": "2026-04-14", "accessed_at": AUDIT_DATE,
     "notes": "I2-B 审计来源：流离失所 1400 万、WHO 约 4 万死亡、El Fasher 2025-10 陷落。"},
    {"source_id": "xinhua-sudan-2025-12", "title": "Sudan's 2025 -- a year of shifting fronts, deepening crises",
     "publisher": "Xinhua", "source_type": "news_media", "reliability": "medium",
     "url": "https://www.news.cn/english/20251229/e8a770f99f0543a6bc0785d9d1cf1e77/c.html",
     "published_at": "2025-12-29", "accessed_at": AUDIT_DATE,
     "notes": "I2-B 审计来源：2025 年战线变化、喀土穆收复、El Fasher 陷落、饥荒确认。"},
    {"source_id": "acled-sudan-2025", "title": "Two years of war in Sudan: How the SAF is gaining the upper hand",
     "publisher": "ACLED", "source_type": "research_institute", "reliability": "high",
     "url": "http://acleddata.com/report/two-years-war-sudan-how-saf-gaining-upper-hand",
     "published_at": "2025-04-01", "accessed_at": AUDIT_DATE,
     "notes": "I2-B 审计来源：达尔富尔联合部队构成与立场（JEM/SLM-MM 2023-11 支持 SAF；SLM/A-TC/GSLF 2025-02 支持 RSF）。"},
    {"source_id": "thenigerianvoice-2025-12", "title": "Divided Sudan, Elusive Peace",
     "publisher": "The Nigerian Voice (analysis)", "source_type": "news_media", "reliability": "medium",
     "url": "https://www.thenigerianvoice.com/news/366382/divided-sudan-elusive-peace.html",
     "published_at": "2025-12-15", "accessed_at": AUDIT_DATE,
     "notes": "I2-B 审计来源：2025 年战线复盘、RSF 并行政府（尼亚拉）、赫梅蒂任总统委员会主席。"},
    {"source_id": "nowinsa-sudan-2025", "title": "Port Sudan power struggle: Will armed groups defy the army before cabinet is formed?",
     "publisher": "Now in SA (analysis)", "source_type": "news_media", "reliability": "medium",
     "url": "https://nowinsa.co.za/2025/port-sudan-power-struggle-will-armed-groups-defy-the-army-before-cabinet-is-formed/",
     "published_at": "2025-06-22", "accessed_at": AUDIT_DATE,
     "notes": "I2-B 审计来源：2025 年苏丹港组阁摩擦、SLM-MM 与军队政府紧张关系。"},
    {"source_id": "reliefweb-moz-2026-01", "title": "Mozambique Conflict Monitor Update: 14 January 2026",
     "publisher": "Cabo Ligado (via ReliefWeb)", "source_type": "research_institute", "reliability": "high",
     "url": "https://reliefweb.int/report/mozambique/mozambique-conflict-monitor-update-14-january-2026",
     "published_at": "2026-01-14", "accessed_at": AUDIT_DATE,
     "notes": "I2-B 审计来源：ISM-RDF 冲突、TotalEnergies LNG 2025-10 解除不可抗力、Macomia/Muidumbe 活动。"},
    {"source_id": "reliefweb-moz-2026-03", "title": "Mozambique Conflict Monitor Update: 25 March 2026",
     "publisher": "Cabo Ligado (via ReliefWeb)", "source_type": "research_institute", "reliability": "high",
     "url": "https://reliefweb.int/report/mozambique/mozambique-conflict-monitor-update-25-march-2026-enpt",
     "published_at": "2026-03-25", "accessed_at": AUDIT_DATE,
     "notes": "I2-B 审计来源：累计数据（2017-10 起 6515 死亡、2172 起 ISM 事件）、FADM 海军对民船打击、RDF 撤军前景。"},
    {"source_id": "warwatch-moz-2025", "title": "Non-international armed conflict in Mozambique",
     "publisher": "Geneva Academy RULAC (WarWatch)", "source_type": "research_institute", "reliability": "high",
     "url": "https://warwatch.ch/situations/non-international-armed-conflict-in-mozambique/",
     "published_at": "2025-06-30", "accessed_at": AUDIT_DATE,
     "notes": "I2-B 审计来源：ISM 领导层更迭（Omar 2023-08 被击毙、Abu Zainabo 继任）、SAMIM 2024-07 结束、RDF 2024 增兵 2000、EUMAM 至 2026 年中。"},
]


def build_audit_records():
    records = []
    def add(region, claim_id, text, ents, rels, srcs, locator, pub, valid_as_of,
            support, issue, correction, final_text, status, notes, cids=None, rids=None):
        records.append({
            "audit_id": f"aud-{region}-{len(records) + 1:03d}",
            "region_id": region,
            "claim_id": claim_id,
            "current_claim_text": text,
            "entity_ids": ents, "relation_ids": rels, "country_ids": cids or [],
            "region_ids": [region], "source_ids": srcs, "source_locator": locator,
            "source_published_at": pub, "claim_valid_as_of": valid_as_of,
            "support_result": support, "issue_type": issue,
            "correction_action": correction, "final_claim_text": final_text,
            "verification_status": status,
            "reviewed_at": AUDIT_DATE, "reviewer_notes": notes,
        })

    LCB = "region-lake-chad-basin"
    SUD = "region-sudan-red-sea-horn"
    MOZ = "region-southeast-africa-mozambique"

    # ---------------- Lake Chad basin (14) ----------------
    add(LCB, "cl-lcb-jas-iswap-split-2016",
        "ISWAP 于 2016 年从博科圣地分裂并宣誓效忠伊斯兰国。",
        ["actor-jas", "actor-iswap", "actor-islamic-state"], ["rel-iswap-islamic-state-affiliation"],
        ["crisis-group-lake-chad"], "Lake Chad Basin analyses (2016 split)", "2023-12-01", "2023-12-01",
        "supported", "", "保留；补充 2025 年动态", "ISWAP 于 2016 年从博科圣地分裂并宣誓效忠伊斯兰国；2025 年仍为乍得湖盆地主要 IS 分支。",
        "verified", "多来源一致；I2-B 审计确认。",
        cids=["country-nigeria", "country-chad", "country-cameroon", "country-niger"])
    add(LCB, "cl-lcb-jas-iswap-rivalry-current",
        "JAS 与 ISWAP 在乍得湖盆地持续敌对并争夺地盘与资源。",
        ["actor-jas", "actor-iswap"], ["rel-jas-iswap-conflict"],
        ["au-psc-lakechad-2025-11", "asa-lakechad-2026-06"],
        "2025-11-05~08 JAS 对 ISWAP 岛屿攻势（AU PSC 1313 次会议简报）", "2025-11-18", "2025-11-18",
        "supported", "stale_source", "更新为近期状态",
        "JAS 与 ISWAP 敌对持续；2025-11-05~08 JAS 发动跨岛屿攻势，为 2021 年谢考死后 ISWAP 在乍得湖岛屿最大的领土损失。",
        "verified", "I2-B 审计以 2025-11 AU PSC 简报确认。")
    add(LCB, "cl-lcb-shekau-death-2021",
        "博科圣地长期领导人阿布巴卡尔·谢考于 2021 年死亡，此后 JAS 领导层碎片化。",
        ["actor-jas"], [],
        ["crisis-group-lake-chad", "au-psc-lakechad-2025-11"],
        "Shekau death (2021) + AU PSC brief", "2025-11-18", "2025-11-18",
        "supported", "", "保留",
        "谢考于 2021 年死亡；此后 JAS 呈高度分散的派别化指挥结构。",
        "verified", "死亡时间获 ISWAP 与多方确认；碎片化获 AU PSC 简报支持。")
    add(LCB, "cl-lcb-jas-leader-current",
        "JAS 现任最高领导人尚未形成公开一致认定。",
        ["actor-jas"], [],
        ["au-psc-lakechad-2025-11"],
        "AU PSC brief (fragmented command)", "2025-11-18", "2025-11-18",
        "partially_supported", "single_source", "降级表述",
        "公开资料显示 JAS 由相互竞争的派别指挥官领导（如巴库拉·莫杜/萨哈巴等派别）；单一资料称伊布拉欣·巴库拉·多罗为现任领导人，尚未获权威来源一致确认。",
        "partially_verified", "I2-A 未设 JAS 现任领导人字段；本审计如实记录不确定。")
    add(LCB, "cl-lcb-iswap-capability-2025",
        "ISWAP 于 2025 年部署无人机与夜视装备，据报攻占 15 处尼日利亚军事据点并发动'Camp Holocaust'攻势。",
        ["actor-iswap"], [],
        ["au-psc-lakechad-2025-11", "asa-lakechad-2026-06"],
        "AU PSC 1313/1318 简报", "2026-06-01", "2026-06-01",
        "supported", "", "新增近期能力描述",
        "ISWAP 2025 年部署武装/侦察无人机与夜视装备，发动'Camp Holocaust'攻势攻占多处军事据点。",
        "verified", "ACSS/AU PSC 口径。")
    add(LCB, "cl-lcb-mnjtf-2015",
        "多国联合特遣部队（MNJTF）于 2015 年启动乍得湖盆地联合反恐行动。",
        ["actor-mnjtf"], ["rel-chad-mnjtf-member"],
        ["crisis-group-lake-chad"], "MNJTF analyses", "2023-12-01", "2023-12-01",
        "supported", "", "保留",
        "MNJTF 于 2015 年成立并启动乍得湖盆地联合反恐行动，成员含乍得、尼日利亚、尼日尔、喀麦隆、贝宁。",
        "verified", "多来源一致。")
    add(LCB, "cl-lcb-mnjtf-mandate-2026",
        "MNJTF 授权于 2025-01-13 续延 12 个月至 2026-02-01；2025-12-15 AU PSC 第 1318 次会议审议新授权。",
        ["actor-mnjtf"], [],
        ["au-psc-mnjtf-2025-12"],
        "PSC 1318th session brief (2025-12-15)", "2025-12-14", "2026-02-01",
        "supported", "stale_source", "更新授权状态",
        "MNJTF 授权经 AU PSC 于 2025-01-13 续延 12 个月（至 2026-02-01），2025-12-15 第 1318 次会议审议延续安排。",
        "verified", "I2-B 审计更新。")
    add(LCB, "cl-lcb-mnjtf-niger-withdrawal",
        "尼日尔已退出 MNJTF；乍得存在缩减参与的可能。",
        ["actor-mnjtf"], [],
        ["asa-lakechad-2026-06"],
        "June 2026 forecast (MNJTF institutional challenges)", "2026-06-01", "2026-06-01",
        "supported", "stale_source", "更新成员国状态",
        "尼日尔已退出 MNJTF，乍得被指可能缩减参与；该部队面临结构性挑战。",
        "verified", "I2-B 审计更新（原数据未反映尼日尔退出）。")
    add(LCB, "cl-lcb-mnjtf-pause-2024",
        "MNJTF 自 2024 年 7 月以来未开展大规模区域行动。",
        ["actor-mnjtf"], [],
        ["asa-lakechad-2026-06"],
        "June 2026 forecast (operational pause)", "2026-06-01", "2026-06-01",
        "supported", "", "新增",
        "MNJTF 自 2024 年 7 月'Operation Lake Sanity 2'后未开展大规模区域行动。",
        "verified", "I2-B 审计新增。")
    add(LCB, "cl-lcb-acss-fatalities-2025",
        "ACSS 统计显示 2025 年乍得湖盆地圣战相关死亡上升 7% 至 3,982 人（占非洲大陆 18%）；平民受袭上升 32% 至 880 人（2016 年以来最高）。",
        [], [],
        ["au-psc-lakechad-2025-11"],
        "ACSS data cited in AU PSC brief", "2025-11-18", "2025-11-18",
        "supported", "", "新增统计数据",
        "ACSS 数据：2025 年乍得湖盆地圣战相关死亡 3,982 人（+7%），平民受袭 880 人（+32%，2016 年以来最高）。",
        "verified", "单一权威转引来源。")
    add(LCB, "cl-lcb-chad-fatalities-2025",
        "乍得 2025 年圣战相关死亡人数翻倍以上至 242 人。",
        ["actor-chad-army"], [],
        ["au-psc-lakechad-2025-11"],
        "ACSS data (Chad 242 deaths)", "2025-11-18", "2025-11-18",
        "supported", "", "新增",
        "乍得 2025 年相关死亡 242 人，较上年翻倍以上；同时面临 MNJTF 参与不确定性。",
        "verified", "I2-B 审计补充乍得当前风险。",
        cids=["country-chad"])
    add(LCB, "cl-lcb-extortion-war-drivers",
        "JAS 与 ISWAP 2025 年冲突的核心驱动是水道走私（武器、燃料）、勒索收入与人员招募竞争，而非单纯意识形态差异。",
        ["actor-jas", "actor-iswap"], ["rel-jas-iswap-conflict"],
        ["au-psc-lakechad-2025-11", "asa-lakechad-2026-06"],
        "AU PSC brief (control of extortion revenues, smuggling corridors)", "2025-11-18", "2025-11-18",
        "supported", "", "强化原因分析",
        "双方 2025 年冲突集中于对乍得湖岛屿水道勒索收入、武器与燃料走私走廊的控制，以及招募与地方影响力竞争。",
        "verified", "基于 AU PSC/ASA 分析，非意识形态单一归因。")
    add(LCB, "cl-lcb-jas-activity-areas-2025",
        "JAS 2025 年活动集中于博尔诺（桑比萨森林）、乍得湖岛屿与曼达拉山；2025 年 6 月起袭击 Baga、Goldavi、Kirawa 等地。",
        ["actor-jas"], [],
        ["au-psc-lakechad-2025-11"],
        "AU PSC brief (JAS attacks at Baga, Goldavi, Kirawa)", "2025-11-18", "2025-11-18",
        "supported", "", "更新活动范围",
        "JAS 活跃于博尔诺州桑比萨森林、乍得湖岛屿及尼日利亚-喀麦隆边境曼达拉山；2025 年 6 月起对 Baga、Goldavi、Kirawa 等地发动夜袭。",
        "verified", "I2-B 审计更新。")
    add(LCB, "cl-lcb-activity-not-control",
        "平台关系'活动于'表述不得被理解为组织控制相关地区。",
        [], [],
        ["au-psc-lakechad-2025-11", "crisis-group-lake-chad"],
        "methodological framing (activity vs control)", "2025-11-18", "2025-11-18",
        "supported", "framing", "保留方法论约束",
        "JAS/ISWAP 在马里/尼日尔/喀麦隆等国的活动不等于控制；控制仅限部分区域与时段。",
        "verified", "延续 V0.2 名称与表述规范。")

    # ---------------- Sudan (14) ----------------
    add(SUD, "cl-sdn-war-start-2023",
        "2023 年 4 月 15 日苏丹武装部队与快速支援部队爆发全面武装冲突。",
        ["actor-saf", "actor-rsf"], ["rel-saf-rsf-war"],
        ["govuk-sudan-cpin-2026-07", "aj-sudan-2026-04"], "CPIN §4.1.6", "2026-07-01", "2026-07-01",
        "supported", "", "保留",
        "SAF 与 RSF 于 2023-04-15 爆发全面武装冲突，延续至今（2026 年）。",
        "verified", "多来源一致。")
    add(SUD, "cl-sdn-control-june-2026",
        "截至 2026 年 6 月：RSF 控制苏丹西部（达尔富尔）与中南部大部；SAF 控制北部、东部与中部（含喀土穆、苏丹港）；青尼罗河州控制权存在争议。",
        ["actor-saf", "actor-rsf"], ["rel-saf-rsf-war"],
        ["govuk-sudan-cpin-2026-07"], "CPIN §4.1.9 (as of June 2026)", "2026-07-01", "2026-06-30",
        "supported", "stale_source", "更新控制格局",
        "截至 2026-06：RSF 控制西部与中南部大部（达尔富尔、西科尔多凡大部、利比亚/埃及边境地带）；SAF 控制北部、东部与中部（喀土穆、苏丹港）；青尼罗河州争议。",
        "verified", "I2-B 审计以 2026-07 UK CPIN 更新（原数据为 2024 年口径）。")
    add(SUD, "cl-sdn-el-fasher-2025",
        "RSF 于 2025 年 10 月攻占法希尔（北达尔富尔首府），此前围城约 18 个月；联合国称接管三日内至少 6,000 人死亡。",
        ["actor-rsf"], [],
        ["aj-sudan-2026-04", "govuk-sudan-cpin-2026-07"],
        "AJ Apr 2026 + CPIN §12.2.1", "2026-07-01", "2026-10-31",
        "supported", "", "新增关键事件",
        "RSF 2025-10 攻占法希尔；围城约 18 个月；UN 报告三日内至少 6,000 人死亡。",
        "verified", "I2-B 审计新增。",
        cids=["country-sudan"])
    add(SUD, "cl-sdn-burhan-saf",
        "阿卜杜勒·法塔赫·布尔汉领导苏丹武装部队，并任主权委员会主席；以苏丹港为基地的军队政府于 2025-05 任命卡米勒·伊德里斯为总理。",
        ["actor-saf", "person-abdel-fattah-al-burhan"], ["rel-saf-rsf-war"],
        ["govuk-sudan-cpin-2026-07", "aj-sudan-2026-04"], "CPIN §4.1.6 + AJ", "2026-07-01", "2026-07-01",
        "supported", "stale_source", "更新现任状态",
        "布尔汉仍领导 SAF/主权委员会；2025-05 军队政府任命卡米勒·伊德里斯为总理。",
        "verified", "I2-B 审计确认现任领导未变。")
    add(SUD, "cl-sdn-hemedti-rsf",
        "穆罕默德·哈姆丹·达加洛（赫梅蒂）指挥快速支援部队；2025-08 RSF 在尼亚拉组建并行政府，赫梅蒂任总统委员会主席。",
        ["actor-rsf", "person-mohamed-hamdan-dagalo"], ["rel-saf-rsf-war"],
        ["govuk-sudan-cpin-2026-07", "thenigerianvoice-2025-12"],
        "CPIN §4.1.10/§4.1.11", "2026-07-01", "2026-07-01",
        "supported", "stale_source", "更新现任状态",
        "赫梅蒂仍指挥 RSF；2025 年 RSF 在尼亚拉组建并行政府，赫梅蒂任总统委员会主席。",
        "verified", "I2-B 审计确认。")
    add(SUD, "cl-sdn-parallel-govts-2025",
        "2025 年苏丹形成苏丹港（SAF）与尼亚拉（RSF）两个并行政府，分别自称合法政权。",
        ["actor-saf", "actor-rsf"], [],
        ["govuk-sudan-cpin-2026-07", "xinhua-sudan-2025-12"],
        "CPIN §4.1.11 + Xinhua 2025 review", "2026-07-01", "2026-07-01",
        "supported", "", "新增",
        "SAF 政府驻苏丹港，RSF 政府驻尼亚拉；RSF 建立并行央行与货币。",
        "verified", "I2-B 审计新增。")
    add(SUD, "cl-sdn-splm-n-rsf-alliance",
        "苏丹人民解放运动—北方局（希卢派）与 RSF 结盟，控制努巴山区大部及南苏丹边境（含黑格里油田以东）部分地区。",
        ["actor-splm-n-al-hilu", "actor-rsf"], [],
        ["govuk-sudan-cpin-2026-07"],
        "CPIN §4.1.9 (SPLM-N allied to RSF, Nuba Mountains)", "2026-07-01", "2026-06-30",
        "supported", "stale_source", "更新结盟状态",
        "SPLM-N（希卢派）与 RSF 结盟，控制南科尔多凡努巴山区大部及南苏丹边境部分区域。",
        "verified", "I2-B 审计更新（原 I2-A 仅记为活跃）。")
    add(SUD, "cl-sdn-slm-aw-neutral",
        "苏丹解放运动/解放军（阿卜杜勒·瓦希德派，SLA-AW）不结盟于 SAF 或 RSF，控制中达尔富尔杰贝勒马拉山地带。",
        ["actor-slm-aw"], [],
        ["govuk-sudan-cpin-2026-07"],
        "CPIN §4.1.9 (SLA-AW unaligned, Jebel Marra)", "2026-07-01", "2026-06-30",
        "supported", "stale_source", "更新定位",
        "SLA-AW 保持不结盟，控制杰贝勒马拉山地带。",
        "verified", "I2-B 审计更新。")
    add(SUD, "cl-sdn-jem-saf-alliance",
        "正义与平等运动（JEM，吉布里勒·易卜拉欣领导）于 2023 年 11 月放弃中立、随达尔富尔联合部队支持 SAF；吉布里勒·易卜拉欣 2025-09-12 遭美国制裁。",
        ["actor-jem"], [],
        ["acled-sudan-2025", "govuk-sudan-cpin-2026-07"],
        "ACLED two-year report (Darfur Joint Forces) + CPIN", "2026-07-01", "2025-09-12",
        "supported", "stale_source", "更新立场",
        "JEM 自 2023-11 支持 SAF；其领导人吉布里勒·易卜拉欣兼任财政部长，2025-09-12 遭美国制裁。",
        "verified", "I2-B 审计确认（原 I2-A 未明确 JEM 当前立场）。")
    add(SUD, "cl-sdn-slm-mm-saf-alliance",
        "苏丹解放运动（明尼·米纳维派，SLM-MM）2023-11 支持 SAF；2025 年与军队政府围绕组阁出现紧张。",
        ["actor-slm-aw"], [],
        ["acled-sudan-2025", "nowinsa-sudan-2025"],
        "ACLED + 2025 Port Sudan cabinet friction reports", "2025-06-01", "2025-06-22",
        "supported", "stale_source", "更新立场",
        "SLM-MM 支持 SAF 但 2025 年与布尔汉政府出现政治摩擦；SLM/A-TC 与 GSLF 则于 2025-02 转向支持 RSF。",
        "verified", "I2-B 审计确认。")
    add(SUD, "cl-sdn-kordofan-front",
        "至 2025 年底主要战线转向科尔多凡；2026-03 SAF 攻占北科尔多凡 Bara，RSF 恢复对 Kadugli 与 Dilling 的围困。",
        ["actor-saf", "actor-rsf"], [],
        ["govuk-sudan-cpin-2026-07"],
        "CPIN §12.1.3/§12.2.3 (March 2026 events)", "2026-07-01", "2026-03-06",
        "supported", "", "新增",
        "主要战线移至科尔多凡；2026-03 SAF 攻占 Bara，RSF 恢复 Kadugli/Dilling 围困。",
        "verified", "I2-B 审计新增。")
    add(SUD, "cl-sdn-displacement",
        "苏丹冲突造成约 1,400 万人流离失所（约占人口四分之一）；其中约 440 万人跨境（主要赴乍得、南苏丹、埃及）。",
        [], [],
        ["aj-sudan-2026-04"],
        "UNHCR figures via AJ", "2026-04-14", "2026-04-14",
        "supported", "", "新增",
        "约 1,400 万人流离失所；约 440 万人跨境。",
        "verified", "I2-B 审计新增。")
    add(SUD, "cl-sdn-casualties",
        "WHO 估计冲突死亡约 4 万人；ACLED 记录 2024-01 至 2026-04 共 10,749 起政治暴力事件、42,346 名军民死亡。",
        [], [],
        ["aj-sudan-2026-04", "govuk-sudan-cpin-2026-07"],
        "WHO via AJ; ACLED via CPIN §13.1.1", "2026-07-01", "2026-04-30",
        "supported", "", "新增",
        "WHO 约 4 万死亡（实际数字可能更高）；ACLED 口径 42,346 军民死亡（2024-01~2026-04）。",
        "verified", "I2-B 审计新增，并列不同口径。")
    add(SUD, "cl-sdn-darfur-joint-forces",
        "达尔富尔联合部队（五支前叛军联盟）2023-04 成立时为中立平民保护力量；2023-11 其中四支（含 JEM、SLM-MM）宣布支持 SAF；SLM/A-TC 与 GSLF 于 2025-02 转投 RSF。",
        ["actor-jem"], [],
        ["acled-sudan-2025"],
        "ACLED two-year report (Darfur Joint Forces timeline)", "2025-04-01", "2025-02-28",
        "supported", "", "新增",
        "达尔富尔联合部队立场演变：2023-11 四支支持 SAF；2024-03 SLM/A-TC 与 GSLF 脱离；2025-02 转投 RSF。",
        "verified", "I2-B 审计新增。")

    # ---------------- Mozambique (12) ----------------
    add(MOZ, "cl-moz-is-affiliation-2017",
        "伊斯兰国莫桑比克省（ISM）自 2017 年 10 月袭击莫辛布瓦-达普拉亚起作为伊斯兰国关联叛乱出现，并向伊斯兰国网络宣誓效忠。",
        ["actor-is-mozambique", "actor-islamic-state"], ["rel-is-moz-islamic-state"],
        ["warwatch-moz-2025", "crisis-group-mozambique"],
        "RULAC timeline (Oct 2017 Mocímboa da Praia attack)", "2025-06-30", "2025-06-30",
        "supported", "", "保留并强化",
        "ISM 2017 年起在德尔加杜角作为伊斯兰国关联武装活动，公开资料将其描述为向伊斯兰国网络效忠的省分支。",
        "verified", "I2-B 审计确认；关系类型修正为 pledged_allegiance_to。")
    add(MOZ, "cl-moz-naming",
        "当地所称 Al-Shabaab、Ansar al-Sunnah（ASWJ）指同一德尔加杜角叛乱；官方名称为'伊斯兰国莫桑比克省'（ISM），不得与索马里 al-Shabaab 或笼统的 IS-CAP 混同。",
        ["actor-is-mozambique"], [],
        ["warwatch-moz-2025", "reliefweb-moz-2026-01"],
        "RULAC naming note + Cabo Ligado monitors", "2026-01-14", "2026-01-14",
        "supported", "", "保留命名区分",
        "各名称反映同一叛乱的不同来源/阶段表述；平台以 IS-Mozambique 为主名并保留别名。",
        "verified", "I2-B 审计确认（原 I2-A 已含该讨论）。")
    add(MOZ, "cl-moz-activity-districts",
        "ISM 2025-2026 年活动集中于德尔加杜角 Macomia、Muidumbe、Mocímboa da Praia、Meluco 等区；2025 年初起控制 Meluco 部分地区。",
        ["actor-is-mozambique"], ["rel-is-moz-mozambique-operates"],
        ["reliefweb-moz-2026-01", "warwatch-moz-2025"],
        "Cabo Ligado Jan 2026 + RULAC (Meluco since early 2025)", "2026-01-14", "2026-03-25",
        "supported", "", "更新活动范围",
        "ISM 活跃于 Macomia、Muidumbe、Mocímboa da Praia、Meluco；2025 年初起控制 Meluco 部分地区。",
        "verified", "I2-B 审计更新。")
    add(MOZ, "cl-moz-leadership-2023",
        "ISM 长期领导人 Bonomade Machude Omar 据报 2023-08 被击毙，由 Abu Zainabo（Ulanga）继任；领导层更迭后组织仍保持作战能力。",
        ["actor-is-mozambique"], [],
        ["warwatch-moz-2025"],
        "RULAC (leadership change Aug 2023)", "2025-06-30", "2025-06-30",
        "partially_supported", "single_source", "标注单一来源",
        "据 Geneva Academy RULAC：Omar 2023-08 被击毙、Abu Zainabo 继任；该认定主要依赖单一权威转引来源，部分细节存在来源差异。",
        "partially_verified", "I2-B 审计：不编造，如实标注来源局限。")
    add(MOZ, "cl-moz-rdf-2021",
        "卢旺达国防军（RDF）自 2021 年起部署于德尔加杜角协助恢复安全。",
        ["actor-rdf", "actor-fadm"], ["rel-rdf-mozambique-fadm-cooperate"],
        ["crisis-group-mozambique", "warwatch-moz-2025"],
        "RULAC (RDF deployed 2021)", "2025-06-30", "2025-06-30",
        "supported", "", "保留",
        "RDF 2021 年部署德尔加杜角，承担主要外部作战角色。",
        "verified", "多来源一致。")
    add(MOZ, "cl-moz-rdf-2024-expansion",
        "卢旺达 2024 年增派约 2,000 名部队，扩大在德尔加杜角的部署规模。",
        ["actor-rdf"], [],
        ["warwatch-moz-2025"],
        "RULAC (RDF expanded by 2,000 in 2024)", "2025-06-30", "2025-06-30",
        "supported", "", "新增",
        "RDF 2024 年增兵约 2,000 人，维持主要作战角色。",
        "verified", "I2-B 审计新增。")
    add(MOZ, "cl-moz-rdf-2026-status",
        "2026-03 卢旺达外长提出撤军前景；RDF 仍在 Macomia 海岸（Pangane 前哨）与 Meluco（N380 新前哨）保持存在。",
        ["actor-rdf"], [],
        ["reliefweb-moz-2026-03"],
        "Cabo Ligado 25 Mar 2026 (RDF new outpost; withdrawal talk)", "2026-03-25", "2026-03-25",
        "supported", "stale_source", "更新当前状态",
        "RDF 仍部署且新增前哨；撤军前景于 2026-03 提出但尚未实施。",
        "verified", "I2-B 审计更新当前状态。")
    add(MOZ, "cl-moz-samim-end",
        "南共体驻莫桑比克特派团（SAMIM）于 2024 年 7 月正式结束任务；南非部队延至 2024-12 底撤出，坦桑尼亚继续双边部署。",
        ["actor-samim", "actor-fadm"], ["rel-samim-fadm-cooperate"],
        ["warwatch-moz-2025"],
        "RULAC (SAMIM officially ended July 2024)", "2025-06-30", "2024-12-31",
        "supported", "stale_source", "修正结束时间",
        "SAMIM 于 2024-07 正式结束（原 I2-A 表述'2024 年前后'不精确）；南非延至 2024-12 底，坦桑尼亚继续双边部署。",
        "verified", "I2-B 审计修正原表述。")
    add(MOZ, "cl-moz-fadm-role",
        "FADM 持续与 ISM 作战；2024 年以来 FADM 海军对德尔加杜角近岸民船攻击显著增加（2026-03-15 打死至少 13 人）。",
        ["actor-fadm"], ["rel-fadm-is-moz-hostile"],
        ["reliefweb-moz-2026-03"],
        "Cabo Ligado 25 Mar 2026 (FADM navy civilian boat attacks)", "2026-03-25", "2026-03-25",
        "supported", "", "新增",
        "FADM 与 ISM 持续交战；海军对民船开火呈上升趋势，造成平民伤亡。",
        "verified", "I2-B 审计新增。")
    add(MOZ, "cl-moz-lng-2025",
        "TotalEnergies 牵头的帕尔马液化天然气项目于 2025 年 10 月解除不可抗力。",
        [], [],
        ["reliefweb-moz-2026-01"],
        "Cabo Ligado Jan 2026 (force majeure lifted Oct 2025)", "2026-01-14", "2025-10-31",
        "supported", "", "新增",
        "TotalEnergies LNG 项目 2025-10 解除不可抗力，恢复重启计划。",
        "verified", "I2-B 审计新增。")
    add(MOZ, "cl-moz-idp-2025",
        "北部莫桑比克境内流离失所者逾 94.5 万，其中德尔加杜角超 82 万（2025 年口径）。",
        [], [],
        ["asa-cabo-delgado-2025"],
        "ASA Cabo Delgado Crisis (945,000+ IDPs)", "2025-06-01", "2025-06-01",
        "supported", "", "新增",
        "德尔加杜角与北部省份流离失所人口持续高位。",
        "verified", "I2-B 审计新增。")
    add(MOZ, "cl-moz-casualties",
        "截至 2026-03，德尔加杜角自 2017-10 累计政治暴力死亡 6,515 人；ISM 相关事件 2,172 起。",
        ["actor-is-mozambique"], [],
        ["reliefweb-moz-2026-03"],
        "Cabo Ligado cumulative data (6,515 deaths; 2,172 ISM events)", "2026-03-25", "2026-03-25",
        "supported", "", "新增",
        "2017-10 以来累计死亡 6,515 人，ISM 事件 2,172 起（截至 2026-03）。",
        "verified", "I2-B 审计新增。")
    add(MOZ, "cl-moz-tanzania-border",
        "ISM 与坦桑尼亚存在跨境关联（边境走私与人员流动风险），坦桑尼亚同时在莫桑比克北部边境维持双边部署。",
        ["actor-is-mozambique", "country-tanzania"], ["rel-is-moz-tanzania-link"],
        ["warwatch-moz-2025"],
        "RULAC (Tanzania bilateral deployment)", "2025-06-30", "2025-06-30",
        "supported", "", "保留并强化",
        "坦桑尼亚维持边境双边部署；ISM 跨境活动风险受监控。",
        "verified", "I2-B 审计确认。")

    return records


def main():
    # 1. relation types registry
    if not (DATA / "relation_types.json").exists():
        save("relation_types.json", {
            "schema_version": "asip-relation-ontology-v1",
            "relation_type_count": len(RELATION_TYPES),
            "note": "I2-B: pledged_allegiance_to 为独立类型，数据层不得映射为 affiliated_with。",
            "relation_types": RELATION_TYPES,
        })
        print("relation_types.json written:", len(RELATION_TYPES))

    # 2. append audit sources
    sources = load("sources.json")
    existing = {s["source_id"] for s in sources["sources"]}
    added = 0
    for s in NEW_SOURCES:
        if s["source_id"] not in existing:
            sources["sources"].append(s)
            added += 1
    save("sources.json", sources)
    print("sources added:", added, "| total:", len(sources["sources"]))

    # 3. audit records
    records = build_audit_records()
    save("audit_records.json", {
        "schema_version": "asip-audit-records-v1",
        "audit_date": AUDIT_DATE,
        "audit_scope": "三组重点区域抽查：乍得湖盆地 / 苏丹 / 莫桑比克（每组>=12条）",
        "count": len(records),
        "note": "每条记录含 support_result / issue_type / correction_action / final_claim_text / 来源与核验状态。",
        "records": records,
    })
    from collections import Counter
    print("audit records:", len(records),
          "| by region:", dict(Counter(r["region_id"] for r in records)),
          "| by support:", dict(Counter(r["support_result"] for r in records)))

    # 4. data corrections supported by the audit
    evidence = load("evidence_records.json")
    for ev in evidence["evidence"]:
        if ev["claim_id"] == "cl-samim-end":
            ev["claim_text_zh"] = ("南共体驻莫桑比克特派团（SAMIM）于 2024 年 7 月正式结束任务；"
                                   "南非部队延至 2024 年 12 月底撤出，坦桑尼亚继续双边部署。")
            ev["verification_status"] = "verified"
            ev["evidence_origin"] = "manual_source_mapping"
            ev["verification_method"] = "I2-B 审计核验（Geneva Academy RULAC 2025）"
            ev["source_locator"] = "RULAC (SAMIM officially ended July 2024)"
            ev["source_published_at"] = "2025-06-30"
            ev["claim_valid_as_of"] = "2024-12-31"
            ev["current_status_verified_at"] = AUDIT_DATE
        if ev["claim_id"] in ("cl-is-moz-cabo-delgado", "cl-rdf-mozambique-2021"):
            ev["verification_status"] = "verified"
            ev["evidence_origin"] = "manual_source_mapping"
            ev["verification_method"] = "I2-B 审计核验（2025-2026 公开来源）"
            ev["current_status_verified_at"] = AUDIT_DATE
    save("evidence_records.json", evidence)
    print("evidence corrections applied")

    # country current-status notes
    countries = load("countries.json")
    for c in countries["countries"]:
        if c["country_id"] == "country-sudan":
            c["trends"] = ("截至 2026-06：RSF 控制苏丹西部与中南部大部（含达尔富尔），SAF 控制北部、东部与中部"
                           "（含喀土穆、苏丹港），青尼罗河州存在争议；主要战线移至科尔多凡。"
                           "I2-B 审计核验（2026-07 UK CPIN）。")
            c["current_status_verified_at"] = AUDIT_DATE
            c["freshness_status"] = "current"
        if c["country_id"] == "country-chad":
            c["trends"] = ("2025 年相关死亡 242 人（较上年翻倍以上）；MNJTF 存在尼日尔退出与乍得可能缩减参与的"
                           "结构压力。I2-B 审计核验（AU PSC 2025-11/2025-12）。")
            c["current_status_verified_at"] = AUDIT_DATE
            c["freshness_status"] = "current"
        if c["country_id"] == "country-mozambique":
            c["trends"] = ("ISM 2025-2026 年活跃于德尔加杜角 Macomia/Muidumbe/Mocímboa da Praia/Meluco；"
                           "SAMIM 2024-07 正式结束，RDF 仍驻防且 2026-03 提出撤军前景；TotalEnergies LNG "
                           "2025-10 解除不可抗力。I2-B 审计核验（Cabo Ligado 2026）。")
            c["current_status_verified_at"] = AUDIT_DATE
            c["freshness_status"] = "current"
    save("countries.json", countries)
    print("country current-status corrections applied")

    # relationship profiles: note SAMIM correction if present
    profs = load("relation_profiles.json")
    if "rel-samim-fadm-cooperate" in profs.get("profiles", {}):
        p = profs["profiles"]["rel-samim-fadm-cooperate"]
        p["current_status"] = "ended (2024-07); South Africa withdrew by 2024-12; Tanzania continues bilaterally"
        p["note_i2b"] = "I2-B 审计修正：SAMIM 2024-07 正式结束，'2024年前后'表述已修正。"
    save("relation_profiles.json", profs)
    print("relation profile SAMIM correction applied")


if __name__ == "__main__":
    main()
