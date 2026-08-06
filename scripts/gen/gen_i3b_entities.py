# -*- coding: utf-8 -*-
"""I3-B: upgrade remaining basic profiles to standard/encyclopedia and add the
10 required core entities (all at least standard, none empty)."""
import json, sys
from pathlib import Path

REPO = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-trusted")
DATA = REPO / "data" / "intelligence" / "africa"
REVIEWED = "2026-08-06"

def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))

def save(name, obj):
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")

def body_chars(sections):
    total = 0
    for k, v in sections.items():
        if isinstance(v, str):
            total += len(v)
        elif isinstance(v, list):
            total += sum(len(str(x)) for x in v)
        elif isinstance(v, dict):
            if v.get("p"):
                total += sum(len(str(x)) for x in v["p"])
            if v.get("list"):
                total += sum(len(str(x)) for x in v["list"])
    return total

def count_sections(sections):
    return sum(1 for k, v in sections.items() if str(v or "").strip())

# =====================================================================
# ENCYCLOPEDIA UPGRADES (5): Ansar Dine, al-Mourabitoun, Katiba Macina, AQIM, IS Sahel
# =====================================================================
ency = {}

ency["actor-ansar-eddine"] = {
  "sections": {
    "core_assessment": "安萨尔埃丁（Ansar al-Din，意为“宗教捍卫者”）是 2012 年马里北部危机中由[[entity:person-iyad-ag-ghali|伊亚德·阿格·加利]]领导的基地组织关联武装，主张在马里推行沙里亚法；2012 年曾与图阿雷格分离武装短暂结盟攻占北部重镇，2013 年法军干预后转入地下，2017 年作为创始力量并入 [[entity:actor-jnim|JNIM]]。当前其是否仍作为独立组织活动存疑——多数评估认为其已融入 JNIM 框架，名称更多作为历史实体保留。",
    "name_and_translation": "规范中文名：安萨尔埃丁（安萨尔丁）；英文/法文 Ansar al-Din / Ansar Dine；阿拉伯语 أنصار الدين。本库以“安萨尔埃丁”为规范名；历史资料中亦写作“安萨尔丁”。",
    "formation_background": "组织源于 2000 年代后期马里北部图阿雷格与阿拉伯社区中的宗教政治运动：伊亚德·阿格·加利曾在 1990 年代领导图阿雷格叛乱并参与和平进程，后转向伊斯兰主义政治；2012 年初马里北部危机中，其组建安萨尔埃丁并拒绝图阿雷格分离派的“世俗国家”主张，提出“沙里亚治理”路线。",
    "history": "2012 年：与阿扎瓦德民族解放运动（MNLA）短暂结盟攻占基达尔、通布图、加奥，后因路线分歧决裂；2013 年：法军“薮猫行动”干预，安萨尔埃丁撤入北部山区与马里—阿尔及利亚边境；2013—2016 年：作为 AQIM 网络一部分进行游击；2017 年 3 月：伊亚德·阿格·加利宣布组建 JNIM，安萨尔埃丁作为创始组成部分并入（constituent_of），此后以 JNIM 名义活动。",
    "structure": "安萨尔埃丁在 2012—2016 年有相对集中的领导（伊亚德·阿格·加利）与区域指挥官网络，在马里北部（基达尔方向）与部分中部地区活动；并入 JNIM 后不再作为独立指挥实体存在，其人员与网络融入 JNIM 的“北部集群”与“中部集群”。",
    "leadership": "创始人与长期领导人：伊亚德·阿格·加利（2012 年起，2017 年后任 JNIM 总埃米尔）；其余高层（如杰哈德·阿格·加里等）公开信息有限。",
    "ideology_goals": "安萨尔埃丁主张在马里推行沙里亚法、反对世俗国家与外国干预；与图阿雷格分离主义的“民族自决”路线根本不同——这是 2012 年与 MNLA 决裂的原因；其意识形态与 AQIM 的萨拉菲圣战主义一致，但对本地（图阿雷格、阿拉伯社区）身份政治的利用使其区别于外来圣战网络。",
    "geography": "历史活动范围：马里北部（基达尔、通布图方向）、马里—阿尔及利亚边境山区；2017 年后相关活动以 JNIM 名义覆盖马里北部与中部。",
    "force_estimates": "独立时期兵力缺乏可靠公开数据（数百人级别的估计不一）；并入 JNIM 后无法单独统计。",
    "tactics": "2012 年以占领与控制城镇为主（短期），2013 年后转为游击：伏击、IED、绑架与谈判筹码；并入 JNIM 后采用 JNIM 的“统治与治理”策略（设卡、征税、教法法庭）。",
    "relationships": "与 [[entity:person-iyad-ag-ghali|伊亚德·阿格·加利]]：创立关系（founded_by）；与 [[entity:actor-aqim|AQIM]]：网络关联；与 [[entity:actor-jnim|JNIM]]：组成关系（constituent_of，2017 年并入）；与 [[entity:actor-is-sahel|IS Sahel]]：敌对（圣战阵营竞争）。",
    "current_assessment": "当前状态：历史实体已并入 JNIM（2017 年起），不再作为独立组织活动；“安萨尔埃丁”名称在历史叙述与部分本地语境中仍被使用，但指挥上不存在独立实体。",
    "regional_impact": "安萨尔埃丁的演变是理解萨赫勒圣战“本地化”的关键案例：其将图阿雷格/阿拉伯社区的政治-宗教诉求接入基地组织全球网络，为后来 JNIM 的“多族群联盟”模式奠定基础。",
    "controversies_uncertainties": "主要争议与缺口：伊亚德·阿格·加利 2012 年与 MNLA 结盟/决裂的具体过程各方叙述不一；2017 年“并入 JNIM”是组织解散还是名义合并存在不同评估；2013 年后其在马里中部（富拉尼方向）的渗透程度缺乏独立核实。",
    "sources": "来源以联合国制裁委员会（QDe.159 等）、CTC、国际危机组织、ISS Africa 及可靠媒体为主；具体见 sources.json 与 evidence_records.json。"
  },
  "depth": "encyclopedia_full"
}

