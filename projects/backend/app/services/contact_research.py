"""Decision Maker Contact Research Service.

Searches for and identifies key decision makers at A/B grade companies.
Priority order:
1. Product/Category Manager, Buyer
2. Purchasing/Procurement/Sourcing Manager
3. Supply Chain/Operations Manager
4. Owner/Founder/President/GM
5. Engineering/Plant Manager
6. Company general email

Each contact is graded:
- GOLD: Name + Title + Public Email/Phone
- SILVER: Name + Title confirmed + LinkedIn/Company Phone
- BRONZE: Company general entry only
"""
import re
import logging
from typing import List, Optional
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from app.services.whatsapp_sniffer import sniff_whatsapp_from_text
from app.services.google_search import search_google

logger = logging.getLogger(__name__)

# Decision maker title patterns (priority order)
DECISION_ROLES = [
    {
        "role": "product_manager",
        "priority": 1,
        "titles": ["product manager", "category manager", "product director", "head of product",
                    "vp product", "buying manager", "buyer", "head buyer"],
        "label": "Product/Category Manager or Buyer"
    },
    {
        "role": "purchasing_manager",
        "priority": 2,
        "titles": ["purchasing manager", "procurement manager", "sourcing manager",
                    "head of purchasing", "procurement director", "chief procurement officer",
                    "purchasing director", "sourcing director"],
        "label": "Purchasing/Procurement/Sourcing Manager"
    },
    {
        "role": "supply_chain",
        "priority": 3,
        "titles": ["supply chain manager", "operations manager", "logistics manager",
                    "head of operations", "vp operations", "director of operations",
                    "supply chain director"],
        "label": "Supply Chain/Operations Manager"
    },
    {
        "role": "executive",
        "priority": 4,
        "titles": ["owner", "founder", "co-founder", "president", "general manager",
                    "ceo", "managing director", "cfo", "coo"],
        "label": "Owner/Founder/President/GM"
    },
    {
        "role": "engineering",
        "priority": 5,
        "titles": ["engineering manager", "plant manager", "technical director",
                    "cto", "vp engineering", "head of engineering", "factory manager",
                    "production manager"],
        "label": "Engineering/Plant Manager"
    },
]

# Email pattern patterns
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
PHONE_PATTERN = re.compile(r'(?:\+?\d{1,3}[\s\-]?)?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}')
LINKEDIN_PATTERN = re.compile(r'https?://(?:www\.)?linkedin\.com/in/[\w\-]+')

# Common email formats for inference
EMAIL_FORMATS = [
    "{first}.{last}@{domain}",
    "{first}{last}@{domain}",
    "{first}@{domain}",
    "{f}{last}@{domain}",
    "{first}_{last}@{domain}",
]

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


async def research_contacts(company_name: str, website: str,
                             country: str = "", project_id: str = "") -> List[dict]:
    """Research decision makers for a company.

    Args:
        company_name: Company name
        website: Company website URL
        country: Company country
        project_id: Project ID for reference

    Returns:
        List of contact dicts ready for database insertion
    """
    contacts = []

    # Strategy 1: Scrape company website team/about pages
    website_contacts = await _scrape_team_pages(website, company_name)
    contacts.extend(website_contacts)

    # Strategy 2: Search LinkedIn via Google
    linkedin_contacts = await _search_linkedin(company_name, country)
    contacts.extend(linkedin_contacts)

    # Strategy 3: Search for email patterns
    email_contacts = await _search_email_patterns(company_name, website)
    contacts.extend(email_contacts)

    # Strategy 4: Extract from company contact pages
    contact_page_contacts = await _scrape_contact_page(website, company_name)
    contacts.extend(contact_page_contacts)

    # Deduplicate and grade contacts
    contacts = _deduplicate_contacts(contacts)
    for contact in contacts:
        contact["contact_grade"] = _grade_contact(contact)
        contact["project_id"] = project_id
        contact["company_name"] = company_name
        contact["collected_at"] = datetime.utcnow().isoformat()

    # Sort by priority role and grade
    contacts.sort(key=lambda c: (
        _get_role_priority(c.get("decision_role", "")),
        _grade_sort_key(c.get("contact_grade", ""))
    ))

    return contacts


