#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reliefweb_collector.py —— ReliefWeb 公开 API（按国家筛选人道/局势信息）。"""
import json
import urllib.parse
from base import BaseCollector, normalize_time


class ReliefWebCollector(BaseCollector):
    def run(self):
        country_en = self.source.get("country_en") or (
            self.country_cfg or {}).get("country_en")
        if not country_en:
            return []
        api = "https://api.reliefweb.int/v1/reports"
        params = {
            "appname": "asip-collector",
            "limit": "20",
            "sort[]": "date.created:desc",
            "query[value][]": "country:%s" % country_en,
        }
        url = api + "?" + urllib.parse.urlencode(params)
        text = self.fetch(url)
        if not text:
            return []
        try:
            d = json.loads(text)
        except Exception as e:
            self.errors.append("reliefweb json: %s" % e)
            return []
        out = []
        for it in d.get("data", []):
            f = it.get("fields", {})
            title = f.get("title", "")
            link = f.get("url", "")
            created = f.get("date", {}).get("created", "")
            src = ""
            s = f.get("source")
            if isinstance(s, list) and s:
                src = s[0].get("name", "") if isinstance(s[0], dict) else str(s[0])
            elif isinstance(s, dict):
                src = s.get("name", "")
            if link:
                a = self.article(title, link, "", normalize_time(created))
                a["source_name"] = src
                out.append(a)
        return out
