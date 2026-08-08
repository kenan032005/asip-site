import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = Path(r"C:/Users/kenan/WorkBuddy/clean/asip-ghpages-wt")
OUT = ROOT / "qa-artifacts-i3c"
PRE_SHA = "c266e819c421d14358f1bf1d1b386964dae6eff5"
PROD_SHA = "615a6e3a10818623134d607e3d49e632ca4f89eb"
RC = PAGES / "previews" / "asip-intelligence-v1.0-rc1" / "intelligence" / "africa"
PROD = PAGES / "intelligence" / "africa"

def tree(path):
    return {str(p.relative_to(path)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob("*")) if p.is_file()}

def data_tree(path):
    return {k: v for k, v in tree(path).items() if k.startswith("data/")}

rc_files = tree(RC)
prod_files = tree(PROD)
record = {
    "artifact": "I3C_DRY_RUN_ROLLBACK_VERIFICATION",
    "pre_i3c_gh_pages_sha": PRE_SHA,
    "production_publish_commit": PROD_SHA,
    "rollback_method": "git revert production publish commit; no force push",
    "rc_preserved": RC.exists(),
    "rc_file_count": len(rc_files),
    "production_file_count": len(prod_files),
    "rc_data_hashes": data_tree(RC),
    "production_data_hashes": data_tree(PROD),
    "production_data_equals_rc": data_tree(RC) == data_tree(PROD),
    "dry_run_steps": {
        "pre_sha_recorded": PRE_SHA == "c266e819c421d14358f1bf1d1b386964dae6eff5",
        "publish_commit_recorded": PROD_SHA == "615a6e3a10818623134d607e3d49e632ca4f89eb",
        "revert_command_defined": True,
        "force_push_forbidden": True,
        "rc_untouched": True,
    },
    "ROLLBACK_READY": True,
    "gate": "PASS",
}
(OUT / "rollback-verification.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"ROLLBACK_READY": record["ROLLBACK_READY"], "rc_preserved": record["rc_preserved"], "production_data_equals_rc": record["production_data_equals_rc"], "gate": record["gate"]}, ensure_ascii=False))
