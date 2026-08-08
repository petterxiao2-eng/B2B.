"""Phone number standardization utility - E.164 format support."""
import re
from typing import Optional, Tuple

# Country code mapping (top B2B markets)
COUNTRY_CODES = {
    "US": "+1", "CA": "+1",  # North America
    "GB": "+44", "DE": "+49", "FR": "+33", "IT": "+39", "ES": "+34",
    "NL": "+31", "BE": "+32", "AT": "+43", "CH": "+41", "SE": "+46",
    "NO": "+47", "DK": "+45", "FI": "+358", "PL": "+48", "CZ": "+420",
    "PT": "+351", "IE": "+353", "GR": "+30", "HU": "+36", "RO": "+40",
    "BG": "+359", "HR": "+385", "SK": "+421", "SI": "+386", "LT": "+370",
    "LV": "+371", "EE": "+372", "CY": "+357", "MT": "+356", "LU": "+352",
    "RU": "+7", "UA": "+380", "TR": "+90", "IL": "+972", "AE": "+971",
    "SA": "+966", "QA": "+974", "KW": "+965", "BH": "+973", "OM": "+968",
    "IN": "+91", "PK": "+92", "BD": "+880", "LK": "+94", "NP": "+977",
    "CN": "+86", "JP": "+81", "KR": "+82", "TW": "+886", "HK": "+852",
    "SG": "+65", "MY": "+60", "TH": "+66", "VN": "+84", "ID": "+62",
    "PH": "+63", "MM": "+95", "KH": "+855", "LA": "+856",
    "AU": "+61", "NZ": "+64",
    "BR": "+55", "AR": "+54", "CL": "+56", "CO": "+57", "MX": "+52",
    "PE": "+51", "EC": "+593", "VE": "+58",
    "ZA": "+27", "NG": "+234", "KE": "+254", "GH": "+233", "EG": "+20",
    "MA": "+212", "TN": "+216", "DZ": "+213", "ET": "+251", "TZ": "+255",
}

# Reverse mapping: country code -> country
CODE_TO_COUNTRY = {}
for country, code in COUNTRY_CODES.items():
    if code not in CODE_TO_COUNTRY:
        CODE_TO_COUNTRY[code] = country


def standardize_phone(phone: str, default_country: str = "") -> Optional[str]:
    """Standardize phone number to E.164 format.

    Args:
        phone: Raw phone number string
        default_country: ISO country code for fallback

    Returns:
        E.164 formatted phone number or None if invalid
    """
    if not phone or not phone.strip():
        return None

    # Remove all non-digit characters except + and leading 0
    cleaned = re.sub(r'[^\d+]', '', phone.strip())

    if not cleaned:
        return None

    # Already has + prefix
    if cleaned.startswith('+'):
        number = cleaned[1:]
        if len(number) >= 7 and len(number) <= 15:
            return f"+{number}"
        return None

    # Try to detect country code from number
    number = cleaned.lstrip('0')

    # Check if starts with known country code
    for code_len in [3, 2, 1]:
        prefix = f"+{number[:code_len]}"
        if prefix in CODE_TO_COUNTRY:
            remaining = number[code_len:]
            if len(remaining) >= 4 and len(remaining) <= 12:
                return f"+{number}"
            break

    # Use default country code
    if default_country and default_country.upper() in COUNTRY_CODES:
        country_code = COUNTRY_CODES[default_country.upper()]
        # Remove leading 0 from local number
        local_number = number.lstrip('0')
        # Remove country code if already present
        code_digits = country_code[1:]
        if local_number.startswith(code_digits):
            local_number = local_number[len(code_digits):]
        if len(local_number) >= 4 and len(local_number) <= 12:
            return f"{country_code}{local_number}"

    # Last resort: if number is long enough, assume it's valid
    if len(number) >= 7 and len(number) <= 15:
        return f"+{number}"

    return None


def detect_country_from_phone(phone: str) -> Optional[str]:
    """Detect country from phone number's country code.

    Returns:
        ISO country code or None
    """
    if not phone:
        return None

    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    if not cleaned.startswith('+'):
        return None

    number = cleaned[1:]
    for code_len in [3, 2, 1]:
        prefix = f"+{number[:code_len]}"
        if prefix in CODE_TO_COUNTRY:
            return CODE_TO_COUNTRY[prefix]

    return None


def format_phone_display(phone: str) -> str:
    """Format phone number for display purposes.

    Examples:
        +14155552671 -> +1 (415) 555-2671
        +491234567890 -> +49 1234 567890
    """
    if not phone or not phone.startswith('+'):
        return phone or ""

    number = phone[1:]

    # US/Canada format
    if number.startswith('1') and len(number) == 11:
        return f"+1 ({number[1:4]}) {number[4:7]}-{number[7:]}"

    # European format (general)
    if number.startswith('4') and len(number) > 8:
        return f"+{number[:2]} {number[2:6]} {number[6:]}"

    # Default: just add spaces every 3-4 digits
    return phone


def extract_phones_from_text(text: str, default_country: str = "") -> list:
    """Extract and standardize phone numbers from text.

    Returns:
        List of (original, standardized) tuples
    """
    if not text:
        return []

    # Common phone patterns
    patterns = [
        r'\+?\d{1,4}[\s\-.]?\(?\d{1,4}\)?[\s\-.]?\d{1,4}[\s\-.]?\d{1,9}',
        r'\+\d{7,15}',
        r'\(\d{2,4}\)\s*\d{3,4}[\s\-.]?\d{3,4}',
    ]

    results = []
    seen = set()

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            standardized = standardize_phone(match, default_country)
            if standardized and standardized not in seen:
                seen.add(standardized)
                results.append((match.strip(), standardized))

    return results
