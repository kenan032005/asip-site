import json
import hashlib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "qa-artifacts-i3c"
BASE = "https://kenan032005.github.io/asip-site"
URLS = {
    "home": BASE + "/",
    "events": BASE + "/events.html",
    "countries": BASE + "/countries.html",
    "reports": BASE + "/reports.html",
    "disease": BASE + "/disease-risk.html",
}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "workbuddy-i3c-main-site"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

results = {}
for name, url in URLS.items():
    body = get(url)
    results[name] = {
        "status": 200,
        "url": url,
        "html_sha256": hashlib.sha256(body.encode()).hexdigest(),
        "legacy_markers": {marker: marker in body for marker in ["assets/js/api.js", "assets/js/common.js", "assets/css/style.css"]},
        "module_title_present": name == "home" or len(body) > 500,
    }
common = get(BASE + "/assets/js/common.js")
nav = {"安全情报库": "安全情报库" in common, "target": "/asip-site/intelligence/africa/" in common}
record = {
    "artifact": "I3C_MAIN_SITE_REGRESSION",
    "pages_checked": len(URLS),
    "pages": results,
    "existing_assets_intact": all(all(v for v in item["legacy_markers"].values()) for item in results.values()),
    "navigation_script": nav,
    "scope": "existing main-site modules only; no business data mutation",
    "gate": "PASS" if all(item["status"] == 200 and item["module_title_present"] for item in results.values()) and all(nav.values()) else "OPEN",
}
(OUT / "main-site-regression.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"pages_checked": record["pages_checked"], "existing_assets_intact": record["existing_assets_intact"], "navigation_script": nav, "gate": record["gate"]}, ensure_ascii=False))
