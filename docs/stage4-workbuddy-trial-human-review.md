# ASIP Stage 4 第二执行包 — 20 条中文质量验收表（人工核验）

**试跑**：WorkBuddy 真实 AI 质量试跑 ｜ **execution_route** = `workbuddy_queue` ｜ **actual_model** = `deepseek-v4-flash` ｜ **direct_website_api_call** = `false` ｜ **model_access_mode** = `workbuddy_managed` ｜ **underlying_model_source** = `unknown`
**生成方式**：从既有 `review_matrix.json` / `enrichment_results.json` / `sample_manifest.json` 确定性导出；未重新调用 AI、未重译、未改写模型结果。
**核验材料**：关键原文证据取自各条 `key_facts[].evidence_excerpt` 短句（按 日期·数字 / 地点·主体 / 事件类型 确定性分组），不复制新闻正文。

## 20 条验收表

### 1. EVT_b3861ba5c8d78187

- **event_id**：`EVT_b3861ba5c8d78187`
- **国家（canonical country_iso3）**：TCD
- **来源**：www.alwihdainfo.com
- **原文语言**：法语（fr）
- **原文标题**：Tchad : appui de l'OIM à la commune de Moussoro pour lutter contre les inondations
- **中文标题**：国际移民组织向乍得穆苏鲁市捐赠防汛设备
- **中文摘要**：国际移民组织（OIM）于2026年8月1日向乍得穆苏鲁市政府交付防汛设备，包括12500个100公斤沙袋、50双靴子、100把铁锹、25把镐、250块防水布和25辆手推车。项目属气候变化与移民数据（CCND）活动，由丹麦外交部资助，用于应对雨季初期洪灾并改善街道排水与居民通行。OIM还对省灾害管理委员会开展了为期三天的风险管理与灾害应对能力培训。
- **事件类型**：`natural_disaster`
- **社会安全相关性**：`indirect`
- **分类置信度**：90
- **结构化地点**：`country_iso3="TCD", admin1="Barh El Gazel", city="Moussoro", site=null, raw_text="Moussoro, province du Barh El Gazel"`
- **关键事实**：
  - 1. OIM于2026年8月1日向穆苏鲁市政府交付防汛设备（依据 body_extracted）
  - 2. 设备含12500个100公斤沙袋、50双靴子、100把铁锹、25把镐、250块防水布和25辆手推车（依据 body_extracted）
  - 3. 项目属CCND活动，由丹麦外交部资助（依据 body_extracted）
  - 4. OIM为省灾害管理委员会开展三天风险管理培训（依据 body_extracted）
- **不确定性**：
  - （无）

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：activités sur le changement climatique et les données migratoires (CCND)；formé pendant trois jours le Comité Provincial de Gestion de Catastrophes
- 与日期、数字、伤亡相关：fourni des équipements de lutte contre les inondations à la mairie de Moussoro le 1er août 2026；12 500 sacs de 100 kg, 50 paires de bottes, 100 pelles, 25 pioches, 250 bâches et 25 brouettes
- 与地点和主体相关：—

### 2. EVT_68ba0eb89452a250

- **event_id**：`EVT_68ba0eb89452a250`
- **国家（canonical country_iso3）**：TCD
- **来源**：lendjampost.com
- **原文语言**：法语（fr）
- **原文标题**：Ennedi Ouest : la multiplication des attaques de chacals fait craindre un risque de rage, un infectiologue appelle à une prise
- **中文标题**：乍得东恩内迪省胡狼袭击致15人以上被咬伤 引发狂犬病担忧
- **中文摘要**：乍得北部东恩内迪省近一个月内连续发生胡狼袭击事件，累计造成超过15名受害者被咬伤。首起袭击发生在2026年6月29日至30日夜间古罗市，5人被咬伤（含4名儿童）；7月27日至28日夜间再发袭击，新增10余例咬伤。因当地医疗机构缺乏狂犬病血清与疫苗，受害者被送往阿贝歇和恩贾梅纳救治。Nimè Tombà组织呼吁公共卫生部尽快向当地供应血清疫苗，并加强家养与野生犬科动物的监测与管控。
- **事件类型**：`other_security`
- **社会安全相关性**：`direct`
- **分类置信度**：75
- **结构化地点**：`country_iso3="TCD", admin1="Ennedi Ouest", city="Gouro", site=null, raw_text="commune de Gouro, province de l'Ennedi Ouest"`
- **关键事实**：
  - 1. 近一个月内胡狼袭击造成超过15名受害者（依据 body_extracted）
  - 2. 6月29日至30日夜间古罗市首起袭击致5人被咬伤，其中4名儿童（依据 body_extracted）
  - 3. 7月27日至28日夜间古罗市再发袭击，新增10余例咬伤（依据 body_extracted）
  - 4. 受害者因当地缺乏血清疫苗被送往阿贝歇和恩贾梅纳救治（依据 body_extracted）
- **不确定性**：
  - 胡狼是否携带狂犬病毒尚未经医学检测确认
  - 受害者确切总人数仅以超过15人表述，未给出精确数字

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：une série d'attaques de chacals ayant fait plus de quinze victimes en l'espace d'un mois；Cinq personnes, dont un adulte et quatre enfants, ont été mordues
- 与日期、数字、伤亡相关：—
- 与地点和主体相关：—

