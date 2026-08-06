#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static/runtime contract checks for the ASIP intelligence demo (I1-A V0.2)."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DIST = ROOT / "dist" / "intelligence" / "demo"


def fail(message):
    raise AssertionError(message)


def main():
    index = (DIST / "index.html").read_text(encoding="utf-8")
    network = (DIST / "network" / "index.html").read_text(encoding="utf-8")
    jnim = (DIST / "entity" / "jnim" / "index.html").read_text(encoding="utf-8")
    intel = (ROOT / "assets" / "js" / "intelligence" / "intelligence.js").read_text(encoding="utf-8")
    graph = (ROOT / "assets" / "js" / "intelligence" / "network.js").read_text(encoding="utf-8")
    css = (ROOT / "assets" / "css" / "intelligence.css").read_text(encoding="utf-8")
    entities = list((DIST / "entity").glob("*/index.html"))
    relations = list((DIST / "relation").glob("*/index.html"))
    if len(entities) != 12: fail(f"expected 12 entity routes, got {len(entities)}")
    if len(relations) != 20: fail(f"expected 20 relation routes, got {len(relations)}")
    if "intelligence.js" not in index or "intelligence.js" not in network or "intelligence.js" not in jnim: fail("shared intelligence script missing")
    if "network.js" not in network: fail("network script missing")
    for required in ["displayTitle", "displayGraph", "displayFirstMention", "displayShort", "displayPlain", "importanceLabel", "relationHref", "initRelation", "display_ring"]:
        if required not in intel: fail(f"intelligence.js unified naming/relation contract missing: {required}")
    for required in ["pushState", "popstate", "queryFocus", "setFocus", "historyStack", "showRelation", "smooth", "importanceFilter", "data-imp-filter", "data-view-filter", "RINGS", "ringFor", "fitAfterFilter"]:
        if required not in graph: fail(f"graph interaction contract missing: {required}")
    for required in ["data-type-filter", "data-rel-filter", "data-imp-filter", "data-view-filter", "zoomIn", "zoomOut", "resetFocus", "backFocus", "entitySearch", "importanceStats"]:
        if required not in network: fail(f"graph control missing: {required}")
    for required in ["@media(max-width:850px)", "@media(max-width:560px)", ".shape.diamond", ".shape.square", ".graph-edge.historical", ".ring-guide", ".imp-L1", ".intel-infobox", ".profile-toc", ".relation-timeline"]:
        if required not in css: fail(f"responsive/legend/profile contract missing: {required}")
    if re.search(r'href="/?intelligence/demo/', index + network + jnim): fail("page assumes domain-root URL")
    if 'id="graphLink"' not in jnim: fail("entity-to-network link marker missing")
    if 'data-intel-page="relation"' not in (DIST / "relation" / "jnim-is-sahel-hostile" / "index.html").read_text(encoding="utf-8"):
        fail("relation page marker missing")
    print("PASS routes=34 (entry + network + 12 entity routes + 20 relation routes)")
    print("PASS shared-data links, base-path relative URLs, graph controls, importance filters, focus history, relation details and relation pages")
    print("PASS responsive breakpoints, ring guides, encyclopedia profile and non-color-only node shapes")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
