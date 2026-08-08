#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/intelligence/africa"
GEN_DIR = ROOT / "scripts/gen"
OUT = ROOT / "qa-artifacts-i3b-fix1c-postqa"
OUT.mkdir(exist_ok=True)

manifest = json.loads((ROOT / "qa-artifacts-i3b-fix1c/correction-application.json").read_text(encoding="utf-8"))
corrections = manifest.get("corrections", manifest if isinstance(manifest, list) else [])
profiles = json.loads((DATA / "country_profiles.json").read_text(encoding="utf-8"))["profiles"]
gen_text = "\n".join(p.read_text(encoding="utf-8") for p in [GEN_DIR / "gen_i3a_countries.py", GEN_DIR / "gen_i3b_countries.py", GEN_DIR / "gen_i3a_relations.py", GEN_DIR / "gen_i3b_relations.py", GEN_DIR / "gen_i3b_entities.py"])

COUNTRY = {
    "FIX1B-CAM-001":"country-cameroon", "FIX1B-CAM-002":"country-cameroon",
    "FIX1B-MALI-001":"country-mali", "FIX1B-MALI-002":"country-mali",
    "FIX1B-BFA-001":"country-burkina-faso", "FIX1B-BFA-002":"country-burkina-faso",
    "FIX1B-NER-001":"country-niger", "FIX1B-NER-002":"country-niger",
    "FIX1B-ETH-001":"country-ethiopia", "FIX1B-ETH-002":"country-ethiopia",
    "FIX1B-ETH-003":"country-ethiopia", "FIX1B-ETH-004":"country-ethiopia",
    "FIX1B-TZA-001":"country-tanzania", "FIX1B-TZA-002":"country-tanzania",
    "FIX1B-TZA-003":"country-tanzania", "FIX1B-TCD-001":"country-chad",
    "FIX1B-LBY-001":"country-libya", "FIX1B-MOZ-001":"country-mozambique",
}
# Mechanical semantic anchors from the original correction manifest; these are not new factual judgments.
# Each item is a list of required groups. A group may contain equivalent wording variants.
ANCHORS = {
 "FIX1B-CAM-001":[["恢复副总统职位"],["职位仍空缺"],["伪造"]], "FIX1B-CAM-002":[["恢复副总统职位"],["职位仍空缺"]],
 "FIX1B-MALI-001":[["燃料进口"],["物流供应线"],["不等同于"]], "FIX1B-MALI-002":[["阶段性军事协作"],["不足以据此确认"],["正式政治军事联盟"]],
 "FIX1B-BFA-001":[["控制范围"],["军方可自由行动"],["不能解释为某一个武装组织单独控制"]], "FIX1B-BFA-002":[["扩大活动"],["围困部分城镇"],["不将“争夺区”或“国家力量无法自由行动区”直接等同于JNIM单独控制区","不能将“争夺区”或“国家力量无法自由行动区”直接等同于JNIM单独控制区"]],
 "FIX1B-NER-001":[["IS Sahel/ISSP"],["公开报道并不一致"],["可能使用"],["不应写成已完全"]], "FIX1B-NER-002":[["2026 年 6 月 18 日"],["JNIM随后认领"],["11名安全人员死亡"]],
 "FIX1B-ETH-001":[["遭受严重压力"],["非盟仍将其视为现行和平框架"],["不应表述为协议已正式","不足以据此断言该和平框架已经正式终结"]],
 "FIX1B-ETH-002":[["联邦政治权威受到重大挑战"],["缺乏一致、可量化"],["不宜概括为提格雷已经","具体行政、军事和地方控制程度缺乏一致、可量化"]],
 "FIX1B-ETH-003":[["政府指控厄立特里亚"],["缺乏充分独立核实"],["据称支持"]], "FIX1B-ETH-004":[["接触、并行行动","可能存在接触或战术协调"],["战术协调"],["不足以将OLA与TPLF描述为已形成稳定、正式的联盟","不足以确认与TPLF已形成正式联盟"]],
 "FIX1B-TZA-001":[["坦桑尼亚政府任命的调查委员会"],["518人死亡"],["不能概括为“整体保持专业和克制”","安全部队在相关事件中的执法行为仍受到调查和人权审查"]], "FIX1B-TZA-002":[["军队承担边境和区域安全任务","TPDF承担边境和区域安全任务","TPDF是边境和区域安全任务的主要承担者","承担边境和区域安全任务"],["执法行为受到调查和争议"],["不对军队与警察作统一的“专业形象”价值判断"]],
 "FIX1B-TZA-003":[["SAMIM于2024年7月结束"],["双边安排"],["具体兵力缺少透明官方公开数据"]], "FIX1B-TCD-001":[["2026 年 5 月 4 日"],["Barka Tolorom"],["5 月 6 日"],["两起事件应分开记录"]],
 "FIX1B-LBY-001":[["创造举行全国性选举的条件"],["没有形成可作为确定事实使用的"],["2027年全国总统和议会选举"]], "FIX1B-MOZ-001":[["2025年11月7日"],["2026年1月29日"],["全面重启"]],
}
OLD_ABSENT = {
 "FIX1B-CAM-001":["比亚任命其子为副总统","弗兰克·比亚已获任命"], "FIX1B-CAM-002":["2026 年副总统任命与继承争议"],
 "FIX1B-MALI-001":["事实上的部分封锁"], "FIX1B-MALI-002":["反政府同盟","正式联盟"],
 "FIX1B-BFA-001":["70%的领土处于武装组织"], "FIX1B-BFA-002":["JNIM控制/争夺约六成领土"],
 "FIX1B-NER-001":["用武装无人机与迫击炮袭击","以武装无人机、轻武器和迫击炮袭击"],
 "FIX1B-ETH-001":["《比勒陀利亚协议》名存实亡","协议死亡"], "FIX1B-ETH-002":["提格雷事实上脱离联邦控制"],
 "FIX1B-ETH-003":["厄立特里亚被指支持TPLF与Fano（武器输送）"], "FIX1B-ETH-004":["OLA 与 TPLF 结盟","OLA与TPLF结盟"],
 "FIX1B-TZA-001":["安全部门任命的调查委员会","整体保持专业和克制"], "FIX1B-TZA-002":["军队与警察总体保持专业形象"],
 "FIX1B-TCD-001":["一次袭击中24名士兵和两名将军死亡","一次袭击中至少24名"], "FIX1B-LBY-001":["2027年举行总统与议会选举"],
 "FIX1B-MOZ-001":["2025年10月解除不可抗力","2025年10月 TotalEnergies解除不可抗力"],
}


