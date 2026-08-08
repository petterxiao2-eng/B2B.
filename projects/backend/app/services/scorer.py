"""Multi-dimensional quantitative scoring service.

100-point scoring system:
- Product Match (25pts): target products, complementary products, application scenarios
- Customer Type Match (20pts): target channel or acceptable customer type
- Procurement/Repurchase Capability (20pts): purchasing, inventory, manufacturing evidence
- Business Scale & Channel (15pts): channel coverage, manufacturing scale, stores, warehouse
- Target Market & Regional Value (10pts): presence in priority markets
- Information Credibility (10pts): website, entity, multi-source evidence completeness

Hard exclusion: unrelated to product, unverifiable entity, pure dropship, non-target market, duplicate
"""
from typing import Optional
from app.models.company import Company


def score_company(company: Company, scoring_template: Optional[dict] = None) -> dict:
    """Score a company based on available evidence.

    Returns:
        {
            "total": float,
            "details": {
                "product_match": float,
                "customer_type_match": float,
                "procurement_capability": float,
                "business_scale": float,
                "market_value": float,
                "info_credibility": float
            },
            "grade": str,
            "excluded": bool,
            "exclusion_reason": str | None
        }
    """
    # Check hard exclusions first
    exclusion = _check_exclusions(company)
    if exclusion:
        return {
            "total": 0,
            "details": {},
            "grade": "excluded",
            "excluded": True,
            "exclusion_reason": exclusion
        }

    # Score each dimension
    product_match = _score_product_match(company)
    customer_type_match = _score_customer_type_match(company)
    procurement = _score_procurement_capability(company)
    business_scale = _score_business_scale(company)
    market_value = _score_market_value(company)
    info_credibility = _score_info_credibility(company)

    total = product_match + customer_type_match + procurement + business_scale + market_value + info_credibility

    # Determine grade
    if total >= 75:
        grade = "A"
    elif total >= 60:
        grade = "B"
    elif total >= 45:
        grade = "C"
    else:
        grade = "D"

    return {
        "total": round(total, 1),
        "details": {
            "product_match": round(product_match, 1),
            "customer_type_match": round(customer_type_match, 1),
            "procurement_capability": round(procurement, 1),
            "business_scale": round(business_scale, 1),
            "market_value": round(market_value, 1),
            "info_credibility": round(info_credibility, 1)
        },
        "grade": grade,
        "excluded": False,
        "exclusion_reason": None
    }


def _check_exclusions(company: Company) -> Optional[str]:
    """Check hard exclusion conditions."""
    # No verifiable business entity
    if not company.company_name or len(company.company_name.strip()) < 2:
        return "No verifiable company name"

    # Pure dropship with no inventory
    if company.main_business and "dropship" in company.main_business.lower():
        if not company.inventory_channel_capability or "warehouse" not in (company.inventory_channel_capability or "").lower():
            return "Pure dropship without warehouse/inventory"

    return None


def _score_product_match(company: Company) -> float:
    """Score product match (0-25 points)."""
    score = 0.0

    # Direct product mention in related products
    if company.related_products:
        score += 15

    # Product match evidence provided
    if company.product_match_evidence:
        score += 7

    # Main business mentions relevant products
    if company.main_business and len(company.main_business) > 20:
        score += 3

    return min(score, 25)


def _score_customer_type_match(company: Company) -> float:
    """Score customer type match (0-20 points)."""
    score = 0.0

    target_types = ["importer", "distributor", "wholesaler", "brand_owner", "oem", "retailer", "ecommerce", "dealer", "trader"]

    if company.customer_type and company.customer_type.lower() in target_types:
        score += 15

    # Evidence of being a buyer/distributor
    if company.main_business:
        biz_lower = company.main_business.lower()
        if any(t in biz_lower for t in ["distribut", "import", "wholesale", "supply", "trade"]):
            score += 5

    return min(score, 20)


def _score_procurement_capability(company: Company) -> float:
    """Score procurement/repurchase capability (0-20 points)."""
    score = 0.0

    if company.procurement_capability:
        score += 10

    # Evidence of inventory/manufacturing
    if company.inventory_channel_capability:
        evidence = company.inventory_channel_capability.lower()
        if any(kw in evidence for kw in ["warehouse", "inventory", "stock", "manufacturing", "factory"]):
            score += 7

    # Customs data available
    if company.customs_data and company.customs_data.get("import_records", 0) > 0:
        score += 3

    return min(score, 20)


def _score_business_scale(company: Company) -> float:
    """Score business scale & channel capability (0-15 points)."""
    score = 0.0

    if company.background_report:
        report = company.background_report
        if report.get("company_size"):
            score += 5
        if report.get("branches") and len(report["branches"]) > 0:
            score += 4
        if report.get("main_markets") and len(report["main_markets"]) > 1:
            score += 3

    if company.inventory_channel_capability:
        evidence = company.inventory_channel_capability.lower()
        if any(kw in evidence for kw in ["multiple locations", "nationwide", "global"]):
            score += 3

    return min(score, 15)


def _score_market_value(company: Company) -> float:
    """Score target market & regional value (0-10 points)."""
    score = 0.0

    if company.country:
        score += 5

    if company.city or company.state_province:
        score += 3

    # Major B2B markets bonus
    priority_markets = ["US", "UK", "DE", "FR", "CA", "AU", "JP", "KR", "NL", "IT"]
    if company.country and company.country.upper() in priority_markets:
        score += 2

    return min(score, 10)


def _score_info_credibility(company: Company) -> float:
    """Score information credibility (0-10 points)."""
    score = 0.0

    # Has website
    if company.website:
        score += 3

    # Has source URLs
    if company.source_url_1:
        score += 2
    if company.source_url_2:
        score += 1

    # Background report available
    if company.background_report:
        score += 2

    # Multiple discovery paths
    if company.discovery_path:
        score += 1

    # Domain verified
    if company.domain:
        score += 1

    return min(score, 10)
