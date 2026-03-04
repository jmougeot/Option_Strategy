from dataclasses import dataclass, field
import numpy as np
from typing import Dict, List, Tuple, Literal, Optional, Any
from option.option_class import Option


@dataclass
class StrategyComparison:
    """Résultat de comparaison d'une stratégie"""

    strategy_name: str
    premium: float
    all_options: List[Option]  # Toutes les options
    signs: np.ndarray  # Signes (+1 pour long, -1 pour short) correspondant aux options
    call_count: int
    put_count : int 
    expiration_month: Literal["F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"]
    expiration_year: int
    max_profit: float
    max_loss: float
    breakeven_points: List[float]
    profit_range: Tuple[float, float]  # Range de prix profitable
    profit_zone_width: float  # Largeur de la zone profitable+
    average_pnl: float  # Espérance du P&L avec mixture
    sigma_pnl: Optional[float]  # Écart-type du P&L avec mixture
    prices: np.ndarray
    pnl_array: np.ndarray
    total_delta: float = 0.0  # Delta de la stratégie
    total_gamma: float = 0.0  # Gamma de la stratégie
    total_vega: float = 0.0  # Vega de la stratégie
    total_theta: float = 0.0  # Theta de la stratégie
    total_iv: float = 0.0  # Volatilité implicite moyenne des options
    profit_at_target: float = 0.0
    score: float = 0.0
    rank: int = 0
    rolls_detail: Dict[str, float] = field(default_factory=dict)  # Rolls par expiry (ex: {"H6": 0.5, "M6": 0.3})
    delta_levrage : float = 0.0
    avg_pnl_levrage : float = 0.0 # avg/premium
