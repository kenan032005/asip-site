#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
identifiers.py —— ASIP Stage-2 统一 ID 生成规则

要求（规范第十一节）：
- article_id 稳定、可重复生成；优先依据 canonical_url；
- event_id 不使用简单递增编号作为唯一识别基础，基于稳定指纹；
- content_hash 基于 normalized_title + normalized_summary + canonical_url；
- 迁移重复运行两次 ID 完全一致；
- URL 跟踪参数 / 追踪参数被规范化；
- 同一 Reuters 转载不能产生多个 source_group（source_group 去重在 normalizers）。
"""

import hashlib
import re
import urllib.parse

# 需要从 URL 中剔除的追踪/营销参数
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "share", "spm",
    "wt.mc_id", "ref", "cmpid", "campaign", "source", "feature", "from",
}

# 仅做规范化、保留含义的参数白名单（不在此列、且非追踪参数的仍保留）
_KEEP_QUERY = True


def _sha16(s: str) -> str:
    """返回 SHA-256 前 16 位十六进制。"""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def normalize_url(url: str) -> str:
    """规范化 URL：剔除片段与追踪参数，域名小写，排序查询参数，去尾部斜杠。"""
    if not url:
        return ""
    u = str(url).strip()
    # 去掉 fragment
    if "#" in u:
        u = u.split("#", 1)[0]
    if not u:
        return ""
    try:
        parts = urllib.parse.urlsplit(u)
        host = parts.netloc.lower()
        # 去掉 www. 前缀以合并同域
        if host.startswith("www."):
            host = host[4:]
        # 解析并过滤查询参数
        qp = urllib.parse.parse_qsl(parts.query, keep_blank_values=False)
        kept = [(k, v) for k, v in qp if k.lower() not in _TRACKING_PARAMS]
        kept.sort(key=lambda kv: kv[0].lower())
        query = urllib.parse.urlencode(kept)
        path = parts.path or "/"
        # 去尾部斜杠（根路径保留）
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        # 重建（保留 scheme，缺省补 https）
        scheme = parts.scheme or "https"
        new = urllib.parse.urlunsplit((scheme, host, path, query, ""))
        return new
    except Exception:
        # 解析失败：退化为去除片段后的原串
        return u


def normalize_title(text: str) -> str:
    """标题归一化（用于哈希/指纹）：去首尾空白、折叠空白、转小写。"""
    if not text:
        return ""
    s = re.sub(r"\s+", " ", str(text).strip())
    return s.lower()


def normalize_location(text: str) -> str:
    """地点归一化（用于事件指纹）：去标点、折叠空白、转小写。"""
    if not text:
        return ""
    s = re.sub(r"[^\w\s一-鿿]", " ", str(text))
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def normalize_actor_action(text: str) -> str:
    """行动主体/核心动作归一化（用于事件指纹）。"""
    return normalize_location(text)


def article_id(canonical_url: str = "", source_id: str = "", published_at: str = "",
               title: str = "") -> str:
    """稳定生成 article_id。

    优先级：canonical_url > (source_id + published_at + normalized_title)。
    同一 Reuters 转载（同 canonical_url）必然产生同一 ID。
    """
    if canonical_url:
        return "ART_" + _sha16(normalize_url(canonical_url))
    base = "|".join([
        (source_id or "").strip().lower(),
        (published_at or "").strip(),
        normalize_title(title),
    ])
    return "ART_" + _sha16(base)


def content_hash(title: str = "", summary: str = "", canonical_url: str = "") -> str:
    """内容指纹：基于 normalized_title + normalized_summary + canonical_url。"""
    base = "\n".join([
        normalize_title(title),
        normalize_title(summary),
        normalize_url(canonical_url),
    ])
    return _sha16(base)


def event_id(country_code: str = "", location: str = "", event_type: str = "",
             event_date: str = "", actor_action: str = "") -> str:
    """稳定生成 event_id：基于国家 + 地点 + 类型 + 日期 + 行动指纹。"""
    base = "|".join([
        (country_code or "").strip().upper(),
        normalize_location(location),
        (event_type or "").strip().lower(),
        (event_date or "").strip(),
        normalize_actor_action(actor_action),
    ])
    return "EVT_" + _sha16(base)


def quarantine_id(original_object_type: str = "", original_id: str = "",
                   reason_code: str = "", detected_at: str = "") -> str:
    """稳定生成 quarantine_id。"""
    base = "|".join([
        (original_object_type or "").strip().lower(),
        (original_id or "").strip(),
        (reason_code or "").strip(),
        (detected_at or "").strip(),
    ])
    return "Q_" + _sha16(base)


def is_article_id(s: str) -> bool:
    return isinstance(s, str) and s.startswith("ART_") and len(s) == 20


def is_event_id(s: str) -> bool:
    return isinstance(s, str) and s.startswith("EVT_") and len(s) == 20


def is_quarantine_id(s: str) -> bool:
    return isinstance(s, str) and s.startswith("Q_") and len(s) == 20
