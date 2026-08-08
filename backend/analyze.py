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
你的工作流基于 Job Hunt Copilot 求职助手方法论：先拆解 JD 关键词，再从简历中挑选最匹配的项目经历重写 bullet，最后给出结构调整建议。
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
  "portfolio": [{"item": "作品集检查项", "done": true 或 false}],
  "pickedProjects": [
    {"name": "选中的项目/经历名", "reason": "为何选中（对应 JD 哪些要求）", "bullets": ["改写后的 bullet 1，措辞贴近 JD 语言", "改写后的 bullet 2，突出个人决策与量化结果"]}
  ],
  "excluded": [{"name": "排除的项目/经历名", "reason": "为何排除"}],
  "structure": "简历整体结构调整建议（如：技能区前移 / 项目经历按相关度重排 / 压缩某部分篇幅）"
}
硬性要求：
1. suggestions 至少 4 条，必须结合目标公司背景与 JD 关键词，禁止通用套话；
2. 每条建议都要能直接执行（改哪里、补什么、作品集怎么摆）；
3. 先分析 JD 关键词：核心技能要求、岗位层级、业务方向，作为改写的锚点；
4. 从简历中挑选 2-4 个与 JD 最匹配的项目经历，按相关度排序写入 pickedProjects，每个项目给出 2-3 条改写后的 bullet points，并在 excluded 中说明排除了哪些经历及原因；
5. 只输出 JSON，不要任何前后缀文字。"""

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
        "pickedProjects": [
            {
                "name": "开放世界小镇地编（课程项目）",
                "reason": "对应 JD「地形编辑 / 大世界」核心要求",
                "bullets": [
                    "基于 UE5 Landscape 完成 1km² 山谷地形与植被铺装，DrawCall 控制在 120 以内",
                    "独立完成白模验证到美术落地的地编全流程，输出 LOD 分层与性能说明",
                ],
            },
            {
                "name": "废弃车站场景（个人项目）",
                "reason": "对应 JD「次世代 PBR 流程 / 场景搭建」要求",
                "bullets": [
                    "ZBrush 高模精雕 180 万面 → 拓扑至 8 万三角面，Substance Painter 输出全套 PBR 贴图",
                    "Marmoset 烘焙 AO/Normal/Curvature，最终 UE5 实时渲染 3 个时段氛围对比图",
                ],
            },
        ],
        "excluded": [
            {"name": "UI 图标绘制练习", "reason": "与目标岗位（场景美术/地编）匹配度低，建议压缩篇幅"}
        ],
        "structure": "建议技能区前移：将「UE5 / Landscape / 地形地编」提到技能第一行；项目经历按本报告 pickedProjects 的顺序重排；删除与场景美术无关的社团经历，压缩至半行以内。",
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
    result["pickedProjects"] = result.get("pickedProjects", []) or []
    result["excluded"] = result.get("excluded", []) or []
    result["structure"] = result.get("structure", "")
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


REWRITE_SYSTEM_PROMPT = """你是一位资深游戏美术 HR 顾问兼简历润色专家，精通针对 JD 的简历定制。
请基于【我的简历】内容，针对【目标岗位 JD】输出一份完整改写后的 Markdown 简历，规则如下：
1. 不得凭空编造项目细节，所有叙事必须基于用户提供的简历内容；信息不足处用「待补充」标注。
2. 结构必须完整：基本信息（姓名/联系方式用占位符）→ 求职意向（针对目标岗位）→ 教育背景 → 技能清单（按 JD 优先级重排，最相关的技能放最前）→ 项目经历（从简历中挑选 2-4 个与 JD 最匹配的项目，重写 bullet，措辞贴近 JD 语言，突出个人决策与量化结果）→ 作品集 → 自我评价。
3. 项目经历每个项目 2-3 条 bullet，以动词开头，量化优先。
4. 在简历末尾另起一节【修改说明】，列出：改了什么、为什么改、用了哪些项目、排除了哪些经历及原因。
只输出 Markdown 正文，不要任何前后缀文字。"""


def mock_rewrite(job):
    company = job.get("company", "目标公司")
    title = job.get("title", "目标岗位")
    return {
        "jobId": job.get("id", ""),
        "company": company,
        "title": title,
        "engine": MODEL,
        "mode": "demo（未配置 DEEPSEEK_API_KEY，返回演示简历）",
        "markdown": f"""# 张三 · 游戏场景美术 / 地编