async def _scrape_team_pages(website: str, company_name: str) -> List[dict]:
    """Scrape team/about pages for contact information."""
    contacts = []
    if not website:
        return contacts

    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=15.0,
            headers=DEFAULT_HEADERS, verify=False
        ) as client:
            resp = await client.get(website)
            if resp.status_code != 200:
                return contacts

            soup = BeautifulSoup(resp.text, "html.parser")

            # Find team/about pages
            team_urls = []
            for link in soup.find_all("a", href=True):
                text = link.get_text(strip=True).lower()
                href = link["href"]
                if any(kw in text for kw in ["team", "our team", "leadership", "about", "staff", "people"]):
                    team_urls.append(_resolve_url(href, website))
                elif any(kw in href.lower() for kw in ["/team", "/about", "/leadership", "/people", "/staff"]):
                    team_urls.append(_resolve_url(href, website))

            # Scrape each team page
            for url in team_urls[:3]:  # Limit to 3 pages
                try:
                    page_resp = await client.get(url)
                    if page_resp.status_code == 200:
                        page_soup = BeautifulSoup(page_resp.text, "html.parser")
                        page_contacts = _extract_contacts_from_team_page(
                            page_soup, url, company_name
                        )
                        contacts.extend(page_contacts)
                except Exception:
                    continue

    except Exception as e:
        logger.warning(f"Error scraping team pages for {website}: {e}")

    return contacts


def _extract_contacts_from_team_page(soup: BeautifulSoup, url: str,
                                      company_name: str) -> List[dict]:
    """Extract contact info from a team/about page."""
    contacts = []

    # Look for person cards/sections
    # Common patterns: h3/h4 with name + p with title
    name_elements = soup.find_all(["h2", "h3", "h4", "h5"])
    for elem in name_elements:
        name = elem.get_text(strip=True)
        if not name or len(name) < 3 or len(name) > 60:
            continue
        # Skip if it looks like a section header
        if any(kw in name.lower() for kw in ["our team", "leadership", "meet", "about"]):
            continue
        # Must look like a person's name (2-4 words)
        words = name.split()
        if len(words) < 2 or len(words) > 4:
            continue

        # Look for title in next sibling
        title = ""
        next_elem = elem.find_next_sibling()
        if next_elem and next_elem.name in ["p", "span", "div"]:
            title = next_elem.get_text(strip=True)

        # Check if title matches any decision role
        matched_role = _match_decision_role(title)
        if not matched_role:
            continue

        # Look for email/phone/linkedin nearby
        parent = elem.parent
        if parent:
            parent_text = parent.get_text()
            emails = EMAIL_PATTERN.findall(parent_text)
            phones = PHONE_PATTERN.findall(parent_text)
            linkedin = LINKEDIN_PATTERN.findall(parent_text)

            contact = {
                "full_name": name,
                "job_title": title[:200] if title else "",
                "decision_role": matched_role["role"],
                "personal_email": emails[0] if emails else None,
                "email_status": "public" if emails else "unknown",
                "personal_phone": phones[0] if phones else None,
                "linkedin_personal": linkedin[0] if linkedin else None,
                "identity_source_url": url,
                "contact_source_url": url,
                "research_notes": f"Found on team page: {url}",
            }
            contacts.append(contact)

    return contacts


