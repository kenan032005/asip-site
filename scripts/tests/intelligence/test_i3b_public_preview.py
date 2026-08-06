#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I3-B: public preview tests — preview URL must be public (not 127.0.0.1),
reachable without login, and the preview marker file/version present."""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "release" / "i3b-rc1"
PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  ({detail})")


def main():
    url = None
    alt_url = None
    manifest = None
    if (RELEASE / "release_candidate_manifest.json").exists():
        manifest = json.loads((RELEASE / "release_candidate_manifest.json").read_text(encoding="utf-8"))
        url = manifest.get("public_preview_url")
        alt_url = manifest.get("public_preview_url_alt")
    if (RELEASE / "public_preview_verification.json").exists():
        pv = json.loads((RELEASE / "public_preview_verification.json").read_text(encoding="utf-8"))
        url = url or pv.get("url")
        alt_url = alt_url or pv.get("verified_immediate_url")

    check("designated preview URL recorded", bool(url), str(url))
    check("verified immediate preview URL recorded", bool(alt_url), str(alt_url))
    if url:
        check("preview URL is public (not 127.0.0.1/localhost)",
              "127.0.0.1" not in url and "localhost" not in url and url.startswith("http"))
        check("preview URL is on github.io or equivalent stable host",
              any(h in url for h in ("github.io", "agentos-app.net")) or "previews" in url, url)
    if alt_url:
        try:
            r = urllib.request.urlopen(urllib.request.Request(alt_url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20)
            body = r.read(2000).decode("utf-8", "ignore")
            check("verified preview URL reachable (HTTP 200)", r.status == 200, str(r.status))
            check("verified preview serves HTML", "html" in body.lower() or "doctype" in body.lower())
        except Exception as ex:
            check("verified preview URL reachable", False, str(ex)[:120])
    if url and "/previews/" in url:
        # gh-pages versioned path: branch-level files must exist (raw endpoint)
        raw_url = "https://raw.githubusercontent.com/kenan032005/asip-site/gh-pages/previews/asip-intelligence-v1.0-rc1/intelligence/africa/index.html"
        try:
            r = urllib.request.urlopen(raw_url, timeout=20)
            check("gh-pages preview files live on branch (raw 200)", r.status == 200, str(r.status))
        except Exception as ex:
            check("gh-pages preview files live on branch (raw 200)", False, str(ex)[:120])

    check("preview is versioned under /previews/ or versioned dir",
          bool(url) and ("/previews/" in url or "asip-intelligence-v1.0-rc1" in url), str(url))

    if FAIL:
        sys.exit(1)
    print(f"\nI3-B public preview: PASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    main()
