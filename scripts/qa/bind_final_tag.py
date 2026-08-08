import json
import subprocess
from pathlib import Path
root = Path(r"C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-i3c")
sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
path = root / "qa-artifacts-i3c" / "final-gates.json"
data = json.loads(path.read_text(encoding="utf-8"))
data["source_head"] = sha
data["tag"] = "asip-intelligence-v1.0"
data["tag_object_sha"] = "45856a210b0327f56e9a40f82e5a85d2902c5ebd"
data["tag_peeled_commit_sha"] = sha
data["tag_remote"] = "origin/asip-intelligence-v1.0"
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"source_head": sha, "overall_gate": data["overall_gate"], "tag": data["tag"]}, ensure_ascii=False))
