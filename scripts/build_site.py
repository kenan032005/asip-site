#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_site.py —— 构建静态站点（零依赖）。

将公开页面与数据装配到 dist/，供 GitHub Pages（gh-pages 分支）发布。
构建时会把 data/*.json 内联为 window.__DB__ 快照，使页面在无法 fetch 时
（如离线、文件协议）仍能渲染；同时保留 fetch 回退（api.js）。

输出目录 dist/ 即 GitHub Pages 站点根。

用法：
  python scripts/build_site.py
  python scripts/build_site.py --no-embed   # 不内联数据，仅复制（依赖运行时 fetch）
"""
import os
import sys
import json
import shutil
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
DATA = os.path.join(ROOT, "data")
ASSETS = os.path.join(ROOT, "assets")
REPORTS = os.path.join(ROOT, "reports")

HTML_FILES = [
    "index.html", "events.html", "event.html", "countries.html", "country.html",
    "reports.html", "report.html", "disease-risk.html", "404.html",
]


def load_db():
    db = {}
    if os.path.isdir(DATA):
        for fn in os.listdir(DATA):
            if fn.endswith(".json"):
                with open(os.path.join(DATA, fn), "r", encoding="utf-8") as f:
                    db[fn[:-5]] = json.load(f)
    return db


def inject_db(html, db):
    blob = json.dumps(db, ensure_ascii=False)
    script = '<script>window.__DB__ = ' + blob + ';</script>\n'
    # 插入到 api.js 引用之前
    marker = '<script src="assets/js/api.js"></script>'
    if marker in html:
        return html.replace(marker, script + marker, 1)
    return script + html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-embed", action="store_true", help="不内联数据快照")
    args = ap.parse_args()

    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST, exist_ok=True)

    # HTML
    for fn in HTML_FILES:
        src = os.path.join(ROOT, fn)
        if not os.path.exists(src):
            print("跳过缺失页面：", fn)
            continue
        with open(src, "r", encoding="utf-8") as f:
            html = f.read()
        if not args.no_embed:
            html = inject_db(html, load_db())
        with open(os.path.join(DIST, fn), "w", encoding="utf-8") as f:
            f.write(html)

    # assets / data / reports
    if os.path.isdir(ASSETS):
        shutil.copytree(ASSETS, os.path.join(DIST, "assets"))
    if os.path.isdir(DATA):
        shutil.copytree(DATA, os.path.join(DIST, "data"))
    if os.path.isdir(REPORTS):
        shutil.copytree(REPORTS, os.path.join(DIST, "reports"))

    # .nojekyll
    with open(os.path.join(DIST, ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")

    print("构建完成 ->", DIST)
    print("  HTML:", len([f for f in HTML_FILES if os.path.exists(os.path.join(ROOT, f))]))
    print("  内联数据快照:", (not args.no_embed))


if __name__ == "__main__":
    main()
