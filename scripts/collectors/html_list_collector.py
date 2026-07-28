#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""html_list_collector.py —— 新闻栏目/首页列表页采集（提取文章链接与标题）。"""
import re
from base import BaseCollector, extract_links, fetch_text, strip_tags

_SKIP = ("/tag/", "/author/", "/category/", "/feed", "/wp-content",
         "/page/", "/wp-json", "/xmlrpc", "/comments", "?share=", "/cdn-cgi/")


class HTMLListCollector(BaseCollector):
    def run(self):
        urls = self.source.get("category_urls") or [self.source.get("url")]
        out = []
        seen = set()
        for u in urls:
            if not u:
                continue
            text = self.fetch(u)
            if not text:
                continue
            for link, txt in extract_links(text, u):
                if len(txt) < 8:
                    continue
                low = link.lower()
                if any(x in low for x in _SKIP):
                    continue
                if link in seen:
                    continue
                seen.add(link)
                out.append(self.article(txt, link, "", ""))
        return out

    @staticmethod
    def fetch_detail_title(url):
        """补全 sitemap 发现的 URL 的标题（仅取 <title>）。"""
        text = fetch_text(url)
        if not text:
            return ""
        m = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
        if m:
            return strip_tags(m.group(1))
        return ""
