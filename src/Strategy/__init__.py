"""
Package strategy
================
Contient les outils de comparaison de stratégies d'options.
"""

try:
    from .comparer import StrategyComparer
    from .comparison_class import StrategyComparison
except ImportError:
    # Fallback pour compatibilité
    from strategy.comparer import StrategyComparer
    from strategy.comparison_class import StrategyComparison

__all__ = [
    'StrategyComparer',
    'StrategyComparison',
]