ency["actor-al-mourabitoun"] = {
  "sections": {
    "core_assessment": "穆拉比通组织（al-Mourabitoun，亦译“阿尔穆拉比通”）是 2013 年由[[entity:person-iyad-ag-ghali|伊亚德·阿格·加利]]的穆拉比通（“誓约者”）与莫赫塔尔·贝勒穆赫塔尔的“蒙面旅”合并而成的基地组织关联武装，主要活动于马里北部与萨赫勒中部；2015 年部分成员转向伊斯兰国阵营（成为大撒哈拉伊斯兰国 ISGS 的前身），2017 年主体并入 [[entity:actor-jnim|JNIM]]。",
    "name_and_translation": "规范中文名：穆拉比通组织；英文 al-Mourabitoun；历史前身包括“西非统一圣战运动（MOJWA/MUJAO）”与“蒙面旅（Les Signataires par le sang）”。本库以“穆拉比通组织”为规范名，保留历史别名。",
    "formation_background": "2012—2013 年，马里北部圣战阵营出现整合与分裂：MOJWA（2011 年从 AQIM 分裂）与贝勒穆赫塔尔领导的“蒙面旅”（2012 年成立）在 2013 年合并为穆拉比通，由贝勒穆赫塔尔任埃米尔、伊亚德·阿格·加利任副手；组织以马里—阿尔及利亚—尼日尔边境地带为基地，以绑架与劫掠闻名。",
    "history": "2013 年：成立（MOJWA+蒙面旅合并）；2013—2015 年：绑架人质获取赎金（多起西方人质事件）、袭击马里/尼日尔边境目标；2015 年：贝勒穆赫塔尔与伊亚德·阿格·加利决裂，部分成员（含萨赫拉维方向）转向伊斯兰国阵营——2015 年 5 月“西非统一圣战运动”遗留分支宣布效忠伊斯兰国，成为大撒哈拉伊斯兰国（ISGS）的源头；2015—2017 年：穆拉比通主体回归 AQIM 网络；2017 年 3 月：并入 JNIM（constituent_of）。",
    "structure": "穆拉比通在 2013—2015 年由贝勒穆赫塔尔（埃米尔）与伊亚德·阿格·加利（副手/马里分支）双头领导；分裂后主体（伊亚德系）保留名称并并入 JNIM，贝勒穆赫塔尔一支（自称“穆拉比通”残余）在阿尔及利亚—利比亚边境活动（2020 年贝勒穆赫塔尔被捕）。",
    "leadership": "联合创始人：莫赫塔尔·贝勒穆赫塔尔（2013—2015 年埃米尔，2020 年被利比亚方面逮捕）；伊亚德·阿格·加利（副手，后主导马里分支并任 JNIM 总埃米尔）。",
    "ideology_goals": "穆拉比通认同基地组织萨拉菲圣战主义，以绑架赎金、袭击“十字军”目标与圣战联盟为手段；其“合并与分裂”的历史反映了基地组织—伊斯兰国阵营竞争对萨赫勒圣战网络的切割。",
    "geography": "历史活动范围：马里北部与中部、尼日尔西部、阿尔及利亚—利比亚边境；2017 年后主体活动以 JNIM 名义覆盖马里中部与北部。",
    "force_estimates": "兵力缺乏可靠公开数据（数百人级别的估计不一）；绑架赎金（单起数百万欧元）是其财政支柱。",
    "tactics": "绑架与赎金谈判（标志性手段）、伏击、IED、跨境机动；贝勒穆赫塔尔以“图阿雷格—阿拉伯混合突击”著称。",
    "relationships": "与 [[entity:actor-jnim|JNIM]]：组成关系（constituent_of，2017 年并入）；与 [[entity:actor-aqim|AQIM]]：网络关联（分裂前）；与 [[entity:actor-is-sahel|IS Sahel]]：历史渊源（2015 年部分成员转向 ISGS，rel-is-mourabitoun-splinter）；与 [[entity:person-iyad-ag-ghali|伊亚德·阿格·加利]]：领导关系（历史）。",
    "current_assessment": "当前状态：主体已并入 JNIM（2017 年起），不再作为独立组织活动；“穆拉比通”名称保留于历史叙述与 JNIM 内部支系表述；贝勒穆赫塔尔一支（被捕后）已基本消亡。",
    "regional_impact": "穆拉比通的历史（MOJWA—蒙面旅合并—ISGS 分裂—JNIM 并入）浓缩了萨赫勒圣战网络的“合并—分裂”动力学，是理解 JNIM 与 IS Sahel 竞争起源的关键案例。",
    "controversies_uncertainties": "主要争议与缺口：2015 年分裂时各支的归属（谁并入 ISGS、谁留 AQIM）各方叙述不一；贝勒穆赫塔尔的被捕细节与当前下落存在多种说法；绑架赎金总额无权威统计。",
    "sources": "来源以联合国制裁委员会、CTC、国际危机组织、ISS Africa 及可靠媒体为主；具体见 sources.json 与 evidence_records.json。"
  },
  "depth": "encyclopedia_full"
}

ency["actor-katiba-macina"] = {
  "sections": {
    "core_assessment": "马西纳旅（Katiba Macina）是 2015 年前后由[[entity:person-amadou-koufa|阿马杜·库法]]在马里中部马西纳地区组建的圣战武装，以动员富拉尼牧民社区著称，2017 年并入 [[entity:actor-jnim|JNIM]] 并成为其在中马里扩张的核心力量；2019 年库法被法军宣布击毙后，马西纳旅由继任指挥官继续作战，2024—2026 年仍主导马里中部与布基纳法索方向的袭击。",
    "name_and_translation": "规范中文名：马西纳旅（Katiba Macina）；英文 Katiba Macina / Macina Liberation Front（FLM）；阿拉伯语 كتيبة ماسينا。本库以“马西纳旅”为规范名。",
    "formation_background": "2015 年前后，富拉尼族传教士阿马杜·库法在马里中部莫普提地区（马西纳）发动圣战动员：以“保护富拉尼牧民免受武装团伙与国家压迫”为叙事，结合萨拉菲圣战意识形态，吸纳因生计冲突与治理缺位而边缘化的牧区青年；其组织以“卡提巴”（营级单位）形式运作，故名马西纳旅。",
    "history": "2015 年：组建并开始袭击（针对政府军、多贡社区武装）；2016—2017 年：在马里中部扩张，2017 年并入 JNIM（constituent_of）；2017—2019 年：作为 JNIM 主力在马里中部与布基纳法索北部作战；2019 年 11 月：阿马杜·库法被法军特种部队击毙（JNIM 未正式确认）；2019—2026 年：继任指挥下继续活动，参与 2025 年巴马科封锁、2026 年跨区域攻势与贝宁北部袭击（JNIM 框架内）。",
    "structure": "马西纳旅按“卡提巴”编组、设区域指挥官；2019 年库法死后指挥层更替（公开资料指向继任者但未获统一确认）；其动员网络依托富拉尼社区的家庭、牧场与清真寺网络，兼具武装与“宣教—治理”功能。",
    "leadership": "创始人：阿马杜·库法（2015—2019 年，2019 年 11 月被宣布击毙）；继任领导层缺乏公开确认。",
    "ideology_goals": "马西纳旅将富拉尼牧民生计诉求（土地、放牧权、反歧视）与圣战叙事结合，主张以沙里亚秩序替代“压迫性国家”；组织否认自身是“族群武装”，但动员基础以富拉尼社区为主——不得把特定族群整体等同于该组织。",
    "geography": "活动范围：马里中部（莫普提大区：吉雷、杜恩扎、滕内库等）、布基纳法索北部（苏姆、塞诺方向）；2025—2026 年经 JNIM 框架向贝宁北部渗透。",
    "force_estimates": "兵力缺乏可靠公开数据（数百至上千人的估计不一）；其影响力通过控制中部农村通道与征税体现。",
    "tactics": "袭击军事据点与多贡民兵、伏击车队、IED、封锁道路与“征税”；对富拉尼社区的动员采用布道、婚姻网络与强制结合；2025—2026 年参与 JNIM 的“经济绞杀”战术（燃料车队拦截）。",
    "relationships": "与 [[entity:person-amadou-koufa|阿马杜·库法]]：创立关系（founded_by）；与 [[entity:actor-jnim|JNIM]]：组成关系（constituent_of）；与 [[entity:person-iyad-ag-ghali|伊亚德·阿格·加利]]：JNIM 网络内领导关系；与多贡社区武装：敌对。",
    "current_assessment": "当前状态：活跃，以 JNIM 马西纳旅名义持续作战（截至 2026 年年中）；指挥层不透明，但组织在马里中部与布基纳法索北部的活动保持高位。",
    "regional_impact": "马西纳旅是中马里冲突“武装化、族群化、圣战化交织”的核心载体：其动员逻辑与多贡/多佐民兵的对抗塑造了 2018 年以来中部大屠杀与反屠杀循环，并推动 JNIM 向布基纳法索与贝宁的扩张。",
    "controversies_uncertainties": "主要争议与缺口：库法死亡时间与继任者身份无独立确认；组织与富拉尼社区关系的性质（“保护” vs “强制”）存在不同评估；兵力与伤亡不透明。",
    "sources": "来源以联合国制裁委员会、CTC、ACLED、国际危机组织、ISS Africa 及可靠媒体为主；具体见 sources.json 与 evidence_records.json。"
  },
  "depth": "encyclopedia_full"
}

