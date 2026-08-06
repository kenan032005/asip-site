#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I2-B: Git delivery manifest tests.

Verifies reports/intelligence/i2a_commit_manifest.json lists the full I2-A
commit chain with real hashes, parents and remote verification; and that the
I2-A remote branch head matches the manifest.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "reports" / "intelligence" / "i2a_commit_manifest.json"
I2A_HEAD = "2a70a282bc163c7d5ef4704c6c987e1acf7f8a0f"
V02_TAG_COMMIT = "d5899d6e50d39a91334f0181a1f2b3966a9173de"

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  ({detail})")


def run(args):
    r = subprocess.run(["git", "-C", str(ROOT)] + args, capture_output=True, text=True)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def main():
    if not MANIFEST.exists():
        print("  [FAIL] manifest file missing")
        return 1
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    commits = m["commits"]

    check("manifest schema", m.get("schema_version") == "asip-delivery-manifest-v1")
    check("i2a remote branch recorded", m.get("i2a_remote_branch") == "feature/asip-intelligence-v10-foundation")
    check("i2a remote head matches", m.get("i2a_remote_head") == I2A_HEAD, str(m.get("i2a_remote_head")))
    check("i2a tag object matches", m.get("i2a_tag_object") == V02_TAG_COMMIT, str(m.get("i2a_tag_object")))
    check("i2b branch recorded", m.get("i2b_branch") == "feature/asip-intelligence-v10-trust-audit")

    # commit chain: >= 5 I2-A commits, real hashes, parents chain, subjects
    check("commit count >= 5", len(commits) >= 5, str(len(commits)))
    seen = set()
    for c in commits:
        check(f"commit hash len {c['commit'][:10]}", len(c["commit"]) == 40)
        check(f"commit unique {c['commit'][:10]}", c["commit"] not in seen)
        seen.add(c["commit"])
        check(f"commit subject {c['commit'][:10]}", bool(c.get("subject")))
        check(f"commit authored_at {c['commit'][:10]}", bool(c.get("authored_at")))
        check(f"commit committed_at {c['commit'][:10]}", bool(c.get("committed_at")))
        check(f"parent chain {c['commit'][:10]}", bool(c.get("parent")), "parent empty")
    # chain starts at v0.2 baseline (d5899d6 itself is the I1-B/v0.2 tag commit)
    last = commits[-1]
    check("chain starts at v0.2 baseline commit", last["commit"] == V02_TAG_COMMIT, last["commit"][:10])
    check("chain baseline has parent (I1-B)", bool(last.get("parent")), last.get("parent", ""))
    last = commits[0]
    check("chain ends at I2-A head", last["commit"] == I2A_HEAD, last["commit"][:10])
    check("head remote_verified true", last.get("remote_verified") is True)

    # cross-check with git log
    code, out, err = run(["log", "--format=%H", "-1", "2a70a282bc163c7d5ef4704c6c987e1acf7f8a0f"])
    check("git can resolve I2-A head", code == 0 and out == I2A_HEAD)

    print(f"\ntest_git_delivery_manifest: PASS={PASS} FAIL={FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