**求职意向**：{company} · {title}
**电话**：待补充　**邮箱**：待补充　**作品集**：ArtStation 链接待补充

---

## 教育背景

**数字媒体艺术专业** · 本科 · 2027 届

---

## 技能清单

- **UE5 / Landscape**：地形编辑、植被铺装、LOD 分层、性能优化
- **PBR 全流程**：Maya / Blender 建模、ZBrush 高模、Substance Painter 贴图、Marmoset 烘焙
- **地编落地**：白模 → Blockout → 美术落地，DrawCall 与面数控制

---

## 项目经历

### 开放世界小镇地编（课程项目）
*对应「地形编辑 / 大世界」要求*

- 基于 UE5 Landscape 完成 1km² 山谷地形与植被铺装，DrawCall 控制在 120 以内
- 独立完成白模验证到美术落地的地编全流程，输出 LOD 分层与性能说明

### 废弃车站场景（个人项目）
*对应「次世代 PBR 流程 / 场景搭建」要求*

- ZBrush 高模精雕 180 万面 → 拓扑至 8 万三角面，Substance Painter 输出全套 PBR 贴图
- Marmoset 烘焙 AO/Normal/Curvature，UE5 实时渲染 3 个时段氛围对比图

---

## 作品集

- ArtStation：场景 / 道具 / 地编分类展示（链接待补充）
- 含白模 → 成品的过程图与性能说明

---

## 自我评价

热爱游戏场景美术与地编，习惯用白模先验证玩法再推进美术落地，注重资源复用与性能表现。

---

## 修改说明

- **结构调整**：技能区前移，把 UE5 / Landscape 提到第一行，突出目标岗位最看重的地编能力。
- **项目挑选**：选用「开放世界小镇地编」（对应地形编辑要求）和「废弃车站场景」（对应 PBR / 场景搭建要求）；排除「UI 图标绘制练习」，与场景美术方向匹配度低。
- **措辞改写**：所有 bullet 改为动词开头、量化表达，贴近 JD 语言（如「完成 1km² 山谷地形」「DrawCall 控制在 120 以内」）。
- **待补充**：姓名、联系方式、作品集链接、教育经历细节请按你的真实信息补全。"""
    }


def rewrite_resume(resume_text, job):
    """针对 JD 直接输出整份改写后的 Markdown 简历。"""
    key = load_key()
    if not key:
        return mock_rewrite(job)
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "【目标岗位 JD】\n"
                + json.dumps(job, ensure_ascii=False)
                + "\n\n【我的简历】\n"
                + (resume_text or "（未提供简历文本）"),
            },
        ],
        "temperature": 0.5,
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
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        raise RuntimeError(f"DeepSeek API 返回 {e.code}：{detail}") from e
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"DeepSeek API 调用失败：{e}") from e
    content = data["choices"][0]["message"]["content"].strip()
    return {
        "jobId": job.get("id", ""),
        "company": job.get("company", "目标公司"),
        "title": job.get("title", "目标岗位"),
        "engine": MODEL,
        "mode": "deepseek-v4-flash（真实调用）",
        "markdown": content,
    }


APPLY_SYSTEM_PROMPT = """你是一位资深求职顾问，专精中小游戏公司（500 人以下）的求职策略。
针对【目标岗位 JD】和【我的简历】，输出结构化 JSON，字段严格如下：
{
  "cover_letter": "求职信正文（Markdown，400-600 字。针对中小公司特点：强调独立完成项目的能力、一专多能、对该公司产品方向的真实热情、能快速上手；结合简历中的具体项目，避免套话）",
  "apply_tips": ["3-5 条针对该公司的投递建议（如：官网直投 / 邮箱投递的注意点、作品集链接重要性、主动跟进节奏、附上项目过程图等）"]
}
硬性要求：
1. 不得编造简历中不存在的项目或数据；
2. 求职信必须有称呼和署名占位（如「贵公司 HR 您好」「此致敬礼 张三」），正文突出与目标岗位的匹配；
3. 只输出 JSON，不要任何前后缀文字。"""


def mock_apply_material(job):
    company = job.get("company", "贵公司")
    title = job.get("title", "目标岗位")
    product = job.get("product", "在研项目")
    return {
        "jobId": job.get("id", ""),
        "company": company,
        "title": title,
        "engine": MODEL,
        "mode": "demo（未配置 DEEPSEEK_API_KEY，返回演示求职信）",
        "cover_letter": f"""尊敬的 {company} 招聘团队：

