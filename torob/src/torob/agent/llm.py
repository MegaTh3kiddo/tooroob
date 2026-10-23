"""LLM Provider Abstraction and Deterministic Fallback Parser.

Supports:
1. External LLM via OpenAI/Gemini compatible API (keys from env, no hardcoded secrets)
2. Safe Deterministic Fallback Parser with Persian digit & scale parsing ("۷۰ میلیون", "تا ۳۰ تومن")
3. Token and cost tracking, timeouts, retries, and prompt injection protection.
"""

from datetime import datetime, timezone
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel, ConfigDict, Field

from torob.agent.location import LocationResolver
from torob.agent.models import ShoppingConstraints, ShoppingIntent
from torob.agent.tools import AgentToolRegistry, sanitize_untrusted_text
from torob.ingestion.normalizer import (
    extract_variant_attributes,
    normalize_digits,
    normalize_persian_text,
)

logger = logging.getLogger("torob.agent.llm")

# Known Tehran landmark coordinates for local physical intent
TEHRAN_LANDMARKS = {
    "انقلاب": (35.7005, 51.3912),
    "دانشگاه": (35.7025, 51.3930),
    "ولیعصر": (35.7115, 51.4072),
    "کریمخان": (35.7150, 51.4180),
    "سعادت آباد": (35.7833, 51.3667),
    "شهرک غرب": (35.7700, 51.3600),
    "بازار": (35.6750, 51.4200),
    "تجریش": (35.8050, 51.4270),
    "پایتخت": (35.7550, 51.4150),
}


# Common product nouns (longest first) used when no dedicated category rule matches.
GENERIC_PRODUCT_NOUNS = [
    "ساعت هوشمند", "هندزفری", "ایرپاد", "هدفون", "هدست", "اسپیکر", "تبلت", "کیبورد", "ماوس",
    "مانیتور", "تلویزیون", "یخچال", "لباسشویی", "ظرفشویی", "جاروبرقی", "پاوربانک", "شارژر",
    "کابل", "دوربین", "پرینتر", "هارد", "فلش", "مودم", "روتر", "کنسول", "پلی استیشن", "اتو",
    "سشوار", "ریش تراش", "مایکروویو", "کولر", "بخاری", "برنج", "روغن",
]


class LLMResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    content: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost_usd: float = 0.0
    model_name: str = "deterministic_fallback"


class BaseLLMProvider:
    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        raise NotImplementedError


class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout_seconds: float = 15.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout_seconds

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": 0.2,
        }
        if tools:
            payload["tools"] = tools

        try:
            with httpx.Client(timeout=self.timeout, trust_env=False) as client:
                res = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()

            choice = data["choices"][0]["message"]
            usage = data.get("usage", {})
            prompt_toks = usage.get("prompt_tokens", 0)
            comp_toks = usage.get("completion_tokens", 0)
            # Approx cost: $0.15/1M input, $0.60/1M output
            cost = (prompt_toks * 0.00000015) + (comp_toks * 0.00000060)

            tool_calls = choice.get("tool_calls", [])
            parsed_tools = []
            for tc in tool_calls:
                fn = tc.get("function", {})
                args_str = fn.get("arguments", "{}")
                try:
                    args = json.loads(args_str)
                except Exception:
                    args = {}
                parsed_tools.append({"name": fn.get("name"), "arguments": args})

            return LLMResponse(
                content=choice.get("content") or "",
                tool_calls=parsed_tools,
                prompt_tokens=prompt_toks,
                completion_tokens=comp_toks,
                total_cost_usd=round(cost, 6),
                model_name=self.model,
            )
        except Exception as e:
            logger.warning(f"External LLM call failed ({e}); falling back to deterministic parser.")
            raise e


