#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASIP 本地静态预览服务（零依赖，仅 Python 标准库）。

用法：
  python server.py                # 默认 http://127.0.0.1:8000
  PORT=8080 python server.py      # 自定义端口

仅用于本地预览。生产部署由 GitHub Pages（gh-pages 分支）承担，
与本项目代码本身无关。所有时间以北京时间（UTC+8）展示，由前端处理。
"""
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        # 防止缓存导致看不到更新
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stdout.write("[{time}] {msg}\n".format(
            time=__import__("datetime").datetime.now().strftime("%H:%M:%S"),
            msg=fmt % args))


def main():
    port = int(os.environ.get("PORT", "8000"))
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print("ASIP 本地预览已启动： http://127.0.0.1:{0}".format(port))
    print("按 Ctrl+C 停止。")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
