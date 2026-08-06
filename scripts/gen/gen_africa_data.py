#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the ASIP Africa intelligence production data package (I2-A).
Single generator: regions, countries, entities, relationships, sources, evidence,
relation profiles/timelines, force estimates, external links, alias & graph index.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(r'C:/Users/kenan/WorkBuddy/recovery/asip-intelligence-v02-clean')
DEMO = ROOT / "data" / "intelligence" / "demo"
OUT = ROOT / "data" / "intelligence" / "africa"
OUT.mkdir(parents=True, exist_ok=True)

def load_demo(name):
    with (DEMO / name).open(encoding="utf-8") as f:
        return json.load(f)

def w(name, data):
    with (OUT / name).open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("wrote", name)

# ----------------------------------------------------------------------------
# Regions (7)
# ----------------------------------------------------------------------------
REGIONS = [
  {"region_id":"region-central-sahel","slug":"central-sahel","name_zh":"中萨赫勒","name_en":"Central Sahel",
   "definition":"以马里、布基纳法索、尼日尔为核心的萨赫勒武装冲突与治理危机带，JNIM 与 IS Sahel 活动核心区。",
   "geographic_scope":"马里北部与中部、布基纳法索北部与东部、尼日尔西南部，及三国边境的利普塔科-古尔马地区。",
   "countries":["country-mali","country-burkina-faso","country-niger","country-chad"],
   "core_topics":["基地组织关联武装（JNIM）","伊斯兰国萨赫勒分支（IS Sahel）","圣战阵营竞争","治理真空与流离失所","国际与地区反恐行动"],
   "main_actors":["actor-jnim","actor-is-sahel","actor-aqim","actor-katiba-macina","person-iyad-ag-ghali"],
   "key_cross_border_relations":["rel-jnim-is-conflict","rel-jnim-mali-operates","rel-is-mali-operates"],
   "current_trends":"JNIM 与 IS Sahel 持续敌对并扩展至沿海国家北部边境；布基纳法索冲突南移。",
   "links_to_other_regions":["region-lake-chad-basin","region-coastal-west-africa-spillover","region-north-africa-sahara"],
   "source_ids":["un-jnim-2018","us-state-crt-2022","ctc-sahel-anomaly-2020","mei-jihadism-schism-2021","gi-toc-wea-obs-2022"],
   "last_verified_at":"2026-08-06","notes":"本区域划分用于 ASIP 安全分析，不等同于唯一的正式地理分类。"},
  {"region_id":"region-lake-chad-basin","slug":"lake-chad-basin","name_zh":"乍得湖盆地","name_en":"Lake Chad Basin",
   "definition":"以乍得湖为中心、覆盖尼日利亚东北部、尼日尔东南部、乍得西部和喀麦隆极北省的跨境安全区，Boko Haram/JAS 与 ISWAP 活动核心区。",
   "geographic_scope":"乍得湖周边四国边境地带（尼日利亚博尔诺、乍得湖区、尼日尔迪法、喀麦隆极北省）。",
   "countries":["country-nigeria","country-chad","country-niger","country-cameroon"],
   "core_topics":["Boko Haram/JAS 与 ISWAP 分裂与竞争","跨国联合反恐（MNJTF）","乍得湖生态与安全关联","流离失所与跨境难民","地方自卫与社区武装"],
   "main_actors":["actor-jas","actor-iswap","actor-mnjtf","actor-chad-army","actor-nigeria-army","actor-cameroon-army"],
   "key_cross_border_relations":["rel-jas-iswap-conflict","rel-chad-mnjtf-member","rel-iswap-operates-nigeria"],
   "current_trends":"ISWAP 与 JAS 竞争持续；MNJTF 维持存在；乍得参与多边行动并承受跨境威胁。",
   "links_to_other_regions":["region-central-sahel","region-coastal-west-africa-spillover"],
   "source_ids":["un-1267-list","us-state-crt-2022","crisis-group-lake-chad","iss-africa-jihadism"],
   "last_verified_at":"2026-08-06","notes":"本区域划分用于 ASIP 安全分析，不等同于唯一的正式地理分类。"},
  {"region_id":"region-coastal-west-africa-spillover","slug":"coastal-west-africa","name_zh":"西非沿海外溢带","name_en":"Coastal West Africa Spillover Belt",
   "definition":"萨赫勒武装活动向贝宁、多哥、加纳、科特迪瓦北部沿海国家外溢的关联带。",
   "geographic_scope":"贝宁北部、多哥北部、加纳与科特迪瓦北部边境；与布基纳法索南部冲突区相邻。",
   "countries":["country-benin","country-burkina-faso","country-niger"],
   "core_topics":["萨赫勒武装跨境渗透与袭击","W-Arly-Pendjari 保护区安全","沿海国家反恐响应","盗猎与武装走私网络"],
   "main_actors":["actor-jnim","actor-is-sahel","actor-benin-forces"],
   "key_cross_border_relations":["rel-jnim-benin-spillover","rel-is-benin-spillover"],
   "current_trends":"布基纳法索南部冲突区外溢，贝宁与多哥北部袭击与绑架风险上升。",
   "links_to_other_regions":["region-central-sahel","region-lake-chad-basin"],
   "source_ids":["us-state-crt-2022","iss-africa-jihadism","crisis-group-sahel"],
   "last_verified_at":"2026-08-06","notes":"本区域划分用于 ASIP 安全分析，不等同于唯一的正式地理分类。"},
  {"region_id":"region-sudan-red-sea-horn","slug":"sudan-red-sea-horn","name_zh":"苏丹—红海—非洲之角关联区","name_en":"Sudan–Red Sea–Horn of Africa Complex",
   "definition":"以苏丹冲突为核心，连接红海安全、埃及与埃塞俄比亚关联及非洲之角动态的复合安全区。",
   "geographic_scope":"苏丹全境、红海沿岸、南苏丹北部边境及埃塞俄比亚西部关联地带。",
   "countries":["country-sudan","country-south-sudan","country-ethiopia","country-chad"],
   "core_topics":["SAF 与 RSF 全面冲突","达尔富尔武装与准军事力量","红海地缘竞争","跨撒哈拉武器与人员流动"],
   "main_actors":["actor-saf","actor-rsf","actor-splm-n-al-hilu","actor-jem","actor-slm-aw"],
   "key_cross_border_relations":["rel-saf-rsf-war","rel-splm-n-saf-conflict"],
   "current_trends":"苏丹内战持续，达尔富尔与科尔多凡武装冲突叠加；跨境外溢影响乍得东部与南苏丹。",
   "links_to_other_regions":["region-nile-basin-east-africa","region-north-africa-sahara"],
   "source_ids":["un-sudan-reports","crisis-group-sudan","us-state-crt-2022"],
   "last_verified_at":"2026-08-06","notes":"本区域划分用于 ASIP 安全分析，不等同于唯一的正式地理分类。"},
  {"region_id":"region-nile-basin-east-africa","slug":"nile-basin-east-africa","name_zh":"尼罗河流域与东非安全带","name_en":"Nile Basin and East African Security Belt",
   "definition":"覆盖尼罗河流域（苏丹、南苏丹、埃塞俄比亚）与东非安全带（含坦桑尼亚、莫桑比克关联）的分析视图。",
   "geographic_scope":"尼罗河中上游流域、南苏丹、埃塞俄比亚，向东延伸至东非沿岸。",
   "countries":["country-south-sudan","country-sudan","country-ethiopia","country-tanzania","country-mozambique"],
   "core_topics":["南苏丹政治-军事冲突","苏丹内战南部外溢","埃塞俄比亚内部冲突","东非圣战网络扩散"],
   "main_actors":["actor-sspdf","actor-splm-io","actor-nas","actor-saf","actor-rsf"],
   "key_cross_border_relations":["rel-splm-io-sspdf-conflict","rel-saf-rsf-war"],
   "current_trends":"南苏丹政治进程反复；苏丹冲突向南部与乍得边境外溢。",
   "links_to_other_regions":["region-sudan-red-sea-horn","region-southeast-africa-mozambique"],
   "source_ids":["crisis-group-south-sudan","un-sudan-reports"],
   "last_verified_at":"2026-08-06","notes":"本区域划分用于 ASIP 安全分析，不等同于唯一的正式地理分类。"},
  {"region_id":"region-north-africa-sahara","slug":"north-africa-sahara","name_zh":"北非—撒哈拉跨境安全区","name_en":"North Africa–Sahara Cross-border Security Zone",
   "definition":"覆盖利比亚、阿尔及利亚南部、毛里塔尼亚与萨赫勒北缘的跨境安全区，武器、人员与走私网络贯穿其中。",
   "geographic_scope":"利比亚全境、阿尔及利亚撒哈拉南部、毛里塔尼亚东部、马里北部与乍得北部。",
   "countries":["country-libya","country-chad","country-mali","country-niger"],
   "core_topics":["利比亚派系冲突","ISIS-Libya 残余","撒哈拉武器走私与人口贩运网络","萨赫勒武装北缘关联"],
   "main_actors":["actor-lna","actor-gnu-forces","actor-isis-libya"],
   "key_cross_border_relations":["rel-lna-gnu-rivalry","rel-isis-libya-affiliation"],
   "current_trends":"利比亚政治僵局与分裂持续；南部通道与萨赫勒犯罪网络关联活跃。",
   "links_to_other_regions":["region-central-sahel","region-sudan-red-sea-horn"],
   "source_ids":["un-libya-reports","crisis-group-libya"],
   "last_verified_at":"2026-08-06","notes":"本区域划分用于 ASIP 安全分析，不等同于唯一的正式地理分类。"},
  {"region_id":"region-southeast-africa-mozambique","slug":"southeast-africa-mozambique","name_zh":"东南部非洲—莫桑比克安全区","name_en":"Southeast Africa–Mozambique Security Zone",
   "definition":"以莫桑比克德尔加杜角冲突为核心、关联坦桑尼亚边境与地区干预力量（SAMIM、卢旺达部署）的独立安全区，不属于萨赫勒。",
   "geographic_scope":"莫桑比克德尔加杜角省、坦桑尼亚南部边境、周边海域与天然气项目区。",
   "countries":["country-mozambique","country-tanzania"],
   "core_topics":["IS Mozambique（旧称 ASWJ/ISIS-M）","德尔加杜角叛乱","卢旺达与 SAMIM 地区干预","天然气投资安全"],
   "main_actors":["actor-is-mozambique","actor-fadm","actor-rdf-mozambique","actor-samim"],
   "key_cross_border_relations":["rel-is-moz-islamic-state","rel-fadm-rdf-cooperate"],
   "current_trends":"莫桑比克安全力量与卢旺达部队恢复对德尔加杜角大部分地区控制；IS Mozambique 残余袭击仍存在。",
   "links_to_other_regions":["region-nile-basin-east-africa"],
   "source_ids":["crisis-group-mozambique","us-state-crt-2022","iss-africa-mozambique"],
   "last_verified_at":"2026-08-06","notes":"本区域划分用于 ASIP 安全分析，不等同于唯一的正式地理分类。"},
]
w("regions.json", {"schema_version":"asip-intelligence-africa-v1.0","generated_at":"2026-08-06","regions":REGIONS})

