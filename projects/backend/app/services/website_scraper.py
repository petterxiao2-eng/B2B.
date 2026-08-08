"""AI Automated Website Background Check Service.

Scrapes company websites and extracts:
- Business scope, product lines, founding year, company size
- Main markets, branches/locations
- Social media presence (LinkedIn, Facebook, Instagram)
- Industry associations and trade show records
- Cross-validates with Google Maps, OpenCorporates, VIES
"""
import re
import logging
from typing import Optional
from datetime import datetime
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.whatsapp_sniffer import sniff_whatsapp_from_text

logger = logging.getLogger(__name__)

# HTTP client with timeout and user agent
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Patterns for extracting business info
YEAR_PATTERN = re.compile(r'(?:founded|established|since|est\.?|incorporated)\s*[:\-]?\s*(\d{4})', re.IGNORECASE)
EMPLOYEE_PATTERN = re.compile(r'(\d{1,5})\s*(?:\+?\s*)?(?:employees|staff|team members|people|workers)', re.IGNORECASE)
REVENUE_PATTERN = re.compile(r'(?:revenue|turnover|sales)\s*[:\-]?\s*\$?([\d,.]+)\s*(million|billion|M|B)', re.IGNORECASE)
LOCATION_PATTERN = re.compile(r'(?:locations?|offices?|branches?|warehouses?|facilities?)\s*(?:in|across|worldwide)?\s*[:\-]?\s*(\d+)', re.IGNORECASE)

# Social media URL patterns
SOCIAL_PATTERNS = {
    "linkedin": re.compile(r'https?://(?:www\.)?linkedin\.com/company/[\w\-]+'),
    "facebook": re.compile(r'https?://(?:www\.)?facebook\.com/[\w.]+'),
    "instagram": re.compile(r'https?://(?:www\.)?instagram\.com/[\w.]+'),
    "twitter": re.compile(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[\w]+'),
    "youtube": re.compile(r'https?://(?:www\.)?youtube\.com/[\w]+'),
}

# Industry association keywords
ASSOCIATION_KEYWORDS = [
    "member of", "member of the", "association", "federation",
    "chamber of commerce", "trade association", "industry body",
    "certified by", "accredited", "ISO", "CE marking"
]

# Trade show keywords
TRADE_SHOW_KEYWORDS = [
    "exhibition", "trade show", "expo", "fair", "conference",
    "Canton Fair", "Hannover Messe", "CES", "MWC", "IFA"
]


async def scrape_website(url: str, timeout: float = 15.0) -> dict:
    """Scrape a company website and extract structured information.

    Args:
        url: The company website URL

    Returns:
        Structured background check report dict
    """
    report = {
        "url": url,
        "scraped_at": datetime.utcnow().isoformat(),
        "success": False,
        "error": None,
        "business_scope": "",
        "product_lines": [],
        "founded_year": None,
        "company_size": "",
        "employee_count": None,
        "revenue": None,
        "main_markets": [],
        "branches": [],
        "google_maps_verified": False,
        "social_media": {},
        "industry_associations": [],
        "trade_shows": [],
        "whatsapp_numbers": [],
        "whatsapp_group_links": [],
        "emails_found": [],
        "phones_found": [],
        "key_pages_visited": [],
    }

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers=DEFAULT_HEADERS,
            verify=False
        ) as client:
            # Scrape main page
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            # Extract text content
            text_content = soup.get_text(separator=" ", strip=True)

            # Extract meta description
            meta_desc = ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            if meta_tag and meta_tag.get("content"):
                meta_desc = meta_tag["content"].strip()

            # Extract business scope
            report["business_scope"] = _extract_business_scope(soup, text_content, meta_desc)

            # Extract product lines
            report["product_lines"] = _extract_product_lines(soup, text_content)

            # Extract founding year
            report["founded_year"] = _extract_founded_year(text_content)

            # Extract company size
            report["company_size"] = _extract_company_size(text_content)
            report["employee_count"] = _extract_employee_count(text_content)
            report["revenue"] = _extract_revenue(text_content)

            # Extract locations/branches
            report["branches"] = _extract_branches(soup, text_content)
            report["main_markets"] = _extract_markets(text_content)

            # Extract social media links
            report["social_media"] = _extract_social_links(html)

            # Extract industry associations
            report["industry_associations"] = _extract_associations(text_content)

            # Extract trade shows
            report["trade_shows"] = _extract_trade_shows(text_content)

            # WhatsApp sniffing
            wa_groups, wa_numbers = sniff_whatsapp_from_text(html)
            report["whatsapp_group_links"] = wa_groups
            report["whatsapp_numbers"] = wa_numbers

            # Extract emails and phones
            report["emails_found"] = _extract_emails(text_content)
            report["phones_found"] = _extract_phones(text_content)

            # Try to scrape About page
            about_url = _find_about_page(soup, url)
            if about_url:
                try:
                    about_resp = await client.get(about_url)
                    if about_resp.status_code == 200:
                        about_soup = BeautifulSoup(about_resp.text, "html.parser")
                        about_text = about_soup.get_text(separator=" ", strip=True)
                        # Enrich report with about page data
                        if not report["founded_year"]:
                            report["founded_year"] = _extract_founded_year(about_text)
                        if not report["employee_count"]:
                            report["employee_count"] = _extract_employee_count(about_text)
                        if not report["business_scope"] or len(report["business_scope"]) < 50:
                            report["business_scope"] = _extract_business_scope(about_soup, about_text, "")
                        report["key_pages_visited"].append("about")
                except Exception:
                    pass

            # Try to scrape Contact page
            contact_url = _find_contact_page(soup, url)
            if contact_url:
                try:
                    contact_resp = await client.get(contact_url)
                    if contact_resp.status_code == 200:
                        contact_soup = BeautifulSoup(contact_resp.text, "html.parser")
                        contact_text = contact_soup.get_text(separator=" ", strip=True)
                        # Extract contact info
                        emails = _extract_emails(contact_text)
                        phones = _extract_phones(contact_text)
                        report["emails_found"].extend(emails)
                        report["phones_found"].extend(phones)
                        # WhatsApp sniffing on contact page
                        wa_groups2, wa_numbers2 = sniff_whatsapp_from_text(contact_resp.text)
                        report["whatsapp_group_links"].extend(wa_groups2)
                        report["whatsapp_numbers"].extend(wa_numbers2)
                        report["key_pages_visited"].append("contact")
                except Exception:
                    pass

            # Deduplicate lists
            report["emails_found"] = list(set(report["emails_found"]))
            report["phones_found"] = list(set(report["phones_found"]))
            report["whatsapp_numbers"] = list(set(report["whatsapp_numbers"]))
            report["whatsapp_group_links"] = list(set(report["whatsapp_group_links"]))

            report["success"] = True

    except httpx.TimeoutException:
        report["error"] = f"Timeout scraping {url}"
        logger.warning(report["error"])
    except httpx.HTTPStatusError as e:
        report["error"] = f"HTTP {e.response.status_code} for {url}"
        logger.warning(report["error"])
    except Exception as e:
        report["error"] = f"Error scraping {url}: {str(e)}"
        logger.error(report["error"])

    return report


