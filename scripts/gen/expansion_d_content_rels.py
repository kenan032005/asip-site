# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-D — relationship content module.

Source of truth: ASIP-PPT-ENTITY-EXPANSION-D-Authoritative-Content-Pack.md §3-§11.
Maps to existing ontology only (no ontology expansion). R3 dossiers carry full
formation/stages/mechanism/geography/attribution/uncertainty/ASIP/watch/timeline.
"""

TODAY = "2026-08-14"
IMPORTER = "expansion-d"

R3 = "R3_FULL_RELATIONSHIP_INTELLIGENCE"
R2 = "R2_DEVELOPED_RELATIONSHIP"
R1 = "R1_SIMPLE_SOURCED_RELATION"

S_NCTC_SINAI = "expd-nctc-isis-sinai"
S_STATE_CRT = "us-state-crt-2022"
S_OFAC = "expd-ofac-2015-09-29"
S_HRW_BURKINA = "d2-hrw-burkina-2026-04-02"
S_MAPPING = "expd-mapping-ansaroul-islam"
S_CTC_ANSOUL = "expd-ctc-ansaroul-islam"
S_AFRICA_CENTER = "expd-africa-center-tactical-units"
S_REUTERS_PIPE = "expd-reuters-niger-pipeline"
S_HRW_NIGER = "expd-hrw-niger-2025"
S_WORLDBANK = "expd-worldbank-niger-2026"
S_AHRAM = "expd-ahram-fpl"
S_REUTERS_FACTBOX = "deptha-reuters-mali-groups-2026-04-27"
S_REUTERS_FLA_JNIM_A = "d1-reuters-fla-jnim-2026-04-25"
S_REUTERS_FLA_JNIM_B = "deptha-reuters-fla-jnim-2026-07-04"
S_REUTERS_GOITA = "expd-reuters-goita-2026-04-28"
S_AP_MALI = "expd-ap-mali-2026"
S_BTI = "expd-bti-mali-2026"


def rel(rid, src, tgt, rtype, *, ring="middle", status, summary,
        direction="bidirectional", time_start="", time_end="", start_year=None,
        confidence="high", formation="", scope="", why="", unc="",
        refs=(), disputed=False, temporal=True, freshness="current",
        status_detail="", note=""):
    return {
        "relationship_id": rid, "slug": rid.replace("rel-", "", 1),
        "source_entity_id": src, "target_entity_id": tgt, "relationship_type": rtype,
        "direction": direction, "display_ring": ring, "current_status": status,
        "time_start": time_start, "time_end": time_end, "start_year": start_year,
        "confidence": confidence, "relation_summary": summary,
        "formation_background": formation or summary, "current_status_detail": status_detail or status,
        "geographic_scope": scope, "why_it_matters": why, "uncertainties": unc,
        "source_refs": list(refs), "last_verified_at": TODAY,
        "temporal_sensitive": temporal, "disputed": disputed,
        "record_created_at": TODAY, "record_updated_at": TODAY, "record_reviewed_at": TODAY,
        "claim_valid_as_of": TODAY, "freshness_status": freshness,
        "current_status_verified_at": TODAY, "relationship_semantics_note": note,
    }


def rprofile(rid, *, title, src, tgt, rtype, ring, maturity, status, overview,
             parties, formation, initial, stages, causes, turning_points, regional,
             impact, why, unc, sources, drivers, constraints, assessment, asip, watch,
             disputed=False, temporal=True):
    return {
        "relationship_id": rid, "relation_title": title,
        "source_entity_id": src, "target_entity_id": tgt, "relation_type": rtype,
        "display_ring": ring, "current_status": status, "overview": overview,
        "parties": list(parties), "formation_background": formation,
        "initial_relationship": initial, "evolution_stages": list(stages),
        "causes": list(causes), "key_turning_points": list(turning_points),
        "regional_differences": regional, "impact_on_security": impact,
        "why_it_matters": why, "uncertainties": unc, "disputed": disputed,
        "temporal_sensitive": temporal, "last_verified_at": TODAY,
        "source_ids": list(sources), "drivers": list(drivers),
        "constraints": list(constraints), "current_assessment": assessment,
        "asip_analysis": asip, "watch_indicators": list(watch),
        "relation_maturity": maturity, "imported_by": IMPORTER,
    }


def tl(date, title, desc, impact, conf, sources, disputed=False):
    return {
        "date": date, "event_title": title, "event_description": desc,
        "impact_on_relationship": impact, "confidence": conf,
        "disputed": disputed, "source_ids": list(sources),
    }


# ---------------------------------------------------------------------------
# NEW relationships
# ---------------------------------------------------------------------------
NEW_RELATIONSHIPS = [
    # 1. ISIS-Sinai → ISIS (pledged allegiance; current but severely degraded branch)
    rel(
        "rel-expd-isis-sinai-isis",
        "actor-isis-sinai", "actor-islamic-state", "pledged_allegiance_to",
        ring="inner", status="reported_current_branch_recognition",
        time_start="2014-11", start_year=2014, confidence="high",
        summary="ISIS-Sinai 是伊斯兰国（ISIS）的西奈半岛分支：其前身“耶路撒冷支持者”（ABM）于 2014 年 11 月正式宣誓效忠 ISIS，成为伊斯兰国西奈省。自 2022 年起该分支明显削弱，至 2025 年 NCTC 仍将其列为 ISIS 分支但判定为严重退化。",
        formation="2014 年 11 月，ABM 正式宣誓效忠 ISIS，采用“伊斯兰国西奈省”身份；2015 年美国将指定修正为纳入 ISIL/西奈省别名。这一效忠是 ISIS 全球分支体系在埃及西奈方向的落地。",
        scope="埃及西奈半岛",
        why="这是理解 ISIS 全球分支体系北非—西奈方向的关键关系；ABM→ISIS-Sinai 的组织连续性是“本地组织并入 ISIS 品牌”的典型样本。",
        unc="效忠 ISIS 时是否伴随派别分裂、以及衰退期后的现役规模，缺乏可靠公开统计。",
        refs=[S_NCTC_SINAI, S_STATE_CRT, S_OFAC],
        freshness="current", temporal=True,
        status_detail="ISIS 分支（当前但严重退化）；2022 年起衰退，2023-02 为最后一次公开宣称袭击。",
        note="ABM 是 ISIS-Sinai 2014-11 宣誓效忠前的历史名称；不得另建当前 ABM 节点。",
    ),
    # 2. Ansaroul Islam ↔ Katiba Macina (historical operational/network association)
    rel(
        "rel-expd-ansaroul-katiba-macina",
        "actor-ansarul-islam", "actor-katiba-macina", "historically_associated_with",
        ring="middle", status="historical_association",
        time_start="2016", start_year=2016, confidence="medium_high",
        summary="安萨鲁伊斯兰的创始人 Ibrahim Dicko 与阿马杜·库法（Amadou Koufa）/马西纳旅网络存在联系；安萨鲁伊斯兰从早期即与 Katiba Macina / JNIM 前身存在行动/训练/网络层面的历史关联。",
        formation="安萨鲁伊斯兰 2016 年成立前即嵌入苏姆省 Al-Irchad 网络，并与马里北部的马西纳旅（Katiba Macina）/阿马杜·库法网络存在人员与网络联系；2016 年 12 月纳苏姆布袭击后公开武装化。",
        scope="布基纳法索北部 ↔ 马里中部（马西纳）",
        why="该历史关联解释了安萨鲁伊斯兰为何最终并入 JNIM 体系——其与马西纳旅网络的历史联系构成并入路径。",
        unc="历史关联的具体机制（训练、人员输送、后勤）缺乏逐项公开披露，以“历史关联”而非“从属/合并”建模。",
        refs=[S_CTC_ANSOUL, S_MAPPING, S_HRW_BURKINA],
        freshness="historical", temporal=False,
        note="仅建模历史行动/训练/网络关联；不建模 constituent_of 或合并关系。",
    ),
    # 3. FPL → Niger (operates_in + rich anti-junta profile)
    rel(
        "rel-expd-fpl-niger-operates",
        "actor-niger-fpl", "country-niger", "operates_in",
        ring="middle", status="active",
        time_start="2023-08", start_year=2023, confidence="high",
        summary="尼日尔爱国解放阵线（FPL）于 2023 年 8 月成立后在尼日尔境内活动，作为反军政府武装对军警与关键基础设施目标发动袭击，核心诉求是释放被推翻总统巴祖姆并恢复宪政秩序。",
        formation="FPL 形成于 2023 年 7 月政变推翻巴祖姆之后，2023 年 8 月成立，公开要求释放巴祖姆、恢复宪政秩序，随后以武装袭击对军政府施压。",
        scope="尼日尔（尤其东部/东北部与输油管道走廊）",
        why="该关系是 FPL 反军政府武装叛乱的地缘落点；其与尼日尔国家的关系是武装对立（anti-junta），通过 operates_in + 富档案承载。",
        unc="FPL 的规模与指挥结构、以及对国家控制的挑战强度缺乏系统公开统计。",
        refs=[S_REUTERS_PIPE, S_HRW_NIGER, S_WORLDBANK],
        freshness="current", temporal=True,
        status_detail="反军政府武装叛乱（活跃）；袭击军警与基础设施以施压尼日尔军政府。",
        note="与尼日尔的关系为反军政府武装对立；采用 operates_in + 富档案承载冲突语义，不新增 ontology。",
    ),
]

NEW_RELATION_PROFILES = {
    # ============================================================ ISIS-Sinai → ISIS
    "rel-expd-isis-sinai-isis": rprofile(
        "rel-expd-isis-sinai-isis",
        title="ISIS-Sinai → 伊斯兰国：2014 年宣誓效忠的西奈分支",
        src="actor-isis-sinai", tgt="actor-islamic-state", rtype="pledged_allegiance_to",
        ring="inner", maturity=R3, status="ISIS 分支（当前但严重退化）",
        overview="ISIS-Sinai 是伊斯兰国的西奈半岛分支。其前身“耶路撒冷支持者”（Ansar Bayt al-Maqdis，ABM）于 2014 年 11 月正式宣誓效忠 ISIS，成为伊斯兰国西奈省。自 2022 年起分支明显削弱，至 2025 年 NCTC 仍将其列为 ISIS 分支但判定为严重退化，最近一次公开宣称袭击为 2023 年 2 月。",
        parties=[{"entity_id": "actor-isis-sinai", "role": "伊斯兰国西奈省（前身 ABM，2014-11 效忠）"},
                 {"entity_id": "actor-islamic-state", "role": "伊斯兰国（ISIS 核心网络）"}],
        formation="ABM 于 2011 年埃及动荡后出现；2014 年 11 月正式宣誓效忠 ISIS，采用西奈省身份；2015 年美国指定修正纳入 ISIL/西奈省别名。效忠构成 ISIS 全球分支体系在北非西奈方向的落地。",
        initial="ABM 早期（2011—2014）以反以色列与反埃及当局的双重目标运作，2012—2014 年声称对以色列与埃及目标发动袭击；2014-11 效忠 ISIS 是组织连续体中的身份转折。",
        stages=[
            {"period": "2011", "detail": "ABM 在埃及动荡后出现。"},
            {"period": "2012—2014", "detail": "声称对以色列与埃及目标发动袭击。"},
            {"period": "2014-11", "detail": "正式宣誓效忠 ISIS，成为西奈省。"},
            {"period": "2015", "detail": "美国指定修正，纳入 ISIL/西奈省别名。"},
            {"period": "2014—2022", "detail": "据 NCTC 统计实施超过 500 次西奈袭击。"},
            {"period": "2022 起", "detail": "进入明显衰退期。"},
            {"period": "2023-02", "detail": "截至 2025-05 的最后一次公开宣称袭击。"},
            {"period": "2025", "detail": "NCTC 仍列为 ISIS 分支但判定严重退化。"},
        ],
        causes=["ABM 的地方暴力能力与 ISIS 全球品牌扩张的相互吸引", "2014 年 ISIS 全球扩张浪潮下的宣誓效忠潮流", "西奈半岛治理真空与埃及中央权威的边境退缩"],
        turning_points=[
            {"event": "2014-11 宣誓效忠", "impact": "ABM 成为 ISIS 西奈省，组织连续体完成身份切换。", "source_ids": [S_NCTC_SINAI, S_STATE_CRT]},
            {"event": "2015 美国指定修正", "impact": "美国正式将西奈省别名纳入 ISIS 相关指定。", "source_ids": [S_OFAC]},
            {"event": "2022 起衰退", "impact": "埃及反恐行动持续削弱分支行动能力。", "source_ids": [S_NCTC_SINAI]},
            {"event": "2023-02 最后一次宣称袭击", "impact": "公开袭击节奏大幅下降，标志严重退化。", "source_ids": [S_NCTC_SINAI]},
        ],
        regional="埃及西奈半岛（北西奈省为主）。",
        impact="该分支历史上对埃及安全形势构成显著威胁（2014—2022 年 500+ 次袭击）；其衰退标志着埃及反恐行动的重要成效，也反映了 ISIS 分支体系在后哈里发时期的整体收缩。",
        why="ABM→ISIS-Sinai 的连续性是“本地组织通过宣誓效忠并入 ISIS 品牌”的典型样本，是理解 ISIS 全球分支形成机制的关键案例。",
        unc="效忠 ISIS 时是否伴随派别分裂、衰退期后现役规模与指挥结构，缺乏可靠公开统计。",
        sources=[S_NCTC_SINAI, S_STATE_CRT, S_OFAC],
        drivers=["ISIS 全球品牌扩张", "西奈地方武装的生存与升级需求", "埃及反恐压力下的抱团与效忠"],
        constraints=["埃及的军事清剿与边境封锁", "部落亲政府力量的抵抗", "ISIS 核心网络的衰落"],
        assessment="宣誓效忠关系（2014-11 至今）；当前为严重退化的 ISIS 分支，组织/法律存在保留但行动节奏与威胁均大幅下降。",
        asip="ASIP 判断：ISIS-Sinai→ISIS 是宣誓效忠（pledged_allegiance_to）关系，且是“严重退化但身份延续”的当前分支。评估必须把组织/法律存在、行动节奏、当前威胁三层分开，避免把严重退化简单写成 defunct，也避免夸大其当前威胁。",
        watch=["是否出现新的公开宣称袭击或 ISIS 宣传重新启用西奈省名号", "埃及反恐与部落亲政府力量的公开动态", "NCTC/美国/联合国对 ISIS-Sinai 表述的更新"],
    ),
    # ============================================================ Ansaroul ↔ Katiba Macina
    "rel-expd-ansaroul-katiba-macina": rprofile(
        "rel-expd-ansaroul-katiba-macina",
        title="安萨鲁伊斯兰 ↔ 马西纳旅：早期历史行动/网络关联",
        src="actor-ansarul-islam", tgt="actor-katiba-macina", rtype="historically_associated_with",
        ring="middle", maturity=R2, status="历史关联（2016—2020 前后）",
        overview="安萨鲁伊斯兰的创始人 Ibrahim Dicko 与阿马杜·库法（Amadou Koufa）/马西纳旅网络存在联系；安萨鲁伊斯兰从早期即与 Katiba Macina / JNIM 前身存在行动、训练与网络层面的历史关联。这一历史关联解释了安萨鲁伊斯兰最终并入 JNIM 体系的路径。",
        parties=[{"entity_id": "actor-ansarul-islam", "role": "安萨鲁伊斯兰（2016 年成立）"},
                 {"entity_id": "actor-katiba-macina", "role": "马西纳旅（马里中部，JNIM 前身组成）"}],
        formation="安萨鲁伊斯兰根植于苏姆省 Al-Irchad 网络，并与马里北部的马西纳旅/阿马杜·库法网络存在人员与网络联系；2016 年 12 月纳苏姆布袭击后公开武装化。",
        initial="Ibrahim Dicko 与阿马杜·库法/马西纳网络的联系构成安萨鲁伊斯兰的早期外联基础。",
        stages=[
            {"period": "2016 前", "detail": "Ibrahim Dicko 与马西纳/库法网络存在联系。"},
            {"period": "2016-12", "detail": "安萨鲁伊斯兰袭击纳苏姆布军警营地，公开武装化。"},
            {"period": "2017 后", "detail": "Ibrahim 去世、Jafar Dicko 继任，与 JNIM 前身联系延续。"},
            {"period": "2020—2021 前后", "detail": "安萨鲁伊斯兰逐步并入 JNIM 体系。"},
        ],
        causes=["萨赫勒圣战网络的跨边境联系", "库法/马西纳网络的扩张", "布基纳法索北部地方武装的崛起"],
        turning_points=[
            {"event": "2016-12 纳苏姆布袭击", "impact": "安萨鲁伊斯兰公开武装化，外联网络转入行动化。", "source_ids": [S_MAPPING, S_CTC_ANSOUL]},
        ],
        regional="布基纳法索北部 ↔ 马里中部（马西纳）。",
        impact="该历史关联构成 JNIM 在布基纳法索扩张的路径基础，是理解萨赫勒圣战网络横向整合的关键。",
        why="解释安萨鲁伊斯兰最终并入 JNIM 的路径；以“历史关联”而非“从属/合并”建模，避免过度断言。",
        unc="历史关联的具体机制（训练、人员输送、后勤）缺乏逐项公开披露。",
        sources=[S_CTC_ANSOUL, S_MAPPING, S_HRW_BURKINA],
        drivers=["萨赫勒网络横向整合", "库法网络的扩张", "跨边境人员流动"],
        constraints=["两国反恐行动", "ISIS 阵营的竞争分流"],
        assessment="历史关联关系；安萨鲁伊斯兰通过该关联最终并入 JNIM，但二者从未是正式的从属/合并关系。",
        asip="ASIP 判断：安萨鲁伊斯兰↔马西纳旅是历史行动/训练/网络关联，是“网络联系→最终并入 JNIM”路径的早期环节。以 historically_associated_with 建模，不升级为 constituent_of/合并。",
        watch=["学术/HRW 对安萨鲁伊斯兰与马西纳网络历史联系的补充披露"],
    ),
    # ============================================================ FPL → Niger
    "rel-expd-fpl-niger-operates": rprofile(
        "rel-expd-fpl-niger-operates",
        title="FPL ↔ 尼日尔：反军政府武装对立（operates_in + 富档案）",
        src="actor-niger-fpl", tgt="country-niger", rtype="operates_in",
        ring="middle", maturity=R3, status="反军政府武装叛乱（活跃）",
        overview="尼日尔爱国解放阵线（FPL）于 2023 年 8 月成立后在尼日尔境内活动，作为反军政府武装对军警与关键基础设施（尤其中资支持的尼日尔—贝宁输油管道）发动袭击，核心诉求是释放被推翻总统巴祖姆并恢复宪政秩序。",
        parties=[{"entity_id": "actor-niger-fpl", "role": "FPL（2023-08 成立的反军政府武装）"},
                 {"entity_id": "country-niger", "role": "尼日尔（军政府控制的国家）"}],
        formation="FPL 形成于 2023 年 7 月尼日尔政变推翻巴祖姆之后，2023 年 8 月成立，公开要求释放巴祖姆、恢复宪政秩序，随后以武装袭击对军政府施压。",
        initial="2023 年 8 月成立即以反军政府、恢复宪政秩序为公开诉求，形成与尼日尔军政府的武装对立。",
        stages=[
            {"period": "2023-07", "detail": "尼日尔政变推翻总统巴祖姆。"},
            {"period": "2023-08", "detail": "FPL 成立，要求释放巴祖姆、恢复宪政秩序。"},
            {"period": "2024-06", "detail": "FPL 宣称袭击中资支持的尼日尔—贝宁输油管道并威胁继续袭击。"},
            {"period": "2024—2026", "detail": "对军警与基础设施目标持续施压。"},
            {"period": "2026-06", "detail": "领导人 Mahamoud Sallah 在利比亚被拘押后获释。"},
        ],
        causes=["2023 年政变引发的政治裂痕武装化", "对政变非法性与宪政秩序诉求的强硬表达", "图布族社群与尼日尔东部的长期边缘化传统"],
        turning_points=[
            {"event": "2023-08 成立", "impact": "反军政府武装阵营在尼日尔形成。", "source_ids": [S_WORLDBANK, S_HRW_NIGER]},
            {"event": "2024-06 管道袭击", "impact": "以高可见度基础设施袭击提升对军政府的经济与安全压力。", "source_ids": [S_REUTERS_PIPE]},
            {"event": "2026-06 领导人获释", "impact": "领导人拘押事件结束，组织动向待观察。", "source_ids": [S_AHRAM]},
        ],
        regional="尼日尔（东部/东北部与输油管道走廊）。",
        impact="FPL 的袭击对尼日尔—贝宁输油管道这一能源走廊构成实际威胁，并加剧了政变后尼日尔的安全与经济不稳定。",
        why="该关系是 FPL 反军政府叛乱的地缘落点；以 operates_in + 富档案承载“武装对立”语义，避免新增 ontology。",
        unc="FPL 的规模、指挥结构、资金与外部支持关系缺乏系统公开披露；其与图布族其他叛乱力量及利比亚各方的关系边界不确定。",
        sources=[S_REUTERS_PIPE, S_HRW_NIGER, S_WORLDBANK, S_AHRAM],
        drivers=["反军政府政治诉求", "对政变非法性的强硬回应", "能源走廊的战略脆弱性"],
        constraints=["尼日尔军政府的镇压", "外部支持的不确定性"],
        assessment="FPL 与尼日尔为反军政府武装对立关系；FPL 属政治-武装叛乱（anti-junta rebel group），非圣战/恐怖组织。",
        asip="ASIP 判断：FPL↔尼日尔是反军政府武装对立，以 operates_in + 富档案承载冲突语义。对中资管道等基础设施的袭击是“高可见度、高经济成本”的施压战术，不得据此将 FPL 归类为恐怖或圣战组织。",
        watch=["FPL 是否继续袭击管道或军警目标", "巴祖姆释放与宪政秩序谈判进展", "Mahamoud Sallah 获释后的组织动向"],
    ),
}

NEW_RELATION_TIMELINES = {
    "rel-expd-isis-sinai-isis": [
        tl("2011", "ABM 出现", "埃及动荡后出现，目标兼及以色列与埃及当局。", "ISIS 西奈分支前身形成。", "high", [S_NCTC_SINAI]),
        tl("2014-11", "宣誓效忠 ISIS", "ABM 正式宣誓效忠 ISIS，成为西奈省。", "组织连续体完成身份切换。", "high", [S_NCTC_SINAI, S_STATE_CRT]),
        tl("2015", "美国指定修正", "指定纳入 ISIL/西奈省别名。", "国际指定层面确认 ISIS 分支身份。", "high", [S_OFAC]),
        tl("2014—2022", "袭击高峰期", "据 NCTC 统计实施超过 500 次袭击。", "对埃及安全形势构成显著威胁。", "high", [S_NCTC_SINAI]),
        tl("2022 起", "衰退期", "埃及反恐行动持续削弱其行动能力。", "分支进入明显衰退。", "high", [S_NCTC_SINAI]),
        tl("2023-02", "最后一次宣称袭击", "截至 2025-05 的最后一次公开宣称恐怖袭击。", "公开袭击节奏大幅下降。", "high", [S_NCTC_SINAI]),
        tl("2025-05", "NCTC 严重退化评估", "仍列为 ISIS 分支但严重退化。", "严重退化但身份延续。", "high", [S_NCTC_SINAI]),
    ],
    "rel-expd-ansaroul-katiba-macina": [
        tl("2016 前", "网络联系形成", "Ibrahim Dicko 与马西纳/库法网络存在联系。", "历史关联的早期环节。", "medium_high", [S_CTC_ANSOUL]),
        tl("2016-12", "纳苏姆布袭击", "安萨鲁伊斯兰公开武装化。", "外联网络转入行动化。", "high", [S_MAPPING, S_CTC_ANSOUL]),
        tl("2017 后", "继任与联系延续", "Jafar Dicko 继任，与 JNIM 前身联系延续。", "历史关联延续。", "medium_high", [S_MAPPING]),
        tl("2020—2021 前后", "并入 JNIM 体系", "安萨鲁伊斯兰逐步并入 JNIM。", "历史关联走向并入。", "high", [S_HRW_BURKINA]),
    ],
    "rel-expd-fpl-niger-operates": [
        tl("2023-07", "尼日尔政变", "政变推翻总统巴祖姆。", "政治裂痕出现。", "high", [S_WORLDBANK]),
        tl("2023-08", "FPL 成立", "成立并要求释放巴祖姆、恢复宪政秩序。", "反军政府武装阵营形成。", "high", [S_WORLDBANK, S_HRW_NIGER]),
        tl("2024-06", "管道袭击", "宣称袭击中资支持的输油管道并威胁继续。", "基础设施袭击升级施压。", "high", [S_REUTERS_PIPE]),
        tl("2024—2026", "持续冲突", "对军警与基础设施目标持续施压。", "反军政府武装对立延续。", "high", [S_HRW_NIGER]),
        tl("2026-06", "领导人获释", "Mahamoud Sallah 在利比亚被拘押后获释。", "领导人拘押事件结束。", "medium_high", [S_AHRAM]),
    ],
}

# ---------------------------------------------------------------------------
# UPGRADE existing relation dossiers to R3
# ---------------------------------------------------------------------------
UPGRADE_PROFILES = {
    "rel-d1-ansarul-jnim-constituent": rprofile(
        "rel-d1-ansarul-jnim-constituent",
        title="安萨鲁伊斯兰 → JNIM：布基纳法索圣战力量的渐进整合",
        src="actor-ansarul-islam", tgt="actor-jnim", rtype="constituent_of",
        ring="inner", maturity=R3, status="结构性并入（渐进式，保留地方身份）",
        overview="安萨鲁伊斯兰于 2020—2021 前后被 JNIM 渐进吸收，成为 JNIM 在布基纳法索扩张所依托的组成单元之一；至 2026 年其已高度整合进 JNIM，但仍在某种程度上保留自身身份。整合是渐进式的，而非单一日期的一次性合并。",
        parties=[{"entity_id": "actor-ansarul-islam", "role": "安萨鲁伊斯兰（2016 年成立，JNIM 组成单元）"},
                 {"entity_id": "actor-jnim", "role": "JNIM（2017 年合并成立的萨赫勒圣战联盟）"}],
        formation="安萨鲁伊斯兰 2016 年末成立后，从早期即与 Katiba Macina / JNIM 前身存在合作；2020—2021 前后被 JNIM 逐步吸收，2025 年公开视频使用 JNIM 媒体品牌，标志整合进入品牌化阶段。",
        initial="安萨鲁伊斯兰以本地圣战武装身份运作（2016—2020），与 JNIM 前身存在历史关联；2019—2020 年少数成员据报转向 ISGS/IS Sahel（派别级流动，非整组转化）。",
        stages=[
            {"period": "2016-12", "detail": "安萨鲁伊斯兰成立并公开武装化。"},
            {"period": "2017", "detail": "Ibrahim Dicko 去世，Jafar Dicko 继任。"},
            {"period": "2019—2020", "detail": "少数成员转向 ISGS/IS Sahel（faction-level）。"},
            {"period": "2020—2021 前后", "detail": "逐步被 JNIM 吸收。"},
            {"period": "2025—2026", "detail": "使用 JNIM 媒体品牌，HRW 确认高度整合但保留身份。"},
        ],
        causes=["JNIM 在布基纳法索的扩张战略", "安萨鲁伊斯兰与 JNIM 前身的历史关联", "本地武装在安全压力下的整合需求"],
        turning_points=[
            {"event": "2020—2021 前后并入", "impact": "安萨鲁伊斯兰成为 JNIM 组成单元。", "source_ids": [S_HRW_BURKINA]},
            {"event": "2025 使用 JNIM 品牌", "impact": "整合进入品牌化阶段。", "source_ids": [S_HRW_BURKINA]},
        ],
        regional="布基纳法索北部 → JNIM 萨赫勒全域。",
        impact="安萨鲁伊斯兰是 JNIM 在布基纳法索扩张的重要组成单元，其并入标志 JNIM 在布基纳法索从渗透走向体系化控制。",
        why="安萨鲁伊斯兰→JNIM 是理解 JNIM 吸收地方叛乱品牌、而非简单取消其身份的扩张模式的关键关系。",
        unc="并入后其名称作为独立组织标签的持续使用程度缺乏统一公开口径。",
        sources=[S_HRW_BURKINA, S_MAPPING, S_CTC_ANSOUL],
        drivers=["JNIM 扩张战略", "历史关联的路径依赖", "整合的生存理性"],
        constraints=["ISIS 阵营的竞争分流", "布基纳法索反恐行动"],
        assessment="结构性并入关系（渐进式）；安萨鲁伊斯兰作为 JNIM 布基纳法索组成单元运作并保留地方身份。",
        asip="ASIP 判断：安萨鲁伊斯兰→JNIM 是渐进式结构性并入，必须守住纪律——整组是 JNIM 组成单元（非 ISIS/IS Sahel）；与 IS Sahel 仅有少数成员的派别级流动。其“保留本地身份”是 JNIM 扩张的治理手段。",
        watch=["JNIM 对安萨鲁伊斯兰品牌的公开使用与人事变动", "是否出现向 IS Sahel 的新的成员流动", "HRW/学术来源对布基纳法索武装格局的新表述"],
    ),
}

UPGRADE_TIMELINES = {
    "rel-d1-ansarul-jnim-constituent": [
        tl("2016-12", "安萨鲁伊斯兰成立", "Ibrahim Dicko 创立，袭击纳苏姆布军警营地。", "JNIM 未来组成单元形成。", "high", [S_MAPPING, S_CTC_ANSOUL]),
        tl("2017", "Ibrahim 去世", "Ibrahim Dicko 去世，Jafar Dicko 继任。", "领导层更替。", "high", [S_MAPPING]),
        tl("2019—2020", "少数成员转向 IS Sahel", "少数成员据报转向 ISGS/IS Sahel（faction-level）。", "派别级流动，非整组转化。", "medium_high", [S_HRW_BURKINA]),
        tl("2020—2021 前后", "逐步并入 JNIM", "被 JNIM 逐步吸收。", "结构性并入推进。", "high", [S_HRW_BURKINA]),
        tl("2025—2026", "品牌化整合", "使用 JNIM 媒体品牌，HRW 确认高度整合但保留身份。", "整合进入品牌化阶段。", "high", [S_HRW_BURKINA]),
    ],
}

# ---------------------------------------------------------------------------
# FLA ↔ JNIM targeted update (cooperates_with → tactical_coordination emphasis)
# ---------------------------------------------------------------------------
FLA_JNIM_UPDATE = {
    "relationship_id": "rel-d1-fla-jnim-cooperation",
    "set_fields": {
        "current_status": "tactical_coordination",
        "current_status_detail": "2026 年 4 月起 FLA 与 JNIM 在对马里军事政府协同攻击中呈现战术性战场协调；二者政治/意识形态目标不同，该关系是行动层临时合作而非联盟或附属。",
    },
    "timeline_append": [
        tl("2024-11", "FLA 正式重组", "当前 FLA 版本于 2024 年 11 月正式形成。", "合作主体形成。", "high", [S_REUTERS_FACTBOX]),
        tl("2026-04", "协同攻击", "FLA 与 JNIM 对马里军事政府发动协同攻击（路透社报道）。", "战术性战场协调出现。", "high", [S_REUTERS_FLA_JNIM_A, S_AP_MALI]),
        tl("2026-07", "持续战场协调", "开源报道继续描述双方战场合作。", "协调持续但持久性存疑。", "high", [S_REUTERS_FLA_JNIM_B]),
    ],
    "profile_merge": {
        "asip_analysis": "ASIP 判断：FLA↔JNIM 是 2026 年的战术性战场协调——针对共同敌人（马里军事政府）的临时合作，二者政治/意识形态目标截然不同（FLA 求阿扎瓦德自决/独立，JNIM 求基地组织关联的伊斯兰治理）。绝不能建模为 affiliation、constituent_of 或 pledged_allegiance_to；协调的持久性高度不确定。",
        "uncertainties": "协调机制、联合指挥程度、后勤共享与长期政治协议均缺乏公开可靠细节；FLA 是否会在政治对话开启后与 JNIM 脱钩存在高度不确定性。",
        "watch_indicators": ["联合声明或共同指挥出现", "是否继续同步行动", "是否发生利益冲突或脱钩", "FLA 与马里政府的政治对话进展"],
    },
}