### 3. EVT_5291228872082f78

- **event_id**：`EVT_5291228872082f78`
- **国家（canonical country_iso3）**：TCD
- **来源**：www.rfi.fr
- **原文语言**：法语（fr）
- **原文标题**：Tchad: attaques de chacals qui pourraient être infectés par la rage dans la commune de Gouro
- **中文标题**：乍得古罗市胡狼袭击引发狂犬病担忧 组织呼吁提供疫苗
- **中文摘要**：据法国国际广播电台报道，乍得东恩内迪省古罗市近期多次发生胡狼袭击事件，首起发生于6月，5人（含4名儿童）被咬伤，本周初又有数人遭袭，部分动物已被射杀。Nimé Tombà组织担忧胡狼携带狂犬病毒，呼吁当局提供抗狂犬病疫苗并识别潜在病畜。因当地缺乏检测与医疗设施，血清和疫苗须由1000多公里外的恩贾梅纳运入，医生同时呼吁加强家养及野生犬科动物的疫苗接种与管控。
- **事件类型**：`other_security`
- **社会安全相关性**：`direct`
- **分类置信度**：75
- **结构化地点**：`country_iso3="TCD", admin1="Ennedi-Ouest", city="Gouro", site=null, raw_text="commune de Gouro, province de l'Ennedi-Ouest"`
- **关键事实**：
  - 1. 古罗市首起胡狼袭击发生于6月，5人被咬伤其中4名儿童（依据 body_extracted）
  - 2. 本周初又有数人遭袭，部分动物已被射杀（依据 body_extracted）
  - 3. Nimé Tombà组织担忧胡狼携带狂犬病毒并呼吁提供疫苗（依据 body_extracted）
  - 4. 血清和疫苗由恩贾梅纳运入，距离超过1000公里（依据 body_extracted）
- **不确定性**：
  - 胡狼是否携带狂犬病毒未经医学检测确认
  - 本周初新增遭袭人数未给出确切数字

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：La première attaque de chacals ... Cinq personnes, dont quatre enfants, avaient été mordues；Plusieurs autres personnes ont de nouveau été attaquées ... Certains animaux ont été abattus
- 与日期、数字、伤亡相关：l'ONG a dû faire venir de Ndjamena, à plus de 1 000 km
- 与地点和主体相关：—

### 4. EVT_8c9d4096815dd33c

- **event_id**：`EVT_8c9d4096815dd33c`
- **国家（canonical country_iso3）**：TCD
- **来源**：journaldutchad.com
- **原文语言**：法语（fr）
- **原文标题**：Tchad : le ministre des Armées effectue une mission de sécurité à Owi - Journal du Tchad
- **中文标题**：乍得武装部队部长赴提贝斯提省奥维开展安全评估
- **中文摘要**：乍得负责军队事务的部长伊萨卡·马卢阿·贾穆斯于2026年7月20日抵达提贝斯提省奥维，开展以评估安全形势和加强国防部署为重点的工作访问。部长由武装部队总参谋长马哈马特·苏莱曼·阿里将军及多名安全部门高级官员陪同，抵达时获政府驻省代表阿利法·韦德耶少将迎接，随后开始既定行程。
- **事件类型**：`other_security`
- **社会安全相关性**：`indirect`
- **分类置信度**：85
- **结构化地点**：`country_iso3="TCD", admin1="Tibesti", city="Owi", site=null, raw_text="Owi, province du Tibesti"`
- **关键事实**：
  - 1. 部长于2026年7月20日抵达奥维开展安全评估工作访问（依据 body_extracted）
  - 2. 总参谋长马哈马特·苏莱曼·阿里将军随行（依据 body_extracted）
  - 3. 访问重点是评估安全形势并加强国防部署（依据 body_extracted）
- **不确定性**：
  - （无）

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：accompagné du chef d'état-major général des Armées ... le général Mahamat Souleymane Ali；évaluation de la situation sécuritaire et le renforcement du dispositif de défense
- 与日期、数字、伤亡相关：arrivé le lundi 20 juillet 2026 ... à Owi, dans la province du Tibesti
- 与地点和主体相关：—

### 5. EVT_9a551301360773c7

- **event_id**：`EVT_9a551301360773c7`
- **国家（canonical country_iso3）**：TCD
- **来源**：tchadone.com
- **原文语言**：法语（fr）
- **原文标题**：Tchad | Grève des enseignants : le régime ampute les salaires et franchit un seuil inquiétant
- **中文标题**：乍得政府切断数千名罢工教师2月工资
- **中文摘要**：据TchadOne报道，乍得政府将切断数千名罢工教师的工资，已致函银行要求取消并冲回2026年2月向教师账户的工资转账，官方以未出勤天数不予计酬为由作出政治性确认。教师工会认为此举是对罢工的集体惩罚，指责政府拒绝执行其自身签署的法令并侵犯宪法承认的罢工权利。报道评论称，财政惩罚而非对话的做法可能引发公务员群体对维权后果的普遍担忧。
- **事件类型**：`civil_unrest`
- **社会安全相关性**：`direct`
- **分类置信度**：70
- **结构化地点**：`country_iso3="TCD", admin1=null, city="N'Djamena", site=null, raw_text="N'Djamena"`
- **关键事实**：
  - 1. 政府致函银行要求取消并冲回2月工资转账（依据 body_extracted）
  - 2. 官方称未出勤天数不予计酬（依据 body_extracted）
  - 3. 教师工会要求执行政府自身签署的法令（依据 body_extracted）
