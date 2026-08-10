# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-B — person content module.

Source of truth: ASIP-PPT-ENTITY-EXPANSION-B-Authoritative-Content-Pack.md (§9-§12).
No independent research; sanctions findings keep attribution; mechanical floor:
persons >=12 meaningful sections, >=1500 Chinese chars.
"""

TODAY = "2026-08-10"
IMPORTER = "expansion-b"

S_NCTC_SHABAAB = "expa-nctc-al-shabaab-2026-04"
S_TREAS_JY1028 = "expb-treasury-jy1028-karate-2022"
S_STATE_KARATE = "expb-state-sdgt-karate-2015-04-10"
S_NCTC_ISS = "expa-nctc-isis-somalia-2025-02"
S_TREAS_JY1652 = "expa-treasury-isis-somalia-financier-2023-07-27"
S_OFAC_YUSUF = "expb-ofac-yusuf-2023-07-27"
S_UN_NKALUBO = "expb-un-nkalubo-listing"
S_NCTC_ISCA = "expa-nctc-isis-ca-2025-04"
S_EU_TALHA = "expb-eu-2026-251-talha"
S_TREAS_JY1066 = "expb-treasury-jy1066-2022-11-01"
S_OFAC_FAHIYE = "expb-ofac-fahiye-2022-11-01"
S_UNS2026 = "d2-un-s2026-44"

IMPORTANCE_L2 = "该实体对理解所在地区安全格局具有重要作用（L2）。"


def person(**kw):
    base = {
        "entity_id": None,
        "entity_type": "person",
        "primary_type": "person",
        "secondary_types": [],
        "slug": None,
        "name_zh": None,
        "name_en": None,
        "acronym": "",
        "native_name": "",
        "aliases": [],
        "historical_names": [],
        "importance_level": "L2",
        "short_description": "",
        "full_description": "",
        "current_status": "",
        "primary_category": "",
        "tags": [],
        "profile_level": "L2",
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


def pprofile(sections, depth="encyclopedia_full"):
    return {
        "profile_level": depth,
        "completeness": "Expansion B 内容包导入档案 · 百科式",
        "importance_level": "L2",
        "importance_statement": IMPORTANCE_L2,
        "profile_depth": depth,
        "content_maturity": "E3_FULL_ENCYCLOPEDIA",
        "imported_by": IMPORTER,
        "sections": sections,
    }


# =====================================================================
# 9. Mahad Karate
# =====================================================================
ENT_KARATE = person(
    entity_id="person-mahad-karate",
    slug="mahad-karate",
    name_zh="马哈德·卡拉特",
    name_en="Mahad Karate",
    aliases=["Abdirahman Mohammed Warsame", "Mahad Karate (Amniyat)"],
    importance_level="L2",
    short_description="索马里青年党财政负责人，兼管阿姆尼亚特（Amniyat）情报与安全翼；曾任副埃米尔；美国国务院 2015 年 4 月将其列为 SDGT。",
    full_description="马哈德·卡拉特（Mahad Karate）是索马里青年党的财政负责人，同时担任该组织阿姆尼亚特（Amniyat）情报与安全翼的指挥官，并曾任副埃米尔。美国国务院于 2015 年 4 月 10 日将其列为 SDGT；美财政部 2022 年材料指认青年党财政结构中多名官员在其团队之下或为其团队成员。",
    current_status="active_al_shabaab_finance_and_amniyat_chief",
    tags=["索马里", "青年党", "财政", "情报"],
    region_ids=["region-sudan-red-sea-horn"],
    country_ids=[],
    source_refs=[S_NCTC_SHABAAB, S_TREAS_JY1028, S_STATE_KARATE],
)

PROF_KARATE = pprofile({
    "lead": "马哈德·卡拉特（Mahad Karate）是索马里青年党的财政负责人，同时指挥该组织的阿姆尼亚特（Amniyat）情报与安全翼，并曾任副埃米尔。美国国家反恐中心 2026 年资料对他的三重定位（财政、情报、前副埃米尔）使其成为理解青年党权力结构的关键人物。",
    "name_identity": "本平台采用中文译名「马哈德·卡拉特」，英文规范名 Mahad Karate。美国国务院列名材料与部分报道使用其别名 Abdirahman Mohammed Warsame；本平台将该别名纳入别名索引，以保证跨来源检索一致性。",
    "biography": "关于其出生背景、教育经历与加入青年党的具体时间，本内容包所依据的权威来源没有提供可引用的记载；本平台不进行推测性叙述。可确认的是其长期在青年党高层担任与财政、情报相关的职务。",
    "roles": {"list": [
        "财政负责人：领导青年党的资金筹措与分配体系。",
        "阿姆尼亚特（Amniyat）指挥官：掌管该组织的情报与内部安全翼。",
        "前副埃米尔：曾任组织二把手，其当前在最高领导层中的具体位次以最新来源为准。",
    ]},
    "organizational_relation": "他与青年党的关系为高层领导关系：在关系图上登记为该组织领导层成员。青年党自 2012 年公开效忠基地组织，其组织架构包含军事、财政、情报等多个职能条线；卡拉特所掌管的财政与阿姆尼亚特两条线是组织运转的支柱。他与组织最高领导人迪里耶之间的关系属组织内部职权关系，公开来源未提供两人互动的具体细节。",
    "influence": "财政与情报双重职能使他在组织内部具有特殊影响力：财政决定行动资源的分配，阿姆尼亚特决定组织对内控制与对外渗透能力。美财政部 2022 年材料指认青年党财政结构中多名官员在其团队之下或为其团队成员，说明其掌握的是一个成体系的财政班子，而非单点职能。在组织韧性评估中，财政与情报领导层的存续状态通常比单个战地指挥官更能反映组织的长期运转能力——这两块职能决定资源的持续供给与内部安全控制。",
    "current_situation": "截至本内容包来源时点，他仍被认定为青年党的财政负责人与阿姆尼亚特指挥官。美国国务院 2015 年 4 月 10 日将其列为 SDGT，该认定属美国法律行为，须标注辖区。",
    "sanctions_legal": {"list": [
        "2015-04-10：美国国务院将其列为 SDGT（属美国司法辖区行为，非国际共识）。",
        "2022 年：美财政部材料指认青年党财政结构围绕其团队运作。",
    ]},
    "events": {"list": [
        "2015-04-10：美国国务院列名 SDGT。",
        "2022 年：美财政部指认其财政团队结构。",
        "2026 年：NCTC 仍将其列为青年党财政负责人与阿姆尼亚特指挥官。",
    ]},
    "uncertainties": {"list": [
        "其个人背景与加入时间缺乏可引用记载。",
        "财政负责人与阿姆尼亚特指挥官的职权边界在公开来源中无系统说明。",
        "前副埃米尔身份与当前最高领导层位次之间的关系需以最新权威来源为准。",
    ]},
    "gaps": "其个人行动轨迹、具体财政操作与情报行动细节缺乏公开可核实材料；美方财政材料属归属性陈述。对青年党财政体系与阿姆尼亚特运作的深入分析需要独立于美方材料的证据来源，当前公开材料不足以支撑更细粒度的描述。本平台对财政与情报职能的具体操作不作推断，仅记录来源支撑的职务与认定事实。",
    "asip_analysis": "ASIP 判断：卡拉特的价值在于他是青年党「财政—情报复合体」的代表性人物。评估青年党韧性时，财政负责人与情报翼指挥官的存续状态比单个战地指挥官更能反映组织的长期运转能力——因为这两块职能决定资源的持续供给与内部安全控制。",
    "watch_indicators": [
        "美国或其他司法辖区对其身份或状态的新认定。",
        "NCTC 资料对其职务表述的调整。",
        "关于青年党财政与阿姆尼亚特结构的公开新证据。",
    ],
    "core_assessment": "卡拉特是青年党财政与情报体系的核心人物，其角色反映了该组织「财政—情报复合体」的组织特征，是评估青年党韧性的关键观察对象。对其记录应保持在来源支撑范围内：职务与认定事实有据可查，个人细节与具体操作保持归属性处理。",
    "sources": [
        "U.S. National Counterterrorism Center (NCTC)：《Al-Shabaab》（https://www.odni.gov/nctc/terrorist_groups/al_shabaab.html）",
        "U.S. Department of the Treasury：《Al-Shabaab finance structure action》（https://home.treasury.gov/news/press-releases/jy1028）",
        "U.S. Department of State：《Designation of Mahad Karate as SDGT》（2015-04-10）",
    ],
})


# =====================================================================
# 10. Abdiweli Mohamed Yusuf
# =====================================================================
ENT_YUSUF = person(
    entity_id="person-abdiweli-mohamed-yusuf",
    slug="abdiweli-mohamed-yusuf",
    name_zh="阿卜迪韦利·穆罕默德·优素福",
    name_en="Abdiweli Mohamed Yusuf",
    aliases=["Abdiweli Aw-Mahamud", "Ina-Waran Walaac"],
    importance_level="L2",
    short_description="伊斯兰国索马里省财政办公室负责人（自 2020 年前后），负责外国战斗人员、补给与弹药的输送及资金转移；2023 年 7 月 27 日被 OFAC 列为 SDGT。",
    full_description="阿卜迪韦利·穆罕默德·优素福（Abdiweli Mohamed Yusuf）自 2020 年前后担任伊斯兰国索马里省财政办公室负责人，在输送外国战斗人员、补给与弹药以及管理该分支资金方面发挥关键作用。美国 OFAC 于 2023 年 7 月 27 日将其列为 SDGT。",
    current_status="active_iss_finance_office_head",
    tags=["索马里", "伊斯兰国索马里省", "财政"],
    region_ids=["region-sudan-red-sea-horn"],
    country_ids=[],
    source_refs=[S_TREAS_JY1652, S_OFAC_YUSUF, S_NCTC_ISS],
)

PROF_YUSUF = pprofile({
    "lead": "阿卜迪韦利·穆罕默德·优素福（Abdiweli Mohamed Yusuf）自 2020 年前后担任伊斯兰国索马里省（ISIS-Somalia）财政办公室负责人。美国财政部材料把他定位为该分支财政体系的关键操作者：负责输送外国战斗人员、补给与弹药，并管理或部分管理该分支的收入与资金转移。",
    "name_identity": "本平台采用中文译名「阿卜迪韦利·穆罕默德·优素福」，英文规范名 Abdiweli Mohamed Yusuf。OFAC 记录其别名 Abdiweli Aw-Mahamud 与 Ina-Waran Walaac，一并纳入别名索引。",
    "biography": "关于其出生背景与早期经历，本内容包来源未提供可引用记载；可确认的是其自 2020 年前后担任 ISIS-Somalia 财政办公室负责人，并与该分支高层直接互动。",
    "roles": {"list": [
        "ISIS-Somalia 财政办公室负责人（自至少 2020 年前后）。",
        "外国战斗人员、补给与弹药输送的关键操作者。",
        "该分支收入管理与资金转移的执行者（管理或部分管理）。",
    ]},
    "organizational_relation": "他与 ISIS-Somalia 的关系为财政高层关系，在关系图上登记为该分支领导/财政体系成员。美国财政部材料称他会见并向阿卜杜勒·卡迪尔·穆明与阿卜迪拉赫曼·法希耶汇报，说明其处于该分支「区域协调—省级行动」双轨结构中财政职能的执行端。",
    "influence": "其影响力体现在伊斯兰国索马里省的财政枢纽职能上：该分支 2021 年创收估计约 250 万美元、2022 年上半年接近 200 万美元——这些是组织层面数字，而非其个人资金。作为财政执行者，他决定资金与补给在分支网络中的流动，直接支撑该分支在伊斯兰国非洲网络中的枢纽地位。美国财政部将 ISIS-Somalia 描述为伊斯兰国最重要的财政分支之一，优素福正是这一财政职能的执行端人物：外国战斗人员、补给与弹药的输送路径都经过其管理的财政办公室。",
    "current_situation": "截至本内容包来源时点，他仍被认定为 ISIS-Somalia 财政办公室负责人。美国 OFAC 于 2023 年 7 月 27 日将其列为 SDGT，该认定属美国法律行为。该分支在邦特兰 Operation Hilaac 打击下实力显著下降（联合国监测组估计剩约 200—300 名战斗人员），但财政与协调职能的受损程度与人员状态需以最新权威来源为准——财政枢纽的削弱并不必然与兵力下降同步。",
    "sanctions_legal": {"list": [
        "2023-07-27：美国 OFAC 将其列为 SDGT（属美国司法辖区行为）。",
    ]},
    "events": {"list": [
        "2020 年前后：担任 ISIS-Somalia 财政办公室负责人。",
        "2023-07-27：OFAC 列名 SDGT。",
    ]},
    "uncertainties": {"list": [
        "其个人背景缺乏可引用记载。",
        "「管理或部分管理」的表述来自美方材料，实际权限范围不透明。",
        "2021—2022 年收入数字为组织层面估计，非其个人资金。",
    ]},
    "gaps": "其资金操作的具体机制、渠道与人脉细节缺乏公开可核实材料；美方陈述属归属性证据。ISIS-Somalia 的财政网络通过哈瓦拉等非正式渠道运作的细节，在公开来源中仅有美方概括性描述，本平台不展开未经来源支撑的具体路径。",
    "asip_analysis": "ASIP 判断：优素福是「伊斯兰国索马里省体量小、权重大的结构性原因」在人事层面的落点——该分支的枢纽价值来自财政与协调职能，而财政执行端正是优素福的岗位。评估该分支韧性时，财政执行者的存续与替换比普通战地指挥官的变动更具指示意义。",
    "watch_indicators": [
        "美国或其他司法辖区对其身份或状态的新认定。",
        "关于 ISIS-Somalia 财政结构的新权威材料。",
        "该分支资金渠道被切断或改道的迹象。",
    ],
    "core_assessment": "优素福是 ISIS-Somalia 财政枢纽的执行端人物，其角色解释了该分支在伊斯兰国非洲网络中的结构性价值；对它的评估应以美方归属性证据为限。",
    "sources": [
        "U.S. Department of the Treasury：《Treasury Designates Senior ISIS-Somalia Financier》（2023-07-27）（https://home.treasury.gov/news/press-releases/jy1652）",
        "U.S. OFAC：《Designation of Abdiweli Mohamed Yusuf》（2023-07-27）（https://ofac.treasury.gov/recent-actions/20230727）",
        "U.S. NCTC：《ISIS-Somalia》（https://www.odni.gov/nctc/terrorist_groups/isis_somalia.html）",
    ],
})


# =====================================================================
# 11. Meddie Nkalubo (Mohamed Ali Nkalubo)
# =====================================================================
ENT_NKALUBO = person(
    entity_id="person-meddie-nkalubo",
    slug="meddie-nkalubo",
    name_zh="穆罕默德·阿里·恩卡卢博（梅迪·恩卡卢博）",
    name_en="Mohamed Ali Nkalubo",
    aliases=["Meddie Nkalubo", "Meddie Lee", "Punisher"],
    importance_level="L2",
    short_description="民主同盟军／伊斯兰国中非省高级领导人（行动/组织/支持与宣传）；2024 年 2 月 20 日列入联合国名单；NCTC 称其为媒体制作与袭击指挥人员。",
    full_description="穆罕默德·阿里·恩卡卢博（Mohamed Ali Nkalubo，常用显示名梅迪·恩卡卢博 Meddie Nkalubo）是民主同盟军／伊斯兰国中非省的高级领导人。联合国安理会于 2024 年 2 月 20 日将其列入制裁名单，叙述称其对 ADF 战斗人员具实际指挥/控制，负责行动、组织、支持与宣传，并在 2017 年即负责 ADF 与伊斯兰国的和解。NCTC 称其为媒体制作与袭击指挥人员。具体罪行指控均属联合国制裁叙述，非法院判决。",
    current_status="active_adf_senior_leader",
    tags=["刚果民主共和国", "ADF", "伊斯兰国中非省", "联合国制裁"],
    region_ids=["region-nile-basin-east-africa"],
    country_ids=[],
    source_refs=[S_UN_NKALUBO, S_NCTC_ISCA],
)

PROF_NKALUBO = pprofile({
    "lead": "穆罕默德·阿里·恩卡卢博（Mohamed Ali Nkalubo，常用显示名梅迪·恩卡卢博 Meddie Nkalubo）是民主同盟军／伊斯兰国中非省（ADF/ISIS-CA）的高级领导人。联合国安理会 2024 年 2 月 20 日将其列入制裁名单，叙述称其对 ADF 战斗人员具实际指挥/控制；美国国家反恐中心称其为媒体制作与袭击指挥人员。",
    "name_identity": "本平台采用中文译名「穆罕默德·阿里·恩卡卢博（梅迪·恩卡卢博）」，英文规范名 Mohamed Ali Nkalubo，常用显示名 Meddie Nkalubo。联合国列名与报道中的别名 Meddie Lee、Punisher 等一并纳入别名索引。",
    "biography": "关于其出生背景与早期经历，本内容包来源未提供可引用记载；可确认的是其在 ADF 体系中长期担任高级领导，并在组织向伊斯兰国分支身份过渡的过程中承担关键角色。联合国列名叙述对其在 ADF 内的职务与职责作出描述，本平台按归属性方式使用。",
    "roles": {"list": [
        "ADF 高级领导人：负责行动、组织、支持与宣传。",
        "媒体制作与袭击指挥人员（NCTC 定位）。",
        "联合国叙述称其对 ADF 战斗人员具实际指挥/控制。",
    ]},
    "organizational_relation": "他与 ADF/ISIS-CA 的关系为高级领导关系，在关系图上登记为该组织领导层成员（与最高领导人巴卢库并列的高级指挥人员）。联合国叙述称其早在 2017 年即负责 ADF 与伊斯兰国的和解，说明他在组织向伊斯兰国靠拢的进程中扮演关键角色。在领导层结构上，他承担的是「行动组织 + 宣传」的职能条线，与巴卢库的总体领导形成职能分工。",
    "influence": "其影响力体现在行动组织与宣传两个层面：负责计划与支持 ADF 活动，并承担袭击行为的宣传与正当化责任。媒体职能与袭击指挥职能的结合，使他成为 ADF 对外叙事与实际作战之间的枢纽人物。联合国叙述赋予其对 ADF 战斗人员的实际指挥/控制——这意味着他不仅是宣传人员，还是能够调动作战单元的指挥节点；该叙述属联合国制裁认定，本平台保持归属性表述。",
    "current_situation": "截至本内容包来源时点，他仍为联合国列名对象与 NCTC 认定的 ADF 高级指挥人员。ADF/ISIS-CA 在刚果（金）东部持续受到 FARDC、UPDF（Operation Shujaa）与 MONUSCO 平民保护行动的压制，其高级指挥人员的公开状态属高时间敏感信息。具体罪行指控属联合国制裁叙述，本平台不将其表述为刑事定罪。",
    "sanctions_legal": {"list": [
        "2024-02-20：联合国安理会将其列入制裁名单（联合国制裁叙述，含具体罪行指控，非法院判决）。",
    ]},
    "events": {"list": [
        "2017 年：联合国叙述称其负责 ADF 与伊斯兰国的和解。",
        "2024-02-20：列入联合国制裁名单。",
    ]},
    "uncertainties": {"list": [
        "其当前具体位置与活动状态缺乏权威公开信息。",
        "联合国叙述中的指控未转化为刑事定罪，须保持归属性表述。",
        "「实际指挥/控制」的表述与可核实行为证据之间的对应关系不透明。",
    ]},
    "gaps": "其个人细节、具体行动指挥记录与宣传材料归属缺乏公开可核实材料。联合国列名叙述对其职务与责任作出描述，但可交叉验证的独立证据有限；本平台以归属性方式使用该叙述，不扩展为行为细节。",
    "asip_analysis": "ASIP 判断：恩卡卢博是 ADF「行动—宣传复合体」的代表性人物。2017 年即负责与伊斯兰国和解这一节点，把他置于组织身份转换的关键叙事线上；评估 ADF 时，宣传指挥的存续状态是判断组织对外叙事能力的重要观察点。",
    "watch_indicators": [
        "联合国或其他司法辖区对其列名状态的新调整。",
        "NCTC 资料对其职务表述的更新。",
        "ADF 宣传产出中与其相关的新署名或任命信息。",
        "Operation Shujaa 框架下 ADF 领导层被打击的公开报道。",
    ],
    "core_assessment": "恩卡卢博是 ADF 高级领导层中行动与宣传职能的枢纽人物，其记录价值集中在组织身份转换叙事与对外叙事能力两个维度。",
    "sources": [
        "United Nations Security Council：《Mohamed Ali Nkalubo — sanctions listing narrative》（https://main.un.org/securitycouncil/en/content/mohamed-ali-nkalubo）",
        "UNSC press release：《sc15597》（2024）（https://press.un.org/en/2024/sc15597.doc.htm）",
        "U.S. NCTC：《ISIS-Central Africa》（https://www.odni.gov/nctc/terrorist_groups/isis_ca.html）",
    ],
})


# =====================================================================
# 12. Abu Zaid Talha al-Misbah
# =====================================================================
ENT_TALHA = person(
    entity_id="person-abu-zaid-talha",
    slug="abu-zaid-talha",
    name_zh="阿布·扎伊德·塔勒哈·米斯巴赫",
    name_en="Abu Zaid Talha al-Misbah",
    importance_level="L2",
    short_description="巴拉·本·马利克旅（BBMB）指挥官；欧盟 2026 年 1 月 29 日列名，称其率部参与喀土穆南部装甲部队基地防御（2023）并进入总统府（2025）；指控属欧盟制裁认定。",
    full_description="阿布·扎伊德·塔勒哈·米斯巴赫（Abu Zaid Talha al-Misbah）是苏丹巴拉·本·马利克旅（BBMB）的指挥官。欧盟 2026 年 1 月 29 日列名材料称其为苏丹国籍、BBMB 指挥官；欧盟称其在 2023 年 6—8 月参与喀土穆南部装甲部队基地防御，并于 2025 年 3 月率 BBMB 战斗人员进入喀土穆总统府。欧盟列名对其指挥责任下的严重虐待行为作出归属性指控，非刑事定罪。",
    current_status="listed_by_eu_bbmb_commander",
    tags=["苏丹", "BBMB", "欧盟制裁"],
    region_ids=["region-sudan-red-sea-horn", "region-nile-basin-east-africa"],
    country_ids=["country-sudan"],
    confidence="medium_high",
    source_refs=[S_EU_TALHA],
)

PROF_TALHA = pprofile({
    "lead": "阿布·扎伊德·塔勒哈·米斯巴赫（Abu Zaid Talha al-Misbah）是苏丹巴拉·本·马利克旅（BBMB）的指挥官。欧盟 2026 年 1 月 29 日列名材料确认其苏丹国籍与 BBMB 指挥官身份，并对其在苏丹冲突中的行动作出归属性陈述；所有指控均属欧盟制裁认定，非刑事定罪。",
    "name_identity": "本平台采用中文译名「阿布·扎伊德·塔勒哈·米斯巴赫」，英文规范名 Abu Zaid Talha al-Misbah。",
    "biography": "欧盟材料确认其苏丹国籍；关于其出生背景与早期经历，本内容包来源未提供更详细的记载，本平台不进行推测。可确认的轨迹来自欧盟列名叙述：他在 2023 年苏丹战争爆发后作为 BBMB 指挥官率部参战，其两次公开行动节点均发生在喀土穆方向。",
    "roles": {"list": [
        "BBMB 指挥官：领导该伊斯兰主义民兵（欧盟称其与苏丹武装部队并肩作战，对抗快速支援部队及其盟友）。",
        "战场行动负责人：率部参与喀土穆南部装甲部队基地防御（2023 年 6—8 月）。",
        "2025 年 3 月率 BBMB 战斗人员进入喀土穆总统府。",
    ]},
    "organizational_relation": "他与 BBMB 的关系为指挥官关系，在关系图上登记为该组织领导人。欧盟描述 BBMB 为与苏丹武装部队并肩作战的伊斯兰主义民兵，因此其与苏丹武装部队之间存在战时同阵营关系（归属性陈述）。此外，他与快速支援部队（RSF）处于敌对关系——他所指挥的部队在苏丹冲突中站在苏丹武装部队一方；这一敌对关系随苏丹战争的战场态势而变化，本平台以欧盟归属性描述为限。",
    "influence": "作为 BBMB 指挥官，他掌握该民兵的实际作战指挥。欧盟列名对其指挥责任下的严重虐待行为作出归属性指控；这些指控属欧盟制裁认定，反映欧盟对其在冲突中角色的判断，但不构成经司法确认的定罪。其指挥的两次公开行动节点——2023 年基地防御与 2025 年总统府行动——勾勒出 BBMB 在苏丹战争中从「防御性参战」到「象征性占领」的角色升级轨迹。这一轨迹表明他所在的民兵组织已深度嵌入苏丹武装部队一方的作战体系，而非边缘性武装存在。",
    "current_situation": "截至本内容包来源时点，他为欧盟 2026 年 1 月 29 日列名对象；其当前具体位置与活动状态缺乏权威公开信息。BBMB 在苏丹战争中的持续活跃状态（欧盟将其描述为与苏丹武装部队并肩作战）意味着其指挥官的公开轨迹是评估该民兵组织动员强度的观察点。苏丹冲突的持续性与伊斯兰主义民兵在战局中的角色，使对该人物状态的跟踪具有时效价值。",
    "sanctions_legal": {"list": [
        "2026-01-29：欧盟第 2026/251 号条例对其列名（欧盟制裁认定，非刑事定罪）。",
    ]},
    "events": {"list": [
        "2023-06 至 08：欧盟称其参与喀土穆南部装甲部队基地防御，这是其在苏丹战争中首次被公开记述的战场行动。",
        "2025-03：欧盟称其率 BBMB 战斗人员进入喀土穆总统府，标志该民兵在战局中的象征性角色。",
        "2026-01-29：欧盟第 2026/251 号条例对其列名。",
    ]},
    "uncertainties": {"list": [
        "欧盟关于其指挥责任与具体行动的陈述属制裁认定，未经司法确认。",
        "其当前位置、状态与 BBMB 内部的指挥结构缺乏公开细节。",
        "BBMB 与苏丹武装部队的整合程度不透明。",
        "欧盟列名叙述中对其行动的描述（基地防御、总统府行动）的具体参战规模与指挥范围未提供量化细节。",
    ]},
    "gaps": "其个人细节、作战指挥记录与内部权力结构缺乏公开可核实材料。本平台的处理原则是把缺口显性化：不因职务身份而填充未经来源支撑的行为细节。",
    "asip_analysis": "ASIP 判断：塔勒哈是「伊斯兰主义民兵深度嵌入苏丹正规军作战体系」的人事样本。2023 年基地防御与 2025 年总统府行动两个节点，勾勒出 BBMB 在苏丹战争中的角色升级；评估苏丹战时政治—军事结构时，这类民兵指挥官的公开轨迹是判断意识形态化武装动员强度的重要观察点，但所有细节必须保持欧盟归属。",
    "watch_indicators": [
        "欧盟或其他司法辖区对其列名状态的新调整。",
        "关于 BBMB 指挥结构或其在战争中角色的新权威材料。",
        "苏丹冲突中民兵—正规军整合格局的公开变化。",
    ],
    "core_assessment": "塔勒哈是 BBMB 的指挥官，其记录价值在于标注伊斯兰主义民兵在苏丹战争中的行动轨迹；所有指控保持欧盟归属，不转为定罪表述。对苏丹战时政治—军事结构的评估，需把这类民兵指挥官的公开轨迹与正规军序列区分开来，避免把意识形态化动员力量直接等同于建制部队。",
    "sources": [
        "Council of the European Union：《Regulation (EU) 2026/251》（https://eur-lex.europa.eu/legal-content/en/ALL/?uri=CELEX%3A32026R0251）",
    ],
})


# =====================================================================
# 1.1 CARRYOVER — Abdirahman Fahiye Isse Mohamud upgrade to encyclopedia_full
# =====================================================================
# Full replacement sections for the existing person-abdirahman-fahiye profile.
FAHIYE_UPGRADE_SECTIONS = {
    "lead": "阿卜迪拉赫曼·法希耶·伊塞（Abdirahman Fahiye Isse Mohamud）是伊斯兰国索马里省（ISIS-Somalia）的领导人，承担该分支行动层面的领导职能。美国财政部称其在 2021 年初是该分支的埃米尔并向阿卜杜勒·卡迪尔·穆明汇报；联合国监测组报告（S/2026/44）称其受命负责 ISIL-Somalia 的行动领导。他的角色与穆明（分支创建者、卡拉尔办公室负责人）明确区分，不得合并。",
    "name_identity": "本平台采用中文译名「阿卜迪拉赫曼·法希耶·伊塞」，英文规范名 Abdirahman Fahiye Isse Mohamud。OFAC 列名记录其别名：Abd-al-Rahman Fahiye 'Isa、Ahmed Aden、Shaykh Abu-Mus'ab al-Sharqawi、Abdirahman Fahiye；全部纳入别名索引。",
    "biography": "根据美国 OFAC 列名记录，法希耶 1985 年出生于索马里博萨索（Bosaso）。美国财政部称其在 2021 年初是 ISIS-Somalia 埃米尔；2023 年报道仍将其认定为该分支埃米尔。其早年经历与加入组织路径在公开来源中无更详细记载。",
    "roles": {"list": [
        "ISIS-Somalia 埃米尔/领导人（行动层面领导职能）。",
        "2017 年 5 月 23 日博萨索自杀式爆炸（该分支首次自杀式爆炸）的协调者（美财政部陈述）。",
        "该分支月度运营报告的组织者：含袭击活动、勒索行动信息、招募数字、财务汇总与内外问题。",
    ]},
    "organizational_relation": "他与 ISIS-Somalia 的关系为领导关系；与穆明的关系为向穆明汇报（美财政部称其 2021 年初向穆明汇报，而穆明同时是分支创建者与卡拉尔办公室负责人）；与财政负责人阿卜迪韦利·穆罕默德·优素福的关系为优素福向其汇报。在关系图上，法希耶代表该分支的行动领导端，穆明代表区域协调端，两者不得合并。",
    "influence": "作为行动领导，他直接组织该分支的袭击活动、运营报告与内部协调。2017 年博萨索爆炸的协调者身份（美方陈述）说明他在分支早期即承担关键行动职能；月度报告的组织者身份说明他掌握分支运营的完整信息流。",
    "current_situation": "美国财政部 2023 年报道仍将其认定为 ISIS-Somalia 埃米尔；联合国监测组 S/2026/44 称其受命负责 ISIL-Somalia 行动领导。该分支在邦特兰 Operation Hilaac 打击下实力显著下降（监测组估计剩约 200—300 名战斗人员），其领导层状态属高时间敏感信息。",
    "sanctions_legal": {"list": [
        "2022-11-01：美国 OFAC 将其列为 SDGT（与 ISIS-Somalia 关联；属美国法律行为）。",
        "美财政部 2022-11-01 与 2023-07-27 相关材料对其职务作出归属性陈述。",
    ]},
    "events": {"list": [
        "1985 年：出生于索马里博萨索（OFAC 记录）。",
        "2017-05-23：协调博萨索自杀式爆炸（该分支首次；美财政部陈述）。",
        "2021 年初：美财政部称其为 ISIS-Somalia 埃米尔，向穆明汇报。",
        "2022-11-01：OFAC 列名 SDGT。",
        "2023 年：美财政部报道仍认定其为分支埃米尔。",
        "2026：UN S/2026/44 称其受命负责 ISIL-Somalia 行动领导。",
    ]},
    "uncertainties": {"list": [
        "美方对其职务的陈述（2021 年初埃米尔、2023 年仍为埃米尔）与联合国 S/2026/44（行动领导）之间的具体职权边界不统一。",
        "当前指挥层级的确切结构（其与穆明、优素福的实时关系）缺乏最新权威说明。",
        "Operation Hilaac 打击后的领导层实际状态需以最新权威来源为准。",
    ]},
    "gaps": "其个人活动轨迹、与伊斯兰国中央的联系方式以及分支内部权力分配缺乏公开可核实材料。",
    "asip_analysis": "ASIP 判断：法希耶与穆明的分离记录，保留了 ISIS-Somalia 内部「行动性权威」与「象征性/区域性权威」可能分离的结构信息。2021 年埃米尔—2026 年行动领导的身份变化，可能反映该分支在持续打击下的权力调整；若两者被合并，这一结构信息将在数据层永久丢失。",
    "watch_indicators": [
        "美国、联合国或其他司法辖区对其身份或状态的新认定。",
        "权威来源对其职务表述的调整。",
        "邦特兰行动后该分支领导层结构的公开变化。",
    ],
    "core_assessment": "法希耶是 ISIS-Somalia 行动层面的领导人，其档案的核心价值在于与穆明的角色区分以及职务表述随时间的演变；所有职务陈述保持来源归属。",
    "sources": [
        "U.S. OFAC：《Designation of Abdirahman Fahiye Isse Mohamud》（2022-11-01）（https://ofac.treasury.gov/recent-actions/20221101）",
        "U.S. Treasury：《Treasury Designates ISIS-Somalia Emir and Financier Network》（2022-11-01）（https://home.treasury.gov/news/press-releases/jy1066）",
        "U.S. Treasury：《Senior ISIS-Somalia Financier》（2023-07-27）（https://home.treasury.gov/news/press-releases/jy1652）",
        "UN Monitoring Team：《S/2026/44》（https://digitallibrary.un.org/record/4102624/files/S_2026_44-EN.pdf）",
    ],
}

PERSON_ENTITIES = [ENT_KARATE, ENT_YUSUF, ENT_NKALUBO, ENT_TALHA]
PERSON_PROFILES = {
    "person-mahad-karate": PROF_KARATE,
    "person-abdiweli-mohamed-yusuf": PROF_YUSUF,
    "person-meddie-nkalubo": PROF_NKALUBO,
    "person-abu-zaid-talha": PROF_TALHA,
}
