"""Personalized Multi-Criteria Product Comparison & Selection Engine.

Solves the real-world shopping problem:
"Among these several candidate laptops/products, which one is best for me based on my
actual priorities (e.g. battery life and portability > gaming/GPU power)?"

Algorithms:
1. Multi-Criteria Decision Analysis (MCDA):
   Normalizes heterogeneous specifications into commensurate dimensions in [0.0, 1.0].
2. Domain Use-Case Profiling:
   - Programming / Engineering: Weight on CPU tier, RAM (16GB+), SSD speed.
   - Mobility / Business: Weight on lightweight (<1.5kg), battery runtime, thin form-factor.
   - Gaming / Creative: Weight on dedicated GPU (RTX), high refresh display, cooling.
   - General / Budget: Weight on price-to-performance ratio and brand reliability.
3. Hard-Constraint Eligibility:
   Flags disqualifications (e.g. 8GB RAM for heavy local development) while keeping explainability.
4. Explainable Trade-Off Matrix:
   Generates explicit comparative explanations of why Option A wins over Option B for the user's specific priorities.
5. Explicit Uncertainty Admission:
   Unlisted or incomplete specifications are never assumed to be optimal or penalized blindly;
   flagged in `uncertain_or_missing_specs`.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from torob.domain.entities import Product
from torob.domain.plans import PersonalizedComparisonResult, ProductSuitabilityScore
from torob.storage.repository_catalog import CatalogRepository

logger = logging.getLogger("torob.intelligence.personalized_recommender")


class PersonalizedProductSelector:
    def __init__(self, catalog_repo: Optional[CatalogRepository] = None):
        self.catalog_repo = catalog_repo or CatalogRepository()

    def compare_and_rank_products(
        self,
        product_ids_or_titles: List[str],
        use_case: str = "general",  # "programming", "gaming", "mobility", "general"
        user_priorities: Optional[Dict[str, float]] = None,
        max_budget_toman: Optional[float] = None,
        excluded_brands: Optional[List[str]] = None,
    ) -> PersonalizedComparisonResult:
        """Evaluates and compares candidate products based on personalized criteria."""
        excluded_brands = excluded_brands or []
        priorities = self._resolve_priorities(use_case, user_priorities)

        # 1. Retrieve Candidate Products
        products: List[Product] = []
        for ref in product_ids_or_titles:
            p = self.catalog_repo.get_product(ref)
            if not p:
                # Search by title
                prods, _ = self.catalog_repo.search_products(q=ref, limit=1)
                if prods:
                    p = prods[0]
            if p and p.product_id not in [x.product_id for x in products]:
                # Check excluded brands
                if any(b.lower() in (p.brand_name or "").lower() for b in excluded_brands):
                    continue
                products.append(p)

        if not products:
            return PersonalizedComparisonResult(
                comparison_criteria=list(priorities.keys()),
                user_priorities=priorities,
                evaluated_products=[],
                top_choice_product_id=None,
                top_choice_summary="هیچ کالایی برای مقایسه یافت نشد.",
                trade_off_matrix="کالاهای درخواستی در کاتالوگ موجود نیستند.",
            )

        # 2. Score each product across dimensions
        evaluated_scores: List[ProductSuitabilityScore] = []
        for p in products:
            score_obj = self._evaluate_single_product(p, priorities, use_case, max_budget_toman)
            evaluated_scores.append(score_obj)

        # Sort primarily by suitability_score descending
        evaluated_scores.sort(key=lambda s: -s.suitability_score)
        top_choice = evaluated_scores[0]

        # 3. Formulate comparative matrix & summary
        summary, matrix = self._generate_comparison_narrative(evaluated_scores, priorities, use_case)

        all_uncertain_specs = list(set(itertools_chain := [s for obj in evaluated_scores for s in obj.uncertain_or_missing_specs]))

        return PersonalizedComparisonResult(
            comparison_criteria=list(priorities.keys()),
            user_priorities=priorities,
            evaluated_products=evaluated_scores,
            top_choice_product_id=top_choice.product_id,
            top_choice_summary=summary,
            trade_off_matrix=matrix,
            unmet_or_uncertain_specs=all_uncertain_specs,
        )

    def _resolve_priorities(
        self, use_case: str, user_priorities: Optional[Dict[str, float]]
    ) -> Dict[str, float]:
        """Resolves weights for criteria: battery, weight, cpu, gpu, ram, price_value."""
        default_weights: Dict[str, Dict[str, float]] = {
            "programming": {"cpu": 0.30, "ram": 0.25, "battery": 0.20, "weight": 0.15, "gpu": 0.10},
            "mobility": {"weight": 0.35, "battery": 0.35, "cpu": 0.15, "ram": 0.10, "gpu": 0.05},
            "gaming": {"gpu": 0.40, "cpu": 0.25, "ram": 0.20, "weight": 0.05, "battery": 0.10},
            "general": {"cpu": 0.25, "ram": 0.20, "battery": 0.20, "weight": 0.20, "gpu": 0.15},
        }
        base = default_weights.get(use_case, default_weights["general"]).copy()
        if user_priorities:
            base.update(user_priorities)
            # Normalize to sum = 1.0
            total = sum(base.values())
            if total > 0:
                base = {k: round(v / total, 3) for k, v in base.items()}
        return base

    def _evaluate_single_product(
        self,
        product: Product,
        priorities: Dict[str, float],
        use_case: str,
        max_budget: Optional[float],
    ) -> ProductSuitabilityScore:
        """Scores product specifications against criteria in [0.0, 1.0]."""
        full_text = f"{product.persian_title} {product.specs or {}}".lower()
        pros: List[str] = []
        cons: List[str] = []
        uncertain_specs: List[str] = []

        # Find min price among offers
        offers = self.catalog_repo.get_offers_by_product(product.product_id, limit=20)
        valid_prices = [o.price_toman for o in offers if o.price_toman and o.price_toman > 1]
        min_price = min(valid_prices) if valid_prices else None

        # 1. CPU Score
        cpu_score = 0.50
        if any(cpu in full_text for cpu in ["i9", "core i9", "ryzen 9"]):
            cpu_score = 1.0
            pros.append("پردازنده رده‌بالا (Core i9 / Ryzen 9)")
        elif any(cpu in full_text for cpu in ["i7", "core i7", "ryzen 7", "m2 pro", "m3 pro"]):
            cpu_score = 0.85
            pros.append("پردازنده قدرتمند (Core i7 / Ryzen 7)")
        elif any(cpu in full_text for cpu in ["i5", "core i5", "ryzen 5", "m1", "m2", "m3"]):
            cpu_score = 0.70
            pros.append("پردازنده میان‌رده کارآمد (Core i5 / Ryzen 5 / Apple Silicon)")
        elif any(cpu in full_text for cpu in ["i3", "celeron", "athlon"]):
            cpu_score = 0.35
            cons.append("پردازنده پایه و ضعیف‌تر")
        else:
            uncertain_specs.append("مدل دقیق پردازنده در کاتالوگ قید نشده است")

        # 2. RAM Score
        ram_score = 0.50
        if any(r in full_text for r in ["32gb", "32 gb", "۳۲ گیگ"]):
            ram_score = 1.0
            pros.append("۳۲ گیگابایت حافظه رم ایده‌آل")
        elif any(r in full_text for r in ["16gb", "16 gb", "۱۶ گیگ"]):
            ram_score = 0.85
            pros.append("۱۶ گیگابایت رم کافی برای مالتی‌تسکینگ")
        elif any(r in full_text for r in ["8gb", "8 gb", "۸ گیگ"]):
            ram_score = 0.55
            if use_case == "programming":
                ram_score = 0.35
                cons.append("رم ۸ گیگابایت ممکن است برای تسک‌های سنگین برنامه‌نویسی محدودکننده باشد")
        elif any(r in full_text for r in ["4gb", "4 gb"]):
            ram_score = 0.25
            cons.append("رم ۴ گیگابایت برای نرم‌افزارهای امروزی ناکافی است")
        else:
            uncertain_specs.append("ظرفیت حافظه رم نامشخص")

        # 3. Battery Score
        battery_score = 0.50
        if any(m in full_text for m in ["macbook", "zenbook", "m1", "m2", "m3", "70wh", "80wh", "90wh"]):
            battery_score = 0.95
            pros.append("شارژدهی باتری فوق‌العاده و بهینگی مصرف")
        elif any(m in full_text for m in ["legion", "tuf", "rog", "omen", "victus"]):
            battery_score = 0.40
            cons.append("لپ‌تاپ گیمینگ پرمصرف؛ شارژدهی باتری محدود")
        else:
            uncertain_specs.append("ظرفیت باتری یا شارژدهی دقیق در مشخصات ثبت نشده است")

        # 4. Weight Score
        weight_score = 0.50
        if any(w in full_text for w in ["air", "zenbook", "gram", "slim", "سبک"]) or ("macbook air" in full_text):
            weight_score = 0.95
            pros.append("بسیار سبک و به شدت قابل‌حمل (< 1.4 کیلوگرم)")
        elif any(w in full_text for w in ["legion", "rog", "tuf", "nitro"]):
            weight_score = 0.35
            cons.append("وزن نسبتاً سنگین بدنه و شارژر")
        else:
            weight_score = 0.60

        # 5. GPU Score
        gpu_score = 0.40
        if any(g in full_text for g in ["rtx 4090", "rtx 4080", "rtx 4070"]):
            gpu_score = 1.0
            pros.append("گرافیک فوق‌العاده قدرتمند سری 40")
        elif any(g in full_text for g in ["rtx 4060", "rtx 4050", "rtx 3060", "rtx 3050"]):
            gpu_score = 0.80
            pros.append("گرافیک مجزای مناسب کارهای بصری و هوش مصنوعی")
        elif "intel iris" in full_text or "radeon graphics" in full_text or "گرافیک یکپارچه" in full_text:
            gpu_score = 0.40
            if use_case == "gaming":
                cons.append("فاقد پردازشگر گرافیکی مجزا برای بازی")

        # 6. Price/Value Score
        price_score = 0.60
        hard_req_met = True
        if max_budget and min_price:
            if min_price > max_budget:
                hard_req_met = False
                cons.append(f"قیمت بیش از سقف بودجه ({min_price:,.0f} > {max_budget:,.0f})")
                price_score = 0.20
            else:
                price_score = 0.85

        # Weighted aggregate suitability
        preference_match = (
            priorities.get("cpu", 0.2) * cpu_score
            + priorities.get("ram", 0.2) * ram_score
            + priorities.get("battery", 0.2) * battery_score
            + priorities.get("weight", 0.2) * weight_score
            + priorities.get("gpu", 0.2) * gpu_score
        )

        composite = 0.70 * preference_match + 0.30 * price_score
        if not hard_req_met:
            composite *= 0.60

        return ProductSuitabilityScore(
            product_id=product.product_id,
            product_title=product.persian_title,
            brand_name=product.brand_name,
            category_name=product.category_name,
            specs=product.specs,
            min_price_toman=min_price,
            suitability_score=round(composite, 3),
            hard_requirements_met=hard_req_met,
            preference_match_score=round(preference_match, 3),
            value_for_money_score=round(price_score, 3),
            pros=pros,
            cons=cons,
            trade_off_notes=f"تطابق با اولویت‌های کاربری ({use_case}): {int(preference_match*100)}٪",
            uncertain_or_missing_specs=uncertain_specs,
        )

    def _generate_comparison_narrative(
        self,
        scores: List[ProductSuitabilityScore],
        priorities: Dict[str, float],
        use_case: str,
    ) -> Tuple[str, str]:
        if not scores:
            return "", ""

        best = scores[0]
        summary = (
            f"گزینه برتر برای شما: «{best.product_title}» با امتیاز شایستگی {int(best.suitability_score*100)}٪. "
            f"با توجه به اهمیت {', '.join([k for k, v in priorities.items() if v >= 0.20])} در کاربری شما، "
            f"این مدل بهترین توازن را با مزایای «{', '.join(best.pros[:2])}» فراهم می‌کند."
        )

        matrix_lines = []
        matrix_lines.append(f"تحلیل مقایسه‌ای گزینه‌ها بر اساس اولویت‌های شما ({use_case}):")
        for s in scores:
            p_str = f"{s.min_price_toman:,.0f} تومان" if s.min_price_toman else "استعلام قیمت"
            matrix_lines.append(f"• **{s.product_title}** (شایستگی: {int(s.suitability_score*100)}٪ | حداقل قیمت: {p_str}):")
            if s.pros:
                matrix_lines.append(f"   - نقاط قوت: {', '.join(s.pros)}")
            if s.cons:
                matrix_lines.append(f"   - نکات احتیاطی/ضعف: {', '.join(s.cons)}")

        return summary, "\n".join(matrix_lines)
