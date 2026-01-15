from dataclasses import dataclass
import numpy as np
from typing import List, Tuple, Literal, Optional
from typing import Any
from myproject.option.option_class import Option


@dataclass
class StrategyComparison:
    """Résultat de comparaison d'une stratégie"""

    strategy_name: str
    strategy: Any  # OptionStrategy-like
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
    surface_profit: Optional[float]  # surface of profit btw min price and max price
    surface_loss: Optional[float]  # surface of loss btw min price and max price
    average_pnl: Optional[float]  # Espérance du P&L avec mixture
    sigma_pnl: Optional[float]  # Écart-type du P&L avec mixture
    surface_loss_ponderated: float
    surface_profit_ponderated: float  # Probabilité de gain
    prices: np.ndarray
    pnl_array: np.ndarray
    risk_reward_ratio: float  # Max loss / Max profit
    risk_reward_ratio_ponderated: float
    total_delta: float = 0.0  # Delta de la stratégie
    total_gamma: float = 0.0  # Gamma de la stratégie
    total_vega: float = 0.0  # Vega de la stratégie
    total_theta: float = 0.0  # Theta de la stratégie
    avg_implied_volatility: float = 0.0  # Volatilité implicite moyenne des options
    profit_at_target: float = 0.0
    profit_at_target_pct: float = 0.0  # % du max profit
    score: float = 0.0
    rank: int = 0

    def _risk_reward_ratio(self):
        self.risk_reward_ratio = self.max_profit / self.max_loss

    def _risk_reward_ratio_ponderated(self):
        self.risk_reward_ratio_ponderated = (
            self.surface_profit_ponderated / self.surface_loss_ponderated
        )

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
