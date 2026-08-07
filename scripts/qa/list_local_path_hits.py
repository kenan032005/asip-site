import json
import os
import re
from pathlib import Path

ROOT = Path(r"C:/Users/kenan/WorkBuddy/clean/asip-intelligence-v10-trusted")
WIN = re.compile(r"[A-Za-z]:(?:\\\\|\\\\|/)+Users(?:\\\\|\\\\|/)+[A-Za-z0-9_.-]+(?:[^\\s\"'<>]*)")
POSIX = re.compile(r"/(?:home|Users)/[A-Za-z0-9_.-]+/(?:[^\\s\"'<>]*)")
EXTS = {".py", ".json", ".md", ".html", ".css", ".js", ".txt", ".yml", ".yaml", ".xml", ".csv", ".gitignore"}
SKIP = {".git", "__pycache__", "node_modules", "backup", ".workbuddy"}

def category(rel):
    if rel.startswith("dist/") or rel.startswith("previews/") or rel.startswith("intelligence/") or rel.startswith("assets/"):
        return "PUBLIC_DEPLOYABLE"
    if rel.startswith("data/intelligence/africa/") or rel.startswith("scripts/gen/") or rel.startswith("scripts/tests/"):
        return "CURRENT_SOURCE"
    if rel.startswith("release/i3b-rc1/"):
        return "CURRENT_RELEASE_ARTIFACT"
    if rel.startswith("qa-artifacts-i3b-fix1c/"):
        return "CURRENT_QA"
    if rel.startswith("qa-artifacts-") or rel.startswith("i0c-") or "I3A" in rel or "I3B" in rel or "I2B" in rel or "I2A" in rel:
        return "HISTORICAL_QA" if rel.endswith((".json", ".js")) else "HISTORICAL_ACCEPTANCE"
    if rel.startswith("scripts/"):
        return "DEVELOPMENT_SCRIPT"
    return "OTHER"

def loc_json(text, match):
    try:
        obj = json.loads(text)
    except Exception:
        return None
    def walk(v, path="$", parent=None):
        if isinstance(v, dict):
            for k, x in v.items():
                found = walk(x, f"{path}.{k}", v)
                if found: return found
        elif isinstance(v, list):
            for i, x in enumerate(v):
                found = walk(x, f"{path}[{i}]", v)
                if found: return found
        elif isinstance(v, str) and match in v:
            return path
        return None
    return walk(obj)

hits=[]
for dp, dns, fns in os.walk(ROOT):
    dns[:] = [d for d in dns if d not in SKIP and not d.startswith(".")]
    for fn in fns:
        p=Path(dp)/fn
        if p.suffix.lower() not in EXTS and fn != ".gitignore": continue
        rel=p.relative_to(ROOT).as_posix()
        try: text=p.read_text(encoding="utf-8", errors="replace")
        except OSError: continue
        for pat in (WIN, POSIX):
            m=pat.search(text)
            if m:
                line=text[:m.start()].count("\n")+1
                hits.append({"file":rel,"line":line,"json_path":loc_json(text,m.group(0)) if p.suffix.lower()==".json" else None,"matched_path":m.group(0),"file_category":category(rel)})
                break
print(json.dumps(hits, ensure_ascii=False, indent=2))
