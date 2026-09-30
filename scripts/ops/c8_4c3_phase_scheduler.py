"""C8-4C3：全局相位调度（两趟预跑）+ 相位遥测 + 墙钟 3000s。

问题（生产实测）：主循环是「国家外层循环 + 各国内部排序」，于是早期国家（如乍得 64 源）
的普通源会把墙钟耗尽，导致**后期国家的 Lane A 完全没跑**（8 个 Lane A 源零执行）。
优先源自身耗时已达 1119s（本轮总 1475s），在 2400s 预算下几乎没有余量。

修复（最小、不重写架构）：
  PASS A（全局相位 0/1/2）：只执行 P0 尼日尔保证键、P1 保证核心键、既有 Lane A 键；
  PASS B（全局相位 3/4）：执行其余全部键。
  用 (country, source_id) 作为执行键去重，**绝不重复执行同一键**。
  墙钟 2400 -> 3000（+25%，只此一次，为 C8-4D 留证据）。
"""
import ast
import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE3 = ROOT / "scripts" / "stage3_collect_v2.py"
WF = ROOT / ".github" / "workflows" / "asip-production-collection.yml"


def patch_signature(s):
    old = "def run_country_pipeline(country_cn, registry, discoverer, dry=False, fresh=False, max_items=0, run_id=\"\"):"
    new = ("def run_country_pipeline(country_cn, registry, discoverer, dry=False, fresh=False, max_items=0,\n"
           "                       run_id=\"\", only_sids=None):")
    assert s.count(old) == 1, "signature"
    return s.replace(old, new, 1)


def patch_source_filter(s):
    old = """    sources = registry.by_country(country_cn)"""
    new = """    sources = registry.by_country(country_cn)
    # C8-4C3：仅执行指定执行键（用于全局相位预跑；默认 None = 该国全部源）
    if only_sids is not None:
        _want = set(only_sids)
        sources = [x for x in sources if str(x.get("source_id")) in _want]
        if not sources:
            return [], [], []"""
    assert s.count(old) == 1, "source filter"
    return s.replace(old, new, 1)


def patch_main(s):
    old = """    for cn in countries:
        arts, ps, errs = run_country_pipeline(cn, registry, discoverer,
                                              dry=args.dry, fresh=args.fresh,
                                              max_items=args.max_items,
                                              run_id=run_id)"""
    new = """    # ── C8-4C3：全局相位调度（两趟）──────────────────────────────
    # PASS A = 相位 0/1/2（P0 尼日尔 → P1 保证核心 → 既有 Lane A）
    # PASS B = 相位 3/4（其余普通国家/本地 与 展开 pan/global/背景）
    # 执行键 = (country_cn, source_id)，去重后绝不重复执行。
    import time as _t
    _phase = {}
    for cn2 in countries:
        for src2 in registry.by_country(cn2):
            sid2 = str(src2.get("source_id"))
            if cn2 == P0_NIGER_COUNTRY and sid2 in P0_NIGER_IDS:
                ph = 0
            elif cn2 in P1_COUNTRIES_ORDER and sid2 in P1_GUARANTEED_IDS:
                ph = 1
            elif sid2 in LANE_A_IDS:
                ph = 2
            else:
                ph = 3 if len(shape_of(src2)) <= 2 else 4
            _phase[(cn2, sid2)] = ph
    done_keys = set()
    phase_stats = {p: {"executions": 0, "skipped": 0, "elapsed": 0.0} for p in range(5)}

    def _run_pass(phases):
        _arts, _ps, _errs = [], [], []
        for cn2 in countries:
            keys = [sid2 for (c2, sid2), p2 in _phase.items() if c2 == cn2 and p2 in phases
                    and (c2, sid2) not in done_keys]
            if not keys:
                continue
            _t0 = _t.time()
            a2, p2_, e2 = run_country_pipeline(cn2, registry, discoverer,
                                               dry=args.dry, fresh=args.fresh,
                                               max_items=args.max_items,
                                               run_id=run_id, only_sids=keys)
            elapsed = _t.time() - _t0
            ph_used = sorted({_phase[(cn2, k)] for k in keys})
            for _p in ph_used:
                phase_stats[_p]["elapsed"] += elapsed / max(1, len(ph_used))
                phase_stats[_p]["executions"] += 1
            for k2 in keys:
                done_keys.add((cn2, k2))
            _arts.extend(a2)
            _ps.extend(p2_)
            _errs.extend(e2)
        return _arts, _ps, _errs

    _a0, _p0s, _e0 = _run_pass({0, 1, 2})
    all_articles.extend(_a0)
    per_source.extend(_p0s)
    all_errors.extend(_e0)
    _a1, _p1s, _e1 = _run_pass({3, 4})
    all_articles.extend(_a1)
    per_source.extend(_p1s)
    all_errors.extend(_e1)
    for _ps2 in list(_p0s) + list(_p1s):
        if str(_ps2.get("status")) == "skipped_wall_clock":
            _k = (_ps2.get("country"), str(_ps2.get("source_id")))
            _ph = _phase.get(_k)
            if _ph is not None:
                phase_stats[_ph]["skipped"] += 1
    for _cn3 in countries:
        for _k3, _p3 in _phase.items():
            if _k3[0] == _cn3 and _k3 not in done_keys:
                phase_stats[_p3]["skipped"] += 1

    for _cn in countries:
        arts, ps, errs = [], [], []"""
    assert s.count(old) == 1, "main loop"
    s = s.replace(old, new, 1)
    # 追尾：把旧的 per-country 调用体清空（保留 persistence 之后的逻辑）
    old_call = """        arts, ps, errs = run_country_pipeline(cn, registry, discoverer,
                                              dry=args.dry, fresh=args.fresh,
                                              max_items=args.max_items,
                                              run_id=run_id)
        all_articles.extend(arts)
        per_source.extend(ps)
        all_errors.extend(errs)"""
    new_call = """        if not arts and not ps:
            continue
        all_articles.extend(arts)
        per_source.extend(ps)
        all_errors.extend(errs)"""
    assert s.count(old_call) == 1, "old call body"
    s = s.replace(old_call, new_call, 1)
    return s


