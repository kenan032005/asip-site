# -*- coding: utf-8 -*-
"""Final Depth Consolidation Pack A — 4 P0 relationship dossier enrichments.

Authoritative facts strictly from ASIP-FINAL-DEPTH-CONSOLIDATION-PACK-A.
Each entry provides profile section overrides + timeline nodes.
"""

REL_SUPPLEMENTS = {
    # =====================================================================
    "rel-jnim-benin-forces-fought": {
        "profile": {
            "formation_background": "JNIM 自 2020 年代起通过 Katiba Hanifa 等单元向贝宁北部渗透，将 W-Arly-Pendjari 跨境保护区及 Alibori 等边境省份作为扩张通道；贝宁安全力量随之将北部反恐与边境管控列为优先。",
            "evolution_stages": "冲突由最初的边境渗透与零星袭击，发展为 2025 年 1 月起的升级：JNIM 在北部边境持续施压，2025 年 4 月 17 日对 Alibori 贝宁军事据点发动袭击，贝宁随后报告至少 54 名士兵死亡；此后 JNIM 在 2025 年 6—11 月宣称继续实施边境袭击，2026 年冲突仍在延续。",
            "current_status": "持续敌对；JNIM 在贝宁北部的袭击与贝宁安全力量的反制构成 2025—2026 年贝宁安全压力的核心战线。",
            "why_it_matters": "贝宁是 JNIM 从萨赫勒向几内亚湾沿岸扩张的关键前沿；北部袭击的升级直接威胁贝宁国家安全，并牵动区域反恐合作与跨境协调约束。",
            "uncertainties": "JNIM 自报的伤亡数字不得作为贝宁政府确认数字；冲突的精确伤亡、JNIM 在贝宁境内的兵力规模与指挥结构存在不确定性。",
            "asip_analysis": "JNIM 在贝宁的扩张揭示萨赫勒圣战向沿海国家外溢的结构性趋势；贝宁安全力量在跨境协调受限的情况下独自应对，暴露区域机制的短板。",
            "watch_indicators": [
                "贝宁北部 Alibori/Atacora 的袭击频率",
                "JNIM 向几内亚湾沿岸的进一步扩张",
                "贝宁与邻国跨境反恐协调的加强",
            ],
            "source_ids": ["asa-benin-2025", "defenceweb-benin-2026", "crisiswatch-2026-06"],
        },
        "timeline": [
            {"date": "2020 年代前期", "event_title": "渗透", "event_description": "JNIM 通过 Katiba Hanifa 等单元向贝宁北部渗透，聚焦 W-Arly-Pendjari 跨境区。"},
            {"date": "2025-01", "event_title": "升级", "event_description": "JNIM 在贝宁北部边境施压升级。"},
            {"date": "2025-04-17", "event_title": "Alibori 袭击", "event_description": "JNIM 袭击 Alibori 贝宁军事据点，贝宁报告至少 54 名士兵死亡。"},
            {"date": "2025-06~11", "event_title": "边境袭击持续", "event_description": "JNIM 宣称继续在边境实施袭击。"},
            {"date": "2026", "event_title": "延续", "event_description": "冲突延续，贝宁安全力量持续反制并调整部署。"},
        ],
    },

    # =====================================================================
    "rel-d1-dan-na-jnim-conflict": {
        "profile": {
            "formation_background": "Dan Na Ambassagou 于 2016 年在中马里社群冲突与圣战不安全背景下成立，作为多贡自卫民兵长期与 JNIM 敌对；这一敌对嵌入中马里更广泛的社群-安全冲突格局，而非简单的多贡对富拉尼二元对立。",
            "evolution_stages": "JNIM 持续对多贡民兵阵地与社区施压，2021 年 10 月民兵/多佐试图打破 JNIM 对 Marebougou 一带的封锁并付出重大伤亡；此后 JNIM 通过军事袭击与地方协商/协议两手策略侵蚀民兵影响，2024—2025 年持续施压。",
            "current_status": "持续敌对；JNIM 将削弱 Dan Na 及关联多佐阵地作为其在中马里扩展地方协议、压缩社区武装空间的优先战线。",
            "why_it_matters": "这条关系是 JNIM 在中马里削弱社区自卫武装、重塑地方安全格局的核心机制，关系到国家与民兵关系的走向。",
            "uncertainties": "具体伤亡、地方协议的范围与民兵当前战斗力存在不确定性；不得将复杂冲突简化为族群对立。",
            "asip_analysis": "JNIM 对 Dan Na 的持续打击是其「分化社区武装 + 扩大地方协议」战略的体现，旨在取代国家与民兵对地方安全秩序的控制。",
            "watch_indicators": [
                "JNIM 对多贡民兵阵地的袭击频率",
                "Dan Na 与 FAMa 关系的演变",
                "地方协议与民兵影响力的消长",
            ],
            "source_ids": ["d2-acled-dan-na-profile"],
        },
        "timeline": [
            {"date": "2016", "event_title": "民兵成立", "event_description": "Dan Na Ambassagou 成立，与 JNIM 敌对关系确立。"},
            {"date": "2021-10", "event_title": "Marebougou 封锁", "event_description": "民兵/多佐尝试打破 JNIM 封锁，付出重大伤亡。"},
            {"date": "2024—2025", "event_title": "持续施压", "event_description": "JNIM 继续施压，军事袭击与地方协议并用。"},
            {"date": "2026-05", "event_title": "再集中打击", "event_description": "JNIM 重新集中打击 Dan Na 及关联多佐阵地。"},
        ],
    },

    # =====================================================================
    "rel-d2-jafar-jnim": {
        "profile": {
            "formation_background": "贾法尔·迪科（Jafar Dicko）于 2017 年继承其兄易卜拉欣·马拉姆·迪科成为 Ansaroul Islam 的领导人；Ansaroul Islam 作为 JNIM 体系内的布基纳法索分支，使贾法尔成为 JNIM 在布基纳法索的关键领导人物。",
            "initial_relationship": "贾法尔与阿马杜·库法（Amadou Koufa）及 JNIM 体系存在组织联系，Ansaroul Islam 在保留地方认同的同时融入 JNIM。",
            "evolution_stages": "2017 年继承领导后，贾法尔将 Ansaroul Islam 带入 JNIM 体系，并在布基纳法索北部扩展影响；2026 年 HRW 报告称其为 JNIM 在布基纳法索的领导人，Mapping Militants 仍将其列为主要 Ansaroul Islam 领导人。",
            "current_status": "现役；贾法尔·迪科是 Ansaroul Islam 领导人与 JNIM 在布基纳法索的现任/资深领导人，但不是整个 JNIM 的埃米尔（伊亚德·阿格·加利仍是更广泛的 JNIM 领导人）。",
            "why_it_matters": "厘清贾法尔的准确角色是理解布基纳法索北部 JNIM 指挥结构与家族化领导的关键，避免误判其层级。",
            "uncertainties": "布基纳法索 JNIM 内部指挥层级与贾法尔/乌斯曼·迪科的分工存在不确定性。",
            "asip_analysis": "迪科家族的跨代领导（易卜拉欣→贾法尔→乌斯曼）说明布基纳法索 JNIM 领导层高度家族化，这既是动员优势也是继承合法性的风险点。",
            "watch_indicators": [
                "布基纳法索 JNIM 指挥结构的进一步披露",
                "迪科家族领导层更替或内部分歧",
            ],
            "source_ids": ["d2-hrw-burkina-2026-04-02", "expd-mapping-ansaroul-islam"],
        },
        "timeline": [
            {"date": "2016-12", "event_title": "Nassoumbou", "event_description": "易卜拉欣领导 Ansaroul Islam 公开崛起。"},
            {"date": "2017", "event_title": "继任", "event_description": "易卜拉欣死亡，贾法尔继任 Ansaroul Islam 领导人。"},
            {"date": "2017—2025", "event_title": "融入 JNIM", "event_description": "Ansaroul Islam 融入 JNIM，贾法尔成为布基纳法索关键领导人物。"},
            {"date": "2026", "event_title": "现任", "event_description": "HRW 称其为 JNIM 布基纳法索领导人；Mapping Militants 仍列为主要 Ansaroul Islam 领导人。"},
        ],
    },

    # =====================================================================
    "rel-d2-dozos-macina-jnim-conflict": {
        "profile": {
            "formation_background": "Dozos of Macina 是中马里马西纳地区传统多佐猎人在冲突中军事化形成的自卫武装网络，与 JNIM/卡蒂巴·马西纳环境处于敌对关系；这一敌对嵌入地方冲突与协商动态，而非全国性正式反恐同盟。",
            "evolution_stages": "JNIM 通过军事袭击、地方协议与社区压力削弱多佐武装，形成局部化的武装对抗；多佐网络在村庄/社区自卫与地方协商之间摇摆，同时与 FAMa 存在互动。",
            "current_status": "持续敌对但嵌入地方冲突与协商；Dozos of Macina 与 JNIM 的对抗是中马里地方安全格局的一部分。",
            "why_it_matters": "这条关系揭示 JNIM 如何在中马里分化并削弱社区自卫力量，同时也反映地方武装在与圣战对抗和协商之间的脆弱平衡。",
            "uncertainties": "多佐网络与 JNIM 的对抗/协商边界、网络规模与领导结构存在不确定性。",
            "asip_analysis": "Dozos of Macina 与 JNIM 的关系是「地方自卫武装 vs 圣战网络」嵌入更大社群-安全冲突的样本，不能简化为全国性反恐同盟。",
            "watch_indicators": [
                "JNIM 对多佐阵地的袭击与地方协议",
                "Dozos of Macina 与 FAMa 的整合",
            ],
            "source_ids": ["d1-acled-dozo-2026"],
        },
        "timeline": [
            {"date": "2010 年代", "event_title": "军事化", "event_description": "中马里冲突中多佐猎人军事化。"},
            {"date": "2018—2023", "event_title": "结构化", "event_description": "形成以苏莱耶为中心的结构化网络，与 JNIM 对抗。"},
            {"date": "2023—2025", "event_title": "对抗-协商", "event_description": "JNIM 以袭击与地方协议削弱多佐武装。"},
            {"date": "2026", "event_title": "现状", "event_description": "对抗持续，嵌入地方冲突与协商动态。"},
        ],
    },
}
