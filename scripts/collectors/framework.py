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
    # 块级结束标签 → 换行（保留段落结构，供按行清洗）
    s = re.sub(r"</(p|div|article|section|h[1-6]|li|tr|blockquote|ul|ol)>", "\n", s, flags=re.I)
    s = re.sub(r"<br[^>]*>", "\n", s, flags=re.I)
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
# 按钮/分页/分享类杂质（正文中出现即剥离或扣分；Stage 3B 清洗强化）
CLEANUP_MARKERS = [
    "lire la suite", "lire l'article", "lire l article", "lire plus",
    "read more", "read the full", "continue reading", "continue lendo",
    "voir plus", "voir la suite", "afficher plus", "afficher la suite",
    "details", "détails", "plus d'infos", "plus d infos", "en savoir plus",
    "learn more", "ouvrir", "open article", "cliquez ici", "click here",
    "partager", "share this", "share on", "facebook", "twitter", "whatsapp",
    "télégramme", "telegram", "linkedin", "pinterest", "print", "imprimer",
    "newsletter", "abonnez-vous", "subscribe", "suivez-nous", "follow us",
    "accueil", "homepage", "retour à l'accueil", "back to home",
    "prochain article", "next article", "précédent", "previous", "related",
    "à lire aussi", "a lire aussi", "articles similaires", "similar articles",
    "voir aussi", "voir egalement", "voir également", "see also", "tags",
    "mots-clés", "mots cles", "keywords", "catégorie", "categorie", "category",
]
# 按钮片段精确匹配（独立短文本）
CLEANUP_EXACT = {
    "lire la suite", "lire la suite details", "details", "détails", "0",
    "read more", "lire plus", "voir la suite", "suite",
}


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
            "body_status": "extraction_failed",
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

        # 1) JSON-LD articleBody（最可靠：结构化正文，含完整段落）
        body = self._extract_jsonld_body(html_text)
        if body:
            result["body"] = body
            result["method"] = "jsonld_article_body"
        else:
            # 2) 来源专用选择器
            body = self._extract_with_selectors(html_text)
            if body:
                result["body"] = body
                result["method"] = "source_selectors"
            else:
                # 3) 通用密度提取
                body = self._extract_generic(html_text)
                if body:
                    result["body"] = body
                    result["method"] = "generic_density"

        # 3a) 软404/列表页检测（清洗前，基于原始 body）：
        #     ① 按钮词密集 → 栏目/首页文本；② 标题与正文无关键词重合 → 软404
        if body:
            low_body = body.lower()
            btn_hits = sum(low_body.count(mk) for mk in (
                "lire la suite", "lire plus", "voir la suite",
                "read more", "voir plus", "afficher plus"))
            title_body_mismatch = self._title_body_mismatch(result, body)
            if btn_hits >= 2 or title_body_mismatch:
                result["quality"] = "intercepted"
                result["body_status"] = "extraction_failed"
                result["quality_reasons"].append(
                    f"soft_404_listing:btn{btn_hits}" if btn_hits >= 2
                    else "soft_404_title_mismatch")
                result["body"] = ""
                result["word_count"] = 0
                self._score(result, source_url)
                return result

        # 3b) 正文清洗（剥离按钮/分享/分页杂质行）
        if result["body"]:
            result["body"] = self._clean_body(result["body"])

        self._score(result, source_url)
        return result

    @staticmethod
    def _title_body_mismatch(result, body):
        """标题与正文关键词重合度检测：标题显著词在正文中出现比例过低 → 软404。
        对法语/英语：取 ≥5 字符的词，剔除常见停用词。"""
        title = (result.get("title") or "").lower()
        if len(title) < 10:
            return False
        # 标题词（去停用词/标点）
        words = re.findall(r"[a-zà-ÿ0-9]{5,}", title)
        stop = {"lire", "plus", "suite", "avec", "pour", "dans", "sont",
                "leur", "être", "etre", "fait", "faire", "nous", "vous",
                "this", "that", "with", "from", "have", "will", "after",
                "un", "une", "des", "les", "the", "and", "but", "not",
                "sont", "ainsi", "alors", "après", "apres", "avant",
                "comme", "déjà", "deja", "encore", "entre", "quand",
                "comment", "pourquoi", "député", "depute", "élection",
                "election", "gouvernement", "gouvernements"}
        kw = [w for w in words if w not in stop]
        if len(kw) < 3:
            return False
        hits = sum(1 for w in kw if w in body.lower())
        # 显著词 ≥3 且命中比例 < 20% → 标题与正文不相关（软404/列表页）
        return hits / len(kw) < 0.2

    def _clean_body(self, body):
        """清洗正文：剥离 CLEANUP_MARKERS 杂质行/句、压缩空白。"""
        # 先剥 HTML 注释（WordPress 区块标记等）与残余标签
        body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
        body = re.sub(r"<[^>]+>", " ", body)
        lines = [ln for ln in body.split("\n")]
        cleaned_lines = []
        for ln in lines:
            s = ln.strip()
            if not s:
                continue
            low = s.lower()
            # 整行是纯按钮/杂质（CLEANUP_EXACT 或长度过短且命中 CLEANUP_MARKERS）
            if low in CLEANUP_EXACT:
                continue
            if len(s) < 3 and low in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9"):
                continue
            # 行首行尾包裹杂质短语 → 截断
            for mk in ("lire la suite", "lire la suite details", "read more",
                       "voir la suite", "lire plus", "ouvrir"):
                if low.startswith(mk) or low.endswith(mk):
                    s = s[len(mk):].strip() if low.startswith(mk) else s[:-len(mk)].strip()
                    break
            if s:
                cleaned_lines.append(s)
        # 段落内嵌的短杂质（如 "Details" 独立词）
        out_lines = []
        for s in cleaned_lines:
            low = s.lower()
            if low in CLEANUP_EXACT:
                continue
            out_lines.append(s)
        return "\n".join(out_lines)

    def _extract_jsonld_body(self, html_text):
        """从 JSON-LD NewsArticle/Article 提取 articleBody（结构化完整正文）。"""
        if not html_text:
            return ""
        for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                             html_text, re.I | re.S):
            raw = m.group(1).strip()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            blocks = []
            if isinstance(data, dict):
                if data.get("@graph") and isinstance(data["@graph"], list):
                    blocks.extend(g for g in data["@graph"] if isinstance(g, dict))
                else:
                    blocks.append(data)
            elif isinstance(data, list):
                blocks.extend(b for b in data if isinstance(b, dict))
            for b in blocks:
                if b.get("@type") in ("NewsArticle", "Article", "ReportageNewsArticle"):
                    ab = b.get("articleBody")
                    if isinstance(ab, str) and len(ab.strip()) > 100:
                        return ab.strip()
        return ""

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
        # 优先常见正文容器 class（列表页 article 过多的站点用此兜底）
        for cls in ("entry-content", "post-content", "td-post-content",
                    "article-content", "single-content", "post-body", "entry-text",
                    "t-content__body", "article__main", "o-article__main"):
            m = re.search(r'<div[^>]*class=["\'][^"\']*' + cls + r'[^"\']*["\'][^>]*>(.*?)</div>',
                          html_text, re.I | re.S)
            if m:
                body = strip_tags(m.group(1))
                if len(body) > 200:
                    return body
        # 优先 <article>（若 article 数量过多说明是列表页，跳过）
        arts = re.findall(r"<article[^>]*>(.*?)</article>", html_text, re.I | re.S)
        if arts and len(arts) <= 10:
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
        # 最后收集全部 <p>（换行连接，保留段落结构供按行清洗）
        ps = re.findall(r"<p[^>]*>(.*?)</p>", html_text, re.I | re.S)
        body = strip_tags("\n".join(ps))
        if len(body) > 30:
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

        # body_status：与质量等级一致的语义化状态
        if result["quality"] == "full_body":
            result["body_status"] = "full_body"
        elif result["quality"] == "partial_body":
            result["body_status"] = "partial_body"
        elif result["quality"] == "rss_summary_only":
            result["body_status"] = "rss_summary_only"
        elif result["quality"] == "title_only":
            result["body_status"] = "title_only"
        elif result["quality"] == "intercepted":
            result["body_status"] = "extraction_failed"
        else:
            result["body_status"] = "extraction_failed"

        # 页面类型识别（首页/列表被误抓）
        title_low = (result["title"] or "").lower()
        if any(tm in title_low for tm in TITLE_MARKERS) and wc < 50:
            result["quality"] = "intercepted"
            result["body_status"] = "extraction_failed"
            reasons.append("looks_like_listing_or_home")


