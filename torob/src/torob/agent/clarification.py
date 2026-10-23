"""Intelligent, Constraint-Aware Clarification Engine for Torob Shopping Agent.

Replaces rigid heuristics with an adaptive, decision-critical question policy:
1. Adapts question budget to query complexity (exact search=0, physical=1, needs=2, basket=3)
2. Eliminates candidate-count stopping fallacies; focuses on decision-critical constraints
3. Detects budget scale ambiguity ("۳۰ تومن" for accessories vs devices)
4. Handles conversational rejection and preference redirection
5. Asks exactly one high-impact question at a time with structured multiple-choice options.
"""

import logging
from typing import List, Optional, Tuple

from torob.agent.models import ShoppingIntent, ShoppingSession

logger = logging.getLogger("torob.agent.clarification")

NO_BRAND_PREFERENCE = "برایم فرقی نمی‌کند"
BRAND_OPTIONS = {
    "گوشی موبایل": ["سامسونگ", "شیائومی", "اپل (آیفون)", NO_BRAND_PREFERENCE],
    "لپ‌تاپ": ["ایسوس", "لنوو", "اچ پی", "اپل", NO_BRAND_PREFERENCE],
}


class ClarificationPolicy:
    def __init__(self, default_budget: int = 2):
        self.default_budget = default_budget

    def evaluate_clarification(
        self,
        session: ShoppingSession,
        candidate_count: int,
    ) -> Optional[Tuple[str, List[str], str]]:
        """Evaluates whether to ask a clarification question.
        
        Returns:
            Tuple of (question_text, options_list, aspect_key) or None if no question needed.
        """
        c_state = session.clarification_state
        constraints = session.constraints
        intent = session.detected_intent

        # 1. Dynamic Question Budget Allocation based on Task Complexity
        effective_budget = self.default_budget
        if intent == ShoppingIntent.EXACT_SEARCH:
            effective_budget = 0
        elif intent == ShoppingIntent.LOCAL_PHYSICAL:
            effective_budget = 1
        elif intent == ShoppingIntent.MULTI_PRODUCT:
            effective_budget = 3
        elif intent == ShoppingIntent.REFINEMENT:
            effective_budget = 1

        c_state.clarification_budget = effective_budget

        # 2. Strict Budget Cap: Never exceed allocated budget
        if c_state.questions_asked_count >= effective_budget:
            return None

        # 3. Exact Model Search: Zero unnecessary questions
        if intent == ShoppingIntent.EXACT_SEARCH:
            return None

        # 4. Critical Ambiguity: Ambiguous Budget Scale (e.g. "۳۰ تومن" for cable vs phone)
        if (
            constraints.budget_confidence == "ambiguous"
            and "budget_scale" not in c_state.resolved_aspects
            and "budget_scale" not in c_state.asked_questions
        ):
            return (
                "مبلغ وارد شده می‌تواند ۳۰ هزار تومان یا ۳۰ میلیون تومان تفسیر شود. منظور شما کدام بازه بودجه است؟",
                ["۳۰ هزار تومان (لوازم جانبی و مصرفی)", "۳۰ میلیون تومان (دستگاه دیجیتال / گوشی)"],
                "budget_scale",
            )

        # 5. Critical Constraint: Missing User Location for Urgent / Local Physical Shopping
        if (
            (intent == ShoppingIntent.LOCAL_PHYSICAL or constraints.urgency == "urgent_today")
            and constraints.user_lat is None
            and constraints.user_lon is None
            and not constraints.location_name
            and "location" not in c_state.resolved_aspects
            and "location" not in c_state.asked_questions
        ):
            return (
                "برای بررسی موجودی در لحظه و ساعت کاری فروشگاه‌های نزدیک به شما، لطفاً محله یا محدودهٔ خود در تهران (یا شهر مدنظر) را مشخص کنید:",
                [
                    "مرکز تهران (میدان انقلاب / چهارراه ولیعصر / بازار چارسو)",
                    "شمال تهران (میرداماد / پایتخت / تجریش / ونک)",
                    "غرب تهران (سعادت‌آباد / شهرک غرب / صادقیه)",
                    "شرق تهران (تهرانپارس / رسالت / هفت تیر)",
                ],
                "location",
            )

        # 6. Critical Constraint: Missing Budget for Needs-Based Shopping when candidates are unconstrained
        has_product_context = bool(
            constraints.target_category
            or constraints.preferred_specs.get("device_type")
            or constraints.target_product_title
        )
        if (
            constraints.budget_max_toman is None
            and "budget" not in c_state.resolved_aspects
            and "budget" not in c_state.asked_questions
            and has_product_context
            and intent in (ShoppingIntent.NEEDS_BASED, ShoppingIntent.BUDGET_SEARCH)
        ):
            category = constraints.target_category or ""
            if "لپ تاپ" in category or "laptop" in category.lower():
                return (
                    "برای انتخاب بهترین لپ‌تاپ متناسب با کاربری شما، لطفاً سقف بودجهٔ مد نظرتان را مشخص کنید:",
                    ["زیر ۳۵ میلیون تومان (کاربری روزمره و دانشجویی)", "۳۵ تا ۶۵ میلیون تومان (برنامه‌نویسی و اداری قوی)", "۶۵ تا ۱۰۰ میلیون تومان (گیمینگ و هوش مصنوعی)", "بالای ۱۰۰ میلیون تومان (تخصصی و ورک‌استیشن)"],
                    "budget",
                )
            else:
                return (
                    "برای انتخاب بهترین گزینه‌ها، سقف بودجهٔ مد نظرتان چقدر است؟",
                    ["زیر ۱۵ میلیون تومان", "۱۵ تا ۳۵ میلیون تومان", "۳۵ تا ۷۰ میلیون تومان", "بالای ۷۰ میلیون تومان"],
                    "budget",
                )

        # 6b. Brand preference for phones / laptops — only inside the guided quick-answer flow (budget was
        #     just asked and answered with a short option), so detailed requests get results immediately
        device_type = constraints.preferred_specs.get("device_type")
        user_msgs = [m.content for m in session.messages if m.role == "user"]
        quick_answer = bool(user_msgs) and len(user_msgs[-1].split()) <= 6
        if (
            device_type in BRAND_OPTIONS
            and "budget" in c_state.asked_questions
            and quick_answer
            and not constraints.target_brand
            and not constraints.preferred_specs.get("compared_brands")
            and "brand" not in c_state.resolved_aspects
            and "brand" not in c_state.asked_questions
            and intent in (ShoppingIntent.NEEDS_BASED, ShoppingIntent.BUDGET_SEARCH)
        ):
            return (
                "برند خاصی مد نظرتان هست؟",
                BRAND_OPTIONS[device_type],
                "brand",
            )

        # 7. Decision-Critical Workload Clarification for Laptop & Hardware Requests
        query_text = " ".join([m.content for m in session.messages if m.role == "user"]).lower()
        if (
            ("لپ" in query_text or "laptop" in query_text or constraints.preferred_specs.get("device_type") == "لپ‌تاپ")
            and ("هوش مصنوعی" in query_text or "ai" in query_text or "ماشین" in query_text or "deep learning" in query_text)
            and "ai_workload" not in c_state.resolved_aspects
            and "ai_workload" not in c_state.asked_questions
        ):
            return (
                "برای کار با هوش مصنوعی، آیا نیاز به پردازش محلی مدل‌ها (کارت گرافیک RTX با حافظه VRAM بالا) دارید یا بیشتر با API و پردازش ابری کار می‌کنید؟",
                [
                    "اجرای محلی مدل‌های زبانی/بینایی (کارت گرافیک مجزا و حداقل ۱۶ گیگ رم)",
                    "استفاده از ابزارهای ابری و برنامه‌نویسی وب (پردازنده قوی و قابلیت حمل بالا)",
                ],
                "ai_workload",
            )

        # 8. Custom PC Build Basket: Primary Workload (Gaming vs Editing/CAD vs Deep Learning)
        if (
            intent == ShoppingIntent.MULTI_PRODUCT
            and "pc_usecase" not in c_state.resolved_aspects
            and "pc_usecase" not in c_state.asked_questions
            and len(constraints.multi_product_basket) > 1
        ):
            return (
                "هدف اصلی این سیستم اسمبل‌شده چیست تا تناسب پردازنده و کارت گرافیک بهینه‌سازی شود؟",
                ["گیمینگ و بازی‌های روز (اولویت کارت گرافیک)", "تدوین، انیمیشن و رندرینگ ۳بعدی (اولویت رم و CPU)", "برنامه‌نویسی و استفاده اداری/مهندسی عمومی"],
                "pc_usecase",
            )

        return None
