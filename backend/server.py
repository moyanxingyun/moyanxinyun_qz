# -*- coding: utf-8 -*-
"""本地数据服务（纯标准库，无需安装依赖）。

启动：python backend/server.py   （默认端口 8001）
接口：
  GET  /api/health      健康检查
  GET  /api/jobs        全部校招岗位
  GET  /api/interns     全部实习岗位
  GET  /api/companies   公司档案汇总
  GET  /api/stats       统计信息
  POST /api/manual/add  手动录入 {kind:"job"|"intern", record:{...}}
  POST /api/analyze     简历 AI 分析 {resume_text, job}
"""
import json
import os
import pathlib
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import analyze
import store

SEED_FILE = ROOT / "data_seed.json"
PORT = int(os.environ.get("PORT", "8001"))


def ensure_seeded():
    store.init()
    if store.load_all("job") or not SEED_FILE.exists():
        return
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    rows = [("job", r) for r in data.get("jobs", [])] + [
        ("intern", r) for r in data.get("interns", [])
    ]
    store.upsert(rows)


def company_type(size):
    s = size or ""
    if "10000" in s:
        return "大厂"
    if "5000" in s:
        return "大厂"
    if "1000" in s or "500-999" in s:
        return "中厂"
    return "独立/小团队"


def companies():
    seen = {}
    for rec in store.load_all("job") + store.load_all("intern"):
        c = rec.get("company")
        if not c or c in seen:
            continue
        seen[c] = {
            "company": c,
            "business": rec.get("business", ""),
            "product": rec.get("product", ""),
            "size": rec.get("size", ""),
            "city": rec.get("city", ""),
            "link": rec.get("link", ""),
            "type": company_type(rec.get("size", "")),
        }
    return sorted(seen.values(), key=lambda x: x["company"])


def extract_resume_text(name, data_b64):
    """从 PDF / Word(.docx) / txt 中提取简历文本。返回 (text, mode)。"""
    import base64
    import io
    import re
    import zipfile

    raw = base64.b64decode(data_b64 or "")
    lower = (name or "").lower()
    if lower.endswith(".pdf"):
        try:
            import pdfplumber
        except ImportError:
            raise RuntimeError("PDF 解析库未安装：pip install pdfplumber")
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        return "\n".join(pages), "pdf"
    if lower.endswith(".docx"):
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                xml = z.read("word/document.xml").decode("utf-8", "ignore")
        except KeyError:
            raise RuntimeError("该 .docx 文件缺少正文结构，请另存为 .docx 或直接粘贴文本")
        xml = xml.replace("</w:p>", "\n").replace("</w:tr>", "\n")
        text = re.sub(r"<[^>]+>", "", xml)
        for a, b in (
            ("&amp;", "&"),
            ("&lt;", "<"),
            ("&gt;", ">"),
            ("&quot;", '"'),
            ("&#39;", "'"),
        ):
            text = text.replace(a, b)
        lines = [ln.strip() for ln in text.splitlines()]
        return "\n".join(l for l in lines if l), "docx"
    if lower.endswith((".txt", ".md", ".csv")):
        for enc in ("utf-8-sig", "utf-8", "gbk"):
            try:
                return raw.decode(enc), "text"
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode("utf-8", "ignore"), "text"
    raise RuntimeError("暂不支持该格式，请使用 PDF / Word(.docx) / txt")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/health":
            self._send(
                {
                    "ok": True,
                    "service": "campus-intel-backend",
                    "updated_at": store.latest_update(),
                }
            )
        elif path == "/api/jobs":
            self._send({"jobs": store.load_all("job"), "updated_at": store.latest_update()})
        elif path == "/api/interns":
            self._send({"interns": store.load_all("intern"), "updated_at": store.latest_update()})
        elif path == "/api/companies":
            self._send({"companies": companies(), "count": len(companies())})
        elif path == "/api/stats":
            self._send(
                {
                    "jobs": len(store.load_all("job")),
                    "interns": len(store.load_all("intern")),
                    "companies": len(companies()),
                    "updated_at": store.latest_update(),
                }
            )
        elif path == "/":
            self._send(
                {
                    "service": "校招情报助手 · 本地数据服务",
                    "endpoints": [
                        "/api/health",
                        "/api/jobs",
                        "/api/interns",
                        "/api/companies",
                        "/api/stats",
                        "POST /api/manual/add",
                        "POST /api/analyze",
                        "POST /api/rewrite",
                        "POST /api/apply-material",
                        "POST /api/extract-resume",
                    ],
                }
            )
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        if path == "/api/manual/add":
            try:
                body = json.loads(raw or "{}")
            except json.JSONDecodeError:
                return self._send({"error": "invalid json"}, 400)
            kind = body.get("kind", "job")
            rec = body.get("record")
            if not rec or not rec.get("id"):
                return self._send({"error": "record.id 必填"}, 400)
            store.upsert([(kind, rec)])
            self._send({"ok": True, "id": rec["id"]})
        elif path == "/api/analyze":
            try:
                body = json.loads(raw or "{}")
            except json.JSONDecodeError:
                return self._send({"error": "invalid json"}, 400)
            try:
                result = analyze.analyze(body.get("resume_text", ""), body.get("job", {}))
            except RuntimeError as e:
                return self._send({"error": str(e), "mode": "deepseek-error"}, 502)
            self._send(result)
        elif path == "/api/rewrite":
            try:
                body = json.loads(raw or "{}")
            except json.JSONDecodeError:
                return self._send({"error": "invalid json"}, 400)
            try:
                result = analyze.rewrite_resume(body.get("resume_text", ""), body.get("job", {}))
            except RuntimeError as e:
                return self._send({"error": str(e), "mode": "deepseek-error"}, 502)
            self._send(result)
        elif path == "/api/apply-material":
            try:
                body = json.loads(raw or "{}")
            except json.JSONDecodeError:
                return self._send({"error": "invalid json"}, 400)
            try:
                result = analyze.build_apply_material(body.get("resume_text", ""), body.get("job", {}))
            except RuntimeError as e:
                return self._send({"error": str(e), "mode": "deepseek-error"}, 502)
            self._send(result)
        elif path == "/api/extract-resume":
            try:
                body = json.loads(raw or "{}")
                text, mode = extract_resume_text(body.get("name", ""), body.get("data", ""))
            except json.JSONDecodeError:
                return self._send({"error": "invalid json"}, 400)
            except Exception as e:  # noqa: BLE001
                return self._send({"error": str(e)}, 400)
            self._send({"text": text[:8000], "mode": mode, "chars": len(text)})
        else:
            self._send({"error": "not found"}, 404)


if __name__ == "__main__":
    ensure_seeded()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    srv.daemon_threads = True
    print(f"校招情报助手数据服务已启动：http://localhost:{PORT}/api/health")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
