# -*- coding: utf-8 -*-
"""Expansion C: ENRICH patches for the four existing core entities.

Each patch is a dict of section key -> new content applied over the existing
profile sections (replacing the key if present, adding if missing). The four
existing entities are already encyclopedia_full; these patches close the
specific coverage gaps required by the content pack (GSPC continuity chapter,
2016 reemergence, 2013 merger mechanics + 2015 faction-only defection, etc.).
"""
from expansion_c_content_orgs_a import TODAY

S_UN_GIA = "expc-un-gia"
S_UN_AQIM = "un-aqim-2001"
S_NCTC_AQIM = "deptha-nctc-aqim-2026-06"
S_NCTC_AAD = "expc-nctc-ansar-dine"
S_NCTC_MURAB = "expc-nctc-murabitun"
S_NCTC_ISSAHEL = "deptha-nctc-is-sahel-2026-06"
S_UN_JNIM = "un-jnim-2018"
S_NCTC_JNIM = "d2-nctc-jnim-2026-05"

# =====================================================================
# ENRICH 1: AQIM — GIA -> GSPC -> AQIM continuity + lineage splits
# =====================================================================
ENRICH_AQIM = {
    "entity_id": "actor-aqim",
    "add_aliases": [],
    "add_historical_names": [],  # GSPC already in aliases + historical_names
    "sections": {
        "formation_background": "AQIM 的谱系起点是阿尔及利亚武装伊斯兰集团（GIA）：1998 年哈桑·哈塔布（Hassan Hattab）自 GIA 分裂成立萨拉菲宣教与战斗组织（GSPC，Groupe Salafiste pour la Prédication et le Combat）。阿卜杜勒马利克·德鲁克德勒（Abdelmalek Droukdel）曾任 GIA 爆炸物专家，后成为 GSPC/AQIM 领导人。2007 年 1 月 GSPC 采用 AQIM（伊斯兰马格里布基地组织）名称，构成 GIA → GSPC → AQIM 的组织连续性。",
        "history": "AQIM 的完整谱系：1998 年哈塔布自 GIA 分裂创立 GSPC；2001 年 10 月 6 日联合国以 GSPC 名称列名该实体；2006 年 9 月 11 日基地组织领导层宣布联合/联盟，NCTC 描述 GSPC 于 2006 年 9 月与基地组织结盟；2007 年 1 月 GSPC 采用 AQIM 名称。此后 AQIM 在阿尔及利亚与萨赫勒地区演化：通过赎金/绑架获取资金，建立撒哈拉埃米尔区（Sahara Emirate），经历分裂（MUJAO、al-Mulathamun 营及 ISIS 倾向派别的脱离），并参与 2012 年马里北部武装格局。2012 年中期起与安萨尔埃丁（Ansar al-Dine）建立关联。2020 年德鲁克德勒死亡后领导层继任，2026 年仍为活跃的基地组织附属组织并保有萨赫勒分支联系。",
        "organizational_relation": "AQIM 的谱系关系包括：分裂自 GIA（1998，经 GSPC）；2006 年 9 月向基地组织结盟/联合（2007 年更名 AQIM）；与安萨尔埃丁自 2012 年中期起存在关联（affiliated_with）；构成 JNIM 2017 年合并的组成部分之一（其萨赫勒分支力量与结构并入 JNIM）；MUJAO 为自 AQIM 分裂的派别；al-Mulathamun 营及部分 ISIS 倾向派别亦自 AQIM 体系脱离。本档案将这些关系分别以现有关系类型表达，并在各关系档案中说明具体机制。",
        "current_situation": "截至 2026 年（NCTC 2026 年 6 月档案为当前锚定来源），AQIM 仍为活跃的基地组织附属组织，保有萨赫勒分支联系（与 JNIM 体系并存的结构性关联）。德鲁克德勒 2020 年死亡后的领导层继任情况以其公开档案为准；本平台不推测未公开的继任细节。",
        "events": {"list": [
            "1998：哈桑·哈塔布自 GIA 分裂创立 GSPC。",
            "2001-10-06：联合国以 GSPC 名称列名该实体。",
            "2006-09-11：基地组织领导层宣布联合/联盟；NCTC 描述 GSPC 与基地组织结盟。",
            "2007-01：GSPC 采用 AQIM 名称。",
            "2012：参与马里北部武装格局；2012 年中期起与安萨尔埃丁建立关联。",
            "2013 前后：MUJAO/al-Mulathamun 等派别自 AQIM 体系分裂/脱离。",
            "2017-03：其萨赫勒分支力量与结构并入 JNIM（构成关系，历史）。",
            "2020：德鲁克德勒死亡，领导层继任。",
            "2026：仍为活跃基地组织附属组织，保有萨赫勒分支联系。",
        ]},
        "asip_analysis": "ASIP 判断：AQIM 的核心谱系事实是 GIA → GSPC → AQIM 的单一组织连续性——GSPC 不是独立组织，而是 AQIM 的 1998—2007 历史阶段（2006 年与基地组织结盟、2007 年更名）。评估 AQIM 时需同时跟踪四层：与基地组织的效忠/联盟关系、与 JNIM 的结构性关联、萨赫勒分支网络的独立性（含 ISIS 倾向派别的脱离）、以及德鲁克德勒之后的领导连续性。",
        "uncertainties": {"list": [
            "GSPC 与基地组织结盟（2006）到更名 AQIM（2007）之间的内部进程细节存在来源差异。",
            "德鲁克德勒死亡后的完整领导层结构缺乏系统性公开披露。",
            "AQIM 萨赫勒分支与 JNIM 之间的指挥边界存在模糊性。",
        ]},
    },
    "source_refs_add": [S_UN_GIA, S_UN_AQIM, S_NCTC_AQIM],
}

