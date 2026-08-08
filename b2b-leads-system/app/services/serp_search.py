"""
真实搜索 Provider 抽象层（Phase 4）。

设计目标：
- 不绑定单一搜索引擎。Google / Bing 都经 SerpAPI 调用（engine 参数不同，复用同一 SERPAPI_KEY），
  通过统一的 SearchProvider 接口接入，未来可无缝加入 DuckDuckGo / Brave 等。
- 国家参数来自 country_matrix.CountryProfile（gl/hl/cc），由调用方传入，实现"国家切换自动变化搜索语言/domain"。
- 返回结构化候选结果（含 provider / 原始查询），供 pipeline 写入 company_sources 做追溯。

合规边界：
- 只做"搜索引擎结果抓取"，等同于人工在 Google/Bing 搜索并翻看结果页，是 SerpAPI 官方允许的用途。
- 不对 LinkedIn/Facebook 登录内容抓取；命中社媒公开页仅保存其 URL（见 routers/search.py）。
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.services.country_matrix import CountryProfile
from app.services.search_matrix import GeneratedQuery


SERPAPI_ENDPOINT = "https://serpapi.com/search"


class SerpSearchError(Exception):
    pass


class SearchProvider:
    """搜索 Provider 统一接口。子类只需实现 engine 与分页参数。"""

    engine: str = ""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.serpapi_key
        if not self.api_key:
            raise SerpSearchError(f"[{self.engine}] 未配置 SERPAPI_KEY，请在 .env 中设置后重试")

    def _base_params(self, query: str, country: CountryProfile, num: int) -> dict:
        return {
            "engine": self.engine,
            "q": query,
            "num": min(num, 100),
            "api_key": self.api_key,
        }

    def _page_offset(self, page: int, num: int) -> dict:
        """不同引擎分页参数不同，由子类覆盖。"""
        return {"start": page * num}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search(self, query: str, country: CountryProfile, num: int = 20, page: int = 0) -> dict:
        params = self._base_params(query, country, num)
        params.update(self._page_offset(page, num))
        with httpx.Client(timeout=30) as client:
            resp = client.get(SERPAPI_ENDPOINT, params=params)
            resp.raise_for_status()
            return resp.json()

    @property
    def name(self) -> str:
        return self.engine


class GoogleProvider(SearchProvider):
    engine = "google"

    def _base_params(self, query: str, country: CountryProfile, num: int) -> dict:
        p = super()._base_params(query, country, num)
        # Google 地理定位与界面语言
        p["gl"] = country.gl
        p["hl"] = country.hl
        return p

    def _page_offset(self, page: int, num: int) -> dict:
        return {"start": page * num}


class BingProvider(SearchProvider):
    engine = "bing"

    def _base_params(self, query: str, country: CountryProfile, num: int) -> dict:
        p = super()._base_params(query, country, num)
        # Bing 市场（国家）与语言
        p["cc"] = country.bing_cc
        p["lang"] = country.hl
        return p

    def _page_offset(self, page: int, num: int) -> dict:
        # SerpAPI Bing 分页使用 offset
        return {"offset": page * num}


def _default_providers() -> list[SearchProvider]:
    """默认 Provider 组合：Google 始终启用；Bing 在开启且有 key 时启用。"""
    providers: list[SearchProvider] = []
    if settings.serpapi_key:
        providers.append(GoogleProvider())
        if settings.enable_bing:
            try:
                providers.append(BingProvider())
            except SerpSearchError:
                pass  # 无 key 时跳过
    return providers


def extract_candidate_links(serp_json: dict) -> list[dict]:
    """从 SerpAPI 返回结果里提取候选链接列表（Google/Bing 结构一致）。"""
    results = []
    for item in serp_json.get("organic_results", []):
        results.append({
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "displayed_link": item.get("displayed_link", ""),
        })
    return results


class SearchManager:
    """统一调度多个 Provider，对一批查询做真实分页搜索并聚合去重。"""

    def __init__(self, providers: list[SearchProvider] | None = None):
        self.providers = providers if providers is not None else _default_providers()
        if not self.providers:
            raise SerpSearchError("未配置任何搜索 Provider（请检查 SERPAPI_KEY / enable_bing）")

    def search_queries(
        self, queries: list[GeneratedQuery], country: CountryProfile, num: int = 20, pages: int = 2
    ) -> tuple[list[dict], int]:
        """对一批 GeneratedQuery 跑全部 Provider，返回 (候选列表, 原始命中数)。

        候选每条：{title, link, snippet, displayed_link, provider, query_obj}
        - query_obj：原始的 GeneratedQuery（含 original/translated/language，供来源追溯）
        - 跨 Provider 按 link 去重（同一 URL 只保留首次出现的来源）
        - 原始命中数 = 所有 Provider/页抓回的 organic_results 总数（含重复/聚合，用于 search_hits 参考值）
        """
        aggregated: list[dict] = []
        seen_links: set[str] = set()
        raw_hits = 0
        for gq in queries:
            for provider in self.providers:
                for page in range(max(pages, 1)):
                    try:
                        serp_json = provider.search(gq.query, country, num=num, page=page)
                    except SerpSearchError:
                        # 单个 Provider/页失败不影响其他，记录后继续
                        continue
                    page_links = extract_candidate_links(serp_json)
                    raw_hits += len(serp_json.get("organic_results", []))
                    for link in page_links:
                        link_url = link.get("link", "")
                        if not link_url or link_url in seen_links:
                            continue
                        seen_links.add(link_url)
                        aggregated.append({
                            **link,
                            "provider": provider.name,
                            "query_obj": gq,
                        })
                    # 本页结果不足 num，说明已到末页，提前停止翻页
                    if len(serp_json.get("organic_results", [])) < num:
                        break
        return aggregated, raw_hits


# ---- 向后兼容的快捷函数（供未重构的旧调用方使用，新代码请用 SearchManager）----
def google_search(query: str, region_code: str = "", num: int = 20, start: int = 0) -> dict:
    from app.services.country_matrix import get_country
    return GoogleProvider().search(query, get_country(region_code), num=num, page=start // max(num, 1))


def google_search_paginated(query: str, region_code: str = "", num: int = 20, pages: int = 1) -> list[dict]:
    from app.services.country_matrix import get_country
    country = get_country(region_code)
    out = []
    for page in range(pages):
        serp = GoogleProvider().search(query, country, num=num, page=page)
        out.extend(extract_candidate_links(serp))
        if len(serp.get("organic_results", [])) < num:
            break
    return out
