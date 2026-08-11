# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-C — historical entities module (part A).

Source of truth: ASIP-PPT-ENTITY-EXPANSION-C-Authoritative-Content-Pack.md.
No independent research; every claim traces to the pack's locked facts.
Mechanical floor: >=14 meaningful sections, >=1800 Chinese chars (all-char metric).
All entities target encyclopedia_full.
"""

TODAY = "2026-08-11"
IMPORTER = "expansion-c"

IMPORTANCE_L2 = "该实体对理解所在地区安全格局具有重要作用（L2）。"


def entity(**kw):
    base = {
        "entity_id": None,
        "entity_type": "organization",
        "primary_type": "organization",
        "secondary_types": [],
        "slug": None,
        "name_zh": None,
        "name_en": None,
        "acronym": "",
        "native_name": "",
        "aliases": [],
        "historical_names": [],
        "importance_level": "L2",
        "short_description": "",
        "full_description": "",
        "current_status": "",
        "primary_category": "",
        "tags": [],
        "profile_level": "L2",
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
        "freshness_status": "historical",
        "verification_status": "pending_review",
        "current_status_verified_at": TODAY,
        "freshness_reviewed_by": IMPORTER,
    }
    base.update(kw)
    return base


def profile(sections, importance="L2", depth="encyclopedia_full"):
    return {
        "profile_level": depth,
        "completeness": "Expansion C 内容包导入档案 · 百科式",
        "importance_level": importance,
        "importance_statement": IMPORTANCE_L2,
        "profile_depth": depth,
        "content_maturity": "E3_FULL_ENCYCLOPEDIA",
        "imported_by": IMPORTER,
        "sections": sections,
    }


# ---------------------------------------------------------------------------
# 1. Egyptian Islamic Jihad (EIJ)
# ---------------------------------------------------------------------------
S_UN_EIJ = "expc-un-eij"
S_UN_AQ = "expc-un-alqaida"
S_STATE_EIJ = "expc-state-eij-2003"
S_STATE_CTR = "expc-state-ctr-2019"

ENT_EIJ = entity(
    entity_id="actor-egyptian-islamic-jihad",
    slug="egyptian-islamic-jihad",
    name_zh="埃及伊斯兰圣战组织",
    name_en="Egyptian Islamic Jihad",
    acronym="EIJ",
    primary_type="terrorist_group",
    aliases=["Al-Jihad", "Jihad Group", "Islamic Jihad", "New Jihad Group", "Vanguards of Conquest", "Tala'a al-Fateh", "Talaa' al-Fateh", "埃及伊斯兰圣战"],
    historical_names=[],
    short_description="埃及伊斯兰圣战组织（EIJ）是自 1970 年代活跃的埃及极端组织，传统目标是推翻埃及政府并建立伊斯兰国家；其原组织涉嫌参与 1981 年萨达特总统遇刺。2001 年 6 月美国国务院历史报告称其与基地组织正式合并，联合国制裁叙述则描述 1998 年即已合并。",
    full_description="埃及伊斯兰圣战组织（Egyptian Islamic Jihad，EIJ）是活跃自 1970 年代的埃及极端组织，目标是推翻埃及政府并以伊斯兰国家取而代之，并针对埃及高级官员发动袭击。美国国务院历史报告称其于 2001 年 6 月与基地组织正式合并；联合国 1267 制裁叙述则描述 1998 年即与基地组织合并。ASIP 将 1998—2001 视为分阶段整合/正式化时期，不强行压缩为单一日期。",
    current_status="historical_absorbed_into_al_qaida",
    tags=["埃及", "历史组织", "基地组织前身", "圣战"],
    region_ids=["region-north-africa-sahara", "region-sudan-red-sea-horn"],
    country_ids=["country-sudan"],
    source_refs=[S_UN_EIJ, S_UN_AQ, S_STATE_EIJ, S_STATE_CTR],
)

PROF_EIJ = profile({
    "lead": "埃及伊斯兰圣战组织（Egyptian Islamic Jihad，EIJ）是活跃自 1970 年代的埃及极端组织。美国国务院历史报告描述其为以推翻埃及政府、建立伊斯兰国家为传统目标的组织，并针对埃及高级官员发动袭击；其原始组织与 1981 年萨达特总统遇刺相关。EIJ 与基地组织的关系是本档案的核心：联合国叙述描述 1998 年合并，美国国务院历史报告描述 2001 年 6 月正式合并，ASIP 将 1998—2001 处理为分阶段整合与正式化时期。",
    "name_and_translation": "本平台采用中文译名「埃及伊斯兰圣战组织」，英文规范名 Egyptian Islamic Jihad，缩写 EIJ。公开材料中亦常见 Al-Jihad、Jihad Group、Islamic Jihad、New Jihad Group、Vanguards of Conquest、Tala'a al-Fateh 等名称，本平台将其全部纳入别名索引。",
    "formation_background": "该组织活跃自 1970 年代，处于埃及伊斯兰主义反对派长期发展的脉络中。其传统政治目标是推翻埃及政府并建立伊斯兰国家，行动上针对埃及高级官员。其起源与埃及国内对世俗政权的伊斯兰主义反抗密切相关，具体组建时点在不同来源中存在差异，本档案不以单一日期定论。",
    "history": "原始圣战组织与 1981 年埃及总统安瓦尔·萨达特遇刺相关，这是其历史上最突出的行动节点。此后组织经历演变，出现以艾曼·扎瓦希里为代表的派别（美国国务院历史报告称扎瓦希里为 Vanguards of Conquest 派别领导人）。EIJ 不仅在埃及活动，还在阿富汗、巴基斯坦、苏丹等地保有成员与外部基地。",
    "ideology_goals": "其意识形态目标是推翻埃及政府并以伊斯兰国家取而代之；这使其区别于以跨境行动为主的全球圣战网络，尽管其后期与基地组织的整合使其融入全球圣战议程。本平台不把组织整体意识形态简化为单一口号，而是记录其以埃及政权更迭为核心的传统目标及其后期的网络化演变。",
    "leadership": "公开材料中最重要的领导人物是艾曼·扎瓦希里，美国国务院历史报告确认其为 Vanguards of Conquest 派别领导人。扎瓦希里后来成为基地组织领导人，这一人事线索是理解 EIJ 与基地组织整合的关键。组织内部其他领导层的完整名单超出本内容包来源范围。",
    "structure": "公开来源未提供 EIJ 完整的组织结构细节；可确认的是组织存在内部派别（如 Vanguards of Conquest），并维持埃及国内与国外（阿富汗、巴基斯坦、苏丹）的人员网络。本平台不编制超出来源支撑的组织架构。",
    "geography": "组织的活动与人员网络覆盖埃及及多个境外地点：美国国务院历史报告提及阿富汗、巴基斯坦与苏丹等外部基地。其地理网络是理解其与基地组织整合的物质基础。",
    "tactics": "传统行动方式是针对埃及高级官员的暗杀与袭击图谋；1981 年萨达特遇刺是其最突出的行动。后期在基地组织体系内的角色以领导层整合与网络化运作为主，具体作战行动细节超出本内容包范围。",
    "finance": "关于 EIJ 的资金渠道，公开来源未提供可引用的系统记载；其外部基地与网络维持涉及的人员与物资流动，仅在来源支撑范围内描述。",
    "legal_status": "EIJ 为联合国 1267 制裁机制列名实体（联合国叙述保留 1998 年合并表述）；美国国务院历史报告对其作出正式外国恐怖组织认定记录。注意：组织现实上已融入基地组织、不再作为独立组织运作，但其列名法律状态属于独立问题，两者不得混同。",
    "organizational_relation": "EIJ 与基地组织的关系是本档案的核心关系：联合国 1267 叙述描述 1998 年合并/整合（关联扎瓦希里与基地组织），美国国务院历史报告描述 2001 年 6 月正式合并。ASIP 明确保留两个日期，并作为 1998—2001 分阶段整合/正式化过程处理，不强行归一。此外 EIJ 参与了 1998 年世界伊斯兰阵线宣言的背景进程。",
    "current_situation": "作为独立组织，EIJ 已不复存在：其整合进基地组织后不再维持独立组织身份。本档案将其记录为历史组织，其历史意义在于构成埃及伊斯兰主义与全球圣战网络之间的关键人事与意识形态桥梁。",
    "regional_impact": "EIJ 的历史影响主要体现为：埃及伊斯兰主义运动的极端化案例、以及通过扎瓦希里等人物向全球圣战网络的领导层输送。其对北非及苏丹—红海—非洲之角地区伊斯兰主义网络的后续影响，属于历史谱系层面的延续。",
    "events": {"list": [
        "1970 年代：组织活跃，传统目标为推翻埃及政府。",
        "1981-10：原始圣战组织与萨达特总统遇刺相关。",
        "1998：联合国 1267 叙述描述 EIJ 与基地组织合并/整合（关联扎瓦希里）；同年参与世界伊斯兰阵线宣言背景进程。",
        "2001-06：美国国务院历史报告描述 EIJ 与基地组织正式合并。",
        "此后：作为独立组织身份终止，融入基地组织体系。",
    ]},
    "uncertainties": {"list": [
        "EIJ 的确切组建时点与早期组织形态在来源中存在差异。",
        "1998 年与 2001 年两个合并日期来自不同权威叙述，ASIP 不强行归一（见组织关系一节）。",
        "内部派别结构与领导层的完整图景缺乏系统公开记载。",
    ]},
    "gaps": "组织完整的编制、资金与行动记录缺乏可引用的系统来源；本档案以 UN 与国务院历史报告为锚，不填补未经来源支撑的细节。",
    "asip_analysis": "ASIP 判断：EIJ 的核心价值是「谱系节点」——它演示了国家层面伊斯兰主义运动如何通过人事与网络整合进入跨国圣战体系。评估时应把 1998 与 2001 两个日期视为不同权威叙述的阶段标记而非矛盾：UN 描述整合进程开启，国务院描述正式化完成。该实体的档案厚度以谱系意义为主，不作为当前威胁实体评估。",
    "watch_indicators": [
        "联合国或美国官方是否更新 EIJ 相关列名或历史叙述。",
        "围绕 1998—2001 整合进程是否出现新的权威历史材料。",
        "扎瓦希里在基地组织体系中的继任或变动对 EIJ 谱系叙事的影响。",
    ],
    "core_assessment": "EIJ 是埃及伊斯兰主义与全球圣战网络之间的关键历史桥梁，其档案以谱系与整合进程为核心，双日期处理是事实纪律的体现。",
    "sources": [
        "UN 1267：《Egyptian Islamic Jihad — narrative summary》（https://main.un.org/securitycouncil/en/sanctions/1267/aq_sanctions_list/summaries/entity/egyptian-islamic-jihad）",
        "UN 1267：《Al-Qaida — narrative summary》（https://main.un.org/securitycouncil/en/sanctions/1267/aq_sanctions_list/summaries/entity/al-qaida）",
        "U.S. State：《Country Reports on Terrorism 2003 — EIJ 历史 FTO 报告》（https://2009-2017.state.gov/j/ct/rls/crt/2003/31711.htm）",
        "U.S. State：《Country Reports on Terrorism 2019》（https://2017-2021.state.gov/reports/country-reports-on-terrorism-2019/）",
    ],
})


# ---------------------------------------------------------------------------
# 2. Armed Islamic Group (GIA)
# ---------------------------------------------------------------------------
S_UN_GIA = "expc-un-gia"
S_UN_AQIM = "un-aqim-2001"
S_NCTC_AQIM = "deptha-nctc-aqim-2026-06"

ENT_GIA = entity(
    entity_id="actor-gia",
    slug="gia",
    name_zh="阿尔及利亚武装伊斯兰集团",
    name_en="Armed Islamic Group",
    acronym="GIA",
    primary_type="terrorist_group",
    aliases=["Groupe Islamique Armé", "Armed Islamic Group of Algeria", "GIA"],
    historical_names=[],
    short_description="阿尔及利亚武装伊斯兰集团（GIA）于阿尔及利亚 1990 年代内战初期兴起，成为该国最激进暴力的伊斯兰组织之一。1993 年起发动高调恐怖行动，针对平民、公共目标与国家/安全目标。1998 年哈桑·哈塔布自 GIA 分裂成立 GSPC（后改名 AQIM），GIA 是理解 GSPC/AQIM 谱系的历史源头。",
    full_description="阿尔及利亚武装伊斯兰集团（Groupe Islamique Armé，GIA）在阿尔及利亚 1990 年代国内冲突初期出现，并成为该国最激进的暴力伊斯兰组织之一。联合国制裁叙述称其 1993 年开始高调恐怖行动，迅速成为阿尔及利亚最激进暴力的极端组织之一，暴力同时针对平民、公共目标与国家安全目标。1998 年哈桑·哈塔布自 GIA 分裂成立 GSPC（2007 年更名 AQIM）。GIA 作为 GSPC/AQIM 谱系的历史源头网络记录，而非当前组织。",
    current_status="historical_largely_defunct",
    tags=["阿尔及利亚", "历史组织", "GSPC/AQIM 前身", "内战"],
    region_ids=["region-north-africa-sahara"],
    country_ids=[],
    source_refs=[S_UN_GIA, S_UN_AQIM, S_NCTC_AQIM],
)

PROF_GIA = profile({
    "lead": "阿尔及利亚武装伊斯兰集团（Groupe Islamique Armé，GIA）在阿尔及利亚 1990 年代国内冲突初期兴起，成为该国最激进的暴力伊斯兰组织之一。联合国制裁叙述称其 1993 年起发动高调恐怖行动，暴力同时针对平民、公共目标与国家安全目标。GIA 是理解 GSPC/AQIM 谱系的历史源头：1998 年哈桑·哈塔布自 GIA 分裂成立 GSPC。",
    "name_and_translation": "本平台采用中文译名「阿尔及利亚武装伊斯兰集团」，英文规范名 Armed Islamic Group，缩写 GIA，法语 Groupe Islamique Armé；别名还包括 Armed Islamic Group of Algeria。",
    "formation_background": "GIA 出现在阿尔及利亚 1990 年代国内冲突（内战）初期，成为冲突中最激进的暴力伊斯兰组织之一。其兴起与阿尔及利亚当时的政治危机与伊斯兰主义运动激进化的背景相关。",
    "history": "1993 年，GIA 开始高调恐怖行动，并迅速成为阿尔及利亚最激进暴力的极端组织之一。其暴力史既针对平民与公共目标，也针对国家安全目标，这一特征使其在同时期的伊斯兰主义武装中格外突出。1998 年，哈桑·哈塔布脱离 GIA 成立 GSPC，成为 GIA 谱系的关键转折。",
    "ideology_goals": "GIA 属于阿尔及利亚内战中的激进伊斯兰主义武装，其意识形态以推翻现政权、建立伊斯兰秩序为核心；对平民目标的暴力使其在同类组织中居于极端一端。本平台以来源支撑为准，不展开未经记载的意识形态细节。",
    "leadership": "公开材料对 GIA 领导层的可靠记载有限；与 GSPC/AQIM 谱系相关的重要人物是哈桑·哈塔布（1998 年自 GIA 分裂）与阿卜杜勒马利克·德鲁克德勒（曾在 GIA 担任爆炸物专家，后成为 GSPC/AQIM 领导人）。两人均为来源确认的谱系人物。",
    "structure": "GIA 的组织结构在来源中缺乏完整记载；其激进性与对内对外暴力史提示其组织控制有限且碎片化，但本平台不据此推断具体编制。",
    "geography": "GIA 的活动以阿尔及利亚为主要舞台，属于北非萨赫勒—撒哈拉安全分析中的阿尔及利亚环节；其跨境网络的细节超出本内容包来源范围。",
    "tactics": "其行动方式以高调恐怖行动为特征，覆盖平民、公共与安全目标；后期组织凝聚力与行为模式存在不确定性，相关叙述以来源为准。",
    "finance": "GIA 的资金渠道缺乏可引用的系统记载；本档案不展开未经来源支撑的财务细节。",
    "legal_status": "GIA 为联合国 1267 制裁机制列名实体；其列名法律状态与组织现实解体属于两个独立问题，本档案分开记录。",
    "organizational_relation": "GIA 与 GSPC/AQIM 的关系是核心谱系关系：1998 年哈桑·哈塔布自 GIA 分裂成立 GSPC，GSPC 于 2007 年更名 AQIM。因此 GSPC/AQIM 连续体分裂自 GIA。关系档案明确：分裂实体成立时名为 GSPC，2007 年更名为 AQIM。此外，德鲁克德勒（后任 GSPC/AQIM 领导人）曾在 GIA 任爆炸物专家，是人事连续性证据。",
    "current_situation": "GIA 作为当前组织基本已解体（largely defunct）；其当代意义是作为 GSPC/AQIM 谱系的历史源头网络被记录，不作为当前活跃组织评估。",
    "regional_impact": "GIA 对阿尔及利亚内战形态有重大历史影响，并经由 GSPC/AQIM 延续至当代萨赫勒反恐格局：GIA 谱系 → GSPC → AQIM →（萨赫勒分支）是理解北非圣战网络连续性的关键链条。",
    "events": {"list": [
        "1990 年代初：阿尔及利亚国内冲突初期，GIA 兴起。",
        "1993：开始高调恐怖行动，成为阿尔及利亚最激进暴力组织之一。",
        "1998：哈桑·哈塔布自 GIA 分裂成立 GSPC。",
        "2007-01：GSPC 更名为 AQIM（谱系延续，非新分裂）。",
    ]},
    "uncertainties": {"list": [
        "GIA 后期组织凝聚力与实际控制存在不确定性。",
        "GIA 领导层的可靠传记材料有限。",
        "GIA 与阿尔及利亚国家冲突之间的复杂互动超出本档案来源范围。",
    ]},
    "gaps": "GIA 完整编制、资金与内部结构缺乏系统公开记载；本档案以 UN 叙述与谱系事实为锚。",
    "asip_analysis": "ASIP 判断：GIA 在情报图中的价值是「谱系根节点」——GSPC/AQIM 的分裂源头。评估 GIA 时应注意三层区分：其作为历史组织的暴力史、其作为谱系源头对 GSPC/AQIM 的人事与意识形态馈赠、以及其法律列名状态。三者时间维度不同，不得混同。",
    "watch_indicators": [
        "联合国或美国官方对 GIA 列名或历史叙述的更新。",
        "GIA 谱系人物（如德鲁克德勒继任者）在 AQIM/JNIM 体系中的公开变动。",
        "学术或官方对 GIA 历史的新研究。",
    ],
    "core_assessment": "GIA 是 GSPC/AQIM 谱系的历史源头，其档案以谱系连续性为核心，区分历史组织、谱系源头与法律状态三个层面。",
    "sources": [
        "UN 1267：《Armed Islamic Group (GIA) — narrative summary》（https://main.un.org/securitycouncil/en/sanctions/1267/aq_sanctions_list/summaries/entity/armed-islamic-group）",
        "UN 1267：《The Organization of Al-Qaida in the Islamic Maghreb — narrative summary》（https://main.un.org/securitycouncil/en/sanctions/1267/aq_sanctions_list/summaries/entity/the-organization-of-al-qaida-in-the-islamic）",
        "NCTC：《AQIM》（2026-06）（https://www.dni.gov/nctc/terrorist_groups/aqim.html）",
    ],
})


# ---------------------------------------------------------------------------
# 3. Al-Itihaad al-Islamiya (AIAI)
# ---------------------------------------------------------------------------
S_UN_AIAI = "expc-un-aiai"
S_S2016 = "expc-un-s2016-919"
S_S2017 = "expc-un-s2017-924"
S_NCTC_SHABAAB = "expa-nctc-al-shabaab-2026-04"

ENT_AIAI = entity(
    entity_id="actor-aiai",
    slug="aiai",
    name_zh="伊斯兰联盟组织",
    name_en="Al-Itihaad al-Islamiya",
    acronym="AIAI",
    primary_type="organization",
    aliases=["Al-Ittihad al-Islami", "Al-Itihaad al-Islamiya", "Islamic Union", "伊斯兰联盟"],
    historical_names=[],
    short_description="伊斯兰联盟组织（AIAI）约于 1982—1984 年建立，与其他组织一同寻求推翻索马里政府，活动于索马里与埃塞俄比亚。联合国材料确认哈桑·达希尔·阿韦斯为其高级领导人，并称 AIAI 是青年党的意识形态前身/前驱网络。ASIP 将其建模为青年党的重要意识形态/人事前身网络，而非唯一直接组织传承。",
    full_description="伊斯兰联盟组织（Al-Itihaad al-Islamiya，AIAI）约于 1982—1984 年建立，寻求与其他组织一同推翻索马里政府，活动覆盖索马里与埃塞俄比亚。联合国制裁材料确认哈桑·达希尔·阿韦斯为高级领导人，联合国专家组报告称其为青年党的意识形态前身/前驱网络。ASIP 明确：AIAI 是青年党的重要意识形态/人事前身网络，公开来源不支持把青年党的起源简化为单一的 AIAI→青年党组织传承。",
    current_status="historical_dissolved_or_absorbed_as_independent_network",
    tags=["索马里", "历史组织", "青年党前身", "埃塞俄比亚"],
    region_ids=["region-sudan-red-sea-horn"],
    country_ids=["country-ethiopia"],
    source_refs=[S_UN_AIAI, S_S2016, S_S2017, S_NCTC_SHABAAB],
)

PROF_AIAI = profile({
    "lead": "伊斯兰联盟组织（Al-Itihaad al-Islamiya，AIAI）约于 1982—1984 年建立，与其他组织一同寻求推翻索马里政府，活动于索马里与埃塞俄比亚。联合国材料确认哈桑·达希尔·阿韦斯为高级领导人，联合国专家组报告将其描述为青年党的意识形态前身。ASIP 把 AIAI 建模为青年党的重要意识形态/人事前身网络，明确其并非青年党的唯一直接组织传承。",
    "name_and_translation": "本平台采用中文译名「伊斯兰联盟组织」，英文规范名 Al-Itihaad al-Islamiya，缩写 AIAI；别名包括 Al-Ittihad al-Islami、Islamic Union。",
    "formation_background": "AIAI 约于 1982—1984 年建立，处于索马里伊斯兰主义组织发展的早期阶段。其建立动机与其他组织共同寻求推翻索马里政府，属于索马里政治伊斯兰主义运动的组成部分。",
    "history": "AIAI 的活动贯穿 1980 年代至 1990 年代，覆盖索马里与埃塞俄比亚。其网络包括在索马里的政治—武装活动以及在埃塞俄比亚相关地区的行动。其后期经历衰落与碎片化，部分人员与网络进入索马里伊斯兰主义后续生态。",
    "ideology_goals": "AIAI 的政治目标是以伊斯兰秩序取代索马里现政权，属于索马里伊斯兰主义运动早期形态；其意识形态与后来青年党的激进圣战议程之间存在联系，但联系的性质与程度以来源为准，本平台不把两者意识形态划等号。",
    "leadership": "联合国制裁材料确认哈桑·达希尔·阿韦斯为 AIAI 高级领导人。阿韦斯后来在索马里伊斯兰主义生态中的角色使其成为 AIAI 与后续网络之间的人事桥梁；具体继任与层级细节超出本内容包来源范围。",
    "structure": "AIAI 的结构在来源中缺乏系统记载；其运作兼具网络与组织特征，覆盖索马里与埃塞俄比亚的人员与活动。本平台不编制超出来源支撑的组织架构。",
    "geography": "AIAI 的活动地理覆盖索马里与埃塞俄比亚。这一跨境地理是其作为地区性伊斯兰主义网络的重要特征，也解释了其后继网络（含青年党生态）的跨境属性。",
    "tactics": "AIAI 的行动方式包括武装活动与政治动员，具体作战与动员细节在来源中记载有限；本档案不展开未经来源支撑的战术描述。",
    "finance": "AIAI 的资金与训练网络缺乏可引用的系统公开记载；其网络运作涉及的资源流动仅在来源支撑范围内描述。",
    "legal_status": "AIAI 为联合国 1267 制裁机制列名实体（联合国叙述保留其历史定性）；其列名法律状态与组织现实解体属独立问题。",
    "organizational_relation": "AIAI 与青年党的关系是核心限定关系：联合国专家组报告将 AIAI 描述为青年党的意识形态前身/前驱网络，联合国综合制裁材料亦报告 AIAI 在索马里/埃塞俄比亚活动并有并入青年党的描述。ASIP 明确限定：这些描述不足以把 AIAI 呈现为青年党的唯一组织亲本——青年党的形成来自更复杂的索马里伊斯兰主义/伊斯兰法院联盟（ICU）生态，AIAI 是其中重要的意识形态/人事前身网络。",
    "current_situation": "AIAI 作为独立网络已解体或被吸收；其当代意义是索马里伊斯兰主义谱系中的历史节点，用于解释青年党生态的意识形态与人事来源，不作为当前独立组织评估。",
    "regional_impact": "AIAI 的历史影响体现在索马里与埃塞俄比亚两国的伊斯兰主义网络谱系；其对青年党生态的意识形态/人事馈赠是理解当代索马里安全格局的历史基础。",
    "events": {"list": [
        "约 1982—1984：AIAI 建立。",
        "1980s—1990s：在索马里与埃塞俄比亚活动。",
        "联合国专家组报告（S/2016/919、S/2017/924）：将 AIAI 描述为青年党意识形态前身/前驱网络。",
        "后期：独立网络解体或被吸收，人员与网络进入索马里伊斯兰主义后续生态。",
    ]},
    "uncertainties": {"list": [
        "AIAI 的确切建立时点（约 1982—1984）与早期组织形态存在来源差异。",
        "AIAI 并入青年党的具体机制与范围缺乏系统公开记载。",
        "AIAI 与 ICU 生态各网络之间的边界不清晰。",
    ]},
    "gaps": "AIAI 完整编制、资金、训练网络细节缺乏可引用系统来源；本档案以 UN 叙述与专家组报告为锚，不填补未经来源支撑的内容。",
    "asip_analysis": "ASIP 判断：AIAI 的档案价值在于「限定性前身」——它是青年党生态的重要意识形态/人事来源，但绝不能写成「AIAI 直接变成青年党」。评估索马里谱系时，应把 AIAI 放在 ICU 时代多网络生态中定位，避免单一组织传承叙事。",
    "watch_indicators": [
        "联合国专家组关于索马里网络谱系的新报告。",
        "涉及阿韦斯或其他 AIAI 谱系人物的公开动态。",
        "对青年党起源的学术或官方新研究。",
    ],
    "core_assessment": "AIAI 是索马里伊斯兰主义谱系中的限定性前身网络，其与青年党的关系以意识形态/人事传承定性，明确排除单一直接组织传承叙事。",
    "sources": [
        "UN 1267：《Al-Itihaad al-Islamiya (AIAI) — narrative summary》（https://main.un.org/securitycouncil/en/sanctions/1267/aq_sanctions_list/summaries/entity/al-itihaad-al-islamiya/aiai）",
        "UN 专家组：《S/2016/919》（https://digitallibrary.un.org/record/846995/files/S_2016_919-EN.pdf）",
        "UN 专家组：《S/2017/924》（https://digitallibrary.un.org/record/1317757/files/S_2017_924-EN.pdf）",
        "NCTC：《Al-Shabaab》（2026-04）（https://www.odni.gov/nctc/terrorist_groups/al_shabaab.html）",
    ],
})


# ---------------------------------------------------------------------------
# 4. Tunisian Combatant Group (TCG)
# ---------------------------------------------------------------------------
S_UN_TCG = "expc-un-tcg"
S_UN_MAAROUFI = "expc-un-tcg-maaroufi"
S_STATE_TCG = "expc-state-tcg-2002"

ENT_TCG = entity(
    entity_id="actor-tunisian-combatant-group",
    slug="tunisian-combatant-group",
    name_zh="突尼斯战斗组织",
    name_en="Tunisian Combatant Group",
    acronym="TCG",
    primary_type="organization",
    aliases=["Groupe Combattant Tunisien", "Jama'a Combattante Tunisienne", "Tunisian Fighting Group", "突尼斯战斗团"],
    historical_names=[],
    short_description="突尼斯战斗组织（TCG）于 2000 年由赛法拉·本·奥马尔·本·穆罕默德·本·哈辛及相关人物（含塔里克·阿尔-马鲁菲）创建，成员与阿富汗基地组织相关营地有联系。美国国务院历史报告称其寻求在突尼斯建立伊斯兰政权并针对美国与西方利益。欧洲调查严重打击了其关联网络。",
    full_description="突尼斯战斗组织（Tunisian Combatant Group，TCG）于 2000 年由赛法拉·本·奥马尔·本·穆罕默德·本·哈辛及塔里克·阿尔-马鲁菲等关联人物创建，成员与阿富汗基地组织相关营地有联系。美国国务院历史报告称其目标是建立伊斯兰政权并针对美国与西方利益。欧洲调查严重破坏了与 TCG 关联的网络。TCG 属于连接阿富汗受训激进分子、欧洲后勤网络与后来突尼斯极端主义圈子的跨国北非圣战网络的一部分；不得将 TCG 自动等同于后来的突尼斯安萨尔伊斯兰教法组织。",
    current_status="historical_severely_disrupted",
    tags=["突尼斯", "历史网络", "阿富汗一代", "欧洲后勤"],
    region_ids=["region-north-africa-sahara"],
    country_ids=[],
    source_refs=[S_UN_TCG, S_UN_MAAROUFI, S_STATE_TCG],
)

PROF_TCG = profile({
    "lead": "突尼斯战斗组织（Tunisian Combatant Group，TCG）于 2000 年由赛法拉·本·奥马尔·本·穆罕默德·本·哈辛及塔里克·阿尔-马鲁菲等关联人物创建，成员与阿富汗基地组织相关营地有联系。美国国务院历史报告称其目标是在突尼斯建立伊斯兰政权并针对美国与西方利益。欧洲调查严重打击了其关联网络；本档案将 TCG 作为跨国北非圣战网络的历史环节记录。",
    "name_and_translation": "本平台采用中文译名「突尼斯战斗组织」，英文规范名 Tunisian Combatant Group，缩写 TCG；别名包括 Groupe Combattant Tunisien、Jama'a Combattante Tunisienne、Tunisian Fighting Group。",
    "formation_background": "TCG 于 2000 年由赛法拉·本·奥马尔·本·穆罕默德·本·哈辛（Seifallah ben Omar ben Mohamed ben Hassine）及相关人物（含塔里克·阿尔-马鲁菲）创建。其形成背景是 1990 年代阿富汗基地组织营地训练网络向北非的人员回流。",
    "history": "TCG 成员与阿富汗基地组织相关营地有联系，属于「阿富汗一代」北非网络。欧洲多国调查严重打击了与 TCG 关联的招募与后勤网络，使其组织能力显著受损。其活动史以跨国人员流动与欧洲后勤网络为特征。",
    "ideology_goals": "美国国务院历史报告称 TCG 寻求在突尼斯建立伊斯兰政权，并针对美国与西方利益。其意识形态属于突尼斯伊斯兰主义圣战分支，但本平台不把其与后来的突尼斯安萨尔伊斯兰教法组织自动等同——人事与意识形态重叠不得改写为组织身份同一。",
    "leadership": "创始人赛法拉·本·奥马尔·本·穆罕默德·本·哈辛为主要领导人物；塔里克·阿尔-马鲁菲为联合国列名的关联人物。两人均为来源确认的 TCG 关键人物。",
    "structure": "TCG 兼具组织与跨国网络特征，成员分布于北非与欧洲；具体编制缺乏系统公开记载，本平台不展开未经来源支撑的结构细节。",
    "geography": "TCG 的活动网络覆盖突尼斯（目标国）、阿富汗（训练营地联系）与欧洲（招募与后勤）。这一三角地理是其作为跨国网络的核心特征。",
    "tactics": "其行动方式以招募、后勤与潜在袭击策划为主；具体行动记录在来源中有限，欧洲调查披露的逮捕与网络打击是主要证据来源。",
    "finance": "TCG 的资金渠道缺乏可引用的系统记载；欧洲调查披露的物流与招募网络细节仅在来源支撑范围内描述。",
    "legal_status": "TCG 为联合国 1267 制裁机制列名实体；塔里克·阿尔-马鲁菲为列名个人。列名法律状态与组织现实受挫属独立问题。",
    "organizational_relation": "TCG 与基地组织的关系为历史关联：成员与阿富汗基地组织相关营地有联系，联合国叙述将其置于基地组织网络背景下。ASIP 以 historically_associated_with 建模（历史关联），并在档案中明确关联的性质为训练营地联系与网络归属，而非正式效忠关系。此外，TCG 与后来突尼斯极端主义圈子的关系仅作历史比较，不建组织传承边。",
    "current_situation": "TCG 作为独立组织已严重受挫（severely disrupted）；其当代意义是理解北非「阿富汗一代」网络向欧洲后勤与后来突尼斯极端主义生态的历史桥梁，不作为当前活跃组织评估。",
    "regional_impact": "TCG 的历史影响体现为：连接阿富汗训练网络、欧洲后勤与突尼斯极端主义圈子的跨国链条；其对北非反恐格局的历史意义大于当前行动意义。",
    "events": {"list": [
        "2000：TCG 由哈辛及相关人物创建。",
        "2002-10：联合国 1267 列名（TCG 及关联人物阿尔-马鲁菲）。",
        "2000 年代：欧洲多国调查打击关联网络。",
        "此后：组织能力严重受损，作为独立组织的历史记录为主。",
    ]},
    "uncertainties": {"list": [
        "TCG 与后来突尼斯极端组织之间的人事/意识形态重叠细节缺乏系统公开记载。",
        "TCG 成员在阿富汗营地的具体训练角色记载有限。",
        "组织规模与结构缺乏权威统计。",
    ]},
    "gaps": "TCG 完整编制、资金与行动记录缺乏系统来源；本档案以 UN 叙述与国务院历史报告为锚。",
    "asip_analysis": "ASIP 判断：TCG 的档案价值是「跨国网络节点」——它演示了阿富汗一代北非网络如何通过欧洲后勤运作。评估时须守住一条纪律：TCG 与后来突尼斯极端主义圈子的关系是历史比较与人事重叠，不是组织身份同一，不得自动写为传承边。",
    "watch_indicators": [
        "联合国或美国官方对 TCG 列名或历史叙述的更新。",
        "涉及哈辛或阿尔-马鲁菲相关网络的新公开动态。",
        "对北非阿富汗一代网络的新学术或官方研究。",
    ],
    "core_assessment": "TCG 是北非阿富汗一代跨国网络的历史节点，其档案以跨国网络结构与历史关联为核心，明确区分历史组织、网络联系与后来突尼斯极端主义生态。",
    "sources": [
        "UN 1267：《Tunisian Combatant Group — narrative summary》（https://main.un.org/securitycouncil/en/sanctions/1267/aq_sanctions_list/summaries/entity/tunisian-combatant-group）",
        "UN 1267：《Tarek ben Habib ben al-Toumi al-Maaroufi — narrative summary》（https://main.un.org/securitycouncil/en/sanctions/1267/aq_sanctions_list/summaries/individual/tarek-ben-habib-ben-al-toumi-al-maaroufi）",
        "U.S. State：《Patterns of Global Terrorism 2002》（https://2009-2017.state.gov/j/ct/rls/crt/2002/html/19992.htm）",
    ],
})

ORG_ENTITIES_A = [ENT_EIJ, ENT_GIA, ENT_AIAI, ENT_TCG]
ORG_PROFILES_A = {
    "actor-egyptian-islamic-jihad": PROF_EIJ,
    "actor-gia": PROF_GIA,
    "actor-aiai": PROF_AIAI,
    "actor-tunisian-combatant-group": PROF_TCG,
}
