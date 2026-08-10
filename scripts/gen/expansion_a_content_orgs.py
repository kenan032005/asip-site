#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-A — organization content module.

Source of truth: ASIP-PPT-ENTITY-EXPANSION-A-Authoritative-Content-Pack.md (§1-§4, §7, §8, §20).
No independent factual research. Every factual claim below traces to the pack's
locked factual core; where the pack is silent, the gap is stated explicitly
instead of being padded (pack §20).
"""

TODAY = "2026-08-09"
IMPORTER = "expansion-a"

# --- source ids (see expansion_a_content_sources.py) ---
S_SHABAAB_NCTC = "expa-nctc-al-shabaab-2026-04"
S_SHABAAB_TFTC = "expa-treasury-tftc-shabaab-2025-04-14"
S_ISS_NCTC = "expa-nctc-isis-somalia-2025-02"
S_ISS_FIN = "expa-treasury-isis-somalia-financier-2023-07-27"
S_ISIS_FS = "expa-treasury-isis-financing-factsheet-2024-02-27"
S_ISCA_NCTC = "expa-nctc-isis-ca-2025-04"
S_ISDRC_NCTC = "expa-nctc-isis-drc-historical"
S_NIGSAC = "expa-nigsac-lakurawa-2025-03"
S_TREAS_SUDAN = "expa-treasury-sudan-islamist-2025-09-12"
S_OFAC_BBMB = "expa-ofac-bbmb-2025-09-12"
S_OFAC_SMB = "expa-ofac-smb-bbmb-2026-03-09"
S_EU_KARTI = "expa-eu-karti-2024"
S_ANSARU_NCTC = "depthb-nctc-ansaru-2025-06"
S_ACLED_JUNE = "d1-acled-africa-june-2026"

IMPORTANCE_L1 = "该实体处于平台核心观察范围，对理解所在地区安全格局具有决定性作用（L1）。"


def entity(**kw):
    """Build an entity record with the repository's full 38-field shape."""
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
        "completeness": "Expansion A 内容包导入档案 · 百科式",
        "importance_level": importance,
        "importance_statement": IMPORTANCE_L1 if importance == "L1" else
                                "该实体对理解所在地区安全格局具有重要作用（L2）。",
        "profile_depth": depth,
        "content_maturity": "E3_FULL_ENCYCLOPEDIA",
        "imported_by": IMPORTER,
        "sections": sections,
    }


# =====================================================================
# 1. Al-Shabaab
# =====================================================================
ENT_SHABAAB = entity(
    entity_id="actor-al-shabaab",
    slug="al-shabaab",
    name_zh="索马里青年党",
    name_en="Al-Shabaab",
    acronym="Al-Shabaab",
    native_name="حركة الشباب المجاهدين",
    aliases=["Harakat al-Shabaab al-Mujahideen", "al-Shabaab", "青年党"],
    historical_names=[],
    importance_level="L1",
    short_description="脱胎于伊斯兰法院联盟军事派系、2012 年公开效忠基地组织的索马里叛乱与恐怖组织；NCTC 截至 2026 年 4 月估计其规模约 7,000—12,000 人。",
    full_description="索马里青年党是基地组织在东非最重要的关联力量。它起源于 2006 年短暂控制索马里中南部部分地区的伊斯兰法院联盟军事派系，在法院联盟被逐出权力后独立发展为兼具叛乱与恐怖属性的组织。NCTC 截至 2026 年 4 月的资料将其定位为寻求推翻索马里联邦政府、驱逐外国部队并建立原教旨伊斯兰国家的基地组织关联方。",
    current_status="active_al_qaida_affiliate_in_east_africa",
    primary_category="al_qaida_aligned_network",
    tags=["非洲之角", "基地组织"],
    region_ids=["region-sudan-red-sea-horn"],
    country_ids=["country-ethiopia"],
    confidence="high",
    source_refs=[S_SHABAAB_NCTC, S_SHABAAB_TFTC],
)

