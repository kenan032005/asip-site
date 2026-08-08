import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "qa-artifacts-i3c"
record = {
    "artifact": "I3C_FINAL_GATES",
    "baseline_commit": "ef967889f64ae70e295935eb28a2aec7c46d96f7",
    "source_branch": "feature/asip-intelligence-v10-i3c-production",
    "source_head": "673390223c9c3e351e90d1556c98fe4f7878cd03",
    "gh_pages_publish_commit": "615a6e3a10818623134d607e3d49e632ca4f89eb",
    "workflow": {"name": "pages build and deployment", "run_id": 31246682879, "run_number": 161, "conclusion": "success"},
    "deployment": {"id": 5806748646, "commit": "615a6e3a10818623134d607e3d49e632ca4f89eb", "state": "success", "environment_url": "https://kenan032005.github.io/asip-site/"},
    "public_url": "https://kenan032005.github.io/asip-site/intelligence/africa/",
    "rc_url": "https://kenan032005.github.io/asip-site/previews/asip-intelligence-v1.0-rc1/intelligence/africa/",
    "gates": {
        "I3C_BASELINE_GATE": "PASS",
        "I3C_REGRESSION_GATE": "PASS",
        "I3C_PRODUCTION_DIFF_GATE": "PASS",
        "I3C_DEPLOYMENT_GATE": "PASS",
        "I3C_PUBLIC_QA_GATE": "PASS",
        "I3C_MAIN_SITE_GATE": "OPEN",
        "I3C_DATA_FREEZE_GATE": "PASS",
        "I3C_ROLLBACK_GATE": "PASS",
    },
    "blocking_issue": "主站首页公网仍返回旧的静态首页 HTML；虽然 assets/js/common.js 已发布并包含安全情报库入口，但当前主页 HTML 未能完成可复核的导航呈现，因此主站 Gate 暂不关闭。",
    "overall_gate": "OPEN",
}
(OUT / "final-gates.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"overall_gate": record["overall_gate"], "I3C_MAIN_SITE_GATE": record["gates"]["I3C_MAIN_SITE_GATE"]}, ensure_ascii=False))
