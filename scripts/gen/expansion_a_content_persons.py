#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-A — person content module (§9-§13).

Abu Zaid Talha al-Misbah (§14) is intentionally NOT created: the authoritative
content pack states that if source coverage is insufficient for an
encyclopedia-level page it must be marked DEFER_FOR_CONTENT_PACK_2 rather than
built as a thin page. See unresolved-supporting-entity-dependencies.json.
"""

from expansion_a_content_orgs import (
    TODAY, IMPORTER, entity,
    S_SHABAAB_NCTC, S_ISS_NCTC, S_ISS_FIN, S_ISIS_FS, S_ISCA_NCTC, S_EU_KARTI,
    S_OFAC_SMB,
)

IMPORTANCE_L2 = "该实体对理解所在地区安全格局具有重要作用（L2）。"


def person(**kw):
    base = dict(
        entity_type="person",
        primary_type="person",
        secondary_types=[],
        importance_level="L2",
        profile_level="L2",
        primary_category="jihadist_leader",
        confidence="medium_high",
    )
    base.update(kw)
    return entity(**base)


def pprofile(sections, depth="encyclopedia_full"):
    return {
        "profile_level": depth,
        "completeness": "Expansion A 内容包导入档案 · 人物",
        "importance_level": "L2",
        "importance_statement": IMPORTANCE_L2,
        "profile_depth": depth,
        "content_maturity": "E3_FULL_ENCYCLOPEDIA" if depth == "encyclopedia_full" else "E2_DEVELOPED",
        "imported_by": IMPORTER,
        "sections": sections,
    }


# =====================================================================
# 9. Ahmed Diriye
# =====================================================================
ENT_DIRIYE = person(
    entity_id="person-ahmed-diriye",
    slug="ahmed-diriye",
    name_zh="艾哈迈德·迪里耶",
    name_en="Ahmed Diriye",
    acronym="",
    native_name="أحمد ديريي",
    aliases=["Abu Ubaidah", "Ahmad Umar", "阿布·乌拜达"],
    short_description="索马里青年党埃米尔（最高领导人），自 2014 年起担任该职务；常用别名 Abu Ubaidah。",
    full_description="艾哈迈德·迪里耶是索马里青年党的埃米尔，即该组织的最高领导人，自 2014 年起担任这一职务。他在公开材料中常以别名 Abu Ubaidah 出现。NCTC 关于青年党的资料把他列为该组织的现任领导人。",
    current_status="active_al_shabaab_emir",
    tags=["非洲之角", "领导人"],
    region_ids=["region-sudan-red-sea-horn"],
    country_ids=[],
    source_refs=[S_SHABAAB_NCTC],
)

PROF_DIRIYE = pprofile({
    "lead": "艾哈迈德·迪里耶（Ahmed Diriye），公开材料中常用别名 Abu Ubaidah，自 2014 年起担任索马里青年党的埃米尔，即该组织的最高领导人。美国国家反恐中心关于青年党的资料把他确认为该组织的现任领导人。青年党源自 2006 年短暂控制索马里中南部的伊斯兰法庭联盟军事派系，目前仍被描述为基地组织关联组织；在这一组织背景下，迪里耶的职务定位是理解其指挥连续性的关键节点。",
    "name_identity": "本平台采用中文译名「艾哈迈德·迪里耶」，英文规范名 Ahmed Diriye。其最常见的战名为 Abu Ubaidah（阿布·乌拜达），在部分权威材料与新闻报道中，该战名的出现频率甚至高于本名。为保证跨来源检索的一致性，本平台把本名与战名同时收入别名索引。个别来源还出现过 Ahmad Umar 一类的拼写变体，一并保留以便检索。",
    "roles": "他在组织中的角色是埃米尔，即最高领导人。在青年党的组织语境中，这一职务同时承载宗教权威与作战决策权威两重含义，是该组织对内维系统一、对外表达立场的核心位置。作为最高领导人，他需要同时处理组织的地面作战、地方治理、税收勒索、跨境行动与对外关系等多个条线，因此不能把该职务简单等同于战场指挥官。",
    "biography": "关于其早年经历、家庭背景、教育与加入组织之前的个人历史，本内容包所依据的权威来源没有提供可引用的记载。本平台按「不发明事实」的原则，不对上述内容作任何推测性叙述，仅记录可由来源支撑的职务与任期信息：他自 2014 年起担任埃米尔，并在 2026 年 4 月的 NCTC 资料中仍被列为现任领导人。",
    "organizational_relation": "他所领导的组织自 2012 年起公开效忠基地组织，并被 NCTC 在 2026 年 4 月的资料中继续确认为基地组织关联方，估计其规模约为 7,000—12,000 名成员，主要据点在索马里中南部，行动延伸至肯尼亚与埃塞俄比亚。因此在关系图上，他与全球圣战网络之间的连接是间接的：通过组织层面的效忠关系建立，而非本人单独的效忠行为。公开来源没有说明他个人与基地组织领导层之间存在何种直接联系。",
    "influence": "作为埃米尔，他处在该组织权力结构的顶端。与他并列出现在公开材料中的另一位重要人物是马哈德·卡拉特（Mahad Karate），后者与财政以及内部安全／情报职能相关。两人的职能分工反映出该组织在军事指挥之外，还维持着独立的财政与内部安全条线。2025 年 4 月，恐怖主义融资打击中心对 15 名青年党领导人、行动人员与资金便利者作出认定，涉及筹资与简易爆炸装置扩散；这类以组织资金网络为对象的行动，同样构成评估其领导层所依赖的资源基础的背景。",
    "current_situation": "截至本内容包所依据来源的时点，他仍被列为该组织的现任领导人，没有公开来源显示其职务发生更替。由于青年党长期处于外部军事压力之下，其领导层的人身安全状态与职务连续性属于高时间敏感度信息，需要以来源更新为准。对评估东非安全形势而言，青年党领导层的稳定与否直接关系到该组织大规模叛乱能力的延续性。",
    "sanctions_legal": "关于针对他个人的法律认定与制裁记录，本内容包未提供可直接引用的条目。本平台因此不在人物层记录任何具体的制裁编号或列名日期，以避免与组织层面的认定（如 2025 年 4 月针对青年党资金网络人员的认定）发生混淆。",
    "events": {"p": [
        "2014 年：出任索马里青年党埃米尔，成为该组织最高领导人。",
        "2026 年 4 月：NCTC 关于青年党的资料仍将其列为现任领导人。",
    ]},
    "uncertainties": {"list": [
        "其早年生平、加入组织的时间与路径缺乏可引用的权威记载。",
        "他与基地组织领导层之间是否存在直接联系，公开来源未作说明。",
        "领导层状态属高时间敏感信息，任何关于其职务变动的报道都需要来源交叉确认。",
    ]},
    "gaps": "人物层面的主要缺口在于个人史与内部权力运作：现有权威来源提供的是职务事实，而非决策过程。这意味着不能从其职务推断具体行动的责任归属。",
    "asip_analysis": "ASIP 判断：对该人物的分析价值主要来自「指挥连续性」这一维度——自 2014 年以来的长期在任，说明该组织在遭受持续军事压力的条件下仍维持了顶层稳定。这一稳定性本身是评估其组织韧性的一项间接指标。",
    "watch_indicators": [
        "是否出现关于其死亡、被捕或去职的权威确认。",
        "NCTC 后续版本资料是否更换所列的组织领导人姓名。",
        "其战名 Abu Ubaidah 在组织公开宣传中的使用是否发生变化。",
        "是否出现针对其个人的新增法律认定。",
    ],
    "core_assessment": "他是青年党自 2014 年以来的顶层稳定因素；对其个人的公开信息虽有限，但其在任时间长度本身即具备分析意义。",
    "sources": [
        "U.S. National Counterterrorism Center (NCTC)：《Al-Shabaab》（https://www.odni.gov/nctc/terrorist_groups/al_shabaab.html）",
    ],
})


# =====================================================================
# 10. Abd al-Qadir Mu'min
# =====================================================================
ENT_MUMIN = person(
    entity_id="person-abd-al-qadir-mumin",
    slug="abd-al-qadir-mumin",
    name_zh="阿卜杜勒·卡迪尔·穆明",
    name_en="Abd al-Qadir Mu'min",
    acronym="",
    native_name="عبد القادر مؤمن",
    aliases=["Abdul Qadir Mumin", "Abdulqadir Mumin", "Abd al-Qadir Mumin"],
    short_description="伊斯兰国索马里省创建者，同时担任卡拉尔办公室负责人，是连接东非分支与伊斯兰国区域资金体系的核心人物。",
    full_description="阿卜杜勒·卡迪尔·穆明是伊斯兰国索马里省的创建者，同时被 NCTC 与美国财政部的材料确认为卡拉尔办公室的负责人。这一双重身份使他成为连接伊斯兰国东非分支与其区域管理／资金体系的关键人物。",
    current_status="active_isis_somalia_founder_and_al_karrar_leader",
    tags=["非洲之角", "伊斯兰国"],
    region_ids=["region-sudan-red-sea-horn"],
    country_ids=[],
    confidence="high",
    source_refs=[S_ISS_NCTC, S_ISS_FIN, S_ISIS_FS],
)

PROF_MUMIN = pprofile({
    "lead": "阿卜杜勒·卡迪尔·穆明（Abd al-Qadir Mu'min）在伊斯兰国的非洲体系中同时担任两个职务：他是伊斯兰国索马里省的创建者，也是卡拉尔办公室的负责人。前一身份指向一个具体的作战分支，后一身份指向覆盖非洲中部、东部与南部的区域管理与资金节点。这种「分支创建者兼区域枢纽主管」的组合，在非洲伊斯兰国体系中并不常见。",
    "name_identity": "权威来源对其姓名的英文转写并不统一，常见形式包括 Abd al-Qadir Mu'min、Abdul Qadir Mumin 与 Abdulqadir Mumin。这类转写差异源自阿拉伯语姓名的不同罗马化方案，并非指向不同人物。本平台以 Abd al-Qadir Mu'min 为规范写法，并将其余变体一并纳入别名索引，以保证跨来源检索可以对齐。",
    "roles": {"p": [
        "第一重身份：伊斯兰国索马里省的创建者。该分支由脱离索马里青年党的人员组成，2015 年宣誓效忠伊斯兰国，2018 年获正式分支承认。",
        "第二重身份：卡拉尔办公室负责人。NCTC 与美国财政部的材料均作此确认。该办公室是伊斯兰国在索马里设置的区域管理节点，职责覆盖非洲中部、东部与南部方向。",
    ]},
    "biography": "关于其出生年份、成长经历、宗教教育背景以及加入武装组织之前的个人历史，本内容包所依据的权威来源未提供可引用的记载。本平台不作推测性补全，仅保留可由来源支撑的组织职务信息。",
    "influence": "他的影响力不来自单一组织内部的层级高度，而来自跨层级的职务重叠：作为分支创建者，他与索马里当地的作战力量直接相关；作为区域节点负责人，他又处在跨行省的资金与协调链路上。这一重叠正是伊斯兰国索马里省与卡拉尔办公室在地理与人员上高度关联的直接原因。",
    "organizational_relation": "需要特别强调的是，人员重叠不构成实体合并的理由。本平台把伊斯兰国索马里省与卡拉尔办公室保留为两个独立实体，因此该人物同时与两者建立关系：与前者为创建关系，与后者为领导关系。另需区分的是，伊斯兰国索马里省的领导人是阿卜迪拉赫曼·法希耶·伊塞，其职责与本人不同，两者不得合并处理。",
    "current_situation": "截至本内容包所依据来源的时点，他仍被列为卡拉尔办公室的负责人。由于该办公室以资金与协调职能为主要存在形式，常规战场指标难以反映其个人状态，相关信息更依赖金融认定与情报机构资料的更新。",
    "sanctions_legal": "美国财政部关于伊斯兰国索马里省资金人员的认定材料，以及《打击伊斯兰国融资情况说明》，均涉及其所领导的组织与资金网络。本平台在人物层不单独登记具体的制裁条目编号，相关法律状态记录在对应的组织实体页面上，以避免个人与组织层面的法律行为发生混淆。",
    "events": {"p": [
        "2015 年：其所属派系脱离索马里青年党并宣誓效忠伊斯兰国。",
        "2018 年：伊斯兰国正式承认该派系的分支地位。",
        "2023 年 7 月 27 日：美国财政部对伊斯兰国索马里省高级资金人员实施认定，相关材料涉及其所领导的网络。",
        "2024 年 2 月 27 日：美国财政部《打击伊斯兰国融资情况说明》描述卡拉尔办公室的区域资金职能。",
    ]},
    "uncertainties": {"list": [
        "其个人生平信息在权威公开来源中基本缺失，无法建立完整的人物时间线。",
        "他对卡拉尔办公室所辖各非洲伊斯兰国分支的实际指挥深度，无法由现有公开来源确认。",
        "其在伊斯兰国全球领导层中的层级位置，公开材料未作明确说明。",
    ]},
    "gaps": "现阶段最关键的空白是「权限范围」：可以确认他担任两个职务，但两个职务各自的决策边界、以及二者之间是否存在职能冲突，均无公开材料支撑。",
    "asip_analysis": "ASIP 判断：该人物是理解非洲伊斯兰国体系「作战—财务」耦合方式的最佳观察点。他的职务组合说明，在该体系中区域资金枢纽与地方作战分支并非彼此独立的两条线，而是通过关键人物实现连接。因此，针对其个人的任何变动都可能同时影响两个实体的运行方式。",
    "watch_indicators": [
        "是否出现关于其死亡、被捕或去职的权威确认。",
        "卡拉尔办公室负责人是否发生更替。",
        "美国财政部是否披露与其个人直接相关的新增资金认定。",
        "其双重职务是否出现公开的结构性拆分。",
    ],
    "core_assessment": "他的分析价值在于职务重叠：一个人同时连接了地方作战分支与跨区域资金枢纽，这使他成为非洲伊斯兰国网络中少数具有结构性意义的个人节点。",
    "sources": [
        "U.S. National Counterterrorism Center (NCTC)：《ISIS-Somalia》（https://www.odni.gov/nctc/terrorist_groups/isis_somalia.html）",
        "U.S. Department of the Treasury：《Treasury Designates Senior ISIS-Somalia Financier》（https://home.treasury.gov/news/press-releases/jy1652）",
        "U.S. Department of the Treasury：《Countering ISIS Financing Fact Sheet》（https://home.treasury.gov/system/files/136/Fact-Sheet-Countering-ISIS-Financing-2-27-24.pdf）",
    ],
})


# =====================================================================
# 11. Abdirahman Fahiye Isse
# =====================================================================
ENT_FAHIYE = person(
    entity_id="person-abdirahman-fahiye",
    slug="abdirahman-fahiye",
    name_zh="阿卜迪拉赫曼·法希耶·伊塞",
    name_en="Abdirahman Fahiye Isse",
    acronym="",
    native_name="",
    aliases=["Abdirahman Fahiye Isse Mohamud", "Abdirahman Fahiye"],
    short_description="伊斯兰国索马里省领导人，承担行动层面的领导职能；与该分支创建者穆明角色不同，不得合并。",
    full_description="阿卜迪拉赫曼·法希耶·伊塞是伊斯兰国索马里省的领导人，在该分支中承担行动层面的领导职能。他与创建者阿卜杜勒·卡迪尔·穆明的角色存在明确区分，权威来源分别记载，不应合并为同一人物记录。",
    current_status="active_isis_somalia_leader",
    tags=["非洲之角", "伊斯兰国"],
    region_ids=["region-sudan-red-sea-horn"],
    country_ids=[],
    confidence="medium_high",
    source_refs=[S_ISS_NCTC, S_ISS_FIN],
)

PROF_FAHIYE = pprofile({
    "lead": "阿卜迪拉赫曼·法希耶·伊塞（Abdirahman Fahiye Isse）是伊斯兰国索马里省的领导人。权威来源把他与该分支的创建者阿卜杜勒·卡迪尔·穆明分别记载：前者承担的是行动层面的领导职能，后者则同时是分支创建者与卡拉尔办公室负责人。这一区分必须在数据层保持显性。",
    "name_identity": "本平台采用中文译名「阿卜迪拉赫曼·法希耶·伊塞」，英文规范名 Abdirahman Fahiye Isse。部分材料中会出现包含更多父名成分的完整写法，本平台将其纳入别名索引以便检索。",
    "roles": "他在伊斯兰国索马里省中担任领导人职务，职责集中在行动层面。相较于创建者身份所对应的组织合法性与对外定位功能，行动领导职能更直接关联具体的作战组织与人员调度。公开来源没有进一步说明其职权范围的具体边界。",
    "organizational_relation": "不得把该人物与阿卜杜勒·卡迪尔·穆明合并处理——这是本内容包的明确要求，理由是两人角色不同。在关系图上，两人分别与伊斯兰国索马里省建立关系：穆明为创建关系，本人为领导关系；此外穆明还与卡拉尔办公室存在领导关系，而本人与该办公室之间没有可由来源支撑的直接关系。",
    "current_situation": "截至本内容包所依据来源的时点，他被列为该分支的领导人。需要注意的是，该分支在此期间承受了邦特兰方面反恐行动带来的实质性人员损失，因此其领导层状态属于高时间敏感信息。",
    "uncertainties": {"list": [
        "其个人背景、加入组织的时间与路径缺乏可引用的权威记载。",
        "其行动领导职能与创建者角色之间的具体分工，公开材料未作说明。",
        "在反恐军事压力之下，其职务状态需以最新权威来源为准。",
    ]},
    "gaps": "该人物页的信息密度受限于公开来源本身：可确认的是职务与所属组织，不可确认的是个人史、实际权限与决策参与程度。本平台不以推测填补这些空白。",
    "asip_analysis": "ASIP 判断：把该人物与穆明分开记录，其意义不只是人物层面的准确性，更在于它保留了伊斯兰国索马里省内部「象征性／创建性权威」与「行动性权威」可能分离的结构信息。若两者被合并，这一结构差异将在数据层永久丢失。",
    "watch_indicators": [
        "是否出现关于其死亡、被捕或去职的权威确认。",
        "权威来源是否调整其在该分支中的职务表述。",
        "该分支领导层结构是否因反恐行动出现公开变动。",
    ],
    "core_assessment": "他是伊斯兰国索马里省行动层面的领导人，其记录的核心价值在于与创建者角色的区分，而非个人细节的丰富度。",
    "sources": [
        "U.S. National Counterterrorism Center (NCTC)：《ISIS-Somalia》（https://www.odni.gov/nctc/terrorist_groups/isis_somalia.html）",
        "U.S. Department of the Treasury：《Treasury Designates Senior ISIS-Somalia Financier》（https://home.treasury.gov/news/press-releases/jy1652）",
    ],
}, depth="standard")


# =====================================================================
# 12. Seka Musa Baluku
# =====================================================================
ENT_BALUKU = person(
    entity_id="person-seka-musa-baluku",
    slug="seka-musa-baluku",
    name_zh="塞卡·穆萨·巴卢库",
    name_en="Seka Musa Baluku",
    acronym="",
    native_name="",
    aliases=["Musa Baluku", "Seka Baluku"],
    short_description="民主同盟军／伊斯兰国中非省最高领导人；NCTC 关于该组织的资料将其列为 overall leader。",
    full_description="塞卡·穆萨·巴卢库是民主同盟军／伊斯兰国中非省的最高领导人。NCTC 关于伊斯兰国中非省的资料把他列为该组织的 overall leader，同时把梅迪·恩卡卢博列为媒体与袭击指挥人员。",
    current_status="active_adf_isis_ca_overall_leader",
    tags=["中部非洲", "伊斯兰国"],
    region_ids=["region-nile-basin-east-africa"],
    country_ids=[],
    source_refs=[S_ISCA_NCTC],
)

PROF_BALUKU = pprofile({
    "lead": "塞卡·穆萨·巴卢库（Seka Musa Baluku）是民主同盟军／伊斯兰国中非省的最高领导人。美国国家反恐中心关于伊斯兰国中非省的资料把他确认为该组织的 overall leader。他所领导的组织在 2019 年获得伊斯兰国的分支承认，此前则是源自乌干达的反政府叛乱运动。这一身份序列意味着，对他的评估需要同时放在「乌干达—刚果（金）跨境武装的历史」与「伊斯兰国非洲分支的当前定位」两个框架下进行。",
    "name_identity": "本平台采用中文译名「塞卡·穆萨·巴卢库」，英文规范名 Seka Musa Baluku。公开报道中亦常见 Musa Baluku 的简写形式，本平台将其纳入别名索引，以覆盖不同来源的命名习惯。不同来源在拼写与顺序上的差异（如 Baluku 与 Seka 的先后）并不影响实体同一性的判断。",
    "roles": "他担任的是组织的最高领导职务。NCTC 资料在列出他的同时，还单独列出了梅迪·恩卡卢博（Meddie Nkalubo）作为媒体与袭击指挥人员，这说明该组织在最高领导层之下设有职能化的分工，至少包含宣传与作战指挥两条线。也就是说，最高领导人并非事无巨细的单一决策者，其下存在承担具体职能的高级指挥人员。",
    "biography": "关于其出生背景、加入组织的时间、在组织内部的晋升路径以及成为最高领导人的具体过程，本内容包所依据的权威来源没有提供可引用的记载。本平台不对上述内容进行推断，以避免在人物页引入无来源支撑的叙述。可以确认的是，他在该组织由乌干达反政府叛乱向伊斯兰国分支转换的过程中持续担任最高领导，这一事实本身具有谱系学价值。",
    "organizational_relation": "他与所领导组织之间的关系，需要放在该组织身份转换的背景下理解：该组织最初是乌干达境内的反政府叛乱运动，其后扎根刚果民主共和国东部，2019 年获伊斯兰国承认为分支。本平台把历史身份与当前身份合并为一个规范实体，因此该人物只与这一个实体建立领导关系，而不会同时连接到「ADF」与「ISIS-CA」两个并列节点。这一建模方式直接来自内容包的规范：历史身份与伊斯兰国品牌应保留在单一规范实体内。",
    "influence": "作为最高领导人，他处在该组织决策结构的顶端。该组织的行为特征包括针对平民的屠杀式袭击与跨境行动能力，其常见战术涵盖轻武器、简易爆炸装置、迫击炮、火箭筒、屠杀、伏击、绑架与跨境袭击；2025 年 4 月 NCTC 估计其规模为 1,000—1,500 人，主要活动区为刚果（金）北基伍省与伊图里省，并具备在乌干达发动袭击的能力。这些特征所反映的组织意志与最高领导层直接相关；但公开来源没有说明具体袭击的决策链条，因此不能把个别事件的责任直接归属到个人层面。",
    "current_situation": "截至本内容包所依据来源的时点，他仍被列为该组织的最高领导人。该组织在刚果（金）东部面临多方军事压力，其领导层状态属于需要持续以权威来源更新的高敏感信息。对在刚果（金）东部及乌干达边境地区活动的人员而言，该组织的绑架与袭击能力构成直接风险，而领导层的存续状态是评估其组织能力恢复程度的重要参考。",
    "uncertainties": {"list": [
        "其个人背景与晋升路径缺乏可引用的权威记载。",
        "他与伊斯兰国中央之间是否存在直接联系，公开来源未作说明。",
        "组织内部最高领导人与职能指挥人员之间的权限划分未被公开披露。",
        "组织从历史 ADF 网络到伊斯兰国分支的转变是渐进的，转变程度与时点在公开来源中没有统一结论，这同样影响对其领导权限范围的界定。",
    ]},
    "gaps": "该人物页可确认的信息集中在职务本身。组织内部决策机制、他与伊斯兰国体系的互动方式，以及其对具体作战行动的参与程度，均超出现有权威来源的披露范围。本平台的策略是显性标注这些缺口，而不是用推测填补。",
    "asip_analysis": "ASIP 判断：对该人物的观察重点应放在「身份转换后的领导连续性」上——该组织在 2019 年被纳入伊斯兰国行省序列之后，最高领导职务并未因品牌变更而更替。这一连续性支持本平台采用单一规范实体建模的处理方式，也提示品牌变更未必等同于组织结构的重构。从威胁评估角度，领导层的延续意味着组织的历史作战经验与网络得以跨身份保留。",
    "watch_indicators": [
        "是否出现关于其死亡、被捕或去职的权威确认。",
        "NCTC 后续资料是否调整其职务表述或更换所列领导人。",
        "组织内部是否出现新的、被权威来源确认的高级指挥人员。",
        "其个人是否被纳入新的国际法律认定。",
        "刚果（金）东部军事行动是否导致该组织领导层公开露面频率变化。",
    ],
    "core_assessment": "他是该组织在身份转换前后保持领导连续性的关键人物，其记录价值主要体现在组织谱系的连贯性上。其个人层面的威胁评估应谨慎区分组织行为与个人责任，前者有充分的行为学证据，后者缺乏来源支撑。",
    "sources": [
        "U.S. National Counterterrorism Center (NCTC)：《ISIS-Central Africa》（https://www.odni.gov/nctc/terrorist_groups/isis_ca.html）",
        "U.S. National Counterterrorism Center (NCTC)：《ISIS-DRC (historical)》（https://www.odni.gov/nctc/terrorist_groups/isis_drc.html）",
    ],
})


# =====================================================================
# 13. Ali Ahmed Karti
# =====================================================================
ENT_KARTI = person(
    entity_id="person-ali-ahmed-karti",
    slug="ali-ahmed-karti",
    name_zh="阿里·艾哈迈德·卡尔提",
    name_en="Ali Ahmed Karti Mohamed",
    acronym="",
    native_name="علي أحمد كرتي",
    aliases=["Ali Ahmed Karti", "Ali Karti"],
    primary_category="islamist_political_figure",
    short_description="欧盟 2024 年制裁材料所指认的苏丹伊斯兰主义运动秘书长、全国大会党重要人物；曾任苏丹外交部长。",
    full_description="阿里·艾哈迈德·卡尔提是苏丹伊斯兰主义运动的秘书长，曾任苏丹外交部长。欧盟 2024 年的制裁材料把他列为该运动的秘书长与全国大会党的重要人物，并对其政治与安全影响力、以及在阻碍政治过渡方面的作用作出判断；上述判断属欧盟结论，本平台按归属性陈述保存。",
    current_status="listed_by_eu_sudanese_islamist_movement_secretary_general",
    tags=["苏丹", "伊斯兰主义网络"],
    region_ids=["region-sudan-red-sea-horn", "region-nile-basin-east-africa"],
    country_ids=["country-sudan"],
    confidence="medium_high",
    disputed=False,
    source_refs=[S_EU_KARTI, S_OFAC_SMB],
)

PROF_KARTI = pprofile({
    "lead": "阿里·艾哈迈德·卡尔提（Ali Ahmed Karti Mohamed，常用显示名 Ali Ahmed Karti）是苏丹伊斯兰主义运动的秘书长，并曾担任苏丹外交部长。欧盟 2024 年的制裁材料在把他列名的同时，明确指认了他在该运动中的秘书长身份以及作为全国大会党重要人物的政治定位。",
    "name_identity": "本平台以「阿里·艾哈迈德·卡尔提」为中文名，英文正式名采用 Ali Ahmed Karti Mohamed，常用显示名为 Ali Ahmed Karti。较短的 Ali Karti 写法在新闻报道中较为常见，一并收入别名索引。",
    "roles": {"p": [
        "组织职务：苏丹伊斯兰主义运动秘书长。这一身份由欧盟 2024 年材料指认，是他与本平台苏丹伊斯兰运动实体之间建立关系的依据。",
        "政党身份：欧盟材料把他描述为全国大会党的重要人物，这一定位把他与巴希尔时期的政治网络联系起来。",
        "公职经历：曾任苏丹外交部长。这是其个人履历中与国家机构直接相关的部分。",
    ]},
    "political_character": "他的角色横跨三个层面：伊斯兰主义运动的组织领导、执政党体系内的政治人物，以及曾经的国家外交负责人。这种跨层身份正是欧盟材料关注其影响力的原因，也是理解苏丹伊斯兰主义网络与国家机构之间联系的一个具体切入点。把他放在苏丹政治史的纵轴上，其意义不止于当前职务：全国大会党时期的网络身份，使他成为连接巴希尔时代与 2023 年冲突后格局的连续性人物，而这类连续性人物往往是评估战后权力重组的关键观察对象。",
    "sanctions_legal": {"p": [
        "欧盟在 2024 年通过相关理事会实施条例对其列名。本平台把该列名记录为欧盟司法辖区的法律行为，不表述为国际共识。",
        "欧盟关于其政治与安全影响力、以及在破坏或阻碍政治过渡方面所起作用的结论，均属欧盟的机构性判断，必须保持归属性表述。",
        "需要与之区分的是，美国 OFAC 在 2026 年 3 月 9 日采取的行动针对的是组织本体（苏丹穆斯林兄弟会及其别名，含苏丹伊斯兰运动），而非本人。两类法律行为的对象、辖区与时点均不相同，不能把针对组织的认定回溯记入个人档案。",
        "与其相关的另一背景是苏丹伊斯兰运动自身在欧盟材料中的定位：欧盟把该运动描述为伊斯兰主义团体的广泛联盟。这一描述属欧盟判断，同样需要与本人身份区分。",
    ]},
    "influence": "欧盟材料还描述了伊斯兰主义运动对苏丹武装部队、警察与情报部门的强大影响。这一描述是关于运动整体的判断，而非直接针对本人的具体行为指控；在使用时应避免把组织层面的影响力评估直接等同于个人的实际控制权。对评估苏丹安全形势而言，欧盟的这一判断值得单独标注为机构性评估：它解释了为何 2023 年冲突中的正规军一侧被认为带有伊斯兰主义色彩，但该判断本身需要其他来源的交叉验证。",
    "organizational_relation": "在关系图上，他与苏丹伊斯兰运动之间建立领导关系，依据是欧盟材料指认的秘书长身份。需要注意的是，该运动本身在 2026 年 3 月被美国以「苏丹穆斯林兄弟会」名义列入 SDN 清单，但组织层面的法律状态不应回溯记入个人档案。此外，巴拉·本·马利克旅在 2026 年 3 月的清单更新中被标注 Linked To: SUDANESE MUSLIM BROTHERHOOD，这属于美国制裁工具对组织间关联的技术性标注，与个人档案无直接关系，也不构成对该旅与本人之间个人关联的认定。",
    "current_situation": "他当前的公开身份是被欧盟列名的苏丹伊斯兰主义运动秘书长。至于其在苏丹 2023 年冲突爆发之后的具体活动、所在地与实际角色，本内容包所依据的来源没有提供可引用的细节。从判断角度可以确认的是：只要该运动在苏丹战争中的政治—军事角色继续存在，其秘书长一职的政治重要性就不会消失，无论本人是否公开活动。",
    "uncertainties": {"list": [
        "欧盟关于其影响力与作用的结论属机构判断，缺少可交叉验证的第二方公开材料。",
        "该运动内部的决策机制不透明，秘书长职务所对应的实际权限范围无法确认。",
        "SIM、苏丹穆斯林兄弟会与历史穆斯林兄弟会网络之间的边界争议，同样影响对其职务外延的理解。",
    ]},
    "asip_analysis": "ASIP 判断：该人物是把「政治网络」与「国家机构」两个分析层面连接起来的样本性节点。他的履历同时覆盖伊斯兰主义运动、执政党与外交系统，因此在评估苏丹伊斯兰主义网络的制度渗透深度时，其个人轨迹具有指示意义。但必须强调，指示意义不等于因果证据。",
    "watch_indicators": [
        "欧盟是否更新或撤销对其列名。",
        "美国或其他司法辖区是否对其个人采取列名行动。",
        "苏丹伊斯兰运动是否公开更换秘书长。",
        "是否出现关于其当前所在地与活动的权威信息。",
    ],
    "core_assessment": "他是苏丹伊斯兰主义网络中身份最清晰、可被权威来源指认的高层人物，其档案的处理关键是维持欧盟判断与既定事实之间的界限。",
    "sources": [
        "European Union：《Council Implementing Regulation (EU) 2024/1783 / Ali Ahmed Karti》（https://eur-lex.europa.eu/eli/dec/2024/1784）",
        "U.S. OFAC：《Counter Terrorism Designations; Sudan-related Designation Update》（9 Mar 2026）（https://ofac.treasury.gov/recent-actions/20260309）",
    ],
})


PERSON_ENTITIES = [ENT_DIRIYE, ENT_MUMIN, ENT_FAHIYE, ENT_BALUKU, ENT_KARTI]

PERSON_PROFILES = {
    "person-ahmed-diriye": PROF_DIRIYE,
    "person-abd-al-qadir-mumin": PROF_MUMIN,
    "person-abdirahman-fahiye": PROF_FAHIYE,
    "person-seka-musa-baluku": PROF_BALUKU,
    "person-ali-ahmed-karti": PROF_KARTI,
}

PERSON_EXTERNAL_LINKS = {
    "person-ali-ahmed-karti": {"wikipedia": [], "authoritative": [
        {"label": "EU — Council Implementing Regulation (EU) 2024/1783", "url": "https://eur-lex.europa.eu/eli/dec/2024/1784"},
    ]},
}
