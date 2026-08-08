"""
搜索矩阵（Phase 2）。

输入：行业关键词 + 产品关键词 + 国家 + 客户类型分层
输出：可真实提交给搜索引擎的查询列表（行业无关，支持任意行业）。

客户类型分层（Tier）：
- Tier1（高价值采购方）：importer / distributor / wholesaler / buyer / procurement
- Tier2（项目型采购方）：EPC / installer / contractor / engineering
- Tier3（供应链上游）：supplier / manufacturer / trader

示例（光伏 / Germany / Tier1）：
    solar panel importer Germany
    solar panel distributor Germany
    ...

AI 本地化增强（深度模式）：
- 默认：只用英文产品词生成查询（original_keyword 即为查询词）。
- 深度模式：传入 translator(产品词, 目标语言) 回调，额外生成"当地语言产品词 + 客户类型 + 国家"查询，
  并分别记录 original_keyword / translated_keyword / language，满足可追溯要求。
"""
from dataclasses import dataclass
from typing import Callable, Optional


# 客户类型分层（行业无关，可任意组合）
CUSTOMER_TYPE_TIERS: dict[str, list[str]] = {
    "Tier1": ["importer", "distributor", "wholesaler", "buyer", "procurement"],
    "Tier2": ["EPC", "installer", "contractor", "engineering"],
    "Tier3": ["supplier", "manufacturer", "trader"],
}


@dataclass
class GeneratedQuery:
    query: str                 # 最终提交给搜索引擎的查询串
    product_keyword: str       # 命中的产品关键词
    customer_type: str         # 客户类型词（importer / distributor ...）
    country_name: str          # 国家英文名
    country_code: str = ""     # 国家代码（由 pipeline 填充）
    original_keyword: str = ""   # 本地化前的产品词
    translated_keyword: str = "" # 本地化后的产品词（深度模式才有值）
    language: str = "en"         # 该查询使用的搜索语言
    source_type_override: str = ""  # 非空时直接作为来源类型（如 linkedin / facebook 公开页）


def _expand_tier_labels(tiers: Optional[list[str]]) -> list[str]:
    """把 ['Tier1','Tier2'] 展开成具体客户类型词列表；空/None = 全部层级。"""
    if not tiers:
        tiers = list(CUSTOMER_TYPE_TIERS.keys())
    labels: list[str] = []
    for t in tiers:
        labels.extend(CUSTOMER_TYPE_TIERS.get(t, []))
    # 去重保序
    seen = set()
    return [x for x in labels if not (x in seen or seen.add(x))]


def generate_queries(
    product_keywords: list[str],
    country_name: str,
    tiers: Optional[list[str]] = None,
    industry_keywords: Optional[list[str]] = None,
    translator: Optional[Callable[[str, str], str]] = None,
    target_lang: str = "en",
    max_per_kw: Optional[int] = None,
) -> list[GeneratedQuery]:
    """生成搜索查询列表。

    :param product_keywords: 产品关键词，例如 ["solar panel", "led floodlight"]
    :param country_name: 国家英文名，例如 "Germany"
    :param tiers: 启用的客户类型分层；空=全开
    :param industry_keywords: 行业关键词（预留，用于未来语义过滤，不强行拼进查询以避免噪声）
    :param translator: 深度模式翻译回调 (word, target_lang) -> translated_word；None=仅英文
    :param target_lang: 深度模式目标语言代码（如 "de"/"tr"）；"en"=不翻译
    :param max_per_kw: 每个产品词最多采用的客户类型数；None=不封顶（由 pipeline 控制总查询量，避免爆炸）
    """
    results: list[GeneratedQuery] = []
    tier_labels = _expand_tier_labels(tiers)
    effective_labels = tier_labels[:max_per_kw] if max_per_kw else tier_labels

    for kw in (product_keywords or []):
        kw = (kw or "").strip()
        if not kw:
            continue
        for ct in effective_labels:
            # 默认英文查询
            q = f"{kw} {ct} {country_name}".strip()
            results.append(GeneratedQuery(
                query=q,
                product_keyword=kw,
                customer_type=ct,
                country_name=country_name,
                original_keyword=kw,
                translated_keyword="",
                language="en",
            ))
            # 深度本地化：额外生成当地语言查询
            if translator and target_lang and target_lang != "en":
                try:
                    trans = (translator(kw, target_lang) or "").strip()
                except Exception:
                    trans = ""
                if trans and trans.lower() != kw.lower():
                    tq = f"{trans} {ct} {country_name}".strip()
                    results.append(GeneratedQuery(
                        query=tq,
                        product_keyword=kw,
                        customer_type=ct,
                        country_name=country_name,
                        original_keyword=kw,
                        translated_keyword=trans,
                        language=target_lang,
                    ))
    return results


# LinkedIn / Facebook 公开公司页的 dork 限定（只发现公开可索引的页，不登录抓取）
_SOCIAL_DORKS = {
    "linkedin": 'site:linkedin.com/company',
    "facebook": 'site:facebook.com',
}


def generate_social_queries(
    product_keywords: list[str],
    country_name: str,
    country_code: str = "",
) -> list[GeneratedQuery]:
    """生成 LinkedIn / Facebook 公开公司页发现查询。

    合规边界：仅经搜索引擎发现公开公司主页 URL，由 pipeline 保存为来源（company page URL + source_url），
    不登录、不抓取需登录内容。
    """
    results: list[GeneratedQuery] = []
    for platform, dork in _SOCIAL_DORKS.items():
        for kw in (product_keywords or []):
            kw = (kw or "").strip()
            if not kw:
                continue
            q = f'{dork} "{kw}" {country_name}'.strip()
            results.append(GeneratedQuery(
                query=q,
                product_keyword=kw,
                customer_type=platform,
                country_name=country_name,
                country_code=country_code,
                original_keyword=kw,
                translated_keyword="",
                language="en",
                source_type_override=platform,
            ))
    return results
