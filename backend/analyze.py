# -*- coding: utf-8 -*-
"""简历 AI 分析接入点（DeepSeek V4 Flash）。

配置方式（任选其一）：
  1. 环境变量 DEEPSEEK_API_KEY=sk-xxxx
  2. backend/.env 文件中的 DEEPSEEK_API_KEY=sk-xxxx
可选：DEEPSEEK_MODEL（默认 deepseek-v4-flash）、DEEPSEEK_API_URL。
未配置 Key 时返回演示结果，接口始终可用。
"""
import json
import os
import pathlib
import re
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")

SYSTEM_PROMPT = """你是一位资深游戏美术 HR 顾问，专精游戏场景美术 / 地编方向的校招简历优化。
根据【目标岗位 JD】和【我的简历】输出结构化 JSON，字段必须严格如下：
{
  "overall": 0-100 的整数,
  "overallTxt": "竞争力评价，如 竞争力很强/具备竞争力/中等偏上/需要明显优化",
  "summary": "一句话总评（结合该公司和岗位）",
  "dims": [
    {"key": "软件技能", "score": 0-100},
    {"key": "项目经验", "score": 0-100},
    {"key": "作品集", "score": 0-100},
    {"key": "经历表达", "score": 0-100},
    {"key": "岗位匹配度", "score": 0-100}
  ],
  "hit": ["简历已覆盖的 JD 关键词"],
  "miss": ["简历缺失的 JD 关键词（按重要性排序）"],
  "suggestions": [
    {"issue": "问题", "advice": "具体建议", "example": "改法示例（带量化或作品集动作）"}
  ],
  "portfolio": [{"item": "作品集检查项", "done": true 或 false}]
}
硬性要求：
1. suggestions 至少 4 条，必须结合目标公司背景与 JD 关键词，禁止通用套话；
2. 每条建议都要能直接执行（改哪里、补什么、作品集怎么摆）；
3. 只输出 JSON，不要任何前后缀文字。"""

DIMS_KEYS = ["软件技能", "项目经验", "作品集", "经历表达", "岗位匹配度"]


def load_key():
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return key
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def mock_result(job):
    kw = job.get("keywords") or []
    return {
        "jobId": job.get("id", ""),
        "company": job.get("company", "该公司"),
        "title": job.get("title", "目标岗位"),
        "engine": MODEL,
        "mode": "demo（未配置 DEEPSEEK_API_KEY，返回演示结果）",
        "overall": 76,
        "overallTxt": "中等偏上",
        "summary": f"针对 {job.get('company', '该公司')} {job.get('title', '岗位')} 的演示分析：整体可用，但缺少 JD 关键证据，建议按下方清单补强。",
        "dims": [
            {"key": "软件技能", "score": 74},
            {"key": "项目经验", "score": 70},
            {"key": "作品集", "score": 80},
            {"key": "经历表达", "score": 66},
            {"key": "岗位匹配度", "score": 72},
        ],
        "hit": kw[:3],
        "miss": kw[3:],
        "suggestions": [
            {
                "issue": "演示模式",
                "advice": "设置 DEEPSEEK_API_KEY 后启用真实语义分析；当前为本地演示结果。",
                "example": "在 backend/.env 中写入 DEEPSEEK_API_KEY=你的Key，重启数据服务即可。",
            }
        ],
        "portfolio": [
            {"item": "ArtStation / Marmoset 链接置于简历顶部", "done": True},
            {"item": "作品按场景/道具/地编分类清晰", "done": True},
            {"item": "含白模 → 成品的过程图", "done": False},
            {"item": "场景截图含引擎实时画面与性能说明", "done": False},
        ],
    }


def _extract_json(text):
    """从模型输出中稳健提取 JSON 对象。"""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    return json.loads(text)


def normalize(result, job):
    """把模型返回规整成前端报告结构，缺字段给默认值，避免前端崩溃。"""
    dims = result.get("dims") or result.get("dimensions") or {}
    if isinstance(dims, dict):
        dims = [{"key": k, "score": int(v)} for k, v in dims.items()]
    dims = [d for d in dims if d.get("key")]
    for k in DIMS_KEYS:
        if not any(d["key"] == k for d in dims):
            dims.append({"key": k, "score": 60})
    result["jobId"] = job.get("id", "")
    result["company"] = job.get("company", "该公司")
    result["title"] = job.get("title", "目标岗位")
    result["engine"] = MODEL
    result["mode"] = "deepseek-v4-flash（真实调用）"
    result["overall"] = int(result.get("overall", 70))
    result["overallTxt"] = result.get("overallTxt", "中等偏上")
    result["dims"] = dims[:5]
    result["hit"] = result.get("hit", []) or []
    result["miss"] = result.get("miss", []) or []
    result["suggestions"] = result.get("suggestions", []) or []
    result["portfolio"] = result.get("portfolio") or result.get("portfolio_checklist", []) or []
    return result


def analyze(resume_text, job):
    key = load_key()
    if not key:
        return mock_result(job)
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "【目标岗位 JD】\n"
                + json.dumps(job, ensure_ascii=False)
                + "\n\n【我的简历】\n"
                + (resume_text or "（未提供简历文本）"),
            },
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        raise RuntimeError(f"DeepSeek API 返回 {e.code}：{detail}") from e
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"DeepSeek API 调用失败：{e}") from e
    content = data["choices"][0]["message"]["content"]
    return normalize(_extract_json(content), job)
