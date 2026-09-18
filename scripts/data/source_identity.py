#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""source_identity.py —— C1B §十六：确定性 Source Identity。

问题（C1B §十三 审计发现）：
  生产 sources.json 里 101 个「启用来源」并不等于 101 个独立媒体：
    * 70 条 GDELT 记录只覆盖 **36 个域名**——每条域名都按国家登记了两遍
      （reuters.com → intl_reuters_chad + intl_reuters_niger；news.cn → xinhua_chad + xinhua_niger；…）；
    * 31 条 RSS 记录里有 4 组「同一 feed_url 登记两次」
      （Al Jazeera / RFI Afrique / BBC Afrique / France24 Afrique 各一份 chad + 一份 niger）；
    * 聚合/转载平台（AllAfrica、ReliefWeb）会把同一篇通讯社稿再分发一遍。
  如果拿「source 记录数」当独立来源数，就会把同一家媒体数成 2 家，
  甚至把同一篇稿件的转载数成「多来源印证」——这正好是 §十五明令禁止的。

本模块给出**确定性**（无 LLM、无网络）的来源身份：
    source_identity_id  = "SI_" + sha1(identity_key)[:12]
    identity_key 分层：
      1) syndication origin（聚合器/转载平台 → 追溯 original publisher）
      2) publisher domain（www 去掉、大小写与端口归一）
      3) 显式 source_group（无 URL 时的最后兜底）
  并附带 independence_class：
      independent_publisher / syndicated_copy / aggregator / unknown

