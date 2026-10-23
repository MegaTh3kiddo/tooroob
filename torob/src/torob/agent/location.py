"""Location Resolution and Spatial Grounding Engine for Torob Shopping Agent.

Provides robust location resolution for local physical shopping:
1. Parses explicit coordinates (lat, lon) from queries or parameters
2. Resolves neighborhoods, districts, landmarks, and transit hubs in Tehran and major cities
3. Rejects silent location assumptions; preserves uncertainty when location is missing or ambiguous
4. Integrates with DistanceRouter and VisitFeasibilityEngine
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger("torob.agent.location")


class ResolvedLocation(BaseModel):
    query_text: str
    canonical_name: str
    lat: float
    lon: float
    city: str = "Tehran"
    district: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    resolution_source: str  # "coordinates", "gazetteer_exact", "gazetteer_fuzzy", "fallback"


class LocationGazetteer:
    """Urban gazetteer covering major neighborhoods, shopping hubs, and landmarks."""

    # Curated coordinates of urban commercial centers & districts (lat, lon, city, district)
    PLACES: Dict[str, Tuple[float, float, str, str]] = {
        # Central Tehran
        "انقلاب": (35.7005, 51.3912, "Tehran", "منطقه ۶/۱۱"),
        "میدان انقلاب": (35.7005, 51.3912, "Tehran", "منطقه ۶/۱۱"),
        "دانشگاه": (35.7025, 51.3930, "Tehran", "منطقه ۶"),
        "دانشگاه تهران": (35.7025, 51.3930, "Tehran", "منطقه ۶"),
        "ولیعصر": (35.7115, 51.4072, "Tehran", "منطقه ۶"),
        "میدان ولیعصر": (35.7115, 51.4072, "Tehran", "منطقه ۶"),
        "چهارراه ولیعصر": (35.7010, 51.4035, "Tehran", "منطقه ۶/۱۱"),
        "بازار رضا": (35.7015, 51.4040, "Tehran", "مرکز کامپیوتر ایران"),
        "کریمخان": (35.7150, 51.4180, "Tehran", "منطقه ۶"),
        "هفت تیر": (35.7170, 51.4250, "Tehran", "منطقه ۷"),
        "میدان هفت تیر": (35.7170, 51.4250, "Tehran", "منطقه ۷"),
        "فردوسی": (35.6980, 51.4170, "Tehran", "منطقه ۱۲"),
        "بازار": (35.6750, 51.4200, "Tehran", "منطقه ۱۲"),
        "بازار بزرگ": (35.6750, 51.4200, "Tehran", "منطقه ۱۲"),
        "جمهوری": (35.6940, 51.4050, "Tehran", "منطقه ۱۱"),
        "علاءالدین": (35.6942, 51.4075, "Tehran", "پاساژ علاءالدین"),
        "پاساژ علاءالدین": (35.6942, 51.4075, "Tehran", "پاساژ علاءالدین"),
        "چارسو": (35.6945, 51.4090, "Tehran", "بازار چارسو"),
        "بازار چارسو": (35.6945, 51.4090, "Tehran", "بازار چارسو"),

        # Northern Tehran
        "تجریش": (35.8050, 51.4270, "Tehran", "منطقه ۱"),
        "میدان تجریش": (35.8050, 51.4270, "Tehran", "منطقه ۱"),
        "نیاوران": (35.8150, 51.4700, "Tehran", "منطقه ۱"),
        "قیطریه": (35.7920, 51.4420, "Tehran", "منطقه ۱"),
        "الهیه": (35.7900, 51.4250, "Tehran", "منطقه ۱"),
        "پایتخت": (35.7550, 51.4150, "Tehran", "مجتمع کامپیوتر پایتخت"),
        "میرداماد": (35.7600, 51.4250, "Tehran", "منطقه ۳"),
        "ونک": (35.7580, 51.4100, "Tehran", "منطقه ۳"),
        "میدان ونک": (35.7580, 51.4100, "Tehran", "منطقه ۳"),
        "سعادت آباد": (35.7833, 51.3667, "Tehran", "منطقه ۲"),
        "شهرک غرب": (35.7700, 51.3600, "Tehran", "منطقه ۲"),
        "پونک": (35.7650, 51.3400, "Tehran", "منطقه ۵"),
        "صادقیه": (35.7200, 51.3350, "Tehran", "منطقه ۲/۵"),
        "فلکه دوم صادقیه": (35.7220, 51.3360, "Tehran", "منطقه ۵"),
        "آریاشهر": (35.7200, 51.3350, "Tehran", "منطقه ۲/۵"),
        "ستارخان": (35.7180, 51.3650, "Tehran", "منطقه ۲"),
        "گیشا": (35.7350, 51.3800, "Tehran", "منطقه ۲"),
        "جنت آباد": (35.7500, 51.3100, "Tehran", "منطقه ۵"),

        # Eastern Tehran
        "تهرانپارس": (35.7300, 51.5300, "Tehran", "منطقه ۴/۸"),
        "فلکه اول تهرانپارس": (35.7280, 51.5280, "Tehran", "منطقه ۸"),
        "نارمک": (35.7250, 51.5000, "Tehran", "منطقه ۸"),
        "رسالت": (35.7350, 51.4750, "Tehran", "منطقه ۴/۸"),
        "میدان رسالت": (35.7350, 51.4750, "Tehran", "منطقه ۴/۸"),
        "پیروزی": (35.6950, 51.4700, "Tehran", "منطقه ۱۳/۱۴"),

        # Other Metropolitan Centers
        "کرج": (35.8327, 50.9915, "Karaj", "البرز"),
        "اصفهان": (32.6546, 51.6680, "Isfahan", "اصفهان"),
        "مشهد": (36.2972, 59.6067, "Mashhad", "خراسان رضوی"),
        "شیراز": (29.5918, 52.5837, "Shiraz", "فارس"),
        "تبریز": (38.0800, 46.2919, "Tabriz", "آذربایجان شرقی"),
    }


class LocationResolver:
    """Resolves spatial constraints without silent assumptions."""

    def __init__(self, gazetteer: Optional[LocationGazetteer] = None):
        self.gazetteer = gazetteer or LocationGazetteer()

    def resolve(self, text: str) -> Optional[ResolvedLocation]:
        """Resolves location from free text or explicit coordinates."""
        if not text:
            return None

        # 1. Check for explicit coordinates format: "35.7005, 51.3912" or "35.7005 51.3912"
        coord_match = re.search(r"(\d{2}\.\d+)[,\s]+(\d{2}\.\d+)", text)
        if coord_match:
            try:
                lat = float(coord_match.group(1))
                lon = float(coord_match.group(2))
                # Validate range for Iran
                if 25.0 <= lat <= 40.0 and 44.0 <= lon <= 64.0:
                    return ResolvedLocation(
                        query_text=text.strip(),
                        canonical_name=f"مختصات جغرافیایی ({lat:.4f}, {lon:.4f})",
                        lat=lat,
                        lon=lon,
                        city="Custom Coordinates",
                        confidence=1.0,
                        resolution_source="coordinates",
                    )
            except ValueError:
                pass

        # 2. Check Gazetteer places (longest match first to prioritize 'میدان ولیعصر' over 'ولیعصر')
        clean_text = text.replace("‌", " ").strip()
        sorted_keys = sorted(self.gazetteer.PLACES.keys(), key=len, reverse=True)

        for place_key in sorted_keys:
            if place_key in clean_text:
                lat, lon, city, district = self.gazetteer.PLACES[place_key]
                return ResolvedLocation(
                    query_text=text.strip(),
                    canonical_name=place_key,
                    lat=lat,
                    lon=lon,
                    city=city,
                    district=district,
                    confidence=0.95,
                    resolution_source="gazetteer_exact",
                )

        return None
