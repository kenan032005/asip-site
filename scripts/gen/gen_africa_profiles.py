#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Part 4: full relation profiles + timelines for ASIP Africa intelligence (I2-A)."""
import json
from pathlib import Path

ROOT = Path(r'C:/Users/kenan/WorkBuddy/recovery/asip-intelligence-v02-clean')
OUT = ROOT / "data" / "intelligence" / "africa"

def w(name, data):
    with (OUT / name).open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("wrote", name)

PROFILES = {
"rel-jnim-is-hostile":{
 "relation_id":"rel-jnim-is-hostile","slug":"jnim-is-sahel-hostile","relation_title":"JNIM—IS Sahel：从“萨赫勒例外”到公开敌对","source_entity_id":"actor-jnim","target_entity_id":"actor-is-sahel","relation_type":"hostile_to","direction":"bidirectional","display_ring":"middle","current_status":"historical_cooperation_or_non_hostility_reported",
 "overview":"2016 年 ISGS 出现至 2019 年前后，JNIM 与 ISGS 维持了被研究者称为“萨赫勒例外”的状态：双方互不攻击，甚至偶发联手袭击共同敌人。2019 年 7 月起双方在三国边境地区公开交火，此后敌对逐步固化。",
 "parties":[{"entity_id":"actor-jnim","role":"基地组织关联联盟，2017 年成立"},{"entity_id":"actor-is-sahel","role":"伊斯兰国萨赫勒省分支，2016 年前后出现"}],
 "formation_background":"双方存在人员与组织同源性：ISGS 核心人物阿德南·阿布·瓦利德·萨赫拉维曾是穆拉比通成员，而穆拉比通大部分力量并入 JNIM。共同起源、人员流动与对共同敌人的作战需求，是早期非敌对状态的背景。",
 "initial_relationship":"非敌对并存在零星合作。CTC 研究指出双方曾有人员往来并共同参与袭击，其非暴力状态部分是“偶尔合作”而非单纯互不攻击。",
 "evolution_stages":[
  {"period":"2016—2019 年初","title":"萨赫勒例外阶段","description":"ISGS 成立后与 JNIM 维持非敌对关系，偶有共同行动，并曾出现对同一袭击的双重认领。"},
  {"period":"2019 年初","title":"意识形态分裂显现","description":"ISGS 正式成为伊斯兰国省分支后宣传渠道受 ISWAP 体系控制；JNIM 开始以贬义称谓指称 ISGS。"},
  {"period":"2019 年 7 月","title":"公开冲突开始","description":"双方在布基纳法索边境村庄阿列尔附近发生交火，被视为 JNIM—ISGS 战争的开端。"},
  {"period":"2020 年","title":"冲突全面升级","description":"当年冲突次数大幅上升；IS《Al Naba》周刊公开承认双方在萨赫勒交战。"},
  {"period":"2021 年至今","title":"敌对固化与地区差异","description":"双方在利普塔科-古尔马地区持续争夺控制与影响。"}],
 "causes":["意识形态与阵营竞争：IS 中央施压 ISGS 对 JNIM 采取敌对立场。","领土与资源竞争：双方控制范围重叠，争夺税收、走私路线和社区影响。","人员与招募竞争：双方都宣称保护富拉尼社群，争夺支持。","领导权竞争：互相指控对方与共同敌人合作。"],
 "key_turning_points":[{"event":"2019 年 7 月阿列尔交火","impact":"结束“萨赫勒例外”，开启公开冲突。","source_ids":["ctc-sahel-anomaly-2020"]},{"event":"2020 年 IS《Al Naba》公开承认交战","impact":"敌对关系公开化。","source_ids":["ctc-sahel-anomaly-2020"]},{"event":"2022 年 IS Sahel 新领导阿布·巴拉·萨赫拉维攻势","impact":"冲突烈度上升。","source_ids":["gi-toc-wea-obs-2022"]}],
 "current_status":"公开敌对状态；冲突在布基纳法索东部、马里东部和尼日尔西南部反复发生。",
 "regional_differences":"马西纳旅活动区（马里中部）初期冲突集中；布基纳法索东部长期为高烈度区域；尼日尔西南部相对分散。",
 "impact_on_security":"双方冲突削弱区域稳定并造成大规模流离失所。",
 "why_it_matters":"理解萨赫勒武装冲突内部结构与圣战阵营竞争的窗口。",
 "uncertainties":"冲突触发序列与各方责任缺乏中立公开裁决；伤亡数据依赖报道；地方分支态度存在差异。",
 "disputed":False,"temporal_sensitive":True,"last_verified_at":"2026-08-06","source_ids":["ctc-sahel-anomaly-2020","mei-jihadism-schism-2021","gi-toc-wea-obs-2022","us-state-crt-2022"]},
"rel-jnim-alqaida-affiliate":{
 "relation_id":"rel-jnim-alqaida-affiliate","slug":"jnim-alqaida-affiliate","relation_title":"JNIM—基地组织：公开关联与网络定位","source_entity_id":"actor-jnim","target_entity_id":"actor-al-qaida","relation_type":"affiliated_with","direction":"bidirectional","display_ring":"inner","current_status":"reported_current_affiliation",
 "overview":"JNIM 公开自称为基地组织在马里的正式分支，联合国制裁委员会将其列为与基地组织及相关实体相关联的实体。",
 "parties":[{"entity_id":"actor-jnim","role":"基地组织关联联盟"},{"entity_id":"actor-al-qaida","role":"跨国圣战网络核心"}],
 "formation_background":"JNIM 组成力量均长期处于基地组织关联体系内。2017 年 3 月 2 日 JNIM 成立视频中，伊亚德·阿格·加利公开向基地组织领导人宣誓效忠。",
 "initial_relationship":"公开的效忠与关联关系；JNIM 自成立即宣示基地组织阵营归属。",
 "evolution_stages":[
  {"period":"2017 年 3 月","title":"成立与效忠","description":"JNIM 成立并公开宣誓效忠基地组织领导层。"},
  {"period":"2018 年","title":"国际认定","description":"美国国务院 2018 年 9 月将其列为外国恐怖组织；联合国制裁委员会 2018 年 10 月将其列名，理由为与基地组织关联。"},
  {"period":"2018 年至今","title":"关联持续","description":"公开资料持续将 JNIM 描述为基地组织在马里的分支或关联联盟。"}],
 "causes":["组成力量的历史归属","领导层公开效忠宣示","国际认定的持续印证"],
 "key_turning_points":[{"event":"2017 年 3 月成立视频","impact":"确立公开效忠与关联定位。","source_ids":["un-jnim-2018"]},{"event":"2018 年 9—10 月国际认定","impact":"官方记录正式标记。","source_ids":["us-state-crt-2022","un-jnim-2018"]}],
 "current_status":"公开关联关系持续有效；属于网络关联而非联盟内部日常指挥。",
 "regional_differences":"无显著地区差异；全球网络定位一致。",
 "impact_on_security":"使 JNIM 成为基地组织全球叙事在非洲的重要载体。",
 "why_it_matters":"理解 JNIM 与 IS Sahel 冲突及萨赫勒圣战阵营结构的基础。",
 "uncertainties":"JNIM 与基地组织核心的实际协调深度缺乏一致公开说明。",
 "disputed":False,"temporal_sensitive":True,"last_verified_at":"2026-08-06","source_ids":["un-jnim-2018","us-state-crt-2022","au-jnim-2023"]},
"rel-jas-iswap-conflict":{
 "relation_id":"rel-jas-iswap-conflict","slug":"jas-iswap-conflict","relation_title":"博科圣地/JAS—ISWAP：同源分裂与持续竞争","source_entity_id":"actor-jas","target_entity_id":"actor-iswap","relation_type":"hostile_to","direction":"bidirectional","display_ring":"middle","current_status":"reported_current_hostility",
 "overview":"ISWAP 于 2016 年从博科圣地分裂并宣誓效忠伊斯兰国，此后两组织在乍得湖盆地长期敌对，争夺地盘、资源与社区支持。",
 "parties":[{"entity_id":"actor-jas","role":"乍得湖盆地圣战武装（基地组织体系外、未效忠伊斯兰国）"},{"entity_id":"actor-iswap","role":"伊斯兰国西非省"}],
 "formation_background":"博科圣地早期由穆罕默德·优素福创立，2009 年其死亡后由阿布巴卡尔·谢考领导；2015—2016 年间，主张效忠伊斯兰国的一派（后称 ISWAP）与谢考派分裂，由阿布·穆萨布·巴纳维等领导。",
 "initial_relationship":"同源组织；分裂初期相互指责，后发展为公开敌对。",
 "evolution_stages":[
  {"period":"2009 年前后","title":"博科圣地兴起","description":"尼日利亚东北部兴起圣战武装，后称 Boko Haram/JAS。"},
  {"period":"2015—2016 年","title":"分裂","description":"主张效忠伊斯兰国的一派独立并宣誓效忠，形成 ISWAP。"},
  {"period":"2016 年至今","title":"敌对与竞争","description":"两组织在博尔诺州及乍得湖周边持续交火与争夺。"}],
 "causes":["对伊斯兰国效忠路线之争","地盘与税收资源竞争","对社区关系与治理策略分歧"],
 "key_turning_points":[{"event":"2016 年 ISWAP 正式成立","impact":"乍得湖盆地圣战分裂固化。","source_ids":["crisis-group-lake-chad"]}],
 "current_status":"公开敌对与竞争持续。",
 "regional_differences":"博尔诺州南部（ISWAP 强）与北部（JAS 强）势力分布存在差异。",
 "impact_on_security":"双方竞争加剧乍得湖盆地暴力并影响平民安全。",
 "why_it_matters":"乍得湖盆地冲突的核心内部维度。",
 "uncertainties":"各地方分支实际立场与停火动态需持续核验。",
 "disputed":False,"temporal_sensitive":True,"last_verified_at":"2026-08-06","source_ids":["crisis-group-lake-chad","us-state-crt-2022"]},
"rel-iswap-islamic-state-affiliation":{
 "relation_id":"rel-iswap-islamic-state-affiliation","slug":"iswap-islamic-state-affiliation","relation_title":"ISWAP—伊斯兰国：效忠与省分支定位","source_entity_id":"actor-iswap","target_entity_id":"actor-islamic-state","relation_type":"affiliated_with","direction":"bidirectional","display_ring":"inner","current_status":"reported_current_affiliation",
 "overview":"ISWAP 于 2016 年宣誓效忠伊斯兰国并获承认，是伊斯兰国在西非（含乍得湖盆地）的省分支代表。",
 "parties":[{"entity_id":"actor-iswap","role":"伊斯兰国西非省"},{"entity_id":"actor-islamic-state","role":"跨国圣战网络核心"}],
 "formation_background":"2015—2016 年博科圣地内部分裂后，效忠伊斯兰国的一派组建 ISWAP，获伊斯兰国承认。",
 "initial_relationship":"公开效忠与承认；ISWAP 以省分支名义运作。",
 "evolution_stages":[
  {"period":"2016 年","title":"效忠与承认","description":"ISWAP 宣布效忠并获承认。"},
  {"period":"2016 年至今","title":"省分支运作","description":"以伊斯兰国西非省名义发布宣传并开展行动。"}],
 "causes":["组织内路线之争","伊斯兰国全球扩展策略"],
 "key_turning_points":[{"event":"2016 年效忠","impact":"确立省分支定位。","source_ids":["crisis-group-lake-chad"]}],
 "current_status":"公开关联持续。",
 "regional_differences":"与伊斯兰国萨赫勒省（ISGS）同为非洲省分支，存在协调与竞争。",
 "impact_on_security":"使乍得湖盆地成为伊斯兰国非洲网络重要节点。",
 "why_it_matters":"解释乍得湖盆地圣战阵营结构。",
 "uncertainties":"ISWAP 与伊斯兰国中央的实际协调深度缺乏公开一致说明。",
 "disputed":False,"temporal_sensitive":True,"last_verified_at":"2026-08-06","source_ids":["crisis-group-lake-chad","un-1267-list"]},
"rel-chad-mnjtf-member":{
 "relation_id":"rel-chad-mnjtf-member","slug":"chad-mnjtf-member","relation_title":"乍得—MNJTF：区域反恐核心参与","source_entity_id":"actor-chad-army","target_entity_id":"actor-mnjtf","relation_type":"member_of_force","direction":"bidirectional","display_ring":"inner","current_status":"active",
 "overview":"乍得是 MNJTF 主要成员，其武装力量长期参与乍得湖盆地联合反恐行动并承担关键机动任务。",
 "parties":[{"entity_id":"actor-chad-army","role":"乍得国防与安全力量"},{"entity_id":"actor-mnjtf","role":"多国联合特遣部队"}],
 "formation_background":"2015 年 MNJTF 启动，乍得与尼日利亚、尼日尔、喀麦隆、贝宁共同参与，应对 JAS/ISWAP 跨境威胁。",
 "initial_relationship":"创始成员与核心参与关系。",
 "evolution_stages":[
  {"period":"2015 年","title":"MNJTF 启动","description":"五国联合反恐架构建立。"},
  {"period":"2015 年至今","title":"持续参与","description":"乍得在湖区及边境开展反恐行动并承担跨境打击任务。"}],
 "causes":["跨境武装威胁","区域安全合作机制"],
 "key_turning_points":[{"event":"2015 年 MNJTF 启动","impact":"建立区域联合反恐框架。","source_ids":["crisis-group-lake-chad"]}],
 "current_status":"持续参与；MNJTF 保持运作。",
 "regional_differences":"乍得承担湖区与东部边境双重任务。",
 "impact_on_security":"区域联合反恐的重要支柱。",
 "why_it_matters":"验证乍得在区域安全体系中的核心角色。",
 "uncertainties":"任务规模与经费持续性需以最新公开资料为准。",
 "disputed":False,"temporal_sensitive":True,"last_verified_at":"2026-08-06","source_ids":["crisis-group-lake-chad"]},
"rel-saf-rsf-war":{
 "relation_id":"rel-saf-rsf-war","slug":"saf-rsf-war","relation_title":"SAF—RSF：2023 年以来的苏丹内战","source_entity_id":"actor-saf","target_entity_id":"actor-rsf","relation_type":"hostile_to","direction":"bidirectional","display_ring":"middle","current_status":"active_conflict",
 "overview":"2023 年 4 月，苏丹武装部队与快速支援部队在喀土穆等地爆发全面武装冲突，此后内战持续，造成大规模流离失所与人道危机。",
 "parties":[{"entity_id":"actor-saf","role":"苏丹国家军队（布尔汉领导）"},{"entity_id":"actor-rsf","role":"准军事力量（达加洛指挥）"}],
 "formation_background":"RSF 源自达尔富尔金戈威德武装，2013 年前后正式组建并逐步扩大；2021 年军事政变后与 SAF 联合执政，2023 年因权力与军队整合问题关系破裂。",
 "initial_relationship":"2019 年后共同主导过渡期，后因安全部门改革与权力分配分歧决裂。",
 "evolution_stages":[
  {"period":"2019 年","title":"联合掌权","description":"苏丹革命后军方与文职过渡安排建立，SAF 与 RSF 共同主导过渡主权委员会。"},
  {"period":"2021 年 10 月","title":"军事政变","description":"军方接管政权，布尔汉与达加洛共同行动但裂痕加深。"},
  {"period":"2023 年 4 月","title":"内战爆发","description":"喀土穆等地爆发全面冲突，战火蔓延至达尔富尔与科尔多凡。"},
  {"period":"2023 年至今","title":"冲突持续","description":"大规模流离失所、饥荒风险与多线战线并存。"}],
 "causes":["安全部门整合与权力分配之争","达加洛的政治野心","外部支持格局变化"],
 "key_turning_points":[{"event":"2023 年 4 月 15 日冲突爆发","impact":"苏丹进入全面内战。","source_ids":["crisis-group-sudan"]},{"event":"2023 年中战火蔓延达尔富尔","impact":"部族暴力与民兵动员加剧。","source_ids":["un-sudan-reports"]}],
 "current_status":"全面冲突持续，各方控制区随战况变化。",
 "regional_differences":"喀土穆及中部战线、达尔富尔（RSF 占优）、科尔多凡（SPLM-N 等参与）呈现不同态势。",
 "impact_on_security":"苏丹冲突是当前非洲最严重安全危机之一，外溢影响乍得、南苏丹等邻国。",
 "why_it_matters":"决定苏丹及周边区域安全走向的核心变量。",
 "uncertainties":"停火与政治进程反复；各方控制范围需持续核验。",
 "disputed":False,"temporal_sensitive":True,"last_verified_at":"2026-08-06","source_ids":["crisis-group-sudan","un-sudan-reports"]},
"rel-is-moz-islamic-state":{
 "relation_id":"rel-is-moz-islamic-state","slug":"is-moz-islamic-state","relation_title":"IS-Mozambique—伊斯兰国：省分支定位与名称问题","source_entity_id":"actor-is-mozambique","target_entity_id":"actor-islamic-state","relation_type":"affiliated_with","direction":"bidirectional","display_ring":"inner","current_status":"reported_current_affiliation",
 "overview":"莫桑比克德尔加杜角叛乱武装自 2019 年前后以伊斯兰国名义活动，2022 年前后正式以“伊斯兰国莫桑比克省”名义发布宣传。该组织的早期称法（ASWJ/Ansar al-Sunna）与后续名称在不同来源中存在差异。",
 "parties":[{"entity_id":"actor-is-mozambique","role":"德尔加杜角叛乱武装"},{"entity_id":"actor-islamic-state","role":"伊斯兰国跨国网络"}],
 "formation_background":"2017 年德尔加杜角武装袭击增多，早期称法为“圣训人民”（Ansar al-Sunna）或 ASWJ；2019 年起公开以伊斯兰国名义活动，2022 年前后称伊斯兰国莫桑比克省，并出现与“伊斯兰国中非省”（IS-CAP）称谓的混用。",
 "initial_relationship":"以伊斯兰国关联名义活动，但早期组织边界模糊。",
 "evolution_stages":[
  {"period":"2017 年","title":"袭击兴起","description":"德尔加杜角武装袭击升级，早期称法多样。"},
  {"period":"2019 年","title":"伊斯兰国名义","description":"公开以伊斯兰国名义发布宣传与认领。"},
  {"period":"2022 年前后","title":"莫桑比克省名义","description":"以伊斯兰国莫桑比克省名义活动，名称与 IS-CAP 混用。"}],
 "causes":["伊斯兰国非洲扩张策略","地方武装寻求国际框架认同"],
 "key_turning_points":[{"event":"2019 年以伊斯兰国名义活动","impact":"组织定位转向伊斯兰国体系。","source_ids":["crisis-group-mozambique"]}],
 "current_status":"以伊斯兰国省分支名义活动；名称与组织边界在不同来源中存在差异。",
 "regional_differences":"坦桑尼亚南部边境存在跨境关联。",
 "impact_on_security":"德尔加杜角叛乱与天然气投资安全密切相关。",
 "why_it_matters":"验证非萨赫勒区域在统一知识库中的建设。",
 "uncertainties":"ASWJ/ISIS-M/IS-CAP 等名称的组织边界缺乏统一公开说明，本平台不擅自拆分或合并。",
 "disputed":True,"temporal_sensitive":True,"last_verified_at":"2026-08-06","source_ids":["crisis-group-mozambique","us-state-crt-2022"]},
"rel-rdf-mozambique-fadm-cooperate":{
 "relation_id":"rel-rdf-mozambique-fadm-cooperate","slug":"rdf-mozambique-fadm-cooperate","relation_title":"莫桑比克国防军—卢旺达部队：反叛乱协同","source_entity_id":"actor-fadm","target_entity_id":"actor-rdf-mozambique","relation_type":"cooperates_with","direction":"bidirectional","display_ring":"middle","current_status":"active",
 "overview":"2021 年 7 月起卢旺达部队部署于德尔加杜角，与莫桑比克国防军协同反叛乱，显著改变当地安全态势。",
 "parties":[{"entity_id":"actor-fadm","role":"莫桑比克国防军"},{"entity_id":"actor-rdf-mozambique","role":"卢旺达驻莫桑比克部队"}],
 "formation_background":"2021 年帕尔马遭袭后，莫桑比克请求卢旺达与南共体支持；卢旺达部队快速部署并协同作战。",
 "initial_relationship":"应莫桑比克请求的军事合作。",
 "evolution_stages":[
  {"period":"2021 年 7 月","title":"卢旺达部署","description":"卢旺达部队进入德尔加杜角协同反叛乱。"},
  {"period":"2021 年至今","title":"协同推进","description":"收复多处要地，残余袭击仍存在。"}],
 "causes":["德尔加杜角安全形势恶化","双边安全协议"],
 "key_turning_points":[{"event":"2021 年部署","impact":"显著改变当地安全态势。","source_ids":["crisis-group-mozambique"]}],
 "current_status":"协同持续；莫桑比克安全力量逐步承担更多责任。",
 "regional_differences":"SAMIM 撤出后，卢旺达部队角色更加突出。",
 "impact_on_security":"德尔加杜角大部分地区安全恢复。",
 "why_it_matters":"验证区域干预模式与统一知识库中的国家—部队关系。",
 "uncertainties":"后续撤出安排需以最新公开资料为准。",
 "disputed":False,"temporal_sensitive":True,"last_verified_at":"2026-08-06","source_ids":["crisis-group-mozambique"]},
}
w("relation_profiles.json", {"schema_version":"asip-intelligence-africa-v1.0","generated_at":"2026-08-06","profiles":PROFILES})

