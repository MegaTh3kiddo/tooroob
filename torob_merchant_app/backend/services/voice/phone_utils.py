import re
from typing import Optional

# Digit conversion mapping for Persian and Eastern Arabic numerals
_PERSIAN_ARABIC_DIGITS = {
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
}

# Standard Iranian Landline Area Codes (2-digit or 3-digit prefixes starting with 0)
# 021 (Tehran), 026 (Alborz), 031 (Isfahan), 051 (Khorasan Razavi), 071 (Fars),
# 041 (East Azerbaijan), 011 (Mazandaran), 013 (Gilan), 061 (Khuzestan), 083 (Kermanshah),
# 025 (Qom), 035 (Yazd), 034 (Kerman), 081 (Hamedan), 086 (Markazi), 087 (Kurdistan),
# 045 (Ardabil), 044 (West Azerbaijan), 054 (Sistan & Baluchestan), 056 (South Khorasan),
# 058 (North Khorasan), 066 (Lorestan), 077 (Bushehr), 076 (Hormozgan), 038 (Chaharmahal),
# 074 (Kohgiluyeh), 084 (Ilam), 028 (Qazvin), 024 (Zanjan), 023 (Semnan), 017 (Golestan)
IRANIAN_LANDLINE_PREFIXES = (
    "011", "013", "017",
    "021", "023", "024", "025", "026", "028",
    "031", "034", "035", "038",
    "041", "044", "045",
    "051", "054", "056", "058",
    "061", "066",
    "071", "074", "076", "077",
    "081", "083", "084", "086", "087"
)


def normalize_phone_number(raw_phone: Optional[str]) -> str:
    """
    Clean and normalize an Iranian phone number:
    - Convert Persian and Arabic digits to ASCII digits.
    - Strip all whitespace, hyphens, parentheses, and special characters.
    - Convert international prefix '+98', '0098', or leading '98' to national prefix '0'.
    - Ensure standard 11-digit national format (e.g. '09121234567' or '02188888888').
    """
    if not raw_phone:
        return ""

    # 1. Convert Persian/Arabic digits
    cleaned = "".join(_PERSIAN_ARABIC_DIGITS.get(ch, ch) for ch in str(raw_phone).strip())

    # 2. Keep only digits and '+'
    cleaned = re.sub(r"[^\d+]", "", cleaned)

    # 3. Handle prefixes
    if cleaned.startswith("+98"):
        cleaned = "0" + cleaned[3:]
    elif cleaned.startswith("0098"):
        cleaned = "0" + cleaned[4:]
    elif cleaned.startswith("98") and len(cleaned) == 12:
        cleaned = "0" + cleaned[2:]
    elif cleaned.startswith("9") and len(cleaned) == 10:
        cleaned = "0" + cleaned

    return cleaned


def is_iranian_mobile(phone: str) -> bool:
    """
    Returns True if the normalized phone number is an Iranian mobile phone:
    11 digits starting with '09'.
    """
    norm = normalize_phone_number(phone)
    return bool(re.match(r"^09\d{9}$", norm))


def is_iranian_landline(phone: str) -> bool:
    """
    Returns True if the normalized phone number is an Iranian landline number:
    11 digits starting with a valid provincial area code (01x-08x, NOT 09).
    """
    norm = normalize_phone_number(phone)
    if len(norm) != 11:
        return False

    if is_iranian_mobile(norm):
        return False

    return norm.startswith(IRANIAN_LANDLINE_PREFIXES) or bool(re.match(r"^0[1-8]\d{9}$", norm))


def is_valid_phone(phone: str) -> bool:
    """Returns True if the number is a valid Iranian mobile or landline."""
    norm = normalize_phone_number(phone)
    return is_iranian_mobile(norm) or is_iranian_landline(norm)


def mask_phone_number(phone: str) -> str:
    """
    Mask phone number for safe logging and telemetry (e.g., '0913***7815').
    Never exposes full number in non-essential audit outputs.
    """
    norm = normalize_phone_number(phone)
    if len(norm) >= 10:
        return f"{norm[:4]}***{norm[-4:]}"
    elif len(norm) >= 6:
        return f"{norm[:2]}***{norm[-2:]}"
    return "***"
