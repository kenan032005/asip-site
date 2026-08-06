#!/usr/bin/env python3
"""Validate V0.2 profile depth, importance levels, rings, and V0.1 data invariants (I1-A)."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / 'data' / 'intelligence' / 'demo'
ALLOWED_LEVELS = {'L1', 'L2', 'L3'}
ALLOWED_RINGS = {'inner', 'middle', 'outer'}
REQUIRED_PROFILE_KEYS = {'profile_level', 'completeness', 'sections'}
EXPECTED_IMPORTANCE = {'actor-jnim':'L1','actor-is-sahel':'L1','actor-aqim':'L2','person-iyad-ag-ghali':'L2','country-mali':'L2','actor-al-qaida':'L2','actor-ansar-eddine':'L3','actor-al-mourabitoun':'L3','actor-katiba-macina':'L3','person-amadou-koufa':'L3','country-burkina-faso':'L3','country-niger':'L3'}
MIN_SECTIONS = {'L1': 4, 'L2': 3, 'L3': 1}

def load(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))

def fail(msg):
    raise AssertionError(msg)

def main():
    entities = load('entities.json')['entities']
    rels = load('relationships.json')['relationships']
    profiles = load('profile_content.json')['profiles']
    if len(entities) != 12: fail(f'expected 12 entities, got {len(entities)}')
    if len(rels) != 20: fail(f'expected 20 relationships, got {len(rels)}')
    if set(e['importance_level'] for e in entities) - ALLOWED_LEVELS: fail('invalid importance level')
    if set(r['display_ring'] for r in rels) - ALLOWED_RINGS: fail('invalid display_ring value')
    for entity in entities:
        if entity['importance_level'] != EXPECTED_IMPORTANCE.get(entity['entity_id']):
            fail(f'unexpected importance_level on {entity["entity_id"]}')
        if entity['entity_id'] not in profiles: fail(f'missing profile content for {entity["entity_id"]}')
        profile = profiles[entity['entity_id']]
        if not REQUIRED_PROFILE_KEYS.issubset(profile): fail(f'profile metadata missing for {entity["entity_id"]}')
        section_count = len([v for v in profile['sections'].values() if v])
        if section_count < MIN_SECTIONS[entity['importance_level']]: fail(f'profile completeness too low for {entity["entity_id"]}')
    if len({r['relationship_id'] for r in rels}) != 20: fail('relationship IDs changed')
    print(f'PASS entities={len(entities)} relationships={len(rels)}')
    print('PASS importance levels L1=2 L2=4 L3=6 (independent from display_ring)')
    print('PASS ring values inner/middle/outer, profile completeness floors, and V0.1 relationship invariant')

if __name__ == '__main__':
    try:
        main()
    except (AssertionError, KeyError, json.JSONDecodeError) as exc:
        print(f'FAIL {exc}')
        sys.exit(1)
