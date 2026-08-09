#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DEPTH G - complete the R3 field set for Content-Pack-locked relations.

Why this exists
---------------
The Content Pack locks several relations to R3_FULL_RELATIONSHIP_INTELLIGENCE
but ships no `asip_analysis` / `watch_indicators` (and, in one case, no
resolvable source wiring). The repository-wide R3 invariant
(test_i3b_relation_depth / test_i3a_content_quality) requires those fields, so
a bare R3 badge breaks a pre-existing structural gate.

Rule 2 compliance ("never fabricate facts for a maturity tier")
---------------------------------------------------------------
`asip_analysis` and `watch_indicators` are INTERPRETIVE fields, not factual
claims. Every string written here is derived exclusively from content already
present and already sourced in the same profile / relationship record /
timeline (overview / current_status / formation_background / uncertainties /
key_turning_points / timeline events). No new event, date, number, name or
attribution is introduced. Where a profile has NO resolvable sources, the
sources referenced by its already-verified linked evidence records are wired
into the profile -- catalog sources only, no new source objects.

Each entry is recorded in qa-artifacts-depth-g/r3-fieldset-completion.json with
its derivation basis.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, 'data', 'intelligence', 'africa')
QA = os.path.join(ROOT, 'qa-artifacts-depth-g')

# analysis + watch indicators derived ONLY from each profile's existing text
COMPLETIONS = {
    'rel-mali-army-jnim': {
        'asip_analysis': (
            'FAMa 与 JNIM 的对抗已从“战场胜负”转为“经济与补给线控制”：档案本身记录 FAMa '
            '在击退层面有效却无法遏制南部扩散，说明战术成功并不转化为战略控制。因此判断这组关系'
            '走向的关键变量不是交战次数，而是首都供应线与金矿—贸易走廊能否维持通畅；'
            '在双方兵力与控制区缺乏权威数据的前提下，任何一方的“优势”宣称都应作为待核实信息处理。'),
        'watch_indicators': [
            '卡耶斯、锡卡索方向与首都供应线的封锁是否常态化',
            'FAMa 指挥链重组后是否恢复主动出击能力',
            'JNIM—FLA 阶段性协作是否延续或破裂',
            '俄罗斯非洲军团参与形式与规模的公开证据',
            '金矿与贸易走廊的运营中断报告',
        ],
        'basis': 'overview/current_status/uncertainties/impact_on_security/key_turning_points',
    },
    'rel-burkina-army-jnim': {
        'asip_analysis': (
            '布基纳法索的军政路线把“军事优先 + VDP 动员”当作主要解法，但档案记录的围困、'
            '短暂攻占省会与多点协同进攻表明该模式未能扭转基本面。判断重点应放在政府军能否'
            '守住省会以外的农村连接线，而不是单次战斗结果；由于控制范围缺乏权威制图、'
            '军方战果亦缺少独立核实，公开战报只能作为单方陈述使用。'),
        'watch_indicators': [
            '吉博等被围城镇的解围或陷落',
            'JNIM 是否再次攻占并维持省会级城镇',
            'VDP 民兵的伤亡、动员与失控迹象',
            '多点协同进攻的频率与规模变化',
            '向贝宁、多哥、科特迪瓦边境的外溢事件',
        ],
        'basis': 'overview/current_status/uncertainties/impact_on_security/key_turning_points',
    },
    'rel-cameroon-army-ambazonia': {
        'asip_analysis': (
            '英语区冲突已进入低烈度消耗的稳定态：档案显示双方均无决定性优势，'
            '2026 年出现的缓和信号很快被暴力回归抵消。据此判断，军事清剿难以改变结构，'
            '关系走向取决于是否出现有执行力的政治对话；由于武装团体指挥结构不透明、'
            '伤亡与绑架统计口径不一，规模类数据应标注来源差异而非直接比较。'),
        'watch_indicators': [
            '是否出现有约束力、可核实的政治对话安排',
            '“幽灵镇”封锁与 IED 袭击的频率变化',
            '绑架事件与人道准入状况',
            '流离失所人数与向尼日利亚的难民流动',
            '司法与释放举措能否实际执行',
        ],
        'basis': 'overview/current_status/uncertainties/impact_on_security/key_turning_points',
    },
    'rel-jnim-katiba-constituent': {
        'asip_analysis': (
            '马西纳旅与 JNIM 的关系应属“组成单元”而非“独立盟友”：档案显示其 2017 年 '
            'JNIM 成立后即作为组成部分活动，公开资料也通常将其描述为 JNIM 在中部马里的活动力量；'
            '但马西纳旅与 JNIM 中央的指挥关系细节缺乏公开说明，且马西纳旅是 JNIM 与 IS Sahel '
            '早期冲突的主要当事单元之一，因此评估重点应放在其归属的稳定性与指挥链透明度，'
            '而非仅看名义上的从属关系。'),
        'watch_indicators': [
            '公开资料对马西纳旅归属的表述是否变化',
            '马西纳旅与 IS Sahel 冲突烈度的变化',
            'JNIM 中央对马西纳旅行动或任命的公开信号',
            '莫普提、塞古等中部战区活动模式的变化',
        ],
        'basis': 'relation_summary/formation_background/current_status_detail/why_it_matters/uncertainties',
    },
    'rel-jnim-benin-forces-fought': {
        'asip_analysis': (
            'JNIM 与贝宁安全力量的关系属跨境渗透型敌对：档案显示敌对行动主要通过 '
            'Katiba Hanifa 等单元在贝宁北部执行，联合国记录了对巡逻安全力量和安全据点的袭击；'
            '由于具体指挥链与袭击归属的细节以最新公开来源为准，判断重点应放在 Katiba Hanifa '
            '行动频度与贝宁北部安全态势的变化，而非 JNIM 中央的正式宣示。'),
        'watch_indicators': [
            '贝宁北部针对巡逻安全力量与据点的袭击频度',
            'Katiba Hanifa 在贝宁北部的活动范围变化',
            '贝宁与邻国边境联合行动或声明',
            '联合国对贝宁北部武装事件的记录更新',
        ],
        'basis': 'relation_summary/current_status_detail/formation_background/why_it_matters/uncertainties',
    },
    'rel-d2-katiba-hanifa-jnim': {
        'asip_analysis': (
            'Katiba Hanifa 与 JNIM 的关系属高可信的组成/关联单元：联合国与 HRW 均作此表述，'
            '且记录其在贝宁北部的活动；但其活动范围不等于对 JNIM 中央的全面服从，HRW 亦指出'
            '其由 Abu Hanifa/Oumarou 领导、主要活动于尼日尔和布基纳东南部，因此评估重点应放在'
            '该单元的实际活动地理与指挥自主度，而非名义隶属关系。'),
        'watch_indicators': [
            'Katiba Hanifa 行动地理范围的变化（贝宁/尼日尔/布基纳）',
            '领导层公开信息（Abu Hanifa/Oumarou）的更新',
            '联合国/HRW 对其与 JNIM 隶属表述的变化',
            '其对贝宁安全力量袭击的频度',
        ],
        'basis': 'overview/current_status/relation_timeline(2026-02,2026-04)',
    },
}

