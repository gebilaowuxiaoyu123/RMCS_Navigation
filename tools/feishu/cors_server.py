#!/usr/bin/env python3
"""给 VS Code 内置浏览器用的只读静态服务器：加 CORS 头，方便 page.evaluate 直接 fetch。"""
import http.server
import os
import functools

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PORT = int(os.environ.get("CORS_PORT", "8099"))


class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"   # 让代理别再截断大文件
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        print("[serve] " + (fmt % args), flush=True)


os.chdir(ROOT)
httpd = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), functools.partial(Handler, directory=ROOT))
print(f"serving {ROOT} on 0.0.0.0:{PORT} with CORS", flush=True)
httpd.serve_forever()
