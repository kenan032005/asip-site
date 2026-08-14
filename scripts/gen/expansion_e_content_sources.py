# -*- coding: utf-8 -*-
"""ASIP-PPT-ENTITY-EXPANSION-E — source content module (regional security actors).

Source of truth: ASIP-PPT-ENTITY-EXPANSION-E-Authoritative-Content-Pack.md.
WorkBuddy does not research independently; all URLs are verbatim from the pack.
"""

TODAY = "2026-08-14"
ACCESSED = "2026-08-14"
IMPORTER = "expansion-e"

NEW_SOURCES = [
    # MNJTF
    {"source_id": "expe-au-psc-mnjtf-2025-12", "title": "Communiqué of the 1318th PSC meeting (15 Dec 2025) — MNJTF mandate renewal", "publisher": "African Union Peace and Security Council", "source_type": "official_au_communique", "url": "https://aupaps.org/en/article/communique-of-the-1318th-meeting-of-the-psc-held-on-15-december-2025-on-consideration-of-the-report-of-the-chairperson-of-the-au-commission-on-the-activities-of-the-multinational-joint-task-force-mnjtf-against-the-boko-haram-terrorist-group-and-renewal", "published_at": "2025-12-15", "date_precision": "day", "reliability": "authoritative", "notes": "MNJTF 授权更新 2026-02-01 至 2027-01-31；Operation Lake Sanity 2；Niger 退出关切。"},
    {"source_id": "expe-print-niger-mnjtf-withdraw", "title": "Niger withdraws from Lake Chad military force", "publisher": "ThePrint", "source_type": "newswire", "url": "https://theprint.in/world/niger-withdraws-from-lake-chad-military-force/2571689/", "published_at": "2025-03-01", "date_precision": "month", "reliability": "news_media", "notes": "尼日尔 2025 年 3 月退出 MNJTF。"},
    {"source_id": "expe-reuters-chad-mnjtf-threat", "title": "Chad threatens to withdraw from multinational security force", "publisher": "Reuters", "source_type": "newswire", "url": "https://www.reuters.com/world/africa/chad-threatens-withdraw-multinational-security-force-2024-11-04/", "published_at": "2024-11-04", "date_precision": "day", "reliability": "news_media", "notes": "乍得 2024-11 威胁退出 MNJTF（威胁，非已完成退出）。"},
    # G5 Sahel
    {"source_id": "expe-un-sc15950-g5", "title": "Security Council 15950th meeting (Dec 2024) — G5 Sahel Joint Force ceased operations", "publisher": "United Nations", "source_type": "un_statement", "url": "https://press.un.org/en/2024/sc15950.doc.htm", "published_at": "2024-12-01", "date_precision": "month", "reliability": "authoritative", "notes": "G5 Sahel 联合部队停止运作。"},
    # AES
    {"source_id": "expe-print-aes-5000", "title": "Junta-led Sahel states ready joint force of 5,000 troops, says minister", "publisher": "ThePrint", "source_type": "newswire", "url": "https://theprint.in/world/junta-led-sahel-states-ready-joint-force-of-5000-troops-says-minister/2456973/", "published_at": "2025-01-01", "date_precision": "month", "reliability": "news_media", "notes": "2025-01 尼日尔防长宣布约 5000 人统一部队接近就绪。"},
    {"source_id": "expe-print-aes-russia", "title": "Russia vows military backing for Sahel juntas' joint force", "publisher": "ThePrint", "source_type": "newswire", "url": "https://theprint.in/world/russia-vows-military-backing-for-sahel-juntas-joint-force/2578533/", "published_at": "2025-04-01", "date_precision": "month", "reliability": "news_media", "notes": "俄罗斯承诺提供武器/训练/技术支持。"},
    {"source_id": "expe-lesahel-aes-command", "title": "Force unifiée de l'AES : l'esprit de la défense collective en marche, le commandement en place", "publisher": "Le Sahel (Niger)", "source_type": "official_self_source", "url": "https://www.lesahel.org/force-unifiee-de-laes-lesprit-de-la-defense-collective-en-marche-le-commandement-en-place/", "published_at": "2025-12-01", "date_precision": "month", "reliability": "official", "notes": "2025-12 尼日尔官方：统一部队成形、指挥架构就位。"},
    # ECOWAS
    {"source_id": "expe-ecowas-ccds-43", "title": "43rd ordinary meeting of ECOWAS Committee of Chiefs of Staff", "publisher": "ECOWAS", "source_type": "official_statement", "url": "https://www.ecowas.int/43rd-ordinary-meeting-of-the-ecowas-committee-of-chiefs-of-staff-ccds-fight-against-the-growing-threat-of-terrorism-in-the-region-on-the-agenda/", "published_at": "2025-01-01", "date_precision": "year", "reliability": "authoritative", "notes": "ECOWAS 反恐力量规划。"},
    {"source_id": "expe-ecowas-ministers-funding", "title": "ECOWAS ministers meet on counterterrorism force financing", "publisher": "ECOWAS", "source_type": "official_statement", "url": "https://www.ecowas.int/les-ministres-de-la-cedeao-se-reunissent-a-abuja-pour-faire-avancer-les-modalites-de-financement-de-la-force-regionale-de-lutte-contre-le-terrorisme/", "published_at": "2025-01-01", "date_precision": "year", "reliability": "authoritative", "notes": "ECOWAS 反恐力量融资机制。"},
    {"source_id": "expe-ecowas-esf-readiness", "title": "ECOWAS Standby Force conducts operational readiness inspection of Guinea's pledged motorized company", "publisher": "ECOWAS", "source_type": "official_statement", "url": "https://www.ecowas.int/ecowas-standby-force-conducts-operational-readiness-inspection-of-guineas-pledged-motorized-company/", "published_at": "2026-01-01", "date_precision": "year", "reliability": "authoritative", "notes": "2026 年 ESF 战备检查。"},
    # SAMIM
    {"source_id": "expe-sadc-samim-closure", "title": "Withdrawal of SAMIM force / SAMIM officially closed 15 July 2024", "publisher": "SADC", "source_type": "official_statement", "url": "https://www.sadc.int/latest-news/withdrawal-southern-african-development-community-mission-mozambique-samim-force", "published_at": "2024-07-15", "date_precision": "day", "reliability": "authoritative", "notes": "SAMIM 2024-07-15 正式结束。"},
    # FADM
    {"source_id": "expe-fadm-official", "title": "FADM — official structure (General Staff / Army / Navy / Air Force)", "publisher": "Ministry of National Defence of Mozambique", "source_type": "official_mission_page", "url": "https://mdn.gov.mz/index.php/fadm/", "published_at": "2026-01-01", "date_precision": "year", "reliability": "authoritative", "notes": "FADM 官方结构。"},
    {"source_id": "expe-fadm-emg", "title": "Estado-Maior General das FADM", "publisher": "Ministry of National Defence of Mozambique", "source_type": "official_mission_page", "url": "https://mdn.gov.mz/index.php/emg/", "published_at": "2026-01-01", "date_precision": "year", "reliability": "authoritative", "notes": "FADM 总参谋部。"},
    # RDF / RSF
    {"source_id": "expe-rwanda-joint-force", "title": "Rwanda deploys joint force to Mozambique", "publisher": "Government of Rwanda", "source_type": "official_self_source", "url": "https://www.gov.rw/blog-detail/rwanda-deploys-joint-force-to-mozambique", "published_at": "2021-07-01", "date_precision": "month", "reliability": "authoritative", "notes": "2021-07 卢旺达部署 RDF+RNP 联合部队。"},
    {"source_id": "expe-acled-rwanda-moz", "title": "Rwanda in Mozambique — limits of civilian protection (ACLED)", "publisher": "ACLED", "source_type": "research_analysis", "url": "https://acleddata.com/report/rwanda-mozambique-limits-civilian-protection", "published_at": "2024-05-01", "date_precision": "month", "reliability": "research_institution", "notes": "ACLED 估算 2024-05 约 4000 卢旺达人员（分析性估计，非官方 2026 兵力）。"},
    # TPDF
    {"source_id": "expe-acled-cabo-ligado-tpdf", "title": "Cabo Ligado update (18 May 2025) — TPDF bilateral presence", "publisher": "ACLED", "source_type": "research_analysis", "url": "https://acleddata.com/update/cabo-ligado-update-5-18-may-2025", "published_at": "2025-05-18", "date_precision": "day", "reliability": "research_institution", "notes": "TPDF 双边部署延续。"},
    # Africa Corps / Wagner
    {"source_id": "expe-yahoo-wagner-mali", "title": "Russia's Wagner mercenary group says it will leave Mali", "publisher": "Yahoo News / Reuters", "source_type": "newswire", "url": "https://www.yahoo.com/news/russias-wagner-mercenary-group-says-150606377.html", "published_at": "2025-06-01", "date_precision": "month", "reliability": "news_media", "notes": "瓦格纳 2025-06 宣布离开马里，非洲军团留驻。"},
    {"source_id": "expe-reuters-africa-corps-civilian", "title": "Russia's Africa Corps kills Mali civilians in indiscriminate attack, rights group says", "publisher": "Reuters", "source_type": "newswire", "url": "https://www.reuters.com/world/africa/russias-africa-corps-kills-mali-civilians-indiscriminate-attack-rights-group-says-2026-07-31/", "published_at": "2026-07-31", "date_precision": "day", "reliability": "news_media", "notes": "HRW/路透对非洲军团平民伤害指控（归因，非已裁定事实）。"},
    {"source_id": "expe-crs-africa-corps", "title": "IF12389 — Russia's Africa Corps (CRS)", "publisher": "U.S. Congressional Research Service", "source_type": "research_analysis", "url": "https://www.congress.gov/crs_external_products/IF/HTML/IF12389.web.html", "published_at": "2025-01-01", "date_precision": "year", "reliability": "research_institution", "notes": "非洲军团起源与国防部控制。"},
    # LAAF/LNA
    {"source_id": "expe-nctc-isis-libya-2026-06", "title": "ISIS-Libya — NCTC profile (June 2026)", "publisher": "U.S. National Counterterrorism Center", "source_type": "official_counterterrorism_profile", "url": "https://www.dni.gov/nctc/terrorist_groups/isis_libya.html", "published_at": "2026-06-01", "date_precision": "month", "reliability": "authoritative", "notes": "前 ISIS-Libya 领导 Abdul Qadr al-Najdi 被 LNA 击杀。"},
    # AFRICOM
    {"source_id": "expe-africom-flintlock-26", "title": "Flintlock 26 commences in Côte d'Ivoire and Libya", "publisher": "U.S. Africa Command (AFRICOM)", "source_type": "official_self_source", "url": "https://www.africom.mil/article/36373/flintlock-26-commences-in-cote-divoire-and-libya", "published_at": "2026-01-01", "date_precision": "year", "reliability": "authoritative", "notes": "Flintlock 2026 于科特迪瓦/利比亚，约 1500 人、30+ 国。"},
    # MINUSMA
    {"source_id": "expe-un-minusma-termination", "title": "Security Council terminates MINUSMA mandate (30 June 2023)", "publisher": "United Nations", "source_type": "un_statement", "url": "https://press.un.org/en/2023/sc15341.doc.htm", "published_at": "2023-06-30", "date_precision": "day", "reliability": "authoritative", "notes": "MINUSMA 授权终止。"},
    {"source_id": "expe-un-res2690", "title": "Resolution 2690 (2023) — MINUSMA withdrawal", "publisher": "United Nations Security Council", "source_type": "un_resolution", "url": "https://minusma.unmissions.org/sites/default/files/res_2690_2023_en.pdf", "published_at": "2023-06-30", "date_precision": "day", "reliability": "authoritative", "notes": "决议 2690 授权撤出，2023-12-31 完成。"},
    # GNU umbrella
    {"source_id": "expe-reuters-libya-clashes-gnu", "title": "Libya clashes point to growing power of Turkey-allied PM", "publisher": "Reuters", "source_type": "newswire", "url": "https://www.reuters.com/world/africa/libya-clashes-point-growing-power-turkey-allied-pm-2025-05-13/", "published_at": "2025-05-13", "date_precision": "day", "reliability": "news_media", "notes": "GNU 相关武装为多支旅/安全机构，非单一统一军队。"},
]

# Reused existing source ids (asserted to exist).
REUSED_SOURCE_IDS = [
    "d2-hrw-burkina-2026-04-02",
    "deptha-reuters-mali-groups-2026-04-27",
    "d1-iss-aes-2026-03-04",
    "depthf-reuters-haftar-drones-2026-04-02",
]
