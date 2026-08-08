# -*- coding: utf-8 -*-
"""网易雷火校招岗位采集（官方接口：27届应届校招 project_id=77）。"""
from parsers import base

COMPANY = "网易雷火"
API = "https://xiaozhao.leihuo.netease.com/api/apply/job/list/show"
BASE = "https://leihuo.163.com/campus"


def fetch(project_id=77):
    out = []
    page = 1
    while page <= 20:
        data = base.http_json(
            f"{API}?job_name=&page_size=50&page_number={page}&project_id={project_id}",
            referer=BASE,
        )
        lst = (data.get("data") or {}).get("apply_job_list") or []
        if not lst:
            break
        for r in lst:
            title = r.get("job_name", "")
            desc = (r.get("job_description") or "") + " " + (r.get("job_requirement") or "")
            work_place = r.get("work_place_name")
            if isinstance(work_place, list):
                work_place = "、".join(str(x) for x in work_place if x)
            type_name = r.get("type_name")
            if isinstance(type_name, list):
                type_name = "、".join(str(x) for x in type_name if x)
            dept = r.get("department_name")
            if isinstance(dept, list):
                dept = "、".join(str(x) for x in dept if x)
            out.append(
                {
                    "_kind": "job",
                    "id": f"netease-{r.get('job_code')}",
                    "company": COMPANY,
                    "product": "《逆水寒》《永劫无间》",
                    "business": "游戏研发/发行",
                    "size": "10000 人以上",
                    "city": str(work_place or "杭州/广州").strip(),
                    "direction": base.classify_direction(title, desc),
                    "title": title,
                    "applyStart": "2026-07-22",
                    "applyEnd": "2026-10-15",
                    "exam": "",
                    "link": r.get("job_detail_url") or (BASE + "/#/full"),
                    "source": "官网",
                    "confirmed": True,
                    "keywords": base.extract_keywords(title + " " + desc),
                    "note": str(type_name or "") + " · " + str(dept or ""),
                    "rolling": False,
                }
            )
        page += 1
    return out