# ----------------------------------------------------------------------------
# Countries (12)
# ----------------------------------------------------------------------------
COUNTRIES = [
 {"country_id":"country-chad","slug":"chad","name_zh":"乍得","name_en":"Chad","iso_alpha2":"TD","iso_alpha3":"TCD","risk_level":"extreme","risk_level_reason":"同时面临乍得湖盆地武装威胁、东部苏丹冲突外溢与内部政治压力","region_ids":["region-central-sahel","region-lake-chad-basin","region-sudan-red-sea-horn"],"primary_region_id":"region-lake-chad-basin","core_conflicts":["乍得湖盆地 JAS/ISWAP 跨境威胁","苏丹达尔富尔冲突外溢","国内政治-军事过渡"],"main_actors":["actor-chad-army","actor-jas","actor-iswap"],"high_risk_areas":["湖区（Lac）","西部与苏丹接壤边境","乍得湖四国交界"],"cross_border_relations":["rel-chad-mnjtf-member","rel-jas-chad-spillover"],"trends":"多边反恐存在维持；东部边境受苏丹冲突外溢影响。","last_verified_at":"2026-08-06","notes":"乍得同时属于中萨赫勒、乍得湖盆地并关联苏丹方向跨境安全。"},
 {"country_id":"country-niger","slug":"niger","name_zh":"尼日尔","name_en":"Niger","iso_alpha2":"NE","iso_alpha3":"NER","risk_level":"high","risk_level_reason":"西南部 JNIM/IS Sahel 跨境武装活动、东南部乍得湖盆地威胁及 2023 年政变后安全合作变化","region_ids":["region-central-sahel","region-lake-chad-basin","region-coastal-west-africa-spillover"],"primary_region_id":"region-central-sahel","core_conflicts":["利普塔科-古尔马跨境武装活动","迪法省乍得湖盆地威胁","政变后安全架构调整"],"main_actors":["actor-jnim","actor-is-sahel","actor-iswap","actor-jas"],"high_risk_areas":["西南部边境（蒂拉贝里等）","东南部迪法省","北部阿加德兹通道"],"cross_border_relations":["rel-jnim-niger-operates","rel-is-niger-operates"],"trends":"西南部武装活动持续；2023 年政变后与部分国际安全伙伴关系变化。","last_verified_at":"2026-08-06","notes":"尼日尔同时属于中萨赫勒与乍得湖盆地，并关联西非沿海外溢。"},
 {"country_id":"country-mali","slug":"mali","name_zh":"马里","name_en":"Mali","iso_alpha2":"ML","iso_alpha3":"MLI","risk_level":"high","risk_level_reason":"JNIM 与 IS Sahel 活动、北部-中部武装冲突及国际力量调整","region_ids":["region-central-sahel","region-north-africa-sahara"],"primary_region_id":"region-central-sahel","core_conflicts":["JNIM 在北部与中部活动","IS Sahel 在东部竞争","武装团体与政府关系"],"main_actors":["actor-jnim","actor-is-sahel","actor-katiba-macina","person-iyad-ag-ghali"],"high_risk_areas":["北部基达尔、加奥、梅纳卡","中部莫普提","边境地区"],"cross_border_relations":["rel-jnim-mali-operates","rel-is-mali-operates"],"trends":"JNIM 在部分地区扩展影响；IS Sahel 在东部发起攻势。","last_verified_at":"2026-08-06","notes":"马里同时关联北非—撒哈拉跨境安全。"},
 {"country_id":"country-burkina-faso","slug":"burkina-faso","name_zh":"布基纳法索","name_en":"Burkina Faso","iso_alpha2":"BF","iso_alpha3":"BFA","risk_level":"high","risk_level_reason":"JNIM 与 IS Sahel 冲突高烈度区，2023 年恐怖相关死亡人数居萨赫勒前列","region_ids":["region-central-sahel","region-coastal-west-africa-spillover"],"primary_region_id":"region-central-sahel","core_conflicts":["JNIM 与 IS Sahel 冲突","东部-北部武装活动","志愿保卫家园志愿者（VDP）参与"],"main_actors":["actor-jnim","actor-is-sahel"],"high_risk_areas":["东部（纳梅滕加等）","北部（苏姆等）","南部边境省份（外溢风险）"],"cross_border_relations":["rel-jnim-burkina-operates","rel-is-burkina-operates"],"trends":"冲突区向南扩展至与贝宁、多哥、加纳、科特迪瓦接壤边境。","last_verified_at":"2026-08-06","notes":"布基纳法索同时属于中萨赫勒与西非沿海外溢带。"},
 {"country_id":"country-nigeria","slug":"nigeria","name_zh":"尼日利亚","name_en":"Nigeria","iso_alpha2":"NG","iso_alpha3":"NGA","risk_level":"high","risk_level_reason":"东北部 JAS/ISWAP 冲突持续，叠加中北部武装暴力与绑架勒索","region_ids":["region-lake-chad-basin","region-coastal-west-africa-spillover"],"primary_region_id":"region-lake-chad-basin","core_conflicts":["东北部 JAS/ISWAP 叛乱","中北部农牧冲突与绑架","武装团伙活动"],"main_actors":["actor-jas","actor-iswap","actor-nigeria-army"],"high_risk_areas":["博尔诺州","约贝、阿达马瓦部分","尼日尔州、卡齐纳等西北部"],"cross_border_relations":["rel-jas-iswap-conflict","rel-iswap-operates-nigeria"],"trends":"ISWAP 在东北部部分地区扩展；绑架与勒索经济活跃。","last_verified_at":"2026-08-06","notes":"尼日利亚同时属于乍得湖盆地与西非沿海外溢带。"},
 {"country_id":"country-cameroon","slug":"cameroon","name_zh":"喀麦隆","name_en":"Cameroon","iso_alpha2":"CM","iso_alpha3":"CMR","risk_level":"high","risk_level_reason":"极北省 JAS/ISWAP 跨境威胁，叠加西北-西南英语区武装冲突","region_ids":["region-lake-chad-basin"],"primary_region_id":"region-lake-chad-basin","core_conflicts":["极北省乍得湖盆地武装威胁","西北-西南英语区冲突"],"main_actors":["actor-jas","actor-iswap","actor-cameroon-army"],"high_risk_areas":["极北省","西北-西南英语区"],"cross_border_relations":["rel-jas-cameroon-spillover"],"trends":"极北省跨境袭击持续；英语区冲突呈长期化。","last_verified_at":"2026-08-06","notes":"喀麦隆同时关联中非方向安全。"},
 {"country_id":"country-benin","slug":"benin","name_zh":"贝宁","name_en":"Benin","iso_alpha2":"BJ","iso_alpha3":"BEN","risk_level":"high","risk_level_reason":"北部边境萨赫勒武装渗透与袭击风险上升，W-Arly-Pendjari 地区安全恶化","region_ids":["region-coastal-west-africa-spillover"],"primary_region_id":"region-coastal-west-africa-spillover","core_conflicts":["北部跨境武装袭击与绑架","W-Arly-Pendjari 保护区安全"],"main_actors":["actor-jnim","actor-is-sahel","actor-benin-forces"],"high_risk_areas":["北部彭贾里、阿塔科拉","W-Arly-Pendjari 保护区"],"cross_border_relations":["rel-jnim-benin-spillover"],"trends":"布基纳法索冲突南移带动贝宁北部袭击增多。","last_verified_at":"2026-08-06","notes":"贝宁属于西非沿海外溢带，与布基纳法索、尼日尔北部安全形势关联。"},
 {"country_id":"country-sudan","slug":"sudan","name_zh":"苏丹","name_en":"Sudan","iso_alpha2":"SD","iso_alpha3":"SDN","risk_level":"extreme","risk_level_reason":"SAF 与 RSF 全面内战、大规模流离失所、达尔富尔与科尔多凡多线冲突","region_ids":["region-sudan-red-sea-horn","region-nile-basin-east-africa"],"primary_region_id":"region-sudan-red-sea-horn","core_conflicts":["SAF—RSF 全面冲突（2023 年 4 月起）","达尔富尔民兵与部族暴力","科尔多凡 SPLM-N 冲突"],"main_actors":["actor-saf","actor-rsf","actor-splm-n-al-hilu","actor-jem","actor-slm-aw"],"high_risk_areas":["喀土穆及周边","达尔富尔五州","科尔多凡","红海州与东部"],"cross_border_relations":["rel-saf-rsf-war","rel-splm-n-saf-conflict"],"trends":"冲突持续并僵持，大规模流离失所与饥荒风险。","last_verified_at":"2026-08-06","notes":"苏丹同时关联东部萨赫勒、红海与非洲之角安全体系。"},
 {"country_id":"country-south-sudan","slug":"south-sudan","name_zh":"南苏丹","name_en":"South Sudan","iso_alpha2":"SS","iso_alpha3":"SSD","risk_level":"high","risk_level_reason":"政治-军事冲突周期性复发、族群暴力与苏丹冲突外溢","region_ids":["region-nile-basin-east-africa","region-sudan-red-sea-horn"],"primary_region_id":"region-nile-basin-east-africa","core_conflicts":["SPLM/A-IO 与 SSPDF 对立","族群-社区暴力","苏丹冲突跨境外溢"],"main_actors":["actor-sspdf","actor-splm-io","actor-nas","person-salva-kiir","person-riek-machar"],"high_risk_areas":["上尼罗河州","琼莱州","瓦拉卜州","与苏丹接壤边境"],"cross_border_relations":["rel-splm-io-sspdf-conflict"],"trends":"政治进程反复；苏丹战争外溢影响边境安全。","last_verified_at":"2026-08-06","notes":"南苏丹属于尼罗河流域与东非安全带，并关联苏丹跨境安全。"},
 {"country_id":"country-ethiopia","slug":"ethiopia","name_zh":"埃塞俄比亚","name_en":"Ethiopia","iso_alpha2":"ET","iso_alpha3":"ETH","risk_level":"high","risk_level_reason":"内部区域冲突与族际暴力、苏丹边境外溢、非洲之角地缘紧张","region_ids":["region-nile-basin-east-africa","region-sudan-red-sea-horn"],"primary_region_id":"region-nile-basin-east-africa","core_conflicts":["区域冲突与族际暴力","阿姆哈拉、奥罗米亚武装活动","苏丹边境外溢"],"main_actors":["actor-rsf"],"high_risk_areas":["阿姆哈拉州","奥罗米亚州部分","与苏丹接壤边境"],"cross_border_relations":[],"trends":"内部武装冲突持续；与苏丹边境局势受苏丹内战影响。","last_verified_at":"2026-08-06","notes":"埃塞俄比亚属于尼罗河流域与东非安全带，并关联非洲之角。"},
 {"country_id":"country-mozambique","slug":"mozambique","name_zh":"莫桑比克","name_en":"Mozambique","iso_alpha2":"MZ","iso_alpha3":"MOZ","risk_level":"extreme","risk_level_reason":"德尔加杜角叛乱持续、天然气投资安全风险与地区干预依赖","region_ids":["region-southeast-africa-mozambique"],"primary_region_id":"region-southeast-africa-mozambique","core_conflicts":["德尔加杜角 IS Mozambique 叛乱","坦桑尼亚边境跨境威胁","天然气项目安全"],"main_actors":["actor-is-mozambique","actor-fadm","actor-rdf-mozambique","actor-samim"],"high_risk_areas":["德尔加杜角省（帕尔马、莫辛博阿-达普拉亚等）","坦桑尼亚南部边境"],"cross_border_relations":["rel-is-moz-islamic-state","rel-fadm-rdf-cooperate"],"trends":"莫桑比克与卢旺达部队恢复大部控制；IS Mozambique 残余与零散袭击仍存在。","last_verified_at":"2026-08-06","notes":"莫桑比克属于东南部非洲—莫桑比克安全区，不属于萨赫勒。"},
 {"country_id":"country-libya","slug":"libya","name_zh":"利比亚","name_en":"Libya","iso_alpha2":"LY","iso_alpha3":"LBY","risk_level":"high","risk_level_reason":"东西部政治分裂、派系武装并存、南部走私网络与 ISIS-Libya 残余","region_ids":["region-north-africa-sahara"],"primary_region_id":"region-north-africa-sahara","core_conflicts":["LNA 与 GNU 安全力量对立","派系武装竞争","南部跨境犯罪网络"],"main_actors":["actor-lna","actor-gnu-forces","actor-isis-libya"],"high_risk_areas":["南部费赞","西部沿海（的黎波里周边）","东部昔兰尼加"],"cross_border_relations":["rel-lna-gnu-rivalry","rel-isis-libya-affiliation"],"trends":"政治僵局持续；南部通道与萨赫勒武器、人员、走私网络关联活跃。","last_verified_at":"2026-08-06","notes":"利比亚属于北非—撒哈拉跨境安全区，并关联萨赫勒跨境网络。"},
]
# move demo countries into the same pool, keep IDs
for c in COUNTRIES:
    if c["country_id"] in ("country-mali","country-burkina-faso","country-niger"):
        pass