PROF_SHABAAB = profile({
    "lead": "索马里青年党（Al-Shabaab / Harakat al-Shabaab al-Mujahideen）是活跃于索马里及周边地区的叛乱与恐怖组织，也是基地组织在东非最主要的关联节点。它由 2006 年一度控制索马里中南部部分区域的伊斯兰法院联盟（ICU）军事派系演化而来；法院联盟失去权力之后，该派系并未瓦解，而是逐步转型为拥有独立指挥体系的武装组织。2012 年，青年党公开宣誓效忠基地组织。截至 2026 年 4 月，美国国家反恐中心（NCTC）仍将其描述为基地组织关联方，其公开目标是推翻索马里联邦政府、驱逐外国部队并建立原教旨主义伊斯兰国家。",
    "name_and_translation": "本平台采用中文名「索马里青年党」，英文正式名 Al-Shabaab，完整名称为 Harakat al-Shabaab al-Mujahideen（意为「圣战青年运动」）。公开材料中常见简写 al-Shabaab。为避免与其他地区同名武装混淆，检索索引同时收录完整阿拉伯语名称与常见英文转写。",
    "formation_background": "该组织的直接前身是伊斯兰法院联盟内部的军事力量。2006 年，法院联盟一度控制索马里中部与南部的部分地区，其武装派系在此期间获得了作战经验与地方网络。法院联盟被逐出权力后，这一军事派系没有随母体一并消失，而是保留骨干并转入持续作战状态，最终发展为具有自主指挥、自主招募与自主财政能力的独立组织。",
    "history": {"p": [
        "从组织史角度看，青年党经历了三个明显不同的阶段：法院联盟军事派系阶段、法院联盟垮台后的独立叛乱阶段，以及 2012 年公开效忠基地组织之后的跨国关联阶段。",
        "2012 年的效忠是一次关键的身份转换：它把一个以索马里国内政治—宗教冲突为主要背景的武装，正式纳入全球圣战网络的叙事结构，并使其后续的国际认定、制裁与反恐定位都以「基地组织关联方」为基准。",
        "在此之后的十余年中，尽管面对索马里联邦政府与外国部队的持续军事压力，该组织始终没有被消灭。NCTC 截至 2026 年 4 月的资料仍将其列为具有实际作战能力的活跃组织。",
    ]},
    "ideology_objectives": "按照 NCTC 截至 2026 年 4 月的描述，青年党的公开政治目标包含三项：推翻索马里联邦政府、把外国部队逐出索马里、并在其控制或影响范围内建立原教旨主义的伊斯兰国家。这三项目标同时决定了它的主要打击对象——政府机构与安全部队、外国与非盟部队，以及被其视为与上述两者合作的地方力量。",
    "external_relations": "青年党与基地组织之间的关系建立在 2012 年的公开效忠之上，并被 NCTC 在 2026 年的资料中继续确认为关联方关系。需要区分的是：公开效忠确立了阵营归属与身份认同，但并不等同于基地组织核心对其日常作战实施直接指挥；后者在公开来源中并没有得到完整披露。与之相对，青年党与伊斯兰国索马里省之间是长期敌对关系，后者本身即由青年党的叛离人员组成。",
    "leadership": {"p": [
        "艾哈迈德·迪里耶（Ahmed Diriye，别名 Abu Ubaidah）是该组织现任埃米尔，即最高领导人。",
        "马哈德·卡拉特（Mahad Karate）是与财政以及内部安全／情报职能相关的重要高级人物。本平台按照「不为补图而建薄弱节点」的原则，暂不为其单独建立人物页，而是将其登记为后续内容包的人物依赖项。",
    ]},
    "structure": "公开来源对青年党内部机构划分的披露有限。可以确认的是，该组织同时具备作战指挥、财政筹措与内部安全／情报三类职能，其中财政与内部安全职能由高级领导层直接掌握。除此之外的科层结构、区域指挥层级与决策流程，现有权威来源尚不足以支撑逐级复原，本页不作推测性补全。",
    "force_estimates": "NCTC 截至 2026 年 4 月的资料估计该组织规模约为 7,000—12,000 名成员。该数字应作为带日期的机构估计使用，不宜视为精确的常备兵力。公开来源对统计口径（是否包含后勤、财政与地方民兵性质的附属人员）没有给出明确说明，因此不同来源之间的横向比较需要谨慎。",
    "geography": "其主要据点位于索马里南部。除本土之外，该组织的行动能力还延伸至肯尼亚与埃塞俄比亚，因此不能仅按单一国家的国内叛乱来理解其威胁范围。本平台的地理归属字段目前只登记已建节点，索马里与肯尼亚尚未建立国家节点，相关缺口已记入未决依赖清单。",
    "tactics": {"p": [
        "该组织的常用手段包括简易爆炸装置（IED）、车载简易爆炸装置（VBIED）、轻武器、军事化突击、伏击、绑架、迫击炮袭击与暗杀。",
        "其复合式袭击具有稳定的战术特征：先以 IED 或 VBIED 实施起爆，随后以轻武器分队跟进突入。这种「爆炸＋突入」的组合决定了固定目标（政府建筑、酒店、军营与外国机构）在遭袭时往往面临二次伤亡风险。",
    ]},
    "finance": "青年党维持着规模可观的资金与便利化网络。2025 年 4 月，恐怖主义融资打击中心（TFTC）对 15 名青年党领导人、行动人员与资金便利者实施认定，指其参与筹资以及 IED 相关物资的扩散。该行动同时说明两点：其一，该组织的资金链条具有可被识别的跨境结构；其二，资金活动与爆炸物供应之间存在被官方指认的关联。至于其地方征税与勒索的具体机制，本内容包所依据的权威来源未作系统披露，此处不作推断。",
    "legal_status": "本页涉及的法律状态主要为美国方面的认定行为。2025 年 4 月 TFTC 的认定针对的是具体个人（领导人、行动人员与资金便利者），性质为多国参与的联合金融认定。所有此类内容在本平台均按「归属于认定方的法律行为」记录，不转写为普遍确立的事实结论。",
    "adversaries": "其主要对手包括索马里联邦政府及其安全部队、驻索马里的外国与非盟部队，以及伊斯兰国索马里省。与前两类的对抗属于典型的叛乱—反叛乱关系，与后者的对抗则同时具有组织竞争与意识形态竞争的双重性质。相关的支撑实体（非盟驻索马里特派团、索马里安全部队）尚未在本平台建立节点，对应关系已记入未决依赖清单。",
    "current_situation": "截至 NCTC 2026 年 4 月资料的时点，该组织仍被认定为具备实际作战能力的活跃组织，其目标设定与作战方式没有发生方向性改变。多年反恐军事行动削弱了它对部分区域的公开控制，但没有终结其组织存续、人员补充与跨境行动能力。",
    "regional_impact": "由于行动范围覆盖索马里本土并延伸至肯尼亚与埃塞俄比亚，该组织的影响不局限于单一国家的政权安全问题，而是构成非洲之角关联区内跨境安全风险的核心变量之一，同时也是基地组织全球叙事在东非的主要载体。",
    "risk_assessment": "对外国人员与外国机构而言，主要风险来自三类情形：针对政府与安全目标的复合式袭击造成的连带伤亡、以绑架为目的的定向行动，以及在其行动延伸区域（含跨境地带）的道路伏击与爆炸物风险。由于袭击常以「爆炸后突入」方式展开，事发现场的二次风险窗口明显长于单次爆炸事件。",
    "events": {"p": [
        "2006 年：伊斯兰法院联盟一度控制索马里中南部部分地区，其军事派系构成该组织的直接源头。",
        "法院联盟失去权力之后：军事派系保留骨干并持续作战，逐步发展为独立的叛乱与恐怖组织。",
        "2012 年：公开宣誓效忠基地组织，完成从本土叛乱到全球圣战网络关联方的身份转换。",
        "2025 年 4 月：TFTC 认定 15 名该组织领导人、行动人员与资金便利者。",
        "2026 年 4 月：NCTC 资料仍将其列为基地组织关联方，规模估计约 7,000—12,000 人。",
    ]},
    "uncertainties": {"list": [
        "规模数字属机构估计，精确成员数量无法确认，且统计口径未被公开说明。",
        "基地组织核心对该组织日常作战的直接控制程度，在公开来源中并不完整可见。",
        "其地方治理与征税机制的具体运作方式，超出本内容包所依据来源的披露范围。",
    ]},
    "gaps": "现阶段的主要信息缺口集中在三处：内部科层与区域指挥结构、财政收入的构成比例，以及与基地组织核心之间的实际协调频度。这些缺口不宜用一般性推论填补，需等待新的权威来源。",
    "asip_analysis": "ASIP 判断：不应把青年党仅仅当作一个索马里恐怖组织来建模，而应当作一个具有韧性的叛乱—行政复合系统，同时也是基地组织在东非的关键节点。其威胁来源于多项能力的叠加——武装能力、强制性地方治理、征税、情报渗透与跨境行动半径——而不是其中任何单一维度。这一判断属平台综合分析，不等同于任何单一政府来源的结论。",
    "watch_indicators": [
        "NCTC 后续版本对其规模区间与关联方定位是否作出调整。",
        "是否出现针对资金便利网络的新一轮多国联合认定。",
        "与伊斯兰国索马里省的武装冲突强度与地理范围是否变化。",
        "跨境行动是否向肯尼亚、埃塞俄比亚方向进一步扩展。",
        "最高领导层是否发生更替或公开效忠对象是否变化。",
    ],
    "core_assessment": "青年党的核心特征是「未被消灭的持续性」：在长期外部军事压力下，它保持了指挥延续、人员补充与跨境投送能力，并通过 2012 年的公开效忠取得了全球网络内的稳定身份定位。",
    "sources": [
        "U.S. National Counterterrorism Center (NCTC)：《Al-Shabaab》（as of April 2026）（https://www.odni.gov/nctc/terrorist_groups/al_shabaab.html）",
        "U.S. Department of the Treasury：《TFTC Designates Al-Shabaab Networks in Somalia》（14 Apr 2025）（https://home.treasury.gov/news/press-releases/sb0084）",
    ],
}, importance="L1")


# =====================================================================
# 2. ISIS-Somalia
# =====================================================================
ENT_ISS = entity(
    entity_id="actor-isis-somalia",
    slug="isis-somalia",
    name_zh="伊斯兰国索马里省",
    name_en="ISIS-Somalia",
    acronym="ISS",
    native_name="ولاية الصومال",
    aliases=["Islamic State in Somalia", "ISS", "ISIS-Somalia"],
    importance_level="L1",
    short_description="由青年党叛离人员组成、2015 年效忠伊斯兰国并于 2018 年获正式分支承认的武装；同时是伊斯兰国在非洲的重要资金与便利化枢纽。",
    full_description="伊斯兰国索马里省由索马里青年党的叛离人员组成，2015 年宣誓效忠伊斯兰国，2018 年获得正式分支地位。其主要活动区域位于索马里邦特兰巴里地区的戈利斯山区。该分支的战略意义明显超出其territorial规模，原因在于它同时承担伊斯兰国在非洲的资金归集与人员、物资转运功能。",
    current_status="active_reduced_but_resilient_islamic_state_branch",
    primary_category="islamic_state_aligned_network",
    tags=["非洲之角", "伊斯兰国"],
    region_ids=["region-sudan-red-sea-horn"],
    country_ids=[],
    confidence="high",
    source_refs=[S_ISS_NCTC, S_ISS_FIN, S_ISIS_FS],
)

