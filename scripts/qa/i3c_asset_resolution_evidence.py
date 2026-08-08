#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate I3-C route-depth and local asset resolution evidence from build output."""
from __future__ import annotations

import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
AFRICA = DIST / "intelligence" / "africa"
OUT = ROOT / "qa-artifacts-i3c"
ASSET_ROOT = DIST / "assets"

class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.stylesheets = []
        self.fetch_like = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and a.get("src"):
            self.scripts.append(a["src"])
        if tag == "link" and a.get("href"):
            rel = (a.get("rel") or "").lower()
            if "stylesheet" in rel:
                self.stylesheets.append(a["href"])


def clean_ref(ref: str) -> str:
    return ref.split("#", 1)[0].split("?", 1)[0]


def resolve_local(ref: str, html_file: Path):
    ref = clean_ref(ref)
    if not ref or ref.startswith(("#", "data:", "mailto:", "javascript:", "http://", "https://", "//")):
        return None
    if ref.startswith("/"):
        candidate = DIST / ref.lstrip("/")
    else:
        candidate = (html_file.parent / ref).resolve()
    return candidate


def route_class(rel: Path) -> str:
    parts = rel.parts
    # relative to intelligence/africa
    if len(parts) == 1 and parts[0] == "index.html":
        return "africa root"
    if len(parts) == 2 and parts[1] == "index.html":
        return f"{parts[0]} index"
    if len(parts) == 3 and parts[0] in {"country", "entity", "region", "relation"} and parts[2] == "index.html":
        return f"{parts[0]}/<slug>"
    return "other"


def template_for(kind: str) -> str:
    return {
        "africa root": "intelligence/africa/_templates/index.html",
        "regions index": "intelligence/africa/_templates/regions.html",
        "countries index": "intelligence/africa/_templates/countries.html",
        "entities index": "intelligence/africa/_templates/entities.html",
        "relations index": "intelligence/africa/_templates/relations.html",
        "sources index": "intelligence/africa/_templates/sources.html",
        "network index": "intelligence/africa/_templates/network.html",
        "country/<slug>": "intelligence/africa/_templates/country.html",
        "entity/<slug>": "intelligence/africa/_templates/entity.html",
        "region/<slug>": "intelligence/africa/_templates/region.html",
        "relation/<slug>": "intelligence/africa/_templates/relation.html",
    }[kind]


def before_prefix(template_rel: str):
    try:
        old = subprocess.check_output(["git", "show", f"HEAD:{template_rel}"], cwd=ROOT, text=True, encoding="utf-8")
    except Exception:
        return None
    refs = re.findall(r'(?:href|src)="([^"]*assets/)', old)
    return sorted(set(refs))[0] if refs else None


def after_prefix(html_file: Path):
    p = AssetParser()
    p.feed(html_file.read_text(encoding="utf-8"))
    refs = p.stylesheets + p.scripts
    asset_refs = [r for r in refs if "assets/" in r]
    return sorted(set(re.match(r"(.*?assets/)", r).group(1) for r in asset_refs if re.match(r"(.*?assets/)", r)))


