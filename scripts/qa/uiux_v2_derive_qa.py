# -*- coding: utf-8 -*-
"""UI/UX V2: derive per-topic QA artifacts from browser-qa.json + interaction-qa.json
and emit component-change-map.json."""
import json, io, os, sys, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
OUT = 'qa-artifacts-uiux-v2'
bq = json.load(io.open(os.path.join(OUT, 'browser-qa.json'), encoding='utf-8'))
iq = json.load(io.open(os.path.join(OUT, 'interaction-qa.json'), encoding='utf-8'))
checks = {c['name']: c for c in iq['checks']}

def grab(*names):
    out = []
    for n in names:
        if n in checks:
            out.append({'check': n, 'pass': checks[n]['pass'], 'detail': checks[n]['detail']})
    return out

# ---------- toc-qa ----------
toc_checks = grab('TOC visible on Al-Shabaab', 'TOC auto-generated >=8 links', 'TOC sections anchored (leadership/uncertainties/asip)',
                  'TOC desktop details open', 'deep-link #sec-leadership lands near top', 'scroll-spy highlights current section',
                  'Mobile TOC collapsed by default')
toc = {'scope': 'entity pages (Al-Shabaab primary) + deep-link + scroll-spy + mobile collapse',
       'checks': toc_checks,
       'pass': all(c['pass'] for c in toc_checks),
       'gate': 'PASS' if all(c['pass'] for c in toc_checks) else 'FAIL'}

# ---------- semantic-visual-qa ----------
sem_checks = grab('Lakurawa disputed badge in hero', 'Lakurawa uncertainty card rendered', 'Disputed relation badge in hero',
                  'Relation timeline V2 stages + current banner')
sem = {'scope': 'VERIFIED FACT / INSTITUTIONAL ASSESSMENT / ASIP ANALYSIS / UNCERTAINTY / WATCH INDICATORS presentation classes; disputed badges',
       'checks': sem_checks,
       'pass': all(c['pass'] for c in sem_checks),
       'gate': 'PASS' if all(c['pass'] for c in sem_checks) else 'FAIL',
       'notes': 'uncertainties rendered as .intel-uncertainty-card (text label + left border + bg); '
                'disputed entities/relations get .intel-badge.disputed in hero; '
                'sanctions_legal/legal_status sections carry .intel-sem-chip.institutional; '
                'ASIP analysis stays in .intel-analysis-card (platform analysis, not verified fact).'}

# ---------- list-search-filter-qa ----------
list_checks = grab('Entity search filters + count updates', 'Entity search syncs ?entityQ= URL',
                   'Entity type filter narrows to persons', 'Entity filter state restores via URL (reload/forward)',
                   'Relation search filters + URL sync')
list_qa = {'scope': 'entities list (search/type/importance/status/region/maturity/sort, URL sync) + relations list (search/type/status/maturity/disputed/time-sensitive, URL sync)',
           'checks': list_checks,
           'pass': all(c['pass'] for c in list_checks),
           'gate': 'PASS' if all(c['pass'] for c in list_checks) else 'FAIL',
           'notes': 'search input uses 350ms debounce pushState; select changes pushState; popstate restores; '
                    'reload with ?entityQ= restores input + count.'}

# ---------- relation-inline-link-qa ----------
inline_checks = grab('Relation body wired through inlineLinks+autoLink renderer')
# static check: every relation-body text field now passes through inlineLinks
js = io.open('assets/js/intelligence/africa.js', encoding='utf-8').read()
il_count = js.count('inlineLinks(esc(')
inline_qa = {'scope': 'relation profile body reuses entity inlineLinks renderer (no new matcher)',
             'checks': inline_checks,
             'inlineLinks_usage_count_in_relation_renderer': il_count,
             'data_markup': 'relation profiles contain 0 [[...]] markers; Fix-1 auto-links exact canonical/alias names (longest-first, denylist, ambiguity-safe, URL/ID protected), no fuzzy matching',
             'pass': all(c['pass'] for c in inline_checks),
             'gate': 'PASS' if all(c['pass'] for c in inline_checks) else 'FAIL'}

# ---------- network-v2-qa ----------
net_checks = grab('Network search syncs ?focus= URL', '2-hop expands nodes (or density note shown)',
                  '2-hop toggle reflects state', 'Relation-type filter narrows edges', 'Disputed edges styled on Lakurawa network')
net_qa = {'scope': 'focused 1-hop default; search URL sync; relation-type/status/disputed filters; optional 2-hop with cap=20 + density note',
          'checks': net_checks,
          'pass': all(c['pass'] for c in net_checks),
          'gate': 'PASS' if all(c['pass'] for c in net_checks) else 'FAIL',
          'notes': '2-hop is OFF by default (aria-pressed=false); importance-first ordering; node cap 20 with user-facing density prompt.'}

# ---------- responsive-qa ----------
res_checks = grab('Mobile h1 font <= 26px (clamp)', 'Mobile no horizontal overflow',
                  'Mobile relation hero single column', 'Mobile TOC collapsed by default')
