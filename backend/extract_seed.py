# -*- coding: utf-8 -*-
"""从 index.html 中提取内置的校招/实习数据，生成 data_seed.json（种子数据）。"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(__file__).resolve().parent / "data_seed.json"


def extract(name: str):
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    m = re.search(r"const " + name + r"\s*=\s*\[(.*?)\n\];", html, re.S)
    if not m:
        raise SystemExit(f"在 index.html 中找不到 {name}")
    body = m.group(1)
    body = body.replace("'", '"')
    body = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)", r'\1"\2"\3', body)
    body = re.sub(r",\s*([}\]])", r"\1", body)
    return json.loads("[" + body + "]")


if __name__ == "__main__":
    jobs = extract("JOBS")
    interns = extract("INTERNS")
    OUT.write_text(
        json.dumps({"jobs": jobs, "interns": interns}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"已生成 {OUT.name}：校招 {len(jobs)} 条，实习 {len(interns)} 条")
