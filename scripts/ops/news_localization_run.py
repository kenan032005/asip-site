#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP C7-3 — 文章级情报本地化 / 富集运行器（LEVEL A：Intelligence Feed）。

只做一件事：把**近期**情报流条目（news_stream，文章级，允许单源）补上
title_cn / summary_cn / why_it_matters，写入运行时缓存
data/runtime/ops/localization/index.json（键 = 条目 dedup_key）。

边界（铁律）：
  - 不写 canonical articles 真相（runtime enrichment → view projection）；
  - 不把任何条目升级为已核实事件（LEVEL A ≠ LEVEL B）；
  - 缓存键 = 内容哈希（dedup_key + 原文摘要），同输入绝不重复 AI 调用；
  - 只处理近 N 天（默认 7d）条目，绝不批量翻译历史库；
  - 凭据缺失 → CREDENTIAL_MISSING 直接退出（fail-closed，不伪造输出）。

用法：
  python scripts/ops/news_localization_run.py                 # 生产（真实 AI）
  python scripts/ops/news_localization_run.py --dry-run       # 只输出计划，不调 AI
  python scripts/ops/news_localization_run.py --max-items 12
"""

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BJT = timezone(timedelta(hours=8))
VIEW = Path("data") / "views" / "news_stream.json"
OUT_DIR = Path("data") / "runtime" / "ops" / "localization"
INDEX = OUT_DIR / "index.json"
BATCH = 8

SYSTEM = (
    "你是 ASIP 平台的资深安全情报编辑，负责把非洲安全领域的公开新闻标题与摘要"
    "本地化为简洁、克制的中文情报条目。"
    "规则：1) 只使用输入材料中已有的信息，禁止补充、推测或添加任何材料外的事实；"
    "2) 逐条输出，不得合并或遗漏；3) 输出必须是严格的 JSON 数组，不要包含任何解释文字。"
)
USER_TMPL = (
    "请将以下 %d 条安全新闻条目本地化。每条输入包含 key、来源标题、来源摘要。\n"
    "对每条输出一个 JSON 对象：\n"
    '{{"key": "<原样返回 key>", "title_cn": "<中文标题，≤40字>", '
    '"summary_cn": "<中文摘要，≤60字，客观陈述事实>", '
    '"why_it_matters": "<安全相关性说明，≤50字，只解释与安全的相关性，不做预测>"}}\n'
    "输入条目：\n%s")


def parse_time(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=BJT)
    except ValueError:
        return None


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def write_atomic(path, obj):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def item_key(it):
    base = json.dumps({
        "k": it.get("dedup_key") or it.get("news_id") or it.get("src_id"),
        "t": (it.get("title_original") or it.get("summary_original") or "")[:200],
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def eligible(items, now, window_days, max_items, index):
    cutoff = now - timedelta(days=window_days)
    rows = []
    for it in items:
        if it.get("quarantined"):
            continue
        if it.get("localized"):
            continue
        t = parse_time(it.get("last_seen_at") or it.get("observed_at"))
        if t is None or t < cutoff:
            continue
        key = item_key(it)
        if key in index:
            continue  # 缓存命中（同输入不重复调用）
        if not (it.get("title_original") or it.get("summary_original") or it.get("title_cn")):
            continue
        rows.append((t, key, it))
    rows.sort(key=lambda r: r[0], reverse=True)
    return rows[:max_items] if max_items else rows


def localize_batch(prov, batch, telemetry):
    """单批一次 AI 调用；返回 {key: {...}} 与 (calls, tokens)。"""
    payload = json.dumps([{
        "key": key,
        "title": it.get("title_original") or it.get("title_cn") or "",
        "summary": (it.get("summary_original") or it.get("summary_cn") or "")[:400],
        "country": it.get("country_cn") or "",
        "event_type": it.get("event_type_cn") or it.get("event_type") or "",
    } for _, key, it in batch], ensure_ascii=False, indent=1)
    task = {
        "task_id": "news-localization-%s" % datetime.now(BJT).strftime("%Y%m%dT%H%M%S"),
        "task_type": "news_localization",
        "system_text": SYSTEM,
        "user_text": USER_TMPL % (len(batch), payload),
        "max_output_tokens": 4000,
    }
    rec = prov.submit_task(task)
    calls = 1
    tokens = (rec.get("total_tokens") if isinstance(rec.get("total_tokens"), int) else 0)
    telemetry.append({"task_id": task["task_id"], "status": rec.get("status"),
                      "model": rec.get("returned_model"),
                      "total_tokens": rec.get("total_tokens")})
    if rec.get("status") != "succeeded":
        return {}, calls, tokens, rec.get("status")
    text = (rec.get("result") or {}).get("text") or ""
    m = text.find("[")
    n = text.rfind("]")
    if m < 0 or n <= m:
        return {}, calls, tokens, "JSON_NOT_FOUND"
    try:
        arr = json.loads(text[m:n + 1])
    except ValueError:
        return {}, calls, tokens, "JSON_INVALID"
    out = {}
    if not isinstance(arr, list):
        return {}, calls, tokens, "JSON_NOT_ARRAY"
    for o in arr:
        if not isinstance(o, dict):
            continue
        key = str(o.get("key") or "")
        tcn = str(o.get("title_cn") or "").strip()
        if not key or not tcn:
            continue
        out[key] = {"title_cn": tcn[:80],
                    "summary_cn": str(o.get("summary_cn") or "").strip()[:140],
                    "why_it_matters": str(o.get("why_it_matters") or "").strip()[:140],
                    "model": rec.get("returned_model"),
                    "generated_at": datetime.now(BJT).isoformat(timespec="seconds")}
    return out, calls, tokens, "ok"


def main(argv=None):
    ap = argparse.ArgumentParser(description="ASIP C7-3 文章级本地化（LEVEL A）")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--max-items", type=int, default=12)
    ap.add_argument("--batch-size", type=int, default=BATCH)
    ap.add_argument("--dry-run", action="store_true", help="只输出计划，不调用 AI")
    args = ap.parse_args(argv)

    root = Path(args.root)
    items = (load_json(root / VIEW, {}) or {}).get("items") or []
    index = load_json(root / INDEX, {})
    if not isinstance(index, dict):
        index = {}

    now = datetime.now(BJT)
    rows = eligible(items, now, args.window_days, args.max_items, index)
    plan = {"mode": "dry-run" if args.dry_run else "apply",
            "feed_items": len(items), "eligible": len(rows),
            "cache_index_entries": len(index), "real_ai_calls": 0}
    if args.dry_run:
        plan["sample"] = [{"key": k, "title": (it.get("title_original") or "")[:60]}
                          for _, k, it in rows[:5]]
        print(json.dumps(plan, ensure_ascii=False, indent=1))
        return 0

    prov = None
    try:
        # 与 enrichment_run 相同的双路径导入约定（脚本以 python scripts/ops/xxx.py
        # 运行时 sys.path[0] 是 scripts/ops，scripts.ai 需要仓库根在路径上）
        for _p in (str(root), str(root / "scripts"), str(root / "scripts" / "data")):
            if _p not in sys.path:
                sys.path.insert(0, _p)
        from scripts.ai.safety import manual_trial as mt  # noqa: E402
        prov = mt._flash_provider()
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"status": "PROVIDER_IMPORT_FAIL", "error": str(e)[:200],
                          "real_ai_calls": 0}, ensure_ascii=False))
        return 0  # fail-closed：不伪造输出，交由下一轮重试

    telemetry = []
    localized, calls, tokens, cache_hits, last_status = 0, 0, 0, 0, "no_eligible"
    for i in range(0, len(rows), max(1, args.batch_size)):
        batch = rows[i:i + max(1, args.batch_size)]
        out, c, tk, st = localize_batch(prov, batch, telemetry)
        calls += c
        tokens += tk or 0
        last_status = st
        if st != "ok":
            break
        for key, val in out.items():
            index[key] = val
        localized += len(out)
    (root / OUT_DIR).mkdir(parents=True, exist_ok=True)
    write_atomic(root / INDEX, index)
    print(json.dumps({"status": last_status, "eligible": len(rows), "localized": localized,
                      "ai_calls": calls, "cache_index_entries": len(index),
                      "total_tokens": tokens, "real_ai_calls": calls,
                      "telemetry": telemetry[-4:]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
