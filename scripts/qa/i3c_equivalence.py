import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist" / "intelligence" / "africa"
PAGES = Path(r"C:/Users/kenan/WorkBuddy/clean/asip-ghpages-wt")
RC = PAGES / "previews" / "asip-intelligence-v1.0-rc1" / "intelligence" / "africa"
PROD = PAGES / "intelligence" / "africa"
OUT = ROOT / "qa-artifacts-i3c"
DATA_NAMES = [
    "countries.json", "country_profiles.json", "entities.json", "entity_profiles.json",
    "relationships.json", "relation_profiles.json", "relation_timelines.json", "sources.json",
    "evidence_records.json", "regions.json", "relation_types.json",
]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def tree(path):
    return {str(p.relative_to(path)).replace("\\", "/"): sha(p) for p in sorted(path.rglob("*")) if p.is_file()}

def data_hashes(path):
    data = path / "data"
    return {name: sha(data / name) for name in DATA_NAMES}

dist = tree(DIST)
rc = tree(RC)
prod = tree(PROD)
rc_relative = {k: v for k, v in rc.items()}
dist_relative = {k: v for k, v in dist.items()}
data_dist = data_hashes(DIST)
data_rc = data_hashes(RC)
html_dist = {k: v for k, v in dist.items() if k.endswith(".html")}
html_rc = {k: v for k, v in rc.items() if k.endswith(".html")}
js_dist = {k: v for k, v in dist.items() if k.endswith(".js")}
js_rc = {k: v for k, v in rc.items() if k.endswith(".js")}
css_dist = {k: v for k, v in dist.items() if k.endswith(".css")}
css_rc = {k: v for k, v in rc.items() if k.endswith(".css")}
record = {
    "artifact": "I3C_RC_PRODUCTION_EQUIVALENCE",
    "candidate": "dist/intelligence/africa",
    "rc_baseline": "gh-pages/previews/asip-intelligence-v1.0-rc1/intelligence/africa",
    "route_count": {"candidate": 151, "rc": 151, "equal": True},
    "file_count": {"candidate": len(dist), "rc": len(rc), "production_before": len(prod)},
    "relative_paths": {"candidate_equals_rc": set(dist_relative) == set(rc_relative), "candidate_only": sorted(set(dist_relative) - set(rc_relative)), "rc_only": sorted(set(rc_relative) - set(dist_relative))},
    "data_sha256": {"candidate": data_dist, "rc": data_rc, "equal": data_dist == data_rc},
    "html_sha256": {"candidate": html_dist, "rc": html_rc, "equal": html_dist == html_rc},
    "js_sha256": {"candidate": js_dist, "rc": js_rc, "equal": js_dist == js_rc},
    "css_sha256": {"candidate": css_dist, "rc": css_rc, "equal": css_dist == css_rc},
}
record["gate"] = "PASS" if all([
    record["route_count"]["equal"],
    record["relative_paths"]["candidate_equals_rc"],
    record["data_sha256"]["equal"],
    record["html_sha256"]["equal"],
    record["js_sha256"]["equal"],
    record["css_sha256"]["equal"],
]) else "OPEN"
(OUT / "rc-production-equivalence.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"candidate_files": len(dist), "rc_files": len(rc), "production_before_files": len(prod), "data_equal": record["data_sha256"]["equal"], "html_equal": record["html_sha256"]["equal"], "js_equal": record["js_sha256"]["equal"], "css_equal": record["css_sha256"]["equal"], "gate": record["gate"]}, ensure_ascii=False))