- **不确定性**：
  - 受影响教师确切人数未在文中给出
  - 报道为TchadOne评论性文章，部分表述带有立场色彩

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：les jours non prestés ne seront pas rémunérés；les syndicats enseignants ne réclament pas une faveur, mais l'application d'un décret signé par le régime lui-même
- 与日期、数字、伤亡相关：correspondance adressée aux banques, ordonnant l'annulation et l'extourne des virements des salaires de février 2026
- 与地点和主体相关：—

### 6. EVT_0f85e5f42626ce7d

- **event_id**：`EVT_0f85e5f42626ce7d`
- **国家（canonical country_iso3）**：TCD
- **来源**：www.tachad.com
- **原文语言**：法语（fr）
- **原文标题**：Province du Salamat : le Délégué général du Gouvernement préside sa première réunion sécuritaire après son retour de mission officielle
- **中文标题**：乍得萨拉马特省举行安全会议部署维稳措施
- **中文摘要**：萨拉马特省省长伊斯特·伊萨卡·阿谢赫将军从公务出差返回后，于周五在阿姆蒂曼主持一次重要安全会议。会议汇集国防与安全部队负责人、军官及行政当局代表，分析全省安全形势、主要挑战与关切，并讨论加强稳定、改善部门间协调及保护民众生命财产的措施。省长强调各方需保持警惕、协作与投入，以维护全省和平、安全与稳定。
- **事件类型**：`other_security`
- **社会安全相关性**：`indirect`
- **分类置信度**：80
- **结构化地点**：`country_iso3="TCD", admin1="Salamat", city="Am Timan", site=null, raw_text="Am Timan, province du Salamat"`
- **关键事实**：
  - 1. 省长在阿姆蒂曼主持安全会议（依据 body_extracted）
  - 2. 会议分析全省安全形势并讨论维稳与协调措施（依据 body_extracted）
  - 3. 省长强调警惕、协作与各方参与（依据 body_extracted）
- **不确定性**：
  - 会议具体公历日期未给出（文中仅称本周五）

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：examiné la situation sécuritaire de la province ... renforcer la stabilité, améliorer la coordination；a insisté sur l'importance de la vigilance, de la collaboration et de l'engagement de tous les acteurs
- 与日期、数字、伤亡相关：—
- 与地点和主体相关：a présidé ce vendredi à Am Timan une importante réunion consacrée à la sécurité

### 7. EVT_451cac52bc310619

- **event_id**：`EVT_451cac52bc310619`
- **国家（canonical country_iso3）**：TCD
- **来源**：tchadinfos.com
- **原文语言**：法语（fr）
- **原文标题**：Salamat : 302 armes de guerre saisies en trois mois d'opération - Tchadinfos
- **中文标题**：乍得萨拉马特省三个月缴获302件武器
- **中文摘要**：乍得国防与安全部队在萨拉马特省为期三个月的行动中共缴获302件各型武器、119个弹匣和25发弹药，于2026年7月31日在省首府阿姆蒂曼省长院内展示。省长伊斯特·伊萨卡·阿谢赫将军肯定部队专业表现，并呼吁民众主动上交非法持有的武器，强调持枪权专属国防与安全部队，同时赞扬各方协作对行动成功的贡献。
- **事件类型**：`other_security`
- **社会安全相关性**：`direct`
- **分类置信度**：85
- **结构化地点**：`country_iso3="TCD", admin1="Salamat", city="Amtiman", site="cour du gouvernorat", raw_text="cour du gouvernorat de la province du Salamat, à Amtiman"`
- **关键事实**：
  - 1. 行动缴获302件各型武器、119个弹匣和25发弹药（依据 body_extracted）
  - 2. 缴获武器于2026年7月31日在阿姆蒂曼展示（依据 body_extracted）
  - 3. 该结果为三个月专项行动的成果（依据 body_extracted）
  - 4. 省长呼吁民众主动上交非法持有的武器（依据 body_extracted）
- **不确定性**：
  - 未说明被缴获武器的来源方是否涉及刑事立案或嫌疑人信息

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：le fruit de trois mois d'opérations menées dans la province；un appel à la population afin qu'elle remette volontairement les armes encore détenues illégalement
- 与日期、数字、伤亡相关：302 armes de différents calibres, 119 chargeurs et 25 munitions；présentés ce vendredi 31 juillet 2026 dans la cour du gouvernorat
- 与地点和主体相关：—

### 8. EVT_1c75a026db7edada

