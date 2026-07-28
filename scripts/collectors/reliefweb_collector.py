#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reliefweb_collector.py —— ReliefWeb 公开 RSS（按主要国家筛选人道/局势信息）。

说明：ReliefWeb API v1 已于 2026 Q1 退役（410 Gone），v2 自 2025-11-01 起要求
预审批 appname（需人工申请）。因此改用官方公开 RSS 通道：
    https://reliefweb.int/updates/rss.xml?search=primary_country.exact:"Chad"
该通道公开、无需鉴权，返回最新 20 条更新，符合合规采集要求。
"""
import urllib.parse
from base import BaseCollector, parse_feed


class ReliefWebCollector(BaseCollector):
    def run(self):
        country_en = self.source.get("country_en") or (
            self.country_cfg or {}).get("country_en")
        if not country_en:
            self.errors.append("reliefweb: 缺少 country_en")
            return []
        q = urllib.parse.quote('primary_country.exact:"%s"' % country_en)
        url = "https://reliefweb.int/updates/rss.xml?search=" + q
        text = self.fetch(url)
        if not text:
            return []
        out = []
        for it in parse_feed(text):
            if not it.get("url") or not it.get("title"):
                continue
            a = self.article(it["title"], it["url"], it.get("summary", ""),
                             it.get("published", ""), "英语")
            a["source_name"] = "ReliefWeb"
            out.append(a)
        return out