async def verify_google_maps(company_name: str, country: str = "") -> dict:
    """Verify company address via Google Maps (placeholder for SerpAPI integration).

    Returns:
        {"verified": bool, "address": str, "place_id": str, "rating": float}
    """
    # This would integrate with SerpAPI Google Maps search
    # For now, return a placeholder structure
    return {
        "verified": False,
        "address": "",
        "place_id": "",
        "rating": None,
        "note": "Requires SerpAPI Google Maps integration"
    }


async def verify_opencorporates(company_name: str, country: str = "") -> dict:
    """Check company registration via OpenCorporates API (placeholder).

    Returns:
        {"verified": bool, "registration_number": str, "status": str, "incorporation_date": str}
    """
    return {
        "verified": False,
        "registration_number": "",
        "status": "",
        "incorporation_date": "",
        "note": "Requires OpenCorporates API key"
    }


async def verify_vies(vat_number: str) -> dict:
    """Verify EU VAT number via VIES (placeholder).

    Returns:
        {"valid": bool, "name": str, "address": str, "country_code": str}
    """
    return {
        "valid": False,
        "name": "",
        "address": "",
        "country_code": "",
        "note": "Requires VIES SOAP API integration"
    }


def generate_background_report(scrape_result: dict, maps_result: dict = None,
                                corp_result: dict = None) -> dict:
    """Generate a structured background check report from scrape results.

    Args:
        scrape_result: Output from scrape_website()
        maps_result: Output from verify_google_maps()
        corp_result: Output from verify_opencorporates()

    Returns:
        Standard background report dict for storage in Company.background_report
    """
    report = {
        "business_scope": scrape_result.get("business_scope", ""),
        "product_lines": scrape_result.get("product_lines", []),
        "founded_year": scrape_result.get("founded_year"),
        "company_size": scrape_result.get("company_size", ""),
        "employee_count": scrape_result.get("employee_count"),
        "revenue": scrape_result.get("revenue"),
        "main_markets": scrape_result.get("main_markets", []),
        "branches": scrape_result.get("branches", []),
        "google_maps_verified": False,
        "social_media": scrape_result.get("social_media", {}),
        "industry_associations": scrape_result.get("industry_associations", []),
        "trade_shows": scrape_result.get("trade_shows", []),
        "whatsapp_numbers": scrape_result.get("whatsapp_numbers", []),
        "whatsapp_group_links": scrape_result.get("whatsapp_group_links", []),
        "emails_found": scrape_result.get("emails_found", []),
        "phones_found": scrape_result.get("phones_found", []),
        "scraped_at": scrape_result.get("scraped_at"),
        "scrape_success": scrape_result.get("success", False),
        "cross_validation": {
            "google_maps": maps_result or {},
            "opencorporates": corp_result or {},
        }
    }

    if maps_result and maps_result.get("verified"):
        report["google_maps_verified"] = True

    return report