- **event_id**：`EVT_1c75a026db7edada`
- **国家（canonical country_iso3）**：TCD
- **来源**：journaldutchad.com
- **原文语言**：法语（fr）
- **原文标题**：Tchad-sécurité : un nouveau poste de commandement opérationnel à Wour
- **中文标题**：乍得启用沃乌新作战指挥所 加强G5萨赫勒防务
- **中文摘要**：乍得武装部队部长伊萨卡·马卢阿·贾穆斯将军于2026年6月25日在提贝斯提省沃乌为新作战指挥所揭牌。该设施属G5萨赫勒联合部队支持项目，由欧盟出资、Expertise France实施，占地45公顷，投资超过1.2亿欧元，包含行政楼、后勤设施、营房与训练场地，可容纳600至700名军人。
- **事件类型**：`other_security`
- **社会安全相关性**：`indirect`
- **分类置信度**：88
- **结构化地点**：`country_iso3="TCD", admin1="Tibesti", city="Wour", site=null, raw_text="Wour, province du Tibesti"`
- **关键事实**：
  - 1. 新作战指挥所于2026年6月25日由国防部长揭牌（依据 body_extracted）
  - 2. 项目由欧盟出资、Expertise France实施（依据 body_extracted）
  - 3. 设施占地45公顷、投资超1.2亿欧元、可容纳600至700名军人（依据 body_extracted）
- **不确定性**：
  - （无）

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：financée par l'Union européenne et mise en œuvre par Expertise France
- 与日期、数字、伤亡相关：inauguré le 25 juin 2026 par ... le général de corps d'armée, Issaka Malloua Djamous；45 hectares ... plus de 120 millions d'euros ... accueillir 600 à 700 militaires
- 与地点和主体相关：—

### 9. EVT_2520e85f1185795d

- **event_id**：`EVT_2520e85f1185795d`
- **国家（canonical country_iso3）**：TCD
- **来源**：www.alwihdainfo.com
- **原文语言**：法语（fr）
- **原文标题**：Libye : Saddam Haftar annonce la mise en place d'une salle d'opérations militaires conjointe à Syrte
- **中文标题**：利比亚宣布在苏尔特设立联合军事行动室
- **中文摘要**：利比亚国民军副总指挥萨达姆·哈夫塔尔在班加西会见美国国会代表团后宣布，将在苏尔特设立联合军事行动室，汇集利比亚阿拉伯武装力量与西部军事单位以加强协调；并称利比亚将主办2027年弗林特洛克演习的主要部分，还拟建立统一空中司令部。会谈亦涉及统一利比亚军事机构。注：本事件Canonical标注国为乍得（TCD），但正文主体涉及利比亚。
- **事件类型**：`other_security`
- **社会安全相关性**：`indirect`
- **分类置信度**：55
- **结构化地点**：`country_iso3="TCD", admin1=null, city=null, site=null, raw_text="Syrte（利比亚）"`
- **关键事实**：
  - 1. 萨达姆·哈夫塔尔在班加西会见美国国会代表团（依据 body_extracted）
  - 2. 宣布将在苏尔特设立联合军事行动室（依据 body_extracted）
  - 3. 据称利比亚将主办2027年Flintlock演习主要部分（依据 body_extracted）
  - 4. 会谈还涉及建立统一空中司令部（依据 body_extracted）
- **不确定性**：
  - 正文主体涉及利比亚（苏尔特、班加西），与Canonical事件标注国TCD不一致，事件实际发生地存疑
  - 利比亚主办2027年Flintlock演习系据称，尚未确认
- **canonical_data_warning** = `primary_country_body_mismatch`
- **suggested_action** = `review_before_activation`

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：Saddam Haftar ... a reçu ... une délégation du Congrès américain conduite par le représentant Austin Scott；la création, à Syrte, d'une salle d'opérations militaires conjointe
- 与日期、数字、伤亡相关：un accord aurait été trouvé pour que la Libye accueille la partie principale de l'exercice Flintlock 2027
- 与地点和主体相关：—

### 10. EVT_2e8ce0003ca07a8b

- **event_id**：`EVT_2e8ce0003ca07a8b`
- **国家（canonical country_iso3）**：TCD
- **来源**：tchadone.com
- **原文语言**：法语（fr）
- **原文标题**：Tchad / Burkina Faso / Recettes douanières | Frontières, minerais, bétail : pourquoi le Tchad affiche 239 milliards quand le Burkina en encaisse 1 253 ?
- **中文标题**：乍得海关税收与出口规模不符引质疑
- **中文摘要**：据TchadOne报道，乍得2025年海关收入为2390亿非洲法郎，远低于布基纳法索的12530亿，与乍得实际出口规模（数千吨锑、大量黄金、每年超20万头牲畜出口至尼日利亚与中部非洲，以及芝麻、阿拉伯胶等农产品）明显不符。报道称官方已承认黄金出口超1.5万亿非洲法郎至阿联酋，但相关税收未在预算中清晰体现；公共财政专家估计，若严格管理，乍得海关年收入可超3万亿非洲法郎。
- **事件类型**：`other_security`
- **社会安全相关性**：`none`
- **分类置信度**：60
- **结构化地点**：`country_iso3="TCD", admin1=null, city="N'Djamena", site=null, raw_text="N'Djamena"`
- **关键事实**：
  - 1. 乍得2025年海关收入2390亿非洲法郎，布基纳法索为12530亿（依据 body_extracted）
  - 2. 报道称乍得每年超20万头牲畜出口至尼日利亚和中部非洲（依据 body_extracted）
  - 3. 官方承认黄金出口超1.5万亿非洲法郎至阿联酋（依据 body_extracted）
  - 4. 专家估计严格管理后年收入可超3万亿非洲法郎（依据 body_extracted）
