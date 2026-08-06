#!/usr/bin/env python3
"""Generate the ASIP intelligence delivery commit manifests.

Produces:
  reports/intelligence/i2a_commit_manifest.json
  reports/intelligence/i2b_commit_manifest.json (starts empty, filled by I2-B)

Each entry:
  commit, parent, subject, authored_at, committed_at, branch, tag, remote_verified
"""
import json
import os
import subprocess
import sys

repo = sys.argv[1] if len(sys.argv) > 1 else "."

I2A_HEAD = "2a70a282bc163c7d5ef4704c6c987e1acf7f8a0f"
I2A_TAG = "asip-intelligence-v0.2"
I2B_BRANCH = "feature/asip-intelligence-v10-trust-audit"


def run(args):
    r = subprocess.run(["git", "-C", repo] + args, capture_output=True, text=True)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def fmt(ts):
    return ts.replace("T", " ").split("+")[0].split(".")[0]


def collect(start, stop):
    """Collect commits from `stop` (inclusive) back until `start` (inclusive)."""
    out = []
    code, stdout, _ = run(["log", "--format=%H %P %s%x09%aI%x09%cI", f"{stop}..." if False else stop, "--topo-order"])
    # simpler: walk by first-parent from stop until we hit start
    cur = stop
    while True:
        code, info, err = run(["log", "-1", "--format=%H%x09%P%x09%s%x09%aI%x09%cI", cur])
        if code != 0 or not info:
            break
        parts = info.split("\t")
        sha, parents, subject, a_iso, c_iso = (parts + [""] * 5)[:5]
        out.append({"commit": sha, "parent": parents, "subject": subject,
                    "authored_at": fmt(a_iso), "committed_at": fmt(c_iso)})
        if sha == start:
            break
        first_parent = parents.split()[0] if parents else None
        if not first_parent:
            break
        cur = first_parent
    return out


def main():
    # --- I2-A manifest: from v0.2 tag (d5899d6, I1-B final) up to I2-A HEAD ---
    i2a = collect("d5899d6e50d39a91334f0181a1f2b3966a9173de", I2A_HEAD)
    # annotate branches/tags
    code, stdout, _ = run(["branch", "--contains", I2A_HEAD])
    branches = [b.strip().lstrip("*").strip() for b in stdout.splitlines() if b.strip()]
    code, stdout, _ = run(["tag", "--contains", I2A_HEAD])
    tags = [t.strip() for t in stdout.splitlines() if t.strip()]
    for entry in i2a:
        entry["branch"] = branches if entry["commit"] == I2A_HEAD else []
        entry["tag"] = [t for t in tags if t]
        entry["remote_verified"] = entry["commit"] != I2A_HEAD or True  # refined below

    # remote verification for I2A_HEAD
    code, stdout, _ = run(["ls-remote", "--heads", "origin", "feature/asip-intelligence-v10-foundation"])
    remote_i2a = stdout.split("\t")[0] if stdout else ""
    code, stdout, _ = run(["ls-remote", "--tags", "origin", I2A_TAG, I2A_TAG + "^{}"])
    remote_tag_obj = ""
    for line in stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and parts[1] == f"refs/tags/{I2A_TAG}^{{}}":
            remote_tag_obj = parts[0]
    for entry in i2a:
        entry["remote_verified"] = (
            entry["commit"] == I2A_HEAD and remote_i2a == I2A_HEAD
        )
    i2a_meta = {
        "schema_version": "asip-delivery-manifest-v1",
        "i2a_baseline_commit": "d5899d6e50d39a91334f0181a1f2b3966a9173de",
        "i2a_baseline_label": "I1-B final (asip-intelligence-v0.2)",
        "i2a_remote_branch": "feature/asip-intelligence-v10-foundation",
        "i2a_remote_head": remote_i2a,
        "i2a_tag": I2A_TAG,
        "i2a_tag_object": remote_tag_obj,
        "i2b_branch": I2B_BRANCH,
        "commits": i2a,
    }

    # --- I2-B manifest: commits on current branch beyond I2-A HEAD ---
    code, stdout, _ = run(["log", "--format=%H %P %s", f"{I2A_HEAD}..HEAD", "--topo-order"])
    i2b_commits = []
    for line in stdout.splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3:
            i2b_commits.append({"commit": parts[0], "parent": parts[1], "subject": parts[2]})
    i2b_meta = {
        "schema_version": "asip-delivery-manifest-v1",
        "i2b_start": I2A_HEAD,
        "i2b_branch": I2B_BRANCH,
        "commits": i2b_commits,
    }

    out_dir = os.path.join(repo, "reports", "intelligence")
    os.makedirs(out_dir, exist_ok=True)
    p1 = os.path.join(out_dir, "i2a_commit_manifest.json")
    p2 = os.path.join(out_dir, "i2b_commit_manifest.json")
    with open(p1, "w", encoding="utf-8") as f:
        json.dump(i2a_meta, f, ensure_ascii=False, indent=1)
    with open(p2, "w", encoding="utf-8") as f:
        json.dump(i2b_meta, f, ensure_ascii=False, indent=1)
    print("i2a manifest:", p1)
    print("i2b manifest:", p2)
    print("I2-A remote head:", remote_i2a)
    print("I2-A tag object:", remote_tag_obj)
    print("I2-A commit count:", len(i2a))
    for e in i2a:
        print(" ", e["commit"][:10], e["parent"][:10] if e["parent"] else "-", e["subject"])
    print("I2-B commits so far:", len(i2b_commits))


if __name__ == "__main__":
    main()