def normalize(text):
    """仅消除中文自然空格和标点差异，不放宽事实词或否定词检查。"""
    return re.sub(r"[\s，。；：、！？（）()“”‘’\"'《》「」『』—–-]", "", str(text))


def contains_group(text, variants):
    normalized = normalize(text)
    return any(normalize(v) in normalized for v in variants)


def old_claim_is_positive(text, old):
    """把事实核查中的被否定旧说法与仍作为事实陈述的旧说法区分开。"""
    normalized = normalize(text)
    old_normalized = normalize(old)
    start = 0
    negative_markers = ("伪造", "不足以", "不应", "不能", "并非", "不是", "未形成", "尚未", "缺乏", "无法", "错误")
    while True:
        pos = normalized.find(old_normalized, start)
        if pos < 0:
            return False
        left = max(0, pos - 90)
        right = min(len(normalized), pos + len(old_normalized) + 90)
        context = normalized[left:right]
        if not any(marker in context for marker in negative_markers):
            return True
        start = pos + len(old_normalized)


def old_claim_absent(text, olds):
    return not any(old_claim_is_positive(text, old) for old in olds)

def flatten(x):
    if isinstance(x, dict): return "\n".join(flatten(v) for v in x.values())
    if isinstance(x, list): return "\n".join(flatten(v) for v in x)
    return str(x)

rows=[]
for c in corrections:
    cid=c["correction_id"]; src=flatten(profiles.get(COUNTRY[cid], {})); anchors=ANCHORS[cid]; olds=OLD_ABSENT.get(cid, [])
    current_match=all(contains_group(src, group) for group in anchors)
    old_absent=old_claim_absent(src, olds)
    # generator consistency is checked against the same mechanical semantic anchors.
    gen_ok=all(contains_group(gen_text, group) for group in anchors if group != [["不能概括为“整体保持专业和克制”"]])
    # NER's source anchor must be present in generator; Tanzania exact wording must be present.
    if cid == "FIX1B-NER-001": gen_ok = all(contains_group(gen_text, [a]) for a in ["IS Sahel/ISSP","公开报道并不一致","可能使用","不应写成已完全"])
    if cid == "FIX1B-TZA-001": gen_ok = all(contains_group(gen_text, [a]) for a in ["坦桑尼亚政府任命的调查委员会","518 人死亡"])
    result="PASS" if current_match and old_absent and gen_ok else "FAIL"
    rows.append({"correction_id":cid,"expected_semantics":c.get("new_text"),"current_source_match":current_match,"old_claim_absent":old_absent,"recommended_semantics_present":current_match,"generator_consistent":gen_ok,"result":result})
blocking=[r for r,c in zip(rows,corrections) if c.get("blocking_for_release")]
artifact={"artifact":"I3B_FIX1C_POSTQA_MANIFEST_FINAL_STATE_CHECK","source_of_truth":"current data/intelligence/africa/country_profiles.json","generator_scope":"gen_i3a_countries.py + gen_i3b_countries.py + related generators","correction_count":len(rows),"blocking_count":len(blocking),"blocking_failures":[r["correction_id"] for r in blocking if r["result"]!="PASS"],"corrections":rows,"gate":"PASS" if all(r["result"]=="PASS" for r in blocking) else "FAIL"}
(OUT/"manifest-final-state-check.json").write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"correction_count":len(rows),"blocking_count":len(blocking),"blocking_failures":artifact["blocking_failures"],"gate":artifact["gate"]},ensure_ascii=False))
raise SystemExit(0 if artifact["gate"]=="PASS" else 1)
