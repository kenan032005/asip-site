#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 国家表示归一化（避免 TD vs 乍得 假冲突）。

第一版覆盖非洲区域常用中文/英文国名 → ISO2。未命中返回原值。
"""

import re

# 中文/英文国名 → ISO2（非洲区域常用 + 项目覆盖国）
COUNTRY_ALIASES = {
    # 中文
    "乍得": "TD", "尼日尔": "NE", "苏丹": "SD", "南苏丹": "SS",
    "尼日利亚": "NG", "肯尼亚": "KE", "埃塞俄比亚": "ET", "利比亚": "LY",
    "贝宁": "BJ", "莫桑比克": "MZ", "喀麦隆": "CM", "中非": "CF",
    "中非共和国": "CF", "马里": "ML", "布基纳法索": "BF", "科特迪瓦": "CI",
    "塞内加尔": "SN", "加纳": "GH", "多哥": "TG", "几内亚": "GN",
    "冈比亚": "GM", "佛得角": "CV", "毛里塔尼亚": "MR", "阿尔及利亚": "DZ",
    "突尼斯": "TN", "埃及": "EG", "摩洛哥": "MA", "索马里": "SO",
    "厄立特里亚": "ER", "吉布提": "DJ", "卢旺达": "RW", "布隆迪": "BI",
    "乌干达": "UG", "坦桑尼亚": "TZ", "赞比亚": "ZM", "津巴布韦": "ZW",
    "博茨瓦纳": "BW", "纳米比亚": "NA", "南非": "ZA", "莱索托": "LS",
    "斯威士兰": "SZ", "马达加斯加": "MG", "毛里求斯": "MU", "科摩罗": "KM",
    "塞舌尔": "SC", "马拉维": "MW", "安哥拉": "AO", "刚果民主共和国": "CD",
    "刚果（金）": "CD", "刚果（布）": "CG", "刚果共和国": "CG", "加蓬": "GA",
    "赤道几内亚": "GQ", "圣多美和普林西比": "ST",
    # 英文
    "chad": "TD", "niger": "NE", "sudan": "SD", "south sudan": "SS",
    "nigeria": "NG", "kenya": "KE", "ethiopia": "ET", "libya": "LY",
    "benin": "BJ", "mozambique": "MZ", "cameroon": "CM", "central african republic": "CF",
    "mali": "ML", "burkina faso": "BF", "cote d'ivoire": "CI", "senegal": "SN",
    "ghana": "GH", "togo": "TG", "guinea": "GN", "gambia": "GM",
    "cape verde": "CV", "mauritania": "MR", "algeria": "DZ", "tunisia": "TN",
    "egypt": "EG", "morocco": "MA", "somalia": "SO", "eritrea": "ER",
    "djibouti": "DJ", "rwanda": "RW", "burundi": "BI", "uganda": "UG",
    "tanzania": "TZ", "zambia": "ZM", "zimbabwe": "ZW", "botswana": "BW",
    "namibia": "NA", "south africa": "ZA", "lesotho": "LS", "eswatini": "SZ",
    "swaziland": "SZ", "madagascar": "MG", "mauritius": "MU", "comoros": "KM",
    "seychelles": "SC", "malawi": "MW", "angola": "AO", "dr congo": "CD",
    "congo": "CG", "gabon": "GA", "equatorial guinea": "GQ", "sao tome and principe": "ST",
}

_ISO2_OR_ISO3_RE = re.compile(r"^[A-Za-z]{2,3}$")


def normalize_country(value):
    """把国家表示归一化为 ISO2。已是 ISO2/ISO3 直接大写返回；别名表命中转换；
    未命中返回原值（不猜测）。"""
    if value is None:
        return ""
    v = str(value).strip()
    if not v:
        return ""
    if _ISO2_OR_ISO3_RE.match(v):
        return v.upper()
    return COUNTRY_ALIASES.get(v.lower(), v)
