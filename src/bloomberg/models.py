"""
Bloomberg Data Models
====================
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional, Literal


@dataclass
class OptionData:
    """
    Données complètes pour une option (sous jacent, indices, taux).

    """
    # Identification
    ticker: str
    underlying: str
    option_type: str  # 'CALL' ou 'PUT'
    strike: float
    expiry_month: Literal['F' , 'G', 'H', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z' ]
    expiry_year: int
    
    # Prix de marché
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    mid: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    
    # Greeks (sensibilités aux facteurs de marché)
    delta: Optional[float] = None  # Sensibilité au prix du sous-jacent
    gamma: Optional[float] = None  # Sensibilité du delta
    vega: Optional[float] = None   # Sensibilité à la volatilité
    theta: Optional[float] = None  # Déclin temporel
    rho: Optional[float] = None    # Sensibilité aux taux
    
    # Volatilité implicite
    implied_volatility: Optional[float] = None  # En %
    
    def __repr__(self) -> str:
        """Affichage condensé pour debug."""
        return (
            f"OptionData({self.ticker} | "
            f"Strike={self.strike} | Last={self.last} | "
            f"Delta={self.delta} | IV={self.implied_volatility}%)"
        )
    
    @property
    def spread(self) -> Optional[float]:
        """Calcule le spread bid-ask si disponible."""
        if self.bid is not None and self.ask is not None:
            return self.ask - self.bid
        return None
    
    @property
    def is_liquid(self) -> bool:
        """
        Vérifie si l'option est liquide (critères simples).
        
        Critères:
        - Volume > 0 ou Open Interest > 10
        - Spread < 10% du mid (si disponible)
        """
        has_volume = (self.volume or 0) > 0 or (self.open_interest or 0) > 10
        
        if self.mid and self.spread:
            tight_spread = self.spread < (self.mid * 0.10)
            return has_volume and tight_spread
        
        return has_volume
    