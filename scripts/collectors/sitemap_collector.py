#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sitemap_collector.py —— XML Sitemap 采集（发现 URL，标题由 collect.py 补全）。"""
import re
from base import BaseCollector


class SitemapCollector(BaseCollector):
    def run(self):
        base = (self.source.get("url") or "").rstrip("/")
        if not base:
            return []
        candidates = []
        if self.source.get("feed_url"):
            candidates.append(self.source["feed_url"])
        candidates += [base + "/sitemap.xml", base + "/sitemap_index.xml",
                       base + "/wp-sitemap.xml"]
        seen = set()
        out = []
        for sm in candidates:
            text = self.fetch(sm)
            if not text:
                continue
            locs = re.findall(r"<loc>(.*?)</loc>", text, re.S)
            subs = [l for l in locs if "sitemap" in l.lower()][:6]
            posts = [l for l in locs if "sitemap" not in l.lower()]
            for l in posts:
                if l not in seen:
                    seen.add(l)
                    out.append(self.article("", l, "", ""))
            for s in subs:
                t2 = self.fetch(s)
                if not t2:
                    continue
                for l in re.findall(r"<loc>(.*?)</loc>", t2, re.S):
                    if l not in seen and "sitemap" not in l.lower():
                        seen.add(l)
                        out.append(self.article("", l, "", ""))
            if out:
                break
        return out
