# -*- coding: utf-8 -*-
"""Final Depth Consolidation Pack A — 9 retained Grade-D entity enrichments.

Authoritative facts strictly from ASIP-FINAL-DEPTH-CONSOLIDATION-PACK-A.
Each entry is a dict of NEW/OVERRIDE sections merged into the entity profile.
"""
# Mapping of source URLs from the pack to repository source_ids (reuse first).
PACK_SOURCES = {
    "katiba_serma": [
        "https://africacenter.org/publication/puzzle-jnim-militant-islamist-groups-sahel/",
        "https://enactafrica.org/enact-observer/jnim-cuts-a-path-into-southern-mali",
        "https://www.aa.com.tr/fr/afrique/mali-larm%C3%A9e-de-laes-neutralise-le-num%C3%A9ro-2-de-lorganisation-katiba-serma/3436301",
        "https://www.wathi.org/laboratoire/choix_de_wathi/non-state-armed-group-and-illicit-economies-in-west-africa-jamaat-nusrat-al-islam-wal-muslimin-jnim-global-initiative-against-transnational-organized-crime-and-acled-october-2023/",
    ],
}

ORG_SUPPLEMENTS = {
    # =====================================================================
    "actor-katiba-serma": {
        "name_identity": "塞尔马旅（Katiba Serma）得名于其在中马里 Douentza 一带 Serma 森林的活动基地，是一个与 JNIM 关联、以当地森林为据点的圣战行动单位（katiba）。",
        "history": "Katiba Serma 作为 JNIM 体系内的行动单位出现，活动范围集中在 Douentza 至 Boni、Hombori 一线及 RN16 公路走廊。它被不同来源分别描述为 Katiba Macina/FLM 的分支、JNIM 的组成部分，或与 JNIM 关联的自主武装团体；其内部指挥关系并不完全透明。",
        "leadership": "Katiba Serma 的领导层公开信息有限。2024 年 12 月，媒体报道马里军队与 AES 部队在行动中击毙了据称为该组织二号人物的 Moussa Himma Diallo，这一事件是其领导层少数被公开确认的个案。",
        "geography": "主要活动区为马里中部 Serma 森林周边，覆盖 Douentza、Boni、Hombori 等城镇及连接它们的 RN16 公路走廊，并向周边农村地带延伸。",
        "tactics": "该组织以公路封锁、简易爆炸装置（IED）/地雷布设和对车队的袭扰为主要战术，通过控制 RN16 等交通线对地方施加压力；同时伴以对平民的胁迫与地方治理行为。",
        "relationships": "与 Katiba Macina / FLM 存在渊源，被视为 JNIM 体系内的行动单元；与 JNIM 的关系介于组成部分与具备相当地方自主性的关联团体之间。",
        "local_arrangements": "2022 年 Boni 一带曾出现封锁与地方协商安排，反映该组织在暴力施压之外也通过地方性交易维持控制与通行秩序。",
        "current_posture": "截至 2026 年，Katiba Serma 仍被视为马里中部 JNIM 体系内活跃的行动单元，继续以森林据点和交通线为中心活动，但确切兵力与指挥状态缺乏公开确认。",
        "timeline": [
            "2022：Boni 一带封锁与地方协议。",
            "2023—2024：RN16 走廊与 Douentza 周边持续活动，IED/地雷与车队袭扰。",
            "2024-12：媒体报道马里军队/AES 部队击毙据称二号人物 Moussa Himma Diallo。",
            "2026：仍作为 JNIM 体系内活跃单元存在。",
        ],
        "uncertainties": "其与 Katiba Macina/FLM 及 JNIM 的精确指挥关系、当前兵力规模与领导层结构均缺乏公开确认。",
        "asip_analysis": "Katiba Serma 体现了 JNIM 在马里中部以半自主行动单元嵌入地方冲突与交通线的模式；对其领导层的打击不会改变这一结构本身。",
        "watch_indicators": [
            "RN16 走廊封锁与 IED 活动频率",
            "与 Katiba Macina/FLM 指挥关系的新披露",
            "领导层更替与地方协议动向",
        ],
    },

    # =====================================================================
    "person-ibrahim-malam-dicko": {
        "biography": "易卜拉欣·马拉姆·迪科（出生名 Boureima Dicko）是布基纳法索苏姆（Soum）地区出身的富拉尼传教士，创立了 Ansaroul Islam。他在 Djibo/Soum 一带建立 Al-Irchad 网络并广泛布道，后与阿马杜·库法（Amadou Koufa）及马里圣战网络建立联系并逐步激进化，2016 年 12 月 Nassoumbou 袭击标志着该组织的公开崛起。",
        "history": "迪科早年接受宗教教育，通过 Al-Irchad 网络在苏姆地区发展影响；在转向武装地下活动后创立 Ansaroul Islam。2016 年 12 月对 Nassoumbou 军营的袭击是其武装化后的标志性事件。",
        "relationships": "与阿马杜·库法及其卡蒂巴·马西纳网络存在直接联系，是布基纳法索与马里圣战网络之间的重要节点；Ansaroul Islam 日后融入 JNIM 体系。",
        "succession": "2017 年迪科在反恐压力下死亡（具体情节各来源说法不一），由其兄弟贾法尔·迪科（Jafar Dicko）继任领导 Ansaroul Islam。",
        "current_status": "已故（deceased_2017）。",
        "historical_significance": "作为 Ansaroul Islam 的创始人，迪科是布基纳法索北部圣战化进程的关键人物，其死亡并未终结该组织，反而由家族网络（迪科家族）延续领导。",
        "timeline": [
            "早年：出生于苏姆地区，接受宗教教育。",
            "2010 年代前期：建立 Al-Irchad 网络并布道。",
            "2010 年代中期：与阿马杜·库法及马里圣战网络建立联系并激进化。",
            "2016-12：Nassoumbou 袭击，Ansaroul Islam 公开崛起。",
            "2017：死亡，贾法尔·迪科继任。",
        ],
        "uncertainties": "其死亡的确切时间与情节在不同来源中存在差异。",
        "asip_analysis": "易卜拉欣·迪科代表布基纳法索北部从地方宗教网络向武装圣战转化的关键节点；家族继任模式也预示了 Ansaroul Islam 在 JNIM 体系内的持续存在。",
    },

    # =====================================================================
    "person-ousmane-dicko": {
        "biography": "乌斯曼·迪科是易卜拉欣与贾法尔·迪科的弟弟，是布基纳法索 JNIM/Ansaroul Islam 体系内的资深指挥官。人权观察（HRW）2026 年 4 月报告称其为贾法尔·迪科的兄弟、JNIM 在布基纳法索的副指挥官；《世界报》将其描述为行动与宣传人物。",
        "role": "在 Ansaroul Islam 与 JNIM 中担任军事指挥与宣传角色，活动围绕 Djibo 及其周边；2025 年 Djibo 一带的攻势使其角色更为突出。",
        "family_network": "迪科家族网络是 Ansaroul Islam 与布基纳法索北部 JNIM 领导层的核心——易卜拉欣（创始人）、贾法尔（现领导）、乌斯曼（副指挥官）构成家族式领导链。",
        "command_uncertainty": "乌斯曼与贾法尔的具体分工、以及布基纳法索 JNIM 指挥结构的内部权责，公开信息有限；不得将其定位为整个 JNIM 的埃米尔。",
        "current_status": "现役（current/time-sensitive），2025—2026 年活跃。",
        "timeline": [
            "2025：Djibo 一带 JNIM 攻势中角色突出。",
            "2026-04：HRW 报告称其为 JNIM 在布基纳法索的副指挥官、贾法尔的兄弟。",
        ],
        "uncertainties": "其与贾法尔·迪科、伊亚德·阿格·加利（Iyad Ag Ghali）之间的指挥层级关系未完全透明；对其个人责任的指控需保留来源归属。",
        "asip_analysis": "乌斯曼·迪科的存在说明布基纳法索北部 JNIM 领导层高度家族化，这既是动员优势也是继承与指挥合法性的风险点。",
        "watch_indicators": [
            "布基纳法索 JNIM 指挥结构的进一步披露",
            "迪科家族领导层更替或内部分歧",
        ],
    },

    # =====================================================================
    "person-youssouf-toloba": {
        "biography": "优素福·托洛巴是中马里重要的多贡（Dogon）民兵领袖，ACLED 将其描述为 Dan Na Ambassagou 的创始人与军事翼负责人/参谋长。Dan Na Ambassagou 于 2016 年在社群冲突与圣战不安全背景下成立。",
        "role": "作为 Dan Na Ambassagou 的创始人与军事领袖，托洛巴在该组织的成立、军事行动及其与国家、社区和圣战武装的互动中处于核心位置。",
        "organization_context": "2019 年 Ogossagou 屠杀后，马里当局下令解散 Dan Na Ambassagou；该组织否认责任且未完全解散，托洛巴在民兵/国家/DDR（复员遣返）争论中一直保持影响至 2026 年。",
        "current_status": "现役/相关（截至 2026 年仍参与民兵与和解议题）。",
        "timeline": [
            "2016：Dan Na Ambassagou 成立，托洛巴任创始人/军事领袖。",
            "2019：Ogossagou 屠杀后当局下令解散，组织拒绝且未完全解散。",
            "2020—2026：在民兵/国家/DDR 与地方和解议题中保持影响。",
        ],
        "uncertainties": "组织层面的虐待指控不得自动归责于托洛巴个人；其当前实际指挥权与政治角色存在不确定性。",
        "asip_analysis": "托洛巴是理解中马里多贡自卫武装与国家、圣战组织三方关系的关键人物；DDR 与地方和解的成败将决定其政治结局。",
        "watch_indicators": [
            "DDR 与地方和解进程对 Dan Na Ambassagou 的处理",
            "托洛巴个人在和解谈判中的角色",
        ],
    },

    # =====================================================================
    "person-sadou-samahouna": {
        "biography": "萨杜·萨马胡纳是前 JNIM 高级指挥官，ACLED 认定其叛逃至伊斯兰国萨赫勒省（ISSP）。这一人员转移与 JNIM/ISSP 在贝宁-尼日尔-尼日利亚边境三角地带竞争的再度加剧及相关暴力上升有关。",
        "defection": "萨马胡纳的叛逃被视为 JNIM 与 ISSP 竞争态势变化的标志性事件，凸显两圣战网络在边境三角地带争夺人员与地盘。",
        "geography": "其活动与 JNIM 在贝宁、尼日尔、尼日利亚边境三角地带的扩张相重叠。",
        "current_status": "高度时间敏感（time_sensitive / status_uncertain）；缺乏高置信证据时不得写为已死亡。",
        "timeline": [
            "此前：任 JNIM 高级指挥官。",
            "2026 年前后：叛逃至伊斯兰国萨赫勒省（ISSP），与边境三角地带 JNIM/ISSP 竞争加剧同步。",
        ],
        "uncertainties": "其当前生死状态与在 ISSP 内的具体角色缺乏高置信确认。",
        "asip_analysis": "萨马胡纳的叛逃是 JNIM 与 ISSP 竞争动态的微观样本：人员流动既反映两网络在边境三角地带的争夺，也影响当地暴力格局。",
        "watch_indicators": [
            "JNIM/ISSP 在贝宁-尼日尔-尼日利亚边境的竞争动态",
            "萨马胡纳在 ISSP 内的角色与状态确认",
        ],
    },

    # =====================================================================
    "actor-hcua": {
        "name_identity": "阿扎瓦德统一高级委员会（High Council for the Unity of Azawad，HCUA；法文 Haut Conseil pour l'unité de l'Azawad）是 2013 年 5 月由后 Ansar Dine/MIA 重新结盟中形成的图阿雷格政治-军事组织，是马里北部和平进程与 CMA（阿扎瓦德运动协调会）架构的主要参与者。",
        "history": "HCUA 于 2013 年 5 月成立，是 2012—2013 年马里北部危机后图阿雷格武装重新结盟的产物。它在阿尔及尔和平框架中扮演角色，并在随后的和平进程与 CMA 架构中作为主要图阿雷格政治-军事参与者。",
        "leadership": "HCUA 的领导层与因塔拉（Intalla）家族网络密切相关，该家族在基达尔（Kidal）地区具有长期政治与宗教影响。",
        "geography": "政治与军事活动主要集中在马里北部基达尔地区及阿扎瓦德更广泛的图阿雷格活动范围。",
        "structure": "兼具政治与军事结构，作为图阿雷格北方政治的代表参与和平谈判与 CMA 联合机制。",
        "relationships": "与 MNLA 等图阿雷格武装、CMA 架构及马里国家均存在互动；其个别成员被指与圣战行动者存在联系，但此类指控需保留来源归属，HCUA 本身不得被重新归类为圣战组织。",
        "algiers_process": "HCUA 是阿尔及尔和平协议相关进程的参与者之一，其角色与北方政治-军事格局的演变紧密相关。",
        "csp_dpa": "HCUA 参与 CSP-DPA（战略框架常设委员会）机制；2024 年 11 月 30 日，在北方武装重组中并入阿扎瓦德解放阵线（FLA）。",
        "merger": "2024 年 11 月 30 日，HCUA 与北方其他武装合并组建 FLA，其独立组织身份由此终结，转入 FLA 的历史谱系。",
        "current_status": "历史（historical / merged_into_FLA，2024-11-30）。",
        "historical_legacy": "HCUA 是 2013 年后马里北部图阿雷格政治-军事格局的重要一环，其并入 FLA 标志着北方武装新一轮整合。",
        "timeline": [
            "2013-05：由后 Ansar Dine/MIA 重新结盟中成立。",
            "2014—2015：参与阿尔及尔和平框架。",
            "2015—2023：在 CMA 架构中作为主要图阿雷格参与者。",
            "2023—2024：参与 CSP-DPA 机制。",
            "2024-11-30：并入阿扎瓦德解放阵线（FLA）。",
        ],
        "uncertainties": "个别成员与圣战行动者的联系指控需保留来源归属，不得因此整体化归责于 HCUA。",
        "asip_analysis": "HCUA 的兴衰折射出马里北部图阿雷格政治-军事力量在和平进程与国家重建之间的摇摆；其并入 FLA 是北方武装为应对局势变化的战略重组。",
        "watch_indicators": [
            "FLA 对原 HCUA 政治遗产与成员的整合",
            "北方和平进程与 FLA 的战略走向",
        ],
    },

    # =====================================================================
    "actor-dana-atem": {
        "name_identity": "达纳·阿特姆（Dana Atem）是一个多贡自卫运动/民兵组织，与 Dan Na Ambassagou 相区别。ACLED 将其描述为 2018 年因 Dan Na Ambassagou 内部分歧而形成的较小多贡自卫团体，由西迪·翁戈伊巴（Sidi Ongoiba）领导。",
        "history": "Dana Atem 形成于 Dan Na Ambassagou 内部矛盾，ACLED 记录其成立于 2018 年；其公开角色在 2020 年前后更为突出，危机组织（Crisis Group）及学术文献强调其倾向于地方协商而非全面对抗。",
        "leadership": "西迪·翁戈伊巴是 Dana Atem 的领导者/负责人。",
        "geography": "活动范围集中在马里中部多贡地区，与 Dan Na Ambassagou 的活动区域有所重叠但组织上相区分。",
        "identity": "以多贡社区自卫为认同，偏好与地方社区及国家的协商，而非激进化对抗。",
        "relationships": "与 Dan Na Ambassagou 存在渊源但组织上独立；与马里武装力量（FAMa）存在互动；对富拉尼/当地社区与圣战组织采取协商或冲突并存的复杂姿态。",
        "formation_nuance": "形成时间存在来源差异：ACLED 记录为 2018 年成立，但公开报道在 2020 年前后才更显著，需保留这一时间差异，不得伪造单一精确成立日期。",
        "current_status": "现役但证据有限（截至 2026 年，公开活动与指挥状态信息有限）。",
        "timeline": [
            "2018：ACLED 记录 Dana Atem 因 Dan Na Ambassagou 内部分歧形成。",
            "2020 前后：公开角色更为突出。",
            "2023—2026：部分成员进入正规军；组织活动信息有限。",
        ],
        "uncertainties": "形成时间存在来源差异；当前兵力与活动规模缺乏公开确认。",
        "asip_analysis": "Dana Atem 代表了中马里多贡社区在 Dan Na Ambassagou 之外的替代自卫路线，其协商倾向与进入正规军的成员流动说明地方武装与国家的复杂整合。",
        "watch_indicators": [
            "Dana Atem 与 FAMa 的整合进展",
            "其与 Dan Na Ambassagou 及地方社区的关系演变",
        ],
    },

    # =====================================================================
    "actor-dozos-of-macina": {
        "name_identity": "马西纳多佐猎人武装网络（Dozos of Macina）是中马里马西纳（Macina）地区传统多佐猎人在冲突中军事化后形成的结构化自卫武装网络，主要基地在苏莱耶（Souleye）。",
        "history": "多佐（Dozo）是西非传统猎人/秘密结社，中马里冲突使其军事化为地方自卫武装。ACLED 2025 年将其描述为跨多个塞尔克尔（cercles）协调活动的结构化网络。",
        "leadership": "阿马杜·尼翁松·迪亚拉（Amadou Nionson Diarra）被认定为核心领导人，负责协调跨多个塞尔克尔的活动。",
        "geography": "以苏莱耶为主要基地，活动覆盖马西纳及中马里多个塞尔克尔。",
        "structure": "具备以苏莱耶为中心的集中层级与营地/网络结构，社会构成以多佐猎人为主但不限于单一族群。",
        "relationships": "与马里武装力量（FAMa）存在互动；与 JNIM/卡蒂巴·马西纳环境处于敌对但嵌入地方冲突与协商动态之中；与 Dan Na Ambassagou、Dana Atem 相区分。",
        "state_relations": "在地方自卫与国家对地方武装的整合/容忍之间运作，既非国家正规军亦非全国性反恐武装。",
        "civilian_risk": "多佐武装的军事化伴随平民风险，包括社区间暴力与对平民的威胁。",
        "current_status": "现役（截至 2026 年仍作为中马里地方自卫网络活跃）。",
        "timeline": [
            "2010 年代：中马里冲突中多佐猎人军事化。",
            "2018—2023：形成以苏莱耶为中心的结构化网络。",
            "2025：ACLED 描述其跨塞尔克尔协调活动。",
            "2026：仍作为地方自卫网络活跃。",
        ],
        "uncertainties": "其与 FAMa 及 JNIM 的精确关系、网络规模与领导层结构存在不确定性。",
        "asip_analysis": "Dozos of Macina 是中马里地方武装碎片化的典型：传统社会制度在冲突中军事化，既提供地方防卫又带来平民风险，并嵌入与 JNIM 的对抗-协商双重关系。",
        "watch_indicators": [
            "Dozos of Macina 与 FAMa 的整合或对抗",
            "与 JNIM 的地方协议或冲突升级",
        ],
    },

    # =====================================================================
    "actor-niger-armed-forces": {
        "name_identity": "尼日尔武装部队（Niger Armed Forces / Forces armées nigériennes，FAN）是尼日尔的国家武装力量，承担领土防御、反恐与内部安全职责。",
        "institutional_history": "尼日尔武装部队在独立后建立，长期承担国防与国内安全职能，并在萨赫勒反恐中扮演关键角色。",
        "structure": "下辖陆军、空军等军种，并有与准军事部队（如国民卫队、国家警察）的边界划分；本档案聚焦正规军，准军事力量不在此处展开。",
        "state_role": "作为国家机器核心，承担边境安全、反恐、平叛与危机响应的核心职能。",
        "ct_partnerships_pre2023": "2023 年政变前，尼日尔是西方（法国、美国等）在萨赫勒反恐合作的重要伙伴，西方在其境内设有军事存在与训练合作。",
        "lake_chad_role": "在乍得湖盆地参与对博科圣地（Boko Haram/JAS）及 ISWAP 的反恐行动。",
        "sahel_threats": "在蒂拉贝里（Tillaberi）与多索（Dosso）地区面临伊斯兰国萨赫勒省（IS Sahel）与 JNIM 的威胁，这两股圣战势力持续向尼日尔南部与西部渗透。",
        "coup_2023": "2023 年 7 月政变后，尼日尔军方主导的当局上台，随后推动西方军事存在的撤出与外部伙伴的转向。",
        "partner_shift": "政变后尼日尔转向俄罗斯/非洲军团等新伙伴，西方反恐合作逐步终止。",
        "mnjtf_withdrawal": "2025 年尼日尔退出多国联合特遣部队（MNJTF）。",
        "aes_security": "尼日尔参与 AES（萨赫勒国家联盟）安全架构与 AES 统一部队的规划，是三国集体防御框架的成员。",
        "capabilities": "尼日尔武装部队具备反恐作战与边境管控能力，但面临装备、后勤与多线作战的持续压力；不得使用未经验证的当前精确兵力数字。",
        "current_posture": "截至 2026 年，尼日尔武装部队在 AES 框架与新外部伙伴关系下持续反恐与平叛，面对蒂拉贝里、多索及边境三角地带的圣战压力。",
        "timeline": [
            "独立后：建立国家武装力量。",
            "2010 年代—2023：作为西方萨赫勒反恐伙伴，参与乍得湖与萨赫勒反恐。",
            "2023-07：政变，军方主导当局上台。",
            "2023—2024：西方军事存在撤出，转向俄罗斯/非洲军团。",
            "2025：退出 MNJTF。",
            "2025—2026：参与 AES 统一部队，应对蒂拉贝里/多索圣战压力。",
        ],
        "uncertainties": "当前兵力规模、AES 统一部队中的具体贡献与指挥整合程度缺乏公开确认。",
        "asip_analysis": "尼日尔武装部队正处于从西方伙伴体系向 AES/俄罗斯框架的战略转向之中，其反恐能力与多线压力之间的张力将决定萨赫勒中部安全格局。",
        "watch_indicators": [
            "尼日尔武装部队在 AES 统一部队中的整合",
            "蒂拉贝里/多索及边境三角地带的圣战压力演变",
        ],
    },
}