w("countries.json", {"schema_version":"asip-intelligence-africa-v1.0","generated_at":"2026-08-06","countries":COUNTRIES})

# ----------------------------------------------------------------------------
# Entities: migrate 12 demo + new actors (no duplicate IDs)
# ----------------------------------------------------------------------------
demo_entities = load_demo("entities.json")["entities"]
migrated = []
for e in demo_entities:
    ent = {k: e[k] for k in e}
    ent["entity_id"] = e["entity_id"]
    ent["primary_type"] = "organization" if e["entity_type"] == "organization" else ("person" if e["entity_type"] == "person" else "country")
    ent["secondary_types"] = []
    ent["importance_score"] = None
    ent["importance_reasons"] = []
    ent["importance_reviewed_at"] = "2026-08-06"
    ent["importance_review_status"] = "migrated"
    ent["evidence_ids"] = []
    if e["entity_id"] == "actor-jnim":
        ent["region_ids"] = ["region-central-sahel"]
        ent["country_ids"] = ["country-mali","country-burkina-faso","country-niger"]
    elif e["entity_id"] == "actor-is-sahel":
        ent["region_ids"] = ["region-central-sahel"]
        ent["country_ids"] = ["country-mali","country-burkina-faso","country-niger"]
    elif e["entity_id"] == "actor-al-qaida":
        ent["region_ids"] = []
        ent["country_ids"] = []
    elif e["entity_id"] == "actor-aqim":
        ent["region_ids"] = ["region-central-sahel","region-north-africa-sahara"]
        ent["country_ids"] = ["country-mali"]
    elif e["entity_id"] in ("actor-ansar-eddine","actor-al-mourabitoun","actor-katiba-macina","person-iyad-ag-ghali","person-amadou-koufa"):
        ent["region_ids"] = ["region-central-sahel"]
        ent["country_ids"] = ["country-mali","country-burkina-faso"]
    else:  # countries
        ent["region_ids"] = []
        ent["country_ids"] = [e["entity_id"]]
    migrated.append(ent)

