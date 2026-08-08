import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = Path(r"C:/Users/kenan/WorkBuddy/clean/asip-ghpages-wt")
OUT = ROOT / "qa-artifacts-i3c"
OUT.mkdir(exist_ok=True)

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git(*args):
    return subprocess.check_output(["git", "-C", str(PAGES), *args], text=True).strip()

def manifest_tree(path):
    if not path.exists():
        return {"exists": False, "file_count": 0, "files": {}}
    files = {}
    for item in sorted(path.rglob("*")):
        if item.is_file():
            rel = str(item.relative_to(path)).replace("\\", "/")
            files[rel] = {"sha256": sha256(item), "bytes": item.stat().st_size}
    return {"exists": True, "file_count": len(files), "files": files}

tracked = git("ls-files").splitlines()
root_files = [p for p in tracked if "/" not in p]
intel_files = [p for p in tracked if p.startswith("intelligence/africa/")]
record = {
    "artifact": "I3C_GH_PAGES_PRE_PRODUCTION_BASELINE",
    "worktree": str(PAGES),
    "remote": git("remote", "get-url", "origin"),
    "branch": git("branch", "--show-current") or "DETACHED",
    "pre_i3c_gh_pages_sha": git("rev-parse", "HEAD"),
    "working_tree_clean": not bool(git("status", "--porcelain")),
    "tracked_root_file_count": len(root_files),
    "tracked_intelligence_africa_file_count": len(intel_files),
    "production_target": manifest_tree(PAGES / "intelligence" / "africa"),
    "rc_target": manifest_tree(PAGES / "previews" / "asip-intelligence-v1.0-rc1" / "intelligence" / "africa"),
    "main_site_baseline": {
        "root_pages": [p for p in root_files if p.endswith(".html")],
        "shared_assets": [p for p in tracked if p.startswith("assets/")],
        "navigation_implementation": "assets/js/common.js",
        "navigation_entry_count": 5,
        "existing_modules": ["首页", "最新事件", "国家", "日报", "非洲传染病风险"],
        "production_navigation_entry_present": False,
        "new_navigation_entry_scope": "only add 安全情报库 -> /asip-site/intelligence/africa/",
    },
    "gate": "PENDING",
}
record["gate"] = "PASS" if record["working_tree_clean"] and record["pre_i3c_gh_pages_sha"] == "c266e819c421d14358f1bf1d1b386964dae6eff5" else "OPEN"
(OUT / "production-before-manifest.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"sha": record["pre_i3c_gh_pages_sha"], "clean": record["working_tree_clean"], "production_exists": record["production_target"]["exists"], "production_files": record["production_target"]["file_count"], "rc_files": record["rc_target"]["file_count"], "gate": record["gate"]}, ensure_ascii=False))