PROF_ISS = profile({
    "lead": "伊斯兰国索马里省（ISIS-Somalia / ISS）是伊斯兰国在东非的正式分支。它并非独立起源，而是由索马里青年党的叛离人员组建：2015 年该派系宣誓效忠伊斯兰国，2018 年获得伊斯兰国正式承认的分支地位。其主要活动区域集中在索马里邦特兰邦巴里地区的戈利斯山区。与其有限的地理规模相比，该分支在伊斯兰国非洲体系中的财务与协调功能更为突出。",
    "name_and_translation": "中文名称采用「伊斯兰国索马里省」，英文常用 ISIS-Somalia，亦见 Islamic State in Somalia 及缩写 ISS。这些写法在权威来源中并存，本平台将其一并纳入别名索引，以保证不同来源之间的检索可对齐。",
    "formation_background": "该组织的产生源于青年党内部的分裂。一部分成员选择脱离原有的基地组织阵营归属，转而承认伊斯兰国的领导权威。这一「同源分裂」背景决定了它与青年党之间的敌对关系并非普通的地盘竞争，而是包含合法性争夺在内的结构性对立。",
    "history": {"p": [
        "2015 年：脱离青年党的派系公开宣誓效忠伊斯兰国。此时其身份尚未获得伊斯兰国的正式确认。",
        "2018 年：伊斯兰国正式承认其分支地位，该组织由此进入伊斯兰国的正式行省序列。",
        "2021—2022 年：美国财政部披露其收入规模，显示其已具备可观的独立筹资能力。",
        "2025 年之后：邦特兰方面的反恐军事行动对其造成实质性人员损失，其规模与 2025 年 2 月的估计相比已发生变化。",
    ]},
    "geography": "其主要作战与藏匿区域为索马里邦特兰巴里地区的戈利斯山区。山地地形为小规模武装提供了藏匿与机动条件，也使外部军事行动的清剿成本显著上升。由于索马里尚未在本平台建立国家节点，本页的国家归属字段暂为空，区域归属登记为非洲之角关联区。",
    "leadership": {"p": [
        "阿卜杜勒·卡迪尔·穆明（Abd al-Qadir Mu'min）是该组织的创建者，同时担任卡拉尔办公室的负责人。",
        "阿卜迪拉赫曼·法希耶·伊塞（Abdirahman Fahiye Isse）是该组织的领导人，承担行动层面的领导职能。两人角色不同，不得合并为同一人物记录。",
        "阿卜迪韦利·穆罕默德·优素福（Abdiweli Mohamed Yusuf）是高级资金人员。本平台按不建薄弱节点的原则，将其登记为后续内容包的人物依赖项。",
    ]},
    "force_estimates": "NCTC 截至 2025 年 2 月的资料估计该组织有 700—1,500 名战斗人员。该数字必须作为带日期的历史估计保存，而不能作为无时间标注的当前兵力使用——原因在于其后邦特兰方面的反恐行动造成了实质性损失，当前实际规模处于流动状态。",
    "tactics": "其作战手段包括轻武器、简易爆炸装置、经改装的商用无人航空系统、自杀式袭击者、车载简易爆炸装置以及复合式袭击。其中商用无人机的武器化使用，使其在装备水平明显弱于对手的条件下仍保有一定的非对称打击能力。",
    "finance": {"p": [
        "该分支在伊斯兰国体系内具有特殊的财务地位。美国财政部的资料指出，它通过勒索获取收入，并促成资金、指令、外籍战斗人员、补给与弹药向非洲其他地区的伊斯兰国分支与网络转移。",
        "在具体数额方面，美国财政部报告其 2021 年收入约为 250 万美元，2022 年上半年接近 200 万美元。财政部其后的分析将其描述为伊斯兰国最重要的财务分支之一。",
        "上述数额与定性描述均属美国财政部口径，本平台按归属性陈述保存，不转写为国际公认结论。",
    ]},
    "external_relations": "该组织与伊斯兰国之间是效忠与分支关系，时间上分为 2015 年效忠与 2018 年正式承认两个节点，两个日期都必须保留。它与卡拉尔办公室在地理与组织上高度重叠，但二者不得合并为同一实体：前者是行省序列中的分支，后者是覆盖非洲中部、东部与南部的区域管理与资金节点。与青年党之间则是长期敌对关系。",
    "adversaries": "其主要对手为索马里青年党与邦特兰安全部队。与青年党的冲突源于同源分裂后的合法性与资源竞争；与邦特兰安全部队的冲突则表现为持续的反恐清剿与反清剿。邦特兰安全部队尚未在本平台建立节点，相应关系已记入未决依赖清单。",
    "current_situation": "综合来看，该组织当前处于「被压缩但未被消除」的状态：反恐军事压力造成了明显损失，其人员规模已不能用 2025 年 2 月的估计直接表示；但其财务与转运功能并未随人员损失同比例下降，这正是它在伊斯兰国非洲网络中难以被替代的原因。",
    "regional_impact": "其区域影响主要通过资金与人员流动实现，而非领土控制。由于它向非洲其他伊斯兰国分支输送资源，其存续状态会间接影响中部非洲等地武装力量的补给条件，因此对该分支的评估不能只看索马里境内的战场态势。",
    "events": {"p": [
        "2015 年：由青年党叛离人员组成的派系宣誓效忠伊斯兰国。",
        "2018 年：获得伊斯兰国正式承认，成为其分支。",
        "2021 年：美国财政部报告其年度收入约 250 万美元。",
        "2022 年上半年：美国财政部报告其收入接近 200 万美元。",
        "2023 年 7 月 27 日：美国财政部对其高级资金人员实施认定。",
        "2025 年 2 月：NCTC 资料给出 700—1,500 名战斗人员的估计。",
    ]},
    "uncertainties": {"list": [
        "反恐行动之后的当前兵力处于流动状态，不得以 2025 年 2 月的估计代替。",
        "该组织与卡拉尔办公室在地理与组织上重叠，但二者的职能边界在公开来源中并未被完整界定，不得合并处理。",
        "其收入数额来自美国财政部单一口径，缺少可交叉验证的第二方来源。",
    ]},
    "asip_analysis": "ASIP 判断：该分支的战略重要性与其territorial足迹不成比例，原因在于它在更广泛的伊斯兰国非洲网络中承担财务与区域协调职能。换言之，评估其威胁水平时，人员规模是弱指标，资金与转运链路的完整性才是强指标。",
    "watch_indicators": [
        "邦特兰方向反恐行动的强度变化及其对该分支控制区的影响。",
        "是否出现新的、经权威来源确认的兵力估计以替代 2025 年 2 月口径。",
        "美国财政部是否披露新的资金流向或对其资金人员的进一步认定。",
        "武器化商用无人机的使用频率与技术水平是否提升。",
        "其与卡拉尔办公室在人员与职能上的重叠是否出现公开的结构性调整。",
    ],
    "core_assessment": "评估该组织应把「财务枢纽属性」置于「地面控制力」之前：它在伊斯兰国非洲体系中的价值主要来自资金归集与跨境转运，而非其在索马里北部山区的实际控制范围。",
    "sources": [
        "U.S. National Counterterrorism Center (NCTC)：《ISIS-Somalia》（as of February 2025）（https://www.odni.gov/nctc/terrorist_groups/isis_somalia.html）",
        "U.S. Department of the Treasury：《Treasury Designates Senior ISIS-Somalia Financier》（27 Jul 2023）（https://home.treasury.gov/news/press-releases/jy1652）",
        "U.S. Department of the Treasury：《Countering ISIS Financing Fact Sheet》（https://home.treasury.gov/system/files/136/Fact-Sheet-Countering-ISIS-Financing-2-27-24.pdf）",
    ],
}, importance="L1")


