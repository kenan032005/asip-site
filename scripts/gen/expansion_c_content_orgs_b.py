# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-C — historical entities module (part B).

GICM / Al-Battar Brigade / Maitatsine / MUJAO. Same discipline as part A.
"""
from expansion_c_content_orgs_a import entity, profile

TODAY = "2026-08-11"

# ---------------------------------------------------------------------------
# 5. Moroccan Islamic Combatant Group (GICM)
# ---------------------------------------------------------------------------
S_UN_GICM = "expc-un-gicm"
S_UN_LIFG = "expc-un-lifg"
S_STATE_GICM_2002 = "expc-state-gicm-2002"
S_STATE_GICM_2007 = "expc-state-gicm-2007"

ENT_GICM = entity(
    entity_id="actor-gicm",
    slug="gicm",
    name_zh="摩洛哥伊斯兰战斗组织",
    name_en="Moroccan Islamic Combatant Group",
    acronym="GICM",
    primary_type="organization",
    aliases=["Groupe Islamique Combattant Marocain", "GICM", "摩洛哥伊斯兰战斗团"],
    historical_names=[],
    short_description="摩洛哥伊斯兰战斗组织（GICM）于 1990 年代从阿富汗基地组织训练营的摩洛哥招募者中兴起。2002 年因与基地组织关联被联合国列名，美国国务院历史报告称其与基地组织有联系，并指认与 GICM 相关的摩洛哥极端分子涉嫌 2004 年 3 月 11 日马德里袭击。美国国务院 2007 年评估其已解体。",
    full_description="摩洛哥伊斯兰战斗组织（Moroccan Islamic Combatant Group，GICM）于 1990 年代从阿富汗基地组织训练营的摩洛哥招募者（部分曾参战）中兴起。2002 年因与基地组织关联被联合国列名。美国国务院历史报告称其与基地组织有联系，并指认与 GICM 相关的摩洛哥极端分子涉嫌 2004 年 3 月 11 日马德里袭击；联合国利比亚伊斯兰战斗组织（LIFG）叙述称 LIFG 与 GICM 共同参与策划 2003 年 5 月卡萨布兰卡爆炸案（属联合国制裁叙述评估）。美国国务院 2007 年评估 GICM 已解体，残余成员缺乏以整体组织实施袭击的能力。",
    current_status="historical_disintegrated_as_coherent_organization",
    tags=["摩洛哥", "历史网络", "阿富汗一代", "马德里袭击"],
    region_ids=["region-north-africa-sahara"],
    country_ids=[],
    source_refs=[S_UN_GICM, S_UN_LIFG, S_STATE_GICM_2002, S_STATE_GICM_2007],
)

PROF_GICM = profile({
    "lead": "摩洛哥伊斯兰战斗组织（Moroccan Islamic Combatant Group，GICM）于 1990 年代从阿富汗基地组织训练营的摩洛哥招募者中兴起，部分成员曾在阿富汗参战。2002 年因与基地组织关联被联合国列名；美国国务院历史报告称其与基地组织有联系，并指认相关摩洛哥极端分子涉嫌 2004 年 3 月 11 日马德里袭击。美国国务院 2007 年评估该组织已解体。",
    "name_and_translation": "本平台采用中文译名「摩洛哥伊斯兰战斗组织」，英文规范名 Moroccan Islamic Combatant Group，缩写 GICM，法语 Groupe Islamique Combattant Marocain。",
    "formation_background": "GICM 于 1990 年代由阿富汗基地组织训练营的摩洛哥招募者形成，属于「阿富汗一代」北非网络。其形成基础是阿富汗战争期间与之后的圣战训练经历与人员网络。",
    "history": "GICM 的网络在 1990 年代至 2000 年代初运作于摩洛哥与欧洲。2002 年联合国因与基地组织关联将其列名。美国国务院历史报告将 GICM 描述为与基地组织有联系的组织，并指认与 GICM 相关的摩洛哥极端分子涉嫌 2004 年 3 月 11 日马德里袭击。联合国 LIFG 叙述称 LIFG 与 GICM 共同参与策划 2003 年 5 月卡萨布兰卡爆炸案（该描述属联合国制裁叙述评估，保留归属性）。2007 年美国国务院评估 GICM 已解体。",
    "ideology_goals": "GICM 属于摩洛哥伊斯兰主义圣战网络，其成员经历阿富汗训练，意识形态与全球圣战议程相连。本平台不把 GICM 与摩洛哥更广泛的「萨拉菲亚·吉哈迪亚」环境划等号——GICM 是其中被列名的具体组织，环境与组织需区分。",
    "leadership": "公开材料对 GICM 领导层的可靠记载有限；联合国列名材料为主要身份来源。本档案以来源为准，不展开未经记载的领导层细节。",
    "structure": "GICM 兼具组织与跨国网络特征，成员分布于摩洛哥与欧洲；具体编制缺乏系统公开记载，其后期解体状态提示组织控制有限。",
    "geography": "GICM 的网络覆盖摩洛哥（本土）与欧洲（招募、后勤与袭击相关环节）；其跨境运作与 2004 年马德里袭击相关指认体现了这一地理特征。",
    "tactics": "其行动方式以招募、后勤与袭击策划网络为主；马德里与卡萨布兰卡相关指认是主要行动事件（前者来自美国国务院历史报告，后者来自联合国 LIFG 叙述，均保留归属性）。",
    "finance": "GICM 的资金渠道缺乏可引用的系统记载；欧洲与摩洛哥的调查披露的招募与后勤细节仅在来源支撑范围内描述。",
    "legal_status": "GICM 为联合国 1267 制裁机制列名实体；列名法律状态与组织现实解体属独立问题，本档案分开记录。",
    "organizational_relation": "GICM 与基地组织的关系为历史关联：联合国因与基地组织关联将其列名，美国国务院历史报告称其与基地组织有联系。ASIP 以 historically_associated_with 建模（历史关联），保留联合国与国务院的归属性表述。GICM 与 LIFG 的卡萨布兰卡策划关联属联合国 LIFG 叙述评估，本档案仅在文字中保留该归属性陈述，不因 LIFG 无节点而省略。",
    "current_situation": "美国国务院 2007 年评估 GICM 已解体，残余前成员缺乏以连贯组织实施袭击的能力；本档案将其作为历史网络记录，不作为当前活跃组织评估。",
    "regional_impact": "GICM 的历史影响体现为：阿富汗一代摩洛哥网络与欧洲袭击策划之间的联系案例，以及摩洛哥反恐与去激进化叙事中的历史参照。",
    "events": {"list": [
        "1990 年代：从阿富汗基地组织训练营的摩洛哥招募者中兴起。",
        "2002-10：联合国因与基地组织关联列名 GICM。",
        "2003-05：联合国 LIFG 叙述称 LIFG 与 GICM 共同策划卡萨布兰卡爆炸案（归属性陈述）。",
        "2004-03-11：美国国务院历史报告指认与 GICM 相关的摩洛哥极端分子涉嫌马德里袭击。",
        "2007：美国国务院评估 GICM 已解体。",
    ]},
    "uncertainties": {"list": [
        "GICM 在马德里袭击中的具体角色存在归属性限制，非司法定罪。",
        "GICM 与摩洛哥更广泛圣战环境之间的边界不清晰。",
        "组织后期碎片化的具体进程缺乏系统公开记载。",
    ]},
    "gaps": "GICM 完整编制、资金与内部结构缺乏系统来源；本档案以联合国叙述与国务院历史报告为锚。",
    "asip_analysis": "ASIP 判断：GICM 的档案价值是「阿富汗一代网络的历史案例」——它演示了训练营网络如何转化为跨国袭击相关网络，以及其后解体的过程。评估时须守住归属性纪律：马德里指认（国务院）与卡萨布兰卡策划（联合国 LIFG 叙述）均为机构评估而非司法确认；同时不得把 GICM 与摩洛哥整体圣战环境混为一谈。",
    "watch_indicators": [
        "联合国或美国官方对 GICM 列名或历史叙述的更新。",
        "马德里或卡萨布兰卡相关调查的新司法进展（如有）。",
        "涉及 GICM 前成员的公开动态。",
    ],
    "core_assessment": "GICM 是阿富汗一代摩洛哥网络的历史案例，其档案以归属性袭击指认、解体评估与组织/环境区分为核心。",
    "sources": [
        "UN 1267：《Moroccan Islamic Combatant Group — narrative summary》（https://main.un.org/securitycouncil/en/sanctions/1267/aq_sanctions_list/summaries/entity/moroccan-islamic-combatant-group）",
        "UN 1267：《Libyan Islamic Fighting Group — narrative summary》（https://main.un.org/securitycouncil/en/sanctions/1267/aq_sanctions_list/summaries/entity/libyan-islamic-fighting-group）",
        "U.S. State：《Country Reports on Terrorism 2002》（https://2001-2009.state.gov/s/ct/rls/crt/45392.htm）",
        "U.S. State：《Country Reports on Terrorism 2007》（https://2001-2009.state.gov/s/ct/rls/crt/2007/103714.htm）",
    ],
})


# ---------------------------------------------------------------------------
# 6. Al-Battar Brigade (Battar Brigade) — Libya precursor
# ---------------------------------------------------------------------------
S_S2015_891 = "expc-un-s2015-891"
S_CTC = "expc-ctc-battar"

ENT_BATTAR = entity(
    entity_id="actor-al-battar-brigade",
    slug="al-battar-brigade",
    name_zh="巴塔尔旅",
    name_en="Al-Battar Brigade",
    acronym="",
    primary_type="organization",
    aliases=["Battar Brigade", "Katibat al-Battar al-Libi", "al-Battar Brigade", "巴塔尔营"],
    historical_names=[],
    short_description="巴塔尔旅（Al-Battar Brigade）于 2012 年为支援叙利亚和伊拉克的 ISIL 而创建，许多成员于 2014 年春返回利比亚。联合国专家组报告称 ISIL 的巴尔卡省（Wilayat Barqa）是巴塔尔旅与伊斯兰青年协商委员会（IYSC/MSSI）在 ISIS 关联领导层下融合的结果。巴塔尔旅是历史前驱网络，不是当前独立的利比亚 ISIS 分支。",
    full_description="巴塔尔旅（Al-Battar Brigade / Katibat al-Battar al-Libi）于 2012 年创建以支援叙利亚和伊拉克的 ISIL，许多成员于 2014 年春返回利比亚。联合国利比亚专家组（S/2015/891）报告称 ISIL 的巴尔卡省（Wilayat Barqa）是巴塔尔旅与伊斯兰青年协商委员会（IYSC/MSSI）在 ISIS 关联领导层下融合的产物。CTC 研究描述利比亚战斗人员在叙利亚组成 Katibat al-Battar al-Libi，在伊斯兰国与努斯拉阵线分裂后与 ISIS 结盟，后返回利比亚，融入德尔纳武装生态。巴塔尔旅是历史前驱/网络，不是当前独立的利比亚 ISIS 分支。",
    current_status="historical_absorbed_into_isis_libya_precursor_ecosystem",
    tags=["利比亚", "历史网络", "ISIS 前身", "外籍战士"],
    region_ids=["region-north-africa-sahara"],
    country_ids=["country-libya"],
    source_refs=[S_S2015_891, S_CTC],
)

PROF_BATTAR = profile({
    "lead": "巴塔尔旅（Al-Battar Brigade，又称 Katibat al-Battar al-Libi）于 2012 年创建以支援叙利亚和伊拉克的 ISIL，许多成员于 2014 年春返回利比亚。联合国利比亚专家组报告称 ISIL 的巴尔卡省（Wilayat Barqa）是巴塔尔旅与伊斯兰青年协商委员会（IYSC/MSSI）在 ISIS 关联领导层下融合的结果。本档案将巴塔尔旅作为历史前驱网络记录，明确其不是当前独立的利比亚 ISIS 分支。",
    "name_and_translation": "本平台采用中文译名「巴塔尔旅」，英文规范名 Al-Battar Brigade；别名包括 Battar Brigade、Katibat al-Battar al-Libi。",
    "formation_background": "巴塔尔旅于 2012 年为支援叙利亚和伊拉克的 ISIL 而创建，属于利比亚外籍战斗人员在叙利亚内战中的组织化进程。CTC 研究将其置于利比亚战斗人员在叙利亚组成战斗单元、并在伊斯兰国与努斯拉阵线分裂后选择与 ISIS 结盟的脉络中。",
    "history": "巴塔尔旅 2012 年在叙利亚-伊拉克战场形成并支援 ISIL；2014 年春许多成员返回利比亚，融入德尔纳武装生态。联合国专家组报告（S/2015/891）指出 ISIL 的巴尔卡省是巴塔尔旅与 IYSC/MSSI 在 ISIS 关联领导层下融合的结果。返回的战斗人员为利比亚 ISIS 各省分支的涌现提供了人员基础。",
    "ideology_goals": "巴塔尔旅成员在叙利亚期间选择与 ISIS 结盟（在 ISIS 与努斯拉阵线分裂后），其意识形态立场属于全球圣战框架下支持 ISIS 的一翼；具体意识形态细节以来源为准。",
    "leadership": "公开材料对巴塔尔旅领导层的可靠记载有限；其形成与 ISIS 关联领导层的联系由专家组报告确认，具体人名超出本内容包范围。",
    "structure": "巴塔尔旅兼具战斗单元与人员网络特征，其成员在叙利亚与利比亚之间流动；具体编制缺乏系统公开记载。",
    "geography": "巴塔尔旅的地理轨迹为：叙利亚/伊拉克（2012—2014 作战与训练）→ 利比亚（2014 年春起返回）→ 德尔纳武装生态（融合为 ISIS 巴尔卡省的前身要素）。",
    "tactics": "其行动方式以外籍战士参战、返回利比亚后融入当地武装生态为主；具体战术细节仅在来源支撑范围内描述。",
    "finance": "巴塔尔旅的资金与后勤渠道缺乏可引用的系统记载；本档案不展开未经来源支撑的财务细节。",
    "legal_status": "本内容包未提供巴塔尔旅的独立列名条目；其法律状态不作断言。注意：历史网络现实融合进 ISIS 体系，不自动代表其成员的法律状态问题，本档案不展开。",
    "organizational_relation": "巴塔尔旅与 ISIS-利比亚的关系为核心谱系关系：联合国专家组报告称 ISIL 巴尔卡省是巴塔尔旅与 IYSC/MSSI 融合的结果。ASIP 以 constituent_of（历史组成）建模：巴塔尔旅作为 ISIS-利比亚前驱要素之一并入其谱系，关系档案明确其是历史前驱/网络，不是仍保持独立编制的当前组成部分。",
    "current_situation": "巴塔尔旅作为独立网络已被吸收进 ISIS 利比亚前驱生态；其当代意义是解释 ISIS-利比亚巴尔卡省的融合起源，不作为当前独立组织评估。",
    "regional_impact": "巴塔尔旅的历史影响体现为利比亚外籍战士回流与 ISIS 利比亚分支形成的桥梁作用；其对德尔纳武装生态与巴尔卡省形成的影响是理解利比亚 ISIS 谱系的关键。",
    "events": {"list": [
        "2012：巴塔尔旅创建以支援叙利亚和伊拉克的 ISIL。",
        "2012—2014：在叙利亚作战；ISIS 与努斯拉阵线分裂后与 ISIS 结盟（CTC 研究）。",
        "2014 年春：许多成员返回利比亚，融入德尔纳武装生态。",
        "2015-11：联合国利比亚专家组报告（S/2015/891）记载 Wilayat Barqa 为巴塔尔旅与 IYSC/MSSI 融合结果。",
    ]},
    "uncertainties": {"list": [
        "巴塔尔旅返回利比亚的确切人数与组织程度缺乏系统公开统计。",
        "巴塔尔旅与 IYSC/MSSI 融合的具体机制与领导层安排记载有限。",
        "外籍战士轨迹的个体细节缺乏完整公开记录。",
    ]},
    "gaps": "巴塔尔旅完整编制、领导层与资金缺乏系统来源；本档案以联合国专家组报告与 CTC 研究为锚。",
    "asip_analysis": "ASIP 判断：巴塔尔旅的档案价值是「ISIS-利比亚谱系的前驱节点」——它演示了叙利亚外籍战士网络如何回流并融入利比亚 ISIS 分支的融合过程。评估时必须保持时间与实体区分：巴塔尔旅是 2012—2014 年的历史网络，Wilayat Barqa 是其与 IYSC 融合的结果，不是同一组织的简单改名。",
    "watch_indicators": [
        "联合国利比亚专家组关于 ISIS 利比亚谱系的新报告。",
        "涉及巴塔尔旅前成员或相关网络的公开动态。",
        "对利比亚 ISIS 起源的新学术或官方研究。",
    ],
    "core_assessment": "巴塔尔旅是 ISIS-利比亚巴尔卡省的前驱融合要素，其档案以叙利亚—利比亚人员流动与融合机制为核心，明确其历史前驱而非当前分支的定位。",
    "sources": [
        "UN 专家组：《S/2015/891（利比亚）》（https://digitallibrary.un.org/record/812254/files/S_2015_891-EN.pdf）",
        "CTC：《Outlasting the Caliphate: The Evolution of the Islamic State Threat in Africa》（https://ctc.westpoint.edu/outlasting-the-caliphate-the-evolution-of-the-islamic-state-threat-in-africa/）",
    ],
})


# ---------------------------------------------------------------------------
# 7. Maitatsine movement
# ---------------------------------------------------------------------------
S_ADESOJI = "expc-adesoji-maitatsine"
S_ISICHEI = "expc-isichei-maitatsine"
S_HISKETT = "expc-hiskett-maitatsine"
S_LUBECK = "expc-lubeck-tatsine"

ENT_MAITATSINE = entity(
    entity_id="actor-maitatsine-movement",
    slug="maitatsine-movement",
    name_zh="迈塔齐尼运动",
    name_en="Maitatsine movement",
    acronym="",
    primary_type="organization",
    aliases=["Maitatsine", "Yan Tatsine", "'Yan Tatsine", "迈塔齐尼"],
    historical_names=[],
    short_description="迈塔齐尼运动与传教士穆罕默德·马尔瓦（通称迈塔齐尼）相关，1980 年 12 月卡诺发生重大对抗/起义，此后 1980 年代初中期尼日利亚北部又发生多起相关起义（1982、1984、1985 年）。学术界视其为尼日利亚北部宗教好战与城市社会抗议的重要历史事件。学理上常与后来的博科圣地比较，但无充分公开证据证明直接组织传承。",
    full_description="迈塔齐尼运动（Maitatsine movement，又称 Yan Tatsine）与传教士穆罕默德·马尔瓦（通称迈塔齐尼）相关。1980 年 12 月卡诺发生重大对抗/起义，此后 1980 年代初中期尼日利亚北部又发生多起相关起义（1982、1984、1985 年）。学术文献将迈塔齐尼视为尼日利亚北部宗教好战与城市社会抗议的重要历史事件，并经常将其与后来的博科圣地作比较；但不存在充分公开证据证明从迈塔齐尼到博科圣地/JAS 的直接组织传承。本平台不建立两者之间的前身/分裂关系边。",
    current_status="historical_defunct_as_coherent_movement",
    tags=["尼日利亚", "历史运动", "宗教好战", "城市社会抗议"],
    region_ids=["region-lake-chad-basin"],
    country_ids=["country-nigeria"],
    source_refs=[S_ADESOJI, S_ISICHEI, S_HISKETT, S_LUBECK],
)

PROF_MAITATSINE = profile({
    "lead": "迈塔齐尼运动（Maitatsine movement，又称 Yan Tatsine）与传教士穆罕默德·马尔瓦（通称迈塔齐尼）相关。1980 年 12 月卡诺发生重大对抗/起义，此后 1980 年代初中期尼日利亚北部又发生多起相关起义。学术文献将其视为尼日利亚北部宗教好战与城市社会抗议的重要历史事件，并常与后来的博科圣地比较；但不存在充分公开证据证明直接组织传承，本平台不建立谱系边。",
    "name_and_translation": "本平台采用中文译名「迈塔齐尼运动」，英文规范名 Maitatsine movement；别名包括 Maitatsine、Yan Tatsine、'Yan Tatsine。",
    "formation_background": "该运动与传教士穆罕默德·马尔瓦（Mohammed Marwa，通称迈塔齐尼）的宗教教导相关，兴起于尼日利亚北部城市环境，其社会基础与城市下层及经济边缘群体的诉求相连。学术研究将其置于半工业化资本主义下伊斯兰抗议的框架中理解。",
    "history": "1980 年 12 月卡诺发生重大对抗/起义，是运动最突出的历史事件。此后 1980 年代初中期，尼日利亚北部又发生多起与迈塔齐尼相关的起义，包括 1982、1984 与 1985 年的暴力。这些事件的序列构成运动的历史主体。",
    "ideology_goals": "迈塔齐尼的宗教教导具有拒斥现行社会秩序的特征，其动员对象主要是城市边缘群体。学术界对其意识形态的解释包括宗教复兴与社会经济抗议两个维度；本平台不把运动简化为单一性质。",
    "leadership": "穆罕默德·马尔瓦（通称迈塔齐尼）是运动的核心传教士人物；1980 年卡诺对抗后其个人的后续角色以学术叙述为准。",
    "structure": "迈塔齐尼运动的组织形态以传教士为核心的动员网络为主，缺乏正式组织架构的记载；其动员依靠宗教教导与社会经济不满。",
    "geography": "运动的核心地理为尼日利亚北部，尤其是卡诺及其周边城市环境；1980 年代相关起义亦涉及北部其他地点。",
    "tactics": "运动的主要对抗形式为城市起义与暴力对抗；1980 年卡诺事件及后续起义是其行为特征的主要来源。",
    "finance": "迈塔齐尼运动的资源动员以城市社会网络为基础，缺乏可引用的系统财务记载；本档案不展开未经来源支撑的细节。",
    "legal_status": "1980 年代运动受到尼日利亚国家镇压；其法律状态属尼日利亚国内事务，本档案不作国际列名断言。",
    "organizational_relation": "迈塔齐尼运动与博科哈拉姆（JAS）的关系是历史比较，而非组织传承：学术文献常比较两者，但不存在充分公开证据证明从迈塔齐尼到博科哈拉姆的直接组织连续性。ASIP 明确禁止建立 predecessor_of 或 split_from 边；运动与尼日利亚（country-nigeria）的活动关系仅作地理活动记录。",
    "current_situation": "迈塔齐尼运动作为连贯运动已不复存在（defunct as coherent movement）；其当代意义是尼日利亚北部宗教好战与城市社会抗议的历史谱系参照，以及理解后来武装动员的社会经济背景。",
    "regional_impact": "迈塔齐尼的历史影响体现为尼日利亚北部宗教好战史与城市社会抗议史的标志性事件；其社会经济解释框架对理解该地区后来的武装动员仍有分析价值，但不得直接外推为组织谱系。",
    "events": {"list": [
        "1980-12：卡诺重大对抗/起义（运动最突出事件）。",
        "1982：尼日利亚北部相关起义。",
        "1984：尼日利亚北部相关暴力。",
        "1985：尼日利亚北部相关起义。",
    ]},
    "uncertainties": {"list": [
        "运动与后续尼日利亚武装组织（含博科哈拉姆）之间是否存在人员/思想联系，缺乏充分公开证据。",
        "1980 年代各起起义之间的组织关联程度记载不一。",
        "马尔瓦个人教导的完整文本与阐释存在争议。",
    ]},
    "gaps": "运动完整动员结构、资源网络与死亡人数缺乏统一权威统计；学术文献之间存在解释差异。",
    "asip_analysis": "ASIP 判断：迈塔齐尼的档案价值是「历史比较基准」——它用于理解尼日利亚北部宗教好战与社会经济抗议的深层背景，但绝不能写成博科哈拉姆的直接前身。评估时应把「学术比较」与「组织传承」严格区分：比较是分析工具，传承是需要证据的断言，而后者当前缺乏。",
    "watch_indicators": [
        "尼日利亚宗教好战研究的新学术文献。",
        "关于迈塔齐尼与后来武装组织人员/思想联系的任何新证据。",
        "尼日利亚官方或学术界的相关纪念与再研究。",
    ],
    "core_assessment": "迈塔齐尼运动是尼日利亚北部宗教好战与城市社会抗议的历史标志事件，其档案坚持「比较≠传承」的事实纪律，不建立任何指向博科哈拉姆的谱系边。",
    "sources": [
        "Adesoji：《Between Maitatsine and Boko Haram》，Africa Today (2011)（https://www.jstor.org/stable/10.2979/africatoday.57.4.99）",
        "Isichei：《The Maitatsine Risings in Nigeria 1980-85》（https://www.jstor.org/stable/1580874）",
        "Hiskett：《The Maitatsine Riots in Kano, 1980》（https://www.jstor.org/stable/1580875）",
        "Lubeck：《'Yan Tatsine Explained》（https://www.cambridge.org/core/journals/africa/article/islamic-protest-under-semiindustrial-capitalism-yan-tatsine-explained/FCFAE63AFC195178A41EC9292995A839）",
    ],
})


# ---------------------------------------------------------------------------
# 8. MUJAO — Movement for Unity and Jihad in West Africa
# ---------------------------------------------------------------------------
S_UN_MUJAO = "expc-nctc-nwa"      # NCTC north/west africa historical (UN consolidated referenced in pack)
S_NCTC_MURABITUN = "expc-nctc-murabitun"

ENT_MUJAO = entity(
    entity_id="actor-mujao",
    slug="mujao",
    name_zh="西非统一与圣战运动",
    name_en="Movement for Unity and Jihad in West Africa",
    acronym="MUJAO",
    primary_type="organization",
    aliases=["Mouvement pour l'Unification et le Jihad en Afrique de l'Ouest", "MUJAO", "西非统一圣战运动"],
    historical_names=[],
    short_description="西非统一与圣战运动（MUJAO）是萨赫勒/撒哈拉的武装伊斯兰组织，属于马里北部武装伊斯兰主义格局的一部分。联合国将其列为与 AQIM 和穆赫塔尔·贝尔穆赫塔尔相关的组织；NCTC 历史材料称穆拉比通于 2013 年由贝尔穆赫塔尔的 al-Mulathamun 营与另一个 AQIM 分裂派别（通常认定为 MUJAO/西非认主独一与圣战）合并而成。",
    full_description="西非统一与圣战运动（Movement for Unity and Jihad in West Africa，MUJAO）活动于萨赫勒/撒哈拉，是马里北部武装伊斯兰主义格局的一部分。联合国将其列为与 AQIM 和穆赫塔尔·贝尔穆赫塔尔相关的组织。NCTC 历史材料称穆拉比通于 2013 年由贝尔穆赫塔尔的 al-Mulathamun 营与另一个 AQIM 分裂派别（通常认定为 MUJAO/西非认主独一与圣战）合并而成。MUJAO 的核心谱系意义为：AQIM 分裂派 → MUJAO → 穆拉比通 → JNIM 网络。",
    current_status="historical_absorbed_into_murabitun_and_jnim_network",
    tags=["马里", "萨赫勒", "历史组织", "AQIM 分裂"],
    region_ids=["region-central-sahel"],
    country_ids=["country-mali"],
    source_refs=[S_UN_MUJAO, S_NCTC_MURABITUN],
)

PROF_MUJAO = profile({
    "lead": "西非统一与圣战运动（Movement for Unity and Jihad in West Africa，MUJAO）活动于萨赫勒/撒哈拉，是马里北部武装伊斯兰主义格局的一部分。联合国将其列为与 AQIM 和穆赫塔尔·贝尔穆赫塔尔相关的组织；NCTC 历史材料称穆拉比通于 2013 年由贝尔穆赫塔尔的 al-Mulathamun 营与一个 AQIM 分裂派别（通常认定为 MUJAO/西非认主独一与圣战）合并而成。",
    "name_and_translation": "本平台采用中文译名「西非统一与圣战运动」，英文规范名 Movement for Unity and Jihad in West Africa，缩写 MUJAO，法语 Mouvement pour l'Unification et le Jihad en Afrique de l'Ouest。",
    "formation_background": "MUJAO 属于从 AQIM 分裂的萨赫勒武装派别，其形成处于 2010 年代初期马里北部武装伊斯兰主义格局扩张的背景中。NCTC 历史材料将其定位为后来穆拉比通合并的组成部分（与贝尔穆赫塔尔的 al-Mulathamun 营并列）。",
    "history": "MUJAO 在马里北部武装伊斯兰主义格局中运作，参与 2012 年前后马里北部的武装占领与治理相关进程（具体细节以来源为准）。其历史轨迹的高峰是 2013 年前后：NCTC 材料称穆拉比通由 al-Mulathamun 营与 MUJAO/认主独一圣战派别合并形成，MUJAO 作为独立组织身份由此并入。",
    "ideology_goals": "MUJAO 属于全球圣战框架下萨赫勒武装的一翼，与 AQIM 网络相关；其具体意识形态表述以来源为准，本平台不展开未经记载的细节。",
    "leadership": "公开材料将 MUJAO 与穆赫塔尔·贝尔穆赫塔尔（Mokhtar Belmokhtar）相关联（联合国表述）；其独立领导层细节超出本内容包来源范围。",
    "structure": "MUJAO 兼具组织与派别特征，其结构在来源中缺乏完整记载；作为 AQIM 分裂产物，其组织形态与合并后的穆拉比通存在连续性，但本平台不据此推断具体编制。",
    "geography": "MUJAO 活动于萨赫勒/撒哈拉，尤其与马里北部相关；其地理角色是马里北部武装伊斯兰主义格局的一部分。",
    "tactics": "其行动方式属于萨赫勒武装组织的袭击与治理混合形态；具体战术细节仅在来源支撑范围内描述。",
    "finance": "MUJAO 的资金渠道缺乏可引用的系统记载；本档案不展开未经来源支撑的财务细节。",
    "legal_status": "联合国将 MUJAO 列为与 AQIM 和贝尔穆赫塔尔相关的组织（综合制裁参考）；具体列名条目以联合国现行文件为准，本档案保留归属性。",
    "organizational_relation": "MUJAO 的两条核心谱系关系：其一，MUJAO 是从 AQIM 分裂的派别（split_from AQIM）；其二，MUJAO 是穆拉比通 2013 年合并的组成部分（与 al-Mulathamun 营合并，NCTC 表述）。ASIP 以 split_from（AQIM）与 historically_associated_with（穆拉比通，合并语义以档案说明）建模，并在档案中明确合并机制；不为此扩展新的关系类型。",
    "current_situation": "MUJAO 作为独立组织已并入穆拉比通，并经由穆拉比通进入 JNIM 网络体系；其当代意义是萨赫勒 AQIM 谱系（AQIM 分裂 → MUJAO → 穆拉比通 → JNIM）的中间节点。",
    "regional_impact": "MUJAO 的历史影响体现为萨赫勒武装伊斯兰主义格局的碎片化与再组合过程；其谱系位置是理解马里北部武装网络连续性的关键。",
    "events": {"list": [
        "2010 年代初期：作为 AQIM 分裂派别在马里北部格局中运作。",
        "2012 年前后：参与马里北部武装格局相关进程。",
        "2013：NCTC 材料称穆拉比通由 al-Mulathamun 营与 MUJAO/认主独一圣战派别合并形成。",
        "此后：作为独立组织身份并入穆拉比通→JNIM 网络谱系。",
    ]},
    "uncertainties": {"list": [
        "MUJAO 与贝尔穆赫塔尔网络之间的组织边界存在模糊性（联合国归属性表述）。",
        "MUJAO 与认主独一圣战派别之间的确切关系存在来源差异。",
        "合并进程的细节与时间线缺乏统一权威记载。",
    ]},
    "gaps": "MUJAO 完整编制、领导层与资金缺乏系统来源；本档案以 NCTC 历史材料与联合国归属性表述为锚。",
    "asip_analysis": "ASIP 判断：MUJAO 的档案价值是「谱系中间节点」——它把 AQIM 的分裂与穆拉比通的合并连接起来。评估时应避免把「与贝尔穆赫塔尔相关」（联合国表述）简化为对 MUJAO 独立结构的确定描述，并明确 MUJAO 的当代意义在于谱系而非当前行动。",
    "watch_indicators": [
        "NCTC 或联合国对 MUJAO 历史叙述的更新。",
        "穆拉比通/JNIM 体系内与 MUJAO 谱系相关的领导层变动。",
        "对马里北部武装网络谱系的新学术或官方研究。",
    ],
    "core_assessment": "MUJAO 是萨赫勒 AQIM 谱系的中间节点，其档案以分裂与合并的谱系机制为核心，明确其并入穆拉比通→JNIM 网络的历史定位。",
    "sources": [
        "NCTC：《Terrorist Groups — North and West Africa (historical)》（https://www.dni.gov/nctc/groups/north_and_west_africa.html）",
        "NCTC：《Al-Murabitun》（2026）（https://www.dni.gov/nctc/terrorist_groups/al_murabitun.html）",
        "UN 综合制裁参考（https://scsanctions.un.org/consolidated）",
    ],
})

ORG_ENTITIES_B = [ENT_GICM, ENT_BATTAR, ENT_MAITATSINE, ENT_MUJAO]
ORG_PROFILES_B = {
    "actor-gicm": PROF_GICM,
    "actor-al-battar-brigade": PROF_BATTAR,
    "actor-maitatsine-movement": PROF_MAITATSINE,
    "actor-mujao": PROF_MUJAO,
}