国家后缀（_chad/_niger）、语言/地区前缀（intl_/chad_/niger_）一律**不进入**
身份键，因此同一家媒体的多国登记会收敛为同一个身份。
"""
import hashlib
import re
import urllib.parse

#: 聚合 / 转载 / 分发平台：其域名不得作为独立事实源，必须追溯到原始出版方
AGGREGATOR_DOMAINS = {
    "allafrica.com", "allafrica.net",
    "reliefweb.int",
    "news.google.com",
    "feedproxy.google.com",
    "yahoo.com", "news.yahoo.com",
    "msn.com",
    "flipboard.com",
    "smartnews.com",
    "newsnow.co.uk",
    "bing.com",
}

#: 已知通讯社/首发媒体域名 → 规范化 publisher key
#: （用于把「同一稿件被多个站点转载」收敛为同一个身份）
WIRE_DOMAINS = {
    "reuters.com": "reuters",
    "apnews.com": "ap",
    "afp.com": "afp",
    "news.cn": "xinhua",
    "xinhuanet.com": "xinhua",
    "china.org.cn": "chinaorg",
}

#: 从 URL 路径里可识别的原始出版方（聚合页常见 /publisher/... 或 ?source=）
_ORIGIN_FROM_QUERY = ("source", "publisher", "origin", "via")

#: 国家/语言/区域前后缀（不参与身份键）
_LOCALE_TOKENS = {
    "intl", "chad", "niger", "nigeria", "sudan", "southsudan", "ssd", "tcd",
    "benin", "ethiopia", "mozambique", "libya", "kenya", "sahel", "afrique",
    "africa", "fr", "en", "ar", "zh",
}
_PREFIX_RX = re.compile(r"^(?:%s)_" % "|".join(sorted(_LOCALE_TOKENS)))
_SUFFIX_RX = re.compile(r"_(?:%s)$" % "|".join(sorted(_LOCALE_TOKENS)))


def domain_of(url):
    """URL → 规范化域名（小写、去 www.、去端口）。"""
    if not url:
        return ""
    u = str(url).strip()
    if not u:
        return ""
    if "://" not in u:
        u = "https://" + u
    try:
        host = urllib.parse.urlsplit(u).netloc.lower()
    except Exception:
        return ""
    host = host.split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("m."):
        host = host[2:]
    return host


def publisher_slug(*candidates):
    """从 source_id / source_name / source_group 提取 publisher slug（确定性）。

    只做小写、去括号、去空格、剥国家与语言前后缀；不做任何模糊匹配。
    """
    for c in candidates:
        if not c:
            continue
        s = str(c).strip().lower()
        if not s:
            continue
        s = re.sub(r"[（(].*?[)）]", "", s)
        s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
        prev = None
        while prev != s:                      # 反复剥前缀（intl_rfi_afrique_chad）
            prev = s
            s = _PREFIX_RX.sub("", s)
            s = _SUFFIX_RX.sub("", s)
            s = s.strip("_")
        if s:
            return s
    return ""


def origin_publisher(record):
    """聚合/转载记录的原始出版方（无则返回空串）。

    只读取**已存在的结构化字段**（origin_publisher / original_publisher /
    original_url 的域名 / URL query 里的 source 参数），不做语义猜测。
    """
    for k in ("origin_publisher", "original_publisher", "syndication_origin"):
        v = record.get(k)
        if v and str(v).strip():
            return publisher_slug(v)
    for k in ("original_url", "origin_url"):
        v = record.get(k)
        if v:
            d = domain_of(v)
            if d:
                return publisher_slug(d, d.split(".")[0])
    try:
        q = dict(urllib.parse.parse_qsl(
            urllib.parse.urlsplit(str(record.get("article_url")
                                       or record.get("canonical_url") or "")).query))
        for k in _ORIGIN_FROM_QUERY:
            if q.get(k):
                return publisher_slug(q[k])
    except Exception:
        pass
    return ""


def source_identity(record):
    """返回 dict：
       {source_identity_id, identity_key, independence_class,
        publisher_key, domain, origin_publisher, reason}

    record 可为 source 记录（含 url/source_id/source_group/source_name）或
    article 记录（含 article_url/canonical_url/source_id/source_group）。
    """
    url = (record.get("article_url") or record.get("canonical_url")
           or record.get("feed_url") or record.get("url") or "")
    dom = domain_of(url)
    sg = record.get("source_group") or ""
    sid = record.get("source_id") or ""
    sname = record.get("source_name") or ""

    # 1) 聚合器：必须追溯到原始出版方，否则只能算 aggregator 身份（永不等于独立媒体）
    if dom and any(dom == a or dom.endswith("." + a) for a in AGGREGATOR_DOMAINS):
        op = origin_publisher(record)
        if op:
            key = "origin:" + op
            cls = "syndicated_copy"
            reason = "aggregator domain %s traced to origin publisher %s" % (dom, op)
        else:
            key = "aggregator:" + (dom or publisher_slug(sid, sg, sname))
            cls = "aggregator"
            reason = "aggregator domain %s without detectable origin publisher" % dom
        return _pack(key, cls, dom, op, reason, sname, sid, sg)

    # 2) 已知通讯社域名 → 规范化 wire 身份
    if dom in WIRE_DOMAINS:
        key = "wire:" + WIRE_DOMAINS[dom]
        return _pack(key, "independent_publisher", dom, "", "known wire domain", sname, sid, sg)

    # 3) 普通域名 → 域名即身份（国家/语言登记不再拆分身份）
    if dom:
        return _pack("pub:" + dom, "independent_publisher", dom, "",
                     "publisher domain", sname, sid, sg)

    # 4) 无 URL → 用 source_group / source_id 的 slug（剥掉国家前后缀）
    slug = publisher_slug(sg, sid, sname)
    if slug:
        return _pack("slug:" + slug, "unknown", "", "", "no url; slug fallback",
                     sname, sid, sg)
    return _pack("unknown:%s" % (sid or "?"), "unknown", "", "", "no identity evidence",
                 sname, sid, sg)


def _pack(key, cls, dom, origin, reason, sname, sid, sg):
    return {
        "source_identity_id": "SI_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12],
        "identity_key": key,
        "independence_class": cls,
        "publisher_key": key.split(":", 1)[-1],
        "domain": dom,
        "origin_publisher": origin,
        "source_name": sname,
        "source_id": sid,
        "source_group": sg or publisher_slug(sid, sname),
        "reason": reason,
    }


def independent_source_count(records):
    """独立来源计数（§十五/§十六）。

    规则：
      * 按 source_identity_id 去重 → 同一媒体多国登记只算 1；
      * syndicated_copy 归并到其 origin publisher（同一篇转载稿不算新增独立来源）；
      * aggregator（无法追溯原始出版方）**不计入**独立来源，但单独计数展示；
      * 绝不把转载/镜像域当成多个独立来源。
    """
    indep, syndicated, aggregators = {}, {}, {}
    for r in records:
        ident = source_identity(r)
        key = ident["identity_key"]
        if ident["independence_class"] == "aggregator":
            aggregators[key] = aggregators.get(key, 0) + 1
        elif ident["independence_class"] == "syndicated_copy":
            syndicated[key] = syndicated.get(key, 0) + 1
        else:
            indep[key] = indep.get(key, 0) + 1
    return {
        "independent_source_count": len(indep),
        "independent_identities": sorted(indep.keys()),
        "syndicated_identities": sorted(syndicated.keys()),
        "aggregator_identities": sorted(aggregators.keys()),
        "all_identity_count": len(set(list(indep) + list(syndicated) + list(aggregators))),
    }