- **不确定性**：
  - 文中牲畜、矿产出口量与税收测算多为估计值，非官方审计数据
  - 报道为TchadOne评论性文章，观点色彩较强
  - 3万亿法郎为专家估算，非官方预测

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：—
- 与日期、数字、伤亡相关：le Burkina Faso a récolté 1 253 milliards de FCFA ... Le Tchad, lui, affiche 239 milliards；plus de 200 000 têtes de bétail exportées chaque année vers le Nigeria et l'Afrique centrale
- 与地点和主体相关：—

### 11. EVT_15fee76f358f8d07

- **event_id**：`EVT_15fee76f358f8d07`
- **国家（canonical country_iso3）**：NER
- **来源**：anp.ne
- **原文语言**：法语（fr）
- **原文标题**：Diffa : le Gouverneur apporte le soutien des plus hautes autorités aux Forces de défense et de sécurité à N'Guigmi et appelle à poursuivre le combat contre le terrorisme - Agence Nigérienne de Presse
- **中文标题**：尼日尔迪法省省长慰问遇袭阵亡军人 承诺继续反恐
- **中文摘要**：尼日尔迪法省省长马哈马杜·易卜拉欣·巴加多马少将于2026年8月1日在恩吉格米会见当地国防与安全部队，转达总统蒂亚尼、总理泽内等最高当局对在恐怖袭击中阵亡军人的哀悼与鼓励，并到访恩吉格米第53合成营。省长强调不因困难动摇士气，呼吁部队保持警惕并继续打击恐怖主义，同时走访传统首领重申合作。该区东部持续面临恐怖武装威胁。
- **事件类型**：`terrorism`
- **社会安全相关性**：`direct`
- **分类置信度**：80
- **结构化地点**：`country_iso3="NER", admin1="Diffa", city="N'Guigmi", site="53ᵉ Bataillon Interarmes", raw_text="N'Guigmi, région de Diffa"`
- **关键事实**：
  - 1. 省长于2026年8月1日在恩吉格米会见国防与安全部队（依据 body_extracted）
  - 2. 会面前一天阵亡军人举行葬礼，系恐怖袭击所致（依据 body_extracted）
  - 3. 省长转达总统蒂亚尼、总理泽内等最高当局的慰问（依据 body_extracted）
  - 4. 省长呼吁部队保持警惕并继续打击恐怖主义（依据 body_extracted）
- **不确定性**：
  - 袭击具体时间与阵亡军人人数未在文中给出

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：ce message émane notamment du Président de la République ... le Général d'Armée Abdourahamane Tiani；à demeurer vigilantes face à un ennemi qui adapte continuellement ses modes opératoires
- 与日期、数字、伤亡相关：—
- 与地点和主体相关：le Gouverneur de la région de Diffa ... a rencontré ... les différents corps des FDS en poste à N'Guigmi；l'inhumation des éléments des FDS tombés ... lors d'une attaque terroriste perpétrée dans le département de N'Guigmi

### 12. EVT_10c3ca125264c6c1

- **event_id**：`EVT_10c3ca125264c6c1`
- **国家（canonical country_iso3）**：NER
- **来源**：anp.ne
- **原文语言**：法语（fr）
- **原文标题**：L’AN 3 DU CNSP : à Diffa, 1.500 tonnes d’engrais réceptionnées par la CAIMA pour soutenir les producteurs agricoles dans le cadre de la campagne 2026
- **中文标题**：尼日尔迪法省接收1500吨化肥支援2026农季
- **中文摘要**：尼日尔农业生产资料供应中心（CAIMA）在迪法接收1500吨化肥，用于支持该地区2026年农季生产者，其中1000吨尿素、500吨NPK复合肥，将逐步运往全区9个市镇。该批物资属国家补贴政策，旨在降低生产成本、提高产量并增强农户应对气候与粮食风险的韧性。对比2025年该地区获1100吨化肥（覆盖7个市镇），今年数量与覆盖面均扩大。
- **事件类型**：`other_security`
- **社会安全相关性**：`none`
- **分类置信度**：85
- **结构化地点**：`country_iso3="NER", admin1="Diffa", city="Diffa", site=null, raw_text="Diffa"`
- **关键事实**：
  - 1. CAIMA在迪法接收1500吨化肥用于2026农季（依据 body_extracted）
  - 2. 化肥含1000吨尿素和500吨NPK复合肥（依据 body_extracted）
  - 3. 化肥将逐步运往全区九个市镇（依据 body_extracted）
  - 4. 2025年该地区获1100吨化肥覆盖7个市镇（依据 body_extracted）
- **不确定性**：
  - （无）

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：acheminés vers les neuf communes de la région
- 与日期、数字、伤亡相关：la CAIMA a réceptionné, à Diffa, un stock de 1.500 tonnes d'engrais；1.000 tonnes d'urée et de 500 tonnes de NPK
- 与地点和主体相关：—

### 13. EVT_3ac33d557e02d42b

