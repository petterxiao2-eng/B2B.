"""WhatsApp sniffing service - detects WhatsApp numbers and group links from web content."""
import re
from typing import List, Tuple
from urllib.parse import urlparse


# WhatsApp group link pattern
WHATSAPP_GROUP_PATTERN = re.compile(
    r'https?://chat\.whatsapp\.com/[A-Za-z0-9]+'
)

# International phone patterns for WhatsApp
# Supports various formats: +1234567890, (123) 456-7890, etc.
PHONE_PATTERNS = [
    # E.164 format: +1234567890
    re.compile(r'\+\d{10,15}'),
    # International format with spaces/dashes: +1 234 567 890
    re.compile(r'\+\d{1,3}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{2,4}[\s\-]?\d{2,6}'),
    # WhatsApp wa.me links
    re.compile(r'https?://wa\.me/(\d{10,15})'),
    # tel: links
    re.compile(r'tel:\+?(\d{10,15})'),
]

# Country code to region mapping (subset)
COUNTRY_CODES = {
    "1": "US/CA", "7": "RU", "20": "EG", "27": "ZA",
    "30": "GR", "31": "NL", "33": "FR", "34": "ES",
    "36": "HU", "39": "IT", "44": "UK", "49": "DE",
    "52": "MX", "55": "BR", "56": "CL", "57": "CO",
    "58": "VE", "60": "MY", "61": "AU", "62": "ID",
    "63": "PH", "64": "NZ", "65": "SG", "66": "TH",
    "81": "JP", "82": "KR", "84": "VN", "86": "CN",
    "90": "TR", "91": "IN", "92": "PK", "93": "AF",
    "94": "LK", "95": "MM", "234": "NG", "254": "KE",
    "971": "AE", "972": "IL", "966": "SA",
}


def sniff_whatsapp_from_text(text: str) -> Tuple[List[str], List[str]]:
    """Extract WhatsApp group links and phone numbers from text.

    Returns:
        (group_links, phone_numbers) - phone numbers in E.164 format
    """
    group_links = list(set(WHATSAPP_GROUP_PATTERN.findall(text)))

    phone_numbers = []
    for pattern in PHONE_PATTERNS:
        matches = pattern.findall(text)
        for match in matches:
            normalized = normalize_phone(match if isinstance(match, str) and match.startswith("+") else f"+{match}")
            if normalized and normalized not in phone_numbers:
                phone_numbers.append(normalized)

    # Also extract from wa.me links
    wa_me_pattern = re.compile(r'https?://wa\.me/(\d{10,15})')
    for match in wa_me_pattern.finditer(text):
        number = f"+{match.group(1)}"
        if number not in phone_numbers:
            phone_numbers.append(number)

    return group_links, phone_numbers


def normalize_phone(phone: str) -> str:
    """Normalize phone number to E.164 format.

    Uses phonenumbers library for proper validation.
    """
    try:
        import phonenumbers
        # Try to parse with common region hints
        for region in ["US", "GB", "DE", "IN", "CN", "AU"]:
            try:
                parsed = phonenumbers.parse(phone, region)
                if phonenumbers.is_valid_number(parsed):
                    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            except phonenumbers.NumberParseException:
                continue

        # Fallback: basic cleanup
        cleaned = re.sub(r'[^\d+]', '', phone)
        if not cleaned.startswith('+'):
            cleaned = '+' + cleaned
        if len(cleaned) >= 11 and len(cleaned) <= 16:
            return cleaned
    except ImportError:
        # Fallback without phonenumbers library
        cleaned = re.sub(r'[^\d+]', '', phone)
        if not cleaned.startswith('+'):
            cleaned = '+' + cleaned
        if len(cleaned) >= 11 and len(cleaned) <= 16:
            return cleaned

    return ""


def detect_country_from_phone(phone: str) -> str:
    """Detect country/region from phone number prefix."""
    if not phone.startswith('+'):
        return "Unknown"

    digits = phone[1:]
    # Try 3-digit, 2-digit, 1-digit codes
    for length in [3, 2, 1]:
        code = digits[:length]
        if code in COUNTRY_CODES:
            return COUNTRY_CODES[code]

    return "Unknown"
