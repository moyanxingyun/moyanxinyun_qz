# -*- coding: utf-8 -*-
"""米哈游校招岗位采集（官方接口，无需登录）。"""
from parsers import base

COMPANY = "米哈游"
API = "https://ats.openout.mihoyo.com/ats-portal/v1/job/list"
BASE = "https://campus.mihoyo.com"


def fetch():
    out = []
    page = 1
    while page <= 20:
        data = base.http_json(
            API,
            {"pageNo": page, "pageSize": 100, "channelDetailIds": [1], "hireType": 1},
            referer=BASE,
        )
        lst = (data.get("data") or {}).get("list") or []
        if not lst:
            break
        for r in lst:
            title = r.get("title", "")
            city = "、".join(
                a.get("addressDetail", "")
                for a in (r.get("addressDetailList") or [])
                if a.get("addressDetail")
            )
            desc = (r.get("jobSummary") or "") + " " + (r.get("objectName") or "")
            intern = "实习" in (r.get("jobNature") or "")
            project = r.get("projectName") or ""
            out.append(
                {
                    "_kind": "intern" if intern else "job",
                    "id": f"mihoyo-{r.get('id')}",
                    "company": COMPANY,
                    "product": "《原神》《崩坏：星穹铁道》《绝区零》",
                    "business": "游戏研发/发行 · 二次元",
                    "size": "5000 人以上",
                    "city": city or "上海",
                    "direction": base.classify_direction(title, desc),
                    "title": title,
                    "applyStart": "" if intern else "2026-08-03",
                    "applyEnd": "" if intern else "2026-10-31",
                    "exam": "",
                    "link": BASE + "/#/campus/position",
                    "source": "官网",
                    "confirmed": True,
                    "keywords": base.extract_keywords(title + " " + desc),
                    "note": project or ("实习" if intern else "2027届秋招"),
                    "rolling": intern,
                }
            )
        page += 1
    return out
