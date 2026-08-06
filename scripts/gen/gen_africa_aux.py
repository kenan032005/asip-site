#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Part 5: force estimates, external links, alias/graph index for Africa (I2-A)."""
import json
from pathlib import Path

ROOT = Path(r'C:/Users/kenan/WorkBuddy/recovery/asip-intelligence-v02-clean')
DEMO = ROOT / "data" / "intelligence" / "demo"
OUT = ROOT / "data" / "intelligence" / "africa"

def w(name, data):
    with (OUT / name).open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("wrote", name)

# force estimates: migrate JNIM/IS Sahel + add cautious entries
demo_estimates = json.loads((DEMO / "force_estimates.json").read_text(encoding="utf-8"))["estimates"]
estimates = dict(demo_estimates)
estimates.setdefault("actor-jas", [
 {"estimate_min":None,"estimate_max":None,"estimate_text":"暂无可靠公开区间估计","estimate_date":"2024年","estimate_scope":"JAS 整体战斗人员","included_components":"未说明","excluded_components":"未说明","source_ids":["crisis-group-lake-chad"],"confidence":"low","trend":"不明","notes":"公开来源未给出稳定区间，本平台不自行推算。"}])
estimates.setdefault("actor-iswap", [
 {"estimate_min":None,"estimate_max":None,"estimate_text":"暂无可靠公开区间估计","estimate_date":"2024年","estimate_scope":"ISWAP 整体战斗人员","included_components":"未说明","excluded_components":"未说明","source_ids":["crisis-group-lake-chad"],"confidence":"low","trend":"不明","notes":"公开来源未给出稳定区间，本平台不自行推算。"}])
estimates.setdefault("actor-is-mozambique", [
 {"estimate_min":None,"estimate_max":None,"estimate_text":"暂无可靠公开区间估计","estimate_date":"2024年","estimate_scope":"IS-Mozambique 战斗人员","included_components":"未说明","excluded_components":"未说明","source_ids":["crisis-group-mozambique"],"confidence":"low","trend":"不明","notes":"不同来源估计差异大且口径不一，本平台不自行推算。"}])
w("force_estimates.json", {"schema_version":"asip-intelligence-africa-v1.0","generated_at":"2026-08-06","estimates":estimates})

