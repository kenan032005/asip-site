#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static/runtime contract checks for the ASIP intelligence demo."""
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
    scripts = (ROOT / "assets" / "js" / "intelligence").glob("*.js")
    intel = (ROOT / "assets" / "js" / "intelligence" / "intelligence.js").read_text(encoding="utf-8")
    graph = (ROOT / "assets" / "js" / "intelligence" / "network.js").read_text(encoding="utf-8")
    css = (ROOT / "assets" / "css" / "intelligence.css").read_text(encoding="utf-8")
    entities = list((DIST / "entity").glob("*/index.html"))
    if len(entities) != 12: fail(f"expected 12 entity routes, got {len(entities)}")
    if "intelligence.js" not in index or "intelligence.js" not in network or "intelligence.js" not in jnim: fail("shared intelligence script missing")
    if "network.js" not in network: fail("network script missing")
    if "data-entity-id" not in intel or "entityHref" not in intel: fail("entity link helper missing")
    for required in ["pushState", "popstate", "queryFocus", "setFocus", "historyStack", "showRelation", "smooth", "focus"]:
        if required not in graph: fail(f"graph interaction contract missing: {required}")
    for required in ["data-type-filter", "data-rel-filter", "zoomIn", "zoomOut", "resetFocus", "backFocus", "entitySearch"]:
        if required not in network: fail(f"graph control missing: {required}")
    for required in ["@media(max-width:850px)", "@media(max-width:560px)", ".shape.diamond", ".shape.square", ".graph-edge.historical"]:
        if required not in css: fail(f"responsive/legend contract missing: {required}")
    if re.search(r'href="/?intelligence/demo/', index + network + jnim): fail("page assumes domain-root URL")
    if 'id="graphLink"' not in jnim:
        fail("entity-to-network link marker missing")
    if "function entityHref" not in intel or "function networkHref" not in intel:
        fail("shared bidirectional link helpers missing")
    if "focus" not in intel or "focus" not in graph:
        fail("focus route contract missing")
    if "actor-jnim" not in network: fail("default focus missing")
    print("PASS routes=14 (entry + network + 12 entity routes)")
    print("PASS shared-data links, base-path relative URLs, graph controls, focus history, relation details")
    print("PASS responsive breakpoints and non-color-only node shapes")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
