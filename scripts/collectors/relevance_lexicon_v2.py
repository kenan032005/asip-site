#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""relevance_lexicon_v2.py —— C2B §九–§十四：多语言安全相关性词表 V2。

设计纪律（严格遵守任务 §八/§十四/§十六）：
  * **只扩词汇覆盖，不降门槛**：判定逻辑（分数、strong 要求、排除族 veto）完全沿用
    `country_runner.relevance_stage1`，本模块只提供词表与分类；
  * **strong / weak 分级**：只有明确的暴力/犯罪/灾害语义才算强信号（可单独判定相关）；
    泛化的行政/机构/程序性词汇（警察、法院、监狱、边境、抗议等）算弱信号，
    单独出现**不足以**判定，需再有强信号；
  * **负例族继续生效**：sports / entertainment / celebrity / lifestyle / routine commercial
    在 score==0 时直接排除；score>0 时降级为 ambiguous(None) → **不会进入 News**，
    从而避免「Nigeria attacks down the wing」这类体育短语被当安全事件；
  * **Arabic = DEFERRED**：现有词边界类 `(?<![a-zà-ÿ0-9])` 不含阿拉伯字母，
    实测 `wb("المقتل في الصومال", "مقتل") == True`（在词内部误匹配），
    在缺少阿拉伯语分词/归一化前加入会造成大量误报 → 本轮不加，显式记录为 DEFERRED。

