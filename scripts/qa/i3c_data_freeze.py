import json
import hashlib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "qa-artifacts-i3c"
BASE = "https://kenan032005.github.io/asip-site"
DATA_NAMES = ["countries.json", "country_profiles.json", "entities.json", "entity_profiles.json", "relationships.json", "relation_profiles.json", "relation_timelines.json", "sources.json", "evidence_records.json", "regions.json", "relation_types.json"]

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "workbuddy-i3c-data-freeze"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()

def hashes(prefix):
    return {name: hashlib.sha256(fetch(f"{prefix}/intelligence/africa/data/{name}")).hexdigest() for name in DATA_NAMES}

rc = hashes(BASE + "/previews/asip-intelligence-v1.0-rc1")
prod = hashes(BASE)
record = {
    "artifact": "I3C_PUBLIC_DATA_FREEZE_RECHECK",
    "rc_data_sha256": rc,
    "production_data_sha256": prod,
    "knowledge_data_changed": int(rc != prod),
    "KNOWLEDGE_DATA_CHANGED": int(rc != prod),
    "gate": "PASS" if rc == prod else "OPEN",
}
(OUT / "production-data-freeze-recheck.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"KNOWLEDGE_DATA_CHANGED": record["KNOWLEDGE_DATA_CHANGED"], "gate": record["gate"]}, ensure_ascii=False))
