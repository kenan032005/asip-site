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


#: C3F §八/§九：monitored 国家的中文显示名 → ISO3 稳定身份。
#: 仅作**静态参考数据**；country_snapshots 里已有的映射优先（见 _iso3_name_map）。
#: 注意：刚果（金）= COD（Kinshasa），刚果共和国（刚果布）= COG（Brazzaville），两者不得混淆。
ISO3_BY_NAME = {
    "乍得": "TCD", "尼日尔": "NER", "尼日利亚": "NGA", "贝宁": "BEN",
    "南苏丹": "SSD", "苏丹": "SDN", "莫桑比克": "MOZ", "利比亚": "LBY",
    "埃塞俄比亚": "ETH", "肯尼亚": "KEN", "索马里": "SOM", "刚果（金）": "COD",
    "刚果民主共和国": "COD", "刚果共和国（刚果布）": "COG", "刚果（布）": "COG",
    "乌干达": "UGA", "加纳": "GHA", "加蓬": "GAB", "坦桑尼亚": "TZA",
    "埃及": "EGY", "塞内加尔": "SEN", "安哥拉": "AGO", "摩洛哥": "MAR",
    "科特迪瓦": "CIV", "突尼斯": "TUN", "阿尔及利亚": "DZA", "中非共和国": "CAF",
    "喀麦隆": "CMR", "马里": "MLI", "布基纳法索": "BFA", "毛里塔尼亚": "MRT",
}


def _iso3_name_map(root):
    """C3F §八：稳定国家身份映射 ISO3 → 中文显示名（禁止用文件名当显示名）。"""
    os_ = os.path.join(str(root), "data", "views", "country_snapshots.json")
    rows = []
    try:
        with io.open(os_, encoding="utf-8") as f:
            rows = (json.load(f).get("snapshots") or [])
    except Exception:  # noqa: BLE001
        rows = []
    iso2name, name2iso, iso2en = {}, {}, {}
    for name, iso in ISO3_BY_NAME.items():      # 静态参考先行
        name2iso[name] = iso
        iso2name.setdefault(iso, name)
    for r in rows:                              # 视图数据优先（更权威）
        iso = (r.get("iso3") or "").upper()
        cn = r.get("country_cn") or ""
        en = r.get("country_en") or ""
        if iso and cn:
            iso2name[iso] = cn
            name2iso[cn] = iso
            iso2en[iso] = en
    return iso2name, name2iso, iso2en


def country_index_by_iso3(root):
    """把 country_analysis artifacts 按 ISO3 建索引（文件名只用于定位，不用于关联）。

    C3F §八：artifact 文件名经过消毒（刚果（金）→ 刚果_金_），
    因此必须用 artifact 内记录的 country 显示名反查 ISO3，绝不用文件名猜国家。
    """
    iso2name, name2iso, _ = _iso3_name_map(root)
    out = {}
    for _k, rec in ART.load_section(root, "country_analysis").items():
        pub = _public(rec)
        if pub is None:
            continue
        cn = rec.get("country") or rec.get("country_cn") or ""
        if cn not in name2iso:
            # 兼容旧 artifact：用文件名去掉消毒字符后尝试匹配显示名
            cand = cn or _k.replace("_", "")
            for name, iso in name2iso.items():
                if name.replace("（", "").replace("）", "") == cand.replace("_", "") or name == _k:
                    cn = name
                    break
        iso = name2iso.get(cn)
        if iso:
            pub["name_cn"] = cn
            out[iso] = pub
    return out


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
                    # C3F §十四：展示状态必须与实际渲染字段一致
                    it["title_cn_missing"] = False
                    merged += 1
                if v.get("summary_cn"):
                    it["summary_cn"] = v["summary_cn"]
                    it["summary_cn_missing"] = False
                break
    # 统一补 summary 状态字段（与 title 状态相互独立）
    for it in (doc.get("items") or []):
        it["summary_cn_missing"] = not bool((it.get("summary_cn") or "").strip())
        if (it.get("title_cn") or "").strip():
            it["title_cn_missing"] = False
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
    hp = ART.read_artifact(root, "homepage_analysis", "current")
    hp_pub = _public(hp)
    # C3F §五/§六：fact pack 一致性契约。
    # 前端只有在 AI.status=FULL 且 fact_pack_hash 与当前确定性 fact pack 一致时才展示 AI。
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "ai"))
        import c3_analysis as _A
        _pack = _A.build_homepage_fact_pack_from_views(root)
        # 一致性契约使用稳定投影（剔除滚动窗口等墙钟敏感字段）
        cur_hash = _A.pack_hash(_A.stable_pack_projection(_pack))
    except Exception:  # noqa: BLE001
        cur_hash = None
    if hp_pub is not None:
        hp_pub["fact_pack_hash"] = hp.get("fact_pack_hash")
        hp_pub["fact_pack_version"] = hp.get("fact_pack_version")
        hp_pub["ai_matches_current_fact_pack"] = bool(
            cur_hash and hp.get("fact_pack_hash") == cur_hash)

    _, name2iso, _ = _iso3_name_map(root)
    doc = {"schema": "ai-intelligence-view-v1",
           "generated_at": None, "data_as_of": None,
           "homepage_fact_pack_hash": cur_hash,
           "homepage": hp_pub,
           "country_index": country_index_by_iso3(root),
           "country_name_to_iso3": name2iso,
           "country_analysis": {}, "event_analysis": {}}
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
