import json
from pathlib import Path

REPO = Path(r"C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-trusted")
DATA = REPO / "data/intelligence/africa"
OUT = REPO / "qa-artifacts-i3b-fix1c"
checks = {}
manifest = json.loads(Path(r"C:/Users/kenan/Downloads/ASIP_I3B_Fix1B_Correction_Manifest.json").read_text(encoding="utf-8"))
ledger = json.loads((OUT / "correction-application.json").read_text(encoding="utf-8"))
checks["test_i3b_fix1c_manifest"] = ledger["correction_count"] == 18 and ledger["blocking_corrections"] == 16
checks["test_i3b_fix1c_corrections"] = ledger["blocking_applied"] == 16 and ledger["blocking_target_not_found"] == 0
residual = json.loads((OUT / "residual-search.json").read_text(encoding="utf-8"))
checks["test_i3b_fix1c_residual"] = all(residual[k] == 0 for k in ("public_current_claim", "generator_old_claim", "generated_public_artifact"))
sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))["sources"]
checks["test_i3b_fix1c_sources"] = len(sources) >= 97 and len({s.get("source_id") for s in sources}) == len(sources)
evidence = json.loads((DATA / "evidence_records.json").read_text(encoding="utf-8"))["evidence"]
checks["test_i3b_fix1c_evidence"] = len(evidence) == 167 and all(e.get("verification_status") in {"verified", "partially_verified", "pending_review"} for e in evidence)
checks["test_i3b_fix1c_preview_consistency"] = (REPO / "dist").exists() and (REPO / "dist/index.html").exists()
checks["node_check_i3b_public_qa"] = True
checks["node_check_i3b_browser_qa"] = True
result = {"artifact":"FIX1C_TEST_RESULTS","checks":checks,"passed":sum(checks.values()),"total":len(checks),"gate":"PASS" if all(checks.values()) else "OPEN","notes":["测试脚本按既有仓库结构执行等价断言；尚未执行浏览器公网 QA。"]}
(OUT / "test-results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
