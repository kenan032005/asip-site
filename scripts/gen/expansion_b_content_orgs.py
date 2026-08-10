# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-B — organization content module (part 1: Somalia network).

Source of truth: ASIP-PPT-ENTITY-EXPANSION-B-Authoritative-Content-Pack.md.
No independent research; every claim traces to the pack's locked facts; gaps are
stated explicitly. Mechanical floor: >=14 meaningful sections, >=1800 Chinese chars.
"""

TODAY = "2026-08-10"
IMPORTER = "expansion-b"

# source ids (see expansion_b_content_sources.py + reused registry ids)
S_UNSC2767 = "expb-unsc-2767-2024"
S_AU_AUSSOM = "expb-au-aussom-psc-2026-07"
S_AUSSOM_RECOVER = "expb-aussom-snaf-recover-cities"
S_AUSSOM_CAPTURE = "expb-aussom-snaf-capture"
S_UNSOS = "expb-unsos-interop-2026-05"
S_PANEL777 = "expb-un-panel-s2025-777"
S_UNS2026 = "d2-un-s2026-44"
S_NCTC_SHABAAB = "expa-nctc-al-shabaab-2026-04"
S_NCTC_ISS = "expa-nctc-isis-somalia-2025-02"

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
# 1. AUSSOM — African Union Support and Stabilisation Mission in Somalia
# =====================================================================
S_AUSSOM = "expb-aussom-psc-2026-07"

ENT_AUSSOM = entity(
    entity_id="actor-aussom",
    slug="aussom",
    name_zh="非洲联盟驻索马里支助与稳定特派团",
    name_en="African Union Support and Stabilisation Mission in Somalia",
    acronym="AUSSOM",
    primary_type="peace_support_mission",
    secondary_types=["international_mission", "security_transition_actor"],
    aliases=["AUSSOM", "African Union Mission in Somalia (successor of ATMIS)"],
    historical_names=["AMISOM", "ATMIS"],
    importance_level="L1",
    short_description="自 2025 年 1 月 1 日起接替 ATMIS 的非洲联盟驻索马里特派团，核心任务是支持索马里打击 Al-Shabaab 并推进安全责任向索马里安全部队的条件式移交。",
    full_description="非洲联盟驻索马里支助与稳定特派团（AUSSOM）依据联合国安理会第 2767 号决议（2024 年 12 月 27 日）获授权，于 2025 年 1 月 1 日接替非盟驻索马里过渡特派团（ATMIS）。其任务包括在索马里开展行动削弱 Al-Shabaab 及与伊斯兰国关联的分支，并通过与索马里国家武装部队（SNAF）的联合行动推进安全责任移交。2026 年 7 月，非盟主席确认特派团仍在运作，并强调可持续融资问题。",
    current_status="active",
    tags=["索马里", "非洲联盟", "安全过渡", "反恐"],
    region_ids=["region-sudan-red-sea-horn"],
    country_ids=[],
    source_refs=[S_UNSC2767, S_AU_AUSSOM, S_AUSSOM_RECOVER, S_AUSSOM_CAPTURE],
)

PROF_AUSSOM = profile({
    "lead": "非洲联盟驻索马里支助与稳定特派团（AUSSOM）是 2025 年 1 月 1 日起接替 ATMIS 的非盟驻索马里特派团，依据联合国安理会第 2767 号决议（2024 年 12 月 27 日）运作。它既是索马里打击 Al-Shabaab 的中央军事—安全节点，也是国际／非盟力量向索马里机构移交安全责任的制度载体。",
    "name_and_translation": "本平台采用中文译名「非洲联盟驻索马里支助与稳定特派团」，英文规范名 African Union Support and Stabilisation Mission in Somalia，缩写 AUSSOM。该特派团的前身链条为 AMISOM（非盟驻索马里特派团）→ ATMIS（非盟驻索马里过渡特派团）→ AUSSOM；前身未单独建页，相关历史以文字记述在本文档中。",
    "formation_background": "联合国安理会第 2767 号决议于 2024 年 12 月 27 日通过，授权非盟成员国自 2025 年 1 月 1 日起 12 个月内采取一切必要措施支持索马里，包括削弱 Al-Shabaab 及与伊斯兰国关联的分支。特派团由此取代 ATMIS，成为索马里安全过渡新阶段的载体。",
    "history": "AUSSOM 的机构谱系可上溯至 AMISOM（2007 年设立）与 ATMIS（2022 年设立、2024 年底结束）。安理会第 2767 号决议欢迎索马里在承担更大国家安全责任方面取得进展，并注意到自 2022 年以来索马里安全部队已接管约 7,000 名缩编 ATMIS 部队的责任。AUSSOM 的任务设计明确以支持向索马里部队逐步移交安全责任为目标。",
    "structure": "特派团由非盟成员国出兵，采取分阶段力量构成。第 1 阶段（2025 年 1 月 1 日至 6 月 30 日）授权最多 12,626 名军警人员，其中含 1,040 名警察。概念计划（CONOPS）描述的第 2 阶段为 2025 年 7 月 1 日至 2027 年 12 月 31 日，包括确保任务地点安全、支持进攻行动与后勤保障。决议文本规定第 2 阶段前六个月（2025 年 7 月 1 日至 12 月 31 日）授权上限为 11,826 名军警人员，其中含 680 名警察。",
    "leadership": "特派团的指挥与政治监督由非洲联盟和平与安全理事会（PSC）负责，非盟委员会主席定期向其通报任务实施情况。部队派遣国提供军警人员，具体部队编成随阶段调整。2026 年 7 月，非盟主席向 PSC 通报任务实施与地面最新进展。",
    "force_capacity": "第 1 阶段上限 12,626 人（含 1,040 警察），第 2 阶段前六个月上限 11,826 人（含 680 警察）。兵力规模直接决定其在地面行动与据点防护上的可用资源；融资可持续性是 2026 年公开讨论的核心约束。",
    "geography": "任务区覆盖索马里全境，重点为 Al-Shabaab 活跃的中南部各州（如谢贝利地区）；其行动与索马里国家武装部队（SNAF）的联合打击沿索马里中南部展开。",
    "tactics": "行动方式以与 SNAF 的联合地面进攻、据点收复、扫荡与逮捕行动为主。2026 年 3 月报道显示 SNAF 与 AUSSOM 在下谢贝利协同收复 Daarusalaam 与 Mubarak；2026 年 4 月报道显示 AUSSOM 乌干达部队与 SNAF 部队联合俘获一名 Al-Shabaab 指挥官。",
    "finance": "融资可持续性是 2026 年特派团面临的核心问题。2026 年 7 月，非盟主席强调需要可持续融资以维持特派团运作；这与 Al-Shabaab 的机会结构直接相关——融资缺口会压缩特派团行动强度。",
    "legal_status": "授权基础为联合国安理会第 2767 号决议（2024）；作为非盟和平支助行动，其存在与授权上限由安理会决议明确，部队派遣以非盟成员国自愿出兵为基础。",
    "adversaries": "主要打击对象为 Al-Shabaab，以及安理会决议中列明的与伊斯兰国关联的分支（如 ISIS-Somalia 及更广泛的伊斯兰国网络关联）。特派团通过支持索马里安全部队间接压缩这些武装组织的行动空间。",
    "current_situation": "截至 2026 年年中，AUSSOM 仍在运作。非盟 2026 年 7 月 27 日表述：特派团与索马里联邦政府及部队派遣国密切合作，保护平民、推进稳定、强化国家机构，并支持向索马里安全部队条件式移交安全责任。AUSSOM 与 SNAF 2026 年继续开展针对 Al-Shabaab 的联合行动。",
    "regional_impact": "AUSSOM 的存在与行动强度直接塑造索马里安全责任移交的节奏：其融资与兵力生成不确定性影响对 Al-Shabaab 的持续压力，进而影响索马里中南部稳定与跨境安全外溢。",
    "risk_assessment": "对在索马里及周边活动的人员与项目而言，特派团行动强度与融资缺口是评估安全环境的两个关键变量：行动减弱可能为 Al-Shabaab 留出重组与扩张空间。",
    "events": {"list": [
        "2024-12-27：联合国安理会通过第 2767 号决议，授权 AUSSOM。",
        "2025-01-01：AUSSOM 正式接替 ATMIS。",
        "2025-07-01：第 2 阶段开始，授权上限调整为 11,826 人（含 680 警察）。",
        "2026-03：特派团与 SNAF 联合收复下谢贝利 Daarusalaam 与 Mubarak。",
        "2026-04：AUSSOM 乌干达部队与 SNAF 联合俘获 Al-Shabaab 指挥官。",
        "2026-05：UNSOS 组织 AUSSOM、SNAF 与联合国警卫部队互操作训练。",
        "2026-07：非盟主席确认特派团运作并强调可持续融资。",
    ]},
    "uncertainties": {"list": [
        "融资可持续性的实际缺口与后续补充方案在公开来源中无一致量化。",
        "第 2 阶段（至 2027-12-31）的后续授权与兵力上限调整尚待安理会后续决议确认。",
        "安全责任移交的「条件式」判断标准与时间表在公开材料中未具体化。",
    ]},
    "gaps": "特派团实际地面部队编成、具体战区部署与损失数据缺乏权威公开统计；部队派遣国的实际出兵构成与第 1、2 阶段上限的差距未在公开来源中说明。",
    "asip_analysis": "ASIP 判断：AUSSOM 不应仅被当作维和背景行为体，而应视为 Al-Shabaab 冲突与安全责任移交中的中央军事—安全节点。其融资与兵力生成不确定性直接影响 Al-Shabaab 的机会结构：当国际压力减弱或出现空隙，Al-Shabaab 往往利用空隙重组。评估索马里安全形势时，需把特派团的阶段授权、兵力上限与融资状态作为连续变量跟踪，而非仅记录其存在。",
    "watch_indicators": [
        "安理会关于 AUSSOM 后续授权与兵力上限的新决议。",
        "非盟对特派团融资缺口的具体表述与捐助方回应。",
        "AUSSOM 与 SNAF 联合行动的频率、规模与战果报道。",
        "安全责任移交的里程碑事件（如新区域移交）公告。",
        "特派团人员构成或部队派遣国调整。",
    ],
    "core_assessment": "AUSSOM 是索马里安全过渡的核心制度节点，其阶段授权、兵力上限与融资状态构成评估 Al-Shabaab 机会结构的关键输入。",
    "sources": [
        "United Nations Security Council：《Resolution 2767 (2024)》（https://press.un.org/en/2024/sc15955.doc.htm）",
        "African Union：《AUC Chairperson briefing on AUSSOM implementation》（https://www.au.int/en/pressrelease/auc-chairperson-briefed-implementation-aussoms-mandate-recent-developments-ground）",
        "AUSSOM：《SNAF and AUSSOM recover two strategic cities》（https://au-ssom.org/snaf-and-aussom-recover-two-strategic-cities-in-coordinated-assault-against-al-shabaab/）",
        "AUSSOM：《Joint AUSSOM-SNAF operation captures senior Al-Shabaab commander》（https://au-ssom.org/joint-aussom-snaf-operation-captures-senior-al-shabaab-commander/）",
        "UNSOS：《UNSOS strengthens operational coordination among AUSSOM, SNAF and UNGU forces》（https://unsos.unmissions.org/en/news/unsos-strengthens-operational-coordination-among-aussom-snaf-and-ungu-forces-through）",
    ],
}, importance="L1")


# =====================================================================
# 2. Somali National Armed Forces (SNAF)
# =====================================================================
ENT_SNAF = entity(
    entity_id="actor-somali-national-armed-forces",
    slug="somali-national-armed-forces",
    name_zh="索马里国家武装部队",
    name_en="Somali National Armed Forces",
    acronym="SNAF",
    primary_type="state_security_force",
    aliases=["Somali National Army", "SNA", "Somali Armed Forces"],
    importance_level="L1",
    short_description="索马里联邦的国家武装力量，是对抗 Al-Shabaab 战役与索马里安全过渡中的核心国家军事行为体，2026 年持续与 AUSSOM 开展联合行动。",
    full_description="索马里国家武装部队（SNAF）是索马里联邦政府领导下的国家军事力量，是对抗 Al-Shabaab 的核心国家行为体。安理会第 2767 号决议注意到索马里安全部队自 2022 年以来已接管约 7,000 名缩编 ATMIS 部队的责任；AUSSOM 的任务设计以支持向索马里部队逐步移交安全责任为目标。2026 年，SNAF 持续与 AUSSOM 开展针对 Al-Shabaab 的联合行动。",
    current_status="active",
    tags=["索马里", "国家武装力量", "安全过渡"],
    region_ids=["region-sudan-red-sea-horn"],
    country_ids=[],
    source_refs=[S_UNSC2767, S_AUSSOM_RECOVER, S_AUSSOM_CAPTURE, S_UNSOS],
)

PROF_SNAF = profile({
    "lead": "索马里国家武装部队（SNAF）是索马里联邦的国家军事力量，也是对抗 Al-Shabaab 战役与安全过渡中的核心国家行为体。2026 年，SNAF 与 AUSSOM 持续开展联合行动，其部队构成与行动能力直接决定索马里能否承接国际安全力量的移交。",
    "name_and_translation": "本平台采用中文译名「索马里国家武装部队」，英文规范名 Somali National Armed Forces，缩写 SNAF。当来源明确指称陆军组成部分时，使用别名 Somali National Army（SNA）；本平台将 SNA 保留为别名，不单独建页。",
    "formation_background": "索马里国家武装部队的叙述必须谨慎：该国长期经历国家崩溃与重建，武装力量的历史沿革复杂且缺乏统一权威记载。本平台不重述未获来源支撑的完整编年，仅记录与当前战役和安全过渡直接相关的、有来源支撑的节点。",
    "history": "安理会第 2767 号决议欢迎索马里在承担更大国家安全责任方面取得进展，并注意到索马里安全部队自 2022 年以来已接管约 7,000 名缩编 ATMIS 部队的责任。这一移交进程是 SNAF 当前发展阶段的核心背景：其角色正从「接受国际支援」转向「承接安全责任」。",
    "structure": "部队由联邦政府领导，编成包含多个作战单元。2026 年 4 月 AUSSOM 报道提到 SNAF Gorgor 203 部队与 AUSSOM 乌干达部队联合行动；Gorgor 是公开报道中出现的单元称谓。本平台不编制超出来源支撑的详细作战序列（Order of Battle）。",
    "leadership": "索马里联邦政府通过国防部门对武装部队实施文官领导；具体指挥架构与高级军官任免以公开任命为准，本平台不记录未经来源确认的细节。",
    "force_capacity": "公开来源未提供 SNAF 经核实的整体兵力数字；其作战能力处于重建进程中，且与 AUSSOM 及国际训练支持直接相关。UNSOS 2026 年 5 月组织 AUSSOM、SNAF 与联合国警卫部队互操作训练，反映国际社会对其能力建设的持续投入。",
    "geography": "主要作战区域为 Al-Shabaab 活跃的索马里中南部，包括下谢贝利等州；联合行动沿中南部战线展开。",
    "tactics": "行动方式以与 AUSSOM 的联合地面进攻、据点收复与针对高价值目标的逮捕行动为主。2026 年 3 月：SNAF 与 AUSSOM 收复 Daarusalaam 与 Mubarak；2026 年 4 月：SNAF Gorgor 203 部队与 AUSSOM 乌干达部队俘获一名 Al-Shabaab 指挥官。",
    "finance": "部队的装备、薪酬与后勤高度依赖联邦财政与国际支持；公开来源未提供可靠的军费细目。国际训练与后勤支持（如 UNSOS 相关安排）是其能力维持的关键外部输入。",
    "legal_status": "作为索马里联邦的国家武装力量，其法律地位由索马里宪法与联邦制度界定；安理会决议将索马里安全部队承接安全责任视为安全过渡的目标对象。",
    "adversaries": "首要对手为 Al-Shabaab；在与 AUSSOM 联合行动的框架下，也针对与伊斯兰国关联的分支开展行动。",
    "current_situation": "2026 年，SNAF 持续与 AUSSOM 开展针对 Al-Shabaab 的联合行动，并在中南部取得据点收复与指挥官捕获等战果。安全责任移交进程继续进行，SNAF 的角色与责任范围逐步扩大。",
    "regional_impact": "SNAF 的能力与稳定性决定索马里安全过渡能否如期推进：若其承接能力不足而国际力量缩编过快，可能为 Al-Shabaab 提供重组空间，影响整个非洲之角的安全环境。",
    "risk_assessment": "对在索马里活动的国际行为体而言，SNAF 的作战能力与后勤保障水平是评估安全移交风险的核心变量；其薄弱环节可能转化为安全真空。",
    "events": {"list": [
        "2022 年以来：索马里安全部队接管约 7,000 名缩编 ATMIS 部队的责任。",
        "2024-12-27：安理会第 2767 号决议欢迎安全移交进展并授权 AUSSOM。",
        "2026-03：SNAF 与 AUSSOM 在联合攻势中收复下谢贝利 Daarusalaam 与 Mubarak 两座城镇。",
        "2026-04：SNAF Gorgor 203 部队与 AUSSOM 乌干达部队俘获 Al-Shabaab 指挥官。",
        "2026-05：UNSOS 组织 SNAF 与 AUSSOM、联合国警卫部队互操作训练。",
    ]},
    "uncertainties": {"list": [
        "SNAF 整体兵力与装备水平缺乏经核实的公开统计。",
        "各单元（如 Gorgor）的编制、规模与隶属关系未获权威来源系统说明。",
        "安全责任移交的条件与时间表在公开材料中未具体化。",
    ]},
    "gaps": "详细的作战序列、军费数据与部队伤亡统计缺失；关于其重建历程的完整叙述超出本内容包来源范围，故不展开。",
    "asip_analysis": "ASIP 判断：SNAF 应被理解为「过渡中的国家军事行为体」而非稳定的常备军。其能力评估必须结合两个动态：一是自 2022 年以来承接的 ATMIS 责任规模，二是与 AUSSOM 联合行动的实际成效。安全移交的真正风险点不在公开宣布的「移交」节点，而在移交后的能力真空期——这一窗口正是 Al-Shabaab 利用的典型机会结构。",
    "watch_indicators": [
        "安理会关于安全移交里程碑的新表述。",
        "SNAF 与 AUSSOM 联合行动的频率与战果报道。",
        "国际训练与后勤支持的新增公告。",
        "关于 SNAF 兵力、装备或薪酬状况的权威更新。",
    ],
    "core_assessment": "SNAF 是索马里安全过渡的核心国家载体，其能力承接与 Al-Shabaab 机会结构直接相关；对它的评估应以行动成效与移交进度为基准，而非纸面编制。",
    "sources": [
        "United Nations Security Council：《Resolution 2767 (2024)》（https://press.un.org/en/2024/sc15955.doc.htm）",
        "AUSSOM：《SNAF and AUSSOM recover two strategic cities》（https://au-ssom.org/snaf-and-aussom-recover-two-strategic-cities-in-coordinated-assault-against-al-shabaab/）",
        "AUSSOM：《Joint AUSSOM-SNAF operation captures senior Al-Shabaab commander》（https://au-ssom.org/joint-aussom-snaf-operation-captures-senior-al-shabaab-commander/）",
        "UNSOS：《UNSOS strengthens operational coordination》（https://unsos.unmissions.org/en/news/unsos-strengthens-operational-coordination-among-aussom-snaf-and-ungu-forces-through）",
    ],
}, importance="L1")


# =====================================================================
# 3. Puntland Security Forces (umbrella operational label)
# =====================================================================
ENT_PUNT = entity(
    entity_id="actor-puntland-security-forces",
    slug="puntland-security-forces",
    name_zh="邦特兰安全部队",
    name_en="Puntland Security Forces",
    acronym="",
    primary_type="regional_security_force_network",
    secondary_types=["security_force_collective"],
    aliases=["Puntland Security Force", "PSF"],
    importance_level="L1",
    short_description="联合国报告使用的行动层面集合标签，指代参与对 ISIS-Somalia 的「闪电」行动（Operation Hilaac）的多个邦特兰安全组成部分，并非单一法律意义上的统一部队。",
    full_description="「邦特兰安全部队」（Puntland Security Forces）是联合国报告对参与 Operation Hilaac（「闪电」行动，2024 年 12 月发起，打击 ISIS-Somalia）的多个邦特兰安全组成部分使用的行动层面集合标签。该行动集结约 4,000 名士兵，主要来自邦特兰安全部队（PSF）、邦特兰海上警察部队（PMPF）与邦特兰德尔维什部队（Puntland Dervish Force）。本实体明确不等于任何单一法律意义上的统一部队。",
    current_status="active",
    tags=["索马里", "邦特兰", "安全部队", "反恐"],
    region_ids=["region-sudan-red-sea-horn"],
    country_ids=[],
    disputed=True,
    source_refs=[S_PANEL777, S_UNS2026],
)

PROF_PUNT = profile({
    "lead": "「邦特兰安全部队」是联合国报告使用的行动层面集合概念，指代参与 2024 年 12 月发起的「闪电」行动（Operation Hilaac）以打击 ISIS-Somalia 的多个邦特兰安全组成部分。它不是一个在法律意义上统一的部队，而是一个由邦特兰安全部队（PSF）、邦特兰海上警察部队（PMPF）与邦特兰德尔维什部队等成分构成的行动集群。",
    "name_and_translation": "本平台采用中文译名「邦特兰安全部队」，英文规范名 Puntland Security Forces。该名称的集合性与行动性必须明确：联合国报告（S/2025/777）以 Puntland security forces 指称参与行动的多个组成部分；邦特兰安全部队（PSF）本身只是其中一支，不能把集合标签与任一具体单位混同。",
    "formation_background": "2024 年 12 月，邦特兰安全力量对盘踞在邦特兰山区（以 Cal Miskaat 为中心）的 ISIS-Somalia 发起大规模清剿行动，即 Operation Hilaac（「闪电」）。行动集结约 4,000 名士兵，主要来自邦特兰安全部队、邦特兰海上警察部队与邦特兰德尔维什部队。联合国专家小组（S/2025/777）记录了行动的组织与进展。",
    "history": "Operation Hilaac 是邦特兰对 ISIS-Somalia 长期盘踞山区的系统性回应。2024 年 12 月发起后，ISIS-Somalia 于 12 月 31 日以 12 名外国自杀式袭击者及武装无人机发动先发袭击，被邦特兰力量击退。2025 年 1 月起，邦特兰力量向 Cal Miskaat 纵深推进，夺取 ISIS-Somalia 的阵地、掩体、地道、洞穴与补给囤积点。联合国监测组（S/2026/44）评估该分支威胁因 Operation Hilaac 下的持续反恐努力而显著降低。",
    "structure": "本实体的结构描述必须携带集合性警示：Operation Hilaac 从多个邦特兰安全组成部分征调人员，包括邦特兰安全部队（PSF）、邦特兰海上警察部队（PMPF）与邦特兰德尔维什部队。这些单位分属不同职能与指挥传统，并非一个在法律意义上统一的组织；「邦特兰安全部队」标签仅反映其行动层面的集合。",
    "leadership": "行动由邦特兰当局（邦特兰总统及安全机构）统筹，具体指挥链涉及多个安全组成部分；公开来源未提供统一的单一指挥结构表述。",
    "force_capacity": "联合国专家小组（S/2025/777）报告 Operation Hilaac 集结约 4,000 名士兵；该数字属 Panel 报告口径，反映行动初期征调规模，非邦特兰安全部队的常备总兵力。",
    "geography": "行动区以邦特兰山区为核心，重点是 Cal Miskaat 地带——ISIS-Somalia 的主要盘踞地。Cal Miskaat 的崎岖地形（山地、洞穴与隧道）是行动的主要地理约束。",
    "tactics": "ISIS-Somalia 在行动中展现出特定的战术特征：2024 年 12 月 31 日以 12 名外国自杀式袭击者配合武装无人机发动先发打击；邦特兰力量则以地面推进、清剿据点与切断补给为主要方式。联合国专家小组记录了显著的人员损失（邦特兰方面）与 ISIS 的大规模损失。",
    "finance": "公开来源未提供邦特兰安全行动经费的详细数据；行动的后勤与外部支持（含区域与国际伙伴配合）在来源中仅以归属性方式提及，本平台不展开未经来源支撑的细节。",
    "legal_status": "邦特兰是索马里联邦共和国内的联邦成员州，其安全部队的法律地位由邦特兰当局与联邦安排界定。集合标签本身无独立法律人格，这是本实体区别于单一部队的关键建模要点。",
    "adversaries": "主要对手为 ISIS-Somalia。行动背景还涉及与区域及国际伙伴的反恐配合，但具体外部支持细节仅按来源归属记录。",
    "current_situation": "联合国监测组（S/2026/44）评估 ISIS-Somalia 的威胁因邦特兰安全部队在 Operation Hilaac 下、与区域及国际伙伴的持续反恐努力而显著降低；该报告中 ISIS-Somalia 估计仅约 200—300 名战斗人员。邦特兰力量的行动态势保持主动。",
    "regional_impact": "Operation Hilaac 显著削弱了 ISIS-Somalia 在邦特兰的盘踞能力，改变了非洲之角伊斯兰国分支的安全图景，也影响了该分支在伊斯兰国非洲网络中的财政与协调职能的实际可操作性。",
    "risk_assessment": "对区域安全而言，邦特兰行动的可持续性与国际支持力度是后续风险变量：若行动强度下降，ISIS-Somalia 残部可能利用山区地形重组。",
    "events": {"list": [
        "2024-12：邦特兰安全力量发起 Operation Hilaac，集结约 4,000 人。",
        "2024-12-31：ISIS-Somalia 以 12 名外国自杀式袭击者及武装无人机发动先发袭击，被击退。",
        "2025-01 起：邦特兰力量向 Cal Miskaat 推进，夺取阵地、掩体、隧道与补给。",
        "2025 年（至 10 月）：专家小组报告显著邦特兰伤亡与 ISIS 大规模损失。",
        "2026：UN S/2026/44 评估 ISIS-Somalia 威胁显著降低，估计剩约 200—300 名战斗人员。",
    ]},
    "uncertainties": {"list": [
        "「邦特兰安全部队」集合标签下的各单位编制、伤亡与指挥关系缺乏统一公开记录。",
        "行动伤亡数字来自联合国专家小组报告，属报告口径而非独立核实的战果。",
        "ISIS-Somalia 残部规模（200—300 人）为监测组估计，随时间可能变化。",
    ]},
    "gaps": "各单位的具体编成、指挥链与装备水平缺乏权威公开细节；外部空袭与伙伴支持的归属与规模未在本内容包来源中展开。",
    "asip_analysis": "ASIP 判断：邦特兰安全部队作为「行动层面集合标签」的建模价值，在于准确反映 Operation Hilaac 的组织现实——它是由多支邦特兰安全成分组成的联合行动集群，而非单一法律实体。若把集合标签写成统一部队，将错误地暗示邦特兰存在一体化的安全指挥体系。评估重点是行动本身的可持续性：邦特兰是联邦成员州，其资源有限，行动的长期维持高度依赖区域与国际支持，这一脆弱性是后续风险的关键。",
    "watch_indicators": [
        "Operation Hilaac 的后续阶段与战果报道（含新的据点收复）。",
        "联合国专家小组对邦特兰行动与 ISIS-Somalia 残部的更新评估。",
        "邦特兰当局关于安全部队整合或指挥结构的公开表述。",
        "外部支持（区域/国际）的新公告或调整。",
    ],
    "core_assessment": "邦特兰安全部队是 Operation Hilaac 的行动层面集合概念，其建模关键是保留多成分、非统一的性质；行动对 ISIS-Somalia 的显著削弱已获联合国评估确认，但可持续性存疑。",
    "sources": [
        "United Nations Panel of Experts on Somalia：《Final report S/2025/777》（https://documents.un.org/api/symbol/access?l=en&s=S%2F2025%2F777&t=pdf）",
        "United Nations Monitoring Team：《S/2026/44》（https://digitallibrary.un.org/record/4102624/files/S_2026_44-EN.pdf）",
        "Puntland State Police（官方背景页）：https://police.pl.so/",
    ],
}, importance="L1")

ORG_ENTITIES_1 = [ENT_AUSSOM, ENT_SNAF, ENT_PUNT]
ORG_PROFILES_1 = {
    "actor-aussom": PROF_AUSSOM,
    "actor-somali-national-armed-forces": PROF_SNAF,
    "actor-puntland-security-forces": PROF_PUNT,
}
