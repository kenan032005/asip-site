# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-B — relationship content module (part 1: Somalia network).

Source of truth: ASIP-PPT-ENTITY-EXPANSION-B-Authoritative-Content-Pack.md (§13-§14).
Maps to existing ontology (no ontology expansion). R3 dossiers carry full
formation/stages/current/geography/events/timeline/why/evidence/uncertainty/
ASIP/watch. No independent research; attribution preserved.
"""

TODAY = "2026-08-10"
IMPORTER = "expansion-b"

S_UNSC2767 = "expb-unsc-2767-2024"
S_AU_AUSSOM = "expb-au-aussom-psc-2026-07"
S_AUSSOM_RECOVER = "expb-aussom-snaf-recover-cities"
S_AUSSOM_CAPTURE = "expb-aussom-snaf-capture"
S_UNSOS = "expb-unsos-interop-2026-05"
S_PANEL777 = "expb-un-panel-s2025-777"
S_UNS2026 = "d2-un-s2026-44"
S_NCTC_SHABAAB = "expa-nctc-al-shabaab-2026-04"
S_NCTC_ISS = "expa-nctc-isis-somalia-2025-02"
S_TREAS_JY1652 = "expa-treasury-isis-somalia-financier-2023-07-27"
S_TREAS_JY1066 = "expb-treasury-jy1066-2022-11-01"
S_NCTC_ISCA = "expa-nctc-isis-ca-2025-04"
S_UPDF_REVIEW = "expb-updf-shujaa-review"
S_UPDF_STRIKE = "expb-updf-shujaa-strike"
S_MONUSCO_FARDC = "expb-monusco-fardc-ituri"
S_UN_FS = "expb-un-monusco-factsheet"
S_UNSC2808 = "expb-unsc-2808-2025"
S_SG_ADF = "expb-un-sg-adf-2025-11-22"
S_TREAS_BBMB = "expa-treasury-sudan-islamist-2025-09-12"
S_OFAC_BBMB = "expa-ofac-bbmb-2025-09-12"
S_EU_TALHA = "expb-eu-2026-251-talha"
S_STATE_KARATE = "expb-state-sdgt-karate-2015-04-10"
S_TREAS_JY1028 = "expb-treasury-jy1028-karate-2022"
S_UN_NKALUBO = "expb-un-nkalubo-listing"


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
    # ---- Somalia network ----
    rel(
        "rel-expb-shabaab-aussom-conflict",
        "actor-al-shabaab", "actor-aussom", "fought_against",
        ring="inner", status="active_armed_conflict",
        time_start="2025-01-01", start_year=2025, confidence="high",
        summary="索马里青年党（Al-Shabaab）与非洲联盟驻索马里支助与稳定特派团（AUSSOM）处于持续的武装对抗状态；AUSSOM 依据安理会第 2767 号决议获授权开展行动削弱 Al-Shabaab 及与伊斯兰国关联的分支。",
        formation="AUSSOM 于 2025 年 1 月 1 日接替 ATMIS，其授权（UNSC 2767）明确包含采取一切必要措施削弱 Al-Shabaab；这使 AUSSOM 成为 Al-Shabaab 在国际/非盟力量层面的首要军事对手。",
        scope="索马里中南部为主（Al-Shabaab 活跃区）",
        why="这是索马里冲突中非盟力量与 Al-Shabaab 的核心对抗线，决定 Al-Shabaab 所受外部军事压力的强度。",
        unc="AUSSOM 与 Al-Shabaab 交战的规模、频率与双方损失缺乏系统公开数据；战果报道多为特派团官方口径。",
        refs=[S_UNSC2767, S_AU_AUSSOM, S_AUSSOM_RECOVER],
        note="fought_against 表达特派团授权下的反 Al-Shabaab 作战关系；AUSSOM 是依据安理会授权的国际力量，其与 Al-Shabaab 的对抗属授权框架内的武装冲突关系。",
    ),
    rel(
        "rel-expb-shabaab-snaf-conflict",
        "actor-al-shabaab", "actor-somali-national-armed-forces", "fought_against",
        ring="inner", status="active_armed_conflict",
        confidence="high",
        summary="索马里国家武装部队（SNAF）与 Al-Shabaab 处于持续的武装对抗状态；SNAF 是对抗 Al-Shabaab 的核心国家军事行为体，并在 2026 年与 AUSSOM 开展联合行动。",
        formation="SNAF 作为索马里国家武装力量，长期与 Al-Shabaab 作战；安理会第 2767 号决议欢迎索马里安全部队自 2022 年以来接管约 7,000 名缩编 ATMIS 部队的责任，标志着国家力量在反 Al-Shabaab 战役中的角色扩大。",
        scope="索马里中南部为主",
        why="这是索马里安全过渡的核心对抗线：SNAF 的作战成效决定国家能否承接国际安全力量的移交。",
        unc="SNAF 对 Al-Shabaab 作战的规模、损失与战果缺乏系统公开数据；联合行动战果多为官方口径。",
        refs=[S_UNSC2767, S_AUSSOM_RECOVER, S_AUSSOM_CAPTURE],
    ),
    rel(
        "rel-expb-aussom-snaf-cooperation",
        "actor-aussom", "actor-somali-national-armed-forces", "cooperates_with",
        ring="inner", status="active_joint_operations_and_transition",
        time_start="2025-01-01", start_year=2025, confidence="high",
        summary="AUSSOM 与索马里国家武装部队（SNAF）开展联合行动对抗 Al-Shabaab，并以向 SNAF 条件式移交安全责任为任务核心。",
        formation="AUSSOM 的任务设计明确以支持向索马里部队逐步移交安全责任为目标；双方 2026 年持续开展联合行动（2026 年 3 月收复下谢贝利两座城市、2026 年 4 月联合俘获指挥官）。",
        scope="索马里中南部",
        why="这是索马里安全过渡的机制核心：联合行动的成效与安全移交的节奏决定国家安全的可持续性。",
        unc="移交的条件判断标准与时间表在公开材料中未具体化；联合行动的具体分工与指挥关系缺乏系统公开数据。",
        refs=[S_UNSC2767, S_AU_AUSSOM, S_AUSSOM_RECOVER, S_AUSSOM_CAPTURE, S_UNSOS],
        note="cooperates_with 表达联合行动与安全移交双重关系；UNSOS 2026 年 5 月组织的互操作训练是双方合作机制的补充证据。",
    ),
    rel(
        "rel-expb-isis-somalia-puntland-conflict",
        "actor-isis-somalia", "actor-puntland-security-forces", "fought_against",
        ring="inner", status="active_armed_conflict",
        time_start="2024-12", start_year=2024, confidence="medium_high",
        summary="伊斯兰国索马里省（ISIS-Somalia）与邦特兰安全力量处于武装对抗状态；邦特兰力量自 2024 年 12 月起以「闪电」行动（Operation Hilaac）对 ISIS-Somalia 发起大规模清剿。",
        formation="2024 年 12 月，邦特兰安全力量（PSF、PMPF、德尔维什部队等组成的行动集群）发起 Operation Hilaac，集结约 4,000 人对盘踞 Cal Miskaat 山区的 ISIS-Somalia 展开清剿；ISIS-Somalia 于 2024 年 12 月 31 日以 12 名外国自杀式袭击者及武装无人机发动先发袭击，被击退。",
        scope="邦特兰山区（Cal Miskaat）",
        why="Operation Hilaac 显著削弱了 ISIS-Somalia（联合国监测组估计剩约 200—300 名战斗人员），是改变该分支在非洲之角安全图景的关键行动。",
        unc="伤亡数字与兵力规模来自联合国专家小组报告，属报告口径而非独立核实；邦特兰集合标签下各单位的实际编成缺乏公开细节。",
        refs=[S_PANEL777, S_UNS2026],
        note="fought_against 表达行动层面的武装对抗；「邦特兰安全部队」为行动层面集合标签，非单一法律统一部队。",
    ),
    rel(
        "rel-expb-shabaab-karate-led",
        "actor-al-shabaab", "person-mahad-karate", "led_by",
        ring="outer", status="reported_leadership_status",
        confidence="high",
        summary="马哈德·卡拉特（Mahad Karate）是索马里青年党的财政负责人与阿姆尼亚特（Amniyat）情报与安全翼指挥官，并曾任副埃米尔。",
        formation="NCTC 2026 年资料确认卡拉特在青年党内的三重定位（财政、情报、前副埃米尔）；美财政部 2022 年材料指认其财政团队结构。",
        scope="索马里",
        why="财政与情报双重职能使他成为青年党权力结构中影响资源分配与内部控制的枢纽人物。",
        unc="其职权边界与当前在最高领导层的具体位次缺乏公开细节。",
        refs=[S_NCTC_SHABAAB, S_TREAS_JY1028, S_STATE_KARATE],
    ),
    rel(
        "rel-expb-isis-somalia-yusuf-led",
        "actor-isis-somalia", "person-abdiweli-mohamed-yusuf", "led_by",
        ring="outer", status="reported_finance_leadership",
        confidence="medium_high",
        summary="阿卜迪韦利·穆罕默德·优素福（Abdiweli Mohamed Yusuf）担任伊斯兰国索马里省财政办公室负责人，负责外国战斗人员、补给与弹药的输送及资金管理。",
        formation="美财政部称优素福自至少 2020 年前后担任 ISIS-Somalia 财政办公室负责人，并向穆明与法希耶汇报。",
        scope="索马里",
        why="财政执行端是该分支在伊斯兰国非洲网络中枢纽价值的落点，优素福是这一职能的核心操作者。",
        unc="「管理或部分管理」的表述来自美方材料，其实际权限范围不透明。",
        refs=[S_TREAS_JY1652],
    ),
    rel(
        "rel-expb-mumin-yusuf-reporting",
        "person-abd-al-qadir-mumin", "person-abdiweli-mohamed-yusuf", "affiliated_with",
        ring="outer", status="reported_reporting_relationship",
        confidence="medium_high",
        summary="美国财政部材料称优素福会见并向阿卜杜勒·卡迪尔·穆明汇报；穆明同时是 ISIS-Somalia 创建者与卡拉尔办公室负责人。",
        formation="在 ISIS-Somalia 的领导网络中，穆明处于区域协调端（卡拉尔办公室），优素福处于财政执行端；美方材料确认两人之间存在汇报关系。",
        scope="索马里",
        why="该关系标注了该分支「区域协调—财政执行」结构的连接点，是理解其财政枢纽运作的人事线索。",
        unc="汇报关系的频率、渠道与内容缺乏公开细节；使用 affiliated_with 表达组织关联，不扩展 ontology。",
        refs=[S_TREAS_JY1652],
        note="现有 ontology 无 reports_to 类型，故用 affiliated_with 表达组织关联并在档案中说明汇报结构，不新增关系类型。",
    ),
    rel(
        "rel-expb-fahiye-yusuf-reporting",
        "person-abdirahman-fahiye", "person-abdiweli-mohamed-yusuf", "affiliated_with",
        ring="outer", status="reported_reporting_relationship",
        confidence="medium_high",
        summary="美国财政部材料称优素福会见并向阿卜迪拉赫曼·法希耶汇报；法希耶是 ISIS-Somalia 行动层面领导人。",
        formation="在 ISIS-Somalia 的领导网络中，法希耶处于行动领导端，优素福处于财政执行端；美方材料确认两人之间存在汇报关系。",
        scope="索马里",
        why="该关系标注了该分支「行动领导—财政执行」结构的连接点。",
        unc="汇报关系的频率、渠道与内容缺乏公开细节；使用 affiliated_with 表达组织关联，不扩展 ontology。",
        refs=[S_TREAS_JY1652],
        note="现有 ontology 无 reports_to 类型，故用 affiliated_with 表达组织关联并在档案中说明汇报结构，不新增关系类型。",
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

# ---- R3 A: Al-Shabaab <-> AUSSOM ----
NEW_RELATION_PROFILES["rel-expb-shabaab-aussom-conflict"] = rprofile(
    "rel-expb-shabaab-aussom-conflict",
    title="索马里青年党—AUSSOM：授权框架下的持续对抗",
    src="actor-al-shabaab", tgt="actor-aussom",
    rtype="fought_against", ring="inner", maturity=R3,
    overview="AUSSOM 依据联合国安理会第 2767 号决议于 2025 年 1 月 1 日接替 ATMIS，其授权明确包含采取一切必要措施削弱 Al-Shabaab 及与伊斯兰国关联的分支。这使 AUSSOM 成为 Al-Shabaab 在国际/非盟力量层面的首要军事对手，双方处于持续的武装对抗状态。",
    parties=[{"entity_id": "actor-al-shabaab", "role": "索马里叛乱与恐怖组织（基地组织关联方）"},
             {"entity_id": "actor-aussom", "role": "非洲联盟驻索马里支助与稳定特派团"}],
    formation="AUSSOM 由安理会第 2767 号决议（2024-12-27）授权，第 1 阶段上限 12,626 人（含 1,040 警察），第 2 阶段前六个月上限 11,826 人（含 680 警察）。其授权包含对 Al-Shabaab 的进攻性削弱任务，与前身 ATMIS 的过渡定位形成衔接。",
    initial="AUSSOM 接替 ATMIS 时即承接了对 Al-Shabaab 的作战与遏制职能；安理会决议将削弱 Al-Shabaab 列为授权目标之一。",
    stages=[
        {"period": "2025-01-01 起", "detail": "AUSSOM 正式运作，授权对 Al-Shabaab 采取一切必要措施。"},
        {"period": "2025-07-01 起", "detail": "第 2 阶段开始，兵力上限调整，任务含确保地点安全与支持进攻行动。"},
        {"period": "2026 年", "detail": "AUSSOM 与 SNAF 持续联合行动（2026 年 3 月收复下谢贝利两城、2026 年 4 月俘获指挥官）；非盟 2026 年 7 月强调融资可持续性问题。"},
    ],
    causes=[
        "安理会授权下的反 Al-Shabaab 任务",
        "Al-Shabaab 对索马里稳定与国际部队的持续威胁",
        "安全责任向索马里部队移交进程中的压力传导",
    ],
    turning_points=[
        {"event": "2024-12-27 安理会第 2767 号决议", "impact": "为 AUSSOM 对 Al-Shabaab 作战提供授权基础。", "source_ids": [S_UNSC2767]},
        {"event": "2025-01-01 AUSSOM 接替 ATMIS", "impact": "作战与遏制职能正式交接。", "source_ids": [S_UNSC2767]},
        {"event": "2026-07 非盟强调融资问题", "impact": "融资不确定性进入公开议程，影响行动强度的可持续性。", "source_ids": [S_AU_AUSSOM]},
    ],
    regional="对抗集中于索马里中南部（Al-Shabaab 活跃区），AUSSOM 行动与 SNAF 联合打击沿中南部战线展开。",
    impact="AUSSOM 的行动强度直接决定 Al-Shabaab 所受外部军事压力；融资与兵力生成不确定性可能为 Al-Shabaab 提供重组空间。",
    why="这是索马里冲突中非盟力量与 Al-Shabaab 的核心对抗线，是评估 Al-Shabaab 机会结构的关键输入。",
    unc="双方交战的规模、频率与损失缺乏系统公开数据；战果报道多为特派团官方口径，未经独立核实。",
    sources=[S_UNSC2767, S_AU_AUSSOM, S_AUSSOM_RECOVER, S_AUSSOM_CAPTURE],
    drivers=["安理会授权框架", "非盟的稳定目标", "Al-Shabaab 的持续抵抗能力"],
    constraints=["融资与兵力生成约束", "安全移交进程的时间压力"],
    assessment="对抗关系当前有效。AUSSOM 的进攻性授权明确，但其实际压力水平受融资与兵力限制。",
    asip="应把 AUSSOM 视为 Al-Shabaab 冲突中的中央军事—安全节点而非维和背景：其阶段授权、兵力上限与融资状态构成连续变量。当国际压力减弱或出现空隙，Al-Shabaab 往往利用空隙重组。",
    watch=[
        "安理会关于 AUSSOM 后续授权与兵力上限的新决议。",
        "非盟对融资缺口的公开表述与捐助方回应。",
        "AUSSOM 与 SNAF 联合行动的频率与战果报道。",
        "安全责任移交的里程碑事件。",
    ],
)
NEW_RELATION_TIMELINES["rel-expb-shabaab-aussom-conflict"] = [
    tl("2024-12-27", "安理会第 2767 号决议", "授权 AUSSOM 采取一切必要措施支持索马里，含削弱 Al-Shabaab。",
       "确立对 Al-Shabaab 作战的授权基础。", "high", [S_UNSC2767]),
    tl("2025-01-01", "AUSSOM 接替 ATMIS", "特派团正式运作，承接对 Al-Shabaab 的作战与遏制职能。",
       "对抗关系进入新阶段。", "high", [S_UNSC2767]),
    tl("2025-07-01", "第 2 阶段开始", "兵力上限调整，任务含支持进攻行动与据点防护。",
       "作战强度与资源配置进入新阶段。", "high", [S_UNSC2767]),
    tl("2026-03", "下谢贝利收复战", "SNAF 与 AUSSOM 收复 Daarusalaam 与 Mubarak。",
       "联合行动取得可引用的战果节点。", "medium_high", [S_AUSSOM_RECOVER]),
    tl("2026-07", "融资可持续性问题", "非盟主席强调特派团需要可持续融资。",
       "融资不确定性进入公开议程。", "medium_high", [S_AU_AUSSOM]),
]

# ---- R3 B: Al-Shabaab <-> SNAF ----
NEW_RELATION_PROFILES["rel-expb-shabaab-snaf-conflict"] = rprofile(
    "rel-expb-shabaab-snaf-conflict",
    title="索马里青年党—索马里国家武装部队：国家反恐战役核心对抗",
    src="actor-al-shabaab", tgt="actor-somali-national-armed-forces",
    rtype="fought_against", ring="inner", maturity=R3,
    overview="索马里国家武装部队（SNAF）是对抗 Al-Shabaab 的核心国家军事行为体。安理会第 2767 号决议欢迎索马里安全部队自 2022 年以来接管约 7,000 名缩编 ATMIS 部队的责任；2026 年 SNAF 持续与 AUSSOM 联合行动对抗 Al-Shabaab。",
    parties=[{"entity_id": "actor-al-shabaab", "role": "索马里叛乱与恐怖组织"},
             {"entity_id": "actor-somali-national-armed-forces", "role": "索马里联邦国家武装力量"}],
    formation="SNAF 长期与 Al-Shabaab 作战；安全过渡进程（自 2022 年接管 ATMIS 责任）扩大了国家力量在战役中的角色。",
    initial="长期持续的武装对抗关系，随安全过渡而强化。",
    stages=[
        {"period": "2022 年以来", "detail": "索马里安全部队接管约 7,000 名缩编 ATMIS 部队的责任。"},
        {"period": "2026-03", "detail": "SNAF 与 AUSSOM 收复下谢贝利 Daarusalaam 与 Mubarak。"},
        {"period": "2026-04", "detail": "SNAF Gorgor 203 部队与 AUSSOM 乌干达部队俘获 Al-Shabaab 指挥官。"},
        {"period": "2026-05", "detail": "UNSOS 组织 SNAF 与 AUSSOM、联合国警卫部队互操作训练。"},
    ],
    causes=["Al-Shabaab 对国家权威的挑战", "安全责任移交进程", "国际训练与联合行动支持"],
    turning_points=[
        {"event": "2022 年以来接管 ATMIS 责任", "impact": "国家力量在反 Al-Shabaab 战役中的角色扩大。", "source_ids": [S_UNSC2767]},
        {"event": "2026-03/04 联合战果", "impact": "验证 SNAF 与 AUSSOM 联合行动的作战成效。", "source_ids": [S_AUSSOM_RECOVER, S_AUSSOM_CAPTURE]},
    ],
    regional="对抗集中于索马里中南部（Al-Shabaab 活跃区）。",
    impact="SNAF 的作战成效决定国家能否承接国际安全力量移交；能力真空期是 Al-Shabaab 的典型机会结构。",
    why="这是索马里安全过渡的核心对抗线，直接决定安全移交的成败。",
    unc="SNAF 对 Al-Shabaab 作战的规模、损失与战果缺乏系统公开数据；联合行动战果多为官方口径。",
    sources=[S_UNSC2767, S_AUSSOM_RECOVER, S_AUSSOM_CAPTURE, S_UNSOS],
    drivers=["国家反恐使命", "安全过渡目标", "国际支持"],
    constraints=["能力建设尚在进行", "后勤与财政约束"],
    assessment="对抗关系当前有效。SNAF 的承接能力与移交节奏是评估重点。",
    asip="SNAF 应被理解为「过渡中的国家军事行为体」：其能力评估必须结合承接的 ATMIS 责任规模与联合行动成效。真正的风险点不在公开宣布的移交节点，而在移交后的能力真空期。",
    watch=[
        "安理会关于安全移交里程碑的新表述。",
        "SNAF 与 AUSSOM 联合行动的频率与战果。",
        "关于 SNAF 兵力、装备或薪酬的权威更新。",
    ],
)
NEW_RELATION_TIMELINES["rel-expb-shabaab-snaf-conflict"] = [
    tl("2022 年以来", "接管 ATMIS 责任", "索马里安全部队接管约 7,000 名缩编 ATMIS 部队的责任。",
       "国家力量角色扩大。", "medium_high", [S_UNSC2767]),
    tl("2024-12-27", "安理会第 2767 号决议", "欢迎安全移交进展并授权 AUSSOM。",
       "移交进程获得进一步制度确认。", "high", [S_UNSC2767]),
    tl("2026-03", "收复下谢贝利两城", "SNAF 与 AUSSOM 收复 Daarusalaam 与 Mubarak。",
       "联合行动战果节点。", "medium_high", [S_AUSSOM_RECOVER]),
    tl("2026-04", "俘获指挥官", "SNAF Gorgor 203 部队与 AUSSOM 联合俘获 Al-Shabaab 指挥官。",
       "联合行动在高价值目标层面取得成果。", "medium_high", [S_AUSSOM_CAPTURE]),
]

# ---- R3 C: AUSSOM <-> SNAF ----
NEW_RELATION_PROFILES["rel-expb-aussom-snaf-cooperation"] = rprofile(
    "rel-expb-aussom-snaf-cooperation",
    title="AUSSOM—索马里国家武装部队：联合行动与安全移交",
    src="actor-aussom", tgt="actor-somali-national-armed-forces",
    rtype="cooperates_with", ring="inner", maturity=R3,
    overview="AUSSOM 与 SNAF 的合作以联合行动与安全责任移交为双重核心：AUSSOM 的任务设计明确支持向索马里部队条件式移交安全责任，双方 2026 年持续开展联合行动。",
    parties=[{"entity_id": "actor-aussom", "role": "非洲联盟驻索马里特派团"},
             {"entity_id": "actor-somali-national-armed-forces", "role": "索马里国家武装力量"}],
    formation="AUSSOM 的授权（UNSC 2767）明确以支持向索马里部队逐步移交安全责任为目标；双方 2026 年 3 月、4 月联合行动取得战果，5 月由 UNSOS 组织互操作训练。",
    initial="AUSSOM 接替 ATMIS 时即与 SNAF 形成「国际力量—国家力量」的合作框架。",
    stages=[
        {"period": "2025-01-01 起", "detail": "AUSSOM 运作，与 SNAF 建立联合行动框架。"},
        {"period": "2026-03", "detail": "联合收复下谢贝利 Daarusalaam 与 Mubarak。"},
        {"period": "2026-04", "detail": "联合俘获 Al-Shabaab 指挥官（Gorgor 203 与乌干达部队）。"},
        {"period": "2026-05", "detail": "UNSOS 组织三方互操作训练。"},
    ],
    causes=["安全责任移交目标", "联合反 Al-Shabaab 战役需求", "国际支持机制（UNSOS）"],
    turning_points=[
        {"event": "2025-01-01 合作框架确立", "impact": "联合行动与移交进程开始运行。", "source_ids": [S_UNSC2767]},
        {"event": "2026 年联合战果", "impact": "验证合作机制的作战成效。", "source_ids": [S_AUSSOM_RECOVER, S_AUSSOM_CAPTURE]},
    ],
    regional="合作覆盖索马里中南部战线与全国安全移交进程。",
    impact="双方合作的质量决定安全移交的成败与 Al-Shabaab 的机会结构。",
    why="这是索马里安全过渡的机制核心。",
    unc="移交条件与时间表未具体化；联合行动的具体分工与指挥关系缺乏系统数据。",
    sources=[S_UNSC2767, S_AU_AUSSOM, S_AUSSOM_RECOVER, S_AUSSOM_CAPTURE, S_UNSOS],
    drivers=["移交目标", "联合反恐需求", "国际支持"],
    constraints=["SNAF 承接能力尚在建设", "融资约束"],
    assessment="合作当前有效，处于联合行动与移交并行的阶段。",
    asip="把 AUSSOM 与 SNAF 的关系视为「联合行动 + 能力移交」的双轨机制：战果反映联合行动成效，而移交的真正风险在能力真空期。评估时应同时跟踪联合行动的持续性、移交里程碑与国际融资状态。",
    watch=[
        "安全移交里程碑公告。",
        "联合行动频率与战果。",
        "UNSOS 或国际支持机制的新安排。",
        "融资与兵力生成状态。",
    ],
)
NEW_RELATION_TIMELINES["rel-expb-aussom-snaf-cooperation"] = [
    tl("2025-01-01", "合作框架确立", "AUSSOM 运作，与 SNAF 建立联合行动与移交框架。",
       "合作关系开始运行。", "high", [S_UNSC2767]),
    tl("2026-03", "下谢贝利收复战", "联合收复 Daarusalaam 与 Mubarak。",
       "联合行动战果节点。", "medium_high", [S_AUSSOM_RECOVER]),
    tl("2026-04", "俘获指挥官", "Gorgor 203 与乌干达部队联合俘获 Al-Shabaab 指挥官。",
       "高价值目标层面成果。", "medium_high", [S_AUSSOM_CAPTURE]),
    tl("2026-05", "互操作训练", "UNSOS 组织 AUSSOM、SNAF 与联合国警卫部队训练。",
       "合作机制制度化加强。", "medium_high", [S_UNSOS]),
]

# ---- R3 D: ISIS-Somalia <-> Puntland Security Forces / Operation Hilaac ----
NEW_RELATION_PROFILES["rel-expb-isis-somalia-puntland-conflict"] = rprofile(
    "rel-expb-isis-somalia-puntland-conflict",
    title="伊斯兰国索马里省—邦特兰安全力量：闪电行动（Operation Hilaac）",
    src="actor-isis-somalia", tgt="actor-puntland-security-forces",
    rtype="fought_against", ring="inner", maturity=R3,
    overview="伊斯兰国索马里省与邦特兰安全力量处于武装对抗状态。2024 年 12 月，邦特兰力量以「闪电」行动（Operation Hilaac）对盘踞 Cal Miskaat 山区的 ISIS-Somalia 发起大规模清剿，显著削弱了该分支。",
    parties=[{"entity_id": "actor-isis-somalia", "role": "伊斯兰国在索马里的分支"},
             {"entity_id": "actor-puntland-security-forces", "role": "邦特兰多成分安全力量（行动层面集合标签）"}],
    formation="2024 年 12 月，邦特兰安全力量集结约 4,000 名士兵（主要来自邦特兰安全部队、海上警察部队与德尔维什部队）发起 Operation Hilaac。ISIS-Somalia 于 2024 年 12 月 31 日以 12 名外国自杀式袭击者及武装无人机发动先发袭击，被击退。",
    initial="行动发起即进入激烈对抗：ISIS-Somalia 以先发打击回应，邦特兰力量随后转入地面清剿。",
    stages=[
        {"period": "2024-12", "detail": "Operation Hilaac 发起，集结约 4,000 人。"},
        {"period": "2024-12-31", "detail": "ISIS-Somalia 先发袭击（12 名外国自杀式袭击者 + 武装无人机），被击退。"},
        {"period": "2025-01 起", "detail": "邦特兰力量向 Cal Miskaat 推进，夺取阵地、掩体、隧道、洞穴与补给囤积点。"},
        {"period": "至 2025-10", "detail": "专家小组报告显著邦特兰伤亡与 ISIS 大规模损失。"},
        {"period": "2026", "detail": "UN S/2026/44 评估 ISIS-Somalia 威胁显著降低，估计剩约 200—300 名战斗人员。"},
    ],
    causes=["ISIS-Somalia 长期盘踞邦特兰山区", "邦特兰当局的反恐决策", "区域与国际伙伴配合"],
    turning_points=[
        {"event": "2024-12 Operation Hilaac 发起", "impact": "大规模清剿启动。", "source_ids": [S_PANEL777]},
        {"event": "2024-12-31 先发袭击被击退", "impact": "ISIS-Somalia 的先发打击未达目的。", "source_ids": [S_PANEL777]},
        {"event": "2025 年 Cal Miskaat 推进", "impact": "剥夺 ISIS-Somalia 的主要据点。", "source_ids": [S_PANEL777]},
        {"event": "2026 年监测组评估", "impact": "确认威胁显著降低与残部规模。", "source_ids": [S_UNS2026]},
    ],
    regional="对抗集中于邦特兰山区（Cal Miskaat），该地形的洞穴与隧道系统是主要地理约束。",
    impact="行动显著削弱 ISIS-Somalia，改变了该分支在非洲之角的安全图景及其在伊斯兰国网络中的枢纽可操作性。",
    why="这是该分支实力骤降的关键行动，也是「邦特兰安全部队」集合标签的由来。",
    unc="伤亡与兵力数字来自联合国专家小组报告，属报告口径；集合标签下各单位的编成缺乏公开细节。",
    sources=[S_PANEL777, S_UNS2026],
    drivers=["邦特兰反恐决策", "ISIS-Somalia 的山区盘踞", "外部配合"],
    constraints=["邦特兰资源有限", "行动可持续性依赖外部支持"],
    assessment="对抗关系当前有效，邦特兰力量保持主动态势。",
    asip="「邦特兰安全部队」作为集合标签的建模，准确反映 Operation Hilaac 的多成分组织现实；评估重点是行动可持续性——邦特兰资源有限，长期维持高度依赖区域与国际支持，这一脆弱性是后续风险关键。",
    watch=[
        "Operation Hilaac 后续阶段与战果报道。",
        "专家小组对残部规模的更新评估。",
        "外部支持的新公告或调整。",
    ],
)
NEW_RELATION_TIMELINES["rel-expb-isis-somalia-puntland-conflict"] = [
    tl("2024-12", "Operation Hilaac 发起", "邦特兰力量集结约 4,000 人对 ISIS-Somalia 展开清剿。",
       "大规模对抗启动。", "medium_high", [S_PANEL777]),
    tl("2024-12-31", "先发袭击被击退", "ISIS-Somalia 以 12 名外国自杀式袭击者及武装无人机发动袭击。",
       "先发打击未达目的。", "medium_high", [S_PANEL777]),
    tl("2025-01 起", "Cal Miskaat 推进", "邦特兰力量夺取 ISIS-Somalia 阵地、掩体、隧道与补给。",
       "主要据点被剥夺。", "medium_high", [S_PANEL777]),
    tl("至 2025-10", "显著伤亡报告", "专家小组报告显著邦特兰伤亡与 ISIS 大规模损失。",
       "对抗强度与代价明确。", "medium_high", [S_PANEL777]),
    tl("2026", "威胁显著降低评估", "UN S/2026/44 估计 ISIS-Somalia 剩约 200—300 人。",
       "行动成效获联合国评估确认。", "medium_high", [S_UNS2026]),
]
