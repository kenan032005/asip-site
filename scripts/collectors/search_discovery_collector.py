#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""search_discovery_collector.py —— 基于 GDELT 公开 API 的补充发现（合规、无需密钥）。"""
import json
import urllib.parse
from base import BaseCollector, normalize_time
from gdelt_rate_limiter import fetch_gdelt, build_gdelt_url

LANG_MAP = {
    "English": "英语", "French": "法语", "German": "德语", "Spanish": "西班牙语",
    "Italian": "意大利语", "Portuguese": "葡萄牙文", "Turkish": "土耳其语",
    "Arabic": "阿拉伯文", "Russian": "俄文", "Chinese": "中文",
}


class SearchDiscoveryCollector(BaseCollector):
    def run(self):
        country_en = (self.country_cfg or {}).get("country_en") or \
            self.source.get("country_en")
        if not country_en:
            return []
        # 支持来源自定义查询（如中文来源：中国/中国公民/中国企业）
        override = self.source.get("query")
        if override:
            query = override
        else:
            query = ('%s (attack OR killed OR clash OR conflict OR bombing OR '
                     'kidnapping OR protest OR insurgent OR "terror" OR sécurité '
                     'OR insécurité OR enlèvement)' % country_en)
        # C1B §九：该查询同样走 GDELT_SHARED_RATE_LIMITER —— 与 gdelt_search
        # 源共享同一份全局节流/缓存/配额，绝不各自并发访问同一公共服务。
        url = build_gdelt_url(query, timespan="72h", maxrecords=25)
        text, err, meta = fetch_gdelt(url, label="search_discovery|%s" % (country_en or ""))
        if not text:
            self.errors.append("GDELT_RATE_LIMITED" if meta.get("rate_limited")
                               else "gdelt fetch: %s" % err)
            return []
        try:
            d = json.loads(text)
        except Exception as e:
            self.errors.append("gdelt json: %s" % e)
            return []
        out = []
        for art in d.get("articles", []):
            title = (art.get("title") or "").strip()
            link = (art.get("url") or "").strip()
            if not link or not title:
                continue
            pub = normalize_time(art.get("seendate") or art.get("date"))
            lang = LANG_MAP.get((art.get("language") or "").strip(),
                                (art.get("language") or "英语").strip())
            out.append(self.article(title, link, "", pub, lang))
        return out
