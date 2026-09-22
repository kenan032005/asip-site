#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""article_persistence.py —— C1B §五/§六：Article Corpus 持久化恢复。

问题（C1B §四 G1 审计结论）：
  生产采集主控 `scripts/stage3_collect_v2.py` 只把结果写进
  `data/canonical/event_clusters.json` 与 `data/canonical/quarantine.json`，
  它在内存中构建的 `all_articles` **从未落任何 Article Corpus**。
  唯一会写 `data/canonical/articles.json` 的路径是 legacy `scripts/collect.py`
  → `Repository.save_articles()`，而没有任何 workflow 调用 `collect.py`。
  结果：Article Layer 自 2026-07-30 冻结，Event Layer 持续前进。

本模块提供采集侧的单一持久化入口：

    persist_collected_articles(root, articles, run_id) -> stats

纪律：
  * **唯一真值**：`data/canonical/articles.json`（经 Repository，schema 校验 + 去重 +
    原子写入 + 备份）。本模块不引入第二个 Article store。
  * **文章入库 ≠ 事实已核实**：写入的 article 只标 `normalized` / `raw`，
    绝不写 `linked_to_event`，也绝不触碰 canonical event 阈值。
  * **确定性**：同一输入 → 同一 article_id / content_hash / 同一输出；
    重复运行不产生重复记录（Repository._save_dedup 按 article_id 幂等）。
  * **排除项显式化**：duplicate / invalid / out_of_scope / safety_hold / malformed
    五类必须逐类计数，不得静默丢弃。

