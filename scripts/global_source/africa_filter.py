#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Global Source Layer — Africa 确定性过滤（§十四，Source Expansion A）。

对全球 feed（如 Al Jazeera）发现的 item 做确定性过滤，判断是否为非洲相关。
依据：ISO 国家 reference / 国家英文法文别名 / 区域关键词。
不用 AI。只用于 candidate discovery，不决定 event primary_country。
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# 非洲 ISO3 / ISO2（含北非），覆盖常见拼写与中/英/法别名
AFRICA_COUNTRY_ALIASES = {
    "DZ": ["algeria", "algérie", "algerie", "阿尔及利亚"],
    "AO": ["angola", "安哥拉"],
    "BJ": ["benin", "bénin", "贝宁"],
    "BW": ["botswana", "博茨瓦纳"],
    "BF": ["burkina faso", "burkina", "布基纳法索"],
    "BI": ["burundi", "布隆迪"],
    "CV": ["cabo verde", "cape verde", "佛得角"],
    "CM": ["cameroon", "cameroun", "喀麦隆"],
    "CF": ["central african republic", "centrafrique", "中非共和国", "中非"],
    "TD": ["chad", "tchad", "乍得"],
    "KM": ["comoros", "科摩罗"],
    "CG": ["congo", "刚果（布）", "刚果布"],
    "CD": ["democratic republic of congo", "dr congo", "rdc", "congo kinshasa", "刚果（金）", "刚果金", "扎伊尔"],
    "CI": ["cote d'ivoire", "ivory coast", "côte d'ivoire", "科特迪瓦"],
    "DJ": ["djibouti", "吉布提"],
    "EG": ["egypt", "égypte", "埃及"],
    "GQ": ["equatorial guinea", "guinée équatoriale", "赤道几内亚"],
    "ER": ["eritrea", "厄立特里亚"],
    "SZ": ["eswatini", "swaziland", "斯威士兰"],
    "ET": ["ethiopia", "éthiopie", "埃塞俄比亚"],
    "GA": ["gabon", "加蓬"],
    "GM": ["gambia", "冈比亚"],
    "GH": ["ghana", "加纳"],
    "GN": ["guinea", "guinée", "几内亚"],
    "GW": ["guinea-bissau", "guinée-bissau", "几内亚比绍"],
    "KE": ["kenya", "肯尼亚"],
    "LS": ["lesotho", "莱索托"],
    "LR": ["liberia", "利比里亚"],
    "LY": ["libya", "libye", "利比亚"],
    "MG": ["madagascar", "马达加斯加"],
    "MW": ["malawi", "马拉维"],
    "ML": ["mali", "马里"],
    "MR": ["mauritania", "mauritanie", "毛里塔尼亚"],
    "MU": ["mauritius", "毛里求斯"],
    "MA": ["morocco", "maroc", "摩洛哥"],
    "MZ": ["mozambique", "莫桑比克"],
    "NA": ["namibia", "纳米比亚"],
    "NE": ["niger", "尼日尔"],
    "NG": ["nigeria", "尼日利亚"],
    "RW": ["rwanda", "卢旺达"],
    "ST": ["sao tome", "são tomé", "圣多美"],
    "SN": ["senegal", "sénégal", "塞内加尔"],
    "SC": ["seychelles", "塞舌尔"],
    "SL": ["sierra leone", "塞拉利昂"],
    "SO": ["somalia", "索马里"],
    "ZA": ["south africa", "afrique du sud", "南非"],
    "SS": ["south sudan", "南苏丹"],
    "SD": ["sudan", "soudan", "苏丹"],
    "TZ": ["tanzania", "坦桑尼亚"],
    "TG": ["togo", "多哥"],
    "TN": ["tunisia", "tunisie", "突尼斯"],
    "UG": ["uganda", "乌干达"],
    "EH": ["western sahara", "西撒哈拉"],
    "ZM": ["zambia", "赞比亚"],
    "ZW": ["zimbabwe", "津巴布韦"],
}

# 区域关键词（不含 AI 判断；命中即视为非洲语境）
AFRICA_REGION_KEYWORDS = [
    "africa", "african", "afrique", "africain", "africaine",
    "sahel", "sahélien", "sahéliens",
    "horn of africa", "corne de l'afrique",
    "west africa", "afrique de l'ouest", "africa occidentale",
    "central africa", "afrique centrale", "africa centrale",
    "east africa", "afrique de l'est", "africa orientale",
    "southern africa", "afrique australe", "africa meridionale",
    "north africa", "afrique du nord", "africa settentrionale",
    "sub-saharan", "subsaharan", "sub-saharienne",
    "lake chad", "lac tchad", "bassin du lac tchad",
    "great lakes africa", "grands lacs",
]

# 主要城市别名（非洲首都/主要城市，用于标题过滤）
AFRICA_CITY_KEYWORDS = [
    "ndjamena", "n'djamena", "abuja", "lagos", "nairobi", "addis ababa",
    "accra", "dakar", "bamako", "niamey", "ouagadougou", "cairo", "algiers",
    "tunis", "rabat", "casablanca", "kinshasa", "brazzaville", "luanda",
    "maputo", "harare", "lusaka", "kampala", "kigali", "bujumbura",
    "antananarivo", "khartoum", "juba", "mogadishu", "asmera",
]


def _norm(text):
    return (text or "").lower()


def is_africa_text(text):
    """确定性判断一段文本（标题+摘要+URL）是否涉及非洲。"""
    t = _norm(text)
    if not t:
        return False
    if any(kw in t for kw in AFRICA_REGION_KEYWORDS):
        return True
    for iso2, aliases in AFRICA_COUNTRY_ALIASES.items():
        for a in aliases:
            if a in t:
                return True
    for city in AFRICA_CITY_KEYWORDS:
        if city in t:
            return True
    return False


def country_hints(text):
    """从文本中提取命中的非洲国家 ISO2 列表（用于 candidate 提示，不裁决 primary）。"""
    t = _norm(text)
    hits = []
    for iso2, aliases in AFRICA_COUNTRY_ALIASES.items():
        if any(a in t for a in aliases):
            hits.append(iso2)
    return sorted(set(hits))


def filter_candidates(items, text_fields=("title", "summary", "url")):
    """对 candidate 列表做 Africa 过滤。返回 (africa_items, filtered_items)。"""
    africa, filtered = [], []
    for it in items:
        text = " ".join(str(it.get(k) or "") for k in text_fields)
        if is_africa_text(text):
            it["africa_filter"] = "pass"
            africa.append(it)
        else:
            it["africa_filter"] = "filtered_non_africa"
            filtered.append(it)
    return africa, filtered
