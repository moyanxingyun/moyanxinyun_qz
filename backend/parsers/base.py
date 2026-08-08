# -*- coding: utf-8 -*-
"""采集解析器公共工具。"""
import json
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"

SOFTWARE_KEYWORDS = [
    "Maya", "Blender", "ZBrush", "Substance Painter", "Substance", "UE5", "UE4",
    "Unity", "Photoshop", "PBR", "Houdini", "3ds Max", "SpeedTree", "Marmoset",
    "NPR", "二次元", "风格化", "写实", "低模", "高模", "地形", "光照", "材质",
    "地编", "关卡", "白盒", "TA", "技术美术",
]


def http_json(url, payload=None, referer=None, timeout=30):
    headers = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
    }
    if referer:
        headers["Referer"] = referer + "/"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        headers["Origin"] = referer
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
    else:
        req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "ignore"))


def classify_direction(title, desc=""):
    t = (title or "") + " " + (desc or "")
    if any(k in t for k in ("场景原画", "场景美术", "场景设计", "场景制作")):
        return "场景美术"
    if any(k in t for k in ("场景模型", "3D场景", "三维场景", "场景建模", "场景建模师")):
        return "场景模型"
    if any(k in t for k in ("地编", "地形", "关卡美术", "场景地编")):
        return "场景地编"
    if any(k in t for k in ("关卡", "白盒")):
        return "关卡美术"
    if any(k in t for k in ("角色", "原画", "特效", "动画", "动效", "界面", "UI", "技术美术", "TA", "美宣")):
        return "美术（其他）"
    if any(k in t for k in ("美术", "艺术", "设计")):
        return "美术（其他）"
    return "非美术"


def extract_keywords(text):
    low = (text or "").lower()
    out = []
    for w in SOFTWARE_KEYWORDS:
        if w.lower() in low:
            out.append(w)
    return out