- **event_id**：`EVT_3ac33d557e02d42b`
- **国家（canonical country_iso3）**：NER
- **来源**：anp.ne
- **原文语言**：法语（fr）
- **原文标题**：Niamey : Le Président de la BOAD fait le point des activités de son institution au Niger au Président de la République
- **中文标题**：尼日尔总统蒂亚尼会见西非开发银行行长
- **中文摘要**：尼日尔总统阿卜杜拉哈马内·蒂亚尼将军于2026年7月28日在办公室接见西非开发银行（BOAD）行长塞尔日·埃库。埃库表示双方就银行运营现状及粮食安全、能源、农业、基础设施等战略项目交换意见，并称BOAD将继续支持尼日尔的发展愿景与项目。总理泽内、财经部长拉乌阿利·阿卜杜·拉法等官员出席会见。
- **事件类型**：`other_security`
- **社会安全相关性**：`none`
- **分类置信度**：85
- **结构化地点**：`country_iso3="NER", admin1=null, city="Niamey", site=null, raw_text="Niamey"`
- **关键事实**：
  - 1. 总统蒂亚尼于2026年7月28日接见BOAD行长埃库（依据 body_extracted）
  - 2. 会谈涉及粮食安全、能源、农业、基础设施等战略项目（依据 body_extracted）
  - 3. 尼日尔为BOAD股东国之一（依据 body_extracted）
- **不确定性**：
  - （无）

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：les questions de la sécurité alimentaire, l'énergie, l'agriculture et enfin celui des infrastructures；la République du Niger étant l'un des propriétaires de la Banque
- 与日期、数字、伤亡相关：le général d'armée Abdourahamane Tiani a reçu, ce mardi 28 juillet 2026 à son cabinet, le Président de la BOAD, M. Serge Ekoue
- 与地点和主体相关：—

### 14. EVT_3e70963728359646

- **event_id**：`EVT_3e70963728359646`
- **国家（canonical country_iso3）**：NER
- **来源**：anp.ne
- **原文语言**：法语（fr）
- **原文标题**：Niamey : Ouverture de la deuxième édition du Forum de la Diaspora Nigérienne
- **中文标题**：尼日尔第二届侨民论坛开幕 聚焦发展贡献
- **中文摘要**：尼日尔总理阿里·马哈曼·拉明·泽内于2026年7月28日在尼亚美马哈特马·甘地会议中心为第二届尼日尔侨民论坛（FDN）揭幕，论坛于7月28日至29日举行，主题为侨民在重建背景下对国家经济社会发展的贡献。泽内号召侨民参与国家建设、动员投资与知识，外交部长桑加雷及OIM西非区域主任西尔维娅·埃克拉等出席。首届论坛于2022年在尼亚美举办。
- **事件类型**：`other_security`
- **社会安全相关性**：`none`
- **分类置信度**：88
- **结构化地点**：`country_iso3="NER", admin1=null, city="Niamey", site="centre des conférences Mahatma Gandhi", raw_text="Niamey, centre des conférences Mahatma Gandhi"`
- **关键事实**：
  - 1. 总理泽内于2026年7月28日为第二届侨民论坛揭幕（依据 body_extracted）
  - 2. 论坛于2026年7月28至29日举行（依据 body_extracted）
  - 3. 首届论坛于2022年在尼亚美举行（依据 body_extracted）
  - 4. 全国协商会议期间侨民贡献了超过45%的建议（依据 body_extracted）
- **不确定性**：
  - （无）

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：Le Premier Ministre, M. Ali Mahaman Lamine Zeine a procédé ... au lancement officiel du Forum de la Diaspora Nigérienne
- 与日期、数字、伤亡相关：Cette 2ᵉ édition, qui se tient du 28 au 29 juillet 2026；la première édition de ce forum a eu lieu en 2022 à Niamey
- 与地点和主体相关：—

### 15. EVT_f873e54241d57b7a

- **event_id**：`EVT_f873e54241d57b7a`
- **国家（canonical country_iso3）**：NER
- **来源**：anp.ne
- **原文语言**：法语（fr）
- **原文标题**：Niamey : Le Premier ministre reçoit une délégation de la BOAD conduite par son président, M. Serge Ekué
- **中文标题**：尼日尔总理会见西非开发银行代表团
- **中文摘要**：尼日尔总理阿里·马哈曼·拉明·泽内于2026年7月28日在办公室会见由行长塞尔日·埃库率领的西非开发银行（BOAD）代表团。会见结束后未向媒体发表任何声明。报道补充说明BOAD致力于促进成员国平衡发展与西非经济一体化。
- **事件类型**：`other_security`
- **社会安全相关性**：`none`
- **分类置信度**：80
- **结构化地点**：`country_iso3="NER", admin1=null, city="Niamey", site=null, raw_text="Niamey"`
- **关键事实**：
  - 1. 总理泽内于2026年7月28日接见BOAD代表团（依据 body_extracted）
  - 2. 会见后未向媒体发表任何声明（依据 body_extracted）
- **不确定性**：
  - 会见内容未公开，未发表任何声明

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：A l'issue de cette audience, aucune déclaration n'a été faite à la presse
- 与日期、数字、伤亡相关：Le Premier ministre, M. Ali Mahamane Lamine Zeine, a reçu, ce mardi 28 juillet 2026 ... une délégation de la BOAD
- 与地点和主体相关：—

### 16. EVT_6b7ce87900f1b656

