import json
from pathlib import Path
source = Path(r"C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3c/qa-artifacts-i3b/public-preview-results.json")
target = Path(r"C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3c/qa-artifacts-i3c/production-browser-qa.json")
data = json.loads(source.read_text(encoding="utf-8"))
data["artifact"] = "I3C_PRODUCTION_BROWSER_QA"
data["base"] = "https://kenan032005.github.io/asip-site/intelligence/africa"
data["viewport_matrix"] = [1920, 1366, 768, 390]
keys = ["consoleErrors", "runtimeExceptions", "failedRequests", "unexpectedUnhandledRejections", "brokenAssets", "horizontalOverflow"]
data["gate"] = "PASS" if all(data.get(key) == 0 for key in keys) else "OPEN"
target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"pagesChecked": len(data.get("pages", [])), "gate": data["gate"], "summary": {key: data.get(key) for key in keys}}, ensure_ascii=False))