# --- Private helper functions ---

def _extract_business_scope(soup: BeautifulSoup, text: str, meta_desc: str) -> str:
    """Extract business scope/description from page content."""
    # Prefer meta description
    if meta_desc and len(meta_desc) > 20:
        return meta_desc

    # Try og:description
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    if og_desc and og_desc.get("content") and len(og_desc["content"]) > 20:
        return og_desc["content"].strip()

    # Try first meaningful paragraph
    paragraphs = soup.find_all("p")
    for p in paragraphs:
        t = p.get_text(strip=True)
        if len(t) > 50 and not _is_navigation_text(t):
            return t[:500]

    # Fallback: first 300 chars of text
    clean_text = re.sub(r'\s+', ' ', text).strip()
    return clean_text[:300] if clean_text else ""


def _extract_product_lines(soup: BeautifulSoup, text: str) -> list:
    """Extract product lines from page content."""
    products = []

    # Look for product-related sections
    product_sections = soup.find_all(
        ["h2", "h3", "h4"],
        string=re.compile(r'(product|solution|service|offering|category)', re.IGNORECASE)
    )
    for section in product_sections:
        next_elem = section.find_next_sibling()
        if next_elem and next_elem.name in ["p", "ul", "div"]:
            items = next_elem.find_all("li") if next_elem.name == "ul" else [next_elem]
            for item in items:
                t = item.get_text(strip=True)
                if t and len(t) > 2 and len(t) < 100:
                    products.append(t)

    # Also look for common product patterns in text
    product_pattern = re.compile(
        r'(?:our products|we offer|product range|product lines?|catalog)\s*[:\-]?\s*(.+?)(?:\.|$)',
        re.IGNORECASE
    )
    matches = product_pattern.findall(text)
    for match in matches:
        items = re.split(r'[,;]| and ', match)
        for item in items:
            item = item.strip()
            if item and len(item) > 2 and len(item) < 80:
                products.append(item)

    return list(set(products))[:20]


def _extract_founded_year(text: str) -> Optional[int]:
    """Extract founding year from text."""
    match = YEAR_PATTERN.search(text)
    if match:
        year = int(match.group(1))
        if 1800 <= year <= 2025:
            return year
    return None


def _extract_company_size(text: str) -> str:
    """Extract company size description."""
    emp_match = EMPLOYEE_PATTERN.search(text)
    if emp_match:
        count = int(emp_match.group(1))
        if count < 10:
            return "Micro (<10 employees)"
        elif count < 50:
            return "Small (10-50 employees)"
        elif count < 200:
            return "Medium (50-200 employees)"
        elif count < 1000:
            return "Large (200-1000 employees)"
        else:
            return "Enterprise (1000+ employees)"

    # Look for size indicators
    size_patterns = [
        (r'small[\s\-]?sized', "Small"),
        (r'medium[\s\-]?sized', "Medium"),
        (r'large[\s\-]?scale', "Large"),
        (r'leading\s+(?:global|international|national)', "Large/Leading"),
    ]
    for pattern, label in size_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return label

    return ""


def _extract_employee_count(text: str) -> Optional[int]:
    """Extract employee count from text."""
    match = EMPLOYEE_PATTERN.search(text)
    if match:
        return int(match.group(1))
    return None


def _extract_revenue(text: str) -> Optional[str]:
    """Extract revenue figure from text."""
    match = REVENUE_PATTERN.search(text)
    if match:
        amount = match.group(1)
        unit = match.group(2).lower()
        if unit in ["billion", "b"]:
            return f"${amount}B"
        return f"${amount}M"
    return None


def _extract_branches(soup: BeautifulSoup, text: str) -> list:
    """Extract branch/location information."""
    branches = []

    # Look for location sections
    loc_sections = soup.find_all(
        ["h2", "h3"],
        string=re.compile(r'(location|office|branch|where\s+we\s+are|our\s+presence)', re.IGNORECASE)
    )
    for section in loc_sections:
        next_elem = section.find_next_sibling()
        if next_elem:
            items = next_elem.find_all("li")
            for item in items:
                t = item.get_text(strip=True)
                if t and len(t) > 2:
                    branches.append(t)

    # Look for address patterns
    addr_pattern = re.compile(r'(\d+[\s\w]+(?:Street|St|Avenue|Ave|Road|Rd|Blvd|Drive|Dr|Lane|Way|Court|Ct)[\s,]+[\w\s]+)')
    addrs = addr_pattern.findall(text)
    branches.extend([a.strip() for a in addrs[:5]])

    return list(set(branches))[:10]


