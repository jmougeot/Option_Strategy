"""
Module de Scoring pour les Stratégies d'Options
================================================
Architecture modulaire pour le calcul des scores:
- metrics_config.py: Configuration des métriques
- normalizers.py: Fonctions de normalisation
- scorers.py: Fonctions de scoring
- comparer.py: Comparateur principal
"""

from myproject.strategy.scoring.comparer import StrategyComparerV2
from myproject.strategy.scoring.metrics_config import MetricConfig, create_metrics_config

__all__ = ["StrategyComparerV2", "MetricConfig", "create_metrics_config"]
