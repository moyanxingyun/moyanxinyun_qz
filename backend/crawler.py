# -*- coding: utf-8 -*-
"""采集器框架（M1）：
1. 从种子数据汇总各公司官方校招页来源；
2. 逐个检查可达性，识别页面类型（静态可解析 / JS 渲染）；
3. 检查结果写入 data.db 的 crawl_log 表，供后续开发逐站解析器使用。

用法：
  python backend/crawler.py check [--limit N] [--company 米哈游]
"""
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import store

TIMEOUT = 8
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CampusIntelBot/0.1"


def sources():
    seed = ROOT / "data_seed.json"
    if not seed.exists():
        print("缺少 data_seed.json，请先运行：python backend/extract_seed.py")
        sys.exit(1)
    data = json.loads(seed.read_text(encoding="utf-8"))
    seen = {}
    for r in data.get("jobs", []) + data.get("interns", []):
        seen.setdefault(r["company"], r["link"])
    return [{"company": c, "url": u} for c, u in seen.items()]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        body = resp.read(65536).decode("utf-8", "ignore")
        return resp.status, body


def classify(body):
    low = body.lower()
    if any(k in low for k in ("<script", "javascript", "react", "vue", "next")):
        return "JS 渲染页面（下一步用浏览器采集）"
    if any(k in low for k in ("position", "job", "apply", "campus")):
        return "静态可解析（可做规则解析器）"
    return "待确认（页面结构需人工查看）"


def main():
    args = sys.argv[1:]
    if not args or args[0] != "check":
        print(__doc__)
        sys.exit(1)
    limit = None
    company = None
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])
    if "--company" in args:
        company = args[args.index("--company") + 1]
    srcs = sources()
    if company:
        srcs = [s for s in srcs if s["company"] == company]
    if limit:
        srcs = srcs[:limit]
    print(f"来源清单共 {len(sources())} 家公司，本次检查 {len(srcs)} 条（每条超时 {TIMEOUT}s）")
    ok = fail = 0
    for s in srcs:
        try:
            status, body = fetch(s["url"])
            note = classify(body)
            ok += 1
        except Exception as e:  # noqa: BLE001
            status, note = "ERR", str(e)[:90]
            fail += 1
        store.log_crawl(s["company"], s["url"], str(status), note)
        print(f"  {s['company']:<14} {str(status):>4}  {note}")
    print(f"完成：可达 {ok}，失败 {fail}。记录已写入 data.db (crawl_log)")


if __name__ == "__main__":
    main()
