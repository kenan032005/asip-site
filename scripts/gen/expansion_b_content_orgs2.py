# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-B — organization content module (part 2: DRC/Uganda/Sudan-external).

Source of truth: ASIP-PPT-ENTITY-EXPANSION-B-Authoritative-Content-Pack.md.
No independent research; every claim traces to the pack's locked facts; gaps are
stated explicitly. Mechanical floor: >=14 meaningful sections, >=1800 Chinese chars.
"""

TODAY = "2026-08-10"
IMPORTER = "expansion-b"

# source ids (see expansion_b_content_sources.py + reused registry ids)
S_UPDF_REVIEW = "expb-updf-shujaa-review"
S_UPDF_STRIKE = "expb-updf-shujaa-strike"
S_MONUSCO_FARDC = "expb-monusco-fardc-ituri"
S_UN_FS = "expb-un-monusco-factsheet"
S_UNSC2808 = "expb-unsc-2808-2025"
S_SG_ADF = "expb-un-sg-adf-2025-11-22"
S_TREAS_BBMB = "expa-treasury-sudan-islamist-2025-09-12"

IMPORTANCE_L1 = "该实体处于平台核心观察范围，对理解所在地区安全格局具有决定性作用（L1）。"
IMPORTANCE_L2 = "该实体对理解所在地区安全格局具有重要作用（L2）。"


def entity(**kw):
    base = {
        "entity_id": None,
        "entity_type": "organization",
        "primary_type": "terrorist_group",
        "secondary_types": [],
        "slug": None,
        "name_zh": None,
        "name_en": None,
        "acronym": "",
        "native_name": "",
        "aliases": [],
        "historical_names": [],
        "importance_level": "L1",
        "short_description": "",
        "full_description": "",
        "current_status": "",
        "primary_category": "",
        "tags": [],
        "profile_level": "L1",
        "region_ids": [],
        "country_ids": [],
        "confidence": "high",
        "temporal_sensitive": True,
        "disputed": False,
        "source_refs": [],
        "last_verified_at": TODAY,
        "importance_review_status": "provisional",
        "importance_score": None,
        "importance_reasons": [],
        "importance_reviewed_at": TODAY,
        "evidence_ids": [],
        "record_created_at": TODAY,
        "record_updated_at": TODAY,
        "record_reviewed_at": TODAY,
        "claim_valid_as_of": TODAY,
        "freshness_status": "current",
        "verification_status": "pending_review",
        "current_status_verified_at": TODAY,
        "freshness_reviewed_by": IMPORTER,
    }
    base.update(kw)
    return base


def profile(sections, importance="L1", depth="encyclopedia_full"):
    return {
        "profile_level": depth,
        "completeness": "Expansion B 内容包导入档案 · 百科式",
        "importance_level": importance,
        "importance_statement": IMPORTANCE_L1 if importance == "L1" else IMPORTANCE_L2,
        "profile_depth": depth,
        "content_maturity": "E3_FULL_ENCYCLOPEDIA",
        "imported_by": IMPORTER,
        "sections": sections,
    }


# =====================================================================
# 4. FARDC — Armed Forces of the Democratic Republic of the Congo
# =====================================================================
ENT_FARDC = entity(
    entity_id="actor-fardc",
    slug="fardc",
    name_zh="刚果民主共和国武装部队",
    name_en="Armed Forces of the Democratic Republic of the Congo",
    acronym="FARDC",
    primary_type="state_security_force",
    aliases=["Forces Armées de la République Démocratique du Congo", "FARDC"],
    importance_level="L1",
    short_description="刚果民主共和国的国家武装力量，是刚果（金）东部反武装团体行动的核心国家行为体，与乌干达 UPDF 联合开展 Operation Shujaa 打击 ADF，并与 MONUSCO 协调平民保护行动。",
    full_description="刚果民主共和国武装部队（FARDC）是刚果（金）的国家武装力量，也是刚果（金）东部反武装团体行动中的中央国家行为体。FARDC 与乌干达 UPDF 在 Operation Shujaa 框架下联合打击 ADF（2021 年 11 月发起），并与 MONUSCO 协调伊图里等地的平民保护与安全行动。",
    current_status="active",
    tags=["刚果民主共和国", "国家武装力量", "ADF", "Operation Shujaa"],
    region_ids=["region-nile-basin-east-africa"],
    country_ids=[],
    source_refs=[S_UPDF_REVIEW, S_UPDF_STRIKE, S_MONUSCO_FARDC],
)

PROF_FARDC = profile({
    "lead": "刚果民主共和国武装部队（FARDC）是刚果（金）的国家武装力量，也是该国东部反武装团体行动中的核心国家行为体。它与乌干达 UPDF 联合开展 Operation Shujaa 打击 ADF/ISIS-CA，并与 MONUSCO 协调平民保护行动；其能力与约束直接影响东部武装冲突的走向。",
    "name_and_translation": "本平台采用中文译名「刚果民主共和国武装部队」，英文规范名 Armed Forces of the Democratic Republic of the Congo，缩写 FARDC（法语 Forces Armées de la République Démocratique du Congo）。",
    "formation_background": "FARDC 作为刚果（金）国家武装力量的历史形成与整合过程复杂，本平台仅在既有来源支撑范围内简述：它是对刚果（金）东部多种武装团体进行国家管控的核心工具，其东部行动集中于北基伍与伊图里等武装团体活跃省份。",
    "history": "FARDC 在刚果（金）东部长期面对多重武装团体（含 ADF 及各类武装网络）与地区冲突。其与 UPDF 的联合反 ADF 行动（Operation Shujaa）于 2021 年 11 月发起；2026 年 2 月，UPDF/FARDC 指挥官在贝尼评估行动并重申联合打击 ADF。",
    "structure": "公开来源未提供 FARDC 完整的部队编制细节；本平台不编制超出来源支撑的作战序列。可确认的是其东部部署以反武装团体为核心任务，并承担与邻国部队联合行动与多边协调职能。",
    "leadership": "作为国家武装力量，其指挥体系由刚果（金）政府与军事高层领导；与 UPDF 的联合行动设有双方指挥官协调机制（2026 年 2 月贝尼评估即由双方指挥官共同进行）。",
    "force_capacity": "公开来源未提供 FARDC 经核实的整体兵力数字。其东部行动能力受到后勤、纪律与多方冲突牵制的约束；与 UPDF 的联合行动与 MONUSCO 的协调是其实施关键任务的外部支撑。",
    "geography": "主要行动区为刚果（金）东部，重点是 ADF 活跃的北基伍省与伊图里省；Operation Shujaa 的联合行动沿贝尼等方向展开。",
    "tactics": "针对 ADF 的行动以联合地面清剿、营地突袭与武器/爆炸物缴获为主。2026 年 2 月 27 日，联合部队袭击伊波卢河以西一处 ADF 营地并缴获武器与炸弹制作材料（UPDF 官方陈述）。",
    "finance": "军费与装备数据缺乏权威公开统计；其后勤保障部分依赖国家财政与国际支持，具体比例未在来源中说明。",
    "legal_status": "作为刚果（金）国家武装力量，其法律地位由刚果（金）宪法与法律界定；其东部行动与多国联合行动（含与乌干达的双边安排）在公开材料中有官方表述。",
    "adversaries": "首要武装对手为 ADF/ISIS-CA；同时面对刚果（金）东部其他武装团体的活动。本平台不展开与 Expansion B 无关的东部冲突全貌，仅记录与 ADF 及安全部队职责直接相关的部分。",
    "current_situation": "2026 年，FARDC 与 UPDF 在 Operation Shujaa 框架下继续联合行动，2 月在贝尼评估行动、2 月 27 日袭击 ADF 营地；同时与 MONUSCO 协调伊图里等地平民保护与安全行动。",
    "regional_impact": "FARDC 在东部反武装团体行动中的角色影响大湖区安全格局：其与 UPDF 的联合行动决定 ADF 的生存空间，与 MONUSCO 的协调决定平民保护的实际覆盖。",
    "risk_assessment": "对在刚果（金）东部活动的人员与项目而言，FARDC 的行动强度、纪律状况与多方冲突牵制构成安全环境变量；ADF 的残存能力与报复风险需持续跟踪。",
    "events": {"list": [
        "2021-11：国家武装力量与 UPDF 在 Operation Shujaa 框架下启动联合反 ADF 攻势（UPDF 官方口径）。",
        "2026-02：UPDF/FARDC 指挥官在贝尼评估行动并重申联合打击 ADF。",
        "2026-02-27：联合部队袭击伊波卢河以西 ADF 营地，缴获武器与炸弹制作材料。",
        "持续：与 MONUSCO 协调伊图里等地的联合巡逻与联合/协调应对。",
    ]},
    "uncertainties": {"list": [
        "FARDC 整体兵力与装备水平缺乏经核实的公开统计。",
        "与 UPDF 联合行动中的战果数字属 UPDF 官方陈述，未经独立核实。",
        "FARDC 在东部多重冲突间的兵力分配与约束缺乏系统性公开数据。",
    ]},
    "gaps": "部队编制、军费、伤亡与纪律问题的系统数据缺失；完整的历史整合叙述超出本内容包来源范围。",
    "asip_analysis": "ASIP 判断：FARDC 应被理解为「受多重约束的国家行为体」：其反 ADF 效能高度依赖与 UPDF 的联合行动框架和与 MONUSCO 的协调，而非单纯的自身能力。评估东部安全时，需同时跟踪三个变量：联合行动的持续性与强度、FARDC 的多线牵制程度、以及平民保护协调的实际覆盖面。",
    "watch_indicators": [
        "Operation Shujaa 的联合行动公告与战果报道（须保留 UPDF 归属）。",
        "MONUSCO 与 FARDC 联合巡逻与平民保护行动的新报道。",
        "东部安全形势中 ADF 报复性袭击的动向。",
    ],
    "core_assessment": "FARDC 是刚果（金）东部反武装团体行动的核心国家载体，其效能与约束直接塑造 ADF 的生存空间与平民保护覆盖面。",
    "sources": [
        "UPDF：《UPDF-FARDC review joint operations against ADF in eastern DRC》（https://www.updf.go.ug/operation-shujaa/updf-fardc-review-joint-operations-against-adf-in-eastern-drc/）",
        "UPDF：《Joint UPDF-FARDC forces strike ADF camp》（https://www.updf.go.ug/operation-shujaa/joint-updf-fardc-forces-strike-adf-camp-recover-weapons-and-explosives-in-eastern-drc/）",
        "MONUSCO：《Ituri: MONUSCO and FARDC combine military and civilian efforts》（https://peacekeeping.un.org/en/news/ituri-monusco-and-fardc-combine-military-and-civilian-efforts-against-armed）",
    ],
}, importance="L1")


# =====================================================================
# 5. UPDF — Uganda Peoples' Defence Forces
# =====================================================================
ENT_UPDF = entity(
    entity_id="actor-updf",
    slug="updf",
    name_zh="乌干达人民国防军",
    name_en="Uganda Peoples' Defence Forces",
    acronym="UPDF",
    primary_type="state_security_force",
    aliases=["Uganda People's Defence Force", "UPDF"],
    importance_level="L1",
    short_description="乌干达的宪法性国家国防力量，其授权涵盖主权与领土完整、支持民政当局、区域稳定与国际和平行动；2021 年 11 月起与 FARDC 联合开展 Operation Shujaa 打击 ADF。",
    full_description="乌干达人民国防军（UPDF）是乌干达的宪法性国家国防力量，授权包括维护主权与领土完整、支持民政当局、区域稳定与国际和平行动。UPDF 在东部刚果（金）与 FARDC 联合开展 Operation Shujaa（2021 年 11 月发起）打击 ADF；2026 年官方报道确认联合行动与指挥协调持续进行。",
    current_status="active",
    tags=["乌干达", "国家武装力量", "ADF", "Operation Shujaa"],
    region_ids=["region-nile-basin-east-africa"],
    country_ids=[],
    source_refs=[S_UPDF_REVIEW, S_UPDF_STRIKE],
)

PROF_UPDF = profile({
    "lead": "乌干达人民国防军（UPDF）是乌干达的宪法性国家国防力量，授权涵盖主权与领土完整、支持民政当局、区域稳定与国际和平行动。其与 FARDC 联合开展的 Operation Shujaa（2021 年 11 月发起）是当前打击 ADF/ISIS-CA 的核心机制，也是理解其区域角色的关键。",
    "name_and_translation": "本平台采用中文译名「乌干达人民国防军」，英文规范名 Uganda Peoples' Defence Forces，缩写 UPDF。",
    "formation_background": "UPDF 是乌干达宪法规定的国家国防力量，官方对其使命的表述包括：维护国家主权与领土完整、支持民政当局、促进区域稳定以及参与国际和平行动。",
    "history": "UPDF 的历史沿革与本轮内容包无直接关联的部分不展开；其区域行动传统使其成为东非主要出兵国之一，官方描述其在多个非洲国家有部署。对 ADF 的打击是其当前最突出的对外安全行动。",
    "structure": "官方领导页确认总统约韦里·穆塞韦尼（Yoweri Museveni）为总司令、穆霍齐·凯内鲁加巴（Gen Muhoozi Kainerugaba）为国防军总参谋长（展示前须核对仓库当前日期）。本平台不展开详细编制。",
    "leadership": "最高领导为国家元首（总司令）与国防军总参谋长；对 ADF 的联合行动由 UPDF 与 FARDC 指挥官协调，2026 年 2 月在贝尼的评估即由双方指挥官共同进行。",
    "force_capacity": "公开来源未提供 UPDF 经核实的整体兵力数字；其跨境作战能力体现在 Operation Shujaa 的持续运作与对 ADF 营地的打击行动中。",
    "geography": "对 ADF 的行动集中于刚果（金）东部（北基伍与伊图里方向），以跨境清剿为特征；其 ADF 威胁评估同时关注乌干达本土遭受跨境袭击的风险。",
    "tactics": "联合行动以地面清剿、营地突袭、武器缴获为主。2026 年 2 月 27 日，UPDF/FARDC 联合部队袭击伊波卢河以西 ADF 营地并缴获武器与炸弹制作材料（UPDF 官方陈述，数字保留归属）。",
    "finance": "军费数据缺乏本内容包来源支撑，不展开。",
    "legal_status": "作为乌干达宪法性国家武装力量，其法律地位由乌干达宪法界定；跨境进入刚果（金）行动的安排以两国官方表述为准。",
    "adversaries": "首要武装对手为 ADF/ISIS-CA；其评估同时涵盖乌干达境内及跨境安全威胁。",
    "current_situation": "2026 年官方 UPDF 报道确认与 FARDC 的联合行动与指挥协调持续进行；2 月贝尼评估、2 月 27 日营地突袭为近期可引用的节点。",
    "regional_impact": "UPDF 的跨境行动塑造大湖区反 ADF 格局：其与 FARDC 的联合行动决定 ADF 的生存空间，其区域部署传统也使其成为东非安全的关键支柱。",
    "risk_assessment": "对乌干达及周边而言，ADF 的跨境袭击能力是直接风险；UPDF 在刚果（金）东部的行动强度与战果直接影响该风险的压制程度。",
    "events": {"list": [
        "2021-11：UPDF 与刚果（金）伙伴方在 Operation Shujaa 框架下启动联合反 ADF 攻势（UPDF 官方口径）。",
        "2026-02：UPDF/FARDC 指挥官在贝尼评估联合行动。",
        "2026-02-27：联合部队袭击 ADF 营地并缴获武器与爆炸物（UPDF 官方陈述）。",
    ]},
    "uncertainties": {"list": [
        "UPDF 在刚果（金）东部的具体部署规模与持续投入缺乏权威公开统计。",
        "战果与伤亡数字来自军方官方陈述，未经独立核实。",
        "Operation Shujaa 的长期化与区域政治影响存在不确定性。",
    ]},
    "gaps": "完整编制、军费与历史编年超出本内容包范围；其索马里/AUSSOM 关联仅在来源支撑时提及，不作为主线展开。",
    "asip_analysis": "ASIP 判断：UPDF 的区域角色以「跨境反恐先行者」为特征——它是少数公开长期在邻国境内执行反武装团体行动的国家武装力量。Operation Shujaa 的可持续性取决于双边政治框架与资源投入；评估时应把联合行动的频率、战果报道与双边政治信号作为连续变量跟踪，并始终把战果数字保持为军方归属陈述。",
    "watch_indicators": [
        "UPDF 官方关于 Operation Shujaa 的新公告（战果数字保留归属）。",
        "乌干达境内 ADF 跨境袭击的动向。",
        "UPDF 与 FARDC 联合指挥机制的公开调整。",
    ],
    "core_assessment": "UPDF 是 Operation Shujaa 的核心推动者，其对 ADF 的跨境打击决定该组织的生存空间，是评估大湖区反 ADF 格局的关键变量。",
    "sources": [
        "UPDF（官方）：《Who we are / official site》（https://www.updf.go.ug/，https://www.updf.go.ug/who-we-are/）",
        "UPDF：《UPDF-FARDC review joint operations》（https://www.updf.go.ug/operation-shujaa/updf-fardc-review-joint-operations-against-adf-in-eastern-drc/）",
        "UPDF：《Joint UPDF-FARDC forces strike ADF camp》（https://www.updf.go.ug/operation-shujaa/joint-updf-fardc-forces-strike-adf-camp-recover-weapons-and-explosives-in-eastern-drc/）",
    ],
}, importance="L1")


# =====================================================================
# 6. MONUSCO — UN Organization Stabilization Mission in the DRC
# =====================================================================
ENT_MONUSCO = entity(
    entity_id="actor-monusco",
    slug="monusco",
    name_zh="联合国刚果民主共和国稳定特派团",
    name_en="United Nations Organization Stabilization Mission in the Democratic Republic of the Congo",
    acronym="MONUSCO",
    primary_type="un_peacekeeping_mission",
    aliases=["MONUSCO", "Mission de l'Organisation des Nations Unies pour la stabilisation en RDC"],
    historical_names=["MONUC"],
    importance_level="L1",
    short_description="依据联合国安理会第 1925 号决议于 2010 年 7 月 1 日接替 MONUC 的联合国维和特派团，核心授权为保护平民与支持刚果（金）稳定；第 2808 号决议（2025）将任务延长至 2026 年 12 月 20 日。",
    full_description="联合国刚果民主共和国稳定特派团（MONUSCO）于 2010 年 7 月 1 日依据安理会第 1925 号决议接替 MONUC，核心授权包括保护平民与支持刚果（金）稳定与和平巩固。安理会第 2808 号决议（2025）将其任务延长至 2026 年 12 月 20 日（含干预旅），授权上限 11,500 名军事人员、600 名军事观察员/参谋军官与 443 名警察。特派团已撤出南基伍，重心保持在北基伍与伊图里等东部地区。",
    current_status="active",
    tags=["联合国", "维和", "刚果民主共和国", "平民保护"],
    region_ids=["region-nile-basin-east-africa"],
    country_ids=[],
    source_refs=[S_UN_FS, S_UNSC2808, S_MONUSCO_FARDC, S_SG_ADF],
)

PROF_MONUSCO = profile({
    "lead": "联合国刚果民主共和国稳定特派团（MONUSCO）于 2010 年 7 月 1 日依据安理会第 1925 号决议接替 MONUC，核心授权为保护平民与支持刚果（金）稳定。其与 FARDC 协调平民保护行动、并面对 ADF 反复袭击平民的威胁，是理解大湖区安全的重要节点。",
    "name_and_translation": "本平台采用中文译名「联合国刚果民主共和国稳定特派团」，英文规范名 United Nations Organization Stabilization Mission in the Democratic Republic of the Congo，缩写 MONUSCO。其前身 MONUC 未单独建页，历史以文字记述。",
    "formation_background": "MONUSCO 于 2010 年 7 月 1 日依据联合国安理会第 1925 号决议成立，接替联合国刚果民主共和国特派团（MONUC）。其核心授权包括保护平民与支持刚果（金）的稳定与和平巩固。",
    "history": "特派团经历了多次授权调整与地理撤编：已撤出南基伍，任务重心保持在北基伍与伊图里等东部地区。2025 年安理会第 2808 号决议将其任务延长至 2026 年 12 月 20 日，并保留干预旅（Force Intervention Brigade）。",
    "structure": "特派团由安理会决议设定授权上限：第 2808 号决议授权 11,500 名军事人员、600 名军事观察员/参谋军官与 443 名警察。干预旅作为其组成部分保留。",
    "leadership": "特派团由联合国秘书长特别代表领导，军事部分由部队指挥官负责；其行动受安理会授权约束并接受秘书长报告机制监督。",
    "force_capacity": "授权上限（11,500 军事人员 + 600 观察员/参谋 + 443 警察）为当前可引用的规模基准；实际部署以联合国官方数据为准。",
    "geography": "任务区集中在刚果（金）东部，重点是北基伍与伊图里；已撤出南基伍。ADF 反复在特派团行动区袭击平民（如 2025 年 11 月卢贝罗地区袭击）。",
    "tactics": "行动以平民保护为核心，采取联合巡逻、军事与民政并重的手段：UN 报道描述 MONUSCO 与 FARDC 在伊图里的联合巡逻与针对 ADF 袭击的联合/协调应对；2025 年重大 ADF 袭击后强化了平民保护并支持刚果当局。",
    "finance": "特派团经费来自联合国会员国会费摊款；具体预算数字以联合国官方文件为准，本内容包未提供明细。",
    "legal_status": "授权基础为联合国安理会决议（1925 号设立、2808 号延长）；作为联合国维和特派团，其法律地位与行为规则由联合国维和框架界定。",
    "adversaries": "特派团不是武装冲突的一方，其任务对象是威胁平民的武装团体，包括 ADF/ISIS-CA。ADF 反复袭击特派团行动区的平民（2025 年 11 月卢贝罗袭击为近期案例，秘书长发言人对袭击作出表态）。",
    "current_situation": "截至第 2808 号决议框架，MONUSCO 任务持续至 2026 年 12 月 20 日；特派团与 FARDC 协调平民保护，并面对 ADF 袭击的持续挑战；撤编与过渡的讨论是背景性议题。",
    "regional_impact": "MONUSCO 的平民保护覆盖与 FARDC 协调机制决定刚果（金）东部武装冲突中平民安全的实际保障水平，也影响区域对维和机制效能的评估。",
    "risk_assessment": "对在刚果（金）东部活动的人员与项目而言，特派团的平民保护强度与 ADF 袭击风险构成核心安全变量；其撤编讨论可能影响东部安全覆盖。",
    "events": {"list": [
        "2010-07-01：依据 UNSC 1925 接替 MONUC 设立。",
        "2025：安理会第 2808 号决议延长任务至 2026-12-20，保留干预旅。",
        "2025-11-22：秘书长发言人就 ADF 袭击卢贝罗平民发表声明。",
        "持续：MONUSCO 与 FARDC 在伊图里等地的联合巡逻与平民保护行动。",
    ]},
    "uncertainties": {"list": [
        "实际部署兵力与授权上限的差距以联合国官方数据为准，本内容包未提供。",
        "撤编/过渡的时间表与条件在公开来源中存在讨论但未定论。",
        "干预旅的后续授权与任务范围调整需以安理会最新决议为准。",
    ]},
    "gaps": "具体部署数字、预算与撤编路线图超出本内容包来源范围；其与 ADF 的直接交火细节未系统公开。",
    "asip_analysis": "ASIP 判断：MONUSCO 与 ADF 的关系不应被写成普通「恐怖组织敌对双方」——特派团是维和力量，其与 ADF 的对抗发生在平民保护与反武装团体任务的框架内，而非武装冲突方的敌对关系。评估东部安全时，应把特派团视为「平民保护与协调机制」：其与 FARDC 的协调决定行动覆盖，其撤编前景决定未来安全真空风险。",
    "watch_indicators": [
        "安理会关于 MONUSCO 授权续期或调整的新决议。",
        "ADF 对特派团行动区平民的袭击动向。",
        "MONUSCO 与 FARDC 联合巡逻与平民保护行动的新报道。",
        "撤编/过渡路线图的官方表述。",
    ],
    "core_assessment": "MONUSCO 是刚果（金）东部平民保护与稳定机制的核心支柱，其授权状态、撤编前景与 FARDC 协调质量共同塑造东部安全环境。",
    "sources": [
        "United Nations Peacekeeping：《MONUSCO fact sheet》（https://peacekeeping.un.org/en/node/104027）",
        "UNSC：《Resolution 2808 (2025)》（https://digitallibrary.un.org/record/4096723/files/S_RES_2808_%282025%29-EN.pdf）",
        "MONUSCO：《Ituri: MONUSCO and FARDC combine military and civilian efforts》（https://peacekeeping.un.org/en/news/ituri-monusco-and-fardc-combine-military-and-civilian-efforts-against-armed）",
        "UN Secretary-General：《Statement on ADF attacks in Lubero territory》（https://www.un.org/sg/en/content/sg/statements/2025-11-22/statement-attributable-the-spokesperson-for-the-secretary-general-adf-attacks-against-civilians-lubero-territory）",
    ],
}, importance="L1")


# =====================================================================
# 7. IRGC — Islamic Revolutionary Guard Corps (external supporting actor, L2)
# =====================================================================
ENT_IRGC = entity(
    entity_id="actor-irgc",
    slug="irgc",
    name_zh="伊朗伊斯兰革命卫队",
    name_en="Islamic Revolutionary Guard Corps",
    acronym="IRGC",
    primary_type="state_security_force",
    secondary_types=["external_security_actor"],
    aliases=["Islamic Revolutionary Guard Corps", "Sepah", "IRGC"],
    importance_level="L2",
    short_description="伊朗的国家安全武装力量；在非洲情报图中作为外部安全行为体记录，本轮仅纳入与苏丹 BBMB 相关的美国财政部归属性证据（训练与武器支持）。",
    full_description="伊朗伊斯兰革命卫队（IRGC）是伊朗的国家安全武装力量。在非洲情报库中，本实体作为外部安全行为体记录，范围聚焦其与苏丹巴拉·本·马利克旅（BBMB）相关的证据：美国财政部 2025 年 9 月称 BBMB 使用了 IRGC 提供的训练与武器。该陈述属美国政府指控/评估，必须保留归属，不得推导为 IRGC 对 BBMB 的作战指挥。",
    current_status="active",
    tags=["伊朗", "外部安全行为体", "苏丹", "BBMB"],
    region_ids=["region-sudan-red-sea-horn"],
    country_ids=["country-sudan"],
    disputed=False,
    source_refs=[S_TREAS_BBMB],
)

PROF_IRGC = profile({
    "lead": "伊朗伊斯兰革命卫队（IRGC）是伊朗的国家安全武装力量。在非洲情报库中，本实体仅作为外部安全行为体记录，其非洲相关证据集中在美国财政部关于苏丹巴拉·本·马利克旅（BBMB）的归属性陈述上：美方称 BBMB 使用了 IRGC 提供的训练与武器。本档案明确不把该陈述推导为 IRGC 对 BBMB 的作战指挥。",
    "name_and_translation": "本平台采用中文译名「伊朗伊斯兰革命卫队」，英文规范名 Islamic Revolutionary Guard Corps，缩写 IRGC。",
    "formation_background": "IRGC 作为伊朗国家安全体系的一部分，其完整历史不在本内容包范围内；本档案聚焦其在非洲（尤其是苏丹）安全格局中的外部行为体角色与相关证据。",
    "history": "对非洲情报图而言，IRGC 的相关性主要来自美国财政部的指控：2025 年 9 月美方在制裁 BBMB 时称其使用了 IRGC 提供的训练与武器。此为美国政府指控/评估，属归属性陈述。",
    "structure": "IRGC 内部结构不在本档案展开；其作为国家武装力量的属性由伊朗国内法律与政治体系界定。在非洲情报库中，本实体被限定为「外部安全行为体」：它不与非洲武装团体建立常态组织隶属关系，其记录仅覆盖与苏丹 BBMB 相关的被指控支持证据。这一建模约束来自内容包的范围规则——这不是伊朗百科项目，档案深度与非洲相关性相匹配。",
    "leadership": "IRGC 领导层细节超出本内容包范围，不展开。需要强调的是，美方对 BBMB 使用 IRGC 训练与武器的陈述不包含对 IRGC 指挥层介入程度的描述，本平台不据此推断任何指挥链条。",
    "force_capacity": "IRGC 整体军力不在此评估；本档案仅记录其与 BBMB 相关的归属性支持证据。美方陈述称 BBMB 使用了 IRGC 提供的训练与武器，但未提供支持规模、频次或机制的量化细节，本平台不填充这些空白。",
    "geography": "在非洲语境下，其相关地理指向苏丹（BBMB 的活动地）；IRGC 自身以伊朗及中东为基地，本档案不扩展其全球部署。BBMB 的活动集中在苏丹战争前线（如喀土穆方向），因此该支持关系的实际作用范围与苏丹冲突地理重合。",
    "tactics": "与 BBMB 相关的战术层面信息仅来自美方陈述（训练与武器支持），不展开未经来源支撑的细节。美方没有描述 IRGC 参与 BBMB 具体作战行动的证据，本平台亦不记录此类推断。",
    "finance": "关于 IRGC 支持的外部资金渠道，公开来源仅有美方归属性表述，本平台不展开。美方陈述将训练与武器支持列为 BBMB 与外部关联的证据之一，但未提供资金流动的具体路径。",
    "legal_status": "IRGC 在多个司法辖区被列为制裁对象，具体法律状态以各辖区现行文件为准；本内容包未提供 IRGC 自身的制裁清单条目。美方对 BBMB 的制裁行动在陈述中提及 IRGC 支持，但该表述是制裁理由的一部分，不构成对 IRGC 法律地位的独立认定。",
    "adversaries": "在非洲语境下，其与 BBMB 的关系是「被指控的支持方」，而非冲突对手；不将其推广为伊朗控制苏丹伊斯兰主义民兵的概括性结论。BBMB 在苏丹战争中与苏丹武装部队并肩作战、对抗快速支援部队（欧盟归属性描述），IRGC 若确曾提供支持，其支持对象处于这一战时阵营结构之中，但本平台不据此推断 IRGC 对苏丹战局的影响程度。",
    "current_situation": "当前可引用的状态是：美国财政部 2025 年 9 月对 BBMB 的制裁陈述中包含 IRGC 训练与武器支持的指控；该陈述保持归属，无更新的权威证据加入。",
    "regional_impact": "若美方指控属实，IRGC 通过支持 BBMB 参与苏丹冲突的影响渠道有限但值得跟踪；本档案明确不把单一来源概括为伊朗对苏丹伊斯兰主义民兵的广泛控制。",
    "risk_assessment": "对苏丹及区域分析而言，IRGC 相关证据的价值在于标注外部行为体介入的可能性与美方政策反应，而非建立确定的指挥关系。",
    "events": {"list": [
        "2025-09-12：美国财政部制裁 BBMB 时称其使用 IRGC 提供的训练与武器（归属性陈述）。",
    ]},
    "uncertainties": {"list": [
        "IRGC 对 BBMB 支持的范围、机制与持续性缺乏公开可核实的细节。",
        "美方陈述与独立证据之间的交叉验证不足。",
        "不应把该单一指控推广为伊朗控制苏丹伊斯兰主义民兵的结论。",
    ]},
    "gaps": "IRGC 在非洲的部署、人员与资金网络细节超出本内容包来源范围；本档案仅记录包内明确提供的归属性证据。",
    "asip_analysis": "ASIP 判断：IRGC 在非洲情报库中的价值是「标注外部介入渠道」而非「建立指挥关系」。处理美方陈述时应保持三层区分：指控本身（归属性）、指控背后的政策反应（美方行动）、以及独立可验证的事实（当前缺乏）。该实体的存在服务于 BBMB↔IRGC 关系档案的完整性，其档案深度与非洲相关性相匹配，不扩展为伊朗百科。",
    "watch_indicators": [
        "美国或其他司法辖区对 IRGC 与苏丹武装关系的新认定。",
        "出现独立于美方陈述的 IRGC-BBMB 关系证据。",
        "苏丹冲突中外部支持格局的公开变化。",
    ],
    "core_assessment": "IRGC 作为外部支持行为体进入非洲情报图，其记录严格限定在美方归属性证据范围内，不推导指挥关系，不泛化。",
    "sources": [
        "U.S. Department of the Treasury：《Sudanese Islamist Actors / BBMB》（2025-09-12）（https://home.treasury.gov/news/press-releases/sb0246）",
    ],
}, importance="L2")

ORG_ENTITIES = [ENT_FARDC, ENT_UPDF, ENT_MONUSCO, ENT_IRGC]
ORG_PROFILES = {
    "actor-fardc": PROF_FARDC,
    "actor-updf": PROF_UPDF,
    "actor-monusco": PROF_MONUSCO,
    "actor-irgc": PROF_IRGC,
}
