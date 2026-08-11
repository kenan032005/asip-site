# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-C — relationship content module.

Source of truth: ASIP-PPT-ENTITY-EXPANSION-C-Authoritative-Content-Pack.md (§15-§16).
Maps to existing ontology (no ontology expansion). R3 dossiers carry full
formation / stages / mechanism / geography / current historical meaning / why /
uncertainty / ASIP / watch / timeline. Attribution preserved.
"""

TODAY = "2026-08-11"
IMPORTER = "expansion-c"

S_UN_EIJ = "expc-un-eij"
S_UN_AQ = "expc-un-alqaida"
S_STATE_EIJ = "expc-state-eij-2003"
S_UN_GIA = "expc-un-gia"
S_UN_AQIM = "un-aqim-2001"
S_NCTC_AQIM = "deptha-nctc-aqim-2026-06"
S_UN_AIAI = "expc-un-aiai"
S_S2016 = "expc-un-s2016-919"
S_S2017 = "expc-un-s2017-924"
S_NCTC_SHABAAB = "expa-nctc-al-shabaab-2026-04"
S_UN_TCG = "expc-un-tcg"
S_UN_MAAROUFI = "expc-un-tcg-maaroufi"
S_STATE_TCG = "expc-state-tcg-2002"
S_UN_GICM = "expc-un-gicm"
S_UN_LIFG = "expc-un-lifg"
S_STATE_GICM_2002 = "expc-state-gicm-2002"
S_STATE_GICM_2007 = "expc-state-gicm-2007"
S_S2015_891 = "expc-un-s2015-891"
S_CTC = "expc-ctc-battar"
S_NCTC_AAD = "expc-nctc-ansar-dine"
S_NCTC_MURAB = "expc-nctc-murabitun"
S_NCTC_ISSAHEL = "deptha-nctc-is-sahel-2026-06"
S_UN_JNIM = "un-jnim-2018"
S_NCTC_JNIM = "d2-nctc-jnim-2026-05"
S_UN_ALQAIDA = "deptha-nctc-alqaida-2026-05"

R3 = "R3_FULL_RELATIONSHIP_INTELLIGENCE"
R2 = "R2_DEVELOPED_RELATIONSHIP"
R1 = "R1_SIMPLE_SOURCED_RELATION"


def rel(rid, src, tgt, rtype, *, ring="middle", status, summary,
        direction="bidirectional", time_start="", time_end="", start_year=None,
        confidence="high", formation="", scope="", why="", unc="",
        refs=(), disputed=False, temporal=True, freshness="historical",
        status_detail="", note=""):
    return {
        "relationship_id": rid,
        "slug": rid.replace("rel-", "", 1),
        "source_entity_id": src,
        "target_entity_id": tgt,
        "relationship_type": rtype,
        "direction": direction,
        "display_ring": ring,
        "current_status": status,
        "time_start": time_start,
        "time_end": time_end,
        "start_year": start_year,
        "confidence": confidence,
        "relation_summary": summary,
        "formation_background": formation or summary,
        "current_status_detail": status_detail or status,
        "geographic_scope": scope,
        "why_it_matters": why,
        "uncertainties": unc,
        "source_refs": list(refs),
        "last_verified_at": TODAY,
        "temporal_sensitive": temporal,
        "disputed": disputed,
        "record_created_at": TODAY,
        "record_updated_at": TODAY,
        "record_reviewed_at": TODAY,
        "claim_valid_as_of": TODAY,
        "freshness_status": freshness,
        "current_status_verified_at": TODAY,
        "relationship_semantics_note": note,
    }


def rprofile(rid, *, title, src, tgt, rtype, ring, maturity,
             overview, parties, formation, initial, stages, causes,
             turning_points, regional, impact, why, unc, sources,
             drivers, constraints, assessment, asip, watch,
             disputed=False, temporal=True):
    return {
        "relationship_id": rid,
        "relation_title": title,
        "source_entity_id": src,
        "target_entity_id": tgt,
        "relation_type": rtype,
        "display_ring": ring,
        "current_status": "historical",
        "overview": overview,
        "parties": list(parties),
        "formation_background": formation,
        "initial_relationship": initial,
        "evolution_stages": list(stages),
        "causes": list(causes),
        "key_turning_points": list(turning_points),
        "regional_differences": regional,
        "impact_on_security": impact,
        "why_it_matters": why,
        "uncertainties": unc,
        "disputed": disputed,
        "temporal_sensitive": temporal,
        "last_verified_at": TODAY,
        "source_ids": list(sources),
        "drivers": list(drivers),
        "constraints": list(constraints),
        "current_assessment": assessment,
        "asip_analysis": asip,
        "watch_indicators": list(watch),
        "relation_maturity": maturity,
        "imported_by": IMPORTER,
    }


def tl(date, title, desc, impact, conf, sources, disputed=False):
    return {
        "date": date, "event_title": title, "event_description": desc,
        "impact_on_relationship": impact, "confidence": conf,
        "disputed": disputed, "source_ids": list(sources),
    }


NEW_RELATIONSHIPS = [
    # 1. GIA -> GSPC/AQIM lineage (split_from; GSPC is AQIM historical phase)
    rel(
        "rel-expc-gia-aqim-lineage",
        "actor-aqim", "actor-gia", "split_from",
        ring="inner", status="historical_lineage",
        time_start="1998", start_year=1998, confidence="high",
        summary="GSPC/AQIM 连续体于 1998 年由哈桑·哈塔布自阿尔及利亚武装伊斯兰集团（GIA）分裂成立（成立时名为 GSPC，2007 年 1 月更名 AQIM）。GIA 是 GSPC/AQIM 谱系的历史源头网络。",
        formation="1998 年哈桑·哈塔布（Hassan Hattab）自 GIA 分裂成立萨拉菲宣教与战斗组织（GSPC）；该分裂实体于 2007 年 1 月采用 AQIM 名称。阿卜杜勒马利克·德鲁克德勒曾任 GIA 爆炸物专家，后成为 GSPC/AQIM 领导人，构成人事连续性证据。",
        scope="阿尔及利亚 → 萨赫勒",
        why="这是 AQIM 谱系的根关系：理解 GIA → GSPC → AQIM 连续体是理解北非圣战网络来源的前提。",
        unc="GIA 后期组织凝聚力存在不确定性；分裂时的人员规模与派别构成缺乏系统统计。",
        refs=[S_UN_GIA, S_UN_AQIM, S_NCTC_AQIM],
        note="split_from 表达 GSPC/AQIM 连续体分裂自 GIA；GSPC 为 AQIM 的历史阶段（非独立节点），关系档案明确分裂实体成立时名为 GSPC、2007 年更名 AQIM。",
    ),
    # 2. GSPC/AQIM -> Al-Qaida alignment/rebranding
    rel(
        "rel-expc-aqim-alqaida-alignment",
        "actor-aqim", "actor-al-qaida", "pledged_allegiance_to",
        ring="inner", status="historical_alignment_then_current_affiliation",
        time_start="2006-09-11", start_year=2006, confidence="high",
        summary="2006 年 9 月 11 日基地组织领导层宣布与 GSPC（后更名 AQIM）联合/联盟；NCTC 描述 GSPC 于 2006 年 9 月与基地组织结盟，2007 年 1 月更名 AQIM。该关系是 GSPC/AQIM 与基地组织之间的正式结盟并延续至今。",
        formation="基地组织领导层于 2006 年 9 月 11 日宣布联合/联盟；NCTC 描述 GSPC 在 2006 年 9 月与基地组织结盟；2007 年 1 月 GSPC 更名 AQIM，标志该连续体以基地组织名义正式运作。",
        scope="北非—萨赫勒",
        why="这是 GSPC/AQIM 从地区武装转向全球圣战网络正式一翼的关键节点，也是 AQIM 身份（名称与效忠）的来源。",
        unc="结盟公告与内部整合进程的细节存在来源差异；效忠/联盟的严格法律性质不作断言。",
        refs=[S_NCTC_AQIM, S_UN_AQIM],
        note="pledged_allegiance_to 表达 2006 年结盟/联合（NCTC 与基地组织公告表述）；本档案以现有关系类型建模，不扩 ontology。",
    ),
    # 3. EIJ -> Al-Qaida staged integration (1998 UN / 2001 State)
    rel(
        "rel-expc-eij-alqaida-integration",
        "actor-egyptian-islamic-jihad", "actor-al-qaida", "constituent_of",
        ring="inner", status="historical_staged_integration",
        time_start="1998", time_end="2001", start_year=1998, confidence="medium_high",
        summary="EIJ 与基地组织的关系是分阶段整合：联合国 1267 叙述描述 1998 年合并/整合（关联扎瓦希里），美国国务院历史报告描述 2001 年 6 月正式合并。ASIP 将 1998—2001 作为分阶段整合/正式化时期，不强行归一为单一日期。",
        formation="联合国 1267 叙述描述 EIJ 与基地组织于 1998 年合并/整合（与艾曼·扎瓦希里关联）；EIJ/扎瓦希里参与了 1998 年世界伊斯兰阵线宣言背景进程。美国国务院历史报告描述 EIJ 于 2001 年 6 月与基地组织正式合并。两个日期来自不同权威叙述，反映整合进程的不同阶段。",
        scope="埃及、阿富汗、巴基斯坦、苏丹 → 全球网络",
        why="EIJ 是基地组织领导层人事来源（扎瓦希里）与埃及伊斯兰主义融入全球圣战网络的关键案例；双日期处理是事实纪律的核心。",
        unc="1998 年与 2001 年两个日期的精确组织机制存在来源差异；ASIP 不强行归一。",
        refs=[S_UN_EIJ, S_UN_AQ, S_STATE_EIJ],
        note="constituent_of 表达 EIJ 并入基地组织的结构性关系；关系档案明确 UN（1998）与 U.S. State（2001-06）双日期为分阶段整合/正式化。",
    ),
    # 4. AIAI <-> Al-Shabaab historical predecessor network
    rel(
        "rel-expc-aiai-shabaab-predecessor",
        "actor-aiai", "actor-al-shabaab", "historically_associated_with",
        ring="middle", status="historical_predecessor_network",
        time_start="2000", start_year=2000, confidence="medium_high",
        summary="AIAI 是青年党的重要意识形态/人事前身网络：联合国专家组报告将 AIAI 描述为青年党的意识形态前驱，联合国综合制裁材料亦报告 AIAI 在索马里/埃塞俄比亚活动并有并入青年党的描述。ASIP 明确：公开来源不支持把青年党的起源简化为单一的 AIAI→青年党直接组织传承。",
        formation="AIAI 约于 1982—1984 年建立，活动于索马里与埃塞俄比亚，哈桑·达希尔·阿韦斯为高级领导人。联合国专家组（S/2016/919、S/2017/924）将 AIAI 描述为青年党的意识形态前驱/前驱网络；联合国综合制裁材料报告 AIAI 活动与并入描述。青年党的形成来自更复杂的索马里伊斯兰主义/伊斯兰法院联盟（ICU）生态。",
        scope="索马里、埃塞俄比亚",
        why="该关系解释青年党生态的意识形态与人事来源，同时守住「前身网络而非唯一组织亲本」的限定。",
        unc="AIAI 并入青年党的具体机制与范围缺乏系统公开记载；AIAI 与 ICU 生态各网络的边界不清晰。",
        refs=[S_UN_AIAI, S_S2016, S_S2017, S_NCTC_SHABAAB],
        note="historically_associated_with 表达限定性前身关系；档案明确 ideological/personnel predecessor，保留 UN 归属性，排除单一直接组织传承叙事。",
    ),
    # 5. Battar Brigade -> ISIS-Libya precursor/fusion
    rel(
        "rel-expc-battar-isis-libya",
        "actor-al-battar-brigade", "actor-isis-libya", "constituent_of",
        ring="inner", status="historical_precursor_fusion",
        time_start="2014", start_year=2014, confidence="medium_high",
        summary="巴塔尔旅是 ISIS-利比亚（巴尔卡省）的前驱融合要素：联合国利比亚专家组报告称 ISIL 的巴尔卡省（Wilayat Barqa）是巴塔尔旅与伊斯兰青年协商委员会（IYSC/MSSI）在 ISIS 关联领导层下融合的结果。",
        formation="巴塔尔旅 2012 年创建支援叙利亚/伊拉克 ISIL，2014 年春许多成员返回利比亚，融入德尔纳武装生态；联合国专家组（S/2015/891）记载 Wilayat Barqa 为巴塔尔旅与 IYSC/MSSI 融合结果。CTC 研究描述利比亚战斗人员在叙利亚组成 Katibat al-Battar al-Libi 并与 ISIS 结盟。",
        scope="叙利亚/伊拉克 → 利比亚（德尔纳）",
        why="该关系解释 ISIS-利比亚分支的融合起源，是理解利比亚 ISIS 谱系的关键前驱链。",
        unc="返回利比亚的确切人数与融合机制的细节缺乏系统公开统计。",
        refs=[S_S2015_891, S_CTC],
        note="constituent_of 表达历史前驱/组成关系；档案明确巴塔尔旅不是仍保持独立编制的当前组成部分（Wilayat Barqa 为融合结果）。",
    ),
    # 6. MUJAO -> Al-Murabitun (2013 merger, no merged_into in ontology)
    rel(
        "rel-expc-mujao-murabitun",
        "actor-mujao", "actor-al-mourabitoun", "historically_associated_with",
        ring="middle", status="historical_merger_lineage",
        time_start="2013", start_year=2013, confidence="medium_high",
        summary="穆拉比通于 2013 年由贝尔穆赫塔尔的 al-Mulathamun 营与另一个 AQIM 分裂派别（通常认定为 MUJAO/西非认主独一与圣战）合并而成（NCTC 表述）。MUJAO 是穆拉比通合并的组成来源之一。",
        formation="NCTC 历史材料称 al-Murabitun 于 2013 年由 al-Mulathamun 营与 MUJAO/认主独一圣战派别合并形成；联合国将 MUJAO 列为与 AQIM 和贝尔穆赫塔尔相关的组织。由于本体无 merged_into 类型，ASIP 以 historically_associated_with 表达合并谱系，机制细节写入关系档案。",
        scope="萨赫勒/撒哈拉（马里北部）",
        why="该关系补全 AQIM 分裂 → MUJAO → 穆拉比通 → JNIM 网络的谱系链。",
        unc="MUJAO 与认主独一圣战派别之间的确切关系存在来源差异；合并细节缺乏统一权威记载。",
        refs=[S_NCTC_MURAB, S_UN_AQIM],
        note="historically_associated_with 表达合并谱系（本体无 merged_into）；档案说明 2013 年合并机制与双方来源。",
    ),
    # 7. AQIM -> MUJAO split
    rel(
        "rel-expc-aqim-mujao-split",
        "actor-mujao", "actor-aqim", "split_from",
        ring="middle", status="historical_splinter",
        time_start="2012", start_year=2012, confidence="medium_high",
        summary="MUJAO 是从 AQIM 分裂的萨赫勒武装派别；联合国将 MUJAO 列为与 AQIM 和穆赫塔尔·贝尔穆赫塔尔相关的组织。",
        formation="MUJAO 属于从 AQIM 分裂的萨赫勒武装派别，其形成处于 2010 年代初期马里北部武装伊斯兰主义格局扩张的背景中；NCTC 历史材料将其定位为后来穆拉比通合并的组成部分。",
        scope="萨赫勒/撒哈拉（马里北部）",
        why="该关系表达 AQIM 体系的第一次主要萨赫勒分裂，是后续穆拉比通合并的前置。",
        unc="分裂的确切时间与内部过程缺乏统一权威记载。",
        refs=[S_UN_AQIM, S_NCTC_MURAB],
    ),
    # 8. AQIM <-> Ansar al-Dine (association from mid-2012)
    rel(
        "rel-expc-aqim-ansar-relation",
        "actor-aqim", "actor-ansar-eddine", "affiliated_with",
        ring="middle", status="historical_association",
        time_start="2012", start_year=2012, time_end="2017", confidence="high",
        summary="安萨尔埃丁自 2012 年中期起与 AQIM 建立关联（NCTC）；该关联处于马里北部 2012 年政变后的武装格局中，双方在北部控制时期存在协调。",
        formation="NCTC 确认安萨尔埃丁自 2012 年中期起与 AQIM 存在关联；双方在马里北部武装伊斯兰主义格局中的协调是理解 2012—2013 年北部控制的关键背景。2017 年双方均并入 JNIM 后，该双边关联让位于 JNIM 体系内的构成关系。",
        scope="马里北部",
        why="该关系解释 2012—2013 年马里北部武装格局中 AQIM 与安萨尔埃丁的协作，以及两者共同并入 JNIM 的前置结构。",
        unc="双方协调的具体机制与指挥边界缺乏系统公开披露。",
        refs=[S_NCTC_AAD, S_NCTC_AQIM],
        note="affiliated_with 表达存在关联（非正式隶属）；NCTC 归属性保留。",
    ),
    # 9. GICM <-> Al-Qaida historical association
    rel(
        "rel-expc-gicm-alqaida",
        "actor-gicm", "actor-al-qaida", "historically_associated_with",
        ring="middle", status="historical_association",
        time_start="1990", start_year=1990, time_end="2007", confidence="high",
        summary="GICM 与基地组织存在历史关联：联合国因与基地组织关联于 2002 年列名 GICM，美国国务院历史报告称其与基地组织有联系。",
        formation="GICM 于 1990 年代从阿富汗基地组织训练营的摩洛哥招募者中兴起；联合国 2002 年因与基地组织关联列名；美国国务院历史报告描述 GICM 为与基地组织有联系。2007 年国务院评估 GICM 解体后，该历史关联不再对应活跃组织关系。",
        scope="阿富汗 → 摩洛哥/欧洲",
        why="该关系记录阿富汗一代摩洛哥网络与基地组织的训练营联系及列名依据。",
        unc="GICM 与基地组织之间的组织化程度缺乏系统公开记载。",
        refs=[S_UN_GICM, S_STATE_GICM_2002, S_STATE_GICM_2007],
        note="historically_associated_with 表达历史关联；联合国与国务院归属性保留。",
    ),
    # 10. TCG <-> Al-Qaida historical association
    rel(
        "rel-expc-tcg-alqaida",
        "actor-tunisian-combatant-group", "actor-al-qaida", "historically_associated_with",
        ring="middle", status="historical_association",
        time_start="2000", start_year=2000, time_end="2002", confidence="medium_high",
        summary="TCG 与基地组织存在历史关联：联合国叙述称 TCG 成员与阿富汗基地组织相关营地有联系。",
        formation="TCG 于 2000 年创建，成员与阿富汗基地组织相关营地有联系；联合国 2002 年列名 TCG（及关联人物阿尔-马鲁菲），将其实置于基地组织网络背景下。欧洲调查随后严重打击其关联网络。",
        scope="突尼斯/阿富汗/欧洲",
        why="该关系记录北非阿富汗一代网络与基地组织的训练营地联系，是 TCG 跨国网络结构的核心。",
        unc="TCG 成员在阿富汗营地的具体训练角色记载有限。",
        refs=[S_UN_TCG, S_UN_MAAROUFI, S_STATE_TCG],
        note="historically_associated_with 表达训练营地联系与网络归属，非正式效忠关系。",
    ),
    # 11. Maitatsine -> Nigeria operates_in (historical geography only, NO lineage)
    rel(
        "rel-expc-maitatsine-nigeria",
        "actor-maitatsine-movement", "country-nigeria", "operates_in",
        ring="middle", status="historical_activity",
        time_start="1980", start_year=1980, time_end="1985", confidence="high",
        summary="迈塔齐尼运动的历史活动集中于尼日利亚北部（卡诺为核心），1980—1985 年发生多起相关起义。",
        formation="运动的核心地理为尼日利亚北部城市环境；1980 年 12 月卡诺重大对抗及 1982、1984、1985 年相关起义构成其历史活动主体。",
        scope="尼日利亚北部（卡诺等）",
        why="该关系仅记录历史地理活动；明确不构成任何指向博科哈拉姆的组织传承。",
        unc="运动在各起义地点的具体组织程度缺乏系统统计。",
        refs=["expc-adesoji-maitatsine", "expc-hiskett-maitatsine"],
        note="operates_in 仅表达历史地理活动，不构成谱系边；档案坚持无直接组织传承纪律。",
    ),
]

NEW_RELATION_PROFILES = {
    "rel-expc-gia-aqim-lineage": rprofile(
        "rel-expc-gia-aqim-lineage",
        title="GIA → GSPC → AQIM：阿尔及利亚谱系的根关系",
        src="actor-aqim", tgt="actor-gia", rtype="split_from", ring="inner", maturity=R3,
        overview="GSPC/AQIM 连续体于 1998 年由哈桑·哈塔布自阿尔及利亚武装伊斯兰集团（GIA）分裂成立；分裂实体成立时名为 GSPC，2007 年 1 月更名 AQIM。GIA 是 GSPC/AQIM 谱系的历史源头网络，本关系是理解北非圣战网络连续性的根节点。",
        parties=[{"entity_id": "actor-gia", "role": "阿尔及利亚内战中的激进暴力伊斯兰组织（历史源头）"},
                 {"entity_id": "actor-aqim", "role": "GSPC/AQIM 连续体（分裂后实体，GSPC 为历史阶段）"}],
        formation="1998 年哈桑·哈塔布自 GIA 分裂成立 GSPC（萨拉菲宣教与战斗组织）。阿卜杜勒马利克·德鲁克德勒曾任 GIA 爆炸物专家，后成为 GSPC/AQIM 领导人，构成人事连续性证据。2007 年 1 月 GSPC 更名 AQIM，完成 GIA → GSPC → AQIM 的组织连续性。",
        initial="GSPC 成立即作为 GIA 的对立/分裂派别出现，立场更趋全球圣战取向；分裂动力包括对 GIA 行为方式的内部异议（以来源为准）。",
        stages=[
            {"period": "1998", "detail": "哈塔布自 GIA 分裂创立 GSPC。"},
            {"period": "2001-10-06", "detail": "联合国以 GSPC 名称列名该实体。"},
            {"period": "2006-09-11", "detail": "基地组织领导层宣布联合/联盟；NCTC 描述 GSPC 与基地组织结盟。"},
            {"period": "2007-01", "detail": "GSPC 采用 AQIM 名称，完成谱系更名。"},
        ],
        causes=[
            "GIA 内部对激进暴力行为的异议（以来源为准）",
            "阿尔及利亚内战中伊斯兰主义武装的分化",
            "全球圣战议程对萨赫勒/北非网络的吸引力",
        ],
        turning_points=[
            {"event": "1998 年哈塔布分裂", "impact": "GSPC 成立，GIA 谱系分支开启。", "source_ids": [S_UN_GIA]},
            {"event": "2007 年更名 AQIM", "impact": "连续体以基地组织名义正式运作。", "source_ids": [S_NCTC_AQIM]},
        ],
        regional="阿尔及利亚本土为分裂发生地；后续沿萨赫勒方向扩张。",
        impact="该谱系关系是北非圣战网络（GSPC/AQIM → 萨赫勒分支 → JNIM）的根源，影响当代萨赫勒反恐格局。",
        why="理解 GIA → GSPC → AQIM 连续体是理解 AQIM 身份、谱系与北非圣战网络延续性的前提；GSPC 作为 AQIM 历史阶段而非独立节点是本轮的关键建模纪律。",
        unc="GIA 后期组织凝聚力存在不确定性；1998 年分裂的人员规模与派别构成缺乏系统统计。",
        sources=[S_UN_GIA, S_UN_AQIM, S_NCTC_AQIM],
        drivers=["阿尔及利亚内战分化", "全球圣战议程", "萨赫勒行动空间"],
        constraints=["阿尔及利亚安全部门镇压", "组织内部碎片化压力"],
        assessment="该关系为历史谱系关系，已无活跃双边结构；其意义在于 AQIM 身份与谱系的连续性。",
        asip="ASIP 判断：本关系的核心纪律是「GSPC = AQIM 历史阶段」——GSPC 是 1998—2007 年的名称与阶段，不是平行节点。评估北非谱系时，GIA 是根，GSPC 是阶段，AQIM 是当前身份，三者是同一谱系链的不同时点，不得分裂为多个「当前独立组织」。",
        watch=["联合国或官方对 GIA/AQIM 历史叙述的更新", "AQIM 领导层与谱系人物相关的公开变动"],
    ),
    "rel-expc-aqim-alqaida-alignment": rprofile(
        "rel-expc-aqim-alqaida-alignment",
        title="GSPC/AQIM ↔ 基地组织：2006 年结盟与身份更替",
        src="actor-aqim", tgt="actor-al-qaida", rtype="pledged_allegiance_to", ring="inner", maturity=R3,
        overview="基地组织领导层于 2006 年 9 月 11 日宣布与 GSPC 联合/联盟；NCTC 描述 GSPC 在 2006 年 9 月与基地组织结盟，2007 年 1 月更名 AQIM。该结盟使 GSPC/AQIM 连续体从阿尔及利亚地区武装转化为基地组织网络的正式一翼，并延续至当前（2026 年 NCTC 仍列为基地组织附属）。结盟、更名与后续萨赫勒扩张构成同一进程的三个阶段。",
        parties=[{"entity_id": "actor-aqim", "role": "GSPC/AQIM 连续体（结盟时名 GSPC）"},
                 {"entity_id": "actor-al-qaida", "role": "基地组织（全球网络中心）"}],
        formation="基地组织领导层 2006 年 9 月 11 日宣布联合/联盟；NCTC 描述 GSPC 2006 年 9 月与基地组织结盟；2007 年 1 月更名 AQIM。结盟标志该连续体从地区武装转向基地组织正式一翼。",
        initial="GSPC 成立后逐步向基地组织议程靠拢；2006 年结盟公告是公开化节点。",
        stages=[
            {"period": "2006-09-11", "detail": "基地组织宣布联合/联盟；NCTC 描述 GSPC 结盟。"},
            {"period": "2007-01", "detail": "更名 AQIM，以基地组织名义运作。"},
            {"period": "2007 至今", "detail": "AQIM 作为基地组织附属组织运作，2026 年仍为活跃附属组织。"},
        ],
        causes=["全球圣战议程整合", "GSPC 领导层与基地组织的人事/意识形态联系", "萨赫勒行动空间的战略价值"],
        turning_points=[
            {"event": "2006-09-11 结盟公告", "impact": "正式纳入基地组织网络。", "source_ids": [S_NCTC_AQIM]},
            {"event": "2007-01 更名", "impact": "身份从 GSPC 转为 AQIM。", "source_ids": [S_NCTC_AQIM]},
        ],
        regional="北非—萨赫勒。",
        impact="该关系确立 AQIM 在基地组织网络中的地位，影响其命名、合法性与萨赫勒扩张。",
        why="2006 年结盟与 2007 年更名是 GSPC→AQIM 连续体的关键转折：结盟确立其在基地组织网络中的地位，更名确立其正式身份，二者共同构成 AQIM 的合法性来源。该关系与 GIA 谱系关系（1998 分裂）首尾相接，完整覆盖 AQIM 身份从 GIA 支脉到基地组织正式附属的演化。",
        unc="结盟公告与内部整合进程细节存在来源差异；效忠/联盟的严格法律性质不作断言。",
        sources=[S_NCTC_AQIM, S_UN_AQIM],
        drivers=["基地组织领导层的整合努力", "GSPC 内部亲基地组织派别"],
        constraints=["阿尔及利亚安全部门压力", "萨赫勒行动环境的资源约束"],
        assessment="该关系为历史结盟并延续为当前附属关系（2026 年 NCTC 仍列为基地组织附属）。",
        asip="ASIP 判断：2006—2007 年的结盟与更名是同一进程的两面——结盟公告（2006-09-11）与身份更名（2007-01）共同完成 GSPC→AQIM 的转化。评估时应把结盟视为 AQIM 谱系的正式起点，同时注意该关系与 GIA 分裂关系（1998）的时序衔接。",
        watch=["基地组织与 AQIM 关系的最新权威表述", "AQIM 内部对基地组织忠诚度的公开信号"],
    ),
    "rel-expc-eij-alqaida-integration": rprofile(
        "rel-expc-eij-alqaida-integration",
        title="EIJ → 基地组织：1998—2001 分阶段整合",
        src="actor-egyptian-islamic-jihad", tgt="actor-al-qaida", rtype="constituent_of", ring="inner", maturity=R3,
        overview="EIJ 与基地组织的关系是分阶段整合：联合国 1267 叙述描述 1998 年合并/整合（关联扎瓦希里），美国国务院历史报告描述 2001 年 6 月正式合并。ASIP 将 1998—2001 作为分阶段整合/正式化时期，明确保留两个日期，不强行归一。",
        parties=[{"entity_id": "actor-egyptian-islamic-jihad", "role": "埃及极端组织（被整合方）"},
                 {"entity_id": "actor-al-qaida", "role": "基地组织（整合目标）"}],
        formation="联合国 1267 叙述描述 EIJ 与基地组织 1998 年合并/整合，与艾曼·扎瓦希里关联；EIJ/扎瓦希里参与 1998 年世界伊斯兰阵线宣言背景进程。美国国务院历史报告描述 2001 年 6 月正式合并。两个日期反映整合进程的不同阶段。",
        initial="EIJ 与基地组织在阿富汗网络中的共存与协作先于正式合并；1998 年为整合进程开启，2001 年 6 月为正式化完成。",
        stages=[
            {"period": "1998", "detail": "联合国叙述：与基地组织合并/整合（关联扎瓦希里）；世界伊斯兰阵线宣言背景进程。"},
            {"period": "1998—2001", "detail": "分阶段整合/正式化时期（ASIP 表述）。"},
            {"period": "2001-06", "detail": "美国国务院历史报告：正式合并。"},
        ],
        causes=["扎瓦希里在基地组织领导层的角色", "EIJ 在埃及受挫后的网络化生存", "全球圣战议程对埃及伊斯兰主义分支的整合"],
        turning_points=[
            {"event": "1998 年整合（UN 表述）", "impact": "整合进程开启。", "source_ids": [S_UN_EIJ]},
            {"event": "2001-06 正式合并（State 表述）", "impact": "正式化完成。", "source_ids": [S_STATE_EIJ]},
        ],
        regional="埃及、阿富汗、巴基斯坦、苏丹 → 全球网络。",
        impact="EIJ 的整合为基地组织带来扎瓦希里等领导层人事来源，强化基地组织的埃及环节。",
        why="该关系是「双日期纪律」的核心案例：UN（1998）与 U.S. State（2001-06）均为权威叙述，ASIP 以分阶段整合处理，不制造虚假的单一日期确定性。",
        unc="两个日期的精确组织机制存在来源差异；ASIP 保留双日期并明确其叙述来源。",
        sources=[S_UN_EIJ, S_UN_AQ, S_STATE_EIJ],
        drivers=["扎瓦希里人事整合", "全球圣战网络扩张"],
        constraints=["EIJ 在埃及国内行动受挫", "整合过程中的组织自主性摩擦（以来源为准）"],
        assessment="历史关系；EIJ 作为独立组织身份已终止，融入基地组织体系。",
        asip="ASIP 判断：EIJ→基地组织的正确表述是「UN 叙述描述 1998 年合并；美国国务院历史报告描述 2001 年 6 月正式合并；ASIP 将 1998—2001 作为分阶段整合/正式化时期」。任何单日期表述都会丢失权威叙述的差异，本档案坚持双日期。",
        watch=["联合国或美国官方对 EIJ 历史叙述的更新", "基地组织领导层与埃及谱系的公开变动"],
    ),
    "rel-expc-aiai-shabaab-predecessor": rprofile(
        "rel-expc-aiai-shabaab-predecessor",
        title="AIAI ↔ 青年党：限定性意识形态/人事前身",
        src="actor-aiai", tgt="actor-al-shabaab", rtype="historically_associated_with", ring="middle", maturity=R3,
        overview="AIAI 是青年党的重要意识形态/人事前身网络：联合国专家组报告将 AIAI 描述为青年党的意识形态前驱/前驱网络，联合国综合制裁材料亦报告 AIAI 活动与并入描述。ASIP 明确：公开来源不支持把青年党的起源简化为单一的 AIAI→青年党直接组织传承。",
        parties=[{"entity_id": "actor-aiai", "role": "索马里—埃塞俄比亚伊斯兰主义网络（历史前身）"},
                 {"entity_id": "actor-al-shabaab", "role": "索马里青年党（基地组织关联组织）"}],
        formation="AIAI 约于 1982—1984 年建立，活动于索马里与埃塞俄比亚，哈桑·达希尔·阿韦斯为高级领导人。联合国专家组（S/2016/919、S/2017/924）将 AIAI 描述为青年党的意识形态前驱/前驱网络；联合国综合制裁材料报告 AIAI 在索马里/埃塞俄比亚活动并有并入青年党的描述。",
        initial="AIAI 的意识形态与人事网络为青年党生态提供来源，但青年党的形成来自更复杂的索马里伊斯兰主义/伊斯兰法院联盟（ICU）生态。",
        stages=[
            {"period": "1982—1984 起", "detail": "AIAI 建立并活动于索马里、埃塞俄比亚。"},
            {"period": "1990s—2000s", "detail": "AIAI 衰落/碎片化，人员与网络进入索马里伊斯兰主义后续生态。"},
            {"period": "2000s 后", "detail": "青年党生态形成；UN 专家组将 AIAI 定性为意识形态前驱。"},
        ],
        causes=["索马里伊斯兰主义运动的延续", "AIAI 人员网络进入后续生态", "ICU 时代的动员结构"],
        turning_points=[
            {"event": "UN 专家组 S/2016/919 定性", "impact": "官方确认 AIAI 为意识形态前驱/前驱网络。", "source_ids": [S_S2016]},
        ],
        regional="索马里、埃塞俄比亚。",
        impact="该关系解释青年党生态的意识形态与人事来源，同时防止单一组织传承的过度简化。",
        why="「意识形态/人事前身网络」的限定是该关系的核心纪律：不得写成「AIAI 直接变成青年党」。",
        unc="AIAI 并入青年党的具体机制与范围缺乏系统公开记载；AIAI 与 ICU 生态各网络的边界不清晰。",
        sources=[S_UN_AIAI, S_S2016, S_S2017, S_NCTC_SHABAAB],
        drivers=["索马里伊斯兰主义生态延续", "AIAI 人事网络流动"],
        constraints=["AIAI 衰落与碎片化的历史进程", "青年党生态的多来源结构"],
        assessment="历史关系；以限定性前身网络定性，保留 UN 归属性。",
        asip="ASIP 判断：AIAI→青年党的正确表述是「重要意识形态/人事前身网络，但公开来源不支持把青年党起源简化为单一直接组织传承」。评估索马里谱系时，应把 AIAI 放在 ICU 时代多网络生态中定位。",
        watch=["联合国专家组关于索马里网络谱系的新报告", "对青年党起源的新学术或官方研究"],
    ),
    "rel-expc-battar-isis-libya": rprofile(
        "rel-expc-battar-isis-libya",
        title="巴塔尔旅 → ISIS-利比亚：前驱融合（Wilayat Barqa）",
        src="actor-al-battar-brigade", tgt="actor-isis-libya", rtype="constituent_of", ring="inner", maturity=R3,
        overview="巴塔尔旅是 ISIS-利比亚（巴尔卡省）的前驱融合要素：联合国利比亚专家组报告称 ISIL 的巴尔卡省（Wilayat Barqa）是巴塔尔旅与伊斯兰青年协商委员会（IYSC/MSSI）在 ISIS 关联领导层下融合的结果。",
        parties=[{"entity_id": "actor-al-battar-brigade", "role": "利比亚外籍战士网络（2012 年创建，历史前驱）"},
                 {"entity_id": "actor-isis-libya", "role": "ISIS-利比亚（含 Wilayat Barqa）"}],
        formation="巴塔尔旅 2012 年创建支援叙利亚/伊拉克 ISIL；2014 年春许多成员返回利比亚，融入德尔纳武装生态；联合国专家组（S/2015/891）记载 Wilayat Barqa 为巴塔尔旅与 IYSC/MSSI 融合结果。CTC 研究描述利比亚战斗人员在叙利亚组成 Katibat al-Battar al-Libi，与 ISIS 结盟后返回。",
        initial="巴塔尔旅在叙利亚期间选择与 ISIS 结盟（ISIS 与努斯拉阵线分裂后），返回利比亚后成为德尔纳武装生态的组成要素。",
        stages=[
            {"period": "2012", "detail": "巴塔尔旅创建支援 ISIL（叙利亚/伊拉克）。"},
            {"period": "2012—2014", "detail": "在叙利亚作战，与 ISIS 结盟。"},
            {"period": "2014 年春", "detail": "许多成员返回利比亚，融入德尔纳武装生态。"},
            {"period": "2015-11", "detail": "UN 专家组记载 Wilayat Barqa 为巴塔尔旅与 IYSC/MSSI 融合结果。"},
        ],
        causes=["叙利亚内战中的外籍战士动员", "ISIS 与努斯拉阵线分裂后的结盟选择", "利比亚安全真空下的回流"],
        turning_points=[
            {"event": "2014 年春返回利比亚", "impact": "为德尔纳生态提供人员基础。", "source_ids": [S_CTC]},
            {"event": "Wilayat Barqa 融合（UN 专家组）", "impact": "ISIS-利比亚巴尔卡省形成。", "source_ids": [S_S2015_891]},
        ],
        regional="叙利亚/伊拉克 → 利比亚（德尔纳）。",
        impact="该关系解释 ISIS-利比亚的融合起源，是利比亚 ISIS 谱系的关键前驱链。",
        why="巴塔尔旅作为历史前驱而非当前分支的定位是核心纪律；Wilayat Barqa 是融合结果而非简单改名。",
        unc="返回利比亚的确切人数与融合机制的细节缺乏系统公开统计。",
        sources=[S_S2015_891, S_CTC],
        drivers=["外籍战士回流", "德尔纳武装生态", "ISIS 关联领导层的整合"],
        constraints=["利比亚安全力量与地方生态的压制", "ISIS-利比亚后续的收缩"],
        assessment="历史前驱关系；巴塔尔旅作为独立网络已被吸收进 ISIS 利比亚前驱生态。",
        asip="ASIP 判断：巴塔尔旅的档案价值是「融合前驱」——Wilayat Barqa 是巴塔尔旅与 IYSC/MSSI 在 ISIS 关联领导层下融合的产物。评估时必须保持时间与实体区分：巴塔尔旅是 2012—2014 年的历史网络，不等于 Wilayat Barqa 本身。",
        watch=["联合国利比亚专家组新报告", "对利比亚 ISIS 起源的新研究"],
    ),
    "rel-expc-mujao-murabitun": rprofile(
        "rel-expc-mujao-murabitun",
        title="MUJAO → 穆拉比通：2013 年合并谱系",
        src="actor-mujao", tgt="actor-al-mourabitoun", rtype="historically_associated_with", ring="middle", maturity=R3,
        overview="穆拉比通于 2013 年由贝尔穆赫塔尔（Mokhtar Belmokhtar）的 al-Mulathamun 营与另一个 AQIM 分裂派别（通常认定为 MUJAO/西非认主独一与圣战）合并而成（NCTC 表述）。MUJAO 是穆拉比通合并的组成来源之一，其独立组织身份由此并入；该合并构成 AQIM 分裂 → MUJAO → 穆拉比通 → JNIM 网络谱系链的中间环节。",
        parties=[{"entity_id": "actor-mujao", "role": "萨赫勒武装派别（合并来源）"},
                 {"entity_id": "actor-al-mourabitoun", "role": "穆拉比通（2013 年合并结果）"}],
        formation="NCTC 历史材料称 al-Murabitun 于 2013 年由 al-Mulathamun 营与 MUJAO/认主独一圣战派别合并形成；联合国将 MUJAO 列为与 AQIM 和贝尔穆赫塔尔相关的组织。合并发生在马里北部武装格局再组合时期：穆拉比通以基地组织阵营定位，与萨赫勒 ISIS 阵营形成竞争。由于本体无 merged_into 类型，ASIP 以 historically_associated_with 表达合并谱系，机制写入本档案。",
        initial="MUJAO 作为 AQIM 分裂派别运作后，与 al-Mulathamun 营合并组建穆拉比通。",
        stages=[
            {"period": "2012 前后", "detail": "MUJAO 作为 AQIM 分裂派别运作。"},
            {"period": "2013", "detail": "与 al-Mulathamun 营合并组建穆拉比通（NCTC）。"},
            {"period": "2013 后", "detail": "穆拉比通以基地组织阵营定位运作，2017 年并入 JNIM。"},
        ],
        causes=["萨赫勒武装格局再组合", "贝尔穆赫塔尔网络的整合", "马里北部冲突背景"],
        turning_points=[
            {"event": "2013 年合并", "impact": "穆拉比通成立，MUJAO 独立身份终止。", "source_ids": [S_NCTC_MURAB]},
        ],
        regional="萨赫勒/撒哈拉（马里北部）。",
        impact="该关系补全 AQIM 分裂 → MUJAO → 穆拉比通 → JNIM 网络的谱系链。",
        why="MUJAO 的谱系意义在于作为穆拉比通合并来源；合并语义通过档案说明，不扩展 ontology。",
        unc="MUJAO 与认主独一圣战派别之间的确切关系存在来源差异；合并细节缺乏统一权威记载。",
        sources=[S_NCTC_MURAB, S_UN_AQIM],
        drivers=["萨赫勒武装整合", "贝尔穆赫塔尔网络的领导"],
        constraints=["马里安全环境压力", "ISIS 阵营竞争"],
        assessment="历史合并谱系关系；MUJAO 独立身份已并入穆拉比通→JNIM 网络。",
        asip="ASIP 判断：MUJAO 的价值是谱系中间节点。由于 ontology 无 merged_into，本关系以 historically_associated_with 建模并以档案说明 2013 年合并机制——这是「用 profile 解释具体语义」的既定纪律。",
        watch=["NCTC/UN 对 MUJAO 历史叙述的更新", "穆拉比通/JNIM 体系相关变动"],
    ),
    "rel-expc-gicm-alqaida": rprofile(
        "rel-expc-gicm-alqaida",
        title="GICM ↔ 基地组织：历史关联（阿富汗一代）",
        src="actor-gicm", tgt="actor-al-qaida", rtype="historically_associated_with", ring="middle", maturity=R3,
        overview="GICM 与基地组织存在历史关联：联合国因与基地组织关联于 2002 年列名 GICM，美国国务院历史报告称其与基地组织有联系。该关联源于 GICM 成员在阿富汗基地组织训练营的经历，是阿富汗一代北非网络与基地组织关系的典型案例；2007 年国务院评估 GICM 解体后，该关联仅具历史意义。",
        parties=[{"entity_id": "actor-gicm", "role": "摩洛哥伊斯兰战斗组织（历史网络）"},
                 {"entity_id": "actor-al-qaida", "role": "基地组织"}],
        formation="GICM 于 1990 年代从阿富汗基地组织训练营的摩洛哥招募者中兴起；联合国 2002 年因与基地组织关联列名；美国国务院历史报告描述 GICM 为与基地组织有联系。2007 年国务院评估 GICM 解体后，该历史关联不再对应活跃组织关系。",
        initial="GICM 的形成即依托阿富汗训练营网络，与基地组织的关联是其组织起源的一部分。",
        stages=[
            {"period": "1990 年代", "detail": "从阿富汗基地组织训练营的摩洛哥招募者中兴起。"},
            {"period": "2002-10", "detail": "联合国因与基地组织关联列名 GICM。"},
            {"period": "2007", "detail": "美国国务院评估 GICM 解体。"},
        ],
        causes=["阿富汗一代训练网络", "基地组织的招募与网络整合", "摩洛哥圣战环境"],
        turning_points=[
            {"event": "2002 年联合国列名", "impact": "确认与基地组织关联。", "source_ids": [S_UN_GICM]},
            {"event": "2007 年解体评估", "impact": "历史关联不再对应活跃组织。", "source_ids": [S_STATE_GICM_2007]},
        ],
        regional="阿富汗 → 摩洛哥/欧洲。",
        impact="该关系记录阿富汗一代摩洛哥网络与基地组织的训练营联系及列名依据；其历史影响体现在摩洛哥反恐叙事与欧洲袭击相关指认的网络背景中，为理解阿富汗一代北非网络的跨国转化提供案例。",
        why="GICM 与基地组织的关联是其组织定义的一部分（联合国列名依据），也是理解马德里相关指认（国务院历史报告归属性表述）的网络背景；该关联同时说明阿富汗训练营网络如何转化为跨国袭击相关网络，是评估 GICM 历史角色的核心线索。",
        unc="GICM 与基地组织之间的组织化程度缺乏系统公开记载。",
        sources=[S_UN_GICM, S_STATE_GICM_2002, S_STATE_GICM_2007],
        drivers=["阿富汗一代动员", "基地组织网络整合"],
        constraints=["摩洛哥与欧洲的打击", "组织内部碎片化"],
        assessment="历史关联关系；GICM 已解体，关联仅具历史意义。",
        asip="ASIP 判断：GICM↔基地组织的关联以联合国列名与国务院历史报告为据，属归属性表述。评估时注意：与基地组织的关联不等于 GICM 对马德里袭击的定罪——马德里指认是国务院历史报告的归属性叙述。",
        watch=["联合国或官方对 GICM 列名或历史叙述的更新"],
    ),
    "rel-expc-tcg-alqaida": rprofile(
        "rel-expc-tcg-alqaida",
        title="TCG ↔ 基地组织：历史关联（训练营地）",
        src="actor-tunisian-combatant-group", tgt="actor-al-qaida", rtype="historically_associated_with", ring="middle", maturity=R3,
        overview="TCG 与基地组织存在历史关联：联合国叙述称 TCG 成员与阿富汗基地组织相关营地有联系。该关联构成 TCG 跨国网络结构的核心——连接阿富汗训练经历、欧洲后勤运作与突尼斯政治目标——也是联合国 2002 年列名的网络背景。",
        parties=[{"entity_id": "actor-tunisian-combatant-group", "role": "突尼斯战斗组织（历史网络）"},
                 {"entity_id": "actor-al-qaida", "role": "基地组织"}],
        formation="TCG 于 2000 年创建，成员与阿富汗基地组织相关营地有联系；联合国 2002 年列名 TCG（及关联人物塔里克·阿尔-马鲁菲），将其置于基地组织网络背景下。该关联的性质是训练营地联系与网络归属，而非正式效忠；欧洲多国调查随后严重打击其关联网络，使组织能力显著受损。",
        initial="TCG 成员的阿富汗训练营地联系先于其组织化活动，构成与基地组织的网络关联基础。",
        stages=[
            {"period": "2000", "detail": "TCG 创建。"},
            {"period": "2002-10", "detail": "联合国列名 TCG 及阿尔-马鲁菲。"},
            {"period": "2000 年代", "detail": "欧洲调查打击关联网络。"},
        ],
        causes=["阿富汗一代训练网络", "北非跨国网络结构", "欧洲后勤联系"],
        turning_points=[
            {"event": "2002 年联合国列名", "impact": "确认基地组织网络背景。", "source_ids": [S_UN_TCG]},
        ],
        regional="突尼斯/阿富汗/欧洲。",
        impact="该关系记录北非阿富汗一代网络与基地组织的训练营地联系，是 TCG 跨国网络结构的核心——训练经历、欧洲后勤与突尼斯政治目标由此连成一体；其历史影响体现在北非反恐格局与后来突尼斯极端主义生态的谱系背景中。",
        why="训练营地联系是 TCG 组织定义的一部分（列名依据），也是理解其跨国网络结构的钥匙。",
        unc="TCG 成员在阿富汗营地的具体训练角色记载有限。",
        sources=[S_UN_TCG, S_UN_MAAROUFI, S_STATE_TCG],
        drivers=["阿富汗一代动员", "跨国后勤网络"],
        constraints=["欧洲调查打击", "组织能力受挫"],
        assessment="历史关联关系；TCG 已严重受挫，关联仅具历史意义。",
        asip="ASIP 判断：TCG↔基地组织的关联以训练营地联系与联合国列名为据。评估时注意：该关联不等于正式效忠，也不等于 TCG 与后来突尼斯极端组织的身份同一。",
        watch=["联合国或官方对 TCG 列名或历史叙述的更新"],
    ),
    "rel-expc-aqim-mujao-split": rprofile(
        "rel-expc-aqim-mujao-split",
        title="AQIM → MUJAO：萨赫勒分裂派别",
        src="actor-mujao", tgt="actor-aqim", rtype="split_from", ring="middle", maturity=R3,
        overview="MUJAO 是从 AQIM 分裂的萨赫勒武装派别；联合国将 MUJAO 列为与 AQIM 和穆赫塔尔·贝尔穆赫塔尔相关的组织。该分裂处于 2010 年代初期马里北部武装格局扩张的背景中，并构成后来穆拉比通合并的前置。",
        parties=[{"entity_id": "actor-aqim", "role": "AQIM（母体，基地组织附属）"},
                 {"entity_id": "actor-mujao", "role": "MUJAO（分裂派别）"}],
        formation="MUJAO 属于从 AQIM 分裂的萨赫勒武装派别；NCTC 历史材料将其定位为后来穆拉比通（2013）合并的组成部分。分裂的驱动包括萨赫勒行动空间的吸引与组织路线分化。",
        initial="MUJAO 成立后以萨赫勒/撒哈拉为主要行动舞台，属马里北部武装伊斯兰主义格局一部分。",
        stages=[
            {"period": "2010 年代初期", "detail": "MUJAO 作为 AQIM 分裂派别运作。"},
            {"period": "2012 前后", "detail": "参与马里北部武装格局相关进程。"},
            {"period": "2013", "detail": "与 al-Mulathamun 营合并组建穆拉比通，独立身份终止。"},
        ],
        causes=["萨赫勒行动空间吸引力", "AQIM 内部路线分化", "马里北部冲突背景"],
        turning_points=[
            {"event": "分裂成立", "impact": "AQIM 萨赫勒体系首次主要分裂。", "source_ids": [S_NCTC_MURAB]},
        ],
        regional="萨赫勒/撒哈拉（马里北部）。",
        impact="该关系是 AQIM 体系分裂史的一部分，是后续 MUJAO → 穆拉比通 → JNIM 谱系的前置。",
        why="AQIM → MUJAO → 穆拉比通 → JNIM 是内容包要求的核心谱系链；分裂关系是链条起点。",
        unc="分裂的确切时间与内部过程缺乏统一权威记载。",
        sources=[S_UN_AQIM, S_NCTC_MURAB],
        drivers=["萨赫勒行动空间", "路线分化"],
        constraints=["AQIM 体系凝聚力", "马里安全环境"],
        assessment="历史分裂关系；MUJAO 独立身份已并入穆拉比通→JNIM 网络。",
        asip="ASIP 判断：MUJAO 分裂自 AQIM 是谱系事实，但其后立即（2013）并入穆拉比通，独立窗口期有限。评估时应把分裂与合并作为同一再组合进程的两端，而非两个独立事件。",
        watch=["NCTC/UN 对 MUJAO 历史叙述的更新"],
    ),
    "rel-expc-aqim-ansar-relation": rprofile(
        "rel-expc-aqim-ansar-relation",
        title="AQIM ↔ 安萨尔埃丁：2012—2017 关联（马里北部格局）",
        src="actor-aqim", tgt="actor-ansar-eddine", rtype="affiliated_with", ring="middle", maturity=R3,
        overview="安萨尔埃丁自 2012 年中期起与 AQIM 建立关联（NCTC）；该关联处于马里北部 2012 年政变后的武装格局中，双方在北部控制时期存在协调。2017 年双方并入 JNIM 后，双边关联让位于 JNIM 体系内构成关系。",
        parties=[{"entity_id": "actor-aqim", "role": "AQIM（基地组织附属，马里北部参与者）"},
                 {"entity_id": "actor-ansar-eddine", "role": "安萨尔埃丁（2011 年成立，马里北部武装）"}],
        formation="NCTC 确认安萨尔埃丁自 2012 年中期起与 AQIM 存在关联；双方在马里北部武装伊斯兰主义格局中的协调是理解 2012—2013 年北部控制的关键背景。2013 年法国干预后格局改变，2017 年双方均并入 JNIM。",
        initial="2012 年政变后马里北部权力真空期，安萨尔埃丁与 AQIM 的协调表现为对北部领土控制格局的共同参与。",
        stages=[
            {"period": "2012 年中期", "detail": "与 AQIM 建立关联。"},
            {"period": "2012—2013", "detail": "马里北部控制时期的协调。"},
            {"period": "2013", "detail": "法国干预后格局改变。"},
            {"period": "2017-03", "detail": "双方并入 JNIM，双边关联让位于体系内构成关系。"},
        ],
        causes=["马里北部权力真空", "武装伊斯兰主义格局扩张", "JNIM 整合进程"],
        turning_points=[
            {"event": "2012 年中期关联建立", "impact": "双方进入协调状态。", "source_ids": [S_NCTC_AAD]},
            {"event": "2017 年并入 JNIM", "impact": "双边关联转为体系内构成。", "source_ids": [S_NCTC_AAD]},
        ],
        regional="马里北部。",
        impact="该关系解释 2012—2013 年马里北部格局中 AQIM 与安萨尔埃丁的协作，以及两者共同并入 JNIM 的前置结构。",
        why="内容包明确要求 Ansar al-Dine ↔ AQIM 关系档案；该关系是理解马里北部武装格局与 JNIM 前史的关键。",
        unc="双方协调的具体机制与指挥边界缺乏系统公开披露。",
        sources=[S_NCTC_AAD, S_NCTC_AQIM],
        drivers=["北部权力真空", "武装格局整合"],
        constraints=["法国干预", "国际反恐压力"],
        assessment="历史关联关系（2012—2017）；2017 年后转为 JNIM 体系内构成。",
        asip="ASIP 判断：AQIM 与安萨尔埃丁的关联是「格局内协调」而非正式隶属：两者在 2012—2013 年北部控制时期共同参与武装格局，但保持独立组织身份直至 2017 年并入 JNIM。评估时不应把关联写为从属关系。",
        watch=["JNIM 体系内安萨尔埃丁与 AQIM 谱系的公开变动"],
    ),
    "rel-expc-maitatsine-nigeria": rprofile(
        "rel-expc-maitatsine-nigeria",
        title="迈塔齐尼运动：尼日利亚北部的历史活动",
        src="actor-maitatsine-movement", tgt="country-nigeria", rtype="operates_in", ring="middle", maturity=R1,
        overview="迈塔齐尼运动的历史活动集中于尼日利亚北部（卡诺为核心），1980—1985 年发生多起相关起义。",
        parties=[{"entity_id": "actor-maitatsine-movement", "role": "历史宗教好战运动（1980 年代）"},
                 {"entity_id": "country-nigeria", "role": "尼日利亚（活动国）"}],
        formation="运动的核心地理为尼日利亚北部城市环境；1980 年 12 月卡诺重大对抗及 1982、1984、1985 年相关起义构成其历史活动主体。",
        initial="运动的动员依托卡诺等北部城市的宗教教导与社会经济不满。",
        stages=[
            {"period": "1980-12", "detail": "卡诺重大对抗/起义。"},
            {"period": "1982/1984/1985", "detail": "尼日利亚北部相关起义。"},
        ],
        causes=["城市社会经济的紧张", "宗教教导的动员", "国家回应"],
        turning_points=[],
        regional="尼日利亚北部。",
        impact="该关系仅记录历史地理活动；明确不构成任何指向博科哈拉姆的组织传承。",
        why="operates_in 仅表达历史地理活动；本档案坚持「比较≠传承」纪律，不建立谱系边。",
        unc="运动在各起义地点的具体组织程度缺乏系统统计。",
        sources=["expc-adesoji-maitatsine", "expc-hiskett-maitatsine"],
        drivers=["宗教与社会经济动员"],
        constraints=["国家镇压"],
        assessment="历史活动关系（1980—1985）。",
        asip="ASIP 判断：迈塔齐尼与尼日利亚的关系仅是历史地理活动记录；任何把该运动写成博科哈拉姆前身的尝试都违反无直接组织传承的事实纪律。",
        watch=["尼日利亚宗教好战研究的新学术文献"],
    ),
}

# ---------------------------------------------------------------------------
# Relation timeline entries for the NEW R3 dossiers
# ---------------------------------------------------------------------------
NEW_RELATION_TIMELINES = {
    "rel-expc-gia-aqim-lineage": [
        tl("1998", "哈塔布自 GIA 分裂创立 GSPC", "哈桑·哈塔布在阿尔及利亚创立萨拉菲宣教与战斗组织（GSPC），作为 GIA 的分裂派别。", "GSPC/AQIM 谱系开启。", "high", [S_UN_GIA]),
        tl("2001-10-06", "联合国以 GSPC 名称列名", "联合国 1267 机制以 GSPC 名称列名该实体。", "国际列名记录以 GSPC 名称为准。", "high", [S_UN_GIA]),
        tl("2006-09-11", "基地组织宣布联合/联盟", "基地组织领导层宣布与 GSPC 联合/联盟；NCTC 描述 GSPC 结盟。", "连续体纳入基地组织网络。", "high", [S_NCTC_AQIM]),
        tl("2007-01", "GSPC 更名 AQIM", "GSPC 采用 AQIM（伊斯兰马格里布基地组织）名称。", "谱系更名完成，GIA→GSPC→AQIM 连续体成型。", "high", [S_NCTC_AQIM]),
    ],
    "rel-expc-aqim-alqaida-alignment": [
        tl("2006-09-11", "基地组织宣布联合/联盟", "基地组织领导层宣布与 GSPC 联合/联盟。", "GSPC/AQIM 纳入基地组织网络。", "high", [S_NCTC_AQIM]),
        tl("2007-01", "更名 AQIM", "GSPC 采用 AQIM 名称。", "以基地组织名义正式运作。", "high", [S_NCTC_AQIM]),
        tl("2026", "NCTC 仍列 AQIM 为基地组织附属", "NCTC 2026 年 6 月档案仍将 AQIM 描述为活跃基地组织附属组织。", "结盟关系延续至当前。", "high", [S_NCTC_AQIM]),
    ],
    "rel-expc-eij-alqaida-integration": [
        tl("1998", "UN 叙述：与基地组织合并/整合", "联合国 1267 叙述描述 EIJ 与基地组织 1998 年合并/整合（关联扎瓦希里）；EIJ/扎瓦希里参与世界伊斯兰阵线宣言背景进程。", "整合进程开启（UN 表述）。", "medium_high", [S_UN_EIJ], disputed=True),
        tl("2001-06", "美国国务院：正式合并", "美国国务院历史报告描述 EIJ 于 2001 年 6 月与基地组织正式合并。", "正式化完成（State 表述）。", "medium_high", [S_STATE_EIJ], disputed=True),
        tl("此后", "独立组织身份终止", "EIJ 作为独立组织身份终止，融入基地组织体系。", "组织谱系并入基地组织。", "high", [S_UN_AQ]),
    ],
    "rel-expc-aiai-shabaab-predecessor": [
        tl("1982—1984", "AIAI 建立", "AIAI 约于此间建立，寻求与其他组织一同推翻索马里政府。", "索马里伊斯兰主义谱系早期节点。", "medium_high", [S_UN_AIAI]),
        tl("1990s—2000s", "AIAI 衰落/碎片化", "AIAI 网络衰落与碎片化，人员进入索马里伊斯兰主义后续生态。", "为青年党生态提供人员/意识形态来源。", "medium_high", [S_S2016]),
        tl("2016-11", "UN 专家组定性前驱", "S/2016/919 将 AIAI 描述为青年党的意识形态前驱/前驱网络。", "官方确认限定性前身关系。", "high", [S_S2016]),
        tl("2017-11", "UN 综合材料再确认", "S/2017/924 记录 AIAI 活动及并入描述，同时不简化青年党起源。", "限定性前身定性延续。", "high", [S_S2017]),
    ],
    "rel-expc-battar-isis-libya": [
        tl("2012", "巴塔尔旅创建", "巴塔尔旅创建以支援叙利亚和伊拉克的 ISIL。", "ISIS 利比亚谱系的外籍战士源头。", "high", [S_S2015_891]),
        tl("2014 年春", "成员返回利比亚", "许多成员返回利比亚，融入德尔纳武装生态。", "为德尔纳生态提供人员基础。", "medium_high", [S_S2015_891, S_CTC]),
        tl("2015-11", "Wilayat Barqa 融合记载", "UN 利比亚专家组记载 Wilayat Barqa 为巴塔尔旅与 IYSC/MSSI 融合结果。", "ISIS-利比亚巴尔卡省形成确认。", "high", [S_S2015_891]),
    ],
    "rel-expc-mujao-murabitun": [
        tl("2012 前后", "MUJAO 作为 AQIM 分裂派别运作", "MUJAO 在萨赫勒/撒哈拉运作，属马里北部武装格局。", "AQIM 分裂谱系的中间节点。", "medium_high", [S_UN_AQIM]),
        tl("2013", "与 al-Mulathamun 营合并组建穆拉比通", "NCTC 材料称穆拉比通由 al-Mulathamun 营与 MUJAO/认主独一圣战派别合并形成。", "MUJAO 独立身份终止，并入穆拉比通。", "medium_high", [S_NCTC_MURAB]),
        tl("2017-03", "穆拉比通并入 JNIM", "穆拉比通作为四支组成组织之一并入 JNIM。", "谱系延续至 JNIM 网络。", "high", [S_UN_JNIM]),
    ],
    "rel-expc-aqim-ansar-relation": [
        tl("2012 年中期", "安萨尔埃丁与 AQIM 建立关联", "NCTC 确认安萨尔埃丁自 2012 年中期起与 AQIM 存在关联。", "马里北部武装格局中的协作开始。", "high", [S_NCTC_AAD]),
        tl("2013", "法国干预后北部控制结束", "2013 年法国军事干预使安萨尔埃丁撤离北部据点。", "双边协作的北部控制背景结束。", "high", [S_NCTC_AAD]),
        tl("2017-03", "双方并入 JNIM", "安萨尔埃丁与 AQIM 萨赫勒分支均并入 JNIM。", "双边关联让位于 JNIM 体系内结构。", "high", [S_UN_JNIM]),
    ],
    "rel-expc-gicm-alqaida": [
        tl("1990 年代", "GICM 自阿富汗训练营兴起", "GICM 从阿富汗基地组织训练营的摩洛哥招募者中兴起。", "与基地组织的关联始于组织起源。", "medium_high", [S_UN_GICM]),
        tl("2002-10", "联合国列名", "联合国因与基地组织关联列名 GICM。", "关联获官方确认。", "high", [S_UN_GICM]),
        tl("2007", "解体评估", "美国国务院评估 GICM 已解体。", "历史关联不再对应活跃组织。", "high", [S_STATE_GICM_2007]),
    ],
    "rel-expc-tcg-alqaida": [
        tl("2000", "TCG 创建", "TCG 由哈辛及相关人物创建，成员与阿富汗营地有联系。", "北非阿富汗一代网络节点形成。", "medium_high", [S_UN_TCG]),
        tl("2002-10", "联合国列名", "联合国列名 TCG 及关联人物阿尔-马鲁菲。", "与基地组织的网络关联获官方记录。", "high", [S_UN_TCG]),
        tl("2000 年代", "欧洲调查打击", "欧洲多国调查严重打击 TCG 关联网络。", "组织能力严重受损。", "medium_high", [S_UN_MAAROUFI]),
    ],
    "rel-expc-aqim-mujao-split": [
        tl("2010 年代初期", "MUJAO 自 AQIM 分裂", "MUJAO 作为 AQIM 分裂派别在萨赫勒/撒哈拉运作。", "AQIM 萨赫勒体系首次主要分裂。", "medium_high", [S_NCTC_MURAB]),
        tl("2012 前后", "马里北部格局参与", "MUJAO 参与马里北部武装格局相关进程。", "武装格局中的活跃节点。", "medium_high", [S_UN_AQIM]),
        tl("2013", "并入穆拉比通", "MUJAO 与 al-Mulathamun 营合并组建穆拉比通。", "独立身份终止，谱系并入穆拉比通。", "medium_high", [S_NCTC_MURAB]),
    ],
    "rel-expc-maitatsine-nigeria": [
        tl("1980-12", "卡诺重大对抗", "迈塔齐尼运动在卡诺发生重大对抗/起义。", "运动最突出的历史事件。", "high", ["expc-hiskett-maitatsine"]),
        tl("1982", "相关起义", "尼日利亚北部发生与迈塔齐尼相关的起义。", "运动延续。", "medium_high", ["expc-isichei-maitatsine"]),
        tl("1984", "相关暴力", "尼日利亚北部相关暴力事件。", "运动延续。", "medium_high", ["expc-isichei-maitatsine"]),
        tl("1985", "相关起义", "尼日利亚北部相关起义。", "运动历史活动末期。", "medium_high", ["expc-isichei-maitatsine"]),
    ],
}
