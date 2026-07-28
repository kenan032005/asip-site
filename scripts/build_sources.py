#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_sources.py —— 生成 expanded data/sources.json（第二轮整改）。

为每个国家生成结构化来源清单：
  - 当地媒体/官方（RSS/HTML）
  - 国际大型媒体（Reuters / Xinhua 强制，AP/AFP/BBC/RFI/Al Jazeera/AllAfrica 等，GDELT domain 检索）
  - 联合国/人道/专业（ReliefWeb API + GDELT domain 检索）
  - 中国相关（外交部/使馆/中新网/央视/CGTN/中国日报，GDELT domain 检索）

每个来源含需求文档第十五节全部字段。真实检测/成功时间由 collect.py 运行写入。
"""
import os
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# 尼日尔排除词（防尼日利亚误判）
NIGER_EXCL = ["Nigeria", "Nigerian", "Niger State", "Niger Delta", "Benin City",
              "Abuja", "Lagos", "Nigéria", "nigérian", "nigériane",
              "delta du Niger", "État du Niger", "Niger River", "fleuve Niger"]


def S(source_id, name, country, url, language, source_type, source_position,
      method, collection=None, feed_url="", category_urls=None, query="",
      domain="", enabled=True, tested=True, lead_only=False, requires_api=False,
      notes=""):
    return {
        "source_id": source_id, "name": name, "country": country, "url": url,
        "language": language, "source_type": source_type,
        "source_position": source_position, "collection_method": method,
        "feed_url": feed_url,
        "category_urls": category_urls or [],
        "query": query, "domain": domain,
        "enabled": enabled, "tested": tested, "lead_only": lead_only,
        "requires_api": requires_api, "last_test_at": "", "last_success_at": "",
        "last_failure_at": "", "failure_count": 0, "articles_detected_last_run": 0,
        "relevant_articles_last_run": 0, "status": "active" if tested else "paused",
        "notes": notes,
    }


def build():
    sources = []

    # ===================== 乍得 =====================
    chad_local = [
        S("chad_tchadinfos", "Tchadinfos", "乍得", "https://tchadinfos.com/",
          "法语", "local_media", "local_media", "rss",
          feed_url="https://tchadinfos.com/feed/", category_urls=["https://tchadinfos.com/category/securite/"],
          notes="第一优先级当地媒体，RSS 可用"),
        S("chad_alwihda", "Alwihda Info", "乍得", "https://www.alwihdainfo.com/",
          "法语", "local_media", "local_media", "rss",
          feed_url="https://www.alwihdainfo.com/rss", category_urls=["https://www.alwihdainfo.com/tchad/"],
          notes="泛区域媒体，需国家识别过滤"),
        S("chad_lendjampost", "Le N'Djam Post", "乍得", "https://lendjampost.com/",
          "法语", "local_media", "local_media", "rss",
          feed_url="https://lendjampost.com/feed/", notes="安全/治安/边境重点"),
        S("chad_journaldutchad", "Journal du Tchad", "乍得", "https://journaldutchad.com/",
          "法语", "local_media", "local_media", "rss",
          feed_url="https://journaldutchad.com/feed/", notes="政治/社会/安全栏目"),
        S("chad_tchadone", "Tchad One", "乍得", "https://tchadone.com/",
          "法语", "commentary", "commentary", "rss",
          feed_url="https://tchadone.com/feed/", lead_only=True,
          notes="评论性较强，仅作线索，事实稿可进候选"),
        S("chad_toumaiweb", "Toumaï Web Médias", "乍得", "https://www.toumaiwebmedias.com/",
          "法语", "local_media", "local_media", "rss",
          feed_url="https://www.toumaiwebmedias.com/feed/", notes="地方突发事件/安全"),
        S("chad_tachad", "Tachad.com", "乍得", "https://www.tachad.com/",
          "法语", "local_media", "local_media", "rss",
          feed_url="https://www.tachad.com/feed/", notes="综合当地媒体"),
        S("chad_presidence", "乍得总统府", "乍得", "https://presidence.td/",
          "法语", "official", "official", "rss",
          feed_url="https://presidence.td/feed/", notes="官方声明来源"),
        S("chad_portail", "乍得复兴门户", "乍得", "https://portail.td/",
          "法语", "official", "official", "rss",
          feed_url="https://portail.td/feed/", notes="政府/国家政策信息"),
    ]
    sources += chad_local

    # ===================== 尼日尔 =====================
    niger_local = [
        S("niger_actuniger", "ActuNiger", "尼日尔", "https://www.actuniger.com/",
          "法语", "local_media", "local_media", "rss",
          feed_url="https://www.actuniger.com/feed/", category_urls=["https://www.actuniger.com/category/securite/"],
          notes="第一优先级；安全/国防重点栏目"),
        S("niger_anp", "ANP(尼日尔官方通讯社)", "尼日尔", "https://anp.ne/",
          "法语", "official", "official", "rss",
          feed_url="https://anp.ne/feed/", notes="官方通讯社，标记 official"),
        S("niger_studiokalangou", "Studio Kalangou", "尼日尔", "https://www.studiokalangou.org/",
          "法语", "local_media", "local_media", "rss",
          feed_url="https://www.studiokalangou.org/feed/", notes="新闻文字稿/安全/边境"),
        S("niger_lesahel", "Le Sahel", "尼日尔", "https://www.lesahel.org/",
          "法语", "state_media", "state_media", "rss",
          feed_url="https://www.lesahel.org/feed/", notes="官方背景，标记 state_media"),
        S("niger_airinfo", "Aïr Info", "尼日尔", "https://airinfoagadez.com/",
          "法语", "local_media", "local_media", "rss",
          feed_url="https://airinfoagadez.com/feed/", notes="阿加德兹/北部重点"),
        S("niger_nigerinter", "Niger Inter", "尼日尔", "https://nigerinter.com/",
          "法语", "local_media", "local_media", "rss",
          feed_url="https://nigerinter.com/feed/", notes="国防安全/城市治安"),
        S("niger_tamtaminfo", "Tamtaminfo", "尼日尔", "https://tamtaminfo.com/",
          "法语", "local_media", "local_media", "rss",
          feed_url="https://tamtaminfo.com/feed/", notes="综合媒体"),
        S("niger_nigerdiaspora", "Niger Diaspora", "尼日尔", "https://nigerdiaspora.net/",
          "法语", "local_media", "local_media", "rss",
          feed_url="https://nigerdiaspora.net/feed/", notes="侨民视角，需核实"),
        S("niger_nigerinfos", "Niger Infos", "尼日尔", "https://nigerinfos.com/",
          "法语", "local_media", "local_media", "rss",
          feed_url="https://nigerinfos.com/feed/", notes="综合媒体"),
        S("niger_journalduniger", "Journal du Niger", "尼日尔", "https://www.journalduniger.com/",
          "法语", "local_media", "local_media", "rss",
          feed_url="https://www.journalduniger.com/feed/", notes="综合媒体"),
    ]
    sources += niger_local

    # ===================== 国际大型媒体（GDELT domain 检索） =====================
    intl = [
        ("reuters", "Reuters", "reuters", "domain:reuters.com"),
        ("xinhua", "新华社/新华网", "xinhua", "domain:news.cn OR domain:xinhuanet.com"),
        ("ap", "Associated Press", "ap", "domain:apnews.com"),
        ("afp", "AFP", "afp", "domain:afp.com OR domain:france24.com"),
        ("bbc", "BBC Afrique", "bbc", "domain:bbc.com"),
        ("rfi", "RFI Afrique", "rfi", "domain:rfi.fr"),
        ("france24", "France 24 Afrique", "france24", "domain:france24.com"),
        ("voa", "VOA Afrique", "voa", "domain:voaafrique.com"),
        ("dw", "DW Afrique", "dw", "domain:dw.com"),
        ("aljazeera", "Al Jazeera", "aljazeera", "domain:aljazeera.com"),
        ("africanews", "Africanews", "africanews", "domain:africanews.com"),
        ("allafrica", "AllAfrica", "allafrica", "domain:allafrica.net"),
        ("guardian", "The Guardian Africa", "guardian", "domain:theguardian.com"),
        ("humanitarian", "The New Humanitarian", "humanitarian", "domain:thenewhumanitarian.org"),
        ("jeuneafrique", "Jeune Afrique", "jeuneafrique", "domain:jeuneafrique.com"),
        ("apa", "APA News", "apa", "domain:apanews.com"),
    ]
    for country, c_en, c_excl_note in (("乍得", "Chad", "Chad OR N'Djamena OR \"Lake Chad\" OR \"Boko Haram Chad\" OR \"Chad Sudan border\""),
                                        ("尼日尔", "Niger", "Niger OR Niamey OR Tillaberi OR Diffa OR Agadez OR \"Niger junta\" OR \"Niger border\"")):
        for key, name, grp, dom in intl:
            # GDELT 语法：括号仅可包 OR 组；AND 用空格隐式表达
            dom_part = "(%s)" % dom if " OR " in dom else dom
            q = "%s %s" % (dom_part, c_en)
            pos = "official" if key in ("reuters",) else "international"
            notes = "强制接入" if key in ("reuters", "xinhua") else "国际大型媒体"
            sources.append(S("intl_%s_%s" % (key, "chad" if country == "乍得" else "niger"),
                              name + ("（乍得）" if country == "乍得" else "（尼日尔）"),
                              country, "https://www.%s.com/" % key if key != "xinhua" else "https://www.news.cn/",
                              "英语" if key not in ("rfi", "france24", "jeuneafrique") else "法语",
                              "international", pos, "gdelt_search",
                              query=q, domain=dom, notes=notes))

    # ===================== 联合国/人道/专业 =====================
    un_list = [
        ("reliefweb", "ReliefWeb", "reliefweb", "reliefweb_api"),
        ("unhcr", "UNHCR", "unhcr", "domain:unhcr.org"),
        ("iom", "IOM/DTM", "iom", "domain:iom.int"),
        ("wfp", "WFP", "wfp", "domain:wfp.org"),
        ("unicef", "UNICEF", "unicef", "domain:unicef.org"),
        ("icrc", "ICRC", "icrc", "domain:icrc.org"),
        ("msf", "MSF", "msf", "domain:msf.org"),
        ("fewsnet", "FEWS NET", "fewsnet", "domain:fews.net"),
        ("unnews", "UN News", "unnews", "domain:news.un.org"),
        ("au", "African Union", "au", "domain:au.int"),
        ("crisisgroup", "International Crisis Group", "crisis", "domain:crisisgroup.org"),
        ("iss", "ISS Africa", "iss", "domain:issafrica.org"),
        ("acled", "ACLED", "acled", "domain:acleddata.com"),
    ]
    for country, c_en in (("乍得", "Chad"), ("尼日尔", "Niger")):
        for key, name, grp, method in un_list:
            if method == "reliefweb_api":
                q = c_en
                sources.append(S("un_%s_%s" % (key, "chad" if country == "乍得" else "niger"),
                                  name + ("（乍得）" if country == "乍得" else "（尼日尔）"),
                                  country, "https://reliefweb.int/country/%s" % ("tcd" if country == "乍得" else "ner"),
                                  "英语", "un_humanitarian", "un_humanitarian", "reliefweb_api",
                                  query=q, notes="联合国人道，API 可用"))
            else:
                q = "%s %s" % ("domain:%s" % ({"unhcr": "unhcr.org", "iom": "iom.int", "wfp": "wfp.org",
                       "unicef": "unicef.org", "icrc": "icrc.org", "msf": "msf.org", "fewsnet": "fews.net",
                       "unnews": "news.un.org", "au": "au.int", "crisisgroup": "crisisgroup.org", "iss": "issafrica.org",
                       "acled": "acleddata.com"}[key]), c_en)
                sources.append(S("un_%s_%s" % (key, "chad" if country == "乍得" else "niger"),
                                  name + ("（乍得）" if country == "乍得" else "（尼日尔）"),
                                  country, "https://www.%s" % key,
                                  "英语", "un_humanitarian", "un_humanitarian",
                                  "gdelt_search" if not (key == "acled") else "gdelt_search",
                                  query=q, requires_api=(key == "acled"),
                                  tested=(key != "acled"),
                                  notes=("需API，未伪造接入" if key == "acled" else "联合国/人道/专业来源")))

    # ===================== 中国相关 =====================
    china_list = [
        ("mfa", "中国外交部", "mfa.gov.cn", "domain:mfa.gov.cn"),
        ("emb_chad", "中国驻乍得使馆", "td.china-embassy.gov.cn", "domain:td.china-embassy.gov.cn"),
        ("emb_niger", "中国驻尼日尔使馆", "ne.china-embassy.gov.cn", "domain:ne.china-embassy.gov.cn"),
        ("chinanews", "中国新闻网", "chinanews.com.cn", "domain:chinanews.com.cn"),
        ("cctv", "央视新闻", "cctv.com", "domain:cctv.com"),
        ("cgtn", "CGTN Africa", "cgtn.com", "domain:cgtn.com"),
        ("people", "人民网", "people.com.cn", "domain:people.com.cn"),
        ("chinadaily", "中国日报", "chinadaily.com.cn", "domain:chinadaily.com.cn"),
    ]
    for country, c_cn in (("乍得", "乍得"), ("尼日尔", "尼日尔")):
        for key, name, dom, query_dom in china_list:
            q = "%s %s" % (query_dom, c_cn)
            sources.append(S("cn_%s_%s" % (key, "chad" if country == "乍得" else "niger"),
                              name + ("（乍得）" if country == "乍得" else "（尼日尔）"),
                              country, "https://www.%s" % dom,
                              "中文", "china_official" if key in ("mfa", "emb_chad", "emb_niger") else "china_media",
                              "china_official" if key in ("mfa", "emb_chad", "emb_niger") else "china_media",
                              "gdelt_search", query=q, notes="中国相关来源"))

    # 启用策略：
    # - 本地 RSS / ReliefWeb 全部启用；
    # - gdelt_search 全部启用（采集器已实现「同国同关键词合并为一次 OR 查询」，
    #   增加域名不增加 API 调用次数，可最大化覆盖 Reuters/Xinhua/AP/AFP/BBC/… ）；
    # - 仅 ACLED（需 API Key，未伪造接入）保持关闭。
    for s in sources:
        if s.get("requires_api"):
            s["enabled"] = False
        else:
            s["enabled"] = True
        s["status"] = "active" if (s["enabled"] and s["tested"]) else ("paused" if not s["enabled"] else s["status"])
    return sources


if __name__ == "__main__":
    sources = build()
    out = {"sources": sources, "updated_at": ""}
    json.dump(out, open(os.path.join(DATA, "sources.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    from collections import Counter
    print("总来源数：", len(sources))
    print("按国家：", dict(Counter(s["country"] for s in sources)))
    print("按方法：", dict(Counter(s["collection_method"] for s in sources)))