# ── 集中式文章处理状态管理 ──────────────────────────
# 状态文件：data/runtime/article_processing_state.json
# 所有决策以该文件为唯一真实来源；不再使用 per-source 零散缓存。
# 内部使用不部署到 dist。
_STATE_PATH = os.path.join(ROOT, "data", "runtime", "article_processing_state.json")
_STATE_BACKUP = _STATE_PATH + ".bak"

# ── 允许的状态枚举 ──
STATE = type("State", (), {
    "DISCOVERED": "discovered",
    "FETCHING": "fetching",
    "FETCH_SUCCEEDED": "fetch_succeeded",
    "FETCH_FAILED_RETRYABLE": "fetch_failed_retryable",
    "FETCH_FAILED_TERMINAL": "fetch_failed_terminal",
    "EXTRACTING": "extracting",
    "EXTRACTION_SUCCEEDED": "extraction_succeeded",
    "EXTRACTION_FAILED_RETRYABLE": "extraction_failed_retryable",
    "EXTRACTION_FAILED_TERMINAL": "extraction_failed_terminal",
    "PUBLISHED": "published",
    "QUARANTINED_TERMINAL": "quarantined_terminal",
})
TERMINAL_STATES = frozenset({
    STATE.PUBLISHED, STATE.QUARANTINED_TERMINAL,
    STATE.FETCH_FAILED_TERMINAL, STATE.EXTRACTION_FAILED_TERMINAL,
})
# 过渡态：中断后可自动恢复
TRANSIENT_STATES = frozenset({STATE.FETCHING, STATE.EXTRACTING})
# 可重试态
RETRYABLE_STATES = frozenset({
    STATE.FETCH_FAILED_RETRYABLE, STATE.EXTRACTION_FAILED_RETRYABLE,
})
# 重试阈值
MAX_FETCH_ATTEMPTS = 3
MAX_EXTRACTION_ATTEMPTS = 2

