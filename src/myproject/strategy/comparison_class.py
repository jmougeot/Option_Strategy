from dataclasses import dataclass, field
import numpy as np
from typing import Dict, List, Tuple, Literal, Optional, Any
from myproject.option.option_class import Option


@dataclass
class StrategyComparison:
    """Résultat de comparaison d'une stratégie"""

    strategy_name: str
    strategy: Any  # OptionStrategy-like
    target_price: float
    premium: float
    all_options: List[Option]  # Toutes les options
    signs: np.ndarray  # Signes (+1 pour long, -1 pour short) correspondant aux options
    call_count: int
    put_count : int 
    expiration_day: Optional[str]
    expiration_week: Optional[str]
    expiration_month: Literal["F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"]
    expiration_year: int
    max_profit: float
    max_loss: float
    breakeven_points: List[float]
    profit_range: Tuple[float, float]  # Range de prix profitable
    profit_zone_width: float  # Largeur de la zone profitable+
    roll: Optional[float]  # Roll moyen (normalisé par nombre de trimestres)
    roll_quarterly: Optional[float]  # Roll Q-1 (trimestre précédent)
    roll_sum: Optional[float]  # Somme des rolls (non normalisée)
    average_pnl: Optional[float]  # Espérance du P&L avec mixture
    sigma_pnl: Optional[float]  # Écart-type du P&L avec mixture
    prices: np.ndarray
    pnl_array: np.ndarray
    total_delta: float = 0.0  # Delta de la stratégie
    total_gamma: float = 0.0  # Gamma de la stratégie
    total_vega: float = 0.0  # Vega de la stratégie
    total_theta: float = 0.0  # Theta de la stratégie
    avg_implied_volatility: float = 0.0  # Volatilité implicite moyenne des options
    profit_at_target: float = 0.0
    profit_at_target_pct: float = 0.0  # % du max profit
    score: float = 0.0
    rank: int = 0
    rolls_detail: Dict[str, float] = field(default_factory=dict)  # Rolls par expiry (ex: {"H6": 0.5, "M6": 0.3})


    def get_positions(self) -> List[str]:
        """
        Retourne les positions ('long' ou 'short') pour chaque option.

        Returns:
            Liste des positions correspondant aux options dans all_options
        """
        return ["long" if sign > 0 else "short" for sign in self.signs]

    def get_option_with_position(self, index: int) -> Tuple[Option, str]:
        """
        Retourne une option avec sa position.

        Args:
            index: Index de l'option

        Returns:
            Tuple (option, position)
        """
        return (self.all_options[index], "long" if self.signs[index] > 0 else "short")
