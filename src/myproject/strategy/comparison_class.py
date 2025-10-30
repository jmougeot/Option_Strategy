from dataclasses import dataclass, field
import numpy as np
from typing import List, Tuple, Literal, Optional
from typing import Any
from myproject.option.option_class import Option

@dataclass
class StrategyComparison:
    """Résultat de comparaison d'une stratégie"""
    strategy_name: str
    strategy: Any  # OptionStrategy-like
    target_price: float
    premium : float 

    # Epiration date
    expiration_day : Optional[str]
    expiration_week : Optional[str]
    expiration_month : Literal['F' , 'G', 'H', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z' ]
    expiration_year : int

    # Métriques financières
    max_profit: float
    max_loss: float
    breakeven_points: List[float]

    # Métriques de risque
    profit_range: Tuple[float, float]  # Range de prix profitable
    profit_zone_width: float  # Largeur de la zone profitable+
    surface_profit: float # surface of profit btw min price and max price 
    surface_loss:float # surface of loss btw min price and max price 
    risk_reward_ratio: float  # Max loss / Max profit
    prices : np.ndarray
    pnl_array : np.ndarray

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

    # Métriques pondérées par mixture gaussienne
    average_pnl: Optional[float] = None  # Espérance du P&L avec mixture
    sigma_pnl: Optional[float] = None    # Écart-type du P&L avec mixture

    # Performance au prix cible
    profit_at_target: float = 0.0
    profit_at_target_pct: float = 0.0  # % du max profit

    # Score et ranking
    score: float = 0.0
    rank: int = 0
