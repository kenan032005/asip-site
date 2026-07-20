#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASIP → GitHub Pages 一次性初始化（零依赖，仅需 Python 标准库 + git）。

流程：创建仓库 -> 构建 dist/ -> 推送到 gh-pages -> 开启 Pages。
固定公网地址形如 https://<用户>.github.io/<仓库>/

所需：一个具有 repo 权限的 GitHub Personal Access Token
      （https://github.com/settings/tokens，勾选 repo）。
密钥仅在本机使用，不会被写入任何文件（除非你显式保存配置）。

用法：
  python tools/setup_gh_pages.py
  GITHUB_TOKEN=ghp_xxx GITHUB_USER=kenan032005 python tools/setup_gh_pages.py

交互提示会询问：令牌、用户名、仓库名（默认 asip-site）、是否私有。
"""
import os
import sys
import json
import shutil
import subprocess
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
API = "https://api.github.com"


def api_req(method, url, token, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, method=method)
    req.add_header("Authorization", "token " + token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode() or "{}"
    except urllib.error.HTTPError as e:
        raise SystemExit("GitHub API 错误 %s: %s" % (e.code, e.read().decode()[:300]))


def main():
    token = os.environ.get("GITHUB_TOKEN") or input("粘贴 GitHub Personal Access Token（需 repo 权限）：").strip()
    if not token:
        raise SystemExit("未提供令牌，已退出。")
    user = os.environ.get("GITHUB_USER") or input("GitHub 用户名 [默认 kenan032005]：").strip() or "kenan032005"
    repo = input("仓库名 [默认 asip-site]：").strip() or "asip-site"
    private = input("是否创建私有仓库？(y/N)：").strip().lower() == "y"

    # 0) 确保已构建
    if not os.path.isdir(DIST):
        print("未找到 dist/，先构建…")
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_site.py")], check=True)

    # 1) 创建仓库（已存在则忽略）
    print("[1/5] 创建仓库 %s/%s …" % (user, repo))
    try:
        api_req("POST", API + "/user/repos", token, {
            "name": repo, "private": private,
            "description": "非洲地区社会安全信息平台 Africa Security Information Platform",
            "auto_init": False,
        })
    except SystemExit as e:
        if "422" in str(e):
            print("      仓库已存在，继续。")
        else:
            raise

    # 2) 推送 dist -> gh-pages
    print("[2/5] 推送静态站点到 gh-pages …")
    remote = "https://%s:%s@github.com/%s/%s.git" % (user, token, user, repo)
    work = os.path.join(ROOT, ".deploy_tmp")
    if os.path.isdir(work):
        shutil.rmtree(work)
    shutil.copytree(DIST, work)
    subprocess.run(["git", "init"], cwd=work, check=True)
    subprocess.run(["git", "checkout", "-b", "gh-pages"], cwd=work, check=True)
    subprocess.run(["git", "add", "-A"], cwd=work, check=True)
    subprocess.run(["git", "commit", "-m", "Initial ASIP site"], cwd=work, check=True)
    # 若已存在 gh-pages，使用当前令牌远程强制更新
    subprocess.run(["git", "remote", "set-url", "origin", remote], cwd=work, check=True)
    try:
        subprocess.run(["git", "push", "-f", "-u", "origin", "gh-pages"], cwd=work, check=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # 3) 开启 Pages
    print("[3/5] 开启 GitHub Pages …")
    api_req("POST", API + "/repos/%s/%s/pages" % (user, repo), token,
            {"source": {"branch": "gh-pages", "path": "/"}})
    info = json.loads(api_req("GET", API + "/repos/%s/%s/pages" % (user, repo), token))
    url = info.get("html_url", "https://%s.github.io/%s/" % (user, repo))

    print("\n✅ 初始化完成！")
    print("   仓库：", "https://github.com/%s/%s" % (user, repo))
    print("   公网地址：", url)
    print("   注意：Pages 首次构建通常需 1~3 分钟，请稍后访问。")


if __name__ == "__main__":
    main()
