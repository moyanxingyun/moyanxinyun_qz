# -*- coding: utf-8 -*-
"""Static site server with gzip compression (no third-party deps)."""
import gzip
import pathlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent
PORT = 8000

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_GET(self):
        path = self.path.split("?")[0].split("#")[0]
        if path in ("/", "/index.html"):
            rel = ROOT / "index.html"
        else:
            rel = (ROOT / path.lstrip("/")).resolve()
            if not str(rel).startswith(str(ROOT.resolve())):
                self.send_error(403)
                return

        if not rel.is_file():
            self.send_error(404)
            return

        raw = rel.read_bytes()
        accept_gzip = "gzip" in self.headers.get("Accept-Encoding", "")
        body = raw
        extra = {}
        if accept_gzip and rel.suffix.lower() in (".html", ".js", ".css", ".json", ".txt", ".md", ".svg"):
            gz = gzip.compress(raw, 9)
            if len(gz) < len(raw):
                body = gz
                extra["Content-Encoding"] = "gzip"

        self.send_response(200)
        self.send_header("Content-Type", MIME.get(rel.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"site: http://localhost:{PORT}/")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