ency["actor-aqim"] = {
  "sections": {
    "core_assessment": "伊斯兰马格里布基地组织（AQIM）是基地组织在北非与萨赫勒的核心分支：起源于 1990 年代阿尔及利亚内战的武装伊斯兰组织，2007 年更名 AQIM 并效忠基地组织；2017 年其萨赫勒分支并入 [[entity:actor-jnim|JNIM]] 后，AQIM 以“母体—联盟”身份存续，对马格里布与萨赫勒圣战网络具有旗帜性影响。",
    "name_and_translation": "规范中文名：伊斯兰马格里布基地组织（AQIM）；英文 Al-Qaeda in the Islamic Maghreb；法文 Al-Qaïda au Maghreb islamique；前身“萨拉菲宣教与战斗团”（GSPC）。",
    "formation_background": "1998 年阿尔及利亚“武装伊斯兰集团”（GIA）分裂出 GSPC；2006—2007 年 GSPC 宣布效忠基地组织并更名 AQIM，获得基地核心的意识形态与资源背书；其传统基地在阿尔及利亚卡比利亚山区，2003 年后向萨赫勒（马里北部、尼日尔）扩展人质经济与武装网络。",
    "history": "2007 年：更名与效忠；2007—2012 年：阿尔及利亚本土袭击与人质绑架；2012—2013 年：马里北部危机中 AQIM 分支参与占领与“伊斯兰统治”；2013 年：法军干预后撤入山区；2013—2017 年：萨赫勒分支（含马西纳旅前身）壮大，AQIM 重心南移；2017 年 3 月：萨赫勒分支并入 JNIM（伊亚德·阿格·加利领导），AQIM 保留母体身份；2020 年 6 月：埃米尔阿卜杜勒马莱克·德鲁克德尔被法军击毙；2020—2026 年：继任领导层不透明，阿尔及利亚方向低烈度活动。",
    "structure": "AQIM 为“中央—区域”网络：阿尔及利亚本土核心（卡比利亚）与萨赫勒各分支；2017 年后萨赫勒作战力量实质由 JNIM 统辖，AQIM 名称保留于效忠链条与联盟架构——其与 JNIM 的关系更接近“母体联盟”而非上下级指挥。",
    "leadership": "历任埃米尔：阿卜杜勒马莱克·德鲁克德尔（2004—2020 年，2020 年 6 月被法军击毙）；继任者公开信息有限（报道指向阿布·乌贝达·优素福·阿纳比等，未获统一确认）。",
    "ideology_goals": "AQIM 认同基地组织全球圣战议程，主张在“马格里布与萨赫勒”建立沙里亚秩序、驱逐外国干预；其对本地部落与族群网络的利用（图阿雷格、阿拉伯、富拉尼）体现“全球意识形态+本地动员”的融合模式。",
    "geography": "活动范围：阿尔及利亚北部（卡比利亚、撒哈拉）、马里北部与中萨赫勒（经 JNIM）、与利比亚、突尼斯、尼日尔的跨境地带。",
    "force_estimates": "兵力缺乏可靠公开数据（数百至数千人的估计不一）；2017 年后其影响力主要通过 JNIM 网络体现，本土核心规模有限。",
    "tactics": "本土以伏击军警、IED 与人质绑架为主；萨赫勒方向经 JNIM 采用“统治—征税—游击”混合模式；人质赎金（长期财政支柱）在萨赫勒被多次使用。",
    "relationships": "与 [[entity:actor-jnim|JNIM]]：组成/母体关系（JNIM 为 constituent_of AQIM 网络，2017 年萨赫勒分支并入）；与 [[entity:actor-al-qaida|基地组织]]：隶属（pledged_allegiance_to 链条）；与 [[entity:actor-is-sahel|IS Sahel]]：敌对（圣战阵营竞争）；与 [[entity:actor-ansar-eddine|安萨尔埃丁]]、[[entity:actor-al-mourabitoun|穆拉比通]]：历史网络关联。",
    "current_assessment": "当前状态：以 JNIM 为萨赫勒实施主体、本土低烈度存在（截至 2026 年年中）。AQIM 作为基地组织马格里布—萨赫勒网络的旗帜存续，实际作战与扩张由 JNIM 承担。",
    "regional_impact": "AQIM 的历史（GSPC—AQIM—JNIM）定义了萨赫勒圣战的组织谱系，其“本地化分支”模式被 JNIM 继承并放大，对北非与萨赫勒安全格局具有持续影响。",
    "controversies_uncertainties": "主要缺口：继任领导层身份与阿尔及利亚本土活动规模缺乏可靠资料；AQIM 与 JNIM 的指挥关系（母体 vs 平等联盟）存在不同评估；人质赎金与财政数据不透明。",
    "sources": "来源以联合国制裁委员会、CTC、国际危机组织、ISS Africa 及可靠媒体为主；具体见 sources.json 与 evidence_records.json。"
  },
  "depth": "encyclopedia_full"
}

