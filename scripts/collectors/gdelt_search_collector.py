#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gdelt_search_collector.py —— 通过 GDELT 公开 API 按「域名+国家查询」发现文章。

用于强制接入路透社(Reuters)、新华社/新华网(News.cn/Xinhuanet)、AP、AFP 等
大型通讯社：这些站点多有反爬/付费墙，直接抓取困难，但 GDELT 公开索引其文章
并暴露标题/链接/时间，属合法公开来源发现（不绕过任何限制、不复制全文）。
采集到的链接指向原始通讯社页面，来源标记 source_name=该通讯社。

来源配置字段（data/sources.json）：
  collection_method = "gdelt_search"
  query             = "domain:reuters.com (Chad OR N'Djamena OR ...)"   # 必填
  timespan          = "72h"  # 可选，默认 72h
  maxrecords        = 25     # 可选
"""
import json
import urllib.parse
from base import BaseCollector, normalize_time

LANG_MAP = {
    "English": "英语", "French": "法语", "German": "德语", "Spanish": "西班牙语",
    "Italian": "意大利语", "Portuguese": "葡萄牙文", "Turkish": "土耳其语",
    "Arabic": "阿拉伯文", "Russian": "俄文", "Chinese": "中文",
}


class GdeltSearchCollector(BaseCollector):
    def run(self):
        query = self.source.get("query") or self.source.get("gdelt_query")
        if not query:
            self.errors.append("gdelt_search: 缺少 query 字段")
            return []
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": self.source.get("maxrecords", "25"),
            "sort": "DateDesc",
            "timespan": self.source.get("timespan", "72h"),
        }
        url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(params)
        text = self.fetch(url)
        if not text:
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
