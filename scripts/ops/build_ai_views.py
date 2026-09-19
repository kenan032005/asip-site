#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_ai_views.py —— 把 C3 AI artifacts 汇总为**公开安全**视图（§三十一/§三十二）。

输出 `data/views/ai_intelligence.json`，只含页面可用的字段：
  country_analysis: {<国家>: {status, executive_assessment, trend_analysis, outlook, watch_points}}
  homepage: {status, executive_assessment, trend_analysis, outlook, watch_points}
  generated_at / data_as_of

**绝不输出** model / prompt_version / input_hash / gate_reasons / 错误信息 / token 等
内部或调试字段（§三十二：普通用户不得看到 pipeline debug / schema failure / API error）。
"""
import argparse
import io
import json
import os
import sys

# C3R2-IMPORT：仓库根从本文件推导（禁止硬编码开发机路径），
# C3 模块走 package-qualified import，扁平导入仅作兼容回退。
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _d in ("", "scripts", "scripts/ai"):
    _p = os.path.join(REPO, _d)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:                                              # noqa: E402
    from scripts.ai import c3_artifacts as ART    # noqa: E402
except ImportError:                               # pragma: no cover
    import c3_artifacts as ART                    # noqa: E402

PUBLIC_FIELDS = ("status", "executive_assessment", "trend_analysis", "outlook",
                 "watch_points", "summary_cn", "significance", "trend_signal")


def _public(rec):
    if not rec:
        return None
    out = {k: rec.get(k) for k in PUBLIC_FIELDS if k in rec}
    out["status"] = rec.get("status")
    return out


def localization_index(root, require_full=True):
    """从 localization artifacts 建索引：display identity / src_id / news_id → {title_cn, summary_cn}。

    §六：live_published_events 没有 Article Store 行，其中文结果只存在于 artifact 层，
    这里按稳定身份把结果取出来供 News view 使用（Article localization 优先）。
    """
    idx = {}
    for _k, rec in ART.load_section(root, "localization").items():
        if require_full and rec.get("status") != "FULL":
            continue
        tc = (rec.get("title_cn") or "").strip()
        sc = (rec.get("summary_cn") or "").strip()
        if not tc and not sc:
            continue
        val = {"title_cn": tc, "summary_cn": sc}
        for f in ("src_id", "display_identity", "news_id"):
            v = rec.get(f)
            if v:
                idx[str(v)] = val
    return idx


def merge_into_news_stream(root, stream_path=None, dist_path=None):
    """把中文化结果并入 News Stream（Article 优先 → artifact → 原文 fallback）。

    **必须在 build_site 之后运行**：站点的 C1A view 构建会从 canonical articles
    重新生成 news_stream.json，之后再用 artifact 补齐 live_published_events 等
    没有 Article 行的条目。
    """
    root = str(root)
    stream_path = stream_path or os.path.join(root, "data", "views", "news_stream.json")
    if not os.path.exists(stream_path):
        return {"merged": 0, "reason": "no_stream"}
    with io.open(stream_path, encoding="utf-8") as f:
        doc = json.load(f)
    idx = localization_index(root)
    merged = 0
    for it in (doc.get("items") or []):
        if (it.get("title_cn") or "").strip():
            continue                      # Article localization 优先
        for key in (str(it.get("src_id") or ""), str(it.get("news_id") or "")):
            if key and key in idx:
                v = idx[key]
                if v.get("title_cn"):
                    it["title_cn"] = v["title_cn"]
                    merged += 1
                if v.get("summary_cn"):
                    it["summary_cn"] = v["summary_cn"]
                break
    with io.open(stream_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    copied = None
    if dist_path is None:
        dist_path = os.path.join(root, "dist", "data", "views", "news_stream.json")
    if os.path.isdir(os.path.dirname(dist_path)):
        import shutil
        shutil.copy2(stream_path, dist_path)
        copied = dist_path
        # AI 视图也必须进 dist，否则前端 fetch 会 404
        ai_src = os.path.join(root, "data", "views", "ai_intelligence.json")
        if os.path.exists(ai_src):
            shutil.copy2(ai_src, os.path.join(os.path.dirname(dist_path),
                                              "ai_intelligence.json"))
    titled = sum(1 for i in (doc.get("items") or []) if (i.get("title_cn") or "").strip())
    return {"merged": merged, "titled_total": titled,
            "items": len(doc.get("items") or []), "dist": copied}


def build(root, out_path=None):
    root = str(root)
    doc = {"schema": "ai-intelligence-view-v1",
           "generated_at": None, "data_as_of": None,
           "homepage": _public(ART.read_artifact(root, "homepage_analysis", "current")),
           "country_analysis": {}, "event_analysis": {}}
    hp = ART.read_artifact(root, "homepage_analysis", "current")
    if hp:
        doc["generated_at"] = hp.get("generated_at")
        doc["data_as_of"] = hp.get("data_as_of")
    for k, rec in ART.load_section(root, "country_analysis").items():
        doc["country_analysis"][k] = _public(rec)
    for k, rec in ART.load_section(root, "event_analysis").items():
        doc["event_analysis"][k] = _public(rec)
    p = out_path or os.path.join(root, "data", "views", "ai_intelligence.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    return doc, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--merge-news-stream", action="store_true",
                    help="把 artifact 中文化并入 News Stream 并同步到 dist（须在 build_site 之后）")
    a = ap.parse_args()
    doc, p = build(a.root, a.out)
    if a.merge_news_stream:
        m = merge_into_news_stream(a.root)
        print("merge_news_stream: %s" % json.dumps(m, ensure_ascii=False))
    print("ai_intelligence: homepage=%s countries=%d events=%d -> %s"
          % ((doc.get("homepage") or {}).get("status"),
             len(doc["country_analysis"]), len(doc["event_analysis"]), p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
