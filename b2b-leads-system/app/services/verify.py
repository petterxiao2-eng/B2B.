"""
真实性验证模块（Phase 5 增强）。

对公司的官网域名真实执行四类验证，返回结构化结果（供 company_verifications 落库 + Company 缓存）：
- DNS：域名能否解析到 IP（附 A/AAAA 记录）
- HTTP：官网是否返回有效状态码（200 视为可达）
- SSL：HTTPS 证书是否有效（未过期、链完整），附签发方与过期日
- MX ：邮箱域名是否存在 MX 记录（附 MX 记录明细）

全部为真实网络请求，带超时与异常兜底；失败时对应字段置 False/None，
绝不以模拟值填充（审计报告要求"真实执行，不是评分模拟"）。
"""
import socket
import ssl
from datetime import datetime
from urllib.parse import urlparse

import httpx

from app.config import settings

try:
    import dns.resolver
    _HAS_DNS = True
except Exception:
    _HAS_DNS = False


def _domain_of(website: str) -> str:
    if not website:
        return ""
    netloc = urlparse(website).netloc or urlparse(f"//{website}").netloc
    domain = netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def verify_dns(domain: str):
    """DNS 解析：返回 (valid, records)。能解析返回 True+IP 列表，失败 False+[]，异常 None+[]。"""
    if not domain:
        return None, []
    try:
        infos = socket.getaddrinfo(domain, None)
        records = sorted({info[4][0] for info in infos})
        return (True, records)
    except (socket.gaierror, OSError):
        return False, []
    except Exception:
        return None, []


def verify_http(domain: str) -> int | None:
    """对官网发起真实 HTTP 请求，返回状态码；失败返回 None。优先 HTTPS，回退 HTTP。"""
    if not domain:
        return None
    headers = {"User-Agent": settings.scraper_user_agent}
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}"
        try:
            with httpx.Client(timeout=settings.scraper_timeout_seconds, follow_redirects=True, headers=headers) as client:
                resp = client.get(url)
                return resp.status_code
        except httpx.HTTPError:
            continue
        except Exception:
            continue
    return None


def verify_ssl(domain: str):
    """SSL 校验：返回 (valid, issuer, expiry)。握手成功且未过期返回 True+签发方+过期日。"""
    if not domain:
        return None, "", ""
    context = ssl.create_default_context()
    try:
        with socket.create_connection((domain, 443), timeout=settings.scraper_timeout_seconds) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                issuer = _flatten_x509_name(cert.get("issuer")) if cert.get("issuer") else ""
                expiry = cert.get("notAfter", "")
                return (True, issuer, expiry)
    except ssl.SSLCertVerificationError:
        return False, "", ""
    except (socket.gaierror, socket.timeout, OSError, ssl.SSLError):
        return False, "", ""
    except Exception:
        return None, "", ""


def _flatten_x509_name(name) -> str:
    """把证书 issuer/subject 的嵌套元组拍平成可读字符串。"""
    parts = []
    try:
        for rdn in name:
            for attr in rdn:
                parts.append(f"{attr[0]}={attr[1]}")
    except Exception:
        return str(name)
    return ", ".join(parts)


def verify_mx(domain: str):
    """MX 校验：返回 (valid, records)。有 MX 记录返回 True+记录列表，无 False+[]，异常 None+[]。"""
    if not domain:
        return None, []
    if not _HAS_DNS:
        # 无 dnspython 时的兜底：无法取明细，保守返回 None
        return None, []
    try:
        answers = dns.resolver.resolve(domain, "MX")
        records = sorted({str(r.exchange).rstrip(".") for r in answers})
        return (True, records) if records else (False, [])
    except Exception:
        return False, []


def verify_company_website(website: str) -> dict:
    """
    对一家公司官网做完整真实性验证，返回结构化结果：
    {dns_valid, dns_records, http_status, ssl_valid, ssl_issuer, ssl_expiry, mx_valid, mx_records, checked_at}
    供 pipeline 落库到 company_verifications（完整历史）与 Company（最新缓存）。
    """
    domain = _domain_of(website)
    dns_valid, dns_records = verify_dns(domain)
    http_status = verify_http(domain)
    ssl_valid, ssl_issuer, ssl_expiry = verify_ssl(domain)
    # MX 基于邮箱域名（与官网域名一致）校验
    mx_valid, mx_records = verify_mx(domain)

    return {
        "dns_valid": dns_valid,
        "dns_records": dns_records,
        "http_status": http_status,
        "ssl_valid": ssl_valid,
        "ssl_issuer": ssl_issuer,
        "ssl_expiry": ssl_expiry,
        "mx_valid": mx_valid,
        "mx_records": mx_records,
        "checked_at": datetime.utcnow(),
    }
