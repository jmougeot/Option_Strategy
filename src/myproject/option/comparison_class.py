from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from datetime import datetime
from typing import Any
from myproject.option.option_class import Option

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


    all_options: List[Option] = field(default_factory=list)  # Toutes les options

    # Greeks exposure - Calls
    total_delta_calls: float = 0.0   # Delta total des calls
    total_gamma_calls: float = 0.0   # Gamma total des calls
    total_vega_calls: float = 0.0    # Vega total des calls
    total_theta_calls: float = 0.0   # Theta total des calls
    
    # Greeks exposure - Puts
    total_delta_puts: float = 0.0    # Delta total des puts
    total_gamma_puts: float = 0.0    # Gamma total des puts
    total_vega_puts: float = 0.0     # Vega total des puts
    total_theta_puts: float = 0.0    # Theta total des puts
    
    # Greeks exposure - Total stratégie
    total_delta: float = 0.0         # Delta total de la stratégie
    total_gamma: float = 0.0         # Gamma total de la stratégie
    total_vega: float = 0.0          # Vega total de la stratégie
    total_theta: float = 0.0         # Theta total de la stratégie
    
    # Volatilité implicite
    avg_implied_volatility: float = 0.0  # Volatilité implicite moyenne des options

    # Performance au prix cible
    profit_at_target: float = 0.0
    profit_at_target_pct: float = 0.0  # % du max profit

    # Score et ranking
    score: float = 0.0
    rank: int = 0
