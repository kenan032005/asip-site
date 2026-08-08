#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poll a GitHub Actions workflow run until completion."""
import json
import sys
import time
import urllib.request

RUN_ID = sys.argv[1] if len(sys.argv) > 1 else "31265830778"
REPO = "kenan032005/asip-site"

def fetch(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "asip-qa"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

for _ in range(40):
    d = fetch(f"https://api.github.com/repos/{REPO}/actions/runs/{RUN_ID}")
    status, conclusion = d.get("status"), d.get("conclusion")
    print(f"run={RUN_ID} status={status} conclusion={conclusion}", flush=True)
    if status == "completed":
        print(json.dumps({"run_id": d.get("id"), "head_sha": d.get("head_sha"), "status": status, "conclusion": conclusion}))
        sys.exit(0 if conclusion == "success" else 1)
    time.sleep(15)
sys.exit(2)
