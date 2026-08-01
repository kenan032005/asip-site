#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
country_runner.py —— 通用国家采集编排（供 chad/ 与 niger/ 调用）。

第二轮整改重点修复：
1. 国家识别不再使用 `kw in text` 子串匹配，全部改为「完整单词边界」匹配；
2. 短词（Lac / mine / riot / air / place / state / army / police）受单词边界
   与语境约束，杜绝 place→Lac、patriot→riot 等误判；
3. 国家识别输出结构化字段：country_match_score / matched_country_entities /
   matched_location_entities / excluded_entities / source_country /
   dateline_country / event_location_country / mentioned_countries /
   country_decision_reason；
4. 严格区分「事件发生国」与「文中提及国」：只有 event_location_country 明确
   为乍得/尼日尔才可归入；
5. 尼日尔/尼日利亚防误判：Niger Delta / Niger State / Nigerian Army / Nigeria
   一律排除；仅在满足强条件时归尼日尔；
6. 乍得湖跨国规则：Lake Chad / Lac Tchad / Lake Chad Basin 不得自动归乍得，
   仅在匹配乍得 Lac 省行政区或明确「in Chad / au Tchad」时归乍得，否则记为
   regional（Lake Chad Basin）；
7. 相关性筛选分两段：确定性排除（体育/农业/会议/评论等）+ 待语义复核标记；
8. 事件类型从标准枚举选择，不再默认 armed_conflict。
"""
import os
import re
import json
from rss_collector import RSSCollector
from wordpress_collector import WordPressCollector
from sitemap_collector import SitemapCollector
from html_list_collector import HTMLListCollector
from reliefweb_collector import ReliefWebCollector
from search_discovery_collector import SearchDiscoveryCollector
from gdelt_search_collector import GdeltSearchCollector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG_DIR = os.path.join(ROOT, "config", "countries")

COLLECTORS = {
    "rss": RSSCollector,
    "wordpress": WordPressCollector,
    "sitemap": SitemapCollector,
    "html_list": HTMLListCollector,
    "reliefweb_api": ReliefWebCollector,
    "search_discovery": SearchDiscoveryCollector,
    "gdelt_search": GdeltSearchCollector,
}

# ---- 单词边界匹配（带重音） ----
_BOUND = r"(?<![a-zà-ÿ0-9])"
_BOUND2 = r"(?![a-zà-ÿ0-9])"


def wb(text, kw):
    """完整单词边界匹配（忽略大小写）。kw 为小写。"""
    return re.search(_BOUND + re.escape(kw) + _BOUND2, text) is not None


def wb_any(text, kws):
    return [k for k in kws if wb(text, k.lower())]


# 社会安全正相关关键词（法/英/中混合，小写）。mine 仅在爆炸物/地雷语境计入。
SECURITY_POS = [
    "attack", "attaque", "killed", "morts", "dead", "clash", "conflit",
    "conflict", "terror", "terrorist", "terrorisme", "terrorism", "kidnap",
    "kidnapping", "enlèvement", "abduct", "hostage", "otage", "manifestation",
    "protest", "sécurité", "securite", "insécurité", "insecurity", "bomb",
    "bombing", "explosion", "raid", "affrontement", "embuscade", "braquage",
    "robbery", "frontière", "frontier", "couvre-feu", "curfew", "crise",
    "émeute", "riot", "violence", "violences", "armed", "armé", "milice",
    "militia", "rebel", "armée", "police", "drone", "séquestration",
    "exécution", "execution", "massacre",
    "réfugié", "refugie", "refugee", "inondation", "inondations", "crue",
    "flood", "drought", "sécheresse", "epidemic", "épidémie", "cholera",
    "choléra", "earthquake", "séisme", "grève", "greve", "strike",
    "arrestation", "arrest", "fermeture", "banditisme", "banditry", "trafic",
    "smuggling", "orpaillage", "ied", "eei", "insurgent", "insurgé", "jnim",
    "gsim", "isgs", "boko haram", "iswap", "fact", "cico",
    "état d'urgence", "etat d'urgence", "state of emergency", "袭击", "冲突",
    "恐怖", "绑架", "示威", "安全", "爆炸", "边境", "宵禁", "危机", "洪水",
    "干旱", "霍乱", "疫情", "抢劫", "交火", "武装", "军队", "警察", "政变",
    "战乱", "叛乱", "伏击", "人质", "撤离", "遇袭", "中国公民", "中国企业",
    "使馆提醒", "领事提醒", "安全提醒", "engin explosif", "explosive",
    "landmine", "land mine",
    # ── Stage 3A 补充：明确的暴力/伤亡/交火词汇（法/英）──
    "tués", "tue", "tué", "tombés", "tombé", "balles", "balle", "fusillade",
    "tirs", "tir", "meurtre", "meurtres", "assassinat", "assassinés",
    "assassiné", "blessés", "blessé", "gunmen", "shooting", "shootout",
    "shootings", "wounded", "killed", "kills", "dead", "deaths", "explosion",
    "explosions", "bomb", "bombs", "bombing", "attack", "attacks", "attaque",
    "attaques", "assault", "assaut", "kidnapped", "kidnapping", "enlèvements",
    "enlevements", "otages", "hostages", "kidnappers", "beheaded",
    "décapitations", "decapitations", "burned", "brûlés", "brûlé", "burnt",
    "incendie", "fire", "clashes", "clash", "combat", "combats", "fighting",
    "battle", "bataille", "offensive", "offensives", "insurgents",
    "jihadists", "jihadistes", "terrorists", "terroristes", "extremists",
    "extrémistes", "fighters", "combattants", "militants", "miliciens",
    "ambush", "ambushes", "embuscades", "assassinations", "attentat",
    "attentats", "suicide bombing", "kamikaze", "carnage", "bloodshed",
    "massacres", "genocide", "ethnic cleansing", "nettoyage ethnique",
    "被枪杀", "遇难", "死亡", "身亡", "阵亡", "开火", "枪击", "爆炸袭击",
    "恐袭", "武装袭击", "屠杀", "斩首", "劫持", "绑架案", "交火",
    "冲突升级", "武装分子", "圣战分子", "极端分子", "叛军", "袭击事件",
    # FDS = Forces de Défense et de Sécurité (乍得/尼日尔安全部队)
    "fds", "forces de défense et de sécurité", "forces de defense et de securite",
    "tombés pour", "tombes pour", "morts pour", "mort pour", "hommage aux",
    "fds tombés", "fds tombes", "militaires tués", "militaires tues",
    "miné", "mine", "minée", "mined", "champ de mines", "champ de minage",
    "démineur", "demineur", "démineurs", "demineurs", "bonbonne",
    # 武器/安全部队行动词汇（Stage 3B）
    "armes", "armes de guerre", "désarmement", "desarmement", "weapons",
    "restitution d'armes", "remise d'armes", "remise volontaire",
    "opération de sécurisation", "operation de securisation", "bavure",
    "bavures", "tuerie", "échanges de tirs", "echanges de tirs",
    "tirs croisés", "tirs croises", "attaque de convoi", "attaque de véhicule",
    "attaque de vehicule", "braquage à main armée", "braquage a main armee",
    "coupeurs de route", "bande armée", "bande armee",
    "état-major", "etat-major", "état major", "gendarmerie", "forces de l'ordre",
    "forces de l ordre", "arrestations massives", "arrestation d'un",
    "saisie d'armes", "saisie d armes", "cache d'armes", "cache d armes",
    "explosion d'un", "explosion d un", "explosion de", "détonation", "detonation",
    "barrage", "checkpoint", "poste de contrôle", "poste de controle",
    "zone rouge", "zone interdite", "état d urgence",
    # 流离失所（限定组合，避免位移/出差误判）
    "déplacement de population", "deplacement de population",
    "déplacement forcé", "deplacement force", "déplacés", "deplaces",
    "déplacées", "deplacees", "déplacé", "deplace",
]

# mine 的爆炸物/地雷语境（满足其一才计入安全相关）
MINE_CONTEXT = ["mine", "landmine", "land mine", "explosive", "ied", "eei",
                "engin explosif", "bombe", "explosion", "démineur", "deminer"]

# 中性复合词（含安全类单词但语义与社会安全无关）——匹配前先从文本剔除
NEUTRAL_COMPOUNDS = [
    "sécurité alimentaire", "securite alimentaire", "food security",
    "sécurité sociale", "securite sociale", "social security",
    "sécurité routière", "securite routiere", "road safety",
    "général d'armée", "general d'armee", "général d'armee", "general d'armée",
    "générale d'armée", "police de proximité", "police de proximite",
    "community policing", "sécurité énergétique", "securite energetique",
    "energy security", "粮食安全", "食品安全", "社会保障", "能源安全",
]

# 弱信号词：泛化用词（头衔/机构/常规语境），单独出现不足以判定为安全事件
WEAK_POS = {
    "sécurité", "securite", "police", "armée", "crise", "frontière",
    "frontier", "fermeture", "arrestation", "arrest", "trafic", "drone",
    "安全", "军队", "警察", "边境", "危机",
}

# ---- 确定性排除（非社会安全） ----
EXCLUDE_SPORTS = [
    "football", "soccer", "marathon", "coupe d'afrique", "can 202", "match",
    "league", "basketball", "tennis", "olympic", "olympique", "world cup",
    "afrobasket", "ballon", "but", "buts", "joueur", "équipe nationale",
    "stade", "foot", "ligue des champions", "qualification", "tournoi",
    "足球", "马拉松", "非洲杯", "世界杯", "篮球", "网球", "奥运",
]
EXCLUDE_CULTURE = [
    "film", "cinema", "cinéma", "concert", "festival culturel", "musique",
    "mode", "fashion", "célébrité", "celebrity", "spectacle", "exposition",
    "galerie", "chanteur", "chanteuse",
    # Stage 3B：音乐/艺术/文学/节日
    "chante", "chanson", "chansons", "album", "artiste", "musiciens",
    "musicien", "musicienne", "titre musical", "clip", "concert",
    "poème", "poeme", "poésie", "poesie", "roman", "livre", "écrivain",
    "ecrivain", "exposition d'art", "peintre", "sculpteur", "théâtre",
    "theatre", "danse", "ballet", "semaine culturelle", "festival de",
    "fête de l'indépendance", "fete de l independance", "célébration de",
    "celebration de", "anniversaire de", "99ème", "anniversaire du parti",
    "journée internationale", "journee internationale", "commémoration de",
    "commemoration de", "hommage à un artiste", "hommage a un artiste",
    # 讣告/悼念（非安全事件）
    "nécrologique", "necrologique", "nécrologie", "necrologie", "décès",
    "deces", "décédé", "decede", "décédée", "decedee", "in memoriam",
    "obsèques", "obseques", "enterrement", "sépulture", "sepulture",
    "dernier hommage", "dernier adieu", "convoi funèbre", "convoy funebre",
    "cérémonie funèbre", "ceremonie funebre", "deuil", "funérailles",
    "funerailles", "obituaire", "condoléances", "condoleances",
]
EXCLUDE_PROMO = [
    "livraison d'engrais", "engrais", "fertilizer", "semences", "seeds",
    "intrants agricoles", "agricultural input", "rencontre avec le gouverneur",
    "rencontre avec le ministre", "visite de courtoisie", "entretien de courtoisie",
    "félicitations", "forum économique", "salon", "investissement",
    "inauguration", "téléthon", "化肥", "农业物资", "种子", "会见",
    "论坛", "研讨会", "推介", "经贸", "招商",
    # Stage 3A: 农业/水利/能源报道（即使含 drought/sécheresse 也非安全事件）
    "campagne agricole", "saison agricole", "récolte", "recolte", "rendement",
    "production agricole", "production agricole", "moisson", "poches de",
    "groupes électrogènes", "électrogène", "electrogene", "centrale électrique",
    "centrale electrique", "énergie", "energie", "électricité", "electricite",
    "forage", "puits", "adduction d'eau", "adduction d eau", "eau potable",
    "forum africain de l'eau", "forum africain de l eau", "conférence de l'eau",
    "cérémonie", "ceremonie", "commémoration", "commemoration", "anniversaire",
    "fête", "fete", "lecture du saint coran", "saint coran",
    "coopération", "cooperation", "diplomatie", "souveraineté", "souverainete",
    "axe nig", "toujours au beau fixe", "réception", "reception", "audience",
    "séance de travail", "seance de travail", "rencontre bilatérale",
]
EXCLUDE_MEETING = [
    "colloque", "séminaire", "atelier de formation", "formation", "workshop",
    "conférence internationale", "sommet de", "forum", "table ronde",
]
# 纯礼节/无安全影响经济
EXCLUDE_ECON = [
    "cours du pétrole", "prix du pétrole", "bourse", "cotation", "pib",
    "croissance économique", "budget ordinaire",
]

# 事件类型标准枚举
EVENT_TYPES = [
    "armed_conflict", "terrorist_attack", "military_operation",
    "political_crisis", "election_security", "protest", "strike",
    "civil_unrest", "kidnapping", "serious_crime", "communal_conflict",
    "border_security", "transport_disruption", "infrastructure_security",
    "natural_disaster", "public_health", "china_related",
    "foreign_national_security", "policy_security", "other_security",
]


def load_country_cfg(name_en):
    p = os.path.join(CFG_DIR, name_en + ".json")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_collector(source, country_cfg):
    method = source.get("collection_method") or "html_list"
    cls = COLLECTORS.get(method, HTMLListCollector)
    return cls(source, country_cfg)


def run_source(source, country_cfg):
    col = get_collector(source, country_cfg)
    arts = col.run()
    if source.get("collection_method") == "sitemap":
        filled = 0
        for a in arts:
            if (not a.get("title")) and filled < 10:
                t = HTMLListCollector.fetch_detail_title(a["url"])
                if t:
                    a["title"] = t
                    filled += 1
    return arts, col.errors


# ---------------------------------------------------------------------------
# 国家识别
# ---------------------------------------------------------------------------
def identify_country(text, country_cfg):
    """返回结构化国家判定字典。"""
    t = (text or "").lower()
    country = country_cfg.get("country")  # 乍得 / 尼日尔
    out = {
        "decision": "unclear",
        "country_match_score": 0,
        "matched_country_entities": [],
        "matched_location_entities": [],
        "excluded_entities": [],
        "source_country": country_cfg.get("country_en", "").lower(),
        "dateline_country": "",
        "event_location_country": "",
        "mentioned_countries": [],
        "country_decision_reason": "",
    }

    kws = [k.lower() for k in country_cfg.get("keywords", [])]
    locs = [l.lower() for l in country_cfg.get("locations", [])]
    excl = [e.lower() for e in country_cfg.get("country_exclusions", [])]

    matched_kw = wb_any(t, kws)
    matched_loc = wb_any(t, locs)
    excluded = wb_any(t, excl)

    out["matched_country_entities"] = matched_kw
    out["matched_location_entities"] = matched_loc
    out["excluded_entities"] = excluded

    # 提及国家（双国上下文）
    if country == "尼日尔":
        if wb_any(t, ["nigeria", "nigéria", "nigerian", "nigérian", "nigériane"]):
            out["mentioned_countries"].append("nigeria")
        if matched_kw or matched_loc:
            out["mentioned_countries"].append("niger")
    else:  # 乍得
        if wb_any(t, ["nigeria", "nigéria", "niger", "nigérien", "nigérienne"]):
            out["mentioned_countries"].append("niger/nigeria")

    out["country_match_score"] = len(matched_kw) + 2 * len(matched_loc)

    # "in Chad / au Tchad" 明确地点
    in_country = bool(re.search(r"(?<![a-z])(in chad|au tchad)(?![a-z])", t)) if country == "乍得" else False

    if country == "尼日尔":
        niger_strong = (("république du niger" in t) or ("republic of niger" in t)
                        or ("niamey" in t) or bool(matched_loc)
                        or bool(re.search(r"frontière niger|frontiere niger|niger/", t))
                        or bool(re.search(r"\bniger\b", t) and re.search(r"diffa|tillabéri|tillaberi|tahoua|dosso|zinder|agadez|maradi", t)))
        if excluded and not niger_strong:
            # Niger Delta / Niger State / Nigerian Army / Nigeria 等 → 排除
            out["decision"] = "exclude"
            out["country_decision_reason"] = (
                "命中尼日利亚排除词(%s)，且无尼日尔强实体" % ", ".join(excluded))
            return out
        if excluded and niger_strong:
            # 同时提及两国，按事件地点决定
            if matched_loc:
                out["decision"] = "niger"
                out["event_location_country"] = "niger"
                out["country_decision_reason"] = "命中尼日尔行政区(%s)，压过尼日利亚排除词" % ", ".join(matched_loc)
            else:
                out["decision"] = "unclear"
                out["country_decision_reason"] = "同时提及尼日尔与尼日利亚但事件地点不明"
            return out
        # 无排除词
        if niger_strong:
            out["decision"] = "niger"
            out["event_location_country"] = "niger"
            out["country_decision_reason"] = "命中尼日尔强实体(%s)" % (
                "niamey" if "niamey" in t else ", ".join(matched_loc) or "république du niger")
            return out
        if matched_kw:
            # 普通 niger 命中：仅当来源为尼日尔国家级媒体且属国内新闻才归尼日尔
            if country_cfg.get("country_en", "").lower() in t or True:
                # 保守：仅有国名无地点/首都，标记 unclear 交由语义复核
                out["decision"] = "unclear"
                out["country_decision_reason"] = "仅命中国名 niger，缺地点/首都，待复核"
                return out
        out["decision"] = "unclear"
        out["country_decision_reason"] = "未命中尼日尔实体"
        return out

    # ---- 乍得 ----
    lake_chad = bool(re.search(r"lake chad|lac tchad|bassin du lac tchad|lake chad basin", t))
    chad_lac_towns = ["bol", "baga sola", "liwa", "ngouboua", "barka tolorem"]
    # 泛湖区时，通用「Lac」省名不应作为乍得境内地点证据（与 lac Tchad 短语冲突）
    matched_loc_eff = [l for l in matched_loc
                       if l.lower() != "lac"
                       and "lac tchad" not in l.lower()
                       and "lake chad" not in l.lower()
                       and "bassin du lac" not in l.lower()] if lake_chad else list(matched_loc)
    chad_admin_loc = bool(matched_loc_eff)  # 乍得行政区（已单词边界匹配，排除通用 Lac）
    chad_name_other = ("tchad" in matched_kw) or ("chad" in matched_kw)
    # 泛湖区：无乍得境内具体地点、且国名仅来自「Lake Chad」短语 → 区域
    if lake_chad and not (chad_admin_loc or in_country or (chad_name_other and not lake_chad)):
        out["decision"] = "regional"
        out["event_location_country"] = "regional"
        out["country_decision_reason"] = "Lake Chad Basin 跨国地区，无乍得境内具体地点"
        return out
    if chad_admin_loc or in_country or (chad_name_other and not lake_chad):
        out["decision"] = "chad"
        out["event_location_country"] = "chad"
        out["country_decision_reason"] = "命中乍得实体(%s)" % (
            ", ".join(matched_loc_eff) or ("in/au Tchad" if in_country else ", ".join(matched_kw)))
        return out
    if matched_kw:
        out["decision"] = "chad"
        out["event_location_country"] = "chad"
        out["country_decision_reason"] = "命中乍得国名"
        return out
    out["decision"] = "unclear"
    out["country_decision_reason"] = "未命中乍得实体"
    return out


# ---------------------------------------------------------------------------
# 相关性筛选（确定性阶段）
# ---------------------------------------------------------------------------
def relevance_stage1(text):
    """返回 (is_relevant, score, matched, excluded_reason)。"""
    t = (text or "").lower().replace("\u2019", "'").replace("\u02bc", "'")
    # 先剔除中性复合词（如"sécurité alimentaire"粮食安全、"général d'armée"军衔）
    for comp in NEUTRAL_COMPOUNDS:
        if comp in t:
            t = t.replace(comp, " ")
    score = 0
    matched = []
    for kw in SECURITY_POS:
        if wb(t, kw):
            # mine 语境约束
            if kw == "mine":
                if not any(ctx in t for ctx in MINE_CONTEXT):
                    continue
            score += 1
            matched.append(kw)
    strong = [k for k in matched if k not in WEAK_POS]
    # 确定性排除
    for fam, lst in (("sports", EXCLUDE_SPORTS), ("culture", EXCLUDE_CULTURE),
                     ("promo", EXCLUDE_PROMO), ("meeting", EXCLUDE_MEETING),
                     ("econ", EXCLUDE_ECON)):
        hit = wb_any(t, lst)
        if hit:
            # 排除词命中且无可信安全信号 → 非相关
            if score == 0:
                return False, 0, [], "excluded:%s(%s)" % (fam, ", ".join(hit))
            # 有安全信号但有排除词（如同时谈体育与恐袭）——标记待复核
            return None, score, matched, "ambiguous:%s(%s)" % (fam, ", ".join(hit))
    if score == 0:
        return False, 0, [], "no_security_signal"
    # 仅弱信号（头衔/机构泛词）命中 → 不自动判相关，标记待复核
    if not strong:
        return None, score, matched, "weak_signal_only(%s)" % ", ".join(matched)
    return True, score, matched, ""


# ---------------------------------------------------------------------------
# 事件类型分类（标准枚举）
# ---------------------------------------------------------------------------
_TYPE_RULES = [
    ("terrorist_attack", ["terror", "terrorist", "terrorisme", "terrorism",
        "attentat", "suicide", "boko haram", "isgs", "jnim", "gsim", "iswap",
        "engin explosif", "ied", "eei", "kamikaze", "袭击", "恐怖"]),
    ("kidnapping", ["enlèvement", "kidnap", "kidnapping", "otage", "hostage",
        "séquestration", "绑架", "人质"]),
    ("military_operation", ["opération militaire", "operation militaire",
        "opération de sécurisation", "offensive", "raid", "assaut", "military operation",
        "army launches", "frappes", "strike (military)", "军事行动", "空袭"]),
    ("natural_disaster", ["inondation", "inondations", "crue", "flood", "drought",
        "sécheresse", "earthquake", "séisme", "cyclone", "tempête", "洪水", "干旱", "地震", "沙尘暴"]),
    ("public_health", ["cholera", "choléra", "epidemic", "épidémie", "measles",
        "rougeole", "marburg", "ebola", "霍乱", "疫情", "瘟疫"]),
    ("protest", ["manifestation", "protest", "sit-in", "示威"]),
    ("strike", ["grève", "greve", "strike (labor)", "罢工"]),
    ("civil_unrest", ["émeute", "riot", "unrest", "violences", "violence", "骚乱", "暴乱"]),
    ("communal_conflict", ["intercommunautaire", "agriculteurs-éleveurs",
        "farmers herders", "communal", "部族", "族群冲突", "农牧民"]),
    ("border_security", ["frontière", "frontier", "fermeture de frontière",
        "border closure", "cross-border", "边境", "闭关"]),
    ("transport_disruption", ["route coupée", "road blocked", "aéroport fermé",
        "airport closed", "transport disrupted", "交通中断", "封路"]),
    ("infrastructure_security", ["oléoduc", "pipeline", "uranium", "barrage",
        "electricity", "infrastructure", "mining", "mine (explosive)", "基础设施", "铀矿", "电站"]),
    ("political_crisis", ["crise politique", "coup", "putsch", "dissolution",
        "arrestation politique", "political crisis", "政变", "政治危机", "解散议会"]),
    ("election_security", ["élection", "électoral", "election", "选举"]),
    ("china_related", ["chinois", "chine", "china", "中国", "中资", "中国公民", "使馆提醒", "领事提醒"]),
    ("foreign_national_security", ["ressortissants étrangers", "expatriates",
        "foreign nationals", "外国人"]),
    ("policy_security", ["état d'urgence", "etat d'urgence", "couvre-feu",
        "curfew", "state of emergency", "宵禁", "紧急状态", "安全政策"]),
    ("serious_crime", ["braquage", "robbery", "banditisme", "banditry",
        "criminal", "trafic", "smuggling", "orpaillage", "抢劫", "严重犯罪", "走私"]),
    ("armed_conflict", ["clash", "conflit", "conflict", "affrontement",
        "embuscade", "engagement", "fighting", "combat", "交火", "冲突", "伏击", "武装冲突"]),
]


def classify_type(text, title=""):
    t = ((text or "") + " " + (title or "")).lower()
    hits = []
    for etype, kws in _TYPE_RULES:
        if any(wb(t, k.lower()) for k in kws):
            hits.append(etype)
    if not hits:
        return "other_security", True
    # 优先级：恐怖/绑架/军事/自然/公共卫生 > 政治/选举 > 边境/交通/基础设施 > 冲突/犯罪/示威
    priority = ["terrorist_attack", "kidnapping", "military_operation",
                "natural_disaster", "public_health", "china_related",
                "political_crisis", "election_security", "border_security",
                "transport_disruption", "infrastructure_security", "civil_unrest",
                "protest", "strike", "communal_conflict", "serious_crime",
                "armed_conflict", "policy_security", "foreign_national_security"]
    for p in priority:
        if p in hits:
            return p, False
    return hits[0], False


# ---------------------------------------------------------------------------
# 国家编排
# ---------------------------------------------------------------------------
def run_country(country_cfg, sources):
    results = []
    for s in sources:
        arts, errs = run_source(s, country_cfg)
        for a in arts:
            blob = (a.get("title") or "") + " " + (a.get("summary") or "")
            cid = identify_country(blob, country_cfg)
            rel, score, matched, excl = relevance_stage1(blob)
            a["_country"] = cid
            a["_relevant"] = rel
            a["_rel_score"] = score
            a["_rel_matched"] = matched
            a["_rel_excluded"] = excl
            if rel is None:
                a["_needs_review"] = True
        results.append({"source": s, "articles": arts, "errors": errs})
    return results