您好！我是数字媒体艺术专业 2027 届毕业生，主修游戏场景美术建模与地编方向。看到贵司正在招聘{title}岗位，非常希望能加入团队，为{product}贡献一份力量。

我一直关注{company}的产品，尤其欣赏团队在美术风格上的独特坚持。作为独立游戏 / 中小团队，我认为场景美术更需要「一专多能」——既能独立完成白模验证到美术落地的全流程，也能在资源有限的条件下做出有表现力的画面。这正是我擅长的：

- 基于 UE5 Landscape 独立完成 1km² 山谷地形与植被铺装，DrawCall 控制在 120 以内，兼顾画面与性能；
- 独立完成次世代 PBR 全流程：ZBrush 高模 180 万面 → 拓扑 8 万三角面 → Substance Painter 全套贴图 → Marmoset 烘焙与 UE5 实时渲染；
- 习惯用白模先验证玩法与动线，再推进美术落地，减少返工。

作品集（ArtStation 链接）中按场景 / 道具 / 地编分类整理了完整项目，包含过程图与性能说明，方便您快速了解我的能力范围。若有机会，我非常愿意在面试中现场演示项目制作思路。

感谢您抽出时间阅读，期待能有机会与贵司团队交流！

此致敬礼
张三
2026 年 8 月""",
        "apply_tips": [
            f"优先通过官网投递入口提交（{job.get('link', '官网')}），中小团队通常直接看 HR 邮箱，正文务必附作品集链接。",
            "求职信已按岗位定制：开头点明对该公司产品的了解，结尾可补充一句对具体项目的想法（如美术风格建议）。",
            "简历中保留 2-4 个项目即可，中小团队更看重深度而非数量；把最匹配该岗位的项目放最前。",
            "投递后 5-7 个工作日可礼貌跟进一次；附上作品集链接时确认前三张就是与该岗位最相关的作品。",
        ],
    }


def build_apply_material(resume_text, job):
    """生成针对目标岗位的求职信与投递建议（中小公司优先）。"""
    key = load_key()
    if not key:
        return mock_apply_material(job)
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": APPLY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "【目标岗位 JD】\n"
                + json.dumps(job, ensure_ascii=False)
                + "\n\n【我的简历】\n"
                + (resume_text or "（未提供简历文本）"),
            },
        ],
        "temperature": 0.5,
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
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        raise RuntimeError(f"DeepSeek API 返回 {e.code}：{detail}") from e
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"DeepSeek API 调用失败：{e}") from e
    content = data["choices"][0]["message"]["content"]
    result = _extract_json(content)
    result["jobId"] = job.get("id", "")
    result["company"] = job.get("company", "目标公司")
    result["title"] = job.get("title", "目标岗位")
    result["engine"] = MODEL
    result["mode"] = "deepseek-v4-flash（真实调用）"
    result["cover_letter"] = result.get("cover_letter", "")
    result["apply_tips"] = result.get("apply_tips", []) or []
    return result
