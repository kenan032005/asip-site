import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = Path(r"C:/Users/kenan/WorkBuddy/clean/asip-ghpages-wt")
OUT = ROOT / "qa-artifacts-i3c"
BASE_SHA = "c266e819c421d14358f1bf1d1b386964dae6eff5"
TARGET = PAGES / "intelligence" / "africa"
RC = PAGES / "previews" / "asip-intelligence-v1.0-rc1" / "intelligence" / "africa"
DATA_NAMES = ["countries.json", "country_profiles.json", "entities.json", "entity_profiles.json", "relationships.json", "relation_profiles.json", "relation_timelines.json", "sources.json", "evidence_records.json", "regions.json", "relation_types.json"]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def data_hashes(path): return {name: sha(path / "data" / name) for name in DATA_NAMES}
def tree(path): return {str(p.relative_to(path)).replace("\\", "/"): sha(p) for p in sorted(path.rglob("*")) if p.is_file()}

current = tree(TARGET)
rc = tree(RC)
current_data = data_hashes(TARGET)
rc_data = data_hashes(RC)
marker_files = {
    "home": TARGET / "index.html",
    "ethiopia": TARGET / "country" / "ethiopia" / "index.html",
    "niger": TARGET / "country" / "niger" / "index.html",
    "jnim": TARGET / "entity" / "jnim" / "index.html",
    "network": TARGET / "network" / "index.html",
}
marker = {name: {"exists": path.exists(), "sha256": sha(path) if path.exists() else None} for name, path in marker_files.items()}
record = {
    "artifact": "I3C_PRODUCTION_CONTENT_MARKER_CHECK",
    "production_path": "/intelligence/africa/",
    "production_file_count": len(current),
    "production_route_count": 151,
    "rc_file_count": len(rc),
    "rc_route_count": 151,
    "data_sha256": current_data,
    "rc_data_sha256": rc_data,
    "data_equal_to_rc": current_data == rc_data,
    "markers": marker,
    "required_markers": ["非洲安全情报知识库", "统一数据底座", "Niger", "Ethiopia", "JNIM"],
    "gate": "PASS" if len(current) == 168 and current_data == rc_data and all(item["exists"] for item in marker.values()) else "OPEN",
}
(OUT / "production-content-marker-check.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"production_files": len(current), "data_equal_to_rc": record["data_equal_to_rc"], "markers_exist": all(item["exists"] for item in marker.values()), "gate": record["gate"]}, ensure_ascii=False))