# =====================================================================
# 3. al-Karrar Office
# =====================================================================
ENT_KARRAR = entity(
    entity_id="actor-al-karrar-office",
    slug="al-karrar-office",
    name_zh="卡拉尔办公室",
    name_en="al-Karrar Office",
    acronym="",
    native_name="مكتب الكرار",
    aliases=["al-Karrar", "Al-Karrar Office"],
    primary_type="network",
    secondary_types=["finance_network"],
    importance_level="L1",
    short_description="与伊斯兰国索马里省同地共处但独立建模的伊斯兰国区域管理与资金节点，负责统筹非洲中部、东部与南部方向的活动。",
    full_description="卡拉尔办公室是伊斯兰国设在索马里的区域管理节点。NCTC 将其描述为由伊斯兰国高级成员组成、负责监督非洲中部、东部与南部伊斯兰国活动的单元；美国财政部则把它描述为「行省总局」体系在索马里的区域节点，并指其通过哈瓦拉网络（含涉及南非的渠道）向中部非洲的伊斯兰国分支输送资金。",
    current_status="active_islamic_state_regional_coordination_node",
    primary_category="islamic_state_aligned_network",
    tags=["非洲之角", "资金网络"],
    region_ids=["region-sudan-red-sea-horn"],
    country_ids=[],
    confidence="medium_high",
    source_refs=[S_ISS_NCTC, S_ISIS_FS, S_ISS_FIN],
)

PROF_KARRAR = profile({
    "lead": "卡拉尔办公室（al-Karrar Office）是伊斯兰国在索马里设置的区域管理与资金节点。它与伊斯兰国索马里省同地共处，但在本平台被建模为独立实体，而不是后者的别名。NCTC 把它描述为一个由伊斯兰国高级成员构成的单元，职责是监督非洲中部、东部与南部方向的伊斯兰国活动。",
    "name_and_translation": "中文名称采用「卡拉尔办公室」，英文写作 al-Karrar Office，公开材料中亦简称 al-Karrar。该名称指向的是一个职能单元而非传统意义上的武装组织，因此本页在类型字段中登记为网络型实体。",
    "organizational_relation": "为什么必须与伊斯兰国索马里省分开建模：两者虽然在地理位置与人员上高度重叠，但职能层级不同。索马里省是行省序列中的作战分支，卡拉尔办公室则是跨行省的区域管理与资金枢纽，其覆盖范围远超索马里一地。若将二者合并，非洲中部方向若干资金与协调关系将失去可解释的连接点。",
    "structure": "美国财政部把卡拉尔描述为伊斯兰国「行省总局」（General Directorate of Provinces）体系在索马里的区域节点。这一表述说明它在伊斯兰国的组织架构中属于中间管理层，而非独立山头。至于其内部人员编制、决策程序与向上汇报机制，现有权威来源没有披露，本页不作补全。",
    "leadership": "NCTC 与美国财政部的材料均将阿卜杜勒·卡迪尔·穆明（Abd al-Qadir Mu'min）确认为卡拉尔办公室的负责人。同一人同时是伊斯兰国索马里省的创建者，这一人事重叠是两个实体高度关联的直接原因，但不构成合并二者的理由。",
    "finance_logistics": "美国财政部的资料指出，卡拉尔通过哈瓦拉网络转移资金，其中包括涉及南非的渠道，资金流向为中部非洲的伊斯兰国分支。这一描述给出了非洲伊斯兰国体系中一条可追踪的资金路径：东非归集—区域节点调度—中部非洲使用。相关表述属美国财政部口径，本平台按归属性陈述保存。",
    "geography": "该单元的实际所在地为索马里，与伊斯兰国索马里省同地共处；其职责覆盖范围则包括非洲中部、东部与南部。需要区分「所在地」与「职责范围」这两个不同概念：前者是点，后者是面，二者不可混为一谈。",
    "external_relations": "卡拉尔办公室与伊斯兰国索马里省之间是同地共处与组织关联关系；与中部非洲方向的伊斯兰国分支之间，目前可确认的是资金输送关系。必须强调的是，本平台不会据此建立卡拉尔对所有非洲伊斯兰国分支的「指挥」边——公开来源不支持这一推论。",
    "current_situation": "截至本内容包所依据来源的时点，该单元仍处于活跃状态，其区域协调与资金调度职能没有出现被替代的公开迹象。由于它本身不以territorial控制为存在形式，常规的战场指标对其状态评估参考价值有限。",
    "regional_impact": "作为跨行省的资金与协调节点，它的影响体现在网络层面而非战场层面：它把东非的资金归集能力与中部非洲的作战需求连接起来，从而在结构上提升了整个非洲伊斯兰国体系的资源调配效率。",
    "controversies_uncertainties": "公开来源不足以确认 al-Karrar Office 对各非洲 ISIS 分支日常战术行动的实际指挥深度。因此，本平台仅建立有来源支撑的资金与协调关系，不建立覆盖式的指挥关系。",
    "uncertainties": {"list": [
        "该单元对各非洲伊斯兰国分支日常战术行动的实际指挥深度，无法由现有公开来源确认。",
        "其与伊斯兰国索马里省之间的人员与职能边界存在重叠，公开材料未给出清晰划分。",
        "哈瓦拉渠道的具体规模、频率与经手方，除美国财政部的概括性描述外缺少细节。",
    ]},
    "gaps": "最关键的缺口是「权限边界」：现有材料能证明它承担监督与资金调度职能，但不能证明其对具体作战行动拥有指挥权。在获得新的权威来源之前，这一区分必须在数据层保持显性。",
    "asip_analysis": "ASIP 判断：设立该实体的必要性在于——如果没有它，伊斯兰国索马里省与非洲其他伊斯兰国分支之间若干资金与协调关系将成为无法解释的孤立连接。它是一个「解释性节点」，其分析价值来自它所连接的关系，而不是它自身的武装能力。",
    "watch_indicators": [
        "是否出现新的权威来源披露其对具体分支的指挥权限。",
        "哈瓦拉渠道是否遭到新的金融认定或执法干预。",
        "其负责人是否发生更替，以及与索马里省领导层的重叠是否延续。",
        "中部非洲方向的资金输送路径是否出现替代节点。",
    ],
    "core_assessment": "该单元是理解非洲伊斯兰国体系资源流动的关键中间层：它的价值不在作战，而在把分散的分支组织连成一个可调度的网络。",
    "sources": [
        "U.S. National Counterterrorism Center (NCTC)：《ISIS-Somalia》（https://www.odni.gov/nctc/terrorist_groups/isis_somalia.html）",
        "U.S. Department of the Treasury：《Countering ISIS Financing Fact Sheet》（https://home.treasury.gov/system/files/136/Fact-Sheet-Countering-ISIS-Financing-2-27-24.pdf）",
        "U.S. Department of the Treasury：《Treasury Designates Senior ISIS-Somalia Financier》（https://home.treasury.gov/news/press-releases/jy1652）",
    ],
}, importance="L1")


