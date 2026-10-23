"""Calibration, Uncertainty Infrastructure & Model Interfaces.

Provides strict separation between heuristic risk scores and empirical calibrated probabilities.
Implements evaluation metrics (Brier Score, Log Loss, Reliability Diagrams, ECE) for synthetic fixtures,
and defines standard abstract interfaces for future statistical and ML models.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger("torob.intelligence.calibration")


@dataclass
class CalibratedPredictionOutput:
    """Strict output container separating heuristics from calibrated probabilities."""
    entity_id: str
    target_event: str  # price_mismatch | stock_unavailable | shop_closed
    heuristic_risk_score: float  # 0.0 - 100.0 heuristic
    evidence_freshness_hours: Optional[float]
    evidence_quality: str  # limited | moderate | high
    calibrated_probability: Optional[float] = None  # Strictly None unless validated on gold labels
    confidence_interval_95: Optional[Tuple[float, float]] = None
    is_empirically_calibrated: bool = False
    calibration_provenance: Optional[str] = None
    reasons: List[str] = field(default_factory=list)


@dataclass
class ReliabilityBin:
    bin_index: int
    bin_range: Tuple[float, float]
    predicted_mean: float
    observed_frequency: float
    sample_count: int
    absolute_calibration_error: float


@dataclass
class CalibrationEvaluationResult:
    brier_score: float
    log_loss: float
    expected_calibration_error: float  # ECE
    total_samples: int
    reliability_bins: List[ReliabilityBin]
    is_simulation_only: bool = True
    caveat: str = "Evaluated on deterministic synthetic fixtures; real-world calibration requires true verified outcome labels."


class CalibrationEvaluator:
    @staticmethod
    def evaluate_binary_calibration(
        predicted_probabilities: List[float],
        true_binary_labels: List[int],
        num_bins: int = 10,
    ) -> CalibrationEvaluationResult:
        """Compute Brier Score, Log Loss, and Reliability Diagram bins."""
        if len(predicted_probabilities) != len(true_binary_labels):
            raise ValueError("Predictions and labels must have identical length")
        n = len(predicted_probabilities)
        if n == 0:
            raise ValueError("Cannot evaluate calibration on empty dataset")

        # 1. Brier Score: 1/N * sum((p - y)^2)
        brier = sum((p - y) ** 2 for p, y in zip(predicted_probabilities, true_binary_labels)) / n

        # 2. Log Loss (cross entropy with epsilon clamping)
        eps = 1e-12
        log_loss_sum = 0.0
        for p, y in zip(predicted_probabilities, true_binary_labels):
            p_clamped = min(max(p, eps), 1.0 - eps)
            log_loss_sum += -(y * math.log(p_clamped) + (1.0 - y) * math.log(1.0 - p_clamped))
        log_loss = log_loss_sum / n

        # 3. Reliability Diagram Bins & ECE
        bin_width = 1.0 / num_bins
        bins: List[ReliabilityBin] = []
        ece = 0.0

        for b in range(num_bins):
            low = b * bin_width
            high = (b + 1) * bin_width
            # Samples falling in this probability bin
            bin_preds = []
            bin_labels = []
            for p, y in zip(predicted_probabilities, true_binary_labels):
                if b == num_bins - 1:
                    in_bin = (low <= p <= high)
                else:
                    in_bin = (low <= p < high)
                if in_bin:
                    bin_preds.append(p)
                    bin_labels.append(y)

            count = len(bin_preds)
            if count > 0:
                pred_mean = sum(bin_preds) / count
                obs_freq = sum(bin_labels) / count
                abs_err = abs(pred_mean - obs_freq)
                ece += (count / n) * abs_err
            else:
                pred_mean = (low + high) / 2.0
                obs_freq = 0.0
                abs_err = 0.0

            bins.append(
                ReliabilityBin(
                    bin_index=b,
                    bin_range=(round(low, 2), round(high, 2)),
                    predicted_mean=round(pred_mean, 4),
                    observed_frequency=round(obs_freq, 4),
                    sample_count=count,
                    absolute_calibration_error=round(abs_err, 4),
                )
            )

        return CalibrationEvaluationResult(
            brier_score=round(brier, 5),
            log_loss=round(log_loss, 5),
            expected_calibration_error=round(ece, 5),
            total_samples=n,
            reliability_bins=bins,
        )


# =====================================================================
# Abstract Model Interfaces for Future ML/Statistical Upgrades
# =====================================================================

class PriceChangeHazardModel(ABC):
    """Abstract hazard rate estimator for time-to-price-change."""
    @abstractmethod
    def estimate_hazard_rate(
        self,
        offer_features: Dict[str, Any],
        elapsed_hours_since_change: float,
    ) -> float:
        """Returns the instantaneous hazard rate h(t) of a price change."""
        pass


class InventorySurvivalModel(ABC):
    """Abstract survival model for physical stock availability over customer travel time."""
    @abstractmethod
    def predict_survival_probability(
        self,
        stock_features: Dict[str, Any],
        elapsed_hours_since_verification: float,
        customer_eta_hours: float,
    ) -> float:
        """Returns P(T > t_arrival | T > t_verification)."""
        pass


class ShopResponsePropensityModel(ABC):
    """Abstract response propensity model for merchant inquiry responsiveness."""
    @abstractmethod
    def predict_response_probability(
        self,
        shop_features: Dict[str, Any],
        request_features: Dict[str, Any],
    ) -> float:
        """Returns P(Response received before deadline)."""
        pass


class InquiryPolicyValueEstimator(ABC):
    """Abstract decision-theoretic value estimator for candidate verifications."""
    @abstractmethod
    def estimate_value_of_information(
        self,
        offer_context: Dict[str, Any],
        market_context: Dict[str, Any],
        user_intent: str,
    ) -> float:
        """Returns expected net utility of triggering an inquiry."""
        pass
