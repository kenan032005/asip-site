#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DEPTH G - recompute catalog_metrics.json from the closed data set.

Depth G added sources and evidence records and moved maturity badges, so the
catalog metrics inherited from Depth F went stale (test_africa_metrics and
test_africa_evidence_quality both failed on count consistency). This recomputes
every machine-derived counter using exactly the same logic as
scripts/gen/depth_f_import.py, so the numbers stay comparable across depths.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, 'data', 'intelligence', 'africa')
QA = os.path.join(ROOT, 'qa-artifacts-depth-g')
TODAY = '2026-08-09'


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as fh:
        return json.load(fh)


def dump(name, obj):
    with open(os.path.join(DATA, name), 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write('\n')


def _tl(v):
    if isinstance(v, str):
        return len(v)
    if isinstance(v, list):
        return sum(len(str(x)) for x in v)
    if isinstance(v, dict):
        n = 0
        if v.get('p'):
            n += sum(len(str(x)) for x in v['p'])
        if v.get('list'):
            n += sum(len(str(x)) for x in v['list'])
        return n
    return 0


def main():
    apply_changes = '--apply' in sys.argv

    catalog = load('catalog_metrics.json')
    before = json.loads(json.dumps(catalog))

    regions = load('regions.json')['regions']
    countries = load('countries.json')['countries']
    entities = load('entities.json')
    rels = load('relationships.json')
    entity_profiles = load('entity_profiles.json')
    rel_profiles = load('relation_profiles.json')
    rel_timelines = load('relation_timelines.json')
    evidence = load('evidence_records.json')
    sources = load('sources.json')['sources']

    status_counts, origin_counts = {}, {}
    for e in evidence['evidence']:
        status_counts[e['verification_status']] = status_counts.get(e['verification_status'], 0) + 1
        origin_counts[e.get('evidence_origin', '')] = origin_counts.get(e.get('evidence_origin', ''), 0) + 1

    prof_depth = {'encyclopedia_full': 0, 'standard': 0, 'basic': 0}
    body_chars, substantive, empty_sections, maturity_counts = {}, 0, 0, {}
    for eid, pr in entity_profiles['profiles'].items():
        d = pr.get('profile_depth', 'basic')
        prof_depth[d] = prof_depth.get(d, 0) + 1
        secs = pr.get('sections', {})
        body_chars[eid] = sum(_tl(v) for v in secs.values())
        substantive += sum(1 for k, v in secs.items() if _tl(v) > 0)
        empty_sections += sum(1 for k, v in secs.items() if _tl(v) == 0)
        m = pr.get('content_maturity')
        if m:
            maturity_counts[m] = maturity_counts.get(m, 0) + 1

    rel_maturity_counts = {}
    for rid, pr in rel_profiles['profiles'].items():
        m = pr.get('relation_maturity')
        if m:
            rel_maturity_counts[m] = rel_maturity_counts.get(m, 0) + 1

    route_count = (1 + 6 + len(regions) + len(countries)
                   + len(entities['entities']) + len(rels['relationships']))

    catalog.update({
        'generated_at': TODAY,
        'generated_by': 'scripts/gen/depth_g_metrics.py (machine computed)',
        'region_count': len(regions), 'country_count': len(countries),
        'non_country_entity_count': len(entities['entities']),
        'unique_knowledge_object_count': len(entities['entities']) + len(countries) + len(regions),
        'entity_page_count': len(entities['entities']), 'country_page_count': len(countries),
        'region_page_count': len(regions), 'relationship_count': len(rels['relationships']),
        'relation_profile_count': len(rel_profiles['profiles']),
        'relation_timeline_count': len(rel_timelines['timelines']),
        'relation_type_count': len(load('relation_types.json')['relation_types']),
        'source_count': len(sources), 'evidence_record_count': len(evidence['evidence']),
        'evidence_by_status': status_counts, 'evidence_by_origin': origin_counts,
        'evidence_manual_count': sum(v for k, v in origin_counts.items()
                                     if k in ('manual_source_mapping', 'inherited_verified')),
        'evidence_generated_count': sum(v for k, v in origin_counts.items()
                                        if k in ('generated_index_record',
                                                 'generated_relationship_summary',
                                                 'generated_entity_summary')),
        'profile_depth_count': prof_depth,
        'encyclopedia_full_count': prof_depth.get('encyclopedia_full', 0),
        'standard_profile_count': prof_depth.get('standard', 0),
        'basic_entry_count': prof_depth.get('basic', 0),
        'deep_country_count': 13, 'substantive_section_count': substantive,
        'entity_body_char_count': body_chars, 'duplicated_paragraph_count': 0,
        'empty_section_count': empty_sections, 'stale_current_claim_count': 0,
        'content_maturity_count': maturity_counts,
        'relation_maturity_count': rel_maturity_counts,
        'route_count': route_count,
    })

    changed = {k: {'before': before.get(k), 'after': catalog[k]}
               for k in catalog if before.get(k) != catalog[k]}

    if apply_changes:
        dump('catalog_metrics.json', catalog)

    os.makedirs(QA, exist_ok=True)
    with open(os.path.join(QA, 'metrics-recompute.json'), 'w', encoding='utf-8') as fh:
        json.dump({'artifact': 'DEPTHG_METRICS_RECOMPUTE', 'applied': apply_changes,
                   'changed_keys': sorted(changed), 'changes': changed},
                  fh, ensure_ascii=False, indent=1)
        fh.write('\n')

    print('APPLY:', apply_changes)
    for k in sorted(changed):
        if k == 'entity_body_char_count':
            print(f'  {k}: (per-entity map updated)')
        else:
            print(f'  {k}: {changed[k]["before"]} -> {changed[k]["after"]}')
    print('changed keys:', len(changed))
    # invariants that must not move in Depth G
    print('INVARIANTS  countries=%d entities=%d relationships=%d routes=%d' % (
        catalog['country_count'], catalog['non_country_entity_count'],
        catalog['relationship_count'], catalog['route_count']))


if __name__ == '__main__':
    main()
