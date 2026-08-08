import json
import hashlib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "qa-artifacts-i3c"
BASE = "https://kenan032005.github.io/asip-site"
URLS = {
    "africa_home": BASE + "/intelligence/africa/",
    "regions": BASE + "/intelligence/africa/regions/",
    "countries": BASE + "/intelligence/africa/countries/",
    "entities": BASE + "/intelligence/africa/entities/",
    "relations": BASE + "/intelligence/africa/relations/",
    "sources": BASE + "/intelligence/africa/sources/",
    "network": BASE + "/intelligence/africa/network/",
    "ethiopia": BASE + "/intelligence/africa/country/ethiopia/",
    "niger": BASE + "/intelligence/africa/country/niger/",
    "jnim": BASE + "/intelligence/africa/entity/jnim/",
    "iswap": BASE + "/intelligence/africa/entity/iswap/",
    "is_sahel": BASE + "/intelligence/africa/entity/is-sahel/",
    "jas": BASE + "/intelligence/africa/entity/boko-haram-jas/",
    "fano": BASE + "/intelligence/africa/entity/fano/",
    "ola": BASE + "/intelligence/africa/entity/ola/",
    "tpdf": BASE + "/intelligence/africa/entity/tpdf/",
    "relation_jnim_is": BASE + "/intelligence/africa/relation/jnim-is-sahel-hostile/",
    "main_home": BASE + "/",
    "main_events": BASE + "/events.html",
    "main_countries": BASE + "/countries.html",
    "main_reports": BASE + "/reports.html",
    "main_disease": BASE + "/disease-risk.html",
    "rc_home": BASE + "/previews/asip-intelligence-v1.0-rc1/intelligence/africa/",
    "public_data": BASE + "/intelligence/africa/data/country_profiles.json",
}

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "workbuddy-i3c-public-qa"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read()
            return {"status": response.status, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "body": body.decode("utf-8", "replace"), "error": None}
    except Exception as error:
        return {"status": None, "bytes": 0, "sha256": None, "body": "", "error": str(error)}

results = {}
for name, url in URLS.items():
    item = fetch(url)
    body = item.pop("body")
    item["url"] = url
    item["required_status"] = 200
    item["status_pass"] = item["status"] == 200
    if name == "public_data":
        try:
            data = json.loads(body)
            item["country_profile_count"] = len(data.get("profiles", {}))
            item["markers"] = {key: value in body for key, value in {"Niger": "尼日尔", "Tanzania": "坦桑尼亚", "government committee": "政府任命"}.items()}
        except Exception as error:
            item["json_error"] = str(error)
    if name == "main_home":
        item["navigation_markers"] = {"最新事件": "最新事件" in body, "国家": "国家" in body, "日报": "日报" in body, "传染病": "非洲传染病风险" in body, "安全情报库": "安全情报库" in body, "target": "/asip-site/intelligence/africa/" in body}
    results[name] = item
required = [name for name in URLS if name not in {"public_data"}]
status_gate = all(results[name]["status_pass"] for name in required)
marker_gate = results["public_data"].get("country_profile_count") == 13 and all(results["public_data"].get("markers", {}).values())
main_gate = all(results["main_home"].get("navigation_markers", {}).values())
record = {
    "artifact": "I3C_PUBLIC_PRODUCTION_CONTENT_MARKER_CHECK",
    "base_url": BASE,
    "urls_checked": len(URLS),
    "results": results,
    "status_gate": "PASS" if status_gate else "OPEN",
    "content_marker_gate": "PASS" if marker_gate else "OPEN",
    "main_navigation_gate": "PASS" if main_gate else "OPEN",
    "gate": "PASS" if status_gate and marker_gate and main_gate else "OPEN",
}
(OUT / "production-public-marker-check.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"urls_checked": len(URLS), "status_gate": record["status_gate"], "content_marker_gate": record["content_marker_gate"], "main_navigation_gate": record["main_navigation_gate"], "gate": record["gate"]}, ensure_ascii=False))
