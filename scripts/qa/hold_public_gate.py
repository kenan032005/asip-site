import json
from pathlib import Path
path = Path(r"C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3c/qa-artifacts-i3c/final-gates.json")
data = json.loads(path.read_text(encoding="utf-8"))
data["gates"]["I3C_PUBLIC_QA_GATE"] = "OPEN"
data["overall_gate"] = "OPEN"
data["blocking_issue"] = "正式生产 79 页浏览器回归的 3 个 runtime exceptions 与 Network 交互检查仍未完全通过；Node/CDP 实际运行结果为 consoleErrors=0、failedRequests=0、horizontalOverflow=0，但 node_click_focus_switch=false，不能关闭公网 QA Gate。"
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"overall_gate": data["overall_gate"], "public_qa_gate": data["gates"]["I3C_PUBLIC_QA_GATE"]}, ensure_ascii=False))
