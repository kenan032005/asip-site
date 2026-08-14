# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-E — entity content module (regional security actors).

Source of truth: ASIP-PPT-ENTITY-EXPANSION-E-Authoritative-Content-Pack.md.
No independent research; classification/status judgments are locked by the pack.
"""
TODAY = "2026-08-14"
IMPORTER = "expansion-e"


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
        "claim_valid_as_of": TODAY, "freshness_status": "historical" if status.startswith(("historical", "closed", "ceased")) else "current",
        "verification_status": "pending_review", "current_status_verified_at": TODAY,
        "freshness_reviewed_by": IMPORTER,
    }


def _prof(sections, importance="L2", completeness="Expansion E 内容包深度审计 · 百科式"):
    return {
        "profile_depth": "encyclopedia_full", "profile_level": "encyclopedia_full",
        "content_maturity": "E3_FULL_ENCYCLOPEDIA", "completeness": completeness,
        "importance_level": importance, "sections": sections,
    }


ORG_ENTITIES = [
    # ============================================================ G5 Sahel Joint Force (HISTORICAL)
    _ent(
        "actor-g5-sahel-joint-force", "g5-sahel-joint-force", "萨赫勒五国联合部队", "G5 Sahel Joint Force", "FC-G5S",
        "regional_force", "L2", "ceased_operations",
        "萨赫勒五国集团（G5 Sahel）联合部队，2017 年建立、2014 年政治框架，属历史性区域反恐力量；马里 2022 年退出、布基纳法索与尼日尔 2023 年退出后，毛里塔尼亚与乍得推动解散程序，至 2024 年底已停止运作。",
        "FC-G5S 是理解萨赫勒区域反恐机制兴衰的关键历史样本。建模纪律：其状态为 historical / ceased_operations，不得显示为 2026 年现役力量；AES 统一部队是后来出现的政治上不同的机制，不得写成 FC-G5S 的法定继承者。",
        aliases=["Force Conjointe du G5 Sahel", "G5 Sahel Force"],
        historical=[], primary_category="historical_regional_counterterrorism_force",
        region_ids=["region-central-sahel"],
        source_refs=["expe-un-sc15950-g5", "d1-iss-aes-2026-03-04"],
        secondary=["regional_counterterrorism_force"],
    ),
    # ============================================================ ECOWAS Standby Force
    _ent(
        "actor-ecowas-standby-force", "ecowas-standby-force", "西非国家经济共同体待命部队", "ECOWAS Standby Force", "ESF",
        "regional_force", "L2", "active_framework",
        "西非国家经济共同体（ECOWAS）框架下的区域待命部队，正在推进反恐力量的生成与战备；2025 年提出 26 万人概念、5000 人旅选项与 1650 人分阶段快速部署/反恐核心等多种兵力方案，2026 年处于战备检查与力量生成阶段。",
        "ESF 的建模纪律：不得写成“ECOWAS 现役 26 万人反恐军队”。必须区分 26 万概念（2025）、5000 人旅选项、1650 人分阶段快速部署/反恐核心、2026 年战备与力量生成进程；当前判断为 operationalizing / force_generation，而非已完全部署的区域作战力量。",
        aliases=["ECOWAS counterterrorism force", "ECOWAS Regional Counterterrorism Force"],
        historical=[], primary_category="regional_standby_force",
        region_ids=["region-coastal-west-africa-spillover"],
        source_refs=["expe-ecowas-ccds-43", "expe-ecowas-ministers-funding", "expe-ecowas-esf-readiness"],
        secondary=["regional_standby_force"],
    ),
    # ============================================================ AFRICOM
    _ent(
        "actor-africom", "africom", "美国非洲司令部", "United States Africa Command", "AFRICOM",
        "state_security_force", "L2", "active",
        "美国非洲司令部（AFRICOM），美国国防部六大地理作战司令部之一，负责美国在非洲的军事行动、反恐打击与伙伴能力建设；2026 年继续对索马里青年党与 ISIS-Somalia 实施空袭，并主持 Flintlock 2026 多国演习。",
        "AFRICOM 是理解美国在非洲反恐介入的核心节点。建模纪律：AFRICOM 不指挥 AUSSOM、SNAF 或邦特兰安全部队，不得创建错误指挥边；对利比亚武装仅限训练/演习合作；对青年党与 ISIS-Somalia 为直接打击（hostile/direct strikes）。",
        aliases=["U.S. Africa Command", "United States Africa Command"],
        historical=[], primary_category="external_military_command",
        region_ids=["region-sudan-red-sea-horn"],
        source_refs=["expe-africom-flintlock-26"],
        secondary=["external_military_command"],
    ),
    # ============================================================ MINUSMA (HISTORICAL)
    _ent(
        "actor-minusma", "minusma", "联合国马里多层面综合稳定团", "United Nations Multidimensional Integrated Stabilization Mission in Mali", "MINUSMA",
        "un_peacekeeping_mission", "L2", "closed_2023",
        "联合国马里多层面综合稳定团（MINUSMA），联合国在马里的维和/稳定任务，2023-06-30 授权终止、2023-12-31 撤出完成，属历史性联合国维和任务。",
        "MINUSMA 的建模纪律：状态为 closed_2023 / historical，不得显示为 active。任务角色包括平民保护、和平进程支持、2015 年协议支持、停火监测与国家权威恢复；其撤出后的安全真空是理解马里北部当前武装格局的背景。",
        aliases=["UN Multidimensional Integrated Stabilization Mission in Mali", "Mission multidimensionnelle intégrée des Nations Unies pour la stabilisation au Mali"],
        historical=[], primary_category="historical_un_peacekeeping_mission",
        region_ids=["region-central-sahel"],
        source_refs=["expe-un-minusma-termination", "expe-un-res2690"],
        secondary=["un_peacekeeping_mission"],
    ),
]

ORG_PROFILES = {
    # ============================================================ G5 Sahel Joint Force
    "actor-g5-sahel-joint-force": _prof({
        "lead": "萨赫勒五国联合部队（Force Conjointe du G5 Sahel，FC-G5S）是 G5 Sahel 政治框架下的区域反恐力量，2017 年建立。其成员国马里 2022 年退出、布基纳法索与尼日尔 2023 年退出后，毛里塔尼亚与乍得随后推动解散程序；联合国至 2024 年底已将其描述为停止运作。该力量属历史性区域反恐机制，而非 2026 年现役力量。",
        "name_and_translation": "中文名称为“萨赫勒五国联合部队”，英文名称 G5 Sahel Joint Force，缩写 FC-G5S。历史语境指布基纳法索、乍得、马里、毛里塔尼亚、尼日尔五国的 G5 Sahel 框架联合部队。",
        "background": "G5 Sahel 政治框架于 2014 年由布基纳法索、乍得、马里、毛里塔尼亚与尼日尔建立；2017 年在此基础上建立联合部队，承担跨境反恐与安全任务。",
        "history": [
            "2014：G5 Sahel 政治框架建立（五国）。",
            "2017：联合部队（FC-G5S）建立。",
            "2022：马里退出。",
            "2023：布基纳法索与尼日尔退出。",
            "2023 后：毛里塔尼亚与乍得推动解散程序。",
            "2024 底：联合国报道描述联合部队停止运作。",
        ],
        "formation_background": "在萨赫勒跨境圣战威胁上升的背景下，五国以联合部队形式协调跨境反恐；其架构依赖成员国部队贡献与国际支持/融资。",
        "structure": "联合部队由成员国部队贡献构成，设联合指挥架构；其跨境作战能力受限于成员国政治协作与融资的持续争议。",
        "geography": "萨赫勒五国交界地带，尤其马里—布基纳法索—尼日尔三国边境区。",
        "operations": "承担跨境反恐巡逻与行动；在成员国相继退出后，行动能力逐步萎缩直至停止。",
        "external_relations": "与联合国、欧盟、法国 Barkhane 行动及国际融资方存在支持/协调关系；与 JNIM、IS Sahel 等圣战组织为敌对关系（历史）。",
        "current_status": "已停止运作（ceased_operations）。非现役力量。",
        "institutional_legacy": "FC-G5S 的兴衰为理解萨赫勒区域反恐机制的制度性失败提供了样本；其与后来的 AES 统一部队是政治上不同的机制，后者非其法定继承者。",
        "relationship_aes": "AES 统一部队是 2023 年后萨赫勒国家联盟（AES）在 G5 框架瓦解后建立的新机制，与 FC-G5S 无法律继承关系；二者应区分处理，不写成“AES = G5 的合法继承”。",
        "major_timeline": [
            "2014：G5 Sahel 框架建立。",
            "2017：联合部队建立。",
            "2022：马里退出。",
            "2023：布基纳法索、尼日尔退出。",
            "2024 底：停止运作。",
        ],
        "uncertainties": "解散程序与资产/人员处置的最终状态缺乏逐项公开披露；FC-G5S 是否以任何形式转入 AES 架构无权威确认。",
        "asip_analysis": "ASIP 判断：FC-G5S 是区域反恐机制在成员国政治分歧与融资不足下失败的典型样本。评估萨赫勒安全格局时，必须将其作为历史机制处理，并将 AES 统一部队作为新的、政治上不同的机制单独评估，避免把二者写成继承关系。",
        "watch_indicators": [
            "FC-G5S 剩余资产/机制是否正式清算",
            "AES 统一部队是否继承 FC-G5S 的任何结构或人员",
        ],
        "sources": [
            "UN SC/15950 (Dec 2024) — https://press.un.org/en/2024/sc15950.doc.htm",
            "ISS: Will the AES Unified Force succeed — https://issafrica.org/iss-today/will-the-aes-unified-force-succeed-where-the-g5-sahel-failed",
        ],
        "capabilities": "FC-G5S 的作战能力依赖成员国部队贡献与国际融资，其跨境行动受成员国政治协作与装备短缺的持续制约；解散前未能形成稳定的区域反恐战斗力。",
        "constraints": "成员国相继退出（马里 2022、布基纳法索与尼日尔 2023）是 FC-G5S 瓦解的直接原因；融资争议与国际支持的不可持续也是关键约束。",
        "dissolution": "马里、布基纳法索、尼日尔退出后，毛里塔尼亚与乍得推动解散程序；联合国 2024 年底报道确认联合部队停止运作。",
    }, importance="L2"),

    # ============================================================ ECOWAS Standby Force
    "actor-ecowas-standby-force": _prof({
        "lead": "西非国家经济共同体待命部队（ECOWAS Standby Force，ESF）是 ECOWAS 框架下的区域待命与反恐力量。其公开规划经历了 2025 年 26 万人概念、5000 人旅选项、1650 人分阶段快速部署/反恐核心等方案，2026 年仍处于战备检查与力量生成（force_generation）阶段，尚未成为已完全部署的区域作战力量。",
        "name_and_translation": "中文名称为“西非国家经济共同体待命部队”，英文名称 ECOWAS Standby Force，缩写 ESF。",
        "background": "ECOWAS 安全架构以非洲待命部队（ASF）为框架背景，ECOWAS 层面发展区域反恐力量以应对萨赫勒—沿海西非的恐怖主义外溢威胁。",
        "history": [
            "2025：提出 26 万人区域反恐力量概念。",
            "2025：讨论 5000 人旅选项。",
            "2025—2026：推进 1650 人分阶段快速部署/反恐核心方案。",
            "2026：开展成员国承诺单位的战备检查（如几内亚摩托化连）。",
        ],
        "structure": "基于非洲待命部队（ASF）框架，ECOWAS 成员国提供兵力贡献；设常备/待命结构，反恐核心力量分阶段生成。",
        "force_generation": "兵力方案分层：26 万概念（2025 广泛概念）、5000 人旅选项、1650 人分阶段快速部署/反恐核心；2026 年处于战备检查与力量生成，非已完全部署。",
        "financing": "融资机制是主要争议点；ECOWAS 成员国对反恐力量的资金分摊与可持续融资持续磋商。",
        "geography": "西非，尤其沿海西非外溢带（贝宁、多哥、加纳、科特迪瓦等）。",
        "relations": "与 MNJTF 存在协调关系；与 AES 分裂的背景下，ESF 作为 ECOWAS 机制单独运作。",
        "current_status": "活跃框架 / 力量生成中（active_framework / force_generation）。非已完全部署的区域作战力量。",
        "uncertainties": "最终兵力规模、融资可持续性与成员国实际贡献程度不确定。",
        "asip_analysis": "ASIP 判断：ESF 是 ECOWAS 对西非恐怖主义外溢的制度回应，但仍处于力量生成阶段。评估时必须区分概念性兵力（26 万）与实际正在生成的快速部署核心（1650 人），避免把 26 万概念写成现役军队。",
        "watch_indicators": [
            "ECOWAS 反恐力量融资机制的落地",
            "1650 人快速部署核心的实际成军进度",
            "与 AES/MNJTF 的协调机制变化",
        ],
        "sources": [
            "ECOWAS CCDS 43rd meeting — https://www.ecowas.int/43rd-ordinary-meeting-of-the-ecowas-committee-of-chiefs-of-staff-ccds-fight-against-the-growing-threat-of-terrorism-in-the-region-on-the-agenda/",
            "ECOWAS ministers funding — https://www.ecowas.int/les-ministres-de-la-cedeao-se-reunissent-a-abuja-pour-faire-avancer-les-modalites-de-financement-de-la-force-regionale-de-lutte-contre-le-terrorisme/",
            "ECOWAS ESF readiness inspection — https://www.ecowas.int/ecowas-standby-force-conducts-operational-readiness-inspection-of-guineas-pledged-motorized-company/",
        ],
        "capabilities": "ESF 作为待命部队，其作战能力取决于成员国兵力贡献与融资落地；目前处于力量生成阶段，尚未形成稳定的区域反恐战斗力。",
        "constraints": "融资可持续性是核心约束；ECOWAS 成员国对反恐力量的资金分摊与可持续融资持续磋商。与 AES 分裂的背景下，ESF 的成员国构成与 AES 三国重叠问题构成政治约束。",
        "coordination": "ESF 与 MNJTF 在反恐任务上存在协调关系；二者的任务边界与指挥关系需通过 ECOWAS 机制明确。",
    }, importance="L2"),

    # ============================================================ AFRICOM
    "actor-africom": _prof({
        "lead": "美国非洲司令部（United States Africa Command，AFRICOM）是美国国防部负责非洲地区的作战司令部，任务涵盖对恐怖组织（青年党、ISIS-Somalia 等）的直接反恐打击、伙伴国能力建设与多国演习（Flintlock）。2026 年继续在索马里对青年党与 ISIS-Somalia 实施空袭，并主持 Flintlock 2026。",
        "name_and_translation": "中文名称为“美国非洲司令部”，英文名称 United States Africa Command，缩写 AFRICOM。",
        "background": "2007 年成立，是美国第六个地理作战司令部，总部设在德国斯图加特；负责协调美国在非洲（埃及除外）的军事活动。",
        "mission": "推进美国国家安全利益，通过伙伴合作与直接行动打击暴力极端主义、建设非洲伙伴的军事能力。",
        "structure": "作为美国作战司令部，下辖非洲之角联合特遣部队等；通过空军打击与伙伴训练双轨运作。",
        "geography": "非洲（埃及除外）；重点在索马里/非洲之角、萨赫勒、利比亚等反恐前线。",
        "operations": "2026 年继续在索马里对青年党实施空袭（与索马里联邦政府协调）；对 ISIS-Somalia 实施打击；主持 Flintlock 2026（科特迪瓦与利比亚，约 1500 人、30+ 国）。",
        "partnership": "通过 Flintlock 等演习与非洲伙伴国军队合作；对利比亚武装仅限训练/演习合作，不构成指挥关系。",
        "command_limits": "AFRICOM 不指挥 AUSSOM、SNAF 或邦特兰安全部队；对索马里行动以索马里联邦政府协调下实施。",
        "current_status": "活跃（active）。",
        "uncertainties": "美国对非军事投入的长期可持续性受国内政治与预算影响。",
        "asip_analysis": "ASIP 判断：AFRICOM 是理解美国在非洲反恐介入的核心节点。必须守住纪律——其直接打击对象是青年党与 ISIS-Somalia（hostile/direct strikes），但对 AUSSOM/SNAF/邦特兰不构成指挥关系，不得创建错误指挥边。",
        "watch_indicators": [
            "AFRICOM 对青年党/ISIS-Somalia 打击的频率与授权变化",
            "Flintlock 与伙伴能力建设的地域扩展",
            "美国对非军事政策的调整",
        ],
        "geographic_remit": "AFRICOM 的地理责任区覆盖非洲（埃及除外），总部设在德国斯图加特；通过前沿部署与轮换部队在非洲之角、萨赫勒与利比亚等反恐前线活动。",
        "capabilities": "AFRICOM 拥有空中打击、情报监视侦察（ISR）与特种作战能力，并通过军事援助与训练建设非洲伙伴国军队的反恐能力。",
        "counterterrorism_operations": "2026 年继续在索马里对青年党实施空袭（与索马里联邦政府协调），并对 ISIS-Somalia 实施打击；这是其在非洲之角直接反恐介入的双目标。",
        "sovereignty_constraints": "AFRICOM 的行动受主权约束——对 AUSSOM、SNAF 与邦特兰安全部队不构成指挥关系，对索马里行动以索马里联邦政府协调下实施。",
        "timeline": [
            "2007：AFRICOM 成立。",
            "2007 前后：开始对青年党相关目标实施打击。",
            "2017 前后：ISIS-Somalia 成为打击目标。",
            "2026：Flintlock 2026 于科特迪瓦/利比亚举行，约 1500 人、30+ 国。",
        ],
        "sources": [
            "AFRICOM Flintlock 26 — https://www.africom.mil/article/36373/flintlock-26-commences-in-cote-divoire-and-libya",
            "AFRICOM press releases (Somalia strikes) — https://www.africom.mil/",
        ],
    }, importance="L2"),

    # ============================================================ MINUSMA
    "actor-minusma": _prof({
        "lead": "联合国马里多层面综合稳定团（MINUSMA）是联合国在马里的维和/稳定任务。应马里当局请求，联合国安理会于 2023-06-30 终止其授权，撤出于 2023-12-31 完成。该任务属历史性联合国维和任务（closed_2023），不得显示为 active。",
        "name_and_translation": "中文名称为“联合国马里多层面综合稳定团”，英文名称 United Nations Multidimensional Integrated Stabilization Mission in Mali，缩写 MINUSMA。",
        "background": "2013 年在马里北部危机与法军干预背景下建立，作为联合国在马里的多层面稳定任务。",
        "history": [
            "2013：MINUSMA 建立。",
            "2013—2023：承担平民保护、和平进程支持、停火监测与国家权威恢复。",
            "2023-06-30：安理会应马里请求终止授权（决议 2690）。",
            "2023-12-31：撤出完成。",
        ],
        "mission": "平民保护、支持和平进程与 2015 年和平协议、停火监测、恢复国家权威。",
        "structure": "联合国维和任务，多国部队与文职构成；历史上屡遭圣战组织袭击（针对车队、营地与人员）。",
        "geography": "马里全境，尤其北部与中部。",
        "relations_mali": "与马里当局关系在 2022—2023 年恶化，马里要求撤出；与 Barkhane 行动、G5 Sahel 等有历史协调关系。",
        "current_status": "已结束（closed_2023）。非 active。",
        "post_withdrawal": "撤出后的安全真空与马里转向俄罗斯/非洲军团支持构成理解马里北部当前武装格局的关键背景。",
        "uncertainties": "撤出后马里北部安全责任转移与稳定机制的不确定性。",
        "asip_analysis": "ASIP 判断：MINUSMA 是萨赫勒国际维和介入退潮的标志性案例。其撤出与 G5 Sahel 解体、马里转向俄罗斯/非洲军团同步发生，构成萨赫勒安全格局从国际机制向区域/双边机制转移的转折。",
        "watch_indicators": [
            "马里北部安全真空的后续填补机制",
            "撤出后联合国在马里的任何残余角色",
        ],
        "mandate_scope": "MINUSMA 的授权涵盖平民保护、支持马里和平进程与 2015 年《和平与和解协议》执行、停火监测、恢复国家权威与保护人权。",
        "jihadist_attacks": "MINUSMA 在其任务期内屡遭 JNIM 等圣战组织的袭击——针对车队、营地与人员，成为联合国最危险的维和任务之一。",
        "timeline": [
            "2013：MINUSMA 建立。",
            "2013—2023：承担平民保护、和平进程支持、停火监测与国家权威恢复。",
            "2022—2023：马里当局要求撤出。",
            "2023-06-30：安理会终止授权（决议 2690）。",
            "2023-12-31：撤出完成。",
        ],
        "legacy": "MINUSMA 是萨赫勒国际维和介入退潮的标志；其撤出与 G5 Sahel 解体、马里转向俄罗斯/非洲军团同步，构成萨赫勒安全格局从国际机制向区域/双边机制转移的转折。",
        "sources": [
            "UN SC terminates MINUSMA (30 June 2023) — https://press.un.org/en/2023/sc15341.doc.htm",
            "Resolution 2690 (2023) — https://minusma.unmissions.org/sites/default/files/res_2690_2023_en.pdf",
        ],
    }, importance="L2"),
}

# ---------------------------------------------------------------------------
# ENRICH patches
# ---------------------------------------------------------------------------
ENRICH_PATCHES = [
    # ---- MNJTF: Niger withdrawal + mandate (already encyclopedia_full)
    {
        "entity_id": "actor-mnjtf",
        "add_aliases": [],
        "add_historical_names": [],
        "source_refs_add": ["expe-au-psc-mnjtf-2025-12", "expe-print-niger-mnjtf-withdraw", "expe-reuters-chad-mnjtf-threat"],
        "set_fields": {"current_status": "active_regional_force_with_niger_withdrawal_constraint"},
        "sections": {
            "niger_withdrawal": "尼日尔于 2025 年 3 月退出 MNJTF；非盟随后表示深切关切并要求乍得湖流域委员会（LCBC）与尼日尔接触促其重返。尼日尔当前不得显示为无条件现役兵力贡献成员。",
            "chad_withdrawal_threat": "乍得于 2024 年 11 月威胁退出 MNJTF。该威胁不得写成已完成的退出——乍得仍为现役成员。",
            "current_mandate": "非盟和平与安全理事会（PSC）更新 MNJTF 授权：2026-02-01 至 2027-01-31。当前打击目标包括博科圣地/JAS 与 ISWAP。",
            "mandate_note": "MNJTF 当前判断：active，但尼日尔退出后区域凝聚力削弱。",
        },
    },
    # ---- AES Unified Force (actor-fu-aes): E2 → E3
    {
        "entity_id": "actor-fu-aes",
        "add_aliases": ["Force Unifiée de la Confédération des États du Sahel", "AES Unified Force", "Force Unifiée de l'AES"],
        "add_historical_names": [],
        "source_refs_add": ["expe-print-aes-5000", "expe-print-aes-russia", "expe-lesahel-aes-command", "d1-iss-aes-2026-03-04"],
        "set_fields": {"current_status": "active_operationalizing"},
        "sections": {
            "lead": "萨赫勒国家联盟统一部队（Force Unifiée de l'AES）是萨赫勒国家联盟（AES，马里、布基纳法索、尼日尔）正在组建的联合部队。AES 于 2023 年 9 月建立，2024 年 7 月签署邦联条约；2025 年宣布约 5000 人部队接近就绪，2025 年 12 月尼日尔官方称指挥架构就位，2026 年 3 月 ISS 称其于 2025 年 12 月启动、总部设尼亚美、约 6000 人。",
            "name_and_translation": "中文名称为“萨赫勒国家联盟统一部队”，英文 AES Unified Force，法语 Force Unifiée de la Confédération des États du Sahel。",
            "background": "AES 由马里、布基纳法索、尼日尔于 2023 年 9 月建立，2024 年 7 月签署邦联条约；统一部队是该邦联框架下的集体防御机制。",
            "history": [
                "2023-09：AES 由马里、布基纳法索、尼日尔建立。",
                "2024-07：签署邦联条约。",
                "2025-01：尼日尔防长宣布约 5000 人统一部队接近就绪（含空中、装备与情报资产）。",
                "2025-04：俄罗斯公开承诺提供武器/训练/技术支持。",
                "2025-12：尼日尔官方称部队成形、指挥架构就位。",
                "2026-03：ISS 称部队于 2025-12 启动、总部尼亚美、约 6000 人。",
            ],
            "structure": "设联合指挥架构，总部尼亚美；包含空中、地面与情报能力概念；由成员国部队贡献构成。",
            "force_estimates": [
                "2025 年宣布/计划：约 5,000 人（尼日尔防长 2025-01 宣布）。",
                "2026 年 ISS 报道：约 6,000 人（2026-03，分析性报道）。",
                "注意：保留时间/来源差异，不写单一固定人数。",
            ],
            "geography": "萨赫勒三国（马里、布基纳法索、尼日尔）境内及其交界地带。",
            "threat_environment": "以 JNIM 与 IS Sahel 为主要威胁；联合部队的集体防御目标即应对萨赫勒圣战威胁。",
            "russian_support": "俄罗斯/非洲军团提供武器、训练与技术支持；该支持为 support/training/equipment，不构成指挥或隶属关系。",
            "current_status": "活跃 / 组建中（active / operationalizing）。",
            "uncertainties": "部队实际成军速度、指挥权归属、与非洲军团的协作深度、成员国兵力贡献的持续性均存在不确定性。",
            "asip_analysis": "ASIP 判断：AES 统一部队是 G5 Sahel 解体后萨赫勒区域安全机制的重建尝试。评估时必须保留兵力数字的时间差（2025 年 5000 vs 2026 年 6000），并把俄罗斯/非洲军团的角色限定为支持而非指挥。",
            "watch_indicators": [
                "统一部队的实际成军与首次联合行动",
                "俄罗斯/非洲军团支持的具体形态",
                "与 JNIM/IS Sahel 的交战动态",
            ],
            "command_structure": "统一部队设联合指挥架构，总部尼亚美；其空中、地面与情报能力概念由三国部队贡献构成，指挥权归属与三国部队整合机制仍在形成中。",
            "coordination_problems": "与邻国机制（如 ECOWAS 待命部队）的协调存在政治问题；AES 三国退出 ECOWAS 与 G5 后，区域反恐机制的碎片化构成协调难题。",
        },
    },
    # ---- SAMIM: standard → encyclopedia_full
    {
        "entity_id": "actor-samim",
        "add_aliases": ["SADC Mission in Mozambique"],
        "add_historical_names": [],
        "source_refs_add": ["expe-sadc-samim-closure"],
        "set_fields": {"current_status": "historical_mission_ended_2024_07_15"},
        "sections": {
            "lead": "南共体驻莫桑比克特派团（SAMIM）是南部非洲发展共同体（SADC）2021 年向莫桑比克派出的区域反恐任务，2024-07-15 正式结束。该任务属历史性区域反恐任务（closed_2024），不得显示为现役。",
            "history": [
                "2021-06：SADC 批准 SAMIM。",
                "2021-07：部署。",
                "2021—2024：在德尔加杜角开展进攻行动与稳定化。",
                "2024：撤出令下达并完成。",
                "2024-07-15：SAMIM 正式结束。",
            ],
            "mandate": "支持莫桑比克打击恐怖主义/暴力极端主义、恢复安全与法治、支持稳定化与人道条件。",
            "operations": "在卡波德尔加杜实施进攻行动，取得实际安全收益，但未根除叛乱。",
            "closure": "2024 年撤出完成，2024-07-15 正式结束；结束后 FADM 承担主要责任，卢旺达与坦桑尼亚的双边部署延续。",
            "legacy": "SAMIM 的区域反恐经验（含得失）为其后区域机制提供教训。",
            "current_status": "已结束（closed_2024 / historical_mission_ended_2024_07_15）。非现役。",
        "participating_forces": "SAMIM 由南部非洲发展共同体成员国部队贡献构成（含南非、坦桑尼亚等），承担进攻行动与稳定化任务。",
        "gains_limitations": "SAMIM 在卡波德尔加杜取得实际安全收益（夺回部分城镇、削弱叛乱控制），但未根除叛乱；撤出后叛乱仍存。",
        "lessons": "SAMIM 的经验教训（区域反恐任务的进攻效果与稳定化局限）为其后区域机制提供了参考。",

        },
    },
    # ---- FADM: depth → encyclopedia_full + leadership
    {
        "entity_id": "actor-fadm",
        "add_aliases": ["Forças Armadas de Defesa de Moçambique"],
        "add_historical_names": [],
        "source_refs_add": ["expe-fadm-official", "expe-fadm-emg"],
        "set_fields": {"current_status": "active_state_force_countering_ism_with_external_support"},
        "sections": {
            "leadership": "总统 Daniel Chapo 为总司令（commander-in-chief）；Júlio dos Santos Jane 将军为总参谋长（Chief of General Staff，2026 年认定）。",
            "structure": "官方结构包括总参谋部、陆军、空军与海军；官方任务含主权/领土防卫与反恐。",
            "counterterrorism": "FADM 是卡波德尔加杜反叛乱的主要国家军事力量；2026 年官方报道描述其与友好力量的持续联合作战/协调。",
            "quick_reaction_forces": "EUMAM MOZ 持续支持 FADM 快速反应部队（QRF）的再生成与训练至 2026 年 12 月（本轮不新建 EUMAM 节点）。",
            "cooperation": "与卢旺达（RDF/RSF）、坦桑尼亚（TPDF）存在双边合作；与 SAMIM 存在历史合作。",
        },
    },
    # ---- RDF / Rwanda Security Force deployment
    {
        "entity_id": "actor-rdf-mozambique",
        "add_aliases": ["Rwanda Security Force", "Rwanda Defence Force", "RDF", "Rwandan Joint Force"],
        "add_historical_names": [],
        "source_refs_add": ["expe-rwanda-joint-force", "expe-acled-rwanda-moz"],
        "set_fields": {"current_status": "active_rwandan_counterinsurgency_deployment_in_cabo_delgado"},
        "sections": {
            "joint_composition": "莫桑比克部署官方上为“卢旺达安全部队/联合部队”（Rwanda Security Force / Joint Force），包含卢旺达国防军（RDF）与卢旺达国家警察（RNP）。Rwanda Security Force 不是 RDF 的简单别名；警察成分不属 RDF。",
            "history": [
                "2021-07：应莫桑比克请求，RDF+RNP 初始 1000 人联合部署。",
                "2021—2024：承担战斗/安全、国家权威恢复、稳定化与安全部门改革任务。",
                "2024：ACLED 估算约 4000 卢旺达人员（分析性估计，非官方 2026 兵力）。",
                "2025—2026：持续轮换与作战规划，与 FADM 合作。",
            ],
            "force_estimate": "ACLED 估算 2024-05 约 4,000 人，仅作为分析性估计，不得显示为官方 2026 现役兵力。",
            "areas": "莫辛博阿（Mocímboa）、帕尔马（Palma）等德尔加杜角北部。",
            "cooperation": "与 FADM 合作为 R3 合作；与 SAMIM 时期共存。",
        },
    },
    # ---- TPDF: depth → encyclopedia_full + SAMIM/bilateral distinction
    {
        "entity_id": "actor-tanzania-tpdf",
        "add_aliases": ["Tanzania People's Defence Force", "TPDF"],
        "add_historical_names": [],
        "source_refs_add": ["expe-acled-cabo-ligado-tpdf"],
        "set_fields": {"current_status": "active_bilateral_border_focused_deployment_in_mozambique"},
        "sections": {
            "two_tracks": "必须区分两个层面：(1) 坦桑尼亚参加 SAMIM；(2) 独立的双边 TPDF 莫桑比克部署。二者不得合并为同一指挥/部署史。",
            "samim_participation": "坦桑尼亚作为 SAMIM 成员国参加该区域任务（历史参加）。",
            "bilateral_deployment": "2022 年起坦桑尼亚在卡波德尔加杜（集中南加德 Nangade）保持独立双边部署；坦桑尼亚公开确认双边部队在 SAMIM 结束后继续保留。",
            "border_security": "承担坦桑尼亚—莫桑比克边境安全、叛乱外溢预防与边境巡逻。",
            "post_samim": "SAMIM 结束后双边部署延续（2025 年报道继续）。",
        },
    },
    # ---- Africa Corps: Wagner distinction + AES support
    {
        "entity_id": "actor-africa-corps",
        "add_aliases": ["Africa Corps", "Afrikanskiy Korpus"],
        "add_historical_names": [],
        "source_refs_add": ["expe-yahoo-wagner-mali", "expe-crs-africa-corps", "expe-reuters-africa-corps-civilian"],
        "set_fields": {"current_status": "active_russian_state_controlled_security_force_in_mali"},
        "sections": {
            "wagner_distinction": "非洲军团不是瓦格纳的简单别名。其形成于 2023 年瓦格纳兵变/普里戈任死亡后，由俄罗斯国防部支持，比瓦格纳早期名义上私营的模式更直接受国家控制。谱系为“人员/任务继承 + 国家整合”，而非别名连续。",
            "personnel_continuity": "路透社 2025-06 报道约 70–80% 非洲军团人员为前瓦格纳成员（基于雇佣兵通信；Reuters 来源估计/报道，非官方统计）。",
            "mali_role": "瓦格纳 2025-06 宣布离开马里，非洲军团留驻；与马里武装力量合作，在 JNIM 冲突环境中行动。",
            "aes_cooperation": "深化与 AES 国家的安全合作；支持 AES 统一部队的装备/训练/技术援助（support，非指挥）。",
            "civilian_harm": "涉及非洲军团与马里部队的平民伤害指控必须归因于 HRW/路透，不得呈现为已裁定事实。",
            "current_status": "活跃（active）。",
        },
    },
    # ---- Wagner Group: depth → encyclopedia_full + Africa Corps distinction
    {
        "entity_id": "actor-wagner-group",
        "add_aliases": ["Wagner Group", "PMC Wagner"],
        "add_historical_names": [],
        "source_refs_add": ["expe-yahoo-wagner-mali"],
        "set_fields": {"current_status": "historical_mali_deployment_ended_2025_06"},
        "sections": {
            "mali_role": "瓦格纳在马里承担安全角色（2021—2025），与马里武装力量合作。",
            "prigozhin_transition": "2023 年普里戈任兵变与死亡构成瓦格纳模式的转折点，此后俄罗斯推动非洲军团作为更受国家控制的替代。",
            "tinzaouaten": "2024 年 Tinzaouaten 战斗瓦格纳人员遭受损失。",
            "mali_withdrawal": "2025 年 6 月瓦格纳宣布离开马里；非洲军团延续存在。",
            "africa_corps_distinction": "瓦格纳并非简单改名为非洲军团：非洲军团是人员/任务继承 + 更强俄罗斯国家整合的新机制。严禁写成“瓦格纳=改名后的非洲军团”。",
            "current_status": "历史（historical，马里部署 2025-06 结束）。",
        "mali_deployment": "瓦格纳 2021 年起在马里承担安全角色，与马里武装力量合作，参与对 JNIM 等圣战组织的行动；2024 年 Tinzaouaten 战斗受损。",
        "capabilities": "瓦格纳以雇佣军模式运作，提供战斗、训练与安保服务；其名义上私营的模式与非洲军团的国家控制模式形成对比。",
        "watch_indicators": [
            "瓦格纳残余人员向非洲军团/其他 PMC 的流动",
            "非洲军团与瓦格纳模式差异的官方表述",
        ],

        },
    },
    # ---- LAAF/LNA: naming enrichment
    {
        "entity_id": "actor-lna",
        "add_aliases": ["Libyan Arab Armed Forces", "LAAF", "Libyan National Army", "Haftar forces"],
        "add_historical_names": [],
        "source_refs_add": ["expe-nctc-isis-libya-2026-06", "depthf-reuters-haftar-drones-2026-04-02"],
        "set_fields": {"current_status": "active_eastern_libyan_military_power_under_ceasefire_rivalry"},
        "sections": {
            "naming": "保持稳定 canonical ID `actor-lna`；补充全称 Libyan Arab Armed Forces（LAAF）与别名 Libyan National Army / LNA / Haftar forces。",
            "modernization": "2026 年报道显示其持续现代化与外部防务联系（含无人机采购等）。",
            "counterterrorism_context": "NCTC 2026-06 称前 ISIS-Libya 领导 Abdul Qadr al-Najdi 被利比亚国民军击杀；ISIS-Libya 持续以利比亚军事/安全部队为目标。",
        },
    },
    # ---- GNU forces: reclassify as fragmented security network (UMBRELLA_ONLY)
    {
        "entity_id": "actor-gnu-forces",
        "add_aliases": [],
        "add_historical_names": [],
        "source_refs_add": ["expe-reuters-libya-clashes-gnu"],
        "set_fields": {
            "primary_type": "regional_security_force_network",
            "current_status": "active_western_government_aligned_security_network_under_fragmented_command",
        },
        "sections": {
            "umbrella_ruling": "“GNU forces”是西利比亚多支旅、安全机构与武装组织的总称（如 444 旅、111 旅、Rada、SSA 等），不是一个统一军事组织。UMBRELLA_ONLY，不得把多支武装合并为一个假统一军队。",
            "fragmentation": "GNU 相关武装由多支独立旅与安全机构构成，指挥碎片化，与的黎波里民族团结政府结盟或合作。",
        },
    },
    # ---- AUSSOM: AMISOM → ATMIS → AUSSOM lineage
    {
        "entity_id": "actor-aussom",
        "add_aliases": [],
        "add_historical_names": [],
        "source_refs_add": [],
        "set_fields": {},
        "sections": {
            "mission_lineage": "AUSSOM 是索马里非盟任务的当前阶段，其历史沿革为 AMISOM → ATMIS → AUSSOM 三个不同的非盟任务阶段/授权。AMISOM 与 ATMIS 是 distinct 历史任务，非 AUSSOM 的别名。",
        },
    },
]