# =====================================================================
# 4. ADF / ISIS-Central Africa
# =====================================================================
ENT_ADF = entity(
    entity_id="actor-adf-isis-ca",
    slug="adf-isis-ca",
    name_zh="民主同盟军（伊斯兰国中非省）",
    name_en="Allied Democratic Forces (ADF) / ISIS–Central Africa",
    acronym="ADF / ISIS-CA",
    native_name="",
    aliases=["Allied Democratic Forces", "ADF", "ISIS-Central Africa", "ISIS-CA", "ISIS-DRC", "ISCAP"],
    historical_names=["Allied Democratic Forces"],
    importance_level="L1",
    short_description="源自乌干达反政府叛乱、后扎根刚果（金）东部并于 2019 年获伊斯兰国承认为分支的武装；NCTC 2025 年 4 月估计约 1,000—1,500 人。",
    full_description="民主同盟军最初是乌干达境内的反政府叛乱运动，其后在刚果民主共和国东部扎根。2019 年伊斯兰国公开承认其分支地位，当前 NCTC 采用「伊斯兰国中非省」这一称谓。其主要活动区域为刚果（金）北基伍与伊图里两省，并具备在乌干达境内实施袭击的能力。",
    current_status="active_islamic_state_central_africa_branch",
    primary_category="islamic_state_aligned_network",
    tags=["中部非洲", "伊斯兰国"],
    region_ids=["region-nile-basin-east-africa"],
    country_ids=[],
    confidence="high",
    source_refs=[S_ISCA_NCTC, S_ISDRC_NCTC],
)

PROF_ADF = profile({
    "lead": "民主同盟军／伊斯兰国中非省（ADF / ISIS-CA）是一个身份经历过重大转换的武装组织。它最初是乌干达境内的反政府叛乱运动，随后在刚果民主共和国东部扎根并长期存续。2019 年，伊斯兰国公开承认其为自身分支；当前 NCTC 使用「伊斯兰国中非省」的称谓，并把它描述为一支原本属于乌干达反政府叛乱、其后成为伊斯兰国分支的力量。",
    "name_and_translation": "本平台把历史身份与当前身份合并在一个规范实体内：中文名「民主同盟军（伊斯兰国中非省）」，英文名 Allied Democratic Forces (ADF) / ISIS–Central Africa，缩写 ADF / ISIS-CA。别名索引同时收录 Allied Democratic Forces、ADF、ISIS-Central Africa、ISIS-CA、ISIS-DRC 与 ISCAP，以覆盖不同时期、不同机构的命名习惯。",
    "genealogy": "命名沿革本身是理解该组织的关键线索。较早的 NCTC 资料使用 ISIS-DRC 的表述，反映当时以所在国为命名依据；此后转为 ISIS-Central Africa，反映的是以区域为命名依据的伊斯兰国行省体系。与此同时，ADF 这一历史名称在学术与新闻报道中长期沿用。三套名称指向同一组织谱系，但侧重点不同。",
    "formation_background": "该组织的起点是乌干达国内的反政府武装斗争。此后其活动重心转移至刚果（金）东部，并在当地形成稳定存在。这一跨境迁移使其同时具备两重属性：对乌干达而言是境外威胁，对刚果（金）而言是境内长期叛乱。",
    "history": {"p": [
        "早期阶段：作为乌干达境内的反政府叛乱运动出现。",
        "中期阶段：活动重心转入刚果民主共和国东部，在北基伍与伊图里方向扎根。",
        "2019 年：伊斯兰国公开承认其分支地位，组织身份进入伊斯兰国行省序列。",
        "此后：NCTC 的命名从 ISIS-DRC 调整为 ISIS-Central Africa，反映其在伊斯兰国体系中的区域定位。",
    ]},
    "geography": "其主要活动区域为刚果民主共和国的北基伍省与伊图里省，同时具备在乌干达境内实施袭击的能力。由于刚果（金）与乌干达尚未在本平台建立国家节点，本页国家归属字段暂为空，区域归属登记为尼罗河流域与东非安全带。",
    "leadership": "塞卡·穆萨·巴卢库（Seka Musa Baluku）是该组织的最高领导人。NCTC 另将梅迪·恩卡卢博（Meddie Nkalubo）确认为媒体与袭击指挥人员。本平台为巴卢库建立独立人物页；恩卡卢博按不建薄弱节点原则登记为后续内容包的人物依赖项。",
    "force_estimates": "NCTC 截至 2025 年 4 月的估计为 1,000—1,500 名成员。与其他同类估计一样，该数字应作为带日期的机构口径使用，并需注意公开材料未说明该口径是否涵盖后勤与外围支持人员。",
    "tactics": "其常见手段包括轻武器、简易爆炸装置、迫击炮、火箭助推榴弹、屠杀、伏击、绑架与跨境袭击。其中针对平民的屠杀式袭击是该组织较为突出的行为特征，也是其造成大规模平民伤亡的主要方式。",
    "external_relations": "其对外关系的核心是与伊斯兰国之间的分支关系，成立时点为 2019 年的公开承认。需要注意的是，本平台不把 ADF 与 ISIS-CA 建模为两个并列的当前实体、再用一条普通关联边连接——这种做法会造成事实失真。历史身份与当前伊斯兰国品牌被保留在同一个规范实体内部。",
    "adversaries": "其主要对手包括刚果（金）武装部队、乌干达人民国防军以及联合国驻刚果（金）稳定特派团。上述三方尚未在本平台建立实体节点，相关关系已按规则记入未决依赖清单，不为补图而创建薄弱节点。",
    "current_situation": "截至 NCTC 2025 年 4 月资料的时点，该组织保持活跃，其跨境袭击能力与对平民的高强度暴力行为没有出现结构性变化。伊斯兰国分支身份则为其提供了品牌、叙事与网络层面的外部连接。",
    "regional_impact": "该组织的影响横跨刚果（金）东部与乌干达两侧，是中部非洲—东非交界地带平民安全风险的主要来源之一。同时，由于它被纳入伊斯兰国行省序列，其活动也构成伊斯兰国在非洲扩张叙事的组成部分。",
    "events": {"p": [
        "起源阶段：作为乌干达境内反政府叛乱运动出现。",
        "扎根阶段：活动重心转入刚果（金）东部的北基伍与伊图里方向。",
        "2019 年：伊斯兰国公开承认其为分支。",
        "命名调整：NCTC 资料由 ISIS-DRC 改用 ISIS-Central Africa。",
        "2025 年 4 月：NCTC 估计其规模为 1,000—1,500 人。",
    ]},
    "uncertainties": {"list": [
        "从历史 ADF 网络向伊斯兰国品牌分支的组织转型是渐进的，不同来源的描述并不一致，因此档案需同时保留历史 ADF 身份与当前 ISIS-CA 认定。",
        "转型的具体程度与时点缺乏统一口径，不能用单一日期概括整个过程。",
        "1,000—1,500 人的估计未说明统计边界，与其他机构口径之间不具备直接可比性。",
    ]},
    "controversies_uncertainties": "命名与身份问题是该实体最主要的争议来源：把 ADF 与 ISIS-CA 视为两个组织、或把伊斯兰国承认视为一次性的完全改造，都会偏离公开材料的描述。本平台采用单一规范实体加多别名的方式处理这一问题。",
    "asip_analysis": "ASIP 判断：该实体的建模方式本身就是一项分析结论——采用单一规范实体，是为了避免把「品牌变更」误读为「组织替换」。观察其后续演化时，应重点关注伊斯兰国品牌在多大程度上改变了它的目标选择与作战方式，而不是简单以更名时点划断历史。",
    "watch_indicators": [
        "NCTC 后续资料是否继续使用 ISIS-Central Africa 命名。",
        "跨境袭击是否向乌干达方向进一步增加。",
        "针对平民的大规模袭击频率与地理分布是否变化。",
        "是否出现关于其与伊斯兰国中央协调深度的新披露。",
        "最高领导层是否发生更替。",
    ],
    "core_assessment": "理解该组织的关键在于「一个组织、两套身份」：历史上的乌干达反政府叛乱与当前的伊斯兰国中非省，指的是同一条组织谱系在不同阶段的呈现。",
    "sources": [
        "U.S. National Counterterrorism Center (NCTC)：《ISIS-Central Africa》（https://www.odni.gov/nctc/terrorist_groups/isis_ca.html）",
        "U.S. National Counterterrorism Center (NCTC)：《ISIS-DRC》（历史资料，用于谱系与别名沿革）（https://www.odni.gov/nctc/terrorist_groups/isis_drc.html）",
    ],
}, importance="L1")