TIMELINES = {
"rel-jnim-is-hostile":[
 {"date":"2016 年前后","event_title":"ISGS 出现","event_description":"大撒哈拉伊斯兰国在马里-布基纳法索边境地区出现。","impact_on_relationship":"开启双方共存起点。","confidence":"medium_high","disputed":False,"source_ids":["ctc-sahel-anomaly-2020"]},
 {"date":"2017 年 3 月","event_title":"JNIM 成立","event_description":"多支基地组织关联武装合并组建 JNIM。","impact_on_relationship":"两大阵营联盟并存于萨赫勒。","confidence":"high","disputed":False,"source_ids":["un-jnim-2018"]},
 {"date":"2019 年初","event_title":"意识形态分裂显现","event_description":"ISGS 正式成为伊斯兰国省分支。","impact_on_relationship":"宣传对抗升级。","confidence":"medium","disputed":False,"source_ids":["ctc-sahel-anomaly-2020"]},
 {"date":"2019 年 7 月","event_title":"阿列尔交火","event_description":"双方在布基纳法索边境发生交火。","impact_on_relationship":"“萨赫勒例外”结束。","confidence":"medium","disputed":False,"source_ids":["ctc-sahel-anomaly-2020"]},
 {"date":"2020 年","event_title":"冲突全面升级","event_description":"双方冲突次数大幅上升并公开承认交战。","impact_on_relationship":"敌对公开化并固化。","confidence":"medium_high","disputed":False,"source_ids":["ctc-sahel-anomaly-2020","mei-jihadism-schism-2021"]},
 {"date":"2022 年至今","event_title":"IS Sahel 攻势与对峙延续","event_description":"IS Sahel 新领导发动大规模攻击。","impact_on_relationship":"冲突持续并随战况变化。","confidence":"medium_high","disputed":False,"source_ids":["gi-toc-wea-obs-2022"]}],
"rel-jnim-alqaida-affiliate":[
 {"date":"2017 年 3 月 2 日","event_title":"JNIM 成立并宣誓效忠","event_description":"JNIM 成立视频中公开向基地组织领导层宣誓效忠。","impact_on_relationship":"确立关联定位。","confidence":"high","disputed":False,"source_ids":["un-jnim-2018"]},
 {"date":"2018 年 9 月","event_title":"美国列名","event_description":"美国国务院将 JNIM 列为外国恐怖组织。","impact_on_relationship":"国际官方记录确认。","confidence":"high","disputed":False,"source_ids":["us-state-crt-2022"]},
 {"date":"2018 年 10 月","event_title":"联合国制裁列名","event_description":"联合国将 JNIM 列入名单，理由为与基地组织关联。","impact_on_relationship":"关联获得联合国记录。","confidence":"high","disputed":False,"source_ids":["un-jnim-2018"]}],
"rel-jas-iswap-conflict":[
 {"date":"2009 年","event_title":"优素福死亡与博科圣地武装化","event_description":"博科圣地创始人死亡，组织走向武装化。","impact_on_relationship":"组织前史。","confidence":"medium_high","disputed":False,"source_ids":["crisis-group-lake-chad"]},
 {"date":"2015—2016 年","event_title":"分裂与 ISWAP 成立","event_description":"效忠伊斯兰国的一派独立组建 ISWAP。","impact_on_relationship":"同源组织分裂。","confidence":"high","disputed":False,"source_ids":["crisis-group-lake-chad"]},
 {"date":"2016 年至今","event_title":"敌对与竞争","event_description":"两组织持续交火与争夺地盘。","impact_on_relationship":"敌对固化。","confidence":"medium_high","disputed":False,"source_ids":["crisis-group-lake-chad","us-state-crt-2022"]}],
"rel-iswap-islamic-state-affiliation":[
 {"date":"2016 年","event_title":"效忠与承认","event_description":"ISWAP 宣誓效忠伊斯兰国并获承认。","impact_on_relationship":"确立省分支定位。","confidence":"high","disputed":False,"source_ids":["crisis-group-lake-chad"]},
 {"date":"2016 年至今","event_title":"省分支运作","event_description":"以伊斯兰国西非省名义开展行动与宣传。","impact_on_relationship":"关联持续。","confidence":"medium_high","disputed":False,"source_ids":["un-1267-list"]}],
"rel-chad-mnjtf-member":[
 {"date":"2015 年","event_title":"MNJTF 启动","event_description":"五国联合反恐架构建立。","impact_on_relationship":"建立合作框架。","confidence":"high","disputed":False,"source_ids":["crisis-group-lake-chad"]},
 {"date":"2015 年至今","event_title":"持续参与","event_description":"乍得在湖区及边境持续执行反恐任务。","impact_on_relationship":"合作关系持续。","confidence":"high","disputed":False,"source_ids":["crisis-group-lake-chad"]}],
"rel-saf-rsf-war":[
 {"date":"2019 年","event_title":"联合过渡","event_description":"军方与文职过渡安排建立。","impact_on_relationship":"SAF 与 RSF 共同主导过渡。","confidence":"high","disputed":False,"source_ids":["crisis-group-sudan"]},
 {"date":"2021 年 10 月","event_title":"军事政变","event_description":"军方接管政权。","impact_on_relationship":"裂痕加深。","confidence":"high","disputed":False,"source_ids":["crisis-group-sudan"]},
 {"date":"2023 年 4 月","event_title":"内战爆发","event_description":"喀土穆等地爆发全面冲突。","impact_on_relationship":"全面敌对。","confidence":"high","disputed":False,"source_ids":["crisis-group-sudan"]},
 {"date":"2023 年至今","event_title":"冲突持续","event_description":"战火蔓延至达尔富尔与科尔多凡。","impact_on_relationship":"冲突持续并外溢。","confidence":"high","disputed":False,"source_ids":["un-sudan-reports"]}],
"rel-is-moz-islamic-state":[
 {"date":"2017 年","event_title":"德尔加杜角袭击兴起","event_description":"武装袭击升级，早期称法多样。","impact_on_relationship":"叛乱兴起。","confidence":"high","disputed":False,"source_ids":["crisis-group-mozambique"]},
 {"date":"2019 年","event_title":"伊斯兰国名义","event_description":"公开以伊斯兰国名义活动。","impact_on_relationship":"定位转向伊斯兰国体系。","confidence":"medium_high","disputed":False,"source_ids":["crisis-group-mozambique"]},
 {"date":"2022 年前后","event_title":"莫桑比克省名义","event_description":"以伊斯兰国莫桑比克省名义活动。","impact_on_relationship":"省分支定位。","confidence":"medium_high","disputed":True,"source_ids":["crisis-group-mozambique","us-state-crt-2022"]}],
"rel-rdf-mozambique-fadm-cooperate":[
 {"date":"2021 年 7 月","event_title":"卢旺达部署","event_description":"卢旺达部队进入德尔加杜角。","impact_on_relationship":"建立协同。","confidence":"high","disputed":False,"source_ids":["crisis-group-mozambique"]},
 {"date":"2021 年至今","event_title":"协同推进","event_description":"收复多处要地，残余袭击仍存在。","impact_on_relationship":"合作持续。","confidence":"high","disputed":False,"source_ids":["crisis-group-mozambique"]}],
}
w("relation_timelines.json", {"schema_version":"asip-intelligence-africa-v1.0","generated_at":"2026-08-06","timelines":TIMELINES})
print("profiles:", len(PROFILES), "timelines:", len(TIMELINES))