NEW_ENTITIES = [
 {"entity_id":"actor-islamic-state","entity_type":"organization","primary_type":"international_network","secondary_types":["terrorist_group"],"slug":"islamic-state","name_zh":"伊斯兰国","name_en":"Islamic State (ISIL/IS)","acronym":"IS","native_name":"الدولة الإسلامية","aliases":["ISIL","ISIS","Islamic State"],"historical_names":[],"importance_level":"L2","short_description":"跨国圣战网络核心实体（生产数据层占位），萨赫勒、乍得湖、莫桑比克与利比亚等分支的关联枢纽。","current_status":"active_network","primary_category":"transnational_jihadist_network","tags":["跨国网络","伊斯兰国体系"],"region_ids":[],"country_ids":[],"confidence":"high","temporal_sensitive":False,"disputed":False,"source_refs":["un-1267-list"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-jas","entity_type":"organization","primary_type":"terrorist_group","secondary_types":["insurgent_group"],"slug":"boko-haram-jas","name_zh":"博科圣地/贾马阿图·阿斯-苏纳","name_en":"Jama'atu Ahl as-Sunnah lid-Da'awati wal-Jihad (Boko Haram/JAS)","acronym":"JAS","native_name":"جماعة أهل السنة للدعوة والجهاد","aliases":["Boko Haram","JAS","Jama'atu Ahlis Sunna Lidda'awati wal-Jihad"],"historical_names":["博科圣地（Boko Haram，通用旧称）"],"importance_level":"L1","short_description":"乍得湖盆地主要圣战武装，2016 年与 ISWAP 分裂后仍控制东北部部分区域。","current_status":"active","primary_category":"islamic_state_rival_network","tags":["乍得湖盆地","尼日利亚东北部"],"region_ids":["region-lake-chad-basin"],"country_ids":["country-nigeria","country-chad","country-cameroon","country-niger"],"confidence":"medium_high","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-lake-chad","us-state-crt-2022"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-iswap","entity_type":"organization","primary_type":"terrorist_group","secondary_types":[],"slug":"iswap","name_zh":"伊斯兰国西非省","name_en":"Islamic State West Africa Province","acronym":"ISWAP","native_name":"ولاية غرب إفريقيا","aliases":["ISWAP","Islamic State in West Africa"],"historical_names":[],"importance_level":"L1","short_description":"2016 年从博科圣地分裂并宣誓效忠伊斯兰国的乍得湖盆地武装。","current_status":"active","primary_category":"islamic_state_aligned_network","tags":["乍得湖盆地","伊斯兰国"],"region_ids":["region-lake-chad-basin"],"country_ids":["country-nigeria","country-chad","country-cameroon","country-niger"],"confidence":"medium_high","temporal_sensitive":True,"disputed":False,"source_refs":["un-1267-list","crisis-group-lake-chad"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-mnjtf","entity_type":"organization","primary_type":"regional_force","secondary_types":[],"slug":"mnjtf","name_zh":"多国联合特遣部队","name_en":"Multinational Joint Task Force","acronym":"MNJTF","native_name":"","aliases":["MNJTF","FMM"],"historical_names":[],"importance_level":"L2","short_description":"由乍得、尼日利亚、尼日尔、喀麦隆、贝宁组成的乍得湖盆地联合反恐部队。","current_status":"active","primary_category":"regional_security_force","tags":["乍得湖盆地","地区联合部队"],"region_ids":["region-lake-chad-basin"],"country_ids":["country-chad","country-nigeria","country-niger","country-cameroon","country-benin"],"confidence":"high","temporal_sensitive":False,"disputed":False,"source_refs":["crisis-group-lake-chad"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-chad-army","entity_type":"organization","primary_type":"state_security_force","secondary_types":[],"slug":"chad-armed-forces","name_zh":"乍得国防与安全力量","name_en":"Chadian Defence and Security Forces","acronym":"","native_name":"","aliases":["FANT","Chadian Armed Forces"],"historical_names":[],"importance_level":"L2","short_description":"乍得国家军队与安全力量，MNJTF 主要成员并长期参与反恐。","current_status":"active","primary_category":"state_security_force","tags":["乍得","国家安全力量"],"region_ids":["region-lake-chad-basin","region-central-sahel"],"country_ids":["country-chad"],"confidence":"high","temporal_sensitive":False,"disputed":False,"source_refs":["crisis-group-lake-chad"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-nigeria-army","entity_type":"organization","primary_type":"state_security_force","secondary_types":[],"slug":"nigerian-armed-forces","name_zh":"尼日利亚武装部队","name_en":"Nigerian Armed Forces","acronym":"","native_name":"","aliases":["Nigerian Army"],"historical_names":[],"importance_level":"L2","short_description":"尼日利亚国家武装力量，对抗 JAS 与 ISWAP 的主要力量。","current_status":"active","primary_category":"state_security_force","tags":["尼日利亚","国家安全力量"],"region_ids":["region-lake-chad-basin"],"country_ids":["country-nigeria"],"confidence":"high","temporal_sensitive":False,"disputed":False,"source_refs":["crisis-group-lake-chad"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-cameroon-army","entity_type":"organization","primary_type":"state_security_force","secondary_types":[],"slug":"cameroon-armed-forces","name_zh":"喀麦隆武装部队","name_en":"Cameroon Armed Forces","acronym":"","native_name":"","aliases":["Cameroon Army"],"historical_names":[],"importance_level":"L3","short_description":"喀麦隆国家武装力量，在极北省对抗跨境武装威胁。","current_status":"active","primary_category":"state_security_force","tags":["喀麦隆","国家安全力量"],"region_ids":["region-lake-chad-basin"],"country_ids":["country-cameroon"],"confidence":"high","temporal_sensitive":False,"disputed":False,"source_refs":["crisis-group-lake-chad"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-benin-forces","entity_type":"organization","primary_type":"state_security_force","secondary_types":[],"slug":"benin-security-forces","name_zh":"贝宁安全力量","name_en":"Benin Security Forces","acronym":"","native_name":"","aliases":["Benin Armed Forces"],"historical_names":[],"importance_level":"L3","short_description":"贝宁国家武装与安全力量，应对北部跨境武装威胁。","current_status":"active","primary_category":"state_security_force","tags":["贝宁","国家安全力量"],"region_ids":["region-coastal-west-africa-spillover"],"country_ids":["country-benin"],"confidence":"high","temporal_sensitive":False,"disputed":False,"source_refs":["us-state-crt-2022"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-saf","entity_type":"organization","primary_type":"state_security_force","secondary_types":[],"slug":"sudanese-armed-forces","name_zh":"苏丹武装部队","name_en":"Sudanese Armed Forces","acronym":"SAF","native_name":"القوات المسلحة السودانية","aliases":["SAF","Sudanese Army"],"historical_names":[],"importance_level":"L1","short_description":"苏丹国家军队，2023 年 4 月起与 RSF 全面交战。","current_status":"active_conflict","primary_category":"state_security_force","tags":["苏丹","国家军队","内战"],"region_ids":["region-sudan-red-sea-horn"],"country_ids":["country-sudan"],"confidence":"high","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-sudan","un-sudan-reports"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-rsf","entity_type":"organization","primary_type":"militia","secondary_types":["political_movement"],"slug":"rapid-support-forces","name_zh":"快速支援部队","name_en":"Rapid Support Forces","acronym":"RSF","native_name":"قوات الدعم السريع","aliases":["RSF","Rapid Support Forces Sudan"],"historical_names":[],"importance_level":"L1","short_description":"源自达尔富尔武装的苏丹准军事力量，2023 年 4 月起与 SAF 全面交战。","current_status":"active_conflict","primary_category":"paramilitary_force","tags":["苏丹","准军事力量","内战"],"region_ids":["region-sudan-red-sea-horn"],"country_ids":["country-sudan"],"confidence":"high","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-sudan","un-sudan-reports"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-splm-n-al-hilu","entity_type":"organization","primary_type":"insurgent_group","secondary_types":[],"slug":"splm-n-al-hilu","name_zh":"苏丹人民解放运动—北方局（希卢派）","name_en":"SPLM-N (al-Hilu faction)","acronym":"SPLM-N","native_name":"","aliases":["SPLM-N al-Hilu"],"historical_names":[],"importance_level":"L2","short_description":"活跃于苏丹青尼罗与南科尔多凡的反政府武装派别。","current_status":"active","primary_category":"insurgent_group","tags":["苏丹","反政府武装"],"region_ids":["region-sudan-red-sea-horn"],"country_ids":["country-sudan"],"confidence":"medium_high","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-sudan"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-jem","entity_type":"organization","primary_type":"insurgent_group","secondary_types":[],"slug":"justice-equality-movement","name_zh":"正义与平等运动","name_en":"Justice and Equality Movement","acronym":"JEM","native_name":"حركة العدل والمساواة","aliases":["JEM"],"historical_names":[],"importance_level":"L2","short_description":"源自达尔富尔的武装运动，苏丹冲突中的关键武装派系之一。","current_status":"active","primary_category":"insurgent_group","tags":["达尔富尔","武装运动"],"region_ids":["region-sudan-red-sea-horn"],"country_ids":["country-sudan"],"confidence":"medium_high","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-sudan"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-slm-aw","entity_type":"organization","primary_type":"insurgent_group","secondary_types":[],"slug":"slm-aw","name_zh":"苏丹解放运动/解放军（阿卜杜勒·瓦希德派）","name_en":"Sudan Liberation Movement/Army (Abdel Wahid)","acronym":"SLM/A-AW","native_name":"","aliases":["SLM/A","Sudan Liberation Army"],"historical_names":[],"importance_level":"L3","short_description":"达尔富尔武装运动派别，苏丹冲突相关武装之一。","current_status":"active","primary_category":"insurgent_group","tags":["达尔富尔","武装运动"],"region_ids":["region-sudan-red-sea-horn"],"country_ids":["country-sudan"],"confidence":"medium","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-sudan"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"person-abdel-fattah-al-burhan","entity_type":"person","primary_type":"person","secondary_types":[],"slug":"abdel-fattah-al-burhan","name_zh":"阿卜杜勒·法塔赫·布尔汉","name_en":"Abdel Fattah al-Burhan","acronym":"","native_name":"عبد الفتاح البرهان","aliases":["al-Burhan"],"historical_names":[],"importance_level":"L2","short_description":"苏丹武装部队领导人，苏丹主权委员会主席（冲突爆发以来）。","current_status":"active","primary_category":"state_leader","tags":["苏丹","SAF领导人"],"region_ids":["region-sudan-red-sea-horn"],"country_ids":["country-sudan"],"confidence":"high","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-sudan"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"person-mohamed-hamdan-dagalo","entity_type":"person","primary_type":"person","secondary_types":[],"slug":"mohamed-hamdan-dagalo","name_zh":"穆罕默德·哈姆丹·达加洛","name_en":"Mohamed Hamdan Dagalo","acronym":"","native_name":"محمد حمدان دقلو","aliases":["Hemedti","赫梅蒂"],"historical_names":[],"importance_level":"L2","short_description":"快速支援部队（RSF）指挥官，苏丹冲突另一主要当事方领导人。","current_status":"active","primary_category":"paramilitary_leader","tags":["苏丹","RSF领导人"],"region_ids":["region-sudan-red-sea-horn"],"country_ids":["country-sudan"],"confidence":"high","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-sudan"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-sspdf","entity_type":"organization","primary_type":"state_security_force","secondary_types":[],"slug":"sspdf","name_zh":"南苏丹人民国防军","name_en":"South Sudan People's Defence Forces","acronym":"SSPDF","native_name":"","aliases":["SSPDF","SPLA（前称）"],"historical_names":["苏丹人民解放军（SPLA，2018 年前后更名）"],"importance_level":"L2","short_description":"南苏丹国家武装力量。","current_status":"active","primary_category":"state_security_force","tags":["南苏丹","国家军队"],"region_ids":["region-nile-basin-east-africa"],"country_ids":["country-south-sudan"],"confidence":"high","temporal_sensitive":False,"disputed":False,"source_refs":["crisis-group-south-sudan"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-splm-io","entity_type":"organization","primary_type":"political_movement","secondary_types":["insurgent_group"],"slug":"splm-io","name_zh":"苏丹人民解放运动/解放军—反对派","name_en":"SPLM/A-IO","acronym":"SPLM-IO","native_name":"","aliases":["SPLM-IO","SPLA-IO"],"historical_names":[],"importance_level":"L2","short_description":"南苏丹主要反对派政治-军事运动，与 SSPDF 存在周期性冲突。","current_status":"active","primary_category":"political_military_movement","tags":["南苏丹","反对派"],"region_ids":["region-nile-basin-east-africa"],"country_ids":["country-south-sudan"],"confidence":"high","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-south-sudan"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-nas","entity_type":"organization","primary_type":"political_movement","secondary_types":[],"slug":"national-salvation-front","name_zh":"全国拯救阵线","name_en":"National Salvation Front","acronym":"NAS","native_name":"","aliases":["NAS"],"historical_names":[],"importance_level":"L3","short_description":"南苏丹武装反对派团体之一。","current_status":"active","primary_category":"political_military_movement","tags":["南苏丹","反对派"],"region_ids":["region-nile-basin-east-africa"],"country_ids":["country-south-sudan"],"confidence":"medium","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-south-sudan"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"person-salva-kiir","entity_type":"person","primary_type":"person","secondary_types":[],"slug":"salva-kiir","name_zh":"萨尔瓦·基尔","name_en":"Salva Kiir Mayardit","acronym":"","native_name":"سلفا كير","aliases":["Salva Kiir"],"historical_names":[],"importance_level":"L2","short_description":"南苏丹总统。","current_status":"active","primary_category":"state_leader","tags":["南苏丹","国家领导人"],"region_ids":["region-nile-basin-east-africa"],"country_ids":["country-south-sudan"],"confidence":"high","temporal_sensitive":False,"disputed":False,"source_refs":["crisis-group-south-sudan"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"person-riek-machar","entity_type":"person","primary_type":"person","secondary_types":[],"slug":"riek-machar","name_zh":"里克·马沙尔","name_en":"Riek Machar","acronym":"","native_name":"ريك مشار","aliases":["Riek Machar"],"historical_names":[],"importance_level":"L2","short_description":"SPLM-IO 领导人，南苏丹第一副总统（多次任命）。","current_status":"active","primary_category":"political_leader","tags":["南苏丹","反对派领导人"],"region_ids":["region-nile-basin-east-africa"],"country_ids":["country-south-sudan"],"confidence":"high","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-south-sudan"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-is-mozambique","entity_type":"organization","primary_type":"terrorist_group","secondary_types":[],"slug":"is-mozambique","name_zh":"伊斯兰国莫桑比克省","name_en":"Islamic State Mozambique Province (IS-Mozambique)","acronym":"IS-Mozambique","native_name":"","aliases":["ISIS-Mozambique","IS-M","Ahlu Sunnah wa-Jama（旧称关联）","ASWJ（旧称关联）"],"historical_names":["圣训人民（Ansar al-Sunna，早期活动称法）","伊斯兰国中非省关联（IS-CAP）"],"importance_level":"L1","short_description":"莫桑比克德尔加杜角叛乱武装，2022 年前后正式以伊斯兰国莫桑比克省名义活动。","current_status":"active","primary_category":"islamic_state_aligned_network","tags":["莫桑比克","德尔加杜角","伊斯兰国"],"region_ids":["region-southeast-africa-mozambique"],"country_ids":["country-mozambique","country-tanzania"],"confidence":"medium_high","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-mozambique","us-state-crt-2022"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-fadm","entity_type":"organization","primary_type":"state_security_force","secondary_types":[],"slug":"mozambique-defence-forces","name_zh":"莫桑比克国防军","name_en":"Mozambique Defence Armed Forces","acronym":"FADM","native_name":"Forças Armadas de Defesa de Moçambique","aliases":["FADM","Mozambique Armed Defence Forces"],"historical_names":[],"importance_level":"L2","short_description":"莫桑比克国家武装力量，德尔加杜角反叛乱行动主力。","current_status":"active","primary_category":"state_security_force","tags":["莫桑比克","国家安全力量"],"region_ids":["region-southeast-africa-mozambique"],"country_ids":["country-mozambique"],"confidence":"high","temporal_sensitive":False,"disputed":False,"source_refs":["crisis-group-mozambique"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-rdf-mozambique","entity_type":"organization","primary_type":"regional_force","secondary_types":[],"slug":"rwanda-force-mozambique","name_zh":"卢旺达驻莫桑比克部队","name_en":"Rwanda Defence Force contingent in Mozambique","acronym":"","native_name":"","aliases":["RDF Mozambique","卢旺达部署力量"],"historical_names":[],"importance_level":"L2","short_description":"2021 年起部署于德尔加杜角的卢旺达部队，协助恢复安全。","current_status":"active","primary_category":"regional_security_force","tags":["莫桑比克","地区干预"],"region_ids":["region-southeast-africa-mozambique"],"country_ids":["country-mozambique"],"confidence":"high","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-mozambique"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-samim","entity_type":"organization","primary_type":"regional_force","secondary_types":[],"slug":"samim","name_zh":"南共体驻莫桑比克特派团","name_en":"SADC Mission in Mozambique","acronym":"SAMIM","native_name":"","aliases":["SAMIM"],"historical_names":[],"importance_level":"L3","short_description":"南共体（SADC）派驻德尔加杜角的任务团，2024 年前后完成撤出。","current_status":"historical_deployment","primary_category":"regional_security_force","tags":["莫桑比克","南共体"],"region_ids":["region-southeast-africa-mozambique"],"country_ids":["country-mozambique"],"confidence":"medium_high","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-mozambique"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-lna","entity_type":"organization","primary_type":"political_movement","secondary_types":["state_security_force"],"slug":"libyan-national-army","name_zh":"利比亚国民军","name_en":"Libyan National Army","acronym":"LNA","native_name":"الجيش الوطني الليبي","aliases":["LNA","Libyan Arab Armed Forces"],"historical_names":[],"importance_level":"L2","short_description":"以东部为基地的利比亚主要军事力量。","current_status":"active","primary_category":"political_military_movement","tags":["利比亚","东部军事力量"],"region_ids":["region-north-africa-sahara"],"country_ids":["country-libya"],"confidence":"medium_high","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-libya"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-gnu-forces","entity_type":"organization","primary_type":"state_security_force","secondary_types":[],"slug":"gnu-forces","name_zh":"民族团结政府相关安全力量","name_en":"Government of National Unity-aligned security forces","acronym":"GNU","native_name":"","aliases":["GNU forces"],"historical_names":[],"importance_level":"L2","short_description":"利比亚民族团结政府（GNU）相关武装与安全力量，以的黎波里为基地。","current_status":"active","primary_category":"state_security_force","tags":["利比亚","西部安全力量"],"region_ids":["region-north-africa-sahara"],"country_ids":["country-libya"],"confidence":"medium_high","temporal_sensitive":True,"disputed":False,"source_refs":["crisis-group-libya"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
 {"entity_id":"actor-isis-libya","entity_type":"organization","primary_type":"terrorist_group","secondary_types":[],"slug":"isis-libya","name_zh":"伊斯兰国利比亚分支","name_en":"ISIL-Libya (ISIS-Libya)","acronym":"ISIS-Libya","native_name":"","aliases":["ISIS-Libya","IS-Libya"],"historical_names":[],"importance_level":"L2","short_description":"伊斯兰国在利比亚的分支，控制区收缩后仍有残余活动。","current_status":"active_reduced","primary_category":"islamic_state_aligned_network","tags":["利比亚","伊斯兰国"],"region_ids":["region-north-africa-sahara"],"country_ids":["country-libya"],"confidence":"medium_high","temporal_sensitive":True,"disputed":False,"source_refs":["un-libya-reports","crisis-group-libya"],"last_verified_at":"2026-08-06","importance_review_status":"provisional","evidence_ids":[]},
]
# merge migrated + new entities, keep country entities in countries.json only
all_entities = migrated + NEW_ENTITIES
ids = [e["entity_id"] for e in all_entities]
assert len(ids) == len(set(ids)), "duplicate entity id"
w("entities.json", {"schema_version":"asip-intelligence-africa-v1.0","generated_at":"2026-08-06","entities":all_entities})
print("entities total:", len(all_entities))