ency["actor-is-sahel"] = {
  "sections": {
    "core_assessment": "伊斯兰国萨赫勒省（IS Sahel/ISSP）是伊斯兰国在中萨赫勒的分支，前身为 2015 年成立的大撒哈拉伊斯兰国（ISGS），2022 年更名；2023 年萨赫拉维死后领导层不透明，但组织 2025—2026 年显著扩张——公开认领尼日尔—尼日利亚边境袭击、2026 年 1 月袭击尼亚美机场、3 月袭击塔瓦，并首次与 [[entity:actor-jnim|JNIM]] 在尼日尔与尼日利亚境内公开交火（2026 年 4 月），成为萨赫勒最活跃的伊斯兰国分支。",
    "name_and_translation": "规范中文名：伊斯兰国萨赫勒省（IS Sahel/ISSP）；英文 Islamic State in the Sahel Province；前称大撒哈拉伊斯兰国（ISGS，Islamic State in the Greater Sahara）；部分报告亦称“萨赫勒伊斯兰国”（ISSP 缩写）。",
    "formation_background": "2015 年，马里北部圣战分子阿德南·阿布·瓦利德·萨赫拉维（Adnan Abu Walid al-Sahrawi）脱离 JNIM 前身阵营（穆拉比通/贝勒穆赫塔尔支系），组建 ISGS 并向伊斯兰国效忠；2016—2019 年与 JNIM 争夺马里—布基纳法索—尼日尔边境的控制权，2019 年被 JNIM 逐出布基纳法索东部后转向尼日尔方向扩张。",
    "history": "2015 年：ISGS 成立与效忠；2016—2019 年：与 JNIM 竞争（2019 年阿列尔交火为“萨赫勒例外”终结标志）；2020 年：被逐出布基纳法索东部、转战尼日尔；2021 年：萨赫拉维被法军击毙；2022 年：更名 ISSP；2023—2024 年：向尼日尔南部扩张、袭击升级；2025 年：公开认领尼日尔—尼日利亚边境袭击；2026 年 1 月 29 日：袭击尼亚美国际机场与空军基地 101（约 30 名武装分子+无人机）；2026 年 3 月：袭击塔瓦军事设施；2026 年 4 月：与 JNIM 首次公开交火。",
    "structure": "按“行省”逻辑设区域指挥（马里—布基纳法索方向、尼日尔方向）；2021 年萨赫拉维死后领导层信息有限；组织以农村游击、税卡、宣教—治理结合运作，2025—2026 年“宣示性袭击”（机场、军事设施）明显增加。",
    "leadership": "创始人：阿德南·阿布·瓦利德·萨赫拉维（2015—2021 年，2021 年被法军击毙）；继任领导层缺乏公开确认（报道指向继任者但未核实）。",
    "ideology_goals": "ISSP 认同伊斯兰国“哈里发国”叙事与全球行省体系，主张以沙里亚统治取代“叛教政权”；与 JNIM 的根本分歧在于效忠对象（伊斯兰国 vs 基地组织）与“叛教”界定（是否滥杀穆斯林平民）。",
    "geography": "活动范围：马里中东部、布基纳法索东部、尼日尔西部（蒂拉贝里、多索、塔瓦）与南部边境；2025—2026 年向尼日利亚西北、贝宁北部渗透。",
    "force_estimates": "兵力缺乏可靠公开数据（数百至数千人的估计不一）；2026 年 1 月尼亚美机场袭击动用约 30 名武装分子与无人机，显示精锐突击能力；2025—2026 年边境地带袭击同比大幅上升（ACLED 记录 86%—90% 增长）。",
    "tactics": "高调袭击战略目标（机场、空军基地、军事设施）、摩托车机动、IED、武装无人机（2026 年首次在尼亚美使用）；对农村实施“存在宣示”与“宣示性认领”（通过伊斯兰国宣传机构公开袭击）。",
    "relationships": "对 [[entity:actor-islamic-state|伊斯兰国]]：宣誓效忠（pledged_allegiance_to）；对 [[entity:actor-jnim|JNIM]]：敌对与竞争（hostile_to，2026 年 4 月公开交火）；对 [[entity:actor-al-mourabitoun|穆拉比通]]：历史渊源（2015 年分裂，rel-is-mourabitoun-splinter）；与拉库拉瓦等南部边境网络：部分报告支持的联系。",
    "current_assessment": "当前状态：扩张且更具进攻性（截至 2026 年年中）。ISSP 通过机场/军事设施袭击与南部边境渗透扩大影响，与 JNIM 的竞争进入公开交火阶段，是萨赫勒最活跃的伊斯兰国分支。",
    "regional_impact": "ISSP 的高调袭击（2026 年 1 月尼亚美）为萨赫勒恐怖主义设定新标杆，迫使 AES 国家强化首都防空与军事设施安保；其向尼日利亚、贝宁方向的扩张直接关联西非沿海风险。",
    "controversies_uncertainties": "主要缺口：现任领导层身份与组织内部结构无可靠公开资料；与伊斯兰国核心的实质联络程度不明；控制区边界（与 JNIM 动态划分）缺乏权威制图；袭击数据口径差异大。",
    "sources": "来源以 ACLED、CTC、国际危机组织、ISS Africa、DefenceWeb 及可靠媒体为主；具体见 sources.json 与 evidence_records.json。"
  },
  "depth": "encyclopedia_full"
}

# =====================================================================
# STANDARD: Al-Qaeda upgrade + 10 new entities
# =====================================================================
std = {}

std["actor-al-qaida"] = {
  "sections": {
    "core_assessment": "基地组织（Al-Qaeda）是 1988 年前后由奥萨马·本·拉登等创建的跨国圣战网络，以“全球圣战”议程著称；在非洲，其影响力主要通过地方分支与联盟体现——马格里布方向的 [[entity:actor-aqim|AQIM]]、萨赫勒方向的 [[entity:actor-jnim|JNIM]]（2017 年成立并公开宣誓效忠）等。基地核心对非洲分支多为“品牌+意识形态+有限资源”的松散关联，不得把所有地方分支行为直接归因于核心领导层命令。",
    "name_and_translation": "规范中文名：基地组织；英文 Al-Qaeda；阿拉伯语 القاعدة（“基地”）。本库以“基地组织”为规范名。",
    "formation_background": "组织起源于 1980 年代阿富汗抗苏战争中的阿拉伯志愿者网络，1988 年本·拉登正式组建；1996 年迁苏丹、1998 年迁阿富汗并宣布“反美圣战”，2001 年 9·11 袭击后成为全球头号反恐目标；核心领导层在阿富汗—巴基斯坦边境被打散，2011 年本·拉登被击毙、2022 年扎瓦希里被击毙后，中央指挥能力进一步弱化。",
    "history": "2001—2011 年：核心受创但全球网络存续；2011—2014 年：“阿拉伯之春”后马格里布/萨赫勒/也门分支扩张；2014 年：伊斯兰国崛起引发“基地 vs 伊斯兰国”全球竞争（部分分支转投伊斯兰国）；2017 年：JNIM 成立并效忠基地组织（萨赫勒最重要基地关联联盟）；2019—2026 年：基地核心持续被压制，非洲分支（JNIM、AQIM）成为其最活跃资产；2025—2026 年：JNIM 在中萨赫勒扩张（巴马科封锁、跨区域攻势），基地品牌的区域影响主要经此体现。",
    "structure": "基地组织为“中央+地方分支/联盟”的松散网络：核心（阿富汗—巴基斯坦方向）提供意识形态与品牌背书，分支（AQIM、JNIM、基地也门分支、索马里青年党等）拥有实质自主权；分支与核心的关系以“宣誓效忠”（bay'ah）维系，多为名义而非指挥关系。",
    "leadership": "历任最高领袖：奥萨马·本·拉登（1988—2011 年）；艾曼·扎瓦希里（2011—2022 年）；2022 年后继任者（赛义夫·阿德尔等报道）未获公开确认，核心领导层信息极少。",
    "ideology_goals": "基地组织主张以武装圣战推翻“叛教政权”、驱逐西方影响、建立沙里亚统治；其全球议程与分支的本地议程（如 JNIM 的萨赫勒治理、青年党的索马里建国）通过“效忠—授权”框架衔接。",
    "geography": "全球网络：阿富汗—巴基斯坦（核心历史基地）、也门、索马里（青年党）、马格里布—萨赫勒（AQIM/JNIM）、南亚（基地南亚分支）等。",
    "force_estimates": "核心兵力无法估计（核心网络仅剩少量领导与训练层）；整体威胁主要经分支体现——萨赫勒 JNIM 为当前最活跃资产，评估其行动能力比统计“基地兵力”更有意义。",
    "tactics": "核心长期以“指引与激励”角色存在（宣传、圣战指导）；实际行动能力集中于分支：JNIM 的“统治—征税—游击”、青年党的叛乱战争、AQIM 的绑架与伏击。",
    "relationships": "与 [[entity:actor-jnim|JNIM]]：效忠—联盟（2017 年 bay'ah）；与 [[entity:actor-aqim|AQIM]]：隶属分支；与 [[entity:actor-islamic-state|伊斯兰国]]：全球竞争与敌对；与 [[entity:actor-iswap|ISWAP]] 等伊斯兰国分支：敌对。",
    "current_assessment": "当前状态（截至 2026 年年中）：核心弱化、网络存续。基地组织中央的指挥与资源能力大幅下降，其全球影响力主要经非洲与亚洲分支（尤其 JNIM）体现；对非洲安全的影响通过“意识形态+品牌”间接传导。",
    "regional_impact": "基地组织对非洲安全格局的影响：一是提供圣战意识形态与“合法化”框架（JNIM、青年党等）；二是与伊斯兰国的全球竞争驱动非洲圣战内部的分化与暴力（萨赫勒 JNIM—ISSP 交火）；三是其“本地分支”模式（JNIM）成为萨赫勒最持久的叛乱结构。",
    "controversies_uncertainties": "主要缺口：2022 年后核心领导层身份无公开确认；核心与分支（尤其 JNIM）的实质指挥/资源联系程度存在不同评估；把分支行为归因于“基地组织命令”常被高估——多数行动由分支自主决策。",
    "sources": "来源以联合国制裁委员会、CTC、国际危机组织、ISS Africa 及可靠媒体为主；具体见 sources.json 与 evidence_records.json。"
  },
  "depth": "standard"
}

