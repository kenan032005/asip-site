#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gdelt_rate_limiter.py —— C1B §九：GDELT 共享限流器（GDELT_SHARED_RATE_LIMITER）。

背景：
  生产来源配置中有 68 个 `collection_method = "gdelt_search"` 的源，但它们**查询的是
  同一个 GDELT 公共 API**（api.gdeltproject.org）。旧实现把它们当作 68 个彼此独立的
  HTTP 源并发访问，只靠一个 20s 的同主机间隔兜底，于是在出口 IP 被节流时整批 429、
  68 个源一起零产出——这正是 Source Yield 报告中 E 档（无产出/被阻断）占比 76% 的
  主要来源之一。

原则（§九）：
  **不得**绕过服务限制 / 代理池规避限流 / 高频暴力请求 / 付费升级。
  **允许**且本模块实现：FREE_ONLY_MODE 下的
    - global request pacing     （全局请求节流，跨源共享）
    - shared cache              （同签名查询全运行期只请求一次）
    - query consolidation       （同国同关键词合并为 OR 查询）
    - request dedupe            （签名去重）
    - country query batching    （同批国家共用一次配额）
    - exponential backoff       （429 指数退避 + 上限）
    - Retry-After respect       （优先遵循服务端 Retry-After）
    - schedule spreading        （同批请求在节流窗口内均匀铺开）