写入映射复用 Stage-2 既有契约 `migrate_stage2.candidate_to_article()`，
与 legacy `collect.py` 完全同源，避免出现两套 Article 语义。
"""
import os
import re
import time
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))          # scripts/data
_SCRIPTS = os.path.dirname(_HERE)                           # scripts
CN = timezone(timedelta(hours=8))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from data.repository import Repository, SCHEMA_DIR           # noqa: E402
from data.migrate_stage2 import (candidate_to_article, build_source_index,  # noqa: E402
                                 _unwrap_source)
from data.identifiers import normalize_url, article_id, content_hash  # noqa: E402
from data.schema_validator import validate_instance, load_schema      # noqa: E402

#: 授权 Article Store（唯一真值）
AUTHORITATIVE_ARTICLE_STORE = "data/canonical/articles.json"

#: 在范围内的国家判定（采集器 identify_country 的 decision 取值）
#: C1C：由 config/countries 派生，而不是硬编码 chad/niger —— 否则新增国别的文章
#: 会被整体判为 EXCLUDED_OUT_OF_SCOPE，扩源在持久化层静默失效。
def _in_scope_decisions():
    base = {"regional"}
    try:
        _cp = os.path.join(_SCRIPTS, "collectors")
        if _cp not in sys.path:
            sys.path.insert(0, _cp)
        from countries import load_all
        for cfg in load_all().values():
            en = str(cfg.get("country_en", "")).strip().lower()
            if en:
                base.add(en)
    except Exception:
        base.update({"chad", "niger"})
    return base


IN_SCOPE_DECISIONS = _in_scope_decisions()

#: 排除码（顺序即优先级，先命中先计）
EX_EMPTY_URL = "EXCLUDED_INVALID_NO_URL"
EX_BAD_URL = "EXCLUDED_INVALID_URL"
EX_MALFORMED_TITLE = "EXCLUDED_MALFORMED_NO_TITLE"
EX_MALFORMED_BODY = "EXCLUDED_MALFORMED_NO_CONTENT"
EX_OUT_OF_SCOPE = "EXCLUDED_OUT_OF_SCOPE"
EX_SAFETY_HOLD = "EXCLUDED_SAFETY_HOLD"
# C3R2-PRE §三：非文章页（栏目/列表/搜索/Feed/作者…）不得作为 Article 正文进入
EX_NON_ARTICLE = "EXCLUDED_NON_ARTICLE_PAGE"
EX_DUPLICATE_URL = "EXCLUDED_DUPLICATE_URL"
EX_DUPLICATE_CONTENT = "EXCLUDED_DUPLICATE_CONTENT"
EX_SCHEMA_INVALID = "EXCLUDED_SCHEMA_INVALID"
EX_BAD_RUN_ID = "BLOCKED_NON_COMPLIANT_RUN_ID"

#: article.schema.json 的 run_id 约束（ASIP 唯一合法格式）
RUN_ID_RE = re.compile(r"^\d{8}T\d{6}\+0800_[a-z0-9]{6}$")


from data.article_url_admission import admit_article_url  # noqa: E402


def _src_url_of(article):
    """从采集 article 记录里取源站点 URL（用于 source lookup 兜底）。"""
    for k in ("feed_url", "listing_url", "canonical_url", "article_url"):
        v = article.get(k)
        if v:
            return v
    return ""


def _rfc3339(s):
    """把采集器的时间串归一为 RFC3339（article.schema 的 format=date-time 要求）。

    采集器内部用的是 `to_beijing()` 的 "%Y-%m-%d %H:%M:%S"（空格分隔、无时区），
    直接写入会被 schema 判为非法（format: date-time）——这会让整批 Article 入库失败。
    这里只做**格式归一**（补 T / 补 +08:00 时区），不改变时刻语义。
    无法解析时返回 None（schema 允许 null），绝不臆造时间。
    """
    if not s:
        return None
    t = str(s).strip()
    if not t:
        return None
    # 已带时区的 RFC3339/ISO8601
    try:
        dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
        if dt.tzinfo:
            return dt.isoformat()
    except ValueError:
        pass
    # 采集器的北京时间本地串："YYYY-MM-DD HH:MM:SS"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(t[:len(fmt) + 2], fmt)
            return dt.replace(tzinfo=CN).isoformat()
        except ValueError:
            continue
    # 交给健壮日期解析器（RFC822 / 命名时区 / dc:date）
    try:
        import sys as _sys
        _cp = os.path.join(_SCRIPTS, "collectors")
        if _cp not in _sys.path:
            _sys.path.insert(0, _cp)
        from feed_parser import parse_feed_date
        dt, _tz = parse_feed_date(t)
        if dt:
            return dt.isoformat()
    except Exception:
        pass
    return None


def article_to_candidate(a):
    """采集器 article dict → Stage-2 candidate dict（candidate_to_article 的输入契约）。

    只做字段改名与类型收敛，不做任何语义推断/翻译/补充。
    """
    cid = a.get("_country") if isinstance(a.get("_country"), dict) else {}
    url = (a.get("canonical_url") or a.get("article_url") or "").strip()
    lang = a.get("language")
    if isinstance(lang, list):
        lang = lang[0] if lang else ""
    published = (a.get("published_at_beijing") or a.get("published_at_original")
                 or a.get("published_time") or "")
    return {
        "url": url,
        "title_original": (a.get("original_title") or "").strip(),
        "summary_original": (a.get("original_summary") or "")[:2000],
        "published_time": _rfc3339(published),
        "fetched_at": _rfc3339(a.get("collected_at_beijing")) or "",
        "source_id": a.get("source_id") or "",
        "source_name": a.get("source_name") or "",
        "source_url": _src_url_of(a),
        "language": lang or "",
        "country": a.get("source_country") or "",
        "country_ok": True,
        "mentioned_countries": cid.get("mentioned_countries", []) or [],
        "matched_location_entities": cid.get("matched_location_entities", []) or [],
        "relevant": a.get("_relevant"),
        "rel_score": a.get("_rel_score") or 0,
        "event_type": a.get("_event_type") or "",
        "title_cn": "",
        "summary_cn": "",
        # C2：历史回填标记（§三）—— 仅回填文章携带，实时文章形状不变
        **({"historical_backfill": True,
            "backfill_collected_at": _rfc3339(a.get("backfill_collected_at")
                                              or a.get("collected_at_beijing")),
            "backfill_method": a.get("backfill_method") or "",
            "publisher_identity_id": a.get("publisher_identity_id") or ""}
           if a.get("historical_backfill") else {}),
    }


def _classify(a, seen_urls, seen_hashes, quarantined_urls):
    """返回 (exclude_code 或 None, cand_url, chash)。纯函数式判定，顺序固定。"""
    raw_url = (a.get("canonical_url") or a.get("article_url") or "").strip()
    if not raw_url:
        return EX_EMPTY_URL, "", ""
    nurl = normalize_url(raw_url)
    if not nurl:
        return EX_BAD_URL, "", ""
    # C3R2-PRE §三：确定性文章页准入（只按路径结构判定，不做语义猜测）
    ok_url, url_reason = admit_article_url(raw_url)
    if not ok_url:
        return EX_NON_ARTICLE, nurl, ""
    title = (a.get("original_title") or "").strip()
    if not title:
        return EX_MALFORMED_TITLE, nurl, ""
    body = (a.get("original_body") or "").strip()
    summary = (a.get("original_summary") or "").strip()
    if not body and not summary:
        return EX_MALFORMED_BODY, nurl, ""
    if a.get("_quarantine_reason"):
        return EX_SAFETY_HOLD, nurl, ""
    if nurl in quarantined_urls:
        return EX_SAFETY_HOLD, nurl, ""
    cid = a.get("_country") if isinstance(a.get("_country"), dict) else {}
    if cid.get("decision") not in IN_SCOPE_DECISIONS:
        return EX_OUT_OF_SCOPE, nurl, ""
    chash = content_hash(title, summary, nurl)
    if nurl in seen_urls:
        return EX_DUPLICATE_URL, nurl, chash
    if chash in seen_hashes:
        return EX_DUPLICATE_CONTENT, nurl, chash
    return None, nurl, chash


def persist_collected_articles(root, articles, run_id, verbose=True):
    """把本次采集的合格 article 写入授权 Article Store。

    返回 stats dict（含各类排除计数与 Repository 的 added/modified/skipped/failed）。
    """
    root = str(root)
    repo = Repository(root=Path(root), run_id=run_id)

    if not RUN_ID_RE.match(str(run_id or "")):
        # 不伪造 run_id：run_id 不合规时拒绝写入（否则会污染 provenance）。
        # 采集器本身始终生成合规 run_id（stage3_collect_v2.main）。
        if verbose:
            print("[article-persist] BLOCKED: non-compliant run_id=%r "
                  "(expect ^\\d{8}T\\d{6}\\+0800_[a-z0-9]{6}$)" % run_id)
        return {
            "run_id": run_id,
            "authoritative_store": AUTHORITATIVE_ARTICLE_STORE,
            "candidates_seen": len(articles),
            "new_articles_persisted": 0,
            "store_before": len(repo.load_articles()),
            "store_after": len(repo.load_articles()),
            "excludes": {EX_BAD_RUN_ID: len(articles)} if articles else {},
            "excluded_total": len(articles),
            "repo_log": {"added": 0, "modified": 0, "skipped": 0, "failed": 0},
            "blocked": True,
        }

    existing = repo.load_articles()
    seen_urls, seen_hashes = set(), set()
    for a in existing:
        for u in (a.get("canonical_url"), a.get("article_url"),
                  (a.get("legacy_payload") or {}).get("url")):
            if u:
                n = normalize_url(u)
                if n:
                    seen_urls.add(n)
        h = a.get("content_hash")
        if h:
            seen_hashes.add(h)

    # 隔离区（安全hold）：本次已判定的隔离 URL + store 中已有的隔离 URL
    quarantined_urls = set()
    q_path = os.path.join(root, "data", "canonical", "quarantine.json")
    if os.path.exists(q_path):
        try:
            import json as _json
            qd = _json.load(open(q_path, encoding="utf-8"))
            for q in (qd.get("items") or []):
                # C2 §七：已被正式释放（重判通过）的 hold 不再构成安全拦截，
                # 否则「释放」会被自己的历史 hold 记录立即挡回，成为空操作。
                if str(q.get("review_status") or "").lower() in ("released", "restored"):
                    continue
                u = q.get("original_id") or q.get("url")
                n = normalize_url(u) if u else ""
                if n:
                    quarantined_urls.add(n)
        except Exception:
            pass
    non_article_rejects = []
    for a in articles:
        _u = (a.get("canonical_url") or a.get("article_url") or "")
        _ok, _reason = admit_article_url(_u)
        if not _ok:
            non_article_rejects.append({"url": _u, "reason": _reason,
                                        "source_id": a.get("source_id") or "",
                                        "run_id": run_id})
    for a in articles:
        if a.get("_quarantine_reason"):
            n = normalize_url(a.get("canonical_url") or a.get("article_url") or "")
            if n:
                quarantined_urls.add(n)

    # 源索引：与 collect.py 完全同源（upgraded → unwrap）
    try:
        upgraded = repo.load_sources()
        op_sources = []
        for rec in upgraded:
            op = _unwrap_source(rec)
            op["enabled"] = bool(rec.get("enabled", op.get("enabled", False)))
            op_sources.append(op)
        idx = build_source_index(op_sources)
    except Exception:
        idx = {}

    schema = load_schema("article.schema.json", SCHEMA_DIR)
    excludes = {}
    to_add, skipped_detail = [], []
    for a in articles:
        code, nurl, chash = _classify(a, seen_urls, seen_hashes, quarantined_urls)
        if code:
            excludes[code] = excludes.get(code, 0) + 1
            continue
        cand = article_to_candidate(a)
        try:
            art = candidate_to_article(cand, from_pending=False, idx=idx)
        except Exception as e:  # noqa: BLE001
            excludes[EX_SCHEMA_INVALID] = excludes.get(EX_SCHEMA_INVALID, 0) + 1
            if verbose:
                print("    [article-persist] adapter failed: %s" % type(e).__name__)
            continue
        # run_id 由 Repository 在保存时统一盖章；此处提前盖章以便通过 schema 预校验
        # （Repository._save_dedup 是先校验后盖章，空 run_id 会整批中止）
        art["run_id"] = run_id
        # 逐条 schema 预校验：一条不合规不得拖垮整批（Repository 是 fail-fast 全批）
        errs = validate_instance(art, schema)
        if errs:
            excludes[EX_SCHEMA_INVALID] = excludes.get(EX_SCHEMA_INVALID, 0) + 1
            if verbose:
                print("    [article-persist] schema reject %s: %s"
                      % (art.get("article_id"), errs[:2]))
            continue
        seen_urls.add(nurl)
        seen_hashes.add(chash)
        to_add.append(art)

    log = {"added": 0, "modified": 0, "skipped": 0, "failed": 0}
    if to_add:
        log = repo.save_articles(existing + to_add, run_id)

    stats = {
        "run_id": run_id,
        "authoritative_store": AUTHORITATIVE_ARTICLE_STORE,
        "candidates_seen": len(articles),
        "new_articles_persisted": log.get("added", 0),
        "store_before": len(existing),
        "store_after": len(repo.load_articles()),
        "excludes": excludes,
        "excluded_total": sum(excludes.values()),
        # C3R2-PRE §三：非文章页拒绝的审计账本（明确留证，不进正文集合）
        "non_article_rejections": non_article_rejects,
        "non_article_rejected_total": len(non_article_rejects),
        "article_url_admission": "data/article_url_admission.admit_article_url",
        "repo_log": log,
    }
    if verbose:
        print("[article-persist] store %d -> %d (added=%d modified=%d skipped=%d failed=%d)"
              % (stats["store_before"], stats["store_after"], log.get("added", 0),
                 log.get("modified", 0), log.get("skipped", 0), log.get("failed", 0)))
        if excludes:
            print("[article-persist] excludes: %s" % excludes)
    if non_article_rejects:
        try:
            import json as _json
            import os as _os
            led = _os.path.join(root, "data", "audit", "article_url_rejections.json")
            _os.makedirs(_os.path.dirname(led), exist_ok=True)
            cur = {}
            if _os.path.exists(led):
                try:
                    cur = _json.load(open(led, encoding="utf-8"))
                except Exception:
                    cur = {}
            entries = cur.get("entries") or []
            entries.extend(non_article_rejects)
            cur = {"schema": "article-url-rejections-v1",
                   "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "reason_codes": ["NON_ARTICLE_PAGE", "NON_ARTICLE_PAGE_HOMEPAGE",
                                    "NON_ARTICLE_PAGE_SCHEME"],
                   "entries": entries[-500:]}
            with open(led, "w", encoding="utf-8") as f:
                _json.dump(cur, f, ensure_ascii=False, indent=1)
        except Exception:
            pass
    return stats


if __name__ == "__main__":
    # 用法：python scripts/data/article_persistence.py --selftest
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Article persistence (C1B §五)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--root", default=None)
    a = ap.parse_args()
    if a.selftest:
        print(json.dumps({"authoritative_store": AUTHORITATIVE_ARTICLE_STORE,
                          "in_scope_decisions": list(IN_SCOPE_DECISIONS),
                          "exclude_codes": [EX_EMPTY_URL, EX_BAD_URL, EX_MALFORMED_TITLE,
                                            EX_MALFORMED_BODY, EX_OUT_OF_SCOPE,
                                            EX_SAFETY_HOLD, EX_DUPLICATE_URL,
                                            EX_DUPLICATE_CONTENT, EX_SCHEMA_INVALID]},
                         ensure_ascii=False, indent=1))
    else:
        print("nothing to do (use --selftest)")
