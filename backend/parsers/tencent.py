# -*- coding: utf-8 -*-
"""腾讯校招岗位采集（官方接口）。"""
from parsers import base

COMPANY = "腾讯 IEG"
API = "https://join.qq.com/api/v1/position/searchPosition"
BASE = "https://join.qq.com"


def fetch():
    out = []
    page = 1
    while page <= 15:
        data = base.http_json(
            API,
            {
                "projectIdList": [],
                "projectMappingIdList": [2, 104, 1, 14, 20, 5],
                "keyword": "",
                "bgList": [],
                "workCountryType": 0,
                "workCityList": [],
                "recruitCityList": [],
                "positionFidList": [],
                "pageIndex": page,
                "pageSize": 100,
            },
            referer=BASE,
        )
        lst = (data.get("data") or {}).get("positionList") or []
        if not lst:
            break
        for r in lst:
            title = r.get("positionTitle", "")
            desc = title + " " + (r.get("recruitLabelName") or "") + " " + (r.get("projectName") or "")
            label = (r.get("recruitLabelName") or "") + (r.get("projectName") or "")
            intern = "实习" in label
            out.append(
                {
                    "_kind": "intern" if intern else "job",
                    "id": f"tencent-{r.get('id')}",
                    "company": COMPANY,
                    "product": "《王者荣耀》《和平精英》",
                    "business": "游戏研发/发行",
                    "size": "10000 人以上",
                    "city": (r.get("workCities") or "深圳/北京/上海/广州/成都/杭州").strip(),
                    "direction": base.classify_direction(title, desc),
                    "title": title,
                    "applyStart": "",
                    "applyEnd": "",
                    "exam": "",
                    "link": BASE + "/post.html",
                    "source": "官网",
                    "confirmed": True,
                    "keywords": base.extract_keywords(title + " " + desc),
                    "note": (r.get("projectName") or "腾讯校招") + " · 截止时间以官网为准",
                    "rolling": True,
                }
            )
        page += 1
    return out
