"""
Package options
===============
Contient les définitions des options et les stratégies générées automatiquement.
"""

try:
    from .option_class import OptionStrategy, GENERATED_STRATEGIES
    from .option_avaible import STRATEGY_DEFINITIONS
except ImportError:
    # Fallback pour compatibilité
    from options.option_class import OptionStrategy, GENERATED_STRATEGIES
    from options.option_avaible import STRATEGY_DEFINITIONS

__all__ = [
    'OptionStrategy',
    'GENERATED_STRATEGIES',
    'STRATEGY_DEFINITIONS',
]