本模块是 GDELT 请求的**唯一出口**：任何采集器都不得直接 urlopen GDELT。
"""
import hashlib
import json
import os
import random
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

HOST = "api.gdeltproject.org"

# ── C8-4E W1：GDELT 响应体分类（「有响应」≠「有可用结果」）──────────
#: 五类区分的落点：合法空结果才记为 QUERY_NO_RESULT；429 / 非 JSON 限流提示 /
#: JSON 解析或结构异常 / 网络超时及其它 HTTP 错误各有独立原因码。
BODY_JSON_OK = "json_ok"                # 合法 JSON 且 articles 为列表
BODY_JSON_STRUCTURE = "json_structure"  # 合法 JSON 但结构不符合 ArtList 约定
BODY_JSON_CORRUPT = "json_corrupt"      # 形如 JSON 但解析失败
BODY_NON_JSON = "non_json"              # 非 JSON 响应体（如 GDELT 限流建议文本）
BODY_EMPTY = "empty"                    # 空响应体

ERR_GDELT_NON_JSON = "GDELT_NON_JSON_RESPONSE"
ERR_GDELT_JSON_INVALID = "GDELT_JSON_INVALID"

#: 已知 GDELT 限流建议的特征串 —— 只用于输出布尔标记，**绝不输出原文**
_ADVISORY_RX = re.compile(r"limit requests|gdeltproject|ngrams dataset|kalev\.leetaru", re.I)


def _safe_detail(**kw):
    """只保留安全元数据（长度/类型/布尔标记），绝不包含原始响应体内容。"""
    return ", ".join("%s=%s" % (k, v) for k, v in sorted(kw.items()))


def classify_body(text):
    """对 GDELT 响应体做确定性分类。

    返回 (body_class, detail_dict, error_or_None)。
    error 为确定性错误码（例：GDELT_NON_JSON_RESPONSE(body_len=347, advisory_like=True)），
    **不含原始响应体任何内容**（C8-4E W1：禁止打印原始响应中的潜在敏感数据）。
    """
    if text is None:
        return None, {}, None
    s = text.strip()
    if not s:
        return BODY_EMPTY, {"body_len": 0}, "%s(body_len=0)" % ERR_GDELT_NON_JSON
    if s[:1] not in "{[":
        det = {"body_len": len(s), "advisory_like": bool(_ADVISORY_RX.search(s))}
        return BODY_NON_JSON, det, "%s(%s)" % (ERR_GDELT_NON_JSON, _safe_detail(**det))
    try:
        obj = json.loads(s)
    except Exception as e:  # noqa: BLE001
        det = {"body_len": len(s), "parse_error": type(e).__name__}
        return BODY_JSON_CORRUPT, det, "%s(%s)" % (ERR_GDELT_JSON_INVALID, _safe_detail(**det))
    if not isinstance(obj, dict) or not isinstance(obj.get("articles"), list):
        det = {"body_len": len(s), "root_type": type(obj).__name__,
               "has_articles": isinstance(obj, dict) and isinstance(obj.get("articles"), list)}
        return BODY_JSON_STRUCTURE, det, "%s(%s)" % (ERR_GDELT_JSON_INVALID, _safe_detail(**det))
    return BODY_JSON_OK, {"body_len": len(s), "articles": len(obj["articles"])}, None


#: 事件 / 快速路径用的 UA（与 collectors/base.py 保持一致语义）
UA = ("Mozilla/5.0 (compatible; ASIP-Collector/1.0; "
      "+https://github.com/kenan032005/asip-site)")


_CN2EN = None


def _cn2en():
    """中文国名 → 英文国名（用于查询签名归一，消除 乍得/Chad 这类等价重复请求）。"""
    global _CN2EN
    if _CN2EN is None:
        m = {}
        try:
            import os
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            d = os.path.join(root, "config", "countries")
            for fn in sorted(os.listdir(d)):
                if fn.endswith(".json"):
                    with open(os.path.join(d, fn), "r", encoding="utf-8") as f:
                        c = json.load(f)
                    if c.get("country") and c.get("country_en"):
                        m[c["country"]] = c["country_en"]
        except Exception:  # noqa: BLE001
            m = {}
        _CN2EN = m
    return _CN2EN or {}


def normalize_query_country(query):
    """把查询串里的中文国名替换为英文，使等价查询签名一致（C7-4S P1）。"""
    q = str(query or "")
    for cn, en in _cn2en().items():
        if cn in q:
            q = q.replace(cn, en)
    return q


def query_signature(url):
    """把 URL 归一成稳定签名：仅保留会影响结果的参数，排序后哈希。

    用于 request dedupe / shared cache —— 同一 (query, mode, timespan,
    maxrecords, sort) 组合只请求一次，与调用它的源无关。
    C7-4S：query 先做国家名归一（Chad/乍得 视为同一查询）。
    """
    try:
        p = urllib.parse.urlsplit(url)
    except Exception:
        return hashlib.sha256(str(url).encode()).hexdigest()[:16]
    qp = dict(urllib.parse.parse_qsl(p.query, keep_blank_values=True))
    keep = {k: qp.get(k, "") for k in ("query", "mode", "timespan", "maxrecords", "sort")}
    keep["query"] = normalize_query_country(keep.get("query", ""))
    raw = "|".join("%s=%s" % (k, keep[k]) for k in sorted(keep))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class GdeltSharedRateLimiter:
    """全局唯一的 GDELT 请求闸门（进程内单例由模块底部的 GLOBAL 提供）。

    线程安全：采集器当前是单线程顺序执行，但闸门本身加锁，避免未来并行化时
    意外击穿节流。
    """

    def __init__(self, min_interval=20.0, max_interval=300.0, max_attempts=3,
                 budget=120, timeout=40, allow_network=True, clock=time.monotonic,
                 sleeper=time.sleep):
        self.min_interval = float(min_interval)
        self.max_interval = float(max_interval)
        self.max_attempts = int(max_attempts)
        self.budget = int(budget)
        self.timeout = int(timeout)
        self.allow_network = bool(allow_network)
        self._clock = clock
        self._sleep = sleeper
        self._lock = threading.RLock()
        self._cache = {}          # signature -> {"text", "error", "status"}
        self._next_allowed = 0.0  # 全局下一次可发起请求的时间（单调钟）
        self.interval = self.min_interval
        self.retry_after_honored = 0
        self.backoff_events = 0
        self.requests = 0          # 逻辑查询数（通过缓存/预算门后的 fetch 次数）
        self.http_attempts = 0    # 物理 HTTP 尝试数（含重试；C8-4E W2 STEP3）
        self.cache_hits = 0
        self.status_counts = {}   # "200" / "429" / "timeout" / ...
        self.by_label = {}        # label -> {requests, success, errors, cache_hits}
        self.body_class_counts = {}  # body_class -> 次数（C8-4E W1）

    # ── 内部 ────────────────────────────────────────────
    def _label(self, label):
        return label or "(unlabeled)"

    def _acc(self, label, key, n=1):
        d = self.by_label.setdefault(self._label(label),
                                     {"requests": 0, "success": 0, "rate_limited": 0,
                                      "errors": 0, "cache_hits": 0, "items": 0})
        d[key] = d.get(key, 0) + n

    def _pace(self):
        """全局节流：保证任意两次 GDELT 请求之间至少间隔 self.interval 秒。"""
        now = self._clock()
        wait = self._next_allowed - now
        if wait > 0:
            self._sleep(wait)
            now = self._clock()
        self._next_allowed = now + self.interval

    def _on_429(self, retry_after=None):
        """指数退避 + Retry-After 优先。返回本次需要等待的秒数。"""
        self.backoff_events += 1
        self.interval = min(self.max_interval, max(self.min_interval, self.interval * 2))
        wait = self.interval
        if retry_after is not None and retry_after > 0:
            wait = max(wait, float(retry_after))
            self.retry_after_honored += 1
        # 抖动避免多个运行在同一时刻重试
        wait += random.uniform(0, min(5.0, self.interval * 0.1))
        self._next_allowed = self._clock() + wait
        return wait

    def _on_success(self):
        """成功后退避衰减（回到全局最小间隔）。"""
        if self.interval > self.min_interval:
            self.interval = max(self.min_interval, self.interval / 2)

    # ── 对外 ────────────────────────────────────────────
    def fetch(self, url, label=None, timeout=None):
        """返回 (text_or_None, error_or_None, meta)。

        meta = {"signature", "cache": bool, "status": int|str, "attempts": int,
                "rate_limited": bool, "retry_after": int|None}
        """
        sig = query_signature(url)
        with self._lock:
            if sig in self._cache:
                self.cache_hits += 1
                self._acc(label, "cache_hits")
                e = self._cache[sig]
                if e.get("body_class"):
                    self.body_class_counts[e["body_class"]] = \
                        self.body_class_counts.get(e["body_class"], 0) + 1
                return e["text"], e["error"], {
                    "signature": sig, "cache": True, "status": e["status"],
                    "attempts": 0, "rate_limited": e["rate_limited"],
                    "retry_after": None, "body_class": e.get("body_class"),
                }
            if self.requests >= self.budget:
                err = "GLOBAL_REQUEST_BUDGET_EXHAUSTED(%d)" % self.budget
                self._acc(label, "errors")
                return None, err, {"signature": sig, "cache": False,
                                   "status": "budget", "attempts": 0,
                                   "rate_limited": False, "retry_after": None}
            self.requests += 1
            self._acc(label, "requests")

        if not self.allow_network:
            err = "NETWORK_DISABLED_FOR_TEST"
            with self._lock:
                self._cache[sig] = {"text": None, "error": err, "status": "offline",
                                    "rate_limited": False, "body_class": None}
                self._acc(label, "errors")
            return None, err, {"signature": sig, "cache": False, "status": "offline",
                               "attempts": 0, "rate_limited": False, "retry_after": None}

        text, err, status, attempts, rate_limited, retry_after = None, None, None, 0, False, None
        body_class = None
        for attempt in range(1, self.max_attempts + 1):
            attempts = attempt
            # C8-4E W2 STEP3：每一次物理 urlopen 尝试都计数，重试不得遗漏
            self.http_attempts += 1
            self._pace()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
                    raw = r.read()
                    status = r.status
                    enc = r.headers.get_content_charset() or "utf-8"
                    try:
                        text = raw.decode(enc, "ignore")
                    except LookupError:
                        text = raw.decode("utf-8", "ignore")
                    # C8-4E W1：HTTP 200 也可能带不可用响应体（限流建议文本等），
                    # 先分类再决定是否当作成功；不可用时 text=None + 确定性错误码。
                    body_class, _det, body_err = classify_body(text)
                    if body_err is not None:
                        text = None
                        err = body_err
                    else:
                        err = None
                break
            except urllib.error.HTTPError as e:
                status = e.code
                err = "HTTP %s" % e.code
                ra = e.headers.get("Retry-After") if e.headers else None
                if ra:
                    try:
                        v = int(str(ra).strip())
                        # 保留本次调用中观察到的最大 Retry-After（最后一次可能无 header）
                        retry_after = v if retry_after is None else max(retry_after, v)
                    except Exception:
                        pass
                if e.code == 429:
                    rate_limited = True
                    if attempt < self.max_attempts:
                        self._on_429(retry_after)
                        continue
                elif attempt < self.max_attempts:
                    self._next_allowed = self._clock() + min(10.0, self.interval)
                    continue
            except Exception as e:  # noqa: BLE001
                status = type(e).__name__
                err = "%s: %s" % (type(e).__name__, e)
                if attempt < self.max_attempts:
                    self._next_allowed = self._clock() + min(10.0, self.interval)
                    continue

        with self._lock:
            key = str(status)
            self.status_counts[key] = self.status_counts.get(key, 0) + 1
            if text:
                self._on_success()
                self._acc(label, "success")
            else:
                self._acc(label, "rate_limited" if rate_limited else "errors")
            if body_class:
                self.body_class_counts[body_class] = \
                    self.body_class_counts.get(body_class, 0) + 1
            self._cache[sig] = {"text": text, "error": err, "status": status,
                                "rate_limited": rate_limited, "body_class": body_class}
        return text, err, {"signature": sig, "cache": False, "status": status,
                           "attempts": attempts, "rate_limited": rate_limited,
                           "retry_after": retry_after, "body_class": body_class}

    def spread_offsets(self, n, window=None):
        """schedule spreading：把同批 n 个请求在节流窗口内均匀铺开（确定性）。

        返回 [0, w, 2w, ...]；采集器可据此在同批国家间主动错峰，避免瞬时并发。
        """
        n = max(0, int(n))
        if n <= 1:
            return [0.0] * max(n, 0)
        w = float(window if window is not None else self.interval)
        step = w / float(n)
        return [round(i * step, 3) for i in range(n)]

    def stats(self):
        with self._lock:
            total = sum(v["requests"] for v in self.by_label.values())
            success = sum(v["success"] for v in self.by_label.values())
            rl = sum(v["rate_limited"] for v in self.by_label.values())
            return {
                "schema": "gdelt-rate-limiter-v1",
                "host": HOST,
                "requests": self.requests,
                "logical_queries": self.requests,
                "cache_hits": self.cache_hits,
                "status_counts": dict(self.status_counts),
                "current_interval_s": round(self.interval, 2),
                "min_interval_s": self.min_interval,
                "max_interval_s": self.max_interval,
                "backoff_events": self.backoff_events,
                "retry_after_honored": self.retry_after_honored,
                "request_budget": self.budget,
                "budget_exhausted": self.requests >= self.budget,
                # C8-4E W1：明确「实际 HTTP 请求数」与「按源聚合计数」的区别，
                # 不得把按源聚合的失败计数说成实际 HTTP 请求数。
                "physical_http_attempts": self.http_attempts,
                "actual_http_requests": self.http_attempts,
                "body_class_counts": dict(self.body_class_counts),
                "counting_note": ("logical_queries/requests=逻辑查询数（已扣除缓存命中与预算拒绝）；"
                                  "physical_http_attempts/actual_http_requests=物理 HTTP 尝试数，"
                                  "**含 429/超时重试**（一次逻辑查询可产生多次物理尝试）；"
                                  "labeled_* 与 failure_reasons 均按 source_id×国家管线聚合，"
                                  "一组共享查询会被多个源重复计数，既不是逻辑查询数也不是物理请求数"),
                "labeled_requests": total,
                "labeled_success": success,
                "labeled_rate_limited": rl,
                "success_rate": (round(success / total, 4) if total else None),
                "rate_limited_rate": (round(rl / total, 4) if total else None),
                "by_label": dict(self.by_label),
            }

    def save_telemetry(self, path):
        """把限流器遥测落盘，供 source_health / yield report 消费。"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.stats(), f, ensure_ascii=False, indent=1)
        return path

    def reset_for_test(self):
        with self._lock:
            self._cache.clear()
            self._next_allowed = 0.0
            self.interval = self.min_interval
            self.retry_after_honored = 0
            self.backoff_events = 0
            self.requests = 0
            self.cache_hits = 0
            self.http_attempts = 0
            self.status_counts = {}
            self.by_label = {}
            self.body_class_counts = {}