# =====================================================================
# ENRICH 2: Ansar al-Dine — formation/AQIM association/JNIM merger
# =====================================================================
ENRICH_ANSAR = {
    "entity_id": "actor-ansar-eddine",
    "add_aliases": ["Ansar al-Dine", "AAD"],
    "add_historical_names": [],
    "sections": {
        "formation_background": "安萨尔埃丁（Ansar al-Dine / Ansar Dine）于 2011 年 11 月在伊亚德·阿格·加利（Iyad Ag Ghali）领导下成立，属于图阿雷格族源的武装组织。其形成处于马里北部图阿雷格动员与地区动荡的背景中。",
        "history": "2011 年 11 月成立后，安萨尔埃丁在 2012 年马里政变后的背景下夺取马里北部领土；2012 年中期起与 AQIM 建立关联；2013 年法国军事干预使其撤离北部据点；2016 年重新出现；2017 年 3 月与另外三支组织合并组建 JNIM，伊亚德·阿格·加利成为 JNIM 埃米尔。NCTC（2026 年 4 月）仍描述安萨尔埃丁的袭击与 JNIM 组成组织并列发生。",
        "organizational_relation": "安萨尔埃丁的两条核心关系：其一，2012 年中期起与 AQIM 的关联（affiliated_with，历史）；其二，2017 年 3 月并入 JNIM（constituent_of，结构并入），其领导人伊亚德·阿格·加利出任 JNIM 埃米尔。本档案以现有关系类型分别表达，并在关系档案中说明时间与机制。",
        "current_situation": "安萨尔埃丁作为 JNIM 的组成力量运作：2017 年并入后不再作为独立组织存在，NCTC 描述其袭击与 JNIM 其他组成组织并列发生。其历史角色是 JNIM 体系中马里北部核心力量的来源之一。",
        "events": {"list": [
            "2011-11：伊亚德·阿格·加利领导下成立。",
            "2012：马里政变背景下夺取北部领土。",
            "2012 年中期：与 AQIM 建立关联。",
            "2013：法国军事干预使其撤离北部。",
            "2016：重新出现。",
            "2017-03：与另三支组织合并组建 JNIM；伊亚德·阿格·加利任 JNIM 埃米尔。",
        ]},
        "asip_analysis": "ASIP 判断：安萨尔埃丁的档案核心是「JNIM 组建单元」——2017 年并入 JNIM 后其组织身份让位于 JNIM 体系。评估时应把三个时期分开：2011—2012 独立武装、2012—2017 与 AQIM 关联的北部势力、2017 至今 JNIM 组成单元；伊亚德·阿格·加利的人事连续性（组织创建者→JNIM 埃米尔）是理解 JNIM 领导结构的关键线索。",
        "uncertainties": {"list": [
            "安萨尔埃丁在 2012—2013 年北部控制期间与 AQIM 的实际协调程度存在来源差异。",
            "并入 JNIM 后其内部结构与行动自主度缺乏系统公开披露。",
        ]},
    },
    "source_refs_add": [S_NCTC_AAD, S_UN_JNIM, S_NCTC_JNIM],
}