async def _search_linkedin(company_name: str, country: str = "") -> List[dict]:
    """Search for company decision makers on LinkedIn via Google."""
    contacts = []
    queries = []

    # Build search queries for LinkedIn profiles
    for role in DECISION_ROLES[:3]:  # Top 3 priority roles
        for title in role["titles"][:2]:
            q = f'site:linkedin.com/in "{company_name}" "{title}"'
            if country:
                q += f" {country}"
            queries.append((q, role))

    for query, role in queries[:6]:  # Limit searches
        try:
            results = await search_google(query, num_results=3)
            for result in results:
                url = result.get("link", "")
                if "linkedin.com/in/" not in url:
                    continue

                # Extract name from LinkedIn URL
                name_match = re.search(r'linkedin\.com/in/([\w\-]+)', url)
                if not name_match:
                    continue

                # Extract name from search result title
                title_text = result.get("title", "")
                name = _extract_name_from_linkedin_title(title_text)
                if not name:
                    name = name_match.group(1).replace("-", " ").title()

                # Extract snippet for job title
                snippet = result.get("snippet", "")
                job_title = _extract_title_from_snippet(snippet, role)

                contact = {
                    "full_name": name,
                    "job_title": job_title or role["label"],
                    "decision_role": role["role"],
                    "linkedin_personal": url,
                    "identity_source_url": url,
                    "contact_source_url": url,
                    "research_notes": f"Found via LinkedIn search: {query}",
                }
                contacts.append(contact)

        except Exception as e:
            logger.warning(f"LinkedIn search error: {e}")
            continue

    return contacts


async def _search_email_patterns(company_name: str, website: str) -> List[dict]:
    """Search for email patterns using Google dorks."""
    contacts = []
    if not website:
        return contacts

    # Extract domain
    from urllib.parse import urlparse
    try:
        domain = urlparse(website).netloc.replace("www.", "")
    except Exception:
        return contacts

    # Search for email patterns
    queries = [
        f'"{domain}" email "@{domain}"',
        f'site:{domain} "contact" OR "email" OR "@"',
    ]

    for query in queries:
        try:
            results = await search_google(query, num_results=5)
            for result in results:
                snippet = result.get("snippet", "")
                emails = EMAIL_PATTERN.findall(snippet)
                for email in emails:
                    if domain in email:
                        contact = {
                            "company_email": email,
                            "email_status": "public",
                            "contact_source_url": result.get("link", ""),
                            "research_notes": f"Found via email search: {query}",
                        }
                        contacts.append(contact)
        except Exception:
            continue

    return contacts


async def _scrape_contact_page(website: str, company_name: str) -> List[dict]:
    """Scrape the contact page for general contact info."""
    contacts = []
    if not website:
        return contacts

    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=15.0,
            headers=DEFAULT_HEADERS, verify=False
        ) as client:
            # Try common contact page URLs
            contact_urls = [
                f"{website.rstrip('/')}/contact",
                f"{website.rstrip('/')}/contact-us",
                f"{website.rstrip('/')}/about/contact",
            ]

            for url in contact_urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue

                    text = resp.text
                    soup = BeautifulSoup(text, "html.parser")
                    page_text = soup.get_text()

                    # Extract emails
                    emails = EMAIL_PATTERN.findall(page_text)
                    emails = [e for e in emails if "example.com" not in e]

                    # Extract phones
                    phones = PHONE_PATTERN.findall(page_text)

                    # Extract WhatsApp
                    wa_groups, wa_numbers = sniff_whatsapp_from_text(text)

                    # Create a BRONZE contact for general company info
                    if emails or phones:
                        contact = {
                            "full_name": None,
                            "job_title": "General Contact",
                            "decision_role": "general",
                            "contact_grade": "BRONZE",
                            "company_email": emails[0] if emails else None,
                            "company_phone": phones[0] if phones else None,
                            "identity_source_url": url,
                            "contact_source_url": url,
                            "research_notes": f"General contact from {url}",
                        }
                        contacts.append(contact)

                    break  # Found a contact page, stop trying
                except Exception:
                    continue

    except Exception as e:
        logger.warning(f"Error scraping contact page for {website}: {e}")

    return contacts


def _match_decision_role(title: str) -> Optional[dict]:
    """Match a job title to a decision role."""
    if not title:
        return None
    title_lower = title.lower()
    for role in DECISION_ROLES:
        for t in role["titles"]:
            if t in title_lower:
                return role
    return None


