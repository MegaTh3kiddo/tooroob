import re
from typing import Any, Dict, Optional, Tuple

PERSIAN_TO_LATIN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

ARABIC_TO_PERSIAN_CHARS = {
    "ي": "ی",
    "ك": "ک",
    "ة": "ه",
    "ۀ": "ه",
    "دِ": "د",
    "بِ": "ب",
    "زِ": "ز",
}

# Arabic diacritics regex
DIACRITICS_REGEX = re.compile(r"[\u064B-\u0652\u0640]")

COLOR_KEYWORDS = {
    "مشکی": "black",
    "سیاه": "black",
    "black": "black",
    "سفید": "white",
    "white": "white",
    "آبی": "blue",
    "blue": "blue",
    "سبز": "green",
    "green": "green",
    "قرمز": "red",
    "red": "red",
    "نقره‌ای": "silver",
    "نقره ای": "silver",
    "silver": "silver",
    "خاکستری": "gray",
    "طوسی": "gray",
    "gray": "gray",
    "grey": "gray",
    "طلایی": "gold",
    "gold": "gold",
    "بنفش": "purple",
    "purple": "purple",
    "صورتی": "pink",
    "pink": "pink",
    "تیتانیوم": "titanium",
    "titanium": "titanium",
}

CONDITION_KEYWORDS = {
    "استوک": "used",
    "دست دوم": "used",
    "کارکرده": "used",
    "used": "used",
    "اوپن باکس": "open_box",
    "open box": "open_box",
    "ریفربیش": "refurbished",
    "refurbished": "refurbished",
    "نو": "new",
    "پلمپ": "new",
    "آکبند": "new",
    "new": "new",
}


def normalize_digits(text: Optional[str]) -> str:
    """Convert Persian and Arabic numerals to standard Latin digits."""
    if not text:
        return ""
    return str(text).translate(PERSIAN_TO_LATIN_DIGITS)


def normalize_persian_text(text: Optional[str]) -> str:
    """Normalize Persian and Arabic characters, removing unwanted diacritics and unifying spacing."""
    if not text:
        return ""
    s = str(text)
    for ar, fa in ARABIC_TO_PERSIAN_CHARS.items():
        s = s.replace(ar, fa)
    # Remove diacritics and tatweel
    s = DIACRITICS_REGEX.sub("", s)
    # Normalize zero-width non-joiner
    s = re.sub(r"\u200c+", "\u200c", s)
    # Normalize extra whitespaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_numeric_price(raw_val: Any) -> Optional[float]:
    """Parse numeric price from various formats, returning float or None."""
    if raw_val is None:
        return None
    if isinstance(raw_val, (int, float)):
        return float(raw_val)
    
    val_str = normalize_digits(str(raw_val)).strip()
    if not val_str or val_str.lower() in ("null", "none", "nan", ""):
        return None
    
    # Remove currency words, commas, underscores
    cleaned = re.sub(r"[^\d.]", "", val_str)
    try:
        val = float(cleaned)
        return val
    except ValueError:
        return None


def extract_variant_attributes(title: str, specs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Extract standard attributes (color, storage, ram, condition, warranty) from title & specs."""
    norm_title = normalize_digits(normalize_persian_text(title)).lower()
    attrs: Dict[str, Any] = {
        "color": None,
        "storage": None,
        "ram": None,
        "condition": "new",
        "warranty": None,
    }

    # Extract Color
    for kw, canon in COLOR_KEYWORDS.items():
        if re.search(rf"\b{re.escape(kw)}\b", norm_title):
            attrs["color"] = canon
            break

    # Extract Condition
    for kw, cond in CONDITION_KEYWORDS.items():
        if kw in norm_title:
            attrs["condition"] = cond
            break

    # Extract Storage (e.g., 128GB, 256 گیگ, 1TB, 512GB, or حافظه 256)
    storage_prefix_match = re.search(r"(?:حافظه|storage)\s*[:\s]?\s*(\d{2,4})\s*(gb|tb|گیگابایت|گیگ|ترابایت)?", norm_title, re.IGNORECASE)
    if storage_prefix_match:
        val = storage_prefix_match.group(1)
        unit = (storage_prefix_match.group(2) or "gb").lower()
        if "t" in unit or "ترا" in unit:
            attrs["storage"] = f"{val}TB"
        else:
            attrs["storage"] = f"{val}GB"
    else:
        storage_match = re.search(r"(\d+)\s*(gb|tb|گیگابایت|گیگ|ترابایت)", norm_title, re.IGNORECASE)
        if storage_match:
            val = storage_match.group(1)
            unit = storage_match.group(2).lower()
            if "t" in unit or "ترا" in unit:
                attrs["storage"] = f"{val}TB"
            else:
                attrs["storage"] = f"{val}GB"

    # Extract RAM (RAM is typically 1-64 GB: رم 8, 8GB ram, رم 16 گیگ)
    ram_match = re.search(r"(?:رم|ram)\s*[:\s]?\s*(\d{1,2})\s*(?:gb|گیگ)?|(?:^|[\s,])(\d{1,2})\s*(?:gb|گیگ)?\s*(?:رم|ram)", norm_title, re.IGNORECASE)
    if ram_match:
        val = ram_match.group(1) or ram_match.group(2)
        attrs["ram"] = f"{val}GB"

    # Merge with structured specs if present
    if specs and isinstance(specs, dict):
        for k, v in specs.items():
            k_norm = normalize_persian_text(str(k)).lower()
            v_norm = normalize_digits(normalize_persian_text(str(v)))
            if "رنگ" in k_norm and not attrs["color"]:
                for kw, canon in COLOR_KEYWORDS.items():
                    if kw in v_norm.lower():
                        attrs["color"] = canon
                        break
            if ("حافظه" in k_norm or "storage" in k_norm) and not attrs["storage"]:
                m = re.search(r"(\d+)\s*(gb|tb|گیگ|ترا)", v_norm, re.IGNORECASE)
                if m:
                    attrs["storage"] = f"{m.group(1)}{'TB' if 'ت' in m.group(2) or 't' in m.group(2).lower() else 'GB'}"
            if "گارانتی" in k_norm:
                attrs["warranty"] = v_norm

    return attrs
