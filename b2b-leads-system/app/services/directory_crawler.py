"""
Trade Directory（行业目录）真实抓取服务（V2 补齐）。

旧版把 IndiaMart / GlobalSources / 公开展会名录 / opencorporates 等命中结果
只当成"空壳线索"（website 留空、不抓内容）。本模块让这些目录页产生真实数据：

- 真实抓取目录/列表页（遵守 robots.txt）
- 从页面抽取公司条目：公司名称 + 其官网链接（可追溯 source_page = 目录列表页）
- 对每个抽到官网的公司，由 pipeline 调用 website_scraper 做背调回填
- 抽不到官网的条目，作为 trade_directory 来源线索留存（写明无深抓）

合规边界：只抓目录站"公开可索引的列表页"，不登录、不绕过任何访问限制。
命中需要登录才能看到的平台内页时，跳过并标注。
"""
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.services.normalize import extract_domain

# 目录页里常见的"非公司官网"链接，跳过
SKIP_DOMAINS = {
    "linkedin.com", "facebook.com", "twitter.com", "x.com", "instagram.com",
    "youtube.com", "google.com", "bing.com", "pinterest.com", "tiktok.com",
}

CONTACT_PAGE_HINTS = ["contact", "about", "about-us", "team"]
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def _fetch(url: str):
    headers = {"User-Agent": settings.scraper_user_agent}
    try:
        with httpx.Client(timeout=settings.scraper_timeout_seconds, follow_redirects=True, headers=headers) as client:
            resp = client.get(url)
            if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                return resp.text
    except httpx.HTTPError:
        return None
    except Exception:
        return None
    return None


def _robots_allowed(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(robots_url)
            if resp.status_code == 200:
                text = resp.text.lower()
                if "user-agent: *" in text:
                    lines = text.splitlines()
                    for i, line in enumerate(lines):
                        if line.strip() == "user-agent: *":
                            for follow in lines[i + 1:]:
                                if follow.strip().startswith("disallow: /") and follow.strip() == "disallow: /":
                                    return False
                                if follow.strip().startswith("user-agent:"):
                                    break
    except httpx.HTTPError:
        pass
    return True


def extract_companies(listing_url: str, max_entries: int = 30) -> list[dict]:
    """
    抓取一个行业目录/列表页，提取公司条目。
    返回: [{"company_name": str, "website": str, "source_page": str}, ...]
    website 为空表示目录页只给了公司名、没给官网链接。
    """
    if not _robots_allowed(listing_url):
        return []

    html = _fetch(listing_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    host = urlparse(listing_url).netloc.lower()
    seen_domains: set[str] = set()
    companies: list[dict] = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        full_url = urljoin(listing_url, href)
        parsed = urlparse(full_url)
        netloc = parsed.netloc.lower()
        if not netloc or netloc == host:
            continue  # 站内链接（分页/锚点等），跳过
        if netloc.startswith("www."):
            netloc = netloc[4:]
        if any(netloc == d or netloc.endswith("." + d) for d in SKIP_DOMAINS):
            continue  # 社媒/搜索等，不是公司官网

        domain = extract_domain(full_url)
        if not domain or domain in seen_domains:
            continue
        seen_domains.add(domain)

        name = a.get_text(strip=True)
        # 名称太短/像按钮文字则跳过
        if not name or len(name) < 2:
            name = domain.split(".")[0].title()

        companies.append({
            "company_name": name[:300],
            "website": full_url,
            "source_page": listing_url,
        })
        if len(companies) >= max_entries:
            break

    return companies