# ── HTTP 状态码驱动的重试策略 ──
FETCH_RETRY_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})
FETCH_TERMINAL_CODES = frozenset({404, 410, 403, 451})


def _http_is_retryable(code):
    if code in FETCH_RETRY_CODES:
        return True
    if isinstance(code, int) and 500 <= code <= 599:
        return True
    return False


def _http_is_terminal(code):
    return code in FETCH_TERMINAL_CODES


def load_processing_state():
    """加载集中式状态文件。损坏时恢复备份，均损坏返回安全空结构。"""
    try:
        with open(_STATE_PATH, "r", encoding="utf-8") as f:
            doc = json.load(f)
        if "articles" not in doc or not isinstance(doc.get("articles"), dict):
            raise json.JSONDecodeError("missing articles", "", 0)
        return doc
    except (FileNotFoundError, json.JSONDecodeError):
        # 尝试备份恢复
        try:
            with open(_STATE_BACKUP, "r", encoding="utf-8") as f:
                backup = json.load(f)
            if "articles" in backup and isinstance(backup["articles"], dict):
                with open(_STATE_PATH, "w", encoding="utf-8") as out:
                    json.dump(backup, out, ensure_ascii=False, indent=2)
                return backup
        except Exception:
            pass
        return {"articles": {}, "generated_at": bj_iso(), "version": 3}