# ---- 10 new entities ----
def new_entity(eid, zh, en, typ, pri, name_zh, sections, depth="standard", slug=None, country_ids=None, region_ids=None, aliases=None, importance="L2"):
    return {"entity_id": eid, "entity_type": typ, "primary_type": pri, "secondary_types": [],
            "slug": slug or eid.replace("actor-", "").replace("person-", ""),
            "name_zh": name_zh, "name_en": en, "acronym": "", "native_name": "",
            "aliases": aliases or [], "historical_names": [],
            "importance_level": importance, "short_description": zh,
            "current_status": "active", "primary_category": "state_security_force" if typ == "organization" else "insurgent_group",
            "tags": [], "region_ids": region_ids or ["region-central-sahel"],
            "country_ids": country_ids or [], "confidence": "medium_high",
            "temporal_sensitive": True, "disputed": False, "source_refs": ["un-jnim-2018"],
            "freshness_status": "current", "claim_valid_as_of": "2026-06-30",
            "current_status_verified_at": REVIEWED, "record_reviewed_at": REVIEWED,
            "record_created_at": REVIEWED, "record_updated_at": REVIEWED,
            "verification_status": "partially_verified", "freshness_reviewed_by": "i3b",
            "importance_review_status": "pending", "importance_score": 60,
            "importance_reviewed_at": REVIEWED, "importance_reasons": [zh]}

# --- Mali / Burkina ---
std["actor-mali-army"] = {
  "sections": {
    "core_assessment": "马里武装部队（FAMa）是马里反叛乱的主力国家军队，2022 年法国与联合国部队撤离后承担全部地面任务，依赖俄罗斯非洲军团（前瓦格纳）支援；2025—2026 年因 JNIM 战线南移西移与首都供应线压力而“过度拉伸”。",
    "name_and_translation": "规范中文名：马里武装部队（FAMa）；法文 Forces Armées Maliennes（FAMa）。",
    "formation_background": "马里独立（1960）后军队历经多次政变（1968、1991、2012、2020、2021），2012 年北部危机暴露其战力崩溃；2013 年起在法国/联合国支援下重建，2020—2021 年政变后转向“主权主义”路线并驱逐外国部队。",
    "history": "2012 年：北部崩溃与政变；2013—2022 年：法国/联合国支援下的重建与反叛乱；2022 年：二次政变、法国撤军；2023 年：收复基达尔（北部转折）；2023—2024 年：俄罗斯非洲军团扩员；2025 年：JNIM 南移、首都燃料封锁、8 月未遂政变；2026 年 4 月：国防部长遇袭、指挥链重组。",
    "structure": "陆军为主（特种部队、伞兵、装甲），配空军（有限）与宪兵；与多佐民兵、俄罗斯非洲军团协同；2025—2026 年调整军事指挥链以应对南部威胁。",
    "leadership": "最高指挥：总统/过渡总统（阿西米·戈伊塔上校）；国防部长萨迪奥·卡马拉 2026 年 4 月 25 日遇袭身亡（时任）。",
    "geography": "部署：北部三区（FLA 方向）、中部莫普提（圣战）、西部卡耶斯与南部锡卡索（2025—2026 年新战线）、巴马科周边与供应走廊。",
    "force_estimates": "兵力缺乏可靠公开数据（数万人的估计不一）；多线作战被评估为“过度拉伸”。",
    "current_assessment": "当前状态（截至 2026 年年中）：多线承压、依赖外部支援。FAMa 在“击退”层面有效，但无法阻止 JNIM 的南部扩散与“锁喉”战术；2025—2026 年未遂政变显示内部不稳。",
    "controversies_uncertainties": "主要争议：与俄罗斯人员的联合行动及暴行指控；空袭与地面行动致平民伤亡；兵力与损失不透明；2026 年 4 月事件后指挥层调整的成效不明。",
    "sources": "来源以联合国文件、ISS Africa、国际危机组织、COFACE 及可靠媒体为主；具体见 sources.json 与 evidence_records.json。"
  },
  "depth": "standard"
}

std["actor-burkina-army"] = {
  "sections": {
    "core_assessment": "布基纳法索武装部队是特拉奥雷军政府（2022 年 9 月政变上台）反叛乱的主力，与数万名国土防卫志愿军（VDP）协同；2025—2026 年在 JNIM 控制/争夺约六成领土的背景下，以“城镇防御+清剿”模式作战，效果有限。",
    "name_and_translation": "规范中文名：布基纳法索武装部队；法文 Forces Armées Nationales du Burkina Faso。",
    "formation_background": "布基纳法索军队在 2015 年前被视为区域稳定典范（孔波雷长期执政后 2014 年人民起义），2015 年圣战袭击入境后转入反叛乱；2022 年两次政变（1 月达米巴、9 月特拉奥雷）反映军队内部对反恐失败的不满。",
    "history": "2015—2020 年：圣战扩张与军队被动；2022 年：两度政变、特拉奥雷上台；2023—2024 年：大规模动员 VDP、反恐战果有限；2025 年：吉博围困与袭击（5 月 100+ 死亡、约 90 名士兵苏姆省伏击）；2026 年：2 月 JNIM 持续一周协同进攻、政党解散、安全事件 +40%。",
    "structure": "陆空一体（陆军主力、有限空军）、宪兵；与 VDP 民兵、俄罗斯安全人员协同；2025—2026 年宣称“数百名武装分子被消灭”但缺乏独立核实。",
    "leadership": "最高指挥：总统伊卜拉欣·特拉奥雷上尉（2022 年 9 月起）；国防部长塞莱斯廷·辛波雷（2026 年任职）。",
    "geography": "部署：北部（苏姆、乌达兰、塞诺）、东部（古尔马、塔波阿）、西部（布克莱迪穆洪）、首都瓦加杜古及周边。",
    "force_estimates": "兵力缺乏可靠公开数据（数万人的估计不一）；VDP 补充人力但训练与纪律问题突出。",
    "current_assessment": "当前状态（截至 2026 年年中）：城镇防御、农村失守。政府军与 VDP 控制瓦加杜古与部分省会，农村大部被 JNIM 争夺/控制；军队暴行（针对富拉尼社区）加剧招募循环。",
    "controversies_uncertainties": "主要争议：VDP 与军队的暴行记录；强制征召（2025 年 4 月动员）；“金矿换保护”指控；伤亡与兵力不透明。",
    "sources": "来源以联合国文件、CRS 国会报告、国际危机组织、ISS Africa、ACLED 及可靠媒体为主；具体见 sources.json 与 evidence_records.json。"
  },
  "depth": "standard"
}

