#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Part 2: relationships, sources, evidence for ASIP Africa intelligence (I2-A)."""
import json
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

def rel(rid, slug, source, target, rtype, ring, status, summary, start, end, conf, refs, geo=None, why=None, uncertain=None, direction="bidirectional"):
    return {
        "relationship_id": rid, "slug": slug, "source_entity_id": source, "target_entity_id": target,
        "relationship_type": rtype, "direction": direction, "display_ring": ring, "current_status": status,
        "time_start": start, "time_end": end, "start_year": int(start[:4]) if start and start[:4].isdigit() else None,
        "confidence": conf, "relation_summary": summary, "formation_background": summary,
        "current_status_detail": status, "geographic_scope": geo or "未说明", "why_it_matters": why or summary,
        "uncertainties": uncertain or "以最新公开来源为准。", "source_refs": refs, "last_verified_at": "2026-08-06",
        "temporal_sensitive": status in ("reported_current_hostility","reported_current_affiliation","active_conflict","reported_leadership_status","reported_activity_presence","historical_cooperation_or_non_hostility_reported","reported_pledge_with_current_status_sensitive","active_reduced"),
        "disputed": False,
    }

# Migrate 20 demo relationships
demo_rels = load_demo("relationships.json")["relationships"]
migrated = []
for r in demo_rels:
    nr = {k: r[k] for k in r}
    nr.setdefault("slug", r["relationship_id"])
    nr.setdefault("display_ring", "inner")
    nr.setdefault("relation_summary", r.get("description", ""))
    nr.setdefault("formation_background", r.get("description", ""))
    nr.setdefault("current_status_detail", r.get("current_status", ""))
    nr.setdefault("geographic_scope", "未说明")
    nr.setdefault("why_it_matters", r.get("description", ""))
    nr.setdefault("uncertainties", "以最新公开来源为准。")
    migrated.append(nr)

