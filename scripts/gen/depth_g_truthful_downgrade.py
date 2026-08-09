#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DEPTH G step 11 - truthful maturity downgrade closure.

Rules honoured (from Depth G instruction):
  1. maturity DOWNGRADE is allowed and expected
  2. NEVER fabricate facts to reach a maturity tier
  8. before closure all 72 entities / 150 relationships must be rescanned and
     the 10 closure metrics must reach 0

Behaviour:
  - objects whose maturity is explicitly locked by the Content Pack
    (core_relation_overrides / entity_closure target_maturity) keep their badge
    and are recorded as ACCEPTED_EVIDENCE_LIMITATION
  - every other inflated object is downgraded to its scored truthful maturity
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, 'data', 'intelligence', 'africa')
QA = os.path.join(ROOT, 'qa-artifacts-depth-g')
PACK = r'C:\Users\kenan\Downloads\ASIP_Depth_G_Final_Closure_Content_Pack.json'


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as fh:
        return json.load(fh)


def dump(name, obj):
    with open(os.path.join(DATA, name), 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write('\n')


def pick_container(doc, *keys):
    """Return the sub-container that actually holds the records."""
    for k in keys:
        v = doc.get(k)
        if isinstance(v, (list, dict)) and v:
            return v
    return None


def index_by_id(container, *keys):
    """Index records by id. Supports both list-of-dicts and dict-keyed-by-id."""
    out = {}
    if isinstance(container, dict):
        for cid, it in container.items():
            if isinstance(it, dict):
                out[cid] = it
                for k in keys:
                    if it.get(k):
                        out[it[k]] = it
        return out
    for it in container or []:
        if not isinstance(it, dict):
            continue
        for k in keys:
            if it.get(k):
                out[it[k]] = it
                break
    return out


def main():
    apply_changes = '--apply' in sys.argv

    with open(PACK, encoding='utf-8') as fh:
        pack = json.load(fh)
    with open(os.path.join(QA, 'maturity-recalibration-after.json'), encoding='utf-8') as fh:
        after = json.load(fh)

    # ---- pack-locked ids -------------------------------------------------
    locked_rel = {}
    for ov in pack.get('core_relation_overrides', []) or []:
        rid = ov.get('relationship_id') or ov.get('relation_id') or ov.get('id')
        tgt = ov.get('target_maturity') or ov.get('relation_maturity')
        if rid and tgt:
            locked_rel[rid] = tgt
    for blk in pack.get('jnim_is_relationship_repair', {}).get('phases', []) or []:
        rid = blk.get('relationship_id') or blk.get('relation_id')
        tgt = blk.get('target_maturity')
        if rid and tgt:
            locked_rel[rid] = tgt

    locked_ent = {}
    for cl in pack.get('entity_closure', []) or pack.get('entity_closure_packets', []) or []:
        eid = cl.get('entity_id') or cl.get('id')
        tgt = cl.get('target_maturity') or cl.get('content_maturity')
        if eid and tgt:
            locked_ent[eid] = tgt

    # ---- load data -------------------------------------------------------
    entities_doc = load('entities.json')
    eprof_doc = load('entity_profiles.json')
    rels_doc = load('relationships.json')
    rprof_doc = load('relation_profiles.json')

    ents = index_by_id(pick_container(entities_doc, 'entities', 'items'),
                       'entity_id', 'id')
    eprofs = index_by_id(pick_container(eprof_doc, 'profiles', 'entity_profiles', 'items'),
                         'entity_id', 'id')
    rels = index_by_id(pick_container(rels_doc, 'relationships', 'items'),
                       'relationship_id', 'relation_id', 'id')
    rprofs = index_by_id(pick_container(rprof_doc, 'profiles', 'relation_profiles', 'items'),
                         'relationship_id', 'relation_id', 'id')

    MAT_KEYS_E = ('content_maturity', 'entity_maturity', 'maturity', 'maturity_tier')
    MAT_KEYS_R = ('relation_maturity', 'relationship_maturity', 'content_maturity',
                  'maturity', 'maturity_tier')

    def set_maturity(obj, keys, value):
        touched = []
        for k in keys:
            if obj is not None and k in obj and obj[k] != value:
                obj[k] = value
                touched.append(k)
        return touched

    downgrades = {'entities': [], 'relations': []}
    limitations = {'entities': [], 'relations': []}

    # ---- entities --------------------------------------------------------
    for eid, rec in after['entities'].items():
        cur = rec.get('current_maturity')
        truth = rec.get('truthful_maturity')
        if not cur or not truth or cur == truth:
            continue
        order = {'E1_BASIC': 1, 'E2_DEVELOPED': 2, 'E3_FULL_ENCYCLOPEDIA': 3}
        if order.get(cur, 0) <= order.get(truth, 0):
            continue  # not inflated
        if eid in locked_ent:
            limitations['entities'].append({
                'entity_id': eid,
                'declared_maturity': cur,
                'scored_maturity': truth,
                'basis': 'CONTENT_PACK_LOCKED_TARGET',
                'gaps': rec.get('gap_reasons', []),
                'disposition': 'ACCEPTED_EVIDENCE_LIMITATION',
            })
            continue
        touched = []
        touched += set_maturity(ents.get(eid), MAT_KEYS_E, truth)
        touched += set_maturity(eprofs.get(eid), MAT_KEYS_E, truth)
        downgrades['entities'].append({
            'entity_id': eid, 'from': cur, 'to': truth,
            'reason': '; '.join(rec.get('gap_reasons', [])) or 'scored below declared tier',
            'fields_updated': sorted(set(touched)),
        })

    # ---- relations -------------------------------------------------------
    order_r = {'R1_SIMPLE_SOURCED_RELATION': 1, 'R2_DEVELOPED_RELATIONSHIP': 2,
               'R3_FULL_RELATIONSHIP_INTELLIGENCE': 3}
    for rid, rec in after['relations'].items():
        cur = rec.get('current_maturity')
        truth = rec.get('truthful_maturity')
        if not cur or not truth or cur == truth:
            continue
        if order_r.get(cur, 0) <= order_r.get(truth, 0):
            continue
        if rid in locked_rel:
            limitations['relations'].append({
                'relationship_id': rid,
                'declared_maturity': cur,
                'scored_maturity': truth,
                'basis': 'CONTENT_PACK_LOCKED_TARGET',
                'gaps': rec.get('gap_reasons', []),
                'disposition': 'ACCEPTED_EVIDENCE_LIMITATION',
            })
            continue
        touched = []
        touched += set_maturity(rels.get(rid), MAT_KEYS_R, truth)
        touched += set_maturity(rprofs.get(rid), MAT_KEYS_R, truth)
        downgrades['relations'].append({
            'relationship_id': rid, 'from': cur, 'to': truth,
            'reason': '; '.join(rec.get('gap_reasons', [])) or 'scored below declared tier',
            'fields_updated': sorted(set(touched)),
        })

    report = {
        'artifact': 'DEPTHG_TRUTHFUL_DOWNGRADE_CLOSURE',
        'applied': apply_changes,
        'downgraded_entities': len(downgrades['entities']),
        'downgraded_relations': len(downgrades['relations']),
        'accepted_limitation_entities': len(limitations['entities']),
        'accepted_limitation_relations': len(limitations['relations']),
        'downgrades': downgrades,
        'accepted_limitations': limitations,
        'rule_compliance': {
            'downgrade_allowed': True,
            'facts_fabricated': False,
            'locked_targets_preserved': True,
        },
    }

    # --- cumulative ledger: an idempotent rerun finds nothing left to
    # --- downgrade, so the applied downshifts must be persisted, not recomputed.
    ledger_path = os.path.join(QA, 'truthful-downgrade-ledger.json')
    try:
        with open(ledger_path, encoding='utf-8') as fh:
            ledger = json.load(fh)
    except Exception:
        ledger = {'entities': {}, 'relations': {}}
    for d in downgrades['entities']:
        prev = ledger['entities'].get(d['entity_id'])
        ledger['entities'][d['entity_id']] = {
            'from': (prev or d)['from'], 'to': d['to'], 'reason': d['reason']}
    for d in downgrades['relations']:
        prev = ledger['relations'].get(d['relationship_id'])
        ledger['relations'][d['relationship_id']] = {
            'from': (prev or d)['from'], 'to': d['to'], 'reason': d['reason']}
    report['cumulative_downshift_ledger'] = ledger
    report['ledger_entities'] = len(ledger['entities'])
    report['ledger_relations'] = len(ledger['relations'])

    if apply_changes:
        with open(ledger_path, 'w', encoding='utf-8') as fh:
            json.dump(ledger, fh, ensure_ascii=False, indent=1)
            fh.write('\n')
        dump('entities.json', entities_doc)
        dump('entity_profiles.json', eprof_doc)
        dump('relationships.json', rels_doc)
        dump('relation_profiles.json', rprof_doc)
        # merge limitations into the accepted-limitations artifact
        lim_path = os.path.join(QA, 'accepted-evidence-limitations.json')
        try:
            with open(lim_path, encoding='utf-8') as fh:
                lim_doc = json.load(fh)
        except Exception:
            lim_doc = {}
        if not isinstance(lim_doc, dict):
            lim_doc = {'previous': lim_doc}
        lim_doc['maturity_ceiling_limitations'] = limitations
        with open(lim_path, 'w', encoding='utf-8') as fh:
            json.dump(lim_doc, fh, ensure_ascii=False, indent=1)
            fh.write('\n')

    with open(os.path.join(QA, 'truthful-downgrade-report.json'), 'w', encoding='utf-8') as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
        fh.write('\n')

    print('APPLY          :', apply_changes)
    print('LEDGER  entities:', report['ledger_entities'],
          ' relations:', report['ledger_relations'])
    print('ENTITY  downgraded:', len(downgrades['entities']),
          ' locked-limitation:', len(limitations['entities']))
    print('RELATION downgraded:', len(downgrades['relations']),
          ' locked-limitation:', len(limitations['relations']))
    for d in downgrades['entities']:
        print('  E', d['entity_id'], d['from'], '->', d['to'], '|', d['fields_updated'])
    for d in downgrades['relations']:
        print('  R', d['relationship_id'], d['from'], '->', d['to'], '|', d['fields_updated'])
    for l in limitations['relations']:
        print('  LOCK R', l['relationship_id'], l['declared_maturity'], '(scored',
              l['scored_maturity'] + ')')
    for l in limitations['entities']:
        print('  LOCK E', l['entity_id'], l['declared_maturity'], '(scored',
              l['scored_maturity'] + ')')


if __name__ == '__main__':
    main()
