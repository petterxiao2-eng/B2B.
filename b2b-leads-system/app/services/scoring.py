"""
多维度量化评分引擎。

每个维度打0-100分，再按权重加总。权重和分级阈值存在 ScoringTemplate 表里，
每个项目可以独立配置（例如高客单价赛道更看重"采购规模"，
小额批发赛道更看重"联系方式完整度+响应速度"）。
"""

DEFAULT_WEIGHTS = {
    "website_quality": 15,       # 官网信息完整度、专业度
    "contact_completeness": 20,  # 邮箱/电话/联系人是否齐全
    "business_scale_signal": 20, # 从文本推断出的规模信号（员工数、成立年限等）
    "market_relevance": 15,      # 主营品类与我方产品的匹配度
    "reachability": 15,          # 邮箱格式有效 / 电话可标准化
    "risk_penalty": 15,          # 风险扣分项（信息严重缺失、页面陈旧等），满分=无风险
}

DEFAULT_GRADE_THRESHOLDS = {"A": 80, "B": 60, "C": 40, "D": 0}


def score_website_quality(scrape_result: dict) -> float:
    if not scrape_result.get("reachable"):
        return 0.0
    pages = len(scrape_result.get("pages_scraped", []))
    text_len = sum(len(t) for t in scrape_result.get("raw_text_snippets", []))
    score = min(100, pages * 20 + min(text_len / 50, 60))
    return round(score, 1)


def score_contact_completeness(company_email: str, company_phone: str, contacts: list) -> float:
    score = 0
    if company_email:
        score += 30
    if company_phone:
        score += 30
    if contacts:
        score += min(len(contacts) * 20, 40)
    return round(min(score, 100), 1)


def score_reachability(email_valid: bool | None, phone_e164: str) -> float:
    score = 0
    if email_valid:
        score += 60
    if phone_e164:
        score += 40
    return round(score, 1)


def score_business_scale(ai_report: dict) -> float:
    text = (ai_report.get("company_size_estimate", "") or "") + (ai_report.get("founded_year", "") or "")
    if "未通过公开渠道查实" in text or not text:
        return 30.0  # 给基础分，不直接判0，避免"信息少=零分"打击过重
    return 70.0


def score_market_relevance(ai_report: dict, target_keywords: list[str]) -> float:
    products = (ai_report.get("products_summary", "") or "").lower()
    if not products or "未通过公开渠道查实" in products:
        return 30.0
    hits = sum(1 for kw in target_keywords if kw.lower() in products)
    return round(min(40 + hits * 20, 100), 1)


def score_risk_penalty(ai_report: dict, scrape_result: dict) -> float:
    """满分=无风险信号，风险越多分越低"""
    score = 100.0
    risk_flags = (ai_report.get("risk_flags", "") or "")
    if risk_flags and "未发现明显风险信号" not in risk_flags:
        score -= 30
    if not scrape_result.get("reachable"):
        score -= 40
    return round(max(score, 0), 1)


def compute_total_score(
    scrape_result: dict,
    ai_report: dict,
    company_email: str,
    company_phone: str,
    email_valid: bool | None,
    phone_e164: str,
    contacts: list,
    target_keywords: list[str],
    weights: dict | None = None,
    grade_thresholds: dict | None = None,
) -> dict:
    weights = weights or DEFAULT_WEIGHTS
    grade_thresholds = grade_thresholds or DEFAULT_GRADE_THRESHOLDS

    breakdown = {
        "website_quality": score_website_quality(scrape_result),
        "contact_completeness": score_contact_completeness(company_email, company_phone, contacts),
        "business_scale_signal": score_business_scale(ai_report),
        "market_relevance": score_market_relevance(ai_report, target_keywords),
        "reachability": score_reachability(email_valid, phone_e164),
        "risk_penalty": score_risk_penalty(ai_report, scrape_result),
    }

    total = 0.0
    for dim, raw_score in breakdown.items():
        weight = weights.get(dim, 0)
        total += raw_score * (weight / 100)

    grade = "unscored"
    for g in ["A", "B", "C", "D"]:
        if total >= grade_thresholds.get(g, 0):
            grade = g
            break

    return {
        "total": round(total, 1),
        "grade": grade,
        "breakdown": breakdown,
    }