# external links: migrate demo links + new real Wikipedia pages
demo_links = json.loads((DEMO / "external_links.json").read_text(encoding="utf-8"))["links"]
links = dict(demo_links)
NEW_LINKS = {
 "actor-jas":{"wikipedia":[{"language":"en","label":"Boko Haram","url":"https://en.wikipedia.org/wiki/Boko_Haram"}],"authoritative":[],"research":[]},
 "actor-iswap":{"wikipedia":[{"language":"en","label":"Islamic State – West Africa Province","url":"https://en.wikipedia.org/wiki/Islamic_State_%E2%80%93_West_Africa_Province"}],"authoritative":[],"research":[]},
 "actor-mnjtf":{"wikipedia":[{"language":"en","label":"Multinational Joint Task Force","url":"https://en.wikipedia.org/wiki/Multinational_Joint_Task_Force"}],"authoritative":[],"research":[]},
 "actor-chad-army":{"wikipedia":[{"language":"en","label":"Chadian National Army","url":"https://en.wikipedia.org/wiki/Chadian_National_Army"}],"authoritative":[],"research":[]},
 "actor-nigeria-army":{"wikipedia":[{"language":"en","label":"Nigerian Armed Forces","url":"https://en.wikipedia.org/wiki/Nigerian_Armed_Forces"}],"authoritative":[],"research":[]},
 "actor-cameroon-army":{"wikipedia":[{"language":"en","label":"Cameroon Armed Forces","url":"https://en.wikipedia.org/wiki/Cameroon_Armed_Forces"}],"authoritative":[],"research":[]},
 "actor-saf":{"wikipedia":[{"language":"en","label":"Sudanese Armed Forces","url":"https://en.wikipedia.org/wiki/Sudanese_Armed_Forces"}],"authoritative":[],"research":[]},
 "actor-rsf":{"wikipedia":[{"language":"en","label":"Rapid Support Forces","url":"https://en.wikipedia.org/wiki/Rapid_Support_Forces"}],"authoritative":[],"research":[]},
 "actor-splm-n-al-hilu":{"wikipedia":[{"language":"en","label":"SPLM-N (al-Hilu)","url":"https://en.wikipedia.org/wiki/SPLM-N_(al-Hilu)"}],"authoritative":[],"research":[]},
 "actor-jem":{"wikipedia":[{"language":"en","label":"Justice and Equality Movement","url":"https://en.wikipedia.org/wiki/Justice_and_Equality_Movement"}],"authoritative":[],"research":[]},
 "actor-slm-aw":{"wikipedia":[{"language":"en","label":"Sudan Liberation Movement/Army","url":"https://en.wikipedia.org/wiki/Sudan_Liberation_Movement/Army"}],"authoritative":[],"research":[]},
 "person-abdel-fattah-al-burhan":{"wikipedia":[{"language":"en","label":"Abdel Fattah al-Burhan","url":"https://en.wikipedia.org/wiki/Abdel_Fattah_al-Burhan"}],"authoritative":[],"research":[]},
 "person-mohamed-hamdan-dagalo":{"wikipedia":[{"language":"en","label":"Mohamed Hamdan Dagalo","url":"https://en.wikipedia.org/wiki/Mohamed_Hamdan_Dagalo"}],"authoritative":[],"research":[]},
 "actor-sspdf":{"wikipedia":[{"language":"en","label":"South Sudan People's Defence Forces","url":"https://en.wikipedia.org/wiki/South_Sudan_People%27s_Defence_Forces"}],"authoritative":[],"research":[]},
 "actor-splm-io":{"wikipedia":[{"language":"en","label":"SPLM-IO","url":"https://en.wikipedia.org/wiki/SPLM-IO"}],"authoritative":[],"research":[]},
 "person-salva-kiir":{"wikipedia":[{"language":"en","label":"Salva Kiir Mayardit","url":"https://en.wikipedia.org/wiki/Salva_Kiir_Mayardit"}],"authoritative":[],"research":[]},
 "person-riek-machar":{"wikipedia":[{"language":"en","label":"Riek Machar","url":"https://en.wikipedia.org/wiki/Riek_Machar"}],"authoritative":[],"research":[]},
 "actor-is-mozambique":{"wikipedia":[{"language":"en","label":"Insurgency in Cabo Delgado","url":"https://en.wikipedia.org/wiki/Insurgency_in_Cabo_Delgado"}],"authoritative":[],"research":[]},
 "actor-fadm":{"wikipedia":[{"language":"pt","label":"Forças Armadas de Defesa de Moçambique","url":"https://pt.wikipedia.org/wiki/For%C3%A7as_Armadas_de_Defesa_de_Mo%C3%A7ambique"}],"authoritative":[],"research":[]},
 "actor-rdf-mozambique":{"wikipedia":[{"language":"en","label":"Rwanda Defence Force","url":"https://en.wikipedia.org/wiki/Rwanda_Defence_Force"}],"authoritative":[],"research":[]},
 "actor-samim":{"wikipedia":[{"language":"en","label":"SADC Mission in Mozambique","url":"https://en.wikipedia.org/wiki/SADC_Mission_in_Mozambique"}],"authoritative":[],"research":[]},
 "actor-lna":{"wikipedia":[{"language":"en","label":"Libyan National Army","url":"https://en.wikipedia.org/wiki/Libyan_National_Army"}],"authoritative":[],"research":[]},
 "actor-gnu-forces":{"wikipedia":[{"language":"en","label":"Government of National Unity (Libya)","url":"https://en.wikipedia.org/wiki/Government_of_National_Unity_(Libya)"}],"authoritative":[],"research":[]},
 "actor-isis-libya":{"wikipedia":[{"language":"en","label":"ISIL in Libya","url":"https://en.wikipedia.org/wiki/Islamic_State_in_Libya"}],"authoritative":[],"research":[]},
 "actor-islamic-state":{"wikipedia":[{"language":"en","label":"Islamic State","url":"https://en.wikipedia.org/wiki/Islamic_State"}],"authoritative":[],"research":[]},
}
links.update(NEW_LINKS)
w("external_links.json", {"schema_version":"asip-intelligence-africa-v1.0","generated_at":"2026-08-06","links":links})

# alias index
entities = json.loads((OUT / "entities.json").read_text(encoding="utf-8"))["entities"]
aliases = {}
for e in entities:
    keys = [e["name_zh"], e["name_en"]]
    if e.get("acronym"): keys.append(e["acronym"])
    if e.get("native_name"): keys.append(e["native_name"])
    for a in e.get("aliases", []): keys.append(a)
    for k in keys:
        if k and k.strip():
            aliases[k.strip().lower()] = e["entity_id"]
w("alias_index.json", {"schema_version":"asip-intelligence-africa-v1.0","aliases":dict(sorted(aliases.items()))})

# graph index
rels = json.loads((OUT / "relationships.json").read_text(encoding="utf-8"))["relationships"]
regions = json.loads((OUT / "regions.json").read_text(encoding="utf-8"))["regions"]
countries = json.loads((OUT / "countries.json").read_text(encoding="utf-8"))["countries"]
graph = {
 "schema_version":"asip-intelligence-africa-v1.0","default_focus":"actor-jnim","max_nodes":24,
 "nodes":[e["entity_id"] for e in entities],
 "regions":[r["region_id"] for r in regions],
 "countries":[c["country_id"] for c in countries],
 "relationship_ids":[r["relationship_id"] for r in rels],
 "relation_slugs":[r.get("slug") or r["relationship_id"] for r in rels],
 "relationship_types":sorted({r["relationship_type"] for r in rels}),
 "rings":["inner","middle","outer"],"importance_levels":["L1","L2","L3"],
 "risk_levels":["extreme","high","medium","low"],
}
w("graph_index.json", graph)
print("aliases:", len(aliases), "relations:", len(rels), "regions:", len(regions), "countries:", len(countries))