def _grade_contact(contact: dict) -> str:
    """Grade a contact based on available information.

    GOLD: Name + Title + Public Email/Phone
    SILVER: Name + Title confirmed + LinkedIn/Company Phone
    BRONZE: Company general entry only
    """
    has_name = bool(contact.get("full_name"))
    has_title = bool(contact.get("job_title")) and contact["job_title"] != "General Contact"
    has_public_email = contact.get("email_status") in ["public", "verified"]
    has_phone = bool(contact.get("personal_phone") or contact.get("company_phone"))
    has_linkedin = bool(contact.get("linkedin_personal"))
    has_company_email = bool(contact.get("company_email"))

    if has_name and has_title and (has_public_email or has_phone):
        return "GOLD"
    elif has_name and has_title and (has_linkedin or has_company_email):
        return "SILVER"
    else:
        return "BRONZE"


def _deduplicate_contacts(contacts: List[dict]) -> List[dict]:
    """Remove duplicate contacts based on name + email + linkedin."""
    seen = set()
    unique = []
    for c in contacts:
        key = (
            c.get("full_name", ""),
            c.get("personal_email", ""),
            c.get("linkedin_personal", ""),
        )
        if key != ("", "", "") and key in seen:
            continue
        if key != ("", "", ""):
            seen.add(key)
        unique.append(c)
    return unique


def _get_role_priority(role: str) -> int:
    """Get numeric priority for a decision role."""
    for r in DECISION_ROLES:
        if r["role"] == role:
            return r["priority"]
    return 99


def _grade_sort_key(grade: str) -> int:
    """Sort key for contact grades (lower = better)."""
    return {"GOLD": 0, "SILVER": 1, "BRONZE": 2}.get(grade, 3)


def _extract_name_from_linkedin_title(title: str) -> Optional[str]:
    """Extract person name from LinkedIn search result title."""
    # Common pattern: "Name - Job Title - Company - LinkedIn"
    if " - " in title:
        name = title.split(" - ")[0].strip()
        if name and len(name) > 2 and len(name) < 50:
            # Remove common suffixes
            name = re.sub(r'\s*\|.*$', '', name)
            return name
    return None


def _extract_title_from_snippet(snippet: str, role: dict) -> str:
    """Extract job title from LinkedIn search snippet."""
    for title in role["titles"]:
        if title.lower() in snippet.lower():
            # Find the context around the title
            idx = snippet.lower().index(title.lower())
            start = max(0, idx - 20)
            end = min(len(snippet), idx + len(title) + 30)
            return snippet[start:end].strip()
    return ""


def _resolve_url(href: str, base_url: str) -> Optional[str]:
    """Resolve a relative URL against a base URL."""
    if not href or href.startswith("#") or href.startswith("javascript:"):
        return None
    if href.startswith("http"):
        return href
    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    return f"{parsed.scheme}://{parsed.netloc}{href}"


def infer_email(first_name: str, last_name: str, domain: str,
                 confirmed_pattern: str = None) -> dict:
    """Infer email address based on common patterns.

    Args:
        first_name: Person's first name
        last_name: Person's last name
        domain: Company email domain
        confirmed_pattern: If known, the company's email format

    Returns:
        {"email": str, "confidence": float, "format": str}
    """
    first = first_name.lower().strip()
    last = last_name.lower().strip()
    f = first[0] if first else ""

    if confirmed_pattern:
        email = confirmed_pattern.format(first=first, last=last, f=f, domain=domain)
        return {"email": email, "confidence": 0.8, "format": confirmed_pattern}

    # Try common formats
    emails = []
    for fmt in EMAIL_FORMATS:
        try:
            email = fmt.format(first=first, last=last, f=f, domain=domain)
            emails.append({"email": email, "confidence": 0.3, "format": fmt})
        except KeyError:
            continue

    # Return the most likely format
    if emails:
        return emails[0]
    return {"email": "", "confidence": 0, "format": ""}
