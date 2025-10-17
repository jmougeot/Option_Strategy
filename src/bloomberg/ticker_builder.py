"""
Bloomberg Ticker Builder
========================
Construction intelligente des tickers Bloomberg pour options.

Supporte:
- Options sur actions (equity): "AAPL 12/20/24 C150 Equity"
- Options sur indices: "SPX 12/20/24 P4500 Index"
- Options EURIBOR (taux): "ER H5 C97.50 Comdty"

Auteur: BGC Trading Desk
Date: 2026-10-16
"""

from datetime import date, datetime
from typing import Literal, Optional


# Codes mensuels Bloomberg (pour les futures et options de taux)
MONTH_CODES = {
    1: 'F',   # Janvier
    2: 'G',   # Février
    3: 'H',   # Mars
    4: 'J',   # Avril
    5: 'K',   # Mai
    6: 'M',   # Juin
    7: 'N',   # Juillet
    8: 'Q',   # Août
    9: 'U',   # Septembre
    10: 'V',  # Octobre
    11: 'X',  # Novembre
    12: 'Z'   # Décembre
}

def build_option_ticker(
    underlying: str,
    expiry_month : Literal['F' , 'G', 'H', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z' ],
    expiry_year : int,
    option_type: Literal['C', 'P'],
    strike: float,
    suffix: Optional[str] = None
) -> str:
    """
    Construit un ticker d'option sur action ou indice.
    """
    ticker = f"{underlying.upper()}{expiry_month}{expiry_year}{option_type} {strike} {suffix}"
    return ticker
    