- **event_id**：`EVT_6b7ce87900f1b656`
- **国家（canonical country_iso3）**：NER
- **来源**：anp.ne
- **原文语言**：法语（fr）
- **原文标题**：L’AN 3 CNSP à Diffa : +21,9 % de demandes d’emploi, 100 % des offres satisfaites… L’ANPE met en lumière les avancées de l’insertion professionnelle des jeunes
- **中文标题**：尼日尔迪法省就业需求上半年增长21.9%
- **中文摘要**：据尼日尔新闻社报道，迪法省国家就业促进局（ANPE）2026年上半年登记就业需求1737件，较2025年同期的1425件增长21.9%，期间收到的9个岗位全部得到满足，保持100%的岗位满足率。报告还显示全国就业合同签证数由281份增至295份（增5%），TRE/E职业培训受益人数增长162.5%。该报告系ANP庆祝CNSP执政三周年系列报道之一。
- **事件类型**：`other_security`
- **社会安全相关性**：`none`
- **分类置信度**：85
- **结构化地点**：`country_iso3="NER", admin1="Diffa", city="Diffa", site=null, raw_text="Diffa"`
- **关键事实**：
  - 1. 2026上半年就业需求1737件，同比增21.9%（依据 body_extracted）
  - 2. 收到的9个岗位全部被满足，满足率100%（依据 body_extracted）
  - 3. 就业合同签证由281份增至295份，增长5%（依据 body_extracted）
  - 4. TRE/E职业培训受益人数增长162.5%（依据 body_extracted）
- **不确定性**：
  - （无）

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：—
- 与日期、数字、伤亡相关：1.737 demandes d'emploi ... contre 1.425 ... soit une progression de 21,9 %；a reçu neuf offres d'emploi ... un taux de satisfaction de 100 %
- 与地点和主体相关：—

### 17. EVT_2460633265046ffa

- **event_id**：`EVT_2460633265046ffa`
- **国家（canonical country_iso3）**：NER
- **来源**：anp.ne
- **原文语言**：法语（fr）
- **原文标题**：Tahoua: Lancement national de la 8ème édition de la caravane civile-militaire, édition 2026
- **中文标题**：尼日尔第八届军民活动大篷车在塔胡阿启动
- **中文摘要**：塔胡阿大区区长苏莱曼·阿马杜·穆萨上校于2026年7月27日在区政府主持启动第八届军民活动大篷车，主题为近邻警务处于安全总动员核心。活动恰逢CNSP执政三周年纪念，获国防与内政两位国务部长联合赞助。全国ACM协调代表团及塔胡阿各界出席，活动旨在以社区警务促进全民安全共治。
- **事件类型**：`other_security`
- **社会安全相关性**：`indirect`
- **分类置信度**：82
- **结构化地点**：`country_iso3="NER", admin1="Tahoua", city="Tahoua", site="Gouvernorat", raw_text="Tahoua"`
- **关键事实**：
  - 1. 第八届军民活动大篷车于2026年7月27日在塔胡阿启动（依据 body_extracted）
  - 2. 本届主题为近邻警务与安全总动员（依据 body_extracted）
  - 3. 活动恰逢CNSP执政三周年纪念（依据 body_extracted）
- **不确定性**：
  - （无）

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：la Police de proximité au cœur de la mobilisation générale pour la sécurisation
- 与日期、数字、伤亡相关：le lancement des activités de la 8 ème édition de la caravane civile-militaire；coïncide avec la commémoration du 3 ème anniversaire de l'avènement du CNSP au pouvoir
- 与地点和主体相关：—

### 18. EVT_f43a44be98d924c4

- **event_id**：`EVT_f43a44be98d924c4`
- **国家（canonical country_iso3）**：NER
- **来源**：anp.ne
- **原文语言**：法语（fr）
- **原文标题**：Niamey : Les conclusions des états généraux du barrage Kandadji présentées au Premier Ministre
- **中文标题**：坎达吉大坝问题大会结论呈报尼日尔总理
- **中文摘要**：尼日尔总理阿里·马哈曼·拉明·泽内于2026年7月27日接见坎达吉大坝融资委员会代表团，听取2026年7月8日至10日在尼亚美举行的坎达吉大坝项目问题大会结论。委员会主席穆穆尼·阿卜杜·拉扎克介绍，大会确定三项基本选项：维持现状、尼日尔自主建坝、或在国家强主导下与少数重要出资方联合实施，相关文件将供决策层参考。
- **事件类型**：`other_security`
- **社会安全相关性**：`none`
- **分类置信度**：85
- **结构化地点**：`country_iso3="NER", admin1=null, city="Niamey", site=null, raw_text="Niamey"`
- **关键事实**：
  - 1. 总理于2026年7月27日听取坎达吉大坝问题大会结论汇报（依据 body_extracted）
  - 2. 大会于2026年7月8至10日在尼亚美举行（依据 body_extracted）
  - 3. 大会确定三项选项：维持现状、自主建坝、与少量出资方联合实施（依据 body_extracted）
- **不确定性**：
  - （无）

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：—
- 与日期、数字、伤亡相关：a reçu, ce lundi 27 juillet 2026, une délégation du comité de financement du Barrage de Kandadji；Etats généraux ... tenus du 08 au 10 juillet 2026 à Niamey
- 与地点和主体相关：—

### 19. EVT_5eeb84b95f768a30