# =====================================================================
# 5. Sudanese Islamic Movement (SIM / SMB)
# =====================================================================
ENT_SIM = entity(
    entity_id="actor-sim",
    slug="sudanese-islamic-movement",
    name_zh="苏丹伊斯兰运动",
    name_en="Sudanese Islamic Movement",
    acronym="SIM",
    native_name="الحركة الإسلامية السودانية",
    aliases=["Sudanese Islamist Movement", "Sudanese Muslim Brotherhood", "Muslim Brotherhood in Sudan", "SMB"],
    primary_type="political_movement",
    secondary_types=["islamist_network"],
    importance_level="L1",
    short_description="根系可追溯数十年的苏丹伊斯兰主义政治网络；2026 年 3 月 9 日被美国 OFAC 以「苏丹穆斯林兄弟会」名义列入 SDN 清单并标注 [FTO] [SDGT]。",
    full_description="苏丹伊斯兰运动是一个长期存在的苏丹伊斯兰主义政治网络，不能被改写为 2026 年新成立的恐怖组织。欧盟 2024 年制裁材料把阿里·艾哈迈德·卡尔提描述为该运动的秘书长，并把该运动描述为伊斯兰主义各派的广泛联盟。2026 年 3 月 9 日，美国 OFAC 将「苏丹穆斯林兄弟会」列入 SDN 清单，同时把「苏丹伊斯兰运动」与「苏丹穆斯林兄弟会（Muslim Brotherhood in Sudan）」列为别名。",
    current_status="active_islamist_political_network_us_designated",
    primary_category="islamist_political_network",
    tags=["苏丹", "伊斯兰主义网络"],
    region_ids=["region-sudan-red-sea-horn", "region-nile-basin-east-africa"],
    country_ids=["country-sudan"],
    confidence="medium_high",
    disputed=True,
    source_refs=[S_OFAC_SMB, S_EU_KARTI, S_TREAS_SUDAN],
)

PROF_SIM = profile({
    "lead": "苏丹伊斯兰运动（Sudanese Islamic Movement，SIM）是一个长期存在的苏丹伊斯兰主义政治网络，其根系可以上溯数十年。它不应被表述为一个 2026 年才出现的新建恐怖组织——美国 2026 年的法律认定是对一个既有网络的定性行为，而不是该网络的起点。欧盟 2024 年制裁材料把它描述为伊斯兰主义各派的广泛联盟，并把阿里·艾哈迈德·卡尔提列为其秘书长。",
    "name_and_translation": "该实体的命名本身即是争议焦点。本平台以「苏丹伊斯兰运动」（Sudanese Islamic Movement，SIM）为规范名，同时把 Sudanese Islamist Movement、Sudanese Muslim Brotherhood、Muslim Brotherhood in Sudan 与缩写 SMB 收录为别名。这一处理与美国 OFAC 2026 年 3 月 9 日的列名方式一致：该次行动以「苏丹穆斯林兄弟会」为主名，并把另外两个名称列为别名。",
    "political_character": "从性质上看，它是政治—意识形态网络，而非武装组织。这一点决定了对它的评估方式不同于武装团体：其影响力主要通过人事渗透、组织动员与政治联盟实现，而不是通过战场控制实现。欧盟材料所称「广泛联盟」的表述，也说明其内部并非单一严密科层。",
    "history": {"p": [
        "历史阶段：作为苏丹伊斯兰主义运动长期存在，其组织根系延续数十年，远早于近年的国际制裁行动。",
        "全国伊斯兰阵线／全国大会党时期：该运动与这一时期的政治网络之间存在紧密关联，欧盟材料把卡尔提描述为全国大会党的重要人物。",
        "巴希尔下台之后：该网络进入重组阶段，其组织形态与公开活动方式随之调整。",
        "2023 年冲突爆发之后：其在苏丹战时政治格局中的角色成为国际关注焦点。",
        "2026 年 3 月 9 日：美国 OFAC 以「苏丹穆斯林兄弟会」名义将其列入 SDN 清单，标注 [FTO] [SDGT]。",
    ]},
    "leadership": "欧盟 2024 年的材料把阿里·艾哈迈德·卡尔提（Ali Ahmed Karti）确认为该运动的秘书长，同时指其为全国大会党的重要人物。卡尔提曾任苏丹外交部长。本平台为其建立独立人物页，并把欧盟关于其政治与安全影响力的判断按「欧盟结论」保存。",
    "influence": "欧盟材料还描述了该伊斯兰主义运动对苏丹武装部队、警察与情报部门的强大影响。这一表述属于欧盟的机构性判断，必须保持归属性，不得改写为各方公认的事实。本平台在数据层将其记录为带来源与归属的机构评估。",
    "legal_status": {"p": [
        "2026 年 3 月 9 日，美国 OFAC 将「SUDANESE MUSLIM BROTHERHOOD」加入 SDN 清单，并将「SUDANESE ISLAMIC MOVEMENT」与「MUSLIM BROTHERHOOD IN SUDAN」列为别名，标注为 [FTO] [SDGT]。",
        "欧盟方面则在 2024 年针对个人（卡尔提）采取列名措施，其法律对象与美国 2026 年针对组织的认定并不相同。",
        "两套法律行动分属不同司法辖区、不同对象与不同时点，本平台分别记录，不作合并表述。",
    ]},
    "external_relations": "在关系层面，最重要的是它与巴拉·本·马利克旅之间的联系。美国法律文书在别名与关联标注上使 SIM/SMB 与该武装之间产生了部分重叠，但本平台仍将二者保留为两个独立实体：前者是政治网络，后者是武装团体，二者的组织性质与行为方式不同。",
    "current_situation": "当前状态需要分两层表述：在事实层面，它是一个仍在运作的苏丹伊斯兰主义政治网络；在法律层面，它自 2026 年 3 月起处于美国 SDN 清单之内并被标注为外国恐怖组织与特别指定全球恐怖分子。两层表述必须同时呈现，缺一都会造成误读。",
    "controversies_uncertainties": "SIM、Sudanese Muslim Brotherhood 与历史苏丹穆斯林兄弟会网络之间的组织边界和同一性，在不同政府及研究来源中并不完全一致。这一分歧直接影响到哪些行为可以归因于哪一主体，因此本平台在实体层保留 disputed 标记。",
    "uncertainties": {"list": [
        "三个名称（SIM、SMB、苏丹穆斯林兄弟会）所指范围是否完全重合，各来源口径不一。",
        "欧盟关于该运动对军警情部门影响力的判断属机构评估，缺少可交叉验证的第二方公开材料。",
        "美国财政部关于巴拉·本·马利克旅投入战斗人员规模的表述，不得转记为本实体自身的兵力。",
    ]},
    "gaps": "现有材料无法回答的核心问题是组织边界：该网络的成员构成、决策机制与对下属或关联组织的实际约束力，均未被公开来源系统披露。这也是不同来源对同一名称给出不同外延的根本原因。",
    "asip_analysis": "ASIP 判断：处理该实体时，最大的风险不是信息不足，而是名称混用带来的归因错误。把美国 2026 年的法律认定当作组织成立时点、或把某一武装团体的人力数字转记到该政治网络名下，都会造成实质性失真。本平台因此采取「一个规范实体、多别名、分层记录法律状态」的处理方式。",
    "watch_indicators": [
        "美国 OFAC 是否对该网络的别名范围或关联标注作出进一步调整。",
        "欧盟或其他司法辖区是否跟进对该组织本体（而非个人）的列名。",
        "苏丹国内政治进程中该网络的公开角色是否发生变化。",
        "是否出现新的权威来源澄清 SIM 与 SMB 的组织边界。",
    ],
    "core_assessment": "该实体的分析价值在于连接政治网络与武装力量两个层面：它既不是纯粹的政党，也不是武装团体，其影响力通过对既有国家机构与武装力量的渗透与联盟关系实现。",
    "sources": [
        "U.S. OFAC：《Counter Terrorism Designations; Sudan-related Designation Update》（9 Mar 2026）（https://ofac.treasury.gov/recent-actions/20260309）",
        "European Union：《Council Implementing Regulation (EU) 2024/1783 / Ali Ahmed Karti》（https://eur-lex.europa.eu/eli/dec/2024/1784）",
        "U.S. Department of the Treasury：《Treasury Targets Sudanese Islamist Actors》（12 Sep 2025）（https://home.treasury.gov/news/press-releases/sb0246）",
    ],
}, importance="L1")


