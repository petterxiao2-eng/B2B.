"""Email validation utility - format check + MX record verification."""
import re
from typing import Tuple
from email_validator import validate_email, EmailNotValidError


def validate_email_address(email: str) -> Tuple[bool, str]:
    """Validate email address.

    Returns:
        (is_valid, reason)
    """
    if not email or not email.strip():
        return False, "Empty email"

    try:
        result = validate_email(email, check_deliverability=True)
        return True, f"Valid: {result.normalized}"
    except EmailNotValidError as e:
        return False, str(e)


def infer_email_from_domain(company_name: str, domain: str, contact_name: str = "") -> list:
    """Infer possible email addresses from company domain.

    Common patterns:
    - firstname@domain
    - firstname.lastname@domain
    - firstinitiallastname@domain
    - info@domain
    - sales@domain
    """
    emails = []

    # Generic company emails
    for prefix in ["info", "sales", "contact", "procurement", "purchasing"]:
        emails.append(f"{prefix}@{domain}")

    if contact_name:
        parts = contact_name.lower().split()
        if len(parts) >= 2:
            first, last = parts[0], parts[-1]
            emails.extend([
                f"{first}@{domain}",
                f"{first}.{last}@{domain}",
                f"{first[0]}{last}@{domain}",
                f"{first}{last}@{domain}",
            ])
        elif len(parts) == 1:
            emails.append(f"{parts[0]}@{domain}")

    return emails
