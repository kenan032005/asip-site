#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Global Cross-Country Source Layer — Registry 加载与校验（Source Expansion A）。

Registry 数据：data/global_sources.json（静态，不含 runtime health）。
校验：source_id 唯一、trust_tier/role/acquisition_method/scope 枚举、
evidence_eligible 布尔、必需字段齐全。
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REGISTRY_PATH = ROOT / "data" / "global_sources.json"
COUNTRY_REGISTRY_PATH = ROOT / "data" / "country_sources.json"

VALID_TRUST_TIERS = {"A", "B", "C", "D", "NONE"}
VALID_ROLES = {
    "evidence", "discovery", "distribution_platform",
    "authoritative_disease_evidence",
}
VALID_ACQUISITION = {
    "public_listing_html", "public_hub_html", "rss", "rss_global_filter",
    "rss_rdf", "api", "official_listing", "listing_publication_discovery",
    "publication_discovery",
}
REQUIRED_FIELDS = [
    "source_id", "name", "source_group", "scope", "country_scope",
    "language", "role", "trust_tier", "evidence_eligible",
    "acquisition_method", "listing_host", "listing_path",
    "detail_strategy", "enabled", "priority",
]
COUNTRY_REQUIRED_FIELDS = [
    "source_id", "name", "source_group", "country_iso3", "language",
    "role", "trust_tier", "evidence_eligible",
    "acquisition_method", "listing_host", "listing_path",
    "detail_strategy", "enabled", "priority",
]


class RegistryError(Exception):
    pass


def load_registry(path=None):
    """加载 Global Source Registry 并校验。返回 (sources, errors)。"""
    p = Path(path) if path else REGISTRY_PATH
    if not p.exists():
        raise RegistryError("registry missing: %s" % p)
    doc = json.loads(p.read_text(encoding="utf-8"))
    sources = doc.get("sources", [])
    if not isinstance(sources, list) or not sources:
        raise RegistryError("registry sources empty: %s" % p)
    errors = _validate(sources, REQUIRED_FIELDS)
    return sources, errors


def load_country_registry(path=None):
    """加载 Country Source Registry（Source Expansion B）。返回 (sources, errors)。"""
    p = Path(path) if path else COUNTRY_REGISTRY_PATH
    if not p.exists():
        raise RegistryError("country registry missing: %s" % p)
    doc = json.loads(p.read_text(encoding="utf-8"))
    sources = doc.get("sources", [])
    if not isinstance(sources, list) or not sources:
        raise RegistryError("country registry sources empty: %s" % p)
    errors = _validate(sources, COUNTRY_REQUIRED_FIELDS, country=True)
    return sources, errors


def _validate(sources, required_fields, country=False):
    errors = []
    seen = set()
    for i, s in enumerate(sources):
        sid = s.get("source_id", "")
        if not sid:
            errors.append("[%d] missing source_id" % i)
            continue
        if sid in seen:
            errors.append("duplicate source_id: %s" % sid)
        seen.add(sid)
        for f in required_fields:
            if f not in s:
                errors.append("%s: missing field %s" % (sid, f))
        if s.get("trust_tier") not in VALID_TRUST_TIERS:
            errors.append("%s: invalid trust_tier %r" % (sid, s.get("trust_tier")))
        if s.get("role") not in VALID_ROLES:
            errors.append("%s: invalid role %r" % (sid, s.get("role")))
        if not isinstance(s.get("evidence_eligible"), bool):
            errors.append("%s: evidence_eligible must be bool" % sid)
        # 聚合类（discovery/distribution）不得 evidence_eligible=True
        if s.get("role") in ("discovery", "distribution_platform") and s.get("evidence_eligible"):
            errors.append("%s: aggregator role must have evidence_eligible=false" % sid)
        if s.get("acquisition_method") not in VALID_ACQUISITION:
            errors.append("%s: invalid acquisition_method %r" % (sid, s.get("acquisition_method")))
        if country:
            if not isinstance(s.get("country_iso3"), str) or len(s.get("country_iso3") or "") != 3:
                errors.append("%s: invalid country_iso3 %r" % (sid, s.get("country_iso3")))
            en = s.get("enabled")
            if not (en is True or en is False or en == "trial"):
                errors.append("%s: enabled must be bool or 'trial'" % sid)
    return errors


def enabled_sources(sources):
    return [s for s in sources if s.get("enabled", False)]


def by_id(sources):
    return {s["source_id"]: s for s in sources}


def check_registry():
    """CLI 便捷入口。"""
    sources, errors = load_registry()
    print("global sources: %d" % len(sources))
    if errors:
        print("errors: %d" % len(errors))
        for e in errors:
            print("  - %s" % e)
        return 1
    print("registry OK")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(check_registry())
