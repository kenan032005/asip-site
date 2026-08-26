#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6B §二 — Deterministic Event-Country Attribution。

修复 source country ≠ event country：
- source registry 的 country_iso3 只表示 source coverage / profile，
  不得自动成为 event_primary_country；
- event_primary_country 必须来自 article 自身证据（title / body / location /
  detected_locations / 已有 canonical event_country）；
- 正文不足 → event_primary_country = None（uncertain），不得用 source country 硬填；
- 跨国/泛非洲源（Radio Tamazuj、Sudan Tribune、Alwihda、AllAfrica、Al Jazeera、
  BBC、RFI、F24、Reuters、AP、ReliefWeb、WHO、Africa CDC 等）绝不 fallback。

不用 AI。纯确定性。输出字段：
  event_primary_country   ISO3 或 None
  mentioned_countries     [ISO3] 文本中出现的国家
  attribution_basis       text | canonical | ambiguous | insufficient_text
  confidence              high | low | none
"""

from scripts.global_source.africa_filter import (
    AFRICA_COUNTRY_ALIASES, _norm,
)

# 全部非洲 ISO2 → ISO3（含北非）
ISO2_TO_ISO3 = {
    "DZ": "DZA", "AO": "AGO", "BJ": "BEN", "BW": "BWA", "BF": "BFA",
    "BI": "BDI", "CV": "CPV", "CM": "CMR", "CF": "CAF", "TD": "TCD",
    "KM": "COM", "CG": "COG", "CD": "COD", "CI": "CIV", "DJ": "DJI",
    "EG": "EGY", "GQ": "GNQ", "ER": "ERI", "SZ": "SWZ", "ET": "ETH",
    "GA": "GAB", "GM": "GMB", "GH": "GHA", "GN": "GIN", "GW": "GNB",
    "KE": "KEN", "LS": "LSO", "LR": "LBR", "LY": "LBY", "MG": "MDG",
    "MW": "MWI", "ML": "MLI", "MR": "MRT", "MU": "MUS", "MA": "MAR",
    "MZ": "MOZ", "NA": "NAM", "NE": "NER", "NG": "NGA", "RW": "RWA",
    "ST": "STP", "SN": "SEN", "SC": "SYC", "SL": "SLE", "SO": "SOM",
    "ZA": "ZAF", "SS": "SSD", "SD": "SDN", "TZ": "TZA", "TG": "TGO",
    "TN": "TUN", "UG": "UGA", "EH": "ESH", "ZM": "ZMB", "ZW": "ZWE",
}

# 长别名压制短别名（避免 "south sudan" 同时命中 SS 与 SD 等子串误判）
_ALIAS_SUPPRESS = [
    ("SS", "SD", "south sudan"),
    ("CD", "CG", "dr congo"),
    ("CD", "CG", "rdc"),
    ("CD", "CG", "congo kinshasa"),
    ("GQ", "GN", "guinée équatoriale"),
    ("GQ", "GN", "equatorial guinea"),
    ("BF", "BF", "burkina faso"),   # 无实际压制，占位保持语义清晰
]

# 跨国/泛非洲源：文本不足时绝不 fallback 到 source country
MULTINATIONAL_SOURCE_IDS = {
    "global_reuters_africa", "global_ap_africa", "global_bbc_africa",
    "global_rfi_afrique", "global_france24_afrique_fr",
    "global_france24_africa_en", "global_aljazeera", "global_allafrica",
    "global_reliefweb", "disease_who_don", "disease_who_afro",
    "disease_africa_cdc",
}
MULTINATIONAL_SOURCE_GROUPS = {
    "allafrica", "reliefweb", "france24", "bbc", "rfi", "aljazeera",
    "reuters", "ap", "who", "africacdc",
}
# 已知区域/跨国国家媒体（即使挂在 country registry 下）
MULTINATIONAL_COUNTRY_SOURCES = {
    "tcd_alwihda", "ssd_radio_tamazuj", "ssd_sudantribune",
}


def country_hints_clean(text):
    """从文本提取非洲国家 ISO2，应用长别名压制（south sudan ⊃ sudan 等）。"""
    t = _norm(text)
    if not t:
        return []
    hits = []
    for iso2, aliases in AFRICA_COUNTRY_ALIASES.items():
        if any(a in t for a in aliases):
            hits.append(iso2)
    for long_iso, short_iso, marker in _ALIAS_SUPPRESS:
        if long_iso in hits and short_iso in hits and marker in t:
            hits.remove(short_iso)
    return sorted(set(hits))


def _country_from_named(value):
    """'乍得' / 'Chad' / 'Tchad' / ISO2/ISO3 → ISO3 或 None。"""
    if not value:
        return None
    v = str(value).strip()
    up = v.upper()
    if up in ISO2_TO_ISO3:
        return ISO2_TO_ISO3[up]
    if up in set(ISO2_TO_ISO3.values()):
        return up
    t = _norm(v)
    for iso2, aliases in AFRICA_COUNTRY_ALIASES.items():
        if any(a in t for a in aliases):
            return ISO2_TO_ISO3[iso2]
    return None


def is_multinational(source):
    """source（registry dict 或 None）是否为跨国/泛非洲源（绝不 fallback）。"""
    if not source:
        return False
    sid = source.get("source_id", "")
    sg = (source.get("source_group") or "").lower()
    if sid in MULTINATIONAL_SOURCE_IDS or sid in MULTINATIONAL_COUNTRY_SOURCES:
        return True
    if sg in MULTINATIONAL_SOURCE_GROUPS:
        return True
    if source.get("scope") != "country":
        return True
    if source.get("country_filter_required"):
        return True
    return False


def attribute_event_country(article, source=None):
    """deterministic event-country attribution。

    article 可含：title / body / body_extracted / location / detected_locations /
    event_country（Stage3 canonical 已裁决）/ mentioned_countries。
    返回 {event_primary_country, mentioned_countries, attribution_basis, confidence}。
    """
    # 1. 已有 canonical event_country（Stage3 裁决）优先复用
    ec = article.get("event_country")
    iso3 = _country_from_named(ec) if ec else None
    if iso3:
        m = article.get("mentioned_countries") or [iso3]
        mentioned = sorted({
            (_country_from_named(x) or x) for x in m if x})
        return {
            "event_primary_country": iso3,
            "mentioned_countries": [x for x in mentioned if x],
            "attribution_basis": "canonical",
            "confidence": "high",
        }

    # 2. 文本证据：title + body + location + detected_locations
    parts = [article.get("title"), article.get("body"), article.get("body_extracted"),
             article.get("location"), article.get("location_raw"),
             article.get("detected_locations")]
    text = " ".join(str(x or "") for x in parts)
    hits = country_hints_clean(text)
    mentioned = [ISO2_TO_ISO3[h] for h in hits]

    # 3. mentioned_countries 字段（如有）补充
    extra = article.get("mentioned_countries") or []
    for x in extra:
        c = _country_from_named(x)
        if c and c not in mentioned:
            mentioned.append(c)
    mentioned = sorted(set(mentioned))

    if len(hits) == 1 and len(mentioned) == 1:
        return {"event_primary_country": mentioned[0], "mentioned_countries": mentioned,
                "attribution_basis": "text", "confidence": "high"}
    if len(hits) >= 2 or len(mentioned) >= 2:
        return {"event_primary_country": None, "mentioned_countries": mentioned,
                "attribution_basis": "ambiguous", "confidence": "low"}

    # 4. 零文本证据：不得用 source country 硬填 → None
    return {"event_primary_country": None, "mentioned_countries": [],
            "attribution_basis": "insufficient_text", "confidence": "none"}
