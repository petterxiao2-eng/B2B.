"""Google Matrix Search Service using SerpAPI."""
import httpx
from typing import List, Optional
from app.config import settings


# B2B customer type keywords
CUSTOMER_TYPE_KEYWORDS = [
    "distributor", "importer", "wholesaler", "dealer",
    "manufacturer", "OEM", "private label", "retailer",
    "installer", "supplier", "brand owner", "trader"
]

# Evidence keywords
EVIDENCE_KEYWORDS = [
    "warehouse", "wholesale", "catalog", "locations",
    "dealer program", "procurement", "in stock", "manufacturing",
    "distribution center", "showroom"
]

# B2B platform targets
B2B_PLATFORMS = [
    "IndiaMart", "GlobalSources", "Alibaba", "TradeKey",
    "Made-in-China", "ThomasNet", "Europages"
]

# Social media targets
SOCIAL_TARGETS = [
    "site:facebook.com/groups",
    "site:linkedin.com/company",
    "site:reddit.com"
]


def build_search_queries(
    product_keywords: List[str],
    customer_types: Optional[List[str]] = None,
    evidence_keywords: Optional[List[str]] = None,
    region_keywords: Optional[List[str]] = None,
    include_dorks: bool = True
) -> List[str]:
    """Build Google search query matrix.

    Formula: product × customer_type × evidence × region
    Also generates B2B platform and social media queries.
    """
    queries = []
    ctypes = customer_types or CUSTOMER_TYPE_KEYWORDS
    evidences = evidence_keywords or EVIDENCE_KEYWORDS

    for product in product_keywords:
        # Core matrix: product × customer_type
        for ctype in ctypes[:6]:  # Limit to top 6 to avoid explosion
            query = f'"{product}" {ctype}'
            queries.append(query)

        # With evidence
        for ctype in ctypes[:3]:
            for evidence in evidences[:3]:
                query = f'"{product}" {ctype} {evidence}'
                queries.append(query)

        # With region
        if region_keywords:
            for region in region_keywords[:5]:
                for ctype in ctypes[:3]:
                    query = f'"{product}" {ctype} "{region}"'
                    queries.append(query)

        # Google Dorks for B2B platforms
        if include_dorks:
            for platform in B2B_PLATFORMS[:3]:
                query = f'"{product}" {platform} supplier OR distributor'
                queries.append(query)

            # Social media
            for social in SOCIAL_TARGETS[:2]:
                query = f'{social} "{product}" buyer OR distributor'
                queries.append(query)

            # Trader/middleman focus
            queries.append(f'"{product}" trading company OR middleman OR agent')
            queries.append(f'"{product}" "we import" OR "we buy" OR "looking for supplier"')

    return queries


async def execute_serpapi_search(query: str, num_results: int = 10, location: str = "") -> dict:
    """Execute a single SerpAPI Google search.

    Returns structured search results.
    """
    if not settings.serpapi_key:
        return {"error": "SerpAPI key not configured", "results": []}

    params = {
        "q": query,
        "api_key": settings.serpapi_key,
        "engine": "google",
        "num": num_results,
    }
    if location:
        params["location"] = location

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://serpapi.com/search.json",
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for r in data.get("organic_results", []):
                results.append({
                    "title": r.get("title", ""),
                    "link": r.get("link", ""),
                    "snippet": r.get("snippet", ""),
                    "displayed_link": r.get("displayed_link", ""),
                })

            return {
                "query": query,
                "total_results": data.get("search_information", {}).get("total_results", 0),
                "results": results
            }
        except httpx.HTTPError as e:
            return {"error": str(e), "query": query, "results": []}


async def run_matrix_search(
    project_id: str,
    keyword_matrix: dict,
    max_queries: int = 50
) -> List[dict]:
    """Run full matrix search for a project.

    Returns list of all discovered companies with source info.
    """
    queries = build_search_queries(
        product_keywords=keyword_matrix.get("product_keywords", []),
        customer_types=keyword_matrix.get("customer_type_keywords"),
        evidence_keywords=keyword_matrix.get("evidence_keywords"),
        region_keywords=keyword_matrix.get("region_keywords")
    )

    # Limit queries to avoid API abuse
    queries = queries[:max_queries]

    all_results = []
    for query in queries:
        result = await execute_serpapi_search(query)
        if "error" not in result:
            for r in result.get("results", []):
                all_results.append({
                    "source_query": query,
                    "title": r["title"],
                    "url": r["link"],
                    "snippet": r["snippet"],
                    "project_id": project_id
                })

    return all_results


async def search_google(query: str, num_results: int = 10) -> List[dict]:
    """Simplified Google search wrapper.

    Args:
        query: Search query string
        num_results: Number of results to return

    Returns:
        List of result dicts with 'title', 'link', 'snippet' keys
    """
    result = await execute_serpapi_search(query, num_results=num_results)
    return result.get("results", [])
