"""AI Shopping Agent Orchestrator for Torob Intelligence Engine.

Coordinates multi-turn dialogue, session persistence, constraint extraction,
intelligent clarification policies, deterministic recommendation ranking,
and grounded Persian response generation.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from torob.agent.clarification import ClarificationPolicy
from torob.agent.llm import (
    DeterministicFallbackParser,
    LLMResponse,
    LLMToolOrchestrator,
    get_llm_client,
    llm_extract_constraints,
    llm_polish_enabled,
    llm_polish_reply,
)
from torob.agent.models import (
    ChatMessage,
    ProposedAction,
    RecommendationResult,
    ShoppingConstraints,
    ShoppingIntent,
    ShoppingSession,
)
from torob.agent.recommender import ShoppingRecommender
from torob.agent.session_repository import ShoppingSessionRepository
from torob.agent.tools import AgentToolRegistry
from torob.domain.plans import MultiStoreBasketPlan
from torob.storage.repository_ledger import LedgerRepository
from torob.intelligence.plan_lifecycle import ShoppingPlanLifecycleManager

logger = logging.getLogger("torob.agent.orchestrator")


class ShoppingAgentOrchestrator:
    def __init__(
        self,
        session_repo: Optional[ShoppingSessionRepository] = None,
        tool_registry: Optional[AgentToolRegistry] = None,
        recommender: Optional[ShoppingRecommender] = None,
        clarification_policy: Optional[ClarificationPolicy] = None,
        lifecycle_manager: Optional[ShoppingPlanLifecycleManager] = None,
        ledger_repo: Optional[Any] = None,
    ):
        self.session_repo = session_repo or ShoppingSessionRepository()
        self.tool_registry = tool_registry or AgentToolRegistry()
        self.recommender = recommender or ShoppingRecommender()
        self.clarification_policy = clarification_policy or ClarificationPolicy()
        self.lifecycle_manager = lifecycle_manager or ShoppingPlanLifecycleManager()
        self.ledger_repo = ledger_repo or LedgerRepository()
        self.llm_client = get_llm_client()

    def get_or_create_session(
        self, session_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> ShoppingSession:
        if session_id:
            existing = self.session_repo.get_session(session_id)
            if existing:
                return existing

        new_session = ShoppingSession(user_id=user_id)
        if session_id:
            new_session.session_id = session_id
        self.session_repo.save_session(new_session)
        return new_session

    def process_message(
        self,
        session_id: str,
        user_message: str,
        user_id: Optional[str] = None,
    ) -> Tuple[ShoppingSession, str]:
        """Main multi-turn agent entry point."""
        session = self.get_or_create_session(session_id=session_id, user_id=user_id)

        # 1. Record incoming user message
        session.messages.append(ChatMessage(role="user", content=user_message))

        # 2. Extract intent and update constraints (preserving prior preferences)
        # (parse_message shallow-copies constraints, so read the previous topic before parsing)
        prev_device_type = session.constraints.preferred_specs.get("device_type")
        detected_intent, extracted_constraints = DeterministicFallbackParser.parse_message(
            user_message, current_constraints=session.constraints
        )

        # 2b. Optional LLM assist: fill only what the deterministic parser missed (never overrides it)
        if self.llm_client is not None:
            self._apply_llm_constraints(user_message, extracted_constraints)

        # Handle rejection of previous recommendations
        if extracted_constraints.preferred_specs.get("action") == "reject_specific_index":
            idx = extracted_constraints.preferred_specs.get("reject_index", 0)
            if session.latest_recommendations and session.latest_recommendations.top_recommendations:
                if 0 <= idx < len(session.latest_recommendations.top_recommendations):
                    rec = session.latest_recommendations.top_recommendations[idx]
                    if rec.product_id not in session.constraints.rejected_product_ids:
                        session.constraints.rejected_product_ids.append(rec.product_id)
                        try:
                            self.ledger_repo.record_recommendation_outcome(
                                outcome_id=f"outc_{uuid.uuid4().hex[:12]}",
                                decision_id=session.session_id,
                                session_id=session.session_id,
                                outcome_type="recommendation_rejected",
                                product_id=rec.product_id,
                                payload={"rejected_index": idx, "reason": "user_explicit_rejection"},
                            )
                        except Exception:
                            pass
            extracted_constraints.preferred_specs.pop("action", None)
            extracted_constraints.preferred_specs.pop("reject_index", None)
        elif extracted_constraints.preferred_specs.get("action") == "reject_previous":
            if session.latest_recommendations and session.latest_recommendations.top_recommendations:
                for rec in session.latest_recommendations.top_recommendations:
                    if rec.product_id not in session.constraints.rejected_product_ids:
                        session.constraints.rejected_product_ids.append(rec.product_id)
                        try:
                            self.ledger_repo.record_recommendation_outcome(
                                outcome_id=f"outc_{uuid.uuid4().hex[:12]}",
                                decision_id=session.session_id,
                                session_id=session.session_id,
                                outcome_type="recommendation_rejected",
                                product_id=rec.product_id,
                                payload={"reason": "user_rejected_all_previous"},
                            )
                        except Exception:
                            pass
            extracted_constraints.preferred_specs.pop("action", None)

        session.detected_intent = detected_intent
        _, stated_now = DeterministicFallbackParser.parse_message(user_message)
        self._reset_on_topic_change(session, detected_intent, extracted_constraints, stated_now, prev_device_type)
        self._merge_constraints(session.constraints, extracted_constraints)

        # Handle Adaptive Replanning
        if detected_intent == ShoppingIntent.ADAPTIVE_REPLAN:
            unavailable_item = extracted_constraints.preferred_specs.get("unavailable_item") or "SSD"
            active_plan_dict = None
            if session.latest_recommendations and session.latest_recommendations.basket_plan:
                active_plan_dict = session.latest_recommendations.basket_plan.get("primary_plan") or session.latest_recommendations.basket_plan

            if active_plan_dict:
                active_plan = MultiStoreBasketPlan.model_validate(active_plan_dict)
                self.lifecycle_manager.register_plan(active_plan)
                res = self.lifecycle_manager.adaptive_replan_after_stock_rejection(
                    plan_id=active_plan.plan_id,
                    unavailable_item=unavailable_item,
                    max_budget_toman=session.constraints.budget_max_toman,
                    max_stops=session.constraints.max_stops,
                )
                if res.is_recovered and res.revised_plan:
                    rec_result = RecommendationResult(
                        intent=ShoppingIntent.ADAPTIVE_REPLAN,
                        total_candidates_found=len(res.revised_plan.stores),
                        top_recommendations=[],
                        trade_off_summary=res.persian_explanation,
                        hard_constraints_satisfied=True,
                        basket_plan=res.revised_plan.model_dump(),
                        adapted_plan=res.revised_plan.model_dump(),
                    )
                else:
                    rec_result = RecommendationResult(
                        intent=ShoppingIntent.ADAPTIVE_REPLAN,
                        total_candidates_found=0,
                        top_recommendations=[],
                        trade_off_summary=res.persian_explanation,
                        hard_constraints_satisfied=False,
                        violated_constraints=[res.adaptation_reason],
                    )
                session.latest_recommendations = rec_result
                reply = res.persian_explanation
                session.messages.append(ChatMessage(role="assistant", content=reply))
                self.session_repo.save_session(session)
                return session, reply

        # Mark aspects as resolved based on user's statement
        if any(w in user_message for w in ["بودجه", "تومان", "تومن", "میلیون"]):
            session.clarification_state.resolved_aspects.append("budget")
        if any(w in user_message for w in ["فرقی نمی", "فرقی نداره", "هر برندی", "برند مهم نیست"]):
            session.clarification_state.resolved_aspects.append("brand")
        if any(w in user_message for w in ["محلی", "ابری", "کلود"]):
            session.clarification_state.resolved_aspects.append("ai_workload")
        if any(w in user_message for w in ["انقلاب", "ولیعصر", "سعادت آباد", "تهران", "شهرک غرب", "علاءالدین", "چارسو", "پایتخت", "میرداماد", "ونک", "رسالت", "نارمک"]):
            session.clarification_state.resolved_aspects.append("location")

        if session.clarification_state.active_clarification_question:
            session.clarification_state.active_clarification_question = None
            session.clarification_state.clarification_options = []

        # 3. Check provisional candidate count
        provisional_recs = self.recommender.recommend(session.constraints, intent=session.detected_intent, limit=3)
        candidate_count = provisional_recs.total_candidates_found

        # 4. Intelligent Clarification Check
        clarification_item = self.clarification_policy.evaluate_clarification(
            session=session,
            candidate_count=candidate_count,
        )

        if clarification_item is not None:
            question_text, options, aspect_key = clarification_item
            session.clarification_state.questions_asked_count += 1
            session.clarification_state.asked_questions.append(aspect_key)
            session.clarification_state.active_clarification_question = question_text
            session.clarification_state.clarification_options = options

            # Response is the targeted clarification
            options_formatted = "\n".join([f"• {opt}" for opt in options]) if options else ""
            reply = f"{question_text}\n\n{options_formatted}".strip()

            session.messages.append(ChatMessage(role="assistant", content=reply))
            self.session_repo.save_session(session)
            return session, reply

        # 5. Recommendation Execution (no clarification needed or budget exhausted)
        rec_result = self.recommender.recommend(session.constraints, intent=session.detected_intent, limit=5)
        session.latest_recommendations = rec_result

        # Record recommendation decision & shown outcome in ledger
        try:
            candidate_ids = [r.product_id for r in rec_result.top_recommendations]
            decision_id = f"rec_{uuid.uuid4().hex[:12]}"
            self.ledger_repo.record_recommendation_decision(
                decision_id=decision_id,
                session_id=session.session_id,
                objective=session.detected_intent.value if session.detected_intent else "browse",
                constraints=session.constraints.model_dump(),
                candidate_product_ids=candidate_ids,
                selected_product_ids=candidate_ids[:3],
                ranking_policy_version="mcda_grounded_v2",
                warnings=rec_result.violated_constraints,
            )
            for pid in candidate_ids[:3]:
                self.ledger_repo.record_recommendation_outcome(
                    outcome_id=f"outc_{uuid.uuid4().hex[:12]}",
                    decision_id=decision_id,
                    session_id=session.session_id,
                    outcome_type="recommendation_shown",
                    product_id=pid,
                )
        except Exception as e:
            logger.warning(f"Could not record recommendation decision: {e}")

        # 6. Formulate grounded conversational reply
        reply = self._formulate_agent_reply(session, rec_result)
        if self.llm_client is not None and llm_polish_enabled() and rec_result.top_recommendations:
            reply = llm_polish_reply(self.llm_client, reply) or reply
        session.messages.append(ChatMessage(role="assistant", content=reply))

        # Check proposed actions
        session.proposed_actions = []
        if rec_result.recommended_inquiry:
            session.proposed_actions.append(
                ProposedAction(
                    action_type="confirm_inquiry",
                    description=rec_result.recommended_inquiry["reason"],
                    payload=rec_result.recommended_inquiry,
                )
            )

        self.session_repo.save_session(session)
        return session, reply

    def _reset_on_topic_change(
        self,
        session: ShoppingSession,
        intent: ShoppingIntent,
        new: ShoppingConstraints,
        stated: ShoppingConstraints,
        old_dev: Optional[str],
    ) -> None:
        """A new product type or a comparison starts a fresh topic: drop the previous topic's budget/brand
        and clarification history so they don't silently filter the new request.
        `new` carries over session context; `stated` holds only what this message itself says."""
        base = session.constraints
        new_dev = stated.preferred_specs.get("device_type")
        switched = bool(new_dev and old_dev and new_dev != old_dev)
        if not (switched or intent == ShoppingIntent.PRODUCT_COMPARISON):
            return
        for c in (base, new):
            if stated.budget_max_toman is None:
                c.budget_max_toman = None
            if stated.budget_min_toman is None:
                c.budget_min_toman = None
            if not stated.target_brand:
                c.target_brand = None
        base.preferred_specs.pop("compared_brands", None)
        if switched:
            session.latest_recommendations = None
            base.target_category = None
            base.target_product_title = None
            new.target_category = stated.target_category
            new.target_product_title = stated.target_product_title
            session.clarification_state.questions_asked_count = 0
            session.clarification_state.asked_questions = []
            session.clarification_state.resolved_aspects = []

    def _apply_llm_constraints(self, user_message: str, extracted: ShoppingConstraints) -> None:
        data = llm_extract_constraints(self.llm_client, user_message)
        if not data:
            return
        product = data.get("product")
        if isinstance(product, str) and product.strip() and not extracted.preferred_specs.get("device_type") \
                and not extracted.target_category and not extracted.target_product_title:
            extracted.preferred_specs["device_type"] = product.strip()[:40]
        brand = data.get("brand")
        if isinstance(brand, str) and brand.strip() and not extracted.target_brand:
            extracted.target_brand = brand.strip()[:40]
        for key in ("budget_min_toman", "budget_max_toman"):
            val = data.get(key)
            if isinstance(val, (int, float)) and 10_000 <= val <= 1e11 and getattr(extracted, key) is None:
                setattr(extracted, key, float(val))
                extracted.budget_confidence = extracted.budget_confidence or "confident"

    def _merge_constraints(
        self, base: ShoppingConstraints, new: ShoppingConstraints
    ) -> None:
        """Merges updated user constraints while preserving established context."""
        if new.budget_max_toman is not None:
            base.budget_max_toman = new.budget_max_toman
        if new.budget_min_toman is not None:
            base.budget_min_toman = new.budget_min_toman
        if new.budget_confidence:
            base.budget_confidence = new.budget_confidence
        if new.target_product_title:
            base.target_product_title = new.target_product_title
        if new.target_category:
            base.target_category = new.target_category
        if new.target_brand:
            base.target_brand = new.target_brand
        if new.excluded_brands:
            base.excluded_brands = list(dict.fromkeys(base.excluded_brands + new.excluded_brands))
        if new.rejected_product_ids:
            base.rejected_product_ids = list(dict.fromkeys(base.rejected_product_ids + new.rejected_product_ids))
        if new.min_shop_reliability is not None:
            base.min_shop_reliability = new.min_shop_reliability
        if new.battery_preference:
            base.battery_preference = new.battery_preference
        if new.newer_models_only:
            base.newer_models_only = new.newer_models_only
        if new.color:
            base.color = new.color
        if new.storage:
            base.storage = new.storage
        if new.ram:
            base.ram = new.ram
        if new.condition:
            base.condition = new.condition
        if new.user_lat is not None and new.user_lon is not None:
            base.user_lat = new.user_lat
            base.user_lon = new.user_lon
        if new.location_name:
            base.location_name = new.location_name
        if new.origin_name:
            base.origin_name = new.origin_name
        if new.origin_lat is not None and new.origin_lon is not None:
            base.origin_lat = new.origin_lat
            base.origin_lon = new.origin_lon
        if new.destination_name:
            base.destination_name = new.destination_name
        if new.destination_lat is not None and new.destination_lon is not None:
            base.destination_lat = new.destination_lat
            base.destination_lon = new.destination_lon
        if new.max_detour_minutes is not None:
            base.max_detour_minutes = new.max_detour_minutes
        if new.max_stops is not None:
            base.max_stops = new.max_stops
        if new.deadline_iso:
            base.deadline_iso = new.deadline_iso
        if new.optimization_priority:
            base.optimization_priority = new.optimization_priority
        if new.basket_queries:
            base.basket_queries = new.basket_queries
        base.require_single_store = new.require_single_store
        if new.urgency:
            base.urgency = new.urgency
        if new.preferred_specs:
            base.preferred_specs.update(new.preferred_specs)

    def _formulate_agent_reply(
        self, session: ShoppingSession, rec_result: RecommendationResult
    ) -> str:
        """Formulates clear, grounded Persian explanation of the recommendations."""
        lines = []

        # 0. Adapted / Recovered Shopping Plan
        if rec_result.adapted_plan:
            ap = rec_result.adapted_plan
            lines.append("🔄 **برنامه بازنگری‌شده و بهبودیافته خرید:**")
            if ap.get("trade_off_explanation"):
                lines.append(f"• {ap.get('trade_off_explanation')}")
            cost_str = f"{ap.get('total_product_cost_toman', 0):,.0f} تومان" if ap.get('total_product_cost_toman') else "نیازمند استعلام قیمت"
            lines.append(f"• تعداد توقف: {ap.get('total_stops', 1)} فروشگاه | مجموع هزینه اقلام: **{cost_str}**")
            for st in ap.get("stores", []):
                lines.append(f"   • فروشگاه {st.get('shop_name')} ({st.get('shop_address') or 'تهران'}):")
                for m in st.get("matched_items", []):
                    m_price = f"{m.get('price_toman'):,.0f} تومان" if m.get('price_toman') else "قیمت استعلامی"
                    stock_tag = "تاییدشده فروشنده" if m.get("stock_evidence") == "seller_confirmed" else "موجود در کاتالوگ"
                    lines.append(f"     - {m.get('matched_product_title', '')[:40]}: {m_price} [{stock_tag}]")
            lines.append("")

        # 1. On-Route Purchase Plan
        elif rec_result.on_route_plan:
            orp = rec_result.on_route_plan
            lines.append("🚗 **برنامه خرید در مسیر سفر:**")
            lines.append(f"• زمان سفر مستقیم بدون توقف: {orp.get('baseline_duration_minutes', 0):.0f} دقیقه ({orp.get('baseline_distance_km', 0):.1f} کیلومتر).")
            if orp.get("recommended_stops"):
                for idx, stop in enumerate(orp["recommended_stops"][:3], start=1):
                    tag = f" 🌟 [{stop.get('trade_off_label')}]" if stop.get('trade_off_label') else ""
                    lines.append(f"{idx}. فروشگاه «{stop.get('shop_name')}»{tag}:")
                    lines.append(f"   • کالا: {stop.get('product_title')} | قیمت: {stop.get('price_toman', 0):,.0f} تومان")
                    lines.append(f"   • انحراف زمانی از مسیر: **{stop.get('detour_minutes', 0):.0f} دقیقه** (کل زمان سفر با توقف: {stop.get('trip_via_shop_minutes', 0):.0f} دقیقه)")
                    if stop.get("warnings"):
                        lines.append(f"   ⚠️ {stop['warnings'][0]}")
            elif orp.get("trade_off_summary"):
                lines.append(f"• {orp.get('trade_off_summary')}")
            lines.append("")

        # 2. Basket Optimization Plan
        elif rec_result.basket_plan:
            bp = rec_result.basket_plan.get("primary_plan") or rec_result.basket_plan
            lines.append(f"🛒 **طرح پیشنهادی سبد خرید ({bp.get('strategy_label_persian', '')}):**")
            cost_str = f"{bp.get('total_product_cost_toman', 0):,.0f} تومان" if bp.get('total_product_cost_toman') else "نیازمند استعلام قیمت"
            lines.append(f"• تعداد توقف: {bp.get('total_stops', 1)} فروشگاه | مجموع هزینه اقلام: **{cost_str}**")
            for st in bp.get("stores", []):
                lines.append(f"   • فروشگاه {st.get('shop_name')} ({st.get('shop_address') or 'تهران'}):")
                for m in st.get("matched_items", []):
                    m_price = f"{m.get('price_toman'):,.0f} تومان" if m.get('price_toman') else "قیمت استعلامی"
                    stock_tag = "تاییدشده فروشنده" if m.get("stock_evidence") == "seller_confirmed" else "موجود در کاتالوگ"
                    lines.append(f"     - {m.get('matched_product_title', '')[:40]}: {m_price} [{stock_tag}]")
            if bp.get("trade_off_explanation"):
                lines.append(f"• {bp.get('trade_off_explanation')}")
            lines.append("")

        # 3. Commercial Hub Clusters
        elif rec_result.shop_clusters:
            lines.append("🏬 **خوشه‌های تجاری همجوار پیشنهادی (فاصله پیاده‌روی اندک):**")
            for cl in rec_result.shop_clusters[:2]:
                lines.append(f"• **{cl.get('cluster_name')}**: {cl.get('summary', '')}")
                if cl.get("inter_shop_walk_minutes"):
                    lines.append(f"  زمان پیاده‌روی بین مغازه‌ها: حدود {cl.get('inter_shop_walk_minutes', 0):.0f} دقیقه")
            lines.append("")

        # 4. Personalized Comparison
        elif rec_result.personalized_comparison:
            pc = rec_result.personalized_comparison
            lines.append("⚖️ **تحلیل مقایسه‌ای گزینه‌ها بر اساس اولویت‌های شما:**")
            if pc.get("top_choice_summary"):
                lines.append(f"• پیشنهاد برتر: {pc.get('top_choice_summary')}")
            if pc.get("trade_off_matrix"):
                lines.append(f"• تحلیل مقایسه‌ای: {pc.get('trade_off_matrix')}")
            if pc.get("unmet_or_uncertain_specs"):
                lines.append(f"⚠️ مشخصات نامشخص: {', '.join(pc.get('unmet_or_uncertain_specs')[:2])}")
            lines.append("")

        # 5. Standard Product Search Recommendations
        elif rec_result.top_recommendations:
            lines.append("نتایج جستجو و ارزیابی شواهد در ترب برای شما:")
            lines.append("")
            for idx, rec in enumerate(rec_result.top_recommendations[:3], start=1):
                tag = ""
                if rec.trade_off_label == "best_overall":
                    tag = " 🌟 [بهترین انتخاب جامع]"
                elif rec.trade_off_label == "budget_pick":
                    tag = " 💰 [گزینه اقتصادی‌تر]"
                elif rec.trade_off_label == "verified_confidence":
                    tag = " 🛡️ [بالاترین اتکای فروشگاه]"

                lines.append(f"{idx}. **{rec.product_title}**{tag}")
                loc_str = rec.shop_address or 'تهران'
                lines.append(f"   • فروشگاه: {rec.shop_name} ({loc_str})")
                lines.append(f"   • قیمت: **{rec.price_toman:,.0f} تومان**")
                lines.append(f"   • نمره اعتماد فروشگاه: {int(rec.shop_reliability_score*100)}٪ | شایستگی: {int(rec.suitability_score*100)}٪")

                if rec.pros:
                    lines.append(f"   • مزایا: {', '.join(rec.pros[:2])}")
                if rec.uncertainty_warnings:
                    lines.append(f"   ⚠️ نکته احتیاطی: {rec.uncertainty_warnings[0]}")
                lines.append("")
        else:
            return rec_result.trade_off_summary or "متأسفانه با مشخصات درخواستی کالایی یافت نشد."

        if rec_result.compatibility_report:
            rep = rec_result.compatibility_report
            if rep.get("is_compatible"):
                lines.append("🔧 **گزارش سازگاری سخت‌افزار:** تمامی قطعات از نظر سوکت و نوع حافظه سازگار هستند.")
            else:
                lines.append("⚠️ **اخطار عدم سازگاری قطعات:**")
                for iss in rep.get("issues", []):
                    lines.append(f"   • {iss.get('message')}")
            if rep.get("missing_specifications"):
                lines.append("   ❓ توجه: برخی مشخصات در کاتالوگ فروشنده ناقص بود و به طور قطعی بررسی نشد.")
            lines.append("")

        if rec_result.recommended_inquiry:
            lines.append("")
            lines.append(f"💡 **پیشنهاد هوشمند:** {rec_result.recommended_inquiry['reason']}")

        return "\n".join(lines).strip()
