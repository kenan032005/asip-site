# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-D — entity content module (new + enrich).

Source of truth: ASIP-PPT-ENTITY-EXPANSION-D-Authoritative-Content-Pack.md.
No independent research; classification judgments are locked by the pack.
"""

TODAY = "2026-08-14"
IMPORTER = "expansion-d"

# ---------------------------------------------------------------------------
# 1. NEW canonical entities
# ---------------------------------------------------------------------------

def _ent(eid, slug, zh, en, acronym, primary_type, importance, status, short, full,
         aliases=(), historical=(), primary_category="", region_ids=(), country_ids=(),
         source_refs=(), temporal=True, secondary=()):
    return {
        "entity_id": eid, "entity_type": "organization", "slug": slug,
        "name_zh": zh, "name_en": en, "acronym": acronym, "native_name": "",
        "aliases": list(aliases), "historical_names": list(historical),
        "importance_level": importance, "short_description": short, "full_description": full,
        "current_status": status, "primary_category": primary_category, "tags": [],
        "profile_level": importance, "source_refs": list(source_refs),
        "last_verified_at": TODAY, "confidence": "high",
        "temporal_sensitive": temporal, "disputed": False,
        "primary_type": primary_type, "secondary_types": list(secondary),
        "importance_score": None, "importance_reasons": [], "importance_reviewed_at": TODAY,
        "importance_review_status": "migrated", "evidence_ids": [],
        "region_ids": list(region_ids), "country_ids": list(country_ids),
        "record_created_at": TODAY, "record_updated_at": TODAY, "record_reviewed_at": TODAY,
        "claim_valid_as_of": TODAY, "freshness_status": "current",
        "verification_status": "pending_review", "current_status_verified_at": TODAY,
        "freshness_reviewed_by": IMPORTER,
    }


def _prof(sections, importance="L2", completeness="Expansion D 内容包深度审计 · 百科式"):
    return {
        "profile_depth": "encyclopedia_full", "profile_level": "encyclopedia_full",
        "content_maturity": "E3_FULL_ENCYCLOPEDIA", "completeness": completeness,
        "importance_level": importance, "sections": sections,
    }


ORG_ENTITIES = [
    _ent(
        "actor-isis-sinai", "isis-sinai", "伊斯兰国西奈省", "ISIS-Sinai Province", "ISIS-SP",
        "terrorist_group", "L2", "active_but_severely_degraded",
        "伊斯兰国（ISIS）的西奈半岛分支，前身为“耶路撒冷支持者”（Ansar Bayt al-Maqdis，ABM），2014年11月宣誓效忠ISIS后改称西奈省；自2022年起明显削弱，至2025年NCTC仍将其列为ISIS分支但判定为严重退化。",
        "ISIS-Sinai 是理解 ISIS 全球分支体系中北非—西奈方向的关键节点，也是“ABM 历史阶段→ISIS 分支”组织连续性的典型样本。建模纪律：ABM 是 ISIS-Sinai 2014 年 11 月宣誓效忠前历史阶段的名称，不得另建当前 ABM 节点；当前状态不得简单写为 defunct，应体现“组织/法律存在与行动节奏、当前威胁”三层区分。",
        aliases=["Islamic State-Sinai Province", "ISIL Sinai Province", "Sinai Province", "Wilayat Sinai",
                 "Wilayat Sayna", "Islamic State in the Sinai", "State of Sinai", "Ansar Bayt al-Maqdis",
                 "Ansar Beit al-Maqdis", "Ansar Jerusalem", "Supporters of Jerusalem",
                 "Jamaat Ansar Beit al-Maqdis fi Sinaa"],
        historical=["Ansar Bayt al-Maqdis", "Ansar Beit al-Maqdis"],
        primary_category="isis_sinai_province_branch",
        region_ids=["region-north-africa-sahara"], country_ids=[],
        source_refs=["expd-nctc-isis-sinai", "us-state-crt-2022", "expd-ofac-2015-09-29", "expd-dfat-egypt"],
        secondary=["terrorist_organization"],
    ),
    _ent(
        "actor-niger-fpl", "niger-fpl", "尼日尔爱国解放阵线", "Front Patriotique de Libération", "FPL",
        "insurgent_group", "L2", "active_anti_junta_rebellion",
        "2023年8月尼日尔政变后成立的图布族反军政府武装，要求释放被推翻总统穆罕默德·巴祖姆并恢复宪政秩序；2024年6月宣称袭击中资支持的尼日尔—贝宁输油管道。分类纪律：反军政府叛乱，而非圣战/恐怖组织。",
        "FPL 是本轮 Expansion D 的“强制纠偏”对象之一：其针对输油管道与军警目标的做法是反政府叛乱的战术/目标集，不得据此将其归入圣战体系。FPL 为政治-武装叛乱组织（anti-junta rebel group），领导人 Mahamoud/Mahmoud Sallah 于利比亚被哈夫塔尔阵营拘押、2026年6月获释，但该事件不构成亲/反哈夫塔尔的永久结盟。",
        aliases=["Front Patriotique de Liberation", "Patriotic Liberation Front"],
        historical=[],
        primary_category="anti_junta_rebel_group",
        region_ids=["region-central-sahel"], country_ids=["country-niger"],
        source_refs=["expd-reuters-niger-pipeline", "expd-hrw-niger-2025", "expd-worldbank-niger-2026", "expd-ahram-fpl"],
        secondary=["political_armed_rebellion", "rebel_group"],
    ),
]

ORG_PROFILES = {
    # ============================================================ ISIS-Sinai
    "actor-isis-sinai": _prof({
        "lead": "伊斯兰国西奈省（ISIS-Sinai Province）是伊斯兰国在北非西奈半岛的分支，前身为 2011 年埃及动荡后出现的“耶路撒冷支持者”（Ansar Bayt al-Maqdis，ABM）。2014 年 11 月 ABM 正式宣誓效忠 ISIS 并成为其西奈省，此后以对埃及安全部队、以以色列相关目标及当地亲政府部落领导人为主要袭击对象。2014—2022 年间据美国国家反恐中心（NCTC）统计实施了超过 500 次袭击；自 2022 年起进入明显衰退，2023 年 2 月是其截至 2025 年 5 月可考的最后一次公开宣称的恐怖袭击。",
        "name_and_translation": "中文名称为“伊斯兰国西奈省”，英文名称为 ISIS-Sinai Province，缩写 ISIS-SP。历史名称包括“耶路撒冷支持者”（Ansar Bayt al-Maqdis / Ansar Beit al-Maqdis）及其阿拉伯语变体（Jamaat Ansar Beit al-Maqdis fi Sinaa）。美国指定实践中将 ABM 与 ISIS-Sinai 视为同一组织连续体，仅以修正后的别名形式并存。",
        "background": "ABM 于 2011 年埃及“阿拉伯之春”动荡后出现，利用了西奈半岛中央政权威望下降、边境地带治理真空与贝都因部落长期边缘化的环境。其早期袭击目标同时指向以色列相关利益与埃及军警目标，呈现“反以 + 反埃及当局”的双重目标结构。",
        "history": [
            "2011：ABM 在埃及动荡后出现。",
            "2012—2014：ABM 声称对以色列与埃及相关目标发动袭击。",
            "2014-11：ABM 正式宣誓效忠 ISIS，成为其西奈省。",
            "2015：美国将指定修正为纳入 ISIL / 伊斯兰国西奈省别名。",
            "2014—2022：据 NCTC 统计实施超过 500 次西奈袭击，主要针对埃及安全部队与亲政府部落领导人。",
            "2022 起：分支进入明显衰退期。",
            "2023-02：据 NCTC（截至 2025-05）为最后一次公开宣称的恐怖袭击。",
            "2025：NCTC 仍将 ISIS-Sinai 视为 ISIS 分支，但判定为严重退化。",
        ],
        "genealogy": "组织谱系为 ABM（2011—2014）→ 宣誓效忠 ISIS（2014-11）→ ISIS-Sinai（2014 至今）。这一连续体是 ISIS 全球分支形成模式的典型样本：本地化暴力的既有组织通过宣誓效忠并入 ISIS 品牌体系。",
        "leadership": "公开来源对 ISIS-Sinai 历任领导层的系统性披露有限。2010 年代中期的多名高级指挥者在埃及反恐行动中被击毙或被捕，埃及的定点清除与逮捕行动持续削弱其指挥链。鉴于信息不足，本档案不对具体现任领导层作逐人推断。",
        "ideology_goals": "作为 ISIS 分支，奉行 ISIS 的极端意识形态，主张在包括西奈在内的领土建立其所谓“哈里发”治理，敌视埃及国家、当地部落权威及以色列。",
        "geography": "主要活动于埃及西奈半岛，尤其北西奈省（拉法赫、谢赫祖韦德、阿里什周边）的边境地带；历史上一度利用与加沙的边境通道进行人员与物资流动。",
        "tactics": "早期广泛使用爆炸装置（IED/汽车炸弹）、伏击、定点枪击与绑架；2015 年击落俄航 9268 航班事件是其在外部造成的最高知名度袭击。对埃及军警哨所、车队、检查站及亲政府部落领导人的定点暗杀是主要行动类型。",
        "operations": "2014—2022 年超过 500 次袭击构成其行动高峰期；2015 年俄航 9268 航班爆炸、2017 年苏菲清真寺大规模袭击等是其标志性事件。2023 年 2 月后公开宣称的袭击节奏大幅下降。",
        "governance_intimidation": "在其控制较强时期，通过暗杀亲政府部落领袖、恐吓告密者、勒索与非法设卡建立地方威慑；但从未在西奈建立稳定的类政权治理。",
        "finance_logistics": "早期依赖走私网络（香烟、毒品、武器）与绑架勒索获取资金，并利用西奈—加沙边境通道补充物资；埃及的边境封锁与军事清剿显著压缩了其物流与资金来源。",
        "current_situation": "自 2022 年起，埃及的持续反恐行动——包括逮捕、击毙、招降与大赦/投降计划——严重削弱了 ISIS-Sinai 的行动能力。至 2025 年，NCTC 仍将其列为 ISIS 分支，但判定为“严重退化”，公开宣称的袭击节奏极低。应区分三层：组织/法律存在、行动节奏、当前领土/安全威胁——三者均已下降，但组织身份尚未被正式撤销。",
        "legal_status": "ABM/ISIS-Sinai 自 2014 年起被美国国务院指定为外国恐怖组织；2015 年 9 月 OFAC 修正指定，纳入 ISIL 西奈省等别名；联合国安理会 ISIS/基地组织制裁委员会亦将 ISIS-Sinai 作为 ISIS 分支列入制裁名单。",
        "major_timeline": [
            "2011：ABM 在埃及动荡后出现。",
            "2014-11：ABM 正式宣誓效忠 ISIS，成为西奈省。",
            "2015：美国指定修正，纳入 ISIL / 伊斯兰国西奈省别名。",
            "2014—2022：据 NCTC 统计实施超过 500 次袭击。",
            "2022 起：进入明显衰退期。",
            "2023-02：据 NCTC（截至 2025-05）为最后一次公开宣称恐怖袭击。",
            "2025-05：NCTC 仍列为 ISIS 分支但判定严重退化。",
        ],
        "controversies_uncertainties": "ABM 与 ISIS-Sinai 的精确组织连续性存在学术与情报口径差异；部分分析将二者视为“ABM 主体 + 效忠后更名”，另有观点认为效忠 ISIS 时伴随派别分裂。领导层与现役人数缺乏可靠公开统计。",
        "asip_analysis": "ASIP 判断：ISIS-Sinai 是“本地暴力组织通过宣誓效忠并入 ISIS 品牌”的典型样本。评估时必须把三条线分开——组织/法律存在、行动节奏、当前威胁——避免把“严重退化”简单写成“defunct”。其对埃及的直接威胁已大幅下降，但其作为 ISIS 分支的身份延续仍具有象征与网络意义，需持续纳入观察。",
        "watch_indicators": [
            "是否出现新的公开宣称袭击或 ISIS 宣传重新启用西奈省名号",
            "埃及反恐行动与部落亲政府力量的公开动态",
            "NCTC / 美国 / 联合国对 ISIS-Sinai 指定或表述的更新",
            "西奈—加沙边境通道的跨境活动迹象",
        ],
        "sources": [
            "NCTC: ISIS-Sinai (as of May 2025) — https://www.dni.gov/nctc/terrorist_groups/isis_sinai.html",
            "U.S. State Dept Country Reports on Terrorism 2022 — https://www.state.gov/reports/country-reports-on-terrorism-2022/",
            "OFAC amendment 2015-09-29 — https://ofac.treasury.gov/recent-actions/20150929",
            "DFAT Egypt — https://www.ecoi.net/en/document/2141293.html",
        ],
    }, importance="L2"),

    # ============================================================ FPL
    "actor-niger-fpl": _prof({
        "lead": "尼日尔爱国解放阵线（Front Patriotique de Libération，FPL）是 2023 年 7 月尼日尔政变后、于 2023 年 8 月成立的反军政府武装运动，领导人 Mahamoud（Mahmoud）Sallah。其核心诉求是释放被推翻总统穆罕默德·巴祖姆并恢复宪政秩序。FPL 于 2024 年 6 月宣称袭击中资支持的尼日尔—贝宁输油管道并威胁继续袭击，被 HRW 描述为图布族反政府武装。",
        "name_and_translation": "中文名称为“尼日尔爱国解放阵线”，英文名称 Front Patriotique de Libération，缩写 FPL，别名 Patriotic Liberation Front。",
        "background": "FPL 形成于 2023 年 7 月尼日尔军政府政变推翻民选总统巴祖姆之后的反对派政治-武装背景。其人员基础与图布族社群相关，并嵌入尼日尔东部/东北部长期存在的边缘化与叛乱传统。",
        "formation_background": "2023 年 7 月政变推翻巴祖姆；2023 年 8 月 FPL 成立，公开要求释放巴祖姆并恢复宪政秩序，成为反军政府阵营中的武装力量。",
        "history": [
            "2023-07：尼日尔政变推翻总统巴祖姆。",
            "2023-08：FPL 成立，要求释放巴祖姆、恢复宪政秩序。",
            "2024-06：FPL 宣称袭击中资支持的尼日尔—贝宁输油管道并威胁继续袭击。",
            "2024—2026：与军政府武装力量及基础设施目标持续冲突。",
            "2026-06：领导人 Mahamoud Sallah 在利比亚被哈夫塔尔阵营拘押后获释。",
        ],
        "leadership": "领导人 Mahamoud（Mahmoud）Sallah。2026 年其在利比亚被哈夫塔尔阵营力量拘押、同年 6 月获释；该事件不构成 FPL 与任何利比亚阵营的永久结盟判断。鉴于信息有限，不为其单独建立人物节点。",
        "ideology_goals": "核心政治诉求是推翻政变的非法性：释放巴祖姆总统、恢复 2023 年政变前的宪政秩序。其意识形态属反军政府的政治-武装反抗，而非宗教极端主义。",
        "political_character": "FPL 是反军政府叛乱组织（anti-junta rebel group），以政治诉求为核心，通过武装手段施压。其与图布族社群、尼日尔东部反对派力量存在联系，但不属于圣战或恐怖主义体系。",
        "geography": "活动集中于尼日尔，尤其东部/东北部与管道沿线地区；其人员基础与图布族社群相关，活动范围与尼日尔—贝宁输油管道走廊重叠。",
        "tactics": "采用对军事力量与关键基础设施的袭击，尤其是对中资支持的尼日尔—贝宁输油管道的破坏性袭击；HRW 描述其宣称至少两次袭击该管道。目标是制造对军政府的经济与安全压力，而非针对平民的大规模恐怖袭击。",
        "operations": "2024 年 6 月 16 日对输油管道的袭击是其公开宣称的最知名行动；此后对军警与基础设施目标持续施压。",
        "external_relations": "与利比亚存在非结盟性接触：领导人 Sallah 曾于利比亚被哈夫塔尔阵营拘押、2026 年 6 月获释。该事件不构成亲/反哈夫塔尔的永久结盟判断。与邻国图布族叛乱网络存在族群性关联。",
        "current_situation": "截至 2026 年，FPL 作为反军政府武装保持活跃，通过袭击基础设施与军警目标持续施压尼日尔军政府，核心诉求仍为释放巴祖姆并恢复宪政秩序。",
        "classification_controversy": "FPL 常因“袭击中资输油管道”而被部分语境误读为恐怖或圣战组织。这是分类争议的核心：袭击中资支持的基础设施是其战术/目标集选择，源于反军政府的经济施压逻辑，不得据此推断其属于圣战体系。FPL 应归类为反军政府武装叛乱，而非恐怖组织。",
        "uncertainties": "FPL 的规模、指挥结构、资金与外部支持关系缺乏系统公开披露；其与图布族其他叛乱力量及利比亚各方的关系边界存在不确定性。",
        "asip_analysis": "ASIP 判断：FPL 是尼日尔政变后政治裂痕武装化的产物，本质是反军政府政治-武装反抗。对中资管道等基础设施的袭击是“高可见度、高经济成本”的施压战术，不应被安全化叙事扭曲为恐怖主义归类。评估其风险时应聚焦其对基础设施、能源走廊与尼日尔—贝宁关系的实际影响，而非宗教极端主义标签。",
        "watch_indicators": [
            "FPL 是否继续袭击输油管道或军警目标",
            "巴祖姆释放与宪政秩序的谈判进展",
            "Mahamoud Sallah 获释后的公开表态与组织动向",
            "图布族叛乱网络与利比亚各方的公开动态",
        ],
        "sources": [
            "Reuters: Niger group claims attack on China-backed pipeline (2024-06-18) — https://www.reuters.com/world/africa/niger-group-claims-attack-china-backed-pipeline-threatens-more-2024-06-18/",
            "HRW World Report 2025 — Niger — https://www.hrw.org/world-report/2025/country-chapters/niger",
            "World Bank Niger Country Context (2026) — https://documents1.worldbank.org/curated/en/099042125174519328/pdf/P507762-11823c7e-3802-4550-a6b8-3b32963b85eb.pdf",
            "AFP/Ahram (French) — https://french.ahram.org.eg/UI/Front/Inner.aspx?NewsContentID=89988",
        ],
    }, importance="L2"),
}

# ---------------------------------------------------------------------------
# 2. ENRICH patches (existing entities → encyclopedia_full alignment)
# ---------------------------------------------------------------------------

ENRICH_PATCHES = [
    # ---- Ansaroul Islam (E2 → E3 encyclopedia_full)
    {
        "entity_id": "actor-ansarul-islam",
        "add_aliases": ["Ansarul Islam", "Ansar al-Islam (Burkina Faso)", "Defenders of Islam"],
        "add_historical_names": [],
        "source_refs_add": ["expd-mapping-ansaroul-islam", "expd-ctc-ansaroul-islam", "expd-oecd-networks", "d2-hrw-burkina-2026-04-02"],
        "set_fields": {
            "current_status": "integrated_jnim_constituent_retaining_local_identity",
        },
        "sections": {
            "lead": "安萨鲁伊斯兰（Ansaroul Islam / Ansarul Islam）是 2016 年末由布基纳法索苏姆省宣教士 Malam Ibrahim Dicko（Boureima Dicko）创立的圣战武装，2016 年 12 月对纳苏姆布（Nassoumbou）军警营地的袭击是其首次重大公开行动。组织根植于当地 Al-Irchad 宗教网络，并深受马里边境冲突塑造。Ibrahim Dicko 2017 年去世后由其弟 Jafar Dicko 继任。至 2026 年，安萨鲁伊斯兰已被 JNIM 高度整合，是 JNIM 在布基纳法索扩张的重要组成单元，但仍在一定程度上保留本地身份。",
            "name_and_translation": "中文名称为“安萨鲁伊斯兰”，英文名称 Ansaroul Islam（亦写作 Ansarul Islam、Ansar al-Islam，义为“伊斯兰的捍卫者/支持者”）。核心语义：JNIM 整合的布基纳法索圣战组成单元，而非与 JNIM 平行的独立当前组织。",
            "background": "根植于苏姆（Soum）省的 Al-Irchad 宗教传播网络，与当地治理薄弱、地方权威虚位和社会矛盾相关；2012 年马里北部冲突及其外溢深刻塑造了其形成环境。",
            "formation_background": "2016 年末由宣教士 Malam Ibrahim Dicko 创立；2016 年 12 月对纳苏姆布军警营地发动首次重大袭击，标志其公开武装化。",
            "history": [
                "2016 年末：Ibrahim Dicko 创立，源自苏姆省 Al-Irchad 网络。",
                "2016-12：袭击纳苏姆布军警营地，首次重大公开行动。",
                "2017：Ibrahim Dicko 去世，其弟 Jafar Dicko 继任。",
                "2019—2020：少数成员据报转向 ISGS/IS Sahel（派别级流动，非整组转化）。",
                "2020—2021 前后：逐步被 JNIM 吸收。",
                "2026：HRW 描述其为 JNIM 在布基纳法索扩张所依托的武装组织之一，与 Katiba Hanifa 均已并入 JNIM 并在一定程度上保留自身身份。",
            ],
            "leadership": "创始人 Malam Ibrahim Dicko（Boureima Dicko，2017 年去世）；其弟 Jafar Dicko 继任；Ousmane 为副手级人物。相关人物已在库中作为 person 节点存在（person-ibrahim-malam-dicko、person-jafar-dicko、person-ousmane-dicko）。",
            "ideology_goals": "圣战意识形态武装，早期以反布基纳法索政府与反西方/反安全力量为诉求；与 JNIM 及基地组织谱系相关，非 ISIS 谱系。",
            "geography": "活动于布基纳法索北部与西部地区，尤其是苏姆省及邻近地带；在马里边境冲突外溢背景下形成跨边境活动能力。",
            "jnim_integration": "从早期即与 Katiba Macina / JNIM 前身存在合作；2020—2021 前后逐步被 JNIM 吸收，2025 年公开视频使用 JNIM 媒体品牌。整合是渐进式的，而非单一日期的一次性合并。",
            "external_relations": "与 Katiba Macina / JNIM 前身存在历史性行动/训练/网络关联（历史关联关系）。与 IS Sahel 仅有历史性/流动性的少数成员叛变接触（2019—2020 年少数成员转投 ISGS/IS Sahel），严禁把整个组织建模为 ISIS/IS Sahel 组成单元。",
            "current_situation": "作为 JNIM 高度整合但保留地方身份的组成单元运作；HRW 2026 年确认其与 Katiba Hanifa 均已并入 JNIM 并在一定程度上保留自身身份。",
            "core_assessment": "安萨鲁伊斯兰在布基纳法索圣战叛乱早期具有关键作用；当前应建模为 JNIM 整合的布基纳法索组成/附属单元并保留本地身份，而非独立平级组织、ISIS 分支或富拉尼族民族组织。",
            "controversies_uncertainties": "并入 JNIM 后其名称作为独立组织标签的持续使用程度缺乏统一公开口径；2019—2020 年转向 ISGS/IS Sahel 的少数成员规模缺乏系统统计。",
            "asip_analysis": "ASIP 判断：安萨鲁伊斯兰是 JNIM 吸收地方叛乱品牌、而非简单取消其身份的扩张模式的典型体现。必须守住两条纪律——整组是 JNIM 组成单元（非 ISIS/IS Sahel）；与 IS Sahel 仅有少数成员的派别级流动。其“保留本地身份”是 JNIM 在布基纳法索扩张的治理手段。",
            "watch_indicators": [
                "JNIM 对安萨鲁伊斯兰品牌的公开使用与人事变动",
                "是否出现向 IS Sahel 的新的成员流动",
                "HRW / 学术来源对布基纳法索武装组织格局的新表述",
            ],
            "sources": [
                "HRW April 2026: “None Can Run Away” — https://www.hrw.org/report/2026/04/02/none-can-run-away/war-crimes-and-crimes-against-humanity-in-burkina-faso-by-all",
                "Mapping Militants: Ansaroul Islam — https://mappingmilitants.org/profiles/ansaroul-islam",
                "CTC West Point: Ansaroul Islam — https://ctc.westpoint.edu/ansaroul-islam-growing-terrorist-insurgency-burkina-faso/",
                "OECD: Conflict Networks in North and West Africa — https://www.oecd.org/en/publications/conflict-networks-in-north-and-west-africa_896e3eca-en/full-report/networks-of-violence-in-north-and-west-africa_be95f83d.html",
            ],
        },
    },

    # ---- Katiba Hanifa (already E3; align status + add facts/sections)
    {
        "entity_id": "actor-katiba-hanifa",
        "add_aliases": ["Hanifa Brigade", "Katibat Hanifa"],
        "add_historical_names": [],
        "source_refs_add": ["expd-africa-center-tactical-units", "expd-critical-threats-benin", "d2-hrw-burkina-2026-04-02", "d2-africa-center-benin-2026"],
        "set_fields": {
            "current_status": "active_and_expanding_cross_border",
        },
        "sections": {
            "lead": "哈尼法旅（Katiba Hanifa，别名 Hanifa Brigade / Katibat Hanifa）是 JNIM 的一支组成/子单元，活跃于布基纳法索东南部—尼日尔西部—贝宁北部/多哥边境的 W-Arly-Pendjari 跨境前沿地带。HRW 2026 年 4 月指出其由 Abou Hanifa（亦称 Oumarou）领导，并确认 Katiba Hanifa 与安萨鲁伊斯兰均已并入 JNIM 且在某种程度上保留自身身份。Katiba Hanifa 不得与安萨鲁伊斯兰等同。",
            "name_and_translation": "中文名称为“哈尼法旅”，英文名称 Katiba Hanifa（亦写作 Katibat Hanifa），别名 Hanifa Brigade。核心语义：JNIM 子单元，非独立组织，更非安萨鲁伊斯兰的别名。",
            "formation_background": "作为 JNIM 的一支战术子单元形成，嵌入布基纳法索东南部—尼日尔西部—贝宁北部的三国/四国交界跨境地带，是 JNIM 向几内亚湾沿岸扩张的尖兵。",
            "history": [
                "2020 年代早期：作为 JNIM 子单元在布基纳法索东南部活动。",
                "2024—2025：沿贝宁、尼日利亚前沿扩张，使用 IED、袭击基础设施与安全部队。",
                "2025-10：据非洲研究中心，其在尼日利亚境内首次被承认的行动。",
                "2026-04：HRW 确认由 Abou Hanifa/Oumarou 领导，已并入 JNIM 并保留身份。",
            ],
            "leadership": "由 Abou Hanifa（亦称 Oumarou）领导（库中 person-abu-hanifa 节点）；领导层归属以 HRW 2026 年 4 月报告为依据。",
            "ideology_goals": "作为 JNIM 子单元，奉行 JNIM 的圣战意识形态，推进 JNIM 向沿海西非（贝宁、多哥、尼日利亚）的跨境扩张。",
            "geography": "以布基纳法索东南部为重心，向西覆盖尼日尔西部、向南覆盖贝宁北部与 W-Arly-Pendjari 边境地带，并据报触及多哥边境与尼日利亚前沿。",
            "tactics": "广泛使用简易爆炸装置（IED），袭击基础设施与安全部队目标；利用 W-Arly-Pendjari 跨境自然保护区的边境走廊进行机动与渗透。",
            "operations": "2025 年 10 月据非洲研究中心为其在尼日利亚境内首次被承认的行动；此前已在贝宁北部与尼日尔西部实施多起袭击。",
            "external_relations": "与 JNIM 为组成关系（constituent_of）；与安萨鲁伊斯兰同为 JNIM 布基纳法索体系的组成单元但彼此独立、不得等同。",
            "current_situation": "活跃且跨境扩张中，是 JNIM 向贝宁、多哥、尼日利亚沿海方向扩张的前沿子单元。",
            "asip_analysis": "ASIP 判断：Katiba Hanifa 是 JNIM 向几内亚湾沿岸（贝宁—多哥—尼日利亚）扩张的最前沿战术单元，其 IED 与基础设施袭击标志 JNIM 沿海扩张的战术升级。必须与安萨鲁伊斯兰严格区分——二者是 JNIM 体系内不同的组成单元。",
            "uncertainties": "其人员规模、与 JNIM 指挥链的具体关系、以及“首次尼日利亚境内行动”是否为持续性的营地级存在，缺乏系统公开披露。",
            "watch_indicators": [
                "是否在尼日利亚/多哥境内出现新的被承认行动",
                "JNIM 对 Katiba Hanifa 的公开表述与领导层变动",
                "贝宁/多哥/尼日利亚对 W-Arly-Pendjari 走廊的反恐行动",
            ],
            "sources": [
                "HRW April 2026: “None Can Run Away” — https://www.hrw.org/report/2026/04/02/none-can-run-away/war-crimes-and-crimes-against-humanity-in-burkina-faso-by-all",
                "Africa Center Feb 2026: Tactical Units in West Africa — https://africacenter.org/wp-content/uploads/2026/02/ASB47EN-Tactical-Units-West-Africa.pdf",
                "Africa Center: Benin — https://africacenter.org/publication/asb46en-benin-battle-militant-groups/",
                "Critical Threats April 2025 — https://www.criticalthreats.org/analysis/africa-file-april-24-2025-jnims-growing-pressure-on-benin-turkey-to-somalia-salafi-jihadi-cells-continue-to-grow-across-nigeria",
            ],
        },
    },

    # ---- FLA (already E3; align classification + tactical-coordination framing)
    {
        "entity_id": "actor-fla",
        "add_aliases": [],
        "add_historical_names": [],
        "source_refs_add": ["deptha-reuters-mali-groups-2026-04-27", "expd-reuters-goita-2026-04-28", "expd-ap-mali-2026", "expd-bti-mali-2026"],
        "set_fields": {
            "primary_type": "political_movement",
            "current_status": "active_azawad_politico_military_front",
        },
        "sections": {
            "lead": "阿扎瓦德解放阵线（Azawad Liberation Front，FLA）是 2024 年 11 月正式形成/重组的图阿雷格主导分离主义-政治军事联盟，源于早期阿扎瓦德分离主义谱系与 CSP-DPA 框架的解体/重组。FLA 追求阿扎瓦德自决/独立，与 JNIM 的政治与意识形态目标截然不同；2026 年 4 月起与 JNIM 在对马里军政府协同攻击中呈现战术性战场协调。分类纪律：分离主义/政治-军事行为体，严禁归类为恐怖组织、圣战组织、JNIM 附属或宣誓效忠。",
            "political_character": "FLA 是分离主义/政治-军事行为体（separatist_rebel_coalition / politico_military_actor），追求阿扎瓦德自决/独立，以图阿雷格政治传统与 2015 年和平框架的破裂为背景。",
            "ideology_goals": "核心目标是阿扎瓦德自决/独立，与 JNIM 的基地组织关联圣战治理诉求根本不同；其对马里军事政府的武装对抗源于政治分离主义，而非宗教极端主义。",
            "jnim_relation": "2026 年 4 月起与 JNIM 出现战术性战场协同（针对共同敌人的临时合作）。二者政治/意识形态目标不同：FLA 求自决/独立，JNIM 求伊斯兰治理。该关系是行动层战术协调，绝非 affiliation / constituent_of / pledged_allegiance_to；其持久性存疑。详见关系 rel-d1-fla-jnim-cooperation。",
            "watch_indicators": [
                "FLA 与 JNIM 战场协同是否持续或破裂",
                "FLA 与马里政府是否进入政治对话",
                "CSP-DPA 框架与阿扎瓦德政治进程的公开动态",
            ],
        },
    },
]
