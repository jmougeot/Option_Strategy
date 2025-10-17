from dataclasses import dataclass
from typing import List, Tuple
from datetime import datetime
from typing import Any

@dataclass
class StrategyComparison:
    """Résultat de comparaison d'une stratégie"""
    strategy_name: str
    strategy: Any  # OptionStrategy-like
    target_price: float
    expiration_date: datetime
    days_to_expiry: int

    # Métriques financières
    net_credit: float
    max_profit: float
    max_loss: float
    breakeven_points: List[float]

    # Métriques de risque
    profit_range: Tuple[float, float]  # Range de prix profitable
    profit_zone_width: float  # Largeur de la zone profitable
    risk_reward_ratio: float  # Max loss / Max profit

    # Performance au prix cible
    profit_at_target: float
    profit_at_target_pct: float  # % du max profit

    # Score et ranking
    score: float = 0.0
    rank: int = 0