#: 进程内唯一实例 —— 所有采集器共用（68 个 gdelt 源共享一个闸门）
#: C1C：参数支持环境变量覆盖。理由（生产可用性）：CI job 有 30 分钟上限，而
#: 20s pacing × 3 次尝试 × （国别数）组查询在 GDELT 持续 429 时可能超时。
#: 默认值与 C1B 完全一致（20s / 300s / 3 次 / 120 预算），仅在显式设置时才改变。
GLOBAL = GdeltSharedRateLimiter(
    min_interval=float(os.environ.get("ASIP_GDELT_MIN_INTERVAL", "20")),
    max_interval=float(os.environ.get("ASIP_GDELT_MAX_INTERVAL", "300")),
    max_attempts=int(os.environ.get("ASIP_GDELT_MAX_ATTEMPTS", "3")),
    budget=int(os.environ.get("ASIP_GDELT_BUDGET", "120")),
    timeout=int(os.environ.get("ASIP_GDELT_TIMEOUT", "40")),
)


def fetch_gdelt(url, label=None, timeout=None, limiter=None):
    """所有 GDELT HTTP 请求的唯一出口。"""
    return (limiter or GLOBAL).fetch(url, label=label, timeout=timeout)


def build_gdelt_url(query, timespan="72h", maxrecords=250, mode="ArtList", sort="DateDesc"):
    params = {"query": query, "mode": mode, "format": "json",
              "maxrecords": str(maxrecords), "sort": sort, "timespan": timespan}
    return "https://%s/api/v2/doc/doc?%s" % (HOST, urllib.parse.urlencode(params))
