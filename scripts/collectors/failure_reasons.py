#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""failure_reasons.py —— C1B §七：逐源失败原因分类（不得一律叫 BLOCKED）。

背景：
  C1A 的 Source Yield 报告里 E 档（无产出/被阻断）有 77 个源，占比 76%。但"无产出"
  不是一种原因，而是十几种原因的混合物：HTTP 429 / 403 / 404 / DNS / 超时 / robots
  拒绝 / RSS 空 / RSS 解析失败 / HTML 解析失败 / 查询无结果 / 源映射错误 /
  确实没有近期内容 / 只有重复内容。混为一谈会导致修复方向完全错误
  （例如把"该源本来就没有近期内容"当成"被封锁"去绕限制）。

本模块把采集过程中已有的确定性证据（错误串、发现计数、抓取计数、去重计数、
解析计数）映射为一个**具体**原因码。纯规则、无 LLM、无猜测：证据不足时输出 UNKNOWN，
绝不臆断为 BLOCKED。
"""
import re

# ── 原因码（规范 §七 固定词表）──────────────────────────
OK_PRODUCTIVE = "OK_PRODUCTIVE"
HTTP_429 = "HTTP_429"
HTTP_403 = "HTTP_403"
HTTP_404 = "HTTP_404"
DNS = "DNS"
TIMEOUT = "TIMEOUT"
ROBOTS_OR_ACCESS = "ROBOTS_OR_ACCESS"
RSS_EMPTY = "RSS_EMPTY"
RSS_PARSE_FAILURE = "RSS_PARSE_FAILURE"
HTML_PARSE_FAILURE = "HTML_PARSE_FAILURE"
QUERY_NO_RESULT = "QUERY_NO_RESULT"
SOURCE_MAPPING_ERROR = "SOURCE_MAPPING_ERROR"
NO_RECENT_CONTENT = "NO_RECENT_CONTENT"
DUPLICATE_ONLY = "DUPLICATE_ONLY"
UNKNOWN = "UNKNOWN"

#: 规范要求的完整词表（顺序即判定优先级）
REASON_CODES = [
    HTTP_429, HTTP_403, HTTP_404, DNS, TIMEOUT, ROBOTS_OR_ACCESS,
    RSS_EMPTY, RSS_PARSE_FAILURE, HTML_PARSE_FAILURE, QUERY_NO_RESULT,
    SOURCE_MAPPING_ERROR, NO_RECENT_CONTENT, DUPLICATE_ONLY, UNKNOWN,
]

_RULES = [
    (HTTP_429, re.compile(r"\b429\b|RATE_LIMIT|Too Many Requests", re.I)),
    (HTTP_403, re.compile(r"\b403\b|Forbidden", re.I)),
    (HTTP_404, re.compile(r"\b404\b|Not Found", re.I)),
    (DNS, re.compile(r"Name or service not known|nodename nor servname|"
                     r"getaddrinfo|DNS|NameResolution|gaierror|"
                     r"Temporary failure in name resolution", re.I)),
    (TIMEOUT, re.compile(r"timed out|timeout|TimeoutError|ReadTimeout|"
                         r"ConnectTimeout|ETIMEDOUT", re.I)),
    (ROBOTS_OR_ACCESS, re.compile(r"robots|disallow|access denied|blocked by|"
                                  r"captcha|cloudflare|just a moment|"
                                  r"interstit|intercepted", re.I)),
    (RSS_PARSE_FAILURE, re.compile(r"rss parse|feed parse|saxparse|"
                                   r"not well-formed|mismatched tag|"
                                   r"xml\.etree|XMLSyntaxError|"
                                   r"feedparser.*(error|fail)", re.I)),
    (HTML_PARSE_FAILURE, re.compile(r"html parse|no <article>|selector|"
                                    r"lxml|BeautifulSoup.*(error|fail)", re.I)),
    (SOURCE_MAPPING_ERROR, re.compile(r"no feed_url|missing feed|"
                                      r"未含 domain|缺少 query|no query|"
                                      r"missing url|未配置|mapping", re.I)),
    (RSS_EMPTY, re.compile(r"empty feed|feed empty|0 entries|no entries", re.I)),
    (QUERY_NO_RESULT, re.compile(r"no result|zero result|0 records|"
                                 r"articles.*empty|query returned 0", re.I)),
]


def classify_source_failure(stat, dis_errors=None, mapping_error=False):
    """返回 (reason_code, evidence_list)。

    stat 为采集器逐源统计（含 status/discovered/fetched/duplicates/errors/...）。
    dis_errors 为发现阶段错误串列表（真实证据，不得为空时臆断）。
    """
    dis_errors = [str(e) for e in (dis_errors or [])]
    blob = " | ".join(dis_errors + [str(stat.get("error") or "")])
    evidence = []

    if mapping_error:
        return SOURCE_MAPPING_ERROR, ["source registry entry lacks discovery config"]

    # 1) 有产出 → 直接判定 OK（产物优先于错误串：部分来源 429 后仍拿到旧缓存内容）
    if stat.get("discovered", 0) > 0 and stat.get("fetched", 0) > 0:
        return OK_PRODUCTIVE, ["discovered=%d fetched=%d"
                               % (stat.get("discovered", 0), stat.get("fetched", 0))]

    # 2) 明确错误串 → 具体原因
    for code, rx in _RULES:
        m = rx.search(blob)
        if m:
            evidence.append("error matched %r" % m.group(0)[:60])
            return code, evidence

    # 3) 有发现但全部被去重吞掉
    if stat.get("discovered", 0) > 0 and stat.get("duplicates", 0) >= stat.get("discovered", 0):
        return DUPLICATE_ONLY, ["discovered=%d duplicates=%d"
                                % (stat.get("discovered", 0), stat.get("duplicates", 0))]

    # 4) 发现为 0 且无错误串：区分「查询无结果」与「确实没有近期内容」
    if stat.get("discovered", 0) == 0 and not dis_errors:
        method = (stat.get("method") or "").lower()
        if method in ("gdelt_search", "search_discovery"):
            return QUERY_NO_RESULT, ["method=%s discovered=0, no transport error" % method]
        if method in ("rss", "atom", "reliefweb_api_or_feed"):
            return RSS_EMPTY, ["method=%s discovered=0, no transport error" % method]
        if method == "html_listing":
            return NO_RECENT_CONTENT, ["method=html_listing discovered=0, no transport error"]

    # 5) 有抓取但正文全部提取失败
    if stat.get("fetched", 0) > 0 and stat.get("full_body", 0) == 0 \
            and stat.get("partial_body", 0) == 0 and stat.get("summary_only", 0) == 0:
        return HTML_PARSE_FAILURE, ["fetched=%d but no body extracted" % stat.get("fetched", 0)]

    # 6) 证据不足：如实标记 UNKNOWN（不得臆断为 BLOCKED）
    evidence.append("insufficient evidence: status=%s errors=%d"
                    % (stat.get("status"), stat.get("errors", 0)))
    return UNKNOWN, evidence


def summarize(rows):
    """按原因码汇总计数（供 Source Yield Report V2 使用）。"""
    out = {}
    for r in rows:
        c = r.get("failure_reason") or UNKNOWN
        out[c] = out.get(c, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def is_blocked(reason):
    """真正属于「被外部阻断」的原因（用于区分 blocked vs no-output）。"""
    return reason in (HTTP_429, HTTP_403, HTTP_404, DNS, TIMEOUT, ROBOTS_OR_ACCESS)