# =====================================================================
# 6. Al-Baraa Bin Malik Brigade
# =====================================================================
ENT_BBMB = entity(
    entity_id="actor-bbmb",
    slug="bbmb",
    name_zh="巴拉·本·马利克旅",
    name_en="Al-Baraa Bin Malik Brigade",
    acronym="BBMB",
    native_name="كتيبة البراء بن مالك",
    aliases=["Al-Bara' Ibn Malik Brigade", "Al-Baraa Bin Malik Battalion", "BBMB"],
    primary_type="armed_group",
    secondary_types=[],
    importance_level="L1",
    short_description="OFAC 记录成立日期为 2020 年 1 月 7 日的苏丹武装团体；2025 年 9 月遭美国制裁，2026 年 3 月 9 日被标注 [FTO] [SDGT] [SUDAN-EO14098] 并关联至苏丹穆斯林兄弟会。",
    full_description="巴拉·本·马利克旅是苏丹境内的武装团体，OFAC 记录其成立日期为 2020 年 1 月 7 日。美国财政部于 2025 年 9 月依据涉苏丹权限对其实施制裁，理由涉及其在苏丹战争中的作用及与伊朗的联系。2026 年 3 月 9 日，OFAC 将其列名更新为 [FTO] [SDGT] [SUDAN-EO14098]，并标注关联至苏丹穆斯林兄弟会。",
    current_status="active_armed_group_us_designated",
    primary_category="sudan_conflict_armed_group",
    tags=["苏丹", "武装团体"],
    region_ids=["region-sudan-red-sea-horn", "region-nile-basin-east-africa"],
    country_ids=["country-sudan"],
    confidence="medium_high",
    source_refs=[S_TREAS_SUDAN, S_OFAC_BBMB, S_OFAC_SMB],
)

PROF_BBMB = profile({
    "lead": "巴拉·本·马利克旅（Al-Baraa Bin Malik Brigade，BBMB）是苏丹境内的武装团体。美国 OFAC 记录其组织成立日期为 2020 年 1 月 7 日，并将其归类为武装团体。2025 年 9 月，美国财政部依据涉苏丹制裁权限对其实施制裁，理由涉及它在苏丹战争中的作用以及与伊朗的联系；2026 年 3 月 9 日，OFAC 进一步把它的列名更新为 [FTO] [SDGT] [SUDAN-EO14098]，并标注其关联至苏丹穆斯林兄弟会。",
    "name_and_translation": "中文名采用「巴拉·本·马利克旅」，英文规范名 Al-Baraa Bin Malik Brigade，缩写 BBMB。公开材料中另见 Al-Bara' Ibn Malik Brigade 与 Al-Baraa Bin Malik Battalion 两种写法，本平台一并收入别名索引，其中 Battalion 与 Brigade 的差异主要来自不同来源对建制层级的译法选择。",
    "formation_background": "美国 OFAC 记录的组织成立日期为 2020 年 1 月 7 日。这一日期来自美国法律文书的登记字段，属该机构的记录口径。围绕该组织成立的具体政治背景与发起过程，本内容包所依据的权威来源没有作系统说明，本页不作补充叙述。",
    "legal_status": {"p": [
        "2025 年 9 月 12 日：美国财政部依据涉苏丹权限对该组织实施制裁，同日 OFAC 完成列名。",
        "2026 年 3 月 9 日：OFAC 更新其列名标注为 [FTO] [SDGT] [SUDAN-EO14098]，并标记为「关联至：苏丹穆斯林兄弟会」。",
        "上述均为美国单方面的法律行为，本平台按归属于认定辖区的法律状态记录，不表述为国际共识。",
    ]},
    "force_capacity": "关于其人力规模，唯一可引用的公开表述来自美国财政部 2025 年 9 月的声明：该部门称该组织在对抗快速支援部队的冲突中投入了两万人以上的战斗人员。这一数字必须始终作为美国财政部的归属性陈述使用，并且不得转移记为苏丹伊斯兰运动／苏丹穆斯林兄弟会自身经核实的人力。此外，该表述指向的是冲突期间的累计投入，而非某一时点的常备编制。",
    "external_relations": "在关系层面可分为三类：其一，与苏丹武装部队之间是战时并肩作战关系；其二，与快速支援部队之间是交战关系；其三，与苏丹伊斯兰运动／苏丹穆斯林兄弟会之间存在美国法律文书所标注的关联。此外，美国政府关于伊朗伊斯兰革命卫队对其训练与支持的指控，因本平台尚未建立相应实体节点，已记入未决依赖清单，暂不建边。",
    "human_rights": "美国政府关于该组织涉及侵权、拘押、酷刑或处决的指控，在本平台一律作为明确归属于美国政府的指控保存，不改写为已确证事实。这一处理方式适用于本页所有源自单一政府来源的负面指控。",
    "organizational_relation": "为什么与苏丹伊斯兰运动分开建模：美国法律文书在别名与关联标注上使两者产生了部分重叠，但二者的组织性质不同——前者是政治与意识形态网络，后者是实际参战的武装团体。若合并，则「政治网络」与「武装力量」两类完全不同的行为主体将无法在数据层区分，进而导致人力、行为与法律责任的错误归属。",
    "current_situation": "该组织当前处于活跃状态，并同时处于美国多重制裁标注之下。其角色主要体现在苏丹内战的实际作战层面，与政治网络的角色需要分开评估。",
    "regional_impact": "作为苏丹内战中的参战方之一，其活动主要影响苏丹境内的冲突态势。由于苏丹同时归属非洲之角关联区与尼罗河流域安全带，其行为的外溢效应需在这两个区域框架下一并观察。",
    "events": {"p": [
        "2020 年 1 月 7 日：OFAC 记录的组织成立日期。",
        "2025 年 9 月 12 日：美国财政部实施制裁并由 OFAC 列名，理由涉及其在苏丹战争中的作用与涉伊朗联系。",
        "2025 年 9 月：美国财政部称其在对抗快速支援部队的冲突中投入两万人以上战斗人员（归属性陈述）。",
        "2026 年 3 月 9 日：OFAC 更新列名为 [FTO] [SDGT] [SUDAN-EO14098]，标注关联至苏丹穆斯林兄弟会。",
    ]},
    "uncertainties": {"list": [
        "两万人以上的表述来自美国财政部单一来源，缺少可交叉验证的独立数据，且未说明统计时点与口径。",
        "美国法律文书中的「关联至」标注，其法律含义与实际组织从属关系之间的对应程度并不明确。",
        "关于伊朗方面训练与支持的指控属美国政府陈述，本平台未获得可独立核验的佐证材料。",
    ]},
    "controversies_uncertainties": "该实体最主要的争议在于它与苏丹伊斯兰运动之间的边界。美国法律文书通过「关联至」的方式建立了两者的形式联系，但这既不等同于隶属，也不足以支持把一方的人力或行为直接记入另一方名下。",
    "asip_analysis": "ASIP 判断：该组织是观察苏丹内战中「政治网络—武装力量」耦合关系的关键样本。分析时应严格区分三个层次——可核实的登记事实（成立日期、列名标注）、归属性的政府陈述（人力规模、涉伊朗指控），以及平台自身的结构性判断。把第二层当作第一层使用，是这一议题上最常见的误读方式。",
    "watch_indicators": [
        "OFAC 是否进一步调整其列名标注或关联对象。",
        "是否出现独立来源对两万人以上表述的验证或修正。",
        "其与苏丹武装部队之间的协同方式是否发生公开变化。",
        "美国之外的司法辖区是否跟进列名。",
        "是否出现关于其指挥层的可靠公开信息。",
    ],
    "core_assessment": "该武装是苏丹内战中一支被美国多重制裁标注的参战力量，其档案的处理难点不在于事件本身，而在于严格维持事实、政府指控与平台分析三者之间的分层。",
    "sources": [
        "U.S. Department of the Treasury：《Treasury Targets Sudanese Islamist Actors》（12 Sep 2025）（https://home.treasury.gov/news/press-releases/sb0246）",
        "U.S. OFAC：《Sudan-related Designations》（12 Sep 2025）（https://ofac.treasury.gov/recent-actions/20250912）",
        "U.S. OFAC：《Counter Terrorism Designations; Sudan-related Designation Update》（9 Mar 2026）（https://ofac.treasury.gov/recent-actions/20260309）",
    ],
}, importance="L1")