std["actor-vdp"] = {
  "sections": {
    "core_assessment": "国土防卫志愿军（VDP，Volontaires pour la Défense de la Patrie）是布基纳法索政府动员的数万名地方民兵，2020 年创立、特拉奥雷政权（2022 年后）大规模扩编，充当正规军辅助与乡村防线；其训练不足、纪律涣散与暴行记录使其既是反恐资产也是冲突恶化因素。",
    "name_and_translation": "规范中文名：国土防卫志愿军（VDP）；法文 Volontaires pour la Défense de la Patrie。",
    "formation_background": "2020 年 1 月立法创设，2019—2020 年圣战扩张背景下作为“社区自卫+政府授权”民兵引入；2022 年特拉奥雷上台后大规模招募（数万人），2025 年 4 月宣布全面动员（含被批评的强制征召）。",
    "history": "2020 年：创设；2021—2023 年：扩编与参与清剿；2024 年：动员争议、暴行记录增多；2025 年：全国动员、吉博等围困中承担补给与防线任务；2026 年：继续扩编，与军队协同。",
    "structure": "按省/区组建志愿分队，受军队指挥协调；成员多为失业青年与农民（含被指强制征召者）；武器由军队配发（口径不一）。",
    "leadership": "无独立指挥体系，接受军队/省长协调；具体领导以地方为单位。",
    "geography": "部署：北部、东部、西部各战区乡村地带，填补军队据点间隙。",
    "force_estimates": "人数无官方确认（“数万”为常见估计）；训练与装备严重不足。",
    "current_assessment": "当前状态（截至 2026 年年中）：活跃、持续扩编。VDP 在乡村防线与补给护送中作用明显，但其暴行（被指针对富拉尼社区的集体惩罚）与武装组织袭击互相推动，构成“安全困境”循环。",
    "controversies_uncertainties": "主要争议：强制征召与人权暴行（国际组织多份记录）；与军队的指挥责任划分；真实人数与伤亡不透明。",
    "sources": "来源以国际危机组织、CRS 国会报告、联合国机构及可靠媒体为主；具体见 sources.json 与 evidence_records.json。"
  },
  "depth": "standard"
}

# --- Cameroon ---
std["actor-cameroon-bir"] = {
  "sections": {
    "core_assessment": "快速干预营（BIR，Bataillon d'Intervention Rapide）是喀麦隆总统直属的精锐军事力量，承担远北反恐（JAS/ISWAP）与英语区平乱双重任务，是喀麦隆安全力量中机动性与战斗力最强的单位。",
    "name_and_translation": "规范中文名：快速干预营（BIR）；法文 Bataillon d'Intervention Rapide。",
    "formation_background": "2001 年前后组建，作为总统卫队性质的精锐快速反应部队，早期承担反盗猎与边境任务；2014 年博科圣地跨境袭击后成为远北反恐主力；2017 年英语区冲突后同时投入平乱。",
    "history": "2014—2016 年：远北反恐（多次击退袭击）；2017—2020 年：英语区清剿主力；2021—2024 年：远北“阿尔法行动”哨所体系、英语区持续作战；2025—2026 年：弗雷凯特（2026-07）等袭击被击退，英语区清剿继续。",
    "structure": "多个快速干预营编组（BIR 序列），配直升机支援与特种训练；受总统与军方高层直接指挥。",
    "leadership": "指挥官序列不透明（属总统直属体系）；最高指挥为总统（保罗·比亚）。",
    "geography": "部署：远北（马约-萨瓦、马约-察纳加、洛贡-沙里）、英语区（西北/西南两省）、首都雅温得（安保）。",
    "force_estimates": "兵力缺乏公开数据（数千人的估计不一）；为喀麦隆最精锐单位。",
    "current_assessment": "当前状态（截至 2026 年年中）：远北防御有效但未消除威胁；英语区清剿与分离武装形成拉锯。",
    "controversies_uncertainties": "主要争议：英语区行动中被指侵犯人权（搜查、逮捕）；远北袭击的伤亡口径不一；兵力与行动细节不透明。",
    "sources": "来源以国际危机组织、regionalert 安全评估、喀麦隆官方媒体及可靠报道为主；具体见 sources.json 与 evidence_records.json。"
  },
  "depth": "standard"
}

std["actor-ambazonia-network"] = {
  "sections": {
    "core_assessment": "安巴佐尼亚武装网络是喀麦隆西北/西南英语区分离主义武装团体的统称（非单一组织）：2017 年起多个武装团体在“安巴佐尼亚”名义下与政府军作战，实施“幽灵镇”封锁、IED 与绑架；各团体指挥独立、目标不尽一致，不得合并为统一组织。",
    "name_and_translation": "规范中文名：安巴佐尼亚武装网络；英文 Ambazonia separatist armed groups；相关政治实体为“南喀麦隆/安巴佐尼亚”分离运动。",
    "formation_background": "2016 年英语区律师与教师抗议法语化政策，2017 年升级为武装分离主义；多个武装团体（自称“安巴佐尼亚防卫部队”等）在西北/西南两省出现，目标为建立独立“安巴佐尼亚国”。",
    "history": "2017 年：武装冲突爆发；2018—2021 年：战斗常态化（“幽灵镇”周一封锁、学校关闭）；2022—2024 年：冲突低烈度化但未解决（6500+ 死亡、58 万流离失所）；2025—2026 年：教皇访问期间部分派系停火（2026-04），随后冲突再起（2026 年 5 月多地交火、袭击法语区西部）。",
    "structure": "多派系并存：自称“安巴佐尼亚临时政府”相关武装与地方指挥网络各自为战；2026 年 3 月最高法院撤销 10 名分离领导人判决（含西苏库·阿尤克·塔贝）后领导层地位存争议；各派系有地盘与资源竞争。",
    "leadership": "政治名义：西苏库·阿尤克·塔贝等（被拘押/重审中）；武装指挥分散、无统一领导。",
    "geography": "活动范围：西北（巴门达、杜巴、恩多普）与西南（布埃亚、昆巴、马姆费）两省，偶发渗透法语区西部（2026-05 库门巴）。",
    "force_estimates": "总人数缺乏可靠数据（数千人级别的估计不一）；以轻武器、IED 与绑架为手段。",
    "current_assessment": "当前状态（截至 2026 年年中）：低烈度持续冲突。部分派系释放谈判信号（教皇斡旋），但政权（2026-04 副总统任命）与分离阵营互信极低，武装袭击与“幽灵镇”封锁继续。",
    "controversies_uncertainties": "主要争议：各派系身份与指挥结构不透明；绑架与勒索的“政治性” vs “经济性”存在不同评估；政府军与武装团体的暴行责任归属。",
    "sources": "来源以国际危机组织、联合国 OCHA、regionalert 安全评估及可靠媒体为主；具体见 sources.json 与 evidence_records.json。"
  },
  "depth": "standard"
}

