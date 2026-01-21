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

import re
from typing import Literal, Optional

# Type pour les mois valides
MonthCode = Literal["F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"]
VALID_MONTHS = {"F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"}


def parse_brut_code(brut_code: str) -> dict:
    """
    Parse un code brut Bloomberg pour extraire les métadonnées.
    
    Exemples de codes bruts:
    - "ERF6C" → underlying="ER", month="F", year=6, option_type="call"
    - "RXWF26C2" → underlying="RXW", month="F", year=26, option_type="call"
    - "RXWF26P2" → underlying="RXW", month="F", year=26, option_type="put"
    
    Format: [UNDERLYING][MONTH][YEAR][C/P][SUFFIX?]
    
    Returns:
        Dict avec underlying, month, year, option_type
    """
    code = brut_code.upper().strip()
    
    # Pattern: lettres + mois (une lettre valide) + année (1-2 chiffres) + C/P + suffix optionnel
    # Ex: RXW F 26 C 2 ou ER H 6 C
    pattern = r'^([A-Z]+)([FGHJKMNQUVXZ])(\d{1,2})([CP])(\d*)$'
    match = re.match(pattern, code)
    
    if match:
        underlying = match.group(1)
        month = match.group(2)
        year = int(match.group(3))
        option_type = "call" if match.group(4) == "C" else "put"
    else:
        # Fallback: ancien parsing
        if "C" in code:
            option_type = "call"
            code_without_type = code.replace("C", "", 1)
        elif "P" in code:
            option_type = "put"
            code_without_type = code.replace("P", "", 1)
        else:
            option_type = "call"
            code_without_type = code
        
        match_year = re.search(r'(\d{1,2})', code_without_type)
        if match_year:
            year = int(match_year.group(1))
            code_without_year = code_without_type[:match_year.start()]
        else:
            year = 6
            code_without_year = code_without_type
        
        month = ""
        underlying = code_without_year
        if code_without_year:
            last_char = code_without_year[-1].upper()
            if last_char in VALID_MONTHS:
                month = last_char
                underlying = code_without_year[:-1]
    
    return {
        "underlying": underlying,
        "month": month,
        "year": year,
        "option_type": option_type,
    }


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