def save_processing_state(doc):
    """原子写入：temp → flush → rename；失败时保留旧文件，写入备份。"""
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    doc["generated_at"] = bj_iso()
    doc.setdefault("version", 3)
    tmp = _STATE_PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    # 保留备份
    try:
        if os.path.exists(_STATE_PATH):
            import shutil
            shutil.copy2(_STATE_PATH, _STATE_BACKUP)
    except Exception:
        pass
    os.replace(tmp, _STATE_PATH)


def should_skip_url(norm_url_val, state_doc=None):
    """终态 URL 应跳过后续处理。"""
    if state_doc is None:
        state_doc = _cached_state_doc
    art = state_doc.get("articles", {}).get(norm_url_val)
    if not art:
        return False
    return art.get("state", "") in TERMINAL_STATES


def get_article_record(norm_url_val, state_doc=None):
    """获取文章记录字典，不存在返回 None。"""
    if state_doc is None:
        state_doc = _cached_state_doc
    return state_doc.get("articles", {}).get(norm_url_val)


def set_article_state_record(state_doc, norm_url_val, state, **extra):
    """设置文章状态记录（覆盖写入，无状态转换校验）。"""
    now = bj_iso()
    prev = state_doc.get("articles", {}).get(norm_url_val, {})
    entry = {
        "normalized_url": norm_url_val,
        "canonical_url": extra.pop("canonical_url", prev.get("canonical_url", "")),
        "source_id": extra.pop("source_id", prev.get("source_id", "")),
        "discovery_method": extra.pop("discovery_method", prev.get("discovery_method", "")),
        "state": state,
        "first_discovered_at": prev.get("first_discovered_at", now),
        "last_attempt_at": now,
        "last_success_at": extra.pop("last_success_at", prev.get("last_success_at", now if "succeeded" in state else "")),
        "attempt_count": prev.get("attempt_count", 0) + 1,
        "fetch_http_status": extra.pop("fetch_http_status", prev.get("fetch_http_status")),
        "content_hash": extra.pop("content_hash", prev.get("content_hash", "")),
        "body_status": extra.pop("body_status", prev.get("body_status", "")),
        "terminal": state in TERMINAL_STATES,
        "retry_after": extra.pop("retry_after", None),
        "last_error_code": extra.pop("last_error_code", prev.get("last_error_code", "")),
        "last_error_message": extra.pop("last_error_message", prev.get("last_error_message", "")),
        "run_id": extra.pop("run_id", prev.get("run_id", "")),
    }
    entry.update(extra)  # 剩余字段附加上去
    state_doc.setdefault("articles", {})[norm_url_val] = entry


# 模块级缓存（一次运行只加载一次）
_cached_state_doc = None


def get_state_doc():
    global _cached_state_doc
    if _cached_state_doc is None:
        _cached_state_doc = load_processing_state()
    return _cached_state_doc


def reset_state_cache():
    global _cached_state_doc
    _cached_state_doc = None


def persist_and_clear_state():
    global _cached_state_doc
    if _cached_state_doc is not None:
        save_processing_state(_cached_state_doc)
        _cached_state_doc = None


# ── 已发布/已隔离 URL 的加载（迁移用）────────────
def _load_published_urls():
    try:
        path = os.path.join(ROOT, "data", "public", "published_events.json")
        with open(path, "r", encoding="utf-8") as f:
            pub = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    urls = {}
    for ev in pub.get("items", []):
        eid = ev.get("event_id", "")
        for sl in ev.get("source_links", []):
            nu = norm_url(sl.get("url", ""))
            if nu:
                urls[nu] = eid
    return urls


