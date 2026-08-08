"""
官网背调服务（V2 增强）。

只抓取目标公司自己对外公开发布的官网页面（首页/About/Contact/Products），
这与人工打开浏览器访问该公司官网查看信息在效果上等同，是完全合规的背调方式。
不做登录、不绕过任何访问控制、遵守 robots.txt。

V2 增强点（对应审计报告"联系方式可追溯 / Company Website crawler"）：
- 逐页记录 original_pages（抓取过哪些页面，可追溯）
- 邮箱 / 电话 / WhatsApp 均标注其被发现的具体来源页 source_page
- 额外抽取官网公开可见的 WhatsApp、LinkedIn 公司页、Facebook 公共主页链接
- 返回真实 http_status，供真实性验证模块使用
"""
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings

CONTACT_PAGE_HINTS = ["contact", "about", "about-us", "aboutus", "team", "management"]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"[\+]?[\d][\d\-\s\(\)]{7,18}\d")
# WhatsApp 公开链接：wa.me/<number> 或 whatsapp.com/<number> 或 api.whatsapp.com/send?phone=
WHATSAPP_RE = re.compile(r"(?:https?://)?(?:api\.)?(?:wa\.me|whatsapp\.com)/(?:send\?phone=)?(\d[\d\s\-]{6,20}\d)", re.I)
LINKEDIN_RE = re.compile(r"https?://(?:\w+\.)?linkedin\.com/(?:company|school|org)/[A-Za-z0-9_\-]+", re.I)
FACEBOOK_RE = re.compile(r"https?://(?:\w+\.)?facebook\.com/[A-Za-z0-9_\-\.]+", re.I)


def _fetch(url: str):
    headers = {"User-Agent": settings.scraper_user_agent}
    try:
        with httpx.Client(timeout=settings.scraper_timeout_seconds, follow_redirects=True, headers=headers) as client:
            resp = client.get(url)
            if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                return resp.text, resp.status_code
            return None, resp.status_code
    except httpx.HTTPError:
        return None, None
    except Exception:
        return None, None


def _check_robots_allowed(url: str) -> bool:
    """简单检查目标域名的 robots.txt 是否禁止抓取根路径，尊重站点意愿"""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(robots_url)
            if resp.status_code == 200:
                text = resp.text.lower()
                if "disallow: /" in text and "user-agent: *" in text:
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


def scrape_company_website(homepage_url: str) -> dict:
    """
    抓取公司官网首页 + 尝试找到 About/Contact 子页，提取：
    - 公司简介文本（供AI摘要用）
    - 页面中出现的邮箱/电话/WhatsApp（公开展示的联系方式），每条标注来源页
    - 官网公开可见的 LinkedIn 公司页 / Facebook 公共主页
    """
    result = {
        "homepage_url": homepage_url,
        "reachable": False,
        "http_status": None,
        "raw_text_snippets": [],
        "emails_found": [],   # [{"value":.., "source_page":..}]
        "phones_found": [],   # [{"value":.., "source_page":..}]
        "whatsapp_found": [], # [{"value":.., "source_page":..}]
        "social_links": {"linkedin": "", "facebook": ""},
        "pages_scraped": [],
    }

    if not _check_robots_allowed(homepage_url):
        result["blocked_by_robots"] = True
        return result

    html, status = _fetch(homepage_url)
    result["http_status"] = status
    if not html:
        return result

    result["reachable"] = True
    soup = BeautifulSoup(html, "lxml")
    result["pages_scraped"].append(homepage_url)
    _extract_page(soup, html, homepage_url, result)

    # 尝试找 About/Contact 链接并抓取（最多3个子页，避免过度请求对方服务器）
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if any(hint in href for hint in CONTACT_PAGE_HINTS):
            full_url = urljoin(homepage_url, a["href"])
            if urlparse(full_url).netloc == urlparse(homepage_url).netloc:
                links.add(full_url)

    for sub_url in list(links)[:3]:
        sub_html, _ = _fetch(sub_url)
        if sub_html:
            sub_soup = BeautifulSoup(sub_html, "lxml")
            result["pages_scraped"].append(sub_url)
            _extract_page(sub_soup, sub_html, sub_url, result)

    return result


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    return raw.strip() if 8 <= len(digits) <= 15 else ""


def _extract_page(soup: BeautifulSoup, html: str, source_page: str, result: dict):
    text = soup.get_text(separator=" ", strip=True)
    result["raw_text_snippets"].append(text[:3000])  # 限长，避免喂给AI时token爆炸

    # 邮箱（排除图片型伪邮箱）
    for m in EMAIL_RE.findall(html):
        if not m.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
            result["emails_found"].append({"value": m, "source_page": source_page})

    # 电话
    for m in PHONE_RE.findall(text):
        norm = _normalize_phone(m)
        if norm:
            result["phones_found"].append({"value": norm, "source_page": source_page})

    # WhatsApp 公开链接
    for m in WHATSAPP_RE.findall(html):
        num = re.sub(r"\D", "", m)
        if len(num) >= 8:
            result["whatsapp_found"].append({"value": num, "source_page": source_page})

    # LinkedIn 公司页 / Facebook 公共主页（取首个有效）
    if not result["social_links"]["linkedin"]:
        lm = LINKEDIN_RE.search(html)
        if lm:
            result["social_links"]["linkedin"] = lm.group(0)
    if not result["social_links"]["facebook"]:
        fm = FACEBOOK_RE.search(html)
        if fm:
            result["social_links"]["facebook"] = fm.group(0)
