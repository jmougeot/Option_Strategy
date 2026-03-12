from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional


class Position(Enum):
    """Position sur une option : long (acheteur) ou short (vendeur)."""
    LONG = "long"
    SHORT = "short"


# Alias pour la compatibilité avec les annotations de type existantes
PositionType = Literal["long", "short"]


@dataclass
class BaseOption:
    """
    Champs communs entre Option (pricing/analytics) et OptionLeg (alarme live Bloomberg).

    Hériter de cette classe pour bénéficier de l'interface minimale partagée :
    identification du ticker, sous-jacent, quantité, strike, cotations BBO,
    Greeks de base et volatilité implicite.
    """
    ticker: Optional[str] = None
    underlying_symbol: Optional[str] = None
    quantity: Optional[int] = 1
    strike: float = 0.0

    # ========== PRIX ET COTATIONS ================
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    mid: Optional[float] = None

    # ================== GREEKS ===================
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None

    # ============ VOLATILITÉ ============
    implied_volatility: Optional[float] = None
