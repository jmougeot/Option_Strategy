"""
Package options
===============
Contient les définitions des options et les stratégies générées automatiquement.
"""

from .option_class import OptionStrategy, GENERATED_STRATEGIES
from .option_avaible import STRATEGY_DEFINITIONS

__all__ = [
    'OptionStrategy',
    'GENERATED_STRATEGIES',
    'STRATEGY_DEFINITIONS',
]
