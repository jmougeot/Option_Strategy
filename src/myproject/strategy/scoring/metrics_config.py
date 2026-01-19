"""
Configuration des métriques de scoring
"""

from typing import List, Callable, Tuple
from dataclasses import dataclass

from myproject.strategy.comparison_class import StrategyComparison
from myproject.strategy.scoring.helpers import safe_value
from myproject.strategy.scoring.normalizers import normalize_max, normalize_min_max, normalize_count
from myproject.strategy.scoring.scorers import (
    score_higher_better,
    score_lower_better,
    score_moderate_better,
    score_call_put,
)


@dataclass
class MetricConfig:
    """Configuration pour une métrique de scoring."""

    name: str
    weight: float
    extractor: Callable[[StrategyComparison], float]
    normalizer: Callable[[List[float]], Tuple[float, float]]
    scorer: Callable[[float, float, float], float]


def create_metrics_config() -> List[MetricConfig]:
    """
    Crée la configuration de toutes les métriques.
    Note: Les poids seront automatiquement normalisés à 1.0 lors du calcul.
    """
    return [
        # ========== GREEKS (optimisés pour neutralité) ==========
        MetricConfig(
            name="delta_neutral",
            weight=0.08,
            extractor=lambda s: abs(safe_value(s.total_delta)),
            normalizer=normalize_max,
            scorer=score_lower_better,
        ),
        MetricConfig(
            name="gamma_low",
            weight=0.05,
            extractor=lambda s: abs(safe_value(s.total_gamma)),
            normalizer=normalize_max,
            scorer=score_lower_better,
        ),
        MetricConfig(
            name="vega_low",
            weight=0.05,
            extractor=lambda s: abs(safe_value(s.total_vega)),
            normalizer=normalize_max,
            scorer=score_lower_better,
        ),
        MetricConfig(
            name="theta_positive",
            weight=0.05,
            extractor=lambda s: safe_value(s.total_theta),
            normalizer=normalize_min_max,
            scorer=score_higher_better,
        ),
        # ========== VOLATILITÉ ==========
        MetricConfig(
            name="implied_vol_moderate",
            weight=0.04,
            extractor=lambda s: safe_value(s.avg_implied_volatility),
            normalizer=normalize_min_max,
            scorer=score_moderate_better,
        ),
        # ========== MÉTRIQUES GAUSSIENNES (MIXTURE) ==========
        MetricConfig(
            name="average_pnl",
            weight=0.20,
            extractor=lambda s: safe_value(s.average_pnl),
            normalizer=normalize_min_max,
            scorer=score_higher_better,
        ),
        MetricConfig(
            name="roll",
            weight=0.06,
            extractor=lambda s: safe_value(s.roll),
            normalizer=normalize_min_max,
            scorer=score_higher_better,
        ),
        MetricConfig(
            name="roll_quarterly",
            weight=0.06,
            extractor=lambda s: safe_value(s.roll_quarterly),
            normalizer=normalize_min_max,
            scorer=score_higher_better,
        ),
        MetricConfig(
            name="sigma_pnl",
            weight=0.05,
            extractor=lambda s: safe_value(s.sigma_pnl),
            normalizer=normalize_max,
            scorer=score_lower_better,
        ),
    ]
