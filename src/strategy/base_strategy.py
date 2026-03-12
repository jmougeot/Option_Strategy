from dataclasses import dataclass, field
from typing import List

from option.base_option import BaseOption


@dataclass
class BaseStrategy:
    """
    Champs communs entre Strategy (alarme live/persistante) et
    StrategyComparison (résultat de ranking du générateur).
    """
    name: str = "Nouvelle Stratégie"
    total_delta: float = 0.0
    total_gamma: float = 0.0
    total_theta: float = 0.0
