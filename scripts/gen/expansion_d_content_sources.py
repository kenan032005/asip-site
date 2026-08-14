# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-D — source content module.

Source of truth: ASIP-PPT-ENTITY-EXPANSION-D-Authoritative-Content-Pack.md.
WorkBuddy does not research independently; every source below is cited verbatim
from the authoritative pack.
"""

TODAY = "2026-08-14"
ACCESSED = "2026-08-14"
IMPORTER = "expansion-d"

# New sources (all URLs taken directly from the authoritative content pack).
NEW_SOURCES = [
    # ISIS-Sinai / ABM
    {"source_id": "expd-nctc-isis-sinai", "title": "ISIS-Sinai — National Counterterrorism Center profile", "publisher": "U.S. National Counterterrorism Center (NCTC)", "source_type": "official_counterterrorism_profile", "url": "https://www.dni.gov/nctc/terrorist_groups/isis_sinai.html", "published_at": "2025-05-01", "date_precision": "month", "reliability": "authoritative", "notes": "ISIS-Sinai 组织连续性（ABM 前身）、500+ 袭击、2023-02 最后一次 claimed 袭击、severely degraded 评估。"},
    {"source_id": "expd-ofac-2015-09-29", "title": "OFAC amendment — ISIL Sinai Province aliases", "publisher": "U.S. Department of the Treasury (OFAC)", "source_type": "sanctions_action", "url": "https://ofac.treasury.gov/recent-actions/20150929", "published_at": "2015-09-29", "date_precision": "day", "reliability": "authoritative", "notes": "2015 年美国对 ISIL/ISIS-Sinai 指定修正，纳入西奈省别名。"},
    {"source_id": "expd-dfat-egypt", "title": "Egypt country information (DFAT)", "publisher": "Australian Department of Foreign Affairs and Trade", "source_type": "country_current_profile", "url": "https://www.ecoi.net/en/document/2141293.html", "published_at": "2023-01-01", "date_precision": "year", "reliability": "authoritative", "notes": "埃及反恐与西奈安全形势背景。"},
    # Ansaroul Islam
    {"source_id": "expd-mapping-ansaroul-islam", "title": "Ansaroul Islam — profile", "publisher": "Mapping Militants Project (Stanford)", "source_type": "actor_profile", "url": "https://mappingmilitants.org/profiles/ansaroul-islam", "published_at": "2026-06-01", "date_precision": "month", "reliability": "research_institution", "notes": "Ansaroul Islam 成立、Ibrahim/Jafar Dicko、Nassoumbou 袭击、JNIM 整合。"},
    {"source_id": "expd-ctc-ansaroul-islam", "title": "Ansaroul Islam: Growing Terrorist Insurgency in Burkina Faso", "publisher": "CTC Sentinel, West Point", "source_type": "research_analysis", "url": "https://ctc.westpoint.edu/ansaroul-islam-growing-terrorist-insurgency-burkina-faso/", "published_at": "2017-01-01", "date_precision": "year", "reliability": "research_institution", "notes": "Ansaroul Islam 起源、Soum/Al-Irchad、Macina 网络联系。"},
    {"source_id": "expd-oecd-networks", "title": "Conflict Networks in North and West Africa", "publisher": "OECD", "source_type": "research_report", "url": "https://www.oecd.org/en/publications/conflict-networks-in-north-and-west-africa_896e3eca-en/full-report/networks-of-violence-in-north-and-west-africa_be95f83d.html", "published_at": "2021-01-01", "date_precision": "year", "reliability": "research_institution", "notes": "北非/西非冲突网络背景。"},
    # Katiba Hanifa
    {"source_id": "expd-africa-center-tactical-units", "title": "Tactical Units in West Africa", "publisher": "Africa Center for Strategic Studies", "source_type": "research_report", "url": "https://africacenter.org/wp-content/uploads/2026/02/ASB47EN-Tactical-Units-West-Africa.pdf", "published_at": "2026-02-01", "date_precision": "month", "reliability": "research_institution", "notes": "Katiba Hanifa 的跨境活动、IED、基础设施/安全部队袭击、尼日利亚前沿扩张。"},
    {"source_id": "expd-critical-threats-benin", "title": "Africa File — JNIM's growing pressure on Benin", "publisher": "Critical Threats Project (AEI)", "source_type": "research_analysis", "url": "https://www.criticalthreats.org/analysis/africa-file-april-24-2025-jnims-growing-pressure-on-benin-turkey-to-somalia-salafi-jihadi-cells-continue-to-grow-across-nigeria", "published_at": "2025-04-24", "date_precision": "day", "reliability": "research_institution", "notes": "Katiba Hanifa / JNIM 对贝宁、尼日利亚压力。"},
    # FPL
    {"source_id": "expd-reuters-niger-pipeline", "title": "Niger group claims attack on China-backed pipeline, threatens more", "publisher": "Reuters", "source_type": "newswire", "url": "https://www.reuters.com/world/africa/niger-group-claims-attack-china-backed-pipeline-threatens-more-2024-06-18/", "published_at": "2024-06-18", "date_precision": "day", "reliability": "news_media", "notes": "FPL 宣称 2024-06-16 袭击中资支持的尼日尔—贝宁输油管道并威胁继续。"},
    {"source_id": "expd-hrw-niger-2025", "title": "World Report 2025 — Niger", "publisher": "Human Rights Watch", "source_type": "human_rights_investigation", "url": "https://www.hrw.org/world-report/2025/country-chapters/niger", "published_at": "2025-01-01", "date_precision": "year", "reliability": "authoritative", "notes": "HRW 描述 FPL 为图布族反政府武装并宣称至少两次袭击管道。"},
    {"source_id": "expd-worldbank-niger-2026", "title": "Niger Country Context (2026)", "publisher": "World Bank", "source_type": "research_report", "url": "https://documents1.worldbank.org/curated/en/099042125174519328/pdf/P507762-11823c7e-3802-4550-a6b8-3b32963b85eb.pdf", "published_at": "2026-01-01", "date_precision": "year", "reliability": "authoritative", "notes": "FPL 与爱国正义阵线作为要求释放 Bazoum 的武装组织。"},
    {"source_id": "expd-ahram-fpl", "title": "FPL — Mahamoud Sallah 利比亚拘押与 2026 年 6 月释放", "publisher": "AFP / Ahram (French)", "source_type": "newswire", "url": "https://french.ahram.org.eg/UI/Front/Inner.aspx?NewsContentID=89988", "published_at": "2026-06-01", "date_precision": "month", "reliability": "news_media", "notes": "Mahamoud Sallah 被哈夫塔尔阵营拘押、2026 年 6 月获释。"},
    # FLA / JNIM 2026 coordination
    {"source_id": "expd-reuters-goita-2026-04-28", "title": "Mali's Goita meets Russian ambassador after attacks", "publisher": "Reuters", "source_type": "newswire", "url": "https://www.reuters.com/world/mali-military-leader-goita-meets-russian-ambassador-after-attacks-office-says-2026-04-28/", "published_at": "2026-04-28", "date_precision": "day", "reliability": "news_media", "notes": "2026 年 4 月 FLA 与 JNIM 协同袭击背景。"},
    {"source_id": "expd-ap-mali-2026", "title": "AP — Mali coordinated attacks (2026)", "publisher": "Associated Press", "source_type": "newswire", "url": "https://apnews.com/article/1da800823d7513f44daf5d1cbf532294", "published_at": "2026-04-28", "date_precision": "day", "reliability": "news_media", "notes": "FLA 与 JNIM 对马里军事政府协调袭击。"},
    {"source_id": "expd-bti-mali-2026", "title": "BTI 2026 Country Report — Mali", "publisher": "Bertelsmann Stiftung Transformation Index", "source_type": "research_report", "url": "https://bti-project.org/fileadmin/api/content/en/downloads/reports/country_report_2026_MLI.pdf", "published_at": "2026-01-01", "date_precision": "year", "reliability": "research_institution", "notes": "马里安全形势与武装组织格局。"},
    # Lions of the Caliphate (Morocco cell) — for excluded/cell audit
    {"source_id": "expd-reuters-morocco-cell", "title": "Morocco foils attacks by cell loyal to Islamic State", "publisher": "Reuters", "source_type": "newswire", "url": "https://www.reuters.com/world/africa/morocco-foils-attacks-by-cell-loyal-islamic-state-2025-02-24/", "published_at": "2025-02-24", "date_precision": "day", "reliability": "news_media", "notes": "摩洛哥 2025-02 破获 12 人“哈里发雄狮”小组。"},
    {"source_id": "expd-ap-morocco-cell", "title": "AP — Morocco dismantles ISIS cell", "publisher": "Associated Press", "source_type": "newswire", "url": "https://apnews.com/article/2eed405c45bd6dc068fe31b25f76315e", "published_at": "2025-02-24", "date_precision": "day", "reliability": "news_media", "notes": "摩洛哥破获 ISIS 关联小组。"},
    {"source_id": "expd-soufan-morocco", "title": "IntelBrief (2025-10-01)", "publisher": "The Soufan Center", "source_type": "research_analysis", "url": "https://thesoufancenter.org/intelbrief-2025-october-1/", "published_at": "2025-10-01", "date_precision": "day", "reliability": "research_institution", "notes": "摩洛哥小组与 ISIS-Sahel 指挥联系。"},
    {"source_id": "expd-hespress-bcij", "title": "BCIJ reveals details of dismantled Daesh-affiliated cell", "publisher": "Hespress", "source_type": "newswire", "url": "https://en.hespress.com/104391-bcij-reveals-details-of-recently-dismantled-daesh-affiliated-terrorist-cell.html", "published_at": "2025-02-25", "date_precision": "day", "reliability": "news_media", "notes": "摩洛哥 BCIJ 披露破获小组细节。"},
    # Yusuf Ghazi exclusion counter-evidence
    {"source_id": "expd-un-s2024-473", "title": "UN S/2024/473 — CAR situation report", "publisher": "United Nations", "source_type": "un_report", "url": "https://digitallibrary.un.org/record/4052901/files/S_2024_473-EN.pdf", "published_at": "2024-06-01", "date_precision": "month", "reliability": "authoritative", "notes": "UN 未确认“Yusuf Ghazi group”，将 Yaloké 地区 3 月 4 日交火归为 3R 关联武装分子。用于排除性说明。"},
    {"source_id": "expd-china-embassy-car", "title": "中国驻中非大使馆 — 雅洛科地区安全提醒", "publisher": "中国驻中非共和国大使馆", "source_type": "official_statement", "url": "https://cf.china-embassy.gov.cn/lsfw/202403/t20240311_11257088.htm", "published_at": "2024-03-11", "date_precision": "day", "reliability": "authoritative", "notes": "中方将雅洛科地区袭击者描述为不明武装团体，未确认“Yusuf Ghazi group”。"},
]

# Source ids already present in the repository that this round reuses (asserted to exist).
REUSED_SOURCE_IDS = [
    "us-state-crt-2022",
    "d2-hrw-burkina-2026-04-02",
    "deptha-reuters-mali-groups-2026-04-27",
    "d1-reuters-fla-jnim-2026-04-25",
    "deptha-reuters-fla-jnim-2026-07-04",
    "d2-africa-center-benin-2026",
    "d1-pax-fla-2024-11-30",
]