class DeterministicFallbackParser:
    """Robust offline Persian & English rule-based intent and constraint parser."""

    _location_resolver = LocationResolver()

    @classmethod
    def parse_message(
        cls, text: str, current_constraints: Optional[ShoppingConstraints] = None
    ) -> Tuple[ShoppingIntent, ShoppingConstraints]:
        norm_text = normalize_digits(normalize_persian_text(text)).strip()
        lower_text = norm_text.lower()
        constraints = current_constraints.model_copy() if current_constraints else ShoppingConstraints()

        # 1. Negative brand extraction ("سامسونگ نباشه", "به جز اپل", "بدون شیائومی")
        excluded = list(constraints.excluded_brands)
        negative_patterns = [
            (r"(?:به جز|غیر از|بدون)\s+(سامسونگ|samsung)", "Samsung"),
            (r"(?:به جز|غیر از|بدون)\s+(اپل|آیفون|apple|iphone)", "Apple"),
            (r"(?:به جز|غیر از|بدون)\s+(شیائومی|شیاومی|xiaomi)", "Xiaomi"),
            (r"(?:به جز|غیر از|بدون)\s+(ایسوس|asus)", "Asus"),
            (r"(?:به جز|غیر از|بدون)\s+(لنوو|lenovo)", "Lenovo"),
            (r"(?:به جز|غیر از|بدون)\s+(اچ پی|hp)", "HP"),
            (r"(سامسونگ|samsung)(?:\s+\S+)?\s*(?:نباشه|نباشد|نمیخوام|نمی‌خوام|نه)", "Samsung"),
            (r"(اپل|آیفون|apple|iphone)(?:\s+\S+)?\s*(?:نباشه|نباشد|نمیخوام|نمی‌خوام|نه)", "Apple"),
            (r"(شیائومی|شیاومی|xiaomi)(?:\s+\S+)?\s*(?:نباشه|نباشد|نمیخوام|نمی‌خوام|نه)", "Xiaomi"),
            (r"(ایسوس|asus)(?:\s+\S+)?\s*(?:نباشه|نباشد|نمیخوام|نمی‌خوام|نه)", "Asus"),
            (r"(لنوو|lenovo)(?:\s+\S+)?\s*(?:نباشه|نباشد|نمیخوام|نمی‌خوام|نه)", "Lenovo"),
            (r"(اچ پی|hp)(?:\s+\S+)?\s*(?:نباشه|نباشد|نمیخوام|نمی‌خوام|نه)", "HP"),
        ]
        for pat, brand in negative_patterns:
            if re.search(pat, lower_text) and brand not in excluded:
                excluded.append(brand)
        constraints.excluded_brands = excluded

        # 2. Rejection / refusal of previous recommendations
        specific_index_rejection = False
        if any(w in lower_text for w in ["نمیخوام", "رد کن", "دوست ندارم", "نه", "حذف کن"]):
            if any(w in lower_text for w in ["دومی", "دوم", "گزینه ۲", "دومین"]):
                constraints.preferred_specs["action"] = "reject_specific_index"
                constraints.preferred_specs["reject_index"] = 1
                specific_index_rejection = True
            elif any(w in lower_text for w in ["اولی", "اول", "گزینه ۱", "اولین"]):
                constraints.preferred_specs["action"] = "reject_specific_index"
                constraints.preferred_specs["reject_index"] = 0
                specific_index_rejection = True
            elif any(w in lower_text for w in ["سومی", "سوم", "گزینه ۳", "سومین"]):
                constraints.preferred_specs["action"] = "reject_specific_index"
                constraints.preferred_specs["reject_index"] = 2
                specific_index_rejection = True

        rejection_words = [
            "اینا رو دوست ندارم", "اینارو دوست ندارم", "نمیپسندم", "نمی‌پسندم",
            "پیشنهاد دیگ", "پیشنهادات دیگر", "گزینه های دیگر", "گزینه دیگری",
            "هیچکدوم", "هیچکدام", "رد کن", "مورد پسند نبود", "مدل های دیگر", "مدل‌های دیگر"
        ]
        is_rejection = any(rw in lower_text for rw in rejection_words)
        if is_rejection and not specific_index_rejection:
            constraints.preferred_specs["action"] = "reject_previous"

        # Adaptive replanning detection ("فروشگاه اول گفت SSD نداره. برنامه رو دوباره بچین.")
        is_conditional = any(w in lower_text for w in ["اگه ", "اگر ", "چنانچه "])
        is_replan = any(w in lower_text for w in ["دوباره بچین", "مجدد بچین", "برنامه رو دوباره", "برنامه جدید", "دوباره برنامه", "دوباره بچینید"])
        seller_out_of_stock = (
            any(w in lower_text for w in ["گفت", "میگه", "اعلام کرد"])
            and any(w in lower_text for w in ["نداره", "موجود نیست", "تموم کرده", "ناموجود"])
            and any(w in lower_text for w in ["فروشگاه", "مغازه", "فروشنده"])
        )
        if (is_replan or seller_out_of_stock) and not is_conditional:
            unavailable_item = None
            for itm in ["ssd", "اس اس دی", "مانیتور", "کیبورد", "موس", "ماوس", "رم", "هارد", "گرافیک"]:
                if itm in lower_text:
                    unavailable_item = itm.upper() if itm in ["ssd", "ram", "gpu"] else itm
                    break
            constraints.preferred_specs["action"] = "adaptive_replan"
            if unavailable_item:
                constraints.reported_unavailable_items.append(unavailable_item)
                constraints.preferred_specs["unavailable_item"] = unavailable_item

        # 3. Contextual budget extraction (Accessory vs Device vs Millions)
        is_accessory = any(w in lower_text for w in [
            "کابل", "شارژر", "کلگی", "آداپتور", "گلس", "محافظ", "قاب", "کاور", "هولدر", "پاوربانک", "هندزفری", "تبدیل"
        ])
        is_device = any(w in lower_text for w in [
            "گوشی", "موبایل", "لپ‌تاپ", "لپ تاپ", "سیستم", "کارت گرافیک", "کامپیوتر", "تبلت", "مادربرد", "پردازنده"
        ])

        explicit_budget_found = False
        range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:تا|-)\s*(\d+(?:\.\d+)?)\s*(?:میلیون|ملیون)", norm_text)
        budget_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:میلیون|همت|ملیون)", norm_text)
        if range_match:
            lo, hi = sorted([float(range_match.group(1)), float(range_match.group(2))])
            constraints.budget_min_toman = lo * 1_000_000
            constraints.budget_max_toman = hi * 1_000_000
            constraints.budget_confidence = "confident"
            explicit_budget_found = True
        elif budget_match:
            millions = float(budget_match.group(1))
            val_toman = millions * 1_000_000
            constraints.budget_confidence = "confident"
            explicit_budget_found = True
            if any(w in norm_text for w in ["حداقل", "بیشتر از", "بالای"]):
                constraints.budget_min_toman = val_toman
            else:
                constraints.budget_max_toman = val_toman
        else:
            colloquial_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:تومان|تومن)", norm_text)
            if colloquial_match:
                raw_num = float(colloquial_match.group(1))
                explicit_budget_found = True
                if is_accessory and raw_num <= 1000:
                    val_toman = raw_num * 1_000
                    constraints.budget_confidence = "confident"
                elif is_device and raw_num <= 500:
                    val_toman = raw_num * 1_000_000
                    constraints.budget_confidence = "confident"
                elif raw_num <= 500:
                    val_toman = raw_num * 1_000_000
                    constraints.budget_confidence = "ambiguous"
                else:
                    val_toman = raw_num
                    constraints.budget_confidence = "confident"

                if any(w in norm_text for w in ["حداقل", "بیشتر از", "بالای"]):
                    constraints.budget_min_toman = val_toman
                else:
                    constraints.budget_max_toman = val_toman
            else:
                toman_match = re.search(r"(\d{6,11})\s*(?:تومان|تومن|ریال)?", norm_text)
                if toman_match:
                    constraints.budget_max_toman = float(toman_match.group(1))
                    constraints.budget_confidence = "confident"
                    explicit_budget_found = True

        # Check relative budget increase ONLY if no explicit budget number was provided in this message
        if not explicit_budget_found and any(w in lower_text for w in ["بودجه رو بیشتر کن", "افزایش بده", "بودجه را افزایش بده", "بیشتر کن"]):
            if constraints.budget_max_toman:
                constraints.budget_max_toman = constraints.budget_max_toman * 1.25

        # 4. Reliability preference
        if any(w in lower_text for w in ["فروشگاه معتبر", "فروشگاه مطمئن", "فروشگاه با سابقه", "امتیاز بالا", "قابل اعتماد", "معتبرتر"]):
            constraints.min_shop_reliability = 0.65

        # 5. Battery and spec preferences
        if any(w in lower_text for w in ["باتری قوی", "شارژدهی بالا", "باتری خوب", "شارژدهی طولانی", "شارژ بالا"]):
            constraints.battery_preference = "high_battery_life"
        if any(w in lower_text for w in ["سبک", "وزن کم"]):
            constraints.preferred_specs["weight"] = "lightweight"
        if any(w in lower_text for w in ["مدل جدید", "نسل جدید", "مدل‌های جدید", "مدل های جدید", "جدیدتر"]):
            constraints.newer_models_only = True

        # 6. Extract Device Category / Target Product
        if any(w in lower_text for w in ["لپ تاپ", "لپ‌تاپ", "laptop", "نوت بوک"]):
            constraints.target_category = "لپ تاپ و نوت بوک"
            constraints.preferred_specs["device_type"] = "لپ‌تاپ"
        elif any(w in lower_text for w in ["گوشی", "موبایل", "phone", "smartphone"]):
            constraints.target_category = "گوشی موبایل"
            constraints.preferred_specs["device_type"] = "گوشی موبایل"
        elif any(w in lower_text for w in ["کارت گرافیک", "gpu", "graphics"]):
            constraints.target_category = "قطعات کامپیوتر"
            constraints.preferred_specs["device_type"] = "کارت گرافیک"
        elif any(w in lower_text for w in ["مادربرد", "motherboard", "مین برد"]):
            constraints.target_category = "قطعات کامپیوتر"
            constraints.preferred_specs["device_type"] = "مادربرد"
        elif any(w in lower_text for w in ["پردازنده", "cpu", "سی پی یو"]):
            constraints.target_category = "قطعات کامپیوتر"
            constraints.preferred_specs["device_type"] = "پردازنده"
        else:
            # Generic product nouns: drive catalogue retrieval by the product the user named
            for noun in GENERIC_PRODUCT_NOUNS:
                if noun in lower_text:
                    constraints.preferred_specs["device_type"] = noun
                    break

        # 7. Extract Brand
        brands_map = {
            "سامسونگ": "Samsung",
            "samsung": "Samsung",
            "اپل": "Apple",
            "apple": "Apple",
            "آیفون": "Apple",
            "iphone": "Apple",
            "ایسوس": "Asus",
            "asus": "Asus",
            "لنوو": "Lenovo",
            "lenovo": "Lenovo",
            "شیائومی": "Xiaomi",
            "xiaomi": "Xiaomi",
            "اچ پی": "HP",
            "hp": "HP",
            "هواوی": "Huawei",
            "huawei": "Huawei",
            "سونی": "Sony",
            "sony": "Sony",
            "نوکیا": "Nokia",
            "nokia": "Nokia",
            "انکر": "Anker",
            "anker": "Anker",
            "لاجیتک": "Logitech",
            "logitech": "Logitech",
        }
        matched_brands = []
        for kw, canon in brands_map.items():
            if kw in lower_text and canon not in matched_brands and canon not in constraints.excluded_brands:
                matched_brands.append(canon)
        if matched_brands:
            constraints.target_brand = matched_brands[0]
            if len(matched_brands) > 1:
                constraints.preferred_specs["compared_brands"] = matched_brands

        # If previously target_brand was excluded in this turn, clear it
        if constraints.target_brand in constraints.excluded_brands:
            constraints.target_brand = None

        # 8. Extract Variant Attributes (storage, ram, color)
        attrs = extract_variant_attributes(norm_text)
        if attrs.get("storage"):
            constraints.storage = attrs["storage"]
        if attrs.get("ram"):
            constraints.ram = attrs["ram"]
        if attrs.get("color"):
            constraints.color = attrs["color"]
        if attrs.get("condition") and attrs["condition"] != "new":
            constraints.condition = attrs["condition"]

        # 9. Extract Journey & On-Route Spatial Constraints ("از صادقیه برم تجریش توی راه...")
        route_pattern = re.search(
            r"از\s+([^\s،,]+(?:\s+[^\s،,]+)?)\s+(?:میخوام\s+)?(?:برم|میرم|میروم|حرکت|تا|به سمت|سمت|به)\s+([^\s،,]+(?:\s+[^\s،,]+)?)",
            norm_text,
        )
        if route_pattern:
            orig_candidate = route_pattern.group(1).replace("میدان", "").replace("میخوام", "").strip()
            dest_candidate = route_pattern.group(2).replace("میدان", "").replace("میخوام", "").strip()
            orig_loc = cls._location_resolver.resolve(orig_candidate)
            dest_loc = cls._location_resolver.resolve(dest_candidate)
            if orig_loc:
                constraints.origin_name = orig_loc.canonical_name
                constraints.origin_lat = orig_loc.lat
                constraints.origin_lon = orig_loc.lon
                # Set as user location as well
                constraints.user_lat = orig_loc.lat
                constraints.user_lon = orig_loc.lon
            if dest_loc:
                constraints.destination_name = dest_loc.canonical_name
                constraints.destination_lat = dest_loc.lat
                constraints.destination_lon = dest_loc.lon

        # Extract On-Route item search term
        if any(w in lower_text for w in ["توی راه", "در مسیر", "سر راه", "بین راه"]):
            item_on_route = re.search(r"(?:توی راه|در مسیر|سر راه|بین راه)\s+(?:یه\s+)?([^،,\.\n]+?)(?:\s+هم|\s+میخوام|\s+بخرم|\s+پیدا|$)", norm_text)
            if item_on_route:
                found_item = item_on_route.group(1).strip()
                if len(found_item) > 2:
                    constraints.target_product_title = found_item

        # Extract Max Detour Minutes ("کمتر از ۲۰ دقیقه انحراف" or "بیشتر از ۲۰ دقیقه هم دور نشم")
        detour_m = re.search(r"(\d+)\s*دقیقه\s*(?:انحراف|بیشتر|دور|معطلی|فاصله|هم\s+دور)", norm_text)
        if detour_m:
            constraints.max_detour_minutes = float(detour_m.group(1))

        # Extract Max Stops ("بیشتر از ۲ مغازه نمیخوام برم")
        stops_m = re.search(r"(?:بیشتر از|حداکثر|سقف|تا)\s*(\d+)\s*(?:مغازه|فروشگاه|توقف|جا)", norm_text)
        if stops_m:
            constraints.max_stops = int(stops_m.group(1))

        # Extract Multi-Product Basket items (e.g. "مانیتور، کیبورد و موس")
        basket_terms = ["مانیتور", "کیبورد", "موس", "ماوس", "هدست", "اس اس دی", "ssd", "هارد", "رم", "کارت گرافیک", "پاور", "مادربرد", "کابل"]
        detected_in_basket = [t for t in basket_terms if t in lower_text]
        if len(detected_in_basket) >= 2:
            constraints.basket_queries = detected_in_basket

        # Extract Single-Store vs Multi-Store requirement
        if any(w in lower_text for w in ["اگه یه فروشگاه نداره", "اگه یک فروشگاه نداره", "اگه یک مغازه نداره", "اگه یه مغازه نداره", "نداره", "نبود", "نیست", "چند مغازه", "چند فروشگاه"]) and any(w in lower_text for w in ["نزدیک", "چند", "هم", "جدا"]):
            constraints.require_single_store = False
        elif any(w in lower_text for w in ["از یک مغازه", "از یک فروشگاه", "از یه مغازه", "از یه فروشگاه", "از یه جا", "کدوم فروشگاه هر سه", "کدوم فروشگاه همه"]) or (any(w in lower_text for w in ["یک فروشگاه همه", "یه فروشگاه همه"]) and not any(w in lower_text for w in ["نداره", "نبود", "نیست"])):
            constraints.require_single_store = True

        # Extract Optimization Priority with Negation Handling
        cheapest_negated = any(w in lower_text for w in ["ارزونترین مهم نیست", "ارزان‌ترین مهم نیست", "ارزونتر مهم نیست", "دیگه ارزونترین", "دیگه ارزان‌ترین"])
        if any(w in lower_text for w in ["سریع‌ترین", "سریعترین", "فوری"]):
            constraints.optimization_priority = "fastest"
        elif any(w in lower_text for w in ["فروشگاه مطمئن‌تر", "فروشگاه مطمئنتر", "معتبرترین", "بالاترین اعتبار", "مطمئن تر", "مطمئنتر"]):
            constraints.optimization_priority = "highest_trust"
            constraints.min_shop_reliability = 0.70
        elif any(w in lower_text for w in ["نزدیک‌ترین", "کمترین مسافت", "کمترین انحراف", "مسیر کوتاه"]):
            constraints.optimization_priority = "minimum_travel"
        elif any(w in lower_text for w in ["کمترین توقف", "یکجا", "تعداد مغازه کمتر"]):
            constraints.optimization_priority = "fewest_stops"
        elif any(w in lower_text for w in ["ارزونترین", "ارزان‌ترین", "کمترین هزینه", "به‌صرفه‌تر", "به صرفه تر"]) and not cheapest_negated:
            constraints.optimization_priority = "cheapest"

        # Extract Criteria Weights for Personalized Comparison ("باتری و وزن برام از گرافیک مهمتره")
        if any(w in lower_text for w in ["مهمتر", "مهم‌تر", "اولویت"]):
            priorities = {}
            if "باتری" in lower_text:
                priorities["battery"] = 0.35
            if any(w in lower_text for w in ["وزن", "سبک"]):
                priorities["weight"] = 0.35
            if "گرافیک" in lower_text and any(w in lower_text for w in ["کمتر", "مهم نیست", "از گرافیک"]):
                priorities["gpu"] = 0.05
            if priorities:
                constraints.preferred_specs["user_priorities"] = priorities

        # 10. Extract Location using LocationResolver (for single point)
        resolved_loc = cls._location_resolver.resolve(norm_text)
        if resolved_loc:
            constraints.user_lat = resolved_loc.lat
            constraints.user_lon = resolved_loc.lon
            constraints.location_name = resolved_loc.canonical_name

        # 11. Intent Detection
        has_specific_product = bool(
            constraints.target_category
            or constraints.preferred_specs.get("device_type")
            or constraints.target_product_title
            or constraints.target_brand
        )
        is_greeting_or_chat = any(w in lower_text for w in [
            "سلام", "درود", "صبح بخیر", "عصر بخیر", "خسته نباشید", "چطوری", "خوبی",
            "چیکار میتونی", "چیکار می‌تونی", "کمکم کن", "راهنماییم کن", "راهنمایی",
            "استعلام چیه", "چطور استعلام", "چطوری استعلام", "درباره ترب", "کی هستی",
            "چطور خرید کنم", "راهنما",
            "غذا", "خوراکی", "رستوران", "سوپرمارکت", "پوشاک", "لباس",
            "چی داری", "چی دارید", "چه چیزهایی داری", "چه محصولاتی داری", "چه کالاهایی داری",
            "داری؟", "دارید؟", "هم داری", "هم دارید",
            "ممنون", "مرسی", "تشکر", "دمت گرم", "دستت درد نکنه", "سپاس", "خداحافظ"
        ])
        if constraints.preferred_specs.get("action") == "adaptive_replan":
            intent = ShoppingIntent.ADAPTIVE_REPLAN
        elif is_rejection or specific_index_rejection or any(w in lower_text for w in ["افزایش بده", "تغییر بده", "ترجیح میدم", "سبک‌تر", "رنگ دیگر", "نباشه", "معتبرتر", "مطمئنتر", "مطمئن‌تر", "دیگه", "مهم نیست", "عوض کن"]):
            intent = ShoppingIntent.REFINEMENT
        elif is_greeting_or_chat and not has_specific_product and not constraints.budget_max_toman:
            intent = ShoppingIntent.GENERAL_CHAT
        elif any(w in lower_text for w in ["توی راه", "در مسیر", "سر راه", "بین راه"]) or (constraints.origin_lat and constraints.destination_lat):
            intent = ShoppingIntent.ON_ROUTE_PURCHASE
        elif any(w in lower_text for w in ["کدوم برای من بهتره", "کدام برای من بهتر است", "کدوم برای من مناسب تره"]) or (
            any(w in lower_text for w in ["بین این", "از بین این"]) and any(w in lower_text for w in ["مهمتر", "مهم‌تر", "اولویت", "مناسب"])
        ):
            intent = ShoppingIntent.PERSONALIZED_SELECTION
        elif len(constraints.basket_queries) >= 2 or (current_constraints and len(current_constraints.basket_queries) >= 2):
            if constraints.require_single_store:
                intent = ShoppingIntent.SINGLE_STORE_BASKET
            elif any(w in lower_text for w in ["نزدیک هم", "نزدیک به هم", "محدوده تجاری", "راسته بازار", "چند مغازه نزدیک"]):
                intent = ShoppingIntent.NEARBY_STORE_CLUSTER
            else:
                intent = ShoppingIntent.MULTI_STORE_BASKET
        elif any(w in lower_text for w in ["سبد", "سی پی یو و رم", "مادربرد", "اسمبل", "سیستم پیشنهادی", "سازگاری قطعات", "قطعات کامپیوتر"]):
            intent = ShoppingIntent.MULTI_PRODUCT
        elif any(w in lower_text for w in ["مقایسه", "کدوم بهتره", "کدام بهتر است", "فرق بین", "بین این دو"]) or re.search(r"\bیا\b", lower_text) or len(matched_brands) > 1:
            intent = ShoppingIntent.PRODUCT_COMPARISON
            constraints.target_product_title = norm_text
        elif any(w in lower_text for w in ["امروز", "حضوری", "نزدیک", "ساعات کاری", "مغازه"]):
            intent = ShoppingIntent.LOCAL_PHYSICAL
            constraints.urgency = "urgent_today"
        elif "iphone 16" in lower_text or "s23 ultra" in lower_text or "galaxy s24" in lower_text:
            intent = ShoppingIntent.EXACT_SEARCH
            constraints.target_product_title = norm_text.split("میخوام")[0].split("دارید")[0].strip()
        elif any(w in lower_text for w in ["زیر", "کمتر از", "سقف", "حداکثر"]) and constraints.budget_max_toman:
            intent = ShoppingIntent.BUDGET_SEARCH
        elif any(w in lower_text for w in ["برای", "جهت", "مناسب", "کاربری", "برنامه نویسی", "برنامه‌نویسی", "گیمینگ", "دانشجویی", "طراحی"]):
            intent = ShoppingIntent.NEEDS_BASED
        elif constraints.budget_max_toman and not constraints.target_product_title:
            intent = ShoppingIntent.BUDGET_SEARCH
        elif not has_specific_product and not constraints.budget_max_toman and not constraints.target_brand:
            intent = ShoppingIntent.GENERAL_CHAT
        else:
            intent = ShoppingIntent.NEEDS_BASED

        return intent, constraints


