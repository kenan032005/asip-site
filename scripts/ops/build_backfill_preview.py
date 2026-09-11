#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build an isolated ASIP V2 historical-backfill Preview.

This orchestration never patches tracked production data. It creates a small
allowlisted data overlay, passes that overlay to build_site, and emits the
historical daily report pages into a separate Preview dist.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = Path(r"C:/Users/kenan/.workbuddy/binaries/python/versions/3.13.12/python.exe")
PREVIEW_ROOT = ROOT / "data" / "runtime" / "backfill_preview_v2"
WORK_ROOT = ROOT / ".workbuddy_tmp"
WORK = WORK_ROOT / "backfill_v2_build_data"
DIST = ROOT / "preview_dist_v2"
BATCH_ID = "asip-backfill-20260818-20260827-v2-full"

ALLOWLIST = [
    "status.json", "latest-summary.json", "events.json", "countries.json",
    "risk-levels.json", "sources.json", "public/published_events.json",
    "public/current_metrics.json", "public/legacy_archive_events.json",
    "public/disease_events.json",
]


def copy_allowlisted_data():
    """Create a data overlay without deleting prior Preview workspaces."""
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    work = WORK_ROOT / ("backfill_v2_build_data_" + stamp)
    work.mkdir(parents=True, exist_ok=False)
    for rel in ALLOWLIST:
        src = ROOT / "data" / rel
        if not src.exists():
            continue
        dst = work / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    print("DATA_OVERLAY:", work)
    return work


def main():
    work = copy_allowlisted_data()
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_site

    # Use the V2 overlay status for the shared header timestamp. This remains
    # inside the isolated Preview data directory and never changes production.
    status_src = PREVIEW_ROOT / "views" / "site_overview.json"
    if status_src.exists():
        status_view = json.loads(status_src.read_text(encoding="utf-8"))
        overlay_status = work / "status.json"
        if overlay_status.exists():
            status_doc = json.loads(overlay_status.read_text(encoding="utf-8"))
            status_doc["last_update_bj"] = status_view.get("latest_data_time_bj") or status_doc.get("last_update_bj")
            status_doc["generated_at_bj"] = status_view.get("generated_at") or status_doc.get("generated_at_bj")
            status_doc["last_updated_beijing"] = status_view.get("latest_data_time_bj") or status_doc.get("last_updated_beijing")
            overlay_status.write_text(json.dumps(status_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    build_site.main(
        run_id="historical-backfill-v2-full",
        data_dir=work,
        frontend_views_dir=PREVIEW_ROOT / "views",
        dist_dir=DIST,
        reports_dir=ROOT / "reports",
    )

    # Report pages must be generated after build_site copied the data views.
    sys.path.insert(0, str(ROOT / "scripts" / "ops"))
    import emit_backfill_report_pages as reports
    reports.DIST = DIST
    reports.REPORTS = PREVIEW_ROOT / "reports"
    reports.main()

    # Reconcile the generated report index with the V2 review summary.
    ri = json.loads((DIST / "data" / "report_index.json").read_text(encoding="utf-8"))
    summary_path = PREVIEW_ROOT / "historical_backfill_v2_import_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.setdefault("summary_fields", {})["PREVIEW_REPORT_INDEX_COUNT"] = ri.get("count", 0)
    summary["summary_fields"]["PREVIEW_DIST"] = str(DIST)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("V2_PREVIEW_BUILD=OK")
    print("PREVIEW_DIST:", DIST)
    print("REPORT_INDEX_COUNT:", ri.get("count", 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