# New relationships
NEW_RELS = [
 rel("rel-jas-iswap-conflict","jas-iswap-conflict","actor-jas","actor-iswap","hostile_to","middle","reported_current_hostility","2016 年 ISWAP 从博科圣地分裂后，两组织在乍得湖盆地持续敌对与竞争。","2016","", "medium_high", ["crisis-group-lake-chad","us-state-crt-2022"],"尼日利亚东北部、乍得湖周边","两大圣战网络的阵营竞争与地盘争夺影响乍得湖盆地安全。","分裂触发事件与各地方分支态度存在来源差异。"),
 rel("rel-jas-islamic-state-hostile","jas-islamic-state-hostile","actor-jas","actor-iswap","hostile_to","middle","historical_cooperation_or_non_hostility_reported","JAS 未加入伊斯兰国体系，与 ISWAP 长期敌对。","2016","","medium","crisis-group-lake-chad".split(",") if False else ["crisis-group-lake-chad"],"乍得湖盆地","同前。",""),
 rel("rel-iswap-islamic-state-affiliation","iswap-islamic-state-affiliation","actor-iswap","actor-al-qaida","affiliated_with","inner","reported_current_affiliation","ISWAP 于 2016 年宣誓效忠伊斯兰国并获承认。","2016","","high",["un-1267-list","crisis-group-lake-chad"],"乍得湖盆地","ISWAP 是伊斯兰国在非洲主要省分支之一。","具体指挥与协调深度缺乏公开一致说明。"),
 rel("rel-iswap-alqaida-hostile","iswap-alqaida-hostile","actor-iswap","actor-al-qaida","hostile_to","middle","reported_current_hostility","ISWAP 与基地组织体系在乍得湖盆地及萨赫勒呈阵营敌对。","2016","","medium",["crisis-group-lake-chad"],"乍得湖盆地、萨赫勒","同前。",""),
 rel("rel-chad-mnjtf-member","chad-mnjtf-member","actor-chad-army","actor-mnjtf","member_of_force","inner","active","乍得国防力量是 MNJTF 主要成员之一。","2015","","high",["crisis-group-lake-chad"],"乍得湖盆地","体现乍得在区域反恐中的核心角色。",""),
 rel("rel-nigeria-mnjtf-member","nigeria-mnjtf-member","actor-nigeria-army","actor-mnjtf","member_of_force","inner","active","尼日利亚武装部队是 MNJTF 主要成员。","2015","","high",["crisis-group-lake-chad"],"乍得湖盆地","",""),
 rel("rel-cameroon-mnjtf-member","cameroon-mnjtf-member","actor-cameroon-army","actor-mnjtf","member_of_force","inner","active","喀麦隆武装部队是 MNJTF 成员。","2015","","high",["crisis-group-lake-chad"],"乍得湖盆地","",""),
 rel("rel-jas-chad-spillover","jas-chad-spillover","actor-jas","country-chad","operates_in","inner","reported_activity_presence","JAS 对乍得湖区构成跨境袭击威胁。","2015","","medium_high",["crisis-group-lake-chad"],"乍得湖区","跨境活动不表示控制。",""),
 rel("rel-jas-nigeria-operates","jas-nigeria-operates","actor-jas","country-nigeria","operates_in","inner","reported_activity_presence","JAS 主要活动于尼日利亚东北部。","2010","","medium_high",["crisis-group-lake-chad"],"博尔诺州等","",""),
 rel("rel-iswap-nigeria-operates","iswap-nigeria-operates","actor-iswap","country-nigeria","operates_in","inner","reported_activity_presence","ISWAP 在尼日利亚东北部活动。","2016","","medium_high",["crisis-group-lake-chad"],"博尔诺州等","",""),
 rel("rel-jas-cameroon-spillover","jas-cameroon-spillover","actor-jas","country-cameroon","operates_in","inner","reported_activity_presence","JAS 跨境袭击影响喀麦隆极北省。","2014","","medium_high",["crisis-group-lake-chad"],"极北省","",""),
 rel("rel-saf-rsf-war","saf-rsf-war","actor-saf","actor-rsf","hostile_to","middle","active_conflict","2023 年 4 月起 SAF 与 RSF 全面交战，苏丹内战持续。","2023","","high",["crisis-group-sudan","un-sudan-reports"],"苏丹全境","苏丹内战是当前非洲最严重的安全危机之一。","停火与政治进程反复；各地方战线状态差异大。"),
 rel("rel-burhan-saf-leads","burhan-saf-leads","actor-saf","person-abdel-fattah-al-burhan","led_by","outer","reported_leadership_status","布尔汉领导苏丹武装部队。","2019","","high",["crisis-group-sudan"],"苏丹","",""),
 rel("rel-dagalo-rsf-leads","dagalo-rsf-leads","actor-rsf","person-mohamed-hamdan-dagalo","led_by","outer","reported_leadership_status","达加洛指挥快速支援部队。","2013","","high",["crisis-group-sudan"],"苏丹","",""),
 rel("rel-splm-n-saf-conflict","splm-n-saf-conflict","actor-splm-n-al-hilu","actor-saf","hostile_to","middle","active_conflict","SPLM-N（希卢派）与苏丹武装部队在青尼罗与南科尔多凡冲突。","2011","","medium_high",["crisis-group-sudan"],"青尼罗、南科尔多凡","",""),
 rel("rel-jem-saf-conflict","jem-saf-conflict","actor-jem","actor-saf","hostile_to","middle","reported_current_hostility","正义与平等运动与苏丹武装部队历史上敌对，内战期间立场复杂。","2003","","medium",["crisis-group-sudan"],"达尔富尔","",""),
 rel("rel-rsf-darfur-origin","rsf-darfur-origin","actor-rsf","actor-jem","historically_associated_with","inner","historical","RSF 源自达尔富尔武装（金戈威德），与达尔富尔各武装运动关系复杂。","2003","","medium",["crisis-group-sudan"],"达尔富尔","",""),
 rel("rel-splm-io-sspdf-conflict","splm-io-sspdf-conflict","actor-splm-io","actor-sspdf","hostile_to","middle","reported_current_hostility","SPLM-IO 与 SSPDF 在南苏丹周期性冲突。","2013","","medium_high",["crisis-group-south-sudan"],"南苏丹多州","",""),
 rel("rel-kiir-sspdf-leads","kiir-sspdf-leads","actor-sspdf","person-salva-kiir","led_by","outer","reported_leadership_status","萨尔瓦·基尔作为总统领导南苏丹与 SSPDF 体系。","2011","","high",["crisis-group-south-sudan"],"南苏丹","",""),
 rel("rel-machar-splm-io-leads","machar-splm-io-leads","actor-splm-io","person-riek-machar","led_by","outer","reported_leadership_status","里克·马沙尔领导 SPLM-IO。","2013","","high",["crisis-group-south-sudan"],"南苏丹","",""),
 rel("rel-nas-splm-io-allied","nas-splm-io-allied","actor-nas","actor-splm-io","allied_with","middle","reported_current_alliance","全国拯救阵线曾与 SPLM-IO 等反对派力量联合。","2017","","medium",["crisis-group-south-sudan"],"南苏丹","",""),
 rel("rel-is-moz-islamic-state","is-moz-islamic-state","actor-is-mozambique","actor-al-qaida","affiliated_with","inner","reported_current_affiliation","IS-Mozambique 以伊斯兰国省分支名义活动（注意：本关系在数据层指向伊斯兰国体系占位实体，页面显示为伊斯兰国非洲网络关联）。","2019","","medium_high",["crisis-group-mozambique","us-state-crt-2022"],"德尔加杜角","名称与组织边界在不同来源中存在差异（ASWJ/ISIS-M/IS-CAP）。",""),
 rel("rel-is-moz-islamic-state2","is-moz-islamic-state2","actor-is-mozambique","actor-iswap","historically_associated_with","middle","reported_current_affiliation","IS-Mozambique 与伊斯兰国非洲省网络（含 ISWAP 体系）存在关联，但具体组织边界来源不一。","2019","","medium",["crisis-group-mozambique"],"东南部非洲","",""),
 rel("rel-fadm-is-moz-hostile","fadm-is-moz-hostile","actor-fadm","actor-is-mozambique","fought_against","middle","active_conflict","莫桑比克国防军与 IS-Mozambique 在德尔加杜角交战。","2017","","high",["crisis-group-mozambique"],"德尔加杜角","",""),
 rel("rel-rdf-mozambique-fadm-cooperate","rdf-mozambique-fadm-cooperate","actor-rdf-mozambique","actor-fadm","cooperates_with","middle","active","卢旺达部队与莫桑比克国防军协同反叛乱。","2021","","high",["crisis-group-mozambique"],"德尔加杜角","",""),
 rel("rel-samim-fadm-cooperate","samim-fadm-cooperate","actor-samim","actor-fadm","cooperates_with","middle","historical_deployment","SAMIM 与莫桑比克国防军合作后于 2024 年前后撤出。","2021","2024","medium_high",["crisis-group-mozambique"],"德尔加杜角","",""),
 rel("rel-lna-gnu-rivalry","lna-gnu-rivalry","actor-lna","actor-gnu-forces","hostile_to","middle","reported_current_hostility","利比亚国民军与民族团结政府相关力量政治-军事对立持续。","2014","","medium_high",["crisis-group-libya"],"利比亚","",""),
 rel("rel-isis-libya-affiliation","isis-libya-affiliation","actor-isis-libya","actor-al-qaida","affiliated_with","inner","reported_current_affiliation","ISIS-Libya 属伊斯兰国体系（数据层指向伊斯兰国体系占位实体，页面显示为伊斯兰国网络）。","2014","","medium_high",["un-libya-reports","crisis-group-libya"],"利比亚","",""),
 rel("rel-isis-libya-lna-conflict","isis-libya-lna-conflict","actor-isis-libya","actor-lna","hostile_to","middle","reported_current_hostility","ISIS-Libya 与利比亚国民军等力量交战。","2015","","medium_high",["crisis-group-libya"],"利比亚","",""),
 rel("rel-jnim-benin-spillover","jnim-benin-spillover","actor-jnim","country-benin","operates_in","inner","reported_activity_presence","JNIM 相关跨境活动与袭击影响贝宁北部。","2019","","medium_high",["us-state-crt-2022"],"贝宁北部","跨境渗透不表示控制。",""),
 rel("rel-is-benin-spillover","is-benin-spillover","actor-is-sahel","country-benin","operates_in","inner","reported_activity_presence","IS Sahel 相关跨境活动与袭击影响贝宁北部。","2019","","medium",["us-state-crt-2022"],"贝宁北部","跨境渗透不表示控制。",""),
 rel("rel-jnim-benin-forces-fought","jnim-benin-forces-fought","actor-jnim","actor-benin-forces","fought_against","middle","reported_current_hostility","贝宁安全力量与跨境武装在北部发生交火。","2021","","medium",["us-state-crt-2022"],"贝宁北部","",""),
 rel("rel-mnjtf-lakechad-operates","mnjtf-lakechad-operates","actor-mnjtf","country-chad","operates_in","inner","active","MNJTF 在乍得湖盆地（含乍得湖区）执行反恐任务。","2015","","high",["crisis-group-lake-chad"],"乍得湖盆地","",""),
 rel("rel-iswap-chad-spillover","iswap-chad-spillover","actor-iswap","country-chad","operates_in","inner","reported_activity_presence","ISWAP 跨境活动影响乍得湖区。","2016","","medium_high",["crisis-group-lake-chad"],"乍得湖区","",""),
 rel("rel-iswap-cameroon-spillover","iswap-cameroon-spillover","actor-iswap","country-cameroon","operates_in","inner","reported_activity_presence","ISWAP 跨境活动影响喀麦隆极北省。","2016","","medium_high",["crisis-group-lake-chad"],"极北省","",""),
 rel("rel-rsf-sudan-operates","rsf-sudan-operates","actor-rsf","country-sudan","operates_in","inner","active_conflict","RSF 在苏丹多地区（含达尔富尔、喀土穆周边）作战与存在。","2023","","high",["crisis-group-sudan"],"苏丹全境","",""),
 rel("rel-saf-sudan-operates","saf-sudan-operates","actor-saf","country-sudan","operates_in","inner","active_conflict","SAF 在苏丹多地区作战与存在。","2023","","high",["crisis-group-sudan"],"苏丹全境","",""),
 rel("rel-sudan-chad-spillover","sudan-chad-spillover","actor-rsf","country-chad","cross_border_link","outer","reported_activity_presence","苏丹冲突（RSF 相关动态）外溢影响乍得东部边境。","2023","","medium",["crisis-group-sudan"],"乍得东部","",""),
 rel("rel-ssudan-sudan-spillover","ssudan-sudan-spillover","actor-saf","country-south-sudan","cross_border_link","outer","reported_activity_presence","苏丹冲突外溢影响南苏丹北部边境安全。","2023","","medium",["un-sudan-reports"],"南苏丹北部边境","",""),
 rel("rel-is-moz-tanzania-link","is-moz-tanzania-link","actor-is-mozambique","country-tanzania","cross_border_link","outer","reported_activity_presence","IS-Mozambique 与坦桑尼亚南部边境存在跨境关联。","2019","","medium",["crisis-group-mozambique"],"坦桑尼亚南部","",""),
 rel("rel-fadm-mozambique-operates","fadm-mozambique-operates","actor-fadm","country-mozambique","operates_in","inner","active","莫桑比克国防军在德尔加杜角等省执行任务。","2017","","high",["crisis-group-mozambique"],"德尔加杜角","",""),
 rel("rel-is-moz-mozambique-operates","is-moz-mozambique-operates","actor-is-mozambique","country-mozambique","operates_in","inner","active_conflict","IS-Mozambique 在德尔加杜角省活动。","2017","","high",["crisis-group-mozambique"],"德尔加杜角","活动不表示控制。",""),
]
# relationships involving MNJTF-chad already covered; keep ID uniqueness
all_rels = migrated + NEW_RELS
ids = [r["relationship_id"] for r in all_rels]
assert len(ids) == len(set(ids)), "duplicate relation id: " + str([x for x in ids if ids.count(x) > 1][:5])
# fix the IS-affiliation targets: point to actor-islamic-state (transnational IS network placeholder)
for r in all_rels:
    if r["relationship_id"] in ("rel-is-moz-islamic-state","rel-isis-libya-affiliation","rel-iswap-islamic-state-affiliation"):
        r["target_entity_id"] = "actor-islamic-state"
        r["relation_summary"] = r["relation_summary"].replace("伊斯兰国体系占位实体","伊斯兰国跨国网络")
        r["formation_background"] = r["relation_summary"]
w("relationships.json", {"schema_version":"asip-intelligence-africa-v1.0","generated_at":"2026-08-06","relationships":all_rels})
print("relationships total:", len(all_rels))
