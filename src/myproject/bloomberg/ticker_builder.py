"""
Bloomberg Ticker Builder
========================
Construction intelligente des tickers Bloomberg pour options.

Supporte:
- Options EURIBOR (taux): "ERH5C 97.5 Comdty"
  Format: [UNDERLYING][MONTH][YEAR][TYPE] [STRIKE] [SUFFIX]
  Exemple: ER + H + 5 + C + " " + 97.5 + " " + Comdty = "ERH5C 97.5 Comdty"

Auteur: BGC Trading Desk
Date: 2025-10-17
"""

from typing import Literal, Optional


def build_option_ticker(
    underlying: str,
    expiry_month: Literal["F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"],
    expiry_year: int,
    option_type: Literal["C", "P"],
    strike: float,
    suffix: Optional[str] = None,
) -> str:
    """
    Construit un ticker Bloomberg pour options EURIBOR.

    Format Bloomberg: [UNDERLYING][MONTH][YEAR][TYPE] [STRIKE] [SUFFIX]

    Args:
        underlying: Symbole du sous-jacent (ex: "ER" pour EURIBOR)
        expiry_month: Code mois Bloomberg ('F', 'G', 'H', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z')
        expiry_year: Année sur 1 chiffre (ex: 5 pour 2025)
        option_type: 'C' pour Call ou 'P' pour Put
        strike: Prix d'exercice (ex: 97.5)
        suffix: Suffixe Bloomberg (ex: "Comdty" pour commodités)

    Returns:
        Ticker Bloomberg formaté (ex: "ERH5C 97.5 Comdty")

    Examples:
        >>> build_option_ticker("ER", "H", 5, "C", 97.5, "Comdty")
        'ERH5C 97.5 Comdty'
        >>> build_option_ticker("ER", "M", 5, "P", 98.0, "Comdty")
        'ERM5P 98.0 Comdty'
    """
    # Arrondir le strike pour éviter les problèmes de précision flottante
    # (ex: 107.09999999999997 → 107.1)
    strike_rounded = round(strike, 5)  # 5 décimales suffisent pour les options
    
    # Format: ERH5C 97.5 Comdty (PAS d'espaces entre underlying, month, year, type)
    ticker = f"{underlying.upper()}{expiry_month}{expiry_year}{option_type} {strike_rounded}"

    # Ajouter le suffixe si fourni
    if suffix:
        ticker = f"{ticker} {suffix}"

    return ticker

def build_option_ticker_brut(
        brut_code:str,
        strike: float,
        suffix: str
    ) -> str :
    """
    Construit un ticket avec le code brut
    """
    # Arrondir le strike pour éviter les problèmes de précision flottante
    strike_rounded = round(strike, 5)
    ticker=f"{brut_code} {strike_rounded} {suffix}"
    
    return ticker



