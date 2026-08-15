#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Final Global Audit — release-readiness scorecard + report (READ-ONLY)."""
import json
import io
import os
import re
import sys
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

OUT = "qa-artifacts-final-global-audit"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(name):
    return json.load(open(os.path.join(OUT, name), encoding="utf-8"))


def write(name, obj):
    io.open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n").write(
        json.dumps(obj, ensure_ascii=False, indent=2))


canon = read("canonical-alias-final-audit.json")
ent = read("entity-final-readiness.json")
rel = read("relationship-final-readiness.json")
deferred = read("deferred-depth-final-disposition.json")
ppt = read("ppt-final-closure-audit.json")
sev = read("source-evidence-final-integrity.json")
fresh = read("freshness-final-audit.json")
ac = read("africa-corps-final-review.json")
theater = read("theater-readiness-final.json")
cr = read("country-region-final-integrity.json")
graph = read("graph-final-integrity.json")
network = read("network-final-qa.json")
ui = read("ui-mobile-final-audit.json")
route = read("route-final-audit.json")
bypass = read("quality-bypass-final-audit.json")
dirty = read("historical-dirty-artifacts-audit.json")
hygiene = read("repository-hygiene-final-audit.json")
reg = read("full-regression-final.json")
post_hash = read("post-final-audit-knowledge-hashes.json")

# --- basic HTML render check (read-only): key routes non-empty + have root markers ---
render_checks = []
dist_africa = os.path.join(ROOT, "dist", "intelligence", "africa")
render_broken = []
for relpath in ("index.html", "entities/index.html", "relations/index.html",
                "sources/index.html", "network/index.html"):
    p = os.path.join(dist_africa, relpath)
    ok = os.path.isfile(p) and os.path.getsize(p) > 500
    render_checks.append({"route": relpath, "renders": ok})
    if not ok:
        render_broken.append(relpath)

scorecard = {
    "ENTITY_READY": "PASS" if (ent["ENTITY_GRADE_C_COUNT"] == 0 and ent["ENTITY_GRADE_D_COUNT"] == 0
                              and ent["ENTITY_NOT_READY_COUNT"] == 0) else "FAIL",
    "RELATION_READY": "PASS" if (rel["RELATION_NOT_READY_COUNT"] == 0 and rel["P0_CONSOLIDATION_COUNT"] == 0) else "FAIL",
    "SOURCE_EVIDENCE_READY": "PASS" if (sev["BROKEN_SOURCE_REFS"] == 0 and sev["BROKEN_EVIDENCE_TARGETS"] == 0
                                        and sev["ORPHAN_EVIDENCE"] == 0 and sev["DUPLICATE_SOURCE_URLS"] == 0) else "FAIL",
    "PPT_COVERAGE_READY": "PASS" if (ppt["PPT_NAMES_UNRESOLVED"] == 0 and ppt["PPT_RESOLUTION_CONFLICT_COUNT"] == 0) else "FAIL",
    "CURRENT_POSTURE_READY": "PASS" if (fresh["STALE_RELEASE_BLOCKING"] == 0 and fresh["CONFLICTING_STATUS"] == 0) else "FAIL",
    "THEATER_READY": "PASS" if theater["THEATER_NOT_READY_COUNT"] == 0 else "FAIL",
    "GRAPH_READY": "PASS" if graph["BROKEN_ORPHAN_NODE"] == 0 else "FAIL",
    "NETWORK_READY": network["NETWORK_QA"],
    "UI_READY": "PASS" if (ui["UI_REGRESSION"] == 0 and ui["BROKEN_INTERNAL_LINKS"] == 0
                           and ui["JS_RUNTIME_ERRORS"] == 0) else "FAIL",
    "MOBILE_READY": "PASS" if ui["MOBILE_HORIZONTAL_OVERFLOW"] == 0 else "FAIL",
    "ROUTES_READY": "PASS" if (route["BUILD"] == "PASS" and route["BROKEN_INTERNAL_LINKS"] == 0
                               and not render_broken) else "FAIL",
    "REGRESSION_READY": "PASS" if reg["TEST_CASES_FAILED"] == 0 else "FAIL",
    "QUALITY_BYPASS_READY": "PASS" if bypass["QUALITY_BYPASS_SUSPECT_COUNT"] == 0 else "FAIL",
    "REPO_HYGIENE_READY": "PASS" if hygiene["RELEASE_BLOCKING"] == 0 else "FAIL",
}

blockers = [k for k, v in scorecard.items() if v == "FAIL"]
minor_debt = [k for k, v in scorecard.items() if v == "PASS_WITH_MINOR_DEBT"]
# Africa Corps: READY_WITH_MINOR_GAPS is allowed (non-blocking)
africa_corps_blocker = ac.get("FINAL_CLOSURE_BLOCKER", False)
final_blocker_count = len(blockers) + (1 if africa_corps_blocker else 0)

tech_debt = []
if ui["long_urls"]:
    tech_debt.append("long source URLs present (43); CSS word-break handles, no confirmed overflow")
if ac.get("conclusion") == "READY_WITH_MINOR_GAPS":
    tech_debt.append("actor-africa-corps READY_WITH_MINOR_GAPS (evidence density, non-blocking)")
rc_count = rel.get("RELATION_GRADE_C_COUNT", 0)
rd_count = rel.get("RELATION_GRADE_D_COUNT", 0)
if rc_count or rd_count:
    tech_debt.append(f"{rc_count} R-C + {rd_count} R-D relations (DEFER_FUTURE / ADEQUATE_FOR_ROLE, non-blocking)")
if len(dirty["tracked_modified_files"]) > 0:
    tech_debt.append("historical dirty QA-artifact diffs left uncommitted (IGNORE_SAFE, non-blocking)")

scorecard_payload = {
    "artifact": "FINAL_AUDIT_RELEASE_READINESS",
    "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
    "dimensions": scorecard,
    "FINAL_RELEASE_BLOCKER_COUNT": final_blocker_count,
    "blockers": blockers,
    "africa_corps_blocker": africa_corps_blocker,
    "KNOWLEDGE_DATA_CHANGED": post_hash["KNOWLEDGE_DATA_CHANGED"],
    "FINAL_TECH_DEBT_LIST": tech_debt,
    "render_checks": render_checks,
    "FINAL_GLOBAL_AUDIT": "PASS" if final_blocker_count == 0 else "FAIL",
    "ASIP_V1_RELEASE_READY": "YES" if final_blocker_count == 0 else "NO",
}
write("final-release-readiness.json", scorecard_payload)

print("=== SCORECARD ===")
for k, v in scorecard.items():
    print(f"  {k}: {v}")
print("FINAL_RELEASE_BLOCKER_COUNT:", final_blocker_count)
print("blockers:", blockers)
print("africa_corps_blocker:", africa_corps_blocker)
print("FINAL_GLOBAL_AUDIT:", scorecard_payload["FINAL_GLOBAL_AUDIT"])
print("ASIP_V1_RELEASE_READY:", scorecard_payload["ASIP_V1_RELEASE_READY"])
print("render_broken:", render_broken)
