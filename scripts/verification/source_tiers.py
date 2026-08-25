#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 5 — 来源可信度分层（§四）。

第一版采用简单、可解释的规则（不做精细信誉评分）：
1. 已知域名/来源名映射 → 精确 tier（A/B）；
2. source_type=aggregation_platform 或聚合关键词 → Tier D（仅 lead）；
3. source_type=state_media / 官方关键词 → Tier A；
4. 国家级主流媒体关键词 → Tier B；
5. local_media / 未知 → Tier C 兜底；
6. 明确未确认/低稳定 → Tier D。
"""

from .constants import TIER_A, TIER_B, TIER_C, TIER_D, AGGREGATOR_KEYWORDS

# 高可信国际通讯社 / 权威国际机构（Tier A）
# 注：reliefweb.int 已移至 DISTRIBUTION_PLATFORM_DOMAINS（按 publisher 继承评级）
TIER_A_DOMAINS = {
    "reuters.com", "apnews.com", "afp.com",
    "who.int", "un.org", "unicef.org", "africacdc.org",
    "imf.org", "worldbank.org", "fao.org",
}
# 国际主流媒体 / 稳定区域媒体（Tier B）
TIER_B_DOMAINS = {
    "bbc.com", "bbc.co.uk", "rfi.fr", "france24.com", "aljazeera.com",
    "dw.com", "lemonde.fr", "theguardian.com", "nytimes.com", "arabnews.com",
    "aa.com.tr", "english.news.cn", "voanews.com", "irinnews.org",
}
# 已知本地/专题媒体（Tier C）
TIER_C_DOMAINS = {
    "tchadinfos.com", "alwihdainfo.com", "journaldutchad.com", "lepaystchad.com",
    "tchadone.com", "nigerdiaspora.net", "actuniger.com", "aoua.org",
    "radiotamazuj.org", "thetidenewsonline.com", "riotimesonline.com",
}
# 聚合平台（Tier D，仅 lead）
TIER_D_DOMAINS = {
    "newsnow.co.uk", "newsnow.com", "allafrica.com", "miragenews.com",
    "feedspot.com", "flipboard.com", "smartnews.com",
}

# 来源名关键词（不依赖域名时使用）
TIER_A_NAME_KEYWORDS = (
    "新华社", "新华网", "国家通讯社", "政府", "总统府", "外交部",
    "国防部", "卫生部", "世界卫生组织", "联合国", "非洲疾控", "红十字",
    "world health organization", "united nations", "africa cdc",
    "reuters", "associated press", "agence france presse", "afp",
)
TIER_B_NAME_KEYWORDS = (
    "bbc", "rfi", "france24", "al jazeera", "dw", "france presse",
    "人民日报", "中央电视台", "国家电视台", "national", "agency",
)
TIER_D_NAME_KEYWORDS = (
    "newsnow", "allafrica", "mirage news", "aggregat", "feedspot",
)


def _host_of(url):
    from urllib.parse import urlparse
    if not url:
        return ""
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""


def _registered_domain(host):
    """简化取注册域：取 host 最后两段（首段为 www 时取三段）。"""
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    if parts[0] in ("www", "m", "mobile"):
        return ".".join(parts[1:])
    return ".".join(parts[-2:])


# 分发平台（distribution platform）：本身不是原始事实来源，须按 publisher 继承评级
DISTRIBUTION_PLATFORM_DOMAINS = {"reliefweb.int", "reliefweb.unocha.org"}


def classify_tier(source_name="", url="", source_type="", publisher=""):
    """返回 (tier, reason)。tier ∈ {A,B,C,D}。

    优先级：分发平台（ReliefWeb 等）publisher 继承 > 域名精确映射（A/B/C/D）
    > 聚合名称关键词 > 官方/媒体名称关键词 > source_type 启发 > 兜底。

    ReliefWeb 规则（Stage 5 第二包修正）：
    - 页面明确提供原始发布机构（WHO/Africa CDC/UN 机构/国家卫生部/政府）→
      source trust 继承原始发布机构等级（publisher 递归评级）；
    - publisher 为 local NGO → 按 NGO 本身评级，不自动 Tier A；
    - 无法识别原始发布者 → 作为 distribution_platform，不高于 Tier C
      （稳定规则：Tier C，不作为 lead-only 排除）。
    """
    name = (source_name or "").strip().lower()
    host = _host_of(url)
    dom = _registered_domain(host)
    stype = (source_type or "").strip().lower()

    # 0) 分发平台（ReliefWeb 类）：publisher 继承评级
    if dom in DISTRIBUTION_PLATFORM_DOMAINS:
        if publisher and str(publisher).strip():
            pt, _ = classify_tier(str(publisher), "", "unknown")
            return pt, "reliefweb_publisher:%s" % publisher
        return TIER_C, "distribution_platform"

    # 1) 域名精确映射（最高优先，A/B/C/D 互斥）
    if dom in TIER_A_DOMAINS:
        return TIER_A, "domain_a"
    if dom in TIER_B_DOMAINS:
        return TIER_B, "domain_b"
    if dom in TIER_C_DOMAINS:
        return TIER_C, "domain_c"
    if dom in TIER_D_DOMAINS:
        return TIER_D, "aggregator_or_unverified"

    # 2) 聚合名称关键词（NewsNow 一类；域名未知时）
    if any(k in name for k in TIER_D_NAME_KEYWORDS) \
            or stype == "aggregation_platform":
        return TIER_D, "aggregator_or_unverified"

    # 3) 名称关键词
    if any(k in name for k in TIER_A_NAME_KEYWORDS):
        return TIER_A, "name_a"
    if any(k in name for k in TIER_B_NAME_KEYWORDS):
        return TIER_B, "name_b"

    # 4) source_type 启发
    if stype in ("state_media", "official"):
        return TIER_A, "state_media"
    if stype in ("international_media", "national_media"):
        return TIER_B, "media_type"
    if stype == "local_media":
        return TIER_C, "local_media"

    # 5) 兜底：有名称/URL 的本地类媒体 → C；完全未知 → D
    if name or dom:
        return TIER_C, "default_local"
    return TIER_D, "unknown"