# ── 旧 per-source 缓存的迁移入口 ──
def migrate_legacy_cache_files():
    """扫描 logs/collector_cache/*.json，将旧 seen_urls 迁移到集中式状态文件。
    输出迁移报告到 logs/cache_migration_report.json。"""
    report = {
        "legacy_seen_url_count": 0,
        "migrated_to_published": 0,
        "migrated_to_terminal_quarantine": 0,
        "migrated_to_discovered": 0,
        "invalid_legacy_records": 0,
        "duplicate_legacy_urls": 0,
        "migration_errors": 0,
    }
    doc = load_processing_state()
    existing = set(doc.get("articles", {}).keys())
    pub_urls = _load_published_urls()
    quar_urls = _load_quarantine_urls()

    import glob
    legacy_files = glob.glob(os.path.join(CACHE_DIR, "*.json"))
    seen_all = set()

    for lf in legacy_files:
        try:
            with open(lf, "r", encoding="utf-8") as f:
                old = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            report["migration_errors"] += 1
            continue
        for url in old.get("seen_urls", []):
            nu = norm_url(url)
            if not nu:
                report["invalid_legacy_records"] += 1
                continue
            if nu in seen_all:
                report["duplicate_legacy_urls"] += 1
                continue
            seen_all.add(nu)
            report["legacy_seen_url_count"] += 1

            if nu in existing:
                continue  # 已存在，幂等跳过

            if nu in pub_urls:
                doc.setdefault("articles", {})[nu] = _make_legacy_record(
                    nu, STATE.PUBLISHED, published_event_id=pub_urls[nu])
                report["migrated_to_published"] += 1
            elif nu in quar_urls:
                doc.setdefault("articles", {})[nu] = _make_legacy_record(
                    nu, STATE.QUARANTINED_TERMINAL, quarantine_id=quar_urls[nu])
                report["migrated_to_terminal_quarantine"] += 1
            else:
                # 无法证明已完成 → 标记为 discovered，允许重新处理
                doc.setdefault("articles", {})[nu] = _make_legacy_record(
                    nu, STATE.DISCOVERED)
                report["migrated_to_discovered"] += 1

    save_processing_state(doc)
    log_dir = os.path.join(ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, "cache_migration_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def _make_legacy_record(nu, state, **extra):
    now = bj_iso()
    return {
        "normalized_url": nu, "canonical_url": "", "source_id": "",
        "discovery_method": "", "state": state,
        "first_discovered_at": now, "last_attempt_at": now,
        "last_success_at": now if "succeeded" in state or state == STATE.PUBLISHED else "",
        "attempt_count": 1, "fetch_http_status": None,
        "content_hash": "", "body_status": "",
        "terminal": state in TERMINAL_STATES,
        "retry_after": None, "last_error_code": "", "last_error_message": "",
        "run_id": "", **extra,
    }


def _load_quarantine_urls():
    try:
        path = os.path.join(ROOT, "data", "canonical", "quarantine.json")
        with open(path, "r", encoding="utf-8") as f:
            q = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    urls = {}
    for item in q.get("items", []):
        oid = norm_url(item.get("original_id", ""))
        if oid and item.get("reason_code") not in ("", "not_security_relevant",
                                                    "weak_signal_needs_review",
                                                    "wrong_country"):
            urls[oid] = item.get("quarantine_id", "")
    return urls


# ── 向后兼容：保留旧函数签名，内部委托到集中式状态 ──
def load_state_cache(source_id):
    return get_state_doc()


def save_state_cache(source_id, cache_doc):
    save_processing_state(cache_doc)


def should_skip(url, cache_doc=None):
    nu = norm_url(url)
    doc = cache_doc if cache_doc is not None else get_state_doc()
    return should_skip_url(nu, doc)


def should_retry(url, cache_doc=None):
    nu = norm_url(url)
    doc = cache_doc if cache_doc is not None else get_state_doc()
    art = doc.get("articles", {}).get(nu)
    if not art:
        return False
    st = art.get("state", "")
    return st in RETRYABLE_STATES or st == "" or st == STATE.DISCOVERED


def set_article_state(cache_doc, url, state, **extra):
    set_article_state_record(cache_doc, norm_url(url), state, **extra)


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