# =====================================================================
# ENRICH 3: Al-Murabitun — 2013 merger + 2015 faction-only defection
# =====================================================================
ENRICH_MURABITUN = {
    "entity_id": "actor-al-mourabitoun",
    "add_aliases": [],
    "add_historical_names": ["al-Mulathamun 营（相关前身）"],
    "sections": {
        "formation_background": "穆拉比通（Al-Murabitun / Al-Mourabitoun）于 2013 年由穆赫塔尔·贝尔穆赫塔尔（Mokhtar Belmokhtar）的 al-Mulathamun 营与另一个 AQIM 分裂派别（通常认定为 MUJAO/西非认主独一与圣战）合并而成（NCTC 表述）。其形成处于萨赫勒武装格局的再组合时期，属于基地组织一翼。",
        "history": "2013 年合并成立后，穆拉比通以基地组织阵营定位运作，历史上袭击酒店、餐厅、矿场与能源设施，以及军事/联合国目标。2015 年，一个派别脱离并投向伊斯兰国，成为 ISIS-Sahel 谱系的来源（仅该派别，而非整个组织）；贝尔穆赫塔尔派系保持基地组织结盟。2017 年 3 月，穆拉比通作为四支组成组织之一并入 JNIM；此后在 JNIM 体系内运作。",
        "organizational_relation": "穆拉比通的三条核心谱系关系：其一，2013 年由 al-Mulathamun 营与 MUJAO 派别合并形成（与 MUJAO 以 historically_associated_with 表达合并语义，机制见档案）；其二，2017 年并入 JNIM（constituent_of）；其三，2015 年一个派别脱离投向 ISIS，形成 ISIS-Sahel 谱系来源（历史关联，faction-only 限定）。本档案明确：2015 年脱离的是派别而非整个组织，贝尔穆赫塔尔派系保持基地组织结盟。",
        "current_situation": "穆拉比通现于 JNIM 体系内运作（2017 年并入后为 JNIM 组成力量）；其独立组织身份让位于 JNIM 体系，但历史档案保留其 2013—2017 年独立阶段。",
        "events": {"list": [
            "2013：由 al-Mulathamun 营与 MUJAO 派别合并成立。",
            "2013—2017：以基地组织阵营定位运作，袭击酒店、餐厅、矿场、能源设施及军事/联合国目标。",
            "2015：一个派别脱离投向伊斯兰国（ISIS-Sahel 谱系来源；faction-only，非全组织）。",
            "2017-03：作为四支组成组织之一并入 JNIM。",
            "此后：在 JNIM 体系内运作。",
        ]},
        "asip_analysis": "ASIP 判断：穆拉比通的档案核心是「2015 年派别分离的限定性」——只有脱离投向伊斯兰国的那个派别构成 ISIS-Sahel 谱系，绝不可写成整个穆拉比通转化为 ISIS-Sahel。同时需区分：贝尔穆赫塔尔派系（基地组织结盟）与脱离派系（ISIS 投向）在 2015 年后分属两个谱系，2017 年基地一翼并入 JNIM。评估萨赫勒网络时，这三条线（并入 JNIM、派别投向 ISIS-Sahel、历史袭击史）必须分开处理。",
        "uncertainties": {"list": [
            "2015 年脱离派别的规模与构成缺乏系统性公开统计。",
            "穆拉比通在 JNIM 体系内的内部结构与行动自主度披露有限。",
            "贝尔穆赫塔尔本人的公开状态与角色存在时效性不确定性。",
        ]},
    },
    "source_refs_add": [S_NCTC_MURAB, S_NCTC_ISSAHEL, S_UN_JNIM],
}

# =====================================================================
# ENRICH 4: Katiba Macina — NCTC four-group merger facts + timeline
# =====================================================================
ENRICH_MACINA = {
    "entity_id": "actor-katiba-macina",
    "add_aliases": [],
    "add_historical_names": [],
    "sections": {
        "formation": "马西纳解放阵线（Macina Liberation Front，MLF，平台规范名 Katibat Macina / 马西纳旅）由阿马杜·库法（Amadou Koufa）创建并担任埃米尔；库法同时是 JNIM 的副手级/创始成员。NCTC 将马西纳解放阵线列为 2017 年 3 月合并组建 JNIM 的四支组织之一。",
        "history": "马西纳旅以马里中部马西纳地区为核心，是 JNIM 向马里中部及邻近地区扩张与行动的关键力量。2017 年 3 月作为四支组成组织之一并入 JNIM 后，其在 JNIM 体系内运作，构成 JNIM 在中部马里的核心子单元；阿马杜·库法作为其创始人与埃米尔，同时是 JNIM 的副手级人物。",
        "current_situation": "马西纳旅当前为 JNIM 的活跃组成单元，是 JNIM 在中部马里及其邻近地区行动足迹的核心力量；其独立组织身份让位于 JNIM 体系，但作为子单元保留名称与地方身份。",
        "events": {"list": [
            "2015 年前后：阿马杜·库法创立马西纳解放阵线（具体年份以来源为准）。",
            "2017-03：作为四支组成组织之一并入 JNIM（NCTC）。",
            "此后：作为 JNIM 中部马里核心子单元运作并扩张。",
        ]},
        "asip_analysis": "ASIP 判断：马西纳旅的档案核心是「JNIM 中部马里支柱」——它是 JNIM 向马里中部及邻近地带扩张的关键组成单元，库法的人事连续性（创始人→JNIM 副手级）是 JNIM 领导结构的重要组成部分。评估时需区分：马西纳旅作为 JNIM 组成单元（2017 至今）与其独立阶段（2017 年前）的边界，以及其在 JNIM 内部相对其他组成单元（如安萨尔埃丁、穆拉比通）的职能分工。",
    },
    "source_refs_add": [S_NCTC_JNIM, S_UN_JNIM],
}

ENRICH_PATCHES = [ENRICH_AQIM, ENRICH_ANSAR, ENRICH_MURABITUN, ENRICH_MACINA]