def patch_totals(s):
    old = """    totals["OTHER_SOURCE_ITEMS_SKIPPED"] = _osa"""
    new = """    # C8-4C3：相位遥测（内部指标，不影响公开 UI）
    try:
        for _p in range(5):
            totals["PHASE%d_EXECUTIONS" % _p] = phase_stats[_p]["executions"]
            totals["PHASE%d_SKIPPED_WALL_CLOCK" % _p] = phase_stats[_p]["skipped"]
            totals["PHASE%d_ELAPSED_SECONDS" % _p] = round(phase_stats[_p]["elapsed"], 1)
    except NameError:
        pass
    totals["OTHER_SOURCE_ITEMS_SKIPPED"] = _osa"""
    assert s.count(old) == 1, "totals"
    return s.replace(old, new, 1)


def patch_shape_helper(s):
    if "def shape_of(" in s:
        return s
    helper = '''def shape_of(src):
    """C8-4C3：源的 country_scope 展开数（用于相位 3/4 判定）。"""
    v = src.get("country_scope")
    return v if isinstance(v, list) else ([v] if v else [])


'''
    anchor = "def _p1_core_first(sources, country_cn):"
    assert s.count(anchor) == 1
    return s.replace(anchor, helper + anchor, 1)


def main():
    s = io.open(STAGE3, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    if "C8-4C3：全局相位调度" in s:
        print("stage3 已含 C8-4C3，跳过")
    else:
        s = patch_shape_helper(s)
        s = patch_signature(s)
        s = patch_source_filter(s)
        s = patch_main(s)
        s = patch_totals(s)
        io.open(STAGE3, "w", encoding="utf-8", newline="").write(s.replace("\n", "\r\n"))
        ast.parse(s)
        print("stage3 已打入 C8-4C3 全局相位调度 ✓")
    # 墙钟 2400 -> 3000
    w = io.open(WF, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    before = re.findall(r"--wall-clock-limit\s+(\d+)", w)
    w2 = re.sub(r"--wall-clock-limit\s+2400", "--wall-clock-limit 3000", w)
    if w2 != w:
        io.open(WF, "w", encoding="utf-8", newline="").write(w2.replace("\n", "\r\n"))
    after = re.findall(r"--wall-clock-limit\s+(\d+)", w2)
    print("workflow wall-clock-limit:", before, "->", after)


if __name__ == "__main__":
    main()
