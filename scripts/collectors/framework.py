#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
framework.py — Stage 3 第二执行包统一采集框架。

组件：
  SourceRegistry       来源注册表（读取 data/sources.json，兼容扩展）
  ArticleDiscoverer    文章发现器（RSS/Atom + HTML栏目页）
  ArticleFetcher       详情页抓取（URL安全校验 + 超时重试）
  ContentExtractor     正文提取（通用密度 + 来源选择器 + 清洗 + 质量评分）
  Normalizer           字段标准化（时间→北京时间等）
  CountryScopeClassifier 国家分类（复用 country_runner）
  RelevanceFilter      相关性筛选（复用 country_runner）
  Deduplicator         URL/内容哈希去重
  PublishGate          发布准入

设计原则：
- 全部零依赖（仅标准库）
- 请求礼貌（UA/超时/重试/限速）
- URL 安全（拒绝 localhost/内网/SSRF）
- 正文质量确定性评分（不依赖 AI）
- 缓存与增量（seen_urls / etag / last_modified）
"""
import os
import re
import json
import time
import html
import hashlib
import socket
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys_add = __import__("sys")
sys_add.path.insert(0, os.path.join(ROOT, "scripts"))
sys_add.path.insert(0, os.path.join(ROOT, "scripts", "collectors"))

# ── 常量 ─────────────────────────────────────────────
UA = ("Mozilla/5.0 (compatible; ASIP-Collector/2.0; "
      "+https://github.com/kenan032005/asip-site)")
HTTP_TIMEOUT = 15
MAX_RETRIES = 2
MIN_INTERVAL = 1.0
MAX_BODY_BYTES = 2 * 1024 * 1024  # 2MB 响应上限
CACHE_DIR = os.path.join(ROOT, "logs", "collector_cache")

# ── URL 安全校验 ─────────────────────────────────────
PRIVATE_IP_PATTERNS = [
    re.compile(r"^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$"),
    re.compile(r"^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$"),
    re.compile(r"^192\.168\.\d{1,3}\.\d{1,3}$"),
    re.compile(r"^172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}$"),
    re.compile(r"^169\.254\.\d{1,3}\.\d{1,3}$"),
    re.compile(r"^0\.0\.0\.0$"),
    re.compile(r"^::1$"),
    re.compile(r"^fe80:"),
    re.compile(r"^fc[0-9a-f]{2}:"),
    re.compile(r"^fd[0-9a-f]{2}:"),
]
METADATA_HOSTS = {"169.254.169.254", "metadata.google.internal",
                  "metadata", "100.100.100.200", "100.100.100.204"}
BLOCKED_SCHEMES = ("file:", "ftp:", "gopher:", "data:", "javascript:", "about:")
BLOCKED_HOSTS = {"localhost"}


def validate_url(url):
    """URL 安全检查。返回 (ok, reason)。拒绝 SSRF/内网/非法协议。"""
    if not url or not isinstance(url, str):
        return False, "empty_url"
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return False, f"scheme_not_http: {url[:30]}"
    for sch in BLOCKED_SCHEMES:
        if url.startswith(sch):
            return False, f"blocked_scheme: {sch}"
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False, "parse_failed"
    host = (parsed.hostname or "").lower()
    if not host:
        return False, "no_host"
    if host in BLOCKED_HOSTS or host in METADATA_HOSTS:
        return False, f"blocked_host: {host}"
    # 尝试解析 IP（IPv4 字面量直接匹配，域名解析后验证）
    if re.match(r"^[\d\.]+$", host):
        for pat in PRIVATE_IP_PATTERNS:
            if pat.match(host):
                return False, f"private_ip: {host}"
    else:
        try:
            infos = socket.getaddrinfo(host, None)
            for info in infos:
                ip = info[4][0]
                for pat in PRIVATE_IP_PATTERNS:
                    if pat.match(ip):
                        return False, f"private_ip_resolved: {ip} ({host})"
        except socket.gaierror:
            return False, f"dns_fail: {host}"
    return True, "ok"


# ── 网络抓取 ─────────────────────────────────────────
_last_hit = {}


def _rate_limit(url):
    host = urllib.parse.urlparse(url).netloc
    now = time.time()
    if host in _last_hit and now - _last_hit[host] < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - (now - _last_hit[host]))
    _last_hit[host] = time.time()


def fetch_page(url, timeout=HTTP_TIMEOUT):
    """抓取页面文本。返回 (text_or_None, error_or_None, http_status_or_None)。"""
    ok, reason = validate_url(url)
    if not ok:
        return None, reason, None
    _rate_limit(url)
    last_err = None
    last_status = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read(MAX_BODY_BYTES + 1)
                if len(raw) > MAX_BODY_BYTES:
                    return None, "response_too_large", r.status
                enc = r.headers.get_content_charset() or "utf-8"
                try:
                    return raw.decode(enc, "ignore"), None, r.status
                except LookupError:
                    return raw.decode("utf-8", "ignore"), None, r.status
        except urllib.error.HTTPError as e:
            last_err = e
            last_status = e.code
            if e.code in (429, 503) and attempt < MAX_RETRIES:
                time.sleep(5 * (attempt + 1))
                continue
            if attempt < MAX_RETRIES:
                time.sleep(2 * (attempt + 1))
                continue
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(2 * (attempt + 1))
                continue
    return None, (str(last_err)[:100] if last_err else "unknown"), last_status


# ── 时间工具 ─────────────────────────────────────────
def bj_now():
    return datetime.now(timezone.utc) + timedelta(hours=8)


def bj_iso():
    return bj_now().strftime("%Y-%m-%dT%H:%M:%S+08:00")


def parse_original_time(s):
    """解析原文时间，返回 (datetime_utc_or_None, tz_label_or_None)。"""
    if not s:
        return None, None
    s = s.strip()
    # RFC 822 / ISO 常见格式
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                "%d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo:
                return dt.astimezone(timezone.utc), str(dt.tzinfo)
            return dt.replace(tzinfo=timezone.utc), None
        except ValueError:
            continue
    # ISO8601 with offset
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo:
            return dt.astimezone(timezone.utc), str(dt.tzinfo)
        return dt.replace(tzinfo=timezone.utc), None
    except ValueError:
        pass
    # 仅日期
    try:
        dt = datetime.strptime(s[:10], "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc), None
    except ValueError:
        pass
    return None, None


def to_beijing(dt_utc):
    if not dt_utc:
        return ""
    return (dt_utc + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")


# ── HTML 工具 ────────────────────────────────────────
def strip_tags(s):
    if not s:
        return ""
    s = re.sub(r"<script.*?</script>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(s).strip()


def extract_meta(html_text, names):
    """提取 meta 标签内容。names 为 name/property 列表。"""
    out = {}
    for n in names:
        # 支持 name/property 在前、content 在后；或 content 在前、name/property 在后
        m = re.search(
            r'<meta[^>]+(?:name|property)=["\']' + re.escape(n) +
            r'["\'][^>]*content=["\']([^"\']*)["\']',
            html_text, re.I)
        if not m:
            m = re.search(
                r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:name|property)=["\']'
                + re.escape(n) + r'["\']',
                html_text, re.I)
        if m:
            out[n] = html.unescape(m.group(1)).strip()
    return out


def extract_title(html_text):
    m = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.I | re.S)
    if m:
        t = strip_tags(m.group(1))
        # 去站点名后缀（常见 " - SiteName"）
        t = re.sub(r"\s+[-|–]\s+[^\-|–]{2,40}$", "", t).strip()
        return t
    return ""


def extract_jsonld(html_text):
    """提取 JSON-LD 中的 article 信息（尽力而为）。"""
    out = {}
    for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                         html_text, re.I | re.S):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            if data.get("@type") in ("NewsArticle", "Article", "ReportageNewsArticle"):
                out = data
                break
    return out


# ── 正文提取器 ───────────────────────────────────────
# 导航/无关区块特征（段落文本中出现即扣分）
NAV_MARKERS = [
    "navigation", "menu", "menu principal", "footer", "copyright",
    "tous droits réservés", "all rights reserved", "cookie", "cookies",
    "partager", "share", "facebook", "twitter", "whatsapp", "related",
    "articles similaires", "à lire aussi", "a lire aussi", "newsletter",
    "abonnez-vous", "subscribe", "commentaire", "comments", "votre avis",
    "contactez-nous", "contact us", "mentions légales", "mentions legales",
    "plan du site", "sitemap", "search", "rechercher",
]
INTERCEPT_MARKERS = [
    "access denied", "just a moment", "attention required", "checking your browser",
    "enable javascript and cookies", "verify you are human", "cf-chl",
    "your connection is not private", "error 403 forbidden", "error 404 not found",
    "cloudflare ray id", "please turn javascript on",
]
TITLE_MARKERS = ["首页", "accueil", "home", "direct", "en direct", "live",
                 "facebook", "twitter", "youtube", "vidéos", "videos"]


class ContentExtractor:
    """正文提取：来源专用选择器 → 通用密度 → 失败标记。"""

    def __init__(self, profile=None):
        self.profile = profile or {}

    def extract(self, html_text, source_url=""):
        """返回 dict: title/body/author/published/lead_image/quality/quality_reasons/method"""
        result = {
            "title": "", "body": "", "author": "", "published_original": "",
            "lead_image_url": "", "method": "none",
            "quality": "extraction_failed", "quality_score": 0,
            "quality_reasons": [], "word_count": 0, "canonical_url": "",
        }
        if not html_text:
            result["quality_reasons"].append("empty_html")
            return result

        # 拦截页识别
        low = html_text.lower()
        for mk in INTERCEPT_MARKERS:
            if mk in low:
                result["quality"] = "intercepted"
                result["quality_reasons"].append(f"intercept_marker:{mk}")
                return result

        # meta / JSON-LD
        meta = extract_meta(html_text, [
            "og:title", "og:description", "og:image", "article:published_time",
            "article:author", "author", "canonical", "twitter:title"])
        jl = extract_jsonld(html_text)
        result["title"] = (meta.get("og:title") or jl.get("headline") or
                           extract_title(html_text) or "").strip()
        result["lead_image_url"] = (meta.get("og:image")
                                    or (jl.get("image", "") if isinstance(jl.get("image"), str) else ""))
        result["published_original"] = (meta.get("article:published_time") or
                                        jl.get("datePublished") or "").strip()
        if isinstance(jl.get("author"), dict):
            result["author"] = jl.get("author", {}).get("name", "")
        elif isinstance(jl.get("author"), list):
            result["author"] = ", ".join(a.get("name", "") for a in jl.get("author", []) if isinstance(a, dict))
        else:
            result["author"] = meta.get("article:author") or meta.get("author") or ""
        cm = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html_text, re.I)
        if cm:
            result["canonical_url"] = cm.group(1)

        # 1) 来源专用选择器
        body = self._extract_with_selectors(html_text)
        if body:
            result["body"] = body
            result["method"] = "source_selectors"
        else:
            # 2) 通用密度提取
            body = self._extract_generic(html_text)
            if body:
                result["body"] = body
                result["method"] = "generic_density"

        self._score(result, source_url)
        return result

    def _extract_with_selectors(self, html_text):
        """使用来源配置的 CSS-like 选择器（简化实现：按 id/class/标签）。"""
        selectors = self.profile.get("selectors") or {}
        body_sel = selectors.get("body_selector")
        if not body_sel:
            return ""
        sel = body_sel.lstrip(".#")
        if body_sel.startswith("."):
            pat = r'<[a-z0-9]+[^>]*class=["\'][^"\']*' + re.escape(sel) + r'[^"\']*["\'][^>]*>(.*?)</[a-z0-9]+>'
        elif body_sel.startswith("#"):
            pat = r'<[a-z0-9]+[^>]*id=["\']' + re.escape(sel) + r'["\'][^>]*>(.*?)</[a-z0-9]+>'
        else:
            pat = r'<(' + re.escape(sel) + r')[^>]*>(.*?)</\1>'
        m = re.search(pat, html_text, re.I | re.S)
        if m:
            return strip_tags(m.group(1) if len(m.groups()) == 1 else m.group(2))
        return ""

    def _extract_generic(self, html_text):
        """通用密度提取：找最长的文本密集 <article> 或 <div> 或 <p> 序列。"""
        # 优先 <article>
        arts = re.findall(r"<article[^>]*>(.*?)</article>", html_text, re.I | re.S)
        if arts:
            best = max(arts, key=lambda a: len(strip_tags(a)))
            body = strip_tags(best)
            if len(body) > 200:
                return body
        # 其次最长 <div>
        divs = re.findall(r"<div[^>]*>(.*?)</div>", html_text, re.I | re.S)
        best_div = max(divs, key=lambda d: len(strip_tags(d))) if divs else ""
        body = strip_tags(best_div)
        if len(body) > 200:
            return body
        # 最后收集全部 <p>
        ps = re.findall(r"<p[^>]*>(.*?)</p>", html_text, re.I | re.S)
        body = strip_tags(" ".join(ps))
        if len(body) > 100:
            return body
        return ""

    def _score(self, result, source_url):
        """正文质量评分（规则确定性）。"""
        body = result["body"]
        reasons = []
        score = 0
        wc = len(body.split())
        result["word_count"] = wc

        if not body:
            reasons.append("no_body")
        else:
            if wc >= 300:
                score += 40
            elif wc >= 150:
                score += 30
            elif wc >= 50:
                score += 15
            else:
                reasons.append("body_too_short")
            # 段落数
            paras = [p for p in body.split("\n") if len(p.strip()) > 30]
            if len(paras) >= 3:
                score += 20
            elif len(paras) >= 1:
                score += 10
            else:
                reasons.append("no_paragraphs")
            # 导航词比例
            low = body.lower()
            nav_hits = sum(1 for mk in NAV_MARKERS if mk in low)
            if nav_hits <= 1:
                score += 15
            else:
                score -= min(15, nav_hits * 3)
                reasons.append(f"nav_markers:{nav_hits}")
            # 标题重复
            if result["title"] and body.count(result["title"][:30]) > 2:
                score -= 10
                reasons.append("title_repeated")
            # 链接密度（无关链接）
            link_count = len(re.findall(r"http", body))
            if link_count > 20:
                score -= 5
                reasons.append("too_many_links")

        # 标题
        if not result["title"] or len(result["title"]) < 5:
            reasons.append("title_missing_or_short")
        else:
            score += 10

        # 拦截内容
        for mk in INTERCEPT_MARKERS:
            if mk in (body + result["title"]).lower():
                result["quality"] = "intercepted"
                reasons.append(f"intercept:{mk}")
                break

        result["quality_score"] = max(0, min(100, score))
        result["quality_reasons"] = reasons[:6]

        # 质量等级
        if result["quality"] == "intercepted":
            pass
        elif not body:
            result["quality"] = "extraction_failed"
        elif wc >= 150 and score >= 60:
            result["quality"] = "full_body"
        elif wc >= 50 and score >= 30:
            result["quality"] = "partial_body"
        elif wc >= 20:
            result["quality"] = "rss_summary_only"
        else:
            result["quality"] = "title_only"

        # 页面类型识别（首页/列表被误抓）
        title_low = (result["title"] or "").lower()
        if any(tm in title_low for tm in TITLE_MARKERS) and wc < 50:
            result["quality"] = "intercepted"
            reasons.append("looks_like_listing_or_home")


# ── 缓存 ─────────────────────────────────────────────
def cache_path(source_id):
    return os.path.join(CACHE_DIR, f"{source_id}.json")


def load_cache(source_id):
    p = cache_path(source_id)
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"seen_urls": [], "seen_hashes": [], "etag": "", "last_modified": ""}


def save_cache(source_id, cache):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_path(source_id), "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# ── 去重 ─────────────────────────────────────────────
def norm_url(url):
    if not url:
        return ""
    u = url.strip().rstrip("/")
    if "#" in u:
        u = u[:u.index("#")]
    # 去追踪参数（utm_ 前缀 + 常见追踪参数精确匹配）
    parsed = urllib.parse.urlparse(u)
    qs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    qs = [(k, v) for k, v in qs
          if not (k.startswith("utm_") or k in ("fbclid", "gclid", "ref", "source", "spm"))]
    u = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(qs)))
    return u.lower()


def content_hash(title, body=""):
    text = ((title or "") + " " + (body or "")).strip().lower()
    text = re.sub(r"\s+", " ", text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ── 标准化输出 Article ───────────────────────────────
def make_article(source, discovered, fetched, extracted, run_id):
    """组装统一 Article 对象。"""
    published_dt, tz_label = parse_original_time(extracted.get("published_original") or
                                                 discovered.get("published", ""))
    return {
        "source_id": source.get("source_id", ""),
        "source_name": source.get("source_name", ""),
        "source_country": source.get("source_country", ""),
        "source_type": source.get("source_type", ""),
        "language": discovered.get("language") or source.get("language", "fr"),
        "discovery_method": discovered.get("method", ""),
        "feed_url": discovered.get("feed_url", ""),
        "listing_url": discovered.get("listing_url", ""),
        "article_url": discovered.get("url", ""),
        "canonical_url": extracted.get("canonical_url", "") or discovered.get("url", ""),
        "original_title": discovered.get("title", "") or extracted.get("title", ""),
        "original_body": extracted.get("body", ""),
        "original_summary": discovered.get("summary", ""),
        "author": extracted.get("author", ""),
        "published_at_original": extracted.get("published_original") or discovered.get("published", ""),
        "published_timezone": tz_label or "",
        "published_at_beijing": to_beijing(published_dt) if published_dt else "",
        "lead_image_url": extracted.get("lead_image_url", ""),
        "article_word_count": extracted.get("word_count", 0),
        "extraction_method": extracted.get("method", ""),
        "extraction_quality": extracted.get("quality", "extraction_failed"),
        "extraction_quality_score": extracted.get("quality_score", 0),
        "extraction_quality_reasons": extracted.get("quality_reasons", []),
        "fetch_status": fetched.get("status", ""),
        "fetch_http_status": fetched.get("http_status"),
        "fetch_attempts": fetched.get("attempts", 0),
        "body_status": "full" if extracted.get("quality") == "full_body" else (
            "partial" if extracted.get("quality") in ("partial_body", "rss_summary_only") else (
                "failed" if not extracted.get("body") else "degraded")),
        "collected_at_beijing": bj_iso(),
        "run_id": run_id,
        "collector_version": "2.0.0",
    }
