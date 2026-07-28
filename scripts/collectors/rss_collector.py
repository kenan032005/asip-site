#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rss_collector.py —— RSS 2.0 / Atom Feed 采集器（第一优先）。"""
from base import BaseCollector, parse_feed


class RSSCollector(BaseCollector):
    def run(self):
        feed = self.source.get("feed_url") or self.source.get("url")
        if not feed:
            return []
        text = self.fetch(feed)
        if not text:
            return []
        arts = parse_feed(text)
        return [self.article(a["title"], a["url"], a["summary"], a["published"])
                for a in arts if a["url"]]
