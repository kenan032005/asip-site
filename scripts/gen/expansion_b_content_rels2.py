# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-B — relationship content module (part 2: DRC/Uganda + Sudan).

Companion to expansion_b_content_rels.py. Adds the DRC/Uganda network
(FARDC/UPDF/MONUSCO/ADF) and the Sudan external-support network (BBMB/IRGC/Talha).
R3 dossiers: ADF-FARDC, ADF-UPDF, FARDC-UPDF/Shujaa, BBMB-IRGC. Attribution
rules from the pack are enforced (UPDF claims stay attributed; Treasury BBMB-IRGC
statement stays attributed; MONUSCO-ADF is not a belligerent framing).
"""

TODAY = "2026-08-10"
IMPORTER = "expansion-b"

S_UNSC2767 = "expb-unsc-2767-2024"
S_UPDF_REVIEW = "expb-updf-shujaa-review"
S_UPDF_STRIKE = "expb-updf-shujaa-strike"
S_MONUSCO_FARDC = "expb-monusco-fardc-ituri"
S_UN_FS = "expb-un-monusco-factsheet"
S_UNSC2808 = "expb-unsc-2808-2025"
S_SG_ADF = "expb-un-sg-adf-2025-11-22"
S_TREAS_BBMB = "expa-treasury-sudan-islamist-2025-09-12"
S_OFAC_BBMB = "expa-ofac-bbmb-2025-09-12"
S_EU_TALHA = "expb-eu-2026-251-talha"
S_NCTC_ISCA = "expa-nctc-isis-ca-2025-04"
S_UN_NKALUBO = "expb-un-nkalubo-listing"
S_NCTC_SHABAAB = "expa-nctc-al-shabaab-2026-04"
S_TREAS_JY1028 = "expb-treasury-jy1028-karate-2022"
S_STATE_KARATE = "expb-state-sdgt-karate-2015-04-10"
S_TREAS_JY1652 = "expa-treasury-isis-somalia-financier-2023-07-27"


def rel(rid, src, tgt, rtype, *, ring="middle", status, summary,
        direction="bidirectional", time_start="", time_end="", start_year=None,
        confidence="high", formation="", scope="", why="", unc="",
        refs=(), disputed=False, temporal=True, freshness="current",
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


NEW_RELATIONSHIPS = [
    # ---- DRC / Uganda network ----
    rel(
        "rel-expb-adf-fardc-conflict",
        "actor-adf-isis-ca", "actor-fardc", "fought_against",
        ring="inner", status="active_armed_conflict",
        time_start="2021-11", start_year=2021, confidence="medium_high",
        summary="民主同盟军／伊斯兰国中非省（ADF/ISIS-CA）与刚果民主共和国武装部队（FARDC）处于武装对抗状态；FARDC 与乌干达 UPDF 联合开展 Operation Shujaa 打击 ADF。",
        formation="ADF 长期盘踞刚果（金）东部；FARDC 作为国家武装力量承担反武装团体任务，2021 年 11 月与 UPDF 联合发起 Operation Shujaa 打击 ADF。",
        scope="刚果（金）北基伍省与伊图里省",
        why="这是 ADF 所受主要军事压力的来源之一，决定其在东部的生存空间。",
        unc="战果数字来自 UPDF/FARDC 官方陈述，未经独立核实。",
        refs=[S_UPDF_REVIEW, S_UPDF_STRIKE],
    ),
    rel(
        "rel-expb-adf-updf-conflict",
        "actor-adf-isis-ca", "actor-updf", "fought_against",
        ring="inner", status="active_armed_conflict",
        time_start="2021-11", start_year=2021, confidence="medium_high",
        summary="民主同盟军／伊斯兰国中非省（ADF/ISIS-CA）与乌干达人民国防军（UPDF）处于武装对抗状态；UPDF 在刚果（金）东部联合 FARDC 开展 Operation Shujaa 打击 ADF。",
        formation="ADF 起源于乌干达反政府叛乱并具跨境袭击能力；UPDF 作为乌干达国家武装力量，2021 年 11 月起跨境联合 FARDC 打击 ADF。",
        scope="刚果（金）东部（北基伍/伊图里）及乌干达跨境方向",
        why="UPDF 的跨境打击直接压制 ADF 对乌干达的威胁及其在东部的生存空间。",
        unc="战果数字来自 UPDF 官方陈述，未经独立核实。",
        refs=[S_UPDF_REVIEW, S_UPDF_STRIKE],
    ),
    rel(
        "rel-expb-fardc-updf-shujaa",
        "actor-fardc", "actor-updf", "cooperates_with",
        ring="inner", status="active_joint_operation",
        time_start="2021-11", start_year=2021, confidence="high",
        summary="刚果民主共和国武装部队（FARDC）与乌干达人民国防军（UPDF）联合开展 Operation Shujaa（2021 年 11 月发起）打击 ADF，2026 年继续联合行动与指挥协调。",
        formation="UPDF 官方报道称 Operation Shujaa 于 2021 年 11 月作为 UPDF-FARDC 联合反 ADF 攻势发起；2026 年 2 月双方指挥官在贝尼评估行动，2 月 27 日联合袭击 ADF 营地。",
        scope="刚果（金）东部（北基伍/伊图里方向）",
        why="这是反 ADF 战役的机制核心，决定 ADF 在东部的生存空间。",
        unc="战果数字来自 UPDF 官方陈述，未经独立核实；联合行动的长期化存在不确定性。",
        refs=[S_UPDF_REVIEW, S_UPDF_STRIKE],
        note="cooperates_with 表达双边联合行动关系；战果与伤亡数字保持 UPDF 官方归属。",
    ),
    rel(
        "rel-expb-monusco-adf-countering",
        "actor-monusco", "actor-adf-isis-ca", "hostile_to",
        ring="middle", status="civilian_protection_countering",
        direction="unidirectional", confidence="medium_high",
        summary="MONUSCO 依据安理会授权在刚果（金）东部开展平民保护与反武装团体行动，ADF 是其面对的反复袭击平民的武装团体；MONUSCO 不是武装冲突方，而是授权框架内的维和力量。",
        formation="MONUSCO 的核心授权为保护平民；ADF 反复袭击其行动区的平民（如 2025 年 11 月卢贝罗袭击），MONUSCO 因此与 FARDC 协调联合巡逻与联合/协调应对。",
        scope="刚果（金）北基伍与伊图里",
        why="该关系标注了维和力量与威胁平民的武装团体之间的结构性对抗，必须在平民保护框架内理解。",
        unc="MONUSCO 与 ADF 的直接交火细节未系统公开；具体部署数据以联合国官方为准。",
        refs=[S_UN_FS, S_UNSC2808, S_MONUSCO_FARDC, S_SG_ADF],
        note="不使用普通「恐怖组织敌对双方」表述：MONUSCO 是依据安理会授权的维和特派团，其与 ADF 的对抗发生在平民保护与反武装团体任务框架内。",
    ),
    rel(
        "rel-expb-monusco-fardc-cooperation",
        "actor-monusco", "actor-fardc", "cooperates_with",
        ring="middle", status="context_dependent_cooperation",
        confidence="medium_high",
        summary="MONUSCO 与刚果民主共和国武装部队（FARDC）在刚果（金）东部协调平民保护与安全行动，包括联合巡逻与针对 ADF 袭击的联合/协调应对。",
        formation="UN 报道描述 MONUSCO 与 FARDC 在伊图里等地结合军事与民政手段应对武装团体；2025 年重大 ADF 袭击后强化了平民保护协调。",
        scope="刚果（金）北基伍与伊图里",
        why="双方协调决定平民保护的实际覆盖，是评估东部安全环境的关键机制。",
        unc="协调的具体机制与成效缺乏系统性公开数据；合作属情境依赖型。",
        refs=[S_MONUSCO_FARDC, S_UNSC2808],
    ),
    rel(
        "rel-expb-adf-nkalubo-led",
        "actor-adf-isis-ca", "person-meddie-nkalubo", "led_by",
        ring="outer", status="reported_senior_leader",
        confidence="high",
        summary="穆罕默德·阿里·恩卡卢博（梅迪·恩卡卢博）是民主同盟军／伊斯兰国中非省的高级领导人，联合国叙述称其对 ADF 战斗人员具实际指挥/控制；NCTC 称其为媒体制作与袭击指挥人员。",
        formation="联合国 2024 年 2 月 20 日将其列入制裁名单，叙述称其负责 ADF 行动、组织、支持与宣传；具体罪行指控属联合国制裁叙述，非法院判决。",
        scope="刚果（金）东部",
        why="他是 ADF 领导层中行动与宣传职能的枢纽人物，处于组织身份转换叙事的关键线上。",
        unc="联合国叙述中的指控未转化为刑事定罪；其当前具体位置与活动状态缺乏权威信息。",
        refs=[S_UN_NKALUBO, S_NCTC_ISCA],
    ),
    # ---- Sudan external-support network ----
    rel(
        "rel-expb-bbmb-irgc-support",
        "actor-bbmb", "actor-irgc", "affiliated_with",
        ring="middle", status="reported_support_relationship",
        confidence="medium", disputed=False,
        summary="美国财政部 2025 年 9 月称巴拉·本·马利克旅（BBMB）使用了伊朗伊斯兰革命卫队（IRGC）提供的训练与武器；该陈述属美国政府指控/评估，必须保留归属，不得推导为 IRGC 对 BBMB 的作战指挥。",
        formation="美国财政部 2025 年 9 月 12 日对 BBMB 实施制裁时陈述其使用了 IRGC 提供的训练与武器。此为归属性证据：记录「U.S. Treasury states BBMB has used training and weapons provided by the IRGC」，不把单一来源概括为伊朗控制苏丹伊斯兰主义民兵。",
        scope="苏丹",
        why="该关系标注了外部行为体介入苏丹冲突的可能渠道与美方政策反应，但属于归属性证据。",
        unc="IRGC 对 BBMB 支持的范围、机制与持续性缺乏公开可核实细节；美方陈述与独立证据之间的交叉验证不足。",
        refs=[S_TREAS_BBMB, S_OFAC_BBMB],
        note="现有 ontology 无 reported_supported_by 类型，使用 affiliated_with 表达被指控的支持关联并在档案与关系概述中显式写明「U.S. Treasury states」；不推导 command/control，不泛化。",
    ),
    rel(
        "rel-expb-bbmb-talha-led",
        "actor-bbmb", "person-abu-zaid-talha", "led_by",
        ring="outer", status="reported_commandership",
        confidence="medium_high",
        summary="阿布·扎伊德·塔勒哈·米斯巴赫是巴拉·本·马利克旅（BBMB）的指挥官；欧盟 2026 年 1 月列名材料确认其身份并对指挥责任下的行为作出归属性指控。",
        formation="欧盟 2026-01-29 列名：苏丹国籍、BBMB 指挥官；欧盟称其参与 2023 年 6—8 月喀土穆南部装甲部队基地防御，2025 年 3 月率 BBMB 战斗人员进入总统府。",
        scope="苏丹（喀土穆）",
        why="作为 BBMB 指挥官，他掌握该民兵的实际作战指挥，是理解伊斯兰主义民兵在苏丹战争中角色的关键人物。",
        unc="欧盟陈述属制裁认定，未经司法确认；其当前状态与 BBMB 内部指挥结构缺乏公开细节。",
        refs=[S_EU_TALHA],
    ),
    rel(
        "rel-expb-talha-saf-allied",
        "person-abu-zaid-talha", "actor-saf", "allied_with",
        ring="outer", status="reported_wartime_alignment",
        direction="unidirectional", confidence="medium",
        summary="欧盟称 BBMB 作为与苏丹武装部队（SAF）并肩作战的伊斯兰主义民兵对抗快速支援部队及盟友；塔勒哈作为 BBMB 指挥官与其处于战时同阵营关系（欧盟归属性陈述）。",
        formation="欧盟 2026-01-29 列名材料描述 BBMB 为与 SAF 并肩作战的伊斯兰主义民兵；塔勒哈率部参与的基地防御与总统府行动均发生在 SAF 一方。",
        scope="苏丹",
        why="该关系标注了伊斯兰主义民兵与正规军之间的战时同阵营结构（欧盟归属性视角）。",
        unc="欧盟陈述属制裁认定；民兵与正规军的实际整合程度不透明。",
        refs=[S_EU_TALHA],
        note="allied_with 表达战时同阵营关系，依据为欧盟归属性陈述；不表示 BBMB 已编入 SAF 建制。",
    ),
]

NEW_RELATION_PROFILES = {}
NEW_RELATION_TIMELINES = {}


def rprofile(rid, *, title, src, tgt, rtype, ring, maturity, overview,
             parties, why, unc, sources, current_status="",
             direction="bidirectional", formation="", initial="", stages=(),
             causes=(), turning_points=(), regional="", impact="",
             drivers=(), constraints=(), assessment="", asip="", watch=(),
             disputed=False, temporal=True):
    return {
        "relation_id": rid,
        "slug": rid.replace("rel-", "", 1),
        "relation_title": title,
        "source_entity_id": src,
        "target_entity_id": tgt,
        "relation_type": rtype,
        "direction": direction,
        "display_ring": ring,
        "current_status": current_status,
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


R3 = "R3_FULL_RELATIONSHIP_INTELLIGENCE"
R2 = "R2_DEVELOPED_RELATIONSHIP"

# ---- R3 E1: ADF/ISIS-CA <-> FARDC ----
NEW_RELATION_PROFILES["rel-expb-adf-fardc-conflict"] = rprofile(
    "rel-expb-adf-fardc-conflict",
    title="民主同盟军（伊斯兰国中非省）—FARDC：国家力量的反武装团体作战",
    src="actor-adf-isis-ca", tgt="actor-fardc",
    rtype="fought_against", ring="inner", maturity=R3,
    overview="民主同盟军／伊斯兰国中非省（ADF/ISIS-CA）长期盘踞刚果（金）东部，与刚果民主共和国武装部队（FARDC）处于武装对抗状态。FARDC 承担国家反武装团体任务，并于 2021 年 11 月与乌干达 UPDF 联合发起 Operation Shujaa 打击 ADF。",
    parties=[{"entity_id": "actor-adf-isis-ca", "role": "盘踞刚果（金）东部的武装组织（伊斯兰国分支）"},
             {"entity_id": "actor-fardc", "role": "刚果民主共和国国家武装力量"}],
    formation="ADF 起源于乌干达反政府叛乱，后在刚果（金）东部扎根；FARDC 作为国家武装力量在东部承担反武装团体任务。2021 年 11 月 Operation Shujaa 作为 UPDF-FARDC 联合反 ADF 攻势发起（UPDF 官方口径）。",
    initial="FARDC 长期在东部与 ADF 作战；Operation Shujaa 使对抗进入双边联合阶段。",
    stages=[
        {"period": "2021-11", "detail": "Operation Shujaa 发起（UPDF 官方口径）。"},
        {"period": "2026-02", "detail": "UPDF/FARDC 指挥官在贝尼评估行动并重申联合打击 ADF。"},
        {"period": "2026-02-27", "detail": "联合部队袭击伊波卢河以西 ADF 营地，缴获武器与炸弹制作材料（UPDF 官方陈述）。"},
        {"period": "持续", "detail": "FARDC 与 MONUSCO 协调伊图里等地平民保护行动。"},
    ],
    causes=["ADF 的长期盘踞", "FARDC 的国家反武装团体使命", "与 UPDF 的双边联合机制"],
    turning_points=[
        {"event": "2021-11 Operation Shujaa 发起", "impact": "对抗进入双边联合阶段。", "source_ids": [S_UPDF_REVIEW]},
        {"event": "2026-02-27 营地突袭", "impact": "联合行动延续，战果为官方口径。", "source_ids": [S_UPDF_STRIKE]},
    ],
    regional="对抗集中于刚果（金）北基伍与伊图里省。",
    impact="FARDC 在东部反武装团体行动中的角色决定 ADF 的生存空间，其与 UPDF 的联合行动与 MONUSCO 的协调共同塑造东部安全格局。",
    why="这是 ADF 所受主要军事压力的来源之一。",
    unc="战果数字来自 UPDF/FARDC 官方陈述，未经独立核实；FARDC 兵力与约束缺乏系统数据。",
    sources=[S_UPDF_REVIEW, S_UPDF_STRIKE, S_MONUSCO_FARDC],
    drivers=["FARDC 国家使命", "双边联合机制", "ADF 的抵抗能力"],
    constraints=["FARDC 多线牵制", "后勤与纪律约束"],
    assessment="对抗关系当前有效，处于联合行动持续期。",
    asip="FARDC 应被理解为受多重约束的国家行为体：其反 ADF 效能高度依赖与 UPDF 的联合框架和与 MONUSCO 的协调。评估时应把联合行动持续性、FARDC 多线牵制与平民保护协调作为三个连续变量。",
    watch=["Operation Shujaa 联合行动公告与战果（保留 UPDF 归属）。", "ADF 报复性袭击动向。", "MONUSCO-FARDC 协调新报道。"],
)
NEW_RELATION_TIMELINES["rel-expb-adf-fardc-conflict"] = [
    tl("2021-11", "Operation Shujaa 发起", "UPDF-FARDC 联合反 ADF 攻势开始（UPDF 官方口径）。",
       "对抗进入双边联合阶段。", "medium_high", [S_UPDF_REVIEW]),
    tl("2026-02", "贝尼评估", "UPDF/FARDC 指挥官评估行动并重申联合打击。",
       "联合机制延续。", "medium_high", [S_UPDF_REVIEW]),
    tl("2026-02-27", "营地突袭", "联合部队袭击伊波卢河以西 ADF 营地并缴获武器与爆炸物。",
       "行动延续，战果为官方口径。", "medium_high", [S_UPDF_STRIKE]),
]

# ---- R3 E2: ADF/ISIS-CA <-> UPDF ----
NEW_RELATION_PROFILES["rel-expb-adf-updf-conflict"] = rprofile(
    "rel-expb-adf-updf-conflict",
    title="民主同盟军（伊斯兰国中非省）—UPDF：跨境打击与乌干达威胁",
    src="actor-adf-isis-ca", tgt="actor-updf",
    rtype="fought_against", ring="inner", maturity=R3,
    overview="民主同盟军／伊斯兰国中非省（ADF/ISIS-CA）起源于乌干达反政府叛乱并具跨境袭击能力；乌干达人民国防军（UPDF）2021 年 11 月起跨境联合 FARDC 开展 Operation Shujaa 打击 ADF，压制其对乌干达的威胁。",
    parties=[{"entity_id": "actor-adf-isis-ca", "role": "具乌干达起源与跨境袭击能力的武装组织"},
             {"entity_id": "actor-updf", "role": "乌干达国家武装力量"}],
    formation="ADF 起源于乌干达反政府叛乱，后在刚果（金）东部扎根并保留跨境袭击能力；UPDF 2021 年 11 月与 FARDC 联合发起 Operation Shujaa。",
    initial="UPDF 跨境作战以消除 ADF 对乌干达的威胁为目标。",
    stages=[
        {"period": "2021-11", "detail": "Operation Shujaa 发起（UPDF 官方口径）。"},
        {"period": "2026-02", "detail": "UPDF/FARDC 指挥官在贝尼评估联合行动。"},
        {"period": "2026-02-27", "detail": "联合部队袭击 ADF 营地（UPDF 官方陈述）。"},
    ],
    causes=["ADF 对乌干达的跨境威胁", "UPDF 的区域安全使命", "双边联合机制"],
    turning_points=[
        {"event": "2021-11 Operation Shujaa 发起", "impact": "跨境打击机制建立。", "source_ids": [S_UPDF_REVIEW]},
        {"event": "2026-02-27 营地突袭", "impact": "跨境行动延续。", "source_ids": [S_UPDF_STRIKE]},
    ],
    regional="刚果（金）东部（北基伍/伊图里）及乌干达跨境方向。",
    impact="UPDF 的跨境打击直接压制 ADF 对乌干达的威胁及其在东部生存空间。",
    why="UPDF 是 Operation Shujaa 的核心推动者，其行动决定 ADF 的生存空间。",
    unc="战果数字来自 UPDF 官方陈述，未经独立核实；UPDF 部署规模缺乏公开统计。",
    sources=[S_UPDF_REVIEW, S_UPDF_STRIKE],
    drivers=["乌干达安全威胁评估", "区域稳定使命", "双边框架"],
    constraints=["行动长期化的资源投入", "跨境行动的政治框架"],
    assessment="对抗关系当前有效，跨境打击持续。",
    asip="UPDF 的区域角色以「跨境反恐先行者」为特征；Operation Shujaa 的可持续性取决于双边政治框架与资源投入。战果数字必须始终保留 UPDF 官方归属。",
    watch=["UPDF 官方新公告（战果保留归属）。", "乌干达境内 ADF 跨境袭击动向。", "双边指挥机制调整。"],
)
NEW_RELATION_TIMELINES["rel-expb-adf-updf-conflict"] = [
    tl("2021-11", "Operation Shujaa 发起", "UPDF-FARDC 联合反 ADF 攻势开始。",
       "跨境打击机制建立。", "medium_high", [S_UPDF_REVIEW]),
    tl("2026-02", "贝尼评估", "UPDF/FARDC 指挥官评估行动。",
       "联合机制延续。", "medium_high", [S_UPDF_REVIEW]),
    tl("2026-02-27", "营地突袭", "联合部队袭击 ADF 营地。",
       "跨境行动延续，战果为官方口径。", "medium_high", [S_UPDF_STRIKE]),
]

# ---- R3 E3: FARDC <-> UPDF / Operation Shujaa ----
NEW_RELATION_PROFILES["rel-expb-fardc-updf-shujaa"] = rprofile(
    "rel-expb-fardc-updf-shujaa",
    title="FARDC—UPDF：Operation Shujaa 双边联合反 ADF 机制",
    src="actor-fardc", tgt="actor-updf",
    rtype="cooperates_with", ring="inner", maturity=R3,
    overview="刚果民主共和国武装部队（FARDC）与乌干达人民国防军（UPDF）自 2021 年 11 月起联合开展 Operation Shujaa 打击 ADF；2026 年双方继续联合行动与指挥协调，2 月 27 日联合袭击 ADF 营地。",
    parties=[{"entity_id": "actor-fardc", "role": "刚果（金）国家武装力量"},
             {"entity_id": "actor-updf", "role": "乌干达国家武装力量"}],
    formation="UPDF 官方报道称 Operation Shujaa 于 2021 年 11 月作为 UPDF-FARDC 联合反 ADF 攻势发起；这是双边国家力量在刚果（金）东部的联合反武装团体机制。",
    initial="以联合打击 ADF 为目标的双边军事合作。",
    stages=[
        {"period": "2021-11", "detail": "Operation Shujaa 发起。"},
        {"period": "2026-02", "detail": "双方指挥官在贝尼评估行动并重申联合打击。"},
        {"period": "2026-02-27", "detail": "联合袭击伊波卢河以西 ADF 营地，缴获武器与爆炸物。"},
    ],
    causes=["共同反 ADF 目标", "双边安全安排", "ADF 跨境威胁"],
    turning_points=[
        {"event": "2021-11 Operation Shujaa 发起", "impact": "双边联合机制建立。", "source_ids": [S_UPDF_REVIEW]},
        {"event": "2026-02-27 营地突袭", "impact": "联合机制延续并产出战果。", "source_ids": [S_UPDF_STRIKE]},
    ],
    regional="刚果（金）东部（北基伍/伊图里方向）。",
    impact="该机制决定 ADF 在东部的生存空间，是反 ADF 战役的核心。",
    why="这是反 ADF 战役的机制核心。",
    unc="战果数字来自 UPDF 官方陈述，未经独立核实；联合机制的长期化与资源投入存在不确定性。",
    sources=[S_UPDF_REVIEW, S_UPDF_STRIKE],
    drivers=["共同反恐目标", "双边政治框架", "跨境威胁认知"],
    constraints=["资源投入的可持续性", "双边政治波动"],
    assessment="合作当前有效，联合行动持续。",
    asip="把 FARDC—UPDF 合作视为「双边联合机制」而非固定联盟：其持续性取决于资源投入与双边政治框架。战果数字保持 UPDF 归属，是避免把官方陈述转写为独立核实事实的关键纪律。",
    watch=["Operation Shujaa 新公告（战果保留归属）。", "双边指挥机制调整。", "ADF 抵抗与报复动向。"],
)
NEW_RELATION_TIMELINES["rel-expb-fardc-updf-shujaa"] = [
    tl("2021-11", "Operation Shujaa 发起", "UPDF-FARDC 联合反 ADF 攻势开始。",
       "双边机制建立。", "medium_high", [S_UPDF_REVIEW]),
    tl("2026-02", "贝尼评估", "双方指挥官评估行动并重申联合打击。",
       "机制延续。", "medium_high", [S_UPDF_REVIEW]),
    tl("2026-02-27", "营地突袭", "联合部队袭击 ADF 营地并缴获武器与爆炸物。",
       "机制产出战果（官方口径）。", "medium_high", [S_UPDF_STRIKE]),
]

# ---- R3 F: BBMB <-> IRGC (attributed-support dossier) ----
NEW_RELATION_PROFILES["rel-expb-bbmb-irgc-support"] = rprofile(
    "rel-expb-bbmb-irgc-support",
    title="巴拉·本·马利克旅—伊朗伊斯兰革命卫队：被指控的支持关系（U.S. Treasury 归属）",
    src="actor-bbmb", tgt="actor-irgc",
    rtype="affiliated_with", ring="middle", maturity=R3,
    overview="美国财政部 2025 年 9 月称巴拉·本·马利克旅（BBMB）使用了伊朗伊斯兰革命卫队（IRGC）提供的训练与武器。该陈述属美国政府指控/评估：本档案以「U.S. Treasury states」形式保留归属，不推导 IRGC 对 BBMB 的作战指挥，不泛化为伊朗控制苏丹伊斯兰主义民兵。",
    parties=[{"entity_id": "actor-bbmb", "role": "苏丹伊斯兰主义武装团体"},
             {"entity_id": "actor-irgc", "role": "伊朗国家安全武装力量（外部行为体）"}],
    formation="美国财政部 2025 年 9 月 12 日依据苏丹相关授权对 BBMB 实施制裁时，陈述其使用了 IRGC 提供的训练与武器。该陈述与制裁行动绑定，属归属性证据。",
    initial="美方在制裁 BBMB 时披露的被指控支持关系；不存在独立核实的支持机制记录。",
    stages=[
        {"period": "2025-09-12", "detail": "美国财政部制裁 BBMB 并陈述其使用 IRGC 训练与武器。"},
        {"period": "后续", "detail": "无更新的独立证据加入；关系保持为归属性陈述。"},
    ],
    causes=["美方对 BBMB 外部支持的评估", "苏丹战争中的外部介入渠道"],
    turning_points=[
        {"event": "2025-09-12 美财政部陈述", "impact": "建立归属性支持关系记录。", "source_ids": [S_TREAS_BBMB]},
    ],
    regional="苏丹（BBMB 活动地）；IRGC 以伊朗及中东为基地。",
    impact="若美方指控属实，标注了外部行为体介入苏丹冲突的可能渠道与美方政策反应。",
    why="该关系记录外部介入可能渠道，同时是归属性证据纪律的示范性案例。",
    unc="IRGC 对 BBMB 支持的范围、机制与持续性缺乏公开可核实细节；美方陈述与独立证据交叉验证不足；不得把单一指控推广为伊朗控制苏丹伊斯兰主义民兵的结论。",
    sources=[S_TREAS_BBMB, S_OFAC_BBMB],
    drivers=["美方评估", "苏丹冲突外部支持格局"],
    constraints=["缺乏独立证据", "指控与事实之间需保持区分"],
    assessment="关系记录为归属性支持关系（U.S. Treasury states），无独立核实事实支撑其扩展。",
    asip="处理该关系应保持三层区分：指控本身（U.S. Treasury states，归属性）、指控背后的政策反应（美方制裁行动）、以及独立可验证的事实（当前缺乏）。IRGC 在非洲图中的价值是标注外部介入渠道，而非建立指挥关系。",
    watch=[
        "美国或其他司法辖区对 IRGC 与苏丹武装关系的新认定。",
        "独立于美方陈述的 IRGC-BBMB 关系证据。",
        "苏丹冲突中外部支持格局的公开变化。",
    ],
)
NEW_RELATION_TIMELINES["rel-expb-bbmb-irgc-support"] = [
    tl("2020-01-07", "BBMB 成立记录（背景）",
       "OFAC 记录巴拉·本·马利克旅的组织成立日期为 2020 年 1 月 7 日，将其归类为武装团体。",
       "确立 BBMB 作为独立武装实体的起点，为后续外部支持指控提供组织背景。", "high", [S_OFAC_BBMB]),
    tl("2025-09-12", "美财政部制裁陈述",
       "美国财政部制裁 BBMB 并称其使用 IRGC 提供的训练与武器（归属性陈述）。",
       "建立归属性支持关系记录。", "medium", [S_TREAS_BBMB]),
    tl("2026-03-09", "OFAC 清单更新（后续背景）",
       "OFAC 更新 BBMB 清单条目为 [FTO][SDGT][SUDAN-EO14098] 并标注 Linked To: SUDANESE MUSLIM BROTHERHOOD。",
       "美方对 BBMB 的法律认定持续更新，但 IRGC 支持证据仍为归属性陈述。", "high", ["expa-ofac-smb-bbmb-2026-03-09"]),
]

# ---- R2 profiles for remaining relations ----
_R2_BATCH = [
    ("rel-expb-monusco-adf-countering",
     "MONUSCO—民主同盟军（伊斯兰国中非省）：平民保护框架下的结构性对抗",
     "actor-monusco", "actor-adf-isis-ca", "hostile_to", "middle",
     "MONUSCO 依据安理会授权在刚果（金）东部开展平民保护与反武装团体行动；ADF 反复袭击其行动区平民。该关系必须在平民保护框架内理解，MONUSCO 不是武装冲突方。",
     "该关系标注了维和力量与威胁平民的武装团体之间的结构性对抗，是理解平民保护机制的关键。",
     "MONUSCO 与 ADF 的直接交火细节未系统公开；具体部署数据以联合国官方为准。",
     [S_UN_FS, S_UNSC2808, S_MONUSCO_FARDC, S_SG_ADF],
     "MONUSCO 是依据安理会授权的维和特派团，其与 ADF 的对抗发生在平民保护与反武装团体任务框架内，而非武装冲突方的敌对关系。评估时应把特派团视为平民保护与协调机制。",
     ["安理会关于 MONUSCO 授权的新决议。", "ADF 对平民的袭击动向。", "MONUSCO-FARDC 协调新报道。"]),
    ("rel-expb-monusco-fardc-cooperation",
     "MONUSCO—FARDC：平民保护与安全行动协调",
     "actor-monusco", "actor-fardc", "cooperates_with", "middle",
     "MONUSCO 与 FARDC 在刚果（金）东部协调平民保护与安全行动，包括联合巡逻与针对 ADF 袭击的联合/协调应对。",
     "双方协调决定平民保护的实际覆盖，是评估东部安全环境的关键机制。",
     "协调的具体机制与成效缺乏系统性公开数据；合作属情境依赖型。",
     [S_MONUSCO_FARDC, S_UNSC2808],
     "该合作是维和力量与国家武装力量在平民保护框架内的协调，其成效影响东部平民安全与 ADF 威胁应对。",
     ["MONUSCO-FARDC 联合巡逻新报道。", "ADF 袭击后的联合应对案例。", "安理会授权变化。"]),
    ("rel-expb-adf-nkalubo-led",
     "民主同盟军（伊斯兰国中非省）—梅迪·恩卡卢博：高级领导关系",
     "actor-adf-isis-ca", "person-meddie-nkalubo", "led_by", "outer",
     "恩卡卢博是 ADF/ISIS-CA 高级领导人，联合国叙述称其对 ADF 战斗人员具实际指挥/控制；NCTC 称其为媒体制作与袭击指挥人员。",
     "他是 ADF 领导层中行动与宣传职能的枢纽人物。",
     "联合国叙述中的指控未转化为刑事定罪；其当前具体位置与活动状态缺乏权威信息。",
     [S_UN_NKALUBO, S_NCTC_ISCA],
     "恩卡卢博处于组织身份转换叙事的关键线上（2017 年即负责 ADF 与伊斯兰国和解）；评估其记录价值需保持联合国叙述的归属性。",
     ["联合国对其列名状态的新调整。", "NCTC 对其职务表述的更新。", "ADF 宣传产出相关新信息。"]),
    ("rel-expb-bbmb-talha-led",
     "巴拉·本·马利克旅—阿布·扎伊德·塔勒哈：指挥官关系",
     "actor-bbmb", "person-abu-zaid-talha", "led_by", "outer",
     "塔勒哈是 BBMB 指挥官；欧盟 2026 年 1 月列名确认其身份，并对指挥责任下的行为作出归属性指控。",
     "作为 BBMB 指挥官，他掌握该民兵的实际作战指挥。",
     "欧盟陈述属制裁认定，未经司法确认；其当前状态与 BBMB 内部指挥结构缺乏公开细节。",
     [S_EU_TALHA],
     "塔勒哈是伊斯兰主义民兵深度嵌入苏丹正规军作战体系的人事样本；所有指控保持欧盟归属。",
     ["欧盟或其他司法辖区对其列名状态的新调整。", "BBMB 指挥结构的权威新材料。"]),
    ("rel-expb-talha-saf-allied",
     "阿布·扎伊德·塔勒哈—苏丹武装部队：战时同阵营（欧盟归属）",
     "person-abu-zaid-talha", "actor-saf", "allied_with", "outer",
     "欧盟称 BBMB 作为与 SAF 并肩作战的伊斯兰主义民兵对抗 RSF 及盟友；塔勒哈作为 BBMB 指挥官与其处于战时同阵营关系（欧盟归属性陈述）。",
     "该关系标注了伊斯兰主义民兵与正规军之间的战时同阵营结构。",
     "欧盟陈述属制裁认定；民兵与正规军的实际整合程度不透明。",
     [S_EU_TALHA],
     "同阵营不等于被编入建制；评估苏丹战后军事结构时需区分意识形态化动员力量与正规军序列。",
     ["欧盟陈述更新。", "苏丹冲突中民兵—正规军整合格局的公开变化。"]),
    ("rel-expb-shabaab-karate-led",
     "索马里青年党—马哈德·卡拉特：财政与情报复合体领导",
     "actor-al-shabaab", "person-mahad-karate", "led_by", "outer",
     "卡拉特是青年党财政负责人与阿姆尼亚特（Amniyat）情报与安全翼指挥官，并曾任副埃米尔。",
     "财政与情报双重职能使他成为影响资源分配与内部控制的枢纽人物。",
     "其职权边界与当前在最高领导层的具体位次缺乏公开细节。",
     [S_NCTC_SHABAAB, S_TREAS_JY1028, S_STATE_KARATE],
     "卡拉特代表青年党的「财政—情报复合体」；财政负责人与情报翼指挥官的存续状态比单个战地指挥官更能反映组织长期运转能力。",
     ["美国或其他司法辖区对其状态的新认定。", "NCTC 对其职务表述的调整。"]),
    ("rel-expb-isis-somalia-yusuf-led",
     "伊斯兰国索马里省—阿卜迪韦利·穆罕默德·优素福：财政领导",
     "actor-isis-somalia", "person-abdiweli-mohamed-yusuf", "led_by", "outer",
     "优素福担任 ISIS-Somalia 财政办公室负责人，负责外国战斗人员、补给与弹药的输送及资金管理。",
     "财政执行端是该分支在伊斯兰国非洲网络中枢纽价值的落点。",
     "「管理或部分管理」的表述来自美方材料，其实际权限范围不透明。",
     [S_TREAS_JY1652],
     "优素福是「该分支体量小、权重大的结构性原因」在人事层面的落点；评估该分支韧性时，财政执行者的存续比普通战地指挥官变动更具指示意义。",
     ["美国或其他司法辖区对其状态的新认定。", "ISIS-Somalia 财政结构的新权威材料。"]),
    ("rel-expb-mumin-yusuf-reporting",
     "阿卜杜勒·卡迪尔·穆明—阿卜迪韦利·穆罕默德·优素福：汇报结构（美方归属）",
     "person-abd-al-qadir-mumin", "person-abdiweli-mohamed-yusuf", "affiliated_with", "outer",
     "美财政部材料称优素福会见并向穆明汇报；穆明同时是 ISIS-Somalia 创建者与卡拉尔办公室负责人。",
     "该关系标注了该分支「区域协调—财政执行」结构的连接点。",
     "汇报关系的频率、渠道与内容缺乏公开细节。",
     [S_TREAS_JY1652],
     "穆明处于区域协调端、优素福处于财政执行端；现有 ontology 无 reports_to，用 affiliated_with 表达组织关联并在档案说明汇报结构。",
     ["美方材料对两人关系的更新表述。", "ISIS-Somalia 领导网络的新权威信息。"]),
    ("rel-expb-fahiye-yusuf-reporting",
     "阿卜迪拉赫曼·法希耶—阿卜迪韦利·穆罕默德·优素福：汇报结构（美方归属）",
     "person-abdirahman-fahiye", "person-abdiweli-mohamed-yusuf", "affiliated_with", "outer",
     "美财政部材料称优素福会见并向法希耶汇报；法希耶是 ISIS-Somalia 行动层面领导人。",
     "该关系标注了该分支「行动领导—财政执行」结构的连接点。",
     "汇报关系的频率、渠道与内容缺乏公开细节。",
     [S_TREAS_JY1652],
     "法希耶处于行动领导端、优素福处于财政执行端；现有 ontology 无 reports_to，用 affiliated_with 表达组织关联并在档案说明汇报结构。",
     ["美方材料对两人关系的更新表述。", "ISIS-Somalia 领导网络的新权威信息。"]),
]
for _rid, _title, _src, _tgt, _rtype, _ring, _ov, _why, _unc, _srcs, _asip, _watch in _R2_BATCH:
    NEW_RELATION_PROFILES[_rid] = rprofile(
        _rid, title=_title, src=_src, tgt=_tgt, rtype=_rtype, ring=_ring,
        maturity=R2, overview=_ov,
        parties=[{"entity_id": _src, "role": "关系一方"}, {"entity_id": _tgt, "role": "关系另一方"}],
        why=_why, unc=_unc, sources=_srcs, asip=_asip, watch=_watch,
    )

_R2_STATUS = {
    "rel-expb-monusco-adf-countering": "结构性对抗关系当前有效，处于平民保护框架内。",
    "rel-expb-monusco-fardc-cooperation": "合作当前有效，属情境依赖型协调。",
    "rel-expb-adf-nkalubo-led": "高级领导关系当前有效（联合国列名对象）。",
    "rel-expb-bbmb-talha-led": "指挥官关系当前有效（欧盟 2026 年列名）。",
    "rel-expb-talha-saf-allied": "战时同阵营关系当前有效（欧盟归属性陈述）。",
    "rel-expb-shabaab-karate-led": "领导关系当前有效。",
    "rel-expb-isis-somalia-yusuf-led": "财政领导关系当前有效。",
    "rel-expb-mumin-yusuf-reporting": "组织关联（汇报结构）当前有效，依据美方材料。",
    "rel-expb-fahiye-yusuf-reporting": "组织关联（汇报结构）当前有效，依据美方材料。",
}
for _k, _v in _R2_STATUS.items():
    NEW_RELATION_PROFILES[_k]["current_status"] = _v
    NEW_RELATION_PROFILES[_k]["current_assessment"] = _v
