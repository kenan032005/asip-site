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

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, os.path.join(REPO, "scripts", "ai"))

import c3_artifacts as ART  # noqa: E402

PUBLIC_FIELDS = ("status", "executive_assessment", "trend_analysis", "outlook",
                 "watch_points", "summary_cn", "significance", "trend_signal")


def _public(rec):
    if not rec:
        return None
    out = {k: rec.get(k) for k in PUBLIC_FIELDS if k in rec}
    out["status"] = rec.get("status")
    return out


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
    a = ap.parse_args()
    doc, p = build(a.root, a.out)
    print("ai_intelligence: homepage=%s countries=%d events=%d -> %s"
          % ((doc.get("homepage") or {}).get("status"),
             len(doc["country_analysis"]), len(doc["event_analysis"]), p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
