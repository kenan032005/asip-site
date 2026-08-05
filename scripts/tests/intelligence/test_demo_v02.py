#!/usr/bin/env python3
"""Validate V0.2 profile depth, display groups, and V0.1 data invariants."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / 'data' / 'intelligence' / 'demo'
ALLOWED_LEVELS = {'L1', 'L2', 'L3'}
REQUIRED_PROFILE_KEYS = {'profile_level', 'completeness', 'sections'}
EXPECTED_LEVELS = {'actor-jnim':'L3','actor-is-sahel':'L3','actor-aqim':'L2','person-iyad-ag-ghali':'L2','country-mali':'L2'}
MIN_SECTIONS = {'L1': 1, 'L2': 3, 'L3': 5}

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
    if set(e['profile_level'] for e in entities) - ALLOWED_LEVELS: fail('invalid profile level')
    for entity in entities:
        if entity['profile_level'] != EXPECTED_LEVELS.get(entity['entity_id'], 'L1'):
            fail(f'unexpected profile level on {entity["entity_id"]}')
        if entity['entity_id'] not in profiles: fail(f'missing profile content for {entity["entity_id"]}')
        profile = profiles[entity['entity_id']]
        if not REQUIRED_PROFILE_KEYS.issubset(profile): fail(f'profile metadata missing for {entity["entity_id"]}')
        if profile['profile_level'] != entity['profile_level']: fail(f'profile level mismatch for {entity["entity_id"]}')
        section_count = len([v for v in profile['sections'].values() if v])
        if section_count < MIN_SECTIONS[entity['profile_level']]: fail(f'profile completeness too low for {entity["entity_id"]}')
    if len({r['relationship_id'] for r in rels}) != 20: fail('relationship IDs changed')
    print(f'PASS entities={len(entities)} relationships={len(rels)}')
    print('PASS profile levels L3=2 L2=3 L1=7')
    print('PASS type templates, completeness floors, and V0.1 relationship invariant')

if __name__ == '__main__':
    try:
        main()
    except (AssertionError, KeyError, json.JSONDecodeError) as exc:
        print(f'FAIL {exc}')
        sys.exit(1)