def _extract_markets(text: str) -> list:
    """Extract main market regions."""
    markets = []
    market_pattern = re.compile(
        r'(?:serve|serving|export|market|markets|customers?\s+in|presence\s+in)\s+[:\-]?\s*(.+?)(?:\.|$)',
        re.IGNORECASE
    )
    matches = market_pattern.findall(text)
    for match in matches:
        parts = re.split(r'[,;]| and |, ', match)
        for part in parts:
            part = part.strip()
            if part and len(part) > 2 and len(part) < 50:
                markets.append(part)

    return list(set(markets))[:15]


def _extract_social_links(html: str) -> dict:
    """Extract social media links from HTML."""
    social = {}
    for platform, pattern in SOCIAL_PATTERNS.items():
        matches = pattern.findall(html)
        if matches:
            social[platform] = matches[0]
    return social


def _extract_associations(text: str) -> list:
    """Extract industry association memberships."""
    associations = []
    for keyword in ASSOCIATION_KEYWORDS:
        pattern = re.compile(
            rf'{re.escape(keyword)}\s+(.+?)(?:\.|,|;|$)',
            re.IGNORECASE
        )
        matches = pattern.findall(text)
        for match in matches:
            item = match.strip()
            if item and len(item) > 3 and len(item) < 100:
                associations.append(item)
    return list(set(associations))[:10]


def _extract_trade_shows(text: str) -> list:
    """Extract trade show/exhibition records."""
    shows = []
    for keyword in TRADE_SHOW_KEYWORDS:
        pattern = re.compile(
            rf'(?:participat\w+|exhibit\w+|present\s+at|attend\w+)?\s*{re.escape(keyword)}\s*[:\-]?\s*(.+?)(?:\.|,|;|$)',
            re.IGNORECASE
        )
        matches = pattern.findall(text)
        for match in matches:
            item = match.strip()
            if item and len(item) > 2 and len(item) < 100:
                shows.append(f"{keyword}: {item}" if keyword.lower() not in item.lower() else item)
    return list(set(shows))[:10]


def _extract_emails(text: str) -> list:
    """Extract email addresses from text."""
    email_pattern = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
    emails = email_pattern.findall(text)
    # Filter out common non-contact emails
    filtered = [e for e in emails if not any(
        x in e.lower() for x in ['example.com', 'sentry.io', 'wixpress.com', 'wordpress.com', 'schema.org']
    )]
    return filtered


def _extract_phones(text: str) -> list:
    """Extract phone numbers from text."""
    phone_pattern = re.compile(r'(?:\+?\d{1,3}[\s\-]?)?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}')
    phones = phone_pattern.findall(text)
    return [p.strip() for p in phones if len(p.strip()) > 8][:10]


def _find_about_page(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """Find the About page URL from navigation."""
    for link in soup.find_all("a", href=True):
        text = link.get_text(strip=True).lower()
        href = link["href"]
        if any(kw in text for kw in ["about", "about us", "company", "who we are"]):
            return _resolve_url(href, base_url)
        if any(kw in href.lower() for kw in ["/about", "/company", "/who-we-are"]):
            return _resolve_url(href, base_url)
    return None


def _find_contact_page(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """Find the Contact page URL from navigation."""
    for link in soup.find_all("a", href=True):
        text = link.get_text(strip=True).lower()
        href = link["href"]
        if any(kw in text for kw in ["contact", "contact us", "get in touch", "reach us"]):
            return _resolve_url(href, base_url)
        if any(kw in href.lower() for kw in ["/contact", "/get-in-touch", "/reach-us"]):
            return _resolve_url(href, base_url)
    return None


def _resolve_url(href: str, base_url: str) -> Optional[str]:
    """Resolve a relative URL against a base URL."""
    if not href or href.startswith("#") or href.startswith("javascript:"):
        return None
    if href.startswith("http"):
        return href
    parsed = urlparse(base_url)
    return f"{parsed.scheme}://{parsed.netloc}{href}"


def _is_navigation_text(text: str) -> bool:
    """Check if text is navigation/UI text rather than content."""
    nav_indicators = [
        "home", "menu", "search", "login", "sign up", "cart",
        "cookie", "privacy", "terms", "copyright", "all rights reserved",
        "subscribe", "newsletter", "follow us"
    ]
    lower = text.lower()
    return any(ind in lower for ind in nav_indicators) and len(text) < 100
