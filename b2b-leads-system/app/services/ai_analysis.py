"""
AI 分析服务：调用 Anthropic API，把抓取到的官网原始文本
结构化为背调报告（对应用户提供的《客户背调》模板结构）。

严格遵循用户模板里的约束条件：
- 报告必须客观、准确，禁止捏造数据
- 若信息无法在公开渠道查实，标注"未通过公开渠道查实"
"""
import json

import httpx

from app.config import settings

ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"

BACKGROUND_CHECK_SYSTEM_PROMPT = """你是一位资深的外贸情报分析师。基于用户提供的公司官网抓取原始文本，
生成结构化的客户背调信息。

严格规则：
1. 只能使用提供的原始文本中出现的信息，禁止编造任何数据。
2. 如果某个字段在原始文本中找不到依据，必须填 "未通过公开渠道查实"，不要猜测或编造。
3. 只输出JSON，不要输出任何其他文字、不要用markdown代码块包裹。

输出JSON格式：
{
  "business_type": "零售商/批发商/OEM代工厂/未通过公开渠道查实",
  "products_summary": "主要经营品类的简要描述",
  "company_size_estimate": "从文本中能推断的规模信息，如提及员工数/成立年份等；否则填未通过公开渠道查实",
  "founded_year": "成立年份或未通过公开渠道查实",
  "main_markets": "主要市场/服务地区，找不到则填未通过公开渠道查实",
  "possible_contacts": [
    {"name": "从文本中提取到的姓名", "title": "职位", "source_note": "提取自官网哪个板块"}
  ],
  "swot_opportunity": "基于官网信息，为什么值得开发（1-2句话，基于事实推断，不夸大）",
  "risk_flags": "从文本中能看到的风险信号（如信息严重缺失、页面陈旧等），没有则填'未发现明显风险信号'"
}
"""


class AIAnalysisError(Exception):
    pass


def _call_claude(system_prompt: str, user_content: str, max_tokens: int = 1500) -> str:
    if not settings.anthropic_api_key:
        raise AIAnalysisError("未配置 ANTHROPIC_API_KEY")

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_content}],
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(ANTHROPIC_ENDPOINT, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        return "\n".join(text_blocks)


def analyze_website_scrape(scrape_result: dict, company_name_hint: str = "") -> dict:
    """把抓取的原始文本喂给AI，得到结构化背调字段"""
    combined_text = "\n---\n".join(scrape_result.get("raw_text_snippets", []))[:8000]
    user_content = f"""公司名称线索：{company_name_hint or "未知，请从文本中判断"}
官网地址：{scrape_result.get("homepage_url", "")}
抓取到的页面文本：
{combined_text}

页面中发现的邮箱：{scrape_result.get("emails_found", [])}
页面中发现的电话：{scrape_result.get("phones_found", [])}
"""
    raw = _call_claude(BACKGROUND_CHECK_SYSTEM_PROMPT, user_content)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # AI偶尔可能输出多余文字，做一次简单的容错提取
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end + 1])
        raise AIAnalysisError(f"AI返回内容无法解析为JSON: {raw[:200]}")


OUTREACH_SYSTEM_PROMPT = """你是一位专业的外贸业务开发专员，语言风格{tone}。
基于提供的客户背调信息，撰写一封简短、有针对性的首次开发信/消息草稿（{channel}）。

规则：
1. 不要使用夸张、群发感的模板话术，要体现出你确实了解这家公司。
2. 邮件控制在150词以内；WhatsApp消息控制在60词以内。
3. 只输出JSON：{{"subject": "邮件主题（WhatsApp渠道可留空）", "body": "正文"}}
4. 这只是草稿，最终会由业务员人工审核修改后才发送，所以语气要克制、专业，不要有虚假承诺。
"""


def generate_outreach_draft(company: dict, channel: str = "email", tone: str = "professional") -> dict:
    system_prompt = OUTREACH_SYSTEM_PROMPT.format(tone=tone, channel=channel)
    user_content = f"""客户公司信息：
公司名称：{company.get('company_name')}
经营品类：{company.get('products_summary')}
业务类型：{company.get('business_type')}
主要市场：{company.get('background_report', {}).get('main_markets', '未知')}
评分理由：{company.get('score_reason', '')}
切入点建议：{company.get('background_report', {}).get('swot_opportunity', '')}
"""
    raw = _call_claude(system_prompt, user_content, max_tokens=600)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end + 1])
        return {"subject": "", "body": raw}


# ---- 关键词本地化（深度模式 AI 增强）----
_LOCALIZE_SYSTEM_PROMPT = """你是一位专业的外贸关键词翻译专家。把用户给的英文产品/行业关键词，
翻译成目标市场的本土语言行业用语（用于当地搜索引擎优化召回）。

严格规则：
1. 只输出一个翻译后的关键词短语，不要解释、不要标点、不要引号、不要多余文字。
2. 如果目标语言与英文相同，或无法稳健翻译，直接原样返回原词。
3. 翻译必须是真实存在的当地行业用语，禁止编造。
"""


def localize_keyword(keyword: str, target_lang: str) -> str:
    """把产品关键词翻译为目标语言（深度模式用）。

    无 ANTHROPIC_API_KEY 时直接返回原文，保证默认英文搜索路径不受损。
    失败时也回退原文，绝不中断搜索流程。
    """
    if not target_lang or target_lang.lower() == "en":
        return keyword
    if not settings.anthropic_api_key:
        return keyword
    try:
        raw = _call_claude(
            _LOCALIZE_SYSTEM_PROMPT,
            f"目标语言代码：{target_lang}\n待翻译关键词：{keyword}",
            max_tokens=50,
        )
        cleaned = raw.strip().strip('"').strip("'").strip()
        return cleaned or keyword
    except Exception:
        return keyword
