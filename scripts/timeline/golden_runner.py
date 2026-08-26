#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6B — Golden Set 评估器（§二十一 Social 16 / §二十二 Disease 12）。

对每组 fixture 运行引擎，按 expected 断言 update_types / current_state /
conflict flags / outbreak identity。全部 28 组 PASS 才算 Golden Set 通过。
"""

import json
import sys

from scripts.timeline.social import new_timeline, apply_update
from scripts.timeline.disease import (new_outbreak_timeline, apply_disease_event,
                                      build_outbreak_timelines, _same_outbreak)
from scripts.timeline.golden import build_social_pairs, build_disease_pairs


def run_social(pairs):
    results = []
    for pid, articles, expected in pairs:
        # S15/S16：同 canonical_url 或同 URL 的重复稿不得形成 update（§二十一 #15）
        seen_url = set()
        arts = []
        for a in articles:
            key = a.get("canonical_url") or a.get("url")
            if key in seen_url:
                continue
            seen_url.add(key)
            arts.append(a)
        tl = new_timeline("ME_" + pid, arts[0])
        utypes = [tl["updates"][0]["update_type"]]
        for a in arts[1:]:
            tl, upd, flags = apply_update(tl, a)
            utypes.append(upd["update_type"])
        exp_types = expected["update_types"]
        # S15/S16 特殊断言（duplicate 不产生 update；syndicated 不增独立来源）
        if pid == "s15_duplicate_no_update":
            ok = (len(tl["updates"]) == 1 and tl["source_count"] == 1
                  and utypes == ["initial_report"])
        elif pid == "s16_syndicated_no_independent":
            ok = (tl["independent_source_count"] == 1 and utypes == exp_types)
        else:
            ok = utypes == exp_types
        # current_state 断言
        st = tl["current_state"]
        if expected.get("deaths") is not None:
            ok = ok and st.get("deaths") == expected["deaths"]
        if expected.get("responsible_party") is not None:
            ok = ok and st.get("responsible_party") == expected["responsible_party"]
        if expected.get("location") is not None:
            ok = ok and st.get("location") == expected["location"]
        if expected.get("official_confirmed") is not None:
            ok = ok and st.get("official_confirmed") == expected["official_confirmed"]
        if expected.get("status") is not None:
            ok = ok and tl["timeline_status"] == expected["status"]
        for f in expected.get("flags", []):
            ok = ok and f in tl["conflict_flags"]
        results.append((pid, "PASS" if ok else "FAIL",
                        {"update_types": utypes, "status": tl["timeline_status"],
                         "deaths": st.get("deaths"),
                         "responsible_party": st.get("responsible_party"),
                         "location": st.get("location"),
                         "official_confirmed": st.get("official_confirmed"),
                         "flags": tl["conflict_flags"],
                         "source_count": tl["source_count"],
                         "independent_source_count": tl["independent_source_count"]}))
    return results


def run_disease(pairs):
    results = []
    for pid, events, expected in pairs:
        if pid == "d11_2024_vs_2026_outbreak":
            # identity 判定：_same_outbreak=False → 独立 outbreak
            ok = not _same_outbreak(events[0], events[1])
            tls, _, _ = build_outbreak_timelines(events)
            ok = ok and len(tls) == 2
            results.append((pid, "PASS" if ok else "FAIL", {"outbreaks": len(tls)}))
            continue
        if len(events) == 1:
            # D12 single event：unknown 保持 unknown
            tl = new_outbreak_timeline(events[0])
            lc = tl["latest_counts"]
            ok = all(lc.get(k) is None for k in ("deaths", "confirmed_cases"))
            results.append((pid, "PASS" if ok else "FAIL", {"latest": lc}))
            continue
        # 链式构造：supersedes 指向上一事件
        tl = new_outbreak_timeline(events[0])
        utypes = [tl["updates"][0]["update_type"]]
        nconf = 0
        for e in events[1:]:
            tl, obs, conflicts = apply_disease_event(tl, e)
            utypes.append(obs["update_type"])
            nconf += len(conflicts)
        exp_types = expected["update_types"]
        ok = utypes == exp_types
        if expected.get("conflicts") is not None:
            ok = ok and nconf == expected["conflicts"]
        lc = tl["latest_counts"]
        for k, v in (expected.get("latest") or {}).items():
            ok = ok and lc.get(k) == v
        if expected.get("admin1") is not None:
            ok = ok and sorted(tl["affected_admin1"]) == sorted(expected["admin1"])
        if expected.get("affected_countries") is not None:
            ok = ok and sorted(tl["affected_countries"]) == sorted(expected["affected_countries"])
        if expected.get("outbreak_status") is not None:
            ok = ok and tl["outbreak_status"] == expected["outbreak_status"]
        results.append((pid, "PASS" if ok else "FAIL",
                        {"update_types": utypes, "latest": lc,
                         "conflicts": nconf, "status": tl["outbreak_status"]}))
    return results


def main():
    social = run_social(build_social_pairs())
    disease = run_disease(build_disease_pairs())
    fails = [r for r in social + disease if r[1] == "FAIL"]
    print("=== Social Golden (%d) ===" % len(social))
    for pid, verdict, detail in social:
        print("  %-38s %s" % (pid, verdict))
    print("=== Disease Golden (%d) ===" % len(disease))
    for pid, verdict, detail in disease:
        print("  %-38s %s" % (pid, verdict))
    print("TOTAL: %d/%d PASS" % (len(social) + len(disease) - len(fails),
                                 len(social) + len(disease)))
    if fails:
        print("FAILURES:")
        for pid, verdict, detail in fails:
            print("  -", pid, detail)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
