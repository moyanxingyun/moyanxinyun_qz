# -*- coding: utf-8 -*-
"""运行采集器并把真实数据写入本地数据库。

用法：
  python backend/collect.py                          # 采集全部站点
  python backend/collect.py --sites mihoyo,tencent   # 指定站点
  python backend/collect.py --watch 6                # 每 6 小时循环采集
"""
import argparse
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import store
import export_embed
from parsers import mihoyo, netease, tencent

SITES = {
    "mihoyo": mihoyo.fetch,
    "netease": netease.fetch,
    "tencent": tencent.fetch,
}


def run(names):
    for name in names:
        try:
            rows = SITES[name]()
            store.delete_by_company(SITES_COMPANY[name])
            store.upsert([(r["_kind"], r) for r in rows])
            jobs = sum(1 for r in rows if r["_kind"] == "job")
            interns = sum(1 for r in rows if r["_kind"] == "intern")
            store.log_crawl(name, "api", "OK", f"{len(rows)} 条（校招 {jobs} / 实习 {interns}）")
            print(f"[OK] {name}: {len(rows)} 条（校招 {jobs} / 实习 {interns}）")
        except Exception as e:  # noqa: BLE001
            store.log_crawl(name, "api", "ERR", str(e)[:120])
            print(f"[ERR] {name}: {e}")
    export_embed.main()


SITES_COMPANY = {"mihoyo": "米哈游", "netease": "网易雷火", "tencent": "腾讯 IEG"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", default=",".join(SITES.keys()))
    ap.add_argument("--watch", type=int, default=0, help="循环采集间隔（小时），0 表示只跑一次")
    args = ap.parse_args()
    names = [s.strip() for s in args.sites.split(",") if s.strip() in SITES]
    if not names:
        print("没有可用的站点，可选：", list(SITES.keys()))
        sys.exit(1)
    while True:
        run(names)
        if args.watch <= 0:
            break
        print(f"等待 {args.watch} 小时后再次采集…")
        time.sleep(args.watch * 3600)


if __name__ == "__main__":
    main()
