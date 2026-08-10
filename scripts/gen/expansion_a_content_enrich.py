#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-A — ENRICH_EXISTING module (§5 Ansaru, §6 Lakurawa).

Both entities already exist with stable IDs (actor-ansaru / actor-lakurawa) and
MUST NOT be duplicated (pack §0.3). This module carries field-level patches and
additive profile sections only; existing sections are preserved unless the pack
requires a correction.
"""

from expansion_a_content_orgs import TODAY, IMPORTER, S_ANSARU_NCTC, S_NIGSAC, S_ACLED_JUNE

# =====================================================================
# 5. Ansaru — ENRICH_EXISTING
# =====================================================================
ANSARU_ENTITY_PATCH = {
    "name_zh": "安萨鲁组织",
    "name_en": "Ansaru",
    "acronym": "Ansaru",
    "aliases_add": [
        "Ansarul Muslimina Fi Biladis Sudan",
        "Jama'atu Ansarul Muslimina Fi Biladis Sudan",
        "JAMBS",
        "Vanguards for the Protection of Muslims in Black Africa",
        "Jamaat Ansar al-Muslimeen fi Bilad al-Sudan",
    ],
    "importance_level": "L2",
    "current_status": "active_but_leadership_disrupted",
    "short_description": "2012 年 1 月从博科圣地体系分裂的尼日利亚武装；NCTC 称其历史上与 AQIM 结盟，主要活动于尼日利亚西北部及贝宁—尼日尔—尼日利亚三边地带。当前成员规模不明，近期尼日利亚反恐行动扰乱其高层领导。",
    "full_description": "安萨鲁组织于 2012 年 1 月从博科圣地体系分裂。NCTC 指出，分裂在很大程度上源于其反对博科圣地针对穆斯林平民的无差别袭击，以及自身向基地组织阵营的靠拢。NCTC 把它描述为历史上与 AQIM 结盟的组织，主要活动区域为尼日利亚西北部及贝宁—尼日尔—尼日利亚三边地带。其历史行为模式包括以勒索赎金为目的的绑架（含针对西方人的绑架）与轻武器袭击。当前成员规模不明；近期尼日利亚反恐行动扰乱了其高层领导，因此当前状态应表述为「仍活跃但领导层受扰」。",
    "confidence": "high",
    "temporal_sensitive": True,
    "source_refs_add": [S_ANSARU_NCTC],
    "record_updated_at": TODAY,
    "claim_valid_as_of": TODAY,
    "last_verified_at": TODAY,
    "current_status_verified_at": TODAY,
    "freshness_reviewed_by": IMPORTER,
}

ANSARU_PROFILE_TOP = {
    "profile_level": "encyclopedia_full",
    "completeness": "Expansion A 内容包导入档案 · 百科式",
    "profile_depth": "encyclopedia_full",
    "content_maturity": "E3_FULL_ENCYCLOPEDIA",
    "imported_by": IMPORTER,
}

# additive / corrective sections. Existing keys not listed here are preserved.
ANSARU_SECTIONS = {
    "name_and_translation": "本平台以「安萨鲁组织」为中文名，英文规范名 Ansaru。该组织的完整名称在不同来源中有多种写法，包括 Ansarul Muslimina Fi Biladis Sudan、Jama'atu Ansarul Muslimina Fi Biladis Sudan 及缩写 JAMBS；其名称的英文意译常作 Vanguards for the Protection of Muslims in Black Africa（黑非洲穆斯林保护先锋）。这些写法均指向同一组织，已一并纳入别名索引。",
    "formation_background": "该组织成立于 2012 年 1 月，由博科圣地体系分裂而来。NCTC 的资料把分裂原因归结为两点：其一是对博科圣地针对穆斯林平民实施无差别袭击的反对，其二是该派系自身向基地组织阵营的靠拢。这两点说明，分裂并非单纯的人事或地盘之争，而是包含了打击目标选择原则与全球阵营归属在内的路线分歧。",
    "ideology_objectives": "从其分裂缘由可以看出该组织的自我定位：它反对把穆斯林平民作为无差别打击对象，并以「保护黑非洲穆斯林」作为名称层面的诉求表达。这一定位使其在尼日利亚圣战光谱中与博科圣地体系形成明确区隔，也构成其向基地组织阵营靠拢的意识形态基础。",
    "external_relations": "NCTC 把该组织描述为历史上与 AQIM 结盟。在本平台既有数据中，其与 AQIM 的关系已登记为效忠关系，与 JNIM 的关系登记为关联关系，二者均予以保留。至于与 Katiba Hanifa 之间可能存在的协作关系，本内容包未提供可引用的证据支撑，因此不予建边，相关项已记入未决依赖清单。",
    "geography": "NCTC 指出其主要活动区域为尼日利亚西北部，以及贝宁—尼日尔—尼日利亚三边地带。这一地理分布使其不同于以博尔诺州与乍得湖核心区为主的博科圣地体系，也解释了它为何被视为连接尼日利亚安全格局与萨赫勒基地组织网络的桥梁节点。",
    "force_capacity": "当前成员规模不明。本平台明确不采用任何未获权威来源支撑的固定兵力数字——包括流传较广的两千至三千人一类的表述。对该组织而言，兵力估计的缺失本身就是一项需要在档案中显性标注的信息状态，而不是可以用近似值填补的空白。",
    "tactics": "其历史行为模式包括以勒索赎金为目的的绑架，其中含针对西方人的绑架案例，以及使用轻武器实施的袭击。绑架西方人这一特征对外国人员风险评估具有直接意义：它说明该组织在目标选择上具备识别高价值外籍目标的意愿与能力。",
    "current_situation": "近期尼日利亚方面的反恐行动扰乱了该组织的高层领导。因此，在没有更精确的存量证据之前，其当前状态应表述为「仍然活跃但领导层受到扰乱」，而不宜简单标注为完全活跃或已被瓦解。领导层受扰通常会在短期内影响协调能力，但不必然导致组织解体。",
    "risk_assessment": "对外国人员而言，该组织的主要风险来自其历史上以赎金为目的的绑架行为。相关风险在尼日利亚西北部及贝宁—尼日尔—尼日利亚三边地带尤为需要关注。由于其当前规模与指挥状态均不透明，风险评估应以行为模式而非兵力规模为基准。",
    "uncertainties": {"list": [
        "当前成员规模不明，任何固定兵力数字均缺乏权威来源支撑。",
        "领导层受扰之后的实际组织完整度与恢复能力无法从公开材料判断。",
        "其与 AQIM、JNIM 之间的实际指挥与协调深度缺少完整公开信息。",
        "与 Katiba Hanifa 的协作关系缺少可引用证据，本平台暂不建立该关系。",
    ]},
    "events": {"p": [
        "2012 年 1 月：从博科圣地体系分裂，分裂原因包含对无差别袭击穆斯林平民的反对与向基地组织阵营的靠拢。",
        "此后：NCTC 将其描述为历史上与 AQIM 结盟的组织，活动集中于尼日利亚西北部与三边地带。",
        "历史行为：以勒索赎金为目的实施绑架，包括针对西方人的绑架，并使用轻武器实施袭击。",
        "近期：尼日利亚反恐行动扰乱其高层领导，当前状态调整为「活跃但领导层受扰」。",
    ]},
    "gaps": "该实体最突出的信息缺口是规模与指挥结构。本平台的处理原则是把缺口显性化：宁可在档案中标注「不明」，也不用来源不足的估计数字替代。",
}

ANSARU_WATCH_ADD = [
    "尼日利亚反恐行动之后是否出现新的高层人事公开信息。",
    "是否出现获权威来源确认的成员规模估计。",
]

# =====================================================================
# 6. Lakurawa — ENRICH_EXISTING
# =====================================================================
LAKURAWA_ENTITY_PATCH = {
    "name_zh": "拉库拉瓦网络",
    "name_en": "Lakurawa",
    "aliases_add": ["Lakurawa Sect", "Lakurawa militants"],
    "importance_level": "L2",
    "current_status": "active_identity_contested",
    "short_description": "身份归属存在争议的跨境武装网络：尼日利亚官方 2025 年 3 月认定其作为 JNIM 的一部分运作，ACLED 2026 年 6 月则评估其为伊斯兰国萨赫勒省边境存在的组成部分。",
    "full_description": "拉库拉瓦网络的组织归属在权威来源之间存在直接冲突。尼日利亚官方制裁机构于 2025 年 3 月认定「拉库拉瓦教派」，并描述其作为 JNIM 的一部分运作，同时列出其在索科托州与凯比州的活动、跨境外籍战斗人员存在、强制征税、招募、绑架勒赎、盗窃牲畜以及建立替代性治理的尝试。另一方面，ACLED 2026 年 6 月《非洲综述》指出，伊斯兰国萨赫勒省正式认领了此前在当地被归于拉库拉瓦的行动，并评估这越来越表明拉库拉瓦是该省边境存在的组成部分，而非一个独立的武装团体。本平台同时保留两种立场，不消除冲突。",
    "confidence": "medium_high",
    "disputed": True,
    "temporal_sensitive": True,
    "source_refs_add": [S_NIGSAC, S_ACLED_JUNE],
    "record_updated_at": TODAY,
    "claim_valid_as_of": TODAY,
    "last_verified_at": TODAY,
    "current_status_verified_at": TODAY,
    "freshness_reviewed_by": IMPORTER,
}

LAKURAWA_PROFILE_TOP = dict(ANSARU_PROFILE_TOP)

LAKURAWA_SECTIONS = {
    "name_and_translation": "本平台以「拉库拉瓦网络」为中文名，英文名 Lakurawa。尼日利亚官方制裁文件使用的名称为「Lakurawa Sect」（拉库拉瓦教派），学术与新闻报道中则常见 Lakurawa militants 一类的复数表述。名称形式上的差异本身即反映出各方对该对象究竟是「组织」还是「标签」存在不同理解。",
    "legal_status": "尼日利亚制裁机构于 2025 年 3 月完成对「拉库拉瓦教派」的认定。该认定文件描述其作为 JNIM 的一部分运作，并列举了在索科托州与凯比州的活动、跨境外籍战斗人员的存在、强制征税、招募、绑架勒赎、盗窃牲畜，以及建立替代性治理的尝试。上述内容属尼日利亚官方立场，本平台按归属于认定辖区的表述保存。",
    "tactics_governance": "根据尼日利亚官方认定文件所列举的行为，该网络的活动方式包含两个层面：一是掠夺性行为，如绑架勒赎与盗窃牲畜；二是准治理行为，如强制征税与建立替代性治理的尝试。第二个层面尤其值得注意，因为它意味着相关武装单元在部分区域并非单纯实施袭击，而是试图取代地方公共权威的部分职能。",
    "geography": "官方认定文件把其活动定位在尼日利亚索科托州与凯比州，并指出存在跨境外籍战斗人员。结合 ACLED 关于边境存在的评估，其地理特征可以概括为：以尼日尔—尼日利亚边境为轴线，活动向尼日利亚西北部各州渗透。",
    "network_links": "本平台在关系层保留两条既有关系并同时标注为存在争议：一条指向伊斯兰国萨赫勒省，一条指向 JNIM。这一处理方式的目的正是保存冲突本身——两条关系分别对应 ACLED 的评估与尼日利亚官方的认定，任何一条被删除都会造成证据面的单方面倾斜。",
    "current_situation": "截至 ACLED 2026 年 6 月资料的时点，证据天平正在向伊斯兰国萨赫勒省方向倾斜：该省对此前被当地归于拉库拉瓦的行动作出了正式认领。但这并不足以支持一个无条件的「分支」判断，因为尼日利亚官方 2025 年 3 月的 JNIM 归属立场并未被撤回或修正。",
    "controversies_uncertainties": {"list": [
        "「拉库拉瓦」可能在部分情形下更接近一个地方性标签，而非边界清晰的正式组织名称。",
        "公开来源在其归属问题上存在直接冲突：尼日利亚官方指向 JNIM，ACLED 指向伊斯兰国萨赫勒省。",
        "当前证据天平越来越倾向伊斯兰国萨赫勒省，但不应据此断言一个无条件的分支关系。",
    ]},
    "uncertainties": {"list": [
        "该名称所指范围是否覆盖统一指挥体系，缺乏可确认的公开依据。",
        "尼日利亚官方立场与 ACLED 评估之间的冲突尚未被任何一方公开调和。",
        "历史事件的组织归属不能被无条件回溯重新划归任一网络。",
    ]},
    "events": {"p": [
        "2025 年之前：拉库拉瓦这一标签已在尼日尔—尼日利亚边境地区被当地广泛使用。",
        "2025 年 3 月：尼日利亚官方制裁机构认定「拉库拉瓦教派」，并描述其作为 JNIM 的一部分运作。",
        "2025—2026 年：指向伊斯兰国萨赫勒省关联的证据逐步增加。",
        "2026 年：伊斯兰国萨赫勒省正式认领此前在当地被归于拉库拉瓦的袭击。",
        "当前 ASIP 评估：证据天平倾向伊斯兰国萨赫勒省，但身份边界仍未解决。",
    ]},
    "gaps": "核心缺口在于「主体识别」：现有材料无法确认被称为拉库拉瓦的各个武装单元是否属于同一指挥体系。在这一问题得到澄清之前，任何单一归属结论都存在过度概括的风险。",
}

LAKURAWA_ASIP = "现有证据越来越倾向其属于或嵌入 ISIS-Sahel 跨境网络，但实体边界及「Lakurawa」名称使用存在明显不确定性。该判断属 ASIP 平台分析，不构成经核实的事实结论；尼日利亚官方 2025 年 3 月关于其作为 JNIM 组成部分运作的认定同时保留在案。"

LAKURAWA_WATCH_ADD = [
    "尼日利亚官方是否修正或重申其 JNIM 归属立场。",
    "ACLED 或其他机构是否发布进一步的归属评估。",
]
