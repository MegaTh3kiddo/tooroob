"""Deterministic Offline Verification Policy Replay & Simulation Harness.

Compares candidate verification policies (Fixed TTL, Category TTL, Risk-Based,
Adaptive VoI, Budget-Constrained VoI) across deterministic synthetic fixtures.
Measures seller interruption burden, useful confirmation rate, detection delay,
and simulated customer-facing mismatches without claiming real-world validation.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("torob.intelligence.policy_simulator")


@dataclass
class PolicyEvaluationMetrics:
    policy_name: str
    total_inquiries: int
    seller_burden_score: float
    useful_confirmations_count: int
    simulated_missed_mismatches: int
    mean_detection_delay_hours: float
    efficiency_useful_per_100_inquiries: float
    budget_exhaustion_events: int = 0
    is_simulation: bool = True


@dataclass
class SimulationFixtureEvent:
    event_time_hours: float  # Elapsed hours in simulation
    offer_id: str
    shop_id: str
    category: str
    actual_price: float
    actual_in_stock: bool
    is_price_changed: bool = False
    is_stock_depleted: bool = False
    customer_visit_intent: bool = False
    customer_detour_min: float = 0.0


class VerificationPolicySimulator:
    def __init__(self, simulation_horizon_hours: float = 336.0):  # 14 days
        self.horizon_hours = simulation_horizon_hours

    def generate_synthetic_fixture(self, num_offers: int = 40) -> List[SimulationFixtureEvent]:
        """Generate a deterministic synthetic event stream with realistic state transitions."""
        events: List[SimulationFixtureEvent] = []
        for i in range(num_offers):
            offer_id = f"sim_off_{i:03d}"
            shop_id = f"sim_shop_{i % 8:02d}"  # 8 shops
            category = "mobile_phones" if i < 15 else ("laptops" if i < 30 else "cables")
            base_price = 20_000_000.0 if "phone" in category else (50_000_000.0 if "laptop" in category else 500_000.0)

            # Initial offer
            events.append(
                SimulationFixtureEvent(
                    event_time_hours=0.0,
                    offer_id=offer_id,
                    shop_id=shop_id,
                    category=category,
                    actual_price=base_price,
                    actual_in_stock=True,
                )
            )

            # Volatile price shock for some items around hour 48
            if i in (2, 7, 18):
                events.append(
                    SimulationFixtureEvent(
                        event_time_hours=48.0,
                        offer_id=offer_id,
                        shop_id=shop_id,
                        category=category,
                        actual_price=base_price * 1.15,
                        actual_in_stock=True,
                        is_price_changed=True,
                    )
                )

            # Stock depletion for some items around hour 96
            if i in (4, 12, 22, 35):
                events.append(
                    SimulationFixtureEvent(
                        event_time_hours=96.0,
                        offer_id=offer_id,
                        shop_id=shop_id,
                        category=category,
                        actual_price=base_price,
                        actual_in_stock=False,
                        is_stock_depleted=True,
                    )
                )

            # Customer visit intents at hours 120 and 200
            events.append(
                SimulationFixtureEvent(
                    event_time_hours=120.0,
                    offer_id=offer_id,
                    shop_id=shop_id,
                    category=category,
                    actual_price=base_price,
                    actual_in_stock=False if i in (4, 12, 22, 35) else True,
                    customer_visit_intent=True,
                    customer_detour_min=25.0 if i % 2 == 0 else 5.0,
                )
            )

        events.sort(key=lambda x: x.event_time_hours)
        return events

    def evaluate_policies(
        self,
        fixture_events: Optional[List[SimulationFixtureEvent]] = None,
    ) -> Dict[str, PolicyEvaluationMetrics]:
        """Replay candidate policies against the event stream and compute comparative metrics."""
        events = fixture_events or self.generate_synthetic_fixture()

        policies = [
            "fixed_ttl_72h",
            "category_aware_ttl",
            "heuristic_risk_band",
            "adaptive_voi",
            "budget_constrained_voi",
        ]

        results = {}
        for p in policies:
            results[p] = self._run_single_policy(p, events)

        return results

    def _run_single_policy(
        self,
        policy_name: str,
        events: List[SimulationFixtureEvent],
    ) -> PolicyEvaluationMetrics:
        total_inquiries = 0
        seller_burden = 0.0
        useful_confirmations = 0
        missed_mismatches = 0
        detection_delays = []
        budget_exhaustions = 0

        # State tracking: offer_id -> (last_verified_hours, known_price, known_in_stock)
        offer_state: Dict[str, Tuple[float, float, bool]] = {}
        # Daily shop inquiry counts: (shop_id, day) -> count
        shop_daily_counts: Dict[Tuple[str, int], int] = {}
        # Pending state changes waiting to be verified: offer_id -> transition_time
        pending_changes: Dict[str, float] = {}

        for ev in events:
            day = int(ev.event_time_hours // 24)
            shop_key = (ev.shop_id, day)
            current_shop_count = shop_daily_counts.get(shop_key, 0)

            # Initialize state
            if ev.offer_id not in offer_state:
                offer_state[ev.offer_id] = (0.0, ev.actual_price, ev.actual_in_stock)

            last_verified, known_price, known_stock = offer_state[ev.offer_id]
            elapsed_since_verify = ev.event_time_hours - last_verified

            # Mark state change if transition occurred
            if ev.is_price_changed or ev.is_stock_depleted:
                pending_changes[ev.offer_id] = ev.event_time_hours

            should_inquire = False

            # Policy logic
            if policy_name == "fixed_ttl_72h":
                if elapsed_since_verify >= 72.0:
                    should_inquire = True

            elif policy_name == "category_aware_ttl":
                ttl = 24.0 if "phone" in ev.category else (48.0 if "laptop" in ev.category else 120.0)
                if elapsed_since_verify >= ttl:
                    should_inquire = True

            elif policy_name == "heuristic_risk_band":
                # High risk if elapsed > 48h or high value
                if elapsed_since_verify >= 48.0 and ev.actual_price > 10_000_000.0:
                    should_inquire = True

            elif policy_name == "adaptive_voi":
                # VoI combines intent, elapsed time, and detour
                loss = (40.0 if ev.actual_price > 10_000_000 else 15.0)
                intent_mult = 1.6 if ev.customer_visit_intent else 0.4
                travel_mult = 1.0 + (ev.customer_detour_min / 30.0)
                voi = (loss * intent_mult * travel_mult * 0.7) - 15.0
                if voi > 0 and elapsed_since_verify >= 12.0:
                    should_inquire = True

            elif policy_name == "budget_constrained_voi":
                loss = (40.0 if ev.actual_price > 10_000_000 else 15.0)
                intent_mult = 1.6 if ev.customer_visit_intent else 0.4
                travel_mult = 1.0 + (ev.customer_detour_min / 30.0)
                voi = (loss * intent_mult * travel_mult * 0.7) - 15.0
                if voi > 0 and elapsed_since_verify >= 12.0:
                    if current_shop_count < 10:  # Max 10 per day
                        should_inquire = True
                    else:
                        budget_exhaustions += 1

            if should_inquire:
                total_inquiries += 1
                seller_burden += 1.0 + (current_shop_count * 0.1)
                shop_daily_counts[shop_key] = current_shop_count + 1

                # Update state upon verification
                was_useful = False
                if ev.offer_id in pending_changes:
                    was_useful = True
                    useful_confirmations += 1
                    delay = max(0.0, ev.event_time_hours - pending_changes.pop(ev.offer_id))
                    detection_delays.append(delay)

                offer_state[ev.offer_id] = (ev.event_time_hours, ev.actual_price, ev.actual_in_stock)

            # Customer visit evaluation
            if ev.customer_visit_intent:
                # If shop is actually out of stock or price changed but system did not verify, it's a mismatch
                if (ev.actual_price != known_price) or (ev.actual_in_stock != known_stock):
                    missed_mismatches += 1

        mean_delay = (sum(detection_delays) / len(detection_delays)) if detection_delays else 0.0
        efficiency = (useful_confirmations / total_inquiries * 100.0) if total_inquiries > 0 else 0.0

        return PolicyEvaluationMetrics(
            policy_name=policy_name,
            total_inquiries=total_inquiries,
            seller_burden_score=round(seller_burden, 2),
            useful_confirmations_count=useful_confirmations,
            simulated_missed_mismatches=missed_mismatches,
            mean_detection_delay_hours=round(mean_delay, 2),
            efficiency_useful_per_100_inquiries=round(efficiency, 2),
            budget_exhaustion_events=budget_exhaustions,
        )