分类（§九）：ARMED_CONFLICT / TERRORISM_SECURITY / CRIME_PUBLIC_SAFETY / CIVIL_UNREST /
POLITICAL_STABILITY / DISASTER_EMERGENCY / BORDER_MIGRATION / PUBLIC_HEALTH
"""
from typing import Dict, List

VERSION = "v2"
ARABIC_RELEVANCE_SUPPORT = "DEFERRED"
ARABIC_DEFERRED_REASON = (
    "词边界类 (?<![a-zà-ÿ0-9]) 不覆盖阿拉伯字母，实测 wb('المقتل في الصومال','مقتل') "
    "为 True（词内误匹配）；在引入阿拉伯语归一化/分词前加入词表会产生大量 false positive，"
    "故本轮显式 DEFERRED，不临时拼凑。")

#: 分类 → 语言 → 强信号词（可单独判定为安全相关）
LEXICON: Dict[str, Dict[str, List[str]]] = {
    "ARMED_CONFLICT": {
        "en": ["attack", "armed attack", "clash", "clashes", "fighting", "gunfire",
               "shooting", "shootout", "killed", "kills", "dead", "deaths", "death toll",
               "wounded", "injured", "gunmen", "armed men", "assault", "ambush",
               "offensive", "shelling", "airstrike", "air strike", "militants",
               "insurgents", "militia", "armed group", "battle", "front line",
               "massacre", "atrocity", "armed clash"],
        "fr": ["attaque", "attaque armée", "affrontement", "fusillade", "tirs",
               "tué", "tués", "mort", "morts", "blessé", "blessés", "assaut",
               "embuscade", "offensive", "bombardement", "milice", "miliciens",
               "combattants", "insurgés", "massacre", "tuerie", "échanges de tirs"],
        "pt": ["ataque", "ataque armado", "confronto", "tiroteio", "disparos",
               "morto", "mortos", "ferido", "feridos", "assalto", "emboscada",
               "ofensiva", "bombardeamento", "milícia", "milicias", "insurgentes",
               "combatentes", "massacre", "chacina"],
    },
    "TERRORISM_SECURITY": {
        "en": ["terror", "terrorist", "terrorism", "bomb", "bombing", "explosion",
               "blast", "suicide bombing", "ied", "improvised explosive", "extremists",
               "jihadist", "radical", "hostage", "beheaded", "beheading"],
        "fr": ["terrorisme", "terroriste", "attentat", "attentats", "bombe",
               "explosion", "kamikaze", "engin explosif", "extrémistes",
               "djihadistes", "otage", "otages", "décapitation", "décapités"],
        "pt": ["terrorismo", "terrorista", "atentado", "bomba", "explosão",
               "explosões", "kamikaze", "engenho explosivo", "extremistas",
               "jihadistas", "refém", "reféns", "decapitação"],
    },
    "CRIME_PUBLIC_SAFETY": {
        "en": ["murder", "homicide", "corpse", "body found", "bodies found", "mutilated",
               "manslaughter", "stabbing", "stabbed", "shot dead", "kidnap",
               "kidnapping", "kidnapped", "abduction", "abducted", "hostage-taking",
               "ransom", "robbery", "armed robbery", "banditry", "armed bandits",
               "theft", "burglary", "carjacking", "drug trafficking", "drug smuggling",
               "heroin", "cocaine", "narcotics", "drug bust", "seized drugs",
               "smuggling", "human trafficking", "money laundering", "prison",
               "jailbreak", "prison break", "escaped inmates", "death sentence",
               "prosecuted", "indicted"],
        "fr": ["meurtre", "meurtres", "homicide", "assassinat", "assassinats",
               "corps retrouvé", "corps sans vie", "démembré", "mutilé", "poignardé",
               "enlèvement", "enlèvements", "enlevé", "rapt", "séquestration",
               "braquage", "vol à main armée", "banditisme", "coupeurs de route",
               "trafic de drogue", "trafic de stupéfiants", "stupéfiants",
               "saisie de drogue", "drogue", "trafic d'armes", "traite des personnes",
               "blanchiment", "prison", "évasion", "évadés", "condamné à mort"],
        "pt": ["homicídio", "homicidios", "assassinato", "assassinatos", "morte violenta",
               "corpo encontrado", "corpos encontrados", "esfaqueado", "mutilado",
               "rapto", "raptos", "sequestro", "sequestros", "refém", "resgate",
               "roubo", "assalto armado", "banditismo", "assaltantes armados",
               "furto", "carjacking", "tráfico de droga", "tráfico de estupefacientes",
               "narcóticos", "cocaína", "heroína", "apreensão de droga",
               "tráfico de armas", "tráfico de seres humanos", "prisão",
               "fuga da prisão", "evadidos", "pena de morte"],
    },
    "CIVIL_UNREST": {
        "en": ["riot", "riots", "protest", "protests", "demonstration",
               "violent protest", "violent demonstrations", "unrest", "looting",
               "tear gas", "curfew", "state of emergency", "general strike",
               "uprising", "crackdown"],
        "fr": ["émeute", "émeutes", "manifestation", "manifestations", "troubles",
               "pillage", "pillages", "gaz lacrymogène", "couvre-feu",
               "état d'urgence", "grève générale", "soulèvement", "répression",
               "manifestations violentes"],
        "pt": ["motim", "motins", "protesto", "protestos", "manifestação",
               "manifestações", "distúrbio", "distúrbios", "saque", "saques",
               "gás lacrimogéneo", "toque de recolher", "estado de emergência",
               "greve geral", "revolta", "repressão", "protestos violentos"],
    },
    "POLITICAL_STABILITY": {
        "en": ["coup", "coup attempt", "junta", "power grab", "impeachment",
               "constitutional crisis", "martial law", "political crisis",
               "election violence", "disputed election", "government collapse",
               "armed takeover"],
        "fr": ["coup d'état", "putsch", "junte", "prise de pouvoir",
               "crise constitutionnelle", "loi martiale", "crise politique",
               "violences électorales", "élection contestée", "chute du gouvernement"],
        "pt": ["golpe de estado", "junta", "tomada de poder",
               "crise constitucional", "lei marcial", "crise política",
               "violência eleitoral", "eleição contestada"],
    },
    "DISASTER_EMERGENCY": {
        "en": ["flood", "floods", "flooding", "earthquake", "landslide", "mudslide",
               "storm", "cyclone", "hurricane", "wildfire", "bushfire",
               "building collapse", "bridge collapse", "dam burst", "drought",
               "famine", "fire", "explosion"],
        "fr": ["inondation", "inondations", "crue", "séisme", "tremblement de terre",
               "glissement de terrain", "effondrement", "incendie", "cyclone",
               "sécheresse", "famine", "rupture de barrage"],
        "pt": ["inundação", "inundações", "cheia", "cheias", "sismo", "terramoto",
               "deslizamento", "deslizamento de terra", "colapso", "desabamento",
               "incêndio", "ciclone", "seca", "fome", "ruptura de barragem"],
    },
    "BORDER_MIGRATION": {
        "en": ["border closure", "border closed", "border crossing closed",
               "refugees", "refugee", "displacement", "displaced", "internally displaced",
               "idp camp", "migration crisis", "mass deportation", "repatriation",
               "asylum seekers"],
        "fr": ["fermeture de frontière", "frontière fermée", "réfugiés", "réfugié",
               "déplacés", "déplacées", "déplacement de population", "camps de déplacés",
               "crise migratoire", "expulsions massives", "rapatriement",
               "demandeurs d'asile"],
        "pt": ["fecho de fronteira", "fronteira fechada", "refugiados", "refugiado",
               "deslocados", "deslocadas", "deslocamento de população",
               "campos de deslocados", "crise migratória", "expulsões em massa",
               "requerentes de asilo"],
    },
    "PUBLIC_HEALTH": {
        "en": ["epidemic", "outbreak", "cholera", "measles", "ebola", "marburg",
               "malaria surge", "polio", "meningitis", "dengue", "mpox",
               "health emergency", "disease outbreak"],
        "fr": ["épidémie", "flambée", "choléra", "rougeole", "ebola", "marburg",
               "paludisme", "poliomyélite", "méningite", "dengue", "variole du singe",
               "urgence sanitaire"],
        "pt": ["epidemia", "surto", "cólera", "sarampo", "ébola", "marburg",
               "malária", "poliomielite", "meningite", "dengue", "varíola dos macacos",
               "emergência sanitária"],
    },
}

#: 弱信号（泛化行政/机构/程序性词汇）——单独出现不足以判定为安全事件
WEAK_TERMS_V2 = {
    "en": ["police", "army", "military", "security forces", "crisis", "border",
           "arrest", "arrested", "arrests", "drone", "court", "trial", "sentenced",
           "investigation", "authorities", "checkpoint", "military operation",
           "security operation", "patrol"],
    "fr": ["police", "armée", "forces de sécurité", "crise", "frontière",
           "arrestation", "arrestations", "arrêté", "drone", "tribunal",
           "procès", "condamnation", "enquête", "autorités", "barrage",
           "opération militaire", "opération de sécurisation"],
    "pt": ["polícia", "forças de segurança", "exército", "crise", "fronteira",
           "detenção", "detidos", "prisão preventiva", "drone", "tribunal",
           "julgamento", "condenação", "investigação", "autoridades",
           "operação militar", "barragem policial"],
    "zh": ["安全", "军队", "警察", "边境", "危机", "政权"],
}

#: 负例族（§十四）：体育/娱乐/名人/生活方式/常规商业
NEGATIVE_TERMS = {
    "sports": ["football", "soccer", "match", "league", "world cup", "olympic",
               "basketball", "tennis", "marathon", "stadium", "coach", "goalkeeper",
               "midfielder", "striker", "penalty", "champion", "tournament",
               "futebol", "jogo", "campeonato", "copa", "jogador", "treinador",
               "estádio", "selecção", "seleção", "足球", "世界杯", "篮球", "网球"],
    "entertainment": ["film", "movie", "cinema", "concert", "music", "album",
                      "singer", "actor", "actress", "celebrity", "festival",
                      "nollywood", "ballet", "theatre", "showbiz",
                      "filme", "cinema", "música", "cantor", "cantora", "ator",
                      "atriz", "celebridade", "festival", "影", "娱乐", "明星"],
    "lifestyle": ["fashion", "beauty", "recipe", "cuisine", "travel tips",
                  "horoscope", "wedding", "fitness", "shopping",
                  "moda", "beleza", "receita", "culinária", "viagem", "horóscopo",
                  "casamento", "时尚", "美食", "旅游"],
    "commercial": ["ipo", "stock market", "share price", "earnings", "profit",
                   "revenue", "gdp growth", "inflation rate", "quarterly results",
                   "startup funding", "product launch",
                   "bolsa de valores", "lucro", "receita", "ações", "上市", "股价"],
}


def flat_strong():
    """全部强信号词（去重、小写）。"""
    out = set()
    for cats in LEXICON.values():
        for terms in cats.values():
            out.update(t.lower() for t in terms)
    return sorted(out)


def flat_weak():
    out = set()
    for terms in WEAK_TERMS_V2.values():
        out.update(t.lower() for t in terms)
    return sorted(out)


def flat_negative():
    out = set()
    for terms in NEGATIVE_TERMS.values():
        out.update(t.lower() for t in terms)
    return sorted(out)


def categories_of(term):
    """某词所属分类（用于可解释性输出）。"""
    t = str(term).lower()
    return sorted(c for c, langs in LEXICON.items()
                  if any(t in {x.lower() for x in ts} for ts in langs.values()))


def stats():
    return {
        "version": VERSION,
        "categories": {c: {lg: len(ts) for lg, ts in langs.items()}
                       for c, langs in LEXICON.items()},
        "strong_terms_total": len(flat_strong()),
        "weak_terms_total": len(flat_weak()),
        "negative_terms_total": len(flat_negative()),
        "arabic_relevance_support": ARABIC_RELEVANCE_SUPPORT,
    }
