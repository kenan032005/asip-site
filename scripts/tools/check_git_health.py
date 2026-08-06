#!/usr/bin/env python3
"""ASIP Git health check (read-only).

Checks the current repository's baseline integrity without modifying any
Git state. Works with both the files ref backend and the reftable backend.

Checks:
  - valid repository
  - current branch and HEAD
  - refs storage backend and file sanity
  - remote heads vs local heads
  - unexpected root commits
  - large batches of untracked production files
  - tag targets
  - fsck result

Usage:
  python scripts/tools/check_git_health.py [repo_path]
"""
import os
import subprocess
import sys


def run(repo, args):
    r = subprocess.run(["git", "-C", repo] + args, capture_output=True, text=True)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    ok = True
    issues = []

    def check(name, cond, detail=""):
        nonlocal ok
        status = "OK " if cond else "FAIL"
        if not cond:
            ok = False
            issues.append(name)
        print(f"[{status}] {name}" + (f"  ({detail})" if detail else ""))

    gitdir = os.path.join(repo, ".git")
    check("valid .git directory", os.path.isdir(gitdir), gitdir)

    code, out, err = run(repo, ["rev-parse", "--is-inside-work-tree"])
    check("is inside work tree", code == 0 and out == "true")

    code, out, err = run(repo, ["symbolic-ref", "-q", "HEAD"])
    branch = out or "(detached)"
    check("HEAD resolves to branch", code == 0 or branch == "(detached)", branch)

    code, out, err = run(repo, ["rev-parse", "HEAD"])
    head = out or ""
    check("HEAD commit resolves", code == 0 and len(head) == 40, head[:12] if head else err[:80])

    # refs backend
    reftable_dir = os.path.join(gitdir, "reftable")
    refs_dir = os.path.join(gitdir, "refs")
    backend = "reftable" if os.path.isdir(reftable_dir) else "files"
    check("refs backend identified", backend in ("reftable", "files"), backend)
    if backend == "reftable":
        tables = os.path.join(reftable_dir, "tables.list")
        check("reftable tables.list exists", os.path.isfile(tables), tables)
        if os.path.isfile(tables):
            entries = [x for x in open(tables, encoding="utf-8").read().splitlines() if x.strip()]
            check("reftable table files present", len(entries) >= 1, f"{len(entries)} tables")

    # local vs remote heads
    code, out, err = run(repo, ["for-each-ref", "--format=%(refname) %(objectname)", "refs/heads/"])
    local_heads = dict()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            local_heads[parts[0]] = parts[1]
    check("local heads readable", len(local_heads) > 0, f"{len(local_heads)} local heads")

    code, out, err = run(repo, ["ls-remote", "--heads", "origin"])
    remote_heads = dict()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            remote_heads["refs/heads/" + parts[1]] = parts[0]
    check("remote heads reachable", len(remote_heads) > 0, f"{len(remote_heads)} remote heads")
    for ref, sha in local_heads.items():
        if ref in remote_heads and remote_heads[ref] != sha:
            check(f"local/remote sync: {ref}", False, f"local={sha[:10]} remote={remote_heads[ref][:10]}")
    print(f"      (checked {len(local_heads)} local vs {len(remote_heads)} remote heads)")

    # root commits: report them, but only FAIL for unexpected ones.
    # Known/expected roots in this repo: gh-pages orphan deploy + initial import.
    KNOWN_ROOT_SUBJECTS = (
        "deploy: publish ASIP V0.2 root tree",
        "初始化：非洲地区社会安全信息平台（独立仓库，未改动 mesip-site）",
    )
    code, out, err = run(repo, ["rev-list", "--all", "--parents"])
    root_commits = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 1:
            root_commits.append(parts[0])
    unexpected_roots = []
    for rc in root_commits:
        code2, out2, err2 = run(repo, ["log", "-1", "--format=%s", rc])
        subject = out2 or err2
        if subject not in KNOWN_ROOT_SUBJECTS:
            unexpected_roots.append((rc, subject))
        else:
            print(f"[OK ] known root commit: {rc[:10]}  ({subject})")
    check("no unexpected root commits", not unexpected_roots,
          f"{len(root_commits)} roots total; unexpected: {len(unexpected_roots)}")

    # untracked production files batch
    code, out, err = run(repo, ["status", "--porcelain=v1", "--untracked-files=all"])
    untracked = [l for l in out.splitlines() if l.startswith("??")]
    prod_untracked = [l for l in untracked if not any(
        k in l for k in ("qa-artifacts", "i1b-qa-summary", "i2a-qa-summary", "I2B_WORKTREE_MARKER", ".workbuddy/" )
    )]
    check("no large untracked production batch", len(prod_untracked) < 100, f"{len(prod_untracked)} untracked")

    # tags
    code, out, err = run(repo, ["for-each-ref", "--format=%(refname) %(objectname)", "refs/tags/"])
    tags = dict()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            tags[parts[0]] = parts[1]
    check("tags readable", len(tags) > 0, f"{len(tags)} tags")

    # fsck
    code, out, err = run(repo, ["fsck", "--full", "--no-reflogs"])
    fsck_lines = [l for l in out.splitlines() if l.strip()]
    fsck_errors = [l for l in fsck_lines if "error" in l.lower() or "fatal" in l.lower()]
    check("fsck clean", code == 0 and not fsck_errors, f"{len(fsck_lines)} lines")

    print()
    if ok:
        print("GIT HEALTH: ALL CHECKS PASSED")
        return 0
    print(f"GIT HEALTH: FAILED on: {', '.join(issues)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