- **event_id**：`EVT_5eeb84b95f768a30`
- **国家（canonical country_iso3）**：NER
- **来源**：www.lesahel.org
- **原文语言**：法语（fr）
- **原文标题**：Sécurité routière : L’ANISER et l’ONG ADSD Bangou Daabey sensibilisent les leaders religieux
- **中文标题**：尼日尔道路交通安全机构培训宗教领袖
- **中文摘要**：尼日尔道路交通安全局（ANISER）与ADSD Bangou Daabey非政府组织于2026年7月26日在尼亚美为宗教协会举办交通安全培训，旨在借助宗教领袖在公众中的影响力推动行为改变。ANISER局长阿布·蒙塔里指出2025年道路事故造成1245人死亡，称道路比一般安全问题更危险，并呼吁杜绝酒驾等危险驾驶行为。
- **事件类型**：`other_security`
- **社会安全相关性**：`indirect`
- **分类置信度**：82
- **结构化地点**：`country_iso3="NER", admin1=null, city="Niamey", site=null, raw_text="Niamey"`
- **关键事实**：
  - 1. ANISER与ADSD于2026年7月26日在尼亚美培训宗教协会（依据 body_extracted）
  - 2. ANISER局长称2025年道路事故致1245人死亡（依据 body_extracted）
  - 3. 培训旨在借助宗教领袖影响力改变公众行为（依据 body_extracted）
- **不确定性**：
  - （无）

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：les leaders religieux sont une cible importante en matière de changement de comportement
- 与日期、数字、伤亡相关：a organisé, le dimanche 26 juillet 2026 à Niamey, une formation sur la sécurité routière au profit des associations religieuses；1245 personnes ont perdu la vie suite aux accidents de la route en 2025
- 与地点和主体相关：—

### 20. EVT_081fa3a5ebcaee5e

- **event_id**：`EVT_081fa3a5ebcaee5e`
- **国家（canonical country_iso3）**：NER
- **来源**：airinfoagadez.com
- **原文语言**：法语（fr）
- **原文标题**：Niger : le président Tiani dénonce un rôle de la France dans les attaques de l’aéroport de Niamey
- **中文标题**：尼日尔总统蒂亚尼指控法国策划尼亚美机场袭击
- **中文摘要**：在执政三周年之际，尼日尔总统阿卜杜拉哈马内·蒂亚尼将军接受官方媒体采访时，指控法国策划了2026年1月28至29日和6月18日对尼亚美迪奥里·哈马尼国际机场的袭击，称袭击者为受法国雇佣的雇佣兵，并指其同时企图袭击总统府与通迪比亚军事中心。蒂亚尼称握有证据但未公布，还称袭击者受欧盟及西方指使。法国官方暂未回应。
- **事件类型**：`terrorism`
- **社会安全相关性**：`direct`
- **分类置信度**：60
- **结构化地点**：`country_iso3="NER", admin1=null, city="Niamey", site="aéroport international Diori Hamani", raw_text="Niamey, aéroport international Diori Hamani"`
- **关键事实**：
  - 1. 蒂亚尼指控法国策划2026年1月28至29日与6月18日的尼亚美机场袭击（依据 body_extracted）
  - 2. 蒂亚尼称袭击者为受法国雇佣的雇佣兵（依据 body_extracted）
  - 3. 称袭击目标还包括总统府与通迪比亚军事中心（依据 body_extracted）
  - 4. 蒂亚尼称握有证据但未公开，法国官方暂未回应（依据 body_extracted）
- **不确定性**：
  - 对法国的指控未经第三方证实且证据未公开
  - 袭击者身份与袭击造成的伤亡情况未在文中说明

**关键原文证据**（短句，来自 key_facts 摘录）：
- 与事件类型相关：« mercenaires à la solde de la France »；viser simultanément le palais présidentiel et le centre militaire de Tondibiah
- 与日期、数字、伤亡相关：a accusé la France d'être l'instigatrice des attaques contre l'aéroport international Diori Hamani de Niamey, survenues les 28-29 janvier et 18 juin 2026
- 与地点和主体相关：—

---

## 非阻断技术债务（本轮记录，不修复）

1. `write_handoff` 任务清单输出 `event=None`（C 包桥接 Provider 索引条目未含 event_id/country 键，不影响功能）——**留待 Stage 4 第三执行包修复，不阻断本次质量验收**。
2. `_load_canonical_eligible` 隔离文件路径不正确（读取 `data/quarantine/quarantine.json`，实际位于 `data/canonical/`）——本轮以 manifest 驱动入队绕开，**留待 Stage 4 第三执行包修复，不阻断本次质量验收**。
3. `EVT_2520e85f1185795d` 国家归因待复核（正文主体为利比亚、canonical 标注 TCD，已在本表标记 `canonical_data_warning=primary_country_body_mismatch` / `suggested_action=review_before_activation`；本轮不改动 Canonical 国家字段）——**建议采集侧复核归因**。

## 验收汇总

- 共 20 条：TCD=10 / NER=10；模型输出硬检查 0/20 失败；异常样本 1 条（序号 9）。
- `execution_route=workbuddy_queue` ｜ `actual_model=deepseek-v4-flash` ｜ `direct_website_api_call=false` ｜ `model_access_mode=workbuddy_managed` ｜ `underlying_model_source=unknown`。
- Token 用量：`token_usage_available=false`（WorkBuddy 队列未暴露模型 Token 用量），未做任何推测。
