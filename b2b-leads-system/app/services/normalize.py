"""数据清洗工具：去重判定、电话号码E.164标准化、邮箱基础有效性校验"""
from urllib.parse import urlparse

import phonenumbers
from email_validator import validate_email, EmailNotValidError


def extract_domain(url: str) -> str:
    """从URL提取标准化域名，用于去重判定（同一域名视为同一家公司）"""
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def normalize_phone(raw_phone: str, region_hint: str = "US") -> str:
    """
    将电话号码标准化为 E.164 格式（如 +966501234567）。
    region_hint 是国家代码提示（当号码没有国际区号前缀时用于推断），传入项目的 region_code 即可。
    """
    if not raw_phone:
        return ""
    try:
        parsed = phonenumbers.parse(raw_phone, region_hint)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
    return ""


def check_email_valid(email: str) -> bool | None:
    """
    基础邮箱有效性校验：格式 + 域名MX记录检查（不做真实发信验证，避免打扰对方服务器/被判定为骚扰探测）。
    返回 None 表示邮箱为空（未知），True/False 表示校验结果。
    """
    if not email:
        return None
    try:
        validate_email(email, check_deliverability=True)
        return True
    except EmailNotValidError:
        return False
