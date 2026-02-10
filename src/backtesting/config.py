"""
Configuration du backtesting SFR (SOFR Futures Options)
========================================================
Paramètres centralisés pour l'import Bloomberg et le calcul
de la distribution implicite.
"""

from dataclasses import dataclass, field
from typing import List
from datetime import date


# ============================================================================
# CONFIGURATION SFR
# ============================================================================

@dataclass
class SFRConfig:
    """
    Configuration pour l'import des options SFR (SOFR).

    Ticker Bloomberg format:
        SFR{MONTH}{YEAR}{C/P} {STRIKE} Comdty
        Exemple: SFRH5C 96.00 Comdty

    Attributes:
        underlying: Préfixe du sous-jacent Bloomberg (SFR)
        suffix: Suffixe Bloomberg (Comdty)
        expiry_month: Code mois d'expiration (H = Mars)
        expiry_year: Année d'expiration sur 1 chiffre (5 = 2025)
        strike_min: Strike minimum (95.0)
        strike_max: Strike maximum (97.0)
        strike_step: Pas entre les strikes (0.125 = 12.5 bps pour SOFR)
        start_date: Date de début de l'historique
        end_date: Date de fin de l'historique (expiration)
        field: Champ Bloomberg à récupérer
    """
    underlying: str = "SFR"
    suffix: str = "Comdty"
    expiry_month: str = "H"
    expiry_year: int = 5
    strike_min: float = 95.0
    strike_max: float = 97.0
    strike_step: float = 0.125
    start_date: date = field(default_factory=lambda: date(2024, 7, 30))
    end_date: date = field(default_factory=lambda: date(2025, 3, 13))
    bbg_field: str = "PX_LAST"

    # ---- Paramètres de distribution ----
    risk_free_rate: float = 0.0
    price_grid_points: int = 500
    price_grid_margin: float = 1.0  # marge autour de [strike_min, strike_max]

    @property
    def strikes(self) -> List[float]:
        """Liste de tous les strikes entre min et max avec le pas donné."""
        strikes = []
        k = self.strike_min
        while k <= self.strike_max + 1e-9:
            strikes.append(round(k, 4))
            k += self.strike_step
        return strikes

    @property
    def start_date_str(self) -> str:
        """Date de début au format Bloomberg (YYYYMMDD)."""
        return self.start_date.strftime("%Y%m%d")

    @property
    def end_date_str(self) -> str:
        """Date de fin au format Bloomberg (YYYYMMDD)."""
        return self.end_date.strftime("%Y%m%d")

    @property
    def full_year(self) -> int:
        """Année complète (2025 pour year=5)."""
        return 2020 + self.expiry_year


# ============================================================================
# CONFIGURATION PAR DÉFAUT
# ============================================================================

DEFAULT_CONFIG = SFRConfig()
