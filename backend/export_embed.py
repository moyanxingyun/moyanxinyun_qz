# -*- coding: utf-8 -*-
"""把数据库中的最新数据内嵌回 index.html，生成可独立发布的单文件页面。

用法：python backend/export_embed.py
collect.py 每次采集完成后会自动调用本脚本，保持页面数据与数据库同步。
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import store

HTML = ROOT.parent / "index.html"


def js_array(rows):
    clean = []
    for r in rows:
        clean.append({k: v for k, v in r.items() if not k.startswith("_")})
    body = ",\n  ".join(json.dumps(r, ensure_ascii=False) for r in clean)
    return "[\n  " + body + "\n]"


def replace_array(text, name, rows):
    pat = re.compile(r"(let " + name + r"\s*=\s*)\[.*?\n\];", re.S)
    new = "\\1" + js_array(rows)
    text, n = pat.subn(new, text)
    return text, n


def main():
    jobs = store.load_all("job")
    interns = store.load_all("intern")
    text = HTML.read_text(encoding="utf-8")
    text, n1 = replace_array(text, "JOBS", jobs)
    text, n2 = replace_array(text, "INTERNS", interns)
    if n1 != 1 or n2 != 1:
        raise SystemExit(f"替换失败：JOBS={n1}, INTERNS={n2}")
    HTML.write_text(text, encoding="utf-8")
    print(f"已内嵌：校招 {len(jobs)} 条 / 实习 {len(interns)} 条 -> index.html（可独立发布）")


if __name__ == "__main__":
    main()