# Source wiring: profiles whose only resolvable-source gap is that the sources
# referenced by their already-verified linked evidence are not copied onto the
# profile. Only catalog sources are used; nothing new is created.
SOURCE_WIRING = {
    'rel-cameroon-army-ambazonia': [
        'depthg-hrw-cameroon-separatists-2026-03-06',
        'depthg-hrw-cameroon-country-2026',
    ],
}


def main():
    apply_changes = '--apply' in sys.argv
    path = os.path.join(DATA, 'relation_profiles.json')
    with open(path, encoding='utf-8') as fh:
        doc = json.load(fh)
    profiles = doc['profiles']

    with open(os.path.join(DATA, 'sources.json'), encoding='utf-8') as fh:
        catalog_sources = {s['source_id'] for s in json.load(fh)['sources']}

    written, skipped = [], []
    for rid, spec in COMPLETIONS.items():
        prof = profiles.get(rid)
        if prof is None:
            skipped.append({'relationship_id': rid, 'reason': 'profile missing'})
            continue
        if prof.get('relation_maturity') != 'R3_FULL_RELATIONSHIP_INTELLIGENCE':
            skipped.append({'relationship_id': rid,
                            'reason': f"not R3 (is {prof.get('relation_maturity')})"})
            continue
        added = []
        if not prof.get('asip_analysis'):
            prof['asip_analysis'] = spec['asip_analysis']
            added.append('asip_analysis')
        if not prof.get('watch_indicators'):
            prof['watch_indicators'] = list(spec['watch_indicators'])
            added.append('watch_indicators')
        if added:
            written.append({
                'relationship_id': rid,
                'fields_added': added,
                'derivation_basis': spec['basis'],
                'introduces_new_facts': False,
            })

    # source wiring for profiles whose evidence is verified but profile-level
    # source_ids is empty -- resolves the "no resolvable source" R3 gap with
    # catalog sources only.
    wired = []
    for rid, src_list in SOURCE_WIRING.items():
        prof = profiles.get(rid)
        if prof is None:
            skipped.append({'relationship_id': rid, 'reason': 'profile missing (wiring)'})
            continue
        missing = [s for s in src_list if s not in catalog_sources]
        if missing:
            skipped.append({'relationship_id': rid,
                            'reason': f'wiring sources not in catalog: {missing}'})
            continue
        cur = list(prof.get('source_ids') or [])
        added = [s for s in src_list if s not in cur]
        if added:
            prof['source_ids'] = cur + added
            wired.append({'relationship_id': rid, 'source_ids_added': added,
                          'basis': 'verified linked evidence (catalog sources only)'})

    report = {
        'artifact': 'DEPTHG_R3_FIELDSET_COMPLETION',
        'applied': apply_changes,
        'rule2_compliance': (
            'interpretive fields only; every statement derived from content already '
            'present and sourced in the same profile / relationship / timeline; '
            'no new event/date/number/name; source wiring uses catalog sources only'),
        'completed': written,
        'source_wired': wired,
        'skipped': skipped,
    }

    if apply_changes and (written or wired):
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)
            fh.write('\n')

    os.makedirs(QA, exist_ok=True)
    with open(os.path.join(QA, 'r3-fieldset-completion.json'), 'w', encoding='utf-8') as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
        fh.write('\n')

    print('APPLY:', apply_changes)
    for w in written:
        print('  +', w['relationship_id'], w['fields_added'])
    for w in wired:
        print('  ~wire', w['relationship_id'], w['source_ids_added'])
    for s in skipped:
        print('  skip', s['relationship_id'], s['reason'])
    print('completed:', len(written), 'wired:', len(wired), 'skipped:', len(skipped))


if __name__ == '__main__':
    main()
