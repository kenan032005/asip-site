import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "intelligence" / "africa"
OUT = ROOT / "qa-artifacts-i3c"
OUT.mkdir(exist_ok=True)

FILES = [
    "countries.json", "country_profiles.json", "entities.json", "entity_profiles.json",
    "relationships.json", "relation_profiles.json", "relation_timelines.json", "sources.json",
    "evidence_records.json", "regions.json", "relation_types.json",
]

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))

def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()

hashes = {name: sha256(DATA / name) for name in FILES}
counts = {
    "countries": len(load("countries.json").get("countries", [])),
    "country_profiles": len(load("country_profiles.json")),
    "entities": len(load("entities.json").get("entities", [])),
    "entity_profiles": len(load("entity_profiles.json")),
    "relationships": len(load("relationships.json").get("relationships", [])),
    "relation_profiles": len(load("relation_profiles.json").get("profiles", [])),
    "relation_timelines": sum(len(value) for value in load("relation_timelines.json").get("timelines", {}).values()),
    "sources": len(load("sources.json").get("sources", [])),
    "evidence": len(load("evidence_records.json").get("evidence", [])),
    "regions": len(load("regions.json").get("regions", [])),
    "relation_types": len(load("relation_types.json").get("relation_types", [])),
}
metrics = load("catalog_metrics.json")
record = {
    "artifact": "I3C_V10_FROZEN_KNOWLEDGE_DATA",
    "baseline_commit": git("rev-parse", "HEAD"),
    "branch": git("branch", "--show-current"),
    "data_directory": "data/intelligence/africa",
    "files": hashes,
    "counts": counts,
    "catalog_metrics": {
        "country_count": metrics.get("country_count"),
        "non_country_entity_count": metrics.get("non_country_entity_count"),
        "relationship_count": metrics.get("relationship_count"),
        "route_count": metrics.get("route_count"),
        "source_count": metrics.get("source_count"),
        "evidence_count": metrics.get("evidence_count"),
    },
    "gate": "PASS" if git("rev-parse", "HEAD") == "ef967889f64ae70e295935eb28a2aec7c46d96f7" else "FAIL",
}
(OUT / "v10-frozen-data-hashes.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record, ensure_ascii=False))