class LLMToolOrchestrator:
    """Multi-step tool calling orchestration loop with safety guards, timeout, and execution tracing."""

    def __init__(
        self,
        provider: BaseLLMProvider,
        tool_registry: AgentToolRegistry,
        max_steps: int = 4,
    ):
        self.provider = provider
        self.tool_registry = tool_registry
        self.max_steps = max_steps

    def run_agent_loop(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
    ) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Executes bounded tool-calling loop until the LLM returns a final text answer
        or max_steps is reached.
        """
        current_messages = list(messages)
        tools = self.tool_registry.get_tool_definitions()
        trace: List[Dict[str, Any]] = []
        total_prompt_toks = 0
        total_comp_toks = 0
        total_cost = 0.0

        for step in range(self.max_steps):
            try:
                resp = self.provider.chat_completion(
                    messages=current_messages,
                    tools=tools,
                    system_prompt=system_prompt,
                )
            except Exception as e:
                logger.warning(f"LLM tool loop failed at step {step}: {e}")
                return "", trace, {"error": str(e), "fallback": True}

            total_prompt_toks += resp.prompt_tokens
            total_comp_toks += resp.completion_tokens
            total_cost += resp.total_cost_usd

            # If no tool calls requested, we have the final assistant response
            if not resp.tool_calls:
                return resp.content, trace, {
                    "steps": step + 1,
                    "prompt_tokens": total_prompt_toks,
                    "completion_tokens": total_comp_toks,
                    "total_cost_usd": round(total_cost, 6),
                    "model_name": resp.model_name,
                }

            # Execute tool calls
            for tc in resp.tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("arguments", {})
                res = self.tool_registry.execute_tool(tool_name, tool_args)
                trace.append({
                    "step": step + 1,
                    "tool": tool_name,
                    "arguments": tool_args,
                    "result": res,
                })
                # Append assistant tool call and tool result to current_messages
                current_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": f"call_{step}_{tool_name}",
                        "type": "function",
                        "function": {"name": tool_name, "arguments": json.dumps(tool_args)},
                    }]
                })
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": f"call_{step}_{tool_name}",
                    "content": sanitize_untrusted_text(json.dumps(res, ensure_ascii=False)),
                })

        # Bounded steps exhausted: request final summary
        summary_resp = self.provider.chat_completion(
            messages=current_messages,
            tools=None,
            system_prompt=system_prompt + "\nابزارهای مورد نیاز اجرا شدند. اکنون پاسخ نهایی را به کاربر ارائه دهید.",
        )
        return summary_resp.content, trace, {
            "steps": self.max_steps,
            "prompt_tokens": total_prompt_toks + summary_resp.prompt_tokens,
            "completion_tokens": total_comp_toks + summary_resp.completion_tokens,
            "total_cost_usd": round(total_cost + summary_resp.total_cost_usd, 6),
            "model_name": summary_resp.model_name,
        }


def get_llm_client() -> Optional[BaseLLMProvider]:
    """Factory creating the configured OpenAI-compatible provider (OpenAI, BoxAPI, OpenRouter, Gemini's
    OpenAI endpoint, a local vLLM/Ollama gateway, ...). Returns None — fully offline deterministic mode —
    when TOROB_LLM_PROVIDER=none or no API key is set."""
    provider = os.environ.get("TOROB_LLM_PROVIDER", "openai_compatible").strip().lower()
    if provider in ("none", "off", "disabled", "false", "0"):
        return None
    api_key = os.environ.get("TOROB_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key.startswith("mock") or api_key.startswith("dummy"):
        return None

    base_url = os.environ.get("TOROB_LLM_BASE_URL") or (
        "https://generativelanguage.googleapis.com/v1beta/openai" if os.environ.get("GEMINI_API_KEY") else "https://api.openai.com/v1"
    )
    model = os.environ.get("TOROB_LLM_MODEL") or (
        "gemini-3.1-flash-lite" if os.environ.get("GEMINI_API_KEY") else "gpt-4o-mini"
    )
    try:
        timeout = float(os.environ.get("TOROB_LLM_TIMEOUT_SECONDS", "12"))
    except ValueError:
        timeout = 12.0
    return OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model=model, timeout_seconds=timeout)


def llm_polish_enabled() -> bool:
    return os.environ.get("TOROB_LLM_POLISH_REPLIES", "true").strip().lower() not in ("0", "false", "no", "off")


_EXTRACT_PROMPT = (
    "You extract shopping constraints from one Persian (or English) user message for an Iranian price-comparison "
    "site. Reply with ONLY a JSON object, no prose, with these keys (use null when not stated): "
    '"product" (short Persian product noun as it would appear at the start of a product title, e.g. "هدفون", '
    '"یخچال", "گوشی موبایل"), "brand" (English brand name, e.g. "Samsung"), '
    '"budget_min_toman" (number), "budget_max_toman" (number). Convert "۲ میلیون" to 2000000. '
    "Never guess values that are not in the message."
)


def _first_json_object(text: str) -> Optional[Dict[str, Any]]:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def llm_extract_constraints(client: BaseLLMProvider, user_message: str) -> Dict[str, Any]:
    """Asks the LLM to parse constraints. Only returns values; never raises (offline parser stays primary)."""
    try:
        resp = client.chat_completion(
            messages=[{"role": "user", "content": sanitize_untrusted_text(user_message)}],
            system_prompt=_EXTRACT_PROMPT,
        )
        return _first_json_object(resp.content) or {}
    except Exception as e:
        logger.warning(f"LLM constraint extraction skipped: {e}")
        return {}


_POLISH_PROMPT = (
    "You are TorobChat, a friendly Persian shopping assistant on TorobMap. Rewrite the DRAFT answer below into short, warm, "
    "natural Persian (max ~8 lines). STRICT RULES: use ONLY facts from the draft; do not add, change or round any "
    "price, number, shop name, stock or reliability figure; do not invent products or availability; keep the same "
    "order of items. Plain text with **bold** allowed."
)

_CHAT_SYSTEM_PROMPT = (
    "شما «ترب‌چت» (TorobChat)، دستیار هوشمند، بسیار صمیمی، دانا و دقیق خرید در سامانه ترب‌مپ (TorobMap) هستید. "
    "شما با کاربران فارسی‌زبان به شکلی صمیمی، محترمانه، روان، جذاب و راهنما گفتگو می‌کنید (نه رباتیک یا خشک). "
    "وظیفه شما راهنمایی خرید، پاسخ به سوالات، مشاوره درباره محصولات، مقایسه تخصصی و راهنمایی درباره استعلام و خرید حضوری است.\n"
    "قوانین مهم و غیرقابل تخطی:\n"
    "۱. اگر اطلاعات کاتالوگ یا محصولات واقعی در پیام ارائه‌شده وجود دارد، فقط و فقط بر اساس همان مشخصات، قیمت‌ها و فروشگاه‌ها صحبت کنید. هرگز قیمت یا فروشگاه ساختگی یا تخمینی از خود ایجاد نکنید.\n"
    "۲. اگر کاربر احوالپرسی یا سلام کرد، گرم و مشتاقانه پاسخ دهید و بپرسید چطور می‌توانید در خرید یا انتخاب کالا کمکش کنید.\n"
    "۳. پاسخ‌ها منسجم، مفید، خوانا (با بولت‌پوینت‌های کوتاه و متون تفکیک‌شده و بولد) باشند.\n"
    "۴. در انتهای پاسخ، در صورت لزوم یک سوال راهنما یا پیشنهاد مناسب مطرح کنید تا کاربر بتواند گفتگو را ادامه دهد.\n"
    "۵. سامانه «ترب‌مپ» مختص کالاهای دیجیتال، موبایل، لپ‌تاپ، لوازم جانبی و قطعات کامپیوتر و الکترونیکی است و اقلام غذایی، سوپرمارکتی، رستورانی یا پوشاک ندارد. اگر کاربر در مورد این اقلام سوال کرد (مثلاً «غذا داری؟»)، خیلی صمیمی و با لبخند توضیح دهید که تخصص ترب‌مپ کالای دیجیتال و الکترونیک است و غذا ندارد، و او را به جستجوی محصولات دیجیتال دعوت کنید.\n"
    "۶. هرگز در پاسخ از نمره اعتماد یا شایستگی یا کلمات و درصدهای آماری داخلی استفاده نکنید. به جای آن، درباره ویژگی‌ها و مشخصات فنی محصول (مثل کیفیت ساخت، کارایی، قابلیت‌ها، شارژدهی، ارزش خرید نسبت به قیمت) و وضعیت باز بودن فروشگاه صحبت کنید."
)


def _numbers(text: str) -> set:
    return set(re.findall(r"\d[\d,]*", normalize_digits(text or "")))


def _price_numbers(text: str) -> set:
    """Extracts large numeric tokens (prices >= 10,000) to ensure groundedness without blocking list numbering or specs."""
    nums = set()
    for token in re.findall(r"\d[\d,]*", normalize_digits(text or "")):
        clean = token.replace(",", "")
        try:
            val = float(clean)
            if val >= 10_000:
                nums.add(int(val))
        except ValueError:
            pass
    return nums


def llm_polish_reply(client: BaseLLMProvider, draft: str, user_message: str = "") -> Optional[str]:
    """Rephrases a grounded draft. Guarded against introducing ungrounded prices."""
    try:
        content = f"DRAFT:\n{draft}"
        if user_message:
            content = f"USER MESSAGE: {user_message}\n\n{content}"
        resp = client.chat_completion(
            messages=[{"role": "user", "content": content}],
            system_prompt=_POLISH_PROMPT,
        )
        out = (resp.content or "").strip()
        if not out:
            return None
        # Verify price numbers if prices were in the draft
        draft_prices = _price_numbers(draft) | _price_numbers(user_message)
        if draft_prices:
            out_prices = _price_numbers(out)
            if not out_prices <= draft_prices:
                logger.warning("LLM reply rejected: introduced price numbers not present in grounded draft.")
                return None
        return out
    except Exception as e:
        logger.warning(f"LLM reply polishing skipped: {e}")
        return None


def llm_generate_chat_reply(
    client: BaseLLMProvider,
    user_message: str,
    draft_reply: str = "",
    history: Optional[List[Dict[str, str]]] = None,
) -> Optional[str]:
    """Generates a warm, natural Persian conversational response grounded in catalog facts."""
    try:
        messages = []
        if history:
            for h in history[-6:]:  # last 3 turns
                messages.append({"role": h["role"], "content": h["content"]})

        user_content = f"پیام کاربر: {user_message}"
        if draft_reply.strip():
            user_content += f"\n\nداده‌های مستند کاتالوگ و نتایج ارزیابی:\n{draft_reply}"

        messages.append({"role": "user", "content": user_content})

        resp = client.chat_completion(
            messages=messages,
            system_prompt=_CHAT_SYSTEM_PROMPT,
        )
        out = (resp.content or "").strip()
        if not out:
            return None

        # Verify price numbers if grounded draft had prices
        draft_prices = _price_numbers(draft_reply) | _price_numbers(user_message)
        if draft_prices:
            out_prices = _price_numbers(out)
            if not out_prices <= draft_prices:
                logger.warning("LLM conversational reply rejected: introduced price numbers not present in grounded data.")
                return None
        return out
    except Exception as e:
        logger.warning(f"LLM conversational reply failed ({e}); falling back.")
        return None


def deterministic_general_chat_reply(user_message: str) -> str:
    """Warm, friendly Persian responses for general chat/greetings when LLM is unavailable."""
    msg = user_message.lower()
    if any(w in msg for w in ["سلام", "درود", "صبح بخیر", "عصر بخیر", "خسته نباشید", "روز بخیر", "سلام خوبی", "سلام علیکم"]):
        return (
            "سلام! روزتون بخیر. به ترب‌چت خوش آمدید 👋\n\n"
            "من دستیار هوشمند خرید ترب هستم. چطور می‌تونم کمکتون کنم؟\n"
            "می‌تونید نام هر کالایی که مد نظرتونه رو بنویسید (مثلاً «هدفون ورزشی»، «گوشی سامسونگ تا ۲۰ میلیون»، «شارژر ۶۵ وات»)، تا بهترین قیمت‌ها و فروشگاه‌های مطمئن رو براتون پیدا کنم."
        )
    if any(w in msg for w in ["غذا", "خوراکی", "رستوران", "سوپرمارکت", "لباس", "پوشاک"]):
        return (
            "در حال حاضر در ترب‌مپ، تمرکز ما روی **کالاهای دیجیتال، موبایل، لپ‌تاپ، لوازم جانبی و قطعات الکترونیکی** فروشگاه‌های فیزیکی تهران است و اقلام غذایی، رستورانی یا سوپرمارکتی در این نسخه ارائه نمی‌شوند.\n\n"
            "اگر دنبال هرگونه کالای دیجیتال، گوشی موبایل، لپ‌تاپ، هدفون، شارژر، پاوربانک یا قطعات کامپیوتر هستید، با کمال میل راهنمایی‌تون می‌کنم! چه کالایی مد نظرتونه؟"
        )
    if any(w in msg for w in ["چی داری", "چی دارید", "چه کالاهایی", "چه محصولاتی", "چه چیزهایی", "دسته‌بندی"]):
        return (
            "در ترب‌مپ می‌توانید انواع **کالاهای دیجیتال و الکترونیک** را جستجو و از فروشگاه‌های معتبر تهران استعلام بگیرید:\n\n"
            "• **موبایل و تبلت:** انواع گوشی‌های سامسونگ، اپل (آیفون)، شیائومی و...\n"
            "• **لپ‌تاپ و قطعات کامپیوتر:** لپ‌تاپ‌های ایسوس، لنوو، پردازنده، گرافیک، مادربرد، رم و اس‌اس‌دی\n"
            "• **لوازم جانبی:** هدفون و هندزفری، پاوربانک، شارژر و آداپتور، ماوس و کیبورد، کابل\n\n"
            "دنبال چه کالایی هستید؟ نام یا بودجه مد نظرتون رو بفرمایید تا مشخصات، قیمت‌ها و نزدیک‌ترین فروشگاه‌ها رو بهتون معرفی کنم."
        )
    if any(w in msg for w in ["ممنون", "مرسی", "تشکر", "دمت گرم", "دستت درد نکنه", "سپاس"]):
        return "خواهش می‌کنم! اگر سوال یا خرید دیگری دارید، در خدمتم. 😊"
    if any(w in msg for w in ["استعلام", "چطور استعلام", "چطوری استعلام"]):
        return (
            "برای استعلام قیمت و موجودی، کافیه روی هر کالایی که در چت یا فهرست می‌بینید دکمهٔ «ترب برایم استعلام بگیرد» رو بزنید.\n\n"
            "سیستم به صورت خودکار با فروشنده تماس می‌گیره یا استعلام رو براش ارسال می‌کنه و نتیجه قطعی موجودی و قیمت ظرف چند دقیقه در بخش استعلام‌ها ثبت می‌شه."
        )
    if any(w in msg for w in ["کی هستی", "چیکار می‌تونی", "چیکار میکنی", "کمک", "راهنمایی", "درباره ترب"]):
        return (
            "من «ترب‌چت» هستم؛ دستیار هوشمند خرید شما در ترب‌مپ.\n\n"
            "کارهایی که می‌تونم براتون انجام بدم:\n"
            "• **جستجو و ارزیابی هوشمند:** پیدا کردن بهترین قیمت و فروشگاه با ارزیابی اعتماد و احتمال موجودی\n"
            "• **مقایسه تخصصی:** مقایسه مدل‌های مختلف و تحلیل نقاط قوت و ضعف هر کدام\n"
            "• **خرید حضوری روی نقشه:** یافتن فروشگاه‌های باز در نزدیکی شما در تهران\n"
            "• **استعلام مستقیم:** استعلام لحظه‌ای موجودی کالا از فروشنده پیش از مراجعه حضوری\n\n"
            "برای شروع، دنبال خرید چه چیزی هستید؟"
        )
    return (
        "خوشحال می‌شم راهنماییتون کنم! لطفاً بفرمایید دنبال چه کالایی هستید یا چه نوع مشاوره‌ای مد نظرتونه (مثلاً با چه بودجه یا ویژگی‌هایی)، تا دقیق‌ترین پیشنهادها رو براتون آماده کنم."
    )