# --- Ethiopia ---
std["actor-endf"] = {
  "sections": {
    "core_assessment": "埃塞俄比亚国防军（ENDF）是埃塞俄比亚联邦军队，2020—2022 年提格雷战争后同时在提格雷（对抗 TDF）、阿姆哈拉（对抗 Fano）、奥罗米亚（对抗 OLA）三线作战；2026 年因燃料短缺与多线牵制而处于战略承压状态。",
    "name_and_translation": "规范中文名：埃塞俄比亚国防军（ENDF）；英文 Ethiopian National Defense Force。",
    "formation_background": "ENDF 源于 1991 年推翻军政府后组建的联邦军队（整合提格雷人民解放阵线 TPLF 主导时期的力量）；2018 年阿比·艾哈迈德执政后进行重组（“军改”削弱提格雷系军官）；2020—2022 年提格雷战争重塑其作战形态（无人机大规模使用）。",
    "history": "2020—2022 年：提格雷战争（11 月《比勒陀利亚协议》结束）；2023 年：阿姆哈拉冲突爆发（8 月）、奥罗米亚 OLA 冲突持续；2024—2025 年：多线作战；2026 年：与 TPLF 军事对峙（2 月）、阿姆哈拉反攻（3 月约 2 万人）、TPLF 重建战前政府（5 月）。",
    "structure": "陆军为主（多军区部署），2020 年后大量使用无人机（含采购与自制）；2023 年解散阿姆哈拉特别部队后该地区反叛乱由 ENDF 承担；受国防部与总参谋部指挥。",
    "leadership": "最高指挥：总理阿比·艾哈迈德（兼任）；总参谋长人选随政治调整（公开信息有限）。",
    "geography": "部署：提格雷（TDF 对峙）、阿姆哈拉（Fano 反叛乱）、奥罗米亚（OLA）、索马里/阿法尔（吉布提走廊）、与厄立特里亚/苏丹边境。",
    "force_estimates": "兵力缺乏可靠公开数据（数十万人的历史估计不可靠）；多线部署致重点方向兵力不足。",
    "current_assessment": "当前状态（截至 2026 年年中）：三线承压、优势受限。ENDF 在阿姆哈拉反攻（3—5 月）中提高对 Fano 行动频率但未压制其活动；提格雷方向实质丧失联邦控制；燃料短缺（伊朗战争影响）制约大规模攻势。",
    "controversies_uncertainties": "主要争议：无人机袭击致平民伤亡（阿姆哈拉被指集体惩罚）；提格雷战争的战争罪指控（双方）；兵力与损失不透明。",
    "sources": "来源以 CFR 冲突追踪、Critical Threats/ACLED、联合国机构及可靠媒体为主；具体见 sources.json 与 evidence_records.json。"
  },
  "depth": "standard"
}

std["actor-fano"] = {
  "sections": {
    "core_assessment": "Fano 相关力量是埃塞俄比亚阿姆哈拉地区多派系民兵的统称（非单一指挥组织）：2023 年 8 月起与联邦军队（ENDF）交战，2026 年 3—5 月进入最活跃阶段；最强派系为“阿姆哈拉 Fano 全国运动”，组织在阿姆哈拉农村建立有限治理结构，并抵制 2026 年 6 月大选。",
    "name_and_translation": "规范中文名：Fano 相关力量（法诺）；英文 Fano militias / Amhara Fano；“Fano”源于阿姆哈拉语爱国者/志愿者的传统称呼。",
    "formation_background": "Fano 一词用于阿姆哈拉地区的地方民兵传统；2023 年 4 月联邦政府解散阿姆哈拉特别部队后，部分前成员与地方武装联合组成反政府民兵，2023 年 8 月爆发全面冲突；动因包括对中央集权、2022 年提格雷停火（未顾及阿姆哈拉领土诉求）与解散特别部队的不满。",
    "history": "2023 年 8 月：冲突爆发（全国多线）；2023—2024 年：Fano 控制大片农村、政府军控城镇；2025 年：冲突持续（ACLED 记录 2025-03 至 2026-03 阿姆哈拉 1485 起事件、5129 人死亡）；2026 年 3 月：ENDF 反攻（约 2 万人）；2026 年 3—5 月：Fano 行动升级（5 月为最活跃月）、袭击选举设施；2026 年 5 月：8 个选区因不安全无法举行选举。",
    "structure": "多派系、地方化：各派系在沃洛、戈贾姆、贡德尔、北谢瓦等地区独立作战；2025—2026 年出现“伞形”整合趋势（阿姆哈拉 Fano 全国运动为最强派系）；无统一指挥体系。",
    "leadership": "公开领导层信息有限（“阿姆哈拉 Fano 全国运动”2026 年 3 月发表政治声明）；各派系领导分散。",
    "geography": "活动范围：阿姆哈拉州农村（北/南沃洛、西/东戈贾姆、北谢瓦、中/南贡德尔），并沿奥罗米亚—阿姆哈拉边境活动。",
    "force_estimates": "人数缺乏可靠数据（数千至数万的估计不一）；以轻武器、伏击与地方动员为特征。",
    "current_assessment": "当前状态（截至 2026 年年中）：活跃、持续抵抗。Fano 在 ENDF 反攻下保持高频活动（2026 年 5 月为最活跃月），抵制选举并建立农村治理结构；与厄立特里亚/TPLF 的武器输送关联为部分报告支持。",
    "controversies_uncertainties": "主要争议：外部武器支持（厄立特里亚经 TPLF）缺乏独立核实；把 Fano 描述为“统一组织”是错误的（多派系）；伤亡数字口径差异大（ACLED vs 官方）。",
    "sources": "来源以 CFR 冲突追踪、Critical Threats/ACLED、比利时 CGVS 国情报告、联合国机构及可靠媒体为主；具体见 sources.json 与 evidence_records.json。"
  },
  "depth": "standard"
}

std["actor-ola"] = {
  "sections": {
    "core_assessment": "奥罗莫解放阵线/解放军（OLA）是埃塞俄比亚奥罗米亚州的武装叛乱组织，源于 2018 年奥罗莫解放阵线（OLF）武装分支的分裂；2024 年 12 月其分裂派系与政府签署有限和平协议，但主流派指挥层拒绝协议并继续武装行动，与 TPLF 结盟。",
    "name_and_translation": "规范中文名：奥罗莫解放阵线/解放军（OLA）；英文 Oromo Liberation Army（曾称 OLF-Shene）。",
    "formation_background": "OLA 于 2018—2019 年从奥罗莫解放阵线（OLF，1991 年流亡、2018 年返埃后放弃武装）分裂，以武装斗争争取奥罗莫人权利；活动区为奥罗米亚西部与南部，长期与政府军冲突。",
    "history": "2018—2020 年：武装化与扩张；2020—2022 年：提格雷战争期间与政府对抗（政府将其与 TPLF 并称“恐怖组织”）；2023—2024 年：冲突持续、与阿姆哈拉 Fano 存在局部协调；2024 年 12 月：分裂派签署有限和平协议（主流派拒绝）；2025—2026 年：主流派继续武装行动并与 TPLF 结盟。",
    "structure": "政治—军事组织：设指挥层与区域作战单位；2024 年 12 月后分裂为主流派（拒绝协议）与协议派（放下武器参与政治进程）。",
    "leadership": "主流派领导公开信息有限（组织指挥层不透明）。",
    "geography": "活动范围：奥罗米亚州西部与南部（含与阿姆哈拉、南方州接壤地带）。",
    "force_estimates": "兵力缺乏可靠数据（数千人级别的估计不一）。",
    "current_assessment": "当前状态（截至 2026 年年中）：主流派继续武装抵抗并与 TPLF 结盟；协议派参与政治进程。OLA 活动对奥罗米亚西部/南部的公路与项目安全构成威胁。",
    "controversies_uncertainties": "主要争议：把 OLA 等同于“所有奥罗莫政治力量”是错误的；与 TPLF、Fano 的实际协调程度缺乏公开资料；人数与伤亡不透明。",
    "sources": "来源以 CFR 冲突追踪、Critical Threats/ACLED、联合国机构及可靠媒体为主；具体见 sources.json 与 evidence_records.json。"
  },
  "depth": "standard"
}

