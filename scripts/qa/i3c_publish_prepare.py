import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist" / "intelligence" / "africa"
PAGES = Path(r"C:/Users/kenan/WorkBuddy/clean/asip-ghpages-wt")
PROD = PAGES / "intelligence" / "africa"
OUT = ROOT / "qa-artifacts-i3c"

WHITELIST = {
    "intelligence/africa/**": "publish frozen ASIP Intelligence V1.0 routes and data",
    "assets/js/common.js": "add one main-site navigation entry: 安全情报库",
    "assets/js/intelligence/africa.js": "mark the published intelligence frontend as V1.0 production",
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def files(path):
    return {str(p.relative_to(path)).replace("\\", "/"): sha(p) for p in sorted(path.rglob("*")) if p.is_file()} if path.exists() else {}

def allowed(path):
    return path.startswith("intelligence/africa/") or path in {"assets/js/common.js", "assets/js/intelligence/africa.js"}

candidate_all = files(ROOT / "dist")
existing_all = files(PAGES)
scoped = {k for k in candidate_all if k.startswith("intelligence/africa/") or k in {"assets/js/common.js", "assets/js/intelligence/africa.js"}}
candidate = {k: candidate_all[k] for k in scoped}
existing = {k: existing_all[k] for k in set(existing_all) if k.startswith("intelligence/africa/") or k in {"assets/js/common.js", "assets/js/intelligence/africa.js"}}
added = sorted(k for k in candidate if k not in existing)
modified = sorted(k for k in candidate if k in existing and candidate[k] != existing[k])
deleted = sorted(k for k in existing if k.startswith("intelligence/africa/") and k not in candidate)
all_changes = sorted(set(added) | set(modified) | set(deleted))
unexpected_added = [p for p in added if not allowed(p)]
unexpected_modified = [p for p in modified if not allowed(p)]
unexpected_deleted = [p for p in deleted if not allowed(p)]
record = {
    "artifact": "I3C_PRODUCTION_CHANGE_WHITELIST",
    "whitelist": WHITELIST,
    "candidate_root": "dist",
    "production_root": "gh-pages root",
    "added_count": len(added),
    "modified_count": len(modified),
    "deleted_count": len(deleted),
    "added": added,
    "modified": modified,
    "deleted": deleted,
    "unexpected_new": unexpected_added,
    "unexpected_modified": unexpected_modified,
    "unexpected_deleted": unexpected_deleted,
    "existing_deleted": len(deleted),
    "gate": "PASS" if not unexpected_added and not unexpected_modified and not unexpected_deleted else "OPEN",
}
(OUT / "production-change-whitelist.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(OUT / "production-diff.json").write_text(json.dumps({
    "artifact": "I3C_PRODUCTION_DIFF",
    "UNEXPECTED_NEW": len(unexpected_added),
    "UNEXPECTED_MODIFIED": len(unexpected_modified),
    "UNEXPECTED_DELETED": len(unexpected_deleted),
    "existing_deleted": len(deleted),
    "paths": {"added": added, "modified": modified, "deleted": deleted},
    "gate": record["gate"],
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
rollback = {
    "artifact": "I3C_ROLLBACK_PLAN",
    "pre_i3c_gh_pages_sha": "c266e819c421d14358f1bf1d1b386964dae6eff5",
    "normal_rollback": "git revert <I3-C production publish commit>; push gh-pages normally; never force-push",
    "file_restore_fallback": "restore only the whitelist paths from PRE_I3C_GH_PAGES_SHA, create a new rollback commit, and push normally",
    "rc_preservation": "do not modify or delete previews/asip-intelligence-v1.0-rc1/",
    "dry_run_steps": ["verify whitelist path set", "verify production target is the only intelligence publish scope", "verify RC remains unchanged", "verify revert target commit is available"],
    "rollback_ready": True,
}
(OUT / "rollback-plan.json").write_text(json.dumps(rollback, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if record["gate"] != "PASS":
    raise SystemExit(json.dumps({"gate": record["gate"], "unexpected": {"new": unexpected_added, "modified": unexpected_modified, "deleted": unexpected_deleted}}, ensure_ascii=False))

# Sync only the candidate site subtree and the two required shared frontend assets.
for source, target in [
    (ROOT / "dist" / "intelligence" / "africa", PAGES / "intelligence" / "africa"),
    (ROOT / "dist" / "assets" / "js" / "common.js", PAGES / "assets" / "js" / "common.js"),
    (ROOT / "dist" / "assets" / "js" / "intelligence" / "africa.js", PAGES / "assets" / "js" / "intelligence" / "africa.js"),
]:
    if source.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

print(json.dumps({
    "gate": record["gate"],
    "added": len(added),
    "modified": len(modified),
    "deleted": len(deleted),
    "unexpected_new": len(unexpected_added),
    "unexpected_modified": len(unexpected_modified),
    "unexpected_deleted": len(unexpected_deleted),
    "synced": True,
}, ensure_ascii=False))