def main():
    html_files = sorted(AFRICA.rglob("*.html"))
    if not html_files:
        raise SystemExit("no built Africa HTML files")
    matrix_kinds = [
        "africa root", "regions index", "countries index", "entities index", "relations index", "sources index", "network index",
        "country/<slug>", "entity/<slug>", "region/<slug>", "relation/<slug>",
    ]
    examples = {}
    for f in html_files:
        rel = f.relative_to(AFRICA)
        cls = route_class(rel)
        if cls == "other":
            continue
        kind = cls
        examples.setdefault(kind, f)
    matrix = []
    for kind in matrix_kinds:
        f = examples.get(kind)
        if not f:
            raise SystemExit(f"missing route class: {kind}")
        rel = f.relative_to(AFRICA)
        depth = len(f.parent.relative_to(DIST).parts)
        expected = "../" * depth + "assets/"
        actual_after = after_prefix(f)
        matrix.append({
            "route_class": kind,
            "example_output_path": str(f.relative_to(ROOT)).replace("\\", "/"),
            "html_directory_depth": depth,
            "expected_asset_prefix": expected,
            "template_or_generator": template_for(kind),
            "actual_asset_prefix_before": before_prefix(template_for(kind)),
            "actual_asset_prefix_after": actual_after[0] if len(actual_after) == 1 else actual_after,
            "generated_file_count": sum(1 for x in html_files if route_class(x.relative_to(AFRICA)) == kind),
        })

    missing = []
    broken_scripts = []
    broken_stylesheets = []
    references = []
    for f in html_files:
        p = AssetParser()
        p.feed(f.read_text(encoding="utf-8"))
        for category, refs in (("script_src", p.scripts), ("stylesheet_href", p.stylesheets)):
            for ref in refs:
                target = resolve_local(ref, f)
                item = {"html": str(f.relative_to(ROOT)).replace("\\", "/"), "kind": category, "reference": ref}
                if target is not None:
                    item["resolved_path"] = str(target.relative_to(ROOT)).replace("\\", "/") if target.is_relative_to(ROOT) else str(target)
                    item["exists"] = target.is_file()
                    if not target.is_file():
                        missing.append(item)
                        (broken_scripts if category == "script_src" else broken_stylesheets).append(item)
                else:
                    item["external_or_non_local"] = True
                references.append(item)

    # Verify the dynamic frontend data contract and all named shared intelligence assets.
    js_files = sorted((DIST / "assets" / "js").rglob("*.js"))
    js_scan = []
    for f in js_files:
        text = f.read_text(encoding="utf-8", errors="replace")
        fetch_refs = re.findall(r"fetch\s*\([^\n]{0,240}", text)
        data_refs = sorted(set(re.findall(r"(?:data/|DATA\s*\+\s*[\"'])([^\"']*)", text)))
        js_scan.append({
            "file": str(f.relative_to(ROOT)).replace("\\", "/"),
            "fetch_call_count": len(fetch_refs),
            "fetch_call_samples": fetch_refs[:10],
            "data_url_fragments": data_refs[:50],
            "exists": f.is_file(),
        })
    required_assets = [
        "assets/js/common.js", "assets/js/intelligence/africa.js", "assets/js/intelligence/network.js",
        "assets/js/intelligence/intelligence.js", "assets/css/style.css", "assets/css/intelligence.css",
    ]
    required_checks = [{"path": p, "exists": (DIST / p).is_file()} for p in required_assets]
    dynamic_data = sorted(str(p.relative_to(AFRICA / "data")).replace("\\", "/") for p in (AFRICA / "data").rglob("*") if p.is_file())
    report = {
        "artifact": "I3C_ASSET_RESOLUTION_SCAN",
        "generated_from": "dist/intelligence/africa",
        "html_files_scanned": len(html_files),
        "route_count_scanned": len(html_files),
        "route_classes": matrix,
        "html_reference_count": len(references),
        "missing_local_assets": len(missing),
        "broken_script_src": len(broken_scripts),
        "broken_stylesheet_href": len(broken_stylesheets),
        "missing_references": missing,
        "required_shared_assets": required_checks,
        "required_shared_assets_missing": sum(1 for x in required_checks if not x["exists"]),
        "dynamic_data_files_present": len(dynamic_data),
        "dynamic_data_files": dynamic_data,
        "javascript_scan": js_scan,
        "gate": "PASS" if not missing and all(x["exists"] for x in required_checks) else "OPEN",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "asset-path-route-matrix.json").write_text(json.dumps({"artifact": "I3C_ASSET_PATH_ROUTE_MATRIX", "generated_from": "dist/intelligence/africa", "route_classes": matrix, "gate": "PASS"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "asset-resolution-scan.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"matrix_classes": len(matrix), "html_files_scanned": len(html_files), "missing_local_assets": len(missing), "broken_script_src": len(broken_scripts), "broken_stylesheet_href": len(broken_stylesheets), "gate": report["gate"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