ORG_ENTITIES = [ENT_SHABAAB, ENT_ISS, ENT_KARRAR, ENT_ADF, ENT_SIM, ENT_BBMB]

ORG_PROFILES = {
    "actor-al-shabaab": PROF_SHABAAB,
    "actor-isis-somalia": PROF_ISS,
    "actor-al-karrar-office": PROF_KARRAR,
    "actor-adf-isis-ca": PROF_ADF,
    "actor-sim": PROF_SIM,
    "actor-bbmb": PROF_BBMB,
}

# --- force estimates (dated, sourced) ---
ORG_FORCE_ESTIMATES = {
    "actor-al-shabaab": [{
        "estimate_min": 7000,
        "estimate_max": 12000,
        "estimate_text": "约 7,000—12,000 名成员",
        "estimate_date": "2026-04",
        "estimate_scope": "NCTC 截至 2026 年 4 月的机构估计；公开材料未说明是否包含后勤与附属人员。",
        "included_components": [],
        "excluded_components": [],
        "source_ids": [S_SHABAAB_NCTC],
        "confidence": "medium_high",
        "trend": "stable",
        "notes": "区间估计，不得作为精确常备兵力使用。",
    }],
    "actor-isis-somalia": [{
        "estimate_min": 700,
        "estimate_max": 1500,
        "estimate_text": "约 700—1,500 名战斗人员",
        "estimate_date": "2025-02",
        "estimate_scope": "NCTC 截至 2025 年 2 月的机构估计。",
        "included_components": [],
        "excluded_components": [],
        "source_ids": [S_ISS_NCTC],
        "confidence": "medium",
        "trend": "decreasing",
        "notes": "此后邦特兰反恐行动造成实质性损失，该数字不得作为无时间标注的当前兵力使用。",
    }],
    "actor-adf-isis-ca": [{
        "estimate_min": 1000,
        "estimate_max": 1500,
        "estimate_text": "约 1,000—1,500 名成员",
        "estimate_date": "2025-04",
        "estimate_scope": "NCTC 截至 2025 年 4 月的机构估计。",
        "included_components": [],
        "excluded_components": [],
        "source_ids": [S_ISCA_NCTC],
        "confidence": "medium_high",
        "trend": "stable",
        "notes": "公开材料未说明统计边界，与其他机构口径不具备直接可比性。",
    }],
    "actor-bbmb": [{
        "estimate_min": 20000,
        "estimate_max": None,
        "estimate_text": "美国财政部称其在对抗快速支援部队的冲突中投入两万人以上战斗人员",
        "estimate_date": "2025-09",
        "estimate_scope": "美国财政部 2025 年 9 月声明中的累计投入表述，非某一时点的常备编制；属归属性政府陈述。",
        "included_components": [],
        "excluded_components": [],
        "source_ids": [S_TREAS_SUDAN],
        "confidence": "medium",
        "trend": "unknown",
        "notes": "该数字不得转记为苏丹伊斯兰运动／苏丹穆斯林兄弟会自身经核实的人力。",
    }],
}

# --- external links (authoritative only; pack provides no wikipedia URLs) ---
ORG_EXTERNAL_LINKS = {
    "actor-al-shabaab": {"wikipedia": [], "authoritative": [
        {"label": "NCTC — Al-Shabaab", "url": "https://www.odni.gov/nctc/terrorist_groups/al_shabaab.html"},
        {"label": "U.S. Treasury — TFTC Designates Al-Shabaab Networks (2025-04-14)", "url": "https://home.treasury.gov/news/press-releases/sb0084"},
    ]},
    "actor-isis-somalia": {"wikipedia": [], "authoritative": [
        {"label": "NCTC — ISIS-Somalia", "url": "https://www.odni.gov/nctc/terrorist_groups/isis_somalia.html"},
        {"label": "U.S. Treasury — Senior ISIS-Somalia Financier (2023-07-27)", "url": "https://home.treasury.gov/news/press-releases/jy1652"},
    ]},
    "actor-al-karrar-office": {"wikipedia": [], "authoritative": [
        {"label": "U.S. Treasury — Countering ISIS Financing Fact Sheet", "url": "https://home.treasury.gov/system/files/136/Fact-Sheet-Countering-ISIS-Financing-2-27-24.pdf"},
        {"label": "NCTC — ISIS-Somalia", "url": "https://www.odni.gov/nctc/terrorist_groups/isis_somalia.html"},
    ]},
    "actor-adf-isis-ca": {"wikipedia": [], "authoritative": [
        {"label": "NCTC — ISIS-Central Africa", "url": "https://www.odni.gov/nctc/terrorist_groups/isis_ca.html"},
        {"label": "NCTC — ISIS-DRC (historical)", "url": "https://www.odni.gov/nctc/terrorist_groups/isis_drc.html"},
    ]},
    "actor-sim": {"wikipedia": [], "authoritative": [
        {"label": "U.S. OFAC — Designation Update (2026-03-09)", "url": "https://ofac.treasury.gov/recent-actions/20260309"},
        {"label": "EU — Council Implementing Regulation (EU) 2024/1783", "url": "https://eur-lex.europa.eu/eli/dec/2024/1784"},
    ]},
    "actor-bbmb": {"wikipedia": [], "authoritative": [
        {"label": "U.S. Treasury — Sudanese Islamist Actors (2025-09-12)", "url": "https://home.treasury.gov/news/press-releases/sb0246"},
        {"label": "U.S. OFAC — Sudan-related Designations (2025-09-12)", "url": "https://ofac.treasury.gov/recent-actions/20250912"},
    ]},
}
