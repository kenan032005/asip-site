#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static/runtime contract checks for ASIP Africa intelligence pages (I2-A)."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DIST = ROOT / "dist" / "intelligence" / "africa"

def fail(msg):
    raise AssertionError(msg)

def main():
    index = (DIST / "index.html").read_text(encoding="utf-8")
    africa_js = (ROOT / "assets" / "js" / "intelligence" / "africa.js").read_text(encoding="utf-8")
    regions = list((DIST / "region").glob("*/index.html"))
    countries = list((DIST / "country").glob("*/index.html"))
    entities = list((DIST / "entity").glob("*/index.html"))
    relations = list((DIST / "relation").glob("*/index.html"))
    for path, label, minimum in [
        (regions, "regions", 7), (countries, "countries", 12), (entities, "entities", 30), (relations, "relations", 60),
    ]:
        if len(path) < minimum: fail(f"{label} routes < {minimum}: {len(path)}")
    if not (DIST / "network" / "index.html").exists(): fail("network route missing")
    if not (DIST / "sources" / "index.html").exists(): fail("sources route missing")
    if "africa.js" not in index: fail("africa.js missing on home")
    for required in ["data-africa-page", "initNetwork", "regionFilter", "countryFilter", "data-imp-filter", "entityHref", "relationHref", "networkHref", "ASIP_AFRICA", "byEntityId"]:
        if required not in africa_js: fail(f"africa.js contract missing: {required}")
    # base path safety: no absolute /intelligence/africa links
    all_html = "".join(p.read_text(encoding="utf-8") for p in list((DIST).rglob("index.html")))
    if re.search(r'href="/?intelligence/africa/', all_html): fail("page assumes domain-root URL")
    # deep pages carry their slug markers
    if 'data-region-slug="central-sahel"' not in (DIST / "region" / "central-sahel" / "index.html").read_text(encoding="utf-8"): fail("region marker missing")
    if 'data-country-slug="chad"' not in (DIST / "country" / "chad" / "index.html").read_text(encoding="utf-8"): fail("chad marker missing")
    if 'data-country-slug="mozambique"' not in (DIST / "country" / "mozambique" / "index.html").read_text(encoding="utf-8"): fail("mozambique marker missing")
    if 'data-entity-slug="jnim"' not in (DIST / "entity" / "jnim" / "index.html").read_text(encoding="utf-8"): fail("jnim marker missing")
    print(f"PASS africa routes: home + 6 index + {len(regions)} regions + {len(countries)} countries + {len(entities)} entities + {len(relations)} relations + network + sources")
    print("PASS base-path relative URLs, page markers, africa.js contracts")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
