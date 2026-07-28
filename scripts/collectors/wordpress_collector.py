#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wordpress_collector.py —— WordPress 站点采集（优先 wp-json，回退 /feed/）。"""
import json
from base import BaseCollector, parse_feed, normalize_time


class WordPressCollector(BaseCollector):
    def run(self):
        base = (self.source.get("url") or "").rstrip("/")
        if not base:
            return []
        # 1) 优先 wp-json REST API
        api = base + "/wp-json/wp/v2/posts?_embed&per_page=20"
        text = self.fetch(api)
        if text:
            try:
                posts = json.loads(text)
                out = []
                for p in posts:
                    title = p.get("title", {}).get("rendered", "")
                    link = p.get("link", "")
                    excerpt = p.get("excerpt", {}).get("rendered", "")
                    date = p.get("date_gmt") or p.get("date", "")
                    if link:
                        out.append(self.article(title, link, excerpt, normalize_time(date)))
                if out:
                    return out
            except Exception as e:
                self.errors.append("wp-json 解析失败: %s" % e)
        # 2) 回退 RSS feed
        text2 = self.fetch(base + "/feed/")
        if text2:
            return [self.article(a["title"], a["url"], a["summary"], a["published"])
                    for a in parse_feed(text2) if a["url"]]
        return []