mobile_rows = [r for r in bq['results'] if r['viewport'] == 'mobile']
overflow_mobile = [r['key'] for r in mobile_rows if r['state'].get('h_overflow')]
res_qa = {'scope': '390x844 mobile across all 19 pages; h1 clamp; TOC collapse; relation hero stacking; no horizontal overflow',
          'checks': res_checks,
          'mobile_overflow_pages': overflow_mobile,
          'desktop_h1_font_al_shabaab': next((r['state']['h1_font'] for r in bq['results'] if r['key'] == 'entity_al_shabaab' and r['viewport'] == 'desktop'), None),
          'mobile_h1_font_al_shabaab': next((r['state']['h1_font'] for r in bq['results'] if r['key'] == 'entity_al_shabaab' and r['viewport'] == 'mobile'), None),
          'pass': all(c['pass'] for c in res_checks) and not overflow_mobile,
          'gate': 'PASS' if (all(c['pass'] for c in res_checks) and not overflow_mobile) else 'FAIL'}

# ---------- component-change-map ----------
ccm = {
  'baseline': 'feature/asip-ppt-entity-expansion-b @ 525012d',
  'summary': 'Presentation-only changes. All knowledge data (data/intelligence/africa/**) untouched (hash-verified, KNOWLEDGE_DATA_CHANGED=0).',
  'components': [
    {'feature': 'Entity long-page TOC (auto, scroll-spy, deep-link, sticky desktop, collapsible mobile)',
     'html_template': 'intelligence/africa/_templates/entity.html (#entityToc container)',
     'js': 'assets/js/intelligence/africa.js (renderSections toc emission; initScrollSpy)',
     'css': 'assets/css/intelligence.css (.profile-toc-wrap/.intel-toc-sticky/.profile-toc-details/.profile-toc a.active)',
     'generator': 'none (template-driven)'},
    {'feature': 'Entity hero + key-facts',
     'html_template': 'intelligence/africa/_templates/entity.html (#entityHeading, #entityKeyFacts)',
     'js': 'assets/js/intelligence/africa.js (initEntity heading + key-facts builder)',
     'css': 'assets/css/intelligence.css (.intel-keyfacts, .intel-entity-head h1 clamp)'},
    {'feature': 'Semantic visual hierarchy (5 classes)',
     'html_template': 'none (rendered)',
     'js': 'assets/js/intelligence/africa.js (renderSections uncertainty/institutional/asip/watch partitions; initRelation uncertainties)',
     'css': 'assets/css/intelligence.css (.intel-sem-chip, .intel-uncertainty-card, .intel-institutional-card, .uncertainty-partition)',
     'note': 'disputed badge reuses .intel-badge.disputed'},
    {'feature': 'Relation page hero (Party A -> summary -> Party B)',
     'html_template': 'intelligence/africa/_templates/relation.html (#relationParties)',
     'js': 'assets/js/intelligence/africa.js (initRelation partyCard/hero)',
     'css': 'assets/css/intelligence.css (.relation-hero, .relation-hero-summary, .relation-hero-arrow)'},
    {'feature': 'Relation body inline entity links (reuse inlineLinks)',
     'js': 'assets/js/intelligence/africa.js (relation body fields now run inlineLinks(esc(...)))',
     'note': 'same renderer as entity pages; no new matching logic'},
    {'feature': 'Relation timeline V2 (stage cards + current-phase banner)',
     'html_template': 'intelligence/africa/_templates/relation.html (#relationTimeline)',
     'js': 'assets/js/intelligence/africa.js (initRelation timeline V2 renderer)',
     'css': 'assets/css/intelligence.css (.rtl-h/.rtl-stage-card/.rtl-current-banner; mobile column)'},
    {'feature': 'Entity list search/filter/sort + URL sync',
     'html_template': 'intelligence/africa/_templates/entities.html (.list-controls)',
     'js': 'assets/js/intelligence/africa.js (initEntities rewrite)',
     'css': 'assets/css/intelligence.css (.list-controls, .list-count, .list-empty)'},
    {'feature': 'Relation list search/filter + URL sync',
     'html_template': 'intelligence/africa/_templates/relations.html (.list-controls)',
     'js': 'assets/js/intelligence/africa.js (initRelations rewrite)',
     'css': 'assets/css/intelligence.css (.list-controls, .list-count, .list-empty)'},
    {'feature': 'Sources/evidence grouped + collapsible',
     'html_template': 'intelligence/africa/_templates/sources.html (#sourceGrid reused)',
     'js': 'assets/js/intelligence/africa.js (initSources rewrite; sourceCategory())',
     'css': 'assets/css/intelligence.css (.source-group, .source-group-items)'},
    {'feature': 'Network V2 (search URL sync, relation filters, 2-hop cap, disputed edges, legend)',
     'html_template': 'intelligence/africa/_templates/network.html (relTypeFilter/relStatusFilter/relDisputedOnly/twoHopToggle/densityNote/legend)',
     'js': 'assets/js/intelligence/africa.js (initNetwork: relFilters, twoHop, generic edge drawing, disputed class)',
     'css': 'assets/css/intelligence.css (.twohop-btn.active, .network-density-note, .graph-edge.disputed, .legend-line.disputed)'},
    {'feature': 'Responsive typography (h1 clamp, en second line)',
     'css': 'assets/css/intelligence.css (.intel-entity-head h1 clamp, .intel-title-en clamp, .rel-hero-title clamp)'},
  ],
}

for name, obj in [('toc-qa', toc), ('semantic-visual-qa', sem), ('list-search-filter-qa', list_qa),
                  ('relation-inline-link-qa', inline_qa), ('network-v2-qa', net_qa), ('responsive-qa', res_qa),
                  ('component-change-map', ccm)]:
    json.dump(obj, io.open(os.path.join(OUT, name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(name, '->', obj.get('gate', 'n/a'))

print('ALL_DERIVED_WRITTEN')