# --- Tanzania ---
std["actor-tanzania-tpdf"] = {
  "sections": {
    "core_assessment": "坦桑尼亚人民国防军（TPDF）是东非训练有素的军队，主要任务为国土防御、国内治安支援与区域维和；2021—2024 年作为南共体驻莫桑比克特派团（SAMIM）主要出兵国之一参与德尔加杜角反叛乱，此后在南部边境（姆特瓦拉方向）维持部署并继续与莫桑比克双边合作。",
    "name_and_translation": "规范中文名：坦桑尼亚人民国防军（TPDF）；英文 Tanzania People's Defence Force；斯瓦希里语 Jeshi la Wananchi wa Tanzania（JWTZ）。",
    "formation_background": "TPDF 于 1964 年由坦噶尼喀与桑给巴尔军队合并组建，历史上参与乌坦战争（1978—1979 年对乌干达）等区域行动；1990 年代后以维和与国内治安为主，2017 年莫桑比克德尔加杜角叛乱后开始参与区域反恐合作。",
    "history": "2021—2024 年：作为 SAMIM 成员向莫桑比克派兵（坦桑尼亚为主要出兵国之一，负责鲁伍马河边境方向）；2024 年 7 月：SAMIM 结束、部队撤回；2024—2026 年：南部边境（姆特瓦拉）维持反渗透部署，与莫桑比克开展双边联合巡逻/情报共享；2025—2026 年：大选安保与国内任务。",
    "structure": "陆海空三军（海军保护海岸与边境水域）；南部边境设反叛乱/反渗透部署；参与南共体（SADC）与东共体（EAC）框架。",
    "leadership": "最高指挥：总统（萨米娅·苏卢胡·哈桑）；国防军司令序列随任命调整。",
    "geography": "部署：南部边境（姆特瓦拉、鲁伍马河方向）、海岸与海域、达累斯萨拉姆及国内治安支援。",
    "force_estimates": "兵力缺乏权威公开数据（数万人的估计不一）；为东非装备与训练较完整的军队之一。",
    "current_assessment": "当前状态（截至 2026 年年中）：南部边境维持部署、区域合作继续。TPDF 有效防止德尔加杜角叛乱升级为坦桑尼亚境内叛乱，但跨境渗透风险持续。",
    "controversies_uncertainties": "主要缺口：边境兵力与行动细节不透明；与莫桑比克双边合作的机制细节缺乏公开资料；选举安保中武力使用引发部分批评。",
    "sources": "来源以南共体文件、加拿大/英国旅行通告、路透社及可靠媒体为主；具体见 sources.json 与 evidence_records.json。"
  },
  "depth": "standard"
}

# =====================================================================
# merge + new entity records
# =====================================================================
profiles = load("entity_profiles.json")["profiles"]

def merge(entries, depth):
    for eid, d in entries.items():
        p = profiles.setdefault(eid, {})
        p["sections"] = d["sections"]
        p["profile_depth"] = d["depth"]
        p["profile_level"] = d["depth"]
        c = body_chars(d["sections"])
        n = count_sections(d["sections"])
        ok = ((d["depth"] == "encyclopedia_full" and c >= 1800 and n >= 8) or
              (d["depth"] == "standard" and c >= 900 and n >= 5))
        print(("OK " if ok else "!! ") + eid + f" depth={d['depth']:16s} chars={c:5d} sections={n:2d}")

print("=== encyclopedia upgrades ===")
merge(ency, "encyclopedia_full")
print("=== standard ===")
merge(std, "standard")
save("entity_profiles.json", {"profiles": profiles,
      "note": "I3-B: all basic entries upgraded; 10 core entities added; depth graded by content."})

# ---- add new entity records to entities.json ----
entities = load("entities.json")
existing = {e["entity_id"] for e in entities["entities"]}
NEW_RECORDS = {
  "actor-mali-army": new_entity("actor-mali-army", "马里武装部队，多线反叛乱的国家军队。", "Malian Armed Forces (FAMa)", "organization", "state_security_force", "马里武装部队（FAMa）", std["actor-mali-army"]["sections"], slug="mali-armed-forces", country_ids=["country-mali"], region_ids=["region-central-sahel"]),
  "actor-burkina-army": new_entity("actor-burkina-army", "布基纳法索武装部队，特拉奥雷政权反叛乱主力。", "Burkina Faso Armed Forces", "organization", "state_security_force", "布基纳法索武装部队", std["actor-burkina-army"]["sections"], slug="burkina-armed-forces", country_ids=["country-burkina-faso"], region_ids=["region-central-sahel"]),
  "actor-vdp": new_entity("actor-vdp", "国土防卫志愿军，布基纳法索政府动员民兵。", "Volunteers for the Defence of the Homeland (VDP)", "organization", "state_security_force", "国土防卫志愿军（VDP）", std["actor-vdp"]["sections"], slug="vdp", country_ids=["country-burkina-faso"], region_ids=["region-central-sahel"]),
  "actor-cameroon-bir": new_entity("actor-cameroon-bir", "快速干预营，喀麦隆总统直属精锐反恐平乱力量。", "Bataillon d'Intervention Rapide (BIR)", "organization", "state_security_force", "快速干预营（BIR）", std["actor-cameroon-bir"]["sections"], slug="bir", country_ids=["country-cameroon"], region_ids=["region-lake-chad-basin"], aliases=["BIR"]),
  "actor-ambazonia-network": new_entity("actor-ambazonia-network", "安巴佐尼亚武装网络，喀麦隆英语区多派系分离武装统称（非统一组织）。", "Ambazonia separatist armed groups", "organization", "insurgent_group", "安巴佐尼亚武装网络", std["actor-ambazonia-network"]["sections"], slug="ambazonia-armed-network", country_ids=["country-cameroon"], region_ids=["region-coastal-west-africa-spillover"], importance="L2"),
  "actor-endf": new_entity("actor-endf", "埃塞俄比亚国防军，多线作战的联邦军队。", "Ethiopian National Defense Force (ENDF)", "organization", "state_security_force", "埃塞俄比亚国防军（ENDF）", std["actor-endf"]["sections"], slug="endf", country_ids=["country-ethiopia"], region_ids=["region-sudan-horn-africa"], aliases=["ENDF"]),
  "actor-fano": new_entity("actor-fano", "Fano 相关力量，阿姆哈拉多派系民兵（非统一组织）。", "Fano militias (Amhara)", "organization", "insurgent_group", "Fano 相关力量", std["actor-fano"]["sections"], slug="fano", country_ids=["country-ethiopia"], region_ids=["region-sudan-horn-africa"], aliases=["Fano", "法诺"], importance="L2"),
  "actor-ola": new_entity("actor-ola", "奥罗莫解放军，奥罗米亚武装叛乱组织（主流派未签和平协议）。", "Oromo Liberation Army (OLA)", "organization", "insurgent_group", "奥罗莫解放军（OLA）", std["actor-ola"]["sections"], slug="ola", country_ids=["country-ethiopia"], region_ids=["region-sudan-horn-africa"], aliases=["OLA"], importance="L2"),
  "actor-tanzania-tpdf": new_entity("actor-tanzania-tpdf", "坦桑尼亚人民国防军，南部边境反渗透部署与区域合作主力。", "Tanzania People's Defence Force (TPDF)", "organization", "state_security_force", "坦桑尼亚人民国防军（TPDF）", std["actor-tanzania-tpdf"]["sections"], slug="tpdf", country_ids=["country-tanzania"], region_ids=["region-east-africa-indian-ocean"], aliases=["TPDF"]),
}
added = 0
for eid, rec in NEW_RECORDS.items():
    if eid not in existing:
        entities["entities"].append(rec)
        added += 1
entities["note"] = ("I2-B: country-type objects removed; I3-B: +10 core entities for remaining five countries.")
save("entities.json", entities)
print("new entity records added:", added, "| total entities:", len(entities["entities"]))
